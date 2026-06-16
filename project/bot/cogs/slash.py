import asyncio
import discord
from discord import app_commands

from bot.core.classes import Cog_Extension
from bot.utils.embed import (
    build_emotion_embed,
    build_summary_embed,
    build_keyword_embed,
    build_topics_embed,
    build_criticism_embed,
    build_timeline_embed,
    build_analyze_embed,
)

EMBED_BUILDERS = {
    "analyze": build_analyze_embed,
    "summary": build_summary_embed,
    "keyword": build_keyword_embed,
    "topics": build_topics_embed,
    "criticism": build_criticism_embed,
    "timeline": build_timeline_embed,
}


class Slash(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot

    async def _submit_analysis(
        self,
        interaction: discord.Interaction,
        url: str,
        *,
        mode: str,
        queued_message: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(
            queued_message.format(pos=pos),
            wait=True,
        )
        job_id = await q.submit(url, mode=mode)
        asyncio.create_task(self._render_and_edit(msg, job_id, mode=mode))

    async def _render_and_edit(self, msg: discord.Message, job_id: str, *, mode: str) -> None:
        q = self.bot.analysis_queue
        try:
            if await q.wait_until_running(job_id, timeout=3.0):
                await msg.edit(
                    content=(
                        "🔎 深度分析中…\n"
                        "正在處理留言摘要、情緒、主題、批評、時間軸與影片內容脈絡。\n"
                        "若影片較長，分析可能需要 3～5 分鐘，完成後會自動更新。"
                    ),
                    embed=None,
                )

            result = await q.wait_for_result(job_id)
            st = q.get_status(job_id) or {}
            from_cache = bool(st.get("from_cache"))
            content = "✅（快取）分析完成" if from_cache else "✅ 分析完成"

            if mode == "emotion":
                embed = build_emotion_embed(result)
                await msg.edit(content=content, embed=embed)
            else:
                embed = EMBED_BUILDERS.get(mode, build_summary_embed)(result)
                await msg.edit(content=content, embed=embed)
                
        except Exception as e:
            try:
                await msg.edit(content=f"⚠️ 分析失敗：{type(e).__name__}: {e}", embed=None)
            except Exception:
                pass


    @app_commands.command(name='analyze', description='Generate a full AI insight report for the video comments.')
    @app_commands.describe(url="YouTube video URL")
    async def analyze(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="analyze",
            queued_message=(
                "🧾 已加入分析隊列（#{pos}）。\n"
                "🔎 本次會整合留言與影片內容進行深度分析，長影片可能需要數分鐘。"
            ),
        )
        
    @app_commands.command(name='summary', description='Analyze the video\'s comments and generate a summary.')
    @app_commands.describe(url="YouTube video URL")
    async def summary(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="summary",
            queued_message="🧾 已加入摘要隊列（#{pos}）。",
        )

    @app_commands.command(name='keyword', description='Analyze the video comments and extract keywords.')
    @app_commands.describe(url="YouTube video URL")
    async def keyword(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="keyword",
            queued_message="🧾 已加入關鍵詞隊列（#{pos}）。",
        )

    @app_commands.command(name="topics", description="Analyzing the main topics of the video comments.")
    @app_commands.describe(url="YouTube video URL")
    async def topics(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="topics",
            queued_message="🧾 已加入主題隊列（#{pos}）。",
        )
        
    @app_commands.command(name="emotion", description="Analyzing emotions of the video comments.")
    @app_commands.describe(url="YouTube video URL")
    async def emotion(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="emotion",
            queued_message="🧾 已加入情感隊列（#{pos}）。",
        )

    @app_commands.command(name="criticism", description="分析 YT 留言中觀眾集體的批評、不滿輿情與改進建議。")
    @app_commands.describe(url="YouTube video URL")
    async def criticism(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="criticism",
            queued_message="🧾 已加入留言批評分析隊列（#{pos}）。完成後會更新這則訊息。",
        )

    @app_commands.command(name="timeline", description="分析 YT 留言中被提及最多的影片時間點。")
    @app_commands.describe(url="YouTube 影片網址")
    async def timeline(self, interaction: discord.Interaction, url: str):
        await self._submit_analysis(
            interaction,
            url,
            mode="timeline",
            queued_message="🧾 已加入時間軸熱點分析隊列（#{pos}）。",
        )
        
async def setup(bot):
    await bot.add_cog(Slash(bot))
