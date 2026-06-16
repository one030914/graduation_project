from __future__ import annotations
from agents.criticism_agent import CriticismAgent
from pipeline.collect import collect_comments
from configs.schema import CommentCriticismResult

def _clean_items(items, *, limit: int = 5) -> list[str]:
    results = []
    seen = set()

    for item in items or []:
        text = str(item or "").strip()
        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)
        results.append(text)

        if len(results) >= limit:
            break

    return results

def _get_criticism_status(
    *,
    analyzed_comments: int,
    main_criticisms: list[str],
    discontent_reasons: list[str],
    suggestions: list[str],
) -> tuple[str, str | None]:
    if analyzed_comments <= 0:
        return "error", "No comments for criticism analysis."

    if analyzed_comments < 5:
        return "insufficient_data", "可分析留言數不足，無法形成穩定批評趨勢。"

    if not main_criticisms and not discontent_reasons and not suggestions:
        return "insufficient_data", "未偵測到明確批評、抱怨或改進建議。"

    return "ok", None

def _build_severity_level(
    *,
    criticism_count: int,
    reason_count: int,
    suggestion_count: int,
) -> str:
    # 簡單規則即可，不要過度設計
    if criticism_count >= 4 or reason_count >= 4:
        return "high"

    if criticism_count >= 2 or reason_count >= 2 or suggestion_count >= 3:
        return "medium"

    return "low"

def _build_criticism_chart_data(
    *,
    criticism_count: int,
    reason_count: int,
    suggestion_count: int,
) -> list[dict]:
    total = max(1, criticism_count + reason_count + suggestion_count)

    return [
        {
            "key": "main_criticisms",
            "label": "主要批評",
            "count": criticism_count,
            "value": criticism_count / total,
        },
        {
            "key": "discontent_reasons",
            "label": "不滿原因",
            "count": reason_count,
            "value": reason_count / total,
        },
        {
            "key": "suggestions",
            "label": "改進建議",
            "count": suggestion_count,
            "value": suggestion_count / total,
        },
    ]

def _build_action_items(
    *,
    suggestions: list[str],
    discontent_reasons: list[str],
    limit: int = 5,
) -> list[str]:
    """
    將觀眾建議轉成創作者可執行的任務，避免和 suggestions 原文重複。
    """
    items = []
    seen = set()

    suggestion_patterns = [
        ("提升", "規劃一輪品質檢查與優化，優先處理：{text}"),
        ("優化", "安排功能與體驗優化，聚焦在：{text}"),
        ("增加", "評估新增需求的可行性與優先級：{text}"),
        ("提供", "補充更清楚的說明或設定選項：{text}"),
        ("希望", "將觀眾需求整理成待辦項目並排入後續規劃：{text}"),
        ("建議", "把觀眾建議轉成可驗收的改善項目：{text}"),
    ]

    def add_action(text: str) -> None:
        text = str(text or "").strip(" 。")
        if not text:
            return

        key = text.casefold()
        if key in seen:
            return

        seen.add(key)
        items.append(text)

    for suggestion in suggestions:
        text = str(suggestion or "").strip()
        if not text:
            continue

        action = ""
        for marker, template in suggestion_patterns:
            if marker in text:
                action = template.format(text=text)
                break

        add_action(action or f"把觀眾建議拆成具體改版任務：{text}")

    if len(items) < limit:
        for reason in discontent_reasons:
            text = str(reason or "").strip()
            if text:
                add_action(f"針對不滿原因設計補充說明或修正方案：{text}")

            if len(items) >= limit:
                break

    return items[:limit]

def analyze_comment_criticism(
    video_url: str,
    pages: int = 15,
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
            total_comments=len(df),
            analyzed_comments=0,
            status="insufficient_data",
            message="留言數不足，無法形成穩定批評趨勢。",
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
            total_comments=len(df),
            analyzed_comments=len(comment_texts),
            status="insufficient_data",
            message="可分析留言文字不足，無法形成穩定批評趨勢。",
        )

    try:
        data = CriticismAgent().analyze(
            title=comments.title,
            comments=comment_texts,
            max_comments=80,
        )
        analyzed_comments = int(data.pop("_analyzed_comment_count", 0))

        main_criticisms = _clean_items(
            data.get("main_criticisms", []) or [],
            limit=5,
        )

        discontent_reasons = _clean_items(
            data.get("discontent_reasons", []) or [],
            limit=5,
        )

        suggestions = _clean_items(
            data.get("suggestions", []) or [],
            limit=5,
        )

        criticism_count = len(main_criticisms)
        reason_count = len(discontent_reasons)
        suggestion_count = len(suggestions)

        status, message = _get_criticism_status(
            analyzed_comments=analyzed_comments,
            main_criticisms=main_criticisms,
            discontent_reasons=discontent_reasons,
            suggestions=suggestions,
        )

        severity_level = _build_severity_level(
            criticism_count=criticism_count,
            reason_count=reason_count,
            suggestion_count=suggestion_count,
        )

        chart_data = _build_criticism_chart_data(
            criticism_count=criticism_count,
            reason_count=reason_count,
            suggestion_count=suggestion_count,
        )

        action_items = _build_action_items(
            suggestions=suggestions,
            discontent_reasons=discontent_reasons,
            limit=5,
        )

        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,

            total_comments=len(df),
            analyzed_comments=analyzed_comments,

            status=status,
            message=message,

            main_criticisms=main_criticisms,
            discontent_reasons=discontent_reasons,
            suggestions=suggestions,

            criticism_count=criticism_count,
            reason_count=reason_count,
            suggestion_count=suggestion_count,

            severity_level=severity_level,
            chart_data=chart_data,
            action_items=action_items,
        )

    except Exception as exc:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            total_comments=len(df),
            analyzed_comments=len(comment_texts) if "comment_texts" in locals() else 0,
            status="error",
            message=f"CriticismAgent analysis failed: {type(exc).__name__}: {exc}",
            error=f"CriticismAgent analysis failed: {type(exc).__name__}: {exc}",
        )
