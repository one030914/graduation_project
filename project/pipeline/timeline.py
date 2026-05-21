from __future__ import annotations

from collections import defaultdict

from configs.schema import TimelineResult, TimelineHotspot
from pipeline.collect import collect_comments

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
            status="error",
            message=comments.error
        )

    df = comments.df.copy()

    buckets = defaultdict(list)

    for _, row in df.iterrows():
        timestamps = row.get("timestamps") or []
        if not timestamps:
            continue

        raw_text = str(row.get("raw_text") or "").strip()

        for ts in timestamps:
            seconds = int(ts.get("seconds", 0))
            b = bucket_seconds(seconds, bucket_size=bucket_size)
            buckets[b].append(raw_text)

    if not buckets:
        return TimelineResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_comments=len(df),
            timestamp_comment_count=0,
            status="insufficient_data",
            message="此影片留言較少提及具體時間點，無法形成穩定時間軸熱點。"
        )

    hotspots = []
    for sec, bucket_comments in buckets.items():
        hotspots.append(
            TimelineHotspot(
                time_label=seconds_to_label(sec),
                seconds=sec,
                count=len(bucket_comments),
                representative_comments=bucket_comments[:5],
            )
        )

    hotspots.sort(key=lambda x: x.count, reverse=True)

    timestamp_comment_count = sum(len(v) for v in buckets.values())

    return TimelineResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        total_comments=len(df),
        timestamp_comment_count=timestamp_comment_count,
        hotspots=hotspots[:10],
    )
