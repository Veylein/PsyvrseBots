import discord
from discord.ext import commands
from datetime import datetime

class ServerInfo(commands.Cog):
    """Server information and statistics"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="serverinfo", aliases=["server", "si"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def server_info(self, ctx):
        """📊 Display comprehensive server statistics (Admin only)"""
        
        guild = ctx.guild
        
        # Calculate statistics
        total_members = guild.member_count
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = total_members - bot_count
        
        online_count = sum(1 for member in guild.members if member.status != discord.Status.offline)
        
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        total_channels = text_channels + voice_channels
        
        role_count = len(guild.roles)
        emoji_count = len(guild.emojis)
        
        # Boost information
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {guild.name} - Server Information",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        
        # Set server icon
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Server basics
        embed.add_field(
            name="🆔 Server ID",
            value=f"`{guild.id}`",
            inline=True
        )
        
        embed.add_field(
            name="👑 Owner",
            value=guild.owner.mention if guild.owner else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(guild.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Vanity URL
        if guild.vanity_url:
            embed.add_field(
                name="🔗 Vanity URL",
                value=f"discord.gg/{guild.vanity_url_code}",
                inline=False
            )
        
        # Member statistics
        member_info = (
            f"👥 **Total:** {total_members:,}\n"
            f"👤 **Humans:** {human_count:,}\n"
            f"🤖 **Bots:** {bot_count:,}\n"
            f"🟢 **Online:** {online_count:,}"
        )
        embed.add_field(
            name="📊 Members",
            value=member_info,
            inline=True
        )
        
        # Channel statistics
        channel_info = (
            f"💬 **Text:** {text_channels}\n"
            f"🔊 **Voice:** {voice_channels}\n"
            f"📁 **Categories:** {categories}\n"
            f"📢 **Total:** {total_channels}"
        )
        embed.add_field(
            name="📺 Channels",
            value=channel_info,
            inline=True
        )
        
        # Other statistics
        other_info = (
            f"🎭 **Roles:** {role_count}\n"
            f"😀 **Emojis:** {emoji_count}/{guild.emoji_limit}\n"
            f"📁 **File Limit:** {guild.filesize_limit // 1048576} MB"
        )
        embed.add_field(
            name="🎨 Other",
            value=other_info,
            inline=True
        )
        
        # Boost information
        boost_emoji = {
            0: "📊",
            1: "🥉",
            2: "🥈",
            3: "🥇"
        }
        
        boost_info = (
            f"{boost_emoji.get(boost_level, '📊')} **Level:** {boost_level}\n"
            f"🚀 **Boosts:** {boost_count}\n"
            f"✨ **Boosters:** {len(guild.premium_subscribers)}"
        )
        embed.add_field(
            name="💎 Server Boosts",
            value=boost_info,
            inline=True
        )
        
        # Verification level
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium",
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        security_info = (
            f"🔒 **Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n"
            f"🛡️ **2FA:** {'Enabled' if guild.mfa_level else 'Disabled'}\n"
            f"🔞 **NSFW Level:** {guild.nsfw_level.name.title()}"
        )
        embed.add_field(
            name="🛡️ Security",
            value=security_info,
            inline=True
        )
        
        # Features
        if guild.features:
            features = []
            feature_emojis = {
                "VERIFIED": "✅",
                "PARTNERED": "🤝",
                "COMMUNITY": "🏘️",
                "DISCOVERABLE": "🔍",
                "WELCOME_SCREEN_ENABLED": "👋",
                "VANITY_URL": "🔗",
                "ANIMATED_ICON": "🎬",
                "BANNER": "🎨",
                "INVITE_SPLASH": "💧",
                "MEMBER_VERIFICATION_GATE_ENABLED": "🚪"
            }
            
            for feature in guild.features[:10]:  # Limit to 10
                emoji = feature_emojis.get(feature, "•")
                features.append(f"{emoji} {feature.replace('_', ' ').title()}")
            
            if len(guild.features) > 10:
                features.append(f"... and {len(guild.features) - 10} more")
            
            embed.add_field(
                name="⭐ Features",
                value="\n".join(features) if features else "None",
                inline=False
            )
        
        # Server banner
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
