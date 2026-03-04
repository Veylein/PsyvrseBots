import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import sys
from utils import user_storage
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis
from utils import user_storage



def _parse_ts(s):
    """Parse ISO timestamp – handles both naive (old data) and tz-aware strings."""
    from datetime import datetime as _dt, timezone as _tz
    d = _dt.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=_tz.utc)


class ShopView(discord.ui.View):
    """Shop view with dropdown menu for purchasing"""
    
    def __init__(self, economy_cog, user):
        super().__init__(timeout=120)
        self.economy_cog = economy_cog
        self.user = user
        
        # Create select menu
        options = []
        for item_id, item in economy_cog.shop_items.items():
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    value=item_id,
                    description=f"{item['price']:,} PsyCoins - {item['description'][:50]}"
                )
            )
        
        select = discord.ui.Select(
            placeholder="Select an item to purchase...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return
        
        item_id = interaction.data["values"][0]
        item = self.economy_cog.shop_items[item_id]
        balance = self.economy_cog.get_balance(self.user.id)
        
        if balance < item["price"]:
            await interaction.response.send_message(
                f"❌ Not enough PsyCoins! You need **{item['price']:,}** but only have **{balance:,}**.",
                ephemeral=True
            )
            return
        
        # Process purchase
        if self.economy_cog.remove_coins(self.user.id, item["price"]):
            self.economy_cog.add_item(self.user.id, item_id, 1)
            
            embed = EmbedBuilder.success(
                "Purchase Successful!",
                f"You bought **{item['name']}** for **{item['price']:,} PsyCoins**"
            )
            embed.add_field(name="Remaining Balance", value=f"{self.economy_cog.get_balance(self.user.id):,} PsyCoins")
            
            if item_id == "card_box":
                embed.add_field(
                    name="💡 Tip",
                    value="Use `/use card_box` to open it and get a random card deck!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return False
        return True


class Economy(commands.Cog):
    """PsyCoins economy system - earn, spend, and manage your currency"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Use persistent directory if on Render with disk mounted
        # Otherwise use data directory
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        self.economy_file = os.path.join(data_dir, "economy.json")
        self.inventory_file = os.path.join(data_dir, "inventory.json")
        
        print(f"[ECONOMY] Data directory: {data_dir}")
        print(f"[ECONOMY] Economy file: {self.economy_file}")
        print(f"[ECONOMY] Inventory file: {self.inventory_file}")
        
        self.economy_data = self.load_economy()
        self.inventory_data = self.load_inventory()
        
        # Concurrency safety locks
        self.economy_lock = asyncio.Lock()
        self.inventory_lock = asyncio.Lock()
        
        # Dirty flags to batch saves
        self.economy_dirty = False
        self.inventory_dirty = False
        
        # Autosave task to ensure data is saved every 5 minutes
        self.autosave_task = None
    
    async def cog_load(self):
        """Called when cog is loaded - start autosave"""
        self.autosave_task = asyncio.create_task(self.autosave_loop())
        
        # Items available in the shop
        self.shop_items = {
            "luck_charm": {"name": "🍀 Luck Charm", "price": 500, "description": "Increases game win rates by 10%"},
            "xp_boost": {"name": "⚡ XP Boost", "price": 300, "description": "Double XP for 1 hour"},
            "pet_food": {"name": "🍖 Premium Pet Food", "price": 150, "description": "Instantly restore pet stats"},
            "energy_drink": {"name": "☕ Energy Drink", "price": 200, "description": "Restore 50 energy to your pet"},
            "mystery_box": {"name": "🎁 Mystery Box", "price": 1000, "description": "Random reward - could be anything!"},
            "streak_shield": {"name": "🛡️ Streak Shield", "price": 800, "description": "Protect your daily streak once"},
            "double_coins": {"name": "💰 Double Coins", "price": 1500, "description": "Double coin rewards for 24 hours"},
            "card_box": {"name": "🎴 Card Box", "price": 2500, "description": "Random card deck (Classic/Dark/Platinum) for poker games!"},
        }
        
        # Card decks available from card boxes
        self.card_decks = {
            "classic": {"name": "🂡 Classic Deck", "rarity": "Common", "weight": 50},
            "dark": {"name": "🃏 Dark Deck", "rarity": "Rare", "weight": 30},
            "platinum": {"name": "💎 Platinum Deck", "rarity": "Legendary", "weight": 20}
        }

    def load_economy(self):
        if os.path.exists(self.economy_file):
            with open(self.economy_file, 'r') as f:
                return json.load(f)
        return {}

    async def save_economy(self):
        """Save economy data with error handling, backup, and concurrency safety"""
        if not self.economy_dirty:
            return  # No changes to save
        
        async with self.economy_lock:
            try:
                # Create backup before saving
                if os.path.exists(self.economy_file):
                    backup_file = f"{self.economy_file}.backup"
                    with open(self.economy_file, 'r') as f:
                        backup_data = f.read()
                    with open(backup_file, 'w') as f:
                        f.write(backup_data)
                
                # Save with atomic write (write to temp, then rename)
                temp_file = f"{self.economy_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(self.economy_data, f, indent=2)
                
                # Atomic rename (works on all platforms)
                if os.path.exists(self.economy_file):
                    os.replace(temp_file, self.economy_file)
                else:
                    os.rename(temp_file, self.economy_file)
                
                self.economy_dirty = False
                print(f"[ECONOMY] Saved {len(self.economy_data)} user balances")
            except Exception as e:
                print(f"❌ ERROR saving economy data: {e}")
                import traceback
                traceback.print_exc()
                # Try to restore from backup if save failed
                backup_file = f"{self.economy_file}.backup"
                if os.path.exists(backup_file):
                    print(f"[ECONOMY] Restoring from backup...")
                    with open(backup_file, 'r') as f:
                        self.economy_data = json.load(f)

    def load_inventory(self):
        if os.path.exists(self.inventory_file):
            with open(self.inventory_file, 'r') as f:
                return json.load(f)
        return {}

    async def save_inventory(self):
        """Save inventory data with error handling and concurrency safety"""
        if not self.inventory_dirty:
            return  # No changes to save
        
        async with self.inventory_lock:
            try:
                temp_file = f"{self.inventory_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(self.inventory_data, f, indent=2)
                
                if os.path.exists(self.inventory_file):
                    os.replace(temp_file, self.inventory_file)
                else:
                    os.rename(temp_file, self.inventory_file)
                
                self.inventory_dirty = False
            except Exception as e:
                print(f"❌ ERROR saving inventory data: {e}")
                import traceback
                traceback.print_exc()
    
    async def autosave_loop(self):
        """Automatically save economy data every 5 minutes"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(300)  # 5 minutes
            print("[ECONOMY] Auto-saving economy data...")
            await self.save_economy()
            await self.save_inventory()
    
    def cog_unload(self):
        """Ensure data is saved when cog unloads"""
        print("[ECONOMY] Saving data before cog unload...")
        # Note: Can't await in sync method, but Discord.py handles this
        # The bot will wait for async cleanup
        if hasattr(self, 'autosave_task'):
            self.autosave_task.cancel()
        # Schedule final save
        asyncio.create_task(self._final_save())
    
    async def _final_save(self):
        """Final save before unload"""
        await self.save_economy()
        await self.save_inventory()

    def get_balance(self, user_id: int) -> int:
        """Get user's PsyCoin balance"""
        user_key = str(user_id)
        if user_key not in self.economy_data:
            self.economy_data[user_key] = {
                "balance": 100,  # Starting balance
                "total_earned": 100,
                "total_spent": 0,
                "last_daily": None,
                "daily_streak": 0,
                "active_boosts": {},
                "username": None  # Cache username for leaderboard
            }
            self.economy_dirty = True
            asyncio.create_task(self.save_economy())
        return self.economy_data[user_key]["balance"]

    def add_coins(self, user_id: int, amount: int, reason: str = "transaction"):
        """Add PsyCoins to user's balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        
        # Check for double coins boost
        if self._has_active_boost(user_id, "double_coins"):
            amount *= 2
        
        self.economy_data[user_key]["balance"] += amount
        self.economy_data[user_key]["total_earned"] += amount
        self.economy_dirty = True
        return self.economy_data[user_key]["balance"]

    def remove_coins(self, user_id: int, amount: int) -> bool:
        """Remove PsyCoins from user's balance. Returns True if successful."""
        user_key = str(user_id)
        balance = self.get_balance(user_id)
        
        if balance >= amount:
            self.economy_data[user_key]["balance"] -= amount
            self.economy_data[user_key]["total_spent"] += amount
            self.economy_dirty = True
            return True
        return False

    def _has_active_boost(self, user_id: int, boost_type: str) -> bool:
        """Check if user has an active boost"""
        user_key = str(user_id)
        if user_key not in self.economy_data:
            return False
        
        boosts = self.economy_data[user_key].get("active_boosts", {})
        if boost_type in boosts:
            expiry = _parse_ts(boosts[boost_type])
            if discord.utils.utcnow() < expiry:
                return True
            else:
                # Remove expired boost
                del boosts[boost_type]
                self.economy_dirty = True
        return False

    def add_boost(self, user_id: int, boost_type: str, duration_hours: int, extend: bool = False):
        """Add or extend a temporary boost to user
        
        Args:
            user_id: User to give boost to
            boost_type: Type of boost (e.g., 'xp_boost', 'double_coins')
            duration_hours: Duration in hours
            extend: If True, extends existing boost. If False, replaces it.
        """
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        
        boosts = self.economy_data[user_key].get("active_boosts", {})
        
        if extend and boost_type in boosts:
            # Extend existing boost
            existing_expiry = _parse_ts(boosts[boost_type])
            if existing_expiry > discord.utils.utcnow():
                # Add time to existing boost
                new_expiry = existing_expiry + timedelta(hours=duration_hours)
            else:
                # Boost expired, start fresh
                new_expiry = discord.utils.utcnow() + timedelta(hours=duration_hours)
        else:
            # New boost or replace existing
            new_expiry = discord.utils.utcnow() + timedelta(hours=duration_hours)
        
        self.economy_data[user_key]["active_boosts"][boost_type] = new_expiry.isoformat()
        self.economy_dirty = True

    def get_inventory(self, user_id: int):
        """Get user's inventory"""
        user_key = str(user_id)
        if user_key not in self.inventory_data:
            self.inventory_data[user_key] = {}
            self.inventory_dirty = True
        return self.inventory_data[user_key]

    def add_item(self, user_id: int, item_id: str, quantity: int = 1):
        """Add item to user's inventory"""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        
        if item_id in inventory:
            inventory[item_id] += quantity
        else:
            inventory[item_id] = quantity
        
        self.inventory_dirty = True


    def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """Remove item from inventory. Returns True if successful."""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        
        if item_id in inventory and inventory[item_id] >= quantity:
            inventory[item_id] -= quantity
            if inventory[item_id] == 0:
                del inventory[item_id]
            self.inventory_dirty = True
            return True
        return False

    # ==================== GAME-SPECIFIC CURRENCIES ====================

    def get_fish_coins(self, user_id: int) -> int:
        """Get user's FishCoin balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        return self.economy_data[user_key].get("fish_coins", 0)

    def add_fish_coins(self, user_id: int, amount: int) -> int:
        """Add FishCoins to user's balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        self.economy_data[user_key]["fish_coins"] = self.economy_data[user_key].get("fish_coins", 0) + amount
        self.economy_dirty = True
        return self.economy_data[user_key]["fish_coins"]

    def remove_fish_coins(self, user_id: int, amount: int) -> bool:
        """Remove FishCoins. Returns True if successful."""
        user_key = str(user_id)
        current = self.get_fish_coins(user_id)
        if current >= amount:
            self.economy_data[user_key]["fish_coins"] = current - amount
            self.economy_dirty = True
            return True
        return False

    def get_mine_coins(self, user_id: int) -> int:
        """Get user's MineCoin balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        return self.economy_data[user_key].get("mine_coins", 0)

    def add_mine_coins(self, user_id: int, amount: int) -> int:
        """Add MineCoins to user's balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        self.economy_data[user_key]["mine_coins"] = self.economy_data[user_key].get("mine_coins", 0) + amount
        self.economy_dirty = True
        return self.economy_data[user_key]["mine_coins"]

    def remove_mine_coins(self, user_id: int, amount: int) -> bool:
        """Remove MineCoins. Returns True if successful."""
        user_key = str(user_id)
        current = self.get_mine_coins(user_id)
        if current >= amount:
            self.economy_data[user_key]["mine_coins"] = current - amount
            self.economy_dirty = True
            return True
        return False

    def get_farm_coins(self, user_id: int) -> int:
        """Get user's FarmCoin balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        return self.economy_data[user_key].get("farm_coins", 0)

    def add_farm_coins(self, user_id: int, amount: int) -> int:
        """Add FarmCoins to user's balance"""
        user_key = str(user_id)
        self.get_balance(user_id)  # Ensure user exists
        self.economy_data[user_key]["farm_coins"] = self.economy_data[user_key].get("farm_coins", 0) + amount
        self.economy_dirty = True
        return self.economy_data[user_key]["farm_coins"]

    def remove_farm_coins(self, user_id: int, amount: int) -> bool:
        """Remove FarmCoins. Returns True if successful."""
        user_key = str(user_id)
        current = self.get_farm_coins(user_id)
        if current >= amount:
            self.economy_data[user_key]["farm_coins"] = current - amount
            self.economy_dirty = True
            return True
        return False

    @commands.command(name="balance", aliases=["bal", "coins"])
    async def balance(self, ctx, member: Optional[discord.Member] = None):
        """Check your or someone else's PsyCoin balance"""
        await self._show_balance(member or ctx.author, ctx, None)

    @app_commands.command(name="balance", description="Check your PsyCoin balance")
    @app_commands.describe(member="User to check (defaults to yourself)")
    async def balance_slash(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        await self._show_balance(member or interaction.user, None, interaction)

    async def _show_balance(self, member, ctx, interaction):
        balance = self.get_balance(member.id)
        user_key = str(member.id)
        data = self.economy_data.get(user_key, {})
        
        # Cache username for leaderboard
        if data.get("username") != member.display_name:
            data["username"] = member.display_name
            self.economy_dirty = True
        
        # Calculate wealth tier
        if balance >= 1_000_000:
            tier = f"{Emojis.CROWN} **BILLIONAIRE**"
            tier_color = Colors.DIVINE
        elif balance >= 100_000:
            tier = f"{Emojis.DIAMOND} **Millionaire**"
            tier_color = Colors.LEGENDARY
        elif balance >= 50_000:
            tier = f"{Emojis.TROPHY} **High Roller**"
            tier_color = Colors.EPIC
        elif balance >= 10_000:
            tier = f"{Emojis.STAR} **Wealthy**"
            tier_color = Colors.RARE
        else:
            tier = f"{Emojis.COIN} **Getting Started**"
            tier_color = Colors.ECONOMY
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TREASURE} {member.display_name}'s Wallet",
            description=tier,
            color=tier_color,
            thumbnail=member.display_avatar.url,
            timestamp=True
        )
        
        # Main balance
        embed.add_field(
            name=f"{Emojis.COIN} Current Balance",
            value=f"```yaml\n{balance:,} PsyCoins\n```",
            inline=False
        )
        
        # Game-specific currencies
        fish_coins = self.get_fish_coins(member.id)
        mine_coins = self.get_mine_coins(member.id)
        farm_coins = self.get_farm_coins(member.id)
        embed.add_field(name="🐟 FishCoins", value=f"**{fish_coins:,}**", inline=True)
        embed.add_field(name="⛏️ MineCoins", value=f"**{mine_coins:,}**", inline=True)
        embed.add_field(name="🌾 FarmCoins", value=f"**{farm_coins:,}**", inline=True)
        
        # Stats grid
        total_earned = data.get('total_earned', 0)
        total_spent = data.get('total_spent', 0)
        embed.add_field(
            name=f"{Emojis.GIFT} Total Earned",
            value=f"**{EmbedBuilder.format_number(total_earned)}** coins",
            inline=True
        )
        embed.add_field(
            name=f"{Emojis.SHOP} Total Spent",
            value=f"**{EmbedBuilder.format_number(total_spent)}** coins",
            inline=True
        )
        
        # Daily streak with visual
        streak = data.get('daily_streak', 0)
        streak_emoji = Emojis.FIRE if streak > 0 else "❄️"
        embed.add_field(
            name=f"{streak_emoji} Daily Streak",
            value=f"**{streak}** days",
            inline=True
        )
        
        # Show active boosts with beautiful formatting
        boosts = data.get("active_boosts", {})
        active_boost_list = []
        for boost_type, expiry_str in boosts.items():
            expiry = _parse_ts(expiry_str)
            if discord.utils.utcnow() < expiry:
                time_left = expiry - discord.utils.utcnow()
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                boost_emoji = Emojis.SPARKLES if "xp" in boost_type else Emojis.DIAMOND
                active_boost_list.append(f"{boost_emoji} **{boost_type.replace('_', ' ').title()}** • `{hours}h {minutes}m`")
        
        if active_boost_list:
            embed.add_field(
                name=f"{Emojis.ROCKET} Active Boosts",
                value="\n".join(active_boost_list),
                inline=False
            )
        
        embed.set_footer(
            text=f"ID: {member.id} • Use L!daily to claim rewards!",
            icon_url=member.display_avatar.url
        )
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim your daily PsyCoin reward"""
        await self._claim_daily(ctx.author, ctx, None)

    @app_commands.command(name="daily", description="Claim your daily PsyCoin reward")
    async def daily_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._claim_daily(interaction.user, None, interaction)

    async def _claim_daily(self, user, ctx, interaction):
        user_key = str(user.id)
        self.get_balance(user.id)  # Ensure user exists
        
        user_data = self.economy_data[user_key]
        
        # Cache username
        username = user.display_name if hasattr(user, 'display_name') else str(user)
        if user_data.get("username") != username:
            user_data["username"] = username
            self.economy_dirty = True
        
        last_daily = user_data.get("last_daily")
        
        now = discord.utils.utcnow()
        
        # Check if user can claim daily
        if last_daily:
            last_claim = _parse_ts(last_daily)
            time_diff = now - last_claim
            
            if time_diff.total_seconds() < 86400:  # 24 hours
                time_left = timedelta(seconds=86400) - time_diff
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                msg = f"⏰ You've already claimed your daily reward! Come back in **{hours}h {minutes}m**"
                if interaction:
                    await interaction.followup.send(msg)
                else:
                    await ctx.send(msg)
                return
            
            # Check streak
            if time_diff.total_seconds() < 172800:  # Less than 48 hours
                user_data["daily_streak"] += 1
            else:
                # Check for streak shield
                if self.remove_item(user.id, "streak_shield"):
                    msg_shield = "🛡️ Your streak was saved by a Streak Shield!\n"
                else:
                    user_data["daily_streak"] = 1
                    msg_shield = ""
        else:
            user_data["daily_streak"] = 1
            msg_shield = ""
        
        # Calculate reward
        base_reward = 100
        streak_bonus = min(user_data["daily_streak"] * 10, 500)  # Max 500 bonus
        total_reward = base_reward + streak_bonus
        
        user_data["last_daily"] = now.isoformat()
        self.add_coins(user.id, total_reward, "daily_reward")
        
        desc = f"{msg_shield if 'msg_shield' in locals() else ''}You received **{total_reward:,} PsyCoins**!"
        embed = EmbedBuilder.success(
            "Daily Reward Claimed!",
            desc
        )
        embed.add_field(name="Base Reward", value=f"{base_reward} PsyCoins", inline=True)
        embed.add_field(name="Streak Bonus", value=f"+{streak_bonus} PsyCoins", inline=True)
        embed.add_field(name="Current Streak", value=f"🔥 {user_data['daily_streak']} days", inline=True)
        embed.add_field(name="New Balance", value=f"💰 {self.get_balance(user.id):,} PsyCoins", inline=False)

        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="shop")
    async def shop(self, ctx):
        """View the shop"""
        await self._show_shop(ctx, None)

    @app_commands.command(name="shop", description="Browse the PsyCoin shop")
    async def shop_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._show_shop(None, interaction)

    async def _show_shop(self, ctx, interaction):
        embed = EmbedBuilder.economy(
            "PsyCoin Shop",
            "Purchase items with your PsyCoins! Use dropdown menu below to buy."
        )
        
        for item_id, item in self.shop_items.items():
            embed.add_field(
                name=f"{item['name']} - {item['price']:,} PsyCoins",
                value=f"{item['description']}\nID: `{item_id}`",
                inline=False
            )
        
        # Create dropdown select menu for purchasing
        view = ShopView(self, interaction.user if interaction else ctx.author)
        
        if interaction:
            await interaction.followup.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)

    @commands.command(name="buy")
    async def buy(self, ctx, item_id: str, quantity: int = 1):
        """Buy an item from the shop"""
        await self._buy_item(ctx.author, item_id, quantity, ctx, None)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_id="Item ID to purchase", quantity="Number of items to buy")
    async def buy_slash(self, interaction: discord.Interaction, item_id: str, quantity: int = 1):
        await interaction.response.defer()
        await self._buy_item(interaction.user, item_id, quantity, None, interaction)

    async def _buy_item(self, user, item_id, quantity, ctx, interaction):
        if item_id not in self.shop_items:
            msg = f"❌ Item `{item_id}` not found! Use `/shop` to see available items."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        item = self.shop_items[item_id]
        total_cost = item["price"] * quantity
        balance = self.get_balance(user.id)
        
        if balance < total_cost:
            msg = f"❌ Not enough PsyCoins! You need **{total_cost:,}** but only have **{balance:,}**."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        # Process purchase
        if self.remove_coins(user.id, total_cost):
            self.add_item(user.id, item_id, quantity)
            
            embed = EmbedBuilder.success(
                "Purchase Successful!",
                f"You bought **{quantity}x {item['name']}** for **{total_cost:,} PsyCoins**"
            )
            embed.add_field(name="Remaining Balance", value=f"{self.get_balance(user.id):,} PsyCoins")
            
            if interaction:
                await interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: Optional[discord.Member] = None):
        """View your or someone else's inventory"""
        await self._show_inventory(member or ctx.author, ctx, None)

    @app_commands.command(name="inventory", description="View your inventory")
    @app_commands.describe(member="User to check (defaults to yourself)")
    async def inventory_slash(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        await self._show_inventory(member or interaction.user, None, interaction)

    async def _show_inventory(self, member, ctx, interaction):
        inventory = self.get_inventory(member.id)
        
        if not inventory:
            # Fix nested quote syntax error
            current_user_id = ctx.author.id if ctx else interaction.user.id
            if member.id == current_user_id:
                msg = "Your inventory is empty!"
            else:
                msg = f"{member.display_name}'s inventory is empty!"
            
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        embed = EmbedBuilder.create(
            title=f"🎒 {member.display_name}'s Inventory",
            color=Colors.PRIMARY
        )
        
        for item_id, quantity in inventory.items():
            if item_id in self.shop_items:
                item = self.shop_items[item_id]
                embed.add_field(
                    name=f"{item['name']} x{quantity}",
                    value=item['description'],
                    inline=False
                )
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="use")
    async def use_item(self, ctx, item_id: str):
        """Use an item from your inventory"""
        await self._use_item(ctx.author, item_id, ctx, None)

    @app_commands.command(name="use", description="Use an item from your inventory")
    @app_commands.describe(item_id="Item ID to use")
    async def use_slash(self, interaction: discord.Interaction, item_id: str):
        await interaction.response.defer()
        await self._use_item(interaction.user, item_id, None, interaction)

    def get_user_card_deck(self, user_id: int) -> str:
        """Get user's currently equipped card deck"""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        return inventory.get("equipped_deck", "classic")
    
    def set_user_card_deck(self, user_id: int, deck_name: str):
        """Set user's equipped card deck"""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        inventory["equipped_deck"] = deck_name
        self.inventory_dirty = True
    
    def get_owned_decks(self, user_id: int) -> list:
        """Get list of card decks user owns"""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        owned = ["classic"]  # Everyone has classic
        
        for deck in ["dark", "platinum"]:
            if inventory.get(f"deck_{deck}", False):
                owned.append(deck)
        
        return owned
    
    def unlock_deck(self, user_id: int, deck_name: str):
        """Unlock a card deck for user"""
        user_key = str(user_id)
        inventory = self.get_inventory(user_id)
        inventory[f"deck_{deck_name}"] = True
        self.inventory_dirty = True

    async def _use_item(self, user, item_id, ctx, interaction):
        if not self.remove_item(user.id, item_id):
            msg = f"❌ You don't have a `{item_id}` in your inventory!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        # Handle different item effects
        if item_id == "xp_boost":
            self.add_boost(user.id, "xp_boost", 1)
            msg = "⚡ XP Boost activated! You'll earn double XP for 1 hour!"
        elif item_id == "double_coins":
            self.add_boost(user.id, "double_coins", 24)
            msg = "💰 Double Coins activated! You'll earn double PsyCoins for 24 hours!"
        elif item_id == "mystery_box":
            # Weighted random rewards (more common rewards appear more)
            rewards = [
                (100, "💰 100 PsyCoins"),
                (100, "💰 100 PsyCoins"),
                (100, "💰 100 PsyCoins"),
                (250, "💰 250 PsyCoins"),
                (250, "💰 250 PsyCoins"),
                (500, "💰 500 PsyCoins!"),
                (500, "💰 500 PsyCoins!"),
                (1000, "💰 1000 PsyCoins!"),
                (2000, "💰💰 2000 PsyCoins!!"),
                (5000, "💰💰💰 JACKPOT 5000 PsyCoins!!!"),
            ]
            reward_coins, reward_msg = random.choice(rewards)
            self.add_coins(user.id, reward_coins, "mystery_box")
            msg = f"🎁 Mystery Box opened! You got {reward_msg}"
        elif item_id in ["pet_food", "energy_drink"]:
            msg = f"✅ {self.shop_items[item_id]['name']} used! (Effect applied to pet system)"
        elif item_id == "luck_charm":
            self.add_boost(user.id, "luck_charm", 24)
            msg = "🍀 Luck Charm activated! Increased win rates for 24 hours!"
        elif item_id == "card_box":
            # Open card box - random card deck
            decks = list(self.card_decks.keys())
            weights = [self.card_decks[d]["weight"] for d in decks]
            drawn_deck = random.choices(decks, weights=weights, k=1)[0]
            
            deck_info = self.card_decks[drawn_deck]
            self.unlock_deck(user.id, drawn_deck)
            
            # Auto-equip if it's their first non-classic deck
            owned = self.get_owned_decks(user.id)
            if len(owned) == 2:  # Only classic + new deck
                self.set_user_card_deck(user.id, drawn_deck)
                equip_msg = " (Auto-equipped!)"
            else:
                equip_msg = f" Use `/equipdeck {drawn_deck}` to use it!"
            
            msg = f"🎴 **Card Box opened!**\n\nYou got: **{deck_info['name']}** ({deck_info['rarity']}){equip_msg}"
        else:
            msg = f"✅ You used {self.shop_items.get(item_id, {}).get('name', item_id)}!"
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @commands.command(name="give")
    async def give_coins(self, ctx, member: discord.Member, amount: int):
        """Give PsyCoins to another user"""
        await self._give_coins(ctx.author, member, amount, ctx, None)

    @app_commands.command(name="give", description="Give PsyCoins to another user")
    @app_commands.describe(member="User to give coins to", amount="Amount of PsyCoins to give")
    async def give_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer()
        await self._give_coins(interaction.user, member, amount, None, interaction)

    async def _give_coins(self, giver, receiver, amount, ctx, interaction):
        if giver.id == receiver.id:
            msg = "❌ You can't give coins to yourself!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        if amount <= 0:
            msg = "❌ Amount must be positive!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        if not self.remove_coins(giver.id, amount):
            msg = f"❌ You don't have enough PsyCoins! You need {amount:,} but only have {self.get_balance(giver.id):,}."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        self.add_coins(receiver.id, amount, "gift")
        
        msg = f"✅ You gave **{amount:,} PsyCoins** to {receiver.mention}!"
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """View the PsyCoin leaderboard"""
        await self._show_leaderboard(ctx.guild, ctx, None)

    @app_commands.command(name="coinleaderboard", description="View the PsyCoin leaderboard")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._show_leaderboard(interaction.guild, None, interaction)

    async def _show_leaderboard(self, guild, ctx, interaction):
        # Sort users by balance
        sorted_users = sorted(self.economy_data.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:10]
        
        embed = discord.Embed(
            title="🏆 PsyCoin Leaderboard",
            description="Top 10 richest users",
            color=discord.Color.gold()
        )
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            balance = data.get("balance", 0)
            streak = data.get("daily_streak", 0)
            cached_name = data.get("username", "Unknown User")
            
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
                
                # Update cached username if changed
                if cached_name != username:
                    data["username"] = username
                    self.economy_dirty = True
                
                embed.add_field(
                    name=f"{i}. {username}",
                    value=f"💰 {balance:,} PsyCoins | 🔥 {streak} day streak",
                    inline=False
                )
            except discord.NotFound:
                print(f"[ECONOMY] User {user_id} not found (left Discord or deleted account)")
                # Use cached username
                embed.add_field(
                    name=f"{i}. {cached_name}",
                    value=f"💰 {balance:,} PsyCoins | 🔥 {streak} day streak",
                    inline=False
                )
            except Exception as e:
                print(f"[ECONOMY] Error fetching user {user_id}: {e}")
                # Use cached username as fallback
                embed.add_field(
                    name=f"{i}. {cached_name}",
                    value=f"💰 {balance:,} PsyCoins | 🔥 {streak} day streak",
                    inline=False
                )
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    # ==================== CURRENCY CONVERSION SYSTEM ====================
    
    @app_commands.command(name="convert", description="Convert between PsyCoins and game currencies (FishCoins / MineCoins / FarmCoins)")
    @app_commands.choices(direction=[
        app_commands.Choice(name="💰 → 🐟  PsyCoin to FishCoin  (4 PSY = 1 FISH)", value="psy_to_fish"),
        app_commands.Choice(name="🐟 → 💰  FishCoin to PsyCoin  (1 FISH = 2 PSY)", value="fish_to_psy"),
        app_commands.Choice(name="💰 → ⛏️  PsyCoin to MineCoin  (5 PSY = 1 MINE)", value="psy_to_mine"),
        app_commands.Choice(name="⛏️ → 💰  MineCoin to PsyCoin  (1 MINE = 3 PSY)", value="mine_to_psy"),
        app_commands.Choice(name="💰 → 🌾  PsyCoin to FarmCoin  (4 PSY = 1 FARM)", value="psy_to_farm"),
        app_commands.Choice(name="🌾 → 💰  FarmCoin to PsyCoin  (1 FARM = 2 PSY)", value="farm_to_psy"),
    ])
    @app_commands.describe(
        direction="Conversion direction",
        amount="Amount of the SOURCE currency to convert"
    )
    async def convert_currency(self, interaction: discord.Interaction, direction: app_commands.Choice[str], amount: int):
        """Convert between PsyCoins and game-specific currencies"""

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return

        user_id = interaction.user.id

        # Rates: each tuple is (source_rate, target_rate) meaning source_rate of source = target_rate of target
        RATES = {
            "psy_to_fish": {
                "src_name": "PsyCoins", "src_emoji": "💰",
                "tgt_name": "FishCoins", "tgt_emoji": "🐟",
                "src_per_unit": 4, "tgt_per_unit": 1,
                "get_src": self.get_balance, "remove_src": self.remove_coins,
                "get_tgt": self.get_fish_coins, "add_tgt": self.add_fish_coins,
            },
            "fish_to_psy": {
                "src_name": "FishCoins", "src_emoji": "🐟",
                "tgt_name": "PsyCoins", "tgt_emoji": "💰",
                "src_per_unit": 1, "tgt_per_unit": 2,
                "get_src": self.get_fish_coins, "remove_src": self.remove_fish_coins,
                "get_tgt": self.get_balance, "add_tgt": lambda uid, a: self.add_coins(uid, a, "convert"),
            },
            "psy_to_mine": {
                "src_name": "PsyCoins", "src_emoji": "💰",
                "tgt_name": "MineCoins", "tgt_emoji": "⛏️",
                "src_per_unit": 5, "tgt_per_unit": 1,
                "get_src": self.get_balance, "remove_src": self.remove_coins,
                "get_tgt": self.get_mine_coins, "add_tgt": self.add_mine_coins,
            },
            "mine_to_psy": {
                "src_name": "MineCoins", "src_emoji": "⛏️",
                "tgt_name": "PsyCoins", "tgt_emoji": "💰",
                "src_per_unit": 1, "tgt_per_unit": 3,
                "get_src": self.get_mine_coins, "remove_src": self.remove_mine_coins,
                "get_tgt": self.get_balance, "add_tgt": lambda uid, a: self.add_coins(uid, a, "convert"),
            },
            "psy_to_farm": {
                "src_name": "PsyCoins", "src_emoji": "💰",
                "tgt_name": "FarmCoins", "tgt_emoji": "🌾",
                "src_per_unit": 4, "tgt_per_unit": 1,
                "get_src": self.get_balance, "remove_src": self.remove_coins,
                "get_tgt": self.get_farm_coins, "add_tgt": self.add_farm_coins,
            },
            "farm_to_psy": {
                "src_name": "FarmCoins", "src_emoji": "🌾",
                "tgt_name": "PsyCoins", "tgt_emoji": "💰",
                "src_per_unit": 1, "tgt_per_unit": 2,
                "get_src": self.get_farm_coins, "remove_src": self.remove_farm_coins,
                "get_tgt": self.get_balance, "add_tgt": lambda uid, a: self.add_coins(uid, a, "convert"),
            },
        }

        r = RATES[direction.value]
        # Calculate how much of source is needed for `amount` source units
        # and how much target the user receives
        # amount = source units to spend
        # target = (amount / src_per_unit) * tgt_per_unit
        # But for psy_to_xxx, amount is in psy (source) and target units = floor(amount / src_per_unit)
        # For xxx_to_psy, amount is in game coins (source) and target = amount * tgt_per_unit

        cost = amount  # source amount to spend
        received = (amount // r["src_per_unit"]) * r["tgt_per_unit"]

        if received <= 0:
            await interaction.response.send_message(
                f"❌ You need at least **{r['src_per_unit']} {r['src_name']}** to convert to 1 {r['tgt_name']}.",
                ephemeral=True
            )
            return

        current_src = r["get_src"](user_id)
        if current_src < cost:
            await interaction.response.send_message(
                f"❌ Not enough {r['src_emoji']} {r['src_name']}!\n"
                f"**Cost:** {cost:,} {r['src_name']}\n"
                f"**You have:** {current_src:,} {r['src_name']}\n"
                f"**Need:** {cost - current_src:,} more",
                ephemeral=True
            )
            return

        # Execute conversion
        r["remove_src"](user_id, cost)
        r["add_tgt"](user_id, received)
        await self.save_economy()

        embed = EmbedBuilder.success(
            "💱 Currency Converted!",
            f"Successfully exchanged {r['src_emoji']} **{cost:,} {r['src_name']}** → {r['tgt_emoji']} **{received:,} {r['tgt_name']}**"
        )
        embed.add_field(name=f"{r['src_emoji']} Spent", value=f"{cost:,} {r['src_name']}", inline=True)
        embed.add_field(name=f"{r['tgt_emoji']} Received", value=f"{received:,} {r['tgt_name']}", inline=True)
        embed.add_field(
            name="📊 New Balances",
            value=(
                f"💰 PsyCoins: **{self.get_balance(user_id):,}**\n"
                f"🐟 FishCoins: **{self.get_fish_coins(user_id):,}**\n"
                f"⛏️ MineCoins: **{self.get_mine_coins(user_id):,}**\n"
                f"🌾 FarmCoins: **{self.get_farm_coins(user_id):,}**"
            ),
            inline=False
        )
        embed.set_footer(text=f"Rate: {r['src_per_unit']} {r['src_name']} = {r['tgt_per_unit']} {r['tgt_name']}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="currencies", description="View all your currency balances")
    async def view_currencies(self, interaction: discord.Interaction):
        """View all currency balances including game-specific ones"""
        user_id = interaction.user.id
        user_key = str(user_id)

        if user_key not in self.economy_data:
            self.economy_data[user_key] = {"balance": 0, "daily_last": None, "daily_streak": 0}

        data = self.economy_data[user_key]

        embed = EmbedBuilder.create(
            title=f"💰 {interaction.user.display_name}'s Currencies",
            description="All your current currency balances across Ludus.",
            color=Colors.ECONOMY,
            thumbnail=interaction.user.display_avatar.url,
            timestamp=True
        )

        # === Main Currency ===
        embed.add_field(
            name="💰 PsyCoins  *(main currency)*",
            value=f"```yaml\n{data.get('balance', 0):,}\n```",
            inline=False
        )

        # === Game Currencies ===
        fish_coins = self.get_fish_coins(user_id)
        mine_coins = self.get_mine_coins(user_id)
        farm_coins = self.get_farm_coins(user_id)

        embed.add_field(
            name="🐟 FishCoins",
            value=f"**{fish_coins:,}**\n*Earned from fishing*",
            inline=True
        )
        embed.add_field(
            name="⛏️ MineCoins",
            value=f"**{mine_coins:,}**\n*Earned from mining*",
            inline=True
        )
        embed.add_field(
            name="🌾 FarmCoins",
            value=f"**{farm_coins:,}**\n*Earned from farming*",
            inline=True
        )

        # Wizard Wars Gold
        ww_data_dir = os.getenv("RENDER_DISK_PATH", ".")
        ww_file = os.path.join(ww_data_dir, "wizard_wars_data.json")
        ww_gold = 0
        if os.path.exists(ww_file):
            try:
                with open(ww_file, 'r') as f:
                    ww_data = json.load(f)
                if user_key in ww_data.get('wizards', {}):
                    ww_gold = ww_data['wizards'][user_key].get('gold', 0)
            except Exception:
                pass
        embed.add_field(name="💎 Wizard Wars Gold", value=f"**{ww_gold:,}**\n*Earned in Wizard Wars*", inline=True)

        # === Conversion Rates ===
        embed.add_field(
            name="📊 Conversion Rates  *(use /convert)*",
            value=(
                "💰→🐟 `4 PSY = 1 FISH`   |   🐟→💰 `1 FISH = 2 PSY`\n"
                "💰→⛏️ `5 PSY = 1 MINE`   |   ⛏️→💰 `1 MINE = 3 PSY`\n"
                "💰→🌾 `4 PSY = 1 FARM`   |   🌾→💰 `1 FARM = 2 PSY`"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
