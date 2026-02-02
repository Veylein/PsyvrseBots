import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import json
import os
import asyncio
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class BusinessManager:
    """Manages user businesses, NPC shops, and cross-server marketplace"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.businesses_file = os.path.join(data_dir, "businesses.json")
        self.businesses = self.load_businesses()
        
        # NPC shops with fixed items and prices (10-20% cheaper than user shops)
        self.npc_shops = {
            "cafe": {
                "name": "☕ Cozy Cafe",
                "description": "Beverages and light snacks to restore energy",
                "items": {
                    "coffee": {"name": "Coffee", "price": 15, "energy": 10, "emoji": "☕"},
                    "tea": {"name": "Tea", "price": 12, "energy": 8, "emoji": "🍵"},
                    "sandwich": {"name": "Sandwich", "price": 25, "energy": 20, "emoji": "🥪"},
                    "pastry": {"name": "Pastry", "price": 18, "energy": 12, "emoji": "🥐"},
                    "smoothie": {"name": "Smoothie", "price": 30, "energy": 25, "emoji": "🥤"},
                }
            },
            "market": {
                "name": "🏪 General Market",
                "description": "Basic supplies and materials",
                "items": {
                    "rope": {"name": "Rope", "price": 20, "emoji": "🪢"},
                    "bucket": {"name": "Bucket", "price": 35, "emoji": "🪣"},
                    "shovel": {"name": "Shovel", "price": 50, "emoji": "⛏️"},
                    "seeds": {"name": "Seeds Pack", "price": 40, "emoji": "🌱"},
                    "fertilizer": {"name": "Fertilizer", "price": 45, "emoji": "💩"},
                }
            },
            "factory": {
                "name": "🏭 Material Factory",
                "description": "Crafting materials and components",
                "items": {
                    "wood": {"name": "Wood Planks", "price": 25, "emoji": "🪵"},
                    "stone": {"name": "Stone Block", "price": 30, "emoji": "🪨"},
                    "iron": {"name": "Iron Ingot", "price": 60, "emoji": "⚙️"},
                    "cloth": {"name": "Cloth Roll", "price": 35, "emoji": "🧵"},
                    "glass": {"name": "Glass Sheet", "price": 40, "emoji": "🪟"},
                }
            },
            "fishsupplies": {
                "name": "🎣 Fish Supplies",
                "description": "Fishing gear and bait",
                "items": {
                    "bait": {"name": "Basic Bait", "price": 10, "emoji": "🪱"},
                    "goodbait": {"name": "Good Bait", "price": 25, "emoji": "🦐"},
                    "net": {"name": "Fishing Net", "price": 75, "emoji": "🕸️"},
                    "rod_upgrade": {"name": "Rod Upgrade", "price": 150, "emoji": "🎣"},
                    "tackle_box": {"name": "Tackle Box", "price": 100, "emoji": "🧰"},
                }
            },
            "petstore": {
                "name": "🐾 Pet Store",
                "description": "Pet food and supplies",
                "items": {
                    "pet_food": {"name": "Pet Food", "price": 20, "emoji": "🍖"},
                    "premium_food": {"name": "Premium Food", "price": 45, "emoji": "🥩"},
                    "toy": {"name": "Pet Toy", "price": 30, "emoji": "🎾"},
                    "bed": {"name": "Pet Bed", "price": 80, "emoji": "🛏️"},
                    "medicine": {"name": "Medicine", "price": 60, "emoji": "💊"},
                }
            },
            "magic_shop": {
                "name": "🔮 Magic Shop",
                "description": "Spells, potions, and mystical items",
                "items": {
                    "health_potion": {"name": "Health Potion", "price": 50, "emoji": "❤️"},
                    "mana_potion": {"name": "Mana Potion", "price": 50, "emoji": "💙"},
                    "luck_charm": {"name": "Luck Charm", "price": 100, "emoji": "🍀"},
                    "speed_spell": {"name": "Speed Spell", "price": 75, "emoji": "⚡"},
                    "shield_spell": {"name": "Shield Spell", "price": 90, "emoji": "🛡️"},
                }
            }
        }
    
    def load_businesses(self):
        """Load user businesses from JSON"""
        if os.path.exists(self.businesses_file):
            try:
                with open(self.businesses_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_businesses(self):
        """Save businesses to JSON"""
        try:
            with open(self.businesses_file, 'w') as f:
                json.dump(self.businesses, f, indent=4)
        except Exception as e:
            print(f"Error saving businesses: {e}")
    
    def get_user_business(self, user_id):
        """Get a user's business"""
        return self.businesses.get(str(user_id))
    
    def create_business(self, user_id, name, description):
        """Create a new business for a user"""
        user_id = str(user_id)
        if user_id in self.businesses:
            return False, "You already own a business!"
        
        self.businesses[user_id] = {
            "name": name,
            "description": description,
            "owner_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "inventory": {},  # item_id: {name, price, quantity, emoji}
            "employees": {},
            "sales": 0,
            "revenue": 0,
            "rating": 5.0,
            "reviews": []
        }
        self.save_businesses()
        return True, "Business created successfully!"

    def add_shipment(self, owner_id, from_user, item_data, eta_minutes=30):
        """Schedule an incoming shipment to a business."""
        owner_id = str(owner_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False, "Owner has no business"

        shipments = business.get('incoming_shipments', [])
        deliver_at = (datetime.utcnow() + timedelta(minutes=eta_minutes)).isoformat()
        shipments.append({
            'from': str(from_user),
            'item': item_data,
            'deliver_at': deliver_at
        })
        business['incoming_shipments'] = shipments
        self.save_businesses()
        return True, f"Shipment scheduled to deliver in {eta_minutes} minutes."
    
    def add_item_to_business(self, user_id, item_data):
        """Add item from user's inventory to their business"""
        user_id = str(user_id)
        business = self.get_user_business(user_id)
        if not business:
            return False, "You don't own a business!"
        
        item_id = item_data['id']
        if item_id in business['inventory']:
            business['inventory'][item_id]['quantity'] += item_data['quantity']
        else:
            business['inventory'][item_id] = item_data
        
        self.save_businesses()
        return True, f"Added {item_data['quantity']}x {item_data['name']} to your shop!"
    
    def set_item_price(self, user_id, item_id, price):
        """Set price for an item in user's business"""
        user_id = str(user_id)
        business = self.get_user_business(user_id)
        if not business:
            return False, "You don't own a business!"
        
        if item_id not in business['inventory']:
            return False, "That item isn't in your shop!"
        
        business['inventory'][item_id]['price'] = price
        self.save_businesses()
        return True, f"Set price to {price} PsyCoins!"
    
    def purchase_item(self, buyer_id, seller_id, item_id, quantity=1):
        """Purchase item from a business"""
        seller_id = str(seller_id)
        business = self.get_user_business(seller_id)
        if not business:
            return False, "Business not found!", None
        
        if item_id not in business['inventory']:
            return False, "Item not available!", None
        
        item = business['inventory'][item_id]
        if item['quantity'] < quantity:
            return False, f"Only {item['quantity']} in stock!", None
        
        total_cost = item['price'] * quantity
        
        # Update business
        item['quantity'] -= quantity
        if item['quantity'] == 0:
            del business['inventory'][item_id]
        
        business['sales'] += quantity
        business['revenue'] += total_cost
        
        self.save_businesses()
        
        return True, f"Purchased {quantity}x {item['name']} for {total_cost} PsyCoins!", total_cost

    def add_employee(self, owner_id, worker_id):
        owner_id = str(owner_id)
        worker_id = str(worker_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False, "Owner has no business"
        employees = business.get('employees', {})
        if worker_id in employees:
            return False, "You already work here!"
        employees[worker_id] = {"last_shift": None, "stability": 100, "role": "worker", "salary": 20, "last_pay": None}
        business['employees'] = employees
        self.save_businesses()
        return True, "Joined as employee"

    def record_shift(self, owner_id, worker_id, amount):
        owner_id = str(owner_id)
        worker_id = str(worker_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False
        employees = business.get('employees', {})
        if worker_id not in employees:
            return False
        employees[worker_id]['last_shift'] = datetime.utcnow().isoformat()
        business['revenue'] = business.get('revenue', 0) - amount
        self.save_businesses()
        return True

    def set_employee_salary(self, owner_id, worker_id, salary):
        owner_id = str(owner_id)
        worker_id = str(worker_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False, "Owner has no business"
        employees = business.get('employees', {})
        if worker_id not in employees:
            return False, "Worker not found"
        employees[worker_id]['salary'] = int(salary)
        business['employees'] = employees
        self.save_businesses()
        return True, "Salary updated"

    def promote_employee(self, owner_id, worker_id):
        owner_id = str(owner_id)
        worker_id = str(worker_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False, "Owner has no business"
        employees = business.get('employees', {})
        if worker_id not in employees:
            return False, "Worker not found"
        # simple promotion path
        role = employees[worker_id].get('role', 'worker')
        if role == 'worker':
            employees[worker_id]['role'] = 'manager'
            employees[worker_id]['salary'] = int(employees[worker_id].get('salary', 20) * 1.5)
        elif role == 'manager':
            employees[worker_id]['role'] = 'director'
            employees[worker_id]['salary'] = int(employees[worker_id].get('salary', 30) * 1.5)
        business['employees'] = employees
        self.save_businesses()
        return True, f"Promoted to {employees[worker_id]['role']}"

    def fire_employee(self, owner_id, worker_id):
        owner_id = str(owner_id)
        worker_id = str(worker_id)
        business = self.get_user_business(owner_id)
        if not business:
            return False, "Owner has no business"
        employees = business.get('employees', {})
        if worker_id not in employees:
            return False, "Worker not found"
        del employees[worker_id]
        business['employees'] = employees
        self.save_businesses()
        return True, "Employee removed"
    
    def get_all_businesses(self):
        """Get all businesses across all servers"""
        return self.businesses
    
    def search_marketplace(self, query=None):
        """Search the cross-server marketplace"""
        results = []
        for user_id, business in self.businesses.items():
            if not business['inventory']:
                continue
            
            for item_id, item in business['inventory'].items():
                if query and query.lower() not in item['name'].lower():
                    continue
                
                results.append({
                    'business_name': business['name'],
                    'owner_id': user_id,
                    'item': item,
                    'item_id': item_id,
                    'rating': business['rating']
                })
        
        # Sort by price (lowest first)
        results.sort(key=lambda x: x['item']['price'])
        return results

    def _ensure_platform(self):
        if "_platform" not in self.businesses:
            self.businesses["_platform"] = {"fee_pct": 0.05, "balance": 0}
            self.save_businesses()

    def add_platform_fee(self, amount: int):
        """Add collected marketplace fee to platform balance."""
        self._ensure_platform()
        self.businesses["_platform"]["balance"] = self.businesses["_platform"].get("balance", 0) + int(amount)
        self.save_businesses()

    def get_platform_info(self):
        self._ensure_platform()
        return self.businesses.get("_platform", {"fee_pct": 0.05, "balance": 0})

    def set_fee_pct(self, pct: float):
        self._ensure_platform()
        self.businesses["_platform"]["fee_pct"] = float(pct)
        self.save_businesses()

    def withdraw_platform_balance(self, amount: int):
        self._ensure_platform()
        bal = self.businesses["_platform"].get("balance", 0)
        if amount > bal:
            return False, bal
        self.businesses["_platform"]["balance"] = bal - int(amount)
        self.save_businesses()
        return True, self.businesses["_platform"]["balance"]

class ShopView(View):
    def __init__(self, ctx, shop_data, shop_type, owner_id=None):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.shop_data = shop_data
        self.shop_type = shop_type  # 'npc' or 'user'
        self.owner_id = owner_id
        
        # Add item buttons
        items = list(shop_data.items())[:25]  # Discord limit
        for i, (item_id, item_data) in enumerate(items):
            if i < 5:  # First row
                button = Button(
                    label=f"{item_data.get('emoji', '📦')} {item_data['name']}",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"buy_{item_id}"
                )
                button.callback = self.create_buy_callback(item_id, item_data)
                self.add_item(button)
    
    def create_buy_callback(self, item_id, item_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("This shop isn't for you!", ephemeral=True)
                return
            
            # Show purchase confirmation
            embed = EmbedBuilder.create(
                title=f"{Emojis.MONEY} Purchase Confirmation",
                description=f"**Item:** {item_data.get('emoji', '📦')} {item_data['name']}\n"
                           f"**Price:** {item_data['price']} PsyCoins\n"
                           f"**In Stock:** {item_data.get('quantity', '∞')}\n\n"
                           f"Use `L!buy {item_id}` to purchase!",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        return callback

class Business(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = BusinessManager(data_dir)
        self.inventory_file = os.path.join(data_dir, "inventory.json")
        # Start background tasks
        self.process_shipments_task.start()
        self.passive_income_task.start()
        self.payroll_task.start()
    
    # Economy is handled by the central Economy cog; file fallbacks are done inline where necessary.
    
    def load_inventory(self):
        """Load inventory data"""
        if os.path.exists(self.inventory_file):
            try:
                with open(self.inventory_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_inventory(self, data):
        """Save inventory data"""
        try:
            with open(self.inventory_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving inventory: {e}")
    
    @commands.group(name="business", aliases=["biz", "myshop"])
    async def business(self, ctx):
        """Business management commands"""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create(
                title=f"{Emojis.MONEY} Business System",
                description="Create and manage your cross-server shop!\n\n"
                           "**Commands:**\n"
                           f"{Emojis.SPARKLES} `L!business create <name>` - Start your business (500 coins)\n"
                           f"{Emojis.TREASURE} `L!business stock <item>` - Add inventory items\n"
                           f"{Emojis.COIN} `L!business price <item> <price>` - Set item prices\n"
                           f"{Emojis.TROPHY} `L!business view [@user]` - View a shop\n"
                           f"{Emojis.CHART} `L!business stats` - View your business stats\n\n"
                           "**Shopping:**\n"
                           f"{Emojis.GAME} `L!shop <npc/user>` - Browse shops\n"
                           f"{Emojis.MONEY} `L!buy <item> [quantity]` - Purchase items\n"
                           f"{Emojis.FIRE} `L!marketplace [search]` - Cross-server marketplace",
                color=Colors.PRIMARY
            )
            await ctx.send(embed=embed)
    
    @business.command(name="create")
    async def business_create(self, ctx, *, name: str):
        """Create a new business (costs 500 PsyCoins)"""
        economy_cog = self.bot.get_cog("Economy")
        user_id = str(ctx.author.id)

        if economy_cog:
            balance = economy_cog.get_balance(ctx.author.id)
            if balance < 500:
                embed = EmbedBuilder.create(
                    title=f"{Emojis.ERROR} Insufficient Funds",
                    description="You need **500 PsyCoins** to start a business!",
                    color=Colors.ERROR
                )
                await ctx.send(embed=embed)
                return

        success, message = self.manager.create_business(user_id, name, "A new business")

        if success:
            # Deduct coins via Economy cog if available
            if economy_cog:
                try:
                    economy_cog.remove_coins(ctx.author.id, 500)
                except Exception:
                    pass

            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Business Created!",
                description=f"**{name}** is now open for business!\n\n"
                           f"💰 Startup Cost: -500 PsyCoins\n"
                           f"📦 Stock items: `L!business stock`\n"
                           f"💵 Set prices: `L!business price`\n\n"
                           f"Your shop is now live on the cross-server marketplace!",
                color=Colors.SUCCESS
            )
        else:
            embed = EmbedBuilder.create(
                title=f"{Emojis.ERROR} Creation Failed",
                description=message,
                color=Colors.ERROR
            )

        await ctx.send(embed=embed)
    
    @business.command(name="view")
    async def business_view(self, ctx, user: discord.User = None):
        """View a user's business"""
        target = user or ctx.author
        business = self.manager.get_user_business(target.id)
        
        if not business:
            embed = EmbedBuilder.create(
                title=f"{Emojis.ERROR} No Business",
                description=f"**{target.display_name}** doesn't own a business!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed)
            return
        
        # Build inventory display
        inventory_text = ""
        if business['inventory']:
            for item_id, item in list(business['inventory'].items())[:10]:
                inventory_text += f"{item.get('emoji', '📦')} **{item['name']}**\n"
                inventory_text += f"  └ {item['price']} coins • {item['quantity']} in stock\n"
        else:
            inventory_text = "*No items in stock*"
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.MONEY} {business['name']}",
            description=f"**Owner:** {target.mention}\n"
                       f"**Rating:** {'⭐' * int(business['rating'])} ({business['rating']:.1f}/5.0)\n"
                       f"**Total Sales:** {business['sales']} items\n"
                       f"**Revenue:** {business['revenue']} PsyCoins\n\n"
                       f"**Inventory:**\n{inventory_text}",
            color=Colors.PRIMARY
        )
        
        if business['inventory']:
            view = ShopView(ctx, business['inventory'], 'user', target.id)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    @business.command(name="stock")
    async def business_stock(self, ctx, item_id: str, quantity: int = 1, price: int = None):
        """Stock items from your inventory into your business"""
        owner_id = str(ctx.author.id)
        business = self.manager.get_user_business(owner_id)
        if not business:
            await ctx.send("❌ You don't own a business! Create one with `L!business create <name>`")
            return

        economy_cog = self.bot.get_cog("Economy")

        # Check owner's inventory and remove items
        if economy_cog:
            inv = economy_cog.get_inventory(ctx.author.id)
            available = inv.get(item_id, 0)
            if available < quantity:
                await ctx.send(f"❌ You only have {available}x {item_id} in your inventory.")
                return
            try:
                economy_cog.remove_item(ctx.author.id, item_id, quantity)
            except Exception:
                pass
            # Resolve item display name and emoji
            item_name = economy_cog.shop_items.get(item_id, {}).get('name', item_id)
            emoji = economy_cog.shop_items.get(item_id, {}).get('emoji', '📦') if hasattr(economy_cog, 'shop_items') else '📦'
        else:
            inv = self.load_inventory()
            owner_inv = inv.get(owner_id, {})
            available = owner_inv.get(item_id, 0)
            if available < quantity:
                await ctx.send(f"❌ You only have {available}x {item_id} in your inventory.")
                return
            owner_inv[item_id] -= quantity
            if owner_inv[item_id] <= 0:
                del owner_inv[item_id]
            inv[owner_id] = owner_inv
            self.save_inventory(inv)
            item_name = item_id
            emoji = '📦'

        item_data = {
            "id": item_id,
            "name": item_name,
            "quantity": quantity,
            "price": price or 10,
            "emoji": emoji
        }

        success, msg = self.manager.add_item_to_business(owner_id, item_data)
        if success:
            await ctx.send(f"✅ {msg}")
        else:
            await ctx.send(f"❌ {msg}")

    @commands.command(name="feebalance")
    @commands.has_permissions(administrator=True)
    async def feebalance_command(self, ctx):
        """Show current accumulated marketplace fees and fee percent"""
        info = self.manager.get_platform_info()
        fee_pct = info.get('fee_pct', 0.05)
        bal = info.get('balance', 0)
        embed = EmbedBuilder.create(
            title=f"{Emojis.TREASURE} Marketplace Fees",
            description=f"**Fee Percent:** {fee_pct*100:.2f}%\n**Accumulated Fees:** {bal} PsyCoins",
            color=Colors.PRIMARY
        )
        await ctx.send(embed=embed)

    @commands.command(name="feeset")
    @commands.has_permissions(administrator=True)
    async def feeset_command(self, ctx, percent: float):
        """Set marketplace fee percent (e.g., 5 for 5%)"""
        if percent < 0 or percent > 100:
            await ctx.send("❌ Percent must be between 0 and 100.")
            return
        self.manager.set_fee_pct(percent/100.0)
        await ctx.send(f"✅ Marketplace fee set to {percent:.2f}%")

    @commands.command(name="feewithdraw")
    @commands.has_permissions(administrator=True)
    async def feewithdraw_command(self, ctx, amount: int, target: discord.User = None):
        """Withdraw accumulated marketplace fees to a target user (admin only)"""
        target = target or ctx.author
        ok, remaining = self.manager.withdraw_platform_balance(int(amount))
        if not ok:
            await ctx.send(f"❌ Not enough platform fees. Current balance: {remaining}")
            return
        econ = self.bot.get_cog('Economy')
        if econ:
            try:
                econ.add_coins(target.id, int(amount), 'fee_withdraw')
            except Exception:
                pass
        else:
            econ_file = os.path.join(self.manager.data_dir, 'economy.json')
            data = {}
            if os.path.exists(econ_file):
                try:
                    with open(econ_file, 'r') as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data.setdefault(str(target.id), {'balance': 0})
            data[str(target.id)]['balance'] = data[str(target.id)].get('balance', 0) + int(amount)
            try:
                with open(econ_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

        await ctx.send(f"✅ Withdrew {amount} PsyCoins to {target.display_name}. Remaining platform balance: {remaining}")

    @business.command(name="price")
    async def business_price(self, ctx, item_id: str, price: int):
        """Set the price for an item in your business"""
        owner_id = str(ctx.author.id)
        success, msg = self.manager.set_item_price(owner_id, item_id, price)
        if success:
            await ctx.send(f"✅ {msg}")
        else:
            await ctx.send(f"❌ {msg}")
    
    @commands.command(name="npcshop")
    async def shop_command(self, ctx, shop_name: str = None):
        """Browse NPC shops or user shops"""
        if not shop_name:
            # Show list of NPC shops
            embed = EmbedBuilder.create(
                title=f"{Emojis.MONEY} Available Shops",
                description="**NPC Shops** (Fixed prices - cheaper than users):\n\n",
                color=Colors.PRIMARY
            )
            
            for shop_id, shop in self.manager.npc_shops.items():
                embed.description += f"{shop['name']}\n*{shop['description']}*\n`L!npcshop {shop_id}`\n\n"
            
            embed.description += "\n**User Shops:**\nUse `L!marketplace` to browse player shops!"
            await ctx.send(embed=embed)
            return
        
        # Check if it's an NPC shop
        if shop_name.lower() in self.manager.npc_shops:
            shop = self.manager.npc_shops[shop_name.lower()]
            
            items_text = ""
            for item_id, item in shop['items'].items():
                items_text += f"{item['emoji']} **{item['name']}** - {item['price']} coins"
                if 'energy' in item:
                    items_text += f" (⚡+{item['energy']})"
                items_text += f"\n  └ `L!buy {item_id}`\n"
            
            embed = EmbedBuilder.create(
                title=shop['name'],
                description=f"*{shop['description']}*\n\n{items_text}",
                color=Colors.SUCCESS
            )
            
            view = ShopView(ctx, shop['items'], 'npc')
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(f"❌ Shop `{shop_name}` not found! Use `L!shop` to see available shops.")
    
    @commands.command(name="npcbuy")
    async def buy_command(self, ctx, item_id: str, quantity: int = 1):
        """Buy an item from a shop (use L!buy from economy.py for regular shop purchases)"""
        economy_cog = self.bot.get_cog("Economy")
        user_id = str(ctx.author.id)

        # Check NPC shops first
        item_found = False
        for shop_id, shop in self.manager.npc_shops.items():
            if item_id in shop['items']:
                item = shop['items'][item_id]
                total_cost = item['price'] * quantity

                if economy_cog:
                    balance = economy_cog.get_balance(ctx.author.id)
                    if balance < total_cost:
                        await ctx.send(f"❌ You need {total_cost} PsyCoins! You have {balance}.")
                        return
                    # Deduct and add item via Economy cog
                    economy_cog.remove_coins(ctx.author.id, total_cost)
                    try:
                        economy_cog.add_item(ctx.author.id, item_id, quantity)
                    except Exception:
                        pass
                    new_balance = economy_cog.get_balance(ctx.author.id)

                    embed = EmbedBuilder.create(
                        title=f"{Emojis.SUCCESS} Purchase Complete!",
                        description=f"Bought **{quantity}x {item['emoji']} {item['name']}**\n"
                                   f"💰 Paid: {total_cost} PsyCoins\n"
                                   f"💵 Balance: {new_balance} PsyCoins",
                        color=Colors.SUCCESS
                    )
                    await ctx.send(embed=embed)
                else:
                    # Fallback to local files (read/write inline)
                    inventory = self.load_inventory()
                    economy_file = os.path.join(self.manager.data_dir, "economy.json")
                    economy = {}
                    if os.path.exists(economy_file):
                        try:
                            with open(economy_file, 'r') as f:
                                economy = json.load(f)
                        except Exception:
                            economy = {}

                    if user_id not in economy:
                        economy[user_id] = {"balance": 0}
                    if economy[user_id]["balance"] < total_cost:
                        await ctx.send(f"❌ You need {total_cost} PsyCoins! You have {economy[user_id]['balance']}.")
                        return
                    economy[user_id]["balance"] -= total_cost
                    if user_id not in inventory:
                        inventory[user_id] = {}
                    if item_id not in inventory[user_id]:
                        inventory[user_id][item_id] = {"name": item['name'], "quantity": 0, "emoji": item['emoji']}
                    inventory[user_id][item_id]['quantity'] += quantity

                    # Save fallback data
                    try:
                        with open(economy_file, 'w') as f:
                            json.dump(economy, f, indent=4)
                    except Exception:
                        pass
                    self.save_inventory(inventory)

                    embed = EmbedBuilder.create(
                        title=f"{Emojis.SUCCESS} Purchase Complete!",
                        description=f"Bought **{quantity}x {item['emoji']} {item['name']}**\n"
                                   f"💰 Paid: {total_cost} PsyCoins\n"
                                   f"💵 Balance: {economy[user_id]['balance']} PsyCoins",
                        color=Colors.SUCCESS
                    )
                    await ctx.send(embed=embed)

                item_found = True
                break
        
        if not item_found:
            await ctx.send(f"❌ Item `{item_id}` not found in any shop!")
    
    @commands.command(name="marketplace", aliases=["market"])
    async def marketplace_command(self, ctx, *, search: str = None):
        """Browse the cross-server marketplace"""
        results = self.manager.search_marketplace(search)

        if not results:
            embed = EmbedBuilder.create(
                title=f"{Emojis.TREASURE} Marketplace",
                description="No items found! Be the first to sell something!",
                color=Colors.WARNING
            )
            await ctx.send(embed=embed)
            return

        # Paginated view
        pages = []
        per_page = 6
        for i in range(0, len(results), per_page):
            chunk = results[i:i+per_page]
            text = ""
            for j, result in enumerate(chunk, 1):
                item = result['item']
                text += f"**{i+j}.** {item.get('emoji', '📦')} {item['name']} — {item.get('price',0)} coins • {item.get('quantity',0)} in {result['business_name']}\n"
            embed = EmbedBuilder.create(
                title=f"{Emojis.TREASURE} Cross-Server Marketplace",
                description=text + "\nUse `L!buyuser @owner <item_id> <qty>` to purchase.",
                color=Colors.PRIMARY
            )
            pages.append(embed)

        # Simple pagination using buttons
        class Pager(View):
            def __init__(self, pages):
                super().__init__(timeout=120)
                self.pages = pages
                self.index = 0

            async def update(self, interaction=None):
                content = self.pages[self.index]
                if interaction:
                    await interaction.response.edit_message(embed=content, view=self)
                else:
                    await message.edit(embed=content, view=self)

            @discord.ui.button(label='Prev', style=discord.ButtonStyle.secondary)
            async def prev(self, button, interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message('This pager is not for you.', ephemeral=True)
                    return
                self.index = (self.index - 1) % len(self.pages)
                await self.update(interaction)

            @discord.ui.button(label='Next', style=discord.ButtonStyle.secondary)
            async def next(self, button, interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message('This pager is not for you.', ephemeral=True)
                    return
                self.index = (self.index + 1) % len(self.pages)
                await self.update(interaction)

        view = Pager(pages)
        message = await ctx.send(embed=pages[0], view=view)

    @commands.command(name="buyuser")
    async def buyuser_command(self, ctx, owner: discord.User, item_id: str, quantity: int = 1):
        """Buy an item from a user's business"""
        economy_cog = self.bot.get_cog("Economy")
        owner_id = str(owner.id)
        buyer_id = str(ctx.author.id)

        business = self.manager.get_user_business(owner_id)
        if not business:
            await ctx.send("❌ That user doesn't own a business!")
            return

        if item_id not in business['inventory']:
            await ctx.send("❌ Item not found in owner's shop!")
            return

        item = business['inventory'][item_id]
        if item['quantity'] < quantity:
            await ctx.send(f"❌ Only {item['quantity']} in stock!")
            return

        total_cost = item['price'] * quantity

        # Check buyer balance first
        if economy_cog:
            balance = economy_cog.get_balance(ctx.author.id)
            if balance < total_cost:
                await ctx.send(f"❌ You need {total_cost} PsyCoins! You have {balance}.")
                return
        else:
            economy_file = os.path.join(self.manager.data_dir, "economy.json")
            economy = {}
            if os.path.exists(economy_file):
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}
            if buyer_id not in economy:
                economy[buyer_id] = {"balance": 0}
            if economy[buyer_id]["balance"] < total_cost:
                await ctx.send(f"❌ You need {total_cost} PsyCoins! You have {economy[buyer_id]['balance']}.")
                return

        # Perform purchase (update shop inventory)
        success, message, cost = self.manager.purchase_item(ctx.author.id, owner.id, item_id, quantity)
        if not success:
            await ctx.send(f"❌ {message}")
            return

        # Transfer funds with marketplace fee
        fee_pct = 0.05
        # read platform fee pct if configured
        platform_info = self.manager.get_platform_info() if hasattr(self.manager, 'get_platform_info') else {"fee_pct": 0.05, "balance": 0}
        fee_pct = float(platform_info.get('fee_pct', 0.05))
        fee = int(total_cost * fee_pct)
        seller_amount = total_cost - fee

        if economy_cog:
            try:
                economy_cog.remove_coins(ctx.author.id, total_cost)
            except Exception:
                pass
            try:
                economy_cog.add_coins(owner.id, seller_amount, "sale")
            except Exception:
                pass
            # record fee to platform account
            try:
                if hasattr(self.manager, 'add_platform_fee'):
                    self.manager.add_platform_fee(fee)
            except Exception:
                pass
            new_balance = economy_cog.get_balance(ctx.author.id)
            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Purchase Complete!",
                description=f"Bought **{quantity}x {item['emoji']} {item['name']}** from {owner.display_name}\n"
                           f"💰 Paid: {total_cost} PsyCoins (Fee: {fee} PsyCoins)\n"
                           f"💵 Balance: {new_balance} PsyCoins",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
        else:
            # Fallback file adjustments
            economy_file = os.path.join(self.manager.data_dir, "economy.json")
            try:
                with open(economy_file, 'r') as f:
                    economy = json.load(f)
            except Exception:
                economy = {}
            if buyer_id not in economy:
                economy[buyer_id] = {"balance": 0}
            if owner_id not in economy:
                economy[owner_id] = {"balance": 0}
            economy[buyer_id]["balance"] -= total_cost
            # credit seller with amount after fee
            economy[owner_id]["balance"] += seller_amount
            # record fee to platform entry
            try:
                if "_platform" not in self.manager.businesses:
                    self.manager._ensure_platform()
                self.manager.businesses["_platform"]["balance"] = self.manager.businesses["_platform"].get("balance", 0) + fee
                self.manager.save_businesses()
            except Exception:
                pass
            try:
                with open(economy_file, 'w') as f:
                    json.dump(economy, f, indent=4)
            except Exception:
                pass

            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Purchase Complete!",
                description=f"Bought **{quantity}x {item['emoji']} {item['name']}** from {owner.display_name}\n"
                           f"💰 Paid: {total_cost} PsyCoins (Fee: {fee} PsyCoins)",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)

    @commands.command(name="work")
    async def work_command(self, ctx, owner: discord.User):
        """Work a shift at someone's business to earn a wage (1h cooldown)"""
        business = self.manager.get_user_business(str(owner.id))
        if not business:
            await ctx.send("❌ That user doesn't own a business!")
            return

        worker_id = str(ctx.author.id)
        owner_id = str(owner.id)
        employees = business.get('employees', {})
        now = datetime.utcnow()

        if worker_id not in employees:
            # Join as employee
            employees[worker_id] = {"last_shift": None, "stability": 100}
            business['employees'] = employees
            self.manager.save_businesses()
            await ctx.send("✅ You've joined the staff. Use `L!work @owner` again to complete a shift.")
            return

        last = employees[worker_id].get('last_shift')
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                secs = (now - last_dt).total_seconds()
                if secs < 3600:
                    await ctx.send(f"⏳ You recently worked. Try again in {int((3600-secs)/60)}m")
                    return
            except Exception:
                pass

        # Wage calculation
        wage = random.randint(10, 50)

        # Pay from business revenue if available, else attempt owner wallet
        economy_cog = self.bot.get_cog("Economy")
        paid = False
        if business.get('revenue', 0) >= wage:
            business['revenue'] -= wage
            self.manager.record_shift(owner_id, worker_id, wage)
            self.manager.save_businesses()
            if economy_cog:
                try:
                    economy_cog.add_coins(ctx.author.id, wage, "work_shift")
                except Exception:
                    pass
            else:
                economy_file = os.path.join(self.manager.data_dir, "economy.json")
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}
                economy.setdefault(worker_id, {"balance": 0})
                economy[worker_id]["balance"] += wage
                try:
                    with open(economy_file, 'w') as f:
                        json.dump(economy, f, indent=4)
                except Exception:
                    pass
            paid = True
        else:
            # Try to pay from owner's wallet
            if economy_cog:
                owner_balance = economy_cog.get_balance(owner.id)
                if owner_balance >= wage:
                    try:
                        economy_cog.remove_coins(owner.id, wage)
                    except Exception:
                        pass
                    try:
                        economy_cog.add_coins(ctx.author.id, wage, "work_shift")
                    except Exception:
                        pass
                    paid = True
            else:
                economy_file = os.path.join(self.manager.data_dir, "economy.json")
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}
                if economy.get(owner_id, {}).get('balance', 0) >= wage:
                    economy[owner_id]['balance'] -= wage
                    economy.setdefault(worker_id, {"balance": 0})
                    economy[worker_id]['balance'] += wage
                    try:
                        with open(economy_file, 'w') as f:
                            json.dump(economy, f, indent=4)
                    except Exception:
                        pass
                    paid = True

        if paid:
            employees[worker_id]['last_shift'] = now.isoformat()
            business['employees'] = employees
            self.manager.save_businesses()
            await ctx.send(f"✅ Shift complete! You earned **{wage} PsyCoins**.")
        else:
            await ctx.send("❌ Unable to pay wages at this time. Employer/business lacks funds.")

    @commands.command(name="ship")
    async def ship_command(self, ctx, owner: discord.User, item_id: str, quantity: int = 1, eta_minutes: int = 30):
        """Create a shipment from your inventory to someone's business."""
        owner_id = str(owner.id)
        sender_id = str(ctx.author.id)
        economy_cog = self.bot.get_cog("Economy")

        # Verify owner has a business
        business = self.manager.get_user_business(owner_id)
        if not business:
            await ctx.send("❌ Recipient does not own a business.")
            return

        # Remove items from sender inventory
        if economy_cog:
            inv = economy_cog.get_inventory(ctx.author.id)
            have = inv.get(item_id, 0)
            if have < quantity:
                await ctx.send(f"❌ You only have {have}x {item_id}.")
                return
            try:
                economy_cog.remove_item(ctx.author.id, item_id, quantity)
            except Exception:
                pass
            item_name = economy_cog.shop_items.get(item_id, {}).get('name', item_id)
            emoji = economy_cog.shop_items.get(item_id, {}).get('emoji', '📦') if hasattr(economy_cog, 'shop_items') else '📦'
        else:
            inv_file = os.path.join(self.manager.data_dir, "inventory.json")
            inv = {}
            if os.path.exists(inv_file):
                try:
                    with open(inv_file, 'r') as f:
                        inv = json.load(f)
                except Exception:
                    inv = {}
            owner_inv = inv.get(sender_id, {})
            have = owner_inv.get(item_id, 0)
            if have < quantity:
                await ctx.send(f"❌ You only have {have}x {item_id}.")
                return
            owner_inv[item_id] -= quantity
            if owner_inv[item_id] <= 0:
                del owner_inv[item_id]
            inv[sender_id] = owner_inv
            try:
                with open(inv_file, 'w') as f:
                    json.dump(inv, f, indent=4)
            except Exception:
                pass
            item_name = item_id
            emoji = '📦'

        item_data = {"id": item_id, "name": item_name, "quantity": quantity, "price": 0, "emoji": emoji}
        success, msg = self.manager.add_shipment(owner_id, sender_id, item_data, eta_minutes)
        if success:
            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Shipment Scheduled",
                description=f"Scheduled delivery of **{quantity}x {emoji} {item_name}** to {owner.display_name} in {eta_minutes} minutes.",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
        else:
            embed = EmbedBuilder.create(
                title=f"{Emojis.ERROR} Shipment Failed",
                description=msg,
                color=Colors.ERROR
            )
            await ctx.send(embed=embed)

    @tasks.loop(minutes=60.0)
    async def payroll_task(self):
        """Pay employee salaries hourly if possible."""
        try:
            econ = self.bot.get_cog('Economy')
            for owner_id, business in list(self.manager.get_all_businesses().items()):
                employees = business.get('employees', {})
                if not employees:
                    continue
                for worker_id, info in list(employees.items()):
                    try:
                        salary = int(info.get('salary', 0))
                        if salary <= 0:
                            continue
                        # Attempt to pay from business revenue first
                        if business.get('revenue', 0) >= salary:
                            business['revenue'] -= salary
                            self.manager.save_businesses()
                            if econ:
                                try:
                                    econ.add_coins(int(worker_id), salary, 'payroll')
                                except Exception:
                                    pass
                            else:
                                econ_file = os.path.join(self.manager.data_dir, 'economy.json')
                                data = {}
                                if os.path.exists(econ_file):
                                    try:
                                        with open(econ_file, 'r') as f:
                                            data = json.load(f)
                                    except Exception:
                                        data = {}
                                data.setdefault(str(worker_id), {'balance': 0})
                                data[str(worker_id)]['balance'] = data[str(worker_id)].get('balance', 0) + salary
                                try:
                                    with open(econ_file, 'w') as f:
                                        json.dump(data, f, indent=2)
                                except Exception:
                                    pass
                        else:
                            # Try owner wallet
                            owner = int(owner_id)
                            paid = False
                            if econ:
                                try:
                                    bal = econ.get_balance(owner)
                                except Exception:
                                    bal = 0
                                if bal >= salary:
                                    try:
                                        econ.remove_coins(owner, salary)
                                    except Exception:
                                        pass
                                    try:
                                        econ.add_coins(int(worker_id), salary, 'payroll')
                                    except Exception:
                                        pass
                                    paid = True
                            else:
                                econ_file = os.path.join(self.manager.data_dir, 'economy.json')
                                data = {}
                                if os.path.exists(econ_file):
                                    try:
                                        with open(econ_file, 'r') as f:
                                            data = json.load(f)
                                    except Exception:
                                        data = {}
                                if data.get(str(owner), {}).get('balance', 0) >= salary:
                                    data[str(owner)]['balance'] -= salary
                                    data.setdefault(str(worker_id), {'balance': 0})
                                    data[str(worker_id)]['balance'] += salary
                                    try:
                                        with open(econ_file, 'w') as f:
                                            json.dump(data, f, indent=2)
                                    except Exception:
                                        pass
                                    paid = True
                            if not paid:
                                # skip payment this cycle
                                continue
                    except Exception:
                        continue
        except Exception:
            pass

    @payroll_task.before_loop
    async def before_payroll(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5.0)
    async def process_shipments_task(self):
        """Background task to process due shipments."""
        try:
            now = datetime.utcnow()
            changed = False
            for owner_id, business in list(self.manager.get_all_businesses().items()):
                shipments = business.get('incoming_shipments', [])
                for shipment in list(shipments):
                    try:
                        deliver_at = datetime.fromisoformat(shipment['deliver_at'])
                    except Exception:
                        continue
                    if deliver_at <= now:
                        item = shipment['item']
                        inv = business.get('inventory', {})
                        if item['id'] in inv:
                            inv[item['id']]['quantity'] += item.get('quantity', 1)
                        else:
                            inv[item['id']] = item
                        business['inventory'] = inv
                        shipments.remove(shipment)
                        changed = True
                        # notify owner
                        try:
                            user = await self.bot.fetch_user(int(owner_id))
                            embed = EmbedBuilder.create(
                                title=f"{Emojis.SUCCESS} Shipment Delivered!",
                                description=f"Your business received {item.get('quantity',1)}x {item.get('emoji','📦')} {item.get('name')} from <@{shipment['from']}>.",
                                color=Colors.SUCCESS
                            )
                            await user.send(embed=embed)
                        except Exception:
                            pass
                if changed:
                    self.manager.save_businesses()
        except Exception:
            pass

    @tasks.loop(minutes=60.0)
    async def passive_income_task(self):
        """Periodic passive payouts based on shop stock value."""
        try:
            econ = self.bot.get_cog('Economy')
            for owner_id, business in list(self.manager.get_all_businesses().items()):
                try:
                    stock_value = sum((item.get('price', 0) * item.get('quantity', 0)) for item in business.get('inventory', {}).values())
                    # small payout: 0.5% of stock value, min 1 coin if any stock
                    income = int(stock_value * 0.005)
                    if income <= 0 and business.get('inventory'):
                        income = 1
                    if income > 0:
                        if econ:
                            try:
                                econ.add_coins(int(owner_id), income, 'passive_income')
                            except Exception:
                                pass
                        else:
                            # fallback to economy file
                            econ_file = os.path.join(self.manager.data_dir, 'economy.json')
                            data = {}
                            if os.path.exists(econ_file):
                                try:
                                    with open(econ_file, 'r') as f:
                                        data = json.load(f)
                                except Exception:
                                    data = {}
                            data.setdefault(str(owner_id), {'balance': 0})
                            data[str(owner_id)]['balance'] = data[str(owner_id)].get('balance', 0) + income
                            try:
                                with open(econ_file, 'w') as f:
                                    json.dump(data, f, indent=2)
                            except Exception:
                                pass
                        # Optionally notify owner
                        try:
                            user = await self.bot.fetch_user(int(owner_id))
                            if user:
                                await user.send(f"💰 Your shop earned {income} PsyCoins in passive income.")
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

    @process_shipments_task.before_loop
    async def before_shipments(self):
        await self.bot.wait_until_ready()

    @passive_income_task.before_loop
    async def before_passive(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Business(bot))

