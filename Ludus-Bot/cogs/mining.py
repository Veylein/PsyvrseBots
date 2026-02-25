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
try:
    from utils.stat_hooks import us_inc as _m_inc
except Exception:
    _m_inc = None

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
        "dirt": 1, "stone": 2, "stone": 2, "coal": 5, "iron": 15, "gold": 50,
        "redstone": 30, "diamond": 200, "emerald": 300, "deepslate": 10,
        "netherite": 1000, "ancient_debris": 500, "bedrock": 0, "grass": 1,
        "mineshaft_wood": 2, "mineshaft_support": 3, "mineshaft_rail": 5, "mineshaft_entrance": 0,
        "chest": 0
    }
    
    # Ore modifiers
    ORE_STATES = {
        "cracked": {"multiplier": 0.5, "emoji": "🪨", "color_mod": (50, 50, 50)},  # 50% yield
        "irradiated": {"energy_cost": "half", "emoji": "☢️", "color_mod": (-30, 100, -30)}  # Takes half of current energy, greenish tint
    }
    
    # Creature types
    CREATURE_TYPES = {
        "zombie": {"emoji": "🧟", "health": 3, "damage": 2, "drops": {"coal": (2, 5), "iron": (1, 2)}, "tunnel": False, "speed": 1, "color": (60, 90, 60)},
        "skeleton": {"emoji": "💀", "health": 2, "damage": 1, "drops": {"stone": (3, 6)}, "tunnel": False, "speed": 2, "color": (200, 200, 200)},
        "spider": {"emoji": "🕷️", "health": 2, "damage": 2, "drops": {"redstone": (1, 3)}, "tunnel": False, "speed": 3, "color": (100, 40, 40)},
        "creeper": {"emoji": "💥", "health": 2, "damage": 5, "drops": {}, "penalty": "explosion", "tunnel": True, "speed": 1, "color": (50, 200, 50)},  # Explodes and damages area
        "enderman": {"emoji": "👾", "health": 4, "damage": 3, "drops": {"emerald": (1, 1)}, "tunnel": False, "speed": 4, "color": (100, 0, 100)},
        "mole": {"emoji": "🦫", "health": 1, "damage": 0, "drops": {"dirt": (5, 10)}, "tunnel": True, "speed": 1, "color": (90, 60, 40)},  # Creates tunnels, harmless
        "worm": {"emoji": "🪱", "health": 5, "damage": 4, "drops": {"gold": (2, 5), "diamond": (1, 2)}, "tunnel": True, "speed": 1, "color": (150, 100, 150)},  # Large tunnel digger
    }
    
    # Mining achievements
    MINING_ACHIEVEMENTS = {
        "first_mine": {"name": "First Steps", "desc": "Mine your first block", "emoji": "⛏️", "reward": 50},
        "depth_10": {"name": "Going Deeper", "desc": "Reach depth 10", "emoji": "🕳️", "reward": 100},
        "depth_50": {"name": "Deep Diver", "desc": "Reach depth 50", "emoji": "🌊", "reward": 500},
        "depth_100": {"name": "Abyss Walker", "desc": "Reach the Abyss (depth 100)", "emoji": "🌑", "reward": 1000},
        "diamond_find": {"name": "Diamonds!", "desc": "Find your first diamond", "emoji": "💎", "reward": 200},
        "emerald_find": {"name": "Emerald Hunter", "desc": "Find your first emerald", "emoji": "💚", "reward": 300},
        "netherite_find": {"name": "Netherite", "desc": "Find netherite", "emoji": "⬛", "reward": 1000},
        "rich_miner": {"name": "Rich Miner", "desc": "Earn 10,000 coins from mining", "emoji": "💰", "reward": 500},
        "explosion_expert": {"name": "Demolitionist", "desc": "Use 10 dynamites", "emoji": "💣", "reward": 300},
        "creature_hunter": {"name": "Monster Hunter", "desc": "Defeat 10 creatures", "emoji": "🗡️", "reward": 400},
        "tunnel_rat": {"name": "Tunnel Rat", "desc": "Mine 1000 blocks", "emoji": "🐀", "reward": 600},
        "chest_finder": {"name": "Treasure Hunter", "desc": "Find 5 chests", "emoji": "📦", "reward": 250},
    }
    
    BLOCK_COLORS = {
        "dirt": (139, 90, 43), "stone2": (111, 111, 117), "stone": (111, 111, 117), "coal": (40, 40, 45),
        "iron": (205, 127, 50), "gold": (255, 215, 0), "redstone": (220, 20, 60),
        "diamond": (0, 200, 255), "emerald": (0, 230, 118), "deepslate": (80, 80, 85),
        "netherite": (70, 40, 50), "ancient_debris": (120, 85, 60), "bedrock": (25, 25, 28),
        "air": (135, 206, 235), "shop": (139, 69, 19), "player": (255, 255, 0),
        "ladder": (139, 90, 0), "portal": (128, 0, 128), "torch": (255, 200, 0),
        "mineshaft_wood": (101, 67, 33), "mineshaft_support": (139, 69, 19),
        "mineshaft_rail": (160, 160, 160), "mineshaft_entrance": (90, 60, 30),
        "chest": (139, 69, 19), "grass": (34, 139, 34), "lapis": (70, 100, 200)
    }
    
    # Minimum pickaxe level required to mine each block
    BLOCK_REQUIREMENTS = {
        "dirt": 1, "grass": 1, "coal": 1,
        "stone": 2, "stone2": 2, "iron": 2, "redstone": 2,
        "gold": 3, "deepslate": 3,
        "diamond": 4, "emerald": 4,
        "netherite": 5, "ancient_debris": 5,
        "lapis": 2, "bedrock": 999,  # Cannot be mined
        "mineshaft_wood": 1, "mineshaft_support": 1, "mineshaft_rail": 1,
        "chest": 1
    }
    
    def __init__(self, user_id: int, seed: int = None, guild_id: int = None, is_shared: bool = False):
        self.user_id = user_id
        self.guild_id = guild_id
        self.is_shared = is_shared
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
        
        # Items inventory (tools/utilities)
        self.items = {}
        
        # Ore states: {(x, y): "cracked" or "irradiated"}
        self.ore_states = {}
        
        # Creatures: {id: {type, x, y, path, path_index, health}}
        self.creatures = {}
        self.creature_counter = 0
        
        # Mining achievements
        self.achievements = {}
        self.stats = {
            "blocks_mined": 0,
            "coins_earned": 0,
            "dynamites_used": 0,
            "creatures_killed": 0,
            "chests_found": 0,
            "max_depth": 0
        }
        
        # Developer mode flags
        self.infinite_energy = False
        self.infinite_backpack = False
        
        # Auto reset setting (for singleplayer)
        self.auto_reset_enabled = True
        
        # Map generation
        self.width = 11  # View width
        self.height = 10  # View height
        self.map_data = {}  # {(x, y): block_type}
        self.last_map_regen = datetime.utcnow()
        
        # Placed structures
        self.ladders = {}  # {(x, y): True} - placed ladders
        self.portals = {}  # {portal_id: {name, x, y, owner_id, public, linked_to}}
        self.torches = {}  # {(x, y): True} - placed torches
        self.portal_counter = 0  # For generating unique portal IDs
        
        # Generated structures
        self.structures = {}  # {structure_id: {type, name, x, y, width, height, discovered}}
        self.structure_counter = 0  # For generating unique structure IDs
        
        # Multiplayer support (guild-wide tracking)
        self.other_players = {}  # {user_id: {x, y, last_update, username}}
        
        self.generate_world()
        
    def generate_world(self, regenerate=False):
        """Generate procedural world"""
        # If regenerating, clear EVERYTHING for fresh start
        if regenerate:
            self.structures = {}
            self.structure_counter = 0
            self.torches = {}
            self.ladders = {}
            self.portals = {}
            self.portal_counter = 0
            self.map_data = {}  # Clear all blocks including mined areas
            self.other_players = {}  # Reset player positions
            # Reset player to spawn point
            self.x = 1
            self.y = -1
            # DON'T reset inventory - player keeps collected ores
        
        # Generate shop at y=-1 (above grass surface)
        for x in range(-50, 50):
            if x == 4:  # Shop left
                self.map_data[(x, -1)] = "shop_left"
            elif x == 5:  # Shop right
                self.map_data[(x, -1)] = "shop_right"
            else:
                self.map_data[(x, -1)] = "air"
        
        # Generate surface (y=0) with grass
        for x in range(-50, 50):
            self.map_data[(x, 0)] = "grass"
        
        # Generate underground layers starting from y=1
        for y in range(1, 150):
            biome = self.get_biome(y)
            for x in range(-50, 50):
                
                # Stable procedural generation - deterministic seed per position
                seed_value = (x * 73856093) ^ (y * 19349663) ^ self.seed
                pos_rng = random.Random(seed_value)
                noise = pos_rng.random()
                blocks = biome["blocks"]
                
                # From depth 10+, use the second-layer palette (stone2/coal2/iron) with rare biome ores
                if y >= 10:
                    # Probabilities: 60% stone2, 25% coal2, 10% iron, 5% rare biome ore
                    if noise < 0.60:
                        block = "stone2"
                    elif noise < 0.85:
                        block = "coal2"
                    elif noise < 0.95:
                        block = "iron"
                    else:
                        # Select ore from biome blocks (excluding stone/deepslate)
                        ores = [b for b in blocks if b not in ["stone", "deepslate"]]
                        if ores:
                            block = pos_rng.choice(ores)
                        else:
                            block = "stone2"
                    self.map_data[(x, y)] = block
                    continue
                
                # Weight distribution (common blocks more frequent) for shallow depths (<10)
                if noise < 0.6:
                    block = blocks[0]  # Most common
                elif noise < 0.85:
                    block = blocks[1] if len(blocks) > 1 else blocks[0]
                elif noise < 0.95:
                    block = blocks[2] if len(blocks) > 2 else blocks[1]
                else:
                    block = blocks[-1]  # Rarest
                
                self.map_data[(x, y)] = block
        
        # Ensure 'coal' does not appear below depth 10 (use 'coal2' there)
        for (mx, my), mblock in list(self.map_data.items()):
            if mblock == "coal" and my >= 10:
                self.map_data[(mx, my)] = "coal2"
        # Add ore states (cracked/irradiated) - 10% of ores get a state
        valuable_ores = ["coal", "coal2", "iron", "gold", "redstone", "diamond", "emerald", "netherite", "ancient_debris"]
        for (ox, oy), block_type in list(self.map_data.items()):
            if block_type in valuable_ores:
                if self.rng.random() < 0.10:  # 10% chance
                    state = self.rng.choice(["cracked", "irradiated"])
                    self.ore_states[(ox, oy)] = state
        
        # Generate structures on both first generation and regeneration
        self.generate_structures()
        
        # Spawn creatures
        self.spawn_creatures()
    
    def generate_structures(self):
        """Generate world structures like mineshafts"""
        # Generate 2-5 mineshafts at random positions
        num_mineshafts = self.rng.randint(2, 5)
        for i in range(num_mineshafts):
            # Random starting X position, avoiding shop area
            start_x = self.rng.choice([x for x in range(-45, 35) if x not in range(3, 7)])
            # Random depth (Y position) for the tunnel
            tunnel_y = self.rng.randint(15, 50)
            # Random height (4-5 blocks tall)
            tunnel_height = self.rng.randint(4, 5)
            # Tunnel length (20-35 blocks)
            tunnel_length = self.rng.randint(20, 35)
            
            # Create mineshaft structure
            structure_id = f"mineshaft_{self.structure_counter}"
            self.structure_counter += 1
            
            self.structures[structure_id] = {
                "type": "mineshaft",
                "name": f"Mineshaft #{i+1}",
                "x": start_x,
                "y": tunnel_y - tunnel_height + 1,  # Top of tunnel
                "width": tunnel_length,
                "height": tunnel_height,
                "discovered": False
            }
            
            # Build the horizontal mineshaft tunnel
            for x_offset in range(tunnel_length):
                current_x = start_x + x_offset
                
                # Build tunnel from TOP to BOTTOM (correct orientation)
                for height_offset in range(tunnel_height):
                    current_y = tunnel_y - height_offset  # Start from tunnel_y and go UP
                    
                    # Floor (bottom layer) - rails (at tunnel_y, the deepest/lowest point)
                    if height_offset == 0:
                        self.map_data[(current_x, current_y)] = "mineshaft_rail"
                    # Ceiling (top layer) - wood (at tunnel_y - tunnel_height + 1, the highest point)
                    elif height_offset == tunnel_height - 1:
                        self.map_data[(current_x, current_y)] = "mineshaft_wood"
                    # Middle layers - air for passage
                    else:
                        self.map_data[(current_x, current_y)] = "air"
                
                # Full support beams every 6 blocks
                if x_offset % 6 == 0 and x_offset > 0:
                    for height_offset in range(tunnel_height):
                        current_y = tunnel_y - height_offset
                        # Full pillar from floor to ceiling
                        if height_offset == 0 or height_offset == tunnel_height - 1:
                            self.map_data[(current_x, current_y)] = "mineshaft_support"
                        else:
                            self.map_data[(current_x, current_y)] = "mineshaft_support"
                
                # Torches every 5 blocks on ceiling
                if x_offset % 5 == 2:
                    torch_y = tunnel_y - 1  # One block below ceiling
                    self.torches[(current_x, torch_y)] = True
                
                # Chests (loot) - random placement (10% chance)
                if x_offset > 3 and self.rng.random() < 0.10:
                    chest_y = tunnel_y - 1  # One block above floor
                    self.map_data[(current_x, chest_y)] = "chest"
                
                # Entrance marker at the start
                if x_offset == 0:
                    entrance_y = tunnel_y - tunnel_height + 2
                    self.map_data[(current_x, entrance_y)] = "mineshaft_entrance"
    
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
        # Allow movement above y=-1 if there's a ladder
        if new_y < -1:
            # Check if there's a ladder at the target position or current position
            if (new_x, new_y) not in self.ladders and (self.x, self.y) not in self.ladders:
                return False
        
        block = self.get_block(new_x, new_y)
        return block in ["air", "shop_left", "shop_right"]  # Removed grass - it must be mined first
    
    def mine_block(self, x: int, y: int) -> tuple[bool, str]:
        """Mine block at position"""
        # Check distance - can only mine adjacent blocks
        if abs(x - self.x) + abs(y - self.y) != 1:
            return False, "**❌ Too far! Can only mine adjacent blocks.**"
        
        # Check if there's a creature at this position
        for creature_id, creature in list(self.creatures.items()):
            if creature["x"] == x and creature["y"] == y:
                killed, msg, drops = self.attack_creature(creature_id)
                return True, msg, (x, y)
        
        block = self.get_block(x, y)
        if block == "air":
            return False, "**❌ Nothing to mine here!**"
        
        if block == "bedrock":
            return False, "**❌ Bedrock is unbreakable!**"
        
        # Check pickaxe level requirement
        required_level = self.BLOCK_REQUIREMENTS.get(block, 1)
        if self.pickaxe_level < required_level:
            return False, f"⛏️ You need a level {required_level} pickaxe to mine {block}! (Current: Lv.{self.pickaxe_level})"
        
        # Energy cost based on biome hardness and pickaxe level
        biome = self.get_biome(y)
        speed_bonus = 1 + (self.pickaxe_level * 0.15)
        energy_cost = max(1, int(biome["hardness"] / speed_bonus))
        
        # Check for irradiated ore (takes half of current energy)
        ore_state = self.ore_states.get((x, y))
        ore_state_msg = ""
        if ore_state == "irradiated":
            # Take half of current energy (minimum 1)
            irradiated_cost = max(1, self.energy // 2)
            energy_cost = irradiated_cost
            ore_state_msg = f" ☢️ **Irradiated ore!** ({irradiated_cost} energy - half your current)"
        
        # Check energy (skip if infinite)
        if not self.infinite_energy and self.energy < energy_cost:
            return False, f"**❌ Not enough energy! Need {energy_cost}**"
        
        # Special handling for chest blocks (loot system)
        if block == "chest":
            # Check inventory space
            if not self.infinite_backpack:
                current_inventory_size = sum(self.inventory.values())
                if current_inventory_size >= self.backpack_capacity:
                    return False, "**❌ Inventory full!**"
            
            # Consume energy if not infinite
            if not self.infinite_energy:
                self.energy -= energy_cost
            
            # Remove chest
            self.map_data[(x, y)] = "air"
            
            # Update stats
            self.stats["chests_found"] += 1
            self.check_achievement("chest_finder")
            
            # Loot table (40% nothing, 60% loot)
            import random
            loot_roll = random.random()
            
            if loot_roll < 0.40:
                # 40% - Nothing
                return True, "📦 **Chest opened... but it's empty!**", (x, y)
            
            # 15% chance: creature jumps out of the chest!
            if loot_roll < 0.55:
                creature_types_list = list(self.CREATURE_TYPES.keys())
                creature_type = random.choice(creature_types_list)
                creature_data_c = self.CREATURE_TYPES[creature_type]
                creature_id = f"creature_{self.creature_counter}"
                self.creature_counter += 1
                spawn_x, spawn_y = x, y
                # Generate short patrol path around spawn
                path_length = self.rng.randint(8, 20)
                path = [(spawn_x, spawn_y)]
                cur_x, cur_y = spawn_x, spawn_y
                for _ in range(path_length - 1):
                    ddx, ddy = self.rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                    cur_x = max(-45, min(45, cur_x + ddx))
                    cur_y = max(0, min(100, cur_y + ddy))
                    path.append((cur_x, cur_y))
                self.creatures[creature_id] = {
                    "type": creature_type,
                    "x": spawn_x,
                    "y": spawn_y,
                    "path": path,
                    "path_index": 0,
                    "health": creature_data_c["health"],
                    "idle_refreshes": 0,
                }
                emoji_c = creature_data_c.get("emoji", "🧟")
                return True, f"📦 **Chest opened... {emoji_c} {creature_type.title()} jumped out!** Watch out!", (x, y)
            else:
                # 60% - Get loot (blocks OR items)
                # First decide: blocks (70%) or items (30%)
                loot_type_roll = random.random()
                
                if loot_type_roll < 0.70:
                    # 70% - Block loot (ores)
                    loot_options = [
                        ("coal", 3, 0.25),      # 25% - 3x coal
                        ("iron", 2, 0.20),      # 20% - 2x iron
                        ("gold", 1, 0.15),      # 15% - 1x gold
                        ("redstone", 2, 0.15),  # 15% - 2x redstone
                        ("diamond", 1, 0.10),   # 10% - 1x diamond
                        ("emerald", 1, 0.08),   # 8% - 1x emerald
                        ("ancient_debris", 1, 0.05),  # 5% - 1x ancient debris
                        ("netherite", 1, 0.02)  # 2% - 1x netherite
                    ]
                    
                    # Weighted random selection
                    total_weight = sum(w for _, _, w in loot_options)
                    rand_val = random.random() * total_weight
                    
                    cumulative = 0
                    selected_loot = None
                    selected_count = 0
                    
                    for loot_type, count, weight in loot_options:
                        cumulative += weight
                        if rand_val <= cumulative:
                            selected_loot = loot_type
                            selected_count = count
                            break
                    
                    # Add loot to inventory
                    self.inventory[selected_loot] = self.inventory.get(selected_loot, 0) + selected_count
                    value = self.BLOCK_VALUES.get(selected_loot, 0) * selected_count
                    
                    return True, f"📦 **Chest opened! Found {selected_count}x {selected_loot}!** (+${value})", (x, y)
                
                else:
                    # 30% - Item loot (ladder, torch, portal, dynamite)
                    item_options = [
                        ("ladder", 3, 0.40),   # 40% - 3x ladder
                        ("torch", 5, 0.35),    # 35% - 5x torch
                        ("portal", 1, 0.10),   # 10% - 1x portal
                        ("dynamite", 2, 0.15)  # 15% - 2x dynamite
                    ]
                    
                    # Weighted random selection
                    total_weight = sum(w for _, _, w in item_options)
                    rand_val = random.random() * total_weight
                    
                    cumulative = 0
                    selected_item = None
                    selected_count = 0
                    
                    for item_type, count, weight in item_options:
                        cumulative += weight
                        if rand_val <= cumulative:
                            selected_item = item_type
                            selected_count = count
                            break
                    
                    # Add item to items
                    self.items[selected_item] = self.items.get(selected_item, 0) + selected_count
                    emoji = {"ladder": "🪜", "torch": "🔦", "portal": "🌀", "dynamite": "💣"}.get(selected_item, "📦")
                    
                    return True, f"📦 **Chest opened! Found {selected_count}x {emoji} {selected_item}!**", (x, y)
        
        # Check inventory space (skip if infinite backpack)
        if not self.infinite_backpack:
            total_items = sum(self.inventory.values())
            if total_items >= self.backpack_capacity:
                return False, "**❌ Backpack full! Return to surface to sell.**"
        
        # Mine successful (consume energy if not infinite)
        if not self.infinite_energy:
            self.energy -= energy_cost
        old_block = self.map_data.get((x, y), "unknown")
        self.map_data[(x, y)] = "air"
        
        # Handle cracked ore (50% yield)
        count_mined = 1
        if ore_state == "cracked":
            if self.rng.random() < 0.5:
                count_mined = 0
                ore_state_msg = " 🪨 **Cracked ore!** It crumbled to dust..."
        
        if count_mined > 0:
            self.inventory[block] = self.inventory.get(block, 0) + count_mined
        
        # Clear ore state
        if (x, y) in self.ore_states:
            del self.ore_states[(x, y)]
        
        # Update stats
        self.stats["blocks_mined"] += 1
        if _m_inc is not None:
            try:
                _m_inc(int(self.user_id), 'mining_total_mined')
            except Exception:
                pass
        if y > self.stats["max_depth"]:
            self.stats["max_depth"] = y
        
        # Update max depth
        if y > self.depth:
            self.depth = y
        
        # Check for achievements
        self.check_achievement("first_mine")
        if y >= 10:
            self.check_achievement("depth_10")
        if y >= 50:
            self.check_achievement("depth_50")
        if y >= 100:
            self.check_achievement("depth_100")
        if block == "diamond":
            self.check_achievement("diamond_find")
        if block == "emerald":
            self.check_achievement("emerald_find")
        if block == "netherite":
            self.check_achievement("netherite_find")
        if self.stats["blocks_mined"] >= 1000:
            self.check_achievement("tunnel_rat")
        
        value = self.BLOCK_VALUES.get(block, 0) * count_mined
        return True, f"⛏️ Mined {block}! (+{value} value){ore_state_msg}", (x, y)
    
    def move_player(self, dx: int, dy: int) -> tuple[bool, str]:
        """Move player by delta (no energy cost for movement)"""
        new_x = self.x + dx
        new_y = self.y + dy
        
        # Check bounds
        if new_x < -50 or new_x > 50:
            return False, "**❌ World boundary!**"
        
        # Check if position is blocked
        if not self.can_move(new_x, new_y):
            return False, "**❌ Blocked! Mine the block first.**"
        
        # No energy cost for movement
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
    
    def check_map_regeneration(self, bot=None, guild_id: int = None) -> bool:
        """Check if map should regenerate (12 hours) - respects server config for shared, self setting for singleplayer"""
        # For singleplayer, check personal auto_reset_enabled flag
        if not self.is_shared:
            if not self.auto_reset_enabled:
                return False  # User disabled auto reset in their singleplayer game
        else:
            # For shared world, check server config
            if bot:
                server_config_cog = bot.get_cog("ServerConfig")
                if server_config_cog:
                    check_guild_id = guild_id or self.guild_id
                    if check_guild_id:
                        config = server_config_cog.get_server_config(check_guild_id)
                        if not config.get("mining_map_reset", True):
                            return False  # Map reset disabled for this server
        
        now = datetime.utcnow()
        elapsed = (now - self.last_map_regen).total_seconds()
        hours_elapsed = elapsed / 3600
        
        if hours_elapsed >= 12:
            self.last_map_regen = now
            self.generate_world(regenerate=True)  # Pass regenerate flag
            return True
        return False
    
    def can_move_up(self) -> bool:
        """Check if player can move up (requires ladder)"""
        # Check if there's a ladder at current position or adjacent
        if (self.x, self.y) in self.ladders:
            return True
        if (self.x, self.y - 1) in self.ladders:
            return True
        return False
    
    def place_ladder(self) -> tuple[bool, str]:
        """Place a ladder at current position"""
        if self.items.get("ladder", 0) <= 0:
            return False, "❌ No ladders in inventory!"
        
        if (self.x, self.y) in self.ladders:
            return False, "❌ Ladder already placed here!"
        
        # Can place ladder anywhere (including surface)
        self.ladders[(self.x, self.y)] = True
        self.items["ladder"] -= 1
        return True, f"🪜 Ladder placed! ({self.items['ladder']} left)"
    
    def place_torch(self) -> tuple[bool, str]:
        """Place a torch at current position"""
        if self.items.get("torch", 0) <= 0:
            return False, "❌ No torches in inventory!"
        
        if (self.x, self.y) in self.torches:
            return False, "❌ Torch already placed here!"
        
        self.torches[(self.x, self.y)] = True
        self.items["torch"] -= 1
        return True, f"🔦 Torch placed! ({self.items['torch']} left)"
    
    def use_dynamite(self) -> tuple[bool, str]:
        """Use dynamite to explode blocks around player (3x3 area)"""
        if self.items.get("dynamite", 0) <= 0:
            return False, "❌ No dynamite in inventory!"
        
        # Explode 3x3 area around player
        blocks_destroyed = 0
        blocks_collected = {}
        
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                target_x = self.x + dx
                target_y = self.y + dy
                
                # Skip player's position and air
                if (dx == 0 and dy == 0) or target_y < 0:
                    continue
                
                block = self.get_block(target_x, target_y)
                if block in ["air", "bedrock", "shop_left", "shop_right"]:
                    continue
                
                # Don't destroy ladders, portals, torches
                if (target_x, target_y) in self.ladders or (target_x, target_y) in self.torches:
                    continue
                
                portal_here = any(p["x"] == target_x and p["y"] == target_y for p in self.portals.values())
                if portal_here:
                    continue
                
                # Collect block if backpack has space
                if not self.infinite_backpack:
                    total_items = sum(self.inventory.values())
                    if total_items >= self.backpack_capacity:
                        continue
                
                # Destroy block and add to inventory
                self.map_data[(target_x, target_y)] = "air"
                blocks_collected[block] = blocks_collected.get(block, 0) + 1
                self.inventory[block] = self.inventory.get(block, 0) + 1
                blocks_destroyed += 1
        
        self.items["dynamite"] -= 1
        self.stats["dynamites_used"] += 1
        self.check_achievement("explosion_expert")
        
        if blocks_destroyed == 0:
            return True, f"💥 Dynamite exploded but nothing was destroyed! ({self.items['dynamite']} left)"
        
        blocks_text = ", ".join([f"{count}x {block}" for block, count in blocks_collected.items()])
        return True, f"💥 Dynamite! Destroyed {blocks_destroyed} blocks: {blocks_text} ({self.items['dynamite']} left)"
    
    def discover_nearby_structures(self, radius: int = 10):
        """Discover structures within radius of player"""
        for structure_id, structure_data in self.structures.items():
            if not structure_data["discovered"]:
                # Check if player is within radius
                dx = abs(structure_data["x"] - self.x)
                dy = abs(structure_data["y"] - self.y)
                if dx <= radius and dy <= radius:
                    structure_data["discovered"] = True
    
    def sell_inventory(self, bot=None) -> tuple[int, str]:
        """Sell all inventory items"""
        if not self.inventory:
            return 0, "**❌ Inventory is empty!**"
        
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
                economy_cog.add_mine_coins(self.user_id, total_value)
        
        self.coins += total_value
        self.stats["coins_earned"] += total_value
        if _m_inc is not None and total_value > 0:
            try:
                _m_inc(int(self.user_id), 'mining_coins_earned', int(total_value))
            except Exception:
                pass
        self.inventory.clear()
        
        # Check achievement
        self.check_achievement("rich_miner", bot)
        
        return total_value, "\n".join(items_sold)
    
    def spawn_creatures(self):
        """Spawn creatures with random patrol paths"""
        # Clear existing creatures on regeneration
        self.creatures = {}
        self.creature_counter = 0
        
        # Spawn 3-8 creatures
        num_creatures = self.rng.randint(3, 8)
        for i in range(num_creatures):
            creature_type = self.rng.choice(list(self.CREATURE_TYPES.keys()))
            creature_data = self.CREATURE_TYPES[creature_type]
            
            # Random spawn position (underground, away from spawn)
            spawn_x = self.rng.randint(-40, 40)
            spawn_y = self.rng.randint(10, 80)  # Underground only
            
            # Generate random patrol path (5-30 waypoints) using cardinal moves (L/R/U/D)
            path_length = self.rng.randint(5, 30)
            path = [(spawn_x, spawn_y)]  # Start at spawn

            current_x, current_y = spawn_x, spawn_y
            for _ in range(path_length - 1):
                # Move one step in a cardinal direction or stay
                step = self.rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
                dx, dy = step
                current_x += dx
                current_y += dy
                # Keep within bounds
                current_x = max(-45, min(45, current_x))
                current_y = max(5, min(100, current_y))
                path.append((current_x, current_y))
            
            # NOTE: Tunnel carving happens step by step in move_creatures, not upfront
            
            creature_id = f"creature_{self.creature_counter}"
            self.creature_counter += 1
            
            self.creatures[creature_id] = {
                "type": creature_type,
                "x": spawn_x,
                "y": spawn_y,
                "path": path,
                "path_index": 0,
                "health": creature_data["health"],
                "idle_refreshes": 0
            }
    
    def move_creatures(self):
        """Move all creatures along their patrol paths"""
        for creature_id, creature in list(self.creatures.items()):
            path = creature.get("path") or []
            if not path:
                continue

            # --- idle (counts per refresh/player action) ---
            idle = creature.get("idle_refreshes", 0)
            if idle > 0:
                creature["idle_refreshes"] = idle - 1
                continue

            # Determine next waypoint index
            current_idx = creature.get("path_index", 0)
            next_idx = (current_idx + 1) % len(path)
            target_x, target_y = path[next_idx]

            cx, cy = creature["x"], creature["y"]

            # If already at target, advance to next waypoint
            if cx == target_x and cy == target_y:
                creature["path_index"] = next_idx
                # Random stop upon reaching the waypoint (30% chance, 2-6 refreshes)
                if self.rng.random() < 0.30:
                    creature["idle_refreshes"] = self.rng.randint(2, 6)
                continue

            # Move one tile toward the target (cardinal only)
            step_x = 0
            step_y = 0
            if target_x != cx:
                step_x = 1 if target_x > cx else -1
            elif target_y != cy:
                step_y = 1 if target_y > cy else -1

            new_x = cx + step_x
            new_y = cy + step_y

            # Keep within bounds
            new_x = max(-45, min(45, new_x))
            new_y = max(0, min(100, new_y))

            # Tunnel creatures carve blocks as they move (step by step, not upfront)
            creature_type = creature.get("type", "")
            creature_data = self.CREATURE_TYPES.get(creature_type, {})
            if creature_data.get("tunnel"):
                # Carve current position
                if (new_x, new_y) in self.map_data and self.map_data[(new_x, new_y)] not in ("air", "bedrock"):
                    self.map_data[(new_x, new_y)] = "air"
                if creature_type == "worm":
                    # Worm: carve 2-tall tunnel in direction of movement
                    if step_x != 0:
                        # Moving horizontally: carve block above
                        above = (new_x, new_y - 1)
                        if above in self.map_data and self.map_data[above] not in ("air", "bedrock"):
                            self.map_data[above] = "air"
                    else:
                        # Moving vertically: carve one block to the side
                        side = (new_x + 1, new_y)
                        if side in self.map_data and self.map_data[side] not in ("air", "bedrock"):
                            self.map_data[side] = "air"

            creature["x"], creature["y"] = new_x, new_y

            # Random stop during movement (10% chance on each refresh, 1-4 refreshes)
            if self.rng.random() < 0.10:
                creature["idle_refreshes"] = self.rng.randint(1, 4)

            # If we reached the waypoint, advance index
            if new_x == target_x and new_y == target_y:
                creature["path_index"] = next_idx

        # Developer auto-respawn: if enabled and all creatures are dead, respawn
        if getattr(self, "dev_mode", False) and not self.creatures:
            self.spawn_creatures()
    
    def attack_creature(self, creature_id: str, bot=None) -> tuple[bool, str, dict]:
        """Attack/mine a creature - returns (killed, message, drops)"""
        if creature_id not in self.creatures:
            return False, "Creature not found!", {}
        
        creature = self.creatures[creature_id]
        creature_data = self.CREATURE_TYPES[creature["type"]]
        
        # Deal damage (1 hit per mine)
        creature["health"] -= 1
        
        if creature["health"] <= 0:
            # Creature killed
            drops = {}
            
            # Handle special penalties
            if creature_data.get("penalty") == "explosion":
                # Creeper explodes! Damage 3x3 area
                cx, cy = creature["x"], creature["y"]
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        target_x = cx + dx
                        target_y = cy + dy
                        if (target_x, target_y) not in self.ladders and (target_x, target_y) not in self.torches:
                            self.map_data[(target_x, target_y)] = "air"
                
                del self.creatures[creature_id]
                self.stats["creatures_killed"] += 1
                self.check_achievement("creature_hunter", bot)
                return True, f"💥 {creature_data['emoji']} Creeper exploded! Destroyed 3x3 area!", {}
            
            # Normal drops
            for drop_type, (min_count, max_count) in creature_data.get("drops", {}).items():
                count = self.rng.randint(min_count, max_count)
                drops[drop_type] = count
                self.inventory[drop_type] = self.inventory.get(drop_type, 0) + count
            
            drops_text = ", ".join([f"{count}x {item}" for item, count in drops.items()]) if drops else "nothing"
            
            del self.creatures[creature_id]
            self.stats["creatures_killed"] += 1
            self.check_achievement("creature_hunter", bot)
            return True, f"⚔️ Killed {creature_data['emoji']} {creature['type']}! Dropped: {drops_text}", drops
        else:
            # Still alive
            return False, f"⚔️ Hit {creature_data['emoji']} {creature['type']}! ({creature['health']} HP left)", {}
    
    def check_achievement(self, achievement_key: str, bot=None):
        """Check and grant achievement if not already earned"""
        if achievement_key in self.achievements:
            return  # Already earned
        
        achievement = self.MINING_ACHIEVEMENTS.get(achievement_key)
        if not achievement:
            return
        
        # Check conditions
        earned = False
        if achievement_key == "first_mine":
            earned = self.stats["blocks_mined"] >= 1
        elif achievement_key == "depth_10":
            earned = self.stats["max_depth"] >= 10
        elif achievement_key == "depth_50":
            earned = self.stats["max_depth"] >= 50
        elif achievement_key == "depth_100":
            earned = self.stats["max_depth"] >= 100
        elif achievement_key == "diamond_find":
            earned = self.inventory.get("diamond", 0) > 0 or self.stats.get("diamonds_found", 0) > 0
        elif achievement_key == "emerald_find":
            earned = self.inventory.get("emerald", 0) > 0 or self.stats.get("emeralds_found", 0) > 0
        elif achievement_key == "netherite_find":
            earned = self.inventory.get("netherite", 0) > 0 or self.stats.get("netherite_found", 0) > 0
        elif achievement_key == "rich_miner":
            earned = self.stats["coins_earned"] >= 10000
        elif achievement_key == "explosion_expert":
            earned = self.stats["dynamites_used"] >= 10
        elif achievement_key == "creature_hunter":
            earned = self.stats["creatures_killed"] >= 10
        elif achievement_key == "tunnel_rat":
            earned = self.stats["blocks_mined"] >= 1000
        elif achievement_key == "chest_finder":
            earned = self.stats["chests_found"] >= 5
        
        if earned:
            self.achievements[achievement_key] = datetime.utcnow().isoformat()
            
            # Grant reward
            if bot:
                economy_cog = bot.get_cog("Economy")
                if economy_cog:
                    economy_cog.add_mine_coins(self.user_id, achievement["reward"])
            
            self.coins += achievement["reward"]
    
    def render_map(self, bot=None) -> io.BytesIO:
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
            
            # Map block types to asset files - use None for colored fallback
            asset_map = {
                #layer1
                "air": "assets/mining/blocks/layer1/air.png",
                "dirt": "assets/mining/blocks/layer1/dirt.png",
                "grass": "assets/mining/blocks/layer1/grass.png",
                "stone": "assets/mining/blocks/layer1/stone.png",
                "coal": "assets/mining/blocks/layer1/coal.png",
                #layer2
                "stone2": "assets/mining/blocks/layer2/stone.png",
                "coal2": "assets/mining/blocks/layer2/coal.png",
                
                "iron": None,  # Use color fallback for orange iron
                "gold": None,  # Use color fallback for golden
                "redstone": None,  # Use color fallback for red
                "diamond": None,  # Use color fallback for cyan
                "emerald": None,  # Use color fallback for green
                "deepslate": None,  # Use color fallback
                "netherite": None,  # Use color fallback
                "ancient_debris": None,  # Use color fallback
                "bedrock": None,  # Use color fallback
                # Shop
                "shop_left": "assets/mining/shop/shop1_left.png",
                "shop_right": "assets/mining/shop/shop1_right.png",
                # Structures
                "mineshaft_wood": "assets/mining/structures/mineshaft/wood.png",
                "mineshaft_support": "assets/mining/structures/mineshaft/support.png",
                "mineshaft_rail": "assets/mining/structures/mineshaft/rail.png",
                "mineshaft_entrance": "assets/mining/structures/mineshaft/entrance.png",
            }
            
            asset_path = asset_map.get(block_type)
            
            # If no asset path or file doesn't exist, use colored fallback
            if asset_path is None:
                fallback = Image.new('RGBA', (block_size, block_size), self.BLOCK_COLORS.get(block_type, (0, 0, 0)))
                texture_cache[block_type] = fallback
                return fallback
            
            try:
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
                
                # Draw ore state overlay if present
                if (world_x, world_y) in self.ore_states:
                    ore_state = self.ore_states[(world_x, world_y)]
                    state_data = self.ORE_STATES.get(ore_state)
                    if state_data:
                        # Apply color modification
                        try:
                            # Create a semi-transparent overlay
                            overlay = Image.new('RGBA', (block_size, block_size), (0, 0, 0, 0))
                            overlay_draw = ImageDraw.Draw(overlay)
                            
                            if ore_state == "cracked":
                                # Draw cracks across the block
                                overlay_draw.line([(0, block_size//3), (block_size, block_size//2)], fill=(0, 0, 0, 150), width=2)
                                overlay_draw.line([(0, 2*block_size//3), (block_size, block_size//2)], fill=(0, 0, 0, 150), width=2)
                            elif ore_state == "irradiated":
                                # Draw radioactive green tint
                                overlay_draw.rectangle([0, 0, block_size, block_size], fill=(0, 255, 0, 60))
                                # Draw radiation symbol
                                center_x, center_y = block_size // 2, block_size // 2
                            img.paste(overlay, (x1, y1), overlay)
                        except:
                            pass
                
                # Draw ladder overlay if placed here
                if (world_x, world_y) in self.ladders:
                    try:
                        ladder_img = Image.open("assets/mining/items/ladder.png").convert("RGBA")
                        ladder_img = ladder_img.resize((block_size, block_size), Image.LANCZOS)
                        img.paste(ladder_img, (x1, y1), ladder_img)
                    except:
                        # Fallback: brown vertical lines
                        draw_temp = ImageDraw.Draw(img)
                        ladder_color = self.BLOCK_COLORS.get("ladder", (139, 90, 0))
                        draw_temp.rectangle([x1 + 5, y1, x1 + 8, y1 + block_size], fill=ladder_color)
                        draw_temp.rectangle([x1 + block_size - 8, y1, x1 + block_size - 5, y1 + block_size], fill=ladder_color)
                
                # Draw torch overlay if placed here
                if (world_x, world_y) in self.torches:
                    try:
                        torch_img = Image.open("assets/mining/items/torch.png").convert("RGBA")
                        torch_img = torch_img.resize((block_size // 2, block_size), Image.LANCZOS)
                        img.paste(torch_img, (x1 + block_size // 4, y1), torch_img)
                    except:
                        # Fallback: yellow/orange glow
                        draw_temp = ImageDraw.Draw(img)
                        torch_color = self.BLOCK_COLORS.get("torch", (255, 200, 0))
                        draw_temp.ellipse([x1 + block_size//3, y1 + 5, x1 + 2*block_size//3, y1 + block_size//2], fill=torch_color)
                
                # Draw portal overlay if placed here
                for portal_id, portal_data in self.portals.items():
                    if portal_data["x"] == world_x and portal_data["y"] == world_y:
                        try:
                            portal_img = Image.open("assets/mining/items/portal.png").convert("RGBA")
                            portal_img = portal_img.resize((block_size, block_size), Image.LANCZOS)
                            img.paste(portal_img, (x1, y1), portal_img)
                            
                            # Draw portal name ABOVE portal
                            img_rgba = img.convert('RGBA')
                            draw_temp = ImageDraw.Draw(img_rgba)
                            try:
                                portal_font = ImageFont.truetype("Arial.ttf", 10)
                            except:
                                portal_font = ImageFont.load_default()
                            portal_name = portal_data["name"][:12]  # Limit name length
                            # Get text size for background
                            bbox = draw_temp.textbbox((0, 0), portal_name, font=portal_font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                            # Center text above portal
                            text_x = x1 + (block_size - text_width) // 2
                            text_y = y1 - text_height - 2
                            # Draw semi-transparent background
                            bg_padding = 2
                            draw_temp.rectangle(
                                [text_x - bg_padding, text_y - bg_padding,
                                 text_x + text_width + bg_padding, text_y + text_height + bg_padding],
                                fill=(138, 43, 226, 200)  # Purple background
                            )
                            # Draw text
                            draw_temp.text((text_x, text_y), portal_name, fill=(255, 255, 255, 255), font=portal_font)
                            img = img_rgba.convert('RGB')
                        except:
                            # Fallback: purple swirl
                            draw_temp = ImageDraw.Draw(img)
                            portal_color = (138, 43, 226)  # Purple
                            draw_temp.ellipse([x1 + 5, y1 + 5, x1 + block_size - 5, y1 + block_size - 5], fill=portal_color, outline=(255, 255, 255), width=2)
                            # Draw portal name above
                            try:
                                portal_font = ImageFont.truetype("Arial.ttf", 8)
                            except:
                                portal_font = ImageFont.load_default()
                            portal_name = portal_data["name"][:8]  # Limit name length
                            draw_temp.text((x1 + 2, y1 - 12), portal_name, fill=(255, 255, 255), font=portal_font)
                        break
        
        # Apply darkness based on depth (darker the deeper you go)
        if self.y > 5:  # Below surface level
            darkness_overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            darkness_draw = ImageDraw.Draw(darkness_overlay)
            
            # Calculate darkness intensity (0-240 alpha based on depth)
            depth_factor = min((self.y - 5) / 55, 1.0)  # 0 at y=5, 1.0 at y=60
            darkness_alpha = int(depth_factor * 240)
            
            # Draw darkness over entire map
            for dy in range(self.height):
                for dx in range(self.width):
                    world_x = start_x + dx
                    world_y = start_y + dy
                    x1 = dx * block_size
                    y1 = dy * block_size
                    
                    # Check if there's a torch nearby (within 5 blocks for brighter radius)
                    lit = False
                    light_distance = 999
                    for tx, ty in self.torches.keys():
                        distance = abs(tx - world_x) + abs(ty - world_y)
                        if distance <= 5:  # Increased to 5 blocks
                            lit = True
                            light_distance = min(light_distance, distance)
                    
                    # Apply darkness if not lit by torch
                    if not lit:
                        darkness_draw.rectangle([x1, y1, x1 + block_size, y1 + block_size], 
                                                fill=(0, 0, 0, darkness_alpha))
                    else:
                        # Gradual light based on torch distance (even brighter gradient)
                        light_alpha = int(darkness_alpha * (light_distance / 6.0))  # Increased from 4.5 to 6.0
                        darkness_draw.rectangle([x1, y1, x1 + block_size, y1 + block_size], 
                                                fill=(0, 0, 0, light_alpha))
            
            img_rgba = img.convert('RGBA')
            img_rgba = Image.alpha_composite(img_rgba, darkness_overlay)
            img = img_rgba.convert('RGB')
        
        # Draw other players in multiplayer mode (before drawing current player)
        if self.is_shared and self.other_players:
            img_rgba = img.convert('RGBA')
            
            # Player colors for multiplayer
            player_colors = [
                (255, 100, 100),  # Red
                (100, 255, 100),  # Green
                (100, 100, 255),  # Blue
                (255, 255, 100),  # Yellow
                (255, 100, 255),  # Magenta
                (100, 255, 255),  # Cyan
                (255, 165, 0),    # Orange
                (255, 192, 203),  # Pink
            ]
            
            for idx, (other_user_id, other_data) in enumerate(self.other_players.items()):
                other_x = other_data["x"]
                other_y = other_data["y"]
                
                # Check if other player is in current view
                view_dx = other_x - start_x
                view_dy = other_y - start_y
                
                if 0 <= view_dx < self.width and 0 <= view_dy < self.height:
                    # Draw other player as colored circle
                    color = player_colors[idx % len(player_colors)]
                    
                    # Create a semi-transparent player marker
                    marker_size = block_size
                    marker = Image.new('RGBA', (marker_size, marker_size), (0, 0, 0, 0))
                    marker_draw = ImageDraw.Draw(marker)
                    
                    center = marker_size // 2
                    radius = marker_size // 3
                    
                    # Draw colored circle with border
                    marker_draw.ellipse([center - radius, center - radius,
                                       center + radius, center + radius],
                                      fill=color + (200,),  # Add alpha
                                      outline=(255, 255, 255, 255),
                                      width=2)
                    
                    # Paste marker on map
                    paste_x = view_dx * block_size
                    paste_y = view_dy * block_size
                    img_rgba.paste(marker, (paste_x, paste_y), marker)
                    
                    # Draw username above player marker
                    username = other_data.get("username", "Player")
                    # Create small font for username
                    try:
                        name_font = ImageFont.truetype("assets/mining/fonts/Arial.ttf", 10)
                    except:
                        try:
                            name_font = ImageFont.truetype("Arial.ttf", 10)
                        except:
                            name_font = ImageFont.load_default()
                    
                    # Draw username with background
                    img_rgba_draw = ImageDraw.Draw(img_rgba)
                    text_bbox = img_rgba_draw.textbbox((0, 0), username, font=name_font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    # Center text above marker
                    text_x = paste_x + (block_size - text_width) // 2
                    text_y = paste_y - text_height - 2
                    
                    # Draw semi-transparent background for text
                    bg_padding = 2
                    img_rgba_draw.rectangle(
                        [text_x - bg_padding, text_y - bg_padding,
                         text_x + text_width + bg_padding, text_y + text_height + bg_padding],
                        fill=(0, 0, 0, 180)
                    )
                    
                    # Draw text
                    img_rgba_draw.text((text_x, text_y), username, fill=(255, 255, 255, 255), font=name_font)
            
            img = img_rgba.convert('RGB')
        
        # Draw creatures
        img_rgba = img.convert('RGBA')
        for creature_id, creature in self.creatures.items():
            creature_x = creature["x"]
            creature_y = creature["y"]
            
            # Check if creature is in current view
            view_dx = creature_x - start_x
            view_dy = creature_y - start_y
            
            if 0 <= view_dx < self.width and 0 <= view_dy < self.height:
                creature_type = creature["type"]
                creature_data = self.CREATURE_TYPES[creature_type]
                
                # Draw creature as colored circle with emoji-like appearance
                marker_size = block_size
                marker = Image.new('RGBA', (marker_size, marker_size), (0, 0, 0, 0))
                marker_draw = ImageDraw.Draw(marker)
                
                center = marker_size // 2
                radius = marker_size // 3
                
                # Draw creature colored circle
                creature_color = creature_data["color"]
                marker_draw.ellipse([center - radius, center - radius,
                                   center + radius, center + radius],
                                  fill=creature_color + (220,),
                                  outline=(0, 0, 0, 255),
                                  width=2)
                
                # Paste marker on map
                paste_x = view_dx * block_size
                paste_y = view_dy * block_size
                img_rgba.paste(marker, (paste_x, paste_y), marker)
                
                # Draw creature type emoji/name above
                creature_label = f"{creature_data['emoji']} {creature_type[:4]}"
                try:
                    creature_font = ImageFont.truetype("Arial.ttf", 8)
                except:
                    creature_font = ImageFont.load_default()
                
                img_rgba_draw = ImageDraw.Draw(img_rgba)
                text_bbox = img_rgba_draw.textbbox((0, 0), creature_label, font=creature_font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Draw health bar
                hp_width = block_size - 4
                hp_height = 3
                hp_x = paste_x + 2
                hp_y = paste_y - 8
                
                # Health bar background
                marker_draw_img = ImageDraw.Draw(img_rgba)
                marker_draw_img.rectangle([hp_x, hp_y, hp_x + hp_width, hp_y + hp_height], fill=(100, 0, 0, 200))
                
                # Health bar fill
                max_hp = self.CREATURE_TYPES[creature_type]["health"]
                current_hp = creature["health"]
                hp_fill_width = int((current_hp / max_hp) * hp_width)
                marker_draw_img.rectangle([hp_x, hp_y, hp_x + hp_fill_width, hp_y + hp_height], fill=(0, 255, 0, 255))
        
        img = img_rgba.convert('RGB')
        
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
            font = ImageFont.truetype("assets/mining/fonts/Arial.ttf", 14)
            font_small = ImageFont.truetype("assets/mining/fonts/Arial.ttf", 12)
        except:
            try:
                font = ImageFont.truetype("Arial.ttf", 14)
                font_small = ImageFont.truetype("Arial.ttf", 12)
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
        
        # Energy icon and text (show "inf/inf" if infinite energy)
        energy_icon = load_ui_icon("assets/mining/ui/energy.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(energy_icon, (5, 3), energy_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        energy_text = "inf/inf" if self.infinite_energy else f"{self.energy}/{self.max_energy}"
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
        
        # Inventory/backpack icon and text (show "blocks/inf" if infinite backpack)
        # Determine backpack level based on capacity
        backpack_level = (self.backpack_capacity - 20) // 10 + 1  # Level 1 = 20 cap, Level 2 = 30, etc.
        backpack_icon = load_ui_icon(f"assets/mining/ui/backpack/backpack{backpack_level}.png")
        img_rgba = img.convert('RGBA')
        img_rgba.paste(backpack_icon, (228, 3), backpack_icon)
        img = img_rgba.convert('RGB')
        draw = ImageDraw.Draw(img)
        
        if self.infinite_backpack:
            # Show inventory size when infinite (number of blocks, not value)
            inv_text = f"{inventory_size}/inf"
            inv_color = (100, 255, 100)
        else:
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
            try:
                warning_font = ImageFont.truetype("assets/mining/fonts/Arial.ttf", 36)
            except:
                try:
                    warning_font = ImageFont.truetype("Arial.ttf", 36)
                except:
                    warning_font = font
            
            warning_text = "NO ENERGY!"
            
            # Load energy icon for warning
            energy_warning_icon = load_ui_icon("assets/mining/ui/energy.png")
            energy_warning_size = 40
            energy_warning_icon = energy_warning_icon.resize((energy_warning_size, energy_warning_size), Image.LANCZOS)
            
            # Get text size
            bbox = draw.textbbox((0, 0), warning_text, font=warning_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Total width including icon and spacing
            total_width = energy_warning_size + 12 + text_width
            
            # Center position
            center_x = img_width // 2
            center_y = img_height // 2
            
            # Draw semi-transparent background
            padding = 25
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
            text_x = icon_x + energy_warning_size + 12
            text_y = center_y - text_height // 2 - 10 
            draw.text((text_x, text_y), warning_text, fill=(255, 255, 100), font=warning_font)
        
        # Draw biome info below top UI
        biome = self.get_biome(self.y)
        
        # Check if map reset is enabled
        reset_enabled = True
        if not self.is_shared:
            # For singleplayer, check personal auto_reset_enabled flag
            reset_enabled = self.auto_reset_enabled
        elif bot and self.guild_id:
            # For shared world, check server config
            server_config_cog = bot.get_cog("ServerConfig")
            if server_config_cog:
                config = server_config_cog.get_server_config(self.guild_id)
                reset_enabled = config.get("mining_map_reset", True)
        
        # Calculate time until map reset or show "reset is off"
        if not reset_enabled:
            reset_text = "reset is off"
        else:
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
        
        biome_text = f"{biome['name']} (Y: {self.y}) | {reset_text}"
        
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
        
        stats_text = (
            f"**Position:** {self.x}, {self.y}"
        )
        
        # Add achievements count
        if self.achievements:
            achievement_count = len(self.achievements)
            total_achievements = len(self.MINING_ACHIEVEMENTS)
            stats_text += f" | **Achievements:** {achievement_count}/{total_achievements} 🏆"
        
        return stats_text
    
    def to_dict(self) -> dict:
        """Serialize game state to dictionary"""
        # Convert map_data keys from tuples to strings for JSON
        map_data_serialized = {f"{x},{y}": block for (x, y), block in self.map_data.items()}
        
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "is_shared": self.is_shared,
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
            "map_data": map_data_serialized,
            "other_players": self.other_players,
            "infinite_energy": self.infinite_energy,
            "infinite_backpack": self.infinite_backpack,
            "auto_reset_enabled": self.auto_reset_enabled,
            "items": self.items,
            "ladders": {f"{x},{y}": True for (x, y) in self.ladders.keys()},
            "portals": self.portals,
            "torches": {f"{x},{y}": True for (x, y) in self.torches.keys()},
            "portal_counter": self.portal_counter,
            "structures": self.structures,
            "structure_counter": self.structure_counter,
            "ore_states": {f"{x},{y}": state for (x, y), state in self.ore_states.items()},
            "creatures": self.creatures,
            "creature_counter": self.creature_counter,
            "achievements": self.achievements,
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Deserialize game state from dictionary"""
        game = cls.__new__(cls)
        game.user_id = data["user_id"]
        game.guild_id = data.get("guild_id")
        game.is_shared = data.get("is_shared", False)
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
        game.other_players = data.get("other_players", {})
        game.infinite_energy = data.get("infinite_energy", False)
        game.infinite_backpack = data.get("infinite_backpack", False)
        game.auto_reset_enabled = data.get("auto_reset_enabled", True)
        
        # Deserialize items and structures
        game.items = data.get("items", {"ladder": 5, "portal": 2, "torch": 10, "dynamite": 3})
        game.portal_counter = data.get("portal_counter", 0)
        game.structures = data.get("structures", {})
        game.structure_counter = data.get("structure_counter", 0)
        
        # Deserialize ore states
        game.ore_states = {}
        for key, state in data.get("ore_states", {}).items():
            x, y = map(int, key.split(","))
            game.ore_states[(x, y)] = state
        
        # Deserialize creatures
        game.creatures = data.get("creatures", {})
        game.creature_counter = data.get("creature_counter", 0)
        
        # Deserialize achievements and stats
        game.achievements = data.get("achievements", {})
        game.stats = data.get("stats", {
            "blocks_mined": 0,
            "coins_earned": 0,
            "dynamites_used": 0,
            "creatures_killed": 0,
            "chests_found": 0,
            "max_depth": 0
        })
        
        # Deserialize ladders
        game.ladders = {}
        for key in data.get("ladders", {}).keys():
            x, y = map(int, key.split(","))
            game.ladders[(x, y)] = True
        
        # Deserialize portals
        game.portals = data.get("portals", {})
        
        # Deserialize torches
        game.torches = {}
        for key in data.get("torches", {}).keys():
            x, y = map(int, key.split(","))
            game.torches[(x, y)] = True
        
        # Deserialize map_data
        game.map_data = {}
        for key, block in data["map_data"].items():
            x, y = map(int, key.split(","))
            game.map_data[(x, y)] = block
        
        return game


class MiningView(discord.ui.LayoutView):
    """Mining game interface using Components v2"""
    
    def __init__(self, game: MiningGame, user_id: int, bot, mining_cog=None):
        self.game = game
        self.user_id = user_id
        self.bot = bot
        self.mining_cog = mining_cog
        self.message = None
        self.map_file = None
        super().__init__(timeout=300)
    
    @classmethod
    async def create(cls, game: MiningGame, user_id: int, bot, mining_cog=None):
        """Async factory method to create view with rendered map"""
        view = cls(game, user_id, bot, mining_cog)
        
        # Regenerate energy before rendering
        view.game.regenerate_energy()
        
        # Render map image in executor (prevents blocking)
        loop = asyncio.get_event_loop()
        map_image = await loop.run_in_executor(None, view.game.render_map, bot)
        view.map_file = discord.File(map_image, filename="mining_map.png")
        
        # Build UI after render completes
        await view._build_ui()
        return view
    
    async def _build_ui(self):
        """Build the UI components"""
        # Create buttons with callbacks
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        down_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬇️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        # Enable up button only if ladder is present
        can_go_up = self.game.can_move_up()
        up_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬆️", disabled=not can_go_up)
        surface_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⤴️", label="Surface")
        blank_btn_1 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        blank_btn_2 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)

        left_btn.callback = self.left_callback
        down_btn.callback = self.mine_callback
        right_btn.callback = self.right_callback
        up_btn.callback = self.up_callback
        surface_btn.callback = self.surface_callback
        
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
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Add inventory dropdown (always visible) - dynamic based on items owned
        inventory_options = [
            discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
        ]
        
        # Add items player actually has (count > 0)
        if self.game.items.get('ladder', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🪜 Place Ladder ({self.game.items['ladder']} left)", value="ladder", description="Climb back up easily"))
        if self.game.items.get('torch', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🔦 Place Torch ({self.game.items['torch']} left)", value="torch", description="Light up dark caves"))
        if self.game.items.get('portal', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🌀 Place Portal ({self.game.items['portal']} left)", value="portal", description="Teleport waystone"))
        if self.game.items.get('dynamite', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"💣 Use Dynamite ({self.game.items['dynamite']} left)", value="dynamite", description="Explode 3x3 area"))
        
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=inventory_options
        )
        inventory_select.callback = self.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(blank_btn_1, up_btn, blank_btn_2),
            discord.ui.ActionRow(left_btn, down_btn, right_btn),
            discord.ui.ActionRow(surface_btn),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(inventory_select),
        ])
        
        # Add auto-reset toggle button for singleplayer
        if not self.game.is_shared:
            reset_status = "ON" if self.game.auto_reset_enabled else "OFF"
            reset_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if self.game.auto_reset_enabled else discord.ButtonStyle.secondary,
                label=f"🔄 Auto-Reset: {reset_status}",
            )
            reset_btn.callback = self.toggle_reset_callback
            container_items.extend([
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(reset_btn),
            ])
        
        self.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5D4E37),
        )
        
        self.add_item(self.container1)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow game owner to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("**❌ This isn't your game!**", ephemeral=True)
            return False
        return True
    
    async def show_portal_modal(self, interaction: discord.Interaction):
        """Show modal for portal placement"""
        if self.game.items.get("portal", 0) <= 0:
            await interaction.response.send_message("❌ No portals in inventory!", ephemeral=True)
            return
        
        modal = discord.ui.Modal(title="Place Portal")
        name_input = discord.ui.TextInput(
            label="Portal Name",
            placeholder="Enter portal name (e.g., 'Home', 'Diamond Mine')",
            required=True,
            max_length=30
        )
        modal.add_item(name_input)
        
        # In multiplayer, ask if public
        if self.game.is_shared:
            public_input = discord.ui.TextInput(
                label="Public? (yes/no)",
                placeholder="yes = everyone can use, no = only you",
                required=True,
                max_length=3
            )
            modal.add_item(public_input)
        
        async def modal_callback(modal_interaction: discord.Interaction):
            portal_name = name_input.value
            is_public = True  # Default for singleplayer
            
            if self.game.is_shared and len(modal.children) > 1:
                public_answer = modal.children[1].value.lower()
                is_public = public_answer in ["yes", "y", "tak", "t"]
            
            # Place portal
            portal_id = f"portal_{self.game.portal_counter}"
            self.game.portal_counter += 1
            
            self.game.portals[portal_id] = {
                "name": portal_name,
                "x": self.game.x,
                "y": self.game.y,
                "owner_id": self.user_id,
                "public": is_public,
                "linked_to": None
            }
            
            self.game.items["portal"] -= 1
            visibility = "Public" if is_public else "Private"
            cog = modal_interaction.client.get_cog("Mining")
            if cog:
                cog.save_data()
            await self.refresh(modal_interaction, f"🌀 Portal '{portal_name}' placed! ({visibility}, {self.game.items['portal']} left)")
        
        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)
    
    async def inventory_callback(self, interaction: discord.Interaction):
        """Handle inventory dropdown selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        # Check if teleporting to another portal
        if action.startswith("teleport_"):
            portal_id = action.replace("teleport_", "")
            if portal_id in self.game.portals:
                target_portal = self.game.portals[portal_id]
                self.game.x = target_portal["x"]
                self.game.y = target_portal["y"]
                await self.refresh(interaction, f"🌀 Teleported to portal '{target_portal['name']}'!")
            else:
                await self.refresh(interaction, "❌ Portal not found!")
            return
        
        if action == "view_inv":
            if not self.game.inventory and not any(self.game.items.values()):
                await interaction.response.send_message("🎒 **Inventory is empty!**", ephemeral=True)
                return
            
            inv_text = "🎒 **Current Inventory:**\n\n"
            
            # Show blocks
            if self.game.inventory:
                inv_text += "**Blocks:**\n"
                for block, count in self.game.inventory.items():
                    value = self.game.BLOCK_VALUES.get(block, 0)
                    inv_text += f"• {count}x {block} (${value * count})\n"
                
                total_value = sum(self.game.BLOCK_VALUES.get(b, 0) * c for b, c in self.game.inventory.items())
                inv_text += f"\n⛏️ **Total Value:** {total_value} MineCoins\n"
            
            # Show items
            if any(self.game.items.values()):
                inv_text += "\n**Items:**\n"
                for item, count in self.game.items.items():
                    emoji = {"ladder": "🪜", "portal": "🌀", "torch": "🔦", "dynamite": "💣"}.get(item, "📦")
                    inv_text += f"• {emoji} {count}x {item}\n"
            
            await interaction.response.send_message(inv_text, ephemeral=True)
        
        elif action == "ladder":
            success, msg = self.game.place_ladder()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
        
        elif action == "torch":
            success, msg = self.game.place_torch()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
        
        elif action == "portal":
            # Show modal for portal placement
            await self.show_portal_modal(interaction)
        
        elif action == "dynamite":
            success, msg = self.game.use_dynamite()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
    
    async def toggle_reset_callback(self, interaction: discord.Interaction):
        """Toggle auto-reset for singleplayer"""
        self.game.auto_reset_enabled = not self.game.auto_reset_enabled
        status = "ENABLED" if self.game.auto_reset_enabled else "DISABLED"
        await self.refresh(interaction, f"🔄 Auto-Reset {status}! Map will {'reset' if self.game.auto_reset_enabled else 'NOT reset'} after 12h.")
    
    async def shop_callback(self, interaction: discord.Interaction):
        """Handle shop dropdown selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        if action == "sell":
            if not self.game.inventory:
                await self.refresh(interaction, "**❌ Inventory is empty!**")
                return
            value, items = self.game.sell_inventory(interaction.client)
            await self.refresh(interaction, f"⛏️ Sold items for {value} ⛏️ MineCoins!")
        
        elif action == "pickaxe":
            cost = self.game.pickaxe_level * 500
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.pickaxe_level += 1
                await self.refresh(interaction, f"⛏️ Upgraded pickaxe to level {self.game.pickaxe_level}!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
        
        elif action == "backpack":
            cost = self.game.backpack_capacity * 100
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.backpack_capacity += 10
                await self.refresh(interaction, f"🎒 Upgraded backpack to {self.game.backpack_capacity} slots!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
        
        elif action == "energy":
            cost = self.game.max_energy * 50
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.max_energy += 20
                self.game.energy = self.game.max_energy
                await self.refresh(interaction, f"⚡ Upgraded max energy to {self.game.max_energy}!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
    
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

    async def up_callback(self, interaction: discord.Interaction):
        """Mine and move up (requires ladder)"""
        # Check if player can move up (needs ladder)
        if not self.game.can_move_up():
            await self.refresh(interaction, "⚠️ Can't move up without a ladder! Place one first.")
            return
        
        target_x = self.game.x
        target_y = self.game.y - 1
    
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
            _, msg = self.game.move_player(0, -1)
    
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
            # Fall down until hitting ground (no energy cost for falling)
            while self.game.can_move(self.game.x, self.game.y + 1):
                self.game.y += 1
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
    
    async def surface_callback(self, interaction: discord.Interaction):
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
        
        # Move creatures along their patrol paths
        self.game.move_creatures()
        
        # Check for map regeneration
        if self.game.check_map_regeneration(bot=interaction.client, guild_id=self.game.guild_id):
            if message:
                message += "\n\n🔄 **Full map reset! (Ladders, portals, torches cleared. Inventory saved!)**"
            else:
                message = "🔄 **Full map reset! (Ladders, portals, torches cleared. Inventory saved!)**"
        
        # Render new map image in executor (prevents blocking)
        loop = asyncio.get_event_loop()
        map_image = await loop.run_in_executor(None, self.game.render_map, interaction.client)
        self.map_file = discord.File(map_image, filename="mining_map.png")
        
        # Update display text
        display_text = f"# ⛏ MINING ADVENTURE\n\n{self.game.get_stats_text()}"
        if message:
            display_text += f"\n\n{message}"
        
        # Clear ALL old items from THIS view
        self.clear_items()
        
        # Create buttons with callbacks for THIS view
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        down_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬇️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        # Enable up button only if ladder is present
        can_go_up = self.game.can_move_up()
        up_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬆️", disabled=not can_go_up)
        surface_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⤴️", label="Surface")
        blank_btn_1 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        blank_btn_2 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        
        up_btn.callback = self.up_callback
        left_btn.callback = self.left_callback
        down_btn.callback = self.mine_callback
        right_btn.callback = self.right_callback
        surface_btn.callback = self.surface_callback
        
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
            shop_select.callback = self.shop_callback
            container_items.append(discord.ui.ActionRow(shop_select))
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Check if player is standing on a portal
        standing_on_portal = False
        current_portal_is_private = False
        current_portal_owner = None
        for portal_id, portal_data in self.game.portals.items():
            if portal_data["x"] == self.game.x and portal_data["y"] == self.game.y:
                standing_on_portal = True
                current_portal_is_private = not portal_data["public"]
                current_portal_owner = portal_data["owner_id"]
                break
        
        # Add portal teleportation menu if standing on portal
        if standing_on_portal:
            # Check if player can use this portal
            can_use_portal = not current_portal_is_private or current_portal_owner == self.user_id
            
            portal_options = []
            
            # Add available portals (public + own private)
            for portal_id, portal_data in self.game.portals.items():
                # Skip current portal
                if portal_data["x"] == self.game.x and portal_data["y"] == self.game.y:
                    continue
                
                # Show if public or owned by player
                if portal_data["public"] or portal_data["owner_id"] == self.user_id:
                    visibility = "🌍" if portal_data["public"] else "🔒"
                    portal_options.append(
                        discord.SelectOption(
                            label=f"{visibility} {portal_data['name']}",
                            value=f"teleport_{portal_id}",
                            description=f"Teleport to ({portal_data['x']}, {portal_data['y']})"
                        )
                    )
            
            # Show portal menu
            if can_use_portal and len(portal_options) > 0:
                # Normal working portal menu
                portal_select = discord.ui.Select(
                    placeholder="🌀 Portal Teleportation",
                    options=portal_options[:25]  # Discord limit
                )
                portal_select.callback = self.inventory_callback
                container_items.append(discord.ui.ActionRow(portal_select))
                container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            elif not can_use_portal:
                # Private portal - show disabled menu
                portal_select = discord.ui.Select(
                    placeholder="🔒 This portal is private - you cannot use it",
                    options=[
                        discord.SelectOption(label="Private Portal", value="private", description="Only the owner can use this portal")
                    ],
                    disabled=True
                )
                container_items.append(discord.ui.ActionRow(portal_select))
                container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Add inventory dropdown (always visible) - dynamic based on items owned
        inventory_options = [
            discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
        ]
        
        # Add items player actually has (count > 0)
        if self.game.items.get('ladder', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🪜 Place Ladder ({self.game.items['ladder']} left)", value="ladder", description="Climb back up easily"))
        if self.game.items.get('torch', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🔦 Place Torch ({self.game.items['torch']} left)", value="torch", description="Light up dark caves"))
        if self.game.items.get('portal', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🌀 Place Portal ({self.game.items['portal']} left)", value="portal", description="Teleport waystone"))
        if self.game.items.get('dynamite', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"💣 Use Dynamite ({self.game.items['dynamite']} left)", value="dynamite", description="Explode 3x3 area"))
        
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=inventory_options
        )
        inventory_select.callback = self.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(blank_btn_1, up_btn, blank_btn_2),
            discord.ui.ActionRow(left_btn, down_btn, right_btn),
            discord.ui.ActionRow(surface_btn),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(inventory_select),
        ])
        
        # Add auto-reset toggle button for singleplayer
        if not self.game.is_shared:
            reset_status = "ON" if self.game.auto_reset_enabled else "OFF"
            reset_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if self.game.auto_reset_enabled else discord.ButtonStyle.secondary,
                label=f"🔄 Auto-Reset: {reset_status}",
            )
            reset_btn.callback = self.toggle_reset_callback
            container_items.extend([
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(reset_btn),
            ])
        

        # Replace container in THIS view
        self.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5D4E37),
        )
        
        self.add_item(self.container1)
        
        try:
            # Edit message with SAME view (self)
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=self, 
                attachments=[self.map_file]
            )
        except discord.errors.NotFound:
            # Message was deleted
            return
        except Exception as e:
            print(f"[Mining] Error refreshing view: {e}")
            return
        
        # Save game state after action
        cog = interaction.client.get_cog("Mining")
        if cog:
            # Update player data in shared world if applicable
            if self.game.is_shared and self.game.guild_id:
                if self.game.guild_id in cog.shared_worlds:
                    world_info = cog.shared_worlds[self.game.guild_id]
                    
                    # Update this player's data
                    player_key = str(self.user_id)
                    world_info["players"][player_key] = {
                        "x": self.game.x,
                        "y": self.game.y,
                        "depth": self.game.depth,
                        "energy": self.game.energy,
                        "max_energy": self.game.max_energy,
                        "last_energy_regen": self.game.last_energy_regen.isoformat(),
                        "pickaxe_level": self.game.pickaxe_level,
                        "backpack_capacity": self.game.backpack_capacity,
                        "inventory": self.game.inventory,
                        "coins": self.game.coins,
                        "items": self.game.items,  # Save personal items
                        "last_update": datetime.utcnow().isoformat()
                    }
                    
                    # Update world data (shared map and structures)
                    world_info["world_data"].map_data = self.game.map_data
                    world_info["world_data"].last_map_regen = self.game.last_map_regen
                    world_info["world_data"].ladders = self.game.ladders
                    world_info["world_data"].torches = self.game.torches
                    world_info["world_data"].portals = self.game.portals
                    world_info["world_data"].portal_counter = self.game.portal_counter
                    
                    # Refresh other players positions for next render
                    self.game.other_players = {}
                    for other_user_id, other_data in world_info["players"].items():
                        if str(other_user_id) != str(self.user_id):
                            # Try to get username from Discord
                            try:
                                user = interaction.client.get_user(int(other_user_id))
                                username = user.name if user else f"User {other_user_id}"
                            except:
                                username = f"User {other_user_id}"
                            
                            self.game.other_players[other_user_id] = {
                                "x": other_data["x"],
                                "y": other_data["y"],
                                "last_update": other_data.get("last_update", datetime.utcnow().isoformat()),
                                "username": username
                            }
            
            cog.save_data()


class OwnerMiningView(discord.ui.LayoutView):
    """Developer mining interface with additional testing features"""
    
    def __init__(self, game: MiningGame, user_id: int, bot, mining_cog=None):
        self.game = game
        self.user_id = user_id
        self.bot = bot
        self.mining_cog = mining_cog
        self.message = None
        self.map_file = None
        self.dev_menu_state = "main"  # Track submenu state: main, teleport, place_blocks, items
        super().__init__(timeout=300)
    
    @classmethod
    async def create(cls, game: MiningGame, user_id: int, bot, mining_cog=None):
        """Async factory method to create view with rendered map"""
        view = cls(game, user_id, bot, mining_cog)
        
        # Regenerate energy before rendering
        view.game.regenerate_energy()
        
        # Render map image in executor (prevents blocking)
        loop = asyncio.get_event_loop()
        map_image = await loop.run_in_executor(None, view.game.render_map, bot)
        view.map_file = discord.File(map_image, filename="mining_map.png")
        
        # Build UI after render completes
        await view._build_ui()
        return view
    
    async def _build_ui(self):
        """Build the UI components with developer menu"""
        # Create buttons with callbacks
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        down_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬇️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        up_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬆️", disabled=True)
        surface_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⤴️", label="Surface")
        blank_btn_1 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        blank_btn_2 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)

        left_btn.callback = self.left_callback
        down_btn.callback = self.mine_callback
        right_btn.callback = self.right_callback
        up_btn.callback = self.up_callback
        surface_btn.callback = self.surface_callback
        
        # Create container as class attribute
        container_items = [
            discord.ui.TextDisplay(content=f"# ⛏ MINING ADVENTURE [DEV MODE]\n\n{self.game.get_stats_text()}"),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://mining_map.png",
                    description=f"Seed: {self.game.seed} (Developer Mode)"
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Add developer menu (changes based on state)
        dev_select = None
        if self.dev_menu_state == "main":
            dev_select = discord.ui.Select(
                placeholder="🔧 Developer Menu",
                options=[
                    discord.SelectOption(label="⚡ Toggle Infinite Energy", value="infinite_energy", description=f"Currently: {'ON' if self.game.infinite_energy else 'OFF'}"),
                    discord.SelectOption(label="🎒 Toggle Infinite Backpack", value="infinite_backpack", description=f"Currently: {'ON' if self.game.infinite_backpack else 'OFF'}"),
                    discord.SelectOption(label="🗑️ Clear Area (5x5)", value="cleararea", description="Clear 5x5 area around you"),
                    discord.SelectOption(label="📍 Teleport Menu", value="teleport_menu", description="Teleport to depths or players"),
                    discord.SelectOption(label="🧱 Place Blocks Menu", value="place_menu", description="Place any block type"),
                    discord.SelectOption(label="📦 Items Menu", value="items_menu", description="Spawn items (ladder/torch/portal)"),
                    discord.SelectOption(label="🏗️ Structures Menu", value="structures_menu", description="Generate mineshafts and discover structures"),
                    discord.SelectOption(label="🔄 Force Map Reset", value="forcereset", description="Regenerate entire map now"),
                    discord.SelectOption(label="🌱 Change Seed", value="customseed", description="Enter custom world seed"),
                    discord.SelectOption(label="💎 Spawn Rare Items", value="spawnitems", description="Add valuable items"),
                    discord.SelectOption(label="🧟 Spawn Creatures", value="spawn_menu", description="Open creature spawn menu"),
                    discord.SelectOption(label="💰 Max All Upgrades", value="maxupgrades", description="Max pickaxe/backpack/energy"),
                    discord.SelectOption(label="🗺️ World Info", value="mapinfo", description="View map details"),
                ]
            )
        elif self.dev_menu_state == "structures":
            # Structures submenu
            dev_select = discord.ui.Select(
                placeholder="🏗️ Generate Structures",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="⛏️ Generate Mineshaft", value="gen_mineshaft", description="Create a vertical mineshaft"),
                    discord.SelectOption(label="🏛️ Discover All Structures", value="discover_all", description="Reveal all hidden structures"),
                ]
            )
        elif self.dev_menu_state == "items":
            # Items submenu
            dev_select = discord.ui.Select(
                placeholder="📦 Spawn Items",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🪜 Add Ladders", value="spawn_ladder", description=f"Current: {self.game.items.get('ladder', 0)}"),
                    discord.SelectOption(label="🔦 Add Torches", value="spawn_torch", description=f"Current: {self.game.items.get('torch', 0)}"),
                    discord.SelectOption(label="🌀 Add Portals", value="spawn_portal", description=f"Current: {self.game.items.get('portal', 0)}"),
                ]
            )
        elif self.dev_menu_state == "teleport":
            # Teleport submenu
            teleport_options = [
                discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                discord.SelectOption(label="📍 Surface", value="tp_surface", description="Y = -1"),
                discord.SelectOption(label="📍 Underground", value="tp_underground", description="Y = 10"),
                discord.SelectOption(label="📍 Deep Caves", value="tp_deep", description="Y = 25"),
                discord.SelectOption(label="📍 Mineral Depths", value="tp_mineral", description="Y = 50"),
                discord.SelectOption(label="📍 Ancient Depths", value="tp_ancient", description="Y = 75"),
                discord.SelectOption(label="📍 Abyss", value="tp_abyss", description="Y = 100"),
            ]
            
            # Add teleports to other players
            if self.game.is_shared and self.game.other_players:
                for player_id, player_data in list(self.game.other_players.items())[:10]:  # Limit to leave room for structures/portals
                    username = player_data.get("username", f"User {player_id}")
                    teleport_options.append(
                        discord.SelectOption(
                            label=f"👤 {username[:20]}", 
                            value=f"tp_player_{player_id}",
                            description=f"X={player_data['x']}, Y={player_data['y']}"
                        )
                    )
            
            # Discover nearby structures
            self.game.discover_nearby_structures(radius=10)
            
            # Add ALL structures (developer can see all, not just discovered)
            for structure_id, structure_data in self.game.structures.items():
                if len(teleport_options) < 23:
                    structure_type_emoji = {"mineshaft": "⛏️"}.get(structure_data["type"], "🏛️")
                    teleport_options.append(
                        discord.SelectOption(
                            label=f"{structure_type_emoji} {structure_data['name']}", 
                            value=f"tp_structure_{structure_id}",
                            description=f"Structure at ({structure_data['x']}, {structure_data['y']})"
                        )
                    )
            
            # Add ALL portals (developer can see all, not just public)
            for portal_id, portal_data in self.game.portals.items():
                if len(teleport_options) >= 25:
                    break
                visibility = "🌍" if portal_data["public"] else "🔒"
                # Show owner info for private portals
                owner_info = ""
                if not portal_data["public"]:
                    owner_info = f" (Owner: {portal_data['owner_id']})"
                teleport_options.append(
                    discord.SelectOption(
                        label=f"{visibility} {portal_data['name'][:15]}", 
                        value=f"tp_portal_{portal_id}",
                        description=f"Portal at ({portal_data['x']}, {portal_data['y']}){owner_info}"
                    )
                )
            
            dev_select = discord.ui.Select(
                placeholder="📍 Teleport Options",
                options=teleport_options
            )
        elif self.dev_menu_state == "place_blocks":
            # Block placement submenu
            dev_select = discord.ui.Select(
                placeholder="🧱 Place Block",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🟩 Grass", value="place_grass", description="Place grass block"),
                    discord.SelectOption(label="🟫 Dirt", value="place_dirt", description="Place dirt"),
                    discord.SelectOption(label="🪨 Stone", value="place_stone", description="Place stone"),
                    discord.SelectOption(label="🟤 Deepslate", value="place_deepslate", description="Place deepslate"),
                    discord.SelectOption(label="🌑 Bedrock", value="place_bedrock", description="Place bedrock"),
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🟩 Grass", value="place_grass", description="Place grass block"),
                    discord.SelectOption(label="🟫 Dirt", value="place_dirt", description="Place dirt"),
                    discord.SelectOption(label="🪧 Rock", value="place_stone", description="Place rock"),
                    discord.SelectOption(label="🪨 Stone", value="place_stone2", description="Place stone (stone2, deep layer)"),
                    discord.SelectOption(label="🟤 Deepslate", value="place_deepslate", description="Place deepslate"),
                    discord.SelectOption(label="🌑 Bedrock", value="place_bedrock", description="Place bedrock"),
                    discord.SelectOption(label="⚫ Coal", value="place_coal", description="Place coal ore"),
                    discord.SelectOption(label="⚪ Iron", value="place_iron", description="Place iron ore"),
                    discord.SelectOption(label="🟡 Gold", value="place_gold", description="Place gold ore"),
                    discord.SelectOption(label="🔴 Redstone", value="place_redstone", description="Place redstone ore"),
                    discord.SelectOption(label="🔷 Lapis", value="place_lapis", description="Place lapis ore"),
                    discord.SelectOption(label="💎 Diamond", value="place_diamond", description="Place diamond ore"),
                    discord.SelectOption(label="💚 Emerald", value="place_emerald", description="Place emerald ore"),
                    discord.SelectOption(label="⬛ Netherite", value="place_netherite", description="Place netherite"),
                    discord.SelectOption(label="🟫 Ancient Debris", value="place_ancient_debris", description="Place ancient debris"),
                    discord.SelectOption(label="📦 Chest", value="place_chest", description="Loot chest"),
                    discord.SelectOption(label="🏪 Shop", value="place_shop", description="Place a shop block"),
                    discord.SelectOption(label="🪵 M.Wood", value="place_mineshaft_wood", description="Mineshaft wood"),
                    discord.SelectOption(label="🏗️ M.Support", value="place_mineshaft_support", description="Support beam"),
                    discord.SelectOption(label="🛤️ M.Rail", value="place_mineshaft_rail", description="Rail"),
                    discord.SelectOption(label="🚪 M.Entrance", value="place_mineshaft_entrance", description="Entrance"),
                    discord.SelectOption(label="🌫️ Air", value="place_air", description="Remove block"),
                ]
            )
        elif self.dev_menu_state == "spawn_creatures":
            # Creature spawn submenu - spawns at player position like a block
            dev_select = discord.ui.Select(
                placeholder="🧟 Select a creature to spawn",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🧟 Zombie", value="spawn_creature_zombie", description=f"HP: {self.game.CREATURE_TYPES['zombie']['health']} | DMG: {self.game.CREATURE_TYPES['zombie']['damage']}"),
                    discord.SelectOption(label="💀 Skeleton", value="spawn_creature_skeleton", description=f"HP: {self.game.CREATURE_TYPES['skeleton']['health']} | DMG: {self.game.CREATURE_TYPES['skeleton']['damage']}"),
                    discord.SelectOption(label="🕷️ Spider", value="spawn_creature_spider", description=f"HP: {self.game.CREATURE_TYPES['spider']['health']} | DMG: {self.game.CREATURE_TYPES['spider']['damage']}"),
                    discord.SelectOption(label="💥 Creeper", value="spawn_creature_creeper", description=f"HP: {self.game.CREATURE_TYPES['creeper']['health']} | DMG: {self.game.CREATURE_TYPES['creeper']['damage']}"),
                    discord.SelectOption(label="👾 Enderman", value="spawn_creature_enderman", description=f"HP: {self.game.CREATURE_TYPES['enderman']['health']} | DMG: {self.game.CREATURE_TYPES['enderman']['damage']}"),
                    discord.SelectOption(label="🦫 Mole", value="spawn_creature_mole", description=f"HP: {self.game.CREATURE_TYPES['mole']['health']} | Harmless tunneler"),
                    discord.SelectOption(label="🪱 Worm", value="spawn_creature_worm", description=f"HP: {self.game.CREATURE_TYPES['worm']['health']} | DMG: {self.game.CREATURE_TYPES['worm']['damage']}"),
                ]
            )
        
        if dev_select is not None:
            dev_select.callback = self.dev_menu_callback
            container_items.append(discord.ui.ActionRow(dev_select))
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
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
            shop_select.callback = self.shop_callback
            container_items.append(discord.ui.ActionRow(shop_select))
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Add inventory dropdown (always visible) - dynamic based on items owned
        inventory_options = [
            discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
        ]
        
        # Add items player actually has (count > 0)
        if self.game.items.get('ladder', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🪜 Place Ladder ({self.game.items['ladder']} left)", value="ladder", description="Climb back up easily"))
        if self.game.items.get('torch', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🔦 Place Torch ({self.game.items['torch']} left)", value="torch", description="Light up dark caves"))
        if self.game.items.get('portal', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🌀 Place Portal ({self.game.items['portal']} left)", value="portal", description="Teleport waystone"))
        if self.game.items.get('dynamite', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"💣 Use Dynamite ({self.game.items['dynamite']} left)", value="dynamite", description="Explode 3x3 area"))
        
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=inventory_options
        )
        inventory_select.callback = self.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(blank_btn_1, up_btn, blank_btn_2),
            discord.ui.ActionRow(left_btn, down_btn, right_btn),
            discord.ui.ActionRow(surface_btn),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(inventory_select),
        ])
        
        # Add auto-reset toggle button for singleplayer
        if not self.game.is_shared:
            reset_status = "ON" if self.game.auto_reset_enabled else "OFF"
            reset_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if self.game.auto_reset_enabled else discord.ButtonStyle.secondary,
                label=f"🔄 Auto-Reset: {reset_status}",
            )
            reset_btn.callback = self.toggle_reset_callback
            container_items.extend([
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(reset_btn),
            ])
        
        self.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0xFF6600),  # Orange for dev mode
        )
        
        self.add_item(self.container1)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow game owner to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("**❌ This isn't your game!**", ephemeral=True)
            return False
        return True
    
    async def toggle_reset_callback(self, interaction: discord.Interaction):
        """Toggle auto-reset for singleplayer"""
        self.game.auto_reset_enabled = not self.game.auto_reset_enabled
        status = "ENABLED" if self.game.auto_reset_enabled else "DISABLED"
        await self.refresh(interaction, f"🔄 Auto-Reset {status}! Map will {'reset' if self.game.auto_reset_enabled else 'NOT reset'} after 12h.")
    
    async def show_portal_modal(self, interaction: discord.Interaction):
        """Show modal for portal placement"""
        if self.game.items.get("portal", 0) <= 0:
            await interaction.response.send_message("❌ No portals in inventory!", ephemeral=True)
            return
        
        modal = discord.ui.Modal(title="Place Portal")
        name_input = discord.ui.TextInput(
            label="Portal Name",
            placeholder="Enter portal name (e.g., 'Home', 'Diamond Mine')",
            required=True,
            max_length=30
        )
        modal.add_item(name_input)
        
        # In multiplayer, ask if public
        if self.game.is_shared:
            public_input = discord.ui.TextInput(
                label="Public? (yes/no)",
                placeholder="yes = everyone can use, no = only you",
                required=True,
                max_length=3
            )
            modal.add_item(public_input)
        
        async def modal_callback(modal_interaction: discord.Interaction):
            portal_name = name_input.value
            is_public = True  # Default for singleplayer
            
            if self.game.is_shared and len(modal.children) > 1:
                public_answer = modal.children[1].value.lower()
                is_public = public_answer in ["yes", "y", "tak", "t"]
            
            # Place portal
            portal_id = f"portal_{self.game.portal_counter}"
            self.game.portal_counter += 1
            
            self.game.portals[portal_id] = {
                "name": portal_name,
                "x": self.game.x,
                "y": self.game.y,
                "owner_id": self.user_id,
                "public": is_public,
                "linked_to": None
            }
            
            self.game.items["portal"] -= 1
            visibility = "Public" if is_public else "Private"
            cog = modal_interaction.client.get_cog("Mining")
            if cog:
                cog.save_data()
            await self.refresh(modal_interaction, f"🌀 Portal '{portal_name}' placed! ({visibility}, {self.game.items['portal']} left)")
        
        modal.on_submit = modal_callback
        await interaction.response.send_modal(modal)
    
    async def inventory_callback(self, interaction: discord.Interaction):
        """Handle inventory dropdown selection in OwnerMiningView"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        # Check if teleporting to another portal
        if action.startswith("teleport_"):
            portal_id = action.replace("teleport_", "")
            if portal_id in self.game.portals:
                target_portal = self.game.portals[portal_id]
                self.game.x = target_portal["x"]
                self.game.y = target_portal["y"]
                await self.refresh(interaction, f"🌀 Teleported to portal '{target_portal['name']}'!")
            else:
                await self.refresh(interaction, "❌ Portal not found!")
            return
        
        if action == "view_inv":
            if not self.game.inventory and not any(self.game.items.values()):
                await interaction.response.send_message("🎒 **Inventory is empty!**", ephemeral=True)
                return
            
            inv_text = "🎒 **Current Inventory:**\n\n"
            
            # Show blocks
            if self.game.inventory:
                inv_text += "**Blocks:**\n"
                for block, count in self.game.inventory.items():
                    value = self.game.BLOCK_VALUES.get(block, 0)
                    inv_text += f"• {count}x {block} (${value * count})\n"
                
                total_value = sum(self.game.BLOCK_VALUES.get(b, 0) * c for b, c in self.game.inventory.items())
                inv_text += f"\n⛏️ **Total Value:** {total_value} MineCoins\n"
            
            # Show items
            if any(self.game.items.values()):
                inv_text += "\n**Items:**\n"
                for item, count in self.game.items.items():
                    emoji = {"ladder": "🪜", "portal": "🌀", "torch": "🔦", "dynamite": "💣"}.get(item, "📦")
                    inv_text += f"• {emoji} {count}x {item}\n"
            
            await interaction.response.send_message(inv_text, ephemeral=True)
        
        elif action == "ladder":
            success, msg = self.game.place_ladder()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
        
        elif action == "torch":
            success, msg = self.game.place_torch()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
        
        elif action == "portal":
            # Show modal for portal placement
            await self.show_portal_modal(interaction)
        
        elif action == "dynamite":
            success, msg = self.game.use_dynamite()
            if success:
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
            await self.refresh(interaction, msg)
    
    async def dev_menu_callback(self, interaction: discord.Interaction):
        """Handle developer menu selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        # Handle submenu navigation
        if action == "back_main":
            self.dev_menu_state = "main"
            await self.refresh(interaction, "🔙 Returned to main developer menu")
            return
        
        elif action == "teleport_menu":
            self.dev_menu_state = "teleport"
            await self.refresh(interaction, "📍 **Teleport Menu** - Select destination")
            return
        
        elif action == "place_menu":
            self.dev_menu_state = "place_blocks"
            await self.refresh(interaction, "🧱 **Place Blocks Menu** - Select block to place")
            return
        
        elif action == "items_menu":
            self.dev_menu_state = "items"
            await self.refresh(interaction, "📦 **Items Menu** - Select item to spawn")
            return

        elif action == "spawn_menu":
            self.dev_menu_state = "spawn_creatures"
            await self.refresh(interaction, "🧟 **Spawn Menu** - Select a creature to spawn")
            return
        
        elif action == "structures_menu":
            self.dev_menu_state = "structures"
            await self.refresh(interaction, "🏗️ **Structures Menu** - Generate world structures")
            return
        
        # Main menu actions
        if action == "infinite_energy":
            self.game.infinite_energy = not self.game.infinite_energy
            status = "**ENABLED** (inf/inf)" if self.game.infinite_energy else "**DISABLED**"
            if self.game.infinite_energy:
                self.game.energy = self.game.max_energy
            await self.refresh(interaction, f"⚡ Infinite Energy: {status}")
        
        elif action == "infinite_backpack":
            self.game.infinite_backpack = not self.game.infinite_backpack
            inv_size = sum(self.game.inventory.values())
            status = f"**ENABLED** ({inv_size}/inf)" if self.game.infinite_backpack else "**DISABLED**"
            await self.refresh(interaction, f"🎒 Infinite Backpack: {status}")
        
        elif action == "cleararea":
            cleared = 0
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    x = self.game.x + dx
                    y = self.game.y + dy
                    if (x, y) in self.game.map_data and y >= 0:
                        self.game.map_data[(x, y)] = "air"
                        cleared += 1
            await self.refresh(interaction, f"🗑️ Cleared {cleared} blocks in 5x5 area!")
        
        elif action == "forcereset":
            # Force regenerate entire map - clear map_data first!
            self.game.map_data = {}
            self.game.generate_world(regenerate=True)
            self.game.last_map_regen = datetime.utcnow()
            self.game.x = 5  # Reset to centerL!ownermine
            self.game.y = -1  # Reset to surface
            await self.refresh(interaction, f"Force Reset! World regenerated with seed {self.game.seed}")
        
        elif action == "customseed":
            # Show modal for custom seed input
            modal = discord.ui.Modal(title="Enter Custom Seed")
            seed_input = discord.ui.TextInput(
                label="World Seed",
                placeholder="Enter seed number (e.g., 12345)",
                required=True,
                max_length=20
            )
            modal.add_item(seed_input)
            
            async def modal_callback(modal_interaction: discord.Interaction):
                try:
                    new_seed = int(seed_input.value)
                    self.game.seed = new_seed
                    self.game.rng = random.Random(new_seed)
                    self.game.map_data = {}  # Clear map first!
                    self.game.generate_world(regenerate=True)
                    self.game.last_map_regen = datetime.utcnow()
                    self.game.x = 5
                    self.game.y = -1
                    await self.refresh(modal_interaction, f"Custom Seed {new_seed} Applied! World regenerated")
                except ValueError:
                    await self.refresh(modal_interaction, "Invalid seed! Please enter a valid number.")
            
            modal.on_submit = modal_callback
            await interaction.response.send_modal(modal)
            return
        
        # Creature spawning - prawdziwy spawn z ścieżką patrolu
        elif action.startswith("spawn_creature_"):
            creature_type = action.replace("spawn_creature_", "")
            if creature_type in self.game.CREATURE_TYPES:
                creature_data = self.game.CREATURE_TYPES[creature_type]
                creature_id = f"creature_{self.game.creature_counter}"
                self.game.creature_counter += 1
                spawn_x = self.game.x
                # Wymuś spawn pod ziemią (y >= 5) żeby patrol działał prawidłowo
                spawn_y = max(5, self.game.y)
                # Generuj losową ścieżkę patrolu (identycznie jak spawn_creatures)
                path_length = self.game.rng.randint(15, 40)
                path = [(spawn_x, spawn_y)]
                cur_x, cur_y = spawn_x, spawn_y
                for _ in range(path_length - 1):
                    dx, dy = self.game.rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                    cur_x = max(-45, min(45, cur_x + dx))
                    cur_y = max(0, min(100, cur_y + dy))
                    path.append((cur_x, cur_y))
                # NOTE: Tunnel carving happens step by step in move_creatures, not upfront
                self.game.creatures[creature_id] = {
                    "type": creature_type,
                    "x": spawn_x,
                    "y": spawn_y,
                    "path": path,
                    "path_index": 0,
                    "health": creature_data["health"],
                    "idle_refreshes": 0
                }
                emoji = creature_data.get("emoji", "🧟")
                cog = interaction.client.get_cog("Mining")
                if cog:
                    cog.save_data()
                await self.refresh(interaction, f"{emoji} Spawned **{creature_type.title()}** at ({spawn_x}, {spawn_y})! HP: {creature_data['health']} | Patrol: {len(path)} waypoints")
            else:
                await self.refresh(interaction, f"❌ Unknown creature type: {creature_type}")
            return

        # Items spawning actions
        elif action.startswith("spawn_"):
            item_type = action.replace("spawn_", "")
            if item_type in ["ladder", "torch", "portal"]:
                # Show modal for quantity input
                modal = discord.ui.Modal(title=f"Add {item_type.title()}s")
                quantity_input = discord.ui.TextInput(
                    label="Quantity",
                    placeholder=f"How many {item_type}s? (e.g., 10)",
                    required=True,
                    max_length=5
                )
                modal.add_item(quantity_input)
                
                async def item_modal_callback(modal_interaction: discord.Interaction):
                    try:
                        quantity = int(quantity_input.value)
                        if quantity < 1:
                            await self.refresh(modal_interaction, "❌ Quantity must be at least 1!")
                            return
                        if quantity > 9999:
                            await self.refresh(modal_interaction, "❌ Maximum quantity is 9999!")
                            return
                        
                        self.game.items[item_type] = self.game.items.get(item_type, 0) + quantity
                        emoji = {"ladder": "🪜", "torch": "🔦", "portal": "🌀"}.get(item_type, "📦")
                        cog = modal_interaction.client.get_cog("Mining")
                        if cog:
                            cog.save_data()
                        await self.refresh(modal_interaction, f"{emoji} Added {quantity}x {item_type}! Total: {self.game.items[item_type]}")
                    except ValueError:
                        await self.refresh(modal_interaction, "❌ Invalid quantity! Please enter a number.")
                
                modal.on_submit = item_modal_callback
                await interaction.response.send_modal(modal)
                return
        
        # Teleport actions
        elif action.startswith("tp_structure_"):
            structure_id = action.replace("tp_structure_", "")
            if structure_id in self.game.structures:
                structure = self.game.structures[structure_id]
                self.game.x = structure["x"]
                self.game.y = structure["y"]
                await self.refresh(interaction, f"🏛️ Teleported to {structure['name']}!")
            else:
                await self.refresh(interaction, "❌ Structure not found!")
        
        elif action.startswith("tp_portal_"):
            portal_id = action.replace("tp_portal_", "")
            if portal_id in self.game.portals:
                portal = self.game.portals[portal_id]
                self.game.x = portal["x"]
                self.game.y = portal["y"]
                await self.refresh(interaction, f"🌀 Teleported to portal '{portal['name']}'!")
            else:
                await self.refresh(interaction, "❌ Portal not found!")
        
        elif action.startswith("tp_player_"):
            player_id = action.replace("tp_player_", "")
            if player_id in self.game.other_players:
                player_data = self.game.other_players[player_id]
                self.game.x = player_data["x"]
                self.game.y = player_data["y"]
                username = player_data.get("username", f"User {player_id}")
                await self.refresh(interaction, f"📍 Teleported to **{username}** at ({self.game.x}, {self.game.y})!")
            else:
                await self.refresh(interaction, "❌ Player not found!")
        
        elif action.startswith("tp_"):
            teleport_depths = {
                "tp_surface": (-1, "Surface"),
                "tp_underground": (10, "Underground"),
                "tp_deep": (25, "Deep Caves"),
                "tp_mineral": (50, "Mineral Depths"),
                "tp_ancient": (75, "Ancient Depths"),
                "tp_abyss": (100, "The Abyss")
            }
            
            if action in teleport_depths:
                depth, name = teleport_depths[action]
                self.game.y = depth
                self.game.x = 5
                await self.refresh(interaction, f"📍 Teleported to **{name}** (Y = {depth})!")
        
        # Block placement actions
        elif action.startswith("place_"):
            block_type = action.replace("place_", "")
            target_x = self.game.x
            target_y = self.game.y + 1  # Place below player
            
            # Place the block
            self.game.map_data[(target_x, target_y)] = block_type
            
            block_names = {
                "shop": "🏪 Shop",
                "stone": "🪨 Stone",
                "stone2": "🪧 Rock",
                "grass": "🟩 Grass",
                "bedrock": "🌑 Bedrock",
                "lapis": "🔷 Lapis Ore",
                "diamond": "💎 Diamond Ore",
                "emerald": "💚 Emerald Ore",
                "gold": "🟡 Gold Ore",
                "netherite": "⬛ Netherite",
                "ancient_debris": "🟫 Ancient Debris",
                "redstone": "🔴 Redstone Ore",
                "coal": "⚫ Coal Ore",
                "iron": "⚪ Iron Ore",
                "deepslate": "🟤 Deepslate",
                "dirt": "🟫 Dirt",
                "chest": "📦 Loot Chest",
                "mineshaft_wood": "🪵 Mineshaft Wood",
                "mineshaft_support": "🏗️ Support Beam",
                "mineshaft_rail": "🛤️ Rail",
                "mineshaft_entrance": "🚪 Entrance",
                "air": "🌫️ Air (removed block)"
            }
            
            block_name = block_names.get(block_type, block_type)
            await self.refresh(interaction, f"🧱 Placed **{block_name}** at ({target_x}, {target_y})!")
        
        elif action == "spawnitems":
            self.game.inventory["diamond"] = self.game.inventory.get("diamond", 0) + 10
            self.game.inventory["emerald"] = self.game.inventory.get("emerald", 0) + 10
            self.game.inventory["gold"] = self.game.inventory.get("gold", 0) + 10
            self.game.inventory["netherite"] = self.game.inventory.get("netherite", 0) + 10
            self.game.inventory["ancient_debris"] = self.game.inventory.get("ancient_debris", 0) + 10
            await self.refresh(interaction, "💎 **Spawned Items:** Diamond x10, Emerald x10, Gold x10, Netherite x10, Ancient Debris x10")
        
        elif action == "maxupgrades":
            self.game.pickaxe_level = 10
            self.game.backpack_capacity = 200
            self.game.max_energy = 200
            self.game.energy = self.game.max_energy
            await self.refresh(interaction, "🚀 **Maxed Upgrades:** Pickaxe Lv.10, Backpack 200, Energy 200!")

        elif action == "respawn_creatures":
            # Force immediate respawn of creatures
            self.game.spawn_creatures()
            await self.refresh(interaction, f"🔁 Respawned {len(self.game.creatures)} creatures!")

        elif action == "toggle_devrespawn":
            # Toggle developer auto-respawn flag on game
            self.game.dev_mode = not getattr(self.game, "dev_mode", False)
            status = "ENABLED" if self.game.dev_mode else "DISABLED"
            await self.refresh(interaction, f"🤖 Dev auto-respawn {status} (game.dev_mode={self.game.dev_mode})")

        elif action == "mapinfo":
            biome = self.game.get_biome(self.game.y)
            info = (
                f"🗺️ **World Information:**\n"
                f"• **Seed:** {self.game.seed}\n"
                f"• **Blocks Generated:** {len(self.game.map_data)}\n"
                f"• **Current Biome:** {biome['name']}\n"
                f"• **Position:** ({self.game.x}, {self.game.y})\n"
                f"• **Max Depth:** {self.game.depth}\n"
                f"• **Shared World:** {'Yes' if self.game.is_shared else 'No'}\n"
                f"• **Other Players:** {len(self.game.other_players)}\n"
                f"• **Infinite Energy:** {'ON' if self.game.infinite_energy else 'OFF'}\n"
                f"• **Infinite Backpack:** {'ON' if self.game.infinite_backpack else 'OFF'}"
            )
            await self.refresh(interaction, info)
        
        # Structures generation actions
        elif action == "gen_mineshaft":
            # Generate a horizontal mineshaft at current position
            structure_id = f"mineshaft_{self.game.structure_counter}"
            self.game.structure_counter += 1
            
            start_x = self.game.x
            tunnel_y = self.game.y
            tunnel_height = self.game.rng.randint(4, 5)  # 4-5 blocks
            tunnel_length = self.game.rng.randint(20, 35)  # 20-35 blocks
            
            self.game.structures[structure_id] = {
                "type": "mineshaft",
                "name": f"Mineshaft #{len([s for s in self.game.structures.values() if s['type'] == 'mineshaft']) + 1}",
                "x": start_x,
                "y": tunnel_y - tunnel_height + 1,
                "width": tunnel_length,
                "height": tunnel_height,
                "discovered": True
            }
            
            # Build the horizontal mineshaft tunnel (CORRECT orientation)
            for x_offset in range(tunnel_length):
                current_x = start_x + x_offset
                
                # Build tunnel from TOP to BOTTOM
                for height_offset in range(tunnel_height):
                    current_y = tunnel_y - height_offset
                    
                    # Floor (bottom layer) - rails
                    if height_offset == 0:
                        self.game.map_data[(current_x, current_y)] = "mineshaft_rail"
                    # Ceiling (top layer) - wood
                    elif height_offset == tunnel_height - 1:
                        self.game.map_data[(current_x, current_y)] = "mineshaft_wood"
                    # Middle layers - air
                    else:
                        self.game.map_data[(current_x, current_y)] = "air"
                
                # Full support beams every 6 blocks
                if x_offset % 6 == 0 and x_offset > 0:
                    for height_offset in range(tunnel_height):
                        current_y = tunnel_y - height_offset
                        self.game.map_data[(current_x, current_y)] = "mineshaft_support"
                
                # Torches every 5 blocks
                if x_offset % 5 == 2:
                    torch_y = tunnel_y - 1
                    self.game.torches[(current_x, torch_y)] = True
                
                # Chests (10% chance)
                if x_offset > 3 and self.game.rng.random() < 0.10:
                    chest_y = tunnel_y - 1  # One block above floor
                    self.game.map_data[(current_x, chest_y)] = "chest"
                
                # Entrance marker at start
                if x_offset == 0:
                    entrance_y = tunnel_y - tunnel_height + 2
                    self.game.map_data[(current_x, entrance_y)] = "mineshaft_entrance"
            
            cog = interaction.client.get_cog("Mining")
            if cog:
                cog.save_data()
            
            await self.refresh(interaction, f"⛏️ Horizontal mineshaft generated! Length: {tunnel_length}, Height: {tunnel_height}")
        
        elif action == "discover_all":
            count = 0
            for structure_data in self.game.structures.values():
                if not structure_data["discovered"]:
                    structure_data["discovered"] = True
                    count += 1
            await self.refresh(interaction, f"🏛️ Discovered {count} hidden structures!")
    
    async def shop_callback(self, interaction: discord.Interaction):
        """Handle shop dropdown selection"""
        selected = interaction.data.get('values', [])
        if not selected:
            await interaction.response.defer()
            return
        
        action = selected[0]
        
        if action == "sell":
            if not self.game.inventory:
                await self.refresh(interaction, "**❌ Inventory is empty!**")
                return
            value, items = self.game.sell_inventory(interaction.client)
            await self.refresh(interaction, f"⛏️ Sold items for {value} ⛏️ MineCoins!")
        
        elif action == "pickaxe":
            cost = self.game.pickaxe_level * 500
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.pickaxe_level += 1
                await self.refresh(interaction, f"⛏️ Upgraded pickaxe to level {self.game.pickaxe_level}!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
        
        elif action == "backpack":
            cost = self.game.backpack_capacity * 100
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.backpack_capacity += 10
                await self.refresh(interaction, f"🎒 Upgraded backpack to {self.game.backpack_capacity} slots!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
        
        elif action == "energy":
            cost = self.game.max_energy * 50
            economy_cog = self.bot.get_cog('Economy')
            
            if not economy_cog:
                await self.refresh(interaction, "**❌ Economy system not available.**")
                return
            
            if economy_cog.remove_mine_coins(interaction.user.id, cost):
                self.game.coins = economy_cog.get_mine_coins(interaction.user.id)
                self.game.max_energy += 20
                self.game.energy = self.game.max_energy
                await self.refresh(interaction, f"⚡ Upgraded max energy to {self.game.max_energy}!")
            else:
                await self.refresh(interaction, f"**❌ Need {cost} ⛏️ MineCoins!**")
    
    async def left_callback(self, interaction: discord.Interaction):
        """Mine and move left"""
        target_x = self.game.x - 1
        target_y = self.game.y
        
        if not self.game.can_move(target_x, target_y):
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:
                self.game.x = target_x
                self.game.y = target_y
                _, msg, _ = result
            else:
                _, msg = result
        else:
            _, msg = self.game.move_player(-1, 0)
        
        await self.refresh(interaction, msg)

    async def up_callback(self, interaction: discord.Interaction):
        """Mine and move up"""
        target_x = self.game.x
        target_y = self.game.y - 1
    
        if not self.game.can_move(target_x, target_y):
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:
                self.game.x = target_x
                self.game.y = target_y
                _, msg, _ = result
            else:
                _, msg = result
        else:
            _, msg = self.game.move_player(0, -1)
    
        await self.refresh(interaction, msg)
    
    async def right_callback(self, interaction: discord.Interaction):
        """Mine and move right"""
        target_x = self.game.x + 1
        target_y = self.game.y
        
        if not self.game.can_move(target_x, target_y):
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:
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
        
        if self.game.can_move(target_x, target_y):
            while self.game.can_move(self.game.x, self.game.y + 1):
                self.game.y += 1
            msg = f"⬇️ Fell to ground at y={self.game.y}"
        else:
            result = self.game.mine_block(target_x, target_y)
            if len(result) == 3 and result[0]:
                success, msg, (new_x, new_y) = result
                self.game.x = new_x
                self.game.y = new_y
                
                while self.game.can_move(self.game.x, self.game.y + 1):
                    self.game.y += 1
                    if self.game.y > new_y:
                        msg += f" → Fell to y={self.game.y}"
                        break
            else:
                _, msg = result
        
        await self.refresh(interaction, msg)
    
    async def surface_callback(self, interaction: discord.Interaction):
        """Return to surface"""
        self.game.x = 1
        self.game.y = -1
        await self.refresh(interaction, "⬆️ Returned to surface!")
    
    async def on_timeout(self):
        """Handle timeout"""
        # Remove user from active sessions
        if self.mining_cog and self.user_id in self.mining_cog.active_sessions:
            del self.mining_cog.active_sessions[self.user_id]
        
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass
    
    async def refresh(self, interaction: discord.Interaction, message: str = None):
        """Refresh the game view"""
        self.game.regenerate_energy()
        
        # Move creatures along their patrol paths
        self.game.move_creatures()
        
        if self.game.check_map_regeneration(bot=interaction.client, guild_id=self.game.guild_id):
            if message:
                message += "\n\n🔄 **Full map reset! (Ladders, portals, torches cleared. Inventory saved!)**"
            else:
                message = "🔄 **Full map reset! (Ladders, portals, torches cleared. Inventory saved!)**"
        
        loop = asyncio.get_event_loop()
        map_image = await loop.run_in_executor(None, self.game.render_map, interaction.client)
        self.map_file = discord.File(map_image, filename="mining_map.png")
        
        display_text = f"# ⛏ MINING ADVENTURE [DEV MODE]\n\n{self.game.get_stats_text()}"
        if message:
            display_text += f"\n\n{message}"
        
        self.clear_items()
        
        left_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬅️")
        down_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬇️")
        right_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="➡️")
        # Enable up button only if ladder is present
        can_go_up = self.game.can_move_up()
        up_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="⬆️", disabled=not can_go_up)
        surface_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⤴️", label="Surface")
        blank_btn_1 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        blank_btn_2 = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="<:space:1468655364982702294>", disabled=True)
        
        up_btn.callback = self.up_callback
        left_btn.callback = self.left_callback
        down_btn.callback = self.mine_callback
        right_btn.callback = self.right_callback
        surface_btn.callback = self.surface_callback
        
        container_items = [
            discord.ui.TextDisplay(content=display_text),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="attachment://mining_map.png",
                    description=f"Seed: {self.game.seed} (Developer Mode)"
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Add developer menu (changes based on state)
        dev_select = None
        if self.dev_menu_state == "main":
            dev_select = discord.ui.Select(
                placeholder="🔧 Developer Menu",
                options=[
                    discord.SelectOption(label="⚡ Toggle Infinite Energy", value="infinite_energy", description=f"Currently: {'ON' if self.game.infinite_energy else 'OFF'}"),
                    discord.SelectOption(label="🎒 Toggle Infinite Backpack", value="infinite_backpack", description=f"Currently: {'ON' if self.game.infinite_backpack else 'OFF'}"),
                    discord.SelectOption(label="🗑️ Clear Area (5x5)", value="cleararea", description="Clear 5x5 area around you"),
                    discord.SelectOption(label="📍 Teleport Menu", value="teleport_menu", description="Teleport to depths or players"),
                    discord.SelectOption(label="🧱 Place Blocks Menu", value="place_menu", description="Place any block type"),
                    discord.SelectOption(label="📦 Items Menu", value="items_menu", description="Spawn items (ladder/torch/portal)"),
                    discord.SelectOption(label="🏗️ Structures Menu", value="structures_menu", description="Generate mineshafts and discover structures"),
                    discord.SelectOption(label="🔄 Force Map Reset", value="forcereset", description="Regenerate entire map now"),
                    discord.SelectOption(label="🌱 Change Seed", value="customseed", description="Enter custom world seed"),
                    discord.SelectOption(label="💎 Spawn Rare Items", value="spawnitems", description="Add valuable items"),
                    discord.SelectOption(label="🧟 Spawn Creatures", value="spawn_menu", description="Open creature spawn menu"),
                    discord.SelectOption(label="💰 Max All Upgrades", value="maxupgrades", description="Max pickaxe/backpack/energy"),
                    discord.SelectOption(label="🗺️ World Info", value="mapinfo", description="View map details"),
                ]
            )
        elif self.dev_menu_state == "structures":
            # Structures submenu
            dev_select = discord.ui.Select(
                placeholder="🏗️ Generate Structures",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="⛏️ Generate Mineshaft", value="gen_mineshaft", description="Create a vertical mineshaft"),
                    discord.SelectOption(label="🏛️ Discover All Structures", value="discover_all", description="Reveal all hidden structures"),
                ]
            )
        elif self.dev_menu_state == "items":
            # Items submenu
            dev_select = discord.ui.Select(
                placeholder="📦 Spawn Items",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🪜 Add Ladders", value="spawn_ladder", description=f"Current: {self.game.items.get('ladder', 0)}"),
                    discord.SelectOption(label="🔦 Add Torches", value="spawn_torch", description=f"Current: {self.game.items.get('torch', 0)}"),
                    discord.SelectOption(label="🌀 Add Portals", value="spawn_portal", description=f"Current: {self.game.items.get('portal', 0)}"),
                ]
            )
        elif self.dev_menu_state == "teleport":
            # Teleport submenu
            teleport_options = [
                discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                discord.SelectOption(label="📍 Surface", value="tp_surface", description="Y = -1"),
                discord.SelectOption(label="📍 Underground", value="tp_underground", description="Y = 10"),
                discord.SelectOption(label="📍 Deep Caves", value="tp_deep", description="Y = 25"),
                discord.SelectOption(label="📍 Mineral Depths", value="tp_mineral", description="Y = 50"),
                discord.SelectOption(label="📍 Ancient Depths", value="tp_ancient", description="Y = 75"),
                discord.SelectOption(label="📍 Abyss", value="tp_abyss", description="Y = 100"),
            ]
            
            # Add teleports to other players
            if self.game.is_shared and self.game.other_players:
                for player_id, player_data in list(self.game.other_players.items())[:10]:  # Limit to leave room for structures/portals
                    username = player_data.get("username", f"User {player_id}")
                    teleport_options.append(
                        discord.SelectOption(
                            label=f"👤 {username[:20]}", 
                            value=f"tp_player_{player_id}",
                            description=f"X={player_data['x']}, Y={player_data['y']}"
                        )
                    )
            
            # Discover nearby structures
            self.game.discover_nearby_structures(radius=10)
            
            # Add ALL structures (developer can see all, not just discovered)
            for structure_id, structure_data in self.game.structures.items():
                if len(teleport_options) < 23: 
                    structure_type_emoji = {"mineshaft": "⛏️"}.get(structure_data["type"], "🏛️")
                    teleport_options.append(
                        discord.SelectOption(
                            label=f"{structure_type_emoji} {structure_data['name']}", 
                            value=f"tp_structure_{structure_id}",
                            description=f"Structure at ({structure_data['x']}, {structure_data['y']})"
                        )
                    )
            
            # Add ALL portals (developer can see all, not just public)
            for portal_id, portal_data in self.game.portals.items():
                if len(teleport_options) >= 25:
                    break
                visibility = "🌍" if portal_data["public"] else "🔒"
                # Show owner info for private portals
                owner_info = ""
                if not portal_data["public"]:
                    owner_info = f" (Owner: {portal_data['owner_id']})"
                teleport_options.append(
                    discord.SelectOption(
                        label=f"{visibility} {portal_data['name'][:15]}", 
                        value=f"tp_portal_{portal_id}",
                        description=f"Portal at ({portal_data['x']}, {portal_data['y']}){owner_info}"
                    )
                )
            
            dev_select = discord.ui.Select(
                placeholder="📍 Teleport Options",
                options=teleport_options
            )
        elif self.dev_menu_state == "place_blocks":
            # Block placement submenu
            dev_select = discord.ui.Select(
                placeholder="🧱 Place Block",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🟩 Grass", value="place_grass", description="Place grass block"),
                    discord.SelectOption(label="🟫 Dirt", value="place_dirt", description="Place dirt"),
                    discord.SelectOption(label="🪧 Rock", value="place_stone", description="Place rock"),
                    discord.SelectOption(label="🪨 Stone", value="place_stone2", description="Place stone (stone2, deep layer)"),
                    discord.SelectOption(label="🟤 Deepslate", value="place_deepslate", description="Place deepslate"),
                    discord.SelectOption(label="🌑 Bedrock", value="place_bedrock", description="Place bedrock"),
                    discord.SelectOption(label="⚫ Coal", value="place_coal", description="Place coal ore"),
                    discord.SelectOption(label="⚪ Iron", value="place_iron", description="Place iron ore"),
                    discord.SelectOption(label="🟡 Gold", value="place_gold", description="Place gold ore"),
                    discord.SelectOption(label="🔴 Redstone", value="place_redstone", description="Place redstone ore"),
                    discord.SelectOption(label="🔷 Lapis", value="place_lapis", description="Place lapis ore"),
                    discord.SelectOption(label="💎 Diamond", value="place_diamond", description="Place diamond ore"),
                    discord.SelectOption(label="💚 Emerald", value="place_emerald", description="Place emerald ore"),
                    discord.SelectOption(label="⬛ Netherite", value="place_netherite", description="Place netherite"),
                    discord.SelectOption(label="🟫 Ancient Debris", value="place_ancient_debris", description="Place ancient debris"),
                    discord.SelectOption(label="📦 Chest", value="place_chest", description="Loot chest"),
                    discord.SelectOption(label="🏪 Shop", value="place_shop", description="Place a shop block"),
                    discord.SelectOption(label="🪵 M.Wood", value="place_mineshaft_wood", description="Mineshaft wood"),
                    discord.SelectOption(label="🏗️ M.Support", value="place_mineshaft_support", description="Support beam"),
                    discord.SelectOption(label="🛤️ M.Rail", value="place_mineshaft_rail", description="Rail"),
                    discord.SelectOption(label="🚪 M.Entrance", value="place_mineshaft_entrance", description="Entrance"),
                    discord.SelectOption(label="🌫️ Air", value="place_air", description="Remove block"),
                ]
            )
        elif self.dev_menu_state == "spawn_creatures":
            # Creature spawn submenu - spawns at player position like a block
            dev_select = discord.ui.Select(
                placeholder="🧟 Wybierz stwora do spawnu",
                options=[
                    discord.SelectOption(label="⬅️ Back to Main Menu", value="back_main", description="Return to main dev menu"),
                    discord.SelectOption(label="🧟 Zombie", value="spawn_creature_zombie", description=f"HP: {self.game.CREATURE_TYPES['zombie']['health']} | DMG: {self.game.CREATURE_TYPES['zombie']['damage']}"),
                    discord.SelectOption(label="💀 Skeleton", value="spawn_creature_skeleton", description=f"HP: {self.game.CREATURE_TYPES['skeleton']['health']} | DMG: {self.game.CREATURE_TYPES['skeleton']['damage']}"),
                    discord.SelectOption(label="🕷️ Spider", value="spawn_creature_spider", description=f"HP: {self.game.CREATURE_TYPES['spider']['health']} | DMG: {self.game.CREATURE_TYPES['spider']['damage']}"),
                    discord.SelectOption(label="💥 Creeper", value="spawn_creature_creeper", description=f"HP: {self.game.CREATURE_TYPES['creeper']['health']} | DMG: {self.game.CREATURE_TYPES['creeper']['damage']}"),
                    discord.SelectOption(label="👾 Enderman", value="spawn_creature_enderman", description=f"HP: {self.game.CREATURE_TYPES['enderman']['health']} | DMG: {self.game.CREATURE_TYPES['enderman']['damage']}"),
                    discord.SelectOption(label="🦫 Mole", value="spawn_creature_mole", description=f"HP: {self.game.CREATURE_TYPES['mole']['health']} | Harmless tunneler"),
                    discord.SelectOption(label="🪱 Worm", value="spawn_creature_worm", description=f"HP: {self.game.CREATURE_TYPES['worm']['health']} | DMG: {self.game.CREATURE_TYPES['worm']['damage']}"),
                ]
            )
        
        if dev_select is not None:
            dev_select.callback = self.dev_menu_callback
            container_items.append(discord.ui.ActionRow(dev_select))
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
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
            container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Check if player is standing on a portal
        standing_on_portal = False
        current_portal_is_private = False
        current_portal_owner = None
        for portal_id, portal_data in self.game.portals.items():
            if portal_data["x"] == self.game.x and portal_data["y"] == self.game.y:
                standing_on_portal = True
                current_portal_is_private = not portal_data["public"]
                current_portal_owner = portal_data["owner_id"]
                break
        
        # Add portal teleportation menu if standing on portal
        if standing_on_portal:
            # Check if player can use this portal
            can_use_portal = not current_portal_is_private or current_portal_owner == self.user_id
            
            portal_options = []
            
            # Add available portals (public + own private)
            for portal_id, portal_data in self.game.portals.items():
                # Skip current portal
                if portal_data["x"] == self.game.x and portal_data["y"] == self.game.y:
                    continue
                
                # Show if public or owned by player
                if portal_data["public"] or portal_data["owner_id"] == self.user_id:
                    visibility = "🌍" if portal_data["public"] else "🔒"
                    portal_options.append(
                        discord.SelectOption(
                            label=f"{visibility} {portal_data['name']}",
                            value=f"teleport_{portal_id}",
                            description=f"Teleport to ({portal_data['x']}, {portal_data['y']})"
                        )
                    )
            
            # Show portal menu
            if can_use_portal and len(portal_options) > 0:
                # Normal working portal menu
                portal_select = discord.ui.Select(
                    placeholder="🌀 Portal Teleportation",
                    options=portal_options[:25]  # Discord limit
                )
                portal_select.callback = self.inventory_callback
                container_items.append(discord.ui.ActionRow(portal_select))
                container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            elif not can_use_portal:
                # Private portal - show disabled menu
                portal_select = discord.ui.Select(
                    placeholder="🔒 Ten portal jest prywatny - nie możesz go użyć",
                    options=[
                        discord.SelectOption(label="Prywatny Portal", value="private", description="Tylko właściciel może użyć tego portalu")
                    ],
                    disabled=True
                )
                container_items.append(discord.ui.ActionRow(portal_select))
                container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Add inventory dropdown (always visible) - dynamic based on items owned
        inventory_options = [
            discord.SelectOption(label="🎒 View Inventory", value="view_inv", description="See what you're carrying"),
        ]
        
        # Add items player actually has (count > 0)
        if self.game.items.get('ladder', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🪜 Place Ladder ({self.game.items['ladder']} left)", value="ladder", description="Climb back up easily"))
        if self.game.items.get('torch', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🔦 Place Torch ({self.game.items['torch']} left)", value="torch", description="Light up dark caves"))
        if self.game.items.get('portal', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"🌀 Place Portal ({self.game.items['portal']} left)", value="portal", description="Teleport waystone"))
        if self.game.items.get('dynamite', 0) > 0:
            inventory_options.append(discord.SelectOption(label=f"💣 Use Dynamite ({self.game.items['dynamite']} left)", value="dynamite", description="Explode 3x3 area"))
        
        inventory_select = discord.ui.Select(
            placeholder="🎒 Inventory & Items",
            options=inventory_options
        )
        inventory_select.callback = self.inventory_callback
        
        container_items.extend([
            discord.ui.ActionRow(blank_btn_1, up_btn, blank_btn_2),
            discord.ui.ActionRow(left_btn, down_btn, right_btn),
            discord.ui.ActionRow(surface_btn),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(inventory_select),
        ])
        
        # Add auto-reset toggle button for singleplayer
        if not self.game.is_shared:
            reset_status = "ON" if self.game.auto_reset_enabled else "OFF"
            reset_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if self.game.auto_reset_enabled else discord.ButtonStyle.secondary,
                label=f"🔄 Auto-Reset: {reset_status}",
            )
            reset_btn.callback = self.toggle_reset_callback
            container_items.extend([
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
                discord.ui.ActionRow(reset_btn),
            ])
        
        self.container1 = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0xFF6600),
        )
        
        self.add_item(self.container1)
        
        try:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=self, 
                attachments=[self.map_file]
            )
        except discord.errors.NotFound:
            return
        except Exception as e:
            print(f"[Mining] Error refreshing view: {e}")
            return
        
        # Save game state after action
        cog = interaction.client.get_cog("Mining")
        if cog:
            if self.game.is_shared and self.game.guild_id:
                if self.game.guild_id in cog.shared_worlds:
                    world_info = cog.shared_worlds[self.game.guild_id]
                    
                    player_key = str(self.user_id)
                    world_info["players"][player_key] = {
                        "x": self.game.x,
                        "y": self.game.y,
                        "depth": self.game.depth,
                        "energy": self.game.energy,
                        "max_energy": self.game.max_energy,
                        "last_energy_regen": self.game.last_energy_regen.isoformat(),
                        "pickaxe_level": self.game.pickaxe_level,
                        "backpack_capacity": self.game.backpack_capacity,
                        "inventory": self.game.inventory,
                        "coins": self.game.coins,
                        "items": self.game.items,  # Save personal items
                        "last_update": datetime.utcnow().isoformat()
                    }
                    
                    # Synchronize world data and structures
                    world_info["world_data"].map_data = self.game.map_data
                    world_info["world_data"].last_map_regen = self.game.last_map_regen
                    world_info["world_data"].ladders = self.game.ladders
                    world_info["world_data"].torches = self.game.torches
                    world_info["world_data"].portals = self.game.portals
                    world_info["world_data"].portal_counter = self.game.portal_counter
                    
                    self.game.other_players = {}
                    for other_user_id, other_data in world_info["players"].items():
                        if str(other_user_id) != str(self.user_id):
                            try:
                                user = interaction.client.get_user(int(other_user_id))
                                username = user.name if user else f"User {other_user_id}"
                            except:
                                username = f"User {other_user_id}"
                            
                            self.game.other_players[other_user_id] = {
                                "x": other_data["x"],
                                "y": other_data["y"],
                                "last_update": other_data.get("last_update", datetime.utcnow().isoformat()),
                                "username": username
                            }
            
            cog.save_data()


class Mining(commands.Cog):
    """⛏️ Mining - Procedurally generated 2D mining adventure"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Personal mode: {user_id: MiningGame}
        self.active_sessions = {}  # Track active mining sessions: {user_id: timestamp}
        self.shared_worlds = {}  # Shared mode: {guild_id: {world_data: MiningGame, players: {user_id: player_data}}}
        self.data_file = "data/mining_data.json"
        self.load_data()
    
    def load_data(self):
        """Load saved mining data"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load personal games (old format compatibility)
                    for user_id_str, game_data in data.get("games", {}).items():
                        user_id = int(user_id_str)
                        game = MiningGame.from_dict(game_data)
                        self.active_games[user_id] = game
                    
                    # Load shared worlds (new format)
                    for guild_id_str, world_data in data.get("shared_worlds", {}).items():
                        guild_id = int(guild_id_str)
                        # Shared world stores one map_data + multiple players
                        world_game = MiningGame.from_dict(world_data["world_data"])
                        self.shared_worlds[guild_id] = {
                            "world_data": world_game,
                            "players": world_data.get("players", {})
                        }
                        
            except Exception as e:
                print(f"[Mining] Error loading data: {e}")
                pass
    
    def save_data(self):
        """Save mining data"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # Serialize all personal games
        games_data = {}
        for user_id, game in self.active_games.items():
            games_data[str(user_id)] = game.to_dict()
        
        # Serialize shared worlds
        shared_worlds_data = {}
        for guild_id, world_info in self.shared_worlds.items():
            shared_worlds_data[str(guild_id)] = {
                "world_data": world_info["world_data"].to_dict(),
                "players": world_info["players"]
            }
        
        data = {
            "games": games_data,
            "shared_worlds": shared_worlds_data
        }
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        # NOTE: User storage recording removed from save_data() to avoid blocking.
        # User game states can be saved separately in async context if needed.
    
    @app_commands.command(name="mine", description="⛏️ Start a procedurally generated mining adventure!")
    async def mine_slash(self, interaction: discord.Interaction):
        """Start a mining adventure! (Slash version)"""
        await interaction.response.defer()
        

        if interaction.user.id in self.active_sessions:
            await interaction.followup.send(
                "❌ **You already have an active mining session!**\n"
                "Please finish or close your current session before starting a new one.\n"
                "💡 Sessions auto-close after 5 minutes of inactivity.",
                ephemeral=True
            )
            return
        
        self.active_sessions[interaction.user.id] = datetime.utcnow()
        
        await self.start_mining(interaction, interaction.user.id, interaction.guild.id if interaction.guild else None)
    
    @commands.command(name="ownermine")
    @commands.is_owner()
    async def ownermine_prefix(self, ctx: commands.Context):
        """🔧 Start mining in developer mode with extra features (owner only)"""
        await self.start_mining(ctx, ctx.author.id, ctx.guild.id if ctx.guild else None, dev_mode=True)
    
    async def start_mining(self, ctx, user_id: int, guild_id: int = None, dev_mode: bool = False):
        """Start or resume mining game (optionally in developer mode)"""
        # Get economy cog for coin sync
        economy_cog = self.bot.get_cog("Economy")
        
        # Check if server has shared mining enabled
        is_shared = False
        if guild_id:
            server_config_cog = self.bot.get_cog("ServerConfig")
            if server_config_cog:
                server_config = server_config_cog.get_server_config(guild_id)
                is_shared = server_config.get("shared_mining_world", False)
        
        if is_shared and guild_id:
            # SHARED WORLD MODE
            if guild_id not in self.shared_worlds:
                # Create new shared world for this guild
                world_game = MiningGame(user_id=0, guild_id=guild_id, is_shared=True)  # user_id=0 for world
                self.shared_worlds[guild_id] = {
                    "world_data": world_game,
                    "players": {}
                }
            
            world_info = self.shared_worlds[guild_id]
            world_game = world_info["world_data"]
            
            # Get or create player data in shared world
            if str(user_id) not in world_info["players"]:
                # New player in shared world
                economy_balance = economy_cog.get_balance(user_id) if economy_cog else 100
                world_info["players"][str(user_id)] = {
                    "x": 1, "y": -1, "depth": 0,
                    "energy": 60, "max_energy": 60,
                    "last_energy_regen": datetime.utcnow().isoformat(),
                    "pickaxe_level": 1, "backpack_capacity": 20,
                    "inventory": {}, "coins": economy_balance,
                    "items": {"ladder": 5, "portal": 2, "torch": 10}  # Personal items per player
                }
            
            player_data = world_info["players"][str(user_id)]
            
            # Create a game instance for this player (uses shared world map)
            game = MiningGame(user_id=user_id, seed=world_game.seed, guild_id=guild_id, is_shared=True)
            game.map_data = world_game.map_data  # Share the world map
            game.last_map_regen = world_game.last_map_regen
            
            # Share world structures (ladders, torches, portals)
            game.ladders = world_game.ladders
            game.torches = world_game.torches
            game.portals = world_game.portals
            game.portal_counter = world_game.portal_counter
            
            # Load player-specific data (including items!)
            game.items = player_data.get("items", {"ladder": 5, "portal": 2, "torch": 10})
            game.x = player_data["x"]
            game.y = player_data["y"]
            game.depth = player_data["depth"]
            game.energy = player_data["energy"]
            game.max_energy = player_data["max_energy"]
            game.last_energy_regen = datetime.fromisoformat(player_data["last_energy_regen"])
            game.pickaxe_level = player_data["pickaxe_level"]
            game.backpack_capacity = player_data["backpack_capacity"]
            game.inventory = player_data["inventory"]
            game.coins = player_data["coins"]
            
            # Sync coins with economy
            if economy_cog:
                game.coins = economy_cog.get_mine_coins(user_id)
                player_data["coins"] = game.coins
            
            # Update other players positions for rendering
            game.other_players = {}
            try:
                for other_user_id, other_data in world_info["players"].items():
                    if str(other_user_id) != str(user_id):
                        # Try to get username from Discord
                        try:
                            user_int = int(other_user_id)
                            user = self.bot.get_user(user_int)
                            username = user.name if user else f"User {other_user_id}"
                        except (ValueError, TypeError):
                            username = f"User {other_user_id}"
                        except Exception:
                            username = f"User {other_user_id}"
                        
                        game.other_players[other_user_id] = {
                            "x": other_data.get("x", 1),
                            "y": other_data.get("y", -1),
                            "last_update": other_data.get("last_update", datetime.utcnow().isoformat()),
                            "username": username
                        }
            except Exception:
                game.other_players = {}
            
        else:
            # PERSONAL MODE (original behavior)
            if user_id in self.active_games:
                game = self.active_games[user_id]
                # Sync coins with main economy on resume
                if economy_cog:
                    economy_balance = economy_cog.get_mine_coins(user_id)
                    game.coins = economy_balance
            else:
                # Create new game
                game = MiningGame(user_id, guild_id=guild_id, is_shared=False)
                
                # Sync coins with main economy
                if economy_cog:
                    economy_balance = economy_cog.get_mine_coins(user_id)
                    game.coins = economy_balance
                
                self.active_games[user_id] = game
        
        message = "🎮 Mining adventure!" + (" 🌍 Shared World!" if is_shared else "")
        if dev_mode:
            message += " 🔧 [Developer Mode]"
        await self.send_game_view(ctx, game, user_id, message, dev_mode=dev_mode)
    
    async def send_game_view(self, ctx, game: MiningGame, user_id: int, message: str, dev_mode: bool = False):
        """Send game view (optionally in developer mode)"""
        # Get bot instance - handle both Interaction and Context
        if hasattr(ctx, 'client'):  # Interaction
            bot = ctx.client
        elif hasattr(ctx, 'bot'):  # Context
            bot = ctx.bot
        else:
            bot = self.bot
        
        guild_id = ctx.guild.id if hasattr(ctx, 'guild') and ctx.guild else game.guild_id
        
        # Check for map regeneration
        if game.check_map_regeneration(bot=bot, guild_id=guild_id):
            message += "\n\n🔄 **Full map reset! (Ladders, portals, torches cleared. Inventory saved!)**"
        
        # Use OwnerMiningView if in developer mode, otherwise regular MiningView
        if dev_mode:
            view = await OwnerMiningView.create(game, user_id, self.bot, mining_cog=self)
        else:
            view = await MiningView.create(game, user_id, self.bot, mining_cog=self)
        
        if hasattr(ctx, 'response'):  # Slash command
            view.message = await ctx.followup.send(view=view, files=[view.map_file])
        else:  # Prefix command
            view.message = await ctx.send(view=view, files=[view.map_file])
        
        # Save game state
        self.save_data()


    async def show_shop(self, interaction: discord.Interaction, game: MiningGame):
        """Show shop interface"""
        if game.y != -1 or game.x not in [4, 5]:
            await interaction.response.send_message("**❌ You need to be at the shop to trade!**", ephemeral=True)
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