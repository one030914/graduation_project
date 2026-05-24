from __future__ import annotations

import re
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
TRANSCRIPT_CHUNK_CHAR_LIMIT = 12_000
MAX_TRANSCRIPT_CHUNKS = 18

CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[._'-][A-Za-z0-9]+)*")


class _VideoContentAnalysis:
    def __init__(
        self,
        *,
        language: str,
        summary_text: str,
        final_conclusion: str,
        recommended_audience: str,
        action_suggestions: list[str],
        chapter_timeline: list[VideoChapterSegment],
    ):
        self.language = language
        self.summary_text = summary_text
        self.final_conclusion = final_conclusion
        self.recommended_audience = recommended_audience
        self.action_suggestions = action_suggestions
        self.chapter_timeline = chapter_timeline


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
    transcript_word_count = _count_transcript_words(transcript)
    segments = _prepare_transcript_segments(transcript)
    if not segments:
        return VideoContentResult(
            title=title,
            url=url,
            transcript_word_count=transcript_word_count,
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
            transcript_word_count=transcript_word_count,
            transcript_source=transcript.source,
            error=f"VideoContentAgent analysis failed: {exc}",
        )

    resolved_language = "zh"
    summary_text = _ensure_terminal_punctuation(analysis.summary_text, language=resolved_language)
    chapter_timeline = _normalize_chapter_timeline(analysis.chapter_timeline)

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
    )

    if summary_text:
        if resolved_language == "zh":
            result.summary_zh = [summary_text]
        else:
            result.summary_en = [summary_text]

    return result


def _agent_data_to_video_analysis(data: dict[str, Any], *, fallback_language: str) -> _VideoContentAnalysis:
    summary_text = _normalize_whitespace(data.get("summary_text") or "")
    if not summary_text:
        legacy_summary = data.get("summary") or []
        if isinstance(legacy_summary, list):
            summary_text = _normalize_whitespace(
                " ".join(str(item).strip() for item in legacy_summary if str(item).strip())
            )

    return _VideoContentAnalysis(
        language=_normalize_language(str(data.get("language") or fallback_language), fallback=fallback_language),
        summary_text=summary_text,
        final_conclusion=_normalize_whitespace(data.get("final_conclusion") or ""),
        recommended_audience=_normalize_whitespace(data.get("recommended_audience") or ""),
        action_suggestions=_coerce_string_list(data.get("action_suggestions") or []),
        chapter_timeline=_parse_chapter_timeline(data.get("chapter_timeline") or []),
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
    url: str,
    segments: Sequence[TranscriptSegment],
    language: str,
) -> _VideoContentAnalysis:
    chunks = _chunk_transcript(_format_transcript_lines(segments))
    agent = VideoContentAgent()

    if not chunks:
        return _VideoContentAnalysis(
            language=language,
            summary_text="",
            final_conclusion="",
            recommended_audience="",
            action_suggestions=[],
            chapter_timeline=[],
        )

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


def _format_transcript_lines(segments: Sequence[TranscriptSegment]) -> List[str]:
    lines: List[str] = []
    for segment in segments:
        start_seconds = max(0, int(segment.start or 0))
        end_seconds = max(start_seconds + 1, int((segment.start or 0) + (segment.duration or 0)))
        lines.append(f"[{_format_timestamp(start_seconds)} - {_format_timestamp(end_seconds)}] {segment.text}")
    return lines


def _chunk_transcript(lines: Sequence[str]) -> List[str]:
    if not lines:
        return []

    total_chars = sum(len(line) + 1 for line in lines)
    char_limit = max(
        TRANSCRIPT_CHUNK_CHAR_LIMIT,
        (total_chars // MAX_TRANSCRIPT_CHUNKS) + 1,
    )

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


def _parse_chapter_timeline(items: Any) -> list[VideoChapterSegment]:
    if not isinstance(items, list):
        return []

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


def _normalize_chapter_timeline(chapters: Sequence[VideoChapterSegment]) -> list[VideoChapterSegment]:
    normalized = [
        chapter
        for chapter in chapters
        if chapter.end_seconds > chapter.start_seconds and chapter.title.strip() and chapter.summary.strip()
    ]
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
