from __future__ import annotations

import gc
import json
import os
import shutil
import tempfile
import time
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import ctranslate2
import yt_dlp
from faster_whisper import WhisperModel, BatchedInferencePipeline
from youtube_transcript_api import (
    FetchedTranscript,
    YouTubeTranscriptApi,
)

from configs.settings import MODEL_DIR
from configs.schema import TranscriptSegment, TranscriptPayload

TRADITIONAL_CHINESE_LANGUAGES = (
    "zh-TW",
    "zh-Hant",
    "zh-HK",
)
TRADITIONAL_CHINESE_LANGUAGE_SET = {
    item.lower()
    for item in TRADITIONAL_CHINESE_LANGUAGES
}
PREFERRED_SOURCE_LANGUAGES = (
    *TRADITIONAL_CHINESE_LANGUAGES,
    "zh-CN",
    "zh-Hans",
    "zh",
    "en-US",
    "en-GB",
    "en",
)
TRANSLATION_LANGUAGE_PREFERENCES = (
    "zh-TW",
    "zh-Hant",
    "zh-HK",
    "zh",
)

def fetch_video_transcript(url: str, *, video_id: str) -> TranscriptPayload:
    caption_error: Optional[Exception] = None

    try:
        started_at = time.perf_counter()
        payload = _fetch_caption_transcript(video_id)
        print(
            f"[transcript] YouTube captions source={payload.source} "
            f"elapsed={time.perf_counter() - started_at:.2f}s"
        )
        return payload
    except Exception as exc:
        caption_error = exc
        print(f"[transcript] captions unavailable, using Whisper: {type(exc).__name__}: {exc}")

    try:
        if _get_env_bool("WHISPER_UNLOAD_OLLAMA_BEFORE_TRANSCRIBE", True):
            _unload_ollama_model()
        started_at = time.perf_counter()
        payload = _transcribe_audio(url)
        print(f"[transcript] Whisper total: {time.perf_counter() - started_at:.2f}s")
        return payload
    except Exception as exc:
        if caption_error is not None:
            raise RuntimeError(
                f"Transcript unavailable from captions and Whisper fallback failed: "
                f"{type(caption_error).__name__}: {caption_error}; "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        raise

def _fetch_caption_transcript(video_id: str) -> TranscriptPayload:
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    transcripts = list(transcript_list)

    manual = [item for item in transcripts if not bool(getattr(item, "is_generated", False))]
    generated = [item for item in transcripts if bool(getattr(item, "is_generated", False))]
    errors: list[str] = []

    for direct_manual in _direct_traditional_captions(manual):
        try:
            return _fetch_caption_payload(direct_manual, source="caption_manual")
        except Exception as exc:
            errors.append(_caption_error(direct_manual, exc))

    for translated_manual in _translatable_captions(manual):
        try:
            return _fetch_translated_caption_payload(
                translated_manual,
                source="caption_manual_translated",
            )
        except Exception as exc:
            errors.append(_caption_error(translated_manual, exc))

    for original_manual in _caption_candidates(manual):
        try:
            return _fetch_caption_payload(original_manual, source="caption_manual")
        except Exception as exc:
            errors.append(_caption_error(original_manual, exc))

    for direct_generated in _direct_traditional_captions(generated):
        try:
            return _fetch_caption_payload(direct_generated, source="caption_generated")
        except Exception as exc:
            errors.append(_caption_error(direct_generated, exc))

    for translated_generated in _translatable_captions(generated):
        try:
            return _fetch_translated_caption_payload(
                translated_generated,
                source="caption_generated_translated",
            )
        except Exception as exc:
            errors.append(_caption_error(translated_generated, exc))

    for original_generated in _caption_candidates(generated):
        try:
            return _fetch_caption_payload(original_generated, source="caption_generated")
        except Exception as exc:
            errors.append(_caption_error(original_generated, exc))

    detail = "; ".join(errors[-4:])
    if detail:
        raise RuntimeError(f"No usable manual or generated captions available: {detail}")
    raise RuntimeError("No usable manual or generated captions available")

def _fetch_caption_payload(transcript, *, source: str) -> TranscriptPayload:
    fetched = transcript.fetch(preserve_formatting=False)
    language = getattr(transcript, "language_code", "") or getattr(fetched, "language_code", "")
    return TranscriptPayload(
        language=str(language or "unknown"),
        source=source,
        segments=_to_segments(fetched),
        source_language=str(language or "unknown"),
    )

def _fetch_translated_caption_payload(transcript, *, source: str) -> TranscriptPayload:
    target_language = _pick_translation_language(transcript)
    if target_language is None:
        raise RuntimeError("Caption does not provide a supported Chinese translation")

    source_language = str(getattr(transcript, "language_code", "") or "unknown")
    translated = transcript.translate(target_language)
    fetched = translated.fetch(preserve_formatting=False)
    return TranscriptPayload(
        language=target_language,
        source=source,
        segments=_to_segments(fetched),
        source_language=source_language,
        translated=True,
        translation_provider="youtube",
    )

def _direct_traditional_captions(transcripts):
    candidates = [
        item
        for item in transcripts
        if _is_traditional_chinese(getattr(item, "language_code", ""))
    ]
    candidates.sort(key=_caption_rank)
    return candidates

def _translatable_captions(transcripts):
    candidates = [
        item
        for item in transcripts
        if bool(getattr(item, "is_translatable", False))
        and _pick_translation_language(item) is not None
    ]
    candidates.sort(key=_caption_rank)
    return candidates

def _caption_candidates(transcripts):
    candidates = list(transcripts)
    candidates.sort(key=_caption_rank)
    return candidates

def _caption_rank(transcript) -> tuple[int, str]:
    language_code = str(getattr(transcript, "language_code", "") or "")
    try:
        language_rank = PREFERRED_SOURCE_LANGUAGES.index(language_code)
    except ValueError:
        language_rank = len(PREFERRED_SOURCE_LANGUAGES)
    return language_rank, language_code

def _pick_translation_language(transcript) -> str | None:
    available: set[str] = set()
    for item in getattr(transcript, "translation_languages", []) or []:
        if isinstance(item, dict):
            code = item.get("language_code")
        else:
            code = getattr(item, "language_code", "")
        if code:
            available.add(str(code))

    for language_code in TRANSLATION_LANGUAGE_PREFERENCES:
        if language_code in available:
            return language_code
    return None

def _is_traditional_chinese(language: str) -> bool:
    normalized = str(language or "").strip().lower()
    return normalized in TRADITIONAL_CHINESE_LANGUAGE_SET

def _caption_error(transcript, exc: Exception) -> str:
    language = str(getattr(transcript, "language_code", "") or "unknown")
    return f"{language}: {type(exc).__name__}: {exc}"

def _to_segments(fetched: FetchedTranscript) -> List[TranscriptSegment]:
    segments: List[TranscriptSegment] = []
    for item in fetched:
        text = str(getattr(item, "text", "")).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                text=text,
                start=float(getattr(item, "start", 0.0) or 0.0),
                duration=float(getattr(item, "duration", 0.0) or 0.0),
            )
        )
    if not segments:
        raise RuntimeError("Transcript is empty")
    return segments

def _transcribe_audio(url: str) -> TranscriptPayload:
    download_started_at = time.perf_counter()
    audio_path, temp_dir = _download_audio(url)
    print(f"[transcript] audio download: {time.perf_counter() - download_started_at:.2f}s")
    try:
        model_started_at = time.perf_counter()
        model = _get_whisper_model()
        print(f"[transcript] Whisper model ready: {time.perf_counter() - model_started_at:.2f}s")
        batch_model = BatchedInferencePipeline(model=model)
        batch_size = _get_env_int("WHISPER_BATCH_SIZE", 16)
        beam_size = _get_env_int("WHISPER_BEAM_SIZE", 8)
        patience = _get_env_float("WHISPER_PATIENCE", 1.2)
        condition_on_previous_text = _get_env_bool("WHISPER_CONDITION_ON_PREVIOUS_TEXT", True)
        inference_started_at = time.perf_counter()
        segments_iter, info = batch_model.transcribe(
            audio_path,
            batch_size=max(1, batch_size),
            vad_filter=True,
            beam_size=max(1, beam_size),
            patience=max(1.0, patience),
            temperature=0.0,
            without_timestamps=False,
            condition_on_previous_text=condition_on_previous_text,
        )
        segments = [
            TranscriptSegment(
                text=str(segment.text).strip(),
                start=float(segment.start),
                duration=max(0.0, float(segment.end) - float(segment.start)),
            )
            for segment in segments_iter
            if str(segment.text).strip()
        ]
        print(f"[transcript] Whisper inference: {time.perf_counter() - inference_started_at:.2f}s")
        if not segments:
            raise RuntimeError("Whisper produced no transcript segments")
        language = str(getattr(info, "language", "") or "unknown")
        return TranscriptPayload(
            language=language,
            source="whisper",
            segments=segments,
            source_language=language,
        )
    finally:
        if _get_env_bool("WHISPER_RELEASE_MODEL_AFTER_TRANSCRIBE", True):
            try:
                del batch_model
            except UnboundLocalError:
                pass
            try:
                del model
            except UnboundLocalError:
                pass
            _get_whisper_model.cache_clear()
            gc.collect()
            print("[transcript] Whisper model cache released")
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)

def _download_audio(url: str) -> tuple[str, str]:
    temp_dir = tempfile.mkdtemp(prefix="video_content_")
    outtmpl = str(Path(temp_dir) / "%(id)s.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "outtmpl": outtmpl,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    requested_downloads = info.get("requested_downloads") or []
    for item in requested_downloads:
        filepath = item.get("filepath")
        if filepath and Path(filepath).exists():
            return filepath, temp_dir

    filename = info.get("_filename")
    if filename and Path(filename).exists():
        return filename, temp_dir

    files = [path for path in Path(temp_dir).iterdir() if path.is_file()]
    if files:
        return str(files[0]), temp_dir

    raise RuntimeError("Audio download failed")

def _get_whisper_device_config() -> tuple[str, str]:
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"

def _get_env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

def _get_env_float(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

def _get_env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _unload_ollama_model() -> None:
    host = str(os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")).rstrip("/")
    model = str(os.getenv("OLLAMA_MODEL", "gemma3:12b")).strip()
    if not model:
        return

    body = json.dumps(
        {
            "model": model,
            "keep_alive": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{host}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15):
            pass
        print(f"[transcript] unloaded Ollama model before Whisper: {model}")
    except Exception as exc:
        print(
            f"[transcript] unable to unload Ollama before Whisper: "
            f"{type(exc).__name__}: {exc}"
        )


@lru_cache(maxsize=1)
def _get_whisper_model() -> WhisperModel:
    model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
    device, compute_type = _get_whisper_device_config()
    download_root = MODEL_DIR / "whisper"
    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=str(download_root),
    )
