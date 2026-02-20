import discord
from discord.ext import commands
from discord import app_commands
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
        self.fishing_data_file = os.path.join(data_dir, "fishing_data.json")
        self.gambling_stats_file = os.path.join(data_dir, "gambling_stats.json")
        # Paths to external stats files
        self.fishing_data_file = os.path.join(data_dir, "fishing_data.json")
        self.gambling_stats_file = os.path.join(data_dir, "gambling_stats.json")
        self.farming_profile_file = os.path.join(data_dir, "profiles.json")  # farming uses same file
    
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

    def _load_fishing_data(self):
        if os.path.exists(self.fishing_data_file):
            try:
                with open(self.fishing_data_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _load_gambling_stats(self):
        if os.path.exists(self.gambling_stats_file):
            try:
                with open(self.gambling_stats_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_user_stats(self, user_id):
        """Return a profile merged with external stats (fishing, gambling, farming files)."""
        user_id = str(user_id)
        profile = self.get_profile(user_id).copy()

        # Merge fishing data
        fishing_data = self._load_fishing_data()
        if user_id in fishing_data:
            user_fishing = fishing_data[user_id]
            profile['fish_caught'] = user_fishing.get('total_catches', 0)
            profile['fishing_trips'] = user_fishing.get('total_catches', 0)
            rare_count = 0
            legendary_count = 0
            biggest_weight = 0
            for fish_id, fish_info in user_fishing.get('fish_caught', {}).items():
                count = fish_info.get('count', 0) if isinstance(fish_info, dict) else 0
                if fish_id == 'kraken':
                    legendary_count += count
                elif count > 0:
                    rare_count += count
                if isinstance(fish_info, dict):
                    biggest = fish_info.get('biggest', 0)
                    if biggest > biggest_weight:
                        biggest_weight = biggest
            profile['rare_fish_caught'] = rare_count
            profile['legendary_fish_caught'] = legendary_count
            profile['biggest_fish_weight'] = biggest_weight

        # Merge gambling data
        gambling_data = self._load_gambling_stats()
        if user_id in gambling_data:
            user_gambling = gambling_data[user_id]
            profile['gambling_count'] = user_gambling.get('total_games', 0)
            profile['gambling_wins'] = sum(g.get('won', 0) for g in user_gambling.get('games', {}).values())
            profile['gambling_losses'] = sum(g.get('lost', 0) for g in user_gambling.get('games', {}).values())
            profile['gambling_total_wagered'] = user_gambling.get('total_wagered', 0)
            profile['gambling_total_won'] = user_gambling.get('total_won', 0)
            profile['total_earned'] = user_gambling.get('total_won', 0)
            profile['total_spent'] = user_gambling.get('total_wagered', 0)
            biggest_win = 0
            biggest_loss = 0
            for game_data in user_gambling.get('games', {}).values():
                if isinstance(game_data, dict):
                    won = game_data.get('won', 0)
                    lost = game_data.get('lost', 0)
                    if won > biggest_win:
                        biggest_win = won
                    if lost > biggest_loss:
                        biggest_loss = lost
            profile['biggest_win'] = biggest_win
            profile['biggest_loss'] = biggest_loss

        # Farming stats already stored inside profile under 'farming_stats'
        farming_stats = profile.get('farming_stats', {})
        profile['crops_planted'] = farming_stats.get('crops_planted', 0)
        profile['crops_harvested'] = farming_stats.get('crops_harvested', 0)

        return profile
    
    def get_profile(self, user_id):
        """Get or create user profile"""
        user_id = str(user_id)
        if user_id not in self.profiles:
            self.profiles[user_id] = self._create_default_profile()
            self.save_profiles()
        # Ensure new fields for cross-cog stats
        profile = self.profiles[user_id]
        # Merge any missing keys from default profile to avoid KeyErrors in views
        default = self._create_default_profile()
        for k, v in default.items():
            if k not in profile:
                profile[k] = v
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
        mpg = profile.setdefault("most_played_games", {})
        mpg[game_name] = mpg.get(game_name, 0) + 1
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

    def get_user_stats(self, user_id):
        """Get comprehensive user stats from all data files"""
        user_id = str(user_id)
        profile = self.get_profile(user_id).copy()

        # Load and merge fishing stats from fishing_data.json
        fishing_data = self._load_fishing_data()
        if user_id in fishing_data:
            user_fishing = fishing_data[user_id]
            profile["fish_caught"] = user_fishing.get("total_catches", 0)
            profile["fishing_trips"] = user_fishing.get("total_catches", 0)
            # Calculate rare/legendary from fish_caught dict
            rare_count = 0
            legendary_count = 0
            biggest_weight = 0
            for fish_id, fish_info in user_fishing.get("fish_caught", {}).items():
                count = fish_info.get("count", 0) if isinstance(fish_info, dict) else 0
                if fish_id == "kraken":
                    legendary_count += count
                elif count > 0:
                    # Check rarity from fishing_cog if available
                    rare_count += count
                if isinstance(fish_info, dict):
                    biggest = fish_info.get("biggest", 0)
                    if biggest > biggest_weight:
                        biggest_weight = biggest
            profile["rare_fish_caught"] = rare_count
            profile["legendary_fish_caught"] = legendary_count
            profile["biggest_fish_weight"] = biggest_weight

        # Load and merge gambling stats from gambling_stats.json
        gambling_data = self._load_gambling_stats()
        if user_id in gambling_data:
            user_gambling = gambling_data[user_id]
            profile["gambling_count"] = user_gambling.get("total_games", 0)
            profile["gambling_wins"] = sum(g.get("won", 0) for g in user_gambling.get("games", {}).values())
            profile["gambling_losses"] = sum(g.get("lost", 0) for g in user_gambling.get("games", {}).values())
            profile["gambling_total_wagered"] = user_gambling.get("total_wagered", 0)
            profile["gambling_total_won"] = user_gambling.get("total_won", 0)
            # Calculate total_earned and total_spent from gambling
            profile["total_earned"] = user_gambling.get("total_won", 0)
            profile["total_spent"] = user_gambling.get("total_wagered", 0)
            profile["biggest_win"] = user_gambling.get("biggest_win", 0)
            profile["biggest_loss"] = user_gambling.get("biggest_loss", 0)

        # Load and merge farming stats from profiles.json (farming uses same file)
        farming_stats = profile.get("farming_stats", {})
        profile["crops_planted"] = farming_stats.get("crops_planted", 0)
        profile["crops_harvested"] = farming_stats.get("crops_harvested", 0)
        profile["farming_level"] = farming_stats.get("level", 1)

        return profile

    def _load_fishing_data(self):
        """Load fishing data from fishing_data.json"""
        if os.path.exists(self.fishing_data_file):
            try:
                with open(self.fishing_data_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _load_gambling_stats(self):
        """Load gambling stats from gambling_stats.json"""
        if os.path.exists(self.gambling_stats_file):
            try:
                with open(self.gambling_stats_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

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
        else:
            # Create missing stat keys on demand
            profile[stat_name] = amount
        self.save_profiles()
        return True
    
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

class ProfileView(discord.ui.LayoutView):
    def __init__(self, bot, profile_data, user, viewer_id):
        super().__init__(timeout=60)
        self.bot = bot
        # Use profile_data if it's a dict (already loaded stats) or use profile_manager.get_profile()
        if isinstance(profile_data, dict):
            self.profile_data = profile_data
        else:
            # profile_data is likely user_id, load from manager
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "manager"):
                # Use manager.get_user_stats to include merged fishing/gambling data
                if hasattr(profile_cog.manager, 'get_user_stats'):
                    self.profile_data = profile_cog.manager.get_user_stats(profile_data)
                else:
                    self.profile_data = profile_cog.manager.get_profile(profile_data)
            else:
                self.profile_data = {"energy": 100, "max_energy": 100, "level": 1, "xp": 0}
        self.user = user
        self.viewer_id = viewer_id
        self.current_page = "overview"
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI with Components v2"""
        container_items = []
        
        # Add the current page content as TextDisplay
        page_content = self._get_page_content()
        container_items.append(discord.ui.TextDisplay(content=page_content))
        container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        # Get economy cog for deck info (show deck selector first)
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            owned_decks = economy_cog.get_owned_decks(self.user.id)
            current_deck = economy_cog.get_user_card_deck(self.user.id)

            # Only show deck dropdown if user owns decks
            if owned_decks:
                deck_options = []
                for deck_name in owned_decks:
                    deck_info = economy_cog.card_decks.get(deck_name, {"name": deck_name.title(), "rarity": "Common"})
                    equipped = " ✅" if deck_name == current_deck else ""
                    deck_options.append(
                        discord.SelectOption(
                            label=f"{deck_info['name']}{equipped}",
                            value=deck_name,
                            description=f"{deck_info.get('rarity', 'Common')} • {'Equipped' if deck_name == current_deck else 'Unequipped'}",
                            emoji="🃏"
                        )
                    )

                deck_select = discord.ui.Select(
                    placeholder="🎴 Card Decks",
                    options=deck_options
                )
                deck_select.callback = self.deck_callback
                container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
                container_items.append(discord.ui.ActionRow(deck_select))

        # Page selector dropdown (after deck selector)
        page_select = discord.ui.Select(
            placeholder="📊 Select Page",
            options=[
                discord.SelectOption(label="Overview", value="overview", emoji="📊", description="Profile overview and quick stats"),
                discord.SelectOption(label="Gaming", value="gaming", emoji="🎮", description="Gaming stats and achievements"),
                discord.SelectOption(label="Economy", value="economy", emoji="💰", description="Financial stats and business"),
                discord.SelectOption(label="Social", value="social", emoji="👥", description="Social interactions and activity"),
            ]
        )
        page_select.callback = self.page_callback
        container_items.append(discord.ui.ActionRow(page_select))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the viewer to interact"""
        if interaction.user.id != self.viewer_id:
            await interaction.response.send_message("**❌ This profile isn't for you!**", ephemeral=True)
            return False
        return True
    
    async def page_callback(self, interaction: discord.Interaction):
        """Handle page selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        self.current_page = selected[0]
        
        # Rebuild UI with new page content
        self.clear_items()
        self._build_ui()
        
        await interaction.response.edit_message(view=self)
    
    async def deck_callback(self, interaction: discord.Interaction):
        """Handle deck equipment"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        deck_name = selected[0]
        
        # Equip the deck
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.set_user_card_deck(self.user.id, deck_name)
            deck_info = economy_cog.card_decks.get(deck_name, {"name": deck_name.title(), "rarity": "Unknown"})
            
            # Rebuild UI to reflect new equipped deck
            self.clear_items()
            self._build_ui()
            
            # Update message with confirmation
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
    
    def _get_page_content(self):
        """Get markdown content for current page"""
        if self.current_page == "overview":
            return self._create_overview_content()
        elif self.current_page == "gaming":
            return self._create_gaming_content()
        elif self.current_page == "economy":
            return self._create_economy_content()
        elif self.current_page == "social":
            return self._create_social_content()
        else:
            return self._create_overview_content()
    
    def _create_overview_content(self):
        """Create overview page as markdown text"""
        p = self.profile_data
        energy_percentage = (p['energy'] / p['max_energy']) * 100
        energy_blocks = int(energy_percentage / 10)
        energy_bar = "█" * energy_blocks + "░" * (10 - energy_blocks)
        gambling_winrate = (p['gambling_wins'] / p['gambling_count'] * 100) if p['gambling_count'] > 0 else 0
        
        # Top Activities
        activities = [
            ("🎲 Gambling", p['gambling_count']),
            ("🎮 Minigames", p['minigames_played']),
            ("⚔️ TCG Battles", p['tcg_battles']),
            ("🎣 Fish Caught", p['fish_caught']),
            ("📜 Quests Done", p['quests_completed']),
        ]
        top_stats = [f"{name}: **{count}**" for name, count in sorted(activities, key=lambda x: x[1], reverse=True)[:5] if count > 0]
        
        badges = ""
        if p.get("badges"):
            badges = "\n🏅 **Badges:** " + " ".join([f"`{b}`" for b in p["badges"]]) + "\n"
        
        top_activities_text = "\n".join(top_stats) if top_stats else '*No activity yet*'
        
        return f"""# 👑 {self.user.display_name}'s Profile

**Level {p['level']}** • {p['xp']} XP
⚡ **Energy:** {energy_bar} {p['energy']}/{p['max_energy']}{badges}

## 🏆 Top Activities
{top_activities_text}

**🎲 Gambling:** {p['gambling_count']} games • {gambling_winrate:.1f}% winrate
**🎮 Minigames:** {p['minigames_played']} played • {p['minigames_won']} won
**💬 Social:** {p['compliments_given']} compliments • {p['events_participated']} events

*Use dropdown to see detailed stats*"""
    
    def _create_gaming_content(self):
        """Create gaming page as markdown text"""
        p = self.profile_data
        tcg_winrate = (p['tcg_wins'] / p['tcg_battles'] * 100) if p['tcg_battles'] > 0 else 0
        
        return f"""# 🎮 {self.user.display_name}'s Gaming Stats

## 🎮 Minigames
**Total:** {p['minigames_played']} played, {p['minigames_won']} won
**Wordle:** {p['wordle_wins']}/{p['wordle_attempts']}
**Riddles:** {p['riddles_solved']} solved
**Trivia:** {p['trivia_correct']}/{p['trivia_attempted']}

## 🎯 Board Games
**Tic-Tac-Toe:** {p['tictactoe_wins']}/{p['tictactoe_played']}
**Connect4:** {p['connect4_wins']}/{p['connect4_played']}
**Hangman:** {p['hangman_wins']}/{p['hangman_played']}

## 🃏 Card Games
**UNO:** {p['uno_wins']}/{p['uno_played']}
**Blackjack:** {p['blackjack_wins']}/{p['blackjack_played']}
**War:** {p['war_played']} games

## ⚔️ Psyvrse TCG
**Battles:** {p['tcg_battles']} ({tcg_winrate:.1f}% WR)
**Ranked:** {p['tcg_ranked_matches']} matches
**Tournaments:** {p['tcg_tournaments_won']}/{p['tcg_tournaments_entered']}
**Collection:** {p['tcg_cards_owned']} cards

## 🎣 Fishing & Combat
**Fish Caught:** {p['fish_caught']} (Rare: {p['rare_fish_caught']}, Legendary: {p['legendary_fish_caught']})
**Record:** {p['biggest_fish_weight']}kg
**PvP:** {p['pvp_wins']}/{p['pvp_battles']}
**Bosses:** {p['boss_wins']}/{p['boss_battles']}
**Dungeons:** {p['dungeons_completed']}"""
    
    def _create_economy_content(self):
        """Create economy page as markdown text"""
        p = self.profile_data
        net_profit = p['total_earned'] - p['total_spent']
        gambling_roi = ((p['gambling_total_won'] - p['gambling_total_wagered']) / p['gambling_total_wagered'] * 100) if p['gambling_total_wagered'] > 0 else 0
        business_status = "✅ Active" if p['business_owned'] else "❌ None"
        win_rate = (p['gambling_wins']/p['gambling_count']*100) if p['gambling_count'] > 0 else 0.0
        
        return f"""# 💰 {self.user.display_name}'s Economy Stats

## 💰 Finances
**Earned:** {p['total_earned']:,} coins
**Spent:** {p['total_spent']:,} coins
**Net Profit:** {net_profit:+,} coins
**Biggest Win:** {p['biggest_win']:,} coins
**Biggest Loss:** {p['biggest_loss']:,} coins

## 🎰 Gambling
**Games:** {p['gambling_count']}
**Win Rate:** {win_rate:.1f}%
**Wagered:** {p['gambling_total_wagered']:,}
**Won:** {p['gambling_total_won']:,}
**ROI:** {gambling_roi:+.1f}%

## 🏪 Business
**Status:** {business_status}
**Sales:** {p['business_sales']} items
**Revenue:** {p['business_revenue']:,}
**Items Sold:** {p['items_sold']}
**Items Bought:** {p['items_bought']}

## 📜 Quests & Rewards
**Daily Streak:** {p['daily_streak']} days (Longest: {p['longest_streak']})
**Quests Done:** {p['quests_completed']}
**Achievements:** {p['achievements_unlocked']}"""
    
    def _create_social_content(self):
        """Create social page as markdown text"""
        p = self.profile_data
        listen_hours = p['total_listen_time'] / 3600
        
        return f"""# 👥 {self.user.display_name}'s Social Stats

## 💬 Interactions
**Compliments Given:** {p['compliments_given']}
**Compliments Received:** {p['compliments_received']}
**Roasts Given:** {p['roasts_given']}
**High-Fives:** {p['highfives']}
**Story Contributions:** {p['stories_contributed']}

## 🐾 Pet Care
**Pets Owned:** {p['pets_owned']}
**Fed:** {p['pet_fed_count']} times
**Played:** {p['pet_played_count']} times
**Walked:** {p['pet_walked_count']} times
**Total Happiness:** {p['pet_total_happiness']}

## 🎉 Events
**Participated:** {p['events_participated']}
**Won:** {p['events_won']}
**Seasonal Points:** {p['seasonal_points']}

## 📊 Activity
**Commands Used:** {p['commands_used']}
**Messages Sent:** {p['messages_sent']}
**Active Servers:** {p['servers_active_in']}
**Reactions Added:** {p['reactions_added']}

## 🎵 Music
**Songs Played:** {p['songs_played']}
**Listen Time:** {listen_hours:.1f} hours
**Favorite Genre:** {p['favorite_genre'] or 'None'}"""

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "./data")
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        self.manager = ProfileManager(data_dir)
        # Compatibility alias used by other cogs
        self.profile_manager = self.manager
    
    @commands.command(name="profile", aliases=["p", "me"])
    async def profile_command(self, ctx, user: discord.User = None):
        """View your comprehensive profile"""
        target = user or ctx.author
        view = ProfileView(self.bot, target.id, target, ctx.author.id)

        await ctx.send(view=view)

    @app_commands.command(name="profile", description="View your comprehensive profile")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Slash command for profile"""
        await interaction.response.defer()

        target = user or interaction.user
        # Pass the bot and the viewer_id (interaction user) to match ProfileView signature
        view = ProfileView(self.bot, target.id, target, interaction.user.id)

        # Send the view directly (Components v2 TextDisplay is used inside the view)
        await interaction.followup.send(view=view)
    
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
