import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List


CATEGORY_NAMES: List[str] = [
    'economy', 'gambling', 'boardgame', 'cards', 'puzzle', 'arcade', 'fishing', 'farming',
    'social', 'pets', 'quests', 'progression', 'business', 'premium', 'fun', 'music', 'utility', 'admin', 'events'
]


class Perimeter(commands.Cog):
    """Bridge to run prefix commands under category-named slash commands.

    Each category command takes a freeform `input` string which is parsed and
    dispatched to the underlying prefix command (first token).
    This approach avoids having to reimplement every subcommand as a true
    subcommand while still exposing simple `/gambling`-style entry points.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def _invoke_prefix_from_interaction(bot: commands.Bot, interaction: discord.Interaction, input: str):
    await interaction.response.defer()
    ctx = await commands.Context.from_interaction(interaction)
    text = (input or "").strip()
    if not text:
        await interaction.followup.send("Please provide a command to run (e.g. `slots 100`).", ephemeral=True)
        return
    parts = text.split()
    cmd_name = parts[0]
    args = parts[1:]
    cmd = bot.get_command(cmd_name)
    if cmd is None:
        # try with common prefixes removed (L! etc.)
        if cmd_name.startswith('L!'):
            cmd = bot.get_command(cmd_name[2:])
    if cmd is None:
        await interaction.followup.send(f"Unknown command: {cmd_name}", ephemeral=True)
        return
    try:
        await ctx.invoke(cmd, *args)
    except Exception as e:
        await interaction.followup.send(f"Failed to run `{cmd_name}`: {e}", ephemeral=True)


async def _minigame_handler(bot: commands.Bot, interaction: discord.Interaction, game: str, target: Optional[str] = None):
    await interaction.response.defer()
    ctx = await commands.Context.from_interaction(interaction)
    # Map a few canonical minigame names to existing commands
    mapping = {
        'wordle': 'wordle',
        'trivia': 'trivia',
        'rps': 'rps',
        'typerace': 'typerace',
        'gtn': 'gtn',
        'memory': 'memory',
    }
    cmd_name = mapping.get(game, game)
    cmd = bot.get_command(cmd_name)
    if cmd is None:
        await interaction.followup.send(f"Minigame not available: {game}", ephemeral=True)
        return
    try:
        if target:
            await ctx.invoke(cmd, target)
        else:
            await ctx.invoke(cmd)
    except Exception as e:
        await interaction.followup.send(f"Failed to start minigame `{game}`: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    cog = Perimeter(bot)
    await bot.add_cog(cog)
    # Per-category bridge commands are provided by the more explicit
    # `PerimeterExplicit` cog which defers registration until after all
    # cogs are loaded. Avoid dynamically creating and registering duplicate
    # category commands here.
