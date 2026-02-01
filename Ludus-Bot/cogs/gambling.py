import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional
import json
import os


# ==================== VIEW CLASSES ====================
# These need to be defined before the Gambling cog

class CrashView(discord.ui.View):
    """View for crash game"""
    
    def __init__(self, cog, user, bet, crash_multiplier):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.bet = bet
        self.crash_multiplier = crash_multiplier
        self.current_multiplier = 1.00
        self.cashed_out = False
        self.crashed = False
    
    @discord.ui.button(label="💰 Cash Out (1.00x)", style=discord.ButtonStyle.green, custom_id="cashout")
    async def cashout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.crashed:
            await interaction.response.send_message("❌ Too late! Already crashed!", ephemeral=True)
            return
        
        if self.cashed_out:
            await interaction.response.send_message("❌ Already cashed out!", ephemeral=True)
            return
        
        self.cashed_out = True
        self.stop()
        
        # Calculate payout
        payout = int(self.bet * self.current_multiplier)
        
        economy_cog = self.cog.bot.get_cog("Economy")
        economy_cog.add_coins(self.user.id, payout, "crash_win")
        
        # Record stats
        self.cog.record_game(self.user.id, "crash", self.bet, True, payout)
        # Update most played games
        profile_cog = self.cog.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(self.user.id, "crash")
        
        # Create result embed
        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"**Multiplier:** {self.current_multiplier:.2f}x\n"
                       f"**Payout:** +{payout:,} coins\n\n"
                       f"*(Game would have crashed at {self.crash_multiplier:.2f}x)*",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def start_crash(self, interaction):
        """Start the crash animation"""
        await asyncio.sleep(2)
        
        # Increment multiplier until crash
        increment = 0.10
        
        while self.current_multiplier < self.crash_multiplier and not self.cashed_out:
            self.current_multiplier += increment
            
            # Update button label
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.custom_id == "cashout":
                    item.label = f"💰 Cash Out ({self.current_multiplier:.2f}x)"
            
            # Update embed
            embed = discord.Embed(
                title="📈 Crash Game Running...",
                description=f"**Your Bet:** {self.bet:,} coins\n\n"
                           f"**Current Multiplier:** {self.current_multiplier:.2f}x\n"
                           f"**Potential Win:** {int(self.bet * self.current_multiplier):,} coins",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Click 'Cash Out' to claim your winnings!")
            
            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except:
                break
            
            # Wait before next increment (speed increases over time)
            wait_time = max(0.3, 1.0 - (self.current_multiplier * 0.05))
            await asyncio.sleep(wait_time)
        
        if not self.cashed_out:
            # CRASHED!
            self.crashed = True
            self.stop()
            
            # Record loss
            self.cog.record_game(self.user.id, "crash", self.bet, False, 0)
            # Update most played games
            profile_cog = self.cog.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "profile_manager"):
                profile_cog.profile_manager.record_game_played(self.user.id, "crash")
            
            embed = discord.Embed(
                title="💥 CRASHED!",
                description=f"**Crash Point:** {self.crash_multiplier:.2f}x\n"
                           f"**You Lost:** -{self.bet:,} coins\n\n"
                           f"You needed to cash out before {self.crash_multiplier:.2f}x!",
                color=discord.Color.red()
            )
            
            try:
                await interaction.edit_original_response(embed=embed, view=None)
            except:
                pass


class MinesView(discord.ui.View):
    """View for mines game"""
    
    def __init__(self, cog, user, bet, mine_count):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.bet = bet
        self.mine_count = mine_count
        self.revealed = []
        self.game_over = False
        
        # Limit: Discord allows max 25 components, so we use 4x5 grid (20 tiles) + 1 cash out button
        self.grid_size = 20
        
        # Place mines randomly on 20 tiles
        positions = list(range(self.grid_size))
        random.shuffle(positions)
        # Adjust mine count if it's too high for 20 tiles
        max_mines = min(mine_count, 18)  # Leave at least 2 safe tiles
        self.mines = set(positions[:max_mines])
        self.mine_count = max_mines
        self.safe_tiles = self.grid_size - max_mines
        self.revealed_safe = 0
        
        # Create 4x5 grid of buttons (20 tiles total)
        for i in range(self.grid_size):
            button = discord.ui.Button(
                label="❓",
                style=discord.ButtonStyle.secondary,
                custom_id=f"tile_{i}",
                row=i // 5
            )
            button.callback = self.create_tile_callback(i)
            self.add_item(button)
        
        # Add cash out button in the last row
        cashout_btn = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.green,
            custom_id="mines_cashout",
            row=4
        )
        cashout_btn.callback = self.cashout_callback
        self.add_item(cashout_btn)
    
    def create_tile_callback(self, position):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
                return
            
            if self.game_over:
                await interaction.response.send_message("❌ Game is over!", ephemeral=True)
                return
            
            if position in self.revealed:
                await interaction.response.send_message("❌ Already revealed!", ephemeral=True)
                return
            
            self.revealed.append(position)
            
            # Check if mine
            if position in self.mines:
                # HIT A MINE!
                self.game_over = True
                await self.reveal_all_mines(interaction)
                
                # Record loss
                self.cog.record_game(self.user.id, "mines", self.bet, False, 0)
                # Update most played games
                profile_cog = self.cog.bot.get_cog("Profile")
                if profile_cog and hasattr(profile_cog, "profile_manager"):
                    profile_cog.profile_manager.record_game_played(self.user.id, "mines")
                
                embed = discord.Embed(
                    title="💥 BOOM! You hit a mine!",
                    description=f"**You Lost:** -{self.bet:,} coins\n\n"
                               f"Better luck next time!",
                    color=discord.Color.red()
                )
                
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
            else:
                # SAFE!
                self.revealed_safe += 1
                
                # Calculate current multiplier
                multiplier = self.calculate_multiplier()
                potential_win = int(self.bet * multiplier)
                
                # Update button
                for item in self.children:
                    if isinstance(item, discord.ui.Button) and item.custom_id == f"tile_{position}":
                        item.label = "💎"
                        item.style = discord.ButtonStyle.success
                        item.disabled = True
                
                # Check if won (all safe tiles revealed)
                if self.revealed_safe >= self.safe_tiles:
                    self.game_over = True
                    await self.auto_cashout(interaction, multiplier, potential_win)
                else:
                    # Update embed
                    embed = discord.Embed(
                        title="💎 Safe Tile!",
                        description=f"**Your Bet:** {self.bet:,} coins\n"
                                   f"**Mines:** {self.mine_count}/25\n"
                                   f"**Revealed:** {self.revealed_safe}/{self.safe_tiles}\n\n"
                                   f"**Current Multiplier:** {multiplier:.2f}x\n"
                                   f"**Potential Win:** {potential_win:,} coins\n\n"
                                   f"Keep going or cash out!",
                        color=discord.Color.green()
                    )
                    
                    await interaction.response.edit_message(embed=embed, view=self)
        
        return callback
    
    def calculate_multiplier(self):
        """Calculate multiplier based on revealed tiles and mine count"""
        # Formula: Base multiplier increases with each reveal
        # More mines = higher multiplier per reveal
        if self.revealed_safe == 0:
            return 1.00
        
        # Multiplier formula (exponential growth)
        mine_factor = 1 + (self.mine_count * 0.1)
        reveal_factor = 1 + (self.revealed_safe * 0.15 * mine_factor)
        
        return round(reveal_factor, 2)
    
    async def cashout_callback(self, interaction: discord.Interaction):
        """Handle cash out"""
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        if self.revealed_safe == 0:
            await interaction.response.send_message("❌ Reveal at least one tile first!", ephemeral=True)
            return
        
        self.game_over = True
        multiplier = self.calculate_multiplier()
        payout = int(self.bet * multiplier)
        
        await self.auto_cashout(interaction, multiplier, payout)
    
    async def auto_cashout(self, interaction, multiplier, payout):
        """Auto cash out when all safe tiles revealed or manual cashout"""
        economy_cog = self.cog.bot.get_cog("Economy")
        economy_cog.add_coins(self.user.id, payout, "mines_win")
        
        # Record win
        self.cog.record_game(self.user.id, "mines", self.bet, True, payout)
        # Update most played games
        profile_cog = self.cog.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(self.user.id, "mines")
        
        # Reveal all mines
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id.startswith("tile_"):
                pos = int(item.custom_id.split("_")[1])
                if pos in self.mines:
                    item.label = "💣"
                    item.style = discord.ButtonStyle.danger
                item.disabled = True
        
        embed = discord.Embed(
            title="💰 Cashed Out!",
            description=f"**Tiles Revealed:** {self.revealed_safe}/{self.safe_tiles}\n"
                       f"**Final Multiplier:** {multiplier:.2f}x\n"
                       f"**Payout:** +{payout:,} coins\n\n"
                       f"Great job avoiding the mines!",
            color=discord.Color.gold()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            await interaction.edit_original_response(embed=embed, view=self)
        
        self.stop()
    
    async def reveal_all_mines(self, interaction):
        """Reveal all mines when player hits one"""
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id.startswith("tile_"):
                pos = int(item.custom_id.split("_")[1])
                if pos in self.mines:
                    item.label = "💣"
                    item.style = discord.ButtonStyle.danger
                elif pos in self.revealed:
                    item.label = "💎"
                    item.style = discord.ButtonStyle.success
                item.disabled = True


class HigherLowerView(discord.ui.View):
    """View for higher/lower game"""
    
    def __init__(self, cog, user, bet, first_card, deck):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.bet = bet
        self.first_card = first_card
        self.deck = deck
    
    @discord.ui.button(label="⬆️ Higher", style=discord.ButtonStyle.green)
    async def higher_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        await self.resolve_game(interaction, "higher")
    
    @discord.ui.button(label="⬇️ Lower", style=discord.ButtonStyle.red)
    async def lower_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        await self.resolve_game(interaction, "lower")
    
    async def resolve_game(self, interaction, choice):
        """Resolve the higher/lower game"""
        self.stop()
        
        # Draw second card
        second_card = self.deck.pop()
        
        # Convert ranks to values
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        first_value = rank_values[self.first_card[0]]
        second_value = rank_values[second_card[0]]
        
        # Determine result
        if second_value > first_value:
            actual = "higher"
        elif second_value < first_value:
            actual = "lower"
        else:
            actual = "tie"
        
        # Check if won
        economy_cog = self.cog.bot.get_cog("Economy")
        
        if choice == actual:
            payout = int(self.bet * 1.6)  # Reduced from 2x to 1.6x
            economy_cog.add_coins(self.user.id, payout, "higherlower_win")
            result_text = f"🎉 **CORRECT!**\n+{payout:,} coins"
            color = discord.Color.green()
            won = True
        else:
            payout = 0
            result_text = f"💀 **WRONG!**\n-{self.bet:,} coins"
            color = discord.Color.red()
            won = False
        
        # Record stats
        self.cog.record_game(self.user.id, "higherlower", self.bet, won, payout)
        # Update most played games
        profile_cog = self.cog.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(self.user.id, "higherlower")
        
        # Create result embed
        embed = discord.Embed(title="🎴 Higher or Lower - Result", color=color)
        embed.add_field(name="First Card", value=f"{self.first_card[0]}{self.first_card[1]}", inline=True)
        embed.add_field(name="Second Card", value=f"{second_card[0]}{second_card[1]}", inline=True)
        embed.add_field(name="Your Guess", value=choice.title(), inline=True)
        embed.add_field(name="Result", value=result_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== GAMBLING COG ====================

class Gambling(commands.Cog):
    """Casino-style gambling games: Poker, Slots, Roulette, Higher/Lower"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.gambling_stats_file = os.path.join(data_dir, "gambling_stats.json")
        self.gambling_stats = self.load_stats()
    
    # Helper method to get user from context
    def _get_user(self, ctx_or_interaction, is_slash: bool):
        """Get user from either context or interaction"""
        return ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    async def _send_message(self, ctx_or_interaction, content=None, embed=None, view=None, is_slash: bool = False):
        """Universal message sender for both prefix and slash commands"""
        if is_slash:
            try:
                await ctx_or_interaction.response.send_message(content=content, embed=embed, view=view)
            except discord.errors.InteractionResponded:
                await ctx_or_interaction.followup.send(content=content, embed=embed, view=view)
        else:
            await ctx_or_interaction.send(content=content, embed=embed, view=view)
        
    def load_stats(self):
        """Load gambling statistics"""
        if os.path.exists(self.gambling_stats_file):
            with open(self.gambling_stats_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_stats(self):
        """Save gambling statistics"""
        with open(self.gambling_stats_file, 'w') as f:
            json.dump(self.gambling_stats, f, indent=2)
    
    def record_game(self, user_id: int, game: str, bet: int, won: bool, payout: int):
        """Record a gambling game for statistics"""
        user_key = str(user_id)
        if user_key not in self.gambling_stats:
            self.gambling_stats[user_key] = {
                "total_games": 0,
                "total_wagered": 0,
                "total_won": 0,
                "total_lost": 0,
                "games": {}
            }
        
        stats = self.gambling_stats[user_key]
        stats["total_games"] += 1
        stats["total_wagered"] += bet
        
        if won:
            stats["total_won"] += payout
        else:
            stats["total_lost"] += bet
        
        if game not in stats["games"]:
            stats["games"][game] = {"played": 0, "won": 0, "lost": 0}
        
        stats["games"][game]["played"] += 1
        if won:
            stats["games"][game]["won"] += 1
        else:
            stats["games"][game]["lost"] += 1
        
        self.save_stats()
    
    # ==================== POKER ====================
    
    @commands.command(name="poker")
    async def poker_prefix(self, ctx, bet: int):
        """Play 5-card poker (10-10,000 coins) - Prefix version"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await ctx.send("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < bet:
            await ctx.send(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(ctx.author.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Deal cards
        deck = self.create_deck()
        player_hand = [deck.pop() for _ in range(5)]
        dealer_hand = [deck.pop() for _ in range(5)]
        
        # Evaluate hands
        player_rank, player_name = self.evaluate_poker_hand(player_hand)
        dealer_rank, dealer_name = self.evaluate_poker_hand(dealer_hand)
        
        # Determine winner
        if player_rank > dealer_rank:
            payout = bet * player_rank
            economy_cog.add_coins(ctx.author.id, payout, "poker_win")
            result = f"🎉 You win with **{player_name}**!"
            color = discord.Color.green()
            won = True
        elif player_rank < dealer_rank:
            payout = 0
            result = f"💀 You lose! Dealer has **{dealer_name}**"
            color = discord.Color.red()
            won = False
        else:
            # Push - return bet
            economy_cog.add_coins(ctx.author.id, bet, "poker_push")
            payout = bet
            result = f"🤝 Push! Both have **{player_name}**"
            color = discord.Color.gold()
            won = False
        
        # Record game
        self.record_game(ctx.author.id, "poker", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "poker")
        
        # Create embed
        embed = discord.Embed(title="🃏 Poker Game", color=color)
        embed.add_field(name="Your Hand", value=" ".join([f"{card[0]}{card[1]}" for card in player_hand]), inline=False)
        embed.add_field(name="Your Rank", value=player_name, inline=True)
        embed.add_field(name="Dealer's Rank", value=dealer_name, inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        if payout > 0:
            embed.add_field(name="Payout", value=f"+{payout:,} coins", inline=True)
        embed.set_footer(text=f"New balance: {economy_cog.get_balance(ctx.author.id):,} coins")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="poker")
    async def poker_prefix(self, ctx, bet: int):
        """Play 5-card poker (L!poker <bet>)"""
        await ctx.send("❌ Poker requires interactive buttons! Please use `/poker <bet>` instead.")
    
    @app_commands.command(name="poker", description="Play 5-card poker (10-10,000 coins)")
    async def poker_slash(self, interaction: discord.Interaction, bet: int):
        """Play poker against the house"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await interaction.response.send_message("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Deal cards
        deck = self.create_deck()
        player_hand = [deck.pop() for _ in range(5)]
        dealer_hand = [deck.pop() for _ in range(5)]
        
        # Evaluate hands
        player_rank, player_name = self.evaluate_poker_hand(player_hand)
        dealer_rank, dealer_name = self.evaluate_poker_hand(dealer_hand)
        
        # Determine winner - reduced payouts
        if player_rank > dealer_rank:
            # Nerf: divide multiplier by 2 for less profit
            payout = bet * max(1.5, player_rank / 2)
            payout = int(payout)
            economy_cog.add_coins(interaction.user.id, payout, "poker_win")
            result = f"🎉 You win with **{player_name}**!"
            color = discord.Color.green()
            won = True
        elif player_rank < dealer_rank:
            payout = 0
            result = f"😔 Dealer wins with **{dealer_name}**"
            color = discord.Color.red()
            won = False
        else:
            # Tie - return bet
            economy_cog.add_coins(interaction.user.id, bet, "poker_tie")
            payout = bet
            result = f"🤝 Push! Both have **{player_name}**"
            color = discord.Color.gold()
            won = False
        
        # Record stats
        self.record_game(interaction.user.id, "poker", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "poker")
        
        # Create embed
        embed = discord.Embed(title="🃏 Poker", color=color)
        embed.add_field(name="Your Hand", value=self.format_hand(player_hand), inline=True)
        embed.add_field(name="Dealer Hand", value=self.format_hand(dealer_hand), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        if won:
            embed.add_field(name="Payout", value=f"+{payout:,} coins", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    def create_deck(self):
        """Create a standard 52-card deck"""
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck
    
    def format_hand(self, hand):
        """Format poker hand for display"""
        return ' '.join([f"{rank}{suit}" for rank, suit in hand])
    
    def evaluate_poker_hand(self, hand):
        """Evaluate poker hand strength (returns multiplier and name)"""
        ranks = [card[0] for card in hand]
        suits = [card[1] for card in hand]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        rank_counts = {r: ranks.count(r) for r in set(ranks)}
        counts = sorted(rank_counts.values(), reverse=True)
        
        is_flush = len(set(suits)) == 1
        sorted_values = sorted([rank_values[r] for r in ranks])
        is_straight = (sorted_values == list(range(sorted_values[0], sorted_values[0] + 5)) or 
                      sorted_values == [2, 3, 4, 5, 14])  # Ace-low straight
        
        # Royal Flush
        if is_flush and is_straight and sorted_values == [10, 11, 12, 13, 14]:
            return (10, "Royal Flush")
        # Straight Flush
        elif is_flush and is_straight:
            return (9, "Straight Flush")
        # Four of a Kind
        elif counts == [4, 1]:
            return (8, "Four of a Kind")
        # Full House
        elif counts == [3, 2]:
            return (7, "Full House")
        # Flush
        elif is_flush:
            return (6, "Flush")
        # Straight
        elif is_straight:
            return (5, "Straight")
        # Three of a Kind
        elif counts == [3, 1, 1]:
            return (4, "Three of a Kind")
        # Two Pair
        elif counts == [2, 2, 1]:
            return (3, "Two Pair")
        # Pair
        elif counts == [2, 1, 1, 1]:
            return (2, "Pair")
        # High Card
        else:
            return (1, "High Card")
    
    # ==================== SLOTS ====================
    
    @commands.command(name="slots")
    async def slots_prefix(self, ctx, bet: int):
        """Play slots (prefix version)"""
        await self._play_slots(ctx, bet, is_slash=False)
    
    @app_commands.command(name="slots", description="Spin the slot machine (10-5,000 coins)")
    async def slots_slash(self, interaction: discord.Interaction, bet: int):
        """Play slots (slash version)"""
        await self._play_slots(interaction, bet, is_slash=True)
    
    async def _play_slots(self, ctx_or_interaction, bet: int, is_slash: bool):
        """Core slots logic"""
        user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            msg = "❌ Economy system not loaded!"
            if is_slash:
                await ctx_or_interaction.response.send_message(msg)
            else:
                await ctx_or_interaction.send(msg)
            return
        
        # Validate bet
        if bet < 10 or bet > 5000:
            msg = "❌ Bet must be between 10 and 5,000 coins!"
            if is_slash:
                await ctx_or_interaction.response.send_message(msg)
            else:
                await ctx_or_interaction.send(msg)
            return
        
        balance = economy_cog.get_balance(user.id)
        if balance < bet:
            msg = f"❌ You only have {balance:,} coins!"
            if is_slash:
                await ctx_or_interaction.response.send_message(msg)
            else:
                await ctx_or_interaction.send(msg)
            return
        
        # Deduct bet
        economy_cog.economy_data[str(user.id)]["balance"] -= bet
        await economy_cog.save_economy()
        
        # Slot symbols - 5% win rate (extremely punishing luck-based game)
        symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '⭐', '💎', '7️⃣']
        weights = [50, 45, 40, 35, 10, 5, 2, 1]  # Extreme weighting - very hard to match
        
        # Force 5% win rate (95% guaranteed loss)
        win_roll = random.randint(1, 100)
        
        if win_roll <= 5:  # Only 5% chance to win
            # Force a winning combination
            rare_chance = random.randint(1, 100)
            if rare_chance <= 1:  # 1% of wins are jackpot
                reels = ['7️⃣', '7️⃣', '7️⃣']
            elif rare_chance <= 5:  # 4% of wins are diamonds
                reels = ['💎', '💎', '💎']
            elif rare_chance <= 15:  # 10% of wins are stars
                reels = ['⭐', '⭐', '⭐']
            elif rare_chance <= 35:  # 20% of wins are bells
                reels = ['🔔', '🔔', '🔔']
            else:  # 65% of wins are common symbols
                symbol = random.choice(['🍒', '🍋', '🍊', '🍇'])
                reels = [symbol, symbol, symbol]
        else:
            # Force a losing combination (90% of the time)
            reels = random.choices(symbols, weights=weights, k=3)
            # Make sure they don't all match by chance
            while reels[0] == reels[1] == reels[2]:
                reels = random.choices(symbols, weights=weights, k=3)
        
        # Calculate payout
        payout = 0
        won = False
        result_text = ""
        
        if reels[0] == reels[1] == reels[2]:
            # All match!
            symbol = reels[0]
            if symbol == '7️⃣':
                payout = bet * 30  # Reduced from 50x
                result_text = "🎰 **JACKPOT!** 🎰"
            elif symbol == '💎':
                payout = bet * 15  # Reduced from 25x
                result_text = "💎 **DIAMOND TRIPLE!** 💎"
            elif symbol == '⭐':
                payout = bet * 8  # Reduced from 15x
                result_text = "⭐ **STAR TRIPLE!** ⭐"
            elif symbol == '🔔':
                payout = bet * 5  # Reduced from 8x
                result_text = "🔔 **BELL TRIPLE!** 🔔"
            else:
                payout = bet * 2  # Reduced from 3x
                result_text = f"✨ **TRIPLE {symbol}!** ✨"
            won = True
        else:
            result_text = "💀 **NO MATCH** 💀"
        
        # Record stats
        self.record_game(user.id, "slots", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(user.id, "slots")
        if won:
            economy_cog.add_coins(user.id, payout, "slots_win")
        
        # Create embed
        color = discord.Color.gold() if won else discord.Color.red()
        embed = discord.Embed(title="🎰 Slot Machine", color=color)
        embed.add_field(name="Spin Result", value=f"╔═══════╗\n║ {reels[0]} {reels[1]} {reels[2]} ║\n╚═══════╝", inline=False)
        embed.add_field(name="Result", value=result_text, inline=False)
        
        if won:
            embed.add_field(name="Payout", value=f"+{payout:,} coins", inline=False)
        else:
            embed.add_field(name="Lost", value=f"-{bet:,} coins", inline=False)
        
        if is_slash:
            await ctx_or_interaction.response.send_message(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    # ==================== ROULETTE ====================
    
    @commands.command(name="roulette")
    async def roulette_prefix(self, ctx, bet: int, choice: str):
        """Spin the roulette wheel (L!roulette <bet> <red/black/odd/even/0-36>)"""
        await ctx.send("💡 For the best experience, use `/roulette <bet> <choice>` instead!")
    
    @app_commands.command(name="roulette", description="Spin the roulette wheel (10-10,000 coins)")
    async def roulette_slash(self, interaction: discord.Interaction, bet: int, choice: str):
        """Play roulette"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await interaction.response.send_message("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Valid choices
        valid_choices = {
            "red": ["1", "3", "5", "7", "9", "12", "14", "16", "18", "19", "21", "23", "25", "27", "30", "32", "34", "36"],
            "black": ["2", "4", "6", "8", "10", "11", "13", "15", "17", "20", "22", "24", "26", "28", "29", "31", "33", "35"],
            "green": ["0"],
            "odd": [str(i) for i in range(1, 37, 2)],
            "even": [str(i) for i in range(2, 37, 2)],
            "low": [str(i) for i in range(1, 19)],
            "high": [str(i) for i in range(19, 37)]
        }
        
        choice = choice.lower()
        
        # Check if choice is a number
        if choice.isdigit():
            if int(choice) < 0 or int(choice) > 36:
                await interaction.response.send_message("❌ Number must be between 0-36!")
                return
            chosen_numbers = [choice]
            payout_mult = 10  # Reduced from 20x - pure luck shouldn't pay much
        elif choice in valid_choices:
            chosen_numbers = valid_choices[choice]
            payout_mult = 1.5  # Reduced from 1.8x - barely profitable
        else:
            await interaction.response.send_message("❌ Invalid choice! Use: red, black, green, odd, even, low, high, or 0-36")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Spin the wheel with extreme house edge (5% win rate - luck-based game)
        # Dramatically increase chance of green (0) appearing
        wheel_roll = random.randint(1, 100)
        if wheel_roll <= 50:  # 50% chance of 0 (house always wins)
            result = "0"
        else:
            result = str(random.randint(1, 36))
        
        # Determine color
        if result in valid_choices["red"]:
            color_result = "🔴 Red"
            color_embed = discord.Color.red()
        elif result in valid_choices["black"]:
            color_result = "⚫ Black"
            color_embed = discord.Color.dark_gray()
        else:
            color_result = "🟢 Green"
            color_embed = discord.Color.green()
        
        # Check if won
        if result in chosen_numbers:
            payout = int(bet * payout_mult)  # Ensure integer payout
            economy_cog.add_coins(interaction.user.id, payout, "roulette_win")
            result_text = f"🎉 **YOU WIN!**\n+{payout:,} coins"
            won = True
        else:
            payout = 0
            result_text = f"💀 **YOU LOSE!**\n-{bet:,} coins"
            won = False
        
        # Record stats
        self.record_game(interaction.user.id, "roulette", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "roulette")
        # Create embed
        embed = discord.Embed(title="🎡 Roulette", color=color_embed)
        embed.add_field(name="Your Bet", value=f"{choice.title()} ({bet:,} coins)", inline=False)
        embed.add_field(name="Result", value=f"**{result}** {color_result}", inline=False)
        embed.add_field(name="Outcome", value=result_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== HIGHER/LOWER ====================
    
    @commands.command(name="higherlower", aliases=["hl"])
    async def higherlower_prefix(self, ctx, bet: int):
        """Guess if next card is higher or lower (L!higherlower <bet>)"""
        await ctx.send("❌ Higher/Lower requires interactive buttons! Please use `/higherlower <bet>` instead.")
    
    @app_commands.command(name="higherlower", description="Guess if next card is higher or lower (10-10,000 coins)")
    async def higherlower(self, interaction: discord.Interaction, bet: int):
        """Play higher or lower"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await interaction.response.send_message("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Draw first card
        deck = self.create_deck()
        first_card = deck.pop()
        
        embed = discord.Embed(
            title="🎴 Higher or Lower",
            description=f"**Current Card:** {first_card[0]}{first_card[1]}\n\nWill the next card be **Higher** or **Lower**?",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click a button to make your choice!")
        
        # Create view with buttons
        view = HigherLowerView(self, interaction.user, bet, first_card, deck)
        
        await interaction.response.send_message(embed=embed, view=view)
        # Update most played games (on game start)
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "higherlower")
    
    # ==================== STATS & INFO ====================
    
    @commands.command(name="gambling_stats", aliases=["gamblingstats", "gstats"])
    async def gambling_stats_prefix(self, ctx, user: Optional[discord.Member] = None):
        """View gambling statistics (L!gambling_stats [user])"""
        await self._show_gambling_stats(ctx, user, is_slash=False)
    
    @app_commands.command(name="gambling_stats", description="View your gambling statistics")
    async def gambling_stats_slash(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """View gambling statistics"""
        await self._show_gambling_stats(interaction, user, is_slash=True)
    
    async def _show_gambling_stats(self, ctx_or_interaction, user, is_slash):
        """Internal method to show gambling stats"""
        requester = self._get_user(ctx_or_interaction, is_slash)
        target = user or requester
        user_key = str(target.id)
        
        if user_key not in self.gambling_stats:
            await self._send_message(ctx_or_interaction, f"❌ {target.mention} hasn't played any gambling games yet!", is_slash=is_slash)
            return
        
        stats = self.gambling_stats[user_key]
        
        embed = discord.Embed(
            title=f"🎰 {target.display_name}'s Gambling Stats",
            color=discord.Color.gold()
        )
        
        # Overall stats
        net_profit = stats["total_won"] - stats["total_lost"]
        win_rate = (stats["total_won"] / stats["total_wagered"] * 100) if stats["total_wagered"] > 0 else 0
        
        embed.add_field(
            name="📊 Overall",
            value=f"**Games Played:** {stats['total_games']:,}\n"
                  f"**Total Wagered:** {stats['total_wagered']:,} coins\n"
                  f"**Total Won:** {stats['total_won']:,} coins\n"
                  f"**Total Lost:** {stats['total_lost']:,} coins\n"
                  f"**Net Profit:** {net_profit:,} coins\n"
                  f"**Win Rate:** {win_rate:.1f}%",
            inline=False
        )
        
        # Game breakdown
        if stats["games"]:
            game_text = []
            for game, game_stats in stats["games"].items():
                win_pct = (game_stats["won"] / game_stats["played"] * 100) if game_stats["played"] > 0 else 0
                game_text.append(f"**{game.title()}:** {game_stats['played']} played ({game_stats['won']}W/{game_stats['lost']}L) - {win_pct:.0f}% WR")
            
            embed.add_field(
                name="🎮 By Game",
                value="\n".join(game_text),
                inline=False
            )
        
        await self._send_message(ctx_or_interaction, embed=embed, is_slash=is_slash)
    
    @commands.command(name="odds")
    async def odds_prefix(self, ctx):
        """View gambling game odds and payouts (L!odds)"""
        await self._show_odds(ctx, is_slash=False)
    
    @app_commands.command(name="odds", description="View gambling game odds and payouts")
    async def odds_slash(self, interaction: discord.Interaction):
        """Show odds for all gambling games"""
        await self._show_odds(interaction, is_slash=True)
    
    async def _show_odds(self, ctx_or_interaction, is_slash):
        """Internal method to show gambling odds"""
        embed = discord.Embed(
            title="🎲 Gambling Odds & Payouts",
            description="All games have varying odds and payouts!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🃏 Poker",
            value="**Payouts:**\n"
                  "Royal Flush: 10x\n"
                  "Straight Flush: 9x\n"
                  "Four of a Kind: 8x\n"
                  "Full House: 7x\n"
                  "Flush: 6x\n"
                  "Straight: 5x\n"
                  "Three of a Kind: 4x\n"
                  "Two Pair: 3x\n"
                  "Pair: 2x\n"
                  "High Card: 1x",
            inline=True
        )
        
        embed.add_field(
            name="🎰 Slots",
            value="**Payouts:**\n"
                  "7️⃣ Triple: 50x 🎰\n"
                  "💎 Triple: 30x\n"
                  "⭐ Triple: 20x\n"
                  "🔔 Triple: 15x\n"
                  "Other Triple: 10x\n"
                  "Double Match: 2x",
            inline=True
        )
        
        embed.add_field(
            name="🎡 Roulette",
            value="**Payouts:**\n"
                  "Single Number: 36x\n"
                  "Red/Black: 2x\n"
                  "Odd/Even: 2x\n"
                  "Low/High: 2x\n"
                  "Green (0): 36x",
            inline=True
        )
        
        embed.add_field(
            name="🎴 Higher/Lower",
            value="**Payout:** 2x\n"
                  "**Odds:** ~50/50\n"
                  "(Tie = loss)",
            inline=True
        )
        
        embed.add_field(
            name="♠️ Blackjack",
            value="**Payouts:**\n"
                  "Blackjack: 2.5x\n"
                  "Win: 2x\n"
                  "Push: 1x (return bet)",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ War",
            value="**Payout:** 2x\n"
                  "**Odds:** ~50/50\n"
                  "(Tie = war)",
            inline=True
        )
        
        embed.set_footer(text="💡 Tip: Higher risk = Higher reward!")
        
        await self._send_message(ctx_or_interaction, embed=embed, is_slash=is_slash)
    
    @commands.command(name="strategy", aliases=["strat"])
    async def strategy_prefix(self, ctx, game: str):
        """Get strategy tips for gambling games (L!strategy <game>)"""
        await self._show_strategy(ctx, game, is_slash=False)
    
    @app_commands.command(name="strategy", description="Get strategy tips for gambling games")
    async def strategy_slash(self, interaction: discord.Interaction, game: str):
        """Show strategy for a game"""
        await self._show_strategy(interaction, game, is_slash=True)
    
    async def _show_strategy(self, ctx_or_interaction, game, is_slash):
        """Internal method to show game strategy"""
        game = game.lower()
        
        strategies = {
            "poker": {
                "title": "🃏 Poker Strategy",
                "tips": [
                    "**Hand Rankings:** Royal Flush > Straight Flush > Four of a Kind > Full House > Flush > Straight > Three of a Kind > Two Pair > Pair > High Card",
                    "**Odds:** You're playing against the dealer, higher hand wins",
                    "**Best Hands:** Aim for flushes and straights for consistent wins",
                    "**Variance:** High - big swings possible with royal flushes"
                ]
            },
            "slots": {
                "title": "🎰 Slots Strategy",
                "tips": [
                    "**Pure Luck:** No strategy affects outcome",
                    "**Jackpot:** 7️⃣ triple pays 50x but is extremely rare",
                    "**Bet Management:** Smaller bets = longer playtime",
                    "**Doubles:** Most common win (2x payout)"
                ]
            },
            "roulette": {
                "title": "🎡 Roulette Strategy",
                "tips": [
                    "**Even Money Bets:** Red/Black, Odd/Even, Low/High (2x payout, ~48% chance)",
                    "**Single Numbers:** 36x payout but only 1/37 chance",
                    "**Martingale:** Double bet after loss (risky!)",
                    "**Safest:** Stick to even money bets for consistent play"
                ]
            },
            "higherlower": {
                "title": "🎴 Higher/Lower Strategy",
                "tips": [
                    "**Low Cards (2-7):** Bet HIGHER",
                    "**High Cards (9-A):** Bet LOWER",
                    "**Middle Cards (8):** 50/50 - pure gamble",
                    "**Ties:** Count as losses, avoid middle cards"
                ]
            },
            "blackjack": {
                "title": "♠️ Blackjack Strategy",
                "tips": [
                    "**Hit on 11 or less:** Always safe",
                    "**Stand on 17 or more:** Risk of busting",
                    "**12-16:** Difficult zone, consider dealer's card",
                    "**Doubles and Splits:** Not available in this version"
                ]
            }
        }
        
        if game not in strategies:
            await self._send_message(
                ctx_or_interaction,
                f"❌ No strategy available for '{game}'!\n"
                f"Available games: poker, slots, roulette, higherlower, blackjack",
                is_slash=is_slash
            )
            return
        
        strategy = strategies[game]
        
        embed = discord.Embed(
            title=strategy["title"],
            description="Here are some tips to improve your odds:",
            color=discord.Color.blue()
        )
        
        for i, tip in enumerate(strategy["tips"], 1):
            embed.add_field(name=f"Tip #{i}", value=tip, inline=False)
        
        embed.set_footer(text="Remember: The house always has an edge! Gamble responsibly.")
        
        await self._send_message(ctx_or_interaction, embed=embed, is_slash=is_slash)

    # ==================== DICE ROLL GAMBLING ====================
    
    @commands.command(name="dicegamble", aliases=["dicebet"])
    async def dice_gamble_prefix(self, ctx, bet: int, target: int):
        """Bet on dice roll outcome (L!dicegamble <bet> <number 1-6>)"""
        # Dice doesn't need buttons, so just call the actual game logic
        # We'll treat ctx like an interaction for this simple game
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await ctx.send("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        # Validate target
        if target < 1 or target > 6:
            await ctx.send("❌ Target must be between 1 and 6!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < bet:
            await ctx.send(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(ctx.author.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Roll dice
        roll = random.randint(1, 6)
        
        # Determine result
        dice_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        
        if roll == target:
            # Exact match - 6x payout!
            payout = bet * 6
            economy_cog.add_coins(ctx.author.id, payout, "dice_win")
            result_text = f"🎉 **EXACT MATCH!**\n+{payout:,} coins (6x)"
            color = discord.Color.gold()
            won = True
        else:
            payout = 0
            result_text = f"💀 **NO MATCH!**\n-{bet:,} coins"
            color = discord.Color.red()
            won = False
        
        # Record stats
        self.record_game(ctx.author.id, "dice", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "dice")
        
        # Create embed
        embed = discord.Embed(title="🎲 Dice Gamble", color=color)
        embed.add_field(name="Your Bet", value=f"Number {target}", inline=True)
        embed.add_field(name="Roll Result", value=f"{dice_emoji[roll-1]} **{roll}**", inline=True)
        embed.add_field(name="Outcome", value=result_text, inline=False)
        embed.set_footer(text="Exact number = 6x payout!")
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="dicegamble", description="Bet on dice roll outcome (10-10,000 coins)")
    async def dice_gamble_slash(self, interaction: discord.Interaction, bet: int, target: int):
        """Gamble on dice roll - guess the number (1-6) for 6x payout, or bet on odd/even for 2x"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await interaction.response.send_message("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        # Validate target (1-6 for exact number)
        if target < 1 or target > 6:
            await interaction.response.send_message("❌ Target must be between 1 and 6!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Roll dice
        roll = random.randint(1, 6)
        
        # Determine result
        dice_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        
        if roll == target:
            # Exact match - 4x payout (nerfed from 6x)
            payout = bet * 4
            economy_cog.add_coins(interaction.user.id, payout, "dice_win")
            result_text = f"🎉 **EXACT MATCH!**\n+{payout:,} coins (4x)"
            color = discord.Color.gold()
            won = True
        else:
            payout = 0
            result_text = f"💀 **NO MATCH!**\n-{bet:,} coins"
            color = discord.Color.red()
            won = False
        
        # Record stats
        self.record_game(interaction.user.id, "dice", bet, won, payout)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "dice")
        
        # Create embed
        embed = discord.Embed(title="🎲 Dice Gamble", color=color)
        embed.add_field(name="Your Bet", value=f"Number {target}", inline=True)
        embed.add_field(name="Roll Result", value=f"{dice_emoji[roll-1]} **{roll}**", inline=True)
        embed.add_field(name="Outcome", value=result_text, inline=False)
        embed.set_footer(text="Exact number = 4x payout!")
        
        await interaction.response.send_message(embed=embed)

    # ==================== CRASH GAME ====================
    
    @commands.command(name="crash")
    async def crash_prefix(self, ctx, bet: int):
        """Multiplier crash game - cash out before it crashes! (L!crash <bet>)"""
        await ctx.send("❌ Crash game requires interactive buttons! Please use `/crash <bet>` instead.")
    
    @app_commands.command(name="crash", description="Multiplier crash game - cash out before it crashes! (10-10,000)")
    async def crash_slash(self, interaction: discord.Interaction, bet: int):
        """Play crash game"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 10000:
            await interaction.response.send_message("❌ Bet must be between 10 and 10,000 coins!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Generate crash point (weighted)
        crash_multiplier = self.generate_crash_multiplier()
        
        # Create game view
        view = CrashView(self, interaction.user, bet, crash_multiplier)
        
        embed = discord.Embed(
            title="📈 Crash Game Starting...",
            description=f"**Your Bet:** {bet:,} coins\n\n**Current Multiplier:** 1.00x\n\nCash out before it crashes!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Click 'Cash Out' to claim your winnings!")
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Start the crash sequence
        await view.start_crash(interaction)
    
    def generate_crash_multiplier(self):
        """Generate a crash multiplier with weighted probability - heavily nerfed"""
        # Generate using exponential-like distribution
        # Lower multipliers MUCH more common - house always wins
        rand = random.random()
        
        if rand < 0.65:  # 65% crash below 1.5x (increased from 50%)
            return round(random.uniform(1.01, 1.49), 2)
        elif rand < 0.85:  # 20% crash 1.5x-3x (reduced from 25%)
            return round(random.uniform(1.50, 2.99), 2)
        elif rand < 0.95:  # 10% crash 3x-6x (reduced from 15%)
            return round(random.uniform(3.00, 5.99), 2)
        elif rand < 0.99:  # 4% crash 6x-10x (reduced from 7%)
            return round(random.uniform(6.00, 9.99), 2)
        else:  # 1% crash above 10x (reduced from 3%)
            return round(random.uniform(10.00, 25.00), 2)
    
    # ==================== MINES ====================
    
    @commands.command(name="mines")
    async def mines_prefix(self, ctx, bet: int, mine_count: int = 8):
        """Minesweeper gambling - reveal tiles without hitting mines! (L!mines <bet> [mines])"""
        await ctx.send("❌ Mines game requires interactive buttons! Please use `/mines <bet> [mine_count]` instead.")
    
    @app_commands.command(name="mines", description="Minesweeper gambling - reveal tiles without hitting mines! (10-5,000)")
    async def mines_slash(self, interaction: discord.Interaction, bet: int, mine_count: int = 8):
        """Play mines game"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!")
            return
        
        # Validate bet
        if bet < 10 or bet > 5000:
            await interaction.response.send_message("❌ Bet must be between 10 and 5,000 coins!")
            return
        
        # Validate mine count (max 18 for 4x5 grid = 20 tiles)
        if mine_count < 1 or mine_count > 18:
            await interaction.response.send_message("❌ Mine count must be between 1 and 18!")
            return
        
        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(f"❌ You only have {balance:,} coins!")
            return
        
        # Deduct bet
        economy_cog.economy_data[str(interaction.user.id)]["balance"] -= bet
        economy_cog.save_economy()
        
        # Create mines game view
        view = MinesView(self, interaction.user, bet, mine_count)
        
        embed = discord.Embed(
            title="💣 Mines Game (4x5 Grid)",
            description=f"**Your Bet:** {bet:,} coins\n"
                       f"**Mines:** {view.mine_count}/20\n"
                       f"**Safe Tiles:** {view.safe_tiles}\n\n"
                       f"**Current Multiplier:** 1.00x\n"
                       f"**Potential Win:** {bet:,} coins\n\n"
                       f"Click tiles to reveal! Avoid the mines!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Cash out anytime or keep going for higher multipliers!")
        
        await interaction.response.send_message(embed=embed, view=view)

    # ==================== COINFLIP ====================
    
    @commands.command(name="coinflip", aliases=["cf", "flip"])
    async def coinflip_prefix(self, ctx, side: str, wager: int):
        """Flip a coin - Double or nothing! Usage: L!coinflip heads 1000"""
        await self._coinflip(ctx.author.id, ctx.author.display_name, side.lower(), wager, ctx=ctx)
    
    @app_commands.command(name="coinflip", description="Flip a coin - Double or nothing!")
    @app_commands.describe(
        side="Choose heads or tails",
        wager="Amount to wager (10 - 1,000,000 PsyCoins)"
    )
    @app_commands.choices(side=[
        app_commands.Choice(name="🪙 Heads", value="heads"),
        app_commands.Choice(name="🪙 Tails", value="tails"),
    ])
    async def coinflip_slash(self, interaction: discord.Interaction, side: str, wager: int):
        """Coinflip gambling game (slash version)"""
        await self._coinflip(interaction.user.id, interaction.user.display_name, side, wager, interaction=interaction)
    
    async def _coinflip(self, user_id, display_name, side, wager, ctx=None, interaction=None):
        """Shared coinflip logic"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            msg = "❌ Economy system not loaded!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Validate side
        if side not in ["heads", "tails", "h", "t"]:
            msg = "❌ Choose heads or tails!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Normalize side
        if side == "h":
            side = "heads"
        elif side == "t":
            side = "tails"
        
        # Validate wager
        if wager < 10:
            msg = "❌ Minimum wager is 10 PsyCoins!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        if wager > 1000000:
            msg = "❌ Maximum wager is 1,000,000 PsyCoins!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        balance = economy_cog.get_balance(user_id)
        if balance < wager:
            msg = f"❌ You only have {balance:,} PsyCoins!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Deduct wager
        if not economy_cog.remove_coins(user_id, wager):
            msg = "❌ Failed to place wager!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Flip coin
        result = random.choice(["heads", "tails"])
        won = result == side
        
        # Coin flip animation
        embed = discord.Embed(
            title="🪙 Coinflip",
            description=f"**Your Choice:** {side.title()}\n"
                       f"**Wager:** {wager:,} PsyCoins\n\n"
                       "🌀 *Flipping...*",
            color=discord.Color.gold()
        )
        
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            msg = await ctx.send(embed=embed)
        
        await asyncio.sleep(2)
        
        if won:
            payout = wager * 2
            economy_cog.add_coins(user_id, payout, "coinflip_win")
            
            embed = discord.Embed(
                title="🎉 Coinflip - YOU WON!",
                description=f"**Result:** {result.title()} 🪙\n"
                           f"**Your Choice:** {side.title()}\n\n"
                           f"**Wager:** {wager:,} PsyCoins\n"
                           f"**Payout:** {payout:,} PsyCoins\n"
                           f"**Profit:** +{wager:,} PsyCoins! 💰",
                color=discord.Color.green()
            )
            
            # Record win
            self.record_game(user_id, "coinflip", wager, True, payout)
            # Update most played games
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "profile_manager"):
                profile_cog.profile_manager.record_game_played(user_id, "coinflip")
            
            # Check for zoo encounter
            zoo_cog = self.bot.get_cog("Zoo")
            if zoo_cog:
                encounter = zoo_cog.trigger_encounter(user_id, "gambling")
                if encounter:
                    animal = encounter["animal"]
                    new_text = "**NEW!**" if encounter["is_new"] else f"(#{encounter['count']})"
                    embed.add_field(
                        name="🦁 Wild Animal Found!",
                        value=f"{animal['name']} {new_text}\n*{animal['description']}*\nCheck `/zoo`!",
                        inline=False
                    )
        else:
            embed = discord.Embed(
                title="💸 Coinflip - You Lost",
                description=f"**Result:** {result.title()} 🪙\n"
                           f"**Your Choice:** {side.title()}\n\n"
                           f"**Lost:** {wager:,} PsyCoins",
                color=discord.Color.red()
            )
            
            # Record loss
            self.record_game(user_id, "coinflip", wager, False, 0)
            # Update most played games
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "profile_manager"):
                profile_cog.profile_manager.record_game_played(user_id, "coinflip")
        
        # Show new balance
        new_balance = economy_cog.get_balance(user_id)
        embed.set_footer(text=f"Balance: {new_balance:,} PsyCoins")
        
        if interaction:
            await interaction.edit_original_response(embed=embed)
        else:
            await msg.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(Gambling(bot))