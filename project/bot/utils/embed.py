import discord
from datetime import datetime
from configs.schema import (
    KeywordResult,
    SummaryResult,
    TopicsResult,
    EmotionResult,
    CommentCriticismResult,
    TimelineResult,
)

# -------------------------
# Helper Functions
# -------------------------

def _clip(text: str, limit: int = 1024) -> str:
    """防止文字超過 Discord 欄位限制"""
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."

def _fmt_list(lines, max_lines: int = 6) -> str:
    """格式化清單內容"""
    if not lines:
        return "（無）"
    lines = [str(x).strip() for x in lines if str(x).strip()]
    if not lines:
        return "（無）"
    lines = lines[:max_lines]
    return "\n".join(f"{i+1}. {s}" for i, s in enumerate(lines))

def _fmt_keywords(words, max_items: int = 12) -> str:
    """格式化關鍵字"""
    if not words:
        return "（無）"
    words = [str(w).strip() for w in words if str(w).strip()]
    if not words:
        return "（無）"
    words = words[:max_items]
    return " ".join(f"`{w}`" for w in words)

def discord_time(iso_time: str | None) -> str:
    """將 ISO 時間轉換為 Discord 的動態時間格式"""
    if not iso_time:
        return ""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        unix = int(dt.timestamp())
        return f"<t:{unix}:R>"
    except Exception:
        return ""
    
def _one_line(text: str, limit: int = 120) -> str:
    text = "" if text is None else str(text)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = " ".join(text.split())
    return _clip(text, limit)

def _safe_get(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)

# -------------------------
# Summary Embed
# -------------------------

def build_summary_embed(result: SummaryResult) -> discord.Embed:
    if result.error or result.status == "error":
        return discord.Embed(
            title="⚠️ 摘要分析失敗",
            description=_clip(result.error or result.message or "摘要分析發生未知錯誤。", 4096),
            color=0xED4245,
        )

    embed = discord.Embed(
        title="🧾 YouTube 留言摘要",
        description=(
            f"**影片：** [{_clip(result.title, 180)}]({result.url})\n"
            f"**分析狀態：** `{result.status}`\n"
            f"**分析留言數：** `{result.analyzed_comments}` / `{result.total_comments}` 則"
        ),
        color=0x5865F2 if result.status == "ok" else 0xFEE75C,
    )

    if result.status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(result.message or "可分析留言數偏少，摘要僅供參考。"),
            inline=False,
        )

    if result.summary_points:
        embed.add_field(
            name="📌 留言摘要",
            value=_clip(_fmt_list(result.summary_points, max_lines=6), 1024),
            inline=False,
        )
    else:
        if result.summary_zh:
            embed.add_field(
                name="📌 中文摘要",
                value=_clip(_fmt_list(result.summary_zh, max_lines=6), 1024),
                inline=False,
            )

        if result.summary_en:
            embed.add_field(
                name="📌 English Summary",
                value=_clip(_fmt_list(result.summary_en, max_lines=6), 1024),
                inline=False,
            )

    lr = result.lang_ratio
    lang_text = (
        f"🇹🇼 中文：{lr.zh:.1%}\n"
        f"🇺🇸 英文：{lr.en:.1%}\n"
        f"🌐 其他：{lr.other:.1%}"
    )

    embed.add_field(
        name="🌍 語言佔比",
        value=_clip(lang_text),
        inline=False,
    )

    embed.set_footer(
        text="Summary Analysis：根據留言內容抽取代表性摘要"
    )

    return embed

# -------------------------
# Keyword Embed
# -------------------------

def build_keyword_embed(result: KeywordResult) -> discord.Embed:
    if result.error or result.status == "error":
        return discord.Embed(
            title="⚠️ 關鍵詞分析失敗",
            description=_clip(result.error or result.message or "關鍵詞分析發生未知錯誤。", 4096),
            color=0xED4245,
        )

    embed = discord.Embed(
        title="🔑 YouTube 留言關鍵詞分析",
        description=(
            f"**影片：** [{_clip(result.title, 180)}]({result.url})\n"
            f"**分析狀態：** `{result.status}`\n"
            f"**分析留言數：** `{result.analyzed_comments}` / `{result.total_comments}` 則\n"
            f"**主要語言：** `{result.language}`"
        ),
        color=0x5865F2 if result.status == "ok" else 0xFEE75C,
    )

    if result.status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(result.message or "可分析留言數偏少，關鍵詞僅供參考。"),
            inline=False,
        )

    if result.top_tags:
        embed.add_field(
            name="🏷️ 熱門標籤",
            value=_clip(" ".join(f"`#{tag}`" for tag in result.top_tags[:10]), 1024),
            inline=False,
        )

    chart_data = getattr(result, "chart_data", []) or []
    if chart_data:
        lines = []
        for item in chart_data[:12]:
            keyword = item.get("keyword") or item.get("label") or ""
            count = int(item.get("count", 0) or 0)
            ratio = float(item.get("ratio", 0.0) or 0.0)

            if not keyword:
                continue

            lines.append(
                f"`{keyword}`：{count} 則（{_fmt_percent(ratio)}）"
            )

        if lines:
            embed.add_field(
                name="📊 熱門關鍵詞分布",
                value=_clip("\n".join(lines), 1024),
                inline=False,
            )

    if result.keywords_zh:
        embed.add_field(
            name="🇹🇼 中文關鍵詞",
            value=_clip(_fmt_keywords(result.keywords_zh, max_items=15), 1024),
            inline=False,
        )

    if result.keywords_en:
        embed.add_field(
            name="🇺🇸 English Keywords",
            value=_clip(_fmt_keywords(result.keywords_en, max_items=15), 1024),
            inline=False,
        )

    wordcloud_data = getattr(result, "wordcloud_data", []) or []
    if wordcloud_data:
        embed.add_field(
            name="☁️ 文字雲資料",
            value=(
                f"已產生 `{len(wordcloud_data)}` 個文字雲詞項，"
                "可供 Web 前端繪製文字雲。"
            ),
            inline=False,
        )

    embed.set_footer(
        text="Keyword Analysis：關鍵詞 count 代表出現於多少則留言中"
    )

    return embed

# -------------------------
# Topics Embed
# -------------------------

LANG_MAP = {
    "zh": "中文",
    "en": "英文",
    "unknown": "其他"
}

def _fmt_topic_keywords(words, max_items: int = 6) -> str:
    if not words:
        return "（無）"

    words = [str(w).strip() for w in words if str(w).strip()]
    if not words:
        return "（無）"

    return " ".join(f"`{w}`" for w in words[:max_items])

def _fmt_topic_representatives(comments, max_items: int = 2) -> str:
    if not comments:
        return "（無）"

    lines = []
    for comment in comments[:max_items]:
        text = _one_line(comment, 120)
        if text:
            lines.append(f"> {text}")

    return "\n".join(lines) if lines else "（無）"

def _topic_status_color(status: str) -> int:
    if status == "error":
        return 0xED4245
    if status == "insufficient_data":
        return 0xFEE75C
    return 0x5865F2

def build_topics_embed(result: TopicsResult) -> discord.Embed:
    status = getattr(result, "status", "ok")
    error = getattr(result, "error", None)
    message = getattr(result, "message", None)

    if status == "error" or error:
        return discord.Embed(
            title="⚠️ Topic 分析失敗",
            description=_clip(error or message or "主題分析發生未知錯誤。", 4096),
            color=0xED4245,
        )

    display_lang = LANG_MAP.get(result.language, result.language)

    embed = discord.Embed(
        title="💬 YouTube 留言主題分析",
        description=(
            f"🧾 影片標題：**[{_clip(result.title, 180)}]({result.url})**\n"
            f"🌐 主要語言：{display_lang}\n"
            f"📌 分析狀態：`{status}`"
        ),
        color=_topic_status_color(status),
    )

    if status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(message or "留言內容不足或過於分散，主題分布僅供參考。"),
            inline=False,
        )

    analyzed = getattr(result, "analyzed_comments", 0) or result.total_comments
    clustered = getattr(result, "clustered_comments", 0) or sum(t.size for t in result.topics)
    noise_count = getattr(result, "noise_count", 0)
    noise_ratio = getattr(result, "noise_ratio", 0.0)
    coverage_ratio = getattr(result, "coverage_ratio", 0.0)

    embed.add_field(
        name="📊 主題分析概況",
        value=(
            f"可分析留言：`{analyzed}` 則\n"
            f"成功分群：`{clustered}` 則（{_fmt_percent(coverage_ratio)}）\n"
            f"未歸入明確主題：`{noise_count}` 則（{_fmt_percent(noise_ratio)}）"
        ),
        inline=False,
    )

    top_keywords = getattr(result, "top_keywords", []) or []
    if top_keywords:
        embed.add_field(
            name="🏷️ 熱門關鍵詞",
            value=_clip(_fmt_topic_keywords(top_keywords, max_items=12), 1024),
            inline=False,
        )

    if not result.topics:
        embed.add_field(
            name="📌 主題結果",
            value="目前沒有形成穩定主題。",
            inline=False,
        )
        embed.set_footer(text=f"總留言數：{result.total_comments}")
        return embed

    for i, topic in enumerate(result.topics[:5], start=1):
        topic_name = (
            getattr(topic, "topic_name", "")
            or getattr(topic, "chart_label", "")
            or f"Topic {i}"
        )

        kw_text = _fmt_topic_keywords(topic.keywords, max_items=6)
        rep_text = _fmt_topic_representatives(topic.representative_comments, max_items=2)

        value = (
            f"**占比：** {_fmt_percent(topic.ratio)} ｜ **留言數：** `{topic.size}`\n"
            f"**關鍵詞：** {kw_text}\n"
            f"**代表留言：**\n{rep_text}"
        )

        embed.add_field(
            name=f"#{i} {topic_name}",
            value=_clip(value, 1024),
            inline=False,
        )

    embed.set_footer(
        text=(
            f"總留言數：{result.total_comments} ｜ "
            f"分析語言：{display_lang} ｜ "
            "主題占比以成功分群留言為基準"
        )
    )

    return embed

# -------------------------
# Emotion Embed
# -------------------------

from bot.utils.chart import build_emotion_radar_chart

EMOTION_ORDER = ["Joy", "Angry", "Sad", "Surprised", "Disgusted", "Neutral"]

EMOTION_DISPLAY_NAMES = {
    "Joy": "喜悅/稱讚",
    "Angry": "憤怒",
    "Sad": "悲傷",
    "Surprised": "驚訝",
    "Disgusted": "厭惡/反感",
    "Neutral": "中性",
}

def _fmt_percent(value, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except Exception:
        return "0.0%"

def _emotion_color(score: int) -> int:
    if score >= 80:
        return 0x57F287  # green
    if score >= 65:
        return 0x2ECC71
    if score >= 45:
        return 0xFEE75C  # yellow
    if score >= 30:
        return 0xE67E22  # orange
    return 0xED4245      # red

def _format_emotion_distribution(result: EmotionResult) -> str:
    stats = result.stats.emotions if result.stats else {}
    ratios = getattr(result, "emotion_ratios", None) or (
        result.stats.ratios if result.stats and hasattr(result.stats, "ratios") else {}
    )

    if not stats:
        return "（無）"

    lines = []
    for emo in EMOTION_ORDER:
        count = stats.get(emo, 0)
        ratio = ratios.get(emo, 0.0)
        display = EMOTION_DISPLAY_NAMES.get(emo, emo)
        lines.append(f"**{display}**：`{count}`（{_fmt_percent(ratio)}）")

    return "\n".join(lines)

def _format_radar_text(result: EmotionResult) -> str:
    radar_data = getattr(result, "radar_data", []) or []

    if not radar_data:
        return "（尚無雷達資料）"

    lines = []
    for item in radar_data[:6]:
        label = item.get("label", "未知")
        value = item.get("value", 0.0)
        lines.append(f"**{label}**：{_fmt_percent(value)}")

    return "\n".join(lines)

def _format_representative_comments(result: EmotionResult, limit_per_emotion: int = 1) -> str:
    reps = getattr(result, "representative_comments", {}) or {}

    if not reps:
        return "（尚無代表留言）"

    lines = []

    for emo in EMOTION_ORDER:
        comments = reps.get(emo, []) or []
        if not comments:
            continue

        display = EMOTION_DISPLAY_NAMES.get(emo, emo)

        for item in comments[:limit_per_emotion]:
            if isinstance(item, dict):
                text = item.get("text", "")
                like_count = item.get("like_count", 0)
                reply_count = item.get("reply_count", 0)
            else:
                text = getattr(item, "text", "")
                like_count = getattr(item, "like_count", 0)
                reply_count = getattr(item, "reply_count", 0)

            if not text:
                continue

            lines.append(
                f"**{display}**｜👍 `{like_count}` 💬 `{reply_count}`\n"
                f"> {_one_line(text, 120)}"
            )

    if not lines:
        return "（尚無代表留言）"

    return "\n\n".join(lines[:5])

def build_emotion_embed(result: EmotionResult) -> tuple[discord.Embed, discord.File | None]:
    status = getattr(result, "status", "ok")
    error = getattr(result, "error", None)
    message = getattr(result, "message", None)

    if status == "error" or error:
        return (
            discord.Embed(
                title="⚠️ Emotion 分析失敗",
                description=_clip(error or message or "情緒分析發生未知錯誤。", 4096),
                color=0xED4245,
            ),
            None,
        )

    score = int(getattr(result, "opinion_score", 50) or 50)
    opinion_label = getattr(result, "opinion_label", "中性 / 意見分歧")
    display_lang = LANG_MAP.get(result.language, result.language)

    embed = discord.Embed(
        title="🎭 YouTube 留言情緒分析",
        description=(
            f"🧾 影片標題：**[{_clip(result.title, 180)}]({result.url})**\n"
            f"🌐 分析語言：{display_lang}\n"
            f"📌 分析狀態：`{status}`"
        ),
        color=_emotion_color(score),
    )

    if status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(message or "可分析留言數偏少，情緒分布僅供參考。"),
            inline=False,
        )

    embed.add_field(
        name="🌡️ 輿情溫度",
        value=(
            f"**{opinion_label}** ｜ `{score}/100`\n"
            f"正向：{_fmt_percent(getattr(result, 'positive_ratio', 0.0))}｜"
            f"負面：{_fmt_percent(getattr(result, 'negative_ratio', 0.0))}｜"
            f"中性：{_fmt_percent(getattr(result, 'neutral_ratio', 0.0))}"
        ),
        inline=False,
    )

    dominant = getattr(result, "dominant_emotion", {}) or {}
    if dominant:
        embed.add_field(
            name="👑 主導情緒",
            value=(
                f"**{dominant.get('display_name', dominant.get('label', '未知'))}**\n"
                f"數量：`{dominant.get('count', 0)}` ｜ "
                f"占比：{_fmt_percent(dominant.get('ratio', 0.0))}"
            ),
            inline=False,
        )

    embed.add_field(
        name="📊 情緒分布",
        value=_clip(_format_emotion_distribution(result), 1024),
        inline=False,
    )

    embed.add_field(
        name="🕸️ 雷達圖文字版",
        value=_clip(_format_radar_text(result), 1024),
        inline=False,
    )

    reps_text = _format_representative_comments(result, limit_per_emotion=1)
    if reps_text != "（尚無代表留言）":
        embed.add_field(
            name="💬 各情緒代表留言",
            value=_clip(reps_text, 1024),
            inline=False,
        )

    analyzed = getattr(result, "analyzed_comments", 0) or (
        result.stats.total if result.stats else 0
    )
    skipped = getattr(result, "skipped_comments", 0) or max(0, result.total_comments - analyzed)

    embed.set_footer(
        text=(
            f"總留言數：{result.total_comments} ｜ "
            f"參與情緒分析：{analyzed} ｜ "
            f"略過：{skipped}"
            "\n情緒分類代表語氣，不等同於對影片立場"
        )
    )

    return embed, None

# -------------------------
# Criticism Embed
# -------------------------

def _criticism_status_color(status: str, severity_level: str = "low") -> int:
    if status == "error":
        return 0xED4245

    if status == "insufficient_data":
        return 0xFEE75C

    if severity_level == "high":
        return 0xED4245

    if severity_level == "medium":
        return 0xE67E22

    return 0x5865F2

def _severity_display(severity_level: str) -> str:
    mapping = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }
    return mapping.get(severity_level, severity_level or "未知")

def _format_criticism_chart_data(chart_data) -> str:
    if not chart_data:
        return "（無）"

    lines = []

    for item in chart_data:
        label = _safe_get(item, "label", "")
        count = int(_safe_get(item, "count", 0) or 0)
        value = float(_safe_get(item, "value", 0.0) or 0.0)

        if not label:
            continue

        lines.append(f"`{label}` {count}（{_fmt_percent(value)}）")

    return "｜".join(lines) if lines else "（無）"

def _fmt_bullets(items, limit: int = 5) -> str:
    if not items:
        return "（無）"

    lines = []
    for item in items[:limit]:
        text = _one_line(item, 160)
        if text:
            lines.append(f"• {text}")

    return "\n".join(lines) if lines else "（無）"

def build_criticism_embed(result: CommentCriticismResult) -> discord.Embed:
    status = getattr(result, "status", "ok")
    error = getattr(result, "error", None)
    message = getattr(result, "message", None)

    if status == "error" or error:
        return discord.Embed(
            title="⚠️ 留言批評分析失敗",
            description=_clip(error or message or "批評分析發生未知錯誤。", 4096),
            color=0xED4245,
        )

    title = getattr(result, "title", "") or "YouTube 影片"
    url = getattr(result, "url", "")

    total_comments = int(getattr(result, "total_comments", 0) or 0)
    analyzed_comments = int(getattr(result, "analyzed_comments", 0) or 0)

    severity_level = getattr(result, "severity_level", "low") or "low"

    criticism_count = int(getattr(result, "criticism_count", 0) or 0)
    reason_count = int(getattr(result, "reason_count", 0) or 0)
    suggestion_count = int(getattr(result, "suggestion_count", 0) or 0)

    main_criticisms = getattr(result, "main_criticisms", []) or []
    discontent_reasons = getattr(result, "discontent_reasons", []) or []
    suggestions = getattr(result, "suggestions", []) or []
    action_items = getattr(result, "action_items", []) or []
    chart_data = getattr(result, "chart_data", []) or []

    embed = discord.Embed(
        title="💬 留言批評與改善訊號分析",
        description=(
            f"**影片：** [{_clip(title, 180)}]({url})\n"
            f"**分析狀態：** `{status}`\n"
            f"**分析留言數：** `{analyzed_comments}` / `{total_comments}` 則"
        ),
        color=_criticism_status_color(status, severity_level),
    )

    if status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(
                message or "可分析留言不足，無法形成穩定批評趨勢。",
                1024,
            ),
            inline=False,
        )

    embed.add_field(
        name="🧭 批評訊號概況",
        value=(
            f"批評強度：**{_severity_display(severity_level)}**\n"
            f"主要批評：`{criticism_count}` 項｜"
            f"不滿原因：`{reason_count}` 項｜"
            f"改進建議：`{suggestion_count}` 項"
        ),
        inline=False,
    )

    if chart_data:
        embed.add_field(
            name="📊 批評類型分布",
            value=_clip(_format_criticism_chart_data(chart_data), 1024),
            inline=False,
        )

    if main_criticisms:
        embed.add_field(
            name="🤬 主要批評與抱怨痛點",
            value=_clip(_fmt_bullets(main_criticisms, limit=5), 1024),
            inline=False,
        )

    if discontent_reasons:
        embed.add_field(
            name="🔍 觀眾不滿原因",
            value=_clip(_fmt_bullets(discontent_reasons, limit=5), 1024),
            inline=False,
        )

    if suggestions:
        embed.add_field(
            name="💡 觀眾提出的改進建議",
            value=_clip(_fmt_bullets(suggestions, limit=5), 1024),
            inline=False,
        )

    if action_items:
        embed.add_field(
            name="🎬 可轉換為創作者行動",
            value=_clip(_fmt_bullets(action_items, limit=5), 1024),
            inline=False,
        )

    if not main_criticisms and not discontent_reasons and not suggestions:
        embed.add_field(
            name="📌 批評結果",
            value="目前沒有形成明確批評、抱怨或改進建議。",
            inline=False,
        )

    embed.set_footer(
        text=(
            "Criticism Analysis：整理留言中的批評、不滿原因與可改善方向；"
            "資料不足時不代表風向良好。"
        )
    )

    return embed

# -------------------------
# Timeline Embed
# -------------------------

def _timeline_status_color(status: str) -> int:
    if status == "error":
        return 0xED4245
    if status == "insufficient_data":
        return 0xFEE75C
    return 0x57F287

def _format_timeline_hotspot(hotspot, index: int) -> str:
    time_label = getattr(hotspot, "time_label", "未知時間")
    count = int(getattr(hotspot, "count", 0) or 0)

    return f"{index}. `{time_label}`｜被提及 `{count}` 次"

def _format_timeline_representatives(comments, limit: int = 3) -> str:
    if not comments:
        return "（無）"

    lines = []

    for comment in comments[:limit]:
        text = _one_line(comment, 140)
        if text:
            lines.append(f"> {text}")

    return "\n".join(lines) if lines else "（無）"

def _format_timeline_series_preview(series, limit: int = 8) -> str:
    """
    用文字方式預覽曲線高點。
    Discord 不畫圖，所以只顯示 count > 0 的前幾個時間點。
    """
    if not series:
        return "（無曲線資料）"

    active_points = [
        point for point in series
        if int(getattr(point, "count", 0) or 0) > 0
    ]

    if not active_points:
        return "（沒有明顯時間點提及）"

    active_points.sort(
        key=lambda x: int(getattr(x, "count", 0) or 0),
        reverse=True,
    )

    lines = []
    for point in active_points[:limit]:
        time_label = getattr(point, "time_label", "未知時間")
        count = int(getattr(point, "count", 0) or 0)
        ratio = float(getattr(point, "ratio", 0.0) or 0.0)

        lines.append(
            f"`{time_label}`：{count} 次（{_fmt_percent(ratio)}）"
        )

    return "\n".join(lines)

def build_timeline_embed(result: TimelineResult) -> discord.Embed:
    status = getattr(result, "status", "ok")
    message = getattr(result, "message", None)

    if status == "error":
        return discord.Embed(
            title="⚠️ 時間軸分析失敗",
            description=_clip(str(message or "分析過程發生未知錯誤。"), 4096),
            color=0xED4245,
        )

    title = getattr(result, "title", "") or "YouTube 影片"
    url = getattr(result, "url", "")

    total_comments = int(getattr(result, "total_comments", 0) or 0)
    timestamp_comment_count = int(
        getattr(result, "timestamp_comment_count", 0) or 0
    )
    timestamp_comment_ratio = float(
        getattr(result, "timestamp_comment_ratio", 0.0) or 0.0
    )

    total_timestamp_mentions = int(
        getattr(result, "total_timestamp_mentions", 0) or 0
    )
    bucket_size = int(getattr(result, "bucket_size", 30) or 30)
    peak_count = int(getattr(result, "peak_count", 0) or 0)

    hotspots = getattr(result, "hotspots", []) or []
    series = getattr(result, "series", []) or []

    embed = discord.Embed(
        title=(
            "📍 時間軸資料不足"
            if status == "insufficient_data"
            else "🔥 留言時間軸熱點分析"
        ),
        description=(
            f"**影片：** [{_clip(title, 180)}]({url})\n"
            f"**分析狀態：** `{status}`\n"
            f"**分析留言數：** `{total_comments}` 則"
        ),
        color=_timeline_status_color(status),
    )

    if status == "insufficient_data":
        embed.add_field(
            name="⚠️ 資料提醒",
            value=_clip(
                message
                or "此影片留言中較少出現時間戳，因此無法形成穩定的影片片段熱點。",
                1024,
            ),
            inline=False,
        )

    embed.add_field(
        name="📊 時間軸資料概況",
        value=(
            f"含時間戳留言：`{timestamp_comment_count}` 則"
            f"（{_fmt_percent(timestamp_comment_ratio)}）\n"
            f"時間戳總提及次數：`{total_timestamp_mentions}` 次\n"
            f"時間桶大小：`{bucket_size}` 秒\n"
            f"最高峰值：`{peak_count}` 次 / bucket"
        ),
        inline=False,
    )

    if series:
        embed.add_field(
            name="📈 曲線高點預覽",
            value=_clip(_format_timeline_series_preview(series, limit=8), 1024),
            inline=False,
        )

    if not hotspots:
        embed.add_field(
            name="📌 熱點結果",
            value="目前沒有形成明確時間軸熱點。",
            inline=False,
        )

        embed.add_field(
            name="建議查看",
            value=(
                "`/analyze` 查看綜合分析\n"
                "`/topics` 觀察熱門討論主題\n"
                "`/emotion` 判斷留言整體風向"
            ),
            inline=False,
        )

        embed.set_footer(
            text=(
                "Timeline Analysis：統計留言中被觀眾主動提及的影片時間點；"
                "資料不足時不強行產生熱點。"
            )
        )

        return embed

    top_hotspot = hotspots[0]
    top_time = getattr(top_hotspot, "time_label", "未知時間")
    top_count = int(getattr(top_hotspot, "count", 0) or 0)
    representative_comments = getattr(
        top_hotspot, "representative_comments", []
    ) or []

    top_value = f"**{top_time}** 附近｜被提及 `{top_count}` 次"

    if representative_comments:
        top_value += (
            "\n"
            + _format_timeline_representatives(
                representative_comments,
                limit=1,
            )
        )

    embed.add_field(
        name="🏆 Top 1 高能片段",
        value=_clip(top_value, 1024),
        inline=False,
    )

    if len(hotspots) > 1:
        other_lines = [
            _format_timeline_hotspot(hotspot, i)
            for i, hotspot in enumerate(hotspots[1:6], start=2)
        ]

        embed.add_field(
            name="📍 其他熱門片段",
            value=_clip("\n".join(other_lines), 1024),
            inline=False,
        )

    if representative_comments:
        embed.add_field(
            name=f"💬 `{top_time}` 代表留言",
            value=_clip(
                _format_timeline_representatives(
                    representative_comments,
                    limit=3,
                ),
                1024,
            ),
            inline=False,
        )

    embed.add_field(
        name="🧭 分析說明",
        value=(
            "此分析統計的是「留言中被觀眾主動提及的影片時間點」，"
            "不是 YouTube 官方觀看重播率。"
        ),
        inline=False,
    )

    embed.set_footer(
        text=(
            "Timeline Analysis：series / chart_data 可供 Web 前端繪製時間軸曲線。"
        )
    )

    return embed

# -------------------------
# Main Insight Embed
# -------------------------

def _as_bullets(items: list[str], limit: int = 5) -> str:
    if not items:
        return "暫無資料"

    lines = []

    for item in items[:limit]:
        text = _one_line(item, 160)
        if text:
            lines.append(f"{len(lines) + 1}. {text}")

    return "\n".join(lines) if lines else "暫無資料"

def _as_tags(tags: list[str], limit: int = 8) -> str:
    if not tags:
        return "`#暫無標籤`"

    clean_tags = []
    seen = set()

    for tag in tags:
        tag = str(tag or "").strip().replace("#", "")
        if not tag:
            continue

        key = tag.lower()
        if key in seen:
            continue

        seen.add(key)
        clean_tags.append(tag)

        if len(clean_tags) >= limit:
            break

    return " ".join(f"`#{tag}`" for tag in clean_tags) if clean_tags else "`#暫無標籤`"

def _opinion_icon(score: int) -> str:
    if score >= 75:
        return "🟢"
    if score >= 50:
        return "🟡"
    return "🔴"

def _opinion_label(score: int) -> str:
    if score >= 75:
        return "正向偏高"
    if score >= 50:
        return "中性偏穩"
    return "負面偏高"

def _opinion_color(score: int) -> int:
    if score >= 75:
        return 0x57F287
    if score >= 50:
        return 0xFEE75C
    return 0xED4245

def _format_data_sources(data_sources: dict[str, str]) -> str:
    if not data_sources:
        return "暫無資料"

    labels = {
        "summary": "摘要",
        "keyword": "關鍵詞",
        "emotion": "情緒",
        "topics": "主題",
        "criticism": "批評",
        "timeline": "時間軸",
        "video_content": "影片內容",
    }

    status_icons = {
        "ok": "✅",
        "insufficient_data": "⚠️",
        "error": "❌",
        "missing": "➖",
    }

    parts = []

    for key, status in data_sources.items():
        label = labels.get(key, key)
        icon = status_icons.get(status, "❔")
        parts.append(f"{icon} {label}：`{status}`")

    return "\n".join(parts)

def _format_top_hotspot(top_hotspot: dict | None) -> str:
    if not top_hotspot:
        return "目前沒有形成明確時間軸熱點。"

    time_label = top_hotspot.get("time_label", "未知時間")
    count = int(top_hotspot.get("count", 0) or 0)
    representative_comment = _one_line(
        top_hotspot.get("representative_comment", ""),
        140,
    )

    text = f"`{time_label}` 附近｜被提及 `{count}` 次"

    if representative_comment:
        text += f"\n> {representative_comment}"

    return text

def build_analyze_embed(result) -> discord.Embed:
    status = getattr(result, "status", "ok")
    error = getattr(result, "error", None)
    message = getattr(result, "message", None)

    if status == "error" or error:
        return discord.Embed(
            title="⚠️ 留言主分析失敗",
            description=_clip(error or message or "主分析發生未知錯誤。", 4096),
            color=0xED4245,
        )

    score = int(getattr(result, "public_opinion_score", 0) or 0)
    icon = _opinion_icon(score)
    label = getattr(result, "opinion_label", "") or _opinion_label(score)

    title = getattr(result, "title", "") or "YouTube 留言 AI 分析"
    url = getattr(result, "url", "")

    total_comments = int(getattr(result, "total_comments", 0) or 0)
    main_emotion = getattr(result, "main_emotion", "") or "未知"
    timeline_status = getattr(result, "timeline_status", "") or "unknown"
    
    data_sources = getattr(result, "data_sources", {}) or {}
    video_content_status = data_sources.get("video_content", "missing")

    embed = discord.Embed(
        title="📊 YouTube 留言 AI 主分析",
        description=(
            f"**影片：** [{_clip(title, 180)}]({url})\n"
            f"**整體風向：** {icon} **{label}** `{score}/100`\n"
            f"**分析狀態：** `{status}`"
        ),
        color=_opinion_color(score),
    )

    if total_comments:
        embed.add_field(
            name="📌 分析範圍",
            value=(
                f"本次共分析 `{total_comments}` 則留言。\n"
                f"主導情緒：**{main_emotion}**\n"
                f"時間軸狀態：`{timeline_status}`\n"
                f"影片內容脈絡：`{video_content_status}`"
            ),
            inline=False,
        )

    data_quality = getattr(result, "data_quality", []) or []
    if data_quality:
        embed.add_field(
            name="⚠️ 資料品質提醒",
            value=_clip(_as_bullets(data_quality, limit=4), 1024),
            inline=False,
        )

    quick_summary = getattr(result, "quick_summary", []) or []
    embed.add_field(
        name="🧭 AI 智慧快報",
        value=_clip(_as_bullets(quick_summary, limit=3), 1024),
        inline=False,
    )

    tags = getattr(result, "tags", []) or []
    embed.add_field(
        name="🏷️ 留言區標籤",
        value=_clip(_as_tags(tags, limit=8), 1024),
        inline=False,
    )

    top_topics = getattr(result, "top_topics", []) or []
    if top_topics:
        embed.add_field(
            name="💬 熱門討論主題",
            value=_clip("、".join(f"`{topic}`" for topic in top_topics[:5]), 1024),
            inline=False,
        )

    top_hotspot = getattr(result, "top_hotspot", None)
    if top_hotspot:
        embed.add_field(
            name="🔥 高能時間點",
            value=_clip(_format_top_hotspot(top_hotspot), 1024),
            inline=False,
        )

    creator_actions = getattr(result, "creator_actions", []) or []
    if creator_actions:
        embed.add_field(
            name="🎬 創作者行動建議",
            value=_clip(_as_bullets(creator_actions, limit=5), 1024),
            inline=False,
        )

    viewer_tips = getattr(result, "viewer_tips", []) or []
    if viewer_tips:
        embed.add_field(
            name="👀 觀眾提示",
            value=_clip(_as_bullets(viewer_tips, limit=5), 1024),
            inline=False,
        )

    if data_sources:
        embed.add_field(
            name="🧩 子分析來源狀態",
            value=_clip(_format_data_sources(data_sources), 1024),
            inline=False,
        )

    embed.set_footer(
        text=(
            "Analyze：整合留言摘要、情緒、主題、批評、關鍵詞、時間軸與影片內容脈絡產生。\n"
            "長影片會因字幕分析而需要較久時間，且可能因字幕品質影響分析結果。"
        )
    )

    return embed