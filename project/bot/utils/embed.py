import discord
from datetime import datetime
from pipeline.schema import AnalysisResult, TopCommentsResult, TopicsResult, EmotionResult

# -------------------------
# Summary Embed
# -------------------------

def _clip(text: str, limit: int = 1024) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."

def _fmt_list(lines, max_lines: int = 6) -> str:
    if not lines:
        return "（無）"
    lines = [str(x).strip() for x in lines if str(x).strip()]
    if not lines:
        return "（無）"
    lines = lines[:max_lines]
    return "\n".join(f"{i+1}. {s}" for i, s in enumerate(lines))

def _fmt_keywords(words, max_items: int = 12) -> str:
    if not words:
        return "（無）"
    words = [str(w).strip() for w in words if str(w).strip()]
    if not words:
        return "（無）"
    words = words[:max_items]
    return " ".join(f"`{w}`" for w in words)

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

    # 摘要
    if mode in ("full", "summary"):
        if result.summary_zh:
            embed.add_field(name="📌 中文摘要", value=_clip(_fmt_list(result.summary_zh, 6)), inline=False)
        if result.summary_en:
            embed.add_field(name="📌 English Summary", value=_clip(_fmt_list(result.summary_en, 6)), inline=False)
        if not result.summary_zh and not result.summary_en:
            embed.add_field(name="📌 摘要", value="（無）", inline=False)

    # 關鍵字
    if mode in ("full", "keywords"):
        if result.keywords_zh:
            embed.add_field(name="🔑 中文關鍵字", value=_clip(_fmt_keywords(result.keywords_zh, 15)), inline=False)
        if result.keywords_en:
            embed.add_field(name="🔑 English Keywords", value=_clip(_fmt_keywords(result.keywords_en, 15)), inline=False)
        if not result.keywords_zh and not result.keywords_en:
            embed.add_field(name="🔑 關鍵字", value="（無）", inline=False)

    # 語言比例
    lr = result.lang_ratio
    lang_text = f"🇹🇼 中文：{lr.zh:.1%}\n🇺🇸 英文：{lr.en:.1%}\n🌐 其他：{lr.other:.1%}"
    embed.add_field(name="🌍 語言佔比", value=_clip(lang_text), inline=False)

    # footer
    embed.set_footer(text=f"總留言數：{result.stats.n_comments}")

    return embed

# -------------------------
# Top Comments Embed
# -------------------------

def discord_time(iso_time: str | None) -> str:
    if not iso_time:
        return ""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        unix = int(dt.timestamp())
        return f"<t:{unix}:R>"
    except Exception:
        return ""

def build_top_comments_embed(result: TopCommentsResult) -> discord.Embed:
    embed = discord.Embed(
        title=_clip(f"🧾 影片標題：**{result.title}**", 256),
        description=_clip(f"🔗 來源：{result.url}", 256),
        color=0x5865F2
    )

    if not result.top:
        embed.add_field(name="結果", value="（無符合條件的留言）", inline=False)
        return embed

    lines = []
    for i, c in enumerate(result.top, start=1):
        # show author and time if available
        author = time = ""
        if c.author:
            author = c.author
        if c.published_at:
            time = discord_time(c.published_at)
        meta_txt = f"{i}. **{author}** {time}\n" if author and time else ""
        
        counts = f" 👍 {c.like_count} ｜ 💬 {c.reply_count}"
        comments = _clip(c.text, 160)
        
        lines.append(f"{meta_txt}{comments}\n{counts}")

    # limit the length of the embed field value
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

    # if not result.topics:
    #     embed.add_field(name="結果", value="（未形成明確主題群）", inline=False)
    #     return embed

    for i, topic in enumerate(result.topics[:5], start=1):
        kw_text = "、".join(topic.keywords[:5]) if topic.keywords else "（無）"
        rep_text = "\n".join(f"- {_clip(x, 100)}" for x in topic.representative_comments[:2]) or "（無）"

        value = (
            f"**占比：** {topic.ratio:.1%}\n"
            f"**關鍵詞：** {kw_text}\n"
            f"**代表留言：**\n{rep_text}"
        )

        if len(value) > 1000:
            value = value[:999] + "…"

        embed.add_field(
            name=f"Topic {i}（{topic.size} 則）",
            value=value,
            inline=False
        )

    embed.set_footer(text=f"總留言數：{result.total_comments}")
    return embed

# -------------------------
# Emotion Embed
# -------------------------

from bot.utils.chart import build_emotion_radar_chart

EMOTION_ORDER = [
    "Joy",
    "Angry",
    "Sad",
    "Surprised",
    "Disgusted",
    "Neutral",
]

def build_emotion_embed(result: EmotionResult) -> tuple[discord.Embed, discord.File | None]:
    if result.error:
        embed = discord.Embed(
            title="⚠️ Emotion 分析失敗",
            description=result.error,
            color=0xED4245
        )
        return embed, None

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

    embed.add_field(
        name="情緒分布",
        value="\n".join(lines) if lines else "（無）",
        inline=False
    )

    embed.set_footer(text=f"總留言數：{result.total_comments} ｜ 參與情緒分析留言數：{total}")

    buf = build_emotion_radar_chart(result.stats.emotions)
    file = discord.File(buf, filename="emotion_radar.png")
    embed.set_image(url="attachment://emotion_radar.png")

    return embed, file