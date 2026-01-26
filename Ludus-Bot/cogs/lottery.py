import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional

class Lottery(commands.Cog):
    """Daily lottery system with growing jackpots"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/lottery.json"
        self.load_data()
        
        # Ticket price
        self.ticket_price = 100
        
        # Start the daily drawing loop
        self.daily_drawing.start()
    
    def load_data(self):
        """Load lottery data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.lottery_data = json.load(f)
        else:
            self.lottery_data = {
                "current_jackpot": 10000,  # Starting jackpot
                "tickets": {},  # {user_id: [ticket_numbers]}
                "ticket_counter": 1,
                "last_drawing": None,
                "next_drawing": self.get_next_drawing_time().isoformat(),
                "winners_history": []
            }
    
    def save_data(self):
        """Save lottery data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.lottery_data, f, indent=4)
    
    def get_next_drawing_time(self):
        """Get the next drawing time (daily at midnight UTC)"""
        now = datetime.utcnow()
        next_drawing = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return next_drawing
    
    def cog_unload(self):
        """Stop the task when cog unloads"""
        self.daily_drawing.cancel()
    
    @tasks.loop(hours=1)
    async def daily_drawing(self):
        """Check if it's time for the daily drawing"""
        now = datetime.utcnow()
        next_drawing = datetime.fromisoformat(self.lottery_data["next_drawing"])
        
        if now >= next_drawing:
            await self.conduct_drawing()
    
    @daily_drawing.before_loop
    async def before_daily_drawing(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
    
    async def conduct_drawing(self):
        """Conduct the lottery drawing"""
        if not self.lottery_data["tickets"]:
            # No tickets sold, jackpot grows
            self.lottery_data["current_jackpot"] += 5000
            self.lottery_data["next_drawing"] = self.get_next_drawing_time().isoformat()
            self.save_data()
            return
        
        # Select a random ticket
        all_tickets = []
        for user_id, tickets in self.lottery_data["tickets"].items():
            for ticket in tickets:
                all_tickets.append((user_id, ticket))
        
        winner_user_id, winning_ticket = random.choice(all_tickets)
        jackpot = self.lottery_data["current_jackpot"]
        
        # Give coins to winner
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(int(winner_user_id), jackpot, "lottery_win")
        
        # Log winner
        self.lottery_data["winners_history"].append({
            "user_id": winner_user_id,
            "jackpot": jackpot,
            "ticket": winning_ticket,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 10 winners
        if len(self.lottery_data["winners_history"]) > 10:
            self.lottery_data["winners_history"] = self.lottery_data["winners_history"][-10:]
        
        # Announce winner in all servers
        try:
            winner = await self.bot.fetch_user(int(winner_user_id))
            embed = discord.Embed(
                title="🎰 LOTTERY WINNER! 🎰",
                description=f"**{winner.name}** won the lottery jackpot!\n\n**Prize: {jackpot:,} PsyCoins**",
                color=discord.Color.gold()
            )
            embed.add_field(name="Winning Ticket", value=f"#{winning_ticket}", inline=True)
            embed.set_footer(text="Buy tickets with L!lottery buy <amount>")
            
            # Send to all servers (first text channel bot can access)
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            await channel.send(embed=embed)
                            break
                        except:
                            continue
        except:
            pass
        
        # Reset lottery
        self.lottery_data["tickets"] = {}
        self.lottery_data["ticket_counter"] = 1
        self.lottery_data["current_jackpot"] = 10000  # Reset to starting amount
        self.lottery_data["last_drawing"] = datetime.utcnow().isoformat()
        self.lottery_data["next_drawing"] = self.get_next_drawing_time().isoformat()
        self.save_data()
    
    @commands.group(name="lottery", invoke_without_command=True)
    async def lottery(self, ctx):
        """View current lottery information"""
        embed = discord.Embed(
            title="🎰 Daily Lottery",
            description=f"**Current Jackpot: {self.lottery_data['current_jackpot']:,} PsyCoins**",
            color=discord.Color.gold()
        )
        
        # Calculate total tickets sold
        total_tickets = sum(len(tickets) for tickets in self.lottery_data["tickets"].values())
        user_tickets = len(self.lottery_data["tickets"].get(str(ctx.author.id), []))
        
        embed.add_field(name="🎫 Ticket Price", value=f"{self.ticket_price:,} coins", inline=True)
        embed.add_field(name="🎫 Tickets Sold", value=total_tickets, inline=True)
        embed.add_field(name="🎫 Your Tickets", value=user_tickets, inline=True)
        
        # Next drawing time
        next_drawing = datetime.fromisoformat(self.lottery_data["next_drawing"])
        time_until = next_drawing - datetime.utcnow()
        hours = int(time_until.total_seconds() // 3600)
        minutes = int((time_until.total_seconds() % 3600) // 60)
        
        embed.add_field(
            name="⏰ Next Drawing",
            value=f"In {hours}h {minutes}m",
            inline=False
        )
        
        if user_tickets > 0:
            win_chance = (user_tickets / total_tickets * 100) if total_tickets > 0 else 0
            embed.add_field(
                name="📊 Your Win Chance",
                value=f"{win_chance:.2f}%",
                inline=False
            )
        
        embed.set_footer(text="Buy tickets: L!lottery buy <amount>")
        
        await ctx.send(embed=embed)
    
    @lottery.command(name="buy")
    async def lottery_buy(self, ctx, amount: int = 1):
        """Buy lottery tickets"""
        if amount < 1:
            await ctx.send("❌ You must buy at least 1 ticket!")
            return
        
        if amount > 100:
            await ctx.send("❌ Maximum 100 tickets per purchase!")
            return
        
        total_cost = amount * self.ticket_price
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < total_cost:
            await ctx.send(f"❌ Not enough coins! You need {total_cost:,} but have {balance:,}")
            return
        
        # Deduct coins
        economy_cog.remove_coins(ctx.author.id, total_cost, "lottery_tickets")
        
        # Give tickets
        user_key = str(ctx.author.id)
        if user_key not in self.lottery_data["tickets"]:
            self.lottery_data["tickets"][user_key] = []
        
        new_tickets = []
        for _ in range(amount):
            ticket_num = self.lottery_data["ticket_counter"]
            self.lottery_data["tickets"][user_key].append(ticket_num)
            new_tickets.append(ticket_num)
            self.lottery_data["ticket_counter"] += 1
        
        # Add to jackpot (50% of ticket sales)
        jackpot_increase = total_cost // 2
        self.lottery_data["current_jackpot"] += jackpot_increase
        
        self.save_data()
        
        embed = discord.Embed(
            title="🎫 Tickets Purchased!",
            description=f"You bought **{amount}** ticket(s) for **{total_cost:,} coins**",
            color=discord.Color.green()
        )
        
        if amount <= 10:
            ticket_list = ", ".join([f"#{t}" for t in new_tickets])
            embed.add_field(name="Your Tickets", value=ticket_list, inline=False)
        
        embed.add_field(name="New Jackpot", value=f"{self.lottery_data['current_jackpot']:,} coins", inline=True)
        
        # Calculate win chance
        total_tickets = sum(len(tickets) for tickets in self.lottery_data["tickets"].values())
        user_tickets = len(self.lottery_data["tickets"][user_key])
        win_chance = (user_tickets / total_tickets * 100)
        
        embed.add_field(name="Your Win Chance", value=f"{win_chance:.2f}%", inline=True)
        
        await ctx.send(embed=embed)
    
    @lottery.command(name="tickets")
    async def lottery_tickets(self, ctx, member: Optional[discord.Member] = None):
        """View your lottery tickets"""
        target = member or ctx.author
        user_key = str(target.id)
        
        if user_key not in self.lottery_data["tickets"] or not self.lottery_data["tickets"][user_key]:
            await ctx.send(f"🎫 {target.mention} has no tickets for the current drawing!")
            return
        
        tickets = self.lottery_data["tickets"][user_key]
        total_tickets = sum(len(t) for t in self.lottery_data["tickets"].values())
        win_chance = (len(tickets) / total_tickets * 100)
        
        embed = discord.Embed(
            title=f"🎫 {target.display_name}'s Lottery Tickets",
            description=f"**{len(tickets)}** tickets | **{win_chance:.2f}%** win chance",
            color=discord.Color.blue()
        )
        
        if len(tickets) <= 20:
            ticket_list = ", ".join([f"#{t}" for t in sorted(tickets)])
            embed.add_field(name="Ticket Numbers", value=ticket_list, inline=False)
        else:
            embed.add_field(
                name="Ticket Numbers",
                value=f"#{min(tickets)} to #{max(tickets)} (showing range due to many tickets)",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @lottery.command(name="winners", aliases=['history'])
    async def lottery_winners(self, ctx):
        """View recent lottery winners"""
        if not self.lottery_data["winners_history"]:
            await ctx.send("📜 No lottery winners yet!")
            return
        
        embed = discord.Embed(
            title="🏆 Recent Lottery Winners",
            description="Last 10 winners",
            color=discord.Color.gold()
        )
        
        for i, winner_data in enumerate(reversed(self.lottery_data["winners_history"]), 1):
            try:
                user = await self.bot.fetch_user(int(winner_data["user_id"]))
                username = user.name
            except:
                username = f"User {winner_data['user_id']}"
            
            timestamp = datetime.fromisoformat(winner_data["timestamp"]).strftime("%Y-%m-%d")
            
            embed.add_field(
                name=f"#{i}. {username}",
                value=f"**{winner_data['jackpot']:,} coins**\nTicket #{winner_data['ticket']}\n*{timestamp}*",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @lottery.command(name="draw", hidden=True)
    @commands.is_owner()
    async def lottery_draw_manual(self, ctx):
        """Manually trigger a lottery drawing (owner only)"""
        await ctx.send("🎰 Conducting lottery drawing...")
        await self.conduct_drawing()
        await ctx.send("✅ Drawing complete!")

async def setup(bot):
    await bot.add_cog(Lottery(bot))
