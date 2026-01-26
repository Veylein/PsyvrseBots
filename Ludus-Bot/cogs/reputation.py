import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional

class Reputation(commands.Cog):
    """Global reputation system that affects prices and rewards"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/reputation.json"
        self.load_data()
        
        # Cooldown for giving rep (24 hours per user pair)
        self.rep_cooldowns = {}
    
    def load_data(self):
        """Load reputation data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.rep_data = json.load(f)
        else:
            self.rep_data = {}
    
    def save_data(self):
        """Save reputation data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.rep_data, f, indent=4)
    
    def get_user_rep(self, user_id):
        """Get user's reputation data"""
        user_key = str(user_id)
        if user_key not in self.rep_data:
            self.rep_data[user_key] = {
                "total_rep": 0,
                "positive_rep": 0,
                "negative_rep": 0,
                "given_rep": {},  # {user_id: timestamp}
                "rep_history": []  # List of rep events
            }
        return self.rep_data[user_key]
    
    def get_rep_tier(self, total_rep):
        """Get reputation tier based on total rep"""
        if total_rep >= 100:
            return "🌟 Legendary", discord.Color.gold()
        elif total_rep >= 50:
            return "⭐ Excellent", discord.Color.purple()
        elif total_rep >= 25:
            return "💎 Great", discord.Color.blue()
        elif total_rep >= 10:
            return "✨ Good", discord.Color.green()
        elif total_rep >= 0:
            return "👤 Neutral", discord.Color.light_grey()
        elif total_rep >= -10:
            return "⚠️ Questionable", discord.Color.orange()
        elif total_rep >= -25:
            return "❌ Bad", discord.Color.red()
        else:
            return "☠️ Notorious", discord.Color.dark_red()
    
    def get_price_modifier(self, total_rep):
        """Get shop price modifier based on reputation"""
        # Positive rep reduces prices, negative increases
        # -20% at 100 rep, +20% at -100 rep
        modifier = 1.0 - (total_rep / 500.0)
        return max(0.8, min(1.2, modifier))  # Cap between 80% and 120%
    
    def get_reward_modifier(self, total_rep):
        """Get reward multiplier based on reputation"""
        # Positive rep increases rewards, negative decreases
        # +10% at 100 rep, -10% at -100 rep
        modifier = 1.0 + (total_rep / 1000.0)
        return max(0.9, min(1.1, modifier))  # Cap between 90% and 110%
    
    def can_give_rep(self, giver_id, receiver_id):
        """Check if giver can give rep to receiver (24hr cooldown)"""
        cooldown_key = f"{giver_id}_{receiver_id}"
        
        if cooldown_key in self.rep_cooldowns:
            last_time = datetime.fromisoformat(self.rep_cooldowns[cooldown_key])
            time_diff = datetime.now() - last_time
            
            if time_diff < timedelta(hours=24):
                time_left = timedelta(hours=24) - time_diff
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                return False, f"{hours}h {minutes}m"
        
        return True, None
    
    @commands.group(name="rep", invoke_without_command=True)
    async def rep(self, ctx, member: Optional[discord.Member] = None):
        """View someone's reputation"""
        target = member or ctx.author
        
        if target.bot:
            await ctx.send("❌ Bots don't have reputation!")
            return
        
        user_rep = self.get_user_rep(target.id)
        total_rep = user_rep["total_rep"]
        
        tier, color = self.get_rep_tier(total_rep)
        price_mod = self.get_price_modifier(total_rep)
        reward_mod = self.get_reward_modifier(total_rep)
        
        embed = discord.Embed(
            title=f"{target.display_name}'s Reputation",
            description=f"**Tier:** {tier}\n**Total Rep:** {total_rep:+d}",
            color=color
        )
        
        embed.add_field(name="👍 Positive", value=user_rep["positive_rep"], inline=True)
        embed.add_field(name="👎 Negative", value=user_rep["negative_rep"], inline=True)
        embed.add_field(name="📊 Net Score", value=f"{total_rep:+d}", inline=True)
        
        # Show effects
        price_percent = int((1 - price_mod) * 100)
        reward_percent = int((reward_mod - 1) * 100)
        
        effects = []
        if price_percent != 0:
            effects.append(f"Shop Prices: {price_percent:+d}%")
        if reward_percent != 0:
            effects.append(f"Rewards: {reward_percent:+d}%")
        
        if effects:
            embed.add_field(name="⚡ Effects", value="\n".join(effects), inline=False)
        
        # Recent rep
        if user_rep["rep_history"]:
            recent = user_rep["rep_history"][-3:]
            recent_str = "\n".join([
                f"{'+1' if r['type'] == 'positive' else '-1'} from {r['giver_name']} - {r.get('reason', 'No reason')[:30]}"
                for r in reversed(recent)
            ])
            embed.add_field(name="📜 Recent", value=recent_str, inline=False)
        
        embed.set_footer(text="Give rep with: L!rep give/remove @user [reason]")
        
        await ctx.send(embed=embed)
    
    @rep.command(name="give", aliases=['add', '+'])
    async def rep_give(self, ctx, member: discord.Member, *, reason: str = "No reason given"):
        """Give positive reputation to a user"""
        if member.bot:
            await ctx.send("❌ You can't give reputation to bots!")
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't give reputation to yourself!")
            return
        
        # Check cooldown
        can_give, time_left = self.can_give_rep(ctx.author.id, member.id)
        if not can_give:
            await ctx.send(f"⏰ You can give rep to {member.mention} again in **{time_left}**")
            return
        
        # Give reputation
        user_rep = self.get_user_rep(member.id)
        user_rep["total_rep"] += 1
        user_rep["positive_rep"] += 1
        user_rep["rep_history"].append({
            "type": "positive",
            "giver_id": ctx.author.id,
            "giver_name": str(ctx.author),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        # Record cooldown
        cooldown_key = f"{ctx.author.id}_{member.id}"
        self.rep_cooldowns[cooldown_key] = datetime.now().isoformat()
        
        self.save_data()
        
        new_total = user_rep["total_rep"]
        tier, color = self.get_rep_tier(new_total)
        
        embed = discord.Embed(
            title="👍 Reputation Given!",
            description=f"{ctx.author.mention} gave +1 rep to {member.mention}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name=f"{member.display_name}'s New Rep", value=f"{new_total:+d} ({tier})", inline=False)
        
        await ctx.send(embed=embed)
    
    @rep.command(name="remove", aliases=['take', '-'])
    async def rep_remove(self, ctx, member: discord.Member, *, reason: str = "No reason given"):
        """Remove reputation from a user (give negative rep)"""
        if member.bot:
            await ctx.send("❌ You can't give reputation to bots!")
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't remove reputation from yourself!")
            return
        
        # Check cooldown
        can_give, time_left = self.can_give_rep(ctx.author.id, member.id)
        if not can_give:
            await ctx.send(f"⏰ You can give rep to {member.mention} again in **{time_left}**")
            return
        
        # Remove reputation
        user_rep = self.get_user_rep(member.id)
        user_rep["total_rep"] -= 1
        user_rep["negative_rep"] += 1
        user_rep["rep_history"].append({
            "type": "negative",
            "giver_id": ctx.author.id,
            "giver_name": str(ctx.author),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        # Record cooldown
        cooldown_key = f"{ctx.author.id}_{member.id}"
        self.rep_cooldowns[cooldown_key] = datetime.now().isoformat()
        
        self.save_data()
        
        new_total = user_rep["total_rep"]
        tier, color = self.get_rep_tier(new_total)
        
        embed = discord.Embed(
            title="👎 Reputation Removed",
            description=f"{ctx.author.mention} gave -1 rep to {member.mention}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name=f"{member.display_name}'s New Rep", value=f"{new_total:+d} ({tier})", inline=False)
        
        await ctx.send(embed=embed)
    
    @rep.command(name="leaderboard", aliases=['lb', 'top'])
    async def rep_leaderboard(self, ctx):
        """View the reputation leaderboard"""
        # Sort users by total rep
        sorted_users = sorted(
            self.rep_data.items(),
            key=lambda x: x[1].get('total_rep', 0),
            reverse=True
        )[:10]
        
        if not sorted_users:
            await ctx.send("📊 No reputation data yet!")
            return
        
        embed = discord.Embed(
            title="🏆 Reputation Leaderboard",
            description="Most reputable users!",
            color=discord.Color.gold()
        )
        
        leaderboard = []
        for rank, (user_id, user_data) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.name
            except:
                username = f"User {user_id}"
            
            total_rep = user_data.get('total_rep', 0)
            tier, _ = self.get_rep_tier(total_rep)
            
            medal = ""
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"`{rank}.`"
            
            leaderboard.append(f"{medal} **{username}** - {total_rep:+d} ({tier.split()[1]})")
        
        embed.description = "\n".join(leaderboard)
        embed.set_footer(text="Give rep to helpful users with L!rep give @user")
        
        await ctx.send(embed=embed)
    
    @rep.command(name="history")
    async def rep_history(self, ctx, member: Optional[discord.Member] = None):
        """View someone's reputation history"""
        target = member or ctx.author
        
        if target.bot:
            await ctx.send("❌ Bots don't have reputation!")
            return
        
        user_rep = self.get_user_rep(target.id)
        
        if not user_rep["rep_history"]:
            await ctx.send(f"📜 {target.mention} has no reputation history yet!")
            return
        
        embed = discord.Embed(
            title=f"📜 {target.display_name}'s Rep History",
            description=f"Total: {user_rep['total_rep']:+d}",
            color=discord.Color.blue()
        )
        
        # Show last 10
        recent = user_rep["rep_history"][-10:]
        for i, entry in enumerate(reversed(recent), 1):
            rep_type = "+1" if entry['type'] == 'positive' else "-1"
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
            
            embed.add_field(
                name=f"{rep_type} from {entry['giver_name']}",
                value=f"{entry.get('reason', 'No reason')}\n*{timestamp}*",
                inline=False
            )
            
            if i >= 5:  # Limit to 5 for readability
                break
        
        await ctx.send(embed=embed)
    
    @rep.command(name="info")
    async def rep_info(self, ctx):
        """Learn about the reputation system"""
        embed = discord.Embed(
            title="ℹ️ Reputation System",
            description="Build your reputation through community interactions!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How It Works",
            value="• Users can give you +1 or -1 rep\n"
                  "• 24-hour cooldown per user pair\n"
                  "• Reputation affects shop prices and rewards\n"
                  "• Climb the leaderboard!",
            inline=False
        )
        
        embed.add_field(
            name="Commands",
            value="```\n"
                  "L!rep @user - View reputation\n"
                  "L!rep give @user [reason] - Give +1 rep\n"
                  "L!rep remove @user [reason] - Give -1 rep\n"
                  "L!rep leaderboard - Top users\n"
                  "L!rep history [@user] - Rep history\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="Tiers",
            value="```\n"
                  "100+  : 🌟 Legendary\n"
                  "50+   : ⭐ Excellent\n"
                  "25+   : 💎 Great\n"
                  "10+   : ✨ Good\n"
                  "0 to 9: 👤 Neutral\n"
                  "-10+  : ⚠️ Questionable\n"
                  "-25+  : ❌ Bad\n"
                  "-100+ : ☠️ Notorious\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="Benefits",
            value="• **High rep**: Cheaper shop prices, better rewards\n"
                  "• **Low rep**: More expensive prices, worse rewards\n"
                  "• Max effects: ±20% prices, ±10% rewards",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Reputation(bot))
