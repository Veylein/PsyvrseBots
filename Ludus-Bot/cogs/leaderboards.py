import discord
from discord.ext import commands
from discord import app_commands
from leaderboard_manager import leaderboard_manager

class Leaderboards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.category_info = {
            "counting": {
                "stat": "counting_peak",
                "title": "🔢 Counting Leaderboard",
                "description": "Top servers by highest count reached",
                "value_format": "{:,}"
            },
            "music": {
                "stat": "music_plays",
                "title": "🎵 Music Leaderboard",
                "description": "Top servers by total songs played",
                "value_format": "{:,} songs"
            },
            "pet": {
                "stat": "pet_adoptions",
                "title": "🐾 Pet Leaderboard",
                "description": "Top servers by total pets adopted",
                "value_format": "{:,} pets"
            },
            "gtn": {
                "stat": "gtn_wins",
                "title": "🎲 GTN Leaderboard",
                "description": "Top servers by Guess the Number wins",
                "value_format": "{:,} wins"
            },
            "tod": {
                "stat": "tod_uses",
                "title": "😈 Truth or Dare Leaderboard",
                "description": "Top servers by Truth or Dare uses",
                "value_format": "{:,} uses"
            }
        }

    def check_permissions(self, user, guild):
        # Check if user is in bot owner list from config
        if user.id in getattr(self.bot, "owner_ids", []):
            return True
        # Check admin permissions as before
        member = guild.get_member(user.id)
        if member and member.guild_permissions.administrator:
            return True
        return False

    @commands.command(name="globalleaderboard", aliases=["glb"])
    async def globalleaderboard(self, ctx, category: str = None):
        if not self.check_permissions(ctx.author, ctx.guild):
            await ctx.send("❌ You need administrator permissions or be the bot owner to view leaderboards!")
            return
        await self._show_leaderboard(ctx.guild, category, ctx)

    # Custom check for slash commands that also allows owners
    def owner_or_admin(interaction: discord.Interaction) -> bool:
        if interaction.user.id in getattr(interaction.client, "owner_ids", []):
            return True
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="globalleaderboard", description="View cross-server leaderboards")
    @app_commands.check(owner_or_admin)
    @app_commands.describe(category="Category: counting, music, pet, gtn, or tod")
    @app_commands.choices(category=[
        app_commands.Choice(name="Counting", value="counting"),
        app_commands.Choice(name="Music", value="music"),
        app_commands.Choice(name="Pet", value="pet"),
        app_commands.Choice(name="Guess the Number", value="gtn"),
        app_commands.Choice(name="Truth or Dare", value="tod")
    ])
    async def leaderboard_slash(self, interaction: discord.Interaction, category: app_commands.Choice[str] = None):
        await interaction.response.defer()
        cat_value = category.value if category else None
        await self._show_leaderboard(interaction.guild, cat_value, interaction)

    async def _show_leaderboard(self, guild, category, ctx_or_interaction):
        if not category:
            embed = discord.Embed(
                title="📊 Leaderboard Categories",
                description="Choose a category to view the top 10 servers!",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="Available Categories",
                value="`counting` - Highest counts reached\n"
                      "`music` - Most songs played\n"
                      "`pet` - Most pets adopted\n"
                      "`gtn` - Most GTN wins\n"
                      "`tod` - Most Truth or Dare uses",
                inline=False
            )
            
            embed.add_field(
                name="Usage",
                value="`/leaderboard <category>`\n"
                      "Example: `/leaderboard counting`",
                inline=False
            )
            
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        category = category.lower()
        
        if category not in self.category_info:
            msg = f"❌ Invalid category! Choose from: `counting`, `music`, `pet`, `gtn`, `tod`"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return
        
        cat_info = self.category_info[category]
        top_servers = leaderboard_manager.get_top_servers(cat_info["stat"], limit=10)
        
        if not top_servers:
            embed = discord.Embed(
                title=cat_info["title"],
                description="No data yet! Start using this feature to appear on the leaderboard!",
                color=discord.Color.gold()
            )
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=cat_info["title"],
            description=cat_info["description"],
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (guild_id, server_name, stat_value) in enumerate(top_servers, 1):
            medal = medals[idx - 1] if idx <= 3 else f"`#{idx}`"
            value_str = cat_info["value_format"].format(stat_value)
            
            current_server = " ⭐" if str(guild_id) == str(guild.id) else ""
            leaderboard_text += f"{medal} **{server_name}** - {value_str}{current_server}\n"
        
        embed.add_field(
            name="Top 10 Servers",
            value=leaderboard_text,
            inline=False
        )
        
        current_guild_stats = leaderboard_manager.get_server_stats(guild.id)
        current_value = current_guild_stats.get(cat_info["stat"], 0)
        
        embed.set_footer(
            text=f"Your server: {cat_info['value_format'].format(current_value)}"
        )
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboards(bot))
