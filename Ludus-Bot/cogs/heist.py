import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class Heist(commands.Cog):
    """Team up for heists and rob banks or players"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/heists.json"
        self.load_data()
        self.active_heists = {}  # {channel_id: heist_data}
    
    def load_data(self):
        """Load heist data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.heist_data = json.load(f)
        else:
            self.heist_data = {}
    
    def save_data(self):
        """Save heist data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.heist_data, f, indent=4)
    
    def get_user_stats(self, user_id):
        """Get user's heist statistics"""
        user_key = str(user_id)
        if user_key not in self.heist_data:
            self.heist_data[user_key] = {
                "total_heists": 0,
                "successful": 0,
                "failed": 0,
                "total_stolen": 0,
                "total_lost": 0,
                "last_heist": None
            }
        return self.heist_data[user_key]
    
    def can_start_heist(self, user_id):
        """Check if user can start a heist (30min cooldown)"""
        stats = self.get_user_stats(user_id)
        if not stats["last_heist"]:
            return True, None
        
        last_heist = datetime.fromisoformat(stats["last_heist"])
        cooldown = timedelta(minutes=30)
        time_passed = datetime.utcnow() - last_heist
        
        if time_passed < cooldown:
            time_left = cooldown - time_passed
            minutes = int(time_left.total_seconds() // 60)
            return False, minutes
        
        return True, None
    
    @commands.group(name="heist", invoke_without_command=True)
    async def heist(self, ctx):
        """View heist information"""
        embed = discord.Embed(
            title="🏴‍☠️ Heist System",
            description="Team up to rob banks or businesses!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="🏦 Bank Heist",
            value="Rob the bank with your crew!\n"
                  "**Reward:** 10,000-50,000 coins\n"
                  "**Risk:** Lose 10% of bet\n"
                  "**Required:** 2-6 players",
            inline=False
        )
        
        embed.add_field(
            name="🏢 Business Heist",
            value="Rob another player's business!\n"
                  "**Reward:** Their pending income\n"
                  "**Risk:** Lose your bet\n"
                  "**Required:** 2-4 players",
            inline=False
        )
        
        embed.add_field(
            name="📊 Success Rates",
            value="```\n"
                  "2 players: 40%\n"
                  "3 players: 55%\n"
                  "4 players: 70%\n"
                  "5 players: 80%\n"
                  "6 players: 90%\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Commands",
            value="```\n"
                  "L!heist bank <bet>\n"
                  "L!heist business <@user> <bet>\n"
                  "L!heist join\n"
                  "L!heist stats [@user]\n"
                  "```",
            inline=False
        )
        
        embed.set_footer(text="30-minute cooldown between heists • All crew members must bet equally")
        
        await ctx.send(embed=embed)
    
    @heist.command(name="bank")
    async def heist_bank(self, ctx, bet: int):
        """Start a bank heist"""
        # Check cooldown
        can_start, minutes_left = self.can_start_heist(ctx.author.id)
        if not can_start:
            await ctx.send(f"⏰ You're on cooldown! Try again in {minutes_left} minutes.")
            return
        
        # Validate bet
        if bet < 1000:
            await ctx.send("❌ Minimum bet is 1,000 coins!")
            return
        
        if bet > 10000:
            await ctx.send("❌ Maximum bet is 10,000 coins per player!")
            return
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < bet:
            await ctx.send(f"❌ You need {bet:,} coins but have {balance:,}")
            return
        
        # Check if heist already active in channel
        if ctx.channel.id in self.active_heists:
            await ctx.send("❌ A heist is already being planned in this channel!")
            return
        
        # Deduct bet
        economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
        
        # Create heist
        self.active_heists[ctx.channel.id] = {
            "type": "bank",
            "leader": ctx.author.id,
            "crew": {str(ctx.author.id): bet},
            "bet_amount": bet,
            "target": None,
            "started": datetime.utcnow().isoformat()
        }
        
        embed = discord.Embed(
            title="🏦 BANK HEIST RECRUITING!",
            description=f"{ctx.author.mention} is planning a bank heist!",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Bet Amount", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Crew Size", value="1/6", inline=True)
        embed.add_field(name="Potential Reward", value="10,000-50,000 coins", inline=True)
        
        embed.add_field(
            name="Join Now!",
            value=f"Type `L!heist join` to join the crew!\n"
                  f"You need {bet:,} coins to join.\n\n"
                  f"⏰ Heist starts in 60 seconds!",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Wait 60 seconds for crew
        await asyncio.sleep(60)
        
        # Execute heist
        if ctx.channel.id in self.active_heists:
            await self.execute_heist(ctx)
    
    @heist.command(name="business")
    async def heist_business(self, ctx, target: discord.Member, bet: int):
        """Start a business heist against another player"""
        if target.id == ctx.author.id:
            await ctx.send("❌ You can't heist yourself!")
            return
        
        if target.bot:
            await ctx.send("❌ Can't heist bots!")
            return
        
        # Check cooldown
        can_start, minutes_left = self.can_start_heist(ctx.author.id)
        if not can_start:
            await ctx.send(f"⏰ You're on cooldown! Try again in {minutes_left} minutes.")
            return
        
        # Check if target has businesses
        business_cog = self.bot.get_cog("Business")
        if not business_cog:
            await ctx.send("❌ Business system not loaded!")
            return
        
        target_businesses = business_cog.get_user_businesses(target.id)
        if not target_businesses["businesses"]:
            await ctx.send(f"❌ {target.mention} doesn't own any businesses!")
            return
        
        # Check protection
        if target_businesses["protection"]:
            protection_expires = datetime.fromisoformat(target_businesses["protection"])
            if datetime.utcnow() < protection_expires:
                await ctx.send(f"🛡️ {target.mention}'s businesses are protected!")
                return
        
        # Validate bet
        if bet < 500:
            await ctx.send("❌ Minimum bet is 500 coins!")
            return
        
        if bet > 5000:
            await ctx.send("❌ Maximum bet is 5,000 coins per player!")
            return
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < bet:
            await ctx.send(f"❌ You need {bet:,} coins but have {balance:,}")
            return
        
        # Check if heist already active
        if ctx.channel.id in self.active_heists:
            await ctx.send("❌ A heist is already being planned in this channel!")
            return
        
        # Deduct bet
        economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
        
        # Create heist
        self.active_heists[ctx.channel.id] = {
            "type": "business",
            "leader": ctx.author.id,
            "crew": {str(ctx.author.id): bet},
            "bet_amount": bet,
            "target": target.id,
            "started": datetime.utcnow().isoformat()
        }
        
        embed = discord.Embed(
            title="🏢 BUSINESS HEIST RECRUITING!",
            description=f"{ctx.author.mention} is planning to rob {target.mention}!",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Bet Amount", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="Crew Size", value="1/4", inline=True)
        embed.add_field(name="Target", value=target.mention, inline=True)
        
        embed.add_field(
            name="Join Now!",
            value=f"Type `L!heist join` to join the crew!\n"
                  f"You need {bet:,} coins to join.\n\n"
                  f"⏰ Heist starts in 45 seconds!",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Wait 45 seconds
        await asyncio.sleep(45)
        
        # Execute heist
        if ctx.channel.id in self.active_heists:
            await self.execute_heist(ctx)
    
    @heist.command(name="join")
    async def heist_join(self, ctx):
        """Join an active heist"""
        if ctx.channel.id not in self.active_heists:
            await ctx.send("❌ No heist is being planned in this channel!")
            return
        
        heist = self.active_heists[ctx.channel.id]
        user_key = str(ctx.author.id)
        
        # Check if already in crew
        if user_key in heist["crew"]:
            await ctx.send("❌ You're already in the crew!")
            return
        
        # Check crew size
        max_crew = 6 if heist["type"] == "bank" else 4
        if len(heist["crew"]) >= max_crew:
            await ctx.send(f"❌ Crew is full! ({max_crew}/{max_crew})")
            return
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        bet = heist["bet_amount"]
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < bet:
            await ctx.send(f"❌ You need {bet:,} coins to join but have {balance:,}")
            return
        
        # Join heist
        economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
        heist["crew"][user_key] = bet
        
        crew_size = len(heist["crew"])
        await ctx.send(f"✅ {ctx.author.mention} joined the crew! ({crew_size}/{max_crew})")
    
    async def execute_heist(self, ctx):
        """Execute the heist"""
        heist = self.active_heists[ctx.channel.id]
        crew_size = len(heist["crew"])
        
        if crew_size < 2:
            # Refund everyone
            economy_cog = self.bot.get_cog("Economy")
            for user_id, bet in heist["crew"].items():
                economy_cog.add_coins(int(user_id), bet, "heist_cancelled")
            
            del self.active_heists[ctx.channel.id]
            await ctx.send("❌ Heist cancelled! Not enough crew members. Bets refunded.")
            return
        
        # Calculate success rate
        success_rates = {2: 0.40, 3: 0.55, 4: 0.70, 5: 0.80, 6: 0.90}
        success_rate = success_rates.get(crew_size, 0.40)
        
        # Roll for success
        success = random.random() < success_rate
        
        economy_cog = self.bot.get_cog("Economy")
        
        if success:
            if heist["type"] == "bank":
                # Bank heist reward
                base_reward = random.randint(10000, 50000)
                reward_per_person = base_reward // crew_size
                
                embed = discord.Embed(
                    title="✅ HEIST SUCCESS!",
                    description=f"The crew successfully robbed the bank!",
                    color=discord.Color.green()
                )
                
                crew_mentions = []
                for user_id, bet in heist["crew"].items():
                    uid = int(user_id)
                    economy_cog.add_coins(uid, reward_per_person, "heist_success")
                    
                    # Update stats
                    stats = self.get_user_stats(uid)
                    stats["total_heists"] += 1
                    stats["successful"] += 1
                    stats["total_stolen"] += reward_per_person
                    stats["last_heist"] = datetime.utcnow().isoformat()
                    
                    user = await self.bot.fetch_user(uid)
                    crew_mentions.append(user.mention)
                
                embed.add_field(name="Crew Size", value=crew_size, inline=True)
                embed.add_field(name="Total Loot", value=f"{base_reward:,} coins", inline=True)
                embed.add_field(name="Per Person", value=f"{reward_per_person:,} coins", inline=True)
                embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
                
            else:  # Business heist
                business_cog = self.bot.get_cog("Business")
                target_businesses = business_cog.get_user_businesses(heist["target"])
                
                # Calculate total pending income
                total_stolen = 0
                for biz_id, biz_data in target_businesses["businesses"].items():
                    biz_type = biz_data["type"]
                    level = biz_data["level"]
                    income = business_cog.calculate_income(biz_type, level)
                    
                    last_collect = datetime.fromisoformat(biz_data["last_collect"])
                    hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
                    pending = int(income * hours_passed)
                    total_stolen += pending
                    
                    # Reset their collection timer
                    biz_data["last_collect"] = datetime.utcnow().isoformat()
                
                business_cog.save_data()
                
                if total_stolen == 0:
                    total_stolen = 1000  # Minimum payout
                
                reward_per_person = total_stolen // crew_size
                
                embed = discord.Embed(
                    title="✅ HEIST SUCCESS!",
                    description=f"The crew robbed {(await self.bot.fetch_user(heist['target'])).mention}'s businesses!",
                    color=discord.Color.green()
                )
                
                crew_mentions = []
                for user_id in heist["crew"].keys():
                    uid = int(user_id)
                    economy_cog.add_coins(uid, reward_per_person, "heist_success")
                    
                    # Update stats
                    stats = self.get_user_stats(uid)
                    stats["total_heists"] += 1
                    stats["successful"] += 1
                    stats["total_stolen"] += reward_per_person
                    stats["last_heist"] = datetime.utcnow().isoformat()
                    
                    user = await self.bot.fetch_user(uid)
                    crew_mentions.append(user.mention)
                
                embed.add_field(name="Crew Size", value=crew_size, inline=True)
                embed.add_field(name="Total Stolen", value=f"{total_stolen:,} coins", inline=True)
                embed.add_field(name="Per Person", value=f"{reward_per_person:,} coins", inline=True)
                embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
        
        else:
            # Heist failed
            embed = discord.Embed(
                title="❌ HEIST FAILED!",
                description="The crew was caught!",
                color=discord.Color.red()
            )
            
            total_lost = sum(heist["crew"].values())
            
            crew_mentions = []
            for user_id in heist["crew"].keys():
                uid = int(user_id)
                
                # Update stats
                stats = self.get_user_stats(uid)
                stats["total_heists"] += 1
                stats["failed"] += 1
                stats["total_lost"] += heist["crew"][user_id]
                stats["last_heist"] = datetime.utcnow().isoformat()
                
                user = await self.bot.fetch_user(uid)
                crew_mentions.append(user.mention)
            
            embed.add_field(name="Crew Size", value=crew_size, inline=True)
            embed.add_field(name="Success Rate", value=f"{int(success_rate * 100)}%", inline=True)
            embed.add_field(name="Total Lost", value=f"{total_lost:,} coins", inline=True)
            embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
        
        self.save_data()
        del self.active_heists[ctx.channel.id]
        
        await ctx.send(embed=embed)
    
    @heist.command(name="stats")
    async def heist_stats(self, ctx, member: Optional[discord.Member] = None):
        """View heist statistics"""
        target = member or ctx.author
        stats = self.get_user_stats(target.id)
        
        if stats["total_heists"] == 0:
            await ctx.send(f"🏴‍☠️ {target.mention} hasn't participated in any heists yet!")
            return
        
        success_rate = (stats["successful"] / stats["total_heists"]) * 100 if stats["total_heists"] > 0 else 0
        net_profit = stats["total_stolen"] - stats["total_lost"]
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {target.display_name}'s Heist Stats",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(name="Total Heists", value=stats["total_heists"], inline=True)
        embed.add_field(name="Successful", value=stats["successful"], inline=True)
        embed.add_field(name="Failed", value=stats["failed"], inline=True)
        
        embed.add_field(name="Success Rate", value=f"{success_rate:.1f}%", inline=True)
        embed.add_field(name="Total Stolen", value=f"{stats['total_stolen']:,} coins", inline=True)
        embed.add_field(name="Total Lost", value=f"{stats['total_lost']:,} coins", inline=True)
        
        embed.add_field(
            name="Net Profit",
            value=f"{'📈' if net_profit > 0 else '📉'} {net_profit:,} coins",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Heist(bot))
