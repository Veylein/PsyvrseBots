import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io

class MiningGame:
    """Represents a single mining game session"""
    
    BIOMES = {
        0: {"name": "Surface", "blocks": ["dirt", "stone", "coal"], "hardness": 1.0},
        10: {"name": "Underground", "blocks": ["stone", "coal", "iron"], "hardness": 1.2},
        25: {"name": "Deep Caves", "blocks": ["stone", "iron", "gold", "redstone"], "hardness": 1.5},
        50: {"name": "Mineral Depths", "blocks": ["deepslate", "gold", "diamond", "emerald"], "hardness": 2.0},
        75: {"name": "Ancient Depths", "blocks": ["deepslate", "diamond", "emerald", "netherite"], "hardness": 3.0},
        100: {"name": "Abyss", "blocks": ["bedrock", "netherite", "ancient_debris"], "hardness": 5.0}
    }
    
    BLOCK_VALUES = {
        "dirt": 1, "stone": 2, "coal": 5, "iron": 15, "gold": 50,
        "redstone": 30, "diamond": 200, "emerald": 300, "deepslate": 10,
        "netherite": 1000, "ancient_debris": 500, "bedrock": 0, "grass": 1
    }
    
    BLOCK_COLORS = {
        "dirt": (139, 90, 43), "stone": (128, 128, 128), "coal": (50, 50, 50),
        "iron": (192, 192, 192), "gold": (255, 215, 0), "redstone": (255, 0, 0),
        "diamond": (0, 191, 255), "emerald": (0, 201, 87), "deepslate": (64, 64, 64),
        "netherite": (50, 35, 35), "ancient_debris": (101, 67, 33), "bedrock": (32, 32, 32),
        "air": (135, 206, 235), "shop": (139, 69, 19), "player": (255, 255, 0)
    }
    
    def __init__(self, user_id: int, seed: int = None):
        self.user_id = user_id
        self.seed = seed or random.randint(1, 999999)
        self.rng = random.Random(self.seed)  # Local RNG, doesn't affect global random
        
        # Player state
        self.x = 1  # Starting X position (3 blocks left of shop)
        self.y = -1  # Starting Y position (above grass)
        self.depth = 0  # Max depth reached
        
        # Energy system
        self.energy = 60
        self.max_energy = 60
        self.last_energy_regen = datetime.utcnow()
        
        # Equipment
        self.pickaxe_level = 1
        self.pickaxe_speed = 1.0
        self.backpack_capacity = 20
        
        # Inventory
        self.inventory = {}
        self.coins = 100
        
        # Map generation
        self.width = 11  # View width
        self.height = 10  # View height
        self.map_data = {}  # {(x, y): block_type}
        self.last_map_regen = datetime.utcnow()
        self.generate_world()
        
    def generate_world(self, regenerate=False):
        """Generate procedural world"""
        # Generate shop at y=-1 (above grass surface)
        for x in range(-50, 50):
            if x == 4:  # Shop left
                self.map_data[(x, -1)] = "shop_left"
            elif x == 5:  # Shop right
                self.map_data[(x, -1)] = "shop_right"
            else:
                self.map_data[(x, -1)] = "air"
        
        # Generate surface (y=0) with grass - never overwrite existing blocks (especially air from mining)
        for x in range(-50, 50):
            if (x, 0) not in self.map_data:
                self.map_data[(x, 0)] = "grass"  # Only add grass if position doesn't exist yet
        
        # Generate underground layers starting from y=1
        for y in range(1, 150):
            biome = self.get_biome(y)
            for x in range(-50, 50):
                # Skip if already exists and we're regenerating (preserve mined areas)
                if regenerate and (x, y) in self.map_data and self.map_data[(x, y)] == "air":
                    continue
                
                # Stable procedural generation - deterministic seed per position
                seed_value = (x * 73856093) ^ (y * 19349663) ^ self.seed
                pos_rng = random.Random(seed_value)
                noise = pos_rng.random()
                blocks = biome["blocks"]
                
                # Weight distribution (common blocks more frequent)
                if noise < 0.6:
                    block = blocks[0]  # Most common
                elif noise < 0.85:
                    block = blocks[1] if len(blocks) > 1 else blocks[0]
                elif noise < 0.95:
                    block = blocks[2] if len(blocks) > 2 else blocks[1]
                else:
                    block = blocks[-1]  # Rarest
                
                self.map_data[(x, y)] = block
    
    def get_biome(self, depth: int):
        """Get biome data for given depth"""
        for min_depth in sorted(self.BIOMES.keys(), reverse=True):
            if depth >= min_depth:
                return self.BIOMES[min_depth]
        return self.BIOMES[0]
    
    def get_block(self, x: int, y: int) -> str:
        """Get block at position"""
        if y < -1:  # Only y < -1 is pure air
            return "air"
        return self.map_data.get((x, y), "air")
    
    def can_move(self, new_x: int, new_y: int) -> bool:
        """Check if player can move to position"""
        if new_y < -1:  # Can't go above sky limit
            return False
        
        block = self.get_block(new_x, new_y)
        return block in ["air", "shop_left", "shop_right"]  # Removed grass - it must be mined first
    
    def mine_block(self, x: int, y: int) -> tuple[bool, str]:
        """Mine block at position"""
        # Check distance - can only mine adjacent blocks
        if abs(x - self.x) + abs(y - self.y) != 1:
            return False, "❌ Too far! Can only mine adjacent blocks."
        
        if y < 0:
            return False, "❌ Can't mine in the sky!"
        
        block = self.get_block(x, y)
        if block == "air":
            return False, "❌ Nothing to mine here!"
        
        if block == "bedrock":
            return False, "❌ Bedrock is unbreakable!"
        
        # Energy cost based on biome hardness and pickaxe level
        biome = self.get_biome(y)
        speed_bonus = 1 + (self.pickaxe_level * 0.15)
        energy_cost = max(1, int(biome["hardness"] / speed_bonus))
        
        if self.energy < energy_cost:
            return False, f"❌ Not enough energy! Need {energy_cost}"
        
        # Check inventory space
        total_items = sum(self.inventory.values())
        if total_items >= self.backpack_capacity:
            return False, "❌ Backpack full! Return to surface to sell."
        
        # Mine successful
        self.energy -= energy_cost
        old_block = self.map_data.get((x, y), "unknown")
        self.map_data[(x, y)] = "air"
        self.inventory[block] = self.inventory.get(block, 0) + 1
        
        # Update max depth
        if y > self.depth:
            self.depth = y
        
        value = self.BLOCK_VALUES.get(block, 0)
        return True, f"⛏️ Mined {block}! (+{value} value)", (x, y)
    
    def move_player(self, dx: int, dy: int) -> tuple[bool, str]:
        """Move player by delta"""
        if self.energy <= 0:
            return False, "❌ No energy! Wait for regeneration."
        
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check bounds
        if new_x < -50 or new_x > 50:
            return False, "❌ World boundary!"
        
        # Check if position is blocked
        if not self.can_move(new_x, new_y):
            return False, "❌ Blocked! Mine the block first."
        
        # Energy cost
        self.energy -= 1
        self.x = new_x
        self.y = new_y
        
        # Check if on shop
        if self.y == -1 and self.x in [4, 5]:
            return True, "🏪 You're at the shop! Use the shop menu to trade."
        
        return True, f"Moved to ({self.x}, {self.y})"
    
    def regenerate_energy(self):
        """Regenerate energy over time (1 per 30 seconds)"""
        now = datetime.utcnow()
        elapsed = (now - self.last_energy_regen).total_seconds()
        regen_count = int(elapsed // 30)
        
        if regen_count > 0:
            self.energy = min(self.max_energy, self.energy + regen_count)
            # Don't lose leftover time
            self.last_energy_regen += timedelta(seconds=regen_count * 30)
    
    def check_map_regeneration(self) -> bool:
        """Check if map should regenerate (12 hours)"""
        now = datetime.utcnow()
        elapsed = (now - self.last_map_regen).total_seconds()
        hours_elapsed = elapsed / 3600
        
        if hours_elapsed >= 12:
            self.last_map_regen = now
            self.generate_world(regenerate=True)  # Pass regenerate flag
            return True
        return False
    
    def sell_inventory(self, bot=None) -> tuple[int, str]:
        """Sell all inventory items"""
        if not self.inventory:
            return 0, "❌ Inventory is empty!"
        
        total_value = 0
        items_sold = []
        
        for block, count in self.inventory.items():
            value = self.BLOCK_VALUES.get(block, 0) * count
            total_value += value
            items_sold.append(f"{count}x {block} = {value}")
        
        # Add to main economy if available
        if bot:
            economy_cog = bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(self.user_id, total_value, "mining_sales")
        
        self.coins += total_value
        self.inventory.clear()
        
        return total_value, "\n".join(items_sold)
    
    def render_map(self) -> io.BytesIO:
        """Render current view as image"""
        block_size = 32
        img_width = self.width * block_size
        img_height = self.height * block_size
        
        img = Image.new('RGB', (img_width, img_height), color=(135, 206, 235))
        
        # Cache for loaded textures
        texture_cache = {}
        
        def load_texture(block_type: str) -> Image.Image:
            """Load texture from assets folder"""
            if block_type in texture_cache:
                return texture_cache[block_type]
            
            # Map block types to asset files
            asset_map = {
                "air": "assets/mining/blocks/layer1/air.png",
                "dirt": "assets/mining/blocks/layer1/dirt.png",
                "grass": "assets/mining/blocks/layer1/grass.png",
                "stone": "assets/mining/blocks/layer1/dirt.png",  # Fallback to dirt
                "coal": "assets/mining/blocks/layer1/coal.png",
                "iron": "assets/mining/blocks/layer1/iron.png",
                "gold": "assets/mining/blocks/layer1/iron.png",  # Fallback
                "redstone": "assets/mining/blocks/layer1/coal.png",  # Fallback
                "diamond": "assets/mining/blocks/layer1/iron.png",  # Fallback
                "emerald": "assets/mining/blocks/layer1/iron.png",  # Fallback
                "deepslate": "assets/mining/blocks/layer1/dirt.png",  # Fallback
                "netherite": "assets/mining/blocks/layer1/coal.png",  # Fallback
                "ancient_debris": "assets/mining/blocks/layer1/coal.png",  # Fallback
                "bedrock": "assets/mining/blocks/layer1/coal.png",  # Fallback
                "shop_left": "assets/mining/shop/shop1_left.png",
                "shop_right": "assets/mining/shop/shop1_right.png",
            }
            
            try:
                asset_path = asset_map.get(block_type, "assets/mining/blocks/layer1/dirt.png")
                texture = Image.open(asset_path).convert("RGBA")
                texture = texture.resize((block_size, block_size), Image.LANCZOS)
                texture_cache[block_type] = texture
                return texture
            except:
                # Fallback to colored rectangle if asset missing
                fallback = Image.new('RGBA', (block_size, block_size), self.BLOCK_COLORS.get(block_type, (0, 0, 0)))
                texture_cache[block_type] = fallback
                return fallback
        
        # Calculate view bounds (centered on player)
        start_x = self.x - self.width // 2
        start_y = self.y - self.height // 2
        
        # Draw blocks
        for dy in range(self.height):
            for dx in range(self.width):
                world_x = start_x + dx
                world_y = start_y + dy
                
                # Get block type
                block = self.get_block(world_x, world_y)
                
                # Load and paste texture
                x1 = dx * block_size
                y1 = dy * block_size
                texture = load_texture(block)
                img.paste(texture, (x1, y1), texture if texture.mode == 'RGBA' else None)
        
        # Draw player overlay
        player_x = self.width // 2
        player_y = self.height // 2
        try:
            player_texture = Image.open("assets/mining/character/avatar.png").convert("RGBA")
            player_texture = player_texture.resize((block_size, block_size), Image.LANCZOS)
            img.paste(player_texture, (player_x * block_size, player_y * block_size), player_texture)
        except:
            # Fallback to yellow circle if avatar missing
            draw = ImageDraw.Draw(img)
            center_x = player_x * block_size + block_size // 2
            center_y = player_y * block_size + block_size // 2
            radius = block_size // 3
            draw.ellipse([center_x - radius, center_y - radius, 
                        center_x + radius, center_y + radius], 
                       fill=self.BLOCK_COLORS["player"])
        
        # Draw UI overlay with stats
        draw = ImageDraw.Draw(img)
        
        # Try to load font
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # UI background (semi-transparent dark overlay at top)
        ui_height = 35
        overlay = Image.new('RGBA', (img_width, ui_height), (0, 0, 0, 180))
        img_rgba = img.convert('RGBA')
        img_rgba.paste(overlay, (0, 0), overlay)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Draw stats with PNG icons
        inventory_size = sum(self.inventory.values())
        icon_size = 20
        
        # Load UI icons
        def load_ui_icon(path: str) -> Image.Image:
            try:
                icon = Image.open(path).convert("RGBA")
                icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
                return icon
            except:
                # Return transparent fallback
                return Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        
        # Energy icon and text
        energy_icon = load_ui_icon("assets/mining/ui/energy.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(energy_icon, (5, 3), energy_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        energy_text = f"{self.energy}/{self.max_energy}"
        draw.text((28, 5), energy_text, fill=(255, 255, 100), font=font)
        
        # Energy bar visualization
        bar_x = 5
        bar_y = 23
        bar_width = 80
        bar_height = 8
        # Background bar
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(40, 40, 40), outline=(80, 80, 80))
        # Filled bar
        fill_width = int((self.energy / self.max_energy) * bar_width)
        if self.energy > 0:
            bar_color = (100, 200, 255) if self.energy > self.max_energy * 0.3 else (255, 100, 100)
            draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=bar_color)
        
        # Coins icon and text
        coins_icon = load_ui_icon("assets/mining/ui/coins.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(coins_icon, (95, 3), coins_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        coins_text = f"{self.coins}"
        draw.text((118, 5), coins_text, fill=(255, 215, 0), font=font)
        
        # Inventory/backpack icon and text
        # Determine backpack level based on capacity
        backpack_level = (self.backpack_capacity - 20) // 10 + 1  # Level 1 = 20 cap, Level 2 = 30, etc.
        backpack_icon = load_ui_icon(f"assets/mining/ui/backpack/backpack{backpack_level}.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(backpack_icon, (228, 3), backpack_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        inv_text = f"{inventory_size}/{self.backpack_capacity}"
        inv_color = (255, 100, 100) if inventory_size >= self.backpack_capacity else (100, 255, 100)
        draw.text((248, 5), inv_text, fill=inv_color, font=font)
        
        # Pickaxe icon and level
        pickaxe_icon = load_ui_icon("assets/mining/ui/pickaxe.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(pickaxe_icon, (300, 3), pickaxe_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        pick_text = f"Lv.{self.pickaxe_level}"
        draw.text((324, 5), pick_text, fill=(255, 255, 255), font=font)
        
        # Draw no energy warning in center if energy is 0
        if self.energy <= 0:
            # Create warning overlay
            warning_font = ImageFont.truetype("arial.ttf", 24) if font != ImageFont.load_default() else font
            warning_text = "NO ENERGY!"
            
            # Load energy icon for warning
            energy_warning_icon = load_ui_icon("assets/mining/ui/energy.png")
            energy_warning_size = 32
            energy_warning_icon = energy_warning_icon.resize((energy_warning_size, energy_warning_size), Image.LANCZOS)
            
            # Get text size
            bbox = draw.textbbox((0, 0), warning_text, font=warning_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Total width including icon and spacing
            total_width = energy_warning_size + 10 + text_width
            
            # Center position
            center_x = img_width // 2
            center_y = img_height // 2
            
            # Draw semi-transparent background
            padding = 20
            bg_x1 = center_x - total_width // 2 - padding
            bg_y1 = center_y - max(energy_warning_size, text_height) // 2 - padding
            bg_x2 = center_x + total_width // 2 + padding
            bg_y2 = center_y + max(energy_warning_size, text_height) // 2 + padding
            
            overlay_warning = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            draw_warning = ImageDraw.Draw(overlay_warning)
            draw_warning.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(139, 0, 0, 200))
            
            img_rgba = img.convert('RGBA')
            img_rgba = Image.alpha_composite(img_rgba, overlay_warning)
            
            # Paste energy icon
            icon_x = center_x - total_width // 2
            icon_y = center_y - energy_warning_size // 2
            img_rgba.paste(energy_warning_icon, (icon_x, icon_y), energy_warning_icon)
            
            img = img_rgba.convert('RGB')
            draw = ImageDraw.Draw(img)
            
            # Draw warning text
            text_x = icon_x + energy_warning_size + 10
            text_y = center_y - text_height // 2
            draw.text((text_x, text_y), warning_text, fill=(255, 255, 100), font=warning_font)
        
        # Draw biome info below top UI
        biome = self.get_biome(self.y)
        
        # Calculate time until map reset
        now = datetime.utcnow()
        elapsed = (now - self.last_map_regen).total_seconds()
        hours_left = 12 - (elapsed / 3600)
        
        if hours_left <= 0:
            reset_text = "Ready!"
        elif hours_left < 1:
            minutes_left = int(hours_left * 60)
            reset_text = f"reset in {minutes_left}m"
        else:
            hours = int(hours_left)
            minutes = int((hours_left - hours) * 60)
            reset_text = f"reset in {hours}h {minutes}m"
        
        biome_text = f"{biome['name']} (Y: {self.y}) • {reset_text}"
        
        # Create semi-transparent background for biome text
        biome_overlay = Image.new('RGBA', (img_width, 25), (0, 0, 0, 150))
        img_rgba = img.convert('RGBA')
        img_rgba.paste(biome_overlay, (0, 35), biome_overlay)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Draw biome text centered (only once!)
        bbox = draw.textbbox((0, 0), biome_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        text_x = (img_width - text_width) // 2
        draw.text((text_x, 41), biome_text, fill=(200, 200, 255), font=font_small)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    def get_stats_text(self) -> str:
        """Get stats display text"""
        biome = self.get_biome(self.y)
        inventory_size = sum(self.inventory.values())
        
        return (f"**Position:** ({self.x}, {self.y})\n")
    
    def to_dict(self) -> dict:
        """Serialize game state to dictionary"""
        # Convert map_data keys from tuples to strings for JSON
        map_data_serialized = {f"{x},{y}": block for (x, y), block in self.map_data.items()}
        
        return {
            "user_id": self.user_id,
            "seed": self.seed,
            "x": self.x,
            "y": self.y,
            "depth": self.depth,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "last_energy_regen": self.last_energy_regen.isoformat(),
            "pickaxe_level": self.pickaxe_level,
            "backpack_capacity": self.backpack_capacity,
            "inventory": self.inventory,
            "coins": self.coins,
            "last_map_regen": self.last_map_regen.isoformat(),
            "map_data": map_data_serialized
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize game state from dictionary"""
        game = cls.__new__(cls)
        game.user_id = data["user_id"]
        game.seed = data["seed"]
        game.rng = random.Random(game.seed)
        game.x = data["x"]
        game.y = data["y"]
        game.depth = data["depth"]
        game.energy = data["energy"]
        game.max_energy = data["max_energy"]
        game.last_energy_regen = datetime.fromisoformat(data["last_energy_regen"])
        game.pickaxe_level = data["pickaxe_level"]
        game.pickaxe_speed = 1.0
        game.backpack_capacity = data["backpack_capacity"]
        game.inventory = data["inventory"]
        game.coins = data["coins"]
        game.last_map_regen = datetime.fromisoformat(data["last_map_regen"])
        game.width = 11
        game.height = 10
        
        # Deserialize map_data
        game.map_data = {}
        for key, block in data["map_data"].items():
            x, y = map(int, key.split(","))
            game.map_data[(x, y)] = block
        
        return game


class MiningView(discord.ui.LayoutView):
    """Mining game interface using Components v2"""
    
    def __init__(self, game: MiningGame, user_id: int, bot):
        self.game = game
        self.user_id = user_id
        self.bot = bot
        self.message = None
        
        # Regenerate energy before rendering
        self.game.regenerate_energy()
        
        # Render map image and store as file
        map_image = self.game.render_map()
        self.map_file = discord.File(map_image, filename="mining_map.png")
        
        # Create buttons with callbacks
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        mine_btn = discord.ui.Button(style=discord.ButtonStyle.success, emoji="⛏️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        up_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⬆️", label="Surface")
        
        left_btn.callback = self.left_callback
        mine_btn.callback = self.mine_callback
        right_btn.callback = self.right_callback
        up_btn.callback = self.up_callback
        
        # Create container as class attribute
        container_items = [
            discord.ui.TextDisplay(content=f"# ⛏ MINING ADVENTURE\n\n{self.game.get_stats_text()}"),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://mining_map.png",
                    description=f"Seed: {self.game.seed}"
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Add shop dropdown if starting at shop
        if self.game.y == -1 and self.game.x in [4, 5]:
            shop_select = discord.ui.Select(
                placeholder="🏪 Shop Options",
                options=[
                    discord.SelectOption(label="💰 Sell Inventory", value="sell", description="Sell all items in inventory"),
                    discord.SelectOption(label="⛏️ Upgrade Pickaxe", value="pickaxe", description=f"Cost: {self.game.pickaxe_level * 500} coins"),
                    discord.SelectOption(label="🎒 Upgrade Backpack", value="backpack", description=f"Cost: {self.game.backpack_capacity * 100} coins"),
                    discord.SelectOption(label="⚡ Upgrade Max Energy", value="energy", description=f"Cost: {self.game.max_energy * 50} coins"),
                ]
            )
            shop_select.callback = self.shop_callback
            container_items.append(discord.ui.ActionRow(shop_select))
        
        # Add inventory dropdown (always visible)
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=[
                discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
                discord.SelectOption(label="🔦 Torch (Coming Soon)", value="torch", description="Light up dark caves"),
                discord.SelectOption(label="🧭 Compass (Coming Soon)", value="compass", description="Find your way back"),
                discord.SelectOption(label="🪜 Ladder (Coming Soon)", value="ladder", description="Climb back up easily"),
                discord.SelectOption(label="💎 Gem Detector (Coming Soon)", value="detector", description="Find rare ores"),
            ]
        )
        inventory_select.callback = self.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(left_btn, mine_btn, right_btn),
            discord.ui.ActionRow(up_btn),
            discord.ui.ActionRow(inventory_select),
        ])
        
        self.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5D4E37),
        )
        
        super().__init__(timeout=300)
        self.add_item(self.container1)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow game owner to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return False
        return True
    
    async def inventory_callback(self, interaction: discord.Interaction):
        """Handle inventory dropdown selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        if action == "view_inv":
            if not self.game.inventory:
                await interaction.response.send_message("🎒 **Inventory is empty!**", ephemeral=True)
                return
            
            inv_text = "🎒 **Current Inventory:**\n"
            for block, count in self.game.inventory.items():
                value = self.game.BLOCK_VALUES.get(block, 0)
                inv_text += f"• {count}x {block} (${value * count})\n"
            
            total_value = sum(self.game.BLOCK_VALUES.get(b, 0) * c for b, c in self.game.inventory.items())
            inv_text += f"\n💰 **Total Value:** {total_value} psycoins"
            
            await interaction.response.send_message(inv_text, ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ This item is coming soon!", ephemeral=True)
    
    async def shop_callback(self, interaction: discord.Interaction):
        """Handle shop dropdown selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        if action == "sell":
            if not self.game.inventory:
                await self.refresh(interaction, "❌ Inventory is empty!")
                return
            value, items = self.game.sell_inventory(interaction.client)
            await self.refresh(interaction, f"💰 Sold items for {value} psycoins!")
        
        elif action == "pickaxe":
            cost = self.game.pickaxe_level * 500
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "❌ Economy system not available.")
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_balance(interaction.user.id)
                self.game.pickaxe_level += 1
                await self.refresh(interaction, f"⛏️ Upgraded pickaxe to level {self.game.pickaxe_level}!")
            else:
                await self.refresh(interaction, f"❌ Need {cost} psycoins!")
        
        elif action == "backpack":
            cost = self.game.backpack_capacity * 100
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "❌ Economy system not available.")
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_balance(interaction.user.id)
                self.game.backpack_capacity += 10
                await self.refresh(interaction, f"🎒 Upgraded backpack to {self.game.backpack_capacity} slots!")
            else:
                await self.refresh(interaction, f"❌ Need {cost} psycoins!")
        
        elif action == "energy":
            cost = self.game.max_energy * 50
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "❌ Economy system not available.")
                return
            
            if economy_cog.remove_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_balance(interaction.user.id)
                self.game.max_energy += 20
                self.game.energy = self.game.max_energy
                await self.refresh(interaction, f"⚡ Upgraded max energy to {self.game.max_energy}!")
            else:
                await self.refresh(interaction, f"❌ Need {cost} psycoins!")
    
    async def left_callback(self, interaction: discord.Interaction):
        """Mine and move left"""
        target_x = self.game.x - 1
        target_y = self.game.y
        
        # Try to mine if blocked
        if not self.game.can_move(target_x, target_y):
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:  # Successful mine
                self.game.x = target_x
                self.game.y = target_y
                _, msg, _ = result
            else:
                _, msg = result
        else:
            _, msg = self.game.move_player(-1, 0)
        
        await self.refresh(interaction, msg)
    
    async def right_callback(self, interaction: discord.Interaction):
        """Mine and move right"""
        target_x = self.game.x + 1
        target_y = self.game.y
        
        # Try to mine if blocked
        if not self.game.can_move(target_x, target_y):
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:  # Successful mine
                self.game.x = target_x
                self.game.y = target_y
                _, msg, _ = result
            else:
                _, msg = result
        else:
            _, msg = self.game.move_player(1, 0)
        
        await self.refresh(interaction, msg)
    
    async def mine_callback(self, interaction: discord.Interaction):
        """Mine block below and fall to ground"""
        target_x = self.game.x
        target_y = self.game.y + 1
        
        # Check if can move down (already empty)
        if self.game.can_move(target_x, target_y):
            # Fall down until hitting ground
            while self.game.can_move(self.game.x, self.game.y + 1):
                self.game.y += 1
                self.game.energy = max(0, self.game.energy - 1)
                if self.game.energy <= 0:
                    break
            msg = f"⬇️ Fell to ground at y={self.game.y}"
        else:
            # Try to mine if blocked
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:  # Successful mine
                success, msg, (new_x, new_y) = result
                self.game.x = new_x
                self.game.y = new_y
                
                # Apply gravity - fall to ground
                while self.game.can_move(self.game.x, self.game.y + 1):
                    self.game.y += 1
                    if self.game.y > new_y:
                        msg += f" → Fell to y={self.game.y}"
                        break
            else:
                _, msg = result
        
        await self.refresh(interaction, msg)
    
    async def up_callback(self, interaction: discord.Interaction):
        """Return to surface"""
        self.game.x = 1
        self.game.y = -1
        await self.refresh(interaction, "⬆️ Returned to surface!")
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass
    
    async def refresh(self, interaction: discord.Interaction, message: str = None):
        """Refresh the game view"""
        self.game.regenerate_energy()
        
        # Check for map regeneration
        if self.game.check_map_regeneration():
            if message:
                message += "\n\n🔄 **Map regenerated after 12 hours!**"
            else:
                message = "🔄 **Map regenerated after 12 hours!**"
        
        # Render new map image and store as file
        map_image = self.game.render_map()
        
        # Create new view instance
        new_view = MiningView(self.game, self.user_id, self.bot)
        new_view.message = self.message
        new_view.map_file = discord.File(map_image, filename="mining_map.png")
        
        # Update container with new data
        display_text = f"# ⛏ MINING ADVENTURE\n\n{self.game.get_stats_text()}"
        if message:
            display_text += f"\n\n{message}"
        
        # Create buttons with callbacks for new view
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        mine_btn = discord.ui.Button(style=discord.ButtonStyle.success, emoji="⛏️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        up_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⬆️", label="Surface")
        
        left_btn.callback = new_view.left_callback
        mine_btn.callback = new_view.mine_callback
        right_btn.callback = new_view.right_callback
        up_btn.callback = new_view.up_callback
        
        # Check if at shop to add dropdown
        container_items = [
            discord.ui.TextDisplay(content=display_text),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://mining_map.png",
                    description=f"Seed: {self.game.seed}"
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Add shop dropdown if at shop
        if self.game.y == -1 and self.game.x in [4, 5]:
            shop_select = discord.ui.Select(
                placeholder="🏪 Shop Options",
                options=[
                    discord.SelectOption(label="💰 Sell Inventory", value="sell", description="Sell all items in inventory"),
                    discord.SelectOption(label="⛏️ Upgrade Pickaxe", value="pickaxe", description=f"Cost: {self.game.pickaxe_level * 500} coins"),
                    discord.SelectOption(label="🎒 Upgrade Backpack", value="backpack", description=f"Cost: {self.game.backpack_capacity * 100} coins"),
                    discord.SelectOption(label="⚡ Upgrade Max Energy", value="energy", description=f"Cost: {self.game.max_energy * 50} coins"),
                ]
            )
            shop_select.callback = new_view.shop_callback
            container_items.append(discord.ui.ActionRow(shop_select))

        
        # Add inventory dropdown (always visible)
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=[
                discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
                discord.SelectOption(label="🔦 Torch (Coming Soon)", value="torch", description="Light up dark caves"),
                discord.SelectOption(label="🧭 Compass (Coming Soon)", value="compass", description="Find your way back"),
                discord.SelectOption(label="🪜 Ladder (Coming Soon)", value="ladder", description="Climb back up easily"),
                discord.SelectOption(label="💎 Gem Detector (Coming Soon)", value="detector", description="Find rare ores"),
            ]
        )
        inventory_select.callback = new_view.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(left_btn, mine_btn, right_btn),
            discord.ui.ActionRow(up_btn),
            discord.ui.ActionRow(inventory_select),
        ])
        
        new_view.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5D4E37),
        )
        
        new_view.add_item(new_view.container1)
        
        try:
            await interaction.response.edit_message(view=new_view, attachments=[new_view.map_file])
            self.stop()
            # Save game state after action
            cog = interaction.client.get_cog("Mining")
            if cog:
                cog.save_data()
        except:
            try:
                await interaction.followup.send("❌ Error updating game!", ephemeral=True)
            except:
                pass


class Mining(commands.Cog):
    """⛏️ Mining - Procedurally generated 2D mining adventure"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # {user_id: MiningGame}
        self.data_file = "data/mining_data.json"
        self.load_data()
    
    def load_data(self):
        """Load saved mining data"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Load saved games
                    for user_id_str, game_data in data.get("games", {}).items():
                        user_id = int(user_id_str)
                        game = MiningGame.from_dict(game_data)
                        # Don't regenerate map on load - preserve mined areas
                        # Map regeneration will be checked when player interacts with game
                        self.active_games[user_id] = game
                #print(f"[Mining] Loaded {len(self.active_games)} saved games")
            except Exception as e:
                print(f"[Mining] Error loading data: {e}")
                pass
    
    def save_data(self):
        """Save mining data"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # Serialize all active games
        games_data = {}
        for user_id, game in self.active_games.items():
            games_data[str(user_id)] = game.to_dict()
        
        data = {
            "games": games_data
        }
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        #print(f"[Mining] Saved {len(games_data)} games")
    
    @commands.command(name="mine")
    async def mine_prefix(self, ctx):
        """Start a mining adventure! (Prefix version)"""
        await self.start_mining(ctx, ctx.author.id)
    
    @app_commands.command(name="mine", description="⛏️ Start a procedurally generated mining adventure!")
    async def mine_slash(self, interaction: discord.Interaction):
        """Start a mining adventure! (Slash version)"""
        await interaction.response.defer()
        await self.start_mining(interaction, interaction.user.id)
    
    async def start_mining(self, ctx, user_id: int):
        """Start or resume mining game"""
        # Get economy cog for coin sync
        economy_cog = self.bot.get_cog("Economy")
        
        # Check if user already has active game
        if user_id in self.active_games:
            game = self.active_games[user_id]
            # Sync coins with main economy on resume
            if economy_cog:
                economy_balance = economy_cog.get_balance(user_id)
                game.coins = economy_balance
        else:
            # Create new game
            game = MiningGame(user_id)
            
            # Sync coins with main economy
            if economy_cog:
                economy_balance = economy_cog.get_balance(user_id)
                game.coins = economy_balance
            
            self.active_games[user_id] = game
        
        await self.send_game_view(ctx, game, user_id, "🎮 Mining adventure!")
    
    async def send_game_view(self, ctx, game: MiningGame, user_id: int, message: str):
        """Send game view"""
        # Check for map regeneration
        if game.check_map_regeneration():
            message += "\n\n🔄 **Map regenerated after 12 hours!**"
        
        view = MiningView(game, user_id, self.bot)
        
        if hasattr(ctx, 'response'):  # Slash command
            view.message = await ctx.followup.send(view=view, files=[view.map_file])
        else:  # Prefix command
            view.message = await ctx.send(view=view, files=[view.map_file])
        
        # Save game state
        self.save_data()


    async def show_shop(self, interaction: discord.Interaction, game: MiningGame):
        """Show shop interface"""
        if game.y != -1 or game.x not in [4, 5]:
            await interaction.response.send_message("❌ You need to be at the shop to trade!", ephemeral=True)
            return
        
        # Sell inventory first
        if game.inventory:
            value, items = game.sell_inventory()
            
            embed = discord.Embed(
                title="🏪 MINING SHOP - Items Sold!",
                description=f"**Total Earned:** {value} coins 💰\n\n{items}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🏪 MINING SHOP",
                description=f"**Your Coins:** {game.coins} 💰",
                color=discord.Color.blue()
            )
        
        # Shop options
        embed.add_field(
            name="⛏️ Pickaxe Upgrades",
            value=f"**Current Level:** {game.pickaxe_level}\n"
                  f"**Upgrade Cost:** {game.pickaxe_level * 500} coins\n"
                  f"Effect: Faster mining, better drops",
            inline=False
        )
        
        embed.add_field(
            name="🎒 Backpack Upgrades",
            value=f"**Current Capacity:** {game.backpack_capacity}\n"
                  f"**Upgrade Cost:** {game.backpack_capacity * 100} coins\n"
                  f"Effect: +10 inventory slots",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Max Energy Upgrades",
            value=f"**Current Max:** {game.max_energy}\n"
                  f"**Upgrade Cost:** {game.max_energy * 50} coins\n"
                  f"Effect: +20 max energy",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Mining(bot))
