from configs.schema import SummaryResult, LangRatio
from scripts.timestamp import Timer

from .collect import collect_comments

def _get_summary_language(summary_zh: list[str], summary_en: list[str]) -> str:
    if summary_zh and summary_en:
        return "mixed"
    if summary_zh:
        return "zh"
    if summary_en:
        return "en"
    return "unknown"

def _build_summary_points(
    summary_zh: list[str],
    summary_en: list[str],
    *,
    limit: int = 6,
) -> list[str]:
    points = []

    for item in summary_zh:
        item = str(item or "").strip()
        if item:
            points.append(item)

    for item in summary_en:
        item = str(item or "").strip()
        if item:
            points.append(item)

    return points[:limit]

def _get_summary_status(
    *,
    analyzed_comments: int,
    summary_points: list[str],
) -> tuple[str, str | None]:
    if analyzed_comments <= 0:
        return "error", "No comments for summary analysis."

    if analyzed_comments < 10:
        return "insufficient_data", "可分析留言數過少，摘要僅供參考。"

    if not summary_points:
        return "insufficient_data", "未產生有效摘要。"

    return "ok", None

def _language_payload_from_dataset(comments):
    df = comments.df.copy()
    lang_counts = df["language"].value_counts(dropna=False).to_dict()
    total = max(1, len(df))
    zh = float(lang_counts.get("zh", 0) / total)
    en = float(lang_counts.get("en", 0) / total)
    other = max(0.0, 1.0 - zh - en)

    payload = {
        "df": df,
        "comments_zh": df[df["language"] == "zh"]["clean_text"].tolist(),
        "comments_en": df[df["language"] == "en"]["clean_text"].tolist(),
        "tokens_zh": df[df["language"] == "zh"]["tokens"].tolist(),
    }
    return payload, LangRatio(zh=zh, en=en, other=other)

def build_summary(
    video_url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
    summary_topk: int = 5,
) -> SummaryResult:
    comments = collect_comments(
        url=video_url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
    )
    return build_summary_from_dataset(
        comments,
        summary_topk=summary_topk,
    )

def build_summary_from_dataset(
    comments,
    *,
    summary_topk: int = 5,
) -> SummaryResult:
    timer = Timer()

    if comments.error:
        return SummaryResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            status="error",
            message=comments.error,
            error=comments.error,
        )

    timer.mark("api fetch")

    payload, lang_ratio = _language_payload_from_dataset(comments)
    df = payload["df"]

    max_n = 600
    comments_zh = payload["comments_zh"][:max_n]
    comments_en = payload["comments_en"][:max_n]
    tokens_zh = payload["tokens_zh"][:max_n]

    analyzed_comments = len(comments_zh) + len(comments_en)

    timer.mark("split language")

    summary_zh = comments_zh[:summary_topk]
    summary_en = comments_en[:summary_topk]

    try:
        from model.process.summary.zh import summarize_zh

        summary_zh = summarize_zh(
            comments_zh,
            topk=summary_topk,
        )
    except Exception as e:
        print("Error: summarize zh", e)

    timer.mark("summarize zh")

    try:
        from model.process.summary.en import summarize_en

        summary_en = summarize_en(
            comments_en,
            topk=summary_topk,
        )
    except Exception as e:
        print("Error: summarize en", e)

    timer.mark("summarize en")

    summary_zh = summary_zh[:summary_topk]
    summary_en = summary_en[:summary_topk]

    summary_points = _build_summary_points(
        summary_zh,
        summary_en,
        limit=summary_topk * 2,
    )

    status, message = _get_summary_status(
        analyzed_comments=analyzed_comments,
        summary_points=summary_points,
    )

    return SummaryResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        total_comments=len(df),
        analyzed_comments=analyzed_comments,
        language=_get_summary_language(summary_zh, summary_en),
        lang_ratio=lang_ratio,
        status=status,
        message=message,
        summary_zh=summary_zh,
        summary_en=summary_en,
        summary_points=summary_points,
        comments_zh=comments_zh,
        comments_en=comments_en,
        tokens_zh=tokens_zh,
    )
