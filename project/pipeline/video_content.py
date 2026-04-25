from __future__ import annotations

import os
import re
import time
from functools import lru_cache
from typing import List, Sequence

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from data.preprocess.cleaner import detect_language
from data.youtube.api import API
from data.youtube.transcript import TranscriptPayload, fetch_video_transcript
from configs.schema import VideoContentResult, TranscriptChunkAnalysis, TranscriptVideoAnalysis

SUMMARY_TOPK = 5
KEYWORD_TOPK = 10
HIGHLIGHT_TOPK = 5
MAX_TRANSCRIPT_SEGMENTS = 2400
TRANSCRIPT_CHUNK_CHAR_LIMIT = 12_000
MAX_TRANSCRIPT_CHUNKS = 18
DEFAULT_GEMINI_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|[。！？]+\s*|\n+")

def build_video_content(url: str) -> VideoContentResult:
    api = API()
    video_id = api.extract_video_id(url)
    if not video_id:
        return VideoContentResult(url=url, error="Invalid YouTube URL / video_id not found.")

    info = api.get_video_info(video_id)
    title = (info or {}).get("title") or video_id

    try:
        transcript = fetch_video_transcript(url, video_id=video_id)
    except Exception as exc:
        return VideoContentResult(title=title, url=url, error=str(exc))

    segments = _prepare_transcript_segments(transcript)
    if not segments:
        return VideoContentResult(
            title=title,
            url=url,
            transcript_source=transcript.source,
            error="No usable transcript text found.",
        )

    language = _resolve_main_language(transcript, segments)

    try:
        analysis = _analyze_transcript_with_llm(
            title=title,
            url=url,
            segments=segments,
            language=language,
        )
    except Exception as exc:
        return VideoContentResult(
            title=title,
            url=url,
            language=language,
            transcript_source=transcript.source,
            error=f"Gemini analysis failed: {exc}",
        )

    resolved_language = _normalize_language(analysis.language, fallback=language)
    summary = _dedup(analysis.summary, SUMMARY_TOPK)
    keywords = _dedup(analysis.keywords, KEYWORD_TOPK, fold_case=False)
    normalized_highlights = [
        _ensure_terminal_punctuation(item, language=resolved_language) for item in analysis.highlights
    ]
    highlights = _dedup(normalized_highlights, HIGHLIGHT_TOPK, fold_case=False)

    result = VideoContentResult(
        title=title,
        url=url,
        language=resolved_language,
        highlights=highlights,
        transcript_source=transcript.source,
    )

    if resolved_language == "zh":
        result.summary_zh = summary
        result.keywords_zh = keywords
    else:
        result.summary_en = summary
        result.keywords_en = keywords

    return result

def _prepare_transcript_segments(transcript: TranscriptPayload) -> List[str]:
    output: List[str] = []
    for segment in transcript.segments:
        text = _normalize_whitespace(segment.text)
        if not text:
            continue
        parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
        for part in parts or [text]:
            normalized = _normalize_whitespace(part)
            if len(normalized) >= 2:
                output.append(normalized)
        if len(output) >= MAX_TRANSCRIPT_SEGMENTS:
            break
    return output

def _resolve_main_language(transcript: TranscriptPayload, segments: Sequence[str]) -> str:
    raw_language = str(transcript.language or "").lower()
    if raw_language.startswith("zh"):
        return "zh"
    if raw_language.startswith("en"):
        return "en"

    sample = " ".join(segments[:30]).strip()
    detected = detect_language(sample[:4000]) if sample else "unknown"
    return _normalize_language(detected, fallback="en")

def _analyze_transcript_with_llm(
    *,
    title: str,
    url: str,
    segments: Sequence[str],
    language: str,
) -> TranscriptVideoAnalysis:
    chunks = _chunk_transcript(segments)
    client = _get_gemini_client()

    if len(chunks) == 1:
        return _call_gemini_json(
            client=client,
            prompt=_build_full_transcript_prompt(
                title=title,
                url=url,
                transcript_text=chunks[0],
                language=language,
            ),
            schema=TranscriptVideoAnalysis,
        )

    chunk_results: List[TranscriptChunkAnalysis] = []
    total_chunks = len(chunks)
    for index, chunk_text in enumerate(chunks, start=1):
        chunk_results.append(
            _call_gemini_json(
                client=client,
                prompt=_build_chunk_prompt(
                    title=title,
                    chunk_text=chunk_text,
                    language=language,
                    chunk_index=index,
                    total_chunks=total_chunks,
                ),
                schema=TranscriptChunkAnalysis,
            )
        )

    return _call_gemini_json(
        client=client,
        prompt=_build_synthesis_prompt(
            title=title,
            url=url,
            language=language,
            chunk_results=chunk_results,
        ),
        schema=TranscriptVideoAnalysis,
    )

def _chunk_transcript(segments: Sequence[str]) -> List[str]:
    if not segments:
        return []

    total_chars = sum(len(segment) + 1 for segment in segments)
    char_limit = max(
        TRANSCRIPT_CHUNK_CHAR_LIMIT,
        (total_chars // MAX_TRANSCRIPT_CHUNKS) + 1,
    )

    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = 0

    for segment in segments:
        for part in _split_long_text(segment, char_limit):
            extra_len = len(part) + (1 if current_parts else 0)
            if current_parts and current_len + extra_len > char_limit:
                chunks.append("\n".join(current_parts))
                current_parts = [part]
                current_len = len(part)
                continue

            current_parts.append(part)
            current_len += extra_len

    if current_parts:
        chunks.append("\n".join(current_parts))

    return chunks

def _split_long_text(text: str, char_limit: int) -> List[str]:
    normalized = _normalize_whitespace(text)
    if len(normalized) <= char_limit:
        return [normalized]

    parts: List[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + char_limit, len(normalized))
        if end < len(normalized):
            split_at = normalized.rfind(" ", start, end)
            if split_at <= start:
                split_at = end
        else:
            split_at = end
        part = normalized[start:split_at].strip()
        if part:
            parts.append(part)
        start = split_at
    return parts or [normalized]

def _build_full_transcript_prompt(*, title: str, url: str, transcript_text: str, language: str) -> str:
    return (
        "You analyze YouTube video transcripts.\n"
        "Use only the transcript content provided below.\n"
        "The transcript may come from YouTube captions or Whisper speech recognition.\n"
        "Treat it as a noisy source: it may contain misheard words, missing words, repeated phrases, incorrect punctuation, awkward sentence boundaries, or caption segmentation issues.\n"
        "Your job includes term normalization: when wording is clearly a transcription error, replace it with the correct or most commonly used wording.\n"
        "Infer the likely meaning only when the surrounding transcript clearly supports it.\n"
        "Do not turn uncertain, garbled, or unsupported text into factual claims.\n"
        "Pay special attention to proper nouns such as people, channels, brands, products, places, works, and organizations.\n"
        "Preserve proper nouns in their original or most commonly used form when possible; do not translate names literally.\n"
        "For example, keep 'Mr. Beast' as 'Mr. Beast' instead of translating it as '野獸先生'.\n"
        "If a proper noun appears misrecognized by Whisper or captions, use the video title and surrounding context to choose the most likely name only when the evidence is clear.\n"
        "When multiple name variants appear, prefer the canonical terms provided below when context does not contradict them.\n"
        "If a term has an obvious typo, homophone error, or ASR artifact and the intended meaning is clear, output only the corrected/common form.\n"
        "Do not include both wrong and corrected variants in summary, keywords, or highlights.\n"
        "If the correct term is uncertain, use safer generic wording or omit that detail rather than guessing a specific name.\n"
        "Do not invent facts, topics, speaker intent, or quotes that are not supported by the transcript.\n"
        "Return JSON that matches the schema.\n"
        "Keep the summary concise, factual, and focused on high-confidence points.\n"
        "Keywords must be short noun phrases grounded in the transcript, preserving proper nouns accurately.\n"
        "Highlights must be representative excerpts from the transcript; you may lightly trim and normalize obvious transcription artifacts, but do not change the meaning.\n"
        "Each highlight must be a complete sentence and must end with proper terminal punctuation.\n"
        "Use natural wording in the requested output language instead of literal, noisy transcript phrasing.\n"
        f"Video title: {title}\n"
        f"Video URL: {url}\n"
        f"Preferred output language: {_language_instruction(language)}\n\n"
        "Transcript:\n"
        f"{transcript_text}"
    )

def _build_chunk_prompt(
    *,
    title: str,
    chunk_text: str,
    language: str,
    chunk_index: int,
    total_chunks: int,
) -> str:
    return (
        "You are analyzing one chunk of a YouTube video transcript.\n"
        "Use only this chunk.\n"
        "The transcript chunk may come from YouTube captions or Whisper speech recognition.\n"
        "Treat it as a noisy source: it may contain misheard words, missing words, repeated phrases, incorrect punctuation, awkward sentence boundaries, or caption segmentation issues.\n"
        "Your job includes term normalization: when wording is clearly a transcription error, replace it with the correct or most commonly used wording.\n"
        "Infer the likely meaning only when this chunk clearly supports it.\n"
        "Do not turn uncertain, garbled, or unsupported text into factual claims.\n"
        "Pay special attention to proper nouns such as people, channels, brands, products, places, works, and organizations.\n"
        "Preserve proper nouns in their original or most commonly used form when possible; do not translate names literally.\n"
        "For example, keep 'Mr. Beast' as 'Mr. Beast' instead of translating it as '野獸先生'.\n"
        "If a proper noun appears misrecognized by Whisper or captions, use the video title and chunk context to choose the most likely name only when the evidence is clear.\n"
        "When multiple name variants appear, prefer the canonical terms provided below when context does not contradict them.\n"
        "If a term has an obvious typo, homophone error, or ASR artifact and the intended meaning is clear, output only the corrected/common form.\n"
        "Do not include both wrong and corrected variants in summary, keywords, or highlights.\n"
        "If the correct term is uncertain, use safer generic wording or omit that detail rather than guessing a specific name.\n"
        "Do not invent facts, topics, speaker intent, or quotes that are not supported by this chunk.\n"
        "Return JSON that matches the schema.\n"
        "Provide up to 3 high-confidence summary points, up to 8 grounded keywords, and up to 3 representative excerpts.\n"
        "Highlights must come from the transcript chunk; you may lightly trim and normalize obvious transcription artifacts, but do not change the meaning.\n"
        "Each highlight must be a complete sentence and must end with proper terminal punctuation.\n"
        "Use natural wording in the requested output language instead of literal, noisy transcript phrasing.\n"
        f"Video title: {title}\n"
        f"Chunk: {chunk_index}/{total_chunks}\n"
        f"Preferred output language: {_language_instruction(language)}\n\n"
        "Transcript chunk:\n"
        f"{chunk_text}"
    )

def _build_synthesis_prompt(
    *,
    title: str,
    url: str,
    language: str,
    chunk_results: Sequence[TranscriptChunkAnalysis],
) -> str:
    lines: List[str] = []
    for index, chunk in enumerate(chunk_results, start=1):
        lines.append(f"Chunk {index} summary:")
        lines.extend(f"- {item}" for item in chunk.summary)
        lines.append(f"Chunk {index} keywords:")
        lines.extend(f"- {item}" for item in chunk.keywords)
        lines.append(f"Chunk {index} highlights:")
        lines.extend(f"- {item}" for item in chunk.highlights)

    merged = "\n".join(lines)
    return (
        "You are synthesizing structured notes from a full YouTube transcript.\n"
        "The notes below were extracted from every chunk of the transcript.\n"
        "The original transcript may have come from YouTube captions or Whisper speech recognition, so the chunk notes may reflect transcription noise or caption segmentation issues.\n"
        "Your job includes term normalization across chunks: when wording is clearly a transcription error, replace it with the correct or most commonly used wording.\n"
        "Only keep high-confidence points that are clearly supported by the chunk notes.\n"
        "Do not turn uncertain, garbled, or weakly supported chunk notes into factual claims.\n"
        "Preserve proper nouns such as people, channels, brands, products, places, works, and organizations in their original or most commonly used form when possible.\n"
        "Do not translate proper nouns literally; for example, keep 'Mr. Beast' as 'Mr. Beast' instead of translating it as '野獸先生'.\n"
        "If a proper noun appears inconsistent across chunks, choose the most likely form only when the title and chunk notes clearly support it; otherwise keep the safer wording or omit that detail.\n"
        "When multiple name variants appear, prefer the canonical terms provided below when context does not contradict them.\n"
        "If a term has an obvious typo, homophone error, or ASR artifact and the intended meaning is clear, output only the corrected/common form.\n"
        "Do not include both wrong and corrected variants in summary, keywords, or highlights.\n"
        "If the correct term is uncertain, prefer safer generic wording or omit that detail.\n"
        "Return JSON that matches the schema.\n"
        "Provide up to 5 summary points, up to 10 keywords, and up to 5 representative excerpts.\n"
        "Do not invent facts that are not supported by the chunk notes.\n"
        "Each highlight must be a complete sentence and must end with proper terminal punctuation.\n"
        "Use natural wording in the requested output language instead of literal, noisy transcript phrasing.\n"
        f"Video title: {title}\n"
        f"Video URL: {url}\n"
        f"Preferred output language: {_language_instruction(language)}\n\n"
        "Chunk notes:\n"
        f"{merged}"
    )

def _language_instruction(language: str) -> str:
    if language == "zh":
        return "Traditional Chinese"
    if language == "en":
        return "English"
    return "Follow the transcript's dominant language"

def _call_gemini_json(*, client: genai.Client, prompt: str, schema: type[BaseModel]) -> BaseModel:
    models = _get_gemini_models()
    max_rounds = max(1, _get_env_int("GEMINI_VIDEO_ANALYSIS_RETRIES", 3))
    last_error: Exception | None = None

    for round_index in range(max_rounds):
        for model in models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.2,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                return _parse_gemini_response(response=response, schema=schema)
            except Exception as exc:
                last_error = exc
                if not _is_retryable_gemini_error(exc):
                    raise

        if round_index < max_rounds - 1:
            time.sleep(min(8.0, 2.0 * (2**round_index)))

    raise RuntimeError(_format_gemini_error(last_error, models))

@lru_cache(maxsize=1)
def _get_gemini_client() -> genai.Client:
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)

def _get_gemini_models() -> List[str]:
    configured = (
        os.getenv("GEMINI_VIDEO_ANALYSIS_MODELS")
        or os.getenv("GEMINI_VIDEO_ANALYSIS_MODEL")
        or ""
    )
    if configured.strip():
        models = [item.strip() for item in configured.split(",") if item.strip()]
        if models:
            return models
    return list(DEFAULT_GEMINI_MODELS)

def _parse_gemini_response(*, response, schema: type[BaseModel]) -> BaseModel:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        if isinstance(parsed, schema):
            return parsed
        return schema.model_validate(parsed)

    text = str(getattr(response, "text", "") or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return schema.model_validate_json(text)

def _is_retryable_gemini_error(exc: Exception) -> bool:
    message = str(exc or "").upper()
    retryable_tokens = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
    )
    return any(token in message for token in retryable_tokens)

def _format_gemini_error(exc: Exception | None, models: Sequence[str]) -> str:
    if exc is None:
        return "Gemini analysis failed after retry attempts."
    message = str(exc).strip()
    if _is_retryable_gemini_error(exc):
        return (
            "Gemini service is temporarily unavailable after retry attempts. "
            f"Tried models: {', '.join(models)}. Last error: {message}"
        )
    return message

def _get_env_int(name: str, default: int) -> int:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default

def _normalize_language(value: str, *, fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    if normalized == "mixed":
        return "zh" if fallback == "zh" else "en"
    if fallback in {"zh", "en"}:
        return fallback
    return "en"

def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()

def _ensure_terminal_punctuation(text: str, *, language: str) -> str:
    value = _normalize_whitespace(text)
    if not value:
        return ""

    # Keep if sentence-ending punctuation already exists (optionally before a closing quote/bracket).
    if re.search(r"[。！？.!?…](?:[\"'”’」』）\)\]]+)?$", value):
        return value

    # If it ends with a closing quote/bracket, insert punctuation before the suffix.
    suffix_match = re.search(r"([\"'”’」』）\)\]]+)$", value)
    punct = "。" if language == "zh" else "."
    if suffix_match:
        suffix = suffix_match.group(1)
        core = value[: -len(suffix)].rstrip()
        if not core:
            return value
        return f"{core}{punct}{suffix}"

    return f"{value}{punct}"

def _dedup(items: Sequence[str], limit: int, *, fold_case: bool = True) -> List[str]:
    output: List[str] = []
    seen = set()
    for item in items:
        value = _normalize_whitespace(item)
        if not value:
            continue
        key = value.casefold() if fold_case else value
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= limit:
            break
    return output
