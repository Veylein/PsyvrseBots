
import discord
from discord.ext import commands
from discord import app_commands
from .. import db_async as db
import datetime

OWNER_IDS = {1300838678280671264, 1382187068373074001, 1311394031640776716, 1310134550566797352}

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    

    def is_owner(self, user_id):
        return user_id in OWNER_IDS

    @commands.hybrid_command(name="audit", description="Show server audit (owner only)")
    async def audit(self, ctx):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        users = await db.fetchall("SELECT * FROM users")
        events = await db.fetchall("SELECT * FROM events")
        embed = discord.Embed(title="Eventus Audit", color=discord.Color.red())
        embed.add_field(name="Total Users", value=len(users))
        embed.add_field(name="Total Events", value=len(events))
        # TODO: Add peak hours, lurkers, dead channels, engagement sparks
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    @commands.hybrid_command(name="tune", description="Tune AI personality (owner only)")
    async def tune(self, ctx, mode: str):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        await db.execute("INSERT INTO analytics (created_at, data) VALUES (?, ?)", (datetime.datetime.utcnow().isoformat(), f"tune:{mode}"), commit=True)
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"AI personality tuned to: {mode}")
        else:
            await ctx.send(f"AI personality tuned to: {mode}")

    @commands.hybrid_command(name="purge_inactive", description="DM inactive users (owner only)")
    async def purge_inactive(self, ctx, days: int = 7):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        inactive = await db.fetchall("SELECT user_id, username FROM users WHERE last_active < ?", (cutoff,))
        for user in inactive:
            try:
                member = ctx.guild.get_member(user['user_id'])
                if member:
                    await member.send(f"You have been inactive for {days} days. Come join an event!")
            except:
                pass
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"Inactive users (> {days} days) notified. Total: {len(inactive)}")
        else:
            await ctx.send(f"Inactive users (> {days} days) notified. Total: {len(inactive)}")

    @commands.hybrid_command(name="force_topic", description="Force a topic to drop right now (owner only)")
    async def force_topic(self, ctx, *, topic: str):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"💡 **Owner Forced Topic:** {topic}")
        else:
            await ctx.send(f"💡 **Owner Forced Topic:** {topic}")

    @commands.hybrid_command(name="override", description="Override event/RSVP/momentum/AI settings (owner only)")
    async def override(self, ctx, what: str, value: str):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        if what == "event_title":
            event_id, new_title = value.split(',', 1)
            await db.execute("UPDATE events SET title = ? WHERE event_id = ?", (new_title, int(event_id)), commit=True)
            msg = f"Event {event_id} title set to {new_title}"
        elif what == "rsvp":
            event_id, user_id = value.split(',', 1)
            row = await db.fetchone("SELECT rsvp_list FROM events WHERE event_id = ?", (int(event_id),))
            rsvp_list = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
            if user_id not in rsvp_list:
                rsvp_list.append(user_id)
                await db.execute("UPDATE events SET rsvp_list = ? WHERE event_id = ?", (','.join(rsvp_list), int(event_id)), commit=True)
            msg = f"User {user_id} added to RSVP for event {event_id}"
        elif what == "momentum":
            user_id, points = value.split(',', 1)
            await db.execute("UPDATE users SET momentum = ? WHERE user_id = ?", (int(points), int(user_id)), commit=True)
            msg = f"User {user_id} momentum set to {points}"
        elif what == "ai_frequency":
            freq = int(value)
            await db.execute("INSERT INTO analytics (created_at, data) VALUES (?, ?)", (datetime.datetime.utcnow().isoformat(), f"ai_frequency:{freq}"), commit=True)
            msg = f"AI frequency set to {freq}"
        elif what == "topic_trigger":
            trigger = value
            await db.execute("INSERT INTO analytics (created_at, data) VALUES (?, ?)", (datetime.datetime.utcnow().isoformat(), f"topic_trigger:{trigger}"), commit=True)
            msg = f"Topic trigger set to {trigger}"
        else:
            msg = "Unknown override."
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @commands.hybrid_command(name="export", description="Export analytics (owner only)")
    async def export(self, ctx, fmt: str = "json"):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        rows = await db.fetchall("SELECT * FROM analytics")
        if fmt == "json":
            import json
            data = [dict(row) for row in rows]
            msg = f"```json\n{json.dumps(data, indent=2)}```"
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg)
            else:
                await ctx.send(msg)
        elif fmt == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys() if rows else [])
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
            msg = f"```csv\n{output.getvalue()}```"
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg)
            else:
                await ctx.send(msg)
        elif fmt == "embed":
            embed = discord.Embed(title="Analytics Export", color=discord.Color.blue())
            for row in rows[-5:]:
                embed.add_field(name=row['created_at'], value=row['data'], inline=False)
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed)
            else:
                await ctx.send(embed=embed)
        else:
            msg = "Unknown format."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg)
            else:
                await ctx.send(msg)

    @commands.hybrid_command(name="silence", description="Mute auto-topics/messages (owner only)")
    async def silence(self, ctx, hours: int = 1):
        user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        if not self.is_owner(user_id):
            if hasattr(ctx, 'respond'):
                await ctx.respond("Only owners can use this command.", ephemeral=True)
            else:
                await ctx.send("Only owners can use this command.")
            return
        await db.execute("INSERT INTO analytics (created_at, data) VALUES (?, ?)", (datetime.datetime.utcnow().isoformat(), f"silence:{hours}"), commit=True)
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"Auto-topics/messages silenced for {hours} hours.")
        else:
            await ctx.send(f"Auto-topics/messages silenced for {hours} hours.")

async def setup(bot):
    await bot.add_cog(Owner(bot))
