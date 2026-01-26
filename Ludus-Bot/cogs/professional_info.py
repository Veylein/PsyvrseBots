import discord
from discord.ext import commands
from discord import app_commands
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class ProfessionalInfo(commands.Cog):
    """Information about Ludus's professional features for server admins"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="professional", aliases=["pro", "enterprise", "profeatures"])
    async def professional_info(self, ctx):
        """Learn about Ludus's professional server features"""
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.CROWN} Ludus Professional Features",
            description="**Built for Official Discord Servers**\n\n"
                       "Ludus is designed to be the perfect bot for professional, "
                       "official, and community Discord servers. Every feature is "
                       "configurable to match your server's needs.",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name=f"{Emojis.TOOLS} Server Configuration",
            value="**Full Control Over Bot Behavior**\n"
                  "• Per-server settings\n"
                  "• Disable specific commands\n"
                  "• Toggle personality reactions\n"
                  "• Control welcome messages\n"
                  "• Spam protection settings\n\n"
                  "`L!serverconfig` - View all settings",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.SHIELD} Privacy & Safety",
            value="**Your Server, Your Rules**\n"
                  "• Welcome DMs are opt-in per server\n"
                  "• Rate limiting prevents spam\n"
                  "• Clean, professional messages\n"
                  "• No intrusive notifications\n"
                  "• GDPR-friendly data handling",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.INFO} Audit Logging",
            value="**Track Bot Actions (Optional)**\n"
                  "• Set a log channel for transparency\n"
                  "• Monitor economy transactions\n"
                  "• Track command errors\n"
                  "• Admin action logging\n\n"
                  "`L!setlogchannel #channel` - Enable logs",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.STAR} Professional Design",
            value="**Clean & Consistent**\n"
                  "• Beautiful embed formatting\n"
                  "• Helpful error messages\n"
                  "• No spam or clutter\n"
                  "• Mobile-friendly interface\n"
                  "• Consistent branding",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.ROCKET} Quick Setup",
            value="**Get Started in 30 Seconds**\n"
                  "1. `L!serverconfig` - Review settings\n"
                  "2. `L!toggle <setting>` - Customize\n"
                  "3. `L!disablecmd <cmd>` - Remove unwanted commands\n"
                  "4. `L!setlogchannel` - Optional logging\n\n"
                  "That's it! Ludus is ready for your server.",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.HEART} Support & Reliability",
            value="**Built to Last**\n"
                  "• 99.9% uptime on Render\n"
                  "• Active development\n"
                  "• Regular updates\n"
                  "• Community-driven features\n"
                  "• Responsive to feedback",
            inline=False
        )
        
        embed.set_footer(text="Ludus - Professional Discord Gaming Bot | L!help for commands")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="privacy")
    async def privacy_info(self, ctx):
        """Privacy policy and data handling information"""
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.SHIELD} Privacy & Data Policy",
            description="**Transparent Data Handling**\n\n"
                       "Ludus is committed to user privacy and data protection.",
            color=Colors.INFO
        )
        
        embed.add_field(
            name="📊 What We Store",
            value="• User IDs (for game progress)\n"
                  "• Server IDs (for configuration)\n"
                  "• Economy data (coins, items)\n"
                  "• Game statistics\n"
                  "• Guild memberships\n\n"
                  "**We DO NOT store:**\n"
                  "• Message content (except commands)\n"
                  "• Personal information\n"
                  "• IP addresses\n"
                  "• Email or real names",
            inline=False
        )
        
        embed.add_field(
            name="🔒 Data Security",
            value="• All data stored in encrypted JSON files\n"
                  "• No third-party data sharing\n"
                  "• Regular backups on Render\n"
                  "• Secure server infrastructure",
            inline=False
        )
        
        embed.add_field(
            name="🗑️ Data Deletion",
            value="• Server admins can disable features anytime\n"
                  "• Users can request data deletion\n"
                  "• Data auto-deletes after 1 year of inactivity\n"
                  "• Contact: `L!support` for deletion requests",
            inline=False
        )
        
        embed.add_field(
            name="⚖️ GDPR Compliance",
            value="Ludus complies with GDPR regulations:\n"
                  "• Right to access your data\n"
                  "• Right to deletion\n"
                  "• Right to portability\n"
                  "• Transparent data usage",
            inline=False
        )
        
        embed.set_footer(text="Last updated: November 2025")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ProfessionalInfo(bot))
