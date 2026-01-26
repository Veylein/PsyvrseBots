import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class Fishing(commands.Cog):
    """Ultimate Fishing Simulator - Boats, Bait, Rods, Areas, Weather, and More!"""

    @app_commands.command(name="fishhelp", description="View all fishing commands and info (paginated)")
    async def fishhelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Fishing"
        category_desc = "Go fishing and catch rare fish! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.fishing_data_file = os.path.join(data_dir, "fishing_data.json")
        self.fishing_data = self.load_fishing_data()
        
        # Weather conditions affecting fishing
        self.weather_types = {
            "sunny": {"multiplier": 1.0, "emoji": "☀️", "description": "Perfect fishing weather!"},
            "cloudy": {"multiplier": 1.2, "emoji": "☁️", "description": "Fish are more active!"},
            "rainy": {"multiplier": 1.5, "emoji": "🌧️", "description": "Great fishing conditions!"},
            "stormy": {"multiplier": 0.5, "emoji": "⛈️", "description": "Dangerous conditions!"},
            "foggy": {"multiplier": 1.3, "emoji": "🌫️", "description": "Mysterious catches await!"},
        }
        
        # Time of day effects
        self.time_periods = {
            "dawn": {"multiplier": 1.4, "emoji": "🌅", "hours": [5, 6, 7]},
            "morning": {"multiplier": 1.0, "emoji": "🌄", "hours": [8, 9, 10, 11]},
            "noon": {"multiplier": 0.8, "emoji": "🌞", "hours": [12, 13, 14]},
            "afternoon": {"multiplier": 1.0, "emoji": "🌤️", "hours": [15, 16, 17]},
            "dusk": {"multiplier": 1.4, "emoji": "🌇", "hours": [18, 19, 20]},
            "night": {"multiplier": 1.2, "emoji": "🌙", "hours": [21, 22, 23, 0, 1, 2, 3, 4]},
        }
        
        # Fishing rods with stats
        self.rods = {
            "basic_rod": {
                "name": "🎣 Basic Rod",
                "description": "A simple fishing rod for beginners",
                "cost": 0,
                "catch_bonus": 0,
                "rare_bonus": 0,
                "durability": 100
            },
            "carbon_rod": {
                "name": "🎣 Carbon Fiber Rod",
                "description": "Lightweight and strong",
                "cost": 1000,
                "catch_bonus": 10,
                "rare_bonus": 5,
                "durability": 200
            },
            "pro_rod": {
                "name": "🎣 Professional Rod",
                "description": "For serious anglers",
                "cost": 5000,
                "catch_bonus": 25,
                "rare_bonus": 15,
                "durability": 350
            },
            "master_rod": {
                "name": "🎣 Master Angler Rod",
                "description": "Expert-level equipment",
                "cost": 15000,
                "catch_bonus": 50,
                "rare_bonus": 30,
                "durability": 500
            },
            "legendary_rod": {
                "name": "🎣 Poseidon's Trident",
                "description": "Divine fishing power!",
                "cost": 50000,
                "catch_bonus": 100,
                "rare_bonus": 60,
                "durability": 999
            }
        }
        
        # Bait types
        self.baits = {
            "worm": {
                "name": "🪱 Worm",
                "description": "Basic bait for common fish",
                "cost": 10,
                "catch_bonus": 5,
                "rare_bonus": 0,
                "uses": 3
            },
            "cricket": {
                "name": "🦗 Cricket",
                "description": "Attracts freshwater fish",
                "cost": 25,
                "catch_bonus": 10,
                "rare_bonus": 5,
                "uses": 3
            },
            "minnow": {
                "name": "🐟 Minnow",
                "description": "Live bait for bigger catches",
                "cost": 50,
                "catch_bonus": 20,
                "rare_bonus": 10,
                "uses": 2
            },
            "squid": {
                "name": "🦑 Squid",
                "description": "Deep sea bait",
                "cost": 100,
                "catch_bonus": 35,
                "rare_bonus": 20,
                "uses": 2
            },
            "golden_lure": {
                "name": "✨ Golden Lure",
                "description": "Legendary bait for legendary fish!",
                "cost": 500,
                "catch_bonus": 75,
                "rare_bonus": 50,
                "uses": 1
            }
        }
        
        # Boats for accessing areas
        self.boats = {
            "none": {
                "name": "🦶 On Foot",
                "description": "Shore fishing only",
                "cost": 0,
                "areas": ["pond", "river"],
                "speed": 0
            },
            "canoe": {
                "name": "🛶 Canoe",
                "description": "Explore calm waters",
                "cost": 2000,
                "areas": ["pond", "river", "lake"],
                "speed": 1
            },
            "motorboat": {
                "name": "🚤 Motorboat",
                "description": "Reach distant locations",
                "cost": 10000,
                "areas": ["pond", "river", "lake", "ocean", "tropical"],
                "speed": 2
            },
            "yacht": {
                "name": "🛥️ Luxury Yacht",
                "description": "Access premium fishing spots",
                "cost": 50000,
                "areas": ["pond", "river", "lake", "ocean", "tropical", "arctic", "reef"],
                "speed": 3
            },
            "submarine": {
                "name": "🚢 Research Submarine",
                "description": "Explore the deepest waters!",
                "cost": 250000,
                "areas": ["pond", "river", "lake", "ocean", "tropical", "arctic", "reef", "abyss", "trench"],
                "speed": 4
            }
        }
        
        # Fishing areas with unique fish
        self.areas = {
            "pond": {
                "name": "🌿 Peaceful Pond",
                "description": "A calm pond perfect for beginners",
                "unlock_cost": 0,
                "fish": ["common_fish", "minnow", "carp", "tadpole", "lily_pad"],
                "required_boat": "none"
            },
            "river": {
                "name": "🌊 Flowing River",
                "description": "Fast-moving water with active fish",
                "unlock_cost": 0,
                "fish": ["trout", "salmon", "bass", "catfish", "river_stone"],
                "required_boat": "none"
            },
            "lake": {
                "name": "🏞️ Crystal Lake",
                "description": "Deep freshwater with variety",
                "unlock_cost": 500,
                "fish": ["pike", "walleye", "perch", "sturgeon", "water_lily"],
                "required_boat": "canoe"
            },
            "ocean": {
                "name": "🌊 Open Ocean",
                "description": "Vast saltwater adventure",
                "unlock_cost": 2500,
                "fish": ["tuna", "swordfish", "marlin", "mackerel", "seaweed"],
                "required_boat": "motorboat"
            },
            "tropical": {
                "name": "🏝️ Tropical Paradise",
                "description": "Exotic fish and warm waters",
                "unlock_cost": 5000,
                "fish": ["clownfish", "angelfish", "butterflyfish", "parrotfish", "coral"],
                "required_boat": "motorboat"
            },
            "arctic": {
                "name": "❄️ Arctic Waters",
                "description": "Frozen seas with rare creatures",
                "unlock_cost": 10000,
                "fish": ["arctic_char", "halibut", "seal", "penguin", "ice_crystal"],
                "required_boat": "yacht"
            },
            "reef": {
                "name": "🪸 Coral Reef",
                "description": "Colorful underwater paradise",
                "unlock_cost": 15000,
                "fish": ["seahorse", "lionfish", "moray_eel", "octopus", "pearl"],
                "required_boat": "yacht"
            },
            "abyss": {
                "name": "🌑 Dark Abyss",
                "description": "The deepest, most mysterious waters",
                "unlock_cost": 50000,
                "fish": ["anglerfish", "giant_squid", "gulper_eel", "vampire_squid", "black_pearl"],
                "required_boat": "submarine"
            },
            "trench": {
                "name": "🕳️ Mariana Trench",
                "description": "The ultimate fishing challenge",
                "unlock_cost": 100000,
                "fish": ["ancient_coelacanth", "megalodon_tooth", "kraken_tentacle", "atlantis_relic", "cosmic_jellyfish"],
                "required_boat": "submarine"
            }
        }
        
        # Fish encyclopedia
        self.fish_types = {
            # Common fish (Pond/River)
            "common_fish": {"name": "🐟 Common Fish", "rarity": "Common", "value": 10, "weight": [0.5, 2], "chance": 40},
            "minnow": {"name": "🐠 Minnow", "rarity": "Common", "value": 8, "weight": [0.1, 0.5], "chance": 35},
            "carp": {"name": "🐡 Carp", "rarity": "Common", "value": 15, "weight": [2, 8], "chance": 30},
            "tadpole": {"name": "🎣 Tadpole", "rarity": "Common", "value": 5, "weight": [0.05, 0.2], "chance": 25},
            "lily_pad": {"name": "🌸 Lily Pad", "rarity": "Common", "value": 3, "weight": [0.1, 0.3], "chance": 20},
            
            # River fish
            "trout": {"name": "🐟 Trout", "rarity": "Uncommon", "value": 35, "weight": [1, 5], "chance": 25},
            "salmon": {"name": "🐟 Salmon", "rarity": "Uncommon", "value": 45, "weight": [3, 12], "chance": 20},
            "bass": {"name": "🐟 Bass", "rarity": "Uncommon", "value": 40, "weight": [2, 8], "chance": 22},
            "catfish": {"name": "🐟 Catfish", "rarity": "Rare", "value": 65, "weight": [5, 25], "chance": 12},
            "river_stone": {"name": "🪨 River Stone", "rarity": "Common", "value": 2, "weight": [0.5, 3], "chance": 15},
            
            # Lake fish
            "pike": {"name": "🐟 Pike", "rarity": "Rare", "value": 75, "weight": [3, 15], "chance": 15},
            "walleye": {"name": "🐟 Walleye", "rarity": "Rare", "value": 70, "weight": [2, 10], "chance": 14},
            "perch": {"name": "🐟 Perch", "rarity": "Uncommon", "value": 35, "weight": [0.5, 3], "chance": 20},
            "sturgeon": {"name": "🐟 Sturgeon", "rarity": "Epic", "value": 200, "weight": [20, 100], "chance": 5},
            "water_lily": {"name": "💮 Water Lily", "rarity": "Uncommon", "value": 25, "weight": [0.1, 0.3], "chance": 18},
            
            # Ocean fish
            "tuna": {"name": "🐟 Tuna", "rarity": "Rare", "value": 100, "weight": [10, 50], "chance": 12},
            "swordfish": {"name": "🗡️ Swordfish", "rarity": "Epic", "value": 250, "weight": [50, 200], "chance": 6},
            "marlin": {"name": "🐟 Marlin", "rarity": "Epic", "value": 300, "weight": [100, 500], "chance": 5},
            "mackerel": {"name": "🐟 Mackerel", "rarity": "Uncommon", "value": 50, "weight": [1, 5], "chance": 18},
            "seaweed": {"name": "🌿 Seaweed", "rarity": "Common", "value": 5, "weight": [0.2, 1], "chance": 25},
            
            # Tropical fish
            "clownfish": {"name": "🤡 Clownfish", "rarity": "Uncommon", "value": 60, "weight": [0.2, 0.8], "chance": 20},
            "angelfish": {"name": "😇 Angelfish", "rarity": "Rare", "value": 90, "weight": [0.5, 2], "chance": 15},
            "butterflyfish": {"name": "🦋 Butterflyfish", "rarity": "Rare", "value": 85, "weight": [0.3, 1.5], "chance": 14},
            "parrotfish": {"name": "🦜 Parrotfish", "rarity": "Rare", "value": 95, "weight": [2, 10], "chance": 12},
            "coral": {"name": "🪸 Coral", "rarity": "Uncommon", "value": 40, "weight": [0.5, 3], "chance": 22},
            
            # Arctic fish
            "arctic_char": {"name": "🐟 Arctic Char", "rarity": "Rare", "value": 110, "weight": [2, 8], "chance": 15},
            "halibut": {"name": "🐟 Halibut", "rarity": "Rare", "value": 120, "weight": [10, 80], "chance": 12},
            "seal": {"name": "🦭 Seal", "rarity": "Epic", "value": 350, "weight": [50, 200], "chance": 5},
            "penguin": {"name": "🐧 Penguin", "rarity": "Epic", "value": 400, "weight": [20, 40], "chance": 4},
            "ice_crystal": {"name": "💎 Ice Crystal", "rarity": "Rare", "value": 150, "weight": [0.1, 1], "chance": 10},
            
            # Reef fish
            "seahorse": {"name": "🦑 Seahorse", "rarity": "Rare", "value": 130, "weight": [0.1, 0.5], "chance": 14},
            "lionfish": {"name": "🦁 Lionfish", "rarity": "Epic", "value": 280, "weight": [0.5, 3], "chance": 7},
            "moray_eel": {"name": "🐍 Moray Eel", "rarity": "Epic", "value": 320, "weight": [5, 30], "chance": 6},
            "octopus": {"name": "🐙 Octopus", "rarity": "Epic", "value": 300, "weight": [3, 15], "chance": 8},
            "pearl": {"name": "📿 Pearl", "rarity": "Epic", "value": 500, "weight": [0.05, 0.2], "chance": 3},
            
            # Abyss fish
            "anglerfish": {"name": "🎣 Anglerfish", "rarity": "Legendary", "value": 800, "weight": [5, 50], "chance": 8},
            "giant_squid": {"name": "🦑 Giant Squid", "rarity": "Legendary", "value": 1000, "weight": [100, 500], "chance": 5},
            "gulper_eel": {"name": "🐍 Gulper Eel", "rarity": "Legendary", "value": 900, "weight": [2, 15], "chance": 6},
            "vampire_squid": {"name": "🦇 Vampire Squid", "rarity": "Legendary", "value": 850, "weight": [1, 10], "chance": 7},
            "black_pearl": {"name": "⚫ Black Pearl", "rarity": "Legendary", "value": 2000, "weight": [0.1, 0.5], "chance": 2},
            
            # Trench (ultimate)
            "ancient_coelacanth": {"name": "🐠 Ancient Coelacanth", "rarity": "Mythic", "value": 5000, "weight": [50, 200], "chance": 5},
            "megalodon_tooth": {"name": "🦷 Megalodon Tooth", "rarity": "Mythic", "value": 8000, "weight": [10, 30], "chance": 3},
            "kraken_tentacle": {"name": "🦑 Kraken Tentacle", "rarity": "Mythic", "value": 10000, "weight": [100, 500], "chance": 2},
            "atlantis_relic": {"name": "🏺 Atlantis Relic", "rarity": "Mythic", "value": 15000, "weight": [5, 20], "chance": 1.5},
            "cosmic_jellyfish": {"name": "🌌 Cosmic Jellyfish", "rarity": "Mythic", "value": 25000, "weight": [0.5, 5], "chance": 0.5},
        }
        
        # Achievements
        self.achievements = {
            "first_catch": {"name": "First Catch", "description": "Catch your first fish", "reward": 100},
            "100_fish": {"name": "Century", "description": "Catch 100 fish", "reward": 1000},
            "rare_hunter": {"name": "Rare Hunter", "description": "Catch 10 rare fish", "reward": 500},
            "legendary_angler": {"name": "Legendary Angler", "description": "Catch a legendary fish", "reward": 2000},
            "deep_explorer": {"name": "Deep Explorer", "description": "Reach the Abyss", "reward": 5000},
            "master_collector": {"name": "Master Collector", "description": "Catch every type of fish", "reward": 50000},
        }
    
    def load_fishing_data(self):
        """Load fishing data from JSON"""
        if not os.path.exists(self.fishing_data_file):
            return {}
        try:
            with open(self.fishing_data_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_fishing_data(self):
        """Save fishing data to JSON"""
        try:
            with open(self.fishing_data_file, 'w') as f:
                json.dump(self.fishing_data, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving fishing data: {e}")
    
    def get_user_data(self, user_id):
        """Get user's fishing data"""
        user_id = str(user_id)
        if user_id not in self.fishing_data:
            self.fishing_data[user_id] = {
                "rod": "basic_rod",
                "boat": "none",
                "current_area": "pond",
                "bait_inventory": {},
                "fish_caught": {},
                "total_catches": 0,
                "total_value": 0,
                "unlocked_areas": ["pond", "river"],
                "achievements": [],
                "stats": {
                    "biggest_catch": None,
                    "rarest_catch": None,
                    "favorite_area": "pond"
                }
            }
        return self.fishing_data[user_id]
    
    def get_current_weather(self):
        """Get random weather"""
        return random.choice(list(self.weather_types.keys()))
    
    def get_current_time_period(self):
        """Get current time period"""
        hour = datetime.now().hour
        for period, data in self.time_periods.items():
            if hour in data["hours"]:
                return period
        return "morning"
    
    # ==================== MAIN FISH COMMAND ====================
    
    @app_commands.command(name="fish", description="🎣 Advanced Fishing Simulator")
    @app_commands.describe(
        action="What would you like to do?",
        bait="Bait type for casting (worm, cricket, minnow, squid, golden_lure)",
        rarity="Filter encyclopedia by rarity"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="🏠 Main Menu", value="menu"),
        app_commands.Choice(name="🎣 Cast Line", value="cast"),
        app_commands.Choice(name="🎒 Inventory", value="inventory"),
        app_commands.Choice(name="🏪 Shop", value="shop"),
        app_commands.Choice(name="🗺️ Areas", value="areas"),
        app_commands.Choice(name="📖 Encyclopedia", value="encyclopedia"),
        app_commands.Choice(name="📊 Stats", value="stats"),
    ])
    async def fish_main(self, interaction: discord.Interaction, action: Optional[str] = "menu", bait: Optional[str] = None, rarity: Optional[str] = None):
        """Main fishing command with optional actions"""
        if action == "cast":
            await self.cast_action(interaction, bait)
        elif action == "inventory":
            await self.fish_inventory_action(interaction)
        elif action == "shop":
            await self.fish_shop_action(interaction)
        elif action == "areas":
            await self.fish_areas_action(interaction)
        elif action == "encyclopedia":
            await self.fish_encyclopedia_action(interaction, rarity)
        elif action == "stats":
            await self.fish_stats_action(interaction)
        else:  # menu
            await self.fish_menu_action(interaction)
    
    async def fish_menu_action(self, interaction: discord.Interaction):
        """Show fishing main menu"""
        user_data = self.get_user_data(interaction.user.id)
        
        embed = discord.Embed(
            title="🎣 Ultimate Fishing Simulator",
            description="**Welcome to the most advanced fishing experience!**\n\n"
                       "**Your Stats:**\n"
                       f"🎣 Rod: {self.rods[user_data['rod']]['name']}\n"
                       f"🛶 Boat: {self.boats[user_data['boat']]['name']}\n"
                       f"📍 Area: {self.areas[user_data['current_area']]['name']}\n"
                       f"🐟 Total Catches: {user_data['total_catches']}\n\n"
                       "**Available Actions:**\n"
                       "Use `/fish <action>` to access different features:\n"
                       "• `cast` - Cast your line and fish!\n"
                       "• `inventory` - View your catches\n"
                       "• `shop` - Buy equipment & bait\n"
                       "• `areas` - Explore fishing locations\n"
                       "• `encyclopedia` - View fish encyclopedia\n"
                       "• `stats` - View your statistics",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def cast_action(self, interaction: discord.Interaction, bait: Optional[str] = None):
        """Cast fishing line"""
        user_data = self.get_user_data(interaction.user.id)
        
        # Get conditions
        weather = self.get_current_weather()
        time_period = self.get_current_time_period()
        weather_data = self.weather_types[weather]
        time_data = self.time_periods[time_period]
        
        # Calculate bonuses
        rod_bonus = self.rods[user_data["rod"]]["catch_bonus"]
        bait_bonus = 0
        bait_name = "None"
        
        if bait and bait in self.baits:
            if bait in user_data.get("bait_inventory", {}) and user_data["bait_inventory"][bait] > 0:
                bait_bonus = self.baits[bait]["catch_bonus"]
                bait_name = self.baits[bait]["name"]
                user_data["bait_inventory"][bait] -= 1
                if user_data["bait_inventory"][bait] <= 0:
                    del user_data["bait_inventory"][bait]
        
        # Fishing animation
        embed = discord.Embed(
            title="🎣 Casting Line...",
            description=f"{weather_data['emoji']} **Weather:** {weather.title()} - {weather_data['description']}\n"
                       f"{time_data['emoji']} **Time:** {time_period.title()}\n"
                       f"🎣 **Rod:** {self.rods[user_data['rod']]['name']}\n"
                       f"🪱 **Bait:** {bait_name}\n\n"
                       "🌊 *Waiting for a bite...*",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(2)
        
        # Determine catch
        area = user_data["current_area"]
        available_fish = self.areas[area]["fish"]
        
        # Calculate catch chance
        base_chance = 100
        total_multiplier = weather_data["multiplier"] * time_data["multiplier"]
        total_multiplier += (rod_bonus + bait_bonus) / 100
        
        # Select fish based on weighted chances
        fish_chances = []
        for fish_id in available_fish:
            fish = self.fish_types[fish_id]
            adjusted_chance = fish["chance"] * total_multiplier
            fish_chances.append((fish_id, adjusted_chance))
        
        # Pick fish
        total_weight = sum(chance for _, chance in fish_chances)
        rand = random.uniform(0, total_weight)
        current = 0
        caught_fish_id = fish_chances[0][0]
        
        for fish_id, chance in fish_chances:
            current += chance
            if rand <= current:
                caught_fish_id = fish_id
                break
        
        caught_fish = self.fish_types[caught_fish_id]
        weight = round(random.uniform(caught_fish["weight"][0], caught_fish["weight"][1]), 2)
        value = int(caught_fish["value"] * (1 + weight / 10))
        
        # Update user data
        if caught_fish_id not in user_data["fish_caught"]:
            user_data["fish_caught"][caught_fish_id] = {
                "count": 0,
                "total_value": 0,
                "biggest": 0
            }
        
        user_data["fish_caught"][caught_fish_id]["count"] += 1
        user_data["fish_caught"][caught_fish_id]["total_value"] += value
        user_data["fish_caught"][caught_fish_id]["biggest"] = max(
            user_data["fish_caught"][caught_fish_id]["biggest"], weight
        )
        user_data["total_catches"] += 1
        user_data["total_value"] += value
        
        # Add coins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(interaction.user.id, value, "fishing")

        # Chance to award a TCG card for simulation category (fishing)
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'simulation')
                if awarded:
                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                    embed.add_field(name='🎴 Bonus Card Reward', value=', '.join(names), inline=False)
            except Exception:
                pass
        
        # Result embed
        rarity_colors = {
            "Common": discord.Color.light_grey(),
            "Uncommon": discord.Color.green(),
            "Rare": discord.Color.blue(),
            "Epic": discord.Color.purple(),
            "Legendary": discord.Color.gold(),
            "Mythic": discord.Color.red()
        }
        
        embed = discord.Embed(
            title="🎉 Fish Caught!",
            description=f"**{caught_fish['name']}**\n"
                       f"**Rarity:** {caught_fish['rarity']}\n"
                       f"**Weight:** {weight} kg\n"
                       f"**Value:** {value} PsyCoins\n\n"
                       f"*Added to your collection!*",
            color=rarity_colors.get(caught_fish["rarity"], discord.Color.blue())
        )
        
        self.save_fishing_data()
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "fishing")
        await interaction.edit_original_response(embed=embed)
    
    async def fish_inventory_action(self, interaction: discord.Interaction):
        """View fishing inventory"""
        user_data = self.get_user_data(interaction.user.id)
        
        if not user_data["fish_caught"]:
            await interaction.response.send_message("🎣 You haven't caught any fish yet! Use `/cast` to start fishing!", ephemeral=True)
            return
        
        # Sort by total count
        sorted_fish = sorted(
            user_data["fish_caught"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        embed = discord.Embed(
            title=f"🐟 {interaction.user.display_name}'s Fish Collection",
            description=f"**Total Catches:** {user_data['total_catches']}\n"
                       f"**Total Value:** {user_data['total_value']} PsyCoins\n"
                       f"**Species Caught:** {len(user_data['fish_caught'])}/{len(self.fish_types)}\n",
            color=discord.Color.blue()
        )
        
        # Show top 10 fish
        for i, (fish_id, data) in enumerate(sorted_fish[:10]):
            fish = self.fish_types[fish_id]
            embed.add_field(
                name=f"{fish['name']} ({fish['rarity']})",
                value=f"Count: {data['count']} | Biggest: {data['biggest']}kg",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def fish_shop_action(self, interaction: discord.Interaction):
        """Fishing shop"""
        user_data = self.get_user_data(interaction.user.id)
        
        embed = discord.Embed(
            title="🏪 Fishing Shop",
            description="**Purchase upgrades and supplies!**\n\n"
                       "Use the commands below to buy items:",
            color=discord.Color.gold()
        )
        
        # Show rods
        rod_text = ""
        for rod_id, rod in self.rods.items():
            owned = "✅" if user_data["rod"] == rod_id else ""
            rod_text += f"{rod['name']} - {rod['cost']} coins {owned}\n"
        embed.add_field(name="🎣 Fishing Rods", value=rod_text or "None", inline=False)
        
        # Show boats
        boat_text = ""
        for boat_id, boat in self.boats.items():
            owned = "✅" if user_data["boat"] == boat_id else ""
            boat_text += f"{boat['name']} - {boat['cost']} coins {owned}\n"
        embed.add_field(name="🛶 Boats", value=boat_text or "None", inline=False)
        
        # Show bait
        bait_text = ""
        for bait_id, bait in self.baits.items():
            bait_text += f"{bait['name']} - {bait['cost']} coins\n"
        embed.add_field(name="🪱 Bait", value=bait_text or "None", inline=False)
        
        embed.set_footer(text="Use /fish action:buy to purchase items")
        
        await interaction.response.send_message(embed=embed)
    
    async def fish_areas_action(self, interaction: discord.Interaction):
        """View fishing areas"""
        user_data = self.get_user_data(interaction.user.id)
        
        embed = discord.Embed(
            title="🗺️ Fishing Areas",
            description=f"**Current Location:** {self.areas[user_data['current_area']]['name']}\n\n"
                       "**Available Areas:**",
            color=discord.Color.blue()
        )
        
        for area_id, area in self.areas.items():
            unlocked = area_id in user_data["unlocked_areas"]
            status = "✅ Unlocked" if unlocked else f"🔒 {area['unlock_cost']} coins"
            current = "📍" if area_id == user_data["current_area"] else ""
            
            embed.add_field(
                name=f"{current} {area['name']} {status}",
                value=f"{area['description']}\nBoat: {self.boats[area['required_boat']]['name']}",
                inline=False
            )
        
        embed.set_footer(text="Use /travel <area> to change location")
        
        
        await interaction.response.send_message(embed=embed)
    
    async def fish_encyclopedia_action(self, interaction: discord.Interaction, rarity: Optional[str] = None):
        embed = discord.Embed(
            title="📖 Fish Encyclopedia",
            description="**Discover all the fish species!**",
            color=discord.Color.green()
        )
        
        # Filter by rarity if provided
        fish_list = []
        for fish_id, fish in self.fish_types.items():
            if rarity is None or fish["rarity"].lower() == rarity.lower():
                fish_list.append((fish_id, fish))
        
        # Sort by value
        fish_list.sort(key=lambda x: x[1]["value"], reverse=True)
        
        # Show first 15
        for fish_id, fish in fish_list[:15]:
            embed.add_field(
                name=f"{fish['name']} ({fish['rarity']})",
                value=f"Value: {fish['value']} | Weight: {fish['weight'][0]}-{fish['weight'][1]}kg",
                inline=True
            )
        
        if len(fish_list) > 15:
            embed.set_footer(text=f"Showing 15/{len(fish_list)} fish")
        
        await interaction.response.send_message(embed=embed)
    
    async def fish_stats_action(self, interaction: discord.Interaction):
        """View fishing stats"""
        user_data = self.get_user_data(interaction.user.id)
        
        # Calculate stats
        biggest_catch = None
        biggest_weight = 0
        rarest_catch = None
        rarity_order = {"Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 3, "Legendary": 4, "Mythic": 5}
        highest_rarity = -1
        
        for fish_id, data in user_data["fish_caught"].items():
            if data["biggest"] > biggest_weight:
                biggest_weight = data["biggest"]
                biggest_catch = self.fish_types[fish_id]["name"]
            
            fish_rarity = self.fish_types[fish_id]["rarity"]
            if rarity_order.get(fish_rarity, 0) > highest_rarity:
                highest_rarity = rarity_order.get(fish_rarity, 0)
                rarest_catch = self.fish_types[fish_id]["name"]
        
        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name}'s Fishing Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🎣 Total Catches", value=str(user_data["total_catches"]), inline=True)
        embed.add_field(name="💰 Total Value", value=f"{user_data['total_value']} coins", inline=True)
        embed.add_field(name="🐟 Species", value=f"{len(user_data['fish_caught'])}/{len(self.fish_types)}", inline=True)
        embed.add_field(name="⚖️ Biggest Catch", value=f"{biggest_catch or 'None'} ({biggest_weight}kg)", inline=True)
        embed.add_field(name="✨ Rarest Catch", value=rarest_catch or "None", inline=True)
        embed.add_field(name="📍 Current Area", value=self.areas[user_data["current_area"]]["name"], inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Fishing(bot))
