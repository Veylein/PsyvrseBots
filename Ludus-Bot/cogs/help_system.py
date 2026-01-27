from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
from typing import List

CAT_LIST = [
    ("Economy", "💰"), ("Gambling", "🎰"), ("Board Games", "🎲"),
    ("Card Games", "🃏"), ("Minigames", "🎮"), ("Puzzle Games", "🧩"),
    ("Arcade", "👾"), ("Fishing+", "🎣"), ("Farming", "🚜"),
    ("Social", "👥"), ("Pets", "🐾"), ("Profile", "👤"), ("Admin", "⚡"), ("Owner", "👑")
]


class HelpView(discord.ui.View):
    def __init__(self, pages: List[discord.Embed], timeout: int = 120):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    def current(self):
        return self.pages[self.index]

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, b, i):
        self.index = (self.index - 1) % len(self.pages)
        await i.response.edit_message(embed=self.current(), view=self)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def next(self, b, i):
        self.index = (self.index + 1) % len(self.pages)
        await i.response.edit_message(embed=self.current(), view=self)


class HelpSystem(commands.Cog):
    """Unified help system: prefix + slash scaffold."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Use a distinct group name to avoid colliding with other `/help` registrations
    help_group = app_commands.Group(name="help_cat", description="Help and documentation")

    async def help_prefix(self, ctx, *, category: str = None):
        if not category:
            await ctx.send(embed=self._category_list_embed())
            return

        # Debug: show incoming category
        print(f"[HELP_SYSTEM debug] Received prefix help request: '{category}' from {ctx.author}")

        # If the richer Help cog exists, delegate to it for detailed category command lists
        help_cog = self.bot.get_cog('Help')
        if help_cog is not None:
            try:
                print(f"[HELP_SYSTEM debug] Delegating prefix help for '{category}' to Help cog")
                is_owner = ctx.author.id in getattr(self.bot, 'owner_ids', [])
                await help_cog._send_category_help(ctx, category.lower(), is_owner, is_slash=False)
                return
            except Exception as e:
                import traceback
                print(f"[HELP_SYSTEM debug] Delegation to Help cog failed: {e}")
                traceback.print_exc()

        # Fallback behaviour
        await ctx.send(embed=self._category_detail_embed(category.title()))

    @help_group.command(name="main", description="Show help categories or a specific category")
    async def help_main(self, interaction: discord.Interaction, category: str = None):
        # If no category supplied, show categories list
        if not category:
            await interaction.response.send_message(embed=self._category_list_embed(), ephemeral=True)
            return
        await interaction.response.send_message(embed=self._category_detail_embed_dynamic(category.title(), interaction.client), ephemeral=True)

    @help_main.autocomplete('category')
    async def _help_category_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [app_commands.Choice(name=name, value=name) for name, _ in CAT_LIST if current.lower() in name.lower()]
        return choices[:25]

    def _category_list_embed(self) -> discord.Embed:
        e = discord.Embed(title="Ludus Help — Categories", color=discord.Color.blurple())
        lines = [f"{emoji} **{name}**" for name, emoji in CAT_LIST]
        e.description = "\n".join(lines)
        e.set_footer(text="Use L!help <category> or /help main category:<name> to view commands")
        return e

    def _category_detail_embed(self, category: str) -> discord.Embed:
        e = discord.Embed(title=f"Help — {category}", color=discord.Color.green())
        e.add_field(name="Overview", value=f"Commands and guides for {category}.")
        e.add_field(name="How to use", value="Use `L!<command>` or `/` slash equivalents.")
        e.set_footer(text="Contact the server owner for custom configs")
        return e

    def _category_detail_embed_dynamic(self, category: str, bot: commands.Bot) -> discord.Embed:
        # Attempt to build a command list from cogs or known categories
        e = discord.Embed(title=f"Help — {category}", color=discord.Color.green())
        lines = []
        lower_cat = category.lower()
        for cog_name, cog in bot.cogs.items():
            if lower_cat in cog_name.lower():
                for cmd in cog.get_commands():
                    help_text = getattr(cmd, 'help', '') or ''
                    lines.append(f"`{cmd.name}` — {help_text}")

        e.description = "\n".join(lines) if lines else "No commands found for this category."
        return e


async def setup(bot: commands.Bot):
    if bot.get_cog('HelpSystem') is not None:
        return
    await bot.add_cog(HelpSystem(bot))
    # Do not register a prefix 'help' command here to avoid conflicting
    # with a dedicated Help cog that provides a richer implementation.
