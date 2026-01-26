import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class ServerConfig(commands.Cog):
    """Server configuration and management for administrators"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/server_configs.json"
        self.configs = self._load_configs()
    
    def _load_configs(self):
        """Load server configurations"""
        os.makedirs("data", exist_ok=True)
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_configs(self):
        """Save server configurations"""
        with open(self.config_file, 'w') as f:
            json.dump(self.configs, f, indent=4)
    
    def get_server_config(self, guild_id):
        """Get config for a server (creates default if not exists)"""
        guild_id = str(guild_id)
        if guild_id not in self.configs:
            self.configs[guild_id] = {
                "welcome_dm": True,
                "personality_reactions": True,
                "disabled_commands": [],
                "mod_roles": [],
                "log_channel": None,
                "rate_limit_enabled": True,
                "nsfw_filter": True
            }
            self._save_configs()
        return self.configs[guild_id]
    
    @commands.command(name="serverconfig", aliases=["servercfg", "botconfig"])
    @commands.has_permissions(administrator=True)
    async def server_config(self, ctx):
        """Configure Ludus bot settings for this server (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TOOLS} Server Configuration",
            description=f"**{ctx.guild.name}** - Bot Settings\n\n"
                       "Use the commands below to customize Ludus for your server!",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name=f"{Emojis.INFO} Current Settings",
            value=(
                f"**Welcome DM:** {'✅ Enabled' if config['welcome_dm'] else '❌ Disabled'}\n"
                f"**Personality Reactions:** {'✅ Enabled' if config['personality_reactions'] else '❌ Disabled'}\n"
                f"**Rate Limiting:** {'✅ Enabled' if config['rate_limit_enabled'] else '❌ Disabled'}\n"
                f"**NSFW Filter:** {'✅ Enabled' if config['nsfw_filter'] else '❌ Disabled'}\n"
                f"**Disabled Commands:** {len(config['disabled_commands'])} commands\n"
                f"**Log Channel:** {'<#'+str(config['log_channel'])+'>' if config['log_channel'] else 'None'}"
            ),
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.TOOLS} Configuration Commands",
            value="`L!toggle welcomedm` - Toggle welcome DMs\n"
                  "`L!toggle personality` - Toggle bot reactions\n"
                  "`L!toggle ratelimit` - Toggle spam protection\n"
                  "`L!disablecmd <command>` - Disable a command\n"
                  "`L!enablecmd <command>` - Enable a command\n"
                  "`L!setlogchannel <channel>` - Set log channel\n"
                  "`L!listdisabled` - View disabled commands",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.SHIELD} Professional Features",
            value="• Per-server customization\n"
                  "• Command disabling\n"
                  "• Spam protection\n"
                  "• Audit logging\n"
                  "• Privacy controls",
            inline=False
        )
        
        embed.set_footer(text="All settings are server-specific")
        await ctx.send(embed=embed)
    
    @commands.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def toggle_setting(self, ctx, setting: str):
        """Toggle server settings (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        setting = setting.lower()
        
        setting_map = {
            "welcomedm": "welcome_dm",
            "personality": "personality_reactions",
            "ratelimit": "rate_limit_enabled",
            "nsfw": "nsfw_filter"
        }
        
        if setting not in setting_map:
            await ctx.send(f"❌ Unknown setting! Options: `welcomedm`, `personality`, `ratelimit`, `nsfw`")
            return
        
        key = setting_map[setting]
        config[key] = not config[key]
        self.configs[str(ctx.guild.id)] = config
        self._save_configs()
        
        status = "✅ Enabled" if config[key] else "❌ Disabled"
        await ctx.send(f"{status} **{setting}** for this server!")
    
    @commands.command(name="disablecmd", aliases=["disablecommand"])
    @commands.has_permissions(administrator=True)
    async def disable_command(self, ctx, command: str):
        """Disable a command in this server (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        
        # Prevent disabling config commands
        protected = ["serverconfig", "toggle", "disablecmd", "enablecmd", "listdisabled"]
        if command.lower() in protected:
            await ctx.send(f"❌ Cannot disable configuration commands!")
            return
        
        if command in config["disabled_commands"]:
            await ctx.send(f"❌ Command `{command}` is already disabled!")
            return
        
        config["disabled_commands"].append(command)
        self.configs[str(ctx.guild.id)] = config
        self._save_configs()
        
        await ctx.send(f"✅ Disabled command: `{command}`\nUsers will receive a clean error message when attempting to use it.")
    
    @commands.command(name="enablecmd", aliases=["enablecommand"])
    @commands.has_permissions(administrator=True)
    async def enable_command(self, ctx, command: str):
        """Enable a previously disabled command (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        
        if command not in config["disabled_commands"]:
            await ctx.send(f"❌ Command `{command}` is not disabled!")
            return
        
        config["disabled_commands"].remove(command)
        self.configs[str(ctx.guild.id)] = config
        self._save_configs()
        
        await ctx.send(f"✅ Enabled command: `{command}`")
    
    @commands.command(name="listdisabled")
    @commands.has_permissions(administrator=True)
    async def list_disabled(self, ctx):
        """List all disabled commands in this server (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        
        if not config["disabled_commands"]:
            await ctx.send("✅ No commands are disabled in this server!")
            return
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.INFO} Disabled Commands",
            description=f"**{ctx.guild.name}**\n\n" + "\n".join(f"• `{cmd}`" for cmd in config["disabled_commands"]),
            color=Colors.WARNING
        )
        
        embed.set_footer(text=f"Use L!enablecmd <command> to re-enable")
        await ctx.send(embed=embed)
    
    @commands.command(name="setlogchannel", aliases=["logchannel"])
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for bot action logs (Admin only)"""
        config = self.get_server_config(ctx.guild.id)
        
        if channel is None:
            config["log_channel"] = None
            self.configs[str(ctx.guild.id)] = config
            self._save_configs()
            await ctx.send("✅ Disabled logging for this server.")
            return
        
        config["log_channel"] = channel.id
        self.configs[str(ctx.guild.id)] = config
        self._save_configs()
        
        await ctx.send(f"✅ Set log channel to {channel.mention}")
        
        # Send test log
        embed = EmbedBuilder.create(
            title=f"{Emojis.INFO} Logging Enabled",
            description=f"Bot action logs will be sent to this channel.\n\n"
                       f"**Logged Events:**\n"
                       f"• Economy transactions over 10,000 coins\n"
                       f"• Command errors\n"
                       f"• Rate limit violations\n"
                       f"• Admin actions",
            color=Colors.SUCCESS
        )
        await channel.send(embed=embed)
    
    async def log_action(self, guild_id, title, description, color=Colors.INFO):
        """Log an action to the server's log channel"""
        config = self.get_server_config(guild_id)
        if not config["log_channel"]:
            return
        
        try:
            channel = self.bot.get_channel(config["log_channel"])
            if channel:
                embed = EmbedBuilder.create(
                    title=title,
                    description=description,
                    color=color
                )
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[ServerConfig] Failed to log action: {e}")

async def setup(bot):
    await bot.add_cog(ServerConfig(bot))
