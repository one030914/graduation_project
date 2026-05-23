from __future__ import annotations

import os
import re
import time
from functools import lru_cache
from typing import List, Sequence

from agents.video_content_agent import VideoContentAgent
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

    return build_video_content_from_transcript(
        transcript,
        title=title,
        url=url,
    )

def build_video_content_from_transcript(
    transcript: TranscriptPayload,
    *,
    title: str = "",
    url: str = "",
) -> VideoContentResult:
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
            error=f"VideoContentAgent analysis failed: {exc}",
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

def _agent_data_to_video_analysis(data: dict, *, fallback_language: str) -> TranscriptVideoAnalysis:
    return TranscriptVideoAnalysis(
        language=_normalize_language(str(data.get("language") or fallback_language), fallback=fallback_language),
        summary=[str(x).strip() for x in data.get("summary", []) if str(x).strip()],
        keywords=[str(x).strip() for x in data.get("keywords", []) if str(x).strip()],
        highlights=[str(x).strip() for x in data.get("highlights", []) if str(x).strip()],
    )

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
    agent = VideoContentAgent()

    if not chunks:
        return TranscriptVideoAnalysis(language=language)

    if len(chunks) == 1:
        data = agent.analyze_full_transcript(
            title=title,
            url=url,
            transcript_text=chunks[0],
            language=language,
        )
        return _agent_data_to_video_analysis(
            data,
            fallback_language=language,
        )

    chunk_results: list[dict] = []
    total_chunks = len(chunks)

    for index, chunk_text in enumerate(chunks, start=1):
        data = agent.analyze_chunk(
            title=title,
            chunk_text=chunk_text,
            language=language,
            chunk_index=index,
            total_chunks=total_chunks,
        )
        chunk_results.append(data)

    merged = agent.synthesize_chunks(
        title=title,
        url=url,
        language=language,
        chunk_results=chunk_results,
    )

    return _agent_data_to_video_analysis(
        merged,
        fallback_language=language,
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
