import discord
from discord.ext import commands
from discord import app_commands


PAGES = [
    {
        "title": "\U0001f3ae Welcome to Ludus \u2014 The Ultimate Discord MMO",
        "description": (
            "Ludus is a full-featured Discord bot packed with games, economy, social systems, and server-wide events.\n\n"
            "**What's inside:**\n"
            "\U0001f4b0 Deep economy with coins, shops & sub-currencies\n"
            "\U0001f3b2 50+ games \u2014 board, card, casino, arcade, puzzle\n"
            "\U0001f3a3\u26cf\ufe0f\U0001f69c Fishing, Mining & Farming simulators\n"
            "\U0001f43e Adoptable pets with real gameplay bonuses\n"
            "\u2694\ufe0f DnD-style RPG (Infinity Adventure)\n"
            "\U0001f30d Cross-server Global Events\n"
            "\U0001f4dc Daily quests & achievement system\n\n"
            "Use `L!help` or `/help` to explore all commands."
        ),
        "color": discord.Color.gold(),
    },
    {
        "title": "\U0001f4b0 Economy & Shop",
        "description": (
            "**Earning PsyCoins:**\n"
            "\u2022 `L!daily` \u2014 300\u20132000+ coins + streak bonus + pet bonus\n"
            "\u2022 Win minigames, gambling, fishing, farming, mining\n"
            "\u2022 Complete quests and achievements\n"
            "\u2022 Participate in global events\n\n"
            "**Spending:**\n"
            "\u2022 `L!shop` \u2014 Browse the item shop\n"
            "\u2022 Upgrade fishing rods, mining pickaxes, farm tools\n"
            "\u2022 Buy card deck cosmetics, boosts, pet access\n\n"
            "**Sub-currencies:** FishCoins \U0001f41f, MineCoins \u26cf\ufe0f, FarmCoins \U0001f33e\n"
            "Convert them: `L!convert <amount> <currency>`\n\n"
            "\U0001f4ca `L!balance` \u00b7 `L!leaderboard` \u00b7 `L!inventory`"
        ),
        "color": discord.Color.green(),
    },
    {
        "title": "\U0001f3b0 Gambling & Casino",
        "description": (
            "All games support bets from **10 to 10,000** coins.\n\n"
            "**Games:**\n"
            "\u2022 `/slots` \u2014 Spin the slot machine\n"
            "\u2022 `/blackjack` \u2014 Beat the dealer at 21\n"
            "\u2022 `/poker` \u2014 Texas Hold'em vs dealer\n"
            "\u2022 `/crash` \u2014 Cash out before it crashes\n"
            "\u2022 `/mines` \u2014 Minesweeper gambling (1\u201324 mines)\n"
            "\u2022 `/roulette` \u2014 Red, black, or number\n"
            "\u2022 `/coinflip` \u2014 50/50 double-or-nothing\n"
            "\u2022 `/dice` \u2014 Bet on a number\n\n"
            "\U0001f4c8 `/odds` \u2014 See win rates   \u2022   `/gambling_stats` \u2014 Your history\n"
            "\u26a0\ufe0f Gamble responsibly!"
        ),
        "color": discord.Color.from_rgb(255, 165, 0),
    },
    {
        "title": "\U0001f3a3\u26cf\ufe0f\U0001f69c Fishing \u00b7 Mining \u00b7 Farming",
        "description": (
            "**\U0001f3a3 Fishing:**\n"
            "Cast your line across 5 areas (pond \u2192 ocean \u2192 trench).\n"
            "Upgrade rods, unlock bait, collect rare fish.\n"
            "`/fish cast` \u00b7 `/fish shop` \u00b7 `/fish stats`\n\n"
            "**\u26cf\ufe0f Mining:**\n"
            "Explore a 2D world map. Dig for coal, iron, gold, diamond, emerald.\n"
            "Upgrade pickaxes, sell ores, share world with server.\n"
            "`/mine` \u00b7 guild config: `shared_mining_world`\n\n"
            "**\U0001f69c Farming:**\n"
            "Plant, water, harvest crops across seasons.\n"
            "Keep animals, breed hybrids, decorate your farm.\n"
            "`/farm view` \u00b7 `/farm plant <crop>` \u00b7 `/farm harvest`\n\n"
            "\U0001f43e **Pets boost all three!** Hungry pets can damage crops."
        ),
        "color": discord.Color.from_rgb(139, 195, 74),
    },
    {
        "title": "\U0001f3b2 Board & Card Games",
        "description": (
            "**Board Games:**\n"
            "\u2022 Tic-Tac-Toe (minimax AI, 3x3/4x4/5x5)\n"
            "\u2022 Connect 4, Hangman, Scrabble, Backgammon, Tetris\n"
            "\u2022 Chess \u265f\ufe0f (PIL rendered, 6 themes, bot AI)\n"
            "\u2022 Checkers (king moves, multi-jump)\n"
            "\u2022 Monopoly \U0001f3a9 (28 properties, houses/hotels, 2\u20136 players)\n\n"
            "**Card Games:**\n"
            "\u2022 UNO \U0001f0cf (Classic, Flip, No Mercy, 2\u201310 players)\n"
            "\u2022 Blackjack, Poker, Go Fish, War, Solitaire, Crazy Eights\n\n"
            "**Prefix:** `L!chess @user` \u00b7 `L!ttt` \u00b7 `/monopoly start`\n"
            "All games award **PsyCoins** on win!"
        ),
        "color": discord.Color.blue(),
    },
    {
        "title": "\u2694\ufe0f RPG \u2014 Infinity Adventure & Wizard Wars",
        "description": (
            "**\U0001f5fa\ufe0f Infinity Adventure (DnD-style):**\n"
            "A full narrative RPG with 9 gate dimensions.\n"
            "Create a character (Warrior/Mage/Rogue/Healer), explore rooms,\n"
            "fight enemies, find artefacts, survive death.\n"
            "Bilingual (EN/PL) \u2014 persistent save per user.\n"
            "`/dnd start`\n\n"
            "**\U0001f9d9 Wizard Wars:**\n"
            "32 spells across 4 schools (Elemental, Cosmic, Forbidden, Divine).\n"
            "6 spell combos \u2014 e.g. Gravity Well + Black Hole \u2192 Singularity.\n"
            "Duel other wizards, conquer territories, earn Gold.\n"
            "`/wizardwars`\n\n"
            "**\U0001f4dc Daily Quests & Achievements:**\n"
            "`L!quests` \u00b7 `L!achievements` \u2014 earn coins + TCG card rewards"
        ),
        "color": discord.Color.dark_purple(),
    },
    {
        "title": "\U0001f30d Global Events",
        "description": (
            "Events are **cross-server** \u2014 all guilds participate at once!\n\n"
            "**\u2694\ufe0f Faction War** `L!event war [hours]`\n"
            "Join one of 4 factions (iron/ash/void/sky).\n"
            "Earn war points by winning games. Winning faction: **10k coins**.\n"
            "`L!joinfaction <name>` \u00b7 `L!warleaderboard`\n\n"
            "**\U0001f409 World Boss** `L!event worldboss [boss]`\n"
            "Shared global HP across ALL servers.\n"
            "Click \u2694\ufe0f Attack! or `L!attack` (30s cooldown).\n"
            "Rewards: 5k base + damage bonus + top-10 bonus + 15k last-hit.\n"
            "`L!bossstats`\n\n"
            "**\U0001f3af Target Hunt** `L!event hunt [minutes]`\n"
            "Random challenges broadcast to every server.\n"
            "Speed completions = points for your server."
        ),
        "color": discord.Color.red(),
    },
    {
        "title": "\U0001f43e Pets & Social",
        "description": (
            "**Pets (16 species, 5 rarities):**\n"
            "Adopt a pet with `L!pet adopt` (first one free).\n"
            "Feed, play, walk \u2014 neglect causes hunger & sadness.\n"
            "Pets provide real bonuses: fishing multiplier, mining XP,\n"
            "farm yield, daily coins bonus, gambling luck, and more.\n"
            "Hungry pets (<40%) can **damage your farm crops**!\n\n"
            "**Social:**\n"
            "\u2022 `L!marry @user` \u2014 Propose (10k coins)\n"
            "\u2022 `L!bank` \u2014 Shared bank with spouse\n"
            "\u2022 `L!rep give @user` \u2014 Give reputation (24h cooldown)\n"
            "\u2022 `/hug` `/kiss` `/slap` `/ship` \u2014 Anime GIF reactions\n"
            "\u2022 `L!roast` \u00b7 `L!compliment` \u00b7 `L!pray` \u00b7 `L!curse`\n\n"
            "\U0001f4ca `L!profile` \u2014 4-page stats: Overview/Gaming/Economy/Social"
        ),
        "color": discord.Color.from_rgb(255, 100, 150),
    },
    {
        "title": "\U0001f4a1 Tips & Quick Start",
        "description": (
            "**First 5 minutes:**\n"
            "1. `L!daily` \u2014 grab your free daily coins\n"
            "2. `L!balance` \u2014 check your wallet\n"
            "3. `L!shop` \u2014 browse what you can buy\n"
            "4. `/fish cast` \u2014 try fishing (free to start)\n"
            "5. `L!quests` \u2014 pick up a daily quest\n\n"
            "**Efficient earning:**\n"
            "\u2022 Daily streak bonus doubles at 7 days\n"
            "\u2022 Fish in higher areas for rare catches\n"
            "\u2022 Participate in every global event\n"
            "\u2022 Pets multiply almost every reward type\n\n"
            "**Commands:** `L!help` \u00b7 `/help [category]`\n"
            "**Prefix:** `L!`  \u00b7  **Slash:** `/`\n\n"
            "\U0001f31f **Have fun \u2014 that's what Ludus is about!**"
        ),
        "color": discord.Color.gold(),
    },
]


class AboutView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.page = 0

    def build_embed(self) -> discord.Embed:
        p = PAGES[self.page]
        embed = discord.Embed(
            title=p["title"],
            description=p["description"],
            color=p["color"]
        )
        embed.set_footer(text=f"Page {self.page + 1} / {len(PAGES)}  \u00b7  Ludus Bot")
        self._update_buttons()
        return embed

    def _update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page == len(PAGES) - 1

    async def _check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn't your guide!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="\u25c4 Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check(interaction):
            return
        self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next \u25ba", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check(interaction):
            return
        self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="\u2715 Close", style=discord.ButtonStyle.danger)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check(interaction):
            return
        await interaction.message.delete()
        self.stop()


class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_dm(self, user: discord.User | discord.Member, ctx_or_interaction):
        view = AboutView(user.id)
        embed = view.build_embed()
        is_slash = isinstance(ctx_or_interaction, discord.Interaction)
        try:
            dm = await user.create_dm()
            await dm.send(embed=embed, view=view)
            msg = "\U0001f4ec Check your DMs for the interactive Ludus guide!"
            if is_slash:
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
        except discord.Forbidden:
            msg = "\u274c I couldn't DM you! Please enable DMs from server members, then try again."
            if is_slash:
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)

    @commands.command(name="about")
    async def about_prefix(self, ctx):
        """Interactive guide to Ludus sent to your DMs."""
        await self._send_dm(ctx.author, ctx)

    @app_commands.command(name="about", description="Get an interactive guide to everything Ludus has to offer (sent to DMs)")
    async def about_slash(self, interaction: discord.Interaction):
        await self._send_dm(interaction.user, interaction)


async def setup(bot):
    await bot.add_cog(About(bot))