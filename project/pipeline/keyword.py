from collections import Counter

from configs.schema import KeywordResult, KeywordItem
from scripts.timestamp import Timer

from .collect import collect_comments
from .summary import _language_payload_from_dataset

def _get_keyword_language(keywords_zh: list[str], keywords_en: list[str]) -> str:
    if keywords_zh and keywords_en:
        return "mixed"
    if keywords_zh:
        return "zh"
    if keywords_en:
        return "en"
    return "unknown"

def _normalize_keyword(word: str) -> str:
    return str(word or "").strip()

def _count_keywords_in_texts(
    keywords: list[str],
    texts: list[str],
) -> dict[str, int]:
    counts = {}

    normalized_texts = [str(text or "").lower() for text in texts]

    for keyword in keywords:
        keyword = _normalize_keyword(keyword)
        if not keyword:
            continue

        key_lower = keyword.lower()
        count = 0

        for text in normalized_texts:
            if key_lower in text:
                count += 1

        counts[keyword] = count

    return counts

def _fallback_keywords_zh(tokens_zh: list[list[str]], topk: int) -> list[str]:
    counter = Counter()

    for toks in tokens_zh:
        for word in toks or []:
            word = _normalize_keyword(word)
            if not word:
                continue
            if len(word) <= 1:
                continue
            counter[word] += 1

    return [word for word, _ in counter.most_common(topk)]

def _build_keyword_items(
    *,
    keywords_zh: list[str],
    keywords_en: list[str],
    comments_zh: list[str],
    comments_en: list[str],
) -> list[KeywordItem]:
    zh_counts = _count_keywords_in_texts(keywords_zh, comments_zh)
    en_counts = _count_keywords_in_texts(keywords_en, comments_en)

    items: list[KeywordItem] = []

    zh_total = max(1, len(comments_zh))
    en_total = max(1, len(comments_en))

    for kw in keywords_zh:
        kw = _normalize_keyword(kw)
        if not kw:
            continue

        count = zh_counts.get(kw, 0)
        items.append(
            KeywordItem(
                keyword=kw,
                count=count,
                ratio=count / zh_total,
                language="zh",
            )
        )

    for kw in keywords_en:
        kw = _normalize_keyword(kw)
        if not kw:
            continue

        count = en_counts.get(kw, 0)
        items.append(
            KeywordItem(
                keyword=kw,
                count=count,
                ratio=count / en_total,
                language="en",
            )
        )

    items.sort(key=lambda x: (x.count, x.ratio), reverse=True)

    return items

def _build_keyword_chart_data(items: list[KeywordItem], limit: int = 15) -> list[dict]:
    return [
        {
            "keyword": item.keyword,
            "label": item.keyword,
            "value": item.count,
            "count": item.count,
            "ratio": item.ratio,
            "language": item.language,
        }
        for item in items[:limit]
    ]
    
def _build_wordcloud_data(items: list[KeywordItem], limit: int = 50) -> list[dict]:
    return [
        {
            "text": item.keyword,
            "value": max(1, item.count),
            "language": item.language,
        }
        for item in items[:limit]
    ]
    
def _build_top_tags(items: list[KeywordItem], limit: int = 10) -> list[str]:
    tags = []
    seen = set()

    for item in items:
        keyword = _normalize_keyword(item.keyword)

        if not keyword:
            continue

        key = keyword.lower()
        if key in seen:
            continue

        seen.add(key)
        tags.append(keyword)

        if len(tags) >= limit:
            break

    return tags

def _get_keyword_status(
    *,
    analyzed_comments: int,
    items: list[KeywordItem],
) -> tuple[str, str | None]:
    if analyzed_comments <= 0:
        return "error", "No comments for keyword analysis."

    if analyzed_comments < 10:
        return "insufficient_data", "可分析留言數過少，關鍵詞僅供參考。"

    if not items:
        return "insufficient_data", "未抽取到有效關鍵詞。"

    return "ok", None

def build_keyword(
    video_url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
    keyword_topk: int = 10,
) -> KeywordResult:
    comments = collect_comments(
        url=video_url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
    )
    return build_keyword_from_dataset(
        comments,
        keyword_topk=keyword_topk,
    )

def build_keyword_from_dataset(
    comments,
    *,
    keyword_topk: int = 10,
) -> KeywordResult:
    timer = Timer()

    if comments.error:
        return KeywordResult(
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

    timer.mark("split language")

    try:
        from model.process.keyword.zh import extract_keywords_zh

        keywords_zh = extract_keywords_zh(
            comments_zh,
            tokens_zh,
            topk=keyword_topk,
        )
    except Exception as e:
        print("Error: extract keywords zh", e)
        keywords_zh = _fallback_keywords_zh(tokens_zh, keyword_topk)

    timer.mark("extract keywords zh")

    try:
        from model.process.keyword.en import extract_keywords_en

        keywords_en = extract_keywords_en(
            comments_en,
            topk=keyword_topk,
        )
    except Exception as e:
        print("Error: extract keywords en", e)
        keywords_en = []

    timer.mark("extract keywords en")

    keywords_zh = keywords_zh[:keyword_topk]
    keywords_en = keywords_en[:keyword_topk]

    items = _build_keyword_items(
        keywords_zh=keywords_zh,
        keywords_en=keywords_en,
        comments_zh=comments_zh,
        comments_en=comments_en,
    )

    keyword_counts = {
        item.keyword: item.count
        for item in items
    }

    keyword_ratios = {
        item.keyword: item.ratio
        for item in items
    }

    analyzed_comments = len(comments_zh) + len(comments_en)

    chart_data = _build_keyword_chart_data(items, limit=15)
    wordcloud_data = _build_wordcloud_data(items, limit=50)
    top_tags = _build_top_tags(items, limit=10)

    status, message = _get_keyword_status(
        analyzed_comments=analyzed_comments,
        items=items,
    )

    return KeywordResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        total_comments=len(df),
        analyzed_comments=analyzed_comments,
        language=_get_keyword_language(keywords_zh, keywords_en),
        status=status,
        message=message,
        keywords=items,
        keyword_counts=keyword_counts,
        keyword_ratios=keyword_ratios,
        chart_data=chart_data,
        wordcloud_data=wordcloud_data,
        top_tags=top_tags,
        keywords_zh=keywords_zh,
        keywords_en=keywords_en,
    )