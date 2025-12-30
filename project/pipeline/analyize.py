import discord

def analyze(url: str) -> discord.Embed:
    """
    Analyze the video's comments.
    """
    
    embed = embed_formatter(result)
    return embed

def embed_formatter(result: dict) -> discord.Embed:
    embed = discord.Embed(
        title="YT 留言摘要機器人",
        description=f"📽️ 影片標題：**{result['video_title']}**",
        color=0x5865F2
    )
    
    return embed