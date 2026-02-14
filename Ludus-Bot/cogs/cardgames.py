import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, Any, Tuple, Union, List
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.card_visuals import (
    create_hand_image,
    create_blackjack_image,
    create_war_image,
    create_comparison_image,
    parse_card
)

class CardGames(commands.Cog):
    """🎴 Card games with beautiful graphics: Go Fish, Blackjack, War"""
    
    def __init__(self, bot):
        self.bot = bot
        self.go_fish_games: Dict[Tuple[Union[int, str], ...], Dict[str, Any]] = {}
        self.player_to_game: Dict[int, Tuple[Union[int, str], ...]] = {}
        self.blackjack_games: Dict[int, Dict[str, Any]] = {}
        self.active_uno_games = {}  # For UNO games

    def get_user_deck(self, user_id: int) -> str:
        """Get user's preferred card deck from economy system"""
        try:
            economy_cog = self.bot.get_cog('Economy')
            if economy_cog:
                return economy_cog.get_user_card_deck(user_id)
        except:
            pass
        return 'classic'  # Default if economy not available
    
    def format_card_for_display(self, card: str) -> str:
        """Convert internal format to display format (e.g., 'A♠' -> 'As')"""
        if not card or card == "JOKER":
            return card
        # Card is already in format like "A♠", convert to "As"
        suit_map = {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}
        for symbol, letter in suit_map.items():
            if symbol in card:
                return card.replace(symbol, letter)
        return card

    def build_deck(self, jokers: int = 0):
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        for _ in range(jokers):
            deck.append("JOKER")
        random.shuffle(deck)
        return deck

    def rank_of(self, card: str) -> str:
        return card[:-1] if card != "JOKER" else "JOKER"

    def pretty_hand(self, hand) -> str:
        return ", ".join(hand) if hand else "(empty)"

    def _find_gofish_game(self, user_id: int) -> Optional[Tuple[Tuple[Union[int, str], ...], Dict[str, Any]]]:
        game_id = self.player_to_game.get(user_id)
        if game_id:
            game_state = self.go_fish_games.get(game_id)
            if game_state:
                return (game_id, game_state)
        return None

    def _check_gofish_win(self, state: Dict[str, Any]) -> Optional[str]:
        p1_id, p2_id = state['players']
        p1_books = len(state['books'][p1_id])
        p2_books = len(state['books'][p2_id])
        
        p1_hand_empty = len(state['hands'][p1_id]) == 0
        p2_hand_empty = len(state['hands'][p2_id]) == 0
        deck_empty = len(state['deck']) == 0
        
        if (p1_hand_empty and p2_hand_empty) or (deck_empty and (p1_hand_empty or p2_hand_empty)):
            p1_name = state['names'][p1_id]
            p2_name = state['names'][p2_id]
            if p1_books > p2_books:
                return f"🎉 {p1_name} wins with {p1_books} books vs {p2_books}!"
            elif p2_books > p1_books:
                return f"🎉 {p2_name} wins with {p2_books} books vs {p1_books}!"
            else:
                return f"🤝 Tie! Both have {p1_books} books."
        return None

    async def _check_books_gofish(self, state: Dict[str, Any], pid):
        hand = state['hands'].get(pid, [])
        ranks = {}
        for c in hand:
            r = self.rank_of(c)
            ranks.setdefault(r, []).append(c)
        completed = []
        for r, cards in ranks.items():
            if len(cards) >= 4:
                for card in cards[:4]:
                    hand.remove(card)
                state['books'][pid].append(r)
                completed.append(r)
        if completed and pid != 'BOT':
            try:
                user = await self.bot.fetch_user(pid)
                await user.send(embed=discord.Embed(
                    title="🎉 Go Fish — Book Completed!",
                    description=f"Completed books: **{', '.join(completed)}**",
                    color=discord.Color.gold()
                ))
            except:
                pass
        return completed

    @commands.group(name="gofish", invoke_without_command=True)
    async def gofish(self, ctx):
        embed = discord.Embed(
            title="🎣 Go Fish",
            description="**Commands:**\n`L!gofish start [@opponent]` or `/gofish start [@opponent]` - Start a game (opponent optional)\n`L!gofish ask <rank>` or `/gofish-ask <rank>` - Ask opponent for cards\n`L!gofish hand` or `/gofish hand` - View your hand\n`L!gofish stop` or `/gofish stop` - End current game\n\n**How to play:**\nCollect 4 of a kind to make a book. Most books wins! Takes turns asking for cards.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @gofish.command(name="start")
    async def gofish_start_prefix(self, ctx, opponent: Optional[discord.Member] = None):
        await self._gofish_start(ctx.author, opponent, ctx, None)

    @app_commands.command(name="gofish", description="Go Fish card game")
    @app_commands.choices(action=[
        app_commands.Choice(name="🎣 Start Game", value="start"),
        app_commands.Choice(name="👀 View Hand", value="hand"),
        app_commands.Choice(name="🛑 Stop Game", value="stop"),
        app_commands.Choice(name="❓ Ask for Card", value="ask")
    ])
    @app_commands.describe(
        opponent="Player to challenge (for starting)",
        rank="Card rank to ask for (A, 2-10, J, Q, K)"
    )
    async def gofish_command(self, interaction: discord.Interaction, action: app_commands.Choice[str], opponent: discord.Member = None, rank: str = None):
        """Unified Go Fish command with action dropdown"""
        await interaction.response.defer()
        action_value = action.value if isinstance(action, app_commands.Choice) else action
        
        if action_value == "start":
            await self._gofish_start(interaction.user, opponent, None, interaction)
        elif action_value == "hand":
            await self._gofish_hand(interaction.user, None, interaction)
        elif action_value == "stop":
            await self._gofish_stop(interaction.user, None, interaction)
        elif action_value == "ask":
            if not rank:
                await interaction.followup.send("❌ You must specify a rank to ask for!", ephemeral=True)
                return
            await self._gofish_ask(interaction.user, rank, None, interaction)

    async def _gofish_start(self, author, opponent, ctx, interaction):
        if opponent and (opponent.bot or opponent.id == author.id):
            msg = "❌ You can't play against bots (except the game AI) or yourself."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        if author.id in self.player_to_game:
            msg = "❗ You already have a Go Fish game running. Use `L!gofish stop` to end it."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if opponent and opponent.id in self.player_to_game:
            msg = f"❌ {opponent.mention} is already in a game."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        deck = self.build_deck()
        p_hand = [deck.pop() for _ in range(7)]
        o_hand = [deck.pop() for _ in range(7)]

        p1_id = author.id
        p2_id = opponent.id if opponent else 'BOT'
        game_id = (p1_id, p2_id) if p2_id != 'BOT' else (p1_id,)

        state = {
            'deck': deck,
            'players': [p1_id, p2_id],
            'hands': {p1_id: p_hand, p2_id: o_hand},
            'books': {p1_id: [], p2_id: []},
            'turn': p1_id,
            'names': {p1_id: author.display_name, p2_id: opponent.display_name if opponent else 'Bot'},
            'channel': ctx.channel.id if ctx else interaction.channel.id
        }

        self.go_fish_games[game_id] = state
        self.player_to_game[p1_id] = game_id
        if opponent:
            self.player_to_game[p2_id] = game_id

        try:
            await author.send(embed=discord.Embed(
                title="🎣 Go Fish — Your starting hand",
                description=self.pretty_hand(p_hand),
                color=discord.Color.blue()
            ))
            if opponent:
                try:
                    await opponent.send(embed=discord.Embed(
                        title="🎣 Go Fish — Your starting hand",
                        description=self.pretty_hand(o_hand),
                        color=discord.Color.blue()
                    ))
                except:
                    pass
            msg = f"🎣 Go Fish started! {author.mention} vs {opponent.mention if opponent else '**Bot**'}.\n**{author.mention}'s turn first!** Use `L!gofish ask <rank>` or `/gofish-ask <rank>`"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        except:
            del self.go_fish_games[game_id]
            del self.player_to_game[p1_id]
            if opponent:
                del self.player_to_game[p2_id]
            msg = "❌ Could not DM you. Please enable DMs from server members."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)

    @gofish.command(name="hand")
    async def gofish_hand_prefix(self, ctx):
        await self._gofish_hand(ctx.author, ctx, None)

    async def _gofish_hand(self, author, ctx, interaction):
        result = self._find_gofish_game(author.id)
        if not result:
            msg = "❌ You have no active Go Fish game."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        game_id, state = result
        hand = state['hands'].get(author.id, [])
        books = state['books'].get(author.id, [])
        p1_id, p2_id = state['players']
        opp_id = p2_id if author.id == p1_id else p1_id
        opp_books = len(state['books'][opp_id])
        
        # Convert cards to visual format
        visual_cards = [self.format_card_for_display(c) for c in hand]
        
        try:
            # Create visual hand
            deck = self.get_user_deck(author.id)
            hand_image = create_hand_image(
                visual_cards, 
                title=f"🎣 Go Fish - Your Hand ({len(books)} books)",
                deck=deck
            )
            
            embed = discord.Embed(title="🎣 Your Go Fish Hand", color=discord.Color.blue())
            embed.add_field(name="Your Books", value=f"{len(books)} ({', '.join(books) if books else 'none'})", inline=True)
            embed.add_field(name="Opponent Books", value=str(opp_books), inline=True)
            embed.add_field(name="Turn", value=state['names'][state['turn']], inline=False)
            embed.add_field(name="Cards in Hand", value=str(len(hand)), inline=True)
            embed.add_field(name="Deck Remaining", value=str(len(state['deck'])), inline=True)
            embed.set_image(url="attachment://hand.png")
            embed.set_footer(text="💡 Use buttons or /gofish ask <rank> to ask for cards")
            
            # Create interactive view for asking cards
            view = GoFishAskView(self, author.id, state, game_id, ctx, interaction)
            
            await author.send(embed=embed, file=hand_image, view=view)
            msg = "✅ I sent your hand via DM with interactive buttons!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        except Exception as e:
            print(f"Error sending Go Fish hand: {e}")
            msg = "❌ Couldn't DM you. Make sure DMs are open."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)

    @gofish.command(name="stop")
    async def gofish_stop_prefix(self, ctx):
        await self._gofish_stop(ctx.author, ctx, None)

    async def _gofish_stop(self, author, ctx, interaction):
        result = self._find_gofish_game(author.id)
        if result:
            game_id, state = result
            for pid in state['players']:
                if pid != 'BOT':
                    self.player_to_game.pop(pid, None)
            del self.go_fish_games[game_id]
            msg = "🛑 Go Fish game stopped."
        else:
            msg = "❌ You have no active Go Fish game."
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @gofish.command(name="ask")
    async def gofish_ask_prefix(self, ctx, rank: str):
        await self._gofish_ask(ctx.author, rank, ctx, None)

    async def _gofish_ask(self, author, rank: str, ctx, interaction):
        result = self._find_gofish_game(author.id)
        if not result:
            msg = "❌ You have no active Go Fish game. Start one with `L!gofish start`."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        game_id, state = result
        
        if state['turn'] != author.id:
            msg = f"❌ It's not your turn! Wait for {state['names'][state['turn']]} to play."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        rank = rank.upper()
        valid = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
        if rank not in valid:
            msg = "❌ Invalid rank. Use A, 2-10, J, Q, or K"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        player_id = author.id
        p1_id, p2_id = state['players']
        opponent_id = p2_id if player_id == p1_id else p1_id
        opponent_hand = state['hands'][opponent_id]
        player_hand = state['hands'][player_id]

        matched = [c for c in opponent_hand if self.rank_of(c) == rank]
        
        if matched:
            for c in matched:
                opponent_hand.remove(c)
                player_hand.append(c)
            await self._check_books_gofish(state, player_id)
            await self._check_books_gofish(state, opponent_id)

            try:
                await author.send(embed=discord.Embed(
                    title="🎣 Go Fish — Success!",
                    description=f"You received **{len(matched)} card(s)**: {', '.join(matched)}\n\n**Your hand:** {self.pretty_hand(player_hand)}",
                    color=discord.Color.green()
                ))
            except:
                pass
            
            win_result = self._check_gofish_win(state)
            if win_result:
                for pid in state['players']:
                    if pid != 'BOT':
                        self.player_to_game.pop(pid, None)
                del self.go_fish_games[game_id]
                msg = f"✅ {author.mention} got **{len(matched)} card(s)**!\n\n{win_result}"
            else:
                msg = f"✅ {author.mention} got **{len(matched)} card(s)**! **You go again!**"
            
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        if not state['deck']:
            state['turn'] = opponent_id
            msg = f"🎴 Deck is empty — {author.mention} passes. {state['names'][opponent_id]}'s turn."
        else:
            drawn = state['deck'].pop()
            player_hand.append(drawn)
            try:
                await author.send(embed=discord.Embed(
                    title="🎣 Go Fish — Drew a card",
                    description=f"You drew: **{drawn}**\n\n**Your hand:** {self.pretty_hand(player_hand)}",
                    color=discord.Color.orange()
                ))
            except:
                pass
            state['turn'] = opponent_id
            msg = f"🎣 {author.mention} went fishing. {state['names'][opponent_id]}'s turn."

        await self._check_books_gofish(state, player_id)

        if opponent_id == 'BOT' and state['turn'] == 'BOT':
            await self._bot_turn_gofish(game_id, state, ctx, interaction)
            return

        win_result = self._check_gofish_win(state)
        if win_result:
            for pid in state['players']:
                if pid != 'BOT':
                    self.player_to_game.pop(pid, None)
            del self.go_fish_games[game_id]
            msg += f"\n\n{win_result}"

        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    async def _bot_turn_gofish(self, game_id, state, ctx, interaction):
        player_id = state['players'][0]
        messages = []
        
        while state['turn'] == 'BOT':
            await asyncio.sleep(1)
            
            if 'BOT' not in state['hands'] or not state['hands']['BOT']:
                if state['deck']:
                    drawn = state['deck'].pop()
                    state['hands']['BOT'].append(drawn)
                    messages.append("🤖 Bot has no cards, drawing from deck...")
                    continue
                else:
                    win_result = self._check_gofish_win(state)
                    if win_result:
                        for pid in state['players']:
                            if pid != 'BOT':
                                self.player_to_game.pop(pid, None)
                        del self.go_fish_games[game_id]
                        messages.append(f"\n{win_result}")
                    else:
                        state['turn'] = player_id
                        messages.append("🤖 Bot has no cards and deck is empty. **Your turn!**")
                    break
                
            bot_rank = self.rank_of(random.choice(state['hands']['BOT']))
            player_hand = state['hands'][player_id]
            
            player_cards = [c for c in player_hand if self.rank_of(c) == bot_rank]
            if player_cards:
                for c in player_cards:
                    player_hand.remove(c)
                    state['hands']['BOT'].append(c)
                await self._check_books_gofish(state, 'BOT')
                messages.append(f"🤖 Bot asked for **{bot_rank}** and took **{len(player_cards)} card(s)**! Bot goes again...")
            else:
                if state['deck']:
                    bdraw = state['deck'].pop()
                    state['hands']['BOT'].append(bdraw)
                    messages.append(f"🤖 Bot asked for **{bot_rank}** and went fishing.")
                else:
                    messages.append(f"🤖 Bot can't draw (deck empty).")
                await self._check_books_gofish(state, 'BOT')
                
                win_result = self._check_gofish_win(state)
                if win_result:
                    for pid in state['players']:
                        if pid != 'BOT':
                            self.player_to_game.pop(pid, None)
                    del self.go_fish_games[game_id]
                    messages.append(f"\n{win_result}")
                    break
                
                state['turn'] = player_id
                messages.append("**Your turn!**")
                break
            
            win_result = self._check_gofish_win(state)
            if win_result:
                for pid in state['players']:
                    if pid != 'BOT':
                        self.player_to_game.pop(pid, None)
                del self.go_fish_games[game_id]
                messages.append(f"\n{win_result}")
                break

        if messages:
            channel = self.bot.get_channel(state['channel'])
            if channel:
                await channel.send("\n".join(messages))

    @commands.group(name="blackjack", invoke_without_command=True)
    async def blackjack(self, ctx):
        embed = discord.Embed(
            title="🃏 Blackjack",
            description="**Commands:**\n`L!blackjack start` or `/blackjack start` - Start a game\n`L!blackjack hit` or `/blackjack hit` - Draw another card\n`L!blackjack stand` or `/blackjack stand` - End your turn\n`L!blackjack hand` or `/blackjack hand` - View your hand\n`L!blackjack stop` or `/blackjack stop` - Forfeit game\n\n**Goal:** Get closer to 21 than the dealer without going over!",
            color=discord.Color.dark_purple()
        )
        await ctx.send(embed=embed)
    
    @app_commands.command(name="blackjack", description="Play or manage your Blackjack game")
    @app_commands.describe(action="Choose an action")
    @app_commands.choices(action=[
        app_commands.Choice(name="start", value="start"),
        app_commands.Choice(name="hit", value="hit"),
        app_commands.Choice(name="stand", value="stand"),
        app_commands.Choice(name="hand", value="hand"),
        app_commands.Choice(name="stop", value="stop")
    ])
    async def blackjack_slash(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        
        if action == "start":
            await self._blackjack_start(interaction.user, None, interaction)
        elif action == "hit":
            await self._blackjack_hit(interaction.user, None, interaction)
        elif action == "stand":
            await self._blackjack_stand(interaction.user, None, interaction)
        elif action == "hand":
            await self._blackjack_hand(interaction.user, None, interaction)
        elif action == "stop":
            await self._blackjack_stop(interaction.user, None, interaction)

    @blackjack.command(name="start")
    async def blackjack_start_prefix(self, ctx):
        await self._blackjack_start(ctx.author, ctx, None)

    async def _blackjack_start(self, author, ctx, interaction):
        if author.id in self.blackjack_games:
            msg = "❗ You already have an active blackjack game. Use `L!blackjack stop` to end it."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        deck = self.build_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        state = {'deck': deck, 'player': player, 'dealer': dealer}
        self.blackjack_games[author.id] = state
        
        # Convert to visual format
        player_visual = [self.format_card_for_display(c) for c in player]
        dealer_visual = [self.format_card_for_display(c) for c in dealer]
        
        player_total = self._bj_value(player)
        dealer_shown = self._bj_value([dealer[0]])
        
        try:
            # Create visual blackjack image
            deck_pref = self.get_user_deck(author.id)
            bj_image = create_blackjack_image(
                player_visual,
                dealer_visual,
                player_total,
                dealer_shown,
                author.display_name,
                bet=0,
                player_deck=deck_pref,
                dealer_deck='classic',
                show_dealer=False
            )
            
            embed = discord.Embed(
                title="🃏 Blackjack — Game Started",
                description=f"**Your total:** {player_total}\n**Dealer shows:** {dealer[0]}",
                color=discord.Color.dark_purple()
            )
            embed.set_image(url="attachment://blackjack.png")
            embed.set_footer(text="Use the buttons below to play!")
            
            # Create interactive view
            view = BlackjackGameView(self, author.id)
            
            await author.send(embed=embed, file=bj_image, view=view)
            msg = "🃏 Blackjack started! I DM'd your hand with interactive buttons!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        except Exception as e:
            print(f"Error starting blackjack: {e}")
            del self.blackjack_games[author.id]
            msg = "❌ Couldn't DM you. Enable DMs to play blackjack."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)

    def _bj_value(self, hand):
        val = 0
        aces = 0
        for c in hand:
            r = self.rank_of(c)
            if r.isdigit():
                val += int(r)
            elif r in ['J','Q','K']:
                val += 10
            elif r == 'A':
                aces += 1
        for _ in range(aces):
            if val + 11 <= 21:
                val += 11
            else:
                val += 1
        return val

    @blackjack.command(name="hit")
    async def blackjack_hit_prefix(self, ctx):
        await self._blackjack_hit(ctx.author, ctx, None)

    async def _blackjack_hit(self, author, ctx, interaction):
        state = self.blackjack_games.get(author.id)
        if not state:
            msg = "❌ You have no active blackjack game. Start one with `L!blackjack start`."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        card = state['deck'].pop()
        state['player'].append(card)
        total = self._bj_value(state['player'])
        
        try:
            await author.send(embed=discord.Embed(
                title="🃏 Blackjack — Hit",
                description=f"**You drew:** {card}\n\n**Your hand:** {self.pretty_hand(state['player'])} **(Total: {total})**",
                color=discord.Color.dark_purple()
            ))
        except:
            msg = "❌ Couldn't DM you. Enable DMs."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        if total > 21:
            try:
                await author.send(embed=discord.Embed(
                    title="💥 Busted!",
                    description=f"You busted with **{total}**. Dealer wins.",
                    color=discord.Color.red()
                ))
            except:
                pass
            del self.blackjack_games[author.id]
            msg = f"💥 {author.mention} busted with **{total}**. Game over."
        else:
            msg = f"🃏 {author.mention} drew a card. Check your DMs!"
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @blackjack.command(name="stand")
    async def blackjack_stand_prefix(self, ctx):
        await self._blackjack_stand(ctx.author, ctx, None)

    async def _blackjack_stand(self, author, ctx, interaction):
        state = self.blackjack_games.get(author.id)
        if not state:
            msg = "❌ You have no active blackjack game."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        dealer = state['dealer']
        while self._bj_value(dealer) < 17:
            dealer.append(state['deck'].pop())
            
        player_total = self._bj_value(state['player'])
        dealer_total = self._bj_value(dealer)
        
        if dealer_total > 21 or player_total > dealer_total:
            result = "🎉 You win!"
            color = discord.Color.green()
        elif dealer_total == player_total:
            result = "🤝 Push (tie)"
            color = discord.Color.gold()
        else:
            result = "😔 Dealer wins"
            color = discord.Color.red()
            
        try:
            embed = discord.Embed(title="🃏 Blackjack — Result", color=color)
            embed.add_field(name="Your Hand", value=f"{self.pretty_hand(state['player'])} **(Total: {player_total})**", inline=False)
            embed.add_field(name="Dealer Hand", value=f"{self.pretty_hand(dealer)} **(Total: {dealer_total})**", inline=False)
            embed.add_field(name="Result", value=result, inline=False)
            await author.send(embed=embed)
        except:
            pass
            
        del self.blackjack_games[author.id]
        msg = f"🃏 {author.mention} finished blackjack. Check your DMs for the result!"
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @blackjack.command(name="hand")
    async def blackjack_hand_prefix(self, ctx):
        await self._blackjack_hand(ctx.author, ctx, None)

    async def _blackjack_hand(self, author, ctx, interaction):
        state = self.blackjack_games.get(author.id)
        if not state:
            msg = "❌ You have no active blackjack game."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        # Convert to visual format
        player_visual = [self.format_card_for_display(c) for c in state['player']]
        dealer_visual = [self.format_card_for_display(c) for c in state['dealer']]
        
        player_total = self._bj_value(state['player'])
        dealer_shown = self._bj_value([state['dealer'][0]])
        
        try:
            # Create visual blackjack image
            deck = self.get_user_deck(author.id)
            bj_image = create_blackjack_image(
                player_visual,
                dealer_visual,
                player_total,
                dealer_shown,
                author.display_name,
                bet=0,
                player_deck=deck,
                dealer_deck='classic',
                show_dealer=False
            )
            
            embed = discord.Embed(
                title="🃏 Blackjack — Your Hand",
                description=f"**Your total:** {player_total}\n**Dealer shows:** {state['dealer'][0]}",
                color=discord.Color.dark_purple()
            )
            embed.set_image(url="attachment://blackjack.png")
            embed.set_footer(text="Use buttons to Hit or Stand")
            
            # Create view
            view = BlackjackGameView(self, author.id)
            
            await author.send(embed=embed, file=bj_image, view=view)
            msg = "✅ I sent your hand via DM with interactive buttons."
        except Exception as e:
            print(f"Error showing blackjack hand: {e}")
            msg = "❌ Couldn't DM you."
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @blackjack.command(name="stop")
    async def blackjack_stop_prefix(self, ctx):
        await self._blackjack_stop(ctx.author, ctx, None)

    async def _blackjack_stop(self, author, ctx, interaction):
        if author.id in self.blackjack_games:
            del self.blackjack_games[author.id]
            msg = "🛑 Blackjack game stopped."
        else:
            msg = "❌ You have no active blackjack game."
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @commands.command(name="war")
    async def war(self, ctx, opponent: Optional[discord.Member] = None):
        await self._play_war(ctx.author, opponent, ctx, None)

    @app_commands.command(name="war", description="Play a round of War card game")
    @app_commands.describe(opponent="User to play against (optional, defaults to bot)")
    async def war_slash(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        await interaction.response.defer()
        await self._play_war(interaction.user, opponent, None, interaction)

    async def _play_war(self, author, opponent, ctx, interaction):
        if opponent and (opponent.bot or opponent.id == author.id):
            msg = "❌ You can't play against bots (except the game AI) or yourself."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
            
        deck = self.build_deck()
        user_card = deck.pop()
        opp_card = deck.pop()
        
        order = {"A":14, "K":13, "Q":12, "J":11, "10":10, "9":9, "8":8, "7":7, "6":6, "5":5, "4":4, "3":3, "2":2}
        def val(card):
            return order.get(self.rank_of(card), 0)
        
        # Determine result
        if val(user_card) > val(opp_card):
            result = f"🎉 {author.mention} wins!"
            color = discord.Color.green()
            result_text = f"{author.display_name} WINS"
        elif val(user_card) < val(opp_card):
            opp_name = opponent.mention if opponent else '**Bot**'
            result = f"😔 {opp_name} wins!"
            color = discord.Color.red()
            result_text = f"{opponent.display_name if opponent else 'Bot'} WINS"
        else:
            result = "It's a WAR (tie)!"
            color = discord.Color.gold()
            result_text = "TIE - WAR"
        
        # Create visual comparison
        user_visual = self.format_card_for_display(user_card)
        opp_visual = self.format_card_for_display(opp_card)
        
        # Get decks - player has custom, bot/opponent has classic or their own
        player_deck = self.get_user_deck(author.id)
        opponent_deck = 'classic' if not opponent else self.get_user_deck(opponent.id)
        
        war_image = create_war_image(
            user_visual,
            opp_visual,
            author.display_name,
            opponent.display_name if opponent else "Bot",
            deck=player_deck,
            result_text=result_text,
            opponent_deck=opponent_deck
        )
        
        embed = discord.Embed(title="⚔️ War Game", color=color, description=result)
        embed.add_field(name=f"{author.display_name}'s Card", value=f"**{user_card}** (Value: {val(user_card)})", inline=True)
        embed.add_field(name=f"{opponent.display_name if opponent else 'Bot'}'s Card", value=f"**{opp_card}** (Value: {val(opp_card)})", inline=True)
        embed.set_image(url="attachment://war.png")
        embed.set_footer(text="Highest card wins | Use /war to play again")
        
        # Add play again button
        view = WarPlayAgainView(self, author, opponent)
        
        if interaction:
            await interaction.followup.send(embed=embed, file=war_image, view=view)
        else:
            try:
                await ctx.reply(embed=embed, file=war_image, view=view)
            except:
                await ctx.send(embed=embed, file=war_image, view=view)

class GoFishAskView(discord.ui.View):
    """Interactive view for asking cards in Go Fish"""
    
    def __init__(self, cog, user_id, game_state, game_id, ctx, interaction):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.game_state = game_state
        self.game_id = game_id
        self.ctx = ctx
        self.interaction = interaction
        
        # Add rank selection dropdown
        self.add_item(GoFishRankSelect(cog, user_id, game_state, game_id, ctx, interaction))
    
    async def on_timeout(self):
        """Called when view times out"""
        for item in self.children:
            item.disabled = True

class GoFishRankSelect(discord.ui.Select):
    """Dropdown for selecting rank to ask for"""
    
    def __init__(self, cog, user_id, game_state, game_id, ctx, interaction_orig):
        self.cog = cog
        self.user_id = user_id
        self.game_state = game_state
        self.game_id = game_id
        self.ctx = ctx
        self.interaction_orig = interaction_orig
        
        # Get unique ranks in player's hand
        hand = game_state['hands'].get(user_id, [])
        ranks = sorted(set([cog.rank_of(card) for card in hand]), 
                      key=lambda x: ["A","2","3","4","5","6","7","8","9","10","J","Q","K"].index(x) if x in ["A","2","3","4","5","6","7","8","9","10","J","Q","K"] else 99)
        
        options = [
            discord.SelectOption(label=rank, description=f"Ask for {rank}'s", emoji="🎴")
            for rank in ranks[:25]  # Max 25 options
        ]
        
        if not options:
            options = [discord.SelectOption(label="No cards", description="Draw from deck first")]
        
        super().__init__(
            placeholder="🎴 Choose a rank to ask for...",
            options=options,
            custom_id="gofish_rank_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle rank selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        rank = self.values[0]
        await interaction.response.defer(ephemeral=True)
        
        # Call the ask logic
        await self.cog._gofish_ask(interaction.user, rank, self.ctx, self.interaction_orig)

class BlackjackGameView(discord.ui.View):
    """Interactive view for Blackjack game"""
    
    def __init__(self, cog, user_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success, emoji="🎴")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        state = self.cog.blackjack_games.get(self.user_id)
        if not state:
            await interaction.followup.send("❌ Game not found!", ephemeral=True)
            return
        
        # Hit logic
        card = state['deck'].pop()
        state['player'].append(card)
        total = self.cog._bj_value(state['player'])
        
        # Convert to visual format
        player_visual = [self.cog.format_card_for_display(c) for c in state['player']]
        dealer_visual = [self.cog.format_card_for_display(c) for c in state['dealer']]
        
        deck = self.cog.get_user_deck(self.user_id)
        bj_image = create_blackjack_image(
            player_visual,
            dealer_visual,
            total,
            self.cog._bj_value([state['dealer'][0]]),
            interaction.user.display_name,
            bet=0,
            player_deck=deck,
            dealer_deck='classic',
            show_dealer=False
        )
        
        if total > 21:
            # Busted!
            del self.cog.blackjack_games[self.user_id]
            
            embed = discord.Embed(
                title="💥 Busted!",
                description=f"You busted with **{total}**.",
                color=discord.Color.red()
            )
            embed.set_image(url="attachment://blackjack.png")
            embed.set_footer(text="😢 Better luck next time! Use /blackjack to play again")
            
            for item in self.children:
                item.disabled = True
            
            await interaction.followup.send(embed=embed, file=bj_image, view=self)
        else:
            # Continue playing
            embed = discord.Embed(
                title="🃏 Blackjack - You Hit!",
                description=f"You drew **{card}**\n\nYour total: **{total}**",
                color=discord.Color.blue()
            )
            embed.set_image(url="attachment://blackjack.png")
            embed.set_footer(text="Hit to draw another card, Stand to end your turn")
            
            await interaction.followup.send(embed=embed, file=bj_image, view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.primary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        state = self.cog.blackjack_games.get(self.user_id)
        if not state:
            await interaction.followup.send("❌ Game not found!", ephemeral=True)
            return
        
        # Dealer plays
        dealer = state['dealer']
        while self.cog._bj_value(dealer) < 17:
            dealer.append(state['deck'].pop())
        
        player_total = self.cog._bj_value(state['player'])
        dealer_total = self.cog._bj_value(dealer)
        
        # Determine winner
        if dealer_total > 21 or player_total > dealer_total:
            result = "🎉 You Win!"
            color = discord.Color.green()
        elif dealer_total == player_total:
            result = "🤝 Push (Tie)"
            color = discord.Color.gold()
        else:
            result = "😔 Dealer Wins"
            color = discord.Color.red()
        
        # Convert to visual format
        player_visual = [self.cog.format_card_for_display(c) for c in state['player']]
        dealer_visual = [self.cog.format_card_for_display(c) for c in dealer]
        
        deck = self.cog.get_user_deck(self.user_id)
        bj_image = create_blackjack_image(
            player_visual,
            dealer_visual,
            player_total,
            dealer_total,
            interaction.user.display_name,
            bet=0,
            player_deck=deck,
            dealer_deck='classic',
            show_dealer=True
        )
        
        del self.cog.blackjack_games[self.user_id]
        
        embed = discord.Embed(title="🃏 Blackjack - Game Over", description=result, color=color)
        embed.add_field(name="Your Hand", value=f"**{player_total}**", inline=True)
        embed.add_field(name="Dealer Hand", value=f"**{dealer_total}**", inline=True)
        embed.set_image(url="attachment://blackjack.png")
        embed.set_footer(text="Use /blackjack to play again!")
        
        for item in self.children:
            item.disabled = True
        
        await interaction.followup.send(embed=embed, file=bj_image, view=self)
    
    @discord.ui.button(label="Quit", style=discord.ButtonStyle.danger, emoji="❌")
    async def quit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.user_id in self.cog.blackjack_games:
            del self.cog.blackjack_games[self.user_id]
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(content="🛑 Game ended.", view=self)

class WarPlayAgainView(discord.ui.View):
    """View for playing War again"""
    
    def __init__(self, cog, player, opponent):
        super().__init__(timeout=60)
        self.cog = cog
        self.player = player
        self.opponent = opponent
    
    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.success, emoji="⚔️")
    async def play_again_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("❌ Only the original player can start a new game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.cog._play_war(self.player, self.opponent, None, interaction)
        
        # Disable button
        for item in self.children:
            item.disabled = True
        
        try:
            await interaction.message.edit(view=self)
        except:
            pass

async def setup(bot):
    await bot.add_cog(CardGames(bot))
