from __future__ import annotations

from configs.schema import IntentResult, IntentComment
from pipeline.collect import collect_comments
from agents.intent_agent import IntentAgent

ACTION_BUCKET_KEYS = [
    "questions",
    "corrections",
    "advice",
    "wishlist",
    "resources",
]

VALID_LLM_INTENTS = {
    "question",
    "correction",
    "advice",
    "wishlist",
    "resource",
    "ignore",
}

LLM_INTENT_TO_BUCKET = {
    "question": "questions",
    "correction": "corrections",
    "advice": "advice",
    "wishlist": "wishlist",
    "resource": "resources",
}

CANDIDATE_KEYWORDS = [
    # question
    "請問", "想問", "有人知道", "為什麼", "怎麼", "如何", "嗎", "？", "?",
    # correction
    "錯", "更正", "修正", "其實是", "不是", "應該是", "講錯",
    # advice
    "建議", "提醒", "記得", "不要", "應該", "必須", "最好", "小心", "注意",
    # wishlist
    "希望", "想看", "下一集", "可以拍", "能不能", "可不可以", "敲碗", "再拍", "再做",
    # resource
    "來源", "資料來源", "連結", "網址", "官方", "證據", "參考", "原文",
]

# ========================================
# Basics
# ========================================

def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0

def _text_has_candidate_signal(text: str) -> bool:
    text = str(text or "")
    lower = text.lower()

    if "http://" in lower or "https://" in lower:
        return True

    return any(keyword.lower() in lower for keyword in CANDIDATE_KEYWORDS)

def _priority_score(item: IntentComment) -> int:
    text_len = len(str(item.text or ""))
    text_bonus = min(text_len // 20, 10)

    return item.like_count + item.reply_count * 3 + text_bonus

def _chunk_items(items: list, batch_size: int = 25) -> list[list]:
    return [
        items[i:i + batch_size]
        for i in range(0, len(items), batch_size)
    ]
    
def _dict_to_intent_comment(data: dict, intent: str) -> IntentComment:
    return IntentComment(
        text=str(data.get("text", "")),
        intent=intent,
        like_count=_safe_int(data.get("like_count", 0)),
        reply_count=_safe_int(data.get("reply_count", 0)),
        comment_id=data.get("comment_id"),
        author=data.get("author"),
        reason=str(data.get("reason", "")),
        urls=data.get("urls", []) or [],
        timestamps=data.get("timestamps", []) or [],
    )
    
# ========================================
# Rule-based Classifier
# ========================================

def _build_candidate_items(df, *, max_items: int = 150) -> list[IntentComment]:
    candidates: list[IntentComment] = []

    for _, row in df.iterrows():
        text = str(row.get("raw_text") or row.get("clean_text") or "").strip()

        if not text:
            continue

        urls = row.get("urls") or []
        timestamps = row.get("timestamps") or []

        like_count = _safe_int(row.get("like_count", 0))
        reply_count = _safe_int(row.get("reply_count", 0))

        has_signal = _text_has_candidate_signal(text)
        is_high_engagement = like_count >= 10 or reply_count >= 2
        has_url = bool(urls)

        if not (has_signal or is_high_engagement or has_url):
            continue

        item = IntentComment(
            text=text,
            intent="candidate",
            like_count=like_count,
            reply_count=reply_count,
            comment_id=row.get("comment_id"),
            author=row.get("author"),
            reason="candidate_extraction",
            urls=urls,
            timestamps=timestamps,
        )

        candidates.append(item)

    # 去重
    seen = set()
    unique: list[IntentComment] = []

    for item in candidates:
        key = item.comment_id or item.text

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    unique.sort(key=_priority_score, reverse=True)

    return unique[:max_items]

# ========================================
# Stats organize
# ========================================

def _build_action_chart_data(classified_actions: dict[str, list[dict]]) -> list[dict]:
    labels = {
        "questions": "問題",
        "corrections": "勘誤",
        "advice": "建議",
        "wishlist": "許願",
        "resources": "資源",
    }

    total = sum(len(items) for items in classified_actions.values())
    denominator = max(1, total)

    return [
        {
            "key": key,
            "label": label,
            "count": len(classified_actions.get(key, [])),
            "value": len(classified_actions.get(key, [])) / denominator,
        }
        for key, label in labels.items()
    ]


def _has_action_items(classified_actions: dict) -> bool:
    return any(
        isinstance(items, list) and len(items) > 0
        for items in classified_actions.values()
    )

# ========================================
# LLM-based Classifier
# ========================================

def _comment_to_llm_item(item: IntentComment, index: int) -> dict:
    return {
        "id": str(index),
        "text": item.text,
        "like_count": item.like_count,
        "reply_count": item.reply_count,
        "urls": item.urls,
        "timestamps": item.timestamps,
    }

def _normalize_llm_intent(value: str) -> str:
    value = str(value or "").strip().lower()

    aliases = {
        "questions": "question",
        "corrections": "correction",
        "suggestion": "advice",
        "suggestions": "advice",
        "advices": "advice",
        "resources": "resource",
        "ignore_item": "ignore",
        "ignored": "ignore",
        "other": "ignore",
        "support": "ignore",
        "praise": "ignore",
        "meme": "ignore",
        "complaint": "advice",
        "complaints": "advice",
    }

    value = aliases.get(value, value)

    if value not in VALID_LLM_INTENTS:
        return "ignore"

    return value

def _empty_classified_actions() -> dict[str, list[dict]]:
    return {
        "questions": [],
        "corrections": [],
        "advice": [],
        "wishlist": [],
        "resources": [],
    }


def _classify_candidates_with_llm(
    candidates: list[IntentComment],
    *,
    batch_size: int = 25,
) -> tuple[dict[str, list[dict]], int, int, int]:
    classified_actions = _empty_classified_actions()

    if not candidates:
        return classified_actions, 0, 0, 0

    agent = IntentAgent()
    batches = _chunk_items(candidates, batch_size=batch_size)

    classified_count = 0
    ignored_count = 0

    for batch in batches:
        id_to_comment = {
            str(i): item
            for i, item in enumerate(batch)
        }

        payload = [
            _comment_to_llm_item(item, i)
            for i, item in enumerate(batch)
        ]

        try:
            result = agent.classify_batch(payload)
            rows = result.get("items", [])

            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue

                item_id = str(row.get("id", ""))
                original = id_to_comment.get(item_id)

                if original is None:
                    continue

                final_intent = _normalize_llm_intent(row.get("intent", "ignore"))

                classified_count += 1

                if final_intent == "ignore":
                    ignored_count += 1
                    continue

                bucket_key = LLM_INTENT_TO_BUCKET.get(final_intent)

                if not bucket_key:
                    ignored_count += 1
                    continue

                classified_actions[bucket_key].append({
                    "text": original.text,
                    "final_intent": final_intent,
                    "reason": str(row.get("reason", "")).strip(),
                    "priority": str(row.get("priority", "medium")).strip(),
                    "like_count": original.like_count,
                    "reply_count": original.reply_count,
                    "comment_id": original.comment_id,
                    "author": original.author,
                    "urls": original.urls,
                    "timestamps": original.timestamps,
                })

        except Exception as exc:
            print(f"IntentAgent batch classification failed: {exc}")

    # 每類只保留高價值前 5 則
    for key, items in classified_actions.items():
        items.sort(
            key=lambda x: (
                x.get("priority") == "high",
                int(x.get("like_count", 0) or 0),
                int(x.get("reply_count", 0) or 0),
            ),
            reverse=True,
        )
        classified_actions[key] = items[:5]

    return classified_actions, classified_count, len(batches), ignored_count
    
# ========================================
# Main entrypoint
# ========================================

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
            status="error",
            message=comments.error,
            error=comments.error,
        )

    df = comments.df.copy()

    if df.empty:
        return IntentResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_comments=0,
            analyzed_comments=0,
            status="error",
            message="No comments found",
            error="No comments found",
        )

    candidates = _build_candidate_items(
        df,
        max_items=150,
    )

    classified_actions = _empty_classified_actions()
    llm_classified_count = 0
    llm_batch_count = 0
    llm_ignored_count = 0

    try:
        (
            classified_actions,
            llm_classified_count,
            llm_batch_count,
            llm_ignored_count,
        ) = _classify_candidates_with_llm(
            candidates,
            batch_size=25,
        )

    except Exception as exc:
        print(f"IntentAgent classification failed: {exc}")

    actionable_count = sum(len(items) for items in classified_actions.values())
    actionable_ratio = actionable_count / max(1, len(df))

    chart_data = _build_action_chart_data(classified_actions)

    if not _has_action_items(classified_actions):
        status = "insufficient_data"
        message = "未從候選留言中找到明確可行動訊號。"
    else:
        status = "ok"
        message = None

    return IntentResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,

        total_comments=len(df),
        analyzed_comments=len(candidates),

        status=status,
        message=message,

        actionable_count=actionable_count,
        actionable_ratio=actionable_ratio,

        chart_data=chart_data,

        high_value_actions=classified_actions,
        classified_actions=classified_actions,

        llm_classified_count=llm_classified_count,
        llm_batch_count=llm_batch_count,
        llm_ignored_count=llm_ignored_count,

        questions=[
            _dict_to_intent_comment(x, "question")
            for x in classified_actions.get("questions", [])
        ],
        corrections=[
            _dict_to_intent_comment(x, "correction")
            for x in classified_actions.get("corrections", [])
        ],
        advice=[
            _dict_to_intent_comment(x, "advice")
            for x in classified_actions.get("advice", [])
        ],
        wishlist=[
            _dict_to_intent_comment(x, "wishlist")
            for x in classified_actions.get("wishlist", [])
        ],
        resources=[
            _dict_to_intent_comment(x, "resource")
            for x in classified_actions.get("resources", [])
        ],
    )