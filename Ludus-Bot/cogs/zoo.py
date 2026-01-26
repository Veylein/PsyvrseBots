import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
from typing import Optional
from datetime import datetime

class Zoo(commands.Cog):
    """Zoo System - Collect wild animals found during minigames!"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.zoo_data_file = os.path.join(data_dir, "zoo_data.json")
        self.zoo_data = self.load_zoo_data()
        
        # Animal encounters by minigame/activity
        self.animals_by_source = {
            "monopoly": {
                "common": [
                    {"name": "🦌 Buck", "rarity": "Common", "description": "A majestic deer, the symbol of wealth"},
                    {"name": "🐕 Dog", "rarity": "Common", "description": "Man's best friend and loyal companion"},
                    {"name": "🐈 Cat", "rarity": "Common", "description": "Independent and graceful feline"},
                    {"name": "🐎 Horse", "rarity": "Common", "description": "Swift and noble steed"},
                ],
                "rare": [
                    {"name": "🦅 Eagle", "rarity": "Rare", "description": "Soaring symbol of freedom"},
                    {"name": "🦊 Fox", "rarity": "Rare", "description": "Cunning and clever predator"},
                ],
                "legendary": [
                    {"name": "👑 Royal Peacock", "rarity": "Legendary", "description": "Magnificent bird of luxury"},
                ]
            },
            "wizard_wars": {
                "common": [
                    {"name": "👺 Goblin", "rarity": "Common", "description": "Mischievous magical creature"},
                    {"name": "🧚 Fairy", "rarity": "Common", "description": "Tiny magical sprite"},
                    {"name": "🦇 Bat", "rarity": "Common", "description": "Nocturnal cave dweller"},
                ],
                "rare": [
                    {"name": "🧙 Wizard Owl", "rarity": "Rare", "description": "Wise magical companion"},
                    {"name": "🐺 Dire Wolf", "rarity": "Rare", "description": "Fierce magical beast"},
                ],
                "legendary": [
                    {"name": "🐉 Dragon", "rarity": "Legendary", "description": "Legendary fire-breathing beast"},
                    {"name": "🦄 Unicorn", "rarity": "Legendary", "description": "Pure magical horse"},
                ]
            },
            "dnd": {
                "common": [
                    {"name": "🐀 Giant Rat", "rarity": "Common", "description": "Dungeon pest"},
                    {"name": "🕷️ Giant Spider", "rarity": "Common", "description": "Eight-legged horror"},
                ],
                "rare": [
                    {"name": "🐉 Wyvern", "rarity": "Rare", "description": "Lesser dragon cousin"},
                    {"name": "🦎 Basilisk", "rarity": "Rare", "description": "Deadly serpent king"},
                ],
                "legendary": [
                    {"name": "🐲 Ancient Dragon", "rarity": "Legendary", "description": "Most powerful dragon"},
                    {"name": "👹 Demon", "rarity": "Legendary", "description": "Otherworldly fiend"},
                ]
            },
            "mystery": {
                "common": [
                    {"name": "🐦‍⬛ Raven", "rarity": "Common", "description": "Mysterious black bird"},
                    {"name": "🐱 Black Cat", "rarity": "Common", "description": "Ominous feline"},
                ],
                "rare": [
                    {"name": "🦉 Owl", "rarity": "Rare", "description": "Wise night hunter"},
                ],
                "legendary": [
                    {"name": "🕵️ Phantom Hound", "rarity": "Legendary", "description": "Ghostly detective's companion"},
                ]
            },
            "gambling": {
                "common": [
                    {"name": "🐰 Lucky Rabbit", "rarity": "Common", "description": "Brings good fortune"},
                    {"name": "🐸 Golden Frog", "rarity": "Common", "description": "Symbol of prosperity"},
                ],
                "rare": [
                    {"name": "🍀 Four-Leaf Clover Cat", "rarity": "Rare", "description": "Ultra lucky feline"},
                ],
                "legendary": [
                    {"name": "💰 Money Dragon", "rarity": "Legendary", "description": "Legendary wealth guardian"},
                ]
            },
            "fishing": {
                "common": [
                    {"name": "🦭 Seal", "rarity": "Common", "description": "Playful sea mammal"},
                    {"name": "🐧 Penguin", "rarity": "Common", "description": "Flightless arctic bird"},
                    {"name": "🦦 Otter", "rarity": "Common", "description": "Adorable water weasel"},
                ],
                "rare": [
                    {"name": "🐬 Dolphin", "rarity": "Rare", "description": "Intelligent marine mammal"},
                    {"name": "🦈 Shark", "rarity": "Rare", "description": "Ocean apex predator"},
                ],
                "legendary": [
                    {"name": "🐋 Blue Whale", "rarity": "Legendary", "description": "Largest animal on Earth"},
                    {"name": "🦑 Kraken", "rarity": "Legendary", "description": "Legendary sea monster"},
                ]
            },
            "farming": {
                "common": [
                    {"name": "🐔 Chicken", "rarity": "Common", "description": "Egg-laying farm bird"},
                    {"name": "🐄 Cow", "rarity": "Common", "description": "Gentle milk producer"},
                    {"name": "🐷 Pig", "rarity": "Common", "description": "Pink farm animal"},
                ],
                "rare": [
                    {"name": "🦙 Llama", "rarity": "Rare", "description": "Exotic farm animal"},
                ],
                "legendary": [
                    {"name": "🦚 Rainbow Peacock", "rarity": "Legendary", "description": "Stunning farm jewel"},
                ]
            },
            "time_travel": {
                "common": [
                    {"name": "🦕 Triceratops", "rarity": "Common", "description": "Ancient three-horned dinosaur"},
                    {"name": "🦖 Velociraptor", "rarity": "Common", "description": "Fast prehistoric hunter"},
                ],
                "rare": [
                    {"name": "🦣 Mammoth", "rarity": "Rare", "description": "Ice age giant"},
                    {"name": "🐅 Sabertooth Tiger", "rarity": "Rare", "description": "Prehistoric apex predator"},
                ],
                "legendary": [
                    {"name": "🦖 Tyrannosaurus Rex", "rarity": "Legendary", "description": "King of dinosaurs"},
                    {"name": "🦤 Dodo", "rarity": "Legendary", "description": "Extinct flightless bird"},
                ]
            },
            "space": {
                "common": [
                    {"name": "👽 Alien Pet", "rarity": "Common", "description": "Extraterrestrial creature"},
                ],
                "rare": [
                    {"name": "🛸 Space Dog", "rarity": "Rare", "description": "Cosmic canine"},
                ],
                "legendary": [
                    {"name": "🌌 Cosmic Phoenix", "rarity": "Legendary", "description": "Immortal space bird"},
                ]
            }
        }
    
    def load_zoo_data(self):
        """Load zoo data from JSON"""
        if not os.path.exists(self.zoo_data_file):
            return {}
        try:
            with open(self.zoo_data_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_zoo_data(self):
        """Save zoo data to JSON"""
        try:
            with open(self.zoo_data_file, 'w') as f:
                json.dump(self.zoo_data, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving zoo data: {e}")
    
    def get_user_zoo(self, user_id):
        """Get user's zoo data"""
        user_id = str(user_id)
        if user_id not in self.zoo_data:
            self.zoo_data[user_id] = {
                "animals": {},
                "total_animals": 0,
                "last_encounter": None
            }
        return self.zoo_data[user_id]
    
    def trigger_encounter(self, user_id: int, source: str) -> Optional[dict]:
        """Trigger a random animal encounter"""
        if source not in self.animals_by_source:
            return None
        
        # 15% chance for any encounter
        if random.random() > 0.15:
            return None
        
        # Rarity chances: 70% common, 25% rare, 5% legendary
        rand = random.random()
        if rand < 0.70:
            rarity = "common"
        elif rand < 0.95:
            rarity = "rare"
        else:
            rarity = "legendary"
        
        animals = self.animals_by_source[source].get(rarity, [])
        if not animals:
            return None
        
        animal = random.choice(animals)
        
        # Add to user's zoo
        user_zoo = self.get_user_zoo(user_id)
        animal_key = f"{source}_{animal['name']}"
        
        if animal_key not in user_zoo["animals"]:
            user_zoo["animals"][animal_key] = {
                "name": animal["name"],
                "rarity": animal["rarity"],
                "description": animal["description"],
                "source": source,
                "found_date": datetime.now().isoformat(),
                "count": 1
            }
            user_zoo["total_animals"] += 1
            is_new = True
        else:
            user_zoo["animals"][animal_key]["count"] += 1
            is_new = False
        
        user_zoo["last_encounter"] = datetime.now().isoformat()
        self.save_zoo_data()
        
        return {
            "animal": animal,
            "is_new": is_new,
            "count": user_zoo["animals"][animal_key]["count"]
        }
    
    @commands.command(name="zoo")
    async def zoo_prefix(self, ctx, filter_by: Optional[str] = None):
        """View zoo collection (prefix version)"""
        await self._display_zoo(ctx.author.id, ctx.author.display_name, filter_by, ctx=ctx)
    
    @app_commands.command(name="zoo", description="View your animal collection!")
    @app_commands.describe(
        filter_by="Filter animals by source or rarity"
    )
    async def zoo_slash(self, interaction: discord.Interaction, filter_by: Optional[str] = None):
        """View zoo collection (slash version)"""
        await self._display_zoo(interaction.user.id, interaction.user.display_name, filter_by, interaction=interaction)
    
    async def _display_zoo(self, user_id, display_name, filter_by=None, ctx=None, interaction=None):
        """Shared zoo display logic"""
        user_zoo = self.get_user_zoo(user_id)
        
        if not user_zoo["animals"]:
            embed = discord.Embed(
                title="🦁 Your Zoo",
                description="Your zoo is empty! Play minigames to find wild animals:\n\n"
                           "🎲 **Monopoly** - Bucks, Eagles, Peacocks\n"
                           "🧙 **Wizard Wars** - Goblins, Dragons, Unicorns\n"
                           "🎲 **D&D** - Dragons, Demons, Basilisks\n"
                           "🎣 **Fishing** - Seals, Dolphins, Whales\n"
                           "🎰 **Gambling** - Lucky creatures\n"
                           "🌱 **Farming** - Farm animals\n"
                           "⏰ **Time Travel** - Dinosaurs, Mammoths\n"
                           "🚀 **Space** - Alien creatures",
                color=discord.Color.green()
            )
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)
            return
        
        # Filter animals
        animals_list = []
        for key, data in user_zoo["animals"].items():
            if filter_by:
                if filter_by.lower() not in data["source"].lower() and filter_by.lower() not in data["rarity"].lower():
                    continue
            animals_list.append(data)
        
        # Sort by rarity then name
        rarity_order = {"Common": 0, "Rare": 1, "Legendary": 2, "Mythic": 3}
        animals_list.sort(key=lambda x: (rarity_order.get(x["rarity"], 0), x["name"]))
        
        embed = discord.Embed(
            title=f"🦁 {display_name}'s Zoo",
            description=f"**Total Species:** {user_zoo['total_animals']}\n"
                       f"**Filter:** {filter_by or 'All'}\n",
            color=discord.Color.green()
        )
        
        # Show animals in groups
        for animal in animals_list[:25]:  # Max 25 per page
            rarity_emoji = {"Common": "⚪", "Rare": "🔵", "Legendary": "🟡", "Mythic": "🔴"}
            embed.add_field(
                name=f"{rarity_emoji.get(animal['rarity'], '⚪')} {animal['name']}",
                value=f"*{animal['description']}*\n"
                     f"Source: {animal['source'].title()} | Count: {animal['count']}",
                inline=False
            )
        
        if len(animals_list) > 25:
            embed.set_footer(text=f"Showing 25 of {len(animals_list)} animals")
        
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    @commands.command(name="release")
    async def release_prefix(self, ctx, *, animal_name: str):
        """Release an animal from your zoo (prefix version)"""
        await self._release_animal(ctx.author.id, animal_name, ctx=ctx)
    
    @app_commands.command(name="zoo_release", description="Release an animal from your zoo")
    @app_commands.describe(animal_name="Name of the animal to release")
    async def zoo_release_slash(self, interaction: discord.Interaction, animal_name: str):
        """Release an animal (slash version)"""
        await self._release_animal(interaction.user.id, animal_name, interaction=interaction)
    
    async def _release_animal(self, user_id, animal_name, ctx=None, interaction=None):
        """Shared release logic"""
        user_zoo = self.get_user_zoo(user_id)
        
        # Find animal
        found_key = None
        for key, data in user_zoo["animals"].items():
            if animal_name.lower() in data["name"].lower():
                found_key = key
                break
        
        if not found_key:
            msg = f"❌ Animal '{animal_name}' not found in your zoo!"
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        animal = user_zoo["animals"][found_key]
        del user_zoo["animals"][found_key]
        user_zoo["total_animals"] -= 1
        self.save_zoo_data()
        
        embed = discord.Embed(
            title="🌿 Animal Released",
            description=f"You released **{animal['name']}** back into the wild!\n\n"
                       f"*{animal['description']}*",
            color=discord.Color.blue()
        )
        
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Zoo(bot))
