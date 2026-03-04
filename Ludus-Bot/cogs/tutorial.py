"""
cogs/tutorial.py - Interactive bilingual tutorial for Ludus.
Languages: EN English / PL Polski
Translations loaded from: language/tutorial.json
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

# ---------------------------------------------------------
#  Translation loader
# ---------------------------------------------------------

_LANG_DIR = Path(__file__).parent.parent / "language"
_LANGS: dict = {}

def _load_langs() -> None:
    global _LANGS
    path = _LANG_DIR / "tutorial.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Map each top-level language key to {"tutorial": <content>}
        # so the rest of the cog can access _LANGS[lang]["tutorial"][...]
        for code, content in data.items():
            _LANGS[code] = {"tutorial": content}
    else:
        _LANGS = {"en": {}, "pl": {}}

_load_langs()

def _t(lang: str, *keys: str, **fmt) -> str:
    """Deep-get a translation key, fall back to English."""
    data = _LANGS.get(lang, {})
    for k in keys:
        if not isinstance(data, dict):
            break
        data = data.get(k, {})
    if isinstance(data, dict):
        data = _LANGS.get("en", {})
        for k in keys:
            if not isinstance(data, dict):
                break
            data = data.get(k, {})
    result = str(data) if not isinstance(data, dict) else ".".join(keys)
    return result.format(**fmt) if fmt else result


# ---------------------------------------------------------
#  Constants
# ---------------------------------------------------------

PAGES = [
    "welcome", "economy", "gambling", "cards", "games",
    "mining", "farming", "business", "social", "achievements", "wizardwars",
    "profile", "quickstart",
]

_COLOR_MAP = {
    "PRIMARY": discord.Color.blurple(),
    "SUCCESS": discord.Color.green(),
    "WARNING": discord.Color.gold(),
    "ERROR":   discord.Color.red(),
}


# ---------------------------------------------------------
#  Embed builder
# ---------------------------------------------------------

def _build_embed(lang: str, page: str, page_num: int) -> discord.Embed:
    data = _LANGS.get(lang, {}).get("tutorial", {}).get("pages", {}).get(page)
    if not data:
        data = _LANGS.get("en", {}).get("tutorial", {}).get("pages", {}).get(page, {})

    color_key = data.get("color", "PRIMARY")
    color = _COLOR_MAP.get(color_key, discord.Color.blurple())

    embed = discord.Embed(
        title=data.get("title", page.capitalize()),
        description=data.get("description", ""),
        color=color,
    )

    for field in data.get("fields", []):
        embed.add_field(
            name=field.get("name", "\u200b"),
            value=field.get("value", "\u200b"),
            inline=field.get("inline", False),
        )

    total = len(PAGES)
    footer_tpl = _t(lang, "tutorial", "footer_page")
    page_info = footer_tpl.format(page=page_num, total=total)
    raw_footer = data.get("footer", "")
    embed.set_footer(text=f"{raw_footer}  |  {page_info}" if raw_footer else page_info)

    lang_name = _t(lang, "tutorial", "lang_name")
    embed.set_author(name=f"Ludus Tutorial  [{lang_name}]")
    return embed


# ---------------------------------------------------------
#  View
# ---------------------------------------------------------

class TutorialView(discord.ui.View):
    """
    Bilingual interactive tutorial with:
      * Language toggle (EN / PL)
      * Prev / Next navigation buttons
      * Section dropdown for quick jump
    """

    def __init__(self, user, lang: str = "en"):
        super().__init__(timeout=300)
        self.user = user
        self.lang = lang
        self.page = "welcome"
        self._refresh_components()

    # -- helpers -------------------------------------------

    @property
    def page_index(self) -> int:
        try:
            return PAGES.index(self.page)
        except ValueError:
            return 0

    def _refresh_components(self) -> None:
        self.clear_items()

        # Row 0 - Language buttons
        btn_en = discord.ui.Button(
            label="English",
            emoji="🇬🇧",
            style=discord.ButtonStyle.primary if self.lang == "en" else discord.ButtonStyle.secondary,
            custom_id="lang_en",
            row=0,
        )
        btn_en.callback = self._lang_en
        self.add_item(btn_en)

        btn_pl = discord.ui.Button(
            label="Polski",
            emoji="🇵🇱",
            style=discord.ButtonStyle.primary if self.lang == "pl" else discord.ButtonStyle.secondary,
            custom_id="lang_pl",
            row=0,
        )
        btn_pl.callback = self._lang_pl
        self.add_item(btn_pl)

        # Row 1 - Prev / Next
        idx = self.page_index
        btn_prev = discord.ui.Button(
            label=_t(self.lang, "tutorial", "btn_prev"),
            style=discord.ButtonStyle.secondary,
            custom_id="nav_prev",
            disabled=(idx == 0),
            row=1,
        )
        btn_prev.callback = self._nav_prev
        self.add_item(btn_prev)

        btn_next = discord.ui.Button(
            label=_t(self.lang, "tutorial", "btn_next"),
            style=discord.ButtonStyle.secondary,
            custom_id="nav_next",
            disabled=(idx == len(PAGES) - 1),
            row=1,
        )
        btn_next.callback = self._nav_next
        self.add_item(btn_next)

        # Row 2 - Section dropdown
        options = []
        for p in PAGES:
            nav_label = _t(self.lang, "tutorial", "nav", p)
            nav_desc  = _t(self.lang, "tutorial", "nav_desc", p)
            options.append(
                discord.SelectOption(
                    label=nav_label[:100],
                    value=p,
                    description=nav_desc[:100],
                    default=(p == self.page),
                )
            )

        select = discord.ui.Select(
            placeholder=_t(self.lang, "tutorial", "nav_placeholder"),
            options=options,
            custom_id="section_select",
            row=2,
        )
        select.callback = self._section_select
        self.add_item(select)

    def _make_embed(self) -> discord.Embed:
        return _build_embed(self.lang, self.page, self.page_index + 1)

    async def _guard(self, interaction: discord.Interaction) -> bool:
        user_id = self.user.id if hasattr(self.user, "id") else None
        if user_id and interaction.user.id != user_id:
            await interaction.response.send_message(
                _t(self.lang, "tutorial", "no_perm"), ephemeral=True
            )
            return False
        return True

    async def _update(self, interaction: discord.Interaction) -> None:
        self._refresh_components()
        await interaction.response.edit_message(embed=self._make_embed(), view=self)

    # -- callbacks -----------------------------------------

    async def _lang_en(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        self.lang = "en"
        await self._update(interaction)

    async def _lang_pl(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        self.lang = "pl"
        await self._update(interaction)

    async def _nav_prev(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        self.page = PAGES[max(0, self.page_index - 1)]
        await self._update(interaction)

    async def _nav_next(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        self.page = PAGES[min(len(PAGES) - 1, self.page_index + 1)]
        await self._update(interaction)

    async def _section_select(self, interaction: discord.Interaction):
        if not await self._guard(interaction):
            return
        self.page = interaction.data["values"][0]
        await self._update(interaction)

    async def on_timeout(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True


# ---------------------------------------------------------
#  Cog
# ---------------------------------------------------------

class Tutorial(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tutorial", aliases=["guide2", "tut"])
    async def tutorial_command(self, ctx: commands.Context, lang: str = "en"):
        """Interactive bilingual tutorial.
        Usage: L!tutorial [en|pl]
        """
        lang = lang.lower() if lang.lower() in _LANGS else "en"
        view = TutorialView(user=ctx.author, lang=lang)
        await ctx.send(embed=view._make_embed(), view=view)

    @app_commands.command(
        name="tutorial",
        description="📖 Interactive bilingual Ludus tutorial [EN/PL]",
    )
    @app_commands.describe(language="Choose tutorial language (default: English)")
    @app_commands.choices(language=[
        app_commands.Choice(name="🇬🇧 English", value="en"),
        app_commands.Choice(name="🇵🇱 Polski",  value="pl"),
    ])
    async def tutorial_slash(
        self,
        interaction: discord.Interaction,
        language: app_commands.Choice[str] = None,
    ):
        """Slash command for bilingual tutorial."""
        lang = language.value if language else "en"
        view = TutorialView(user=interaction.user, lang=lang)
        await interaction.response.send_message(embed=view._make_embed(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tutorial(bot))
