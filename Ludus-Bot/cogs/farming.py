import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import os
from datetime import datetime, timedelta
import random
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class FarmingManager:
    """Manages farming system with crops, harvesting, and seasons"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.farms_file = os.path.join(data_dir, "farms.json")
        self.seeds_file = os.path.join(data_dir, "seeds.json")
        self.seeds = self.load_seeds()
        self.farms = self.load_farms()
        
        # Crop definitions with growth times and values
        self.crops = {
            "wheat": {
                "name": "Wheat",
                "emoji": "🌾",
                "grow_time": 30,  # minutes
                "seed_cost": 10,
                "sell_price": 25,
                "xp": 5,
                "season": "all",
                "energy_cost": 5
            },
            "corn": {
                "name": "Corn",
                "emoji": "🌽",
                "grow_time": 45,
                "seed_cost": 15,
                "sell_price": 40,
                "xp": 8,
                "season": "summer",
                "energy_cost": 7
            },
            "tomato": {
                "name": "Tomato",
                "emoji": "🍅",
                "grow_time": 60,
                "seed_cost": 20,
                "sell_price": 55,
                "xp": 10,
                "season": "spring",
                "energy_cost": 8
            },
            "carrot": {
                "name": "Carrot",
                "emoji": "🥕",
                "grow_time": 25,
                "seed_cost": 8,
                "sell_price": 20,
                "xp": 4,
                "season": "fall",
                "energy_cost": 4
            },
            "potato": {
                "name": "Potato",
                "emoji": "🥔",
                "grow_time": 40,
                "seed_cost": 12,
                "sell_price": 30,
                "xp": 6,
                "season": "all",
                "energy_cost": 6
            },
            "pumpkin": {
                "name": "Pumpkin",
                "emoji": "🎃",
                "grow_time": 120,
                "seed_cost": 50,
                "sell_price": 150,
                "xp": 25,
                "season": "fall",
                "energy_cost": 15
            },
            "strawberry": {
                "name": "Strawberry",
                "emoji": "🍓",
                "grow_time": 35,
                "seed_cost": 18,
                "sell_price": 45,
                "xp": 7,
                "season": "spring",
                "energy_cost": 7
            },
            "watermelon": {
                "name": "Watermelon",
                "emoji": "🍉",
                "grow_time": 90,
                "seed_cost": 35,
                "sell_price": 100,
                "xp": 18,
                "season": "summer",
                "energy_cost": 12
            },
            "lettuce": {
                "name": "Lettuce",
                "emoji": "🥬",
                "grow_time": 20,
                "seed_cost": 6,
                "sell_price": 15,
                "xp": 3,
                "season": "all",
                "energy_cost": 3
            },
            "eggplant": {
                "name": "Eggplant",
                "emoji": "🍆",
                "grow_time": 70,
                "seed_cost": 28,
                "sell_price": 75,
                "xp": 14,
                "season": "summer",
                "energy_cost": 10
            }
        }
    
    def load_farms(self):
        """Load farms from JSON"""
        if os.path.exists(self.farms_file):
            try:
                with open(self.farms_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def load_seeds(self):
        """Load seeds inventory per user"""
        if os.path.exists(self.seeds_file):
            try:
                with open(self.seeds_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_seeds(self):
        try:
            with open(self.seeds_file, 'w') as f:
                json.dump(self.seeds, f, indent=4)
        except Exception as e:
            print(f"Error saving seeds: {e}")

    def get_seed_count(self, user_id, crop_id):
        user_key = str(user_id)
        user_seeds = self.seeds.get(user_key, {})
        return user_seeds.get(crop_id, 0)

    def add_seeds(self, user_id, crop_id, quantity=1):
        user_key = str(user_id)
        if user_key not in self.seeds:
            self.seeds[user_key] = {}
        self.seeds[user_key][crop_id] = self.seeds[user_key].get(crop_id, 0) + quantity
        self.save_seeds()

    def remove_seeds(self, user_id, crop_id, quantity=1):
        user_key = str(user_id)
        if user_key not in self.seeds or self.seeds[user_key].get(crop_id, 0) < quantity:
            return False
        self.seeds[user_key][crop_id] -= quantity
        if self.seeds[user_key][crop_id] <= 0:
            del self.seeds[user_key][crop_id]
        self.save_seeds()
        return True
    
    def save_farms(self):
        """Save farms to JSON"""
        try:
            with open(self.farms_file, 'w') as f:
                json.dump(self.farms, f, indent=4)
        except Exception as e:
            print(f"Error saving farms: {e}")
    
    def get_farm(self, user_id):
        """Get or create user's farm"""
        user_id = str(user_id)
        if user_id not in self.farms:
            self.farms[user_id] = {
                "plots": 4,  # Starting plots
                "max_plots": 20,  # Max upgradeable
                "farming_level": 1,
                "farming_xp": 0,
                "crops_planted": {},  # plot_id: {crop, planted_at}
                "total_harvested": 0,
                "crops_harvested": {},  # crop_name: count
                "upgrades": {
                    "sprinkler": False,  # Reduces grow time 20%
                    "fertilizer": False,  # +50% sell price
                    "greenhouse": False   # All-season crops
                }
            }
            self.save_farms()
        return self.farms[user_id]
    
    def get_current_season(self):
        """Get current season based on month"""
        month = datetime.utcnow().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "fall"
        else:
            return "winter"
    
    def can_plant_crop(self, crop_id, season, has_greenhouse):
        """Check if crop can be planted in current season"""
        crop = self.crops.get(crop_id)
        if not crop:
            return False
        
        if crop["season"] == "all":
            return True
        
        if has_greenhouse:
            return True
        
        return crop["season"] == season
    
    def plant_crop(self, user_id, plot_id, crop_id):
        """Plant a crop on a plot"""
        farm = self.get_farm(user_id)
        
        if plot_id >= farm["plots"]:
            return False, "You don't have that many plots!"
        
        if str(plot_id) in farm["crops_planted"]:
            return False, "That plot is already planted!"
        
        crop = self.crops.get(crop_id)
        if not crop:
            return False, "Invalid crop!"

        # Check seed availability
        seed_count = self.get_seed_count(user_id, crop_id)
        if seed_count <= 0:
            return False, f"You don't have any seeds for {crop['name']}. Buy seeds from the farm shop first!"
        
        season = self.get_current_season()
        if not self.can_plant_crop(crop_id, season, farm["upgrades"]["greenhouse"]):
            return False, f"{crop['name']} can't be planted in {season}!"
        
        # Plant the crop
        farm["crops_planted"][str(plot_id)] = {
            "crop_id": crop_id,
            "planted_at": datetime.utcnow().isoformat(),
            "ready_at": (datetime.utcnow() + timedelta(minutes=crop["grow_time"])).isoformat()
        }

        # Consume one seed
        self.remove_seeds(user_id, crop_id, 1)
        
        self.save_farms()
        return True, f"Planted {crop['emoji']} {crop['name']}!"
    
    def harvest_crop(self, user_id, plot_id):
        """Harvest a ready crop"""
        farm = self.get_farm(user_id)
        
        if str(plot_id) not in farm["crops_planted"]:
            return False, "Nothing planted there!", None
        
        plant_data = farm["crops_planted"][str(plot_id)]
        ready_time = datetime.fromisoformat(plant_data["ready_at"])
        
        if datetime.utcnow() < ready_time:
            time_left = ready_time - datetime.utcnow()
            minutes = int(time_left.total_seconds() / 60)
            return False, f"Not ready yet! {minutes} minutes remaining.", None
        
        crop = self.crops[plant_data["crop_id"]]
        
        # Calculate value with upgrades
        value = crop["sell_price"]
        if farm["upgrades"]["fertilizer"]:
            value = int(value * 1.5)
        
        # Random bonus yield (10% chance for double)
        quantity = 2 if random.random() < 0.1 else 1
        total_value = value * quantity
        
        # Update stats
        farm["total_harvested"] += quantity
        if crop["name"] not in farm["crops_harvested"]:
            farm["crops_harvested"][crop["name"]] = 0
        farm["crops_harvested"][crop["name"]] += quantity
        
        farm["farming_xp"] += crop["xp"] * quantity
        
        # Check level up
        level_up = False
        xp_needed = farm["farming_level"] * 100
        if farm["farming_xp"] >= xp_needed:
            farm["farming_level"] += 1
            farm["farming_xp"] -= xp_needed
            level_up = True
        
        # Remove crop from plot
        del farm["crops_planted"][str(plot_id)]
        
        self.save_farms()
        
        return True, {
            "crop": crop,
            "quantity": quantity,
            "value": total_value,
            "xp": crop["xp"] * quantity,
            "level_up": level_up,
            "new_level": farm["farming_level"] if level_up else None
        }, total_value
    
    def get_plot_status(self, user_id):
        """Get status of all plots"""
        farm = self.get_farm(user_id)
        plots = []
        
        for i in range(farm["plots"]):
            if str(i) in farm["crops_planted"]:
                plant_data = farm["crops_planted"][str(i)]
                crop = self.crops[plant_data["crop_id"]]
                ready_time = datetime.fromisoformat(plant_data["ready_at"])
                
                if datetime.utcnow() >= ready_time:
                    status = "ready"
                    time_info = "Ready to harvest!"
                else:
                    status = "growing"
                    time_left = ready_time - datetime.utcnow()
                    minutes = int(time_left.total_seconds() / 60)
                    time_info = f"{minutes}m remaining"
                
                plots.append({
                    "plot_id": i,
                    "status": status,
                    "crop": crop,
                    "time_info": time_info
                })
            else:
                plots.append({
                    "plot_id": i,
                    "status": "empty",
                    "crop": None,
                    "time_info": "Empty plot"
                })
        
        return plots
    
    def upgrade_farm(self, user_id, upgrade_type):
        """Upgrade farm"""
        farm = self.get_farm(user_id)
        
        upgrade_costs = {
            "plot": 500,  # Add 1 plot
            "sprinkler": 2000,  # Reduce grow time 20%
            "fertilizer": 3000,  # +50% sell price
            "greenhouse": 5000   # All-season crops
        }
        
        if upgrade_type == "plot":
            if farm["plots"] >= farm["max_plots"]:
                return False, "Maximum plots reached!", 0
            
            cost = upgrade_costs["plot"] * (farm["plots"] - 3)  # Gets more expensive
            farm["plots"] += 1
            self.save_farms()
            return True, f"Added a new plot! Now have {farm['plots']} plots.", cost
        
        elif upgrade_type in upgrade_costs:
            if farm["upgrades"].get(upgrade_type):
                return False, "Already have this upgrade!", 0
            
            cost = upgrade_costs[upgrade_type]
            farm["upgrades"][upgrade_type] = True
            self.save_farms()
            return True, f"Purchased {upgrade_type} upgrade!", cost
        
        return False, "Invalid upgrade!", 0

class FarmView(View):
    def __init__(self, ctx, manager, farm):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.manager = manager
        self.farm = farm
        
        # Add harvest all button if any crops are ready
        plots = manager.get_plot_status(ctx.author.id)
        if any(p["status"] == "ready" for p in plots):
            harvest_button = Button(label="Harvest All", style=discord.ButtonStyle.success, emoji="🌾")
            harvest_button.callback = self.harvest_all_callback
            self.add_item(harvest_button)
    
    async def harvest_all_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This farm isn't yours!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Harvest all ready crops
        plots = self.manager.get_plot_status(self.ctx.author.id)
        harvested = []
        total_value = 0
        
        for plot in plots:
            if plot["status"] == "ready":
                success, result, value = self.manager.harvest_crop(self.ctx.author.id, plot["plot_id"])
                if success:
                    harvested.append(result)
                    total_value += value
        
        if not harvested:
            await interaction.followup.send("No crops ready to harvest!")
            return
        
        # Create harvest summary
        summary = ""
        for h in harvested:
            summary += f"{h['crop']['emoji']} {h['quantity']}x {h['crop']['name']} (+{h['value']} coins)\n"
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.SUCCESS} Harvest Complete!",
            description=f"**Harvested {len(harvested)} crops!**\n\n{summary}\n"
                       f"💰 **Total Value:** {total_value} PsyCoins\n"
                       f"⭐ **Total XP:** {sum(h['xp'] for h in harvested)}",
            color=Colors.SUCCESS
        )
        
        await interaction.followup.send(embed=embed)
        # Award PsyCoins for the harvested value via Economy cog
        economy_cog = self.manager and getattr(self.manager, 'data_dir', None) and self.manager
        # Use bot economy cog instead
        try:
            econ = self.ctx.bot.get_cog("Economy")
            if econ:
                econ.add_coins(self.ctx.author.id, total_value, "farming")
        except Exception:
            pass

class Farming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = FarmingManager(data_dir)
        self.inventory_file = os.path.join(data_dir, "inventory.json")
        self.profile_file = os.path.join(data_dir, "profiles.json")
    
    # Economy is handled via the central Economy cog; file fallbacks are performed inline where needed.
    
    def load_profile(self):
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_profile(self, data):
        try:
            with open(self.profile_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving profile: {e}")
    
    @commands.command(name="farm")
    async def farm_command(self, ctx):
        """View your farm"""
        farm = self.manager.get_farm(ctx.author.id)
        plots = self.manager.get_plot_status(ctx.author.id)
        season = self.manager.get_current_season()
        
        # Build plot display
        plot_text = ""
        for plot in plots:
            if plot["status"] == "empty":
                plot_text += f"**Plot {plot['plot_id']+1}:** 🟫 Empty\n"
            elif plot["status"] == "growing":
                plot_text += f"**Plot {plot['plot_id']+1}:** {plot['crop']['emoji']} {plot['crop']['name']} - {plot['time_info']}\n"
            elif plot["status"] == "ready":
                plot_text += f"**Plot {plot['plot_id']+1}:** ✨ {plot['crop']['emoji']} {plot['crop']['name']} - **READY!**\n"
        
        # Upgrades
        upgrades_text = ""
        if farm["upgrades"]["sprinkler"]:
            upgrades_text += "💧 Sprinkler (-20% grow time)\n"
        if farm["upgrades"]["fertilizer"]:
            upgrades_text += "💩 Fertilizer (+50% sell price)\n"
        if farm["upgrades"]["greenhouse"]:
            upgrades_text += "🏠 Greenhouse (All-season crops)\n"
        if not upgrades_text:
            upgrades_text = "*No upgrades*"
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} {ctx.author.display_name}'s Farm",
            description=f"**Level {farm['farming_level']}** Farmer\n"
                       f"**Season:** {season.capitalize()} {self._get_season_emoji(season)}\n"
                       f"**XP:** {farm['farming_xp']}/{farm['farming_level']*100}\n"
                       f"**Total Harvested:** {farm['total_harvested']} crops\n\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"{plot_text}\n"
                       f"**Upgrades:**\n{upgrades_text}",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="Commands",
            value="`L!plant <crop> <plot>` - Plant seeds\n"
                  "`L!harvest <plot>` - Harvest crop\n"
                  "`L!seeds` - View available seeds\n"
                  "`L!farmupgrade` - Upgrade farm",
            inline=False
        )
        
        view = FarmView(ctx, self.manager, farm)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="seeds")
    async def seeds_command(self, ctx):
        """View available seeds"""
        season = self.manager.get_current_season()
        farm = self.manager.get_farm(ctx.author.id)
        embed = EmbedBuilder.create(
            title=f"{Emojis.TREASURE} Available Seeds",
            description=f"**Current Season:** {season.capitalize()} {self._get_season_emoji(season)}\n"
                       "Purchase seeds with `/farmshop action:buyseed`\n\n",
            color=Colors.PRIMARY
        )

        # Show user's seed inventory counts alongside seed info
        for crop_id, crop in self.manager.crops.items():
            can_plant = self.manager.can_plant_crop(crop_id, season, farm["upgrades"]["greenhouse"])
            status = "✅" if can_plant else "❌"
            seed_count = self.manager.get_seed_count(ctx.author.id, crop_id)

            embed.add_field(
                name=f"{status} {crop['emoji']} {crop['name']}",
                value=f"**Seeds Owned:** {seed_count} | **Grow Time:** {crop['grow_time']}m\n"
                      f"**Seed Cost:** {crop['seed_cost']} coins | **Sell Price:** {crop['sell_price']} coins\n"
                      f"**Season:** {crop['season'].capitalize()}",
                inline=True
            )

        await ctx.send(embed=embed)
    
    @commands.command(name="plant")
    async def plant_command(self, ctx, crop: str, plot: int = 0):
        """Plant a crop"""
        # Check profile for energy
        profiles = self.load_profile()
        user_id = str(ctx.author.id)
        
        if user_id in profiles:
            profile = profiles[user_id]
            crop_data = self.manager.crops.get(crop.lower())
            if crop_data:
                if profile['energy'] < crop_data['energy_cost']:
                    await ctx.send(f"❌ Not enough energy! Need {crop_data['energy_cost']}, have {profile['energy']}.")
                    return
                
                profile['energy'] -= crop_data['energy_cost']
                self.save_profile(profiles)
        
        success, message = self.manager.plant_crop(ctx.author.id, plot, crop.lower())
        
        if success:
            crop_data = self.manager.crops[crop.lower()]
            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Planted!",
                description=f"{crop_data['emoji']} **{crop_data['name']}** planted on plot {plot+1}!\n\n"
                           f"⏱️ Ready in: **{crop_data['grow_time']} minutes**\n"
                           f"⚡ Energy used: {crop_data['energy_cost']}\n"
                           f"💰 Sell price: {crop_data['sell_price']} coins",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
            # Update most played games
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "profile_manager"):
                profile_cog.profile_manager.record_game_played(ctx.author.id, "farming")
        else:
            await ctx.send(f"❌ {message}")
    
    @commands.command(name="harvest")
    async def harvest_command(self, ctx, plot: int = None):
        """Harvest a crop"""
        if plot is None:
            await ctx.send("❌ Specify a plot number! Example: `L!harvest 1`")
            return
        
        success, result, value = self.manager.harvest_crop(ctx.author.id, plot - 1)
        
        if not success:
            await ctx.send(f"❌ {result}")
            return
        
        # Award PsyCoins via Economy cog
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            try:
                economy_cog.add_coins(ctx.author.id, value, "farming")
            except Exception:
                pass

        # Update profile
        profiles = self.load_profile()
        user_id = str(ctx.author.id)
        if user_id in profiles:
            profiles[user_id]["crops_harvested"] = profiles[user_id].get("crops_harvested", 0) + result["quantity"]
            self.save_profile(profiles)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.SUCCESS} Harvest Complete!",
            description=f"Harvested **{result['quantity']}x {result['crop']['emoji']} {result['crop']['name']}**!\n\n"
                       f"💰 Earned: **{value} PsyCoins**\n"
                       f"⭐ XP: **+{result['xp']}**",
            color=Colors.SUCCESS
        )
        
        if result["level_up"]:
            embed.add_field(
                name=f"{Emojis.LEVEL_UP} Level Up!",
                value=f"Farming Level **{result['new_level']}**!",
                inline=False
            )
        
        await ctx.send(embed=embed)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "farming")
        # Chance to award a TCG card for simulation category (farming)
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(ctx.author.id), 'simulation')
                if awarded:
                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                    embed.add_field(name='🎴 Bonus Card Reward', value=', '.join(names), inline=False)
                    # edit the previous message to include the reward (if using ctx.send earlier, we can send a follow-up)
                    await ctx.send(f"You received TCG card(s): {', '.join(names)}")
            except Exception:
                pass
    
    @commands.command(name="farmupgrade", aliases=["farmup"])
    async def farmupgrade_command(self, ctx):
        """View and purchase farm upgrades"""
        farm = self.manager.get_farm(ctx.author.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TOOLS} Farm Upgrades",
            description="Enhance your farming experience!\n\n",
            color=Colors.WARNING
        )
        
        # Plot upgrade
        if farm["plots"] < farm["max_plots"]:
            cost = 500 * (farm["plots"] - 3)
            embed.add_field(
                name="🟫 Additional Plot",
                value=f"**Cost:** {cost} coins\n"
                      f"**Current:** {farm['plots']}/{farm['max_plots']}\n"
                      f"`L!buyupgrade plot`",
                inline=True
            )
        
        # Sprinkler
        if not farm["upgrades"]["sprinkler"]:
            embed.add_field(
                name="💧 Sprinkler System",
                value=f"**Cost:** 2,000 coins\n"
                      f"Reduces grow time by 20%\n"
                      f"`L!buyupgrade sprinkler`",
                inline=True
            )
        
        # Fertilizer
        if not farm["upgrades"]["fertilizer"]:
            embed.add_field(
                name="💩 Premium Fertilizer",
                value=f"**Cost:** 3,000 coins\n"
                      f"+50% crop sell price\n"
                      f"`L!buyupgrade fertilizer`",
                inline=True
            )
        
        # Greenhouse
        if not farm["upgrades"]["greenhouse"]:
            embed.add_field(
                name="🏠 Greenhouse",
                value=f"**Cost:** 5,000 coins\n"
                      f"Grow all crops year-round\n"
                      f"`L!buyupgrade greenhouse`",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="buyupgrade")
    async def buyupgrade_command(self, ctx, upgrade_type: str):
        """Purchase a farm upgrade"""
        success, message, cost = self.manager.upgrade_farm(ctx.author.id, upgrade_type.lower())
        
        if not success:
            await ctx.send(f"❌ {message}")
            return
        
        # Deduct coins via Economy cog
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            balance = economy_cog.get_balance(ctx.author.id)
            if balance < cost:
                await ctx.send(f"❌ Not enough coins! Need {cost}, have {balance}.")
                return
            economy_cog.remove_coins(ctx.author.id, cost)
        else:
            # Fallback to local economy file
            economy_file = os.path.join(self.manager.data_dir, "economy.json")
            economy = {}
            if os.path.exists(economy_file):
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}

            user_id = str(ctx.author.id)
            if user_id not in economy:
                economy[user_id] = {"balance": 0}
            if economy[user_id]["balance"] < cost:
                await ctx.send(f"❌ Not enough coins! Need {cost}, have {economy[user_id]['balance']}.")
                return
            economy[user_id]["balance"] -= cost
            try:
                with open(economy_file, 'w') as f:
                    json.dump(economy, f, indent=4)
            except Exception:
                pass
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.SUCCESS} Upgrade Purchased!",
            description=f"{message}\n\n💰 Cost: **{cost} PsyCoins**",
            color=Colors.SUCCESS
        )
        await ctx.send(embed=embed)
    
    def _get_season_emoji(self, season):
        emojis = {
            "spring": "🌸",
            "summer": "☀️",
            "fall": "🍂",
            "winter": "❄️"
        }
        return emojis.get(season, "🌍")

async def setup(bot):
    await bot.add_cog(Farming(bot))
