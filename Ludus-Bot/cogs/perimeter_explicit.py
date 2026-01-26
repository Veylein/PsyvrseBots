import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List


def _make_choice(name: str):
    return app_commands.Choice(name=name, value=name)


class PerimeterExplicit(commands.Cog):
    """Explicit per-category slash commands with subcommand autocomplete.

    Each command takes a single `subcommand` string and attempts to invoke
    the corresponding prefix command on the bot. Autocomplete will suggest
    matching prefix commands present on the bot at runtime.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _invoke(self, interaction: discord.Interaction, subcommand: str):
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        text = (subcommand or "").strip()
        if not text:
            await interaction.followup.send("Please provide a subcommand to run.", ephemeral=True)
            return
        parts = text.split()
        cmd_name = parts[0]
        args = parts[1:]
        cmd = self.bot.get_command(cmd_name)
        if cmd is None:
            # try with L! prefix
            if cmd_name.startswith('L!'):
                cmd = self.bot.get_command(cmd_name[2:])
        if cmd is None:
            await interaction.followup.send(f"Unknown command: {cmd_name}", ephemeral=True)
            return
        try:
            await ctx.invoke(cmd, *args)
        except Exception as e:
            await interaction.followup.send(f"Error running `{cmd_name}`: {e}", ephemeral=True)

    def _autocomplete_for(self, interaction: discord.Interaction, current: str, keyword: str) -> List[app_commands.Choice]:
        current = (current or "").lower()
        matches = []
        for c in self.bot.commands:
            try:
                cog_name = c.cog_name.lower() if c.cog_name else ''
                name = c.name.lower()
                help_text = (c.help or '').lower()
                if keyword in cog_name or keyword in name or keyword in help_text:
                    if current in c.name.lower():
                        matches.append(_make_choice(c.name))
                    elif not current:
                        matches.append(_make_choice(c.name))
            except Exception:
                continue
        return matches[:25]


# Define category commands (exclude 'minigame' — handled separately)
CATEGORIES = [
    'economy', 'gambling', 'boardgame', 'cards', 'puzzle', 'arcade', 'fishing', 'farming',
    'social', 'pets', 'quests', 'progression', 'business', 'premium', 'fun', 'music', 'utility', 'admin', 'events'
]


for cat in CATEGORIES:
    # create a function and autocomplete function per category
    async def _cmd(self, interaction: discord.Interaction, subcommand: str = ""):
        await self._invoke(interaction, subcommand)

    async def _ac(self, interaction: discord.Interaction, current: str):
        return self._autocomplete_for(interaction, current, keyword=cat)

    # assign names and docstrings
    _cmd.__name__ = cat
    _cmd.__doc__ = f"Run a {cat} category command (pass subcommand and args)."
    _ac.__name__ = f"{cat}_autocomplete"

    # attach to Cog class
    setattr(PerimeterExplicit, cat, app_commands.command(name=cat, description=f"Run a {cat} category command")( _cmd ))
    # attach autocomplete decorator
    getattr(PerimeterExplicit, cat).autocomplete('subcommand')(_ac)


async def setup(bot: commands.Bot):
    cog = PerimeterExplicit(bot)
    await bot.add_cog(cog)

    # Register only commands that do not already exist to avoid collisions
    for cat in CATEGORIES:
        if bot.tree.get_command(cat) is not None:
            # skip if another extension already registered this slash command
            continue

        async def _wrapper(interaction: discord.Interaction, subcommand: str = "", _cog=cog):
            await _cog._invoke(interaction, subcommand)

        cmd = app_commands.Command(name=cat, callback=_wrapper, description=f"Run a {cat} category command")
        try:
            bot.tree.add_command(cmd)
        except Exception:
            # if adding fails, skip and continue
            continue

    # Add a /minigame command if not present
    if bot.tree.get_command('minigame') is None:
        async def _minigame_wrapper(interaction: discord.Interaction, game: str, target: Optional[str] = None, _cog=cog):
            await _cog._invoke(interaction, f"{game} {target or ''}".strip())

        cmd = app_commands.Command(name='minigame', callback=_minigame_wrapper, description='Play a selected minigame')
        try:
            bot.tree.add_command(cmd)
        except Exception:
            pass
