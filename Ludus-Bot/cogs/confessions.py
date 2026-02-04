import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class Confessions(commands.Cog):
    """Anonymous confession system with logging"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/confession_config.json"
        self.load_config()
    
    def load_config(self):
        """Load confession configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def save_config(self):
        """Save confession configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get_server_config(self, guild_id):
        """Get configuration for a specific server"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config:
            self.config[guild_id_str] = {
                "confession_channel": None,
                "log_channel": None,
                "confession_count": 0
            }
            self.save_config()
        return self.config[guild_id_str]
    
    @commands.group(name="confession", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def confession(self, ctx):
        """Manage the confession system"""
        embed = discord.Embed(
            title="🔒 Confession System",
            description="**Commands:**\n"
                       "`L!confession set #channel` - Set confession channel\n"
                       "`L!confession setlog #channel` - Set logging channel\n"
                       "`L!confession status` - View current setup\n"
                       "`L!confession disable` - Disable system",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)
    
    @confession.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """Set the confession channel"""
        config = self.get_server_config(ctx.guild.id)
        config["confession_channel"] = channel.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Confession Channel Set",
            description=f"Confession channel set to {channel.mention}\n\n"
                       f"**How it works:**\n"
                       f"• Users send messages in {channel.mention}\n"
                       f"• Bot deletes their message and posts anonymously\n"
                       f"• Format: `CONFESSION #X: <message>`\n"
                       f"• Admins can see who sent what in the log channel",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @confession.command(name="setlog", aliases=["logchannel"])
    @commands.has_permissions(administrator=True)
    async def set_log(self, ctx, channel: discord.TextChannel):
        """Set the logging channel for confession tracking"""
        config = self.get_server_config(ctx.guild.id)
        config["log_channel"] = channel.id
        self.save_config()
        
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Confession logs will be sent to {channel.mention}\n\n"
                       f"**Logged Information:**\n"
                       f"• Username and ID of confessor\n"
                       f"• Confession number\n"
                       f"• Full message content\n"
                       f"• Timestamp",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @confession.command(name="status")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        """View confession system status"""
        config = self.get_server_config(ctx.guild.id)
        
        conf_channel = self.bot.get_channel(config["confession_channel"])
        log_channel = self.bot.get_channel(config["log_channel"])
        
        embed = discord.Embed(
            title="🔒 Confession System Status",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Confession Channel",
            value=conf_channel.mention if conf_channel else "❌ Not set",
            inline=False
        )
        
        embed.add_field(
            name="Log Channel",
            value=log_channel.mention if log_channel else "❌ Not set",
            inline=False
        )
        
        embed.add_field(
            name="Total Confessions",
            value=f"{config['confession_count']} confessions posted",
            inline=False
        )
        
        if conf_channel and log_channel:
            embed.add_field(
                name="Status",
                value="✅ System Active",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="⚠️ Incomplete Setup",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @confession.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        """Disable the confession system"""
        guild_id_str = str(ctx.guild.id)
        if guild_id_str in self.config:
            del self.config[guild_id_str]
            self.save_config()
        
        embed = discord.Embed(
            title="🔒 Confession System Disabled",
            description="The confession system has been disabled for this server.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle confession submissions"""
        
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check if message is in confession channel
        config = self.get_server_config(message.guild.id)
        
        if not config["confession_channel"]:
            return
        
        if message.channel.id != config["confession_channel"]:
            return
        
        # Don't process commands
        if message.content.startswith(('L!', '/', '!')):
            return
        
        # Don't process empty messages
        if not message.content.strip():
            return
        
        # Get channels
        confession_channel = self.bot.get_channel(config["confession_channel"])
        log_channel = self.bot.get_channel(config["log_channel"])
        
        if not confession_channel:
            return
        
        # Delete original message
        try:
            await message.delete()
        except:
            pass
        
        # Increment confession count
        config["confession_count"] += 1
        confession_num = config["confession_count"]
        self.save_config()
        
        # Post anonymous confession
        confession_embed = discord.Embed(
            title=f"🔒 CONFESSION #{confession_num}",
            description=message.content,
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        confession_embed.set_footer(text="Anonymous Confession")
        
        await confession_channel.send(embed=confession_embed)
        
        # Log to admin channel
        if log_channel:
            log_embed = discord.Embed(
                title=f"📋 Confession Log #{confession_num}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            
            log_embed.add_field(
                name="User",
                value=f"{message.author.mention} ({message.author.name}#{message.author.discriminator})",
                inline=False
            )
            
            log_embed.add_field(
                name="User ID",
                value=f"`{message.author.id}`",
                inline=False
            )
            
            log_embed.add_field(
                name="Confession Content",
                value=message.content[:1024],  # Limit to 1024 chars
                inline=False
            )
            
            log_embed.set_thumbnail(url=message.author.display_avatar.url)
            log_embed.set_footer(text=f"Confession #{confession_num}")
            
            await log_channel.send(embed=log_embed)

async def setup(bot):
    await bot.add_cog(Confessions(bot))
