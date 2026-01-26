import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple

class GlobalLeaderboard(commands.Cog):
    """Global server leaderboard tracking ALL bot activities"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "data/global_leaderboard.json"
        self.consent_file = "data/global_consent.json"
        self.data = self.load_data()
        self.consents = self.load_consents()
        
    def load_data(self):
        """Load global leaderboard data"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_data(self):
        """Save global leaderboard data"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def load_consents(self):
        """Load server consents"""
        if os.path.exists(self.consent_file):
            try:
                with open(self.consent_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_consents(self):
        """Save server consents"""
        os.makedirs(os.path.dirname(self.consent_file), exist_ok=True)
        with open(self.consent_file, 'w') as f:
            json.dump(self.consents, f, indent=4)
    
    def get_server_data(self, guild_id: int, server_name: str = None) -> Dict:
        """Get or initialize server data"""
        guild_id_str = str(guild_id)
        
        if guild_id_str not in self.data:
            self.data[guild_id_str] = {
                # Economy & Coins
                "total_coins": 0,
                "coins_earned": 0,
                "coins_spent": 0,
                
                # Fishing
                "fish_caught": 0,
                "rare_fish": 0,
                "legendary_fish": 0,
                "fishing_tournaments": 0,
                
                # Pets
                "pets_adopted": 0,
                "pets_fed": 0,
                "pets_played": 0,
                
                # Music
                "songs_played": 0,
                "radio_listened": 0,
                "music_hours": 0,
                
                # Gambling
                "gambles_won": 0,
                "gambles_played": 0,
                "gambling_profit": 0,
                
                # Minigames
                "minigames_played": 0,
                "minigames_won": 0,
                
                # Card/Board Games
                "card_games": 0,
                "board_games": 0,
                "monopoly_games": 0,
                
                # Leveling
                "total_xp": 0,
                "levels_gained": 0,
                "top_level": 0,
                
                # Social
                "messages_sent": 0,
                "commands_used": 0,
                "members_active": 0,
                
                # Events
                "events_participated": 0,
                "quests_completed": 0,
                
                # Farming
                "crops_harvested": 0,
                "farms_active": 0,
                
                # Business
                "businesses_owned": 0,
                "business_income": 0,
                
                # Server Info
                "server_name": server_name or f"Server {guild_id}",
                "last_updated": datetime.utcnow().isoformat()
            }
            self.save_data()
        
        # Update server name if provided
        if server_name and self.data[guild_id_str].get("server_name") != server_name:
            self.data[guild_id_str]["server_name"] = server_name
            self.save_data()
        
        return self.data[guild_id_str]
    
    def add_activity(self, guild_id: int, activity_type: str, amount: int = 1, server_name: str = None):
        """Add activity to server stats"""
        guild_data = self.get_server_data(guild_id, server_name)
        
        if activity_type in guild_data:
            guild_data[activity_type] += amount
            guild_data["last_updated"] = datetime.utcnow().isoformat()
            self.save_data()
    
    def get_category_rankings(self, consented_only: bool = True) -> Dict[str, List[Tuple[str, str, int]]]:
        """Get rankings for each category"""
        categories = {
            "coins": "total_coins",
            "fishing": "fish_caught",
            "pets": "pets_adopted",
            "music": "songs_played",
            "gambling": "gambles_won",
            "minigames": "minigames_won",
            "leveling": "total_xp",
            "activity": "commands_used"
        }
        
        rankings = {}
        
        for category, stat_key in categories.items():
            sorted_servers = []
            
            for guild_id, guild_data in self.data.items():
                # Check consent if required
                if consented_only and not self.consents.get(guild_id, {}).get("enabled", False):
                    continue
                
                value = guild_data.get(stat_key, 0)
                if value > 0:
                    sorted_servers.append((
                        guild_id,
                        guild_data.get("server_name", f"Server {guild_id}"),
                        value
                    ))
            
            sorted_servers.sort(key=lambda x: x[2], reverse=True)
            rankings[category] = sorted_servers
        
        return rankings
    
    def calculate_overall_rank(self, guild_id: str, rankings: Dict) -> float:
        """Calculate overall ranking based on average position across categories"""
        positions = []
        
        for category, ranked_list in rankings.items():
            # Find position in this category (1-indexed)
            for idx, (gid, name, value) in enumerate(ranked_list, 1):
                if gid == guild_id:
                    positions.append(idx)
                    break
            else:
                # Not in this category - assign last place + 1
                positions.append(len(ranked_list) + 1)
        
        if not positions:
            return 999999  # No rankings
        
        # Average position (lower is better)
        return sum(positions) / len(positions)
    
    @commands.command(name="global")
    async def global_leaderboard(self, ctx, category: str = None):
        """View global server leaderboard - L!global [category]
        
        Categories: coins, fishing, pets, music, gambling, minigames, leveling, activity, overall
        """
        
        guild_id_str = str(ctx.guild.id)
        
        # Check consent
        if guild_id_str not in self.consents:
            # First time - show consent message
            consent_embed = discord.Embed(
                title="⚠️ GLOBAL LEADERBOARD CONSENT",
                description="**This command shows a global server leaderboard.**\n\n"
                           "🔗 **The #1 server will be showcased with:**\n"
                           "• Server name and icon\n"
                           "• **Public invite link**\n"
                           "• Server statistics\n\n"
                           "⚠️ **This allows other users to join your server!**\n\n"
                           "**Do you want to enable this for your server?**\n"
                           "React with ✅ to consent or ❌ to decline.",
                color=discord.Color.orange()
            )
            consent_embed.set_footer(text="This choice can be changed later by server admins")
            
            msg = await ctx.send(embed=consent_embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            def check(reaction, user):
                return (user.id == ctx.author.id and 
                       reaction.message.id == msg.id and 
                       str(reaction.emoji) in ["✅", "❌"])
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                
                if str(reaction.emoji) == "✅":
                    self.consents[guild_id_str] = {
                        "enabled": True,
                        "consented_by": ctx.author.id,
                        "consented_at": datetime.utcnow().isoformat()
                    }
                    self.save_consents()
                    await msg.delete()
                else:
                    self.consents[guild_id_str] = {
                        "enabled": False,
                        "consented_by": ctx.author.id,
                        "consented_at": datetime.utcnow().isoformat()
                    }
                    self.save_consents()
                    await ctx.send("❌ Global leaderboard disabled for this server. You can still view the leaderboard but won't be ranked.")
                    return
            
            except:
                await ctx.send("⏰ Consent timeout. Use `L!global` again to try.")
                return
        
        # Check if consent is enabled
        if not self.consents.get(guild_id_str, {}).get("enabled", False):
            await ctx.send("❌ This server has declined global leaderboard participation. An admin can use `L!globalconsent` to change this.")
            return
        
        # Get rankings for all categories
        rankings = self.get_category_rankings(consented_only=True)
        
        # Calculate overall rankings based on average position
        overall_rankings = []
        for guild_id in self.data.keys():
            if not self.consents.get(guild_id, {}).get("enabled", False):
                continue
            
            avg_rank = self.calculate_overall_rank(guild_id, rankings)
            server_name = self.data[guild_id].get("server_name", f"Server {guild_id}")
            overall_rankings.append((guild_id, server_name, avg_rank))
        
        overall_rankings.sort(key=lambda x: x[2])  # Lower average rank = better
        
        # Show specific category or overall
        if category and category.lower() in rankings:
            await self.show_category_leaderboard(ctx, category.lower(), rankings)
        else:
            await self.show_overall_leaderboard(ctx, overall_rankings, rankings)
    
    async def show_overall_leaderboard(self, ctx, overall_rankings: List, rankings: Dict):
        """Show the overall combined leaderboard"""
        guild_id_str = str(ctx.guild.id)
        
        if not overall_rankings:
            await ctx.send("📊 No servers on the global leaderboard yet! Play games to rank your server!")
            return
        
        # Create main embed
        embed = discord.Embed(
            title="🌍 GLOBAL SERVER LEADERBOARD - OVERALL",
            description="**Top servers ranked by average performance across ALL categories!**\n\n"
                       "📊 Categories: Coins, Fishing, Pets, Music, Gambling, Minigames, Leveling, Activity\n"
                       "Use `L!global <category>` to view specific rankings\n",
            color=discord.Color.gold()
        )
        
        # Top server showcase (only #1 gets invite)
        if overall_rankings:
            top_guild_id, top_name, top_avg_rank = overall_rankings[0]
            
            try:
                guild = self.bot.get_guild(int(top_guild_id))
                
                if guild:
                    # Try to create invite for #1
                    invite_link = "No invite available"
                    try:
                        invite_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                        if invite_channel:
                            invite = await invite_channel.create_invite(
                                max_age=86400,  # 24 hours
                                max_uses=100,
                                unique=False,
                                reason="Global Leaderboard #1 Showcase"
                            )
                            invite_link = invite.url
                    except:
                        pass
                    
                    # Get stats for showcase
                    guild_data = self.data.get(top_guild_id, {})
                    
                    showcase = (
                        f"👑 **#{1} - {guild.name}**\n"
                        f"📊 Average Rank: **{top_avg_rank:.1f}**\n"
                        f"👥 Members: {guild.member_count:,}\n"
                        f"💰 Total Coins: {guild_data.get('total_coins', 0):,}\n"
                        f"🎣 Fish Caught: {guild_data.get('fish_caught', 0):,}\n"
                        f"🎮 Games Played: {guild_data.get('minigames_played', 0):,}\n"
                        f"🔗 **Join: {invite_link}**\n"
                    )
                    
                    embed.add_field(
                        name="🏆 TOP SERVER SHOWCASE",
                        value=showcase,
                        inline=False
                    )
                    
                    if guild.icon:
                        embed.set_thumbnail(url=guild.icon.url)
            except:
                pass
        
        # Top 7 servers
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (guild_id, server_name, avg_rank) in enumerate(overall_rankings[:7], 1):
            medal = medals[idx-1] if idx <= 3 else f"**{idx}.**"
            
            # Show their top categories
            top_cats = self.get_top_categories(guild_id, rankings, limit=2)
            cat_str = f" ({', '.join(top_cats)})" if top_cats else ""
            
            # Highlight current server
            if guild_id == guild_id_str:
                leaderboard_text += f"⭐ {medal} **{server_name}** - Avg: {avg_rank:.1f}{cat_str}\n"
            else:
                leaderboard_text += f"{medal} {server_name} - Avg: {avg_rank:.1f}{cat_str}\n"
        
        embed.add_field(
            name="📋 TOP 7 SERVERS",
            value=leaderboard_text or "No servers yet!",
            inline=False
        )
        
        # Current server detailed stats
        current_rank = next((i+1 for i, (gid, name, ar) in enumerate(overall_rankings) if gid == guild_id_str), "Unranked")
        guild_data = self.data.get(guild_id_str, {})
        
        # Show position in each category
        cat_positions = []
        for cat_name, ranked_list in rankings.items():
            pos = next((i+1 for i, (gid, name, val) in enumerate(ranked_list) if gid == guild_id_str), None)
            if pos and pos <= 10:  # Only show top 10 positions
                cat_positions.append(f"#{pos} {cat_name.title()}")
        
        current_stats = (
            f"**Overall Rank:** #{current_rank}\n"
            f"**Top Categories:** {', '.join(cat_positions[:3]) if cat_positions else 'None'}\n\n"
            f"💰 Coins: {guild_data.get('total_coins', 0):,}\n"
            f"🎣 Fish: {guild_data.get('fish_caught', 0):,}\n"
            f"🐾 Pets: {guild_data.get('pets_adopted', 0):,}\n"
            f"🎵 Music: {guild_data.get('songs_played', 0):,}"
        )
        
        embed.add_field(
            name=f"📊 {ctx.guild.name}",
            value=current_stats,
            inline=False
        )
        
        embed.set_footer(text="Categories: coins, fishing, pets, music, gambling, minigames, leveling, activity")
        
        await ctx.send(embed=embed)
    
    async def show_category_leaderboard(self, ctx, category: str, rankings: Dict):
        """Show leaderboard for a specific category"""
        guild_id_str = str(ctx.guild.id)
        ranked_list = rankings.get(category, [])
        
        if not ranked_list:
            await ctx.send(f"📊 No servers ranked in **{category.title()}** yet!")
            return
        
        # Category info
        category_info = {
            "coins": ("💰", "Total PsyCoins", "coins"),
            "fishing": ("🎣", "Fish Caught", "fish"),
            "pets": ("🐾", "Pets Adopted", "pets"),
            "music": ("🎵", "Songs Played", "songs"),
            "gambling": ("🎲", "Gambles Won", "wins"),
            "minigames": ("🎮", "Minigames Won", "wins"),
            "leveling": ("⭐", "Total XP", "XP"),
            "activity": ("📊", "Commands Used", "commands")
        }
        
        icon, title, unit = category_info.get(category, ("📊", category.title(), "points"))
        
        embed = discord.Embed(
            title=f"🌍 GLOBAL LEADERBOARD - {icon} {title.upper()}",
            description=f"**Top servers ranked by {title.lower()}**\n\n"
                       f"Use `L!global` for overall rankings or `L!global <category>` for others\n",
            color=discord.Color.blue()
        )
        
        # Top server showcase with invite (only #1)
        if ranked_list:
            top_guild_id, top_name, top_value = ranked_list[0]
            
            try:
                guild = self.bot.get_guild(int(top_guild_id))
                
                if guild:
                    invite_link = "No invite available"
                    try:
                        invite_channel = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                        if invite_channel:
                            invite = await invite_channel.create_invite(
                                max_age=86400,
                                max_uses=100,
                                unique=False,
                                reason=f"Global Leaderboard #{category.title()} Champion"
                            )
                            invite_link = invite.url
                    except:
                        pass
                    
                    showcase = (
                        f"👑 **#{1} - {guild.name}**\n"
                        f"{icon} **{title}:** {top_value:,} {unit}\n"
                        f"👥 Members: {guild.member_count:,}\n"
                        f"🔗 **Join: {invite_link}**\n"
                    )
                    
                    embed.add_field(
                        name=f"🏆 {title.upper()} CHAMPION",
                        value=showcase,
                        inline=False
                    )
                    
                    if guild.icon:
                        embed.set_thumbnail(url=guild.icon.url)
            except:
                pass
        
        # Top 10 leaderboard
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, (guild_id, server_name, value) in enumerate(ranked_list[:10], 1):
            medal = medals[idx-1] if idx <= 3 else f"**{idx}.**"
            
            # Highlight current server
            if guild_id == guild_id_str:
                leaderboard_text += f"⭐ {medal} **{server_name}** - {value:,} {unit}\n"
            else:
                leaderboard_text += f"{medal} {server_name} - {value:,} {unit}\n"
        
        embed.add_field(
            name=f"📋 TOP 10 - {title.upper()}",
            value=leaderboard_text,
            inline=False
        )
        
        # Current server stats in this category
        current_pos = next((i+1 for i, (gid, name, val) in enumerate(ranked_list) if gid == guild_id_str), None)
        if current_pos:
            current_value = next((val for gid, name, val in ranked_list if gid == guild_id_str), 0)
            embed.add_field(
                name=f"📊 {ctx.guild.name}",
                value=f"**Rank:** #{current_pos}\n**{title}:** {current_value:,} {unit}",
                inline=False
            )
        
        embed.set_footer(text="Play more to climb the rankings! • Rankings update in real-time")
        
        await ctx.send(embed=embed)
    
    def get_top_categories(self, guild_id: str, rankings: Dict, limit: int = 3) -> List[str]:
        """Get the top categories for a server"""
        positions = []
        
        for category, ranked_list in rankings.items():
            pos = next((i+1 for i, (gid, name, val) in enumerate(ranked_list) if gid == guild_id), None)
            if pos:
                positions.append((category, pos))
        
        positions.sort(key=lambda x: x[1])
        return [f"#{pos} {cat.title()}" for cat, pos in positions[:limit]]
    
    @commands.command(name="globalconsent")
    @commands.has_permissions(administrator=True)
    async def global_consent(self, ctx, enabled: str):
        """Toggle global leaderboard participation (Admin only)"""
        
        if enabled.lower() not in ["on", "off", "enable", "disable", "yes", "no"]:
            await ctx.send("❌ Usage: `L!globalconsent <on/off>`")
            return
        
        guild_id_str = str(ctx.guild.id)
        enable_value = enabled.lower() in ["on", "enable", "yes"]
        
        self.consents[guild_id_str] = {
            "enabled": enable_value,
            "consented_by": ctx.author.id,
            "consented_at": datetime.utcnow().isoformat()
        }
        self.save_consents()
        
        if enable_value:
            await ctx.send("✅ Global leaderboard **enabled**! Your server will be ranked and can be showcased.")
        else:
            await ctx.send("❌ Global leaderboard **disabled**. Your server won't be ranked or showcased.")

async def setup(bot):
    await bot.add_cog(GlobalLeaderboard(bot))
