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
            await self.bot.load_extension(f'bot.cogs.{extension}')
            await ctx.send(f'Loaded {extension} done.')
        except commands.ExtensionNotFound as e:
            await ctx.send(f'Extension {extension} not found.')
        except commands.ExtensionAlreadyLoaded as e:
            await ctx.send(f'Extension {extension} already loaded.')
        except commands.ExtensionFailed as e:
            await ctx.send(f'Extension {extension} failed to load.')
        except Exception as e:
            await ctx.send(f'An error occurred: {str(e)}')
    
    @commands.command()
    async def unload(self, ctx, extension=None):
        if extension is None:
            await ctx.send('請提供要卸載的擴充名稱！')
            return
        
        try:
            await self.bot.unload_extension(f'bot.cogs.{extension}')
            await ctx.send(f'Unloaded {extension} done.')
        except commands.ExtensionNotFound as e:
            await ctx.send(f'Extension {extension} not found.')
        except commands.ExtensionNotLoaded as e:
            await ctx.send(f'Extension {extension} not loaded.')
        except Exception as e:
            await ctx.send(f'An error occurred: {str(e)}')

    @commands.command()
    async def reload(self, ctx, extension=None):
        if extension is None:
            await ctx.send('請提供要重新載入的擴充名稱！')
            return
        
        try:
            await self.bot.reload_extension(f'bot.cogs.{extension}')
            await ctx.send(f'Reloaded {extension} done.')
        except commands.ExtensionNotLoaded as e:
            await ctx.send(f'Extension {extension} not loaded.')
        except commands.ExtensionNotFound as e:
            await ctx.send(f'Extension {extension} not found.')
        except commands.ExtensionFailed as e:
            await ctx.send(f'Extension {extension} failed to load.')
        except Exception as e:
            await ctx.send(f'An error occurred: {str(e)}')

async def setup(bot):
    await bot.add_cog(Cmd(bot))