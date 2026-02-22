"""
CardGames — War (prefix L!war) + Go Fish (/gofish)
War:    simple 1v1 card flip, no betting, no disclaimer, prefix only
GoFish: in-channel vs bot, PIL hand images, rank-select dropdown, slash only
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import sys
import os
from typing import Optional
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.card_visuals import create_hand_image, create_war_image

try:
    from utils.stat_hooks import us_inc as _inc, us_mg as _mg
except Exception:
    _inc = _mg = None


# ── Constants ──────────────────────────────────────────────────────────────────

# War
WAR_CARD_VALUES = {
    "A": 14, "K": 13, "Q": 12, "J": 11, "10": 10,
    "9": 9, "8": 8, "7": 7, "6": 6, "5": 5, "4": 4, "3": 3, "2": 2,
}

# Go Fish
GF_RANK_ORDER = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

GF_RULES = (
    "**🎣 How to Play Go Fish**\n\n"
    "• Each player starts with **7 cards**.\n"
    "• On your turn, **ask the bot** for a rank you hold in your hand.\n"
    "• If the bot has it → you get the cards and **go again**.\n"
    "• If not → **Go Fish!** Draw the top card from the deck.\n"
    "  ‣ If you drew the rank you asked for → go again!\n"
    "• Collect **4-of-a-kind** to complete a 📗 book (+1 point).\n"
    "• Game ends when the deck is empty **and** a hand runs out.\n"
    "• **Most books wins!** 🏆"
)


# ── Shared card helpers ────────────────────────────────────────────────────────

def _build_deck() -> list:
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    deck = [f"{r}{s}" for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def _rank(card: str) -> str:
    return card[:-1] if card else ""


def _fmt(card: str) -> str:
    """Convert ♠/♥/♦/♣ → s/h/d/c for card_visuals."""
    for sym, ch in {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}.items():
        if sym in card:
            return card.replace(sym, ch)
    return card


def _war_val(card: str) -> int:
    return WAR_CARD_VALUES.get(_rank(card), 0)


# ── Go Fish helpers ────────────────────────────────────────────────────────────

def _check_books(hand: list) -> tuple:
    """Return (completed_book_ranks, remaining_hand)."""
    cnt = Counter(_rank(c) for c in hand)
    books = [r for r, n in cnt.items() if n >= 4]
    new_hand = [c for c in hand if _rank(c) not in books]
    return books, new_hand


def _bot_ask_rank(bot_hand: list) -> Optional[str]:
    if not bot_hand:
        return None
    cnt = Counter(_rank(c) for c in bot_hand)
    return cnt.most_common(1)[0][0]


def _gf_game_over(state: dict) -> bool:
    return (
        len(state["deck"]) == 0
        and (len(state["player_hand"]) == 0 or len(state["bot_hand"]) == 0)
    ) or (len(state["player_hand"]) == 0 and len(state["bot_hand"]) == 0)


# ── War Views ──────────────────────────────────────────────────────────────────

class WarChallengeView(discord.ui.View):
    """Challenge accept/decline — opponent must accept before game starts."""

    def __init__(self, cog, challenger, opponent: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="⚔️ Accept", style=discord.ButtonStyle.success)
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ This challenge isn't for you!", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"✅ {self.opponent.display_name} accepted! Let the War begin!",
            embed=None, view=self
        )
        self.stop()
        await self.cog._war_play_rounds(interaction, self.challenger, self.opponent)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.opponent.id, self.challenger.id):
            await interaction.response.send_message("❌ Not your challenge!", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="❌ Challenge declined.", embed=None, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class WarPlayAgainView(discord.ui.View):
    """Play Again after 10-round war — challenger only."""

    def __init__(self, cog, challenger_id: int, opponent: Optional[discord.Member]):
        super().__init__(timeout=120)
        self.cog = cog
        self.challenger_id = challenger_id
        self.opponent = opponent

    @discord.ui.button(label="⚔️ Play Again", style=discord.ButtonStyle.success)
    async def play_again_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenger_id:
            await interaction.response.send_message("❌ Only the original challenger can rematch!", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog._war_play_rounds(interaction, interaction.user, self.opponent)


# ── Go Fish Views ──────────────────────────────────────────────────────────────

class GoFishPlayAgainView(discord.ui.View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id

    @discord.ui.button(label="Play Again 🎣", style=discord.ButtonStyle.success, row=0)
    async def play_again_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog._gf_start_game(interaction)

    @discord.ui.button(label="📋 Rules", style=discord.ButtonStyle.secondary, row=0)
    async def rules_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎣 Go Fish — Rules", description=GF_RULES, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GoFishRankDropdown(discord.ui.Select):
    def __init__(self, cog, user_id: int, ranks: list):
        self.cog = cog
        self.user_id = user_id
        options = [
            discord.SelectOption(label=r, description=f"Ask the bot for {r}s", emoji="🃏")
            for r in ranks[:25]
        ]
        super().__init__(
            placeholder="🃏 Pick a rank to ask for…",
            options=options,
            custom_id="gf_rank",
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your turn!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.cog._gf_player_ask(interaction, self.values[0])


class GoFishActionView(discord.ui.View):
    def __init__(self, cog, user_id: int, state: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        ranks = sorted(
            set(_rank(c) for c in state["player_hand"]),
            key=lambda r: GF_RANK_ORDER.index(r) if r in GF_RANK_ORDER else 99,
        )
        if ranks:
            self.add_item(GoFishRankDropdown(cog, user_id, ranks))

    @discord.ui.button(label="👁 View Hand", style=discord.ButtonStyle.secondary, row=1)
    async def view_hand_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        state = self.cog.active_gofish.get(self.user_id)
        if not state:
            await interaction.response.send_message("❌ Game not found!", ephemeral=True)
            return
        hand = state["player_hand"]
        if not hand:
            await interaction.response.send_message("🃏 Your hand is empty!", ephemeral=True)
            return
        deck = self.cog.get_user_deck(self.user_id)
        img = await asyncio.to_thread(create_hand_image, [_fmt(c) for c in hand], "Your Hand", deck)
        embed = discord.Embed(
            title="🃏 Your Hand",
            description=f"**{len(hand)} card(s)** — Books: **{len(state['player_books'])}** 📗",
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://hand.png")
        await interaction.response.send_message(embed=embed, file=img, ephemeral=True)

    @discord.ui.button(label="📋 Rules", style=discord.ButtonStyle.secondary, row=1)
    async def rules_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎣 Go Fish — Rules", description=GF_RULES, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── Cog ────────────────────────────────────────────────────────────────────────

class CardGames(commands.Cog):
    """🎴 Card games: War (L!war) and Go Fish (/gofish)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_gofish: dict = {}  # user_id → state

    # ─── shared helper ─────────────────────────────────────────────────────────

    def get_user_deck(self, user_id: int) -> str:
        try:
            eco = self.bot.get_cog("Economy")
            if eco:
                return eco.get_user_card_deck(user_id)
        except Exception:
            pass
        return "classic"

    # ═════════════════════════════════════════════════════════════════════════
    #  WAR — prefix only, 10 rounds, acceptance required vs players
    # ═════════════════════════════════════════════════════════════════════════

    @commands.command(name="war", aliases=["cardwar"])
    async def war_prefix(self, ctx, opponent: Optional[discord.Member] = None):
        """⚔️ 10-round War — most round wins takes glory! (no coins lost)"""
        if opponent:
            if opponent.bot or opponent.id == ctx.author.id:
                await ctx.send("❌ You can't challenge yourself or another bot!")
                return
            embed = discord.Embed(
                title="⚔️ War Challenge!",
                description=(
                    f"{ctx.author.mention} challenges {opponent.mention} to a **10-round War**!\n\n"
                    "*Each round you both flip a card — highest card wins the round.*\n"
                    "*Most rounds won takes glory. No coins lost — just pride!*"
                ),
                color=discord.Color.gold(),
            )
            embed.set_footer(text="Challenge expires in 60 seconds")
            view = WarChallengeView(self, ctx.author, opponent)
            await ctx.send(content=opponent.mention, embed=embed, view=view)
        else:
            # vs bot — play immediately
            await self._war_play_rounds(ctx, ctx.author, None)

    async def _war_play_rounds(self, ctx_or_interaction, challenger, opponent: Optional[discord.Member]):
        ROUNDS = 10
        p_score = 0
        b_score = 0
        ties = 0
        opp_name = opponent.display_name if opponent else "Bot"
        opp_icon = "👤" if opponent else "🤖"
        round_log = []
        p_deck = self.get_user_deck(challenger.id)
        b_deck = self.get_user_deck(opponent.id) if opponent else "classic"

        # Send initial message (placeholder image first round)
        first_deck = _build_deck()
        first_p = first_deck.pop()
        first_b = first_deck.pop()
        first_img = await asyncio.to_thread(
            create_war_image,
            _fmt(first_p), _fmt(first_b),
            challenger.display_name, opp_name,
            deck=p_deck, result_text="Round 1...", opponent_deck=b_deck,
        )
        first_embed = discord.Embed(
            title=f"⚔️ War — {challenger.display_name} vs {opp_name}",
            description="⏳ Flipping cards...",
            color=discord.Color.gold(),
        )
        first_embed.set_image(url="attachment://war.png")
        first_embed.set_footer(text=f"Round 0 / {ROUNDS}")

        if isinstance(ctx_or_interaction, commands.Context):
            msg = await ctx_or_interaction.send(embed=first_embed, file=first_img)
        else:
            msg = await ctx_or_interaction.followup.send(embed=first_embed, file=first_img, wait=True)

        # Play rounds
        for rnd in range(1, ROUNDS + 1):
            deck = _build_deck()
            p_card = deck.pop()
            b_card = deck.pop()
            p_val = _war_val(p_card)
            b_val = _war_val(b_card)

            if p_val > b_val:
                p_score += 1
                icon = "🟢"
                result = f"{challenger.display_name} wins"
                result_txt = f"{challenger.display_name} WINS"
                round_color = discord.Color.green()
            elif b_val > p_val:
                b_score += 1
                icon = "🔴"
                result = f"{opp_name} wins"
                result_txt = f"{opp_name} WINS"
                round_color = discord.Color.red()
            else:
                ties += 1
                icon = "🟡"
                result = "Tie"
                result_txt = "TIE"
                round_color = discord.Color.gold()

            round_log.append(f"{icon} R{rnd}: **{p_card}** vs **{b_card}** — {result}")

            # Generate card image for this round
            war_img = await asyncio.to_thread(
                create_war_image,
                _fmt(p_card), _fmt(b_card),
                challenger.display_name, opp_name,
                deck=p_deck, result_text=result_txt, opponent_deck=b_deck,
            )

            embed = discord.Embed(
                title=f"⚔️ War — {challenger.display_name} vs {opp_name}",
                color=round_color,
            )
            embed.add_field(
                name="📊 Score",
                value=(
                    f"🧑 **{challenger.display_name}**: {p_score}\n"
                    f"{opp_icon} **{opp_name}**: {b_score}\n"
                    f"🟡 Ties: {ties}"
                ),
                inline=True,
            )
            embed.add_field(
                name="📜 Last Rounds",
                value="\n".join(round_log[-5:]),
                inline=True,
            )
            embed.set_image(url="attachment://war.png")
            embed.set_footer(text=f"Round {rnd} / {ROUNDS}")
            await msg.edit(embed=embed, attachments=[war_img])
            if rnd < ROUNDS:
                await asyncio.sleep(1.5)

        # Final result
        if p_score > b_score:
            title = f"🏆 {challenger.display_name} Wins the War!"
            color = discord.Color.green()
            outcome = "win"
        elif b_score > p_score:
            title = f"🏆 {opp_name} Wins the War!"
            color = discord.Color.red()
            outcome = "lose"
        else:
            title = "⚔️ Perfect Draw!"
            color = discord.Color.gold()
            outcome = "draw"

        # Stats
        if _mg:
            try:
                _mg(challenger.id, "war", outcome, 0)
                _inc(challenger.id, "war_played")
                if outcome == "win":
                    _inc(challenger.id, "war_wins")
                elif outcome == "lose":
                    _inc(challenger.id, "war_losses")
                if opponent:
                    opp_out = "lose" if outcome == "win" else ("win" if outcome == "lose" else "draw")
                    _mg(opponent.id, "war", opp_out, 0)
                    _inc(opponent.id, "war_played")
            except Exception:
                pass

        # Final summary image — last round's cards stay visible
        final_img = await asyncio.to_thread(
            create_war_image,
            _fmt(p_card), _fmt(b_card),
            challenger.display_name, opp_name,
            deck=p_deck, result_text=title.replace(f"🏆 ", "").replace(" Wins the War!", " WINS").replace("Perfect Draw!", "DRAW"),
            opponent_deck=b_deck,
        )

        embed = discord.Embed(title=title, color=color)
        embed.add_field(
            name="🏅 Final Score",
            value=(
                f"🧑 **{challenger.display_name}**: {p_score} round wins\n"
                f"{opp_icon} **{opp_name}**: {b_score} round wins\n"
                f"🟡 Ties: {ties}"
            ),
            inline=True,
        )
        embed.add_field(
            name="📜 All Rounds",
            value="\n".join(round_log),
            inline=False,
        )
        embed.set_image(url="attachment://war.png")
        embed.set_footer(text="10 rounds • No coins lost — just glory! • L!war to rematch")

        view = WarPlayAgainView(self, challenger.id, opponent)
        await msg.edit(embed=embed, attachments=[final_img], view=view)

    # ═════════════════════════════════════════════════════════════════════════
    #  GO FISH — slash command, vs bot, in-channel
    # ═════════════════════════════════════════════════════════════════════════

    @app_commands.command(name="gofish", description="🎣 Play Go Fish against the bot!")
    async def gofish_cmd(self, interaction: discord.Interaction):
        if interaction.user.id in self.active_gofish:
            await interaction.response.send_message(
                "❗ You already have a Go Fish game running! Finish it first.",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        await self._gf_start_game(interaction)

    async def _gf_start_game(self, interaction: discord.Interaction):
        uid = interaction.user.id
        state = self._gf_build_state(interaction.channel_id)
        self.active_gofish[uid] = state
        self._gf_log(state, "🎮 Game started! You go first.")

        embed = self._gf_status_embed(state, interaction.user)
        embed.description = (
            f"**Welcome, {interaction.user.mention}!**\n"
            "Pick a rank from the dropdown below to ask the bot. "
            "Use 👁 to view your cards.\n\n"
            "*Collect 4-of-a-kind to complete a 📗 book — most books wins!*"
        )
        view = GoFishActionView(self, uid, state)
        msg = await interaction.followup.send(embed=embed, view=view, wait=True)
        state["msg"] = msg

    def _gf_build_state(self, channel_id: int) -> dict:
        deck = _build_deck()
        p_hand = [deck.pop() for _ in range(7)]
        b_hand = [deck.pop() for _ in range(7)]
        p_books, p_hand = _check_books(p_hand)
        b_books, b_hand = _check_books(b_hand)
        return {
            "deck": deck,
            "player_hand": p_hand,
            "bot_hand": b_hand,
            "player_books": p_books,
            "bot_books": b_books,
            "channel_id": channel_id,
            "log": [],
            "msg": None,
        }

    def _gf_status_embed(self, state: dict, user) -> discord.Embed:
        p_books = state["player_books"]
        b_books = state["bot_books"]
        embed = discord.Embed(title="🎣 Go Fish", color=discord.Color.teal())
        embed.add_field(
            name=f"🧑 {user.display_name}",
            value=(
                f"📗 Books: **{len(p_books)}**"
                + (f" `{'` `'.join(p_books)}`" if p_books else "")
                + f"\n🃏 Cards: **{len(state['player_hand'])}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="🤖 Bot",
            value=(
                f"📕 Books: **{len(b_books)}**"
                + (f" `{'` `'.join(b_books)}`" if b_books else "")
                + f"\n🃏 Cards: **{len(state['bot_hand'])}**"
            ),
            inline=True,
        )
        embed.add_field(name="🎴 Deck", value=f"**{len(state['deck'])}** remaining", inline=True)
        if state["log"]:
            embed.add_field(
                name="📜 Last Actions",
                value="\n".join(state["log"][-5:]),
                inline=False,
            )
        embed.set_footer(text="Dropdown → ask for a rank  •  👁 → see your hand")
        return embed

    def _gf_log(self, state: dict, msg: str):
        state["log"].append(msg)

    async def _gf_player_ask(self, interaction: discord.Interaction, rank: str):
        uid = interaction.user.id
        state = self.active_gofish.get(uid)
        if not state:
            await interaction.followup.send("❌ No active game found!", ephemeral=True)
            return
        if not any(_rank(c) == rank for c in state["player_hand"]):
            await interaction.followup.send(
                f"❌ You don't have any **{rank}s** in your hand!", ephemeral=True
            )
            return

        given = [c for c in state["bot_hand"] if _rank(c) == rank]
        if given:
            for c in given:
                state["bot_hand"].remove(c)
            state["player_hand"].extend(given)
            self._gf_log(state, f"✅ Bot had {len(given)} **{rank}(s)** — you got them! Go again.")
            new_books, state["player_hand"] = _check_books(state["player_hand"])
            for b in new_books:
                state["player_books"].append(b)
                self._gf_log(state, f"📗 Book completed: **{b}** ({len(state['player_books'])} total)")
            if not state["bot_hand"] and state["deck"]:
                state["bot_hand"].append(state["deck"].pop())
                self._gf_log(state, "🤖 Bot drew a card (hand was empty).")
        else:
            if state["deck"]:
                drawn = state["deck"].pop()
                state["player_hand"].append(drawn)
                if _rank(drawn) == rank:
                    self._gf_log(state, f"🎣 Go Fish! You drew **{drawn}** — matches! Go again.")
                else:
                    self._gf_log(state, f"🎣 Go Fish! You drew a card. Bot's turn.")
                    new_books, state["player_hand"] = _check_books(state["player_hand"])
                    for b in new_books:
                        state["player_books"].append(b)
                        self._gf_log(state, f"📗 Book completed: **{b}**")
                    await self._gf_update(interaction, state, uid)
                    await asyncio.sleep(1.2)
                    await self._gf_bot_turn(interaction, state, uid)
                    return
            else:
                self._gf_log(state, "🎣 Go Fish! Deck empty — bot's turn.")
                await self._gf_update(interaction, state, uid)
                await asyncio.sleep(1.2)
                await self._gf_bot_turn(interaction, state, uid)
                return

        if _gf_game_over(state):
            await self._gf_end(interaction, state, uid)
            return
        await self._gf_update(interaction, state, uid)

    async def _gf_bot_turn(self, interaction: discord.Interaction, state: dict, uid: int):
        while True:
            if _gf_game_over(state):
                await self._gf_end(interaction, state, uid)
                return
            if not state["bot_hand"]:
                if state["deck"]:
                    state["bot_hand"].append(state["deck"].pop())
                else:
                    break
            rank = _bot_ask_rank(state["bot_hand"])
            if not rank:
                break
            given = [c for c in state["player_hand"] if _rank(c) == rank]
            if given:
                for c in given:
                    state["player_hand"].remove(c)
                state["bot_hand"].extend(given)
                self._gf_log(state, f"🤖 Bot asked for **{rank}** — you had {len(given)}! Bot goes again.")
                new_books, state["bot_hand"] = _check_books(state["bot_hand"])
                for b in new_books:
                    state["bot_books"].append(b)
                    self._gf_log(state, f"📕 Bot completed book: **{b}** ({len(state['bot_books'])} total)")
                if not state["player_hand"] and state["deck"]:
                    state["player_hand"].append(state["deck"].pop())
                    self._gf_log(state, "🧑 You drew a card (hand was empty).")
                if _gf_game_over(state):
                    await self._gf_end(interaction, state, uid)
                    return
                await self._gf_update(interaction, state, uid)
                await asyncio.sleep(1.2)
            else:
                if state["deck"]:
                    drawn = state["deck"].pop()
                    state["bot_hand"].append(drawn)
                    if _rank(drawn) == rank:
                        self._gf_log(state, f"🤖 Bot fished for **{rank}** and got it! Bot goes again.")
                        new_books, state["bot_hand"] = _check_books(state["bot_hand"])
                        for b in new_books:
                            state["bot_books"].append(b)
                            self._gf_log(state, f"📕 Bot completed book: **{b}**")
                        if _gf_game_over(state):
                            await self._gf_end(interaction, state, uid)
                            return
                        await self._gf_update(interaction, state, uid)
                        await asyncio.sleep(1.2)
                        continue
                    else:
                        self._gf_log(state, f"🤖 Bot asked for **{rank}** → Go Fish! Your turn.")
                else:
                    self._gf_log(state, f"🤖 Bot asked for **{rank}** → Go Fish! Deck empty. Your turn.")
                break

        if _gf_game_over(state):
            await self._gf_end(interaction, state, uid)
            return
        await self._gf_update(interaction, state, uid)

    async def _gf_update(self, interaction: discord.Interaction, state: dict, uid: int):
        embed = self._gf_status_embed(state, interaction.user)
        view = GoFishActionView(self, uid, state) if state["player_hand"] else discord.ui.View()
        msg = state.get("msg")
        try:
            if msg:
                await msg.edit(embed=embed, view=view)
            else:
                msg = await interaction.followup.send(embed=embed, view=view, wait=True)
                state["msg"] = msg
        except discord.NotFound:
            msg = await interaction.followup.send(embed=embed, view=view, wait=True)
            state["msg"] = msg

    async def _gf_end(self, interaction: discord.Interaction, state: dict, uid: int):
        user = interaction.user
        p_cnt = len(state["player_books"])
        b_cnt = len(state["bot_books"])

        if p_cnt > b_cnt:
            title = f"🏆 {user.display_name} Wins!"
            desc = f"**{p_cnt}** books vs bot's **{b_cnt}**. Well played!"
            color = discord.Color.green()
            outcome = "win"
        elif b_cnt > p_cnt:
            title = "🤖 Bot Wins!"
            desc = f"Bot had **{b_cnt}** books vs your **{p_cnt}**. Better luck next time!"
            color = discord.Color.red()
            outcome = "lose"
        else:
            title = "🤝 Tie!"
            desc = f"Both finished with **{p_cnt}** books — incredible!"
            color = discord.Color.gold()
            outcome = "draw"

        if _mg:
            try:
                _mg(uid, "gofish", outcome, 0)
                _inc(uid, "gofish_played")
                if outcome == "win":
                    _inc(uid, "gofish_wins")
            except Exception:
                pass

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.add_field(
            name=f"🧑 {user.display_name}",
            value=(
                f"📗 Books: **{p_cnt}**"
                + (f"\n`{'` `'.join(state['player_books'])}`" if state["player_books"] else "")
            ),
            inline=True,
        )
        embed.add_field(
            name="🤖 Bot",
            value=(
                f"📕 Books: **{b_cnt}**"
                + (f"\n`{'` `'.join(state['bot_books'])}`" if state["bot_books"] else "")
            ),
            inline=True,
        )
        embed.set_footer(text="Thanks for playing! Use Play Again to start fresh.")

        view = GoFishPlayAgainView(self, uid)
        del self.active_gofish[uid]

        msg = state.get("msg")
        try:
            if msg:
                await msg.edit(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
        except discord.NotFound:
            await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(CardGames(bot))
