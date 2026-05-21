from configs.schema import AnalysisResult, Stats
from scripts.timestamp import Timer

from .summary import _language_payload


def _fallback_keywords_zh(tokens_zh: list[list[str]], topk: int) -> list[str]:
    flat = [w for toks in tokens_zh for w in (toks or [])]
    seen = set()
    keywords = []

    for word in flat:
        word = str(word).strip()
        if word and word not in seen:
            seen.add(word)
            keywords.append(word)
        if len(keywords) >= topk:
            break

    return keywords


def build_keyword(
    video_url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
    keyword_topk: int = 10,
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

    try:
        from model.process.keyword.zh import extract_keywords_zh

        keywords_zh = extract_keywords_zh(comments_zh, tokens_zh, topk=keyword_topk)
    except Exception:
        keywords_zh = _fallback_keywords_zh(tokens_zh, keyword_topk)

    timer.mark("extract keywords zh")

    try:
        from model.process.keyword.en import extract_keywords_en

        keywords_en = extract_keywords_en(comments_en, topk=keyword_topk)
    except Exception:
        keywords_en = []

    timer.mark("extract keywords en")

    return AnalysisResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        stats=Stats(n_comments=len(df)),
        lang_ratio=lang_ratio,
        comments_zh=comments_zh,
        comments_en=comments_en,
        tokens_zh=tokens_zh,
        keywords_zh=keywords_zh[:keyword_topk],
        keywords_en=keywords_en[:keyword_topk],
    )
