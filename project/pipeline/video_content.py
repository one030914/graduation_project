from __future__ import annotations

import math
import os
import re
import time
from typing import Any, List, Sequence

from agents.video_content_agent import VideoContentAgent
from configs.schema import TranscriptPayload, TranscriptSegment, VideoChapterSegment, VideoContentResult
from data.preprocess.cleaner import detect_language
from data.youtube.api import API
from data.youtube.transcript import fetch_video_transcript

CHAPTER_TOPK = 8
CHAPTER_KEYWORD_TOPK = 5
MAX_CHAPTER_KEYWORD_LENGTH = 18
MAX_TRANSCRIPT_SEGMENTS = 2400
DEFAULT_TRANSCRIPT_CHUNK_CHAR_LIMIT = 8_000

CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[._'-][A-Za-z0-9]+)*")


class _VideoContentAnalysis:
    def __init__(
        self,
        *,
        summary_text: str,
        final_conclusion: str,
        recommended_audience: str,
        action_suggestions: list[str],
        chapter_timeline: list[VideoChapterSegment],
    ):
        self.summary_text = summary_text
        self.final_conclusion = final_conclusion
        self.recommended_audience = recommended_audience
        self.action_suggestions = action_suggestions
        self.chapter_timeline = chapter_timeline


def build_video_content(url: str) -> VideoContentResult:
    started_at = time.perf_counter()
    api = API()
    video_id = api.extract_video_id(url)
    if not video_id:
        return VideoContentResult(url=url, error="Invalid YouTube URL / video_id not found.")

    info = api.get_video_info(video_id)
    print(f"[video_content] video metadata: {time.perf_counter() - started_at:.2f}s")
    title = (info or {}).get("title") or video_id
    video_duration_seconds = _coerce_duration_seconds((info or {}).get("duration_seconds"))

    try:
        transcript_started_at = time.perf_counter()
        transcript = fetch_video_transcript(url, video_id=video_id)
        print(
            f"[video_content] transcript source={transcript.source} "
            f"segments={len(transcript.segments)} "
            f"elapsed={time.perf_counter() - transcript_started_at:.2f}s"
        )
    except Exception as exc:
        return VideoContentResult(title=title, url=url, error=str(exc))

    return build_video_content_from_transcript(
        transcript,
        title=title,
        url=url,
        video_duration_seconds=video_duration_seconds,
    )


def build_video_content_from_transcript(
    transcript: TranscriptPayload,
    *,
    title: str = "",
    url: str = "",
    video_duration_seconds: int | None = None,
) -> VideoContentResult:
    transcript_word_count = _count_transcript_words(transcript)
    segments = _prepare_transcript_segments(transcript)
    resolved_video_duration_seconds = _resolve_video_duration_seconds(
        segments,
        video_duration_seconds=video_duration_seconds,
    )
    if not segments:
        return VideoContentResult(
            title=title,
            url=url,
            transcript_word_count=transcript_word_count,
            transcript_source=transcript.source,
            transcript_source_language=transcript.source_language or transcript.language,
            transcript_translated=transcript.translated,
            transcript_translation_provider=transcript.translation_provider,
            error="No usable transcript text found.",
        )

    language = _resolve_main_language(transcript, segments)

    try:
        llm_started_at = time.perf_counter()
        analysis = _analyze_transcript_with_llm(
            title=title,
            segments=segments,
            language=language,
            video_duration_seconds=resolved_video_duration_seconds,
        )
        print(f"[video_content] LLM analysis: {time.perf_counter() - llm_started_at:.2f}s")
    except Exception as exc:
        return VideoContentResult(
            title=title,
            url=url,
            language=language,
            transcript_word_count=transcript_word_count,
            transcript_source=transcript.source,
            transcript_source_language=transcript.source_language or transcript.language,
            transcript_translated=transcript.translated,
            transcript_translation_provider=transcript.translation_provider,
            error=f"VideoContentAgent analysis failed: {exc}",
        )

    resolved_language = "zh"
    summary_text = _ensure_terminal_punctuation(analysis.summary_text, language=resolved_language)
    chapter_timeline = _normalize_chapter_timeline(
        analysis.chapter_timeline,
        video_duration_seconds=resolved_video_duration_seconds,
    )

    result = VideoContentResult(
        title=title,
        url=url,
        language=resolved_language,
        summary_text=summary_text,
        final_conclusion=_ensure_terminal_punctuation(analysis.final_conclusion, language=resolved_language),
        recommended_audience=_ensure_terminal_punctuation(analysis.recommended_audience, language=resolved_language),
        action_suggestions=_dedup_short_items(analysis.action_suggestions, limit=5),
        transcript_word_count=transcript_word_count,
        chapter_timeline=chapter_timeline,
        transcript_source=transcript.source,
        transcript_source_language=transcript.source_language or transcript.language,
        transcript_translated=transcript.translated,
        transcript_translation_provider=transcript.translation_provider,
    )

    if summary_text:
        result.summary_zh = [summary_text]

    return result


def _agent_data_to_video_analysis(
    data: dict[str, Any],
    *,
    segments: Sequence[TranscriptSegment] | None = None,
) -> _VideoContentAnalysis:
    summary_text = _normalize_whitespace(data.get("summary_text") or "")
    if not summary_text:
        legacy_summary = data.get("summary") or []
        if isinstance(legacy_summary, list):
            summary_text = _normalize_whitespace(
                " ".join(str(item).strip() for item in legacy_summary if str(item).strip())
            )

    return _VideoContentAnalysis(
        summary_text=summary_text,
        final_conclusion=_normalize_whitespace(data.get("final_conclusion") or ""),
        recommended_audience=_normalize_whitespace(data.get("recommended_audience") or ""),
        action_suggestions=_coerce_string_list(data.get("action_suggestions") or []),
        chapter_timeline=_parse_chapter_timeline(
            data.get("chapter_timeline") or [],
            segments=segments,
        ),
    )


def _prepare_transcript_segments(transcript: TranscriptPayload) -> List[TranscriptSegment]:
    output: List[TranscriptSegment] = []
    for segment in transcript.segments:
        text = _normalize_whitespace(segment.text)
        if len(text) < 2:
            continue
        output.append(
            TranscriptSegment(
                text=text,
                start=max(0.0, float(segment.start or 0.0)),
                duration=max(0.0, float(segment.duration or 0.0)),
            )
        )
        if len(output) >= MAX_TRANSCRIPT_SEGMENTS:
            break
    return output


def _resolve_main_language(transcript: TranscriptPayload, segments: Sequence[TranscriptSegment]) -> str:
    raw_language = str(transcript.language or "").lower()
    if raw_language.startswith("zh"):
        return "zh"
    if raw_language.startswith("en"):
        return "en"

    sample = " ".join(segment.text for segment in segments[:30]).strip()
    detected = detect_language(sample[:4000]) if sample else "unknown"
    return _normalize_language(detected, fallback="en")


def _analyze_transcript_with_llm(
    *,
    title: str,
    segments: Sequence[TranscriptSegment],
    language: str,
    video_duration_seconds: int | None = None,
) -> _VideoContentAnalysis:
    chunks = _chunk_transcript(_format_transcript_lines(segments))
    agent = VideoContentAgent()
    print(
        f"[video_content] prepared {len(segments)} transcript segments "
        f"as {len(chunks)} LLM chunk(s)"
    )

    if not chunks:
        return _VideoContentAnalysis(
            summary_text="",
            final_conclusion="",
            recommended_audience="",
            action_suggestions=[],
            chapter_timeline=[],
        )

    if len(chunks) == 1:
        data = agent.analyze_full_transcript(
            title=title,
            transcript_text=chunks[0],
            language=language,
            video_duration_seconds=video_duration_seconds,
        )
        return _agent_data_to_video_analysis(
            data,
            segments=segments,
        )

    chunk_results: list[dict] = []
    total_chunks = len(chunks)

    for index, chunk_text in enumerate(chunks, start=1):
        chunk_started_at = time.perf_counter()
        try:
            data = agent.analyze_chunk(
                title=title,
                chunk_text=chunk_text,
                language=language,
                chunk_index=index,
                total_chunks=total_chunks,
                video_duration_seconds=video_duration_seconds,
            )
            chunk_results.append(data)
        except Exception as exc:
            print(
                f"[video_content] LLM chunk {index}/{total_chunks} skipped: "
                f"{type(exc).__name__}: {exc}"
            )
        print(
            f"[video_content] LLM chunk {index}/{total_chunks}: "
            f"{time.perf_counter() - chunk_started_at:.2f}s"
        )

    if not chunk_results:
        raise RuntimeError("All transcript chunk analyses failed.")

    synthesis_started_at = time.perf_counter()
    merged = agent.synthesize_chunks(
        title=title,
        language=language,
        chunk_results=chunk_results,
        video_duration_seconds=video_duration_seconds,
    )
    print(
        f"[video_content] LLM synthesis: "
        f"{time.perf_counter() - synthesis_started_at:.2f}s"
    )

    return _agent_data_to_video_analysis(
        merged,
        segments=segments,
    )


def _format_transcript_lines(segments: Sequence[TranscriptSegment]) -> List[str]:
    lines: List[str] = []
    for segment in segments:
        start_seconds = max(0, math.floor(segment.start or 0))
        end_seconds = max(
            start_seconds + 1,
            math.ceil((segment.start or 0) + (segment.duration or 0)),
        )
        lines.append(
            f"[{_format_timestamp(start_seconds)} - {_format_timestamp(end_seconds)}] "
            f"({start_seconds}s - {end_seconds}s) {segment.text}"
        )
    return lines


def _chunk_transcript(lines: Sequence[str]) -> List[str]:
    if not lines:
        return []

    char_limit = _transcript_chunk_char_limit()

    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = 0

    for line in lines:
        for part in _split_long_text(line, char_limit):
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


def _transcript_chunk_char_limit() -> int:
    configured = str(os.getenv("VIDEO_TRANSCRIPT_CHUNK_CHARS", "")).strip()
    if configured:
        try:
            return max(2_000, int(configured))
        except ValueError:
            pass

    model_name = str(os.getenv("OLLAMA_MODEL", "")).lower()
    if "llama3.2:3b" in model_name:
        return 6_000
    if "gemma4:12b" in model_name:
        return 12_000
    return DEFAULT_TRANSCRIPT_CHUNK_CHAR_LIMIT


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


def _count_transcript_words(transcript: TranscriptPayload) -> int:
    text = " ".join(_normalize_whitespace(segment.text) for segment in transcript.segments if segment.text)
    if not text:
        return 0

    return len(CJK_CHAR_RE.findall(text)) + len(WORD_RE.findall(text))


def _resolve_video_duration_seconds(
    segments: Sequence[TranscriptSegment],
    *,
    video_duration_seconds: int | None,
) -> int | None:
    provided = _coerce_duration_seconds(video_duration_seconds)
    if provided is not None:
        return provided

    end_seconds = [
        int((segment.start or 0) + (segment.duration or 0))
        for segment in segments
        if (segment.start or 0) + (segment.duration or 0) > 0
    ]
    if not end_seconds:
        return None
    return max(end_seconds)


def _parse_chapter_timeline(
    items: Any,
    *,
    segments: Sequence[TranscriptSegment] | None = None,
) -> list[VideoChapterSegment]:
    if not isinstance(items, list):
        return []

    valid_starts, valid_ends = _source_timestamp_boundaries(segments)
    chapters: list[VideoChapterSegment] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        start_seconds = _coerce_seconds(item.get("start_seconds"))
        end_seconds = _coerce_seconds(item.get("end_seconds"))
        title = _normalize_whitespace(item.get("title") or "")
        summary = _normalize_whitespace(item.get("summary") or "")
        keywords = _normalize_chapter_keywords(item.get("keywords") or [])
        importance = _normalize_importance(item.get("importance"))
        if start_seconds is None or end_seconds is None:
            continue
        if valid_starts and start_seconds not in valid_starts:
            continue
        if valid_ends and end_seconds not in valid_ends:
            continue
        if end_seconds <= start_seconds:
            continue
        if not title or not summary:
            continue

        chapters.append(
            VideoChapterSegment(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                title=title,
                summary=summary,
                keywords=keywords,
                importance=importance,
            )
        )

    return _normalize_chapter_timeline(chapters)


def _source_timestamp_boundaries(
    segments: Sequence[TranscriptSegment] | None,
) -> tuple[set[int], set[int]]:
    if not segments:
        return set(), set()

    starts: set[int] = set()
    ends: set[int] = set()
    for segment in segments:
        start_seconds = max(0, math.floor(segment.start or 0))
        end_seconds = max(
            start_seconds + 1,
            math.ceil((segment.start or 0) + (segment.duration or 0)),
        )
        starts.add(start_seconds)
        ends.add(end_seconds)
    return starts, ends


def _normalize_chapter_timeline(
    chapters: Sequence[VideoChapterSegment],
    *,
    video_duration_seconds: int | None = None,
) -> list[VideoChapterSegment]:
    duration = _coerce_duration_seconds(video_duration_seconds)
    normalized: list[VideoChapterSegment] = []

    for chapter in chapters:
        if not chapter.title.strip() or not chapter.summary.strip():
            continue

        start_seconds = int(chapter.start_seconds)
        end_seconds = int(chapter.end_seconds)

        if duration is not None:
            if start_seconds >= duration:
                continue
            end_seconds = min(end_seconds, duration)

        if end_seconds <= start_seconds:
            continue

        normalized.append(
            VideoChapterSegment(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                title=chapter.title,
                summary=chapter.summary,
                keywords=chapter.keywords,
                importance=chapter.importance,
            )
        )

    normalized.sort(key=lambda chapter: (chapter.start_seconds, chapter.end_seconds))
    return normalized[:CHAPTER_TOPK]


def _normalize_chapter_keywords(items: Any) -> list[str]:
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []

    output: list[str] = []
    seen = set()
    for item in items:
        value = _normalize_keyword_text(item)
        if not value:
            continue
        if len(value) > MAX_CHAPTER_KEYWORD_LENGTH:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= CHAPTER_KEYWORD_TOPK:
            break
    return output


def _normalize_importance(value: Any) -> str:
    normalized = _normalize_whitespace(value).lower()
    mapping = {
        "high": "high",
        "高度": "high",
        "高": "high",
        "medium": "medium",
        "mid": "medium",
        "中度": "medium",
        "中": "medium",
        "low": "low",
        "低度": "low",
        "低": "low",
    }
    return mapping.get(normalized, "medium")


def _coerce_string_list(items: Any) -> list[str]:
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return []
    return [_normalize_whitespace(item) for item in items if _normalize_whitespace(item)]


def _dedup_short_items(items: Sequence[str], *, limit: int) -> list[str]:
    output: list[str] = []
    seen = set()
    for item in items:
        value = _normalize_whitespace(item)
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if len(output) >= limit:
            break
    return output


def _normalize_keyword_text(value: Any) -> str:
    normalized = _normalize_whitespace(value)
    normalized = re.sub(r"^[,，、;；:：\-\s]+|[,，、;；:：\-\s]+$", "", normalized)
    return normalized


def _coerce_seconds(value: Any) -> int | None:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _coerce_duration_seconds(value: Any) -> int | None:
    seconds = _coerce_seconds(value)
    if seconds is None or seconds <= 0:
        return None
    return seconds


def _format_timestamp(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


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


def _normalize_whitespace(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _ensure_terminal_punctuation(text: str, *, language: str) -> str:
    value = _normalize_whitespace(text)
    if not value:
        return ""

    if re.search(r"[。！？.!?…](?:[\"'”’」』）\)\]]+)?$", value):
        return value

    suffix_match = re.search(r"([\"'”’」』）\)\]]+)$", value)
    punct = "。" if language == "zh" else "."
    if suffix_match:
        suffix = suffix_match.group(1)
        core = value[: -len(suffix)].rstrip()
        if not core:
            return value
        return f"{core}{punct}{suffix}"

    return f"{value}{punct}"
