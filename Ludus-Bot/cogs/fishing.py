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
from utils.embed_styles import EmbedBuilder, Colors, Emojis
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}


class EncyclopediaView(discord.ui.View):
    """Paginated fish encyclopedia view"""
    
    def __init__(self, fish_list, rarity_filter=None):
        super().__init__(timeout=180)
        self.fish_list = fish_list
        self.rarity_filter = rarity_filter
        self.current_page = 0
        self.items_per_page = 10
        self.max_pages = (len(fish_list) - 1) // self.items_per_page + 1
        
    def get_embed(self):
        """Generate embed for current page"""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_fish = self.fish_list[start_idx:end_idx]
        
        title = "📖 Fish Encyclopedia"
        if self.rarity_filter:
            title += f" - {self.rarity_filter.title()} Rarity"
        
        embed = discord.Embed(
            title=title,
            description=f"**Discover all the fish species!**\n"
                       f"Page {self.current_page + 1}/{self.max_pages}",
            color=discord.Color.green()
        )
        
        for fish_id, fish in page_fish:
            embed.add_field(
                name=f"{fish['name']} ({fish['rarity']})",
                value=f"💰 Value: {fish['value']} coins\n"
                      f"⚖️ Weight: {fish['weight'][0]}-{fish['weight'][1]}kg",
                inline=True
            )
        
        embed.set_footer(text=f"Total: {len(self.fish_list)} fish | Use arrows to navigate")
        return embed
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Already on first page!", ephemeral=True)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Already on last page!", ephemeral=True)
    
    @discord.ui.button(label="⏭️ First", style=discord.ButtonStyle.secondary, custom_id="first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != 0:
            self.current_page = 0
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Already on first page!", ephemeral=True)
    
    @discord.ui.button(label="Last ⏩", style=discord.ButtonStyle.secondary, custom_id="last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != self.max_pages - 1:
            self.current_page = self.max_pages - 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Already on last page!", ephemeral=True)
# ==================== FISHING MINIGAME ====================

class FishingMinigameView(discord.ui.View):
    """Interactive fishing minigame"""
    
    def __init__(self, cog, user, fish_id, difficulty):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.cog = cog
        self.user = user
        self.fish_id = fish_id
        self.difficulty = difficulty  # 1-5
        self.position = 5  # Fish position (0-10)
        self.player_position = 5  # Player position (0-10)
        self.catches = 0
        self.escapes = 0
        # Harder difficulties need more catches and allow fewer escapes
        self.required_catches = 3 + (difficulty // 2)  # 3-5 catches needed
        self.max_escapes = 4 - (difficulty // 2)  # 4-2 escapes allowed
        self.game_over = False
        self.fish_move_range = 1 + difficulty  # Fish moves further on higher difficulties
        self.move_interval = 3.0 - (difficulty * 0.3)  # Fish moves faster on higher difficulties
        self.message = None
        self.auto_move_task = None
        self.start_time = None
        
    async def start_auto_movement(self, interaction: discord.Interaction):
        """Start automatic fish movement"""
        self.message = await interaction.original_response()
        self.start_time = asyncio.get_event_loop().time()
        self.auto_move_task = asyncio.create_task(self._auto_move_fish())
    
    async def on_timeout(self):
        """Called when the view times out after 3 minutes"""
        self.game_over = True
        if self.auto_move_task:
            self.auto_move_task.cancel()
        
        if self.message:
            try:
                fish_data = self.cog.fish_types[self.fish_id]
                embed = discord.Embed(
                    title="⏱️ Time's Up!",
                    description=f"**The fish escaped:** {fish_data['name']}\n\n"
                                f"You took too long and the fish got away!\n"
                                f"Try to be quicker next time.",
                    color=discord.Color.orange()
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass
        
    async def _auto_move_fish(self):
        """Background task to move fish automatically"""
        try:
            while not self.game_over:
                await asyncio.sleep(self.move_interval)
                if self.game_over:
                    break
                    
                # Move fish randomly
                self.position += random.randint(-1, 1)
                self.position = max(0, min(10, self.position))
                
                # Update display
                if self.message:
                    try:
                        await self._update_display()
                    except:
                        break
        except asyncio.CancelledError:
            pass
            
    async def _update_display(self):
        """Update the message display"""
        fish_data = self.cog.fish_types[self.fish_id]
        
        # Calculate remaining time
        elapsed = asyncio.get_event_loop().time() - self.start_time
        remaining = max(0, 180 - int(elapsed))  # 180 seconds = 3 minutes
        minutes = remaining // 60
        seconds = remaining % 60
        time_display = f"{minutes}:{seconds:02d}"
        
        # Create visual representation
        line = ["⬜"] * 11
        line[self.player_position] = "🎣"
        
        # Show fish position indicator
        if self.player_position == self.position:
            line[self.position] = "🟢"  # Perfect alignment!
        else:
            line[self.position] = "🐟"
        
        visual = "".join(line)
        
        # Build progress bars
        catches_bar = "🟢" * self.catches + "⚪" * (self.required_catches - self.catches)
        escapes_bar = "🔴" * self.escapes + "⚪" * (self.max_escapes - self.escapes)
        
        embed = discord.Embed(
            title="🎣 Fishing Minigame",
            description=f"**Catching:** {fish_data['name']} ({fish_data['rarity']})\n"
                       f"**Progress:** {catches_bar} ({self.required_catches} needed)\n"
                       f"**Escapes:** {escapes_bar} ({self.max_escapes} max)\n"
                       f"⏱️ **Time Remaining:** {time_display}\n\n"
                       f"{visual}\n\n"
                       f"**Tips:**\n"
                       f"• Move ⬅️ ➡️ to align EXACTLY with the fish\n"
                       f"• Press 🎣 when you see 🟢 to reel in!\n"
                       f"• The fish moves automatically - be quick!\n"
                       f"• Difficulty: {'⭐' * self.difficulty}",
            color=discord.Color.blue()
        )
        
        await self.message.edit(embed=embed, view=self)
        
    def stop(self):
        """Stop the view and cancel auto-movement"""
        if self.auto_move_task:
            self.auto_move_task.cancel()
        super().stop()
        
    @discord.ui.button(label="⬅️ Left", style=discord.ButtonStyle.primary, custom_id="fish_left")
    async def move_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your fishing game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        self.player_position = max(0, self.player_position - 1)
        await self.update_game(interaction)
    
    @discord.ui.button(label="➡️ Right", style=discord.ButtonStyle.primary, custom_id="fish_right")
    async def move_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your fishing game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        self.player_position = min(10, self.player_position + 1)
        await self.update_game(interaction)
    
    @discord.ui.button(label="🎣 Reel In", style=discord.ButtonStyle.success, custom_id="fish_reel")
    async def reel_in(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your fishing game!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        # Check if player is EXACTLY aligned with fish (harder)
        if self.player_position == self.position:
            self.catches += 1
            if self.catches >= self.required_catches:
                await self.win_game(interaction)
                return
        else:
            self.escapes += 1
            if self.escapes >= self.max_escapes:
                await self.lose_game(interaction)
                return
        
        # Move fish randomly - more erratic on higher difficulties
        move_range = self.fish_move_range
        self.position += random.randint(-move_range, move_range)
        self.position = max(0, min(10, self.position))
        
        await self.update_game(interaction)
    
    async def update_game(self, interaction: discord.Interaction):
        """Update game display"""
        fish_data = self.cog.fish_types[self.fish_id]
        
        # Calculate remaining time
        elapsed = asyncio.get_event_loop().time() - self.start_time
        remaining = max(0, 180 - int(elapsed))  # 180 seconds = 3 minutes
        minutes = remaining // 60
        seconds = remaining % 60
        time_display = f"{minutes}:{seconds:02d}"
        
        # Create visual representation
        line = ["⬜"] * 11
        line[self.player_position] = "🎣"
        
        # Show fish position indicator
        if self.player_position == self.position:
            line[self.position] = "🟢"  # Perfect alignment!
        else:
            line[self.position] = "🐟"
        
        visual = "".join(line)
        
        # Build progress bars
        catches_bar = "🟢" * self.catches + "⚪" * (self.required_catches - self.catches)
        escapes_bar = "🔴" * self.escapes + "⚪" * (self.max_escapes - self.escapes)
        
        embed = discord.Embed(
            title="🎣 Fishing Minigame",
            description=f"**Catching:** {fish_data['name']} ({fish_data['rarity']})\n"
                       f"**Progress:** {catches_bar} ({self.required_catches} needed)\n"
                       f"**Escapes:** {escapes_bar} ({self.max_escapes} max)\n"
                       f"⏱️ **Time Remaining:** {time_display}\n\n"
                       f"{visual}\n\n"
                       f"**Tips:**\n"
                       f"• Move ⬅️ ➡️ to align EXACTLY with the fish\n"
                       f"• Press 🎣 when you see 🟢 to reel in!\n"
                       f"• The fish moves automatically - be quick!\n"
                       f"• Difficulty: {'⭐' * self.difficulty}",
            color=discord.Color.blue()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            await interaction.edit_original_response(embed=embed, view=self)
    
    async def win_game(self, interaction: discord.Interaction):
        """Player caught the fish"""
        self.game_over = True
        self.stop()
        
        fish_data = self.cog.fish_types[self.fish_id]
        weight = round(random.uniform(fish_data["weight"][0], fish_data["weight"][1]), 2)
        
        # Save catch
        user_data = self.cog.get_user_data(self.user.id)
        if self.fish_id not in user_data["fish_caught"]:
            user_data["fish_caught"][self.fish_id] = {"count": 0, "biggest": 0}
        
        user_data["fish_caught"][self.fish_id]["count"] += 1
        if weight > user_data["fish_caught"][self.fish_id]["biggest"]:
            user_data["fish_caught"][self.fish_id]["biggest"] = weight
        
        user_data["total_catches"] += 1
        user_data["total_value"] += fish_data["value"]
        self.cog.save_fishing_data()
        
        # Award coins
        economy_cog = self.cog.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(self.user.id, fish_data["value"], "fishing")
        
        # Record for tournament if active
        if hasattr(interaction, 'guild_id') and interaction.guild_id:
            self.cog.record_tournament_catch(interaction.guild_id, self.user.id, self.fish_id, weight)
        
        # TCG Card Drop chance (based on fish rarity)
        card_dropped = None
        if tcg_manager and CARD_DATABASE:
            rarity_chances = {
                "Common": 0.05,      # 5% chance
                "Uncommon": 0.10,    # 10% chance
                "Rare": 0.15,        # 15% chance
                "Epic": 0.25,        # 25% chance
                "Legendary": 0.35,   # 35% chance
                "Mythic": 0.50       # 50% chance
            }
            
            drop_chance = rarity_chances.get(fish_data["rarity"], 0.05)
            if random.random() < drop_chance:
                try:
                    # Get random card from database
                    available_cards = list(CARD_DATABASE.keys())
                    if available_cards:
                        card_id = random.choice(available_cards)
                        card_data = CARD_DATABASE[card_id]
                        
                        # Add card to player's collection
                        tcg_manager.add_card_to_collection(self.user.id, card_id)
                        card_dropped = f"🎴 **Bonus!** You found a card: **{card_data.get('name', card_id)}** ({card_data.get('rarity', 'Common')})"
                except Exception as e:
                    print(f"[FISHING] Card drop error: {e}")
        
        description = (f"**You caught:** {fish_data['name']}\n"
                      f"**Rarity:** {fish_data['rarity']}\n"
                      f"**Weight:** {weight}kg\n"
                      f"**Value:** +{fish_data['value']} coins\n\n"
                      f"Great job! The fish is added to your collection.")
        
        if card_dropped:
            description += f"\n\n{card_dropped}"
        
        embed = discord.Embed(
            title="🎉 Fish Caught!",
            description=description,
            color=discord.Color.green()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except:
            await interaction.edit_original_response(embed=embed, view=None)
    
    async def lose_game(self, interaction: discord.Interaction):
        """Fish got away"""
        self.game_over = True
        self.stop()
        
        fish_data = self.cog.fish_types[self.fish_id]
        
        embed = discord.Embed(
            title="💨 Fish Got Away!",
            description=f"**The fish escaped:** {fish_data['name']}\n\n"
                       f"The fish was too quick and got away!\n"
                       f"Better luck next time.",
            color=discord.Color.red()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except:
            await interaction.edit_original_response(embed=embed, view=None)


# ==================== ENCYCLOPEDIA WITH RARITY FILTER + PAGINATION ====================

class EncyclopediaView(discord.ui.View):
    """Encyclopedia with rarity dropdown AND pagination arrows"""
    def __init__(self, fishing_cog, fish_list, rarity=None):
        super().__init__(timeout=180)
        self.fishing_cog = fishing_cog
        self.all_fish = fish_list  # All fish (full list)
        self.fish_list = fish_list  # Current filtered list
        self.rarity = rarity
        self.current_page = 0
        self.items_per_page = 10
        
        # Add rarity dropdown
        rarity_options = [
            discord.SelectOption(label="All Fish", value="all", emoji="🐟"),
            discord.SelectOption(label="Common", value="common", emoji="⚪"),
            discord.SelectOption(label="Uncommon", value="uncommon", emoji="🟢"),
            discord.SelectOption(label="Rare", value="rare", emoji="🔵"),
            discord.SelectOption(label="Epic", value="epic", emoji="🟣"),
            discord.SelectOption(label="Legendary", value="legendary", emoji="🟠"),
            discord.SelectOption(label="Mythic", value="mythic", emoji="🔴")
        ]
        self.rarity_select = discord.ui.Select(
            placeholder="🔍 Filter by rarity...",
            options=rarity_options,
            row=0
        )
        self.rarity_select.callback = self.rarity_callback
        self.add_item(self.rarity_select)
    
    async def rarity_callback(self, interaction: discord.Interaction):
        """Handle rarity filter selection"""
        selected = self.rarity_select.values[0]
        
        if selected == "all":
            self.rarity = None
            self.fish_list = self.all_fish
        else:
            self.rarity = selected
            self.fish_list = [(fid, f) for fid, f in self.all_fish if f["rarity"].lower() == selected.lower()]
        
        self.current_page = 0
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def get_embed(self):
        """Generate current page embed"""
        total_pages = (len(self.fish_list) - 1) // self.items_per_page + 1 if self.fish_list else 1
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.fish_list[start_idx:end_idx]
        
        title = "📖 Fish Encyclopedia"
        if self.rarity:
            title += f" - {self.rarity.title()} Rarity"
        
        embed = discord.Embed(
            title=title,
            description=f"**Total Species:** {len(self.all_fish)}\n"
                        f"**Showing:** {len(self.fish_list)} fish\n"
                        f"**Page:** {self.current_page + 1}/{total_pages}",
            color=discord.Color.blue()
        )
        
        for fish_id, fish in page_items:
            embed.add_field(
                name=f"{fish['name']} ({fish['rarity']})",
                value=f"Value: {fish['value']} | Weight: {fish['weight'][0]}-{fish['weight'][1]}kg",
                inline=True
            )
        
        if not page_items:
            embed.add_field(name="No Fish Found", value="Try a different rarity filter!", inline=False)
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{total_pages} • Use arrows to navigate")
        return embed
    
    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary, row=1)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to first page"""
        self.current_page = 0
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, row=1)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on first page!", ephemeral=True)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        total_pages = (len(self.fish_list) - 1) // self.items_per_page + 1 if self.fish_list else 1
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on last page!", ephemeral=True)
    
    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary, row=1)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to last page"""
        total_pages = (len(self.fish_list) - 1) // self.items_per_page + 1 if self.fish_list else 1
        self.current_page = total_pages - 1
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)


# ==================== MAIN COG ====================

class ShopSelectView(discord.ui.View):
    """Shop with 3 dropdowns for rods, boats, and bait"""
    def __init__(self, fishing_cog, user_data):
        super().__init__(timeout=180)
        self.fishing_cog = fishing_cog
        self.user_data = user_data
        
        # Rod dropdown
        rod_options = [
            discord.SelectOption(label="🎣 Carbon Fiber Rod", value="carbon_rod", description="1000 coins - Lightweight and strong"),
            discord.SelectOption(label="🎣 Professional Rod", value="pro_rod", description="5000 coins - For serious anglers"),
            discord.SelectOption(label="🎣 Master Angler Rod", value="master_rod", description="15000 coins - Expert-level equipment"),
            discord.SelectOption(label="🎣 Poseidon's Trident", value="legendary_rod", description="50000 coins - Divine fishing power!")
        ]
        self.rod_select = discord.ui.Select(placeholder="🎣 Select rod to buy...", options=rod_options, row=0)
        self.rod_select.callback = self.rod_callback
        self.add_item(self.rod_select)
        
        # Boat dropdown
        boat_options = [
            discord.SelectOption(label="🛶 Canoe", value="canoe", description="2000 coins - Explore calm waters"),
            discord.SelectOption(label="🚤 Motorboat", value="motorboat", description="10000 coins - Reach distant locations"),
            discord.SelectOption(label="🛥️ Luxury Yacht", value="yacht", description="50000 coins - Access premium spots"),
            discord.SelectOption(label="🚢 Research Submarine", value="submarine", description="250000 coins - Explore deepest waters")
        ]
        self.boat_select = discord.ui.Select(placeholder="🛶 Select boat to buy...", options=boat_options, row=1)
        self.boat_select.callback = self.boat_callback
        self.add_item(self.boat_select)
        
        # Bait dropdown
        bait_options = [
            discord.SelectOption(label="🪱 Worm", value="worm", description="10 coins - Basic bait"),
            discord.SelectOption(label="🦗 Cricket", value="cricket", description="25 coins - Attracts freshwater fish"),
            discord.SelectOption(label="🐟 Minnow", value="minnow", description="50 coins - Live bait for bigger catches"),
            discord.SelectOption(label="🦑 Squid", value="squid", description="100 coins - Deep sea bait"),
            discord.SelectOption(label="✨ Golden Lure", value="golden_lure", description="500 coins - Legendary bait!")
        ]
        self.bait_select = discord.ui.Select(placeholder="🪱 Select bait to buy...", options=bait_options, row=2)
        self.bait_select.callback = self.bait_callback
        self.add_item(self.bait_select)
    
    async def rod_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            rod_id = self.rod_select.values[0]
            rod = self.fishing_cog.rods[rod_id]
            cost = rod['cost']
            economy_cog = self.fishing_cog.bot.get_cog("Economy")
            
            owned_rods = self.user_data.setdefault('owned_rods', [self.user_data['rod']])
            if rod_id in owned_rods:
                await interaction.followup.send(f"❌ You already own {rod['name']}!", ephemeral=True)
                return
            
            if not economy_cog:
                await interaction.followup.send("❌ Economy system not available.", ephemeral=True)
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                owned_rods.append(rod_id)
                self.user_data['rod'] = rod_id
                self.fishing_cog.save_fishing_data()
                
                # Show success message
                temp_embed = discord.Embed(
                    title="✅ Success",
                    description=f"🎣 Purchased **{rod['name']}** for {cost} PsyCoins!",
                    color=discord.Color.green()
                )
                await interaction.edit_original_response(embed=temp_embed, view=None)
                await asyncio.sleep(3)
                
                # Refresh shop
                await self._refresh_shop(interaction, economy_cog)
            else:
                await interaction.followup.send(f"❌ You need {cost} PsyCoins to buy {rod['name']}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def boat_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            boat_id = self.boat_select.values[0]
            boat = self.fishing_cog.boats[boat_id]
            cost = boat['cost']
            economy_cog = self.fishing_cog.bot.get_cog("Economy")
            
            owned_boats = self.user_data.setdefault('owned_boats', [self.user_data['boat']])
            if boat_id in owned_boats:
                await interaction.followup.send(f"❌ You already own {boat['name']}!", ephemeral=True)
                return
            
            if not economy_cog:
                await interaction.followup.send("❌ Economy system not available.", ephemeral=True)
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                owned_boats.append(boat_id)
                self.user_data['boat'] = boat_id
                self.fishing_cog.save_fishing_data()
                
                # Show success message
                temp_embed = discord.Embed(
                    title="✅ Success",
                    description=f"🛶 Purchased **{boat['name']}** for {cost} PsyCoins!",
                    color=discord.Color.green()
                )
                await interaction.edit_original_response(embed=temp_embed, view=None)
                await asyncio.sleep(3)
                
                # Refresh shop
                await self._refresh_shop(interaction, economy_cog)
            else:
                await interaction.followup.send(f"❌ You need {cost} PsyCoins to buy {boat['name']}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def bait_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            bait_id = self.bait_select.values[0]
            bait = self.fishing_cog.baits[bait_id]
            cost = bait['cost']
            economy_cog = self.fishing_cog.bot.get_cog("Economy")
            
            if not economy_cog:
                await interaction.followup.send("❌ Economy system not available.", ephemeral=True)
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                inv = self.user_data.setdefault('bait_inventory', {})
                inv[bait_id] = inv.get(bait_id, 0) + 1
                self.fishing_cog.save_fishing_data()
                
                # Show success message
                temp_embed = discord.Embed(
                    title="✅ Success",
                    description=f"🪱 Purchased 1x **{bait['name']}** for {cost} PsyCoins!",
                    color=discord.Color.green()
                )
                await interaction.edit_original_response(embed=temp_embed, view=None)
                await asyncio.sleep(3)
                
                # Refresh shop
                await self._refresh_shop(interaction, economy_cog)
            else:
                await interaction.followup.send(f"❌ You need {cost} PsyCoins to buy {bait['name']}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def _refresh_shop(self, interaction: discord.Interaction, economy_cog):
        """Refresh the shop embed with updated data"""
        balance = economy_cog.get_balance(interaction.user.id) if economy_cog else 0
        
        embed = discord.Embed(
            title="🪙 Fishing Shop",
            description=f"**Your Balance:** {balance} PsyCoins\n\n"
                        f"**Current Equipment:**\n"
                        f"🎣 Rod: {self.fishing_cog.rods[self.user_data['rod']]['name']}\n"
                        f"🛶 Boat: {self.fishing_cog.boats[self.user_data['boat']]['name']}\n\n"
                        "**Select items from the dropdowns below to purchase!**",
            color=discord.Color.gold()
        )
        
        # Rods section
        rods_text = ""
        owned_rods = self.user_data.setdefault('owned_rods', [self.user_data['rod']])
        for rod_id, rod in self.fishing_cog.rods.items():
            owned = "✅" if rod_id in owned_rods else ""
            rods_text += f"{rod['name']} - **{rod['cost']} PsyCoins** {owned}\n"
        embed.add_field(name="🎣 Fishing Rods", value=rods_text, inline=False)
        
        # Boats section
        boats_text = ""
        owned_boats = self.user_data.setdefault('owned_boats', [self.user_data['boat']])
        for boat_id, boat in self.fishing_cog.boats.items():
            owned = "✅" if boat_id in owned_boats else ""
            boats_text += f"{boat['name']} - **{boat['cost']} PsyCoins** {owned}\n"
        embed.add_field(name="🛶 Boats", value=boats_text, inline=False)
        
        # Bait section
        bait_text = ""
        for bait_id, bait in self.fishing_cog.baits.items():
            bait_text += f"{bait['name']} - **{bait['cost']} PsyCoins** (x1)\n"
        embed.add_field(name="🪱 Bait", value=bait_text, inline=False)
        
        embed.set_footer(text="💡 Select from dropdowns below to buy items!")
        
        # Create new view
        new_view = ShopSelectView(self.fishing_cog, self.user_data)
        await interaction.edit_original_response(embed=embed, view=new_view)


class AreaSelectView(discord.ui.View):
    """Dropdown to select and travel to fishing areas"""
    def __init__(self, fishing_cog, user_data):
        super().__init__(timeout=180)
        self.fishing_cog = fishing_cog
        self.user_data = user_data
        
        # Build area options
        options = []
        for area_id, area in fishing_cog.areas.items():
            unlocked = area_id in user_data["unlocked_areas"]
            current = area_id == user_data["current_area"]
            
            if current:
                label = f"📍 {area['name']} (Current)"
            elif unlocked:
                label = f"✅ {area['name']}"
            else:
                label = f"🔒 {area['name']} - {area['unlock_cost']} coins"
            
            options.append(discord.SelectOption(
                label=label[:100],
                value=area_id,
                description=area['description'][:100]
            ))
        
        self.area_select_menu = discord.ui.Select(
            placeholder="🗺️ Select area to travel or unlock...",
            options=options
        )
        self.area_select_menu.callback = self.area_callback
        self.add_item(self.area_select_menu)
    
    async def area_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            area_id = self.area_select_menu.values[0]
            area = self.fishing_cog.areas[area_id]
            economy_cog = self.fishing_cog.bot.get_cog("Economy")
            
            # Check if already at this area
            if area_id == self.user_data["current_area"]:
                await interaction.followup.send("📍 You are already at this location!", ephemeral=True)
                return
            
            # Check if unlocked
            success_message = None
            if area_id not in self.user_data["unlocked_areas"]:
                # Try to unlock
                if not economy_cog:
                    await interaction.followup.send("❌ Economy system not available.", ephemeral=True)
                    return
                
                cost = area["unlock_cost"]
                if economy_cog.remove_coins(interaction.user.id, cost):
                    self.user_data["unlocked_areas"].append(area_id)
                    self.user_data["current_area"] = area_id
                    self.fishing_cog.save_fishing_data()
                    success_message = f"🎉 Unlocked and traveled to **{area['name']}** for {cost} PsyCoins!"
                else:
                    await interaction.followup.send(
                        f"❌ You need {cost} PsyCoins to unlock **{area['name']}**.",
                        ephemeral=True
                    )
                    return
            else:
                # Just travel
                self.user_data["current_area"] = area_id
                self.fishing_cog.save_fishing_data()
                success_message = f"🚤 Traveled to **{area['name']}**!"
            
            # Show success message temporarily
            if success_message:
                temp_embed = discord.Embed(
                    title="✅ Success",
                    description=success_message,
                    color=discord.Color.green()
                )
                await interaction.edit_original_response(embed=temp_embed, view=None)
                
                # Wait 3 seconds
                await asyncio.sleep(3)
                
                # Refresh the areas view with updated data
                current_area = self.fishing_cog.areas[self.user_data['current_area']]
                balance = economy_cog.get_balance(interaction.user.id) if economy_cog else 0
                
                new_embed = discord.Embed(
                    title="🗺️ Fishing Areas",
                    description=f"**Your Balance:** {balance} PsyCoins\n"
                                f"**Current Location:** 📍 {current_area['name']}\n"
                                f"**Unlocked Areas:** {len(self.user_data['unlocked_areas'])}/{len(self.fishing_cog.areas)}\n\n"
                                "**Select an area from the dropdown below to travel or unlock!**",
                    color=discord.Color.green()
                )
                
                # Add all areas as fields
                for area_id_iter, area_iter in self.fishing_cog.areas.items():
                    unlocked = area_id_iter in self.user_data["unlocked_areas"]
                    current = area_id_iter == self.user_data["current_area"]
                    
                    if current:
                        status = "📍 Current Location"
                    elif unlocked:
                        status = "✅ Unlocked"
                    else:
                        status = f"🔒 Locked - {area_iter['unlock_cost']} PsyCoins"
                    
                    new_embed.add_field(
                        name=f"{area_iter['name']}",
                        value=f"{area_iter['description']}\n**Status:** {status}",
                        inline=False
                    )
                
                new_embed.set_footer(text="💡 Use the dropdown below to travel or unlock areas!")
                
                # Create new view with updated data
                new_view = AreaSelectView(self.fishing_cog, self.user_data)
                await interaction.edit_original_response(embed=new_embed, view=new_view)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class BaitSelectView(discord.ui.View):
    """Dropdown to select bait before casting"""
    def __init__(self, fishing_cog, user_data, interaction_obj):
        super().__init__(timeout=60)
        self.fishing_cog = fishing_cog
        self.user_data = user_data
        self.interaction_obj = interaction_obj
        
        # Build bait options from user's inventory
        bait_options = [discord.SelectOption(
            label="🚫 No Bait",
            value="none",
            description="Fish without bait (lower catch rate)",
            emoji="🚫"
        )]
        
        bait_inventory = user_data.get("bait_inventory", {})
        for bait_id, count in bait_inventory.items():
            if count > 0 and bait_id in fishing_cog.baits:
                bait = fishing_cog.baits[bait_id]
                bait_options.append(discord.SelectOption(
                    label=f"{bait['name']} (x{count})",
                    value=bait_id,
                    description=f"+{bait['catch_bonus']}% catch bonus"
                ))
        
        self.bait_select = discord.ui.Select(
            placeholder="🪱 Select bait to use...",
            options=bait_options,
            row=0
        )
        self.bait_select.callback = self.bait_callback
        self.add_item(self.bait_select)
    
    async def bait_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            selected_bait = self.bait_select.values[0]
            bait_choice = None if selected_bait == "none" else selected_bait
            
            # Start fishing with selected bait
            await self.fishing_cog.cast_action(interaction, bait_choice)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class InventoryEquipView(discord.ui.View):
    """Dropdown to equip rods and boats from inventory"""
    def __init__(self, fishing_cog, user_data):
        super().__init__(timeout=180)
        self.fishing_cog = fishing_cog
        self.user_data = user_data
        
        # Build rod options - only show owned rods
        rod_options = []
        owned_rods = user_data.get("owned_rods", [user_data["rod"]])
        for rod_id in owned_rods:
            if rod_id in fishing_cog.rods:
                rod = fishing_cog.rods[rod_id]
                current = "✅ " if rod_id == user_data["rod"] else ""
                rod_options.append(discord.SelectOption(
                    label=f"{current}{rod['name']}",
                    value=rod_id,
                    description=f"Catch: +{rod['catch_bonus']} | Rare: +{rod['rare_bonus']}"[:100]
                ))
        
        if len(rod_options) > 1:  # Only add dropdown if user has multiple rods
            self.rod_select = discord.ui.Select(
                placeholder="🎣 Select rod to equip...",
                options=rod_options,
                row=0
            )
            self.rod_select.callback = self.equip_rod_callback
            self.add_item(self.rod_select)
        
        # Build boat options - only show owned boats
        boat_options = []
        owned_boats = user_data.get("owned_boats", [user_data["boat"]])
        for boat_id in owned_boats:
            if boat_id in fishing_cog.boats:
                boat = fishing_cog.boats[boat_id]
                current = "✅ " if boat_id == user_data["boat"] else ""
                boat_options.append(discord.SelectOption(
                    label=f"{current}{boat['name']}",
                    value=boat_id,
                    description=boat['description'][:100]
                ))
        
        if len(boat_options) > 1:  # Only add dropdown if user has multiple boats
            self.boat_select = discord.ui.Select(
                placeholder="🛶 Select boat to equip...",
                options=boat_options,
                row=1
            )
            self.boat_select.callback = self.equip_boat_callback
            self.add_item(self.boat_select)
    
    async def equip_rod_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            rod_id = self.rod_select.values[0]
            rod = self.fishing_cog.rods[rod_id]
            
            if self.user_data['rod'] == rod_id:
                await interaction.followup.send(f"✅ {rod['name']} is already equipped!", ephemeral=True)
                return
            
            self.user_data['rod'] = rod_id
            self.fishing_cog.save_fishing_data()
            
            temp_embed = discord.Embed(
                title="✅ Success",
                description=f"🎣 Equipped **{rod['name']}**!",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=temp_embed, view=None)
            await asyncio.sleep(2)
            
            await self._refresh_inventory(interaction)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def equip_boat_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            boat_id = self.boat_select.values[0]
            boat = self.fishing_cog.boats[boat_id]
            
            if self.user_data['boat'] == boat_id:
                await interaction.followup.send(f"✅ {boat['name']} is already equipped!", ephemeral=True)
                return
            
            self.user_data['boat'] = boat_id
            self.fishing_cog.save_fishing_data()
            
            temp_embed = discord.Embed(
                title="✅ Success",
                description=f"🛶 Equipped **{boat['name']}**!",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=temp_embed, view=None)
            await asyncio.sleep(2)
            
            await self._refresh_inventory(interaction)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def _refresh_inventory(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}'s Fishing Inventory",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎣 Equipped Rod",
            value=self.fishing_cog.rods[self.user_data["rod"]]["name"],
            inline=True
        )
        embed.add_field(
            name="🛶 Equipped Boat",
            value=self.fishing_cog.boats[self.user_data["boat"]]["name"],
            inline=True
        )
        embed.add_field(
            name="📍 Current Area",
            value=self.fishing_cog.areas[self.user_data["current_area"]]["name"],
            inline=True
        )
        
        if self.user_data.get("bait_inventory"):
            bait_text = ""
            for bait_id, count in self.user_data["bait_inventory"].items():
                bait_text += f"{self.fishing_cog.baits[bait_id]['name']}: {count}\n"
            embed.add_field(name="🪱 Bait Inventory", value=bait_text or "None", inline=False)
        
        if self.user_data["fish_caught"]:
            embed.add_field(
                name="🐟 Fish Collection",
                value=f"**Total Catches:** {self.user_data['total_catches']}\n"
                     f"**Total Value:** {self.user_data['total_value']} coins\n"
                     f"**Species:** {len(self.user_data['fish_caught'])}/{len(self.fishing_cog.fish_types)}",
                inline=False
            )
            
            sorted_fish = sorted(
                self.user_data["fish_caught"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            
            fish_list = ""
            for fish_id, data in sorted_fish[:5]:
                fish = self.fishing_cog.fish_types[fish_id]
                fish_list += f"{fish['name']}: {data['count']} (Biggest: {data['biggest']}kg)\n"
            
            embed.add_field(name="🏆 Top 5 Fish", value=fish_list, inline=False)
        else:
            embed.add_field(
                name="🐟 Fish Collection",
                value="No fish caught yet! Use `/fish cast` to start.",
                inline=False
            )
        
        embed.set_footer(text="💡 Use the dropdowns above to change your equipment!")
        
        new_view = InventoryEquipView(self.fishing_cog, self.user_data)
        await interaction.edit_original_response(embed=embed, view=new_view)


class FishingHelpView(discord.ui.View):
    """Multi-page help view for fishing system"""
    def __init__(self, fishing_cog):
        super().__init__(timeout=180)
        self.fishing_cog = fishing_cog
        self.current_page = 0
        self.pages = []
        self._build_pages()
    
    def _build_pages(self):
        """Build all help pages"""
        # Page 0: Main Commands
        page0 = discord.Embed(
            title="🎣 Fishing System - Commands",
            description="**Welcome to Ultimate Fishing Simulator!**\n\n"
                       "Cast your line, catch fish, and compete in tournaments!\n"
                       "Every catch includes an interactive minigame!",
            color=discord.Color.blue()
        )
        page0.add_field(
            name="📋 Main Commands",
            value="`/fish cast` - Start fishing (with minigame!)\n"
                 "`/fish inventory` - View your collection\n"
                 "`/fish shop` - Buy rods, boats, and bait\n"
                 "`/fish areas` - Travel to fishing locations\n"
                 "`/fish encyclopedia` - Browse all fish\n"
                 "`/fish stats` - View your statistics",
            inline=False
        )
        page0.set_footer(text="Page 1/6 • Use arrows to navigate")
        self.pages.append(page0)
        
        # Page 1: Minigame Guide
        page1 = discord.Embed(
            title="🎮 Interactive Minigame",
            description="**How to catch fish:**\n"
                       "When you cast your line, a fish bites and you enter the minigame!",
            color=discord.Color.green()
        )
        page1.add_field(
            name="🕹️ Controls",
            value="**⬅️ Left** - Move your rod left\n"
                 "**➡️ Right** - Move your rod right\n"
                 "**🎣 Reel In** - Catch when aligned!\n\n"
                 "⚠️ You must be **EXACTLY** aligned with the fish (🟢)",
            inline=False
        )
        page1.add_field(
            name="⏱️ Timer & Progress",
            value="**Time Limit:** 3 minutes per catch\n"
                 "**Progress:** Catch the fish multiple times (🟢)\n"
                 "**Escapes:** Limited mistakes allowed (🔴)\n"
                 "**Auto-Movement:** Fish moves on its own!",
            inline=False
        )
        page1.add_field(
            name="⭐ Difficulty",
            value="**Common:** ⭐ (3 catches, 4 escapes, slow)\n"
                 "**Uncommon:** ⭐⭐ (3-4 catches, 3-4 escapes)\n"
                 "**Rare:** ⭐⭐⭐ (4 catches, 3 escapes)\n"
                 "**Epic:** ⭐⭐⭐⭐ (4-5 catches, 2-3 escapes)\n"
                 "**Legendary:** ⭐⭐⭐⭐⭐ (5 catches, 2 escapes, fast!)\n"
                 "**Mythic:** ⭐⭐⭐⭐⭐ (5 catches, 2 escapes, very fast!)",
            inline=False
        )
        page1.set_footer(text="Page 2/6 • Use arrows to navigate")
        self.pages.append(page1)
        
        # Page 2: Rods & Equipment
        page2 = discord.Embed(
            title="🎣 Fishing Rods",
            description="**Better rods = Better catches!**\n"
                       "Rods provide catch bonuses and rare fish bonuses.",
            color=discord.Color.gold()
        )
        for rod_id, rod in self.fishing_cog.rods.items():
            page2.add_field(
                name=f"{rod['name']}",
                value=f"**Cost:** {rod['cost']:,} PsyCoins\n"
                     f"**Catch Bonus:** +{rod['catch_bonus']}%\n"
                     f"**Rare Bonus:** +{rod['rare_bonus']}%\n"
                     f"*{rod['description']}*",
                inline=True
            )
        page2.add_field(
            name="💡 Tip",
            value="Invest in better rods to catch rarer and more valuable fish!\n"
                 "Higher bonuses mean better chances!",
            inline=False
        )
        page2.set_footer(text="Page 3/6 • Use arrows to navigate")
        self.pages.append(page2)
        
        # Page 3: Bait & Boats
        page3 = discord.Embed(
            title="🪱 Bait & 🛶 Boats",
            description="**Enhance your fishing with bait and travel with boats!**",
            color=discord.Color.purple()
        )
        
        bait_text = ""
        for bait_id, bait in self.fishing_cog.baits.items():
            bait_text += f"**{bait['name']}** - {bait['cost']} coins\n"
            bait_text += f"+{bait['catch_bonus']}% catch, +{bait['rare_bonus']}% rare\n"
            bait_text += f"*{bait['description']}*\n\n"
        page3.add_field(name="🪱 Bait Types", value=bait_text, inline=False)
        
        boat_text = "**🦶 On Foot** - Free (Pond, River)\n"
        boat_text += "**🛶 Canoe** - 2,000 coins (+ Lake)\n"
        boat_text += "**🚤 Motorboat** - 10,000 coins (+ Ocean, Tropical)\n"
        boat_text += "**🛥️ Yacht** - 50,000 coins (+ Arctic, Reef)\n"
        boat_text += "**🚢 Submarine** - 250,000 coins (+ Abyss, Trench)\n"
        page3.add_field(name="🛶 Boats", value=boat_text, inline=False)
        page3.set_footer(text="Page 4/6 • Use arrows to navigate")
        self.pages.append(page3)
        
        # Page 4: Fishing Areas
        page4 = discord.Embed(
            title="🗺️ Fishing Areas",
            description="**Explore 9 unique fishing locations!**\n"
                       "Each area has different fish and unlock costs.",
            color=discord.Color.teal()
        )
        for area_id, area in self.fishing_cog.areas.items():
            unlock_text = "Free" if area['unlock_cost'] == 0 else f"{area['unlock_cost']:,} coins"
            page4.add_field(
                name=f"{area['name']}",
                value=f"**Unlock:** {unlock_text}\n"
                     f"**Requires:** {self.fishing_cog.boats[area['required_boat']]['name']}\n"
                     f"**Fish Species:** {len(area['fish'])}\n"
                     f"*{area['description']}*",
                inline=True
            )
        page4.add_field(
            name="🌟 Tips",
            value="• Start at Pond & River (free)\n"
                 "• Buy better boats to unlock more areas\n"
                 "• Rarer areas = Rarer fish = More coins!",
            inline=False
        )
        page4.set_footer(text="Page 5/6 • Use arrows to navigate")
        self.pages.append(page4)
        
        # Page 5: Tournaments & Advanced
        page5 = discord.Embed(
            title="🏆 Tournaments & Advanced Features",
            description="**Compete with other players in fishing tournaments!**",
            color=discord.Color.orange()
        )
        page5.add_field(
            name="🎯 Tournament Types",
            value="**🏆 Biggest Fish** - Catch the heaviest fish\n"
                 "**📊 Most Fish** - Catch the most fish\n"
                 "**✨ Rarest Fish** - Catch the rarest fish\n\n"
                 "Tournaments appear randomly (6-12h intervals, 10% chance)!",
            inline=False
        )
        page5.add_field(
            name="🎁 Prizes",
            value="**🥇 1st Place:** 1,000 coins\n"
                 "**🥈 2nd Place:** 500 coins\n"
                 "**🥉 3rd Place:** 250 coins\n\n"
                 "All catches count automatically when tournament is active!",
            inline=False
        )
        page5.add_field(
            name="🌤️ Weather & Time",
            value="**Weather Effects:**\n"
                 "☀️ Sunny (1.0x) | ☁️ Cloudy (1.2x) | 🌧️ Rainy (1.5x)\n"
                 "⛈️ Stormy (0.5x) | 🌫️ Foggy (1.3x)\n\n"
                 "**Time Effects:**\n"
                 "🌅 Dawn (1.4x) | 🌇 Dusk (1.4x) | 🌙 Night (1.2x)\n"
                 "Fish more actively during dawn and dusk!",
            inline=False
        )
        page5.add_field(
            name="📖 Encyclopedia",
            value="Use `/fish encyclopedia` to browse all 50+ fish species!\n"
                 "Filter by rarity and see detailed stats for each fish.",
            inline=False
        )
        page5.set_footer(text="Page 6/6 • Use arrows to navigate")
        self.pages.append(page5)
    
    def get_current_embed(self):
        """Get the current page embed"""
        return self.pages[self.current_page]
    
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary, custom_id="first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.get_current_embed(), view=self)


class Fishing(commands.Cog):
    """Ultimate Fishing Simulator - Boats, Bait, Rods, Areas, Weather, and More!"""
    @app_commands.command(name="fishhelp", description="View all fishing commands and info (paginated)")
    async def fishhelp_slash(self, interaction: discord.Interaction):
        view = FishingHelpView(self)
        await interaction.response.send_message(embed=view.get_current_embed(), view=view)
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.fishing_data_file = os.path.join(data_dir, "fishing_data.json")
        self.fishing_data = self.load_fishing_data()
        self.active_tournaments = {}
        self.random_tournament_task = None
        
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
    
    def get_guild_config(self, guild_id):
        """Get guild configuration for tournaments"""
        guild_id = str(guild_id)
        config_key = f"guild_{guild_id}"
        if config_key not in self.fishing_data:
            self.fishing_data[config_key] = {
                "tournament_channel": None  # Admin can set this
            }
        return self.fishing_data[config_key]
    
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
    async def fish_main(self, interaction: discord.Interaction, action: Optional[str] = "menu"):
        """Main fishing command with optional actions"""
        if action == "cast":
            # Check if user has bait and no bait was specified
            user_data = self.get_user_data(interaction.user.id)
            bait_inventory = user_data.get("bait_inventory", {})
            has_bait = bool(bait_inventory) and any(count > 0 for count in bait_inventory.values())
            
            if has_bait:
                # Show bait selection menu
                embed = discord.Embed(
                    title="🎣 Select Your Bait",
                    description="You have bait in your inventory!\n"
                               "Select which bait to use, or choose **No Bait** to fish without it.\n\n"
                               "💡 Using bait increases your catch rate!",
                    color=discord.Color.blue()
                )
                view = BaitSelectView(self, user_data, interaction)
                await interaction.response.send_message(embed=embed, view=view)
            else:
                # Cast directly (no bait available)
                await self.cast_action(interaction, None)
        elif action == "inventory":
            await self.fish_inventory_action(interaction)
        elif action == "shop":
            await self.fish_shop_action(interaction)
        elif action == "areas":
            await self.fish_areas_action(interaction)
        elif action == "encyclopedia":
            await self.fish_encyclopedia_action(interaction, None)
        elif action == "stats":
            await self.fish_stats_action(interaction)
        else:  # menu
            await self.fish_menu_action(interaction)
    
    async def fish_menu_action(self, interaction: discord.Interaction):
        """Show fishing main menu"""
        user_data = self.get_user_data(interaction.user.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} Ultimate Fishing Simulator",
            description="**Welcome to the most advanced fishing experience!**\n\n"
                       "**Your Stats:**\n"
                       f"🎣 Rod: {self.rods[user_data['rod']]['name']}\n"
                       f"🛶 Boat: {self.boats[user_data['boat']]['name']}\n"
                       f"📍 Area: {self.areas[user_data['current_area']]['name']}\n"
                       f"🐟 Total Catches: {user_data['total_catches']}\n\n"
                       "**Available Actions:**\n"
                       "Use `/fish <action>` to access different features:\n"
                       "• `cast` - Cast your line and fish!\n"
                       "• `inventory` - View catches & equipment\n"
                       "• `shop` - Purchase equipment & bait\n"
                       "• `areas` - View locations & travel\n"
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
        embed = EmbedBuilder.info(
            "Casting Line...",
            f"{weather_data['emoji']} **Weather:** {weather.title()} - {weather_data['description']}\n"
            f"{time_data['emoji']} **Time:** {time_period.title()}\n"
            f"🎣 **Rod:** {self.rods[user_data['rod']]['name']}\n"
            f"🪱 **Bait:** {bait_name}\n\n"
            "🌊 *Waiting for a bite...*",
            footer_text="Tight lines!"
        )
        
        # Check if interaction was already responded to (from bait selection)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=None)
        else:
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
        # Apply pet-based fishing multiplier if user has a pet
        pet_multiplier = 1.0
        try:
            pets_cog = self.bot.get_cog("Pets")
            if pets_cog:
                pet_multiplier = pets_cog.get_fishing_multiplier(interaction.user.id)
        except Exception:
            pet_multiplier = 1.0

        fish_chances = []
        for fish_id in available_fish:
            fish = self.fish_types[fish_id]
            # Apply rarity-specific pet bonuses (e.g., axolotl/cat)
            rarity_mult = 1.0
            try:
                pets_cog = self.bot.get_cog("Pets")
                if pets_cog:
                    rarity_mult = pets_cog.get_rarity_multiplier(interaction.user.id, fish.get("rarity"))
            except Exception:
                rarity_mult = 1.0

            adjusted_chance = fish["chance"] * total_multiplier * pet_multiplier * rarity_mult
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
        
        # Fish bites! Show catch animation
        embed.description = f"{weather_data['emoji']} **Weather:** {weather.title()}\n" \
                           f"{time_data['emoji']} **Time:** {time_period.title()}\n" \
                           f"🎣 **Rod:** {self.rods[user_data['rod']]['name']}\n" \
                           f"🪱 **Bait:** {bait_name}\n\n" \
                           f"🐟 **A fish is biting!**\n" \
                           f"Get ready to catch it!"
        
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(1)
        

        # Determine difficulty based on rarity
        difficulty_map = {
            "Common": 1,
            "Uncommon": 2,
            "Rare": 3,
            "Epic": 4,
            "Legendary": 5,
            "Mythic": 5
        }
        difficulty = difficulty_map.get(caught_fish["rarity"], 3)
        
        # Start minigame
        minigame_view = FishingMinigameView(self, interaction.user, caught_fish_id, difficulty)
        
        embed = discord.Embed(
            title="🎣 Fishing Minigame",
            description=f"**Catching:** {caught_fish['name']} ({caught_fish['rarity']})\n"
                       f"**Progress:** ⚪⚪⚪ ({3 + (difficulty // 2)} needed)\n"
                       f"**Escapes:** ⚪⚪⚪ ({4 - (difficulty // 2)} max)\n"
                       f"⏱️ **Time Remaining:** 3:00\n\n"
                       f"⬜⬜⬜⬜⬜🎣⬜⬜⬜⬜⬜\n\n"
                       f"**Tips:**\n"
                       f"• Move ⬅️ ➡️ to align EXACTLY with the fish\n"
                       f"• Press 🎣 when you see 🟢 to reel in!\n"
                       f"• The fish moves automatically - be quick!\n"
                       f"• Difficulty: {'⭐' * difficulty}",
            color=discord.Color.blue()
        )
        
        await interaction.edit_original_response(embed=embed, view=minigame_view)
        
        # Start automatic fish movement
        await minigame_view.start_auto_movement(interaction)
        
        # Save data and update stats
        self.save_fishing_data()
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "fishing")
    
    async def fish_inventory_action(self, interaction: discord.Interaction):
        """View fishing inventory with equipment"""
        user_data = self.get_user_data(interaction.user.id)
        embed = discord.Embed(
            title=f"🎒 {interaction.user.display_name}'s Fishing Inventory",
            color=discord.Color.blue()
        )
        
        # Show equipped items
        embed.add_field(
            name="🎣 Equipped Rod",
            value=self.rods[user_data["rod"]]["name"],
            inline=True
        )
        embed.add_field(
            name="🛶 Equipped Boat",
            value=self.boats[user_data["boat"]]["name"],
            inline=True
        )
        embed.add_field(
            name="📍 Current Area",
            value=self.areas[user_data["current_area"]]["name"],
            inline=True
        )
        
        # Show bait inventory
        if user_data.get("bait_inventory"):
            bait_text = ""
            for bait_id, count in user_data["bait_inventory"].items():
                bait_text += f"{self.baits[bait_id]['name']}: {count}\n"
            embed.add_field(name="🪱 Bait Inventory", value=bait_text or "None", inline=False)
        
        # Show fish stats
        if user_data["fish_caught"]:
            embed.add_field(
                name="🐟 Fish Collection",
                value=f"**Total Catches:** {user_data['total_catches']}\n"
                     f"**Total Value:** {user_data['total_value']} coins\n"
                     f"**Species:** {len(user_data['fish_caught'])}/{len(self.fish_types)}",
                inline=False
            )
            
            # Show top 5 fish
            sorted_fish = sorted(
                user_data["fish_caught"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            
            fish_list = ""
            for fish_id, data in sorted_fish[:5]:
                fish = self.fish_types[fish_id]
                fish_list += f"{fish['name']}: {data['count']} (Biggest: {data['biggest']}kg)\n"
            
            embed.add_field(name="🏆 Top 5 Fish", value=fish_list, inline=False)
        else:
            embed.add_field(
                name="🐟 Fish Collection",
                value="No fish caught yet! Use `/fish cast` to start.",
                inline=False
            )
        
        embed.set_footer(text="💡 Use the dropdowns above to change your equipment!")
        
        view = InventoryEquipView(self, user_data)
        await interaction.response.send_message(embed=embed, view=view)
    
    async def fish_shop_action(self, interaction: discord.Interaction):
        """View fishing shop with dropdowns"""
        try:
            user_data = self.get_user_data(interaction.user.id)
            economy_cog = self.bot.get_cog("Economy")
            balance = economy_cog.get_balance(interaction.user.id) if economy_cog else 0
            
            embed = discord.Embed(
                title="🪙 Fishing Shop",
                description=f"**Your Balance:** {balance} PsyCoins\n\n"
                            f"**Current Equipment:**\n"
                            f"🎣 Rod: {self.rods[user_data['rod']]['name']}\n"
                            f"🛶 Boat: {self.boats[user_data['boat']]['name']}\n\n"
                            "**Select items from the dropdowns below to purchase!**",
                color=discord.Color.gold()
            )
            
            # Rods section
            rods_text = ""
            for rod_id, rod in self.rods.items():
                owned = "✅" if rod_id == user_data["rod"] else ""
                rods_text += f"{rod['name']} - **{rod['cost']} PsyCoins** {owned}\n"
            embed.add_field(name="🎣 Fishing Rods", value=rods_text, inline=False)
            
            # Boats section
            boats_text = ""
            for boat_id, boat in self.boats.items():
                owned = "✅" if boat_id == user_data["boat"] else ""
                boats_text += f"{boat['name']} - **{boat['cost']} PsyCoins** {owned}\n"
            embed.add_field(name="🛶 Boats", value=boats_text, inline=False)
            
            # Bait section
            bait_text = ""
            for bait_id, bait in self.baits.items():
                bait_text += f"{bait['name']} - **{bait['cost']} PsyCoins** (x1)\n"
            embed.add_field(name="🪱 Bait", value=bait_text, inline=False)
            
            embed.set_footer(text="💡 Select from dropdowns below to buy items!")
            
            view = ShopSelectView(self, user_data)
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            print(f"[FISHING SHOP ERROR] {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    
    async def fish_areas_action(self, interaction: discord.Interaction):
        """View fishing areas with dropdown to travel/unlock"""
        try:
            user_data = self.get_user_data(interaction.user.id)
            current_area = self.areas[user_data['current_area']]
            economy_cog = self.bot.get_cog("Economy")
            balance = economy_cog.get_balance(interaction.user.id) if economy_cog else 0
            
            embed = discord.Embed(
                title="🗺️ Fishing Areas",
                description=f"**Your Balance:** {balance} PsyCoins\n"
                            f"**Current Location:** 📍 {current_area['name']}\n"
                            f"**Unlocked Areas:** {len(user_data['unlocked_areas'])}/{len(self.areas)}\n\n"
                            "**Select an area from the dropdown below to travel or unlock!**",
                color=discord.Color.green()
            )
            
            # Add all areas as fields
            for area_id, area in self.areas.items():
                unlocked = area_id in user_data["unlocked_areas"]
                current = area_id == user_data["current_area"]
                
                if current:
                    status = "📍 Current Location"
                elif unlocked:
                    status = "✅ Unlocked"
                else:
                    status = f"🔒 Locked - {area['unlock_cost']} PsyCoins"
                
                embed.add_field(
                    name=f"{area['name']}",
                    value=f"{area['description']}\n**Status:** {status}",
                    inline=False
                )
            
            embed.set_footer(text="💡 Use the dropdown below to travel or unlock areas!")
            
            view = AreaSelectView(self, user_data)
            await interaction.response.send_message(embed=embed, view=view)
        except Exception as e:
            print(f"[FISHING AREAS ERROR] {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def fish_encyclopedia_action(self, interaction: discord.Interaction, rarity: Optional[str] = None):
        """View fish encyclopedia with rarity filter and pagination"""
        # Get all fish
        fish_list = []
        for fish_id, fish in self.fish_types.items():
            fish_list.append((fish_id, fish))
        
        # Sort by value
        fish_list.sort(key=lambda x: x[1]["value"], reverse=True)
        
        # Create encyclopedia view with rarity filter + pagination
        view = EncyclopediaView(self, fish_list, rarity)
        
        # If rarity specified, filter now
        if rarity:
            view.fish_list = [(fid, f) for fid, f in fish_list if f["rarity"].lower() == rarity.lower()]
        
        embed = view.get_embed()
        await interaction.response.send_message(embed=embed, view=view)
    
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
        
        embed = EmbedBuilder.create(
            title=f"📊 {interaction.user.display_name}'s Fishing Stats",
            color=Colors.FISHING
        )
        
        embed.add_field(name="🎣 Total Catches", value=str(user_data["total_catches"]), inline=True)
        embed.add_field(name="💰 Total Value", value=f"{user_data['total_value']} coins", inline=True)
        embed.add_field(name="🐟 Species", value=f"{len(user_data['fish_caught'])}/{len(self.fish_types)}", inline=True)
        embed.add_field(name="⚖️ Biggest Catch", value=f"{biggest_catch or 'None'} ({biggest_weight}kg)", inline=True)
        embed.add_field(name="✨ Rarest Catch", value=rarest_catch or "None", inline=True)
        embed.add_field(name="📍 Current Area", value=self.areas[user_data["current_area"]]["name"], inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== TOURNAMENT SYSTEM ====================
    # Tournament commands are owner-only via owner.py
    # This section contains helper functions for tournament management
    
    async def end_tournament(self, guild_id: str):
        """End a tournament and announce winners"""
        if guild_id not in self.active_tournaments:
            return
        
        tournament = self.active_tournaments[guild_id]
        
        if not tournament['participants']:
            channel = self.bot.get_channel(tournament['channel_id'])
            if channel:
                await channel.send("🎣 Tournament ended with no participants!")
            del self.active_tournaments[guild_id]
            return
        
        # Determine winners
        mode = tournament['mode']
        participants = tournament['participants']
        
        if mode == "biggest":
            sorted_players = sorted(
                participants.items(),
                key=lambda x: x[1].get('biggest_weight', 0),
                reverse=True
            )
        elif mode == "most":
            sorted_players = sorted(
                participants.items(),
                key=lambda x: x[1].get('count', 0),
                reverse=True
            )
        elif mode == "rarest":
            rarity_values = {"Common": 1, "Uncommon": 2, "Rare": 3, "Epic": 4, "Legendary": 5, "Mythic": 6}
            sorted_players = sorted(
                participants.items(),
                key=lambda x: rarity_values.get(x[1].get('rarest_rarity', 'Common'), 0),
                reverse=True
            )
        
        # Create results embed
        embed = discord.Embed(
            title="🏆 Fishing Tournament Results!",
            description=f"**Mode:** {tournament['mode_name']}\n"
                       f"**Participants:** {len(participants)}\n\n"
                       f"**🥇 Winners:**",
            color=discord.Color.gold()
        )
        
        # Award prizes
        prizes = [1000, 500, 250]  # 1st, 2nd, 3rd place
        economy_cog = self.bot.get_cog("Economy")
        
        for idx, (user_id, data) in enumerate(sorted_players[:3]):
            user = await self.bot.fetch_user(int(user_id))
            medal = ["🥇", "🥈", "🥉"][idx]
            
            if mode == "biggest":
                score = f"{data.get('biggest_weight', 0)}kg"
            elif mode == "most":
                score = f"{data.get('count', 0)} fish"
            elif mode == "rarest":
                rarest_fish_name = data.get('rarest_fish')
                rarest_rarity = data.get('rarest_rarity', 'Common')
                if rarest_fish_name and rarest_fish_name != 'None':
                    score = f"{rarest_fish_name} ({rarest_rarity})"
                else:
                    score = 'No catches yet'
            
            embed.add_field(
                name=f"{medal} {user.display_name}",
                value=f"**Score:** {score}\n**Prize:** {prizes[idx]} coins",
                inline=False
            )
            
            # Award coins
            if economy_cog:
                economy_cog.add_coins(int(user_id), prizes[idx], "fishing_tournament")
        
        # Send results
        channel = self.bot.get_channel(tournament['channel_id'])
        if channel:
            await channel.send(embed=embed)
        
        # Cleanup
        del self.active_tournaments[guild_id]
    
    def record_tournament_catch(self, guild_id: str, user_id: int, fish_id: str, weight: float):
        """Record a catch for tournament tracking"""
        if not hasattr(self, 'active_tournaments'):
            return
        
        guild_id_str = str(guild_id)
        if guild_id_str not in self.active_tournaments:
            return
        
        tournament = self.active_tournaments[guild_id_str]
        user_id_str = str(user_id)
        
        if user_id_str not in tournament['participants']:
            tournament['participants'][user_id_str] = {
                'count': 0,
                'biggest_weight': 0,
                'biggest_fish': None,
                'rarest_rarity': 'Common',
                'rarest_fish': None
            }
        
        player_data = tournament['participants'][user_id_str]
        fish_data = self.fish_types[fish_id]
        
        # Update count
        player_data['count'] += 1
        
        # Update biggest
        if weight > player_data['biggest_weight']:
            player_data['biggest_weight'] = weight
            player_data['biggest_fish'] = fish_data['name']
        
        # Update rarest
        rarity_order = {"Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 3, "Legendary": 4, "Mythic": 5}
        if rarity_order.get(fish_data['rarity'], 0) > rarity_order.get(player_data['rarest_rarity'], 0):
            player_data['rarest_rarity'] = fish_data['rarity']
            player_data['rarest_fish'] = fish_data['name']
    
    async def start_random_tournament(self, guild_id: int, channel_id: int, mode: str = None, duration: int = None):
        """Start a random tournament in a guild"""
        guild_id_str = str(guild_id)
        
        # Check if tournament already running
        if guild_id_str in self.active_tournaments:
            return
        
        # Random or specified tournament parameters
        if mode:
            mode_names = {
                "biggest": "🏆 Biggest Fish",
                "most": "📊 Most Fish",
                "rarest": "✨ Rarest Fish"
            }
            mode_value = mode
            mode_name = mode_names.get(mode, "🏆 Biggest Fish")
        else:
            modes = [
                ("biggest", "🏆 Biggest Fish"),
                ("most", "📊 Most Fish"),
                ("rarest", "✨ Rarest Fish")
            ]
            mode_value, mode_name = random.choice(modes)
        
        if duration is None:
            duration = random.randint(30, 180)  # 30min-3h for auto tournaments (rare!)
        
        # Create tournament
        end_time = datetime.now() + timedelta(minutes=duration)
        tournament_data = {
            'mode': mode_value,
            'mode_name': mode_name,
            'host': None,  # Auto-generated
            'participants': {},
            'end_time': end_time,
            'duration': duration,
            'channel_id': channel_id,
            'auto_generated': True
        }
        
        self.active_tournaments[guild_id_str] = tournament_data
        
        # Announce tournament
        channel = self.bot.get_channel(channel_id)
        if channel:
            # Format duration nicely
            if duration >= 60:
                hours = duration // 60
                minutes = duration % 60
                duration_text = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
            else:
                duration_text = f"{duration} minutes"
            
            embed = discord.Embed(
                title="🎣 Rare Fishing Tournament Started!",
                description=f"**Mode:** {mode_name}\n"
                           f"**Duration:** {duration_text}\n"
                           f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                           f"🎉 **An extremely rare tournament appeared!**\n"
                           f"⚠️ Tournaments are very rare (6-12h intervals, 10% chance) - don't miss this!\n\n"
                           f"Use `/fish cast` to participate!\n"
                           f"All catches count automatically.\n\n",
                color=discord.Color.gold()
            )
            
            if mode_value == "biggest":
                embed.add_field(name="🏆 Goal", value="Catch the heaviest fish!", inline=False)
            elif mode_value == "most":
                embed.add_field(name="🏆 Goal", value="Catch the most fish!", inline=False)
            elif mode_value == "rarest":
                embed.add_field(name="🏆 Goal", value="Catch the rarest fish!", inline=False)
            
            embed.add_field(name="💰 Prizes", value="🥇 1000 coins\n🥈 500 coins\n🥉 250 coins", inline=False)
            embed.set_footer(text=f"Tournament ends in {duration_text}!")
            
            await channel.send(embed=embed)
        
        # Schedule tournament end
        await asyncio.sleep(duration * 60)
        await self.end_tournament(guild_id_str)
    
    async def random_tournament_loop(self):
        """Background task to randomly start tournaments"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Wait 6-12 hours between tournaments (much rarer)
                wait_time = random.randint(21600, 43200)  # 6-12 hours in seconds
                await asyncio.sleep(wait_time)
                
                # Get all guilds and pick random ones to host tournaments
                for guild in self.bot.guilds:
                    # 10% chance per guild (rare)
                    if random.random() < 0.1:
                        # Check if admin has set a tournament channel
                        guild_config = self.get_guild_config(guild.id)
                        
                        # Only start tournament if channel is configured
                        if guild_config.get("tournament_channel"):
                            channel = self.bot.get_channel(guild_config["tournament_channel"])
                            if channel and channel.permissions_for(guild.me).send_messages:
                                asyncio.create_task(self.start_random_tournament(guild.id, channel.id))
                
            except Exception as e:
                print(f"[FISHING] Error in random tournament loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start random tournament task when bot is ready"""
        if not self.random_tournament_task or self.random_tournament_task.done():
            self.random_tournament_task = asyncio.create_task(self.random_tournament_loop())
            print("[FISHING] Random tournament system started!")

    # ==================== PREFIX COMMAND ====================
    @commands.command(name="fish", aliases=["fishing"])
    async def fish_prefix(self, ctx, action: str = "help"):
        """Fish with prefix command
        
        Usage:
        {prefix}fish - Show fishing help
        {prefix}fish cast - Cast your fishing line
        {prefix}fish inventory - View your fish collection
        {prefix}fish shop - Buy fishing equipment
        {prefix}fish areas - View fishing areas
        {prefix}fish encyclopedia - View all fish types
        {prefix}fish stats - View your fishing statistics
        """
        action = action.lower()
        
        if action == "help":
            # Create a fake interaction for the help command
            prefix = self.bot.command_prefix
            embed = discord.Embed(
                title="🎣 Fishing System - Interactive Minigame!",
                description=f"Catch fish in various locations and build your collection!\n"
                           f"Now featuring an **interactive minigame** - align your rod with the fish and reel it in!",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📋 Commands",
                value=f"**{prefix}fish cast** - Cast your line (start minigame)\n"
                     f"**{prefix}fish inventory** - View your collection\n"
                     f"**{prefix}fish shop** - Purchase equipment & bait\n"
                     f"**{prefix}fish areas** - View locations & travel\n"
                     f"**{prefix}fish encyclopedia** - See all fish types\n"
                     f"**{prefix}fish stats** - View your statistics",
                inline=False
            )
            
            embed.add_field(
                name="🎮 Minigame Tips",
                value="• Use ⬅️ ➡️ buttons to move your rod\n"
                     "• Align EXACTLY with the fish (must be 🟢)\n"
                     "• Press 🎣 to reel in when aligned perfectly\n"
                     "• Fish moves automatically - timing is key!\n"
                     "• Rarer fish = harder difficulty (more catches needed, fish moves faster)",
                inline=False
            )
            
            embed.add_field(
                name="🌊 Areas",
                value="Unlock new areas with better equipment!\n"
                     "Each area has unique fish and treasures.",
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        elif action == "cast":
            await ctx.send("⚠️ Use `/fish cast` (slash command) to start fishing!")
        
        elif action in ["inventory", "inv", "collection"]:
            await ctx.send("⚠️ Use `/fish inventory` (slash command) to view your collection!")
        
        elif action == "shop":
            await ctx.send("⚠️ Use `/fish shop` (slash command) to buy equipment!")
        
        elif action == "areas":
            await ctx.send("⚠️ Use `/fish areas` (slash command) to view locations!")
        
        elif action in ["encyclopedia", "enc", "guide"]:
            await ctx.send("⚠️ Use `/fish encyclopedia` (slash command) to see all fish!")
        
        elif action == "stats":
            await ctx.send("⚠️ Use `/fish stats` (slash command) to view statistics!")
        
        else:
            await ctx.send(f"❌ Unknown action `{action}`. Use `{self.bot.command_prefix}fish` for help!")

async def setup(bot):
    await bot.add_cog(Fishing(bot))
