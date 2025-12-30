import discord
from pipeline.schema import AnalysisResult

FIELD_VALUE_LIMIT = 1024

def _clip(text: str, limit: int = FIELD_VALUE_LIMIT) -> str:
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

def build_summary_embed(result: AnalysisResult) -> discord.Embed:
    if result.error:
        return discord.Embed(
            title="⚠️ 分析失敗",
            description=_clip(result.error, 4096),
            color=0xED4245
        )

    e = discord.Embed(
        title="YT 留言摘要機器人",
        description=_clip(f"🧾 影片標題：**{result.title or result.video_id}**", 4096),
        color=0x5865F2
    )

    # 摘要
    if result.summary_zh:
        e.add_field(name="📌 中文摘要", value=_clip(_fmt_list(result.summary_zh, 6)), inline=False)
    if result.summary_en:
        e.add_field(name="📌 English Summary", value=_clip(_fmt_list(result.summary_en, 6)), inline=False)
    if not result.summary_zh and not result.summary_en:
        e.add_field(name="📌 摘要", value="（無）", inline=False)

    # 關鍵字
    if result.keywords_zh:
        e.add_field(name="🔑 中文關鍵字", value=_clip(_fmt_keywords(result.keywords_zh, 15)), inline=False)
    if result.keywords_en:
        e.add_field(name="🔑 English Keywords", value=_clip(_fmt_keywords(result.keywords_en, 15)), inline=False)
    if not result.keywords_zh and not result.keywords_en:
        e.add_field(name="🔑 關鍵字", value="（無）", inline=False)

    # 語言比例
    lr = result.lang_ratio
    lang_text = f"🇹🇼 中文：{lr.zh:.1%}\n🇺🇸 英文：{lr.en:.1%}\n🌐 其他：{lr.other:.1%}"
    e.add_field(name="🌍 語言佔比", value=_clip(lang_text), inline=False)

    # footer
    e.set_footer(text=f"總留言數：{result.stats.n_comments}")

    return e
