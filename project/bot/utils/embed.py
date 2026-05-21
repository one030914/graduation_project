import discord
from datetime import datetime
from configs.schema import (
    AnalysisResult, 
    TopCommentsResult, 
    TopicsResult, 
    EmotionResult,
    CommentCriticismResult
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

# -------------------------
# Summary Embed
# -------------------------

def build_summary_embed(result: AnalysisResult, mode: str = "full") -> discord.Embed:
    if result.error:
        return discord.Embed(
            title="⚠️ 分析失敗",
            description=_clip(result.error, 4096),
            color=0xED4245
        )

    embed = discord.Embed(
        title=_clip(f"🧾 影片標題：**{result.title}**", 256),
        description=_clip(f"🔗 來源：{result.url}", 256),
        color=0x5865F2
    )

    if mode in ("full", "summary"):
        if result.summary_zh:
            embed.add_field(name="📌 中文摘要", value=_clip(_fmt_list(result.summary_zh, 6)), inline=False)
        if result.summary_en:
            embed.add_field(name="📌 English Summary", value=_clip(_fmt_list(result.summary_en, 6)), inline=False)
        if not result.summary_zh and not result.summary_en:
            embed.add_field(name="📌 摘要", value="（無）", inline=False)

    if mode in ("full", "keywords"):
        if result.keywords_zh:
            embed.add_field(name="🔑 中文關鍵字", value=_clip(_fmt_keywords(result.keywords_zh, 15)), inline=False)
        if result.keywords_en:
            embed.add_field(name="🔑 English Keywords", value=_clip(_fmt_keywords(result.keywords_en, 15)), inline=False)
        if not result.keywords_zh and not result.keywords_en:
            embed.add_field(name="🔑 關鍵字", value="（無）", inline=False)

    lr = result.lang_ratio
    lang_text = f"🇹🇼 中文：{lr.zh:.1%}\n🇺🇸 英文：{lr.en:.1%}\n🌐 其他：{lr.other:.1%}"
    embed.add_field(name="🌍 語言佔比", value=_clip(lang_text), inline=False)
    embed.set_footer(text=f"總留言數：{result.stats.n_comments}")

    return embed

# -------------------------
# Top Comments Embed
# -------------------------

def build_top_comments_embed(result: TopCommentsResult) -> discord.Embed:
    if result.error:
        return discord.Embed(
            title="⚠️ Top comments 分析失敗",
            description=_clip(result.error, 4096),
            color=0xED4245
        )

    embed = discord.Embed(
        title=_clip(f"🧾 影片標題：**{result.title}**", 256),
        description=_clip(f"🔗 來源：{result.url}", 256),
        color=0x5865F2
    )

    lines = []
    for i, c in enumerate(result.top, start=1):
        author = time = ""
        if c.author:
            author = c.author
        if c.published_at:
            time = discord_time(c.published_at)
        meta_txt = f"{i}. **{author}** {time}\n" if author and time else ""
        counts = f" 👍 {c.like_count} ｜ 💬 {c.reply_count}"
        comments = _clip(c.text, 160)
        lines.append(f"{meta_txt}{comments}\n{counts}")

    chunk = "\n\n".join(lines)
    if len(chunk) > 3500:
        chunk = chunk[:3499] + "…"

    embed.add_field(name=f"Top {len(result.top)} comments", value=_clip(chunk), inline=False)
    embed.set_footer(text=f"共抓到可用留言：{result.total_fetched}")
    return embed

# -------------------------
# Topics Embed
# -------------------------

LANG_MAP = {
    "zh": "中文",
    "en": "英文",
    "unknown": "其他"
}

def build_topics_embed(result: TopicsResult) -> discord.Embed:
    if result.error:
        return discord.Embed(
            title="⚠️ Topic 分析失敗",
            description=result.error,
            color=0xED4245
        )

    display_lang = LANG_MAP.get(result.language, result.language)
    embed = discord.Embed(
        title="YT 留言主題分析",
        description=f"🧾 影片標題：**{result.title}**\n🌐 主要語言：{display_lang}",
        color=0x5865F2
    )

    for i, topic in enumerate(result.topics[:5], start=1):
        kw_text = "、".join(topic.keywords[:5]) if topic.keywords else "（無）"
        rep_text = "\n".join(f"- {_clip(x, 100)}" for x in topic.representative_comments[:2]) or "（無）"
        value = (f"**占比：** {topic.ratio:.1%}\n**關鍵詞：** {kw_text}\n**代表留言：**\n{rep_text}")
        if len(value) > 1000:
            value = value[:999] + "…"
        embed.add_field(name=f"Topic {i}（{topic.size} 則）", value=value, inline=False)

    embed.set_footer(text=f"參與主題分析留言數：{result.total_comments}")
    return embed

# -------------------------
# Emotion Embed
# -------------------------

from bot.utils.chart import build_emotion_radar_chart

EMOTION_ORDER = ["Joy", "Angry", "Sad", "Surprised", "Disgusted", "Neutral"]

def build_emotion_embed(result: EmotionResult) -> tuple[discord.Embed, discord.File | None]:
    if result.error:
        return discord.Embed(title="⚠️ Emotion 分析失敗", description=result.error, color=0xED4245), None

    display_lang = LANG_MAP.get(result.language, result.language)
    embed = discord.Embed(
        title="YT 留言情緒分析",
        description=f"🧾 影片標題：**{result.title}**\n🌐 分析語言：{display_lang}",
        color=0x5865F2
    )

    stats = result.stats.emotions if result.stats else {}
    total = result.stats.total if result.stats else 0
    lines = []
    for emo in EMOTION_ORDER:
        count = stats.get(emo, 0)
        ratio = (count / total) if total else 0
        lines.append(f"**{emo}**：{count}（{ratio:.1%}）")

    embed.add_field(name="情緒分布", value="\n".join(lines) if lines else "（無）", inline=False)
    embed.set_footer(text=f"總留言數：{result.total_comments} ｜ 參與分析留言數：{total}")

    buf = build_emotion_radar_chart(result.stats.emotions)
    file = discord.File(buf, filename="emotion_radar.png")
    embed.set_image(url="attachment://emotion_radar.png")
    return embed, file

# -------------------------
# Criticism Embed
# -------------------------

def build_criticism_embed(result: CommentCriticismResult) -> discord.Embed:
    """
    建構留言批評輿情分析的 Discord Embed。
    使用 E67E22 (暗橘色) 作為警示色調。
    """
    if result.error:
        return discord.Embed(
            title="⚠️ 留言批評分析失敗",
            description=_clip(result.error, 4096),
            color=0xED4245
        )

    embed = discord.Embed(
        title=_clip(f"💬 觀眾留言批評與輿情觀測：**{result.title}**", 256),
        description=_clip(f"🔗 來源：{result.url}", 256),
        color=0xE67E22
    )

    # 主要批評點
    criticisms_text = "\n".join([f"• {item}" for item in result.main_criticisms]) if result.main_criticisms else "（留言區風向良好，未見明顯集體不滿）"
    embed.add_field(
        name="🤬 留言集中批評與抱怨痛點", 
        value=_clip(criticisms_text), 
        inline=False
    )

    # 不滿原因
    reasons_text = "\n".join([f"• {item}" for item in result.discontent_reasons]) if result.discontent_reasons else "（無特殊導火線或潛在衝突原因）"
    embed.add_field(
        name="🔍 觀眾不滿/引發爭議的底層因素", 
        value=_clip(reasons_text), 
        inline=False
    )

    # 改進建議
    suggestions_text = "\n".join([f"• {item}" for item in result.suggestions]) if result.suggestions else "（觀眾未在留言中提出具體改進期望）"
    embed.add_field(
        name="💡 觀眾敲碗或優化建議意向", 
        value=_clip(suggestions_text), 
        inline=False
    )

    embed.set_footer(text="Powered by Ollama (Llama3) 留言輿情分析模組")
    return embed

# -------------------------
# Intent Embed
# -------------------------

def _safe_get(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _format_intent_comment(item, index: int) -> str:
    text = _safe_get(item, "text", "")
    like_count = _safe_get(item, "like_count", 0) or 0
    reply_count = _safe_get(item, "reply_count", 0) or 0

    return (
        f"{index}. {_clip(text, 100)}\n"
        f"   👍 `{like_count}`｜💬 `{reply_count}`"
    )

def _format_comment_list(items, limit: int = 3) -> str:
    if not items:
        return "暫無資料"

    return "\n".join(
        _format_intent_comment(item, i + 1)
        for i, item in enumerate(items[:limit])
    )

def _format_distribution(counts: dict, total: int) -> str:
    if not counts:
        return "暫無資料"

    labels = {
        "question": "提問",
        "correction": "勘誤",
        "wishlist": "許願",
        "complaint": "抱怨",
        "resource": "資源",
        "praise": "稱讚",
        "meme": "玩梗",
        "other": "其他",
    }

    parts = []
    for key, label in labels.items():
        value = int(counts.get(key, 0) or 0)
        if value <= 0:
            continue

        ratio = value / max(1, total) * 100
        parts.append(f"`{label}` {value} ({ratio:.1f}%)")

    return "｜".join(parts) if parts else "暫無明顯意圖分類"

def build_intent_embed(result) -> discord.Embed:
    error = _safe_get(result, "error")
    if error:
        return discord.Embed(
            title="⚠️ 留言意圖分析失敗",
            description=str(error),
            color=discord.Color.red(),
        )

    title = _safe_get(result, "title", "") or "YouTube 影片"
    url = _safe_get(result, "url", "")
    total_comments = int(_safe_get(result, "total_comments", 0) or 0)

    counts = _safe_get(result, "intent_counts", {}) or {}

    questions = _safe_get(result, "questions", []) or []
    corrections = _safe_get(result, "corrections", []) or []
    wishlist = _safe_get(result, "wishlist", []) or []
    complaints = _safe_get(result, "complaints", []) or []
    resources = _safe_get(result, "resources", []) or []

    high_value_count = (
        len(questions)
        + len(corrections)
        + len(wishlist)
        + len(complaints)
        + len(resources)
    )

    embed = discord.Embed(
        title="🎯 留言意圖與行動分析",
        description=(
            f"**影片：** [{title}]({url})\n"
            f"**分析留言數：** `{total_comments}` 則\n"
            f"**高價值留言類型：** `{high_value_count}` 筆候選"
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="📊 意圖分布",
        value=_format_distribution(counts, total_comments),
        inline=False,
    )

    if questions:
        embed.add_field(
            name="❓ 高價值提問",
            value=_format_comment_list(questions, limit=3),
            inline=False,
        )

    if corrections:
        embed.add_field(
            name="🛠️ 重要勘誤",
            value=_format_comment_list(corrections, limit=3),
            inline=False,
        )

    if wishlist:
        embed.add_field(
            name="🌱 觀眾許願池",
            value=_format_comment_list(wishlist, limit=3),
            inline=False,
        )

    if complaints:
        embed.add_field(
            name="⚠️ 主要抱怨 / 批評",
            value=_format_comment_list(complaints, limit=3),
            inline=False,
        )

    if resources:
        lines = []
        for i, item in enumerate(resources[:3]):
            text = _safe_get(item, "text", "")
            urls = _safe_get(item, "urls", []) or []
            url_text = urls[0] if urls else "未擷取到網址"
            lines.append(
                f"{i + 1}. {_clip(text, 80)}\n"
                f"   🔗 {url_text}"
            )

        embed.add_field(
            name="🔗 外部資源分享",
            value="\n".join(lines) if lines else "暫無資料",
            inline=False,
        )

    embed.set_footer(
        text="Intent Analysis：依留言文字、讚數、回覆數與連結資訊排序"
    )

    return embed

# -------------------------
# Timeline Embed
# -------------------------

def build_timeline_embed(result) -> discord.Embed:
    status = getattr(result, "status", "ok")
    message = getattr(result, "message", None)

    if status == "error":
        return discord.Embed(
            title="⚠️ 時間軸分析失敗",
            description=str(message or "分析過程發生未知錯誤。"),
            color=discord.Color.red(),
        )

    title = getattr(result, "title", "") or "YouTube 影片"
    url = getattr(result, "url", "")
    total_comments = int(getattr(result, "total_comments", 0) or 0)
    timestamp_comment_count = int(
        getattr(result, "timestamp_comment_count", 0) or 0
    )
    hotspots = getattr(result, "hotspots", []) or []

    if status == "insufficient_data" or not hotspots:
        message or (
            "此影片留言中較少出現 05:10 這類時間戳，"
            "因此無法形成穩定的影片片段熱點。"
        )

        embed = discord.Embed(
            title="📍 時間軸資料不足",
            description=(
                f"**影片：** [{title}]({url})\n"
                f"**分析留言數：** `{total_comments}` 則\n"
                f"**含時間戳留言：** `{timestamp_comment_count}` 則\n\n"
                f"{message}"
            ),
            color=discord.Color.orange(),
        )

        embed.add_field(
            name="建議查看",
            value=(
                "`/topics` 觀察熱門討論主題\n"
                "`/intent` 查看提問、勘誤與許願內容\n"
                "`/emotion` 判斷留言整體風向"
            ),
            inline=False,
        )

        embed.set_footer(
            text="Timeline Analysis：資料不足時不強行產生熱點，避免誤導判讀"
        )

        return embed

    embed = discord.Embed(
        title="🔥 留言時間軸熱點分析",
        description=(
            f"**影片：** [{title}]({url})\n"
            f"**分析留言數：** `{total_comments}` 則\n"
            f"**含時間戳留言：** `{timestamp_comment_count}` 則"
        ),
        color=discord.Color.green(),
    )

    top_hotspot = hotspots[0]
    top_time = getattr(top_hotspot, "time_label", "未知時間")
    top_count = int(getattr(top_hotspot, "count", 0) or 0)
    representative_comments = getattr(
        top_hotspot, "representative_comments", []
    ) or []

    top_value = f"**{top_time}** 附近｜被提及 `{top_count}` 次"

    if representative_comments:
        top_value += f"\n> {_clip(representative_comments[0], 140)}"

    embed.add_field(
        name="🏆 Top 1 高能片段",
        value=top_value,
        inline=False,
    )

    if len(hotspots) > 1:
        other_lines = []
        for i, h in enumerate(hotspots[1:6], start=1):
            time_label = getattr(h, "time_label", "未知時間")
            count = int(getattr(h, "count", 0) or 0)
            other_lines.append(
                f"{i}. `{time_label}`｜被提及 `{count}` 次"
            )

        embed.add_field(
            name="📍 其他熱門片段",
            value="\n".join(other_lines),
            inline=False,
        )

    if representative_comments:
        comments_text = "\n".join(
            f"> {_clip(comment, 120)}"
            for comment in representative_comments[:3]
        )

        embed.add_field(
            name=f"💬 `{top_time}` 代表留言",
            value=comments_text,
            inline=False,
        )

    embed.add_field(
        name="🧭 分析說明",
        value=(
            "此分析統計的是「留言中被觀眾主動提及的影片時間點」，"
            "不是 YouTube 實際重播率。"
        ),
        inline=False,
    )

    embed.set_footer(
        text="Timeline Analysis：根據留言中的時間戳統計"
    )

    return embed

# -------------------------
# Main Insight Embed
# -------------------------

def _as_bullets(items: list[str], limit: int = 5) -> str:
    if not items:
        return "暫無資料"

    return "\n".join(
        f"{i + 1}. {str(item)}"
        for i, item in enumerate(items[:limit])
    )

def _as_tags(tags: list[str], limit: int = 6) -> str:
    if not tags:
        return "`#暫無標籤`"

    return " ".join(f"`#{tag}`" for tag in tags[:limit])

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

def build_main_insight_embed(result) -> discord.Embed:
    if getattr(result, "error", None):
        return discord.Embed(
            title="⚠️ 綜合分析失敗",
            description=result.error,
            color=discord.Color.red(),
        )

    score = int(getattr(result, "public_opinion_score", 0) or 0)
    icon = _opinion_icon(score)
    label = getattr(result, "opinion_label", "") or _opinion_label(score)

    title = getattr(result, "title", "") or "YouTube 留言 AI 綜合分析"
    url = getattr(result, "url", "")

    embed = discord.Embed(
        title="📊 YouTube 留言 AI 綜合分析",
        description=(
            f"**影片：** [{title}]({url})\n"
            f"**整體風向：** {icon} **{label}** `{score}/100`"
        ),
        color=discord.Color.green() if score >= 75 else (
            discord.Color.gold() if score >= 50 else discord.Color.red()
        ),
    )

    total_comments = getattr(result, "total_comments", 0)
    if total_comments:
        embed.add_field(
            name="📌 分析範圍",
            value=f"本次共分析 `{total_comments}` 則留言。",
            inline=False,
        )

    embed.add_field(
        name="🧭 AI 智慧快報",
        value=_as_bullets(getattr(result, "quick_summary", []), limit=3),
        inline=False,
    )

    embed.add_field(
        name="🏷️ 留言區標籤",
        value=_as_tags(getattr(result, "tags", []), limit=6),
        inline=False,
    )

    top_topics = getattr(result, "top_topics", [])
    if top_topics:
        embed.add_field(
            name="💬 熱門討論主題",
            value="、".join(f"`{topic}`" for topic in top_topics[:5]),
            inline=False,
        )

    top_hotspot = getattr(result, "top_hotspot", None)
    if top_hotspot:
        time_label = top_hotspot.get("time_label", "未知時間")
        count = top_hotspot.get("count", 0)
        comment = top_hotspot.get("representative_comment", "")

        value = f"**{time_label}** 附近被留言提及 `{count}` 次"
        if comment:
            value += f"\n> {comment[:120]}"

        embed.add_field(
            name="🔥 最高討論片段",
            value=value,
            inline=False,
        )

    creator_actions = getattr(result, "creator_actions", [])
    if creator_actions:
        embed.add_field(
            name="🎬 創作者行動建議",
            value=_as_bullets(creator_actions, limit=3),
            inline=False,
        )

    viewer_tips = getattr(result, "viewer_tips", [])
    if viewer_tips:
        embed.add_field(
            name="👀 觀眾觀看提示",
            value=_as_bullets(viewer_tips, limit=3),
            inline=False,
        )

    embed.set_footer(
        text="Main Insight 由情緒、主題、時間軸與意圖分析彙整產生"
    )

    return embed