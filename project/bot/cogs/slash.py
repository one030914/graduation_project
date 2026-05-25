import asyncio
import discord
from discord import app_commands

from bot.core.classes import Cog_Extension
from bot.utils.embed import (
    build_emotion_embed,
    build_summary_embed,
    build_keyword_embed,
    build_top_comments_embed,
    build_topics_embed,
    build_criticism_embed,
    build_intent_embed,
    build_timeline_embed,
    build_analyze_embed,
)

class Slash(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot

    async def _render_and_edit(self, msg: discord.Message, job_id: str, *, mode: str) -> None:
        q = self.bot.analysis_queue
        try:
            if await q.wait_until_running(job_id, timeout=3.0):
                await msg.edit(content="🔎 分析中…（模型推論可能需要一點時間）", embed=None)

            result = await q.wait_for_result(job_id)
            st = q.get_status(job_id) or {}
            from_cache = bool(st.get("from_cache"))
            content = "✅（快取）分析完成" if from_cache else "✅ 分析完成"

            if mode == "top_comments":
                embed = build_top_comments_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "topics":
                embed = build_topics_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "emotion":
                embed, file = build_emotion_embed(result)
                if file:
                    await msg.edit(content=content, embed=embed, attachments=[file])
                else:
                    await msg.edit(content=content, embed=embed)
            elif mode == "criticism":
                embed = build_criticism_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "intent":
                embed = build_intent_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "timeline":
                embed = build_timeline_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "analyze":
                embed = build_analyze_embed(result)
                await msg.edit(content=content, embed=embed)
            elif mode == "keyword":
                embed = build_keyword_embed(result)
                await msg.edit(content=content, embed=embed)
            else:
                embed = build_summary_embed(result)
                await msg.edit(content=content, embed=embed)
                
        except Exception as e:
            try:
                await msg.edit(content=f"⚠️ 分析失敗：{type(e).__name__}: {e}", embed=None)
            except Exception:
                pass


    @app_commands.command(name='analyze', description='Generate a full AI insight report for the video comments.')
    @app_commands.describe(url="YouTube video URL")
    async def analyze(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(content=f"🧾 已加入分析隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="analyze")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="analyze"))
        
    @app_commands.command(name='summary', description='Analyze the video\'s comments and generate a summary.')
    @app_commands.describe(url="YouTube video URL")
    async def summary(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入摘要隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="summary")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="summary"))

    @app_commands.command(name='keyword', description='Analyze the video comments and extract keywords.')
    @app_commands.describe(url="YouTube video URL")
    async def keyword(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入關鍵詞隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="keyword")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="keyword"))

    @app_commands.command(name="top_comments", description="Show top 15 comments of the video.")
    @app_commands.describe(url="YouTube video URL")
    async def top_comments(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(content=f"🧾 已加入熱門留言隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="top_comments")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="top_comments"))
        
    @app_commands.command(name="topics", description="Analyzing the main topics of the video comments.")
    @app_commands.describe(url="YouTube video URL")
    async def topics(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入主題隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="topics")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="topics"))
        
    @app_commands.command(name="emotion", description="Analyzing emotions of the video comments.")
    @app_commands.describe(url="YouTube video URL")
    async def emotion(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入情感隊列（#{pos}）。", wait=True)
        job_id = await q.submit(url, mode="emotion")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="emotion"))

    @app_commands.command(name="criticism", description="分析 YT 留言中觀眾集體的批評、不滿輿情與改進建議。")
    @app_commands.describe(url="YouTube video URL")
    async def criticism(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(
            content=f"🧾 已加入留言批評分析隊列（#{pos}）。完成後會更新這則訊息。",
            wait=True
        )

        job_id = await q.submit(url, mode="criticism")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="criticism"))

    @app_commands.command(name="intent", description="分析 YT 留言中的提問、勘誤、許願與外部資源。")
    @app_commands.describe(url="YouTube video URL")
    async def intent(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(
            content=f"🧾 已加入留言意圖分析隊列（#{pos}）。",
            wait=True
        )

        job_id = await q.submit(url, mode="intent")
        asyncio.create_task(self._render_and_edit(msg, job_id, mode="intent"))
        
    @app_commands.command(name="timeline", description="分析 YT 留言中被提及最多的影片時間點。")
    @app_commands.describe(url="YouTube 影片網址")
    async def timeline(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        q = self.bot.analysis_queue
        pos = q.queue_size() + 1

        msg = await interaction.followup.send(
            content=f"🧾 已加入時間軸熱點分析隊列（#{pos}）。",
            wait=True
        )

        job_id = await q.submit(url, mode="timeline")
        asyncio.create_task(
            self._render_and_edit(msg, job_id, mode="timeline")
        )
        
async def setup(bot):
    await bot.add_cog(Slash(bot))
