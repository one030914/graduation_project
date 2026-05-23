from __future__ import annotations
from agents.criticism_agent import CriticismAgent
from pipeline.collect import collect_comments
from configs.schema import CommentCriticismResult

def analyze_comment_criticism(
    video_url: str,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
) -> CommentCriticismResult:
    comments = collect_comments(
        url=video_url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
        order="relevance",
    )

    return analyze_comment_criticism_from_dataset(comments)


def analyze_comment_criticism_from_dataset(comments) -> CommentCriticismResult:
    if comments.error:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error=comments.error,
        )

    df = comments.df.copy()

    if len(df) < 5:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error="Not enough comments to analyze criticism.",
        )

    comment_texts = (
        df["clean_text"]
        .dropna()
        .astype(str)
        .map(str.strip)
        .loc[lambda s: s != ""]
        .tolist()
    )

    if len(comment_texts) < 5:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error="Not enough usable comment text for criticism analysis.",
        )

    try:
        data = CriticismAgent().analyze(
            title=comments.title,
            comments=comment_texts,
            max_comments=180,
        )

        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            main_criticisms=data.get("main_criticisms", []) or [],
            discontent_reasons=data.get("discontent_reasons", []) or [],
            suggestions=data.get("suggestions", []) or [],
        )

    except Exception as exc:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error=f"CriticismAgent analysis failed: {type(exc).__name__}: {exc}",
        )