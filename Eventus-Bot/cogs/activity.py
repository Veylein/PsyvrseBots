from discord import app_commands, Interaction
import discord
from discord.ext import commands, tasks
import datetime
from .. import db_async as db
import time
from typing import Dict, Tuple
import json
import io
import asyncio

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
        # rate limiter: map (guild_id, user_id) -> (count, window_start)
        self._rate: Dict[Tuple[int, int], Tuple[int, float]] = {}
        # config: max counted messages per window (per user)
        self._rate_window_seconds = 60
        self._rate_max_per_window = 6
        self._rate_cleanup_task = tasks.loop(seconds=30.0)(self._rate_cleanup)
        self._rate_cleanup_task.start()

    # Using async DB helper (`db_async`) — no synchronous get_db

    def cog_unload(self):
        try:
            self.ping_task.cancel()
        except Exception:
            pass

    async def update_activity(self, user_id, username, guild_id, channel_id, message_type, topic=None, extra: float = 0):
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
        total_add = float(weight) + float(extra)
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
            user_id, username, total_add, now, streak, topic_influence, ','.join(multi_channel),
            total_add, now, streak, topic_influence, ','.join(multi_channel)
        ), commit=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        user_id = message.author.id
        username = str(message.author)
        guild_id = message.guild.id if message.guild else None
        channel_id = message.channel.id
        # check ignored channels/roles for this guild
        try:
            if guild_id:
                chrow = await db.fetchone("SELECT 1 FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
                if chrow:
                    return
                # check roles
                roles = [r.id for r in message.author.roles]
                if roles:
                    placeholders = ",".join(["?" for _ in roles])
                    q = f"SELECT role_id FROM ignored_roles WHERE guild_id = ? AND role_id IN ({placeholders})"
                    rows = await db.fetchall(q, (guild_id, *roles))
                    if rows:
                        return
        except Exception:
            # On DB failure, proceed but avoid crashing
            pass
        # rate-limit counting to avoid spam gaming
        try:
            key = (guild_id or 0, user_id)
            now_ts = time.time()
            cnt, start = self._rate.get(key, (0, now_ts))
            if now_ts - start > self._rate_window_seconds:
                cnt, start = (0, now_ts)
            if cnt >= self._rate_max_per_window:
                # record message but don't increment activity
                try:
                    content = (message.content or "")[:2000]
                    await db.execute("INSERT OR REPLACE INTO messages (message_id, guild_id, channel_id, author_id, created_at, content) VALUES (?, ?, ?, ?, ?, ?)", (message.id, guild_id, channel_id, user_id, message.created_at.isoformat(), content), commit=True)
                except Exception:
                    pass
                return
            # increment counter
            self._rate[key] = (cnt + 1, start)
        except Exception:
            pass
        # Advanced tracking
        message_type = 'message'
        topic = None
        if message.reference:
            message_type = 'reply'
        # Conversation starter: first message in channel after inactivity
        # (Could check last message time per channel)
        # record message in messages table for analytics
        try:
            content = (message.content or "")[:2000]
            await db.execute("INSERT OR REPLACE INTO messages (message_id, guild_id, channel_id, author_id, created_at, content) VALUES (?, ?, ?, ?, ?, ?)", (message.id, guild_id, channel_id, user_id, message.created_at.isoformat(), content), commit=True)
        except Exception:
            pass
        # add extra weight for longer messages (words)
        try:
            words = len((message.content or "").split())
            extra = min(5, words // 20)  # small bonus per long message
        except Exception:
            extra = 0
        await self.update_activity(user_id, username, guild_id, channel_id, message_type, topic, extra=extra)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        try:
            message = reaction.message
            # ignore reactions if message in ignored channel or user has ignored role
            gid = getattr(message.guild, 'id', None)
            try:
                if gid:
                    chrow = await db.fetchone("SELECT 1 FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (gid, message.channel.id))
                    if chrow:
                        return
                    roles = [r.id for r in user.roles] if hasattr(user, 'roles') else []
                    if roles:
                        placeholders = ",".join(["?" for _ in roles])
                        q = f"SELECT role_id FROM ignored_roles WHERE guild_id = ? AND role_id IN ({placeholders})"
                        rows = await db.fetchall(q, (gid, *roles))
                        if rows:
                            return
            except Exception:
                pass
            # credit the reactor
            await self.update_activity(user.id, str(user), gid, message.channel.id, 'reaction', topic=None, extra=0)
            # small credit to the message author for receiving a reaction
            if message.author and not message.author.bot:
                await self.update_activity(message.author.id, str(message.author), gid, message.channel.id, 'reaction', topic=None, extra=0.5)
        except Exception:
            pass

    async def _rate_cleanup(self):
        # periodically purge old rate limiter entries
        now_ts = time.time()
        remove = []
        for k, v in list(self._rate.items()):
            cnt, start = v
            if now_ts - start > self._rate_window_seconds * 2:
                remove.append(k)
        for k in remove:
            try:
                del self._rate[k]
            except KeyError:
                pass

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

    @commands.hybrid_command(name="leaderboard", description="Show top active users by activity score.")
    async def leaderboard(self, ctx, top: int = 10):
        guild = ctx.guild
        if not guild:
            await ctx.send("This command must be used in a server.")
            return
        top = max(1, min(50, top))
        rows = await db.fetchall("SELECT user_id, activity_score FROM users ORDER BY activity_score DESC LIMIT ?", (top,))
        if not rows:
            await ctx.send("No activity data available.")
            return
        lines = []
        rank = 1
        for r in rows:
            uid = r['user_id']
            score = r.get('activity_score', 0)
            member = guild.get_member(uid)
            name = member.mention if member else str(uid)
            lines.append(f"#{rank} {name} — {score} pts")
            rank += 1
        await ctx.send("\n".join(lines))

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

    @commands.command(name="ignore_channel")
    @commands.has_permissions(manage_guild=True)
    async def ignore_channel(self, ctx, channel: discord.TextChannel):
        """Ignore a channel for activity tracking."""
        await db.execute("INSERT OR IGNORE INTO ignored_channels (guild_id, channel_id) VALUES (?, ?)", (ctx.guild.id, channel.id), commit=True)
        await ctx.send(f"Channel {channel.mention} will be ignored for activity tracking.")

    @commands.command(name="unignore_channel")
    @commands.has_permissions(manage_guild=True)
    async def unignore_channel(self, ctx, channel: discord.TextChannel):
        await db.execute("DELETE FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (ctx.guild.id, channel.id), commit=True)
        await ctx.send(f"Channel {channel.mention} will no longer be ignored.")

    @commands.command(name="list_ignored_channels")
    @commands.has_permissions(manage_guild=True)
    async def list_ignored_channels(self, ctx):
        rows = await db.fetchall("SELECT channel_id FROM ignored_channels WHERE guild_id = ?", (ctx.guild.id,))
        if not rows:
            await ctx.send("No ignored channels set for this server.")
            return
        mentions = []
        for r in rows:
            ch = ctx.guild.get_channel(r['channel_id'])
            mentions.append(ch.mention if ch else str(r['channel_id']))
        await ctx.send("Ignored channels:\n" + '\n'.join(mentions))

    @commands.command(name="ignore_role")
    @commands.has_permissions(manage_guild=True)
    async def ignore_role(self, ctx, role: discord.Role):
        """Ignore a role for activity tracking (users with this role won't be counted)."""
        await db.execute("INSERT OR IGNORE INTO ignored_roles (guild_id, role_id) VALUES (?, ?)", (ctx.guild.id, role.id), commit=True)
        await ctx.send(f"Users with role {role.name} will be ignored for activity tracking.")

    @commands.command(name="unignore_role")
    @commands.has_permissions(manage_guild=True)
    async def unignore_role(self, ctx, role: discord.Role):
        await db.execute("DELETE FROM ignored_roles WHERE guild_id = ? AND role_id = ?", (ctx.guild.id, role.id), commit=True)
        await ctx.send(f"Role {role.name} will no longer be ignored.")

    @commands.command(name="list_ignored_roles")
    @commands.has_permissions(manage_guild=True)
    async def list_ignored_roles(self, ctx):
        rows = await db.fetchall("SELECT role_id FROM ignored_roles WHERE guild_id = ?", (ctx.guild.id,))
        if not rows:
            await ctx.send("No ignored roles set for this server.")
            return
        names = []
        for r in rows:
            role = ctx.guild.get_role(r['role_id'])
            names.append(role.name if role else str(r['role_id']))
        await ctx.send("Ignored roles:\n" + '\n'.join(names))

    @commands.command(name="export_stats")
    @commands.has_permissions(manage_guild=True)
    async def export_stats(self, ctx):
        """Export key tables (users, events, pings, rewards, topic settings) to a JSON file and send it."""
        await ctx.send("Preparing export, this may take a few seconds...")
        async def gather():
            out = {}
            tbls = {
                'users': "SELECT * FROM users",
                'events': "SELECT * FROM events",
                'pings': "SELECT * FROM pings",
                'rewards': "SELECT * FROM rewards",
                'topic_settings': "SELECT * FROM topic_settings",
                'topic_opt_out': "SELECT * FROM topic_opt_out",
                'ignored_channels': "SELECT * FROM ignored_channels",
                'ignored_roles': "SELECT * FROM ignored_roles",
            }
            for name, q in tbls.items():
                try:
                    rows = await db.fetchall(q)
                    out[name] = [dict(r) for r in rows] if rows else []
                except Exception:
                    out[name] = []
            return out

        data = await gather()
        b = io.BytesIO(json.dumps(data, default=str, indent=2).encode('utf-8'))
        b.seek(0)
        try:
            await ctx.send(file=discord.File(b, filename=f"eventus_export_{ctx.guild.id}.json"))
        except Exception:
            await ctx.send("Failed to send export file; writing to disk instead.")
            path = f"eventus_export_{ctx.guild.id}.json"
            await asyncio.to_thread(lambda: open(path, 'wb').write(b.getvalue()))
            await ctx.send(f"Wrote export to {path}")

    @commands.command(name="export_messages")
    @commands.has_permissions(manage_guild=True)
    async def export_messages(self, ctx, limit: int = 2000):
        """Export recent messages for this guild (up to `limit`)."""
        limit = max(10, min(20000, limit))
        await ctx.send(f"Gathering last {limit} messages from DB...")
        try:
            rows = await db.fetchall("SELECT message_id, guild_id, channel_id, author_id, created_at, content FROM messages WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?", (ctx.guild.id, limit))
            data = [dict(r) for r in rows] if rows else []
            b = io.BytesIO(json.dumps({'messages': data}, default=str, indent=2).encode('utf-8'))
            b.seek(0)
            await ctx.send(file=discord.File(b, filename=f"eventus_messages_{ctx.guild.id}.json"))
        except Exception as e:
            await ctx.send(f"Failed to export messages: {e}")

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

    @commands.hybrid_command(name="ping_optout", description="Opt-out of being pinged by Eventus for top contributors in this server.")
    async def ping_optout(self, ctx):
        guild = ctx.guild
        if not guild:
            await ctx.send("This command must be used in a server.")
            return
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        await db.execute("INSERT OR IGNORE INTO topic_opt_out (guild_id, user_id) VALUES (?, ?)", (guild.id, user.id), commit=True)
        await ctx.respond("You have opted out of top contributor pings for this server.") if hasattr(ctx, 'respond') else await ctx.send("You have opted out of top contributor pings for this server.")

    @commands.hybrid_command(name="ping_optin", description="Re-enable pings from Eventus for top contributors in this server.")
    async def ping_optin(self, ctx):
        guild = ctx.guild
        if not guild:
            await ctx.send("This command must be used in a server.")
            return
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        await db.execute("DELETE FROM topic_opt_out WHERE guild_id = ? AND user_id = ?", (guild.id, user.id), commit=True)
        await ctx.respond("You will now receive top contributor pings again in this server.") if hasattr(ctx, 'respond') else await ctx.send("You will now receive top contributor pings again in this server.")

    @commands.hybrid_command(name="list_optouts", description="List users who opted out of pings (admin only).")
    @commands.has_permissions(manage_guild=True)
    async def list_optouts(self, ctx):
        guild = ctx.guild
        if not guild:
            await ctx.send("This command must be used in a server.")
            return
        rows = await db.fetchall("SELECT user_id FROM topic_opt_out WHERE guild_id = ?", (guild.id,))
        if not rows:
            await ctx.send("No users have opted out in this server.")
            return
        mentions = []
        for r in rows:
            member = guild.get_member(r['user_id'])
            mentions.append(member.mention if member else str(r['user_id']))
        await ctx.send("Opted-out users:\n" + '\n'.join(mentions))

    # ...existing code...

async def setup(bot):
    await bot.add_cog(ActivityEngine(bot))
