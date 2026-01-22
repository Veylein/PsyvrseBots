import discord
from discord.ext import commands, tasks
import datetime
from .. import db_async as db

class Rewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_rewards.start()

    def cog_unload(self):
        self.weekly_rewards.cancel()

    # use async DB helper (db_async)

    @commands.command(name="add_reward")
    @commands.has_permissions(manage_guild=True)
    async def add_reward(self, ctx, role: discord.Role, tier: int = 0, *, criteria: str = "activity_score>=10"):
        """Add a reward mapping to assign `role` when `criteria` is met."""
        await db.execute("INSERT INTO rewards (guild_id, role_id, criteria, tier) VALUES (?, ?, ?, ?)", (ctx.guild.id, role.id, criteria, tier), commit=True)
        await ctx.send(f"Reward added: role={role.name}, tier={tier}, criteria={criteria}")

    @commands.command(name="list_rewards")
    async def list_rewards(self, ctx):
        rows = await db.fetchall("SELECT reward_id, role_id, criteria, tier FROM rewards WHERE guild_id = ?", (ctx.guild.id,))
        if not rows:
            await ctx.send("No rewards configured for this server.")
            return
        msg = "Rewards:\n"
        for r in rows:
            role = ctx.guild.get_role(r['role_id'])
            msg += f"- [{r['reward_id']}] {role.name if role else r['role_id']} (tier {r['tier']}): {r['criteria']}\n"
        await ctx.send(msg)

    @tasks.loop(hours=24)
    async def weekly_rewards(self):
        # Daily check to apply rewards; tiered logic
        rewards = await db.fetchall("SELECT * FROM rewards")
        for r in rewards:
            guild = self.bot.get_guild(r['guild_id'])
            if not guild:
                continue
            role = guild.get_role(r['role_id'])
            if not role:
                continue
            # Very simple criteria parser: activity_score>=N
            crit = r['criteria']
            try:
                if "activity_score>=" in crit:
                    threshold = int(crit.split('>=')[-1])
                    users = await db.fetchall("SELECT user_id, activity_score FROM users WHERE activity_score >= ?", (threshold,))
                    for u in users:
                        member = guild.get_member(u['user_id'])
                        if member:
                            try:
                                await member.add_roles(role)
                            except:
                                pass
                    # Remove role from members who no longer meet criteria
                    qualifying = {u['user_id'] for u in users}
                    for member in list(role.members):
                        if member.bot:
                            continue
                        if member.id not in qualifying:
                            try:
                                await member.remove_roles(role)
                            except:
                                pass
                    # update last_applied
                    await db.execute("UPDATE rewards SET last_applied = ? WHERE reward_id = ?", (datetime.datetime.utcnow().isoformat(), r['reward_id']), commit=True)
            except Exception:
                pass

    @weekly_rewards.before_loop
    async def before_rewards(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Rewards(bot))
