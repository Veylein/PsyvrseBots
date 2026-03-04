import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os
from datetime import datetime, timezone, timedelta


def _parse_ts(s):
    """Parse ISO timestamp – handles both naive (old data) and tz-aware strings."""
    from datetime import datetime as _dt, timezone as _tz
    d = _dt.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=_tz.utc)


class Simulations(commands.Cog):
    """Simulation games like farming and ice cream maker"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        os.makedirs(data_dir, exist_ok=True)
        self.farm_data_file = os.path.join(data_dir, "farms.json")
        self._migrate_farms(data_dir)
        self.farm_data = self.load_data()
        
        self.crops = {
            "wheat": {"name": "🌾 Wheat", "grow_time": 5, "sell_price": 20, "cost": 1, "water_needs": 2, "xp": 5},
            "corn": {"name": "🌽 Corn", "grow_time": 10, "sell_price": 50, "cost": 2, "water_needs": 3, "xp": 10},
            "carrot": {"name": "🥕 Carrot", "grow_time": 7, "sell_price": 35, "cost": 2, "water_needs": 2, "xp": 7},
            "potato": {"name": "🥔 Potato", "grow_time": 8, "sell_price": 40, "cost": 2, "water_needs": 2, "xp": 8},
            "tomato": {"name": "🍅 Tomato", "grow_time": 12, "sell_price": 70, "cost": 3, "water_needs": 4, "xp": 15},
            "pumpkin": {"name": "🎃 Pumpkin", "grow_time": 15, "sell_price": 100, "cost": 4, "water_needs": 5, "xp": 20},
            "strawberry": {"name": "🍓 Strawberry", "grow_time": 10, "sell_price": 60, "cost": 3, "water_needs": 3, "xp": 12},
            "watermelon": {"name": "🍉 Watermelon", "grow_time": 20, "sell_price": 150, "cost": 5, "water_needs": 6, "xp": 30},
            "rice": {"name": "🍚 Rice", "grow_time": 15, "sell_price": 80, "cost": 3, "water_needs": 7, "xp": 18},
            "coffee": {"name": "☕ Coffee", "grow_time": 25, "sell_price": 200, "cost": 6, "water_needs": 4, "xp": 40},
            "cotton": {"name": "🧵 Cotton", "grow_time": 18, "sell_price": 120, "cost": 5, "water_needs": 3, "xp": 25},
            "sugarcane": {"name": "🎋 Sugarcane", "grow_time": 20, "sell_price": 140, "cost": 5, "water_needs": 5, "xp": 28}
        }
        
        self.tools = {
            "basic_hoe": {"name": "🪓 Basic Hoe", "cost": 0, "plant_speed": 1.0, "harvest_speed": 1.0},
            "iron_hoe": {"name": "⛏️ Iron Hoe", "cost": 50, "plant_speed": 1.2, "harvest_speed": 1.1},
            "steel_hoe": {"name": "🔨 Steel Hoe", "cost": 150, "plant_speed": 1.5, "harvest_speed": 1.3},
            "golden_hoe": {"name": "✨ Golden Hoe", "cost": 500, "plant_speed": 2.0, "harvest_speed": 1.5},
            "bucket": {"name": "🪣 Water Bucket", "cost": 30, "water_capacity": 10},
            "sprinkler": {"name": "💧 Sprinkler", "cost": 200, "auto_water": True, "plots": 2},
            "advanced_sprinkler": {"name": "🌊 Advanced Sprinkler", "cost": 500, "auto_water": True, "plots": 4},
            "fertilizer": {"name": "🍂 Fertilizer", "cost": 20, "growth_boost": 0.5},
            "super_fertilizer": {"name": "✨ Super Fertilizer", "cost": 80, "growth_boost": 0.75},
            "scarecrow": {"name": "🧸 Scarecrow", "cost": 100, "pest_protection": True},
            "greenhouse": {"name": "🏡 Greenhouse", "cost": 1000, "weather_protection": True, "plots": 12},
            "tractor": {"name": "🚜 Tractor", "cost": 2000, "auto_harvest": True, "plots": 6},
            "combine": {"name": "🌾 Combine Harvester", "cost": 5000, "auto_harvest": True, "auto_plant": True, "plots": 12}
        }
        
        self.animals = {
            "chicken": {"name": "🐔 Chicken", "cost": 50, "product": "🥚 Egg", "produce_time": 10, "product_value": 15, "feed_cost": 5, "breed_time": 30},
            "cow": {"name": "🐄 Cow", "cost": 200, "product": "🥛 Milk", "produce_time": 20, "product_value": 40, "feed_cost": 15, "breed_time": 60},
            "sheep": {"name": "🐑 Sheep", "cost": 150, "product": "🧶 Wool", "produce_time": 30, "product_value": 60, "feed_cost": 10, "breed_time": 45},
            "pig": {"name": "🐖 Pig", "cost": 180, "product": "🥓 Bacon", "produce_time": 25, "product_value": 50, "feed_cost": 12, "breed_time": 40},
            "goat": {"name": "🐐 Goat", "cost": 120, "product": "🧀 Cheese", "produce_time": 18, "product_value": 35, "feed_cost": 8, "breed_time": 35},
            "bee": {"name": "🐝 Bee Hive", "cost": 250, "product": "🍯 Honey", "produce_time": 15, "product_value": 80, "feed_cost": 3, "breed_time": 20}
        }
        
        # Rare/Hybrid Crops (from breeding/genetics)
        self.rare_crops = {
            "golden_wheat": {"name": "✨ Golden Wheat", "parent1": "wheat", "parent2": "wheat", "grow_time": 8, "sell_price": 80, "cost": 5, "water_needs": 3, "xp": 25},
            "super_corn": {"name": "⭐ Super Corn", "parent1": "corn", "parent2": "tomato", "grow_time": 15, "sell_price": 150, "cost": 8, "water_needs": 5, "xp": 40},
            "rainbow_berry": {"name": "🌈 Rainbow Berry", "parent1": "strawberry", "parent2": "watermelon", "grow_time": 25, "sell_price": 300, "cost": 10, "water_needs": 8, "xp": 60},
            "magic_pumpkin": {"name": "🎃✨ Magic Pumpkin", "parent1": "pumpkin", "parent2": "potato", "grow_time": 30, "sell_price": 400, "cost": 12, "water_needs": 10, "xp": 80}
        }
        
        # Pests & Diseases
        self.pests = ["🐛 Aphids", "🦟 Locusts", "🐌 Slugs", "🦠 Blight", "🐭 Rats"]
        self.pest_chance = 0.15  # 15% chance per harvest
        
        # Farm Decorations
        self.decorations = {
            "fence": {"name": "🚧 Fence", "cost": 20, "beauty": 5},
            "stone_path": {"name": "🪨 Stone Path", "cost": 30, "beauty": 8},
            "flower_bed": {"name": "🌸 Flower Bed", "cost": 40, "beauty": 12},
            "fountain": {"name": "⛲ Fountain", "cost": 100, "beauty": 25},
            "windmill": {"name": "🌾 Windmill", "cost": 200, "beauty": 40},
            "statue": {"name": "🗿 Statue", "cost": 150, "beauty": 35},
            "lamp_post": {"name": "💡 Lamp Post", "cost": 50, "beauty": 15},
            "tree": {"name": "🌳 Tree", "cost": 60, "beauty": 18}
        }
        
        # Daily Quests
        self.daily_quests = {
            "plant_5": {"name": "Plant 5 Crops", "requirement": 5, "reward": 50, "type": "plant"},
            "harvest_10": {"name": "Harvest 10 Crops", "requirement": 10, "reward": 80, "type": "harvest"},
            "feed_animals": {"name": "Feed All Animals", "requirement": 1, "reward": 40, "type": "feed"},
            "collect_products": {"name": "Collect 5 Products", "requirement": 5, "reward": 60, "type": "collect"},
            "earn_tokens": {"name": "Earn 100 Farm Tokens", "requirement": 100, "reward": 150, "type": "earn"}
        }
        
        # Achievements
        self.achievements = {
            "first_harvest": {"name": "🌾 First Harvest", "desc": "Harvest your first crop", "reward": 25},
            "master_farmer": {"name": "🚜 Master Farmer", "desc": "Reach level 10", "reward": 200},
            "animal_lover": {"name": "🐔 Animal Lover", "desc": "Own 10 animals", "reward": 150},
            "wealthy_farmer": {"name": "💰 Wealthy Farmer", "desc": "Have 1000 Farm Tokens", "reward": 500},
            "hybrid_creator": {"name": "🧬 Hybrid Creator", "desc": "Create a hybrid crop", "reward": 300},
            "beautiful_farm": {"name": "✨ Beautiful Farm", "desc": "Reach 100 beauty points", "reward": 250},
            "speedrunner": {"name": "⚡ Speedrunner", "desc": "Harvest 50 crops in one day", "reward": 400}
        }
        
        # Market prices (fluctuate)
        self.market_multipliers = {
            "high_demand": 1.5,
            "normal": 1.0,
            "low_demand": 0.7,
            "shortage": 2.0
        }
        
        self.seasons = {
            "spring": {"name": "🌸 Spring", "bonus": ["strawberry", "carrot"], "multiplier": 1.5},
            "summer": {"name": "☀️ Summer", "bonus": ["watermelon", "tomato", "corn"], "multiplier": 1.5},
            "fall": {"name": "🍂 Fall", "bonus": ["pumpkin", "wheat"], "multiplier": 1.5},
            "winter": {"name": "❄️ Winter", "bonus": ["potato"], "multiplier": 1.2}
        }
        
        self.ice_cream_bases = ["🍦 Vanilla", "🍫 Chocolate", "🍓 Strawberry", "🍨 Mint", "🍦 Cookie Dough"]
        self.ice_cream_toppings = ["🍫 Chocolate Chips", "🍓 Strawberries", "🍌 Banana", "🥜 Peanuts", 
                                    "🍒 Cherry", "🍪 Cookie Crumbs", "🍬 Candy", "🌰 Almonds"]
        self.ice_cream_sauces = ["🍫 Chocolate Sauce", "🍯 Caramel", "🍓 Strawberry Syrup", "🍦 Hot Fudge"]
    
    def _migrate_farms(self, data_dir: str):
        """Migrate farms.json from cwd root to data/ on first run."""
        old = "farms.json"
        if not os.path.exists(self.farm_data_file) and os.path.exists(old):
            import shutil
            shutil.copy2(old, self.farm_data_file)

    def load_data(self):
        """Load farm data"""
        if os.path.exists(self.farm_data_file):
            try:
                with open(self.farm_data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_data(self):
        """Save farm data"""
        try:
            with open(self.farm_data_file, 'w') as f:
                json.dump(self.farm_data, f, indent=4)
        except Exception as e:
            print(f"Error saving farm data: {e}")
    
    def get_farm(self, user_id):
        """Get user's farm"""
        user_id = str(user_id)
        if user_id not in self.farm_data:
            # Give starter pack: 10 Farm Tokens to begin
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                if user_id not in economy_cog.economy_data:
                    economy_cog.economy_data[user_id] = {"balance": 0, "farm_tokens": 10}
                else:
                    economy_cog.economy_data[user_id]["farm_tokens"] = economy_cog.economy_data[user_id].get("farm_tokens", 0) + 10
                economy_cog.economy_dirty = True
            
            self.farm_data[user_id] = {
                "plots": {},
                "inventory": {},
                "season": "spring",
                "season_change": (discord.utils.utcnow() + timedelta(days=1)).isoformat(),
                "tools": ["basic_hoe"],  # Start with basic hoe
                "animals": {},
                "animal_products": {},
                "water_level": 10,  # Start with 10 water
                "xp": 0,
                "level": 1,
                "max_plots": 6,
                "auto_watered_plots": [],
                "fertilized_plots": {},
                "weather": "sunny",
                "decorations": {},
                "beauty_points": 0,
                "daily_quest": None,
                "quest_progress": 0,
                "quest_reset": (discord.utils.utcnow() + timedelta(days=1)).isoformat(),
                "achievements": [],
                "genetics_lab": False,  # Unlock at level 10
                "market_status": {},
                "harvests_today": 0,
                "last_reset": discord.utils.utcnow().isoformat(),
                "breeding_pairs": {}
            }
            self.save_data()
        return self.farm_data[user_id]
    
    def get_current_season(self, farm):
        """Get current season and rotate if needed"""
        season_change = _parse_ts(farm["season_change"])
        if discord.utils.utcnow() >= season_change:
            seasons_list = list(self.seasons.keys())
            current_idx = seasons_list.index(farm["season"])
            farm["season"] = seasons_list[(current_idx + 1) % len(seasons_list)]
            farm["season_change"] = (discord.utils.utcnow() + timedelta(days=1)).isoformat()
            self.save_data()
        return farm["season"]
    
    def check_daily_reset(self, farm):
        """Reset daily counters"""
        last_reset = _parse_ts(farm.get("last_reset", discord.utils.utcnow().isoformat()))
        if (discord.utils.utcnow() - last_reset).days >= 1:
            farm["harvests_today"] = 0
            farm["last_reset"] = discord.utils.utcnow().isoformat()
            # Assign new daily quest
            quest_id = random.choice(list(self.daily_quests.keys()))
            farm["daily_quest"] = quest_id
            farm["quest_progress"] = 0
            farm["quest_reset"] = (discord.utils.utcnow() + timedelta(days=1)).isoformat()
            self.save_data()
    
    def check_pest_attack(self):
        """Random pest attack chance"""
        return random.random() < self.pest_chance
    
    def get_market_price(self, crop_name, base_price, farm):
        """Get dynamic market price for crop"""
        if crop_name not in farm.get("market_status", {}):
            # Assign random market status
            statuses = ["high_demand", "normal", "normal", "normal", "low_demand", "shortage"]
            farm["market_status"][crop_name] = random.choice(statuses)
            self.save_data()
        
        status = farm["market_status"].get(crop_name, "normal")
        multiplier = self.market_multipliers.get(status, 1.0)
        return int(base_price * multiplier), status
    
    def check_achievement(self, user_id, achievement_id):
        """Check and award achievement"""
        farm = self.get_farm(user_id)
        if achievement_id not in farm.get("achievements", []):
            achievement = self.achievements[achievement_id]
            farm["achievements"] = farm.get("achievements", []) + [achievement_id]
            
            # Award tokens
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                user_id_str = str(user_id)
                economy_cog.economy_data[user_id_str]["farm_tokens"] = \
                    economy_cog.economy_data[user_id_str].get("farm_tokens", 0) + achievement["reward"]
                economy_cog.economy_dirty = True
            
            self.save_data()
            return True, achievement
        return False, None
    
    # Farm command
    @app_commands.command(name="farm", description="🚜 Ultimate farming simulator with tools, animals & more!")
    @app_commands.choices(action=[
        app_commands.Choice(name="🚜 View Farm", value="view"),
        app_commands.Choice(name="🌱 Plant Crop", value="plant"),
        app_commands.Choice(name="🌾 Harvest Crops", value="harvest"),
        app_commands.Choice(name="💧 Water Crops", value="water"),
        app_commands.Choice(name="💰 Sell Harvest", value="sell"),
        app_commands.Choice(name="🏪 Shop (Tools & Animals)", value="shop"),
        app_commands.Choice(name="🐔 Manage Animals", value="animals"),
        app_commands.Choice(name="🌾 Feed Animals", value="feed"),
        app_commands.Choice(name="📦 Collect Products", value="collect"),
        app_commands.Choice(name="⬆️ Upgrade Farm", value="upgrade"),
        app_commands.Choice(name="📊 Farm Stats", value="stats"),
        app_commands.Choice(name="🧬 Breed Crops", value="breed"),
        app_commands.Choice(name="✨ Decorations", value="decorate"),
        app_commands.Choice(name="📋 Daily Quest", value="quest"),
        app_commands.Choice(name="📊 Market Prices", value="market"),
        app_commands.Choice(name="🏆 Achievements", value="achievements")
    ])
    @app_commands.describe(
        crop="For planting: wheat, corn, carrot, potato, tomato, pumpkin, strawberry, watermelon, rice, coffee, cotton, sugarcane",
        item="For shop: item name (e.g., iron_hoe, bucket, chicken, etc.)",
        plot="Plot number for specific actions"
    )
    async def farm_command(self, interaction: discord.Interaction, action: app_commands.Choice[str], crop: str = None, item: str = None, plot: int = None):
        """Unified ultimate farm command"""
        action_value = action.value if isinstance(action, app_commands.Choice) else action
        
        if action_value == "view":
            await self.farm_view_action(interaction)
        elif action_value == "plant":
            if not crop:
                await interaction.response.send_message("❌ Specify a crop! Available: " + ", ".join(self.crops.keys()), ephemeral=True)
                return
            await self.farm_plant_action(interaction, crop, plot)
        elif action_value == "harvest":
            await self.farm_harvest_action(interaction)
        elif action_value == "water":
            await self.farm_water_action(interaction, plot)
        elif action_value == "sell":
            await self.farm_sell_action(interaction)
        elif action_value == "shop":
            await self.farm_shop_action(interaction, item)
        elif action_value == "animals":
            await self.farm_animals_action(interaction)
        elif action_value == "feed":
            await self.farm_feed_action(interaction)
        elif action_value == "collect":
            await self.farm_collect_action(interaction)
        elif action_value == "upgrade":
            await self.farm_upgrade_action(interaction)
        elif action_value == "stats":
            await self.farm_stats_action(interaction)
        elif action_value == "breed":
            await self.farm_breed_action(interaction)
        elif action_value == "decorate":
            await self.farm_decorate_action(interaction)
        elif action_value == "quest":
            await self.farm_quest_action(interaction)
        elif action_value == "market":
            await self.farm_market_action(interaction)
        elif action_value == "achievements":
            await self.farm_achievements_action(interaction)
        elif action_value == "sell":
            await self.farm_sell_action(interaction)
    
    async def farm_view_action(self, interaction: discord.Interaction):
        """View farm"""
        farm = self.get_farm(interaction.user.id)
        current_season = self.get_current_season(farm)
        season_data = self.seasons[current_season]
        self.check_daily_reset(farm)
        
        # Check for pet interaction
        pets_cog = self.bot.get_cog("Pets")
        pet_warning = ""
        if pets_cog:
            pet_check = pets_cog.check_pet_farm_interaction(interaction.user.id)
            if pet_check["interaction"]:
                pet_warning = f"\n⚠️ **{pet_check['pet_emoji']} {pet_check['pet_name']} is hungry and might cause trouble!**"
        
        # Check plots
        plot_status = []
        for plot_num, plot_data in farm["plots"].items():
            crop = self.crops[plot_data["crop"]]
            plant_time = _parse_ts(plot_data["planted"])
            elapsed = (discord.utils.utcnow() - plant_time).total_seconds() / 60  # minutes
            
            # Show watered/fertilized status
            status_icons = ""
            if plot_data.get("watered"):
                status_icons += "💧"
            if plot_data.get("fertilized"):
                status_icons += "🌱"
            
            if elapsed >= crop["grow_time"]:
                plot_status.append(f"Plot {plot_num}: {crop['name']} {status_icons} ✅ **READY!**")
            else:
                remaining = crop["grow_time"] - elapsed
                plot_status.append(f"Plot {plot_num}: {crop['name']} {status_icons} ⏳ {remaining:.1f}min")
        
        if not plot_status:
            plot_status.append("*No crops planted*")
        
        # Inventory
        inventory_str = "\n".join([
            f"{self.crops.get(crop, self.rare_crops.get(crop, {'name': crop}))['name']} x{count}"
            for crop, count in farm["inventory"].items()
        ]) if farm["inventory"] else "*Empty*"
        
        # Get farm tokens from economy
        farm_tokens = 0
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user_id = str(interaction.user.id)
            if user_id in economy_cog.economy_data:
                farm_tokens = economy_cog.economy_data[user_id].get("farm_tokens", 0)
        
        # Daily quest status
        quest_str = "*No quest today*"
        if farm.get("daily_quest"):
            quest_info = self.daily_quests.get(farm["daily_quest"])
            if quest_info:
                progress = farm.get("quest_progress", 0)
                target = quest_info.get("requirement", quest_info.get("target", 1))
                reward = quest_info["reward"]
                status = "✅ COMPLETE!" if progress >= target else f"{progress}/{target}"
                quest_str = f"{quest_info.get('description', quest_info.get('name', '?'))} - {status} (Reward: {reward} 🌾)"
        
        # Beauty & level info
        level = farm.get("level", 1)
        xp = farm.get("xp", 0)
        max_plots = farm.get("max_plots", 6)
        beauty = farm.get("beauty_points", 0)
        
        # Achievements count
        achievements_count = len(farm.get("achievements", []))
        
        embed = discord.Embed(
            title=f"🚜 {interaction.user.display_name}'s Farm (Level {level})",
            description=f"**Season:** {season_data['name']}\n"
                       f"**Season Bonus:** {', '.join([self.crops[c]['name'] for c in season_data['bonus']])} "
                       f"({int((season_data['multiplier'] - 1) * 100)}% more profit!)\n"
                       f"**Farm Tokens:** 🌾 {farm_tokens}\n"
                       f"**XP:** {xp}/100 to Level {level + 1}\n"
                       f"**Max Plots:** {max_plots}\n"
                       f"**Beauty Points:** ✨ {beauty}\n"
                       f"**Achievements:** 🏆 {achievements_count}/7"
                       f"{pet_warning}\n\n"
                       f"**Daily Quest:**\n{quest_str}\n\n"
                       f"**Plots:**\n" + "\n".join(plot_status),
            color=discord.Color.green()
        )
        
        embed.add_field(name="Inventory", value=inventory_str, inline=False)
        
        # Show decorations if any
        if farm.get("decorations"):
            deco_list = [f"{item} x{count}" for item, count in farm["decorations"].items()]
            embed.add_field(name="Decorations", value="\n".join(deco_list), inline=False)
        
        embed.set_footer(text="Use /farm plant, /farm harvest, /farm decorate, /farm quest")
        
        await interaction.response.send_message(embed=embed)
    
    async def farm_plant_action(self, interaction: discord.Interaction, crop: str, plot: int = None):
        """Plant crop"""
        if crop.lower() not in self.crops:
            await interaction.response.send_message(
                f"❌ Invalid crop! Available: {', '.join(self.crops.keys())}",
                ephemeral=True
            )
            return
        
        farm = self.get_farm(interaction.user.id)
        crop_data = self.crops[crop.lower()]
        
        # Check if user has enough Farm Tokens
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user_id = str(interaction.user.id)
            if user_id not in economy_cog.economy_data:
                economy_cog.economy_data[user_id] = {"balance": 0, "farm_tokens": 10}  # Give starter tokens
            
            farm_tokens = economy_cog.economy_data[user_id].get("farm_tokens", 0)
            if farm_tokens < crop_data["cost"]:
                await interaction.response.send_message(
                    f"❌ You need {crop_data['cost']} 🌾 Farm Tokens to plant {crop_data['name']}!\n"
                    f"You have: {farm_tokens} 🌾\n\n"
                    f"💡 Convert PsyCoins to Farm Tokens with `/convert`!\n"
                    f"💡 Or plant cheaper crops first (wheat costs 1 🌾)!",
                    ephemeral=True
                )
                return
            
            # Deduct tokens
            economy_cog.economy_data[user_id]["farm_tokens"] -= crop_data["cost"]
            economy_cog.economy_dirty = True
            await economy_cog.save_economy()
        
        # Find empty plot
        plot_num = 1
        while str(plot_num) in farm["plots"]:
            plot_num += 1
        
        if plot_num > farm.get("max_plots", 6):  # Max plots
            await interaction.response.send_message(
                "❌ All plots are full! Harvest some crops first!",
                ephemeral=True
            )
            return
        
        # Check for pet interference
        pets_cog = self.bot.get_cog("Pets")
        pet_msg = ""
        if pets_cog:
            pet_check = pets_cog.check_pet_farm_interaction(interaction.user.id)
            if pet_check["interaction"] and pet_check["type"] == "dig":
                pet_msg = f"\n\n⚠️ Oh no! {pet_check['pet_emoji']} {pet_check['pet_name']} dug up your seeds!"
                # Randomly damage the crop
                if random.randint(1, 2) == 1:
                    pet_msg += f" The seeds were ruined! Feed your pet to prevent this."
                    await interaction.response.send_message(pet_msg)
                    return
        
        # Plant crop
        farm["plots"][str(plot_num)] = {
            "crop": crop.lower(),
            "planted": discord.utils.utcnow().isoformat(),
            "watered": False,
            "fertilized": False
        }
        
        # Add XP
        farm["xp"] = farm.get("xp", 0) + crop_data.get("xp", 5)
        
        # Update quest progress
        if farm.get("daily_quest") == "plant_5":
            farm["quest_progress"] = farm.get("quest_progress", 0) + 1
        
        self.save_data()
        
        embed = discord.Embed(
            title="🌱 Crop Planted!",
            description=f"You planted {crop_data['name']} in Plot {plot_num}!{pet_msg}\n\n"
                       f"**Grow Time:** {crop_data['grow_time']} minutes\n"
                       f"**Sell Price:** {crop_data['sell_price']} PsyCoins\n"
                       f"**XP Gained:** +{crop_data.get('xp', 5)} XP\n\n"
                       f"💧 Water crops with `/farm water` for faster growth!\n"
                       f"Come back later to harvest!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def farm_harvest_action(self, interaction: discord.Interaction):
        """Harvest crops"""
        farm = self.get_farm(interaction.user.id)
        current_season = self.get_current_season(farm)
        season_data = self.seasons[current_season]
        self.check_daily_reset(farm)
        
        # Check for pet interference BEFORE harvesting
        pets_cog = self.bot.get_cog("Pets")
        pet_interaction = {"interaction": False}
        if pets_cog:
            pet_interaction = pets_cog.check_pet_farm_interaction(interaction.user.id)
        
        harvested = []
        total_value = 0
        pet_messages = []
        pest_attacks = []
        xp_gained = 0
        achievements_unlocked = []
        
        for plot_num, plot_data in list(farm["plots"].items()):
            crop = self.crops[plot_data["crop"]]
            plant_time = _parse_ts(plot_data["planted"])
            elapsed = (discord.utils.utcnow() - plant_time).total_seconds() / 60
            
            if elapsed >= crop["grow_time"]:
                crop_name = plot_data["crop"]
                base_value = crop["sell_price"]
                
                # Check for pest attack
                if self.check_pest_attack() and "scarecrow" not in farm.get("tools", []):
                    pest_name = random.choice(self.pests)
                    pest_attacks.append(f"{pest_name} destroyed {crop['name']}!")
                    del farm["plots"][plot_num]
                    continue
                
                # Get dynamic market price
                market_price, market_status = self.get_market_price(crop_name, base_value, farm)
                value = market_price
                
                # Apply season bonus
                if crop_name in season_data["bonus"]:
                    value = int(value * season_data["multiplier"])
                
                # Check if pet interferes with THIS crop
                if pet_interaction["interaction"]:
                    interaction_type = pet_interaction["type"]
                    pet_name = pet_interaction["pet_name"]
                    pet_emoji = pet_interaction["pet_emoji"]
                    
                    # Roll for each crop (30% chance if pet is mischievous)
                    if random.randint(1, 100) <= 30:
                        if interaction_type == "trample":
                            pet_messages.append(f"💥 {pet_emoji} {pet_name} trampled your {crop['name']}!")
                            del farm["plots"][plot_num]
                            continue
                        elif interaction_type == "burn":
                            pet_messages.append(f"🔥 {pet_emoji} {pet_name} burned your {crop['name']}!")
                            del farm["plots"][plot_num]
                            continue
                        elif interaction_type == "eat":
                            value = int(value * 0.5)  # 50% reduced value
                            pet_messages.append(f"😋 {pet_emoji} {pet_name} ate half your {crop['name']}!")
                        elif interaction_type == "dig":
                            pet_messages.append(f"🕳️ {pet_emoji} {pet_name} dug up your {crop['name']}!")
                            del farm["plots"][plot_num]
                            continue
                        elif interaction_type == "hoard":
                            stolen = int(value * 0.3)  # Steal 30%
                            value -= stolen
                            pet_messages.append(f"🎁 {pet_emoji} {pet_name} hoarded some of your {crop['name']}!")
                
                # Add to inventory and value
                farm["inventory"][crop_name] = farm["inventory"].get(crop_name, 0) + 1
                total_value += value
                xp_gained += crop.get("xp", 5)
                
                # Market status indicator
                status_emoji = {"high_demand": "📈", "normal": "➡️", "low_demand": "📉", "shortage": "🚨"}
                harvested.append(f"{crop['name']} (+{value} {status_emoji.get(market_status, '➡️')})")
                
                # Track for quests
                farm["harvests_today"] = farm.get("harvests_today", 0) + 1
                
                # Clear plot
                del farm["plots"][plot_num]
        
        if not harvested:
            await interaction.response.send_message("❌ No crops are ready to harvest!", ephemeral=True)
            return
        
        # Add XP and check level up
        farm["xp"] = farm.get("xp", 0) + xp_gained
        old_level = farm.get("level", 1)
        new_level = 1 + (farm["xp"] // 100)  # Level up every 100 XP
        if new_level > old_level:
            farm["level"] = new_level
            farm["max_plots"] = 6 + (new_level * 2)  # 2 more plots per level
            achievements_unlocked.append(f"⬆️ Level {new_level}! Max plots: {farm['max_plots']}")
        
        # Check achievements
        if len(harvested) == 1 and "first_harvest" not in farm.get("achievements", []):
            unlocked, achievement = self.check_achievement(interaction.user.id, "first_harvest")
            if unlocked:
                achievements_unlocked.append(f"🏆 {achievement['name']}: +{achievement['reward']} 🌾!")
        
        if farm.get("harvests_today", 0) >= 50:
            unlocked, achievement = self.check_achievement(interaction.user.id, "speedrunner")
            if unlocked:
                achievements_unlocked.append(f"🏆 {achievement['name']}: +{achievement['reward']} 🌾!")
        
        # Update quest progress
        if farm.get("daily_quest") == "harvest_10":
            farm["quest_progress"] = farm.get("quest_progress", 0) + len(harvested)
        
        self.save_data()
        
        # Build embed with all info
        description = f"**Harvested:**\n" + "\n".join(harvested)
        description += f"\n\n**XP Gained:** +{xp_gained} XP"
        
        if pest_attacks:
            description += f"\n\n**🐛 Pest Attacks:**\n" + "\n".join(pest_attacks)
            description += f"\n\n💡 *Buy a Scarecrow to prevent pests!*"
        
        if pet_messages:
            description += f"\n\n**Pet Mischief:**\n" + "\n".join(pet_messages)
            description += f"\n\n💡 *Feed your pet to reduce mischief!*"
        
        if achievements_unlocked:
            description += f"\n\n**🎉 Achievements:**\n" + "\n".join(achievements_unlocked)
        
        description += f"\n\n**Total Value:** {total_value} PsyCoins\n**Current Level:** {farm.get('level', 1)}\nUse `/farm sell` to sell your harvest!"
        
        embed = discord.Embed(
            title="🌾 Harvest Complete!",
            description=description,
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def farm_sell_action(self, interaction: discord.Interaction):
        """Sell crops"""
        farm = self.get_farm(interaction.user.id)
        current_season = self.get_current_season(farm)
        season_data = self.seasons[current_season]
        
        if not farm["inventory"]:
            await interaction.response.send_message("❌ No crops to sell!", ephemeral=True)
            return
        
        total_value = 0
        sold_items = []
        
        for crop_name, count in farm["inventory"].items():
            crop = self.crops[crop_name]
            value = crop["sell_price"] * count
            
            # Season bonus
            if crop_name in season_data["bonus"]:
                value = int(value * season_data["multiplier"])
            
            total_value += value
            sold_items.append(f"{crop['name']} x{count} = {value} coins")
        
        # Convert coins to Farm Tokens (PsyCoins → Tokens)
        # Reward rate: 1 Farm Token per 50 PsyCoins worth of crops sold
        farm_tokens = max(1, total_value // 50)
        
        # Add Farm Tokens instead of PsyCoins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user_id = str(interaction.user.id)
            if user_id not in economy_cog.economy_data:
                economy_cog.economy_data[user_id] = {"balance": 0, "farm_tokens": 0}
            
            economy_cog.economy_data[user_id]["farm_tokens"] = economy_cog.economy_data[user_id].get("farm_tokens", 0) + farm_tokens
            economy_cog.economy_dirty = True
            await economy_cog.save_economy()
        
        farm["inventory"] = {}
        self.save_data()
        
        embed = discord.Embed(
            title="💰 Crops Sold!",
            description="**Sold:**\n" + "\n".join(sold_items) + f"\n\n"
                       f"**Crop Value:** {total_value} PsyCoins\n"
                       f"**Earned:** {farm_tokens} 🌾 Farm Tokens!\n\n"
                       f"*Farm Tokens can be used to plant more crops!*",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def farm_breed_action(self, interaction: discord.Interaction):
        """Breed two crops to create hybrid crops"""
        farm = self.get_farm(interaction.user.id)
        
        # Check if user has genetics lab
        if "genetics_lab" not in farm.get("tools", []):
            await interaction.response.send_message(
                "❌ You need a **Genetics Lab** to breed crops!\n"
                "Buy one from `/farm shop` for 500 🌾",
                ephemeral=True
            )
            return
        
        # Show breeding options
        embed = discord.Embed(
            title="🧬 Crop Breeding Lab",
            description="**Available Hybrids:**\n\n"
                       "Combine two parent crops to create rare hybrids!\n"
                       "Each breeding costs 5 of each parent crop.\n\n",
            color=discord.Color.purple()
        )
        
        for hybrid_name, hybrid_data in self.rare_crops.items():
            parent1, parent2 = hybrid_data["parents"]
            p1_name = self.crops[parent1]["name"]
            p2_name = self.crops[parent2]["name"]
            
            # Check if user has enough
            p1_count = farm["inventory"].get(parent1, 0)
            p2_count = farm["inventory"].get(parent2, 0)
            
            status = "✅ Ready!" if p1_count >= 5 and p2_count >= 5 else "❌ Not enough"
            
            embed.add_field(
                name=f"{hybrid_data['name']} {hybrid_data['emoji']}",
                value=f"{p1_name} ({p1_count}/5) + {p2_name} ({p2_count}/5)\n"
                      f"Value: {hybrid_data['sell_price']} | {status}",
                inline=False
            )
        
        embed.set_footer(text="Reply with the hybrid name to breed (e.g., 'golden_wheat')")
        await interaction.response.send_message(embed=embed)
        
        def check_msg(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        try:
            msg = await self.bot.wait_for('message', check=check_msg, timeout=30.0)
            hybrid_choice = msg.content.lower()
            
            if hybrid_choice not in self.rare_crops:
                await interaction.followup.send("❌ Invalid hybrid name!", ephemeral=True)
                return
            
            hybrid_data = self.rare_crops[hybrid_choice]
            parent1, parent2 = hybrid_data["parents"]
            
            # Check inventory
            if farm["inventory"].get(parent1, 0) < 5 or farm["inventory"].get(parent2, 0) < 5:
                await interaction.followup.send("❌ Not enough parent crops!", ephemeral=True)
                return
            
            # Consume parents
            farm["inventory"][parent1] -= 5
            farm["inventory"][parent2] -= 5
            
            # Add hybrid
            farm["inventory"][hybrid_choice] = farm["inventory"].get(hybrid_choice, 0) + 1
            
            # Track breeding pairs
            farm.setdefault("breeding_pairs", []).append({
                "parents": [parent1, parent2],
                "result": hybrid_choice,
                "timestamp": discord.utils.utcnow().isoformat()
            })
            
            # Check achievement
            unlocked, achievement = self.check_achievement(interaction.user.id, "hybrid_creator")
            achievement_msg = ""
            if unlocked:
                achievement_msg = f"\n\n🏆 **{achievement['name']}** unlocked! +{achievement['reward']} 🌾"
            
            self.save_data()
            
            await interaction.followup.send(
                f"🧬 **Breeding Success!**\n\n"
                f"You created: **{hybrid_data['name']}** {hybrid_data['emoji']}\n"
                f"Value: {hybrid_data['sell_price']} PsyCoins"
                f"{achievement_msg}"
            )
        
        except Exception as e:
            await interaction.followup.send("❌ Breeding cancelled or timed out.", ephemeral=True)
    
    async def farm_decorate_action(self, interaction: discord.Interaction):
        """Place decorations to increase farm beauty"""
        farm = self.get_farm(interaction.user.id)
        
        # Show available decorations
        embed = discord.Embed(
            title="✨ Farm Decorations",
            description=f"**Current Beauty Points:** {farm.get('beauty_points', 0)}\n\n"
                       "Decorations increase your farm's beauty and provide bonuses!\n\n"
                       "**Available Decorations:**\n",
            color=discord.Color.from_rgb(255, 105, 180)
        )
        
        for deco_name, deco_data in self.decorations.items():
            owned = farm.get("decorations", {}).get(deco_name, 0)
            embed.add_field(
                name=f"{deco_data['name']}",
                value=f"Cost: {deco_data['cost']} 🌾 | Beauty: +{deco_data['beauty']}\n"
                      f"Owned: {owned}",
                inline=True
            )
        
        embed.set_footer(text="Reply with decoration name to buy (e.g., 'fence')")
        await interaction.response.send_message(embed=embed)
        
        # Get farm tokens
        economy_cog = self.bot.get_cog("Economy")
        farm_tokens = 0
        if economy_cog:
            user_id = str(interaction.user.id)
            if user_id in economy_cog.economy_data:
                farm_tokens = economy_cog.economy_data[user_id].get("farm_tokens", 0)
        
        def check_msg(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        try:
            msg = await self.bot.wait_for('message', check=check_msg, timeout=30.0)
            deco_choice = msg.content.lower()
            
            if deco_choice not in self.decorations:
                await interaction.followup.send("❌ Invalid decoration!", ephemeral=True)
                return
            
            deco_data = self.decorations[deco_choice]
            cost = deco_data["cost"]
            
            if farm_tokens < cost:
                await interaction.followup.send(f"❌ Not enough Farm Tokens! Need {cost} 🌾", ephemeral=True)
                return
            
            # Deduct tokens
            if economy_cog:
                economy_cog.economy_data[user_id]["farm_tokens"] -= cost
                economy_cog.economy_dirty = True
                await economy_cog.save_economy()
            
            # Add decoration
            farm.setdefault("decorations", {})[deco_choice] = farm.get("decorations", {}).get(deco_choice, 0) + 1
            farm["beauty_points"] = farm.get("beauty_points", 0) + deco_data["beauty"]
            
            # Check achievement
            unlocked, achievement = self.check_achievement(interaction.user.id, "beautiful_farm")
            achievement_msg = ""
            if unlocked:
                achievement_msg = f"\n\n🏆 **{achievement['name']}** unlocked! +{achievement['reward']} 🌾"
            
            self.save_data()
            
            await interaction.followup.send(
                f"✨ **Decoration Placed!**\n\n"
                f"{deco_data['name']}\n"
                f"Beauty: +{deco_data['beauty']} (Total: {farm['beauty_points']})"
                f"{achievement_msg}"
            )
        
        except Exception as e:
            await interaction.followup.send("❌ Purchase cancelled or timed out.", ephemeral=True)
    
    async def farm_quest_action(self, interaction: discord.Interaction):
        """View daily quest and claim reward"""
        farm = self.get_farm(interaction.user.id)
        self.check_daily_reset(farm)
        
        quest_id = farm.get("daily_quest")
        if not quest_id:
            await interaction.response.send_message("❌ No daily quest available!", ephemeral=True)
            return
        
        quest_data = self.daily_quests[quest_id]
        progress = farm.get("quest_progress", 0)
        target = quest_data.get("requirement", quest_data.get("target", 1))
        reward = quest_data["reward"]
        
        # Check if complete
        if progress >= target:
            # Give reward
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                user_id = str(interaction.user.id)
                if user_id not in economy_cog.economy_data:
                    economy_cog.economy_data[user_id] = {"balance": 0, "farm_tokens": 0}
                
                economy_cog.economy_data[user_id]["farm_tokens"] = economy_cog.economy_data[user_id].get("farm_tokens", 0) + reward
                economy_cog.economy_dirty = True
                await economy_cog.save_economy()
            
            # Reset quest
            farm["daily_quest"] = None
            farm["quest_progress"] = 0
            self.save_data()
            
            embed = discord.Embed(
                title="🎉 Quest Complete!",
                description=f"**{quest_data.get('description', quest_data.get('name', '?'))}**\n\n"
                           f"Progress: {progress}/{target} ✅\n"
                           f"Reward: +{reward} 🌾 Farm Tokens!",
                color=discord.Color.gold()
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            # Show progress
            embed = discord.Embed(
                title="📋 Daily Quest",
                description=f"**{quest_data.get('description', quest_data.get('name', '?'))}**\n\n"
                           f"Progress: {progress}/{target}\n"
                           f"Reward: {reward} 🌾 Farm Tokens",
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed)
    
    async def farm_market_action(self, interaction: discord.Interaction):
        """View dynamic market prices"""
        farm = self.get_farm(interaction.user.id)
        
        embed = discord.Embed(
            title="📊 Farm Market Prices",
            description="Current market conditions affect crop prices!\n\n",
            color=discord.Color.blue()
        )
        
        for crop_name, crop_data in self.crops.items():
            base_price = crop_data["sell_price"]
            current_price, market_status = self.get_market_price(crop_name, base_price, farm)
            
            status_emoji = {
                "high_demand": "📈",
                "normal": "➡️",
                "low_demand": "📉",
                "shortage": "🚨"
            }
            
            status_names = {
                "high_demand": "High Demand (+50%)",
                "normal": "Normal",
                "low_demand": "Low Demand (-30%)",
                "shortage": "Shortage! (+100%)"
            }
            
            embed.add_field(
                name=f"{crop_data['name']} {status_emoji.get(market_status, '➡️')}",
                value=f"{base_price} → **{current_price}** coins\n{status_names.get(market_status, 'Normal')}",
                inline=True
            )
        
        embed.set_footer(text="Market prices change every 6 hours!")
        await interaction.response.send_message(embed=embed)
    
    async def farm_achievements_action(self, interaction: discord.Interaction):
        """View farm achievements"""
        farm = self.get_farm(interaction.user.id)
        earned = farm.get("achievements", [])
        
        embed = discord.Embed(
            title="🏆 Farm Achievements",
            description=f"**Progress: {len(earned)}/7**\n\n",
            color=discord.Color.gold()
        )
        
        for achievement_id, achievement_data in self.achievements.items():
            status = "✅" if achievement_id in earned else "🔒"
            embed.add_field(
                name=f"{status} {achievement_data['name']}",
                value=f"{achievement_data.get('description', achievement_data.get('desc', '?'))}\n"
                      f"Reward: {achievement_data['reward']} 🌾",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    # Ice Cream Maker
    @app_commands.command(name="icecream", description="Build a custom ice cream sundae!")
    async def ice_cream_maker(self, interaction: discord.Interaction):
        """Ice cream sundae maker"""
        sundae = {
            "base": None,
            "toppings": [],
            "sauce": None
        }
        
        embed = discord.Embed(
            title="🍦 Ice Cream Sundae Maker",
            description="**Build your perfect sundae!**\n\n"
                       "**Step 1:** Choose your base\nReact with 1️⃣-5️⃣",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        
        for i, base in enumerate(self.ice_cream_bases[:5]):
            embed.add_field(name=f"{i+1}️⃣", value=base, inline=True)
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        # Step 1: Choose base
        for i in range(min(5, len(self.ice_cream_bases))):
            await msg.add_reaction(f"{i+1}️⃣")
        
        def check_number(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4}
            sundae["base"] = self.ice_cream_bases[emoji_to_num[str(reaction.emoji)]]
            
            # Step 2: Choose toppings
            embed = discord.Embed(
                title="🍦 Ice Cream Sundae Maker",
                description=f"**Base:** {sundae['base']}\n\n"
                           "**Step 2:** Add toppings (click up to 3)\nReact when done: ✅",
                color=discord.Color.from_rgb(255, 192, 203)
            )
            
            for i, topping in enumerate(self.ice_cream_toppings[:8]):
                embed.add_field(name=f"{i+1}️⃣", value=topping, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(min(8, len(self.ice_cream_toppings))):
                await msg.add_reaction(f"{i+1}️⃣")
            await msg.add_reaction("✅")
            
            def check_topping(reaction, user):
                return user.id == interaction.user.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "✅"]
            
            while len(sundae["toppings"]) < 3:
                reaction, user = await self.bot.wait_for('reaction_add', check=check_topping, timeout=45.0)
                
                if str(reaction.emoji) == "✅":
                    break
                
                emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4, "6️⃣": 5, "7️⃣": 6, "8️⃣": 7}
                topping = self.ice_cream_toppings[emoji_to_num[str(reaction.emoji)]]
                
                if topping not in sundae["toppings"]:
                    sundae["toppings"].append(topping)
                    await interaction.followup.send(f"Added {topping}!", ephemeral=True)
                
                if len(sundae["toppings"]) >= 3:
                    break
            
            # Step 3: Choose sauce
            embed = discord.Embed(
                title="🍦 Ice Cream Sundae Maker",
                description=f"**Base:** {sundae['base']}\n"
                           f"**Toppings:** {', '.join(sundae['toppings']) if sundae['toppings'] else 'None'}\n\n"
                           "**Step 3:** Choose your sauce\nReact with 1️⃣-4️⃣",
                color=discord.Color.from_rgb(255, 192, 203)
            )
            
            for i, sauce in enumerate(self.ice_cream_sauces):
                embed.add_field(name=f"{i+1}️⃣", value=sauce, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.ice_cream_sauces)):
                await msg.add_reaction(f"{i+1}️⃣")
            
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            sundae["sauce"] = self.ice_cream_sauces[emoji_to_num[str(reaction.emoji)]]
            
            # Final result
            value = 50 + (len(sundae["toppings"]) * 25)
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(interaction.user.id, value, "ice_cream_sundae")
            
            embed = discord.Embed(
                title="🎉 Sundae Complete!",
                description=f"**Your Perfect Sundae:**\n\n"
                           f"🍦 Base: {sundae['base']}\n"
                           f"🍓 Toppings: {', '.join(sundae['toppings']) if sundae['toppings'] else 'None'}\n"
                           f"🍯 Sauce: {sundae['sauce']}\n\n"
                           f"**Deliciousness Rating:** {'⭐' * (3 + len(sundae['toppings']))}\n\n"
                           f"**+{value} PsyCoins!**",
                color=discord.Color.gold()
            )
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
        except asyncio.TimeoutError:
            await msg.edit(content="⏰ Time's up! Sundae melted...", embed=None)
            await msg.clear_reactions()

async def setup(bot):
    await bot.add_cog(Simulations(bot))
