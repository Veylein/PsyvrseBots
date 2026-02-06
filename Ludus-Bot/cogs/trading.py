import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional
import asyncio
from datetime import datetime
from utils import user_storage

class Trading(commands.Cog):
    """Player-to-player trading system for items and coins"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_trades = {}  # trade_id: Trade object
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.trade_history_file = os.path.join(data_dir, "trade_history.json")
        self.blocks_file = os.path.join(data_dir, "blocks.json")
        self.gift_settings_file = os.path.join(data_dir, "gift_settings.json")
        self.load_history()
        self.blocks_data = self.load_blocks()
        self.gift_settings = self.load_gift_settings()
        
        # Item values for selling (85-90% of original price)
        self.item_sell_values = {
            # Shop items
            "luck_charm": 450,
            "xp_boost": 270,
            "pet_food": 135,
            "energy_drink": 180,
            "double_coins": 765,
            "mystery_box": 225,
            "rare_fish_bait": 180,
            "farm_expansion": 900,
        }
    
    def load_history(self):
        """Load trade history"""
        if os.path.exists(self.trade_history_file):
            with open(self.trade_history_file, 'r') as f:
                self.trade_history = json.load(f)
        else:
            self.trade_history = {}
    
    def load_blocks(self):
        """Load blocked users data"""
        if os.path.exists(self.blocks_file):
            with open(self.blocks_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_blocks(self):
        """Save blocked users data"""
        with open(self.blocks_file, 'w') as f:
            json.dump(self.blocks_data, f, indent=2)
    
    def load_gift_settings(self):
        """Load gift settings data"""
        if os.path.exists(self.gift_settings_file):
            with open(self.gift_settings_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_gift_settings(self):
        """Save gift settings data"""
        with open(self.gift_settings_file, 'w') as f:
            json.dump(self.gift_settings, f, indent=2)
    
    def gifts_enabled(self, user_id: int) -> bool:
        """Check if user has gifts enabled (default: True)"""
        user_key = str(user_id)
        return self.gift_settings.get(user_key, {}).get('enabled', True)
    
    def is_blocked(self, user_id: int, target_id: int) -> bool:
        """Check if target has blocked user"""
        target_key = str(target_id)
        if target_key in self.blocks_data:
            return user_id in self.blocks_data[target_key]
        return False
    
    def save_history(self):
        """Save trade history"""
        with open(self.trade_history_file, 'w') as f:
            json.dump(self.trade_history, f, indent=4)
    
    def log_trade(self, trade_data):
        """Log completed trade"""
        trade_id = str(len(self.trade_history) + 1)
        self.trade_history[trade_id] = {
            **trade_data,
            'timestamp': datetime.now().isoformat()
        }
        self.save_history()

    def _record_trade_state(self, user_id: int, username: str | None, trade_summary: dict):
        """Store trade summary in per-user game state."""
        try:
            user = user_storage.load_user(user_id, username)
            games = user.setdefault("games", {})
            trading = games.setdefault("trading", {})
            trading["total_trades"] = trading.get("total_trades", 0) + 1
            trading["last_trade"] = trade_summary
            recent = trading.setdefault("recent_trades", [])
            recent.insert(0, trade_summary)
            if len(recent) > 50:
                recent[:] = recent[:50]
            user.setdefault("meta", {})["updated_at"] = datetime.utcnow().isoformat() + "Z"
            user["meta"]["last_active"] = datetime.utcnow().isoformat() + "Z"
            if username:
                user["username"] = username
            user_storage.save_user(user)
        except Exception:
            pass
    
    class TradeSession:
        """Represents an active trade between two users"""
        def __init__(self, user1, user2, channel):
            self.user1 = user1
            self.user2 = user2
            self.channel = channel
            
            # Trade offers
            self.user1_coins = 0
            self.user1_items = {}  # item_id: quantity
            self.user2_coins = 0
            self.user2_items = {}
            
            # Confirmation status
            self.user1_confirmed = False
            self.user2_confirmed = False
            
            self.active = True
            self.expires_at = asyncio.get_event_loop().time() + 300  # 5 min timeout
        
        def add_offer(self, user_id, coins=0, items=None):
            """Add items/coins to user's offer"""
            if user_id == self.user1.id:
                if coins:
                    self.user1_coins += coins
                if items:
                    for item_id, qty in items.items():
                        self.user1_items[item_id] = self.user1_items.get(item_id, 0) + qty
                # Reset confirmation when offer changes
                self.user1_confirmed = False
                self.user2_confirmed = False
            elif user_id == self.user2.id:
                if coins:
                    self.user2_coins += coins
                if items:
                    for item_id, qty in items.items():
                        self.user2_items[item_id] = self.user2_items.get(item_id, 0) + qty
                self.user1_confirmed = False
                self.user2_confirmed = False
        
        def remove_offer(self, user_id, coins=0, item_id=None, qty=1):
            """Remove items/coins from user's offer"""
            if user_id == self.user1.id:
                if coins:
                    self.user1_coins = max(0, self.user1_coins - coins)
                if item_id and item_id in self.user1_items:
                    self.user1_items[item_id] = max(0, self.user1_items[item_id] - qty)
                    if self.user1_items[item_id] == 0:
                        del self.user1_items[item_id]
                self.user1_confirmed = False
                self.user2_confirmed = False
            elif user_id == self.user2.id:
                if coins:
                    self.user2_coins = max(0, self.user2_coins - coins)
                if item_id and item_id in self.user2_items:
                    self.user2_items[item_id] = max(0, self.user2_items[item_id] - qty)
                    if self.user2_items[item_id] == 0:
                        del self.user2_items[item_id]
                self.user1_confirmed = False
                self.user2_confirmed = False
        
        def confirm(self, user_id):
            """Confirm trade for a user"""
            if user_id == self.user1.id:
                self.user1_confirmed = True
            elif user_id == self.user2.id:
                self.user2_confirmed = True
        
        def is_confirmed(self):
            """Check if both users confirmed"""
            return self.user1_confirmed and self.user2_confirmed
        
        def get_embed(self):
            """Create trade status embed"""
            embed = discord.Embed(
                title="🤝 Active Trade",
                description=f"Trade between {self.user1.mention} and {self.user2.mention}",
                color=discord.Color.blue()
            )
            
            # User 1's offer
            user1_offer = []
            if self.user1_coins > 0:
                user1_offer.append(f"💰 {self.user1_coins:,} PsyCoins")
            for item_id, qty in self.user1_items.items():
                user1_offer.append(f"📦 {item_id} x{qty}")
            
            if not user1_offer:
                user1_offer.append("*Nothing offered*")
            
            status1 = "✅ Confirmed" if self.user1_confirmed else "⏳ Not confirmed"
            embed.add_field(
                name=f"{self.user1.display_name}'s Offer ({status1})",
                value="\n".join(user1_offer),
                inline=True
            )
            
            # User 2's offer
            user2_offer = []
            if self.user2_coins > 0:
                user2_offer.append(f"💰 {self.user2_coins:,} PsyCoins")
            for item_id, qty in self.user2_items.items():
                user2_offer.append(f"📦 {item_id} x{qty}")
            
            if not user2_offer:
                user2_offer.append("*Nothing offered*")
            
            status2 = "✅ Confirmed" if self.user2_confirmed else "⏳ Not confirmed"
            embed.add_field(
                name=f"{self.user2.display_name}'s Offer ({status2})",
                value="\n".join(user2_offer),
                inline=True
            )
            
            # Instructions
            embed.add_field(
                name="Commands",
                value="```\n"
                      "L!tradeadd coins <amount>\n"
                      "L!tradeadd item <item_id> [qty]\n"
                      "L!traderemove coins <amount>\n"
                      "L!traderemove item <item_id> [qty]\n"
                      "L!tradeconfirm\n"
                      "L!tradecancel\n"
                      "```",
                inline=False
            )
            
            embed.set_footer(text="Both users must confirm to complete trade | Trade expires in 5 minutes")
            
            return embed
    
    def get_active_trade(self, user_id):
        """Get user's active trade"""
        for trade_id, trade in self.active_trades.items():
            if trade.user1.id == user_id or trade.user2.id == user_id:
                return trade_id, trade
        return None, None
    
    @commands.group(name="trade", invoke_without_command=True)
    async def trade(self, ctx, member: discord.Member = None):
        """Start a trade with another user"""
        if member is None:
            await ctx.send("❌ Please mention a user to trade with: `L!trade @user`")
            return
        
        if member.bot:
            await ctx.send("❌ You can't trade with bots!")
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't trade with yourself!")
            return
        
        # Check if blocked
        if self.is_blocked(ctx.author.id, member.id):
            await ctx.send(f"❌ {member.mention} has blocked you!")
            return
        
        if self.is_blocked(member.id, ctx.author.id):
            await ctx.send(f"❌ You have blocked {member.mention}!")
            return
        
        # Check if either user has an active trade
        trade_id1, existing1 = self.get_active_trade(ctx.author.id)
        trade_id2, existing2 = self.get_active_trade(member.id)
        
        if existing1:
            await ctx.send(f"❌ You already have an active trade! Use `L!tradecancel` to cancel it.")
            return
        
        if existing2:
            await ctx.send(f"❌ {member.mention} already has an active trade!")
            return
        
        # Create trade request
        embed = discord.Embed(
            title="🤝 Trade Request",
            description=f"{ctx.author.mention} wants to trade with {member.mention}!\n\n"
                       f"{member.mention}, react with ✅ to accept or ❌ to decline.",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user.id == member.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Create trade session
                trade_id = f"{ctx.author.id}_{member.id}_{int(asyncio.get_event_loop().time())}"
                trade = self.TradeSession(ctx.author, member, ctx.channel)
                self.active_trades[trade_id] = trade
                
                embed = trade.get_embed()
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {member.mention} declined the trade request.")
                
        except asyncio.TimeoutError:
            await ctx.send(f"⏱️ Trade request expired. {member.mention} didn't respond.")
    
    @trade.command(name="add")
    async def trade_add(self, ctx, item_type: str, item_or_amount: str, quantity: int = 1):
        """Add items or coins to your trade offer"""
        trade_id, trade = self.get_active_trade(ctx.author.id)
        
        if not trade:
            await ctx.send("❌ You don't have an active trade!")
            return
        
        if not trade.active:
            await ctx.send("❌ This trade has ended!")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        item_type = item_type.lower()
        
        if item_type in ["coin", "coins", "psycoin", "psycoins"]:
            # Adding coins
            try:
                amount = int(item_or_amount)
            except ValueError:
                await ctx.send("❌ Invalid amount!")
                return
            
            if amount <= 0:
                await ctx.send("❌ Amount must be positive!")
                return
            
            # Check if user has enough coins
            balance = economy_cog.get_balance(ctx.author.id)
            current_offer = trade.user1_coins if ctx.author.id == trade.user1.id else trade.user2_coins
            
            if balance < (current_offer + amount):
                await ctx.send(f"❌ You don't have enough coins! Balance: {balance:,}")
                return
            
            trade.add_offer(ctx.author.id, coins=amount)
            await ctx.send(f"✅ Added **{amount:,} PsyCoins** to your offer!")
            
        elif item_type in ["item", "items"]:
            # Adding items
            item_id = item_or_amount
            
            if quantity <= 0:
                await ctx.send("❌ Quantity must be positive!")
                return
            
            # Check if user has the item
            user_inventory = economy_cog.get_inventory(ctx.author.id)
            if item_id not in user_inventory or user_inventory[item_id] < quantity:
                await ctx.send(f"❌ You don't have {quantity}x {item_id}!")
                return
            
            trade.add_offer(ctx.author.id, items={item_id: quantity})
            await ctx.send(f"✅ Added **{quantity}x {item_id}** to your offer!")
        else:
            await ctx.send("❌ Invalid type! Use `coins` or `item`")
            return
        
        # Update trade display
        embed = trade.get_embed()
        await ctx.send(embed=embed)
    
    @trade.command(name="remove")
    async def trade_remove(self, ctx, item_type: str, item_or_amount: str, quantity: int = 1):
        """Remove items or coins from your trade offer"""
        trade_id, trade = self.get_active_trade(ctx.author.id)
        
        if not trade:
            await ctx.send("❌ You don't have an active trade!")
            return
        
        item_type = item_type.lower()
        
        if item_type in ["coin", "coins", "psycoin", "psycoins"]:
            try:
                amount = int(item_or_amount)
            except ValueError:
                await ctx.send("❌ Invalid amount!")
                return
            
            trade.remove_offer(ctx.author.id, coins=amount)
            await ctx.send(f"✅ Removed **{amount:,} PsyCoins** from your offer!")
            
        elif item_type in ["item", "items"]:
            item_id = item_or_amount
            trade.remove_offer(ctx.author.id, item_id=item_id, qty=quantity)
            await ctx.send(f"✅ Removed **{quantity}x {item_id}** from your offer!")
        else:
            await ctx.send("❌ Invalid type! Use `coins` or `item`")
            return
        
        # Update trade display
        embed = trade.get_embed()
        await ctx.send(embed=embed)
    
    @trade.command(name="confirm")
    async def trade_confirm(self, ctx):
        """Confirm your side of the trade"""
        trade_id, trade = self.get_active_trade(ctx.author.id)
        
        if not trade:
            await ctx.send("❌ You don't have an active trade!")
            return
        
        if not trade.active:
            await ctx.send("❌ This trade has ended!")
            return
        
        # Confirm trade
        trade.confirm(ctx.author.id)
        
        if trade.is_confirmed():
            # Execute trade
            await self.execute_trade(ctx, trade_id, trade)
        else:
            await ctx.send(f"✅ You confirmed the trade! Waiting for the other user...")
            embed = trade.get_embed()
            await ctx.send(embed=embed)
    
    async def execute_trade(self, ctx, trade_id, trade):
        """Execute a confirmed trade"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        try:
            # Verify both users still have what they're trading
            user1_balance = economy_cog.get_balance(trade.user1.id)
            user2_balance = economy_cog.get_balance(trade.user2.id)
            
            if user1_balance < trade.user1_coins:
                await ctx.send(f"❌ Trade failed! {trade.user1.mention} doesn't have enough coins!")
                del self.active_trades[trade_id]
                return
            
            if user2_balance < trade.user2_coins:
                await ctx.send(f"❌ Trade failed! {trade.user2.mention} doesn't have enough coins!")
                del self.active_trades[trade_id]
                return
            
            # Verify items
            user1_inv = economy_cog.get_inventory(trade.user1.id)
            user2_inv = economy_cog.get_inventory(trade.user2.id)
            
            for item_id, qty in trade.user1_items.items():
                if item_id not in user1_inv or user1_inv[item_id] < qty:
                    await ctx.send(f"❌ Trade failed! {trade.user1.mention} doesn't have {qty}x {item_id}!")
                    del self.active_trades[trade_id]
                    return
            
            for item_id, qty in trade.user2_items.items():
                if item_id not in user2_inv or user2_inv[item_id] < qty:
                    await ctx.send(f"❌ Trade failed! {trade.user2.mention} doesn't have {qty}x {item_id}!")
                    del self.active_trades[trade_id]
                    return
            
            # Execute the trade
            # Transfer coins
            if trade.user1_coins > 0:
                economy_cog.remove_coins(trade.user1.id, trade.user1_coins, "trade")
                economy_cog.add_coins(trade.user2.id, trade.user1_coins, "trade")
            
            if trade.user2_coins > 0:
                economy_cog.remove_coins(trade.user2.id, trade.user2_coins, "trade")
                economy_cog.add_coins(trade.user1.id, trade.user2_coins, "trade")
            
            # Transfer items
            for item_id, qty in trade.user1_items.items():
                economy_cog.remove_item(trade.user1.id, item_id, qty)
                economy_cog.add_item(trade.user2.id, item_id, qty)
            
            for item_id, qty in trade.user2_items.items():
                economy_cog.remove_item(trade.user2.id, item_id, qty)
                economy_cog.add_item(trade.user1.id, item_id, qty)
            
            # Log trade
            self.log_trade({
                'user1_id': trade.user1.id,
                'user1_name': str(trade.user1),
                'user1_coins': trade.user1_coins,
                'user1_items': trade.user1_items,
                'user2_id': trade.user2.id,
                'user2_name': str(trade.user2),
                'user2_coins': trade.user2_coins,
                'user2_items': trade.user2_items,
                'server_id': ctx.guild.id,
                'server_name': ctx.guild.name
            })
            
            trade_summary = {
                "trade_id": trade_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "user1_id": trade.user1.id,
                "user1_name": str(trade.user1),
                "user1_coins": trade.user1_coins,
                "user1_items": trade.user1_items,
                "user2_id": trade.user2.id,
                "user2_name": str(trade.user2),
                "user2_coins": trade.user2_coins,
                "user2_items": trade.user2_items,
                "server_id": ctx.guild.id,
                "server_name": ctx.guild.name
            }
            self._record_trade_state(trade.user1.id, getattr(trade.user1, "name", None), trade_summary)
            self._record_trade_state(trade.user2.id, getattr(trade.user2, "name", None), trade_summary)
            
            # Success message
            embed = discord.Embed(
                title="✅ Trade Completed!",
                description=f"Trade between {trade.user1.mention} and {trade.user2.mention} completed successfully!",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
            
            # Clean up
            trade.active = False
            del self.active_trades[trade_id]
            
        except Exception as e:
            await ctx.send(f"❌ Trade failed due to an error: {e}")
            trade.active = False
            if trade_id in self.active_trades:
                del self.active_trades[trade_id]
    
    @trade.command(name="cancel")
    async def trade_cancel(self, ctx):
        """Cancel your active trade"""
        trade_id, trade = self.get_active_trade(ctx.author.id)
        
        if not trade:
            await ctx.send("❌ You don't have an active trade!")
            return
        
        trade.active = False
        del self.active_trades[trade_id]
        
        await ctx.send(f"❌ Trade cancelled!")
    
    @commands.command(name="tradehistory")
    async def trade_history(self, ctx, limit: int = 5):
        """View your recent trades"""
        user_trades = []
        
        for trade_id, trade_data in self.trade_history.items():
            if trade_data['user1_id'] == ctx.author.id or trade_data['user2_id'] == ctx.author.id:
                user_trades.append((trade_id, trade_data))
        
        if not user_trades:
            await ctx.send("📜 You haven't completed any trades yet!")
            return
        
        # Sort by most recent
        user_trades.sort(key=lambda x: x[1].get('timestamp', ''), reverse=True)
        user_trades = user_trades[:limit]
        
        embed = discord.Embed(
            title=f"📜 {ctx.author.display_name}'s Trade History",
            description=f"Showing last {len(user_trades)} trades",
            color=discord.Color.blue()
        )
        
        for trade_id, trade_data in user_trades:
            user1_summary = []
            if trade_data['user1_coins'] > 0:
                user1_summary.append(f"{trade_data['user1_coins']:,} coins")
            if trade_data['user1_items']:
                items_str = ", ".join([f"{qty}x {item}" for item, qty in trade_data['user1_items'].items()])
                user1_summary.append(items_str)
            
            user2_summary = []
            if trade_data['user2_coins'] > 0:
                user2_summary.append(f"{trade_data['user2_coins']:,} coins")
            if trade_data['user2_items']:
                items_str = ", ".join([f"{qty}x {item}" for item, qty in trade_data['user2_items'].items()])
                user2_summary.append(items_str)
            
            trade_summary = f"**{trade_data['user1_name']}** traded {', '.join(user1_summary) if user1_summary else 'nothing'}\n" \
                          f"**{trade_data['user2_name']}** traded {', '.join(user2_summary) if user2_summary else 'nothing'}"
            
            timestamp = trade_data.get('timestamp', 'Unknown')
            embed.add_field(
                name=f"Trade #{trade_id}",
                value=f"{trade_summary}\n*{timestamp[:10]}*",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="sell")
    async def sell_item(self, ctx, *, args: str = None):
        """Sell inventory items for 85-90% of their value
        
        Usage: L!sell <item_name>
        Example: L!sell luck_charm
        """
        
        if not args:
            embed = discord.Embed(
                title="💰 Sell System",
                description="**Sell your items for 85-90% of their value!**\n\n"
                           "**Usage:** `L!sell <item_name>`\n\n"
                           "**Sellable Items:**\n"
                           "• Shop items (luck_charm, xp_boost, pet_food, etc.)\n"
                           "• Farm crops (wheat, corn, pumpkin, etc.)\n"
                           "• Wizard Wars spells (except starter spells)\n"
                           "• Pets (requires confirmation)\n\n"
                           "**Examples:**\n"
                           "`L!sell luck_charm`\n"
                           "`L!sell wheat`\n"
                           "`L!sell fireball`\n"
                           "`L!sell tiger` (pet)",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return
        
        item_name = args.lower().replace(" ", "_")
        economy_cog = self.bot.get_cog("Economy")
        
        if not economy_cog:
            await ctx.send("❌ Economy system not available!")
            return
        
        import random
        modifier = random.uniform(0.85, 0.90)
        
        # Try shop items first
        inventory = economy_cog.get_inventory(ctx.author.id)
        if item_name in inventory and inventory[item_name] > 0:
            base_value = self.item_sell_values.get(item_name, 0)
            if base_value == 0:
                # Try to get value from shop_items
                if item_name in economy_cog.shop_items:
                    base_value = economy_cog.shop_items[item_name]['price']
            
            value = int(base_value * modifier)
            economy_cog.remove_item(ctx.author.id, item_name, 1)
            economy_cog.add_coins(ctx.author.id, value, "item_sale")
            
            item_display = economy_cog.shop_items.get(item_name, {}).get('name', item_name.replace("_", " ").title())
            embed = discord.Embed(
                title="💰 Item Sold!",
                description=f"You sold **{item_display}** for **{value}** PsyCoins!",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Sold at {int(modifier*100)}% value")
            await ctx.send(embed=embed)
            return
        
        # Try farm crops
        sim_cog = self.bot.get_cog("Simulations")
        if sim_cog:
            farm = sim_cog.get_farm(ctx.author.id)
            if item_name in farm["inventory"] and farm["inventory"][item_name] > 0:
                crop = sim_cog.crops.get(item_name, {})
                base_value = crop.get('sell_price', 10)
                value = int(base_value * modifier)
                
                farm["inventory"][item_name] -= 1
                if farm["inventory"][item_name] == 0:
                    del farm["inventory"][item_name]
                sim_cog.save_data()
                economy_cog.add_coins(ctx.author.id, value, "crop_sale")
                
                embed = discord.Embed(
                    title="💰 Crop Sold!",
                    description=f"You sold **{crop.get('name', item_name)}** for **{value}** PsyCoins!",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Sold at {int(modifier*100)}% value")
                await ctx.send(embed=embed)
                return
        
        # Try wizard spells
        ww_cog = self.bot.get_cog("WizardWars")
        if ww_cog:
            user_id = str(ctx.author.id)
            if user_id in ww_cog.wizards:
                wizard = ww_cog.wizards[user_id]
                spell_found = None
                
                for spell in wizard['spells']:
                    if spell.lower().replace(" ", "_") == item_name or spell.lower() == item_name:
                        spell_found = spell
                        break
                
                if spell_found:
                    if spell_found in ["Flame Burst", "Water Shield", "Lightning Strike"]:
                        await ctx.send("❌ You can't sell starter spells!")
                        return
                    
                    spell_data = ww_cog.spells.get(spell_found, {})
                    base_value = spell_data.get('power', 3) * 100
                    value = int(base_value * modifier)
                    
                    wizard['spells'].remove(spell_found)
                    if spell_found in wizard['equipped_spells']:
                        wizard['equipped_spells'].remove(spell_found)
                    ww_cog.save_data()
                    economy_cog.add_coins(ctx.author.id, value, "spell_sale")
                    
                    embed = discord.Embed(
                        title="💰 Spell Sold!",
                        description=f"You sold **{spell_found}** for **{value}** PsyCoins!",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"Sold at {int(modifier*100)}% value")
                    await ctx.send(embed=embed)
                    return
        
        # Try pets
        pets_cog = self.bot.get_cog("Pets")
        if pets_cog:
            user_id = str(ctx.author.id)
            if user_id in pets_cog.pets_data:
                pet = pets_cog.pets_data[user_id]
                if pet['type'].lower() == item_name or pet['name'].lower() == item_name:
                    # Confirmation for pets
                    pet_values = {
                        "tiger": 500, "dragon": 1000, "panda": 400, "dog": 200,
                        "cat": 200, "hamster": 150, "snake": 300, "horse": 700, "axolotl": 500
                    }
                    base_value = pet_values.get(pet['type'].lower(), 300)
                    value = int(base_value * modifier)
                    
                    confirm_msg = await ctx.send(
                        f"⚠️ Are you sure you want to sell {pet['emoji']} **{pet['name']}**?\n"
                        f"You'll receive **{value}** PsyCoins.\n\n"
                        f"React with ✅ to confirm or ❌ to cancel."
                    )
                    await confirm_msg.add_reaction("✅")
                    await confirm_msg.add_reaction("❌")
                    
                    def check(reaction, user):
                        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
                    
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                        if str(reaction.emoji) == "✅":
                            del pets_cog.pets_data[user_id]
                            pets_cog.save_pets()
                            economy_cog.add_coins(ctx.author.id, value, "pet_sale")
                            
                            embed = discord.Embed(
                                title="💰 Pet Sold!",
                                description=f"You sold {pet['emoji']} **{pet['name']}** for **{value}** PsyCoins!",
                                color=discord.Color.green()
                            )
                            embed.set_footer(text=f"Sold at {int(modifier*100)}% value")
                            await ctx.send(embed=embed)
                            return
                        else:
                            await ctx.send("❌ Pet sale cancelled.")
                            return
                    except:
                        await ctx.send("⏰ Pet sale timed out.")
                        return
        
        await ctx.send(f"❌ You don't have **{item_name.replace('_', ' ')}** to sell!")
    
    @commands.command(name="block")
    async def block_user(self, ctx, member: discord.Member = None):
        """Block a user from directly interacting with you
        
        Usage: L!block @user
        """
        
        if not member:
            await ctx.send("❌ Please mention a user to block! Example: `L!block @user`")
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't block yourself!")
            return
        
        if member.bot:
            await ctx.send("❌ You can't block bots!")
            return
        
        user_key = str(ctx.author.id)
        if user_key not in self.blocks_data:
            self.blocks_data[user_key] = []
        
        if member.id in self.blocks_data[user_key]:
            await ctx.send(f"❌ You've already blocked {member.display_name}!")
            return
        
        self.blocks_data[user_key].append(member.id)
        self.save_blocks()
        
        embed = discord.Embed(
            title="🚫 User Blocked",
            description=f"You blocked **{member.display_name}**\n\n"
                       f"They can no longer:\n"
                       f"• Challenge you directly in games\n"
                       f"• Trade with you\n"
                       f"• Send you gifts\n\n"
                       f"You can still play together in group games.\n"
                       f"Use `L!unblock @{member.name}` to reverse this.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="unblock")
    async def unblock_user(self, ctx, member: discord.Member = None):
        """Unblock a user
        
        Usage: L!unblock @user
        """
        
        if not member:
            await ctx.send("❌ Please mention a user to unblock! Example: `L!unblock @user`")
            return
        
        user_key = str(ctx.author.id)
        if user_key not in self.blocks_data or member.id not in self.blocks_data[user_key]:
            await ctx.send(f"❌ {member.display_name} is not blocked!")
            return
        
        self.blocks_data[user_key].remove(member.id)
        self.save_blocks()
        
        embed = discord.Embed(
            title="✅ User Unblocked",
            description=f"You unblocked **{member.display_name}**\n\nThey can now interact with you normally.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="blocklist")
    async def view_blocklist(self, ctx):
        """View your blocked users"""
        
        user_key = str(ctx.author.id)
        if user_key not in self.blocks_data or not self.blocks_data[user_key]:
            await ctx.send("✅ You haven't blocked anyone!")
            return
        
        blocked_users = []
        for user_id in self.blocks_data[user_key]:
            try:
                user = await self.bot.fetch_user(user_id)
                blocked_users.append(f"• {user.name}")
            except:
                blocked_users.append(f"• Unknown User ({user_id})")
        
        embed = discord.Embed(
            title="🚫 Your Blocklist",
            description="\n".join(blocked_users),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Use L!unblock @user to unblock someone")
        await ctx.send(embed=embed)
    
    @commands.command(name="gift")
    async def send_gift(self, ctx, member: discord.Member = None, *, args: str = None):
        """Send a secret anonymous gift
        
        Usage: L!gift @user <item_name> [message]
        Example: L!gift @user luck_charm Hope this helps!
        """
        
        if not member or not args:
            embed = discord.Embed(
                title="🎁 Gift System",
                description="**Send secret anonymous gifts!**\n\n"
                           "**Usage:** `L!gift @user <item> [message]`\n\n"
                           "**Giftable:**\n"
                           "• Shop items\n"
                           "• Farm crops\n"
                           "• Wizard Wars spells\n"
                           "• PsyCoins (L!gift @user 1000 coins)\n\n"
                           "**Examples:**\n"
                           "`L!gift @user luck_charm`\n"
                           "`L!gift @user 1000 coins Here you go!`\n"
                           "`L!gift @user fireball Enjoy!`\n\n"
                           "**Gift Settings:**\n"
                           "`L!gift enable` - Enable receiving gifts\n"
                           "`L!gift disable` - Disable receiving gifts\n"
                           "`L!gift status` - Check your gift settings",
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
            return
        
        if member.id == ctx.author.id:
            await ctx.send("❌ You can't gift yourself!")
            return
        
        if member.bot:
            await ctx.send("❌ You can't gift bots!")
            return
        
        # Check if receiver has gifts enabled
        if not self.gifts_enabled(member.id):
            await ctx.send(f"❌ {member.display_name} has disabled receiving gifts!")
            return
        
        # Check blocks
        if self.is_blocked(ctx.author.id, member.id):
            await ctx.send(f"❌ {member.mention} has blocked you!")
            return
        
        # Parse args for item and message
        parts = args.split()
        item_name = parts[0].lower().replace(" ", "_")
        message_text = " ".join(parts[1:]) if len(parts) > 1 else ""
        
        # Check if it's coins
        if parts[-1].lower() == "coins" and len(parts) >= 2:
            try:
                amount = int(parts[0])
                message_text = " ".join(parts[1:-1]) if len(parts) > 2 else ""
                
                economy_cog = self.bot.get_cog("Economy")
                if economy_cog.get_balance(ctx.author.id) >= amount:
                    economy_cog.remove_coins(ctx.author.id, amount, "gift")
                    economy_cog.add_coins(member.id, amount, "gift")
                    
                    gift_embed = discord.Embed(
                        title="🎁 You Received a Secret Gift!",
                        description=f"**A mysterious benefactor sent you:**\n💰 {amount:,} PsyCoins\n\n",
                        color=discord.Color.purple()
                    )
                    
                    if message_text:
                        gift_embed.add_field(name="📝 Message", value=message_text, inline=False)
                    
                    gift_embed.set_footer(text="The sender's identity is secret! 🤫")
                    
                    dm_sent = False
                    try:
                        await member.send(embed=gift_embed)
                        dm_sent = True
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
                    
                    if dm_sent:
                        await ctx.send(f"✅ **Gift delivered!** 🎁\n{member.display_name} received your anonymous gift of **{amount:,} PsyCoins** via DM!")
                    else:
                        await ctx.send(f"⚠️ **Gift sent but DM failed!**\n{member.display_name} received **{amount:,} PsyCoins** but their DMs are closed. The item was still transferred!")
                    return
                else:
                    await ctx.send("❌ You don't have enough coins!")
                    return
            except ValueError:
                pass
        
        # Try shop items
        economy_cog = self.bot.get_cog("Economy")
        inventory = economy_cog.get_inventory(ctx.author.id)
        
        if item_name in inventory and inventory[item_name] > 0:
            economy_cog.remove_item(ctx.author.id, item_name, 1)
            economy_cog.add_item(member.id, item_name, 1)
            
            item_display = economy_cog.shop_items.get(item_name, {}).get('name', item_name.replace("_", " ").title())
            
            gift_embed = discord.Embed(
                title="🎁 You Received a Secret Gift!",
                description=f"**A mysterious benefactor sent you:**\n{item_display}\n\n",
                color=discord.Color.purple()
            )
            
            if message_text:
                gift_embed.add_field(name="📝 Message", value=message_text, inline=False)
            
            gift_embed.set_footer(text="The sender's identity is secret! 🤫")
            
            dm_sent = False
            try:
                await member.send(embed=gift_embed)
                dm_sent = True
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            
            if dm_sent:
                await ctx.send(f"✅ **Gift delivered!** 🎁\n{member.display_name} received your anonymous gift of **{item_display}** via DM!")
            else:
                await ctx.send(f"⚠️ **Gift sent but DM failed!**\n{member.display_name} received **{item_display}** but their DMs are closed. The item was still transferred!")
            return
        
        # Try farm crops
        sim_cog = self.bot.get_cog("Simulations")
        if sim_cog:
            sender_farm = sim_cog.get_farm(ctx.author.id)
            if item_name in sender_farm["inventory"] and sender_farm["inventory"][item_name] > 0:
                receiver_farm = sim_cog.get_farm(member.id)
                sender_farm["inventory"][item_name] -= 1
                if sender_farm["inventory"][item_name] == 0:
                    del sender_farm["inventory"][item_name]
                receiver_farm["inventory"][item_name] = receiver_farm["inventory"].get(item_name, 0) + 1
                sim_cog.save_data()
                
                crop = sim_cog.crops.get(item_name, {})
                item_display = crop.get('name', item_name.replace("_", " ").title())
                
                gift_embed = discord.Embed(
                    title="🎁 You Received a Secret Gift!",
                    description=f"**A mysterious benefactor sent you:**\n{item_display}\n\n",
                    color=discord.Color.purple()
                )
                
                if message_text:
                    gift_embed.add_field(name="📝 Message", value=message_text, inline=False)
                
                gift_embed.set_footer(text="The sender's identity is secret! 🤫")
                
                dm_sent = False
                try:
                    await member.send(embed=gift_embed)
                    dm_sent = True
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass
                
                if dm_sent:
                    await ctx.send(f"✅ **Gift delivered!** 🎁\n{member.display_name} received your anonymous gift of **{item_display}** via DM!")
                else:
                    await ctx.send(f"⚠️ **Gift sent but DM failed!**\n{member.display_name} received **{item_display}** but their DMs are closed. The item was still transferred!")
                return
        
        # Try wizard spells
        ww_cog = self.bot.get_cog("WizardWars")
        if ww_cog:
            sender_id = str(ctx.author.id)
            receiver_id = str(member.id)
            
            if sender_id in ww_cog.wizards:
                wizard = ww_cog.wizards[sender_id]
                spell_found = None
                
                for spell in wizard['spells']:
                    if spell.lower().replace(" ", "_") == item_name or spell.lower() == item_name:
                        spell_found = spell
                        break
                
                if spell_found and spell_found not in ["Flame Burst", "Water Shield", "Lightning Strike"]:
                    if receiver_id not in ww_cog.wizards:
                        await ctx.send(f"❌ {member.display_name} doesn't have a wizard!")
                        return
                    
                    receiver_wizard = ww_cog.wizards[receiver_id]
                    
                    wizard['spells'].remove(spell_found)
                    if spell_found in wizard['equipped_spells']:
                        wizard['equipped_spells'].remove(spell_found)
                    
                    if spell_found not in receiver_wizard['spells']:
                        receiver_wizard['spells'].append(spell_found)
                    
                    ww_cog.save_data()
                    
                    gift_embed = discord.Embed(
                        title="🎁 You Received a Secret Gift!",
                        description=f"**A mysterious benefactor sent you:**\n🔮 {spell_found}\n\n",
                        color=discord.Color.purple()
                    )
                    
                    if message_text:
                        gift_embed.add_field(name="📝 Message", value=message_text, inline=False)
                    
                    gift_embed.set_footer(text="The sender's identity is secret! 🤫")
                    
                    dm_sent = False
                    try:
                        await member.send(embed=gift_embed)
                        dm_sent = True
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass
                    
                    if dm_sent:
                        await ctx.send(f"✅ **Gift delivered!** 🎁\n{member.display_name} received your anonymous gift of **{spell_found}** via DM!")
                    else:
                        await ctx.send(f"⚠️ **Gift sent but DM failed!**\n{member.display_name} received **{spell_found}** but their DMs are closed. The item was still transferred!")
                    return
        
        await ctx.send(f"❌ You don't have **{item_name.replace('_', ' ')}** to gift!")
    
    @commands.group(name="gifts", invoke_without_command=True)
    async def gifts_settings(self, ctx):
        """Manage your gift settings"""
        user_key = str(ctx.author.id)
        enabled = self.gift_settings.get(user_key, {}).get('enabled', True)
        
        status = "✅ **Enabled**" if enabled else "❌ **Disabled**"
        
        embed = discord.Embed(
            title="🎁 Your Gift Settings",
            description=f"**Status:** {status}\n\n"
                       f"When enabled, you can receive anonymous gifts from other players.\n"
                       f"When disabled, players cannot send you gifts.\n\n"
                       f"**Commands:**\n"
                       f"`L!gifts enable` - Enable receiving gifts\n"
                       f"`L!gifts disable` - Disable receiving gifts\n"
                       f"`L!gifts status` - Check your current settings",
            color=discord.Color.purple() if enabled else discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @gifts_settings.command(name="enable")
    async def gifts_enable(self, ctx):
        """Enable receiving gifts"""
        user_key = str(ctx.author.id)
        
        if user_key not in self.gift_settings:
            self.gift_settings[user_key] = {}
        
        if self.gift_settings[user_key].get('enabled', True):
            await ctx.send("✅ Gifts are already enabled!")
            return
        
        self.gift_settings[user_key]['enabled'] = True
        self.save_gift_settings()
        
        embed = discord.Embed(
            title="✅ Gifts Enabled!",
            description="You can now receive anonymous gifts from other players!\n\n"
                       "Players can send you items, coins, crops, and spells anonymously.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @gifts_settings.command(name="disable")
    async def gifts_disable(self, ctx):
        """Disable receiving gifts"""
        user_key = str(ctx.author.id)
        
        if user_key not in self.gift_settings:
            self.gift_settings[user_key] = {}
        
        if not self.gift_settings[user_key].get('enabled', True):
            await ctx.send("❌ Gifts are already disabled!")
            return
        
        self.gift_settings[user_key]['enabled'] = False
        self.save_gift_settings()
        
        embed = discord.Embed(
            title="🚫 Gifts Disabled!",
            description="You will no longer receive anonymous gifts.\n\n"
                       "Players who try to gift you will see a message that you have gifts disabled.\n"
                       "You can re-enable gifts anytime with `L!gifts enable`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @gifts_settings.command(name="status")
    async def gifts_status(self, ctx):
        """Check your gift settings"""
        user_key = str(ctx.author.id)
        enabled = self.gift_settings.get(user_key, {}).get('enabled', True)
        
        status = "✅ **Enabled**" if enabled else "❌ **Disabled**"
        
        embed = discord.Embed(
            title="🎁 Your Gift Settings",
            description=f"**Status:** {status}\n\n"
                       f"{'You can receive anonymous gifts!' if enabled else 'You cannot receive gifts.'}",
            color=discord.Color.purple() if enabled else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(name="admire")
    async def admire_user(self, ctx, member: discord.Member = None):
        """Anonymously admire someone"""
        if not member:
            await ctx.send("❌ Please mention someone to admire!")
            return
        
        if member.bot:
            await ctx.send("❌ Bots don't need admiration!")
            return
        
        admiration_messages = [
            "Someone thinks you're amazing! ✨",
            "You've been admired by a secret fan! 💫",
            "Someone appreciates you! 🌟",
            "A mysterious person thinks you're awesome! 🎭",
            "You've caught someone's admiration! 💝"
        ]
        
        import random
        msg = random.choice(admiration_messages)
        
        embed = discord.Embed(
            title="💖 Secret Admiration",
            description=msg,
            color=discord.Color.pink()
        )
        embed.set_footer(text="Someone in this server admires you! 🤫")
        
        dm_sent = False
        try:
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        
        if dm_sent:
            await ctx.send(f"💖 **Admiration sent!** {member.display_name} received your anonymous message via DM!")
        else:
            await ctx.send(f"⚠️ **Couldn't send DM!** {member.display_name} has DMs closed. Consider telling them in person! 😊")
    
    @commands.command(name="encourage")
    async def encourage_user(self, ctx, member: discord.Member = None):
        """Send anonymous encouragement"""
        if not member:
            await ctx.send("❌ Please mention someone to encourage!")
            return
        
        if member.bot:
            await ctx.send("❌ Bots are already encouraged by their code!")
            return
        
        encouragements = [
            "You're doing great! Keep it up! 💪",
            "Someone believes in you! 🌟",
            "You've got this! Don't give up! 🔥",
            "You're stronger than you think! 💫",
            "Your efforts don't go unnoticed! ⭐",
            "You're making a difference! Keep going! 🌈"
        ]
        
        import random
        msg = random.choice(encouragements)
        
        embed = discord.Embed(
            title="💪 Anonymous Encouragement",
            description=msg,
            color=discord.Color.gold()
        )
        embed.set_footer(text="Someone in this server is rooting for you! 🤫")
        
        dm_sent = False
        try:
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        
        if dm_sent:
            await ctx.send(f"💪 **Encouragement sent!** {member.display_name} received your anonymous message via DM!")
        else:
            await ctx.send(f"⚠️ **Couldn't send DM!** {member.display_name} has DMs closed. Consider encouraging them in person! 😊")

async def setup(bot):
    await bot.add_cog(Trading(bot))
