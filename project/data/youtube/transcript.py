from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
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

PREFERRED_CAPTION_LANGUAGES = (
    "zh-TW",
    "zh-Hant",
    "zh-HK",
    "zh-CN",
    "zh-Hans",
    "zh",
    "en-US",
    "en-GB",
    "en",
)

@dataclass(slots=True)
class TranscriptSegment:
    text: str
    start: float = 0.0
    duration: float = 0.0

@dataclass(slots=True)
class TranscriptPayload:
    language: str
    source: str
    segments: List[TranscriptSegment]

def fetch_video_transcript(url: str, *, video_id: str) -> TranscriptPayload:
    caption_error: Optional[Exception] = None

    try:
        return _fetch_caption_transcript(video_id)
    except Exception as exc:
        caption_error = exc

    try:
        return _transcribe_audio(url)
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

    transcript = _pick_preferred_transcript(transcript_list)
    fetched = transcript.fetch(preserve_formatting=False)

    language = getattr(transcript, "language_code", "") or getattr(fetched, "language_code", "")
    return TranscriptPayload(
        language=str(language or "unknown"),
        source="caption",
        segments=_to_segments(fetched),
    )

def _pick_preferred_transcript(transcript_list):
    last_error: Optional[Exception] = None
    try:
        return transcript_list.find_manually_created_transcript(PREFERRED_CAPTION_LANGUAGES)
    except Exception as exc:
        last_error = exc

    manual_candidates = [
        transcript
        for transcript in transcript_list
        if not bool(getattr(transcript, "is_generated", False))
    ]
    if manual_candidates:
        manual_candidates.sort(key=_manual_caption_rank)
        return manual_candidates[0]

    if last_error is not None:
        raise RuntimeError("No manually created captions available") from last_error
    raise RuntimeError("No manually created captions available")


def _manual_caption_rank(transcript) -> tuple[int, str]:
    language_code = str(getattr(transcript, "language_code", "") or "")
    try:
        language_rank = PREFERRED_CAPTION_LANGUAGES.index(language_code)
    except ValueError:
        language_rank = len(PREFERRED_CAPTION_LANGUAGES)
    return language_rank, language_code

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
    audio_path, temp_dir = _download_audio(url)
    try:
        model = _get_whisper_model()
        batch_model = BatchedInferencePipeline(model=model)
        segments_iter, info = batch_model.transcribe(
            audio_path,
            batch_size=32,
            vad_filter=True,
            beam_size=1,
            best_of=1,
            without_timestamps=True,
            condition_on_previous_text=False,
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
        if not segments:
            raise RuntimeError("Whisper produced no transcript segments")
        language = str(getattr(info, "language", "") or "unknown")
        return TranscriptPayload(language=language, source="whisper", segments=segments)
    finally:
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
