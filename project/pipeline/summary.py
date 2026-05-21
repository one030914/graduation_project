from configs.schema import AnalysisResult, LangRatio, Stats
from scripts.timestamp import Timer

from .collect import collect_comments


def _language_payload(video_url: str, *, pages: int, page_size: int, min_likes: int):
    comments = collect_comments(
        url=video_url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
    )

    if comments.error:
        return comments, None, LangRatio()

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
    return comments, payload, LangRatio(zh=zh, en=en, other=other)


def build_summary(
    video_url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
    summary_topk: int = 5,
) -> AnalysisResult:
    timer = Timer()
    comments, payload, lang_ratio = _language_payload(
        video_url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
    )

    if comments.error:
        return AnalysisResult(error=comments.error)

    timer.mark("api fetch")

    df = payload["df"]
    max_n = 600
    comments_zh = payload["comments_zh"][:max_n]
    comments_en = payload["comments_en"][:max_n]
    tokens_zh = payload["tokens_zh"][:max_n]

    timer.mark("split language")

    summary_zh = comments_zh[:summary_topk]
    summary_en = comments_en[:summary_topk]

    try:
        from model.process.summary.zh import summarize_zh

        summary_zh = summarize_zh(comments_zh, topk=summary_topk)
    except Exception as e:
        print("Error: summarize zh", e)

    timer.mark("summarize zh")

    try:
        from model.process.summary.en import summarize_en

        summary_en = summarize_en(comments_en, topk=summary_topk)
    except Exception as e:
        print("Error: summarize en", e)

    timer.mark("summarize en")

    return AnalysisResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        stats=Stats(n_comments=len(df)),
        lang_ratio=lang_ratio,
        comments_zh=comments_zh,
        comments_en=comments_en,
        tokens_zh=tokens_zh,
        summary_zh=summary_zh[:summary_topk],
        summary_en=summary_en[:summary_topk],
    )
