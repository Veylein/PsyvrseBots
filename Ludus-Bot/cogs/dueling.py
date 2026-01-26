import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio
from datetime import datetime
from typing import Optional

class Dueling(commands.Cog):
    """Challenge other players to duels with coin bets"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_duels = {}  # duel_id: Duel object
        self.spectator_bets = {}  # duel_id: {user_id: {target, amount}}
        self.file_path = "cogs/duel_history.json"
        self.load_history()
        
        # Available duel games
        self.duel_games = {
            "rps": "Rock Paper Scissors",
            "coinflip": "Coin Flip",
            "dice": "Dice Roll (highest wins)",
            "highlow": "High-Low Card Game",
            "quickdraw": "Quick Draw (fastest reaction)"
        }
    
    def load_history(self):
        """Load duel history"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.duel_history = json.load(f)
        else:
            self.duel_history = {}
    
    def save_history(self):
        """Save duel history"""
        with open(self.file_path, 'w') as f:
            json.dump(self.duel_history, f, indent=4)
    
    def log_duel(self, duel_data):
        """Log completed duel"""
        duel_id = str(len(self.duel_history) + 1)
        self.duel_history[duel_id] = {
            **duel_data,
            'timestamp': datetime.now().isoformat()
        }
        self.save_history()
    
    class DuelSession:
        """Represents an active duel"""
        def __init__(self, challenger, opponent, game_type, bet_amount):
            self.challenger = challenger
            self.opponent = opponent
            self.game_type = game_type
            self.bet_amount = bet_amount
            self.channel = None
            self.active = True
            self.spectators_can_bet = True
            self.start_time = datetime.now()
        
        def get_embed(self, status="waiting"):
            """Create duel status embed"""
            embed = discord.Embed(
                title="⚔️ Duel Challenge!",
                description=f"{self.challenger.mention} challenges {self.opponent.mention}",
                color=discord.Color.red()
            )
            
            embed.add_field(name="Game", value=self.game_type, inline=True)
            embed.add_field(name="Bet", value=f"{self.bet_amount:,} PsyCoins", inline=True)
            embed.add_field(name="Status", value=status, inline=True)
            
            if self.spectators_can_bet:
                embed.add_field(
                    name="🎲 Spectators",
                    value="Spectators can bet on the outcome!\nUse `L!bet <player> <amount>`",
                    inline=False
                )
            
            return embed
    
    @commands.group(name="duel", invoke_without_command=True)
    async def duel(self, ctx, opponent: discord.Member, game: str = "rps", bet: int = 100):
        """Challenge someone to a duel with a coin bet"""
        if opponent.bot:
            await ctx.send("❌ You can't duel bots!")
            return
        
        if opponent.id == ctx.author.id:
            await ctx.send("❌ You can't duel yourself!")
            return
        
        if bet < 10:
            await ctx.send("❌ Minimum bet is 10 PsyCoins!")
            return
        
        if bet > 100000:
            await ctx.send("❌ Maximum bet is 100,000 PsyCoins!")
            return
        
        # Validate game type
        game = game.lower()
        if game not in self.duel_games:
            await ctx.send(f"❌ Invalid game! Choose from: {', '.join(self.duel_games.keys())}")
            return
        
        # Check if users have enough coins
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        challenger_balance = economy_cog.get_balance(ctx.author.id)
        opponent_balance = economy_cog.get_balance(opponent.id)
        
        if challenger_balance < bet:
            await ctx.send(f"❌ You don't have enough coins! Balance: {challenger_balance:,}")
            return
        
        if opponent_balance < bet:
            await ctx.send(f"❌ {opponent.mention} doesn't have enough coins for this bet!")
            return
        
        # Create duel session
        duel = self.DuelSession(ctx.author, opponent, self.duel_games[game], bet)
        duel.channel = ctx.channel
        
        embed = duel.get_embed("Waiting for opponent...")
        embed.set_footer(text=f"{opponent.display_name}, react with ⚔️ to accept or ❌ to decline")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user.id == opponent.id and str(reaction.emoji) in ["⚔️", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "⚔️":
                # Start the duel!
                duel_id = f"{ctx.author.id}_{opponent.id}_{int(asyncio.get_event_loop().time())}"
                self.active_duels[duel_id] = duel
                self.spectator_bets[duel_id] = {}
                
                await ctx.send(f"⚔️ **DUEL ACCEPTED!** Spectators have 10 seconds to place bets!")
                await asyncio.sleep(10)
                
                duel.spectators_can_bet = False
                
                # Play the game
                await self.play_duel(ctx, duel_id, duel, game)
            else:
                await ctx.send(f"❌ {opponent.mention} declined the duel.")
                
        except asyncio.TimeoutError:
            await ctx.send(f"⏱️ Duel request expired. {opponent.mention} didn't respond.")
    
    async def play_duel(self, ctx, duel_id, duel, game):
        """Play the actual duel game"""
        if game == "rps":
            await self.play_rps(ctx, duel_id, duel)
        elif game == "coinflip":
            await self.play_coinflip(ctx, duel_id, duel)
        elif game == "dice":
            await self.play_dice(ctx, duel_id, duel)
        elif game == "highlow":
            await self.play_highlow(ctx, duel_id, duel)
        elif game == "quickdraw":
            await self.play_quickdraw(ctx, duel_id, duel)
    
    async def play_rps(self, ctx, duel_id, duel):
        """Rock Paper Scissors duel"""
        await ctx.send(f"🎮 **Rock Paper Scissors!**\n{duel.challenger.mention} and {duel.opponent.mention}, DM me your choice!")
        
        choices = {}
        
        # Get choices via DM
        for player in [duel.challenger, duel.opponent]:
            try:
                dm_channel = await player.create_dm()
                await dm_channel.send("Choose: **rock**, **paper**, or **scissors**")
                
                def check(m):
                    return m.author.id == player.id and m.channel == dm_channel and m.content.lower() in ['rock', 'paper', 'scissors']
                
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                choices[player.id] = msg.content.lower()
                await dm_channel.send(f"✅ You chose **{msg.content}**!")
            except asyncio.TimeoutError:
                await ctx.send(f"⏱️ {player.mention} took too long! They forfeit!")
                winner = duel.opponent if player == duel.challenger else duel.challenger
                await self.resolve_duel(ctx, duel_id, duel, winner, "timeout")
                return
            except Exception as e:
                await ctx.send(f"❌ Error getting choice from {player.mention}: {e}")
                return
        
        # Determine winner
        c1 = choices[duel.challenger.id]
        c2 = choices[duel.opponent.id]
        
        await ctx.send(f"🎮 {duel.challenger.mention} chose **{c1}**!\n🎮 {duel.opponent.mention} chose **{c2}**!")
        
        if c1 == c2:
            await ctx.send("🤝 It's a tie! Bets are returned.")
            await self.resolve_duel(ctx, duel_id, duel, None, "tie")
        elif (c1 == "rock" and c2 == "scissors") or (c1 == "scissors" and c2 == "paper") or (c1 == "paper" and c2 == "rock"):
            await self.resolve_duel(ctx, duel_id, duel, duel.challenger, "won")
        else:
            await self.resolve_duel(ctx, duel_id, duel, duel.opponent, "won")
    
    async def play_coinflip(self, ctx, duel_id, duel):
        """Coin flip duel"""
        await ctx.send(f"🪙 **Coin Flip!**\n{duel.challenger.mention}, call it! Type **heads** or **tails**")
        
        def check(m):
            return m.author.id == duel.challenger.id and m.channel == ctx.channel and m.content.lower() in ['heads', 'tails']
        
        try:
            msg = await self.bot.wait_for('message', timeout=15.0, check=check)
            call = msg.content.lower()
            
            result = random.choice(['heads', 'tails'])
            
            await ctx.send(f"🪙 Flipping...")
            await asyncio.sleep(2)
            await ctx.send(f"🪙 **{result.upper()}!**")
            
            if call == result:
                await self.resolve_duel(ctx, duel_id, duel, duel.challenger, "won")
            else:
                await self.resolve_duel(ctx, duel_id, duel, duel.opponent, "won")
                
        except asyncio.TimeoutError:
            await ctx.send(f"⏱️ {duel.challenger.mention} took too long! They forfeit!")
            await self.resolve_duel(ctx, duel_id, duel, duel.opponent, "forfeit")
    
    async def play_dice(self, ctx, duel_id, duel):
        """Dice roll duel - highest wins"""
        await ctx.send(f"🎲 **Dice Duel!** Highest roll wins!\n\nRolling...")
        await asyncio.sleep(2)
        
        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)
        
        await ctx.send(f"🎲 {duel.challenger.mention} rolled **{roll1}**!\n🎲 {duel.opponent.mention} rolled **{roll2}**!")
        
        if roll1 > roll2:
            await self.resolve_duel(ctx, duel_id, duel, duel.challenger, "won")
        elif roll2 > roll1:
            await self.resolve_duel(ctx, duel_id, duel, duel.opponent, "won")
        else:
            await ctx.send("🤝 It's a tie! Bets are returned.")
            await self.resolve_duel(ctx, duel_id, duel, None, "tie")
    
    async def play_highlow(self, ctx, duel_id, duel):
        """High-low card game"""
        cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        card_values = {card: i for i, card in enumerate(cards, start=2)}
        
        await ctx.send(f"🃏 **High-Low Card Game!** Higher card wins!")
        await asyncio.sleep(2)
        
        card1 = random.choice(cards)
        card2 = random.choice(cards)
        
        await ctx.send(f"🃏 {duel.challenger.mention} drew **{card1}**!\n🃏 {duel.opponent.mention} drew **{card2}**!")
        
        if card_values[card1] > card_values[card2]:
            await self.resolve_duel(ctx, duel_id, duel, duel.challenger, "won")
        elif card_values[card2] > card_values[card1]:
            await self.resolve_duel(ctx, duel_id, duel, duel.opponent, "won")
        else:
            await ctx.send("🤝 It's a tie! Bets are returned.")
            await self.resolve_duel(ctx, duel_id, duel, None, "tie")
    
    async def play_quickdraw(self, ctx, duel_id, duel):
        """Quick draw - first to react wins"""
        await ctx.send("⏳ Get ready for **QUICK DRAW**...")
        await asyncio.sleep(random.uniform(2, 5))
        
        message = await ctx.send("🔫 **DRAW!** First to react wins!")
        await message.add_reaction("🔫")
        
        def check(reaction, user):
            return user.id in [duel.challenger.id, duel.opponent.id] and str(reaction.emoji) == "🔫" and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0, check=check)
            winner = duel.challenger if user.id == duel.challenger.id else duel.opponent
            await ctx.send(f"⚡ {winner.mention} was faster!")
            await self.resolve_duel(ctx, duel_id, duel, winner, "won")
        except asyncio.TimeoutError:
            await ctx.send("❌ Nobody reacted! Tie!")
            await self.resolve_duel(ctx, duel_id, duel, None, "tie")
    
    async def resolve_duel(self, ctx, duel_id, duel, winner, result):
        """Resolve the duel and distribute winnings"""
        economy_cog = self.bot.get_cog("Economy")
        
        if result == "tie":
            # Return bets
            await ctx.send("💰 Bets returned to both players.")
            # Return spectator bets
            if duel_id in self.spectator_bets:
                for user_id, bet_data in self.spectator_bets[duel_id].items():
                    economy_cog.add_coins(user_id, bet_data['amount'], "bet_returned")
        
        elif result in ["won", "forfeit", "timeout"]:
            loser = duel.opponent if winner == duel.challenger else duel.challenger
            
            # Transfer bet amounts
            economy_cog.remove_coins(duel.challenger.id, duel.bet_amount, "duel_bet")
            economy_cog.remove_coins(duel.opponent.id, duel.bet_amount, "duel_bet")
            economy_cog.add_coins(winner.id, duel.bet_amount * 2, "duel_win")
            
            # Process spectator bets
            total_spectator_winnings = 0
            if duel_id in self.spectator_bets:
                for user_id, bet_data in self.spectator_bets[duel_id].items():
                    if bet_data['target'] == winner.id:
                        # Winner! 2x payout
                        winnings = bet_data['amount'] * 2
                        economy_cog.add_coins(user_id, winnings, "bet_win")
                        total_spectator_winnings += winnings
                        try:
                            user = await self.bot.fetch_user(user_id)
                            await ctx.send(f"🎉 {user.mention} won {winnings:,} coins on their bet!")
                        except:
                            pass
            
            embed = discord.Embed(
                title="🏆 Duel Complete!",
                description=f"**Winner:** {winner.mention}\n**Loser:** {loser.mention}",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Prize", value=f"{duel.bet_amount * 2:,} PsyCoins", inline=True)
            if total_spectator_winnings > 0:
                embed.add_field(name="Spectator Winnings", value=f"{total_spectator_winnings:,} coins", inline=True)
            
            await ctx.send(embed=embed)
            
            # Log duel
            self.log_duel({
                'challenger_id': duel.challenger.id,
                'challenger_name': str(duel.challenger),
                'opponent_id': duel.opponent.id,
                'opponent_name': str(duel.opponent),
                'game_type': duel.game_type,
                'bet_amount': duel.bet_amount,
                'winner_id': winner.id,
                'winner_name': str(winner),
                'result': result
            })
        
        # Cleanup
        duel.active = False
        if duel_id in self.active_duels:
            del self.active_duels[duel_id]
        if duel_id in self.spectator_bets:
            del self.spectator_bets[duel_id]
    
    @commands.command(name="bet")
    async def place_bet(self, ctx, target: discord.Member, amount: int):
        """Place a bet on a duel outcome (spectators only)"""
        if amount < 10:
            await ctx.send("❌ Minimum bet is 10 PsyCoins!")
            return
        
        # Find active duel in this channel
        active_duel = None
        duel_id = None
        for did, duel in self.active_duels.items():
            if duel.channel == ctx.channel and duel.active and duel.spectators_can_bet:
                active_duel = duel
                duel_id = did
                break
        
        if not active_duel:
            await ctx.send("❌ No active duel to bet on in this channel!")
            return
        
        if ctx.author.id in [active_duel.challenger.id, active_duel.opponent.id]:
            await ctx.send("❌ You're in this duel! You can't bet on yourself!")
            return
        
        if target.id not in [active_duel.challenger.id, active_duel.opponent.id]:
            await ctx.send(f"❌ {target.mention} is not in this duel!")
            return
        
        # Check if already bet
        if ctx.author.id in self.spectator_bets[duel_id]:
            await ctx.send("❌ You've already placed a bet on this duel!")
            return
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < amount:
            await ctx.send(f"❌ You don't have enough coins! Balance: {balance:,}")
            return
        
        # Place bet
        economy_cog.remove_coins(ctx.author.id, amount, "duel_bet")
        self.spectator_bets[duel_id][ctx.author.id] = {
            'target': target.id,
            'amount': amount
        }
        
        await ctx.send(f"✅ {ctx.author.mention} bet **{amount:,} coins** on {target.mention} to win!")
    
    @duel.command(name="stats")
    async def duel_stats(self, ctx, member: Optional[discord.Member] = None):
        """View duel statistics"""
        target = member or ctx.author
        
        wins = 0
        losses = 0
        total_winnings = 0
        
        for duel_id, duel_data in self.duel_history.items():
            if duel_data['winner_id'] == target.id:
                wins += 1
                total_winnings += duel_data['bet_amount']
            elif target.id in [duel_data['challenger_id'], duel_data['opponent_id']]:
                losses += 1
                total_winnings -= duel_data['bet_amount']
        
        total_duels = wins + losses
        win_rate = (wins / total_duels * 100) if total_duels > 0 else 0
        
        embed = discord.Embed(
            title=f"⚔️ {target.display_name}'s Duel Stats",
            color=discord.Color.red()
        )
        
        embed.add_field(name="🏆 Wins", value=wins, inline=True)
        embed.add_field(name="💀 Losses", value=losses, inline=True)
        embed.add_field(name="📊 Win Rate", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="💰 Net Winnings", value=f"{total_winnings:+,} coins", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dueling(bot))
