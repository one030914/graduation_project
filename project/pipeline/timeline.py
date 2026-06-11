from __future__ import annotations
from collections import defaultdict

from configs.schema import TimelineResult, TimelineHotspot, TimelinePoint
from pipeline.collect import collect_comments

LOW_VALUE_TIMELINE_COMMENTS = {
    "這裡",
    "這段",
    "這邊",
    "笑死",
    "哈哈",
    "哈哈哈",
    "+1",
    "讚",
}

def _clean_representative_comments(
    comments: list[str],
    *,
    limit: int = 3,
    min_len: int = 4,
) -> list[str]:
    results = []
    seen = set()

    for text in comments:
        text = _one_line(text, limit=180)

        if not text:
            continue

        if text.lower() in LOW_VALUE_TIMELINE_COMMENTS:
            continue

        if len(text) < min_len:
            continue

        if text in seen:
            continue

        seen.add(text)
        results.append(text)

        if len(results) >= limit:
            break

    return results

def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0
    
def _one_line(text: str, limit: int = 160) -> str:
    text = "" if text is None else str(text)
    text = (
        text.replace("\r\n", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
    )
    text = " ".join(text.split())

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"

def _build_series(
    buckets: dict[int, list[str]],
    *,
    bucket_size: int,
) -> list[TimelinePoint]:
    if not buckets:
        return []

    max_second = max(buckets.keys())
    total_mentions = sum(len(items) for items in buckets.values())
    denominator = max(1, total_mentions)

    series = []

    for sec in range(0, max_second + bucket_size, bucket_size):
        count = len(buckets.get(sec, []))

        series.append(
            TimelinePoint(
                time_label=seconds_to_label(sec),
                seconds=sec,
                count=count,
                ratio=count / denominator,
            )
        )

    return series

def _series_to_chart_data(series: list[TimelinePoint]) -> list[dict]:
    return [
        {
            "time_label": point.time_label,
            "seconds": point.seconds,
            "count": point.count,
            "ratio": point.ratio,
        }
        for point in series
    ]

def _build_hotspots(
    buckets: dict[int, list[str]],
    *,
    limit: int = 10,
) -> list[TimelineHotspot]:
    hotspots = []

    for sec, bucket_comments in buckets.items():
        clean_comments = _clean_representative_comments(
            bucket_comments,
            limit=3,
        )

        hotspots.append(
            TimelineHotspot(
                time_label=seconds_to_label(sec),
                seconds=sec,
                count=len(bucket_comments),
                representative_comments=clean_comments,
            )
        )

    hotspots.sort(key=lambda x: x.count, reverse=True)

    return hotspots[:limit]

def _get_timeline_status(
    *,
    timestamp_comment_count: int,
    total_comments: int,
    peak_count: int,
) -> tuple[str, str | None]:
    if timestamp_comment_count <= 0:
        return (
            "insufficient_data",
            "此影片留言較少提及具體時間點，無法形成穩定時間軸熱點。",
        )

    ratio = timestamp_comment_count / max(1, total_comments)

    if timestamp_comment_count < 3:
        return (
            "insufficient_data",
            "時間戳留言數過少，時間軸結果僅供參考。",
        )

    if ratio < 0.005 and timestamp_comment_count < 10:
        return (
            "insufficient_data",
            "時間戳留言比例偏低，無法形成穩定時間軸曲線。",
        )

    if peak_count <= 1:
        return (
            "insufficient_data",
            "時間戳分布過於分散，尚未形成明顯熱點。",
        )

    return "ok", None

def seconds_to_label(seconds: int) -> str:
    seconds = int(seconds)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"

    return f"{m}:{s:02d}"

def bucket_seconds(seconds: int, bucket_size: int = 30) -> int:
    return int(seconds // bucket_size) * bucket_size

# =========================================
# Main entry point
# =========================================

def build_timeline(
    url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
    bucket_size: int = 30,
) -> TimelineResult:
    comments = collect_comments(
        url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
        order="relevance",
        duplicate=True,
    )
    
    return build_timeline_from_dataset(
        comments,
        bucket_size=bucket_size,
    )

def build_timeline_from_dataset(
    comments,
    bucket_size: int = 30,
) -> TimelineResult:
    if comments.error:
        return TimelineResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            bucket_size=bucket_size,
            status="error",
            message=comments.error,
        )

    df = comments.df.copy()

    if df.empty:
        return TimelineResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_comments=0,
            bucket_size=bucket_size,
            status="insufficient_data",
            message="沒有可分析的留言資料。",
        )

    buckets = defaultdict(list)
    timestamp_comment_ids = set()
    total_timestamp_mentions = 0

    for index, row in df.iterrows():
        timestamps = row.get("timestamps") or []

        if not timestamps:
            continue

        raw_text = str(row.get("raw_text") or row.get("clean_text") or "").strip()

        if not raw_text:
            continue

        comment_id = row.get("comment_id") or str(index)
        timestamp_comment_ids.add(comment_id)

        for ts in timestamps:
            seconds = _safe_int(ts.get("seconds", 0))

            if seconds < 0:
                continue

            b = bucket_seconds(seconds, bucket_size=bucket_size)
            buckets[b].append(raw_text)
            total_timestamp_mentions += 1

    timestamp_comment_count = len(timestamp_comment_ids)
    timestamp_comment_ratio = timestamp_comment_count / max(1, len(df))

    if not buckets:
        return TimelineResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_comments=len(df),
            timestamp_comment_count=0,
            timestamp_comment_ratio=0.0,
            total_timestamp_mentions=0,
            bucket_size=bucket_size,
            peak_count=0,
            status="insufficient_data",
            message="此影片留言較少提及具體時間點，無法形成穩定時間軸熱點。",
        )

    series = _build_series(
        buckets,
        bucket_size=bucket_size,
    )

    chart_data = _series_to_chart_data(series)

    hotspots = _build_hotspots(
        buckets,
        limit=10,
    )

    peak_count = max((point.count for point in series), default=0)

    status, message = _get_timeline_status(
        timestamp_comment_count=timestamp_comment_count,
        total_comments=len(df),
        peak_count=peak_count,
    )

    return TimelineResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        total_comments=len(df),
        timestamp_comment_count=timestamp_comment_count,
        timestamp_comment_ratio=timestamp_comment_ratio,
        total_timestamp_mentions=total_timestamp_mentions,
        bucket_size=bucket_size,
        peak_count=peak_count,
        series=series,
        chart_data=chart_data,
        hotspots=hotspots,
        status=status,
        message=message,
    )