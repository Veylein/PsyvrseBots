import discord
from discord.ext import commands, tasks
from .. import db_async as db
import datetime

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_report.start()

    def cog_unload(self):
        self.weekly_report.cancel()

    async def get_weekly_stats(self):
        one_week_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
        users = await db.fetchall("SELECT * FROM users")
        total_msgs = sum(u['activity_score'] for u in users)
        most_helpful = max(users, key=lambda u: u['activity_score'], default=None)
        most_reactive = most_helpful  # Placeholder
        # Average interaction depth (demo: activity_score / users)
        avg_interaction = total_msgs / len(users) if users else 0
        # Topic of the week (from analytics)
        topic_row = await db.fetchone("SELECT data FROM analytics WHERE data LIKE 'topic:%' ORDER BY created_at DESC LIMIT 1")
        topic_of_week = topic_row['data'].split(':', 1)[-1] if topic_row else "N/A"
        # Channel activity map (demo: random)
        channel_map = "#general: 50, #events: 30, #random: 20"
        # Calculate peak/silent hours (demo: random)
        peak_hours = "18:00-21:00"
        silent_hours = "03:00-06:00"
        # Weekly activity score comparison (demo: difference from last week)
        snapshots = await db.fetchall("SELECT * FROM analytics ORDER BY created_at DESC LIMIT 2")
        activity_comparison = "N/A"
        if len(snapshots) == 2:
            try:
                prev = int(snapshots[1]['data'].split(':')[-1])
                curr = int(snapshots[0]['data'].split(':')[-1])
                activity_comparison = f"{curr - prev:+d} vs last week"
            except:
                pass
        return {
            'total_msgs': total_msgs,
            'most_helpful': most_helpful,
            'most_reactive': most_reactive,
            'users': users,
            'avg_interaction': avg_interaction,
            'topic_of_week': topic_of_week,
            'channel_map': channel_map,
            'peak_hours': peak_hours,
            'silent_hours': silent_hours,
            'activity_comparison': activity_comparison,
            'vibe_rating': "(AI generated soon)"
        }

    @tasks.loop(hours=168)  # Weekly
    async def weekly_report(self):
        # Drop analytics in all guilds
        stats = await self.get_weekly_stats()
        # Store analytics snapshot
        await db.execute("INSERT INTO analytics (created_at, data) VALUES (?, ?)", (datetime.datetime.utcnow().isoformat(), f"activity_score:{stats['total_msgs']}"), commit=True)
        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name="general")
            if not channel:
                continue
            embed = discord.Embed(title="📊 Social Health Dashboard", color=discord.Color.purple())
            embed.add_field(name="Total Messages Sent", value=stats['total_msgs'])
            embed.add_field(name="Average Interaction Depth", value=f"{stats['avg_interaction']:.2f}")
            if stats['most_helpful']:
                embed.add_field(name="Most Helpful User", value=stats['most_helpful']['username'])
            if stats['most_reactive']:
                embed.add_field(name="Most Reactive User", value=stats['most_reactive']['username'])
            embed.add_field(name="Topic of the Week", value=stats['topic_of_week'])
            embed.add_field(name="Peak Chat Hours", value=stats['peak_hours'])
            embed.add_field(name="Silent Hours", value=stats['silent_hours'])
            embed.add_field(name="Channel Activity Map", value=stats['channel_map'])
            embed.add_field(name="Weekly Activity Score Comparison", value=stats['activity_comparison'])
            embed.add_field(name="Community Vibe Rating", value=stats['vibe_rating'])
            await channel.send(embed=embed)

    @commands.hybrid_command(name="dashboard", description="Show the current social health dashboard.")
    async def dashboard(self, ctx):
        stats = await self.get_weekly_stats()
        embed = discord.Embed(title="📊 Social Health Dashboard", color=discord.Color.purple())
        embed.add_field(name="Total Messages Sent", value=stats['total_msgs'])
        embed.add_field(name="Average Interaction Depth", value=f"{stats['avg_interaction']:.2f}")
        if stats['most_helpful']:
            embed.add_field(name="Most Helpful User", value=stats['most_helpful']['username'])
        if stats['most_reactive']:
            embed.add_field(name="Most Reactive User", value=stats['most_reactive']['username'])
        embed.add_field(name="Topic of the Week", value=stats['topic_of_week'])
        embed.add_field(name="Peak Chat Hours", value=stats['peak_hours'])
        embed.add_field(name="Silent Hours", value=stats['silent_hours'])
        embed.add_field(name="Channel Activity Map", value=stats['channel_map'])
        embed.add_field(name="Weekly Activity Score Comparison", value=stats['activity_comparison'])
        embed.add_field(name="Community Vibe Rating", value=stats['vibe_rating'])
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dashboard(bot))
