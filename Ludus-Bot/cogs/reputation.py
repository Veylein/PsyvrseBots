import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def _parse_ts(s):
    """Parse ISO timestamp – handles both naive (old data) and tz-aware strings."""
    from datetime import datetime as _dt, timezone as _tz
    d = _dt.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=_tz.utc)


class Reputation(commands.Cog):
    """Global reputation system that affects prices and rewards"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        os.makedirs(data_dir, exist_ok=True)
        self.file_path = os.path.join(data_dir, "reputation.json")
        self._migrate_old_file()
        self.load_data()

        # Cooldown for giving rep (24 hours per user pair)
        self.rep_cooldowns = {}

    def _migrate_old_file(self):
        """Move legacy cogs/reputation.json → data/reputation.json on first run."""
        import shutil
        old = os.path.join("cogs", "reputation.json")
        if os.path.exists(old) and not os.path.exists(self.file_path):
            shutil.copy2(old, self.file_path)
            print(f"[REPUTATION] Migrated data: {old} → {self.file_path}")
    
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
            last_time = _parse_ts(self.rep_cooldowns[cooldown_key])
            time_diff = discord.utils.utcnow() - last_time
            
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
            "timestamp": discord.utils.utcnow().isoformat()
        })
        
        # Record cooldown
        cooldown_key = f"{ctx.author.id}_{member.id}"
        self.rep_cooldowns[cooldown_key] = discord.utils.utcnow().isoformat()
        
        self.save_data()

        # sync profile stats
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            profile_cog.increment_stat(ctx.author.id, "reputation_given")
            profile_cog.increment_stat(member.id, "reputation_received")

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
            "timestamp": discord.utils.utcnow().isoformat()
        })
        
        # Record cooldown
        cooldown_key = f"{ctx.author.id}_{member.id}"
        self.rep_cooldowns[cooldown_key] = discord.utils.utcnow().isoformat()
        
        self.save_data()

        # sync profile stats
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            profile_cog.increment_stat(ctx.author.id, "reputation_given")

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
            timestamp = _parse_ts(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
            
            embed.add_field(
                name=f"{rep_type} from {entry['giver_name']}",
                value=f"{entry.get('reason', 'No reason')}\n*{timestamp}*",
                inline=False
            )
            
            if i >= 5:  # Limit to 5 for readability
                break
        
        await ctx.send(embed=embed)
    
async def setup(bot):
    await bot.add_cog(Reputation(bot))
