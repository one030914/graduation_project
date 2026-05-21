from __future__ import annotations

from typing import List

from .collect import collect_comments
from configs.schema import TopCommentsResult, TopComment, Order, SortBy

def get_top_comments(
    url: str,
    *,
    n: int = 10,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 1,
    order: Order = "relevance",
    sort_by: SortBy = "likes",
) -> TopCommentsResult:
    comments = collect_comments(
        url=url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
        order=order,
    )
    return get_top_comments_from_dataset(
        comments,
        n=n,
        order=order,
        sort_by=sort_by,
    )

def get_top_comments_from_dataset(
    comments,
    *,
    n: int = 10,
    order: Order = "relevance",
    sort_by: SortBy = "likes",
) -> TopCommentsResult:
    if comments.error:
        return TopCommentsResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            order=order,
            sort_by=sort_by,
            error=comments.error,
        )

    df = comments.df.copy()
    if df.empty:
        return TopCommentsResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            order=order,
            sort_by=sort_by,
            error="No valid comments after filtering",
        )

    sort_column = {
        "replies": "reply_count",
        "time": "published_at",
    }.get(sort_by, "like_count")

    if sort_column in df.columns:
        df = df.sort_values(sort_column, ascending=False, na_position="last")

    n = max(1, min(int(n), 10))
    items: List[TopComment] = []
    for row in df.head(n).itertuples(index=False):
        text = str(getattr(row, "clean_text", "")).strip()
        if not text:
            text = str(getattr(row, "raw_text", "")).strip()
        if not text:
            continue

        items.append(
            TopComment(
                text=text,
                like_count=int(getattr(row, "like_count", 0) or 0),
                reply_count=int(getattr(row, "reply_count", 0) or 0),
                published_at=getattr(row, "published_at", None),
                author=getattr(row, "author", None),
                comment_id=getattr(row, "comment_id", None),
            )
        )

    if not items:
        return TopCommentsResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_fetched=len(df),
            order=order,
            sort_by=sort_by,
            error="No valid comments after filtering",
        )

    return TopCommentsResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        top=items,
        total_fetched=len(df),
        order=order,
        sort_by=sort_by,
    )
