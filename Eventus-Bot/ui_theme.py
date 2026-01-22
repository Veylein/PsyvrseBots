import discord

DEFAULT_THUMB = "https://i.imgur.com/8Km9tLL.png"

def polished_embed(title: str, description: str, color_name: str = 'blue', image_url: str = None, thumbnail_url: str = None, footer: str = None):
    color_map = {
        'blue': discord.Color.blue(),
        'green': discord.Color.green(),
        'red': discord.Color.red(),
        'purple': discord.Color.purple(),
        'orange': discord.Color.orange(),
        'gold': discord.Color.gold(),
        'teal': discord.Color.teal()
    }
    color = color_map.get(color_name.lower() if color_name else 'blue', discord.Color.blue())
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    else:
        embed.set_thumbnail(url=DEFAULT_THUMB)
    if image_url:
        embed.set_image(url=image_url)
    if footer:
        embed.set_footer(text=footer)
    return embed
