import discord
from discord.ext import commands
import traceback
from datetime import datetime
from typing import Optional

class BotLogger(commands.Cog):
    """Comprehensive logging system for all bot activities"""
    
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1442605619835179127  # Your logging channel
        
    async def get_log_channel(self):
        """Get the logging channel"""
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.log_channel_id)
            return channel
        except:
            return None
    
    async def log(self, title: str, description: str, color: discord.Color, fields: list = None):
        """Send a log message to the logging channel"""
        channel = await self.get_log_channel()
        if not channel:
            return
        
        try:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.utcnow()
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
        """Log all command errors"""
        error_msg = str(error)
        full_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Truncate if too long
        if len(full_traceback) > 1800:
            full_traceback = full_traceback[:1800] + "\n... (truncated)"
        
        await self.log(
            title="❌ COMMAND ERROR",
            description=f"**Error Type:** {type(error).__name__}\n**Error:** {error_msg}",
            color=discord.Color.red(),
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
        """Log slash command errors"""
        error_msg = str(error)
        full_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        if len(full_traceback) > 1800:
            full_traceback = full_traceback[:1800] + "\n... (truncated)"
        
        await self.log(
            title="❌ SLASH COMMAND ERROR",
            description=f"**Error Type:** {type(error).__name__}\n**Error:** {error_msg}",
            color=discord.Color.red(),
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
        except:
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
        except:
            pass
    
    async def log_economy(self, transaction_type: str, user_id: int, amount: int, reason: str = ""):
        """Log major economy transactions"""
        if amount < 1000:  # Only log transactions over 1000 coins
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
        except:
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
        """Log when bot joins a server"""
        try:
            invite = "N/A"
            if guild.system_channel:
                inv = await guild.system_channel.create_invite(max_age=0, max_uses=1)
                invite = inv.url
        except:
            pass
        
        await self.log(
            title="📥 JOINED SERVER",
            description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count:,}\n**Invite:** {invite}",
            color=discord.Color.green(),
            fields=[
                {"name": "Owner", "value": f"{guild.owner} ({guild.owner_id})", "inline": True},
                {"name": "Created", "value": guild.created_at.strftime("%Y-%m-%d"), "inline": True}
            ]
        )
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Log when bot leaves a server"""
        await self.log(
            title="📤 LEFT SERVER",
            description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count:,}",
            color=discord.Color.red()
        )

async def setup(bot):
    await bot.add_cog(BotLogger(bot))
