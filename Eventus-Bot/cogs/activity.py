from discord import app_commands, Interaction
import discord
from discord.ext import commands, tasks
import datetime
from .. import db_async as db

class ActivityEngine(commands.Cog):
    @commands.hybrid_command(name="aip", description="Show Activity Intelligence Profile (AIP) for a user.")
    async def aip(self, ctx, member: discord.Member = None):
        member = member or (ctx.author if hasattr(ctx, 'author') else ctx.user)
        row = await db.fetchone("SELECT * FROM users WHERE user_id = ?", (member.id,))
        if not row:
            if hasattr(ctx, 'respond'):
                await ctx.respond(f"No activity data for {member.display_name}.", ephemeral=True)
            else:
                await ctx.send(f"No activity data for {member.display_name}.")
            return
        embed = discord.Embed(title=f"Activity Intelligence Profile: {member.display_name}", color=discord.Color.green())
        embed.add_field(name="Activity Score", value=row['activity_score'])
        embed.add_field(name="Momentum", value=row['momentum'])
        embed.add_field(name="Streak", value=row['streak'])
        embed.add_field(name="Last Active", value=row['last_active'])
        embed.add_field(name="Topic Influence", value=row['topic_influence'])
        embed.add_field(name="Multi-Channel Presence", value=len(str(row['multi_channel_presence']).split(',')) if row['multi_channel_presence'] else 0)
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)
    def __init__(self, bot):
        self.bot = bot
        self.ping_task.start()

    # Using async DB helper (`db_async`) — no synchronous get_db

    def cog_unload(self):
        try:
            self.ping_task.cancel()
        except Exception:
            pass

    async def update_activity(self, user_id, username, guild_id, channel_id, message_type, topic=None):
        now = datetime.datetime.utcnow().isoformat()
        # Weighted message count
        weight = 1
        if message_type == 'starter':
            weight = 3
        elif message_type == 'reply':
            weight = 2
        elif message_type == 'reaction':
            weight = 1.5
        # Streak logic (read then write)
        row = await db.fetchone("SELECT last_active, streak, multi_channel_presence FROM users WHERE user_id = ?", (user_id,))
        streak = 1
        multi_channel = set()
        if row:
            last_active = row['last_active']
            if last_active:
                last_dt = datetime.datetime.fromisoformat(last_active)
                if (datetime.datetime.utcnow() - last_dt).days == 1:
                    streak = row['streak'] + 1
                elif (datetime.datetime.utcnow() - last_dt).days > 1:
                    streak = 1
                else:
                    streak = row['streak']
            multi_channel = set(str(row['multi_channel_presence']).split(',')) if row['multi_channel_presence'] else set()
        multi_channel.add(str(channel_id))
        # Topic influence
        topic_influence = 0.0
        if topic:
            topic_influence = 1.0
        await db.execute("""
            INSERT INTO users (user_id, username, activity_score, last_active, streak, topic_influence, multi_channel_presence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                activity_score = activity_score + ?,
                username = excluded.username,
                last_active = ?,
                streak = ?,
                topic_influence = topic_influence + ?,
                multi_channel_presence = ?
        """, (
            user_id, username, weight, now, streak, topic_influence, ','.join(multi_channel),
            weight, now, streak, topic_influence, ','.join(multi_channel)
        ), commit=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        user_id = message.author.id
        username = str(message.author)
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id
        # Advanced tracking
        message_type = 'message'
        topic = None
        if message.reference:
            message_type = 'reply'
        # Conversation starter: first message in channel after inactivity
        # (Could check last message time per channel)
        await self.update_activity(user_id, username, guild_id, channel_id, message_type, topic)

    @commands.hybrid_command(name="server_stats", description="Show server activity stats: top members, top channels, and recent activity times.")
    async def server_stats(self, ctx):
        guild = ctx.guild
        if not guild:
            await ctx.send("This command must be used in a server.")
            return
        # Top members by message count in messages table
        member_rows = await db.fetchall("SELECT author_id, COUNT(*) as cnt FROM messages WHERE guild_id = ? GROUP BY author_id ORDER BY cnt DESC LIMIT 10", (guild.id,))
        top_members = []
        for r in member_rows:
            uid = r['author_id']
            cnt = r['cnt']
            member = guild.get_member(uid)
            last = await db.fetchone("SELECT last_active FROM users WHERE user_id = ?", (uid,))
            last_active = last['last_active'] if last else None
            last_ts = ''
            if last_active:
                try:
                    dt = datetime.datetime.fromisoformat(last_active)
                    last_ts = f" (<t:{int(dt.timestamp())}:R>)"
                except Exception:
                    last_ts = ''
            top_members.append(f"{member.mention if member else uid} — {cnt} msgs{last_ts}")

        # Top channels
        chan_rows = await db.fetchall("SELECT channel_id, COUNT(*) as cnt FROM messages WHERE guild_id = ? GROUP BY channel_id ORDER BY cnt DESC LIMIT 10", (guild.id,))
        top_channels = []
        for r in chan_rows:
            cid = r['channel_id']
            cnt = r['cnt']
            ch = guild.get_channel(cid)
            top_channels.append(f"{ch.mention if ch else cid} — {cnt} msgs")

        # Recent activity time for guild
        last_row = await db.fetchone("SELECT MAX(created_at) as last FROM messages WHERE guild_id = ?", (guild.id,))
        last_msg_time = last_row['last'] if last_row else None
        last_msg_field = 'No recent messages recorded.'
        if last_msg_time:
            try:
                ldt = datetime.datetime.fromisoformat(last_msg_time)
                last_msg_field = f"Last recorded message: <t:{int(ldt.timestamp())}:f> (<t:{int(ldt.timestamp())}:R>)"
            except Exception:
                last_msg_field = f"Last recorded message: {last_msg_time}"

        embed = discord.Embed(title=f"Server Activity — {guild.name}", color=discord.Color.purple())
        embed.add_field(name="Top Members", value='\n'.join(top_members) if top_members else 'No data', inline=False)
        embed.add_field(name="Top Channels", value='\n'.join(top_channels) if top_channels else 'No data', inline=False)
        embed.add_field(name="Recent Activity", value=last_msg_field, inline=False)
        await ctx.send(embed=embed)

    @tasks.loop(minutes=60.0)
    async def ping_task(self):
        # Periodically ping top contributors for configured pings
        rows = await db.fetchall("SELECT ping_id, guild_id, channel_id, top_n, interval_minutes, last_sent FROM pings")
        for row in rows:
            guild = self.bot.get_guild(row['guild_id'])
            if not guild:
                continue
            channel = guild.get_channel(row['channel_id'])
            if not channel:
                continue
            # respect per-ping cooldown
            try:
                last_sent = row.get('last_sent')
                if last_sent:
                    last_dt = datetime.datetime.fromisoformat(last_sent)
                    interval = int(row.get('interval_minutes') or 60)
                    if (datetime.datetime.utcnow() - last_dt).total_seconds() < interval * 60:
                        continue
            except Exception:
                pass
            top_n = row['top_n'] or 3
            leaders = await db.fetchall("SELECT user_id, activity_score FROM users ORDER BY activity_score DESC LIMIT ?", (top_n,))
            if not leaders:
                continue
            mentions = []
            for leader in leaders:
                user_id = leader['user_id']
                opt = await db.fetchone("SELECT 1 FROM topic_opt_out WHERE guild_id = ? AND user_id = ?", (guild.id, user_id))
                if opt:
                    continue
                member = guild.get_member(user_id)
                if member:
                    mentions.append(member.mention)
            if mentions:
                try:
                    await channel.send(f"🔥 Top contributors: {' '.join(mentions)} — keep chatting!")
                    await db.execute("UPDATE pings SET last_sent = ? WHERE ping_id = ?", (datetime.datetime.utcnow().isoformat(), row['ping_id']), commit=True)
                except Exception:
                    pass

    @ping_task.before_loop
    async def before_ping(self):
        await self.bot.wait_until_ready()

    @commands.command(name="add_ping")
    @commands.has_permissions(manage_guild=True)
    async def add_ping(self, ctx, channel: discord.TextChannel, interval_minutes: int = 60, top_n: int = 3):
        """Configure a dynamic ping in a channel to notify top contributors."""
        await db.execute("INSERT INTO pings (guild_id, channel_id, interval_minutes, top_n, last_sent) VALUES (?, ?, ?, ?, ?)", (ctx.guild.id, channel.id, interval_minutes, top_n, None), commit=True)
        last = await db.fetchone("SELECT ping_id FROM pings WHERE guild_id = ? AND channel_id = ? ORDER BY ping_id DESC LIMIT 1", (ctx.guild.id, channel.id))
        ping_id = last['ping_id'] if last else 'unknown'
        await ctx.send(f"Ping configured (id={ping_id}) in {channel.mention} every {interval_minutes} minutes for top {top_n} users.")

    @commands.command(name="list_pings")
    async def list_pings(self, ctx):
        rows = await db.fetchall("SELECT ping_id, channel_id, interval_minutes, top_n, last_sent FROM pings WHERE guild_id = ?", (ctx.guild.id,))
        if not rows:
            await ctx.send("No pings configured for this server.")
            return
        lines = []
        for r in rows:
            ch = ctx.guild.get_channel(r['channel_id'])
            lines.append(f"[{r['ping_id']}] {ch.mention if ch else r['channel_id']} every {r['interval_minutes']}m top={r['top_n']} last_sent={r['last_sent']}")
        await ctx.send("\n".join(lines))

    @commands.command(name="remove_ping")
    @commands.has_permissions(manage_guild=True)
    async def remove_ping(self, ctx, ping_id: int):
        await db.execute("DELETE FROM pings WHERE ping_id = ? AND guild_id = ?", (ping_id, ctx.guild.id), commit=True)
        row = await db.fetchone("SELECT 1 FROM pings WHERE ping_id = ?", (ping_id,))
        if row:
            await ctx.send(f"Failed to remove ping {ping_id}.")
        else:
            await ctx.send(f"Removed ping {ping_id}.")

    # ...existing code...

async def setup(bot):
    await bot.add_cog(ActivityEngine(bot))
