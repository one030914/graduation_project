from __future__ import annotations

from collections import Counter

from configs.schema import IntentResult, IntentComment
from pipeline.collect import collect_comments
from agents.intent_agent import IntentAgent

INTENT_RULES = {
    "question": [
        "請問", "為什麼", "怎麼", "如何", "嗎", "？", "?",
        "what", "why", "how", "can anyone", "does anyone"
    ],
    "correction": [
        "錯", "不是", "應該是", "更正", "修正", "其實是", "講錯",
        "wrong", "actually", "correction", "mistake"
    ],
    "wishlist": [
        "希望", "想看", "下一集", "可以拍", "能不能", "可不可以", "跪求",
        "please make", "next video", "can you make"
    ],
    "complaint": [
        "爛", "失望", "不好", "太貴", "有問題", "不準", "不公平", "看不懂",
        "bad", "disappointed", "too expensive", "not fair"
    ],
    "praise": [
        "讚", "好看", "厲害", "專業", "推", "喜歡", "感謝", "清楚",
        "great", "good", "awesome", "thanks", "love"
    ],
    "meme": [
        "笑死", "哈哈", "梗", "太好笑", "wwww", "XD", "lol", "lmao"
    ],
}

def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0

def classify_intent(text: str, urls: list[str] | None = None) -> tuple[str, str]:
    text = str(text or "").strip()
    lower = text.lower()
    urls = urls or []

    if urls:
        return "resource", "留言包含外部連結或參考資源"

    for intent, keywords in INTENT_RULES.items():
        for kw in keywords:
            if kw.lower() in lower:
                return intent, f"命中關鍵詞：{kw}"

    return "other", "未命中明確意圖規則"

def build_intent(
    url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 0,
) -> IntentResult:
    comments = collect_comments(
        url,
        pages=pages,
        page_size=page_size,
        min_likes=min_likes,
        order="relevance",
    )
    
    return build_intent_from_dataset(comments)
    
def build_intent_from_dataset(comments) -> IntentResult:
    if comments.error:
        return IntentResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error=comments.error,
        )

    df = comments.df.copy()

    buckets = {
        "question": [],
        "correction": [],
        "wishlist": [],
        "complaint": [],
        "resource": [],
        "praise": [],
        "meme": [],
        "other": [],
    }

    for _, row in df.iterrows():
        text = str(row.get("raw_text") or row.get("clean_text") or "").strip()
        urls = row.get("urls") or []
        timestamps = row.get("timestamps") or []

        intent, reason = classify_intent(text, urls)

        item = IntentComment(
            text=text,
            intent=intent,
            like_count=_safe_int(row.get("like_count", 0)),
            reply_count=_safe_int(row.get("reply_count", 0)),
            comment_id=row.get("comment_id"),
            author=row.get("author"),
            reason=reason,
            urls=urls,
            timestamps=timestamps,
        )

        buckets.setdefault(intent, []).append(item)

    # 高價值留言排序：讚數優先，其次回覆數
    for key in buckets:
        buckets[key].sort(
            key=lambda x: (x.like_count, x.reply_count),
            reverse=True
        )

    counts = {key: len(value) for key, value in buckets.items()}
    total = max(1, sum(counts.values()))
    ratios = {key: value / total for key, value in counts.items()}
    
    # ========================================
    # AI agent
    # ========================================
    
    agent_summary = []
    priority_questions = []
    priority_corrections = []
    content_ideas = []
    action_suggestions = []

    agent_payload = {
        "intent_counts": counts,
        "questions": [
            {
                "text": x.text,
                "like_count": x.like_count,
                "reply_count": x.reply_count,
            }
            for x in buckets["question"][:10]
        ],
        "corrections": [
            {
                "text": x.text,
                "like_count": x.like_count,
                "reply_count": x.reply_count,
            }
            for x in buckets["correction"][:10]
        ],
        "wishlist": [
            {
                "text": x.text,
                "like_count": x.like_count,
                "reply_count": x.reply_count,
            }
            for x in buckets["wishlist"][:10]
        ],
        "complaints": [
            {
                "text": x.text,
                "like_count": x.like_count,
                "reply_count": x.reply_count,
            }
            for x in buckets["complaint"][:10]
        ],
        "resources": [
            {
                "text": x.text,
                "urls": x.urls,
                "like_count": x.like_count,
            }
            for x in buckets["resource"][:10]
        ],
    }

    try:
        agent_result = IntentAgent().analyze(agent_payload)

        agent_summary = agent_result.get("summary", [])
        priority_questions = agent_result.get("priority_questions", [])
        priority_corrections = agent_result.get("priority_corrections", [])
        content_ideas = agent_result.get("content_ideas", [])
        action_suggestions = agent_result.get("action_suggestions", [])

    except Exception as e:
        print(f"IntentAgent failed, fallback to rule-based result: {e}")

    return IntentResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        total_comments=len(df),
        intent_counts=counts,
        intent_ratios=ratios,
        questions=buckets["question"][:10],
        corrections=buckets["correction"][:10],
        wishlist=buckets["wishlist"][:10],
        complaints=buckets["complaint"][:10],
        resources=buckets["resource"][:10],
        praise=buckets["praise"][:10],
        memes=buckets["meme"][:10],
        agent_summary=agent_summary,
        priority_questions=priority_questions,
        priority_corrections=priority_corrections,
        content_ideas=content_ideas,
        action_suggestions=action_suggestions,
    )