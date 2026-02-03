import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class ProfileManager:
    """Manages comprehensive user profiles tracking ALL activities"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.profiles_file = os.path.join(data_dir, "profiles.json")
        self.profiles = self.load_profiles()
    
    def load_profiles(self):
        """Load profiles from JSON"""
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_profiles(self):
        """Save profiles to JSON"""
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=4)
        except Exception as e:
            print(f"Error saving profiles: {e}")
    
    def get_profile(self, user_id):
        """Get or create user profile"""
        user_id = str(user_id)
        if user_id not in self.profiles:
            self.profiles[user_id] = self._create_default_profile()
            self.save_profiles()
        # Ensure new fields for cross-cog stats
        profile = self.profiles[user_id]
        if "most_played_games" not in profile:
            profile["most_played_games"] = {}
        if "most_played_with" not in profile:
            profile["most_played_with"] = {}
        if "inventory" not in profile:
            profile["inventory"] = {}
        if "fishing_stats" not in profile:
            profile["fishing_stats"] = {"fish_caught": 0, "rare_fish": 0, "legendary_fish": 0, "biggest_fish": 0}
        if "farming_stats" not in profile:
            profile["farming_stats"] = {"crops_planted": 0, "crops_harvested": 0, "level": 1}
        self.save_profiles()
        return profile
        def record_game_played(self, user_id, game_name, with_users=None):
            """Track most played games and most played with (friends/rivals)"""
            profile = self.get_profile(user_id)
            # Most played games
            mpg = profile.setdefault("most_played_games", {})
            mpg[game_name] = mpg.get(game_name, 0) + 1
            # Most played with
            if with_users:
                mpw = profile.setdefault("most_played_with", {})
                for uid in with_users:
                    mpw[str(uid)] = mpw.get(str(uid), 0) + 1
            self.save_profiles()

        def update_fishing(self, user_id, fish_type, weight=0):
            """Update fishing stats in profile"""
            profile = self.get_profile(user_id)
            stats = profile.setdefault("fishing_stats", {"fish_caught": 0, "rare_fish": 0, "legendary_fish": 0, "biggest_fish": 0})
            if fish_type == "normal":
                stats["fish_caught"] += 1
            elif fish_type == "rare":
                stats["rare_fish"] += 1
            elif fish_type == "legendary":
                stats["legendary_fish"] += 1
            if weight > stats.get("biggest_fish", 0):
                stats["biggest_fish"] = weight
            self.save_profiles()

        def update_farming(self, user_id, planted=0, harvested=0, level=None):
            """Update farming stats in profile"""
            profile = self.get_profile(user_id)
            stats = profile.setdefault("farming_stats", {"crops_planted": 0, "crops_harvested": 0, "level": 1})
            stats["crops_planted"] += planted
            stats["crops_harvested"] += harvested
            if level is not None:
                stats["level"] = max(stats["level"], level)
            self.save_profiles()

        def update_inventory(self, user_id, item, amount):
            """Update inventory in profile"""
            profile = self.get_profile(user_id)
            inv = profile.setdefault("inventory", {})
            inv[item] = inv.get(item, 0) + amount
            if inv[item] <= 0:
                del inv[item]
            self.save_profiles()
    
    def _create_default_profile(self):
        """Create default profile structure"""
        return {
            # Badges
            "badges": [],
            # Core Stats
            "created_at": datetime.utcnow().isoformat(),
        }

    def add_badge(self, user_id, badge_id):
        """Add a badge to a user's profile if not already present"""
        profile = self.get_profile(user_id)
        if "badges" not in profile:
            profile["badges"] = []
        if badge_id not in profile["badges"]:
            profile["badges"].append(badge_id)
            self.save_profiles()
            return True
        return False

    def _create_default_profile(self):
        """Create default profile structure"""
        return {
            "energy": 100,
            "max_energy": 100,
            "level": 1,
            "xp": 0,
            # Economy Stats
            "total_earned": 0,
            "total_spent": 0,
            "biggest_win": 0,
            "biggest_loss": 0,
            # Gambling Stats
            "gambling_count": 0,
            "gambling_wins": 0,
            "gambling_losses": 0,
            "gambling_total_wagered": 0,
            "gambling_total_won": 0,
            "slots_played": 0,
            "blackjack_played": 0,
            "roulette_played": 0,
            
            # Minigame Stats
            "minigames_played": 0,
            "minigames_won": 0,
            "wordle_attempts": 0,
            "wordle_wins": 0,
            "riddles_solved": 0,
            "typerace_average_wpm": 0,
            "trivia_correct": 0,
            "trivia_attempted": 0,
            
            # Board Game Stats
            "tictactoe_played": 0,
            "tictactoe_wins": 0,
            "connect4_played": 0,
            "connect4_wins": 0,
            "hangman_played": 0,
            "hangman_wins": 0,
            
            # Card Game Stats
            "uno_played": 0,
            "uno_wins": 0,
            "blackjack_wins": 0,
            "war_played": 0,
            "gofish_played": 0,
            
            # TCG Stats
            "tcg_battles": 0,
            "tcg_wins": 0,
            "tcg_losses": 0,
            "tcg_ai_battles": 0,
            "tcg_ranked_matches": 0,
            "tcg_tournaments_entered": 0,
            "tcg_tournaments_won": 0,
            "tcg_cards_owned": 0,
            "tcg_cards_crafted": 0,
            
            # Social Stats
            "compliments_given": 0,
            "compliments_received": 0,
            "roasts_given": 0,
            "highfives": 0,
            "stories_contributed": 0,
            
            # Pet Stats
            "pets_owned": 0,
            "pet_total_happiness": 0,
            "pet_fed_count": 0,
            "pet_played_count": 0,
            "pet_walked_count": 0,
            
            # Fishing Stats
            "fish_caught": 0,
            "rare_fish_caught": 0,
            "legendary_fish_caught": 0,
            "biggest_fish_weight": 0,
            "fishing_trips": 0,
            
            # Farming Stats (for future expansion)
            "crops_planted": 0,
            "crops_harvested": 0,
            "farming_level": 1,
            
            # Quest Stats
            "quests_completed": 0,
            "daily_quests_done": 0,
            "achievements_unlocked": 0,
            "daily_streak": 0,
            "longest_streak": 0,
            
            # Event Stats
            "events_participated": 0,
            "events_won": 0,
            "seasonal_points": 0,
            
            # Business Stats
            "business_owned": False,
            "business_sales": 0,
            "business_revenue": 0,
            "items_sold": 0,
            "items_bought": 0,
            
            # Battle Stats
            "pvp_battles": 0,
            "pvp_wins": 0,
            "boss_battles": 0,
            "boss_wins": 0,
            "dungeons_completed": 0,
            
            # Music Stats
            "songs_played": 0,
            "total_listen_time": 0,  # in seconds
            "favorite_genre": None,
            
            # Misc Stats
            "commands_used": 0,
            "messages_sent": 0,
            "servers_active_in": 0,
            "voice_time": 0,  # in seconds
            "reactions_added": 0,
        }
    
    def increment_stat(self, user_id, stat_name, amount=1):
        """Increment a stat for a user"""
        profile = self.get_profile(user_id)
        if stat_name in profile:
            profile[stat_name] += amount
            self.save_profiles()
            return True
        return False
    
    def set_stat(self, user_id, stat_name, value):
        """Set a specific stat value"""
        profile = self.get_profile(user_id)
        if stat_name in profile:
            profile[stat_name] = value
            self.save_profiles()
            return True
        return False
    
    def use_energy(self, user_id, amount):
        """Use energy (returns False if not enough)"""
        profile = self.get_profile(user_id)
        if profile['energy'] >= amount:
            profile['energy'] -= amount
            self.save_profiles()
            return True
        return False
    
    def restore_energy(self, user_id, amount):
        """Restore energy (capped at max_energy)"""
        profile = self.get_profile(user_id)
        profile['energy'] = min(profile['energy'] + amount, profile['max_energy'])
        self.save_profiles()
    
    def get_top_stats(self, user_id):
        """Get user's top 5 activities"""
        profile = self.get_profile(user_id)
        
        activities = {
            "Gambling Sessions": profile['gambling_count'],
            "Minigames Played": profile['minigames_played'],
            "TCG Battles": profile['tcg_battles'],
            "Fish Caught": profile['fish_caught'],
            "Quests Completed": profile['quests_completed'],
            "Events Joined": profile['events_participated'],
            "Commands Used": profile['commands_used'],
            "Social Interactions": profile['compliments_given'] + profile['roasts_given'],
        }
        
        # Sort and get top 5
        top = sorted(activities.items(), key=lambda x: x[1], reverse=True)[:5]
        return top

class ProfileView(View):
    def __init__(self, ctx, profile_data, user):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.profile_data = profile_data
        self.user = user
        self.current_page = "overview"
    
    @discord.ui.button(label="Overview", style=discord.ButtonStyle.primary, emoji="📊")
    async def overview_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This profile isn't for you!", ephemeral=True)
            return
        
        self.current_page = "overview"
        embed = self._create_overview_embed()
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Gaming", style=discord.ButtonStyle.success, emoji="🎮")
    async def gaming_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This profile isn't for you!", ephemeral=True)
            return
        
        self.current_page = "gaming"
        embed = self._create_gaming_embed()
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Economy", style=discord.ButtonStyle.success, emoji="💰")
    async def economy_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This profile isn't for you!", ephemeral=True)
            return
        
        self.current_page = "economy"
        embed = self._create_economy_embed()
        await interaction.response.edit_message(embed=embed)
    
    @discord.ui.button(label="Social", style=discord.ButtonStyle.primary, emoji="👥")
    async def social_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This profile isn't for you!", ephemeral=True)
            return
        
        self.current_page = "social"
        embed = self._create_social_embed()
        await interaction.response.edit_message(embed=embed)
    
    def _create_overview_embed(self):
        """Create overview page"""
        p = self.profile_data
        # Energy bar
        energy_percentage = (p['energy'] / p['max_energy']) * 100
        energy_bar = EmbedBuilder.progress_bar(energy_percentage, 10)
        # Calculate stats
        gambling_winrate = (p['gambling_wins'] / p['gambling_count'] * 100) if p['gambling_count'] > 0 else 0
        minigame_winrate = (p['minigames_won'] / p['minigames_played'] * 100) if p['minigames_played'] > 0 else 0
        # Badges
        badge_display = ""
        if p.get("badges"):
            badge_display = "\n🏅 **Badges:** " + " ".join([f"`{b}`" for b in p["badges"]])
        embed = EmbedBuilder.create(
            title=f"{Emojis.CROWN} {self.user.display_name}'s Profile",
            description=f"**Level {p['level']}** • {p['xp']} XP\n"
                       f"⚡ **Energy:** {energy_bar} {p['energy']}/{p['max_energy']}\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━━"
                       f"{badge_display}",
            color=Colors.PRIMARY
        )
        # Top Activities
        top_stats = []
        activities = [
            ("🎲 Gambling", p['gambling_count']),
            ("🎮 Minigames", p['minigames_played']),
            ("⚔️ TCG Battles", p['tcg_battles']),
            ("🎣 Fish Caught", p['fish_caught']),
            ("📜 Quests Done", p['quests_completed']),
        ]
        
        for name, count in sorted(activities, key=lambda x: x[1], reverse=True)[:5]:
            if count > 0:
                top_stats.append(f"{name}: **{count}**")
        
        embed.add_field(
            name=f"{Emojis.TROPHY} Top Activities",
            value="\n".join(top_stats) if top_stats else "*No activity yet*",
            inline=False
        )
        
        # Quick Stats Grid
        embed.add_field(
            name=f"{Emojis.DICE} Gambling",
            value=f"**{p['gambling_count']}** games\n"
                  f"**{gambling_winrate:.1f}%** winrate",
            inline=True
        )
        
        embed.add_field(
            name=f"🎮 Minigames",
            value=f"**{p['minigames_played']}** played\n"
                  f"**{p['minigames_won']}** won",
            inline=True
        )
        
        embed.add_field(
            name=f"{Emojis.HEART} Social",
            value=f"**{p['compliments_given']}** compliments\n"
                  f"**{p['events_participated']}** events",
            inline=True
        )
        
        embed.set_footer(text="Use buttons to see detailed stats • Energy restores over time")
        embed.set_thumbnail(url=self.user.display_avatar.url)
        
        return embed
    
    def _create_gaming_embed(self):
        """Create gaming stats page"""
        p = self.profile_data
        
        embed = EmbedBuilder.create(
            title=f"🎮 {self.user.display_name}'s Gaming Stats",
            description="Complete overview of all gaming activities!",
            color=Colors.SUCCESS
        )
        
        # Minigames
        embed.add_field(
            name="🎮 Minigames",
            value=f"**Total:** {p['minigames_played']} played, {p['minigames_won']} won\n"
                  f"**Wordle:** {p['wordle_wins']}/{p['wordle_attempts']}\n"
                  f"**Riddles:** {p['riddles_solved']} solved\n"
                  f"**Trivia:** {p['trivia_correct']}/{p['trivia_attempted']}",
            inline=False
        )
        
        # Board Games
        embed.add_field(
            name="🎯 Board Games",
            value=f"**Tic-Tac-Toe:** {p['tictactoe_wins']}/{p['tictactoe_played']}\n"
                  f"**Connect4:** {p['connect4_wins']}/{p['connect4_played']}\n"
                  f"**Hangman:** {p['hangman_wins']}/{p['hangman_played']}",
            inline=True
        )
        
        # Card Games
        embed.add_field(
            name="🃏 Card Games",
            value=f"**UNO:** {p['uno_wins']}/{p['uno_played']}\n"
                  f"**Blackjack:** {p['blackjack_wins']}/{p['blackjack_played']}\n"
                  f"**War:** {p['war_played']} games",
            inline=True
        )
        
        # TCG
        tcg_winrate = (p['tcg_wins'] / p['tcg_battles'] * 100) if p['tcg_battles'] > 0 else 0
        embed.add_field(
            name="⚔️ Psyvrse TCG",
            value=f"**Battles:** {p['tcg_battles']} ({tcg_winrate:.1f}% WR)\n"
                  f"**Ranked:** {p['tcg_ranked_matches']} matches\n"
                  f"**Tournaments:** {p['tcg_tournaments_won']}/{p['tcg_tournaments_entered']}\n"
                  f"**Collection:** {p['tcg_cards_owned']} cards",
            inline=False
        )
        
        # Fishing
        embed.add_field(
            name="🎣 Fishing",
            value=f"**Total:** {p['fish_caught']} fish\n"
                  f"**Rare:** {p['rare_fish_caught']}\n"
                  f"**Legendary:** {p['legendary_fish_caught']}\n"
                  f"**Record:** {p['biggest_fish_weight']}kg",
            inline=True
        )
        
        # Battles
        embed.add_field(
            name="⚔️ Combat",
            value=f"**PvP:** {p['pvp_wins']}/{p['pvp_battles']}\n"
                  f"**Bosses:** {p['boss_wins']}/{p['boss_battles']}\n"
                  f"**Dungeons:** {p['dungeons_completed']}",
            inline=True
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed
    
    def _create_economy_embed(self):
        """Create economy stats page"""
        p = self.profile_data
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.COIN} {self.user.display_name}'s Economy Stats",
            description="Financial overview and business stats!",
            color=Colors.WARNING
        )
        
        # Earnings & Spending
        net_profit = p['total_earned'] - p['total_spent']
        embed.add_field(
            name="💰 Finances",
            value=f"**Earned:** {EmbedBuilder.format_number(p['total_earned'])} coins\n"
                  f"**Spent:** {EmbedBuilder.format_number(p['total_spent'])} coins\n"
                  f"**Net Profit:** {EmbedBuilder.format_number(net_profit)} coins\n"
                  f"**Biggest Win:** {EmbedBuilder.format_number(p['biggest_win'])} coins\n"
                  f"**Biggest Loss:** {EmbedBuilder.format_number(p['biggest_loss'])} coins",
            inline=False
        )
        
        # Gambling
        gambling_roi = ((p['gambling_total_won'] - p['gambling_total_wagered']) / p['gambling_total_wagered'] * 100) if p['gambling_total_wagered'] > 0 else 0
        embed.add_field(
            name="🎰 Gambling",
            value=f"**Games:** {p['gambling_count']}\n"
                  f"**Win Rate:** {(p['gambling_wins']/p['gambling_count']*100):.1f}%" if p['gambling_count'] > 0 else "0%\n"
                  f"**Wagered:** {EmbedBuilder.format_number(p['gambling_total_wagered'])}\n"
                  f"**Won:** {EmbedBuilder.format_number(p['gambling_total_won'])}\n"
                  f"**ROI:** {gambling_roi:+.1f}%",
            inline=True
        )
        
        # Business
        business_status = "✅ Active" if p['business_owned'] else "❌ None"
        embed.add_field(
            name="🏪 Business",
            value=f"**Status:** {business_status}\n"
                  f"**Sales:** {p['business_sales']} items\n"
                  f"**Revenue:** {EmbedBuilder.format_number(p['business_revenue'])}\n"
                  f"**Items Sold:** {p['items_sold']}\n"
                  f"**Items Bought:** {p['items_bought']}",
            inline=True
        )
        
        # Streaks & Quests
        embed.add_field(
            name="📜 Quests & Rewards",
            value=f"**Daily Streak:** {p['daily_streak']} days\n"
                  f"**Longest Streak:** {p['longest_streak']} days\n"
                  f"**Quests Done:** {p['quests_completed']}\n"
                  f"**Achievements:** {p['achievements_unlocked']}",
            inline=False
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed
    
    def _create_social_embed(self):
        """Create social stats page"""
        p = self.profile_data
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.HEART} {self.user.display_name}'s Social Stats",
            description="Community engagement and interactions!",
            color=Colors.PRIMARY
        )
        
        # Social Interactions
        embed.add_field(
            name="💬 Interactions",
            value=f"**Compliments Given:** {p['compliments_given']}\n"
                  f"**Compliments Received:** {p['compliments_received']}\n"
                  f"**Roasts Given:** {p['roasts_given']}\n"
                  f"**High-Fives:** {p['highfives']}\n"
                  f"**Story Contributions:** {p['stories_contributed']}",
            inline=True
        )
        
        # Pet Care
        embed.add_field(
            name="🐾 Pet Care",
            value=f"**Pets Owned:** {p['pets_owned']}\n"
                  f"**Fed:** {p['pet_fed_count']} times\n"
                  f"**Played:** {p['pet_played_count']} times\n"
                  f"**Walked:** {p['pet_walked_count']} times\n"
                  f"**Total Happiness:** {p['pet_total_happiness']}",
            inline=True
        )
        
        # Events
        embed.add_field(
            name="🎉 Events",
            value=f"**Participated:** {p['events_participated']}\n"
                  f"**Won:** {p['events_won']}\n"
                  f"**Seasonal Points:** {p['seasonal_points']}",
            inline=True
        )
        
        # Activity
        embed.add_field(
            name="📊 Activity",
            value=f"**Commands Used:** {p['commands_used']}\n"
                  f"**Messages Sent:** {p['messages_sent']}\n"
                  f"**Active Servers:** {p['servers_active_in']}\n"
                  f"**Reactions Added:** {p['reactions_added']}",
            inline=True
        )
        
        # Music
        listen_hours = p['total_listen_time'] / 3600
        embed.add_field(
            name="🎵 Music",
            value=f"**Songs Played:** {p['songs_played']}\n"
                  f"**Listen Time:** {listen_hours:.1f} hours\n"
                  f"**Favorite Genre:** {p['favorite_genre'] or 'None'}",
            inline=True
        )
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        return embed

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = ProfileManager(data_dir)
    
    @commands.command(name="profile", aliases=["p", "me"])
    async def profile_command(self, ctx, user: discord.User = None):
        """View your comprehensive profile"""
        target = user or ctx.author
        profile = self.manager.get_profile(target.id)
        
        view = ProfileView(ctx, profile, target)
        embed = view._create_overview_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="profile", description="View your comprehensive profile")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Slash command for profile"""
        await interaction.response.defer()
        
        target = user or interaction.user
        profile = self.manager.get_profile(target.id)
        
        # Create fake context for view
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
        
        fake_ctx = FakeContext(interaction)
        view = ProfileView(fake_ctx, profile, target)
        embed = view._create_overview_embed()
        
        await interaction.followup.send(embed=embed, view=view)
    
    @commands.command(name="energy")
    async def energy_command(self, ctx):
        """Check your current energy"""
        profile = self.manager.get_profile(ctx.author.id)
        
        energy_percentage = (profile['energy'] / profile['max_energy']) * 100
        energy_bar = EmbedBuilder.progress_bar(energy_percentage, 15)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} Energy Status",
            description=f"{energy_bar}\n"
                       f"**{profile['energy']}/{profile['max_energy']} Energy**\n\n"
                       f"💡 Energy is used for activities like fishing, farming, and battles!\n"
                       f"🍵 Restore energy at the **Cozy Cafe**: `L!shop cafe`\n"
                       f"⏰ Energy also restores automatically over time!",
            color=Colors.WARNING
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
