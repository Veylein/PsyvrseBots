from discord import app_commands, Interaction
import discord
from discord.ext import commands
import sqlite3
import datetime

class ActivityEngine(commands.Cog):
    @commands.hybrid_command(name="aip", description="Show Activity Intelligence Profile (AIP) for a user.")
    async def aip(self, ctx, member: discord.Member = None):
        member = member or (ctx.author if hasattr(ctx, 'author') else ctx.user)
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
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

    def get_db(self):
        conn = sqlite3.connect('eventus.db')
        conn.row_factory = sqlite3.Row
        return conn

    def update_activity(self, user_id, username, guild_id, channel_id, message_type, topic=None):
        conn = self.get_db()
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        # Weighted message count
        weight = 1
        if message_type == 'starter':
            weight = 3
        elif message_type == 'reply':
            weight = 2
        elif message_type == 'reaction':
            weight = 1.5
        # Streak logic
        c.execute("SELECT last_active, streak, multi_channel_presence FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
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
        c.execute("""
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
        ))
        conn.commit()
        conn.close()

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
        self.update_activity(user_id, username, guild_id, channel_id, message_type, topic)

    # ...existing code...

async def setup(bot):
    await bot.add_cog(ActivityEngine(bot))
