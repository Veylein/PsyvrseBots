import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, Any, Tuple, Union, List

# UNO Card representation
class UNOCard:
    COLORS = ["🔴", "🟡", "🟢", "🔵"]
    SPECIAL_CARDS = ["Skip", "Reverse", "Draw2"]
    WILD_CARDS = ["Wild", "Wild Draw4"]
    
    def __init__(self, color=None, value=None):
        self.color = color
        self.value = value
    
    def __str__(self):
        if self.value in self.WILD_CARDS:
            return f"🌈 {self.value}"
        return f"{self.color} {self.value}"
    
    def __repr__(self):
        return self.__str__()
    
    @staticmethod
    def create_deck():
        """Create a full UNO deck"""
        deck = []
        
        # Number cards (0-9, two of each except 0)
        for color in UNOCard.COLORS:
            deck.append(UNOCard(color, "0"))
            for num in range(1, 10):
                deck.append(UNOCard(color, str(num)))
                deck.append(UNOCard(color, str(num)))
            
            # Special cards (2 of each)
            for special in UNOCard.SPECIAL_CARDS:
                deck.append(UNOCard(color, special))
                deck.append(UNOCard(color, special))
        
        # Wild cards (4 of each)
        for _ in range(4):
            deck.append(UNOCard(None, "Wild"))
            deck.append(UNOCard(None, "Wild Draw4"))
        
        random.shuffle(deck)
        return deck
    
    def can_play_on(self, other_card, declared_color=None):
        """Check if this card can be played on another"""
        # Wild cards can always be played
        if self.value in self.WILD_CARDS:
            return True
        
        # Match color or value
        target_color = declared_color if declared_color else other_card.color
        return self.color == target_color or self.value == other_card.value

class UNOGame:
    def __init__(self, players: List[discord.Member]):
        self.players = players
        self.hands = {player.id: [] for player in players}
        self.deck = UNOCard.create_deck()
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        self.current_color = None
        self.game_over = False
        self.winner = None
        
        # Deal initial hands
        for player in players:
            for _ in range(7):
                self.hands[player.id].append(self.deck.pop())
        
        # Start discard pile with a non-special card
        while True:
            card = self.deck.pop()
            if card.value not in UNOCard.SPECIAL_CARDS and card.value not in UNOCard.WILD_CARDS:
                self.discard_pile.append(card)
                self.current_color = card.color
                break
    
    @property
    def current_player(self):
        return self.players[self.current_player_index]
    
    @property
    def top_card(self):
        return self.discard_pile[-1] if self.discard_pile else None
    
    def draw_card(self, player_id, count=1):
        """Draw cards from deck"""
        cards = []
        for _ in range(count):
            if not self.deck:
                # Reshuffle discard pile (except top card)
                if len(self.discard_pile) > 1:
                    self.deck = self.discard_pile[:-1]
                    random.shuffle(self.deck)
                    self.discard_pile = [self.discard_pile[-1]]
                else:
                    break
            
            card = self.deck.pop()
            self.hands[player_id].append(card)
            cards.append(card)
        return cards
    
    def play_card(self, player_id, card_index, declared_color=None):
        """Play a card from hand"""
        if card_index < 0 or card_index >= len(self.hands[player_id]):
            return False, "Invalid card index!"
        
        card = self.hands[player_id][card_index]
        
        # Check if card can be played
        if not card.can_play_on(self.top_card, self.current_color):
            return False, "Card cannot be played on current card!"
        
        # Remove card from hand
        self.hands[player_id].pop(card_index)
        self.discard_pile.append(card)
        
        # Update current color
        if card.value in UNOCard.WILD_CARDS:
            self.current_color = declared_color
        else:
            self.current_color = card.color
        
        # Handle special cards
        if card.value == "Skip":
            self.next_turn()
        elif card.value == "Reverse":
            self.direction *= -1
            if len(self.players) == 2:
                self.next_turn()
        elif card.value == "Draw2":
            self.next_turn()
            self.draw_card(self.current_player.id, 2)
            return True, "Next player draws 2 cards!"
        elif card.value == "Wild Draw4":
            self.next_turn()
            self.draw_card(self.current_player.id, 4)
            return True, "Next player draws 4 cards!"
        
        # Check for win
        if len(self.hands[player_id]) == 0:
            self.game_over = True
            self.winner = next(p for p in self.players if p.id == player_id)
            return True, "WIN!"
        
        return True, "Card played successfully!"
    
    def next_turn(self):
        """Move to next player"""
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
    
    def get_hand_display(self, player_id):
        """Display a player's hand"""
        hand = self.hands[player_id]
        return "\n".join([f"`{i}` {card}" for i, card in enumerate(hand)])

class CardGames(commands.Cog):
    """Card games: Go Fish (vs bot or player), Blackjack (vs dealer), War (instant), UNO (multiplayer)"""
    
    def __init__(self, bot):
        self.bot = bot
        self.go_fish_games: Dict[Tuple[Union[int, str], ...], Dict[str, Any]] = {}
        self.player_to_game: Dict[int, Tuple[Union[int, str], ...]] = {}
        self.blackjack_games: Dict[int, Dict[str, Any]] = {}
        self.active_uno_games = {}  # For UNO games

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
        
        try:
            embed = discord.Embed(title="🎣 Your Go Fish hand", color=discord.Color.blue())
            embed.add_field(name="Cards", value=self.pretty_hand(hand), inline=False)
            embed.add_field(name="Your Books", value=f"{len(books)} ({', '.join(books) if books else 'none'})", inline=True)
            embed.add_field(name="Opponent Books", value=str(opp_books), inline=True)
            embed.add_field(name="Turn", value=state['names'][state['turn']], inline=False)
            await author.send(embed=embed)
            msg = "✅ I sent your hand via DM."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        except:
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
        
        try:
            await author.send(embed=discord.Embed(
                title="🃏 Blackjack — Game Started",
                description=f"**Your hand:** {self.pretty_hand(player)} **(Total: {self._bj_value(player)})**\n**Dealer shows:** {dealer[0]}",
                color=discord.Color.dark_purple()
            ))
            msg = "🃏 Blackjack started! I DM'd your hand. Use `L!blackjack hit/stand` or `/blackjack hit/stand`."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
        except:
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
            
        try:
            await author.send(embed=discord.Embed(
                title="🃏 Blackjack — Your Hand",
                description=f"{self.pretty_hand(state['player'])} **(Total: {self._bj_value(state['player'])})**",
                color=discord.Color.dark_purple()
            ))
            msg = "✅ I sent your hand via DM."
        except:
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
            
        if val(user_card) > val(opp_card):
            result = f"🎉 {author.mention} wins the round!"
            color = discord.Color.green()
        elif val(user_card) < val(opp_card):
            result = f"😔 {opponent.mention if opponent else '**Bot**'} wins the round!"
            color = discord.Color.red()
        else:
            result = "⚔️ It's a tie (WAR)!"
            color = discord.Color.gold()
            
        embed = discord.Embed(title="⚔️ War", color=color)
        embed.add_field(name=f"{author.display_name}'s Card", value=f"**{user_card}**", inline=True)
        embed.add_field(name=f"{opponent.display_name if opponent else 'Bot'}'s Card", value=f"**{opp_card}**", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            try:
                await ctx.reply(embed=embed)
            except:
                await ctx.send(embed=embed)

    # ==================== UNO COMMANDS ====================
    
    @app_commands.command(name="uno", description="UNO card game")
    @app_commands.choices(action=[
        app_commands.Choice(name="🎴 Create Game", value="create"),
        app_commands.Choice(name="▶️ Start Game", value="start"),
        app_commands.Choice(name="🃏 Play Card", value="play"),
        app_commands.Choice(name="➕ Draw Card", value="draw"),
        app_commands.Choice(name="👀 View Hand", value="hand")
    ])
    @app_commands.describe(
        card_number="For playing: card number from your hand",
        color="For wild cards: red, blue, green, or yellow"
    )
    async def uno_command(self, interaction: discord.Interaction, action: app_commands.Choice[str], card_number: int = None, color: str = None):
        """Unified UNO command with action dropdown"""
        action_value = action.value if isinstance(action, app_commands.Choice) else action
        
        if action_value == "create":
            await self.uno_create_action(interaction)
        elif action_value == "start":
            await self.uno_start_action(interaction)
        elif action_value == "play":
            await self.uno_play_action(interaction, card_number, color)
        elif action_value == "draw":
            await self.uno_draw_action(interaction)
        elif action_value == "hand":
            await self.uno_hand_action(interaction)
    
    async def uno_create_action(self, interaction: discord.Interaction):
        """Start UNO game"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_uno"
        
        if game_id in self.active_uno_games:
            await interaction.response.send_message("❌ There's already an UNO game here!")
            return
        
        # Create initial player list
        embed = discord.Embed(
            title="🎴 UNO Game Starting!",
            description=f"{interaction.user.mention} wants to play UNO!\n\n"
                       f"**Players:** {interaction.user.mention}\n\n"
                       f"React with 🎴 to join! (Max 10 players)\n"
                       f"Game starts in 30 seconds or when host types `/uno start`",
            color=discord.Color.red()
        )
        
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎴")
        await interaction.response.send_message("✅ UNO game created!", ephemeral=True)
        
        # Store game setup
        self.active_uno_games[game_id] = {
            "setup": True,
            "host": interaction.user,
            "message": msg,
            "players": [interaction.user]
        }
    
    async def uno_start_action(self, interaction: discord.Interaction):
        """Start the UNO game"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_uno"
        
        if game_id not in self.active_uno_games:
            await interaction.response.send_message("❌ No UNO game to start!")
            return
        
        game_data = self.active_uno_games[game_id]
        
        if not game_data.get("setup"):
            await interaction.response.send_message("❌ Game already started!")
            return
        
        if interaction.user != game_data["host"]:
            await interaction.response.send_message("❌ Only the host can start!", ephemeral=True)
            return
        
        # Get players from reactions
        try:
            msg = game_data["message"]
            msg = await interaction.channel.fetch_message(msg.id)
            
            reaction = discord.utils.get(msg.reactions, emoji="🎴")
            if reaction:
                players = [user async for user in reaction.users() if not user.bot]
                game_data["players"] = players[:10]  # Max 10 players
        except:
            await interaction.response.send_message("❌ Error fetching players!")
            return
        
        if len(game_data["players"]) < 2:
            await interaction.response.send_message("❌ Need at least 2 players!")
            return
        
        # Create game
        game = UNOGame(game_data["players"])
        self.active_uno_games[game_id] = game
        
        # Send starting hands to each player via DM
        for player in game.players:
            try:
                hand_display = game.get_hand_display(player.id)
                await player.send(f"🎴 **Your UNO hand:**\n{hand_display}")
            except:
                pass
        
        embed = discord.Embed(
            title="🎴 UNO Game Started!",
            description=f"**Players:** {', '.join([p.mention for p in game.players])}\n\n"
                       f"**Top Card:** {game.top_card}\n"
                       f"**Current Color:** {game.current_color}\n\n"
                       f"**{game.current_player.mention}'s turn!**\n\n"
                       f"Use `/uno play <card_number>` to play a card\n"
                       f"Use `/uno draw` to draw a card\n"
                       f"Check your hand with `/uno hand`",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def uno_play_action(self, interaction: discord.Interaction, card_number: int, color: Optional[str] = None):
        """Play an UNO card"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_uno"
        
        if game_id not in self.active_uno_games:
            await interaction.response.send_message("❌ No active UNO game!")
            return
        
        game = self.active_uno_games[game_id]
        
        if isinstance(game, dict):
            await interaction.response.send_message("❌ Game hasn't started yet!")
            return
        
        if interaction.user != game.current_player:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        # Parse color for wild cards
        declared_color = None
        if color:
            color_map = {"red": "🔴", "yellow": "🟡", "green": "🟢", "blue": "🔵"}
            declared_color = color_map.get(color.lower())
        
        success, message = game.play_card(interaction.user.id, card_number, declared_color)
        
        if not success:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Check for win
        if game.game_over:
            reward = 300 + (len(game.players) * 50)
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(game.winner.id, reward, "uno_win")
            
            reward_text = f"\n+{reward} PsyCoins!" if economy_cog else ""
            embed = discord.Embed(
                title="🎴 UNO - GAME OVER!",
                description=f"🏆 **{game.winner.mention} wins!**{reward_text}",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            del self.active_uno_games[game_id]
            return
        
        # Move to next turn
        game.next_turn()
        
        # Update game state
        embed = discord.Embed(
            title="🎴 UNO Game",
            description=f"**Top Card:** {game.top_card}\n"
                       f"**Current Color:** {game.current_color}\n\n"
                       f"**{game.current_player.mention}'s turn!**\n\n"
                       f"{message}",
            color=discord.Color.red()
        )
        
        # Show card counts
        counts = "\n".join([f"{p.mention}: {len(game.hands[p.id])} cards" for p in game.players])
        embed.add_field(name="Card Counts", value=counts)
        
        await interaction.response.send_message(embed=embed)
    
    async def uno_draw_action(self, interaction: discord.Interaction):
        """Draw a card"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_uno"
        
        if game_id not in self.active_uno_games:
            await interaction.response.send_message("❌ No active UNO game!")
            return
        
        game = self.active_uno_games[game_id]
        
        if isinstance(game, dict):
            await interaction.response.send_message("❌ Game hasn't started yet!")
            return
        
        if interaction.user != game.current_player:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        cards = game.draw_card(interaction.user.id, 1)
        
        if not cards:
            await interaction.response.send_message("❌ No more cards in deck!", ephemeral=True)
            return
        
        game.next_turn()
        
        await interaction.response.send_message(
            f"You drew: {cards[0]}\n\n**{game.current_player.mention}'s turn!**"
        )
    
    async def uno_hand_action(self, interaction: discord.Interaction):
        """View hand"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_uno"
        
        if game_id not in self.active_uno_games:
            await interaction.response.send_message("❌ No active UNO game!", ephemeral=True)
            return
        
        game = self.active_uno_games[game_id]
        
        if isinstance(game, dict):
            await interaction.response.send_message("❌ Game hasn't started yet!", ephemeral=True)
            return
        
        hand_display = game.get_hand_display(interaction.user.id)
        await interaction.response.send_message(f"🎴 **Your hand:**\n{hand_display}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(CardGames(bot))
