import discord
from discord.ext import commands
import traceback
from datetime import datetime, timezone
import asyncio
import aiohttp
import sys
import json
from typing import Optional, List, Dict, Any

class BotLogger(commands.Cog):
    """Comprehensive logging system for all bot activities"""

    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1442605619835179127

    async def get_log_channel(self):
        """Get the logging channel"""
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            return channel
        except():
            return None

    async def log(
        self,
        title: str,
        description: str,
        color: discord.Color,
        fields: Optional[List[Dict[str, Any]]] = None,
    ):
        """Send a log message to the logging channel"""
        channel = await self.get_log_channel()
        if not channel:
            return

        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            if fields:
                for field in fields:
                    embed.add_field(
                        name=field.get("name", "Field"),
                        value=field.get("value", "No value"),
                        inline=field.get("inline", False)
                    )

            await channel.send(embed=embed)
        except Exception as e:
            print(f"[LOGGER] Failed to send log: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Log all command errors with specific handling for different error types"""
        error = getattr(error, 'original', error)

        error_msg = str(error)
        full_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        if len(full_traceback) > 1800:
            full_traceback = full_traceback[:1800] + "\n... (truncated)"

        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            title = "🔒 PERMISSION ERROR"
            color = discord.Color.orange()
        elif isinstance(error, commands.BotMissingPermissions):
            title = "⚠️ BOT PERMISSION ERROR"
            color = discord.Color.orange()
        elif isinstance(error, commands.MissingRequiredArgument):
            title = "📝 MISSING ARGUMENT ERROR"
            color = discord.Color.gold()
        elif isinstance(error, commands.BadArgument):
            title = "❓ BAD ARGUMENT ERROR"
            color = discord.Color.gold()
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.MaxConcurrencyReached):
            title = "⏸️ CONCURRENCY ERROR"
            color = discord.Color.orange()
        elif isinstance(error, discord.RateLimited):
            title = "🚦 RATE LIMIT ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.Forbidden):
            title = "🚫 FORBIDDEN ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.HTTPException):
            title = "🌐 HTTP ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.NotFound):
            title = "🔍 NOT FOUND ERROR"
            color = discord.Color.orange()
        elif isinstance(error, discord.DiscordServerError):
            title = "🔥 DISCORD SERVER ERROR"
            color = discord.Color.dark_red()
        elif isinstance(error, discord.InvalidData):
            title = "📊 INVALID DATA ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.GatewayNotFound):
            title = "🌐 GATEWAY NOT FOUND"
            color = discord.Color.dark_red()
        elif isinstance(error, discord.ConnectionClosed):
            title = "🔌 CONNECTION CLOSED"
            color = discord.Color.dark_red()
        elif isinstance(error, asyncio.TimeoutError):
            title = "⏱️ TIMEOUT ERROR"
            color = discord.Color.orange()
        elif isinstance(error, asyncio.CancelledError):
            title = "🚫 TASK CANCELLED"
            color = discord.Color.orange()
        elif isinstance(error, aiohttp.ClientError):
            title = "🌐 CLIENT ERROR"
            color = discord.Color.red()
        elif isinstance(error, aiohttp.ServerDisconnectedError):
            title = "🔌 SERVER DISCONNECTED"
            color = discord.Color.red()
        elif isinstance(error, aiohttp.ClientConnectionError):
            title = "🔌 CLIENT CONNECTION ERROR"
            color = discord.Color.red()
        elif isinstance(error, ConnectionError):
            title = "🔌 CONNECTION ERROR"
            color = discord.Color.red()
        elif isinstance(error, OSError):
            title = "💾 OS ERROR"
            color = discord.Color.red()
        elif isinstance(error, MemoryError):
            title = "🧠 MEMORY ERROR"
            color = discord.Color.dark_red()
        elif isinstance(error, json.JSONDecodeError):
            title = "📋 JSON DECODE ERROR"
            color = discord.Color.orange()
        else:
            title = "❌ COMMAND ERROR"
            color = discord.Color.red()

        await self.log(
            title=title,
            description=f"**Error Type:** {type(error).__name__}\n**Error:** {error_msg}",
            color=color,
            fields=[
                {"name": "Command", "value": f"`{ctx.command.name if ctx.command else 'Unknown'}`", "inline": True},
                {"name": "User", "value": f"{ctx.author} ({ctx.author.id})", "inline": True},
                {"name": "Server", "value": f"{ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'})", "inline": True},
                {"name": "Channel", "value": f"#{ctx.channel.name if hasattr(ctx.channel, 'name') else 'DM'}", "inline": True},
                {"name": "Traceback", "value": f"```python\n{full_traceback}\n```", "inline": False}
            ]
        )

    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error):
        """Log slash command errors with specific handling"""
        error = getattr(error, 'original', error)

        error_msg = str(error)
        full_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        if len(full_traceback) > 1800:
            full_traceback = full_traceback[:1800] + "\n... (truncated)"

        if isinstance(error, discord.Forbidden):
            title = "🚫 SLASH FORBIDDEN ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.HTTPException):
            title = "🌐 SLASH HTTP ERROR"
            color = discord.Color.red()
        elif isinstance(error, discord.NotFound):
            title = "🔍 SLASH NOT FOUND ERROR"
            color = discord.Color.orange()
        elif isinstance(error, asyncio.TimeoutError):
            title = "⏱️ SLASH TIMEOUT ERROR"
            color = discord.Color.orange()
        else:
            title = "❌ SLASH COMMAND ERROR"
            color = discord.Color.red()

        await self.log(
            title=title,
            description=f"**Error Type:** {type(error).__name__}\n**Error:** {error_msg}",
            color=color,
            fields=[
                {"name": "Command", "value": f"`/{interaction.command.name if interaction.command else 'Unknown'}`", "inline": True},
                {"name": "User", "value": f"{interaction.user} ({interaction.user.id})", "inline": True},
                {"name": "Server", "value": f"{interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild.id if interaction.guild else 'N/A'})", "inline": True},
                {"name": "Traceback", "value": f"```python\n{full_traceback}\n```", "inline": False}
            ]
        )

    async def log_owner_command(self, ctx, command_name: str, details: str = ""):
        """Log owner commands"""
        await self.log(
            title="👑 OWNER COMMAND USED",
            description=f"**Command:** `{command_name}`\n{details}",
            color=discord.Color.purple(),
            fields=[
                {"name": "User", "value": f"{ctx.author} ({ctx.author.id})", "inline": True},
                {"name": "Server", "value": f"{ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'})", "inline": True},
                {"name": "Channel", "value": f"#{ctx.channel.name if hasattr(ctx.channel, 'name') else 'DM'}", "inline": True}
            ]
        )

    async def log_admin_command(self, ctx, command_name: str, details: str = ""):
        """Log admin commands"""
        await self.log(
            title="🛡️ ADMIN COMMAND USED",
            description=f"**Command:** `{command_name}`\n{details}",
            color=discord.Color.blue(),
            fields=[
                {"name": "User", "value": f"{ctx.author} ({ctx.author.id})", "inline": True},
                {"name": "Server", "value": f"{ctx.guild.name if ctx.guild else 'DM'}", "inline": True},
                {"name": "Channel", "value": f"#{ctx.channel.name if hasattr(ctx.channel, 'name') else 'DM'}", "inline": True}
            ]
        )

    async def log_event_spawn(self, event_type: str, guild_id: int, spawner_id: int, details: str = ""):
        """Log global event spawns"""
        try:
            guild = self.bot.get_guild(guild_id)
            spawner = await self.bot.fetch_user(spawner_id)

            await self.log(
                title="🌍 GLOBAL EVENT SPAWNED",
                description=f"**Event Type:** {event_type}\n{details}",
                color=discord.Color.gold(),
                fields=[
                    {"name": "Spawned By", "value": f"{spawner} ({spawner_id})", "inline": True},
                    {"name": "Server", "value": f"{guild.name if guild else 'Unknown'} ({guild_id})", "inline": True}
                ]
            )
        except():
            pass

    async def log_event_end(self, event_type: str, details: str = ""):
        """Log global event endings"""
        await self.log(
            title="🏁 GLOBAL EVENT ENDED",
            description=f"**Event Type:** {event_type}\n{details}",
            color=discord.Color.orange()
        )

    async def log_moderation(self, action: str, guild_id: int, moderator_id: int, target_id: int, reason: str = ""):
        """Log moderation actions"""
        try:
            guild = self.bot.get_guild(guild_id)
            moderator = await self.bot.fetch_user(moderator_id)
            target = await self.bot.fetch_user(target_id)

            await self.log(
                title=f"🔨 MODERATION: {action.upper()}",
                description=f"**Action:** {action}\n**Reason:** {reason or 'No reason provided'}",
                color=discord.Color.red(),
                fields=[
                    {"name": "Moderator", "value": f"{moderator} ({moderator_id})", "inline": True},
                    {"name": "Target", "value": f"{target} ({target_id})", "inline": True},
                    {"name": "Server", "value": f"{guild.name if guild else 'Unknown'}", "inline": True}
                ]
            )
        except():
            pass

    async def log_economy(self, transaction_type: str, user_id: int, amount: int, reason: str = ""):
        """Log major economy transactions"""
        if amount < 1000:
            return

        try:
            user = await self.bot.fetch_user(user_id)

            await self.log(
                title="💰 LARGE TRANSACTION",
                description=f"**Type:** {transaction_type}\n**Amount:** {amount:,} PsyCoins\n**Reason:** {reason}",
                color=discord.Color.green(),
                fields=[
                    {"name": "User", "value": f"{user} ({user_id})", "inline": True}
                ]
            )
        except():
            pass

    async def log_bot_event(self, event_type: str, description: str):
        """Log important bot events (startup, shutdown, etc)"""
        await self.log(
            title=f"🤖 BOT EVENT: {event_type.upper()}",
            description=description,
            color=discord.Color.blurple()
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """Log bot startup"""
        await self.log_bot_event(
            "STARTUP",
            f"**Bot is online!**\n"
            f"**Servers:** {len(self.bot.guilds)}\n"
            f"**Users:** {sum(g.member_count for g in self.bot.guilds):,}\n"
            f"**Latency:** {round(self.bot.latency * 1000)}ms"
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        invite = "N/A"

        try:
            if guild.system_channel:
                inv = await guild.system_channel.create_invite(max_age=0, max_uses=1)
                invite = inv.url
        except():
            pass

        await self.log(
            title="📥 JOINED SERVER",
            description=(
                f"**Server:** {guild.name}\n"
                f"**ID:** {guild.id}\n"
                f"**Members:** {guild.member_count:,}\n"
                f"**Invite:** {invite}"
            ),
            color=discord.Color.green(),
            fields=[
                {"name": "Owner", "value": f"{guild.owner} ({guild.owner_id})", "inline": True},
                {"name": "Created", "value": guild.created_at.strftime("%Y-%m-%d"), "inline": True},
            ],
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Log when bot leaves a server"""
        await self.log(
            title="📤 LEFT SERVER",
            description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count:,}",
            color=discord.Color.red()
        )
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """Catch-all for uncaught errors in event listeners"""
        error_info = traceback.format_exc()

        if len(error_info) > 1800:
            error_info = error_info[:1800] + "\n... (truncated)"

        await self.log(
            title="⚠️ EVENT ERROR",
            description=f"**Event:** {event}\n**Args:** {len(args)} arguments",
            color=discord.Color.dark_red(),
            fields=[
                {"name": "Error Info", "value": f"```python\n{error_info}\n```", "inline": False}
            ]
        )
    async def cog_load(self):
        """Set up global exception handling when cog loads"""
        self.original_excepthook = sys.excepthook
        sys.excepthook = self.handle_exception

    async def cog_unload(self):
        """Restore original exception hook when cog unloads"""
        sys.excepthook = self.original_excepthook

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_info = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        if len(error_info) > 1800:
            error_info = error_info[:1800] + "\n... (truncated)"

        asyncio.create_task(self.log(
            title="💥 UNCAUGHT EXCEPTION",
            description=f"**Type:** {exc_type.__name__}",
            color=discord.Color.dark_red(),
            fields=[
                {"name": "Traceback", "value": f"```python\n{error_info}\n```", "inline": False}
            ]
        ))

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    @commands.Cog.listener()
    async def on_disconnect(self):
        """Log when bot disconnects"""
        await self.log_bot_event(
            "DISCONNECT",
            "⚠️ **Bot has disconnected from Discord**"
        )

    @commands.Cog.listener()
    async def on_resumed(self):
        """Log when bot resumes connection"""
        await self.log_bot_event(
            "RESUMED",
            "✅ **Bot has resumed connection to Discord**"
        )

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        """Log shard connections (if bot is sharded)"""
        await self.log_bot_event(
            "SHARD CONNECT",
            f"**Shard {shard_id} connected**"
        )

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        """Log shard disconnections (if bot is sharded)"""
        await self.log_bot_event(
            "SHARD DISCONNECT",
            f"⚠️ **Shard {shard_id} disconnected**"
        )

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        """Log when shards become ready"""
        await self.log_bot_event(
            "SHARD READY",
            f"✅ **Shard {shard_id} is ready**"
        )

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        """Log when shards resume"""
        await self.log_bot_event(
            "SHARD RESUMED",
            f"✅ **Shard {shard_id} resumed**"
        )

    @commands.Cog.listener()
    async def on_socket_event_type(self, event_type):
        """Track websocket events for debugging connection issues"""
        critical_events = ['RESUMED', 'READY', 'GUILD_UNAVAILABLE']
        if event_type in critical_events:
            await self.log_bot_event(
                "WEBSOCKET EVENT",
                f"📡 **Event:** {event_type}"
            )

async def setup(bot):
    await bot.add_cog(BotLogger(bot))
