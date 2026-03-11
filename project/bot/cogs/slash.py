import discord
from discord import app_commands
from datetime import datetime

from bot.core.classes import Cog_Extension

class Slash(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='analyze', description='Analyze the video\'s comments and generate a summary and keywords.')
    @app_commands.describe(url="YouTube video URL")
    async def analyze(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        q = self.bot.analysis_queue

        pos = q.queue_size() + 1
        msg = await interaction.followup.send(
            content=f"🧾 已加入分析隊列（#{pos}）。完成後我會更新這則訊息。",
            wait=True
        )

        await q.submit(url, msg, mode="full")
        
    @app_commands.command(name='summary', description='Analyze the video\'s comments and generate a summary.')
    @app_commands.describe(url="YouTube video URL")
    async def summary(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入摘要隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
        await q.submit(url, msg, mode="summary")


    @app_commands.command(name='keywords', description='Analyze the video\'s comments and generate keywords.')
    @app_commands.describe(url="YouTube video URL")
    async def keywords(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入關鍵字隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
        await q.submit(url, msg, mode="keywords")
        
    @app_commands.command(name="top_comments", description="Show top 15 comments of the video.")
    @app_commands.describe(url="YouTube video URL")
    async def top_comments(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(
            content=f"🧾 已加入熱門留言隊列（#{pos}）。完成後會更新這則訊息。", wait=True)

        await q.submit(url, msg, mode="top_comments")
        
    @app_commands.command(name="topics", description="Analyzing the main topics of the video comments.")
    @app_commands.describe(url="YouTube video URL")
    async def topics(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        q = self.bot.analysis_queue
        pos = q.queue_size() + 1
        msg = await interaction.followup.send(f"🧾 已加入主題隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
        await q.submit(url, msg, mode="topics")
        
    # @app_commands.command(name="sentiment", description="Show sentiment of the video.")
    # @app_commands.describe(url="YouTube video URL")
    # async def sentiment(self, interaction: discord.Interaction, url: str):
    #     await interaction.response.defer(thinking=True)
    #     q = self.bot.analysis_queue
    #     pos = q.queue_size() + 1
    #     msg = await interaction.followup.send(f"🧾 已加入情感隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
    #     await q.submit(url, msg, mode="sentiment")
        
    # @app_commands.command(name="trend_comments", description="Show trend comments of the video.")
    # @app_commands.describe(url="YouTube video URL")
    # async def trend_comments(self, interaction: discord.Interaction, url: str):
    #     await interaction.response.defer(thinking=True)
    #     q = self.bot.analysis_queue
    #     pos = q.queue_size() + 1
    #     msg = await interaction.followup.send(f"🧾 已加入趨勢留言隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
    #     await q.submit(url, msg, mode="trend_comments")
        
    # @app_commands.command(name="spam_comments", description="Show spam comments of the video.")
    # @app_commands.describe(url="YouTube video URL")
    # async def spam_comments(self, interaction: discord.Interaction, url: str):
    #     await interaction.response.defer(thinking=True)
    #     q = self.bot.analysis_queue
    #     pos = q.queue_size() + 1
    #     msg = await interaction.followup.send(f"🧾 已加入垃圾留言隊列（#{pos}）。完成後會更新這則訊息。", wait=True)
    #     await q.submit(url, msg, mode="spam_comments")
        
async def setup(bot):
    await bot.add_cog(Slash(bot))
