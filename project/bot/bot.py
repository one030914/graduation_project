import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from configs.settings import ROOT, BOT_DIR

from bot.queue import AnalysisQueue

from pipeline.analyze import analyze

from data.youtube.api import API

load_dotenv(verbose=True)

with open(f"{ROOT}/data.json", "r", encoding="utf8") as jfile:
    jdata = json.load(jfile)

intents = discord.Intents.default()
intents.message_content = True

api = API()

def extract_video_id_only(url: str):
    return api.extract_video_id(url)

class MyBot(commands.Bot):
    async def setup_hook(self):
        # 1) load all cogs
        for path in (BOT_DIR / "cogs").glob("*.py"):
            if path.name != "__init__.py":
                await self.load_extension(f"bot.cogs.{path.stem}")

        # 2) sync slash commands
        slash = await self.tree.sync()
        print(f"loaded {len(slash)} slash commands.")

        # 3) analysis queue
        self.analysis_queue = AnalysisQueue(
            analyze_fn=analyze,
            extract_video_id_fn=extract_video_id_only,
            workers=4,
            cache_ttl_minutes=10,
            max_queue_size=50,
        )
        await self.analysis_queue.start()

    async def close(self):
        if hasattr(self, "analysis_queue"):
            await self.analysis_queue.stop()
        await super().close()

bot = MyBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
