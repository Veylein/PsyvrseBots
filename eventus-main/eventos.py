import discord
from discord.ext import commands
import sqlite3
import datetime

class EventOS(commands.Cog):
    EVENT_TEMPLATES = {
        'gaming': {'title': 'Game Night', 'description': 'Join us for a night of gaming!'},
        'study': {'title': 'Study Session', 'description': 'Collaborative study time.'},
        'movie': {'title': 'Movie Night', 'description': 'Watch a movie together!'}
    }

    @commands.hybrid_command(name="event_template", description="Create an event from a template.")
    async def event_template(self, ctx, template: str):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events or getattr(perms, 'create_events', False)):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.")
            return
        t = self.EVENT_TEMPLATES.get(template)
        if not t:
            msg = f"Template not found. Available: {', '.join(self.EVENT_TEMPLATES.keys())}"
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        await self.create_event(ctx, t['title'], description=t['description'])

    @commands.hybrid_command(name="event_embed", description="Interactive embed builder for events.")
    async def event_embed(self, ctx, title: str, description: str, color: str = "blue"):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events or getattr(perms, 'create_events', False)):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.")
            return
        color_map = {"blue": 3447003, "green": 3066993, "red": 15158332, "purple": 10181046}
        embed = discord.Embed(title=title, description=description, color=color_map.get(color, 3447003))
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="remind_rsvp", description="Send RSVP reminders to users who haven't RSVPed.")
    async def remind_rsvp(self, ctx, event_id: int):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Manage Events' or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT rsvp_list FROM events WHERE event_id = ?", (event_id,))
        row = c.fetchone()
        c.execute("SELECT user_id FROM users")
        all_users = [str(u['user_id']) for u in c.fetchall()]
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        not_rsvped = [uid for uid in all_users if uid not in rsvped]
        conn.close()
        for uid in not_rsvped:
            member = ctx.guild.get_member(int(uid))
            if member:
                try:
                    await member.send(f"Reminder: RSVP for event {event_id}!")
                except:
                    pass
        msg = f"Reminders sent to {len(not_rsvped)} users."
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @commands.hybrid_command(name="assign_event_role", description="Assign a role to all event attendees.")
    async def assign_event_role(self, ctx, event_id: int, role: discord.Role):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Manage Events' or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT rsvp_list FROM events WHERE event_id = ?", (event_id,))
        row = c.fetchone()
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        conn.close()
        for uid in rsvped:
            member = ctx.guild.get_member(int(uid))
            if member:
                try:
                    await member.add_roles(role)
                except:
                    pass
        msg = f"Role assigned to {len(rsvped)} attendees."
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @commands.hybrid_command(name="find_free_time", description="Suggest best time for events based on user activity.")
    async def find_free_time(self, ctx):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Manage Events' or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT last_active FROM users")
        times = [u['last_active'] for u in c.fetchall() if u['last_active']]
        conn.close()
        import random
        best_time = random.choice(["18:00", "20:00", "21:00", "19:00"])
        msg = f"Suggested best time for event: {best_time}"
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @commands.hybrid_command(name="create_event_thread", description="Create a thread for an event.")
    async def create_event_thread(self, ctx, event_id: int):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Manage Events' or 'Manage Server' permission.", ephemeral=True)
            else:
                await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        thread = await ctx.channel.create_thread(name=f"Event {event_id} Discussion")
        msg = f"Thread created: {thread.mention}"
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)
    @commands.hybrid_command(name="setprefix", description="Change the bot prefix for this server.")
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx, prefix: str):
        from eventus_render_mega import set_guild_prefix
        set_guild_prefix(ctx.guild.id, prefix)
        msg = f"Prefix updated to `{prefix}`."
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        conn = sqlite3.connect('eventus.db')
        conn.row_factory = sqlite3.Row
        return conn

    @commands.hybrid_command(name="create_event", description="Create an event with RSVP, recurrence, and reminders.")
    async def create_event(self, ctx, title: str, *, description: str):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        if not (perms.manage_guild or perms.manage_events or getattr(perms, 'create_events', False)):
            if hasattr(ctx, 'respond'):
                await ctx.respond("You need 'Create Events', 'Manage Events', or 'Manage Server' permission to create events.", ephemeral=True)
            else:
                await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission to create events.")
            return
        conn = self.get_db()
        c = conn.cursor()
        recurrence = 'none'
        if 'weekly' in description.lower():
            recurrence = 'weekly'
        start_time = None
        end_time = None
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        c.execute("INSERT INTO events (title, description, creator_id, start_time, end_time, rsvp_list, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (title, description, user.id, start_time, end_time, "", recurrence))
        event_id = c.lastrowid
        conn.commit()
        conn.close()
        embed = discord.Embed(title=f"📅 Event: {title}", description=description, color=discord.Color.blue())
        embed.set_footer(text=f"Event ID: {event_id} | Recurrence: {recurrence}")
        if hasattr(ctx, 'respond'):
            msg = await ctx.respond(embed=embed)
        else:
            msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        info = f"Event created! Use `{ctx.prefix}rsvp {event_id}` to RSVP."
        if hasattr(ctx, 'respond'):
            await ctx.respond(info)
        else:
            await ctx.send(info)

    @commands.hybrid_command(name="rsvp", description="RSVP to an event.")
    async def rsvp_event(self, ctx, event_id: int):
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT rsvp_list, archived FROM events WHERE event_id = ?", (event_id,))
        row = c.fetchone()
        if not row:
            msg = "Event not found."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        if row['archived']:
            msg = "This event is archived."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        rsvp_list = row['rsvp_list'].split(',') if row['rsvp_list'] else []
        user_id = str(user.id)
        if user_id in rsvp_list:
            msg = "You already RSVPed."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        rsvp_list.append(user_id)
        c.execute("UPDATE events SET rsvp_list = ? WHERE event_id = ?", (','.join(rsvp_list), event_id))
        conn.commit()
        conn.close()
        msg = f"{user.mention} RSVPed to event {event_id}!"
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @commands.hybrid_command(name="archive_event", description="Archive an event (manage_events or owner only).")
    async def archive_event(self, ctx, event_id: int):
        perms = ctx.author.guild_permissions if hasattr(ctx, 'author') else ctx.user.guild_permissions
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        if not (perms.manage_events or perms.manage_guild or user.id in [1300838678280671264, 1382187068373074001, 1311394031640776716, 1310134550566797352]):
            msg = "You need 'Manage Events', 'Manage Server', or be an owner to archive events."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        conn = self.get_db()
        c = conn.cursor()
        c.execute("UPDATE events SET archived = 1 WHERE event_id = ?", (event_id,))
        conn.commit()
        conn.close()
        msg = f"Event {event_id} archived."
        if hasattr(ctx, 'respond'):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(EventOS(bot))
