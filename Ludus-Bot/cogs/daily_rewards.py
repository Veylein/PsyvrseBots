import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional

class DailyRewards(commands.Cog):
    """Enhanced daily login rewards with milestones"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/daily_rewards.json"
        self.load_data()
        
        # Reward tiers
        self.daily_rewards = {
            1: 100,      # Day 1
            2: 150,      # Day 2
            3: 200,      # Day 3
            4: 250,      # Day 4
            5: 300,      # Day 5
            6: 350,      # Day 6
            7: 500,      # Week 1 bonus
            14: 750,     # Week 2 bonus
            30: 2000,    # Month bonus
            60: 5000,    # 2 months
            100: 10000,  # 100 days!
            365: 50000,  # 1 year!!!
        }
        
        # Streak milestones (special rewards)
        self.milestone_rewards = {
            7: {"coins": 500, "title": "Weekly Warrior", "item": "streak_shield"},
            30: {"coins": 2000, "title": "Monthly Master", "item": "lucky_coin"},
            60: {"coins": 5000, "title": "Devoted", "item": "xp_boost"},
            100: {"coins": 10000, "title": "Centurion", "item": "mystery_box"},
            365: {"coins": 50000, "title": "Legendary", "item": "premium_pet_food"},
        }
    
    def load_data(self):
        """Load daily rewards data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.rewards_data = json.load(f)
        else:
            self.rewards_data = {}
    
    def save_data(self):
        """Save daily rewards data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.rewards_data, f, indent=4)
    
    def get_user_data(self, user_id):
        """Get user's daily reward data"""
        user_key = str(user_id)
        if user_key not in self.rewards_data:
            self.rewards_data[user_key] = {
                "last_claim": None,
                "current_streak": 0,
                "total_days": 0,
                "best_streak": 0,
                "total_earned": 0,
                "milestones_reached": []
            }
        return self.rewards_data[user_key]
    
    def can_claim(self, user_id):
        """Check if user can claim daily reward"""
        user_data = self.get_user_data(user_id)
        
        if not user_data["last_claim"]:
            return True, None
        
        last_claim = datetime.fromisoformat(user_data["last_claim"])
        now = datetime.now()
        time_diff = now - last_claim
        
        if time_diff.days >= 1:
            return True, time_diff.days
        else:
            # Calculate when they can claim next
            next_claim = last_claim + timedelta(days=1)
            time_until = next_claim - now
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            return False, f"{hours}h {minutes}m"
    
    @commands.command(name="claim")
    async def claim_daily(self, ctx):
        """Claim your daily login reward!"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        can_claim, info = self.can_claim(ctx.author.id)
        
        if not can_claim:
            embed = discord.Embed(
                title="⏰ Already Claimed Today!",
                description=f"Come back in **{info}** for your next reward!",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Check if streak continues
        if info is None or info == 1:
            # Streak continues!
            user_data["current_streak"] += 1
        else:
            # Streak broken
            user_data["current_streak"] = 1
        
        user_data["total_days"] += 1
        user_data["last_claim"] = datetime.now().isoformat()
        
        # Update best streak
        if user_data["current_streak"] > user_data["best_streak"]:
            user_data["best_streak"] = user_data["current_streak"]
        
        # Calculate reward
        current_streak = user_data["current_streak"]
        base_reward = self.daily_rewards.get(current_streak, 100 + (current_streak * 10))
        
        # Add streak bonus (5% per day up to 50%)
        streak_multiplier = min(1.0 + (current_streak * 0.05), 1.5)
        total_reward = int(base_reward * streak_multiplier)
        
        # Give coins
        economy_cog.add_coins(ctx.author.id, total_reward, "daily_reward")
        user_data["total_earned"] += total_reward
        
        # Check for milestone rewards
        milestone_reached = None
        if current_streak in self.milestone_rewards:
            if current_streak not in user_data["milestones_reached"]:
                milestone_reached = self.milestone_rewards[current_streak]
                user_data["milestones_reached"].append(current_streak)
                
                # Give milestone rewards
                economy_cog.add_coins(ctx.author.id, milestone_reached["coins"], "milestone")
                if "item" in milestone_reached:
                    economy_cog.add_item(ctx.author.id, milestone_reached["item"], 1)
        
        self.save_data()
        
        # Create reward embed
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"**+{total_reward:,} PsyCoins**",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🔥 Current Streak", value=f"{current_streak} days", inline=True)
        embed.add_field(name="📅 Total Days", value=user_data["total_days"], inline=True)
        embed.add_field(name="🏆 Best Streak", value=user_data["best_streak"], inline=True)
        
        if streak_multiplier > 1.0:
            bonus_percent = int((streak_multiplier - 1.0) * 100)
            embed.add_field(
                name="⚡ Streak Bonus",
                value=f"+{bonus_percent}% reward!",
                inline=False
            )
        
        # Milestone notification
        if milestone_reached:
            embed.add_field(
                name="🌟 MILESTONE REACHED!",
                value=f"**{milestone_reached['title']}**\n"
                      f"+{milestone_reached['coins']:,} bonus coins!\n"
                      f"+ {milestone_reached.get('item', 'Special item')}!",
                inline=False
            )
            embed.color = discord.Color.purple()
        
        # Next milestone
        next_milestones = [m for m in self.milestone_rewards.keys() if m > current_streak]
        if next_milestones:
            next_milestone = min(next_milestones)
            days_until = next_milestone - current_streak
            embed.set_footer(text=f"Next milestone in {days_until} days: {next_milestone} day streak!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="streaks")
    async def view_streaks(self, ctx, member: Optional[discord.Member] = None):
        """View your or another user's login streaks"""
        target = member or ctx.author
        user_data = self.get_user_data(target.id)
        
        embed = discord.Embed(
            title=f"📊 {target.display_name}'s Login Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🔥 Current Streak", value=f"{user_data['current_streak']} days", inline=True)
        embed.add_field(name="🏆 Best Streak", value=f"{user_data['best_streak']} days", inline=True)
        embed.add_field(name="📅 Total Days", value=user_data['total_days'], inline=True)
        embed.add_field(name="💰 Total Earned", value=f"{user_data['total_earned']:,} coins", inline=True)
        
        # Milestones reached
        if user_data["milestones_reached"]:
            milestones_str = ", ".join([str(m) for m in sorted(user_data["milestones_reached"])])
            embed.add_field(name="🌟 Milestones", value=milestones_str, inline=False)
        
        # Show next milestone
        current_streak = user_data["current_streak"]
        next_milestones = [m for m in self.milestone_rewards.keys() if m > current_streak]
        if next_milestones:
            next_milestone = min(next_milestones)
            days_until = next_milestone - current_streak
            reward = self.milestone_rewards[next_milestone]
            embed.add_field(
                name="🎯 Next Milestone",
                value=f"**{next_milestone} days** (in {days_until} days)\n"
                      f"{reward['title']} - {reward['coins']:,} coins + {reward.get('item', 'item')}",
                inline=False
            )
        
        # Last claim time
        if user_data["last_claim"]:
            last_claim = datetime.fromisoformat(user_data["last_claim"])
            embed.set_footer(text=f"Last claim: {last_claim.strftime('%Y-%m-%d %H:%M')}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="calendar")
    async def reward_calendar(self, ctx):
        """View the reward calendar and milestones"""
        embed = discord.Embed(
            title="📅 Daily Reward Calendar",
            description="Claim daily rewards and build your streak!",
            color=discord.Color.gold()
        )
        
        # Show first week rewards
        week1 = "\n".join([f"Day {day}: {self.daily_rewards.get(day, 100)} coins" for day in range(1, 8)])
        embed.add_field(name="Week 1", value=week1, inline=True)
        
        # Show milestone rewards
        milestones_str = ""
        for day, reward in sorted(self.milestone_rewards.items()):
            milestones_str += f"**{day} days**: {reward['title']}\n"
            milestones_str += f"  └ {reward['coins']:,} coins + {reward.get('item', 'special item')}\n"
        
        embed.add_field(name="🌟 Milestone Rewards", value=milestones_str, inline=False)
        
        # Info
        embed.add_field(
            name="ℹ️ How It Works",
            value="• Claim daily with `L!claim`\n"
                  "• Streak bonus: +5% per day (up to +50%)\n"
                  "• Missing a day breaks your streak\n"
                  "• Milestones give huge bonuses!",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="streakleaderboard", aliases=['streaklb'])
    async def streak_leaderboard(self, ctx):
        """View the top login streaks across all users"""
        # Sort users by current streak
        sorted_users = sorted(
            self.rewards_data.items(),
            key=lambda x: x[1].get('current_streak', 0),
            reverse=True
        )[:10]
        
        if not sorted_users:
            await ctx.send("📊 No streak data yet!")
            return
        
        embed = discord.Embed(
            title="🔥 Top Login Streaks",
            description="Users with the longest current streaks!",
            color=discord.Color.red()
        )
        
        leaderboard = []
        for rank, (user_id, user_data) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.name
            except:
                username = f"User {user_id}"
            
            streak = user_data.get('current_streak', 0)
            total_days = user_data.get('total_days', 0)
            
            medal = ""
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"`{rank}.`"
            
            leaderboard.append(f"{medal} **{username}** - {streak} days (total: {total_days})")
        
        embed.description = "\n".join(leaderboard)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DailyRewards(bot))
