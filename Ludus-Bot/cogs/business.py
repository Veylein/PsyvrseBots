import discord
from discord.ext import commands
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
            "sales": 0,
            "revenue": 0,
            "rating": 5.0,
            "reviews": []
        }
        self.save_businesses()
        return True, "Business created successfully!"
    
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
        self.economy_file = os.path.join(data_dir, "economy.json")
        self.inventory_file = os.path.join(data_dir, "inventory.json")
    
    def load_economy(self):
        """Load economy data"""
        if os.path.exists(self.economy_file):
            try:
                with open(self.economy_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_economy(self, data):
        """Save economy data"""
        try:
            with open(self.economy_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving economy: {e}")
    
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
        economy = self.load_economy()
        user_id = str(ctx.author.id)
        
        if user_id not in economy:
            economy[user_id] = {"balance": 0}
        
        if economy[user_id]["balance"] < 500:
            embed = EmbedBuilder.create(
                title=f"{Emojis.ERROR} Insufficient Funds",
                description="You need **500 PsyCoins** to start a business!",
                color=Colors.ERROR
            )
            await ctx.send(embed=embed)
            return
        
        success, message = self.manager.create_business(user_id, name, "A new business")
        
        if success:
            economy[user_id]["balance"] -= 500
            self.save_economy(economy)
            
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
        economy = self.load_economy()
        inventory = self.load_inventory()
        user_id = str(ctx.author.id)
        
        if user_id not in economy:
            economy[user_id] = {"balance": 0}
        
        if user_id not in inventory:
            inventory[user_id] = {}
        
        # Check NPC shops first
        item_found = False
        for shop_id, shop in self.manager.npc_shops.items():
            if item_id in shop['items']:
                item = shop['items'][item_id]
                total_cost = item['price'] * quantity
                
                if economy[user_id]["balance"] < total_cost:
                    await ctx.send(f"❌ You need {total_cost} PsyCoins! You have {economy[user_id]['balance']}.")
                    return
                
                # Process purchase
                economy[user_id]["balance"] -= total_cost
                
                if item_id not in inventory[user_id]:
                    inventory[user_id][item_id] = {
                        "name": item['name'],
                        "quantity": 0,
                        "emoji": item['emoji']
                    }
                
                inventory[user_id][item_id]['quantity'] += quantity
                
                self.save_economy(economy)
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
        
        # Show first 10 results
        items_text = ""
        for i, result in enumerate(results[:10], 1):
            item = result['item']
            items_text += f"**{i}.** {item.get('emoji', '📦')} {item['name']}\n"
            items_text += f"  └ {item['price']} coins • {item['quantity']} stock • {result['business_name']}\n"
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TREASURE} Cross-Server Marketplace",
            description=f"**{len(results)} items available**\n\n{items_text}\n\n"
                       f"Use `L!business view @user` to visit their shop!",
            color=Colors.PRIMARY
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Business(bot))
