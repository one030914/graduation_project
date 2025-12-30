import discord
from discord.ext import commands
from bot.core.classes import Cog_Extension

class Cmd(Cog_Extension):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def load(self, ctx, extension=None):
        if extension is None:
            await ctx.send('請提供要載入的擴充名稱！')
            return
        
        try:
            await self.bot.load_extension(f'cogs.{extension}')
            await ctx.send(f'Loaded {extension} done.')
        except Exception as e:
            await ctx.send(f'載入失敗：{str(e)}')
    
    @commands.command()
    async def unload(self, ctx, extension=None):
        if extension is None:
            await ctx.send('請提供要卸載的擴充名稱！')
            return
        
        try:
            await self.bot.unload_extension(f'cogs.{extension}')
            await ctx.send(f'Unloaded {extension} done.')
        except Exception as e:
            await ctx.send(f'卸載失敗：{str(e)}')

    @commands.command()
    async def reload(self, ctx, extension=None):
        if extension is None:
            await ctx.send('請提供要重新載入的擴充名稱！')
            return
        
        try:
            await self.bot.reload_extension(f'cogs.{extension}')
            await ctx.send(f'Reloaded {extension} done.')
        except Exception as e:
            await ctx.send(f'重新載入失敗：{str(e)}')

async def setup(bot):
    await bot.add_cog(Cmd(bot))