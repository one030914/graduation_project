import discord
from discord.ext import commands
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from configs.settings import ROOT, BOT_DIR

load_dotenv(verbose=True)
with open(f'{ROOT}/data.json', 'r', encoding='utf8') as jfile:
    jdata = json.load(jfile)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event      # prefix: !
async def on_ready():
    for path in (BOT_DIR / "cogs").glob("*.py"):
        if path.name != "__init__.py":
            await bot.load_extension(f"bot.cogs.{path.stem}")
    
    slash = await bot.tree.sync()
    print(f"loaded {len(slash)} slash commands.")
    print('Bot is online!')

if __name__ == '__main__':
    bot.run(os.getenv('TOKEN'))