import discord
from discord import app_commands
from discord.ui import View, Button
from datetime import datetime
from core.classes import Cog_Extension
from pipeline.analyize import analyze

class Slash(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name='ping', description='Check the bot\'s latency')
    async def ping(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title='Pong!',
            description=f'Latency: {round(self.bot.latency*1000)} ms',
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name='analyze', description='analyze the video\'t comments.')
    @app_commands.describe(url="YouTube 影片網址")
    async def analyze(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, analyze, url)

        await interaction.followup.send(embed=result)

async def setup(bot):
    await bot.add_cog(Slash(bot))