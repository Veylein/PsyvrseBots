import discord
from discord import app_commands
from discord.ext import commands

from src.logger import setup_logger
from src.utils.guild_settings import load as load_guild_settings

logger = setup_logger(__name__)

from typing import List

PAGINATION_LINES = 10
PAGINATION_TIMEOUT = 120.0


def _build_help_pages(bot: commands.Bot, prefix: str, color_int: int, examples: dict) -> List[discord.Embed]:
    cmds = [c for c in bot.commands if not c.hidden]
    # ensure help filled from docstrings
    for c in cmds:
        if not c.help:
            doc = getattr(getattr(c, 'callback', None), '__doc__', None)
            if doc:
                c.help = doc.strip().splitlines()[0]

    # flatten lines with cog headings when changed
    lines = []
    last_cog = None
    for c in sorted(cmds, key=lambda x: (x.cog_name or '', x.name)):
        cog = c.cog_name or 'General'
        if cog != last_cog:
            lines.append(f"__{cog}__")
            last_cog = cog
        sig = f" {c.signature}" if c.signature else ''
        name = f"{prefix}{c.name}{sig}"
        desc = c.help or 'No description provided.'
        lines.append(f"**{name}** — {desc}")

    # chunk into pages
    pages: List[discord.Embed] = []
    for i in range(0, len(lines), PAGINATION_LINES):
        chunk = lines[i:i + PAGINATION_LINES]
        e = discord.Embed(title='🎶 Sonus Help', color=color_int, timestamp=discord.utils.utcnow())
        e.description = '\n'.join(chunk)
        pages.append(e)

    if not pages:
        pages.append(discord.Embed(title='🎶 Sonus Help', color=color_int, description='(no commands)'))
    # add footer with page numbering (updated by view)
    return pages


class HelpPaginator(discord.ui.View):
    def __init__(self, pages: List[discord.Embed], timeout: float = PAGINATION_TIMEOUT):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    async def _update(self, interaction: discord.Interaction):
        page = self.pages[self.index]
        footer = f'Page {self.index+1}/{len(self.pages)}'
        page.set_footer(text=footer)
        try:
            await interaction.response.edit_message(embed=page, view=self)
        except Exception:
            try:
                await interaction.edit_original_response(embed=page, view=self)
            except Exception:
                pass

    @discord.ui.button(label='◀️', style=discord.ButtonStyle.secondary)
    async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.index = (self.index - 1) % len(self.pages)
        await self._update(interaction)

    @discord.ui.button(label='❌', style=discord.ButtonStyle.danger)
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(content='Help closed.', embed=None, view=None)
        except Exception:
            try:
                await interaction.edit_original_response(content='Help closed.', embed=None, view=None)
            except Exception:
                pass

    @discord.ui.button(label='▶️', style=discord.ButtonStyle.secondary)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.index = (self.index + 1) % len(self.pages)
        await self._update(interaction)


def register(bot: commands.Bot):
    # helper to extract help text from a command
    def _cmd_help_text(cmd: commands.Command) -> str:
        if cmd.help:
            return cmd.help
        doc = getattr(getattr(cmd, 'callback', None), '__doc__', None)
        if doc:
            return doc.strip().splitlines()[0]
        return 'No description provided.'

    # small emoji map for nicer section headers
    EMOJI_MAP = {
        'Music': '🎵',
        'Playlist': '📀',
        'Utility': '🛠️',
        'Owner': '🔒',
        'UI': '🎛️',
        'Database': '🗄️',
        'General': '📚'
    }

    # Short examples to show in detailed help where applicable
    EXAMPLES = {
        'play': 'S!play Never Gonna Give You Up',
        'pause': 'S!pause',
        'queue': 'S!queue',
        'settings-prefix': 'S!settings prefix !',
        'settings-color': 'S!settings color #1DB954',
        'playlist_add': 'S!playlist_add mylist https://youtu.be/...',
        'feedback': 'S!feedback I love Sonus!'
    }

    # -----------------------
    # Prefix command
    # -----------------------
    if bot.get_command('help') is None:
        @bot.command(
            name="help",
            help="Show help for commands. Optionally provide a command name for detailed help."
        )
        async def _help(ctx: commands.Context, command_name: str | None = None):
            settings = load_guild_settings(ctx.guild.id) if ctx.guild else {"prefix": "S!", "color": "#1DB954"}
            prefix = settings.get("prefix", "S!")
            color = settings.get("color", "#1DB954")
            color_int = int(color.lstrip("#"), 16) if isinstance(color, str) and color.startswith("#") else 0x1DB954

            # Populate missing command.help from docstring where possible
            for c in bot.commands:
                if not c.help:
                    doc = getattr(getattr(c, 'callback', None), '__doc__', None)
                    if doc:
                        c.help = doc.strip().splitlines()[0]

            # Detailed view for a single command
            if command_name:
                cmd = bot.get_command(command_name)
                if not cmd:
                    await ctx.send(f"Unknown command: `{command_name}`")
                    return

                e = discord.Embed(title=f"Help: {cmd.name}", color=color_int)
                e.add_field(name="Signature", value=f"{prefix}{cmd.name} {cmd.signature}".strip(), inline=False)
                e.add_field(name="Description", value=_cmd_help_text(cmd), inline=False)
                if cmd.aliases:
                    e.add_field(name="Aliases", value=', '.join(cmd.aliases), inline=False)
                # include a short example if known
                ex = EXAMPLES.get(cmd.name) or EXAMPLES.get(cmd.name.replace('-', '_'))
                if ex:
                    e.add_field(name="Example", value=f"`{ex}`", inline=False)
                await ctx.send(embed=e)
                return

            # Aggregate all visible prefix commands, grouped by cog
            cmds = [c for c in bot.commands if not c.hidden]
            grouped: dict[str, list[commands.Command]] = {}
            for c in sorted(cmds, key=lambda x: (x.cog_name or '', x.name)):
                key = c.cog_name or 'General'
                grouped.setdefault(key, []).append(c)

            # author & thumbnail
            try:
                author_name = str(bot.user)
                author_icon = bot.user.display_avatar.url
            except Exception:
                author_name = 'Sonus'
                author_icon = None

            # For large command sets use paginator
            pages = _build_help_pages(bot, prefix, color_int, EXAMPLES)
            # add author/thumbnail to first page only
            try:
                if pages and author_icon:
                    pages[0].set_author(name=author_name, icon_url=author_icon)
                    pages[0].set_thumbnail(url=author_icon)
            except Exception:
                pass

            if len(pages) == 1:
                pages[0].set_footer(text=f"Type {prefix}help <command> for details. Showing {len(cmds)} commands.")
                await ctx.send(embed=pages[0])
            else:
                view = HelpPaginator(pages)
                # set initial footer
                pages[0].set_footer(text=f'Page 1/{len(pages)}')
                await ctx.send(embed=pages[0], view=view)

    # -----------------------
    # Slash command
    # -----------------------
    if bot.tree.get_command('help') is None:
        @bot.tree.command(
            name="help",
            description="Show help for bot commands. Optionally provide a command name."
        )
        @app_commands.describe(command_name="Optional command name to show detailed help for")
        async def _help_slash(interaction: discord.Interaction, command_name: str | None = None):
            settings = load_guild_settings(interaction.guild.id) if interaction.guild else {"prefix": "S!", "color": "#1DB954"}
            prefix = settings.get("prefix", "S!")
            color = settings.get("color", "#1DB954")
            color_int = int(color.lstrip("#"), 16) if isinstance(color, str) and color.startswith("#") else 0x1DB954

            # Populate missing command.help from docstring where possible
            for c in bot.commands:
                if not c.help:
                    doc = getattr(getattr(c, 'callback', None), '__doc__', None)
                    if doc:
                        c.help = doc.strip().splitlines()[0]

            if command_name:
                cmd = bot.get_command(command_name)
                if not cmd:
                    await interaction.response.send_message(f"Unknown command: `{command_name}`", ephemeral=True)
                    return

                e = discord.Embed(title=f"Help: {cmd.name}", color=color_int)
                e.add_field(name="Signature", value=f"{prefix}{cmd.name} {cmd.signature}".strip(), inline=False)
                e.add_field(name="Description", value=_cmd_help_text(cmd), inline=False)
                if cmd.aliases:
                    e.add_field(name="Aliases", value=', '.join(cmd.aliases), inline=False)
                ex = EXAMPLES.get(cmd.name) or EXAMPLES.get(cmd.name.replace('-', '_'))
                if ex:
                    e.add_field(name="Example", value=f"`{ex}`", inline=False)
                await interaction.response.send_message(embed=e, ephemeral=True)
                return

            cmds = [c for c in bot.commands if not c.hidden]
            grouped: dict[str, list[commands.Command]] = {}
            for c in sorted(cmds, key=lambda x: (x.cog_name or '', x.name)):
                key = c.cog_name or 'General'
                grouped.setdefault(key, []).append(c)

            # author & thumbnail
            try:
                author_name = str(bot.user)
                author_icon = bot.user.display_avatar.url
            except Exception:
                author_name = 'Sonus'
                author_icon = None

            e = discord.Embed(title="🎶 Sonus Help", color=color_int, timestamp=discord.utils.utcnow())
            if author_icon:
                e.set_author(name=author_name, icon_url=author_icon)
                e.set_thumbnail(url=author_icon)

            # For large command sets use paginator
            pages = _build_help_pages(bot, prefix, color_int, EXAMPLES)
            try:
                if pages and author_icon:
                    pages[0].set_author(name=author_name, icon_url=author_icon)
                    pages[0].set_thumbnail(url=author_icon)
            except Exception:
                pass

            if len(pages) == 1:
                pages[0].set_footer(text=f"Type {prefix}help <command> for details. Showing {len(cmds)} commands.")
                await interaction.response.send_message(embed=pages[0], ephemeral=True)
            else:
                view = HelpPaginator(pages)
                pages[0].set_footer(text=f'Page 1/{len(pages)}')
                await interaction.response.send_message(embed=pages[0], view=view, ephemeral=True)
    else:
        logger.info("Slash help command already exists; skipping registration")