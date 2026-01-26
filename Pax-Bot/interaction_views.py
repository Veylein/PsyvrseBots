"""
Discord UI Views and Buttons for Interactive Bot Features
Provides button-based interfaces for duels, gardens, teams, towns, mining, and player shops
"""

import discord
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class SessionManager:
    """Manages active UI interaction sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
    
    def create_session(self, key: str, session_data: Any):
        """Create a new session"""
        self.sessions[key] = session_data
        self.locks[key] = asyncio.Lock()
    
    def get_session(self, key: str) -> Optional[Any]:
        """Get session data"""
        return self.sessions.get(key)
    
    async def update_session(self, key: str, session_data: Any):
        """Update session data with lock"""
        if key in self.locks:
            async with self.locks[key]:
                self.sessions[key] = session_data
    
    def delete_session(self, key: str):
        """Delete a session and its lock"""
        self.sessions.pop(key, None)
        self.locks.pop(key, None)
    
    def get_lock(self, key: str) -> Optional[asyncio.Lock]:
        """Get the lock for a session"""
        return self.locks.get(key)


class DuelView(View):
    """Interactive buttons for duel combat - IMPROVED with simplified names"""
    
    def __init__(self, duel_data: Dict[str, Any], session_key: str, session_manager: SessionManager):
        super().__init__(timeout=600)
        self.duel_data = duel_data
        self.session_key = session_key
        self.session_manager = session_manager
        self.message = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow participants to use buttons"""
        is_participant = interaction.user.id in [
            self.duel_data["challenger"],
            self.duel_data["challenged"]
        ]
        
        if not is_participant:
            await interaction.response.send_message("❌ You're not in this duel!", ephemeral=True)
            return False
        
        # Check turn
        current_turn = self.duel_data.get("turn")
        if current_turn and interaction.user.id != current_turn:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return False
        
        return True
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                
                embed = discord.Embed(
                    title="⏰ Duel Expired",
                    description="This duel has timed out due to inactivity.",
                    color=discord.Color.dark_grey()
                )
                await self.message.edit(embed=embed, view=self)
            except:
                pass
        
        self.session_manager.delete_session(self.session_key)
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger, custom_id="duel_attack")
    async def attack_button(self, interaction: discord.Interaction, button: Button):
        """Attack button - Shows simplified attack list"""
        await interaction.response.send_message(
            "⚔️ **How to Attack:**\n\n"
            "**Quick Method:**\n"
            "`P!duel attack VW1` - Use attack code (fast!)\n\n"
            "**Full Method:**\n"
            "`P!duel attack Verdant Windblade Emerald Laceration`\n\n"
            "💡 **TIP:** Use `P!weapons` to see your attack codes!\n"
            "📚 New? Try `P!dueltutorial` for a complete guide!",
            ephemeral=True
        )
    
    @discord.ui.button(label="💚 Items", style=discord.ButtonStyle.success, custom_id="duel_heal")
    async def heal_button(self, interaction: discord.Interaction, button: Button):
        """Items button - Shows how to use items in duel"""
        await interaction.response.send_message(
            "💚 **Using Items in Duels:**\n\n"
            "**Healing:**\n"
            "`P!duel heal <item>` - Heal yourself\n\n"
            "**Potions (use BEFORE duel):**\n"
            "`P!potion drink <potion>` - Activate potion effect\n\n"
            "**Artifacts:**\n"
            "Equipped automatically for HP bonus!\n\n"
            "**Pet Attacks:**\n"
            "`P!pet attack` - Use your pet's special move!\n\n"
            "💡 See `P!inv` for all your items!",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏃 Forfeit", style=discord.ButtonStyle.secondary, custom_id="duel_run")
    async def run_button(self, interaction: discord.Interaction, button: Button):
        """Forfeit button - shows warning"""
        await interaction.response.send_message(
            "⚠️ **Forfeit Duel?**\n\n"
            "You'll lose:\n"
            "• The duel\n"
            "• 100 chi penalty\n\n"
            "To confirm: `P!duel run`",
            ephemeral=True
        )
    
    @discord.ui.button(label="📚 Help", style=discord.ButtonStyle.primary, custom_id="duel_spectate")
    async def spectate_button(self, interaction: discord.Interaction, button: Button):
        """Help button - Quick reference"""
        if interaction.user.id in [self.duel_data["challenger"], self.duel_data["challenged"]]:
            await interaction.response.send_message(
                "⚔️ **Quick Duel Guide:**\n\n"
                "**Attack:** `P!duel attack <code>` (e.g., VW1)\n"
                "**Heal:** `P!duel heal <item>`\n"
                "**Pet:** `P!pet attack`\n"
                "**Forfeit:** `P!duel run`\n\n"
                "💡 Use `P!weapons` to see attack codes\n"
                "📚 Full tutorial: `P!dueltutorial`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "👀 **Spectator Guide:**\n\n"
                "**Bet:** `P!duel bet <amount> @duelist`\n"
                "Win = 2x your bet!\n"
                "Lose = Lose your bet\n\n"
                "Enjoy the show! 🍿",
                ephemeral=True
            )


class GardenView(View):
    """Interactive buttons for garden management - FULLY FUNCTIONAL"""
    
    def __init__(self, user_id: int, chi_data: Dict, gardens_data: Dict, garden_shop_items: Dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.chi_data = chi_data
        self.gardens_data = gardens_data
        self.garden_shop_items = garden_shop_items
        self.message = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the garden owner to use buttons"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your garden!", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="🌱 Plant Seeds", style=discord.ButtonStyle.success, custom_id="garden_plant")
    async def plant_button(self, interaction: discord.Interaction, button: Button):
        """Plant seeds button with dropdown - FUNCTIONAL"""
        user_id_str = str(self.user_id)
        
        if user_id_str not in self.gardens_data:
            await interaction.response.send_message("❌ You don't have a garden yet! Use `P!garden create` to start.", ephemeral=True)
            return
        
        garden = self.gardens_data[user_id_str]
        user_inventory = self.chi_data.get(user_id_str, {}).get("garden_inventory", {})
        
        # Check for seeds
        available_seeds = []
        for seed_name, quantity in user_inventory.items():
            if seed_name in self.garden_shop_items.get("seeds", {}) and quantity > 0:
                available_seeds.append(seed_name)
        
        if not available_seeds:
            await interaction.response.send_message(
                "❌ You don't have any seeds!\nBuy seeds from the Garden Shop using `P!gshop`",
                ephemeral=True
            )
            return
        
        # Create dropdown menu for seed selection
        seed_options = []
        for seed in available_seeds[:25]:  # Discord limit
            seed_info = self.garden_shop_items["seeds"][seed]
            quantity = user_inventory[seed]
            seed_options.append(
                discord.SelectOption(
                    label=f"{seed} (x{quantity})",
                    value=seed,
                    emoji=seed_info.get("emoji", "🌱")
                )
            )
        
        select_menu = Select(
            placeholder="Choose a seed to plant...",
            options=seed_options,
            custom_id=f"plant_seed_{self.user_id}"
        )
        
        async def seed_callback(select_interaction):
            selected_seed = select_menu.values[0]
            seed_info = self.garden_shop_items["seeds"][selected_seed]
            user_inv_qty = user_inventory.get(selected_seed, 0)
            
            # Show planting instructions instead of actually planting
            await select_interaction.response.send_message(
                f"🌱 **Plant {seed_info.get('emoji', '🌱')} {selected_seed}**\n\n"
                f"You have **{user_inv_qty}** seeds in your inventory.\n\n"
                f"**To plant:**\n"
                f"• `P!garden plant {selected_seed}` - Plant 1 seed\n"
                f"• `P!garden plant {selected_seed} 5` - Plant 5 seeds\n\n"
                f"Growth time: **{seed_info.get('grow_time_minutes', 60)} minutes**",
                ephemeral=True
            )
        
        select_menu.callback = seed_callback
        view = View(timeout=60)
        view.add_item(select_menu)
        
        await interaction.response.send_message("Select a seed to plant:", view=view, ephemeral=True)
    
    @discord.ui.button(label="💧 Water Plants", style=discord.ButtonStyle.primary, custom_id="garden_water")
    async def water_button(self, interaction: discord.Interaction, button: Button):
        """Water plants button - FUNCTIONAL"""
        await interaction.response.send_message(
            "💧 **Watering System**\n\nUse these commands to water your plants:\n• `P!garden water` - Water all plants\n• `P!garden water <plant_name>` - Water specific plant\n\nWatering requires watering tools from the Garden Shop!",
            ephemeral=True
        )
    
    @discord.ui.button(label="✨ Harvest Chi", style=discord.ButtonStyle.success, custom_id="garden_harvest")
    async def harvest_button(self, interaction: discord.Interaction, button: Button):
        """Harvest chi button - FUNCTIONAL"""
        await interaction.response.send_message(
            "✨ **Harvest System**\n\nUse these commands to harvest:\n• `P!garden harvest <plant_name>` - Harvest specific plant type\n• `P!garden harvest all` - Harvest all ready plants\n\nReady plants are marked with ✅ in your garden!",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏪 Shop", style=discord.ButtonStyle.secondary, custom_id="garden_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        """Garden shop button - Shows shop"""
        embed = discord.Embed(
            title="🌸 Garden Shop",
            description="Buy seeds and tools for your garden!",
            color=discord.Color.green()
        )
        
        tools_text = []
        tool_idx = 1
        for name, info in self.garden_shop_items.get("tools", {}).items():
            tools_text.append(f"**G{tool_idx}.** {info['emoji']} **{name}** - {info['cost']:,} chi")
            tool_idx += 1
        
        seeds_text = []
        for name, info in self.garden_shop_items.get("seeds", {}).items():
            seeds_text.append(f"**G{tool_idx}.** {info['emoji']} **{name}** - {info['cost']:,} chi")
            tool_idx += 1
        
        if tools_text:
            embed.add_field(name="🧰 Tools", value="\n".join(tools_text), inline=False)
        if seeds_text:
            embed.add_field(name="🌱 Seeds", value="\n".join(seeds_text), inline=False)
        
        embed.set_footer(text="Use P!garden shop buy <ID> <quantity> to purchase")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📋 Help", style=discord.ButtonStyle.secondary, custom_id="garden_help")
    async def help_button(self, interaction: discord.Interaction, button: Button):
        """Garden help button"""
        embed = discord.Embed(
            title="🌸 Garden Command Help",
            description="All available garden commands:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🌱 Basic Commands",
            value="• `P!garden` - View your garden\n• `P!garden shop` - View shop\n• `P!garden shop buy <ID> <qty>` - Buy items\n• `P!inv` - View full inventory",
            inline=False
        )
        
        embed.add_field(
            name="🌿 Planting & Harvesting",
            value="• `P!garden plant <seed> <qty>` - Plant seeds\n• `P!garden harvest <plant>` - Harvest plant\n• `P!garden harvest all` - Harvest all ready plants",
            inline=False
        )
        
        embed.add_field(
            name="💧 Watering & Care",
            value="• `P!garden water` - Water all plants\n• `P!garden water <plant>` - Water specific plant\n• Water requires tools from shop!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ShopView(View):
    """Interactive buttons for shop purchases - FULLY FUNCTIONAL"""
    
    def __init__(self, user_id: int, chi_data: Dict, shop_data: Dict, shop_name: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.chi_data = chi_data
        self.shop_data = shop_data
        self.shop_name = shop_name
        self.message = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow only the user who opened the shop"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your shop menu!", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="🛒 Buy Item", style=discord.ButtonStyle.success, custom_id="shop_buy")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        """Buy item button with dropdown - FUNCTIONAL"""
        user_id_str = str(self.user_id)
        
        if user_id_str not in self.chi_data:
            self.chi_data[user_id_str] = {"chi": 0, "rebirths": 0, "purchased_items": []}
        
        user_chi = self.chi_data[user_id_str].get("chi", 0)
        user_rebirths = self.chi_data[user_id_str].get("rebirths", 0)
        
        # Build purchase options based on shop type
        purchase_options = []
        
        if "items" in self.shop_data:  # Chi Shop / Rebirth Shop format
            for idx, item in enumerate(self.shop_data["items"][:25], 1):  # Discord limit
                # Check if already owned (for chi shop)
                already_owned = item["name"] in self.chi_data[user_id_str].get("purchased_items", [])
                
                # Check if affordable
                if self.shop_name == "Chi Shop":
                    can_afford = user_chi >= item["cost"] and not already_owned
                    status = "✅" if can_afford else ("🔒 Owned" if already_owned else f"🔒 Need {item['cost']:,} chi")
                else:  # Rebirth Shop
                    can_afford = user_rebirths >= item["cost"]
                    status = "✅" if can_afford else f"🔒 Need {item['cost']} rebirth(s)"
                
                purchase_options.append(
                    discord.SelectOption(
                        label=f"{item['name']} - {item['cost']:,} {item.get('currency', 'chi')}",
                        value=str(idx-1),
                        description=status,
                        emoji=item.get("emoji", "📦")
                    )
                )
        
        if not purchase_options:
            await interaction.response.send_message("❌ No items available for purchase!", ephemeral=True)
            return
        
        select_menu = Select(
            placeholder="Choose an item to buy...",
            options=purchase_options,
            custom_id=f"buy_item_{self.user_id}"
        )
        
        async def purchase_callback(select_interaction):
            selected_idx = int(select_menu.values[0])
            item = self.shop_data["items"][selected_idx]
            
            # Verify purchase
            if self.shop_name == "Chi Shop":
                if item["name"] in self.chi_data[user_id_str].get("purchased_items", []):
                    await select_interaction.response.send_message(f"❌ You already own **{item['name']}**!", ephemeral=True)
                    return
                
                if self.chi_data[user_id_str].get("chi", 0) < item["cost"]:
                    await select_interaction.response.send_message(
                        f"❌ Not enough chi! You need **{item['cost']:,} chi** but only have **{self.chi_data[user_id_str].get('chi', 0):,} chi**",
                        ephemeral=True
                    )
                    return
                
                # Process purchase
                self.chi_data[user_id_str]["chi"] -= item["cost"]
                if "purchased_items" not in self.chi_data[user_id_str]:
                    self.chi_data[user_id_str]["purchased_items"] = []
                self.chi_data[user_id_str]["purchased_items"].append(item["name"])
                
                await select_interaction.response.send_message(
                    f"✅ **Purchase Successful!**\nYou bought **{item['name']}** for **{item['cost']:,} chi**!\n\n💎 Remaining Chi: **{self.chi_data[user_id_str]['chi']:,}**",
                    ephemeral=False
                )
            
            else:  # Rebirth Shop
                if self.chi_data[user_id_str].get("rebirths", 0) < item["cost"]:
                    await select_interaction.response.send_message(
                        f"❌ Not enough rebirths! You need **{item['cost']} rebirth(s)** but only have **{self.chi_data[user_id_str].get('rebirths', 0)}**",
                        ephemeral=True
                    )
                    return
                
                # Process purchase (rebirths are not deducted, they're milestones)
                if "purchased_items" not in self.chi_data[user_id_str]:
                    self.chi_data[user_id_str]["purchased_items"] = []
                
                if item["name"] not in self.chi_data[user_id_str]["purchased_items"]:
                    self.chi_data[user_id_str]["purchased_items"].append(item["name"])
                
                await select_interaction.response.send_message(
                    f"✅ **Purchase Successful!**\nYou bought **{item['name']}** with **{item['cost']} rebirth milestone**!\n\n♻️ Total Rebirths: **{self.chi_data[user_id_str]['rebirths']}**",
                    ephemeral=False
                )
        
        select_menu.callback = purchase_callback
        view = View(timeout=60)
        view.add_item(select_menu)
        
        await interaction.response.send_message(f"Select an item from the {self.shop_name}:", view=view, ephemeral=True)
    
    @discord.ui.button(label="💰 Check Balance", style=discord.ButtonStyle.primary, custom_id="shop_balance")
    async def balance_button(self, interaction: discord.Interaction, button: Button):
        """Check balance button"""
        user_id_str = str(self.user_id)
        
        if user_id_str not in self.chi_data:
            self.chi_data[user_id_str] = {"chi": 0, "rebirths": 0}
        
        chi = self.chi_data[user_id_str].get("chi", 0)
        rebirths = self.chi_data[user_id_str].get("rebirths", 0)
        
        await interaction.response.send_message(
            f"💎 **Your Balance:**\nChi: **{chi:,}**\nRebirths: **{rebirths}**",
            ephemeral=True
        )


class TeamView(View):
    """Interactive buttons for team management"""
    
    def __init__(self, team_id: int, is_leader: bool, user_id: int):
        super().__init__(timeout=180)
        self.team_id = team_id
        self.is_leader = is_leader
        self.user_id = user_id
        self.message = None
        
        if not is_leader:
            self.upgrade_button.disabled = True
            self.invite_button.disabled = True
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow team members to use buttons"""
        return interaction.user.id == self.user_id
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="📊 Team Info", style=discord.ButtonStyle.primary, custom_id="team_info")
    async def info_button(self, interaction: discord.Interaction, button: Button):
        """Team info button"""
        await interaction.response.send_message(
            "View team details with: `P!team info`",
            ephemeral=True
        )
    
    @discord.ui.button(label="👥 Invite Member", style=discord.ButtonStyle.success, custom_id="team_invite")
    async def invite_button(self, interaction: discord.Interaction, button: Button):
        """Invite member button (leader only)"""
        await interaction.response.send_message(
            "Invite members with: `P!team invite @user`\n*Leader only*",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏗️ Upgrade Base", style=discord.ButtonStyle.danger, custom_id="team_upgrade")
    async def upgrade_button(self, interaction: discord.Interaction, button: Button):
        """Upgrade base button (leader only)"""
        await interaction.response.send_message(
            "Upgrade your base with: `P!team upgrade <gym/arena>`\n*Leader only*",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏪 Team Shop", style=discord.ButtonStyle.secondary, custom_id="team_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        """Team shop button"""
        await interaction.response.send_message(
            "View team shop with: `P!tshop`\nBuy items with: `P!tshop buy <item_number>`",
            ephemeral=True
        )
    
    @discord.ui.button(label="🤝 Manage Relations", style=discord.ButtonStyle.primary, custom_id="team_relations")
    async def relations_button(self, interaction: discord.Interaction, button: Button):
        """Manage allies/enemies button"""
        await interaction.response.send_message(
            "**Manage Relations:**\n`P!team ally <team_name>` - Request alliance\n`P!team enemy <team_name>` - Declare rivalry\n*Leader only*",
            ephemeral=True
        )


class TownView(View):
    """Interactive buttons for town navigation"""
    
    def __init__(self, town_name: str, user_id: int):
        super().__init__(timeout=300)
        self.town_name = town_name
        self.user_id = user_id
        self.message = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow any user to navigate"""
        return True
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="🏪 Visit Shop", style=discord.ButtonStyle.primary, custom_id="town_shop")
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        """Shop button"""
        if self.town_name == "Panda Town":
            await interaction.response.send_message(
                "Visit shops:\n`P!cshop` - Chi Shop\n`P!rshop` - Rebirth Shop\n`P!gshop` - Garden Shop",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "`P!lusharmory` - Browse the Lushsoul Cavern armory",
                ephemeral=True
            )
    
    @discord.ui.button(label="⛏️ Go Mining", style=discord.ButtonStyle.success, custom_id="town_mine")
    async def mine_button(self, interaction: discord.Interaction, button: Button):
        """Mining button"""
        if self.town_name == "Lushsoul Cavern":
            await interaction.response.send_message(
                "Start mining with: `P!mine`\nMine for chi and rare items every 5 minutes!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Mining is only available in Lushsoul Cavern!\nTravel there with: `P!visit lushsoul`",
                ephemeral=True
            )
    
    @discord.ui.button(label="🗺️ Travel", style=discord.ButtonStyle.secondary, custom_id="town_travel")
    async def travel_button(self, interaction: discord.Interaction, button: Button):
        """Travel button"""
        if self.town_name == "Panda Town":
            await interaction.response.send_message(
                "Travel to: `P!visit lushsoul` - Lushsoul Cavern",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Travel to: `P!visit panda` - Panda Town",
                ephemeral=True
            )
    
    @discord.ui.button(label="ℹ️ Town Info", style=discord.ButtonStyle.primary, custom_id="town_info")
    async def info_button(self, interaction: discord.Interaction, button: Button):
        """Town info button"""
        await interaction.response.send_message(
            f"Use `P!visit {self.town_name.lower().split()[0]}` to see full town information",
            ephemeral=True
        )


class PlayerShopPriceModal(Modal):
    """Modal for entering item sale price"""
    
    def __init__(self, item_name: str, user_id: str, shop_id: str, chi_data: Dict, player_shops_data: Dict, save_data_func, save_shops_func, category: str = "Other"):
        super().__init__(title=f"Sell {item_name}")
        self.item_name = item_name
        self.user_id = user_id
        self.shop_id = shop_id
        self.chi_data = chi_data
        self.player_shops_data = player_shops_data
        self.save_data_func = save_data_func
        self.save_shops_func = save_shops_func
        self.category = category
        
        self.price_input = TextInput(
            label="Sale Price (in chi)",
            placeholder="Enter price between 1 and 1,000,000",
            min_length=1,
            max_length=7,
            required=True
        )
        self.add_item(self.price_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the listing when submitted"""
        try:
            price = int(self.price_input.value)
            if price <= 0 or price > 1000000:
                await interaction.response.send_message(
                    "❌ Price must be between 1 and 1,000,000 chi!",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid price! Please enter a number.",
                ephemeral=True
            )
            return
        
        # CRITICAL: Revalidate inventory ownership before listing
        inventory = self.chi_data[self.user_id].get("inventory", {})
        if self.item_name not in inventory or inventory[self.item_name] <= 0:
            await interaction.response.send_message(
                f"❌ You no longer have **{self.item_name}** in your inventory!",
                ephemeral=True
            )
            return
        
        # Get shop
        shop = self.player_shops_data["shops"][self.shop_id]
        
        # Check if already listed
        for listing in shop["listings"]:
            if listing["item_name"].lower() == self.item_name.lower():
                await interaction.response.send_message(
                    f"❌ **{self.item_name}** is already listed! Remove it first with `P!pshop remove {self.item_name}`",
                    ephemeral=True
                )
                return
        
        # Remove from inventory (now safe because we validated above)
        inventory[self.item_name] -= 1
        if inventory[self.item_name] <= 0:
            del inventory[self.item_name]
        
        # Add to shop
        shop["listings"].append({
            "item_name": self.item_name,
            "price": price,
            "quantity": 1,
            "category": self.category,
            "listed_at": str(datetime.now())
        })
        
        # Save data
        self.save_data_func()
        self.save_shops_func()
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Item Listed!",
            description=f"**{self.item_name}** is now for sale in your shop!",
            color=discord.Color.green()
        )
        embed.add_field(name="Price", value=f"{price:,} chi", inline=True)
        embed.add_field(name="Category", value=self.category, inline=True)
        embed.add_field(name="Shop", value=f"{shop['name']} ({self.shop_id})", inline=False)
        embed.set_footer(text=f"Buyers can purchase with: P!pshop buy {self.shop_id} {self.item_name}")
        
        await interaction.response.send_message(embed=embed)


class PlayerShopInventorySelect(View):
    """View with select menu for choosing inventory items to sell"""
    
    def __init__(self, user_id: str, inventory: Dict[str, int], shop_id: str, chi_data: Dict, player_shops_data: Dict, chi_shop_data: Dict, save_data_func, save_shops_func):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.inventory = inventory
        self.shop_id = shop_id
        self.chi_data = chi_data
        self.player_shops_data = player_shops_data
        self.chi_shop_data = chi_shop_data
        self.save_data_func = save_data_func
        self.save_shops_func = save_shops_func
        
        # Create select menu with inventory items
        options = []
        for item_name, quantity in sorted(inventory.items())[:25]:  # Discord max 25 options
            if quantity > 0:
                # Try to find category
                category = "Other"
                for cat, items in chi_shop_data.get("items", {}).items():
                    if isinstance(items, dict):
                        for item_data in items.values():
                            if item_data.get("name", "").lower() == item_name.lower():
                                category = cat.capitalize()
                                break
                
                qty_text = f" (x{quantity})" if quantity > 1 else ""
                options.append(
                    discord.SelectOption(
                        label=f"{item_name}{qty_text}",
                        value=item_name,
                        description=f"{category} item - Select to sell",
                        emoji="📦"
                    )
                )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="No items to sell",
                    value="none",
                    description="Your inventory is empty"
                )
            )
        
        select = Select(
            placeholder="Choose an item to sell...",
            options=options,
            custom_id="shop_item_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        # Add cancel button
        cancel_btn = Button(label="❌ Cancel", style=discord.ButtonStyle.secondary, custom_id="shop_cancel")
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle item selection"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ This is not your inventory!",
                ephemeral=True
            )
            return
        
        selected_item = interaction.data["values"][0]
        
        if selected_item == "none":
            await interaction.response.send_message(
                "❌ You don't have any items to sell!",
                ephemeral=True
            )
            return
        
        # Determine category
        category = "Other"
        for cat, items in self.chi_shop_data.get("items", {}).items():
            if isinstance(items, dict):
                for item_data in items.values():
                    if item_data.get("name", "").lower() == selected_item.lower():
                        category = cat.capitalize()
                        break
        
        # Show price modal
        modal = PlayerShopPriceModal(
            selected_item,
            self.user_id,
            self.shop_id,
            self.chi_data,
            self.player_shops_data,
            self.save_data_func,
            self.save_shops_func,
            category
        )
        await interaction.response.send_modal(modal)
    
    async def cancel_callback(self, interaction: discord.Interaction):
        """Handle cancellation"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ This is not your menu!",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("❌ Cancelled.", ephemeral=True)
        self.stop()
    
    async def on_timeout(self):
        """Disable view on timeout"""
        for item in self.children:
            item.disabled = True


session_manager = SessionManager()
