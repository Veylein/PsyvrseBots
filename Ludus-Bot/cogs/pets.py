import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from datetime import datetime
from leaderboard_manager import leaderboard_manager

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class Pets(commands.Cog):
    """Adopt, feed, and play with pets!"""

    @app_commands.command(name="petshelp", description="View all pet commands and info (paginated)")
    async def petshelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Pets"
        category_desc = "Adopt, feed, and play with pets! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.pets_file = os.path.join(data_dir, "pets.json")
        self.pets_data = self.load_pets()
        
        self.available_pets = [
            {"emoji": "🐯", "name": "Tiger", "behavior": "aggressive", "farm_impact": "trample"},
            {"emoji": "🐉", "name": "Dragon", "behavior": "chaotic", "farm_impact": "burn"},
            {"emoji": "🐼", "name": "Panda", "behavior": "peaceful", "farm_impact": "eat"},
            {"emoji": "🐶", "name": "Dog", "behavior": "loyal", "farm_impact": "dig"},
            {"emoji": "🐱", "name": "Cat", "behavior": "lazy", "farm_impact": "none"},
            {"emoji": "🐹", "name": "Hamster", "behavior": "playful", "farm_impact": "hoard"},
            {"emoji": "🐍", "name": "Snake", "behavior": "sneaky", "farm_impact": "none"},
            {"emoji": "🐴", "name": "Horse", "behavior": "strong", "farm_impact": "trample"},
            {"emoji": "🦎", "name": "Axolotl", "behavior": "calm", "farm_impact": "none"}
        ]
        
        # Pet behavior descriptions
        self.farm_behaviors = {
            "trample": "Can trample and destroy crops",
            "burn": "Might accidentally burn crops",
            "eat": "Will eat crops when hungry",
            "dig": "Might dig up planted seeds",
            "hoard": "Steals harvested crops",
            "none": "Doesn't interact with farms"
        }

    def load_pets(self):
        if os.path.exists(self.pets_file):
            with open(self.pets_file, 'r') as f:
                return json.load(f)
        return {}

    def save_pets(self):
        with open(self.pets_file, 'w') as f:
            json.dump(self.pets_data, f, indent=2)

    @commands.group(name="pet", invoke_without_command=True)
    async def pet(self, ctx):
        await ctx.send("Pet commands: `adopt`, `feed`, `play`, `walk`, `status`\nExample: `L!pet adopt` or `/pet adopt`")

    @app_commands.command(name="pet", description="Virtual pet management")
    @app_commands.choices(action=[
        app_commands.Choice(name="🏠 Adopt Pet", value="adopt"),
        app_commands.Choice(name="🍖 Feed Pet", value="feed"),
        app_commands.Choice(name="🎾 Play with Pet", value="play"),
        app_commands.Choice(name="🚶 Walk Pet", value="walk"),
        app_commands.Choice(name="📊 Pet Status", value="status")
    ])
    async def pet_slash(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        """Unified pet command with action dropdown"""
        await interaction.response.defer()
        
        action_value = action.value if isinstance(action, app_commands.Choice) else action
        
        if action_value == "adopt":
            await self.pet_adopt_action(interaction.user, interaction.guild, interaction)
        elif action_value == "feed":
            await self.pet_feed_action(interaction.user, interaction)
        elif action_value == "play":
            await self.pet_play_action(interaction.user, interaction)
        elif action_value == "walk":
            await self.pet_walk_action(interaction.user, interaction)
        elif action_value == "status":
            await self.pet_status_action(interaction.user, interaction)

    @pet.command(name="adopt")
    async def adopt(self, ctx):
        await self.pet_adopt_action(ctx.author, ctx.guild, ctx)

    async def pet_adopt_action(self, user, guild, ctx_or_interaction):
        user_id = str(user.id)
        
        if user_id in self.pets_data:
            msg = "You already have a pet! Take care of it first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        random_pet = random.choice(self.available_pets)
        
        pet = {
            "emoji": random_pet["emoji"],
            "type": random_pet["name"],
            "name": f"{user.name}'s {random_pet['name']}",
            "hunger": 50,
            "happiness": 50,
            "energy": 50,
            "adopted": str(datetime.now()),
            "behavior": random_pet["behavior"],
            "farm_impact": random_pet["farm_impact"]
        }
        
        self.pets_data[user_id] = pet
        self.save_pets()
        
        leaderboard_manager.increment_stat(
            guild.id,
            "pet_adoptions",
            1,
            guild.name
        )
        
        embed = EmbedBuilder.success(
            "Pet Adopted!",
            f"You adopted a {random_pet['emoji']} **{random_pet['name']}**! Take good care of it!\nUse `/pet status` to check on your pet."
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        # Award small adoption bonus via Economy cog
        try:
            econ = self.bot.get_cog("Economy")
            if econ:
                econ.add_coins(user.id, 50, "pet_adopt")
        except Exception:
            pass

    @pet.command(name="feed")
    async def feed(self, ctx):
        await self.pet_feed_action(ctx.author, ctx)

    async def pet_feed_action(self, user, ctx_or_interaction):
        user_id = str(user.id)
        
        if user_id not in self.pets_data:
            msg = "You don't have a pet yet! Use `/pet adopt` first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet = self.pets_data[user_id]
        
        if pet["hunger"] >= 90:
            msg = f"Your {pet['emoji']} {pet['type']} is already full!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet["hunger"] = min(100, pet["hunger"] + 30)
        pet["happiness"] = min(100, pet["happiness"] + 10)
        self.save_pets()
        
        embed = EmbedBuilder.success(
            "Pet Fed",
            f"🍖 You fed your {pet['emoji']} {pet['type']}! Hunger: {pet['hunger']}/100"
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        # Small reward for tending pet
        try:
            econ = self.bot.get_cog("Economy")
            if econ:
                econ.add_coins(user.id, 5, "pet_feed")
        except Exception:
            pass

    @pet.command(name="play")
    async def play(self, ctx):
        await self.pet_play_action(ctx.author, ctx)

    async def pet_play_action(self, user, ctx_or_interaction):
        user_id = str(user.id)
        
        if user_id not in self.pets_data:
            msg = "You don't have a pet yet! Use `/pet adopt` first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet = self.pets_data[user_id]
        
        if pet["energy"] < 20:
            msg = f"Your {pet['emoji']} {pet['type']} is too tired to play!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet["happiness"] = min(100, pet["happiness"] + 25)
        pet["energy"] = max(0, pet["energy"] - 20)
        pet["hunger"] = max(0, pet["hunger"] - 10)
        self.save_pets()
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.PARTY} Playtime",
            description=f"🎾 You played with your {pet['emoji']} {pet['type']}! Happiness: {pet['happiness']}/100",
            color=Colors.PETS
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        # Reward for playing with pet
        try:
            econ = self.bot.get_cog("Economy")
            if econ:
                econ.add_coins(user.id, 15, "pet_play")
        except Exception:
            pass

    @pet.command(name="walk")
    async def walk(self, ctx):
        await self.pet_walk_action(ctx.author, ctx)

    async def pet_walk_action(self, user, ctx_or_interaction):
        user_id = str(user.id)
        
        if user_id not in self.pets_data:
            msg = "You don't have a pet yet! Use `/pet adopt` first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet = self.pets_data[user_id]
        
        if pet["energy"] < 15:
            msg = f"Your {pet['emoji']} {pet['type']} is too tired for a walk!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet["happiness"] = min(100, pet["happiness"] + 15)
        pet["energy"] = max(0, pet["energy"] - 15)
        pet["hunger"] = max(0, pet["hunger"] - 15)
        self.save_pets()
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.ROCKET} Walk Complete",
            description=f"🚶 You walked your {pet['emoji']} {pet['type']}! It enjoyed the fresh air!",
            color=Colors.PETS
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
        # Reward for walking pet
        try:
            econ = self.bot.get_cog("Economy")
            if econ:
                econ.add_coins(user.id, 10, "pet_walk")
        except Exception:
            pass

    @pet.command(name="status")
    async def status(self, ctx):
        await self.pet_status_action(ctx.author, ctx)

    async def pet_status_action(self, user, ctx_or_interaction):
        user_id = str(user.id)
        
        if user_id not in self.pets_data:
            msg = "You don't have a pet yet! Use `/pet adopt` first."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        pet = self.pets_data[user_id]
        
        embed = EmbedBuilder.create(
            title=f"{pet['emoji']} {pet['name']}",
            description=None,
            color=Colors.PETS
        )
        embed.add_field(name="🍖 Hunger", value=f"{pet['hunger']}/100", inline=True)
        embed.add_field(name="😊 Happiness", value=f"{pet['happiness']}/100", inline=True)
        embed.add_field(name="⚡ Energy", value=f"{pet['energy']}/100", inline=True)
        embed.add_field(name="🎭 Behavior", value=pet.get('behavior', 'unknown').title(), inline=True)

        farm_impact = pet.get('farm_impact', 'none')
        farm_desc = self.farm_behaviors.get(farm_impact, "No special behavior")
        embed.add_field(name="🌾 Farm Behavior", value=farm_desc, inline=False)

        # Show pet bonuses for fishing/farming/coins
        try:
            fish_mult = self.get_fishing_multiplier(user.id)
            farm_mult = self.get_farm_yield_multiplier(user.id)
            coin_bonus = self.get_coin_bonus(user.id)

            if fish_mult and fish_mult != 1.0:
                embed.add_field(name="🎣 Fishing Bonus", value=f"+{int((fish_mult-1)*100)}% catch chance", inline=True)
            else:
                embed.add_field(name="🎣 Fishing Bonus", value="None", inline=True)

            if farm_mult and farm_mult != 1.0:
                embed.add_field(name="🌾 Farm Yield Bonus", value=f"+{int((farm_mult-1)*100)}% harvest", inline=True)
            else:
                embed.add_field(name="🌾 Farm Yield Bonus", value="None", inline=True)

            embed.add_field(name="💰 Coin Bonus", value=(f"+{coin_bonus} coins on pet actions" if coin_bonus else "None"), inline=False)
        except Exception:
            pass

        # Warning if pet is hungry
        if pet['hunger'] < 30:
            embed.add_field(
                name="⚠️ Warning",
                value=f"Your {pet['type']} is hungry! Feed it soon or it might cause trouble on your farm!",
                inline=False
            )

        embed.add_field(name="📅 Adopted", value=pet['adopted'][:10], inline=False)

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    
    def check_pet_farm_interaction(self, user_id: str) -> dict:
        """Check if pet will interact with user's farm - called by farm cog"""
        user_id = str(user_id)
        if user_id not in self.pets_data:
            return {"interaction": False}
        
        pet = self.pets_data[user_id]
        farm_impact = pet.get('farm_impact', 'none')
        hunger = pet.get('hunger', 50)
        
        # Pet only causes trouble if hungry (below 40) and has farm impact
        if hunger < 40 and farm_impact != 'none':
            chance = (40 - hunger) * 2  # 0-80% chance based on hunger
            if random.randint(1, 100) <= chance:
                return {
                    "interaction": True,
                    "type": farm_impact,
                    "pet_name": pet['name'],
                    "pet_emoji": pet['emoji'],
                    "pet_type": pet['type']
                }
        
        return {"interaction": False}

    def get_fishing_multiplier(self, user_id: int) -> float:
        """Return a multiplier to improve fishing chances based on pet type."""
        uid = str(user_id)
        if uid not in self.pets_data:
            return 1.0

        pet = self.pets_data[uid]
        pet_type = pet.get('type', '').lower()

        # Tuned multipliers: make fish-friendly pets more meaningful
        if pet_type in ('cat', 'cat 🐱'):
            return 1.20
        if pet_type in ('axolotl', 'axolotl 🦎'):
            return 1.30

        # small baseline bump for friendly pets
        if pet_type in ('hamster', 'hamster 🐹'):
            return 1.05

        return 1.0

    def get_farm_yield_multiplier(self, user_id: int) -> float:
        """Return a multiplier applied to farm collection yields based on pet type."""
        uid = str(user_id)
        if uid not in self.pets_data:
            return 1.0

        pet = self.pets_data[uid]
        pet_type = pet.get('type', '').lower()

        # Tuned farm yield multipliers
        if pet_type in ('dog', 'dog 🐶'):
            return 1.15
        if pet_type in ('horse', 'horse 🐴'):
            return 1.18
        if pet_type in ('hamster', 'hamster 🐹'):
            return 1.10
        if pet_type in ('panda', 'panda 🐼'):
            return 1.07

        return 1.0

    def get_coin_bonus(self, user_id: int) -> int:
        """Return a small flat coin bonus applied on certain pet interactions."""
        uid = str(user_id)
        if uid not in self.pets_data:
            return 0

        pet = self.pets_data[uid]
        pet_type = pet.get('type', '').lower()

        # Some pets give a small passive coin bonus when interacting
        if pet_type in ('dragon', 'dragon 🐉'):
            return 15
        if pet_type in ('tiger', 'tiger 🐯'):
            return 8

        # cats give a small coin-on-play bonus
        if pet_type in ('cat', 'cat 🐱'):
            return 3

        return 0

    def get_rarity_multiplier(self, user_id: int, rarity: str) -> float:
        """Return an extra multiplier for specific rarities based on pet.

        Used to slightly boost chances for Rare+ catches when the pet
        has affinity (eg. cat/axolotl)."""
        uid = str(user_id)
        if uid not in self.pets_data:
            return 1.0

        pet = self.pets_data[uid]
        pet_type = pet.get('type', '').lower()
        rarity = (rarity or '').lower()

        # Axolotl gives bigger boosts for uncommon+ aquatic finds
        if pet_type in ('axolotl', 'axolotl 🦎'):
            if rarity in ('rare', 'epic'):
                return 1.25
            if rarity in ('legendary', 'mythic'):
                return 1.40

        # Cat gives moderate boosts
        if pet_type in ('cat', 'cat 🐱'):
            if rarity in ('rare', 'epic'):
                return 1.15
            if rarity in ('legendary', 'mythic'):
                return 1.25

        return 1.0

    def get_auto_tend_chance(self, user_id: int) -> float:
        """Return chance [0-1] that pet auto-tends hungry animals during collection."""
        uid = str(user_id)
        if uid not in self.pets_data:
            return 0.0

        pet = self.pets_data[uid]
        pet_type = pet.get('type', '').lower()

        if pet_type in ('dog', 'dog 🐶'):
            return 0.40
        if pet_type in ('horse', 'horse 🐴'):
            return 0.35
        if pet_type in ('hamster', 'hamster 🐹'):
            return 0.20
        if pet_type in ('panda', 'panda 🐼'):
            return 0.12

        return 0.0

async def setup(bot):
    await bot.add_cog(Pets(bot))
