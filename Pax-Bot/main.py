import discord
from discord.ext import commands, tasks
import json
import re
import os
import random
import asyncio
from datetime import datetime, timedelta, timezone
import time
from deep_translator import GoogleTranslator
from db_service import db
from interaction_views import DuelView, GardenView, TeamView, TownView, ShopView, session_manager, PlayerShopInventorySelect
from discord import app_commands

DATA_FILE = "chi_data.json"
QUEST_DATA_FILE = "quests_data.json"
SHOP_DATA_FILE = "shop_data.json"
CHI_SHOP_DATA_FILE = "chi_shop_data.json"
BLACKLIST_FILE = "blacklisted_users.json"
TEAMS_DATA_FILE = "teams_data.json"
ARTIFACT_STATE_FILE = "artifact_state.json"
PET_CATALOG_FILE = "pet_catalog.json"
GARDENS_DATA_FILE = "gardens_data.json"
POTIONS_DATA_FILE = "potions_data.json"
ACHIEVEMENTS_DATA_FILE = "achievements_data.json"
PLAYER_SHOPS_FILE = "player_shops_data.json"
ERROR_LOG_FILE = "error_logs.json"
LOG_CONFIG_FILE = "log_config.json"
SERVER_CONFIG_FILE = "server_config.json"

# Server Configuration System (Multi-Guild)
def load_server_configs():
    """Load all server configurations from file"""
    try:
        with open(SERVER_CONFIG_FILE, "r") as f:
            data = json.load(f)
            
            # Migrate old single-guild format to multi-guild
            if "guilds" not in data:
                # Legacy format - migrate to new format
                if "guild_id" in data and data["guild_id"] is not None:
                    # Has a guild_id, migrate that guild's config
                    guild_id_str = str(data["guild_id"])
                    migrated = {
                        "guilds": {
                            guild_id_str: {
                                "channels": data.get("channels", {}),
                                "roles": data.get("roles", {}),
                                "features": data.get("features", {})
                            }
                        }
                    }
                    save_server_configs(migrated)
                    return migrated
                else:
                    # No guild_id, start fresh
                    return {"guilds": {}}
            return data
    except FileNotFoundError:
        return {"guilds": {}}

def save_server_configs(configs):
    """Save all server configurations to file"""
    with open(SERVER_CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=2)

def get_guild_config(guild_id):
    """Get configuration for a specific guild"""
    configs = load_server_configs()
    guild_id_str = str(guild_id)
    
    if guild_id_str not in configs["guilds"]:
        # Create default config for this guild
        configs["guilds"][guild_id_str] = {
            "channels": {
                "log_channel_id": None,
                "garden_channels": [],
                "duel_channels": [],
                "pet_channels": [],
                "updates_channel_id": None
            },
            "roles": {
                "admin_role_id": None,
                "quest_completer_role_id": None,
                "positive_role_id": None,
                "negative_role_id": None
            },
            "features": {
                "setup_complete": False
            }
        }
        save_server_configs(configs)
    
    return configs["guilds"][guild_id_str]

def update_guild_config(guild_id, updates):
    """Update configuration for a specific guild"""
    configs = load_server_configs()
    guild_id_str = str(guild_id)
    
    if guild_id_str not in configs["guilds"]:
        configs["guilds"][guild_id_str] = get_guild_config(guild_id)
    
    # Deep merge updates
    for key, value in updates.items():
        if isinstance(value, dict) and key in configs["guilds"][guild_id_str]:
            configs["guilds"][guild_id_str][key].update(value)
        else:
            configs["guilds"][guild_id_str][key] = value
    
    save_server_configs(configs)
    return configs["guilds"][guild_id_str]

def get_config_value(guild_id, path, default=None):
    """Get a config value for a guild using dot notation (e.g., 'channels.log_channel_id')"""
    config = get_guild_config(guild_id)
    keys = path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value if value is not None else default

# Load configs on startup
server_configs = load_server_configs()

# Error logging system
error_logs = []
error_log_counter = 0  # Global counter for unique IDs
MAX_ERROR_LOGS = 1000  # Keep errors for up to 1000 entries (auto-purge old ones)
ERROR_LOG_RETENTION_DAYS = 7  # Keep errors for 7 days

POSITIVE_WORDS = [
    "delightful","fabulous","supeletrcalifragilisticexpialidocious","magnificent","spectacular",
    "extraordinary","phenomenal","marvelous","splendid","exquisite","sublime","breathtaking",
    "resplendent","stupendous","miraculous","enchanting","captivating","mesmerizing","radiant",
    "luminous","effervescent","euphoric","transcendent","wondrous","quintessential","ethereal",
    "serendipitous","vivacious","ebullient","jubilant","illustrious","exemplary","distinguished",
    "remarkable","noteworthy","praiseworthy","commendable","admirable","laudable","meritorious",
    "benevolent","magnanimous","altruistic","philanthropic","gracious","cordial","amiable",
    "congenial","affable","genial","convivial","gregarious","effulgent","incandescent"
]

NEGATIVE_WORDS = [
    "motherfucker","bitch","asshole","idiot","stupid","jerk","dumb","loser","ugly","fool",
    "moron","lazy","nasty","worthless","scum","trash","pathetic","evil","mean","cruel",
    "vile","dirty","corrupt","coward","cheater","fraud","fake","greedy","selfish","bully",
    "shitty","twat","bastard","prick","loser","dickhead","jerkwad","imbecile","rat","snake",
    "ugly","punk","brat","savage","ignorant","cunt","slut","ratface","knobhead","buffoon",
    "clown","scoundrel"
]

SECRET_WORDS = {
    "bamboo": (10, 15),  # Rare discovery reward - reduced from 15-20
    "cookie": (10, 15),
    "cake": (10, 15),
    "pizza": (10, 15),
    "donut": (10, 15),
    "cinnamon": (10, 15),
}

POSITIVE_ROLE_ID = int(os.getenv("POSITIVE_Rgo OLE_ID", "1430936795637350480"))
NEGATIVE_ROLE_ID = int(os.getenv("NEGATIVE_ROLE_ID", "1430937317731995678"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1405984673057734748"))
PSY_DM_ID = int(os.getenv("PSY_DM_ID", "1382187068373074001"))

# LOG_CHANNEL_ID - REMOVED for universal deployment
# Logging now uses per-guild configuration via get_config_value(guild_id, "channels.log_channel_id")
# with fallback to first available text channel if not configured

QUEST_COMPLETER_ROLE_ID = 1430937039691735081

# CHI_EVENT_CHANNELS - REMOVED (now using guild config)
# ARTIFACT_CHANNELS - REMOVED (now using guild config)

CHI_EVENT_CLAIM_TIME = 60
CHI_EVENT_MIN_INTERVAL = 600
CHI_EVENT_MAX_INTERVAL = 1500
CHI_REBIRTH_THRESHOLD = 500000  # Strong currency - rebirth at 500k chi

# Artifact system configuration
ARTIFACT_SPAWN_MIN_HOURS = 1
ARTIFACT_SPAWN_MAX_HOURS = 12
ARTIFACT_CLAIM_TIME = 300  # 5 minutes

ARTIFACT_CONFIG = {
    "common": {
        "emojis": ["🪨", "🍃", "💧", "🪵", "⚪"],
        "names": ["Smooth Stone", "Bamboo Leaf", "Morning Dew", "Driftwood", "River Pebble"],
        "heal_percent": 10,
        "weight": 100
    },
    "rare": {
        "emojis": ["💎", "🔮", "⚡", "🌟", "💫", "🦋", "🌺", "🎐"],
        "names": ["Crystal Shard", "Oracle's Orb", "Thunder Strike", "Celestial Star", "Twilight Nova", "Spirit Butterfly", "Sakura Bloom", "Wind Chime"],
        "heal_percent": 25,
        "weight": 60
    },
    "legendary": {
        "emojis": ["👑", "🏆", "🔱", "⚔️", "🛡️", "🎭", "🗡️", "💍"],
        "names": ["Dragon Crown", "Champion's Trophy", "Neptune's Trident", "Excalibur Blade", "Aegis Shield", "Oni Mask", "Muramasa Katana", "Ring of Wisdom"],
        "heal_percent": 50,
        "weight": 35
    },
    "eternal": {
        "emojis": ["🌌", "✨", "🌠", "🔥", "💥", "🌀", "⭐", "🌊"],
        "names": ["Void Galaxy", "Stardust Essence", "Cosmic Meteor", "Phoenix Flame", "Big Bang Core", "Eternal Vortex", "North Star", "Tsunami Wave"],
        "heal_percent": 75,
        "weight": 5
    },
    "mythical": {
        "emojis": ["🐉", "🦅", "🐲", "🔯", "☯️"],
        "names": ["Azure Dragon Spirit", "Golden Phoenix Feather", "Jade Emperor's Scale", "Star of Destiny", "Yin-Yang Orb"],
        "heal_percent": 100,
        "weight": 1
    },
    "primal": {
        "emojis": ["🔥"],
        "names": ["Primal Artifact"],
        "heal_percent": 100,
        "weight": 0,  # Never spawns naturally - must be obtained through quest/event
        "description": "Ancient artifact required to unlock the Dragon pet",
        "realm": "Pandian Realm"
    }
}

# Garden system configuration
MAX_GARDEN_SEEDS = 200  # Base capacity for rare tier

GARDEN_TIERS = {
    "rare": {
        "name": "Pond Garden",
        "emoji": "🪷",
        "max_capacity": 200,
        "speed_bonus": 0.0,  # No bonus
        "upgrade_cost_chi": None,  # Starting tier
        "upgrade_cost_rebirths": None,
        "unlocks_seed": None
    },
    "legendary": {
        "name": "Chi Grove",
        "emoji": "🎋",
        "max_capacity": 250,  # +50 capacity
        "speed_bonus": 0.15,  # 15% faster growth
        "upgrade_cost_chi": 15000,
        "upgrade_cost_rebirths": 0,
        "unlocks_seed": "Moonshade"
    },
    "eternal": {
        "name": "Hépíng sēnlín",
        "emoji": "🌸",
        "max_capacity": 500,  # +250 more capacity (tier 3 holds 500 plants before reset)
        "speed_bonus": 0.30,  # 30% faster growth (cumulative)
        "upgrade_cost_chi": 30000,  # 30k chi upgrade cost
        "upgrade_cost_rebirths": 0,  # No rebirth cost
        "unlocks_seed": "Heartvine"
    },
    "rift": {
        "name": "Rift Garden",
        "emoji": "🌀",
        "max_capacity": 500,  # Same as eternal
        "speed_bonus": 0.60,  # 60% faster growth (30% base + 30% rift bonus)
        "upgrade_cost_chi": None,  # Can only upgrade via Rift Shard item
        "upgrade_cost_rebirths": None,  # Can only upgrade via Rift Shard item
        "unlocks_seed": None,
        "requires_item": "Rift Shard"  # Special upgrade requirement
    }
}

# Boss Battle System Configuration
BOSS_DATA = {
    "fang": {
        "name": "Fang of the Bamboo",
        "emoji": "🐉",
        "hp": 1000,
        "damage_min": 20,
        "damage_max": 80,
        "special": {
            "name": "Bamboo Strike",
            "description": "ignores defense 10% of the time",
            "chance": 0.10
        },
        "rewards": {
            "key": "Bamboo Key 🌿",
            "chi": 150,  # 50% increase from 100
            "artifact_chance": 0.0
        }
    },
    "ironhide": {
        "name": "Ironhide Titan",
        "emoji": "🪨",
        "hp": 1500,
        "damage_min": 30,
        "damage_max": 120,
        "special": {
            "name": "Iron Wall",
            "description": "heals 10% HP after 3 turns",
            "heal_percent": 0.10,
            "trigger_turn": 3
        },
        "rewards": {
            "key": "Titan Key ⚙️",
            "chi": 300,  # 50% increase from 200
            "artifact_chance": 0.0
        }
    },
    "emberclaw": {
        "name": "Emberclaw the Eternal",
        "emoji": "🔥",
        "hp": 2000,
        "damage_min": 50,
        "damage_max": 200,
        "special": {
            "name": "Infernal Roar",
            "description": "burns player for 25 HP over 3 turns",
            "burn_damage": 25,
            "burn_turns": 3
        },
        "rewards": {
            "key": "Eternal Key 🔥",
            "chi": 750,  # 50% increase from 500
            "artifact_chance": 0.05
        }
    },
    "rifter": {
        "name": "Rifter",
        "emoji": "🌀",
        "hp": 2500,
        "damage_min": 20,
        "damage_max": 250,
        "special": {
            "name": "Infernal Roar",
            "description": "burns player for 25 HP over 3 turns",
            "burn_damage": 25,
            "burn_turns": 3
        },
        "rewards": {
            "chi": 1500,
            "custom_item": "Rift Shard"
        }
    }
}


# NPC Training System Configuration
NPC_DATA = {
    "dummy": {
        "name": "Training Dummy",
        "emoji": "🎯",
        "hp": 1000,
        "damage_min": 0,
        "damage_max": 0,
        "description": "Practice target - it never attacks back!"
    },
    "easy": {
        "name": "Peaceful Panda",
        "emoji": "🐼",
        "hp": 200,
        "damage_min": 1,
        "damage_max": 10,
        "description": "A gentle sparring partner for beginners"
    },
    "medium": {
        "name": "Bamboo Warrior",
        "emoji": "🥋",
        "hp": 400,
        "damage_min": 1,
        "damage_max": 30,
        "description": "An experienced fighter looking for a challenge"
    },
    "hard": {
        "name": "Master Shifu",
        "emoji": "🦊",
        "hp": 600,
        "damage_min": 1,
        "damage_max": 50,
        "description": "A legendary master testing your true skills"
    }
}

# ============================================
# PANDA REALM NPC TRADING SYSTEM
# ============================================

# Panda Realm NPC Traders (Panda Town & Lushsoul Cavern)
PANDA_NPC_TRADERS = {
    "panda_town": {
        "merchant_mei": {
            "name": "Merchant Mei",
            "emoji": "👩‍💼",
            "location": "Panda Town Market",
            "buys": {  # What NPC buys from players
                "Peace Lily": 2,  # Item: chi offered
                "Peace Rose": 6,
                "Lavender": 10,
                "Sunbloom": 15,
                "Moonpetal": 20
            },
            "sells": {  # What NPC sells to players
                "Healing Potion": 50,  # Item: chi cost
                "Strength Potion": 150,
                "Speed Potion": 150
            },
            "dialogue": "Looking to trade? I buy seeds and sell potions!"
        },
        "blacksmith_bo": {
            "name": "Blacksmith Bo",
            "emoji": "🔨",
            "location": "Panda Town Forge",
            "buys": {
                "Iron Ore": 30,
                "Silver Ore": 50,
                "Gold Ore": 100,
                "Voidstone": 200
            },
            "sells": {
                "Iron Sword": 500,
                "Silver Shield": 800,
                "Golden Armor": 1500
            },
            "dialogue": "I work with ores and metal. Bring me materials, I'll pay fair prices!"
        }
    },
    "lushsoul_cavern": {
        "gem_dealer_jade": {
            "name": "Gem Dealer Jade",
            "emoji": "💎",
            "location": "Lushsoul Market",
            "buys": {
                "Ruby Quartz": 150,
                "Sapphire Shard": 200,
                "Emerald Fragment": 250,
                "Diamond Dust": 500
            },
            "sells": {
                "Gemcutting Kit": 1000,
                "Crystal Magnifier": 1500
            },
            "dialogue": "Gems and crystals are my specialty. I'll trade you fair!"
        },
        "ore_merchant_rex": {
            "name": "Ore Merchant Rex",
            "emoji": "⛏️",
            "location": "Lushsoul Mining District",
            "buys": {
                "Iron Ore": 35,
                "Silver Ore": 55,
                "Gold Ore": 110,
                "Voidstone": 220,
                "Titanium Ore": 300
            },
            "sells": {
                "Advanced Pickaxe": 2000,
                "Mining Helmet": 1200,
                "Ore Detector": 1800
            },
            "dialogue": "I buy all kinds of ores. Got something to sell?"
        }
    }
}


# Lushsoul Cavern Mining & Town System
LUSHARMORY_ITEMS = {
    "A1": {
        "name": "Pickaxe",
        "emoji": "⛏️",
        "cost": 50,
        "cost_type": "chi",
        "description": "Essential tool for mining in Lushsoul Cavern",
        "type": "tool"
    },
    "A2": {
        "name": "Virestone Armor",
        "emoji": "🛡️",
        "cost": 50,
        "cost_type": "Virestone Ore",
        "description": "Sturdy armor providing +5% protection in duels",
        "protection": 5,
        "type": "armor"
    },
    "A3": {
        "name": "Hemalyte Armor",
        "emoji": "⚔️",
        "cost": 75,
        "cost_type": "Hemalyte Ore",
        "description": "Advanced armor providing +15% protection in duels",
        "protection": 15,
        "type": "armor"
    },
    "A4": {
        "name": "Eclipsite Armor",
        "emoji": "🌑",
        "cost": 100,
        "cost_type": "Eclipsite Ore",
        "description": "Legendary armor providing +25% protection in duels",
        "protection": 25,
        "type": "armor"
    },
    "A5": {
        "name": "Lushcore Blade",
        "emoji": "🗡️",
        "cost": 30,
        "cost_type": "Lushcore Gem",
        "description": "A blade forged from Lushcore - deals 80-120 damage",
        "damage_min": 80,
        "damage_max": 120,
        "type": "weapon"
    },
    "A6": {
        "name": "Voidstone Hammer",
        "emoji": "🔨",
        "cost": 40,
        "cost_type": "Voidstone",
        "description": "Heavy hammer from the void - deals 100-150 damage",
        "damage_min": 100,
        "damage_max": 150,
        "type": "weapon"
    },
    "A7": {
        "name": "Echo Lantern",
        "emoji": "🏮",
        "cost": 25,
        "cost_type": "Echo Quartz",
        "description": "Illuminates hidden treasures - +10% chance to find rare items when mining",
        "mining_bonus": 10,
        "type": "tool"
    },
    "A8": {
        "name": "Aether Pendant",
        "emoji": "💠",
        "cost": 50,
        "cost_type": "Aether Dust",
        "description": "Mystical pendant - heals 100 HP in duels",
        "healing": 100,
        "type": "consumable"
    }
}

MINING_ORES = {
    "Virestone Ore": {"emoji": "💚", "chance": 50, "rarity": "Common"},
    "Hemalyte Ore": {"emoji": "🔴", "chance": 20, "rarity": "Uncommon"},
    "Eclipsite Ore": {"emoji": "⚫", "chance": 0, "rarity": "Legendary", "eclipse_only": True}
}

MINING_ITEMS = {
    "Stone": {"emoji": "🪨", "chance": 100, "rarity": "Common"},
    "Gravel": {"emoji": "⬜", "chance": 85, "rarity": "Common"},
    "Limestone": {"emoji": "🪶", "chance": 70, "rarity": "Common"},
    "Echo Quartz": {"emoji": "💎", "chance": 40, "rarity": "Uncommon"},
    "Lushcore Gem": {"emoji": "💚", "chance": 25, "rarity": "Rare"},
    "Aether Dust": {"emoji": "✨", "chance": 20, "rarity": "Rare"},
    "Rustroot": {"emoji": "🌿", "chance": 30, "rarity": "Uncommon"},
    "Fossil Fragments": {"emoji": "🦴", "chance": 15, "rarity": "Rare"},
    "Voidstone": {"emoji": "🌑", "chance": 10, "rarity": "Epic"}
}

NPC_TRADERS = {
    "Minerva": {
        "emoji": "👩‍🔬",
        "description": "Ore specialist who trades plants for Echo Quartz",
        "trades": {
            "Lavender": {"cost": 10, "gives": 3, "gives_item": "Echo Quartz"},
            "Silverdew": {"cost": 5, "gives": 5, "gives_item": "Echo Quartz"},
            "Peace Lily": {"cost": 20, "gives": 2, "gives_item": "Echo Quartz"}
        }
    },
    "Bonetooth": {
        "emoji": "🦴",
        "description": "Collector of rare materials",
        "trades": {
            "Fossil Fragments": {"cost": 15, "gives": 8, "gives_item": "Echo Quartz"},
            "Voidstone": {"cost": 5, "gives": 15, "gives_item": "Echo Quartz"},
            "Rustroot": {"cost": 10, "gives": 4, "gives_item": "Echo Quartz"}
        }
    },
    "Whiskerbell": {
        "emoji": "🐱",
        "description": "Pet food merchant",
        "trades": {
            "Echo Quartz": {"cost": 5, "gives": 3, "gives_item": "Bamboo Biscuits"},
            "Echo Quartz": {"cost": 10, "gives": 5, "gives_item": "Zen Tea"},
            "Echo Quartz": {"cost": 15, "gives": 2, "gives_item": "Spirit Cake"}
        }
    },
    "Quartzbeard": {
        "emoji": "🧙",
        "description": "Master of stone and gem",
        "trades": {
            "Stone": {"cost": 50, "gives": 1, "gives_item": "Echo Quartz"},
            "Gravel": {"cost": 30, "gives": 1, "gives_item": "Echo Quartz"},
            "Limestone": {"cost": 25, "gives": 2, "gives_item": "Echo Quartz"}
        }
    }
}

# ============================================
# PET SYSTEM - FULL OVERHAUL
# ============================================

# Pet Data: 5 Pets with unique attacks and garden bonuses
PET_DATA = {
    "ox": {
        "name": "Ox",
        "emoji": "🐂",
        "tier": 5,  # 5th best
        "base_hp": 1000,
        "price": 43400,  # Reduced by 30% for strong currency balance
        "description": "Sturdy and reliable, the Ox provides consistent garden boosts",
        "garden_bonus": {
            "chi_yield": 0.10,  # +10% chi from harvests
            "growth_speed": 0.05,  # +5% faster growth
            "rare_drop": 0.05  # +5% rare ingredient chance
        },
        "attacks": {
            "headbutt": {
                "name": "Headbutt",
                "emoji": "💥",
                "base_damage": 80,
                "damage_range": (70, 90),
                "description": "Simple but effective headbutt attack",
                "special_effect": None
            },
            "charge": {
                "name": "Bull Charge",
                "emoji": "⚡",
                "base_damage": 100,
                "damage_range": (80, 120),
                "description": "Powerful charge with 30% chance to stun for 1 turn",
                "special_effect": {"type": "stun", "chance": 0.30, "duration": 1}
            },
            "stomp": {
                "name": "Earth Stomp",
                "emoji": "🌍",
                "base_damage": 60,
                "damage_range": (50, 70),
                "description": "Ground-shaking stomp that reduces enemy damage by 20% for 2 turns",
                "special_effect": {"type": "weaken", "amount": 0.20, "duration": 2}
            }
        }
    },
    "snake": {
        "name": "Snake",
        "emoji": "🐍",
        "tier": 4,  # 4th best
        "base_hp": 2000,
        "price": 87500,  # Reduced by 30%
        "description": "Swift and cunning, the Snake enhances rare ingredient drops",
        "garden_bonus": {
            "chi_yield": 0.15,  # +15% chi
            "growth_speed": 0.10,  # +10% faster growth
            "rare_drop": 0.15  # +15% rare ingredient chance
        },
        "attacks": {
            "bite": {
                "name": "Venomous Bite",
                "emoji": "🦷",
                "base_damage": 90,
                "damage_range": (75, 105),
                "description": "Poisonous bite that deals 15 HP per turn for 3 turns",
                "special_effect": {"type": "poison", "damage": 15, "duration": 3}
            },
            "constrict": {
                "name": "Constrict",
                "emoji": "🌀",
                "base_damage": 70,
                "damage_range": (60, 80),
                "description": "Squeezes opponent, preventing healing for 2 turns",
                "special_effect": {"type": "healing_block", "duration": 2}
            },
            "hiss": {
                "name": "Intimidating Hiss",
                "emoji": "😱",
                "base_damage": 50,
                "damage_range": (40, 60),
                "description": "Frightening hiss with 40% chance to make opponent flee (skip turn)",
                "special_effect": {"type": "fear", "chance": 0.40, "duration": 1}
            }
        }
    },
    "tiger": {
        "name": "Tiger",
        "emoji": "🐯",
        "tier": 3,  # 3rd best
        "base_hp": 3000,
        "price": 175000,  # Reduced by 30%
        "description": "Fierce and fast, the Tiger dramatically speeds up garden growth",
        "garden_bonus": {
            "chi_yield": 0.20,  # +20% chi
            "growth_speed": 0.25,  # +25% faster growth!
            "rare_drop": 0.10  # +10% rare ingredient chance
        },
        "attacks": {
            "claw": {
                "name": "Razor Claw",
                "emoji": "🗡️",
                "base_damage": 120,
                "damage_range": (100, 140),
                "description": "Vicious claw swipe with 20% lifesteal",
                "special_effect": {"type": "lifesteal", "percent": 0.20}
            },
            "pounce": {
                "name": "Lightning Pounce",
                "emoji": "⚡",
                "base_damage": 150,
                "damage_range": (120, 180),
                "description": "Aggressive pounce that deals more damage but takes 30% recoil",
                "special_effect": {"type": "recoil", "percent": 0.30}
            },
            "roar": {
                "name": "Thunderous Roar",
                "emoji": "🔊",
                "base_damage": 80,
                "damage_range": (70, 90),
                "description": "Terrifying roar that boosts next attack by 50%",
                "special_effect": {"type": "attack_boost", "percent": 0.50, "next_turn": True}
            }
        }
    },
    "panda": {
        "name": "Panda",
        "emoji": "🐼",
        "tier": 2,  # 2nd best
        "base_hp": 4000,
        "price": 350000,  # Reduced by 30%
        "description": "Balanced and harmonious, the Panda provides excellent all-around garden benefits",
        "garden_bonus": {
            "chi_yield": 0.30,  # +30% chi!
            "growth_speed": 0.20,  # +20% faster growth
            "rare_drop": 0.20  # +20% rare ingredient chance
        },
        "attacks": {
            "bamboo_strike": {
                "name": "Bamboo Strike",
                "emoji": "🎋",
                "base_damage": 140,
                "damage_range": (120, 160),
                "description": "Powerful strike with 100% accuracy",
                "special_effect": None
            },
            "zen_heal": {
                "name": "Zen Healing",
                "emoji": "💚",
                "base_damage": 0,
                "damage_range": (0, 0),
                "description": "Heals 200 HP and removes all status effects",
                "special_effect": {"type": "heal_cleanse", "amount": 200}
            },
            "chi_blast": {
                "name": "Chi Blast",
                "emoji": "✨",
                "base_damage": 110,
                "damage_range": (90, 130),
                "description": "Energy blast that also heals you for 30% of damage dealt",
                "special_effect": {"type": "lifesteal", "percent": 0.30}
            }
        }
    },
    "dragon": {
        "name": "Dragon",
        "emoji": "🐉",
        "tier": 1,  # BEST
        "base_hp": 5000,
        "price": 525000,  # Reduced by 30%
        "description": "Legendary and powerful, the Dragon maximizes all garden benefits",
        "garden_bonus": {
            "chi_yield": 0.50,  # +50% chi!!!
            "growth_speed": 0.30,  # +30% faster growth!
            "rare_drop": 0.30  # +30% rare ingredient chance!
        },
        "attacks": {
            "fire_breath": {
                "name": "Dragon Fire Breath",
                "emoji": "🔥",
                "base_damage": 160,
                "damage_range": (140, 180),
                "description": "Scorching flames that burn for 20 HP per turn until healed",
                "special_effect": {"type": "burn", "damage": 20, "duration": 999}  # Until healed
            },
            "wing_slash": {
                "name": "Wing Slash",
                "emoji": "🌪️",
                "base_damage": 180,
                "damage_range": (150, 210),
                "description": "Devastating wing attack with 25% chance to critical (2x damage)",
                "special_effect": {"type": "critical", "chance": 0.25, "multiplier": 2.0}
            },
            "dragon_roar": {
                "name": "Dragon's Roar",
                "emoji": "⚡",
                "base_damage": 130,
                "damage_range": (110, 150),
                "description": "Primal roar that reduces all enemy damage by 40% for 3 turns",
                "special_effect": {"type": "weaken", "amount": 0.40, "duration": 3}
            }
        }
    }
}

# Pet Food System
PET_FOOD = {
    # Ox Food (Primary: Grass, Rare: Hay)
    "grass": {
        "name": "Grass",
        "emoji": "🌾",
        "healing": 100,
        "price": 50,
        "description": "Fresh grass for herbivores",
        "primary_for": "ox"
    },
    "hay": {
        "name": "Hay",
        "emoji": "🌿",
        "healing": 200,
        "price": 200,
        "description": "Premium dried hay",
        "primary_for": "ox"
    },
    
    # Snake Food (Primary: Mice)
    "mice": {
        "name": "Mice",
        "emoji": "🐭",
        "healing": 200,
        "price": 150,
        "description": "Fresh mice for carnivores",
        "primary_for": "snake"
    },
    
    # Tiger Food (Primary: Raw Meat)
    "raw_meat": {
        "name": "Raw Meat",
        "emoji": "🥩",
        "healing": 300,
        "price": 250,
        "description": "Fresh raw meat for predators",
        "primary_for": "tiger"
    },
    
    # Panda Food (Primary: Fish, Rare: Bamboo Stock)
    "fish": {
        "name": "Fish",
        "emoji": "🐟",
        "healing": 400,
        "price": 300,
        "description": "Fresh fish for pandas",
        "primary_for": "panda"
    },
    "bamboo_stock": {
        "name": "Bamboo Stock",
        "emoji": "🎋",
        "healing": 500,
        "price": 500,
        "description": "Premium bamboo stalks",
        "primary_for": "panda"
    },
    
    # Dragon Food (Primary: Dragon Fruit)
    "dragon_fruit": {
        "name": "Dragon Fruit",
        "emoji": "🐉",
        "healing": 1000,
        "price": 1000,
        "description": "Legendary fruit for dragons",
        "primary_for": "dragon"
    },
    
    # Generic Pet Food (existing items)
    "bamboo_biscuits": {
        "name": "Bamboo Biscuits",
        "emoji": "🍪",
        "healing": 150,
        "price": 350,
        "description": "Crunchy bamboo-flavored treats"
    },
    "zen_tea": {
        "name": "Zen Tea",
        "emoji": "🍵",
        "healing": 300,
        "price": 840,
        "description": "Soothing tea that restores energy"
    },
    "spirit_cake": {
        "name": "Spirit Cake",
        "emoji": "🍰",
        "healing": 500,
        "price": 1750,
        "description": "Delicious cake infused with chi energy"
    }
}

# ============================================
# WINTER WONDERLAND UPDATE - POTION SYSTEM
# ============================================

# Potion Catalog with Effects
POTION_CATALOG = {
    # === BASE POTIONS ===
    "healing_potion": {
        "name": "Healing Potion",
        "emoji": "🧪",
        "rarity": "common",
        "description": "Restores 100 HP instantly",
        "effect_type": "instant_heal",
        "effect_value": 100,
        "duration": None,
        "throwable": False,
        "pre_duel_only": False
    },
    "strength_potion": {
        "name": "Strength Potion",
        "emoji": "💪",
        "rarity": "uncommon",
        "description": "Increases attack damage by 10% for the entire duel (use before battle)",
        "effect_type": "damage_boost",
        "effect_value": 0.10,  # 10% boost
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": True
    },
    "speed_potion": {
        "name": "Speed Potion",
        "emoji": "⚡",
        "rarity": "uncommon",
        "description": "25% chance to attack twice per turn, but all attacks deal 30% less damage",
        "effect_type": "speed_boost",
        "effect_value": {"double_attack_chance": 0.25, "damage_penalty": 0.30},
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": False
    },
    "poison_potion": {
        "name": "Poison Potion",
        "emoji": "☠️",
        "rarity": "uncommon",
        "description": "Throw at enemy! Deals 5 HP per attack they make. 20% chance to backfire!",
        "effect_type": "poison",
        "effect_value": {"damage_per_attack": 5, "backfire_chance": 0.20},
        "duration": "duel",
        "throwable": True,
        "pre_duel_only": False
    },
    "resistance_potion": {
        "name": "Resistance Potion",
        "emoji": "🛡️",
        "rarity": "rare",
        "description": "Reduces incoming damage by 45% for the entire duel",
        "effect_type": "damage_reduction",
        "effect_value": 0.45,
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": False
    },
    "regeneration_potion": {
        "name": "Regeneration Potion",
        "emoji": "💚",
        "rarity": "rare",
        "description": "Heal 5 HP every time you attack (use during duel)",
        "effect_type": "regen_on_attack",
        "effect_value": 5,
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": False
    },
    
    # === RARE/MYTHIC POTIONS ===
    "phoenix_elixir": {
        "name": "Phoenix Elixir",
        "emoji": "🔥",
        "rarity": "epic",
        "description": "If you are knocked out in combat, revive once with 50% HP!",
        "effect_type": "revive",
        "effect_value": 0.50,  # 50% HP on revive
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": False
    },
    "berserker_fury": {
        "name": "Berserker's Fury",
        "emoji": "😤",
        "rarity": "epic",
        "description": "Gain 50% damage boost but cannot use healing items!",
        "effect_type": "berserker",
        "effect_value": {"damage_boost": 0.50, "no_healing": True},
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": True
    },
    "shadow_veil": {
        "name": "Shadow Veil",
        "emoji": "🌑",
        "rarity": "legendary",
        "description": "30% chance to dodge attacks + 20% counter chance",
        "effect_type": "dodge_counter",
        "effect_value": {"dodge_chance": 0.30, "counter_chance": 0.20},
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": False
    },
    "dragon_blessing": {
        "name": "Dragon's Blessing",
        "emoji": "🐉",
        "rarity": "mythic",
        "description": "Immune to all status effects + 15% boost to all stats",
        "effect_type": "dragon_blessing",
        "effect_value": {"stat_boost": 0.15, "status_immunity": True},
        "duration": "duel",
        "throwable": False,
        "pre_duel_only": True
    }
}

# Ingredient Catalog
INGREDIENT_CATALOG = {
    # === GARDEN INGREDIENTS (Common/Uncommon/Rare) ===
    "moonpetal": {"emoji": "🌙", "rarity": "common", "source": "garden", "description": "Glowing petals harvested under moonlight"},
    "winterleaf": {"emoji": "❄️", "rarity": "common", "source": "garden", "description": "Frost-touched leaves from winter gardens"},
    "sunbloom": {"emoji": "🌻", "rarity": "common", "source": "garden", "description": "Bright flowers that capture sunlight"},
    "moonflower": {"emoji": "🌙", "rarity": "uncommon", "source": "garden", "description": "Mystical flower that only blooms at night"},
    "chi_blossom": {"emoji": "🌸", "rarity": "rare", "source": "garden", "description": "Rare blossom infused with pure chi energy"},
    "mistmoss": {"emoji": "🌫️", "rarity": "uncommon", "source": "garden", "description": "Mysterious moss that grows in mist"},
    "starherb": {"emoji": "⭐", "rarity": "uncommon", "source": "garden", "description": "Rare herb that only blooms at night"},
    "emberroot": {"emoji": "🔥", "rarity": "rare", "source": "garden", "description": "Fiery root that burns but never chars"},
    
    # === MINING INGREDIENTS (Uncommon/Rare) ===
    "crystal_shard": {"emoji": "💎", "rarity": "uncommon", "source": "mining", "description": "Shimmering crystal from deep caverns"},
    "iron_ore": {"emoji": "⚙️", "rarity": "common", "source": "mining", "description": "Sturdy ore for crafting"},
    "shadow_stone": {"emoji": "🌑", "rarity": "rare", "source": "mining", "description": "Dark stone infused with shadow energy"},
    "phoenix_coal": {"emoji": "🔥", "rarity": "epic", "source": "mining", "description": "Coal that never stops burning"},
    
    # === BOSS DROP INGREDIENTS (Epic/Mythic) ===
    "bamboo_essence": {"emoji": "🎋", "rarity": "epic", "source": "boss:fang", "description": "Pure essence from Fang of the Bamboo"},
    "titan_core": {"emoji": "⚙️", "rarity": "epic", "source": "boss:ironhide", "description": "Hardened core from Ironhide Titan"},
    "eternal_flame": {"emoji": "🔥", "rarity": "mythic", "source": "boss:emberclaw", "description": "Eternal fire from Emberclaw"},
    
    # === NPC TRADER INGREDIENTS (Rare) ===
    "dragon_scale": {"emoji": "🐉", "rarity": "legendary", "source": "npc_trade", "description": "Mystical scale from ancient dragons"},
    "void_essence": {"emoji": "🌀", "rarity": "legendary", "source": "npc_trade", "description": "Essence from the void itself"},
    "liquid_light": {"emoji": "✨", "rarity": "rare", "source": "npc_trade", "description": "Bottled light from fallen stars"}
}

# Crafting Recipes
POTION_RECIPES = {
    # === COMMON POTIONS ===
    "healing_potion": {
        "ingredients": {
            "moonpetal": 3,
            "sunbloom": 2
        },
        "chi_cost": 35,  # Reduced by 30%
        "brew_time": 60,  # seconds
        "success_rate": 0.95,
        "tier": "common",
        "requires_workstation": None
    },
    
    # === UNCOMMON POTIONS ===
    "strength_potion": {
        "ingredients": {
            "emberroot": 2,
            "iron_ore": 3,
            "sunbloom": 1
        },
        "chi_cost": 105,  # Reduced by 30%
        "brew_time": 120,
        "success_rate": 0.85,
        "tier": "uncommon",
        "requires_workstation": "garden"
    },
    "speed_potion": {
        "ingredients": {
            "moonflower": 2,
            "crystal_shard": 2,
            "winterleaf": 3
        },
        "chi_cost": 105,  # Reduced by 30%
        "brew_time": 120,
        "success_rate": 0.85,
        "tier": "uncommon",
        "requires_workstation": "garden"
    },
    "poison_potion": {
        "ingredients": {
            "shadow_stone": 1,
            "mistmoss": 3,
            "emberroot": 1
        },
        "chi_cost": 140,  # Reduced by 30%
        "brew_time": 180,
        "success_rate": 0.80,
        "tier": "uncommon",
        "requires_workstation": "garden"
    },
    
    # === RARE POTIONS ===
    "resistance_potion": {
        "ingredients": {
            "titan_core": 1,  # Boss drop
            "iron_ore": 5,
            "moonflower": 3
        },
        "chi_cost": 350,  # Reduced by 30%
        "brew_time": 300,
        "success_rate": 0.75,
        "tier": "rare",
        "requires_workstation": "alchemy_lab"
    },
    "regeneration_potion": {
        "ingredients": {
            "bamboo_essence": 1,  # Boss drop
            "chi_blossom": 3,
            "moonflower": 5
        },
        "chi_cost": 350,  # Reduced by 30%
        "brew_time": 300,
        "success_rate": 0.75,
        "tier": "rare",
        "requires_workstation": "alchemy_lab"
    },
    
    # === EPIC POTIONS ===
    "phoenix_elixir": {
        "ingredients": {
            "eternal_flame": 1,  # Mythic boss drop
            "phoenix_coal": 2,
            "liquid_light": 3
        },
        "chi_cost": 1400,  # Reduced by 30%
        "brew_time": 600,
        "success_rate": 0.60,
        "tier": "epic",
        "requires_workstation": "master_cauldron"
    },
    "berserker_fury": {
        "ingredients": {
            "titan_core": 2,
            "emberroot": 5,
            "shadow_stone": 3
        },
        "chi_cost": 1050,  # Reduced by 30%
        "brew_time": 500,
        "success_rate": 0.65,
        "tier": "epic",
        "requires_workstation": "master_cauldron"
    },
    
    # === LEGENDARY POTIONS ===
    "shadow_veil": {
        "ingredients": {
            "void_essence": 2,
            "shadow_stone": 5,
            "chi_blossom": 5
        },
        "chi_cost": 2100,  # Reduced by 30%
        "brew_time": 800,
        "success_rate": 0.50,
        "tier": "legendary",
        "requires_workstation": "master_cauldron"
    },
    
    # === MYTHIC POTIONS ===
    "dragon_blessing": {
        "ingredients": {
            "dragon_scale": 3,
            "eternal_flame": 2,
            "void_essence": 2,
            "liquid_light": 5
        },
        "chi_cost": 7000,  # Reduced by 30%
        "brew_time": 1200,
        "success_rate": 0.40,
        "tier": "mythic",
        "requires_workstation": "master_cauldron"
    }
}

GARDEN_SHOP_ITEMS = {
    "bundles": {
        "Sickle Bundle": {
            "cost": 75000,
            "emoji": "⚔️",
            "description": "Premium gardening package with legendary tools",
            "realm": "Pandian Realm",
            "contents": {
                "Eternal Sickle": 1,
                "Heartvine": 20,
                "Fertilizer Bag": 1
            }
        },
        "Heroic Bundle": {
            "cost": 60000,
            "emoji": "🏆",
            "description": "Hero's gardening kit for serious farmers",
            "realm": "Pandian Realm",
            "contents": {
                "Heroic Hoe": 1,
                "Moonshade": 20,
                "Fertilizer Bag": 1
            }
        },
        "Scythe Bundle": {
            "cost": 40000,
            "emoji": "🗡️",
            "description": "Complete package for advanced gardening",
            "realm": "Pandian Realm",
            "contents": {
                "Silverdew Scythe": 1,
                "Silverdew": 20,
                "Fertilizer Bag": 1
            }
        }
    },
    "tools": {
        "Watering Bucket": {
            "cost": 525,
            "emoji": "🪣",
            "description": "Water your plants every 24 hours to keep them growing",
            "realm": "Pandian Realm"
        },
        "Golden Watering Can": {
            "cost": 2100,
            "emoji": "✨",
            "description": "A luxurious watering can that never runs out",
            "realm": "Pandian Realm"
        },
        "Fertilizer Bag": {
            "cost": 7000,
            "emoji": "🌿",
            "description": "Reduces growth time by 25% for all plants",
            "realm": "Pandian Realm"
        },
        "Eternal Sickle": {
            "cost": 35000,
            "emoji": "⚔️",
            "description": "Legendary harvesting tool (cosmetic)",
            "realm": "Pandian Realm"
        },
        "Heroic Hoe": {
            "cost": 28000,
            "emoji": "🏆",
            "description": "Hero's cultivation tool (cosmetic)",
            "realm": "Pandian Realm"
        },
        "Silverdew Scythe": {
            "cost": 20000,
            "emoji": "🗡️",
            "description": "Advanced harvesting scythe (cosmetic)",
            "realm": "Pandian Realm"
        }
    },
    "seeds": {
        "Peace Lily": {
            "cost": 350,
            "emoji": "🌸",
            "harvest_chi": 21,  # Rebalanced to 40% (was 53, now 630 chi/hr)
            "grow_time_minutes": 2,
            "description": "A delicate flower that brings peace (630 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Peace Rose": {
            "cost": 1220,
            "emoji": "🌹",
            "harvest_chi": 73,  # Rebalanced to 40% (was 183, now 1095 chi/hr)
            "grow_time_minutes": 4,
            "description": "A beautiful rose that radiates tranquility (1095 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Lavender": {
            "cost": 1890,
            "emoji": "💜",
            "harvest_chi": 114,  # Rebalanced to 40% (was 284, now 974 chi/hr)
            "grow_time_minutes": 7,
            "description": "Soothing lavender with calming properties (974 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Jasmine Plant": {
            "cost": 2940,
            "emoji": "🤍",
            "harvest_chi": 176,  # Rebalanced to 40% (was 441, now 1056 chi/hr)
            "grow_time_minutes": 10,
            "description": "Fragrant jasmine that fills the air with serenity (1056 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Cherry Blossom": {
            "cost": 4200,
            "emoji": "🌸",
            "harvest_chi": 252,  # Rebalanced to 40% (was 630, now 1008 chi/hr)
            "grow_time_minutes": 15,
            "description": "Majestic cherry blossoms symbolizing renewal (1008 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Silverdew": {
            "cost": 14000,
            "emoji": "💧",
            "harvest_chi": 840,  # Rebalanced to 40% (was 2100, now 1120 chi/hr)
            "grow_time_minutes": 45,
            "description": "Rare mystical flowers that glisten with morning dew (1120 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Moonshade": {
            "cost": 28000,
            "emoji": "🌙",
            "harvest_chi": 1680,  # Rebalanced to 40% (was 4200, now 1120 chi/hr)
            "grow_time_minutes": 90,
            "description": "Legendary plants that bloom under moonlight (1120 chi/hr)",
            "realm": "Pandian Realm"
        },
        "Heartvine": {
            "cost": 35000,
            "emoji": "💚",
            "harvest_chi": 2100,  # Rebalanced to 40% (was 5250, now 700 chi/hr)
            "grow_time_minutes": 180,
            "description": "Ancient vines that pulse with life force (700 chi/hr)",
            "realm": "Pandian Realm"
        }
    }
}

# Garden Tool System - Offsets economy nerf with craftable/purchasable percentage boosts
GARDEN_TOOLS = {
    "basic_hoe": {
        "name": "Basic Hoe",
        "tier": "Basic",
        "emoji": "🔨",
        "harvest_bonus_percent": 10,  # +10% harvest chi
        "speed_bonus_percent": 0,
        "flat_chi_bonus": 0,
        "cost_chi": 5000,
        "cost_rebirths": 0,
        "description": "A simple farming tool (+10% harvest chi)",
        "acquisition": "shop"
    },
    "steel_rake": {
        "name": "Steel Rake",
        "tier": "Basic",
        "emoji": "⛏️",
        "harvest_bonus_percent": 10,
        "speed_bonus_percent": 5,  # +5% faster growth
        "flat_chi_bonus": 0,
        "cost_chi": 8000,
        "cost_rebirths": 0,
        "description": "Sturdy steel rake (+10% harvest, +5% speed)",
        "acquisition": "shop"
    },
    "silverdew_scythe": {
        "name": "Silverdew Scythe",
        "tier": "Advanced",
        "emoji": "🗡️",
        "harvest_bonus_percent": 20,  # +20% harvest chi
        "speed_bonus_percent": 10,  # +10% faster growth
        "flat_chi_bonus": 0,
        "crafting_recipe": {
            "Silverdew Artifact": 1,
            "Silver Ore": 5,
            "Bamboo": 10
        },
        "description": "Mystical harvesting scythe (+20% harvest, +10% speed)",
        "acquisition": "crafting"
    },
    "eternal_planters": {
        "name": "Eternal Planters",
        "tier": "Advanced",
        "emoji": "🌱",
        "harvest_bonus_percent": 25,  # +25% harvest chi
        "speed_bonus_percent": 15,  # +15% faster growth
        "flat_chi_bonus": 0,
        "crafting_recipe": {
            "Eternal Shard": 1,
            "Gold Ore": 3,
            "Heartstone": 2
        },
        "description": "Blessed planting boxes (+25% harvest, +15% speed)",
        "acquisition": "crafting"
    },
    "moonstone_trowel": {
        "name": "Moonstone Trowel",
        "tier": "Elite",
        "emoji": "✨",
        "harvest_bonus_percent": 35,  # +35% harvest chi
        "speed_bonus_percent": 15,  # +15% faster growth
        "flat_chi_bonus": 100,  # +100 flat chi per harvest
        "crafting_recipe": {
            "Moonstone Artifact": 1,
            "Platinum Ore": 2,
            "Dragon Scale": 1
        },
        "description": "Legendary cultivation tool (+35% harvest, +15% speed, +100 flat chi)",
        "acquisition": "crafting"
    },
    "rift_gardener": {
        "name": "Rift Gardener's Glove",
        "tier": "Mythic",
        "emoji": "🌀",
        "harvest_bonus_percent": 50,  # +50% harvest chi
        "speed_bonus_percent": 25,  # +25% faster growth
        "flat_chi_bonus": 250,  # +250 flat chi per harvest
        "special_effect": "5% chance for bonus seed on harvest",
        "crafting_recipe": {
            "Rift Shard": 2,
            "Cosmic Dust": 5,
            "Void Crystal": 1
        },
        "description": "Mythical glove from the void (+50% harvest, +25% speed, +250 chi, bonus seed chance)",
        "acquisition": "crafting"
    },
    "bamboo_spade": {
        "name": "Bamboo Spade",
        "tier": "Basic",
        "emoji": "🎋",
        "harvest_bonus_percent": 10,
        "speed_bonus_percent": 0,
        "flat_chi_bonus": 0,
        "description": "Lightweight bamboo tool (+10% harvest chi)",
        "acquisition": "artifact_search",
        "rarity_weight": 30  # Common drop from artifact searches
    },
    "chi_infused_watering_can": {
        "name": "Chi-Infused Watering Can",
        "tier": "Advanced",
        "emoji": "💧",
        "harvest_bonus_percent": 20,
        "speed_bonus_percent": 10,
        "flat_chi_bonus": 50,
        "description": "Magical watering can (+20% harvest, +10% speed, +50 chi)",
        "acquisition": "artifact_search",
        "rarity_weight": 10  # Rare drop from artifact searches
    },
    "dragon_cultivator": {
        "name": "Dragon Cultivator",
        "tier": "Elite",
        "emoji": "🐉",
        "harvest_bonus_percent": 35,
        "speed_bonus_percent": 20,
        "flat_chi_bonus": 150,
        "description": "Dragon-blessed farming tool (+35% harvest, +20% speed, +150 chi)",
        "acquisition": "artifact_search",
        "rarity_weight": 3  # Very rare drop from artifact searches
    }
}

ITEM_QUESTS = [
    {
        "id": 1,
        "name": "Quest One: Warmth for Pax",
        "dialogue": "{user}, Pax is cold bring him a coat",
        "item_needed": "Panda Coat"
    },
    {
        "id": 2,
        "name": "Quest Two: Bamboo Blade",
        "dialogue": "Hello {user} can you please go get me my sword? Its made of the same matieral I eat.",
        "item_needed": "Bamboo Sword"
    },
    {
        "id": 3,
        "name": "Quest Three: Captain of the Sea",
        "dialogue": "YO HO YO HO A PIRATES LIFE FOR ME... Oh ahoy there {user} what be bringin ye to this part of the sea? Quests ey? Well I have a challenge for you... I need my pirate hat, without it I'm just a buccaneer, but with it? Oh with it I am the captian of the sea!!!!",
        "item_needed": "Pirate Hat"
    }
]

# Tutorial Quest System - Teaches users how to use the bot!
TUTORIAL_QUESTS = [
    "1️⃣ First Steps: Spread Positivity! 🌸\nSay 5 positive words in chat to earn chi!\n**Reward:** 75 chi",
    "2️⃣ Create Your Garden 🪷\nUse `P!garden` to start your chi farming journey!\n**Reward:** 150 chi",
    "3️⃣ Join the Team Spirit 🐼\nCreate a team with `P!team create <name>` or join one!\n**Reward:** 225 chi",
    "4️⃣ Challenge a Friend ⚔️\nStart your first duel with `P!duel @user`!\n**Reward:** 300 chi",
    "5️⃣ Upgrade Your Team Base 🏠\nAdd a decoration to your team base with `P!team base decorate`!\n**Reward:** 450 chi",
    "6️⃣ Grow Your Garden 🎋\nUpgrade your garden tier with `P!garden upgrade`!\n**Reward:** 600 chi",
    "7️⃣ Claim an Artifact ✨\nFind and claim an artifact when one spawns with `P!find artifact`!\n**Reward:** 750 chi",
    "8️⃣ Make a Trade 🤝\nTrade chi or artifacts with another user using `P!trade`!\n**Reward:** 900 chi",
    "9️⃣ Defeat a Boss 🐉\nComplete a boss battle with `P!boss`!\n**Reward:** 1200 chi",
    "🔟 Tutorial Master 🏆\nComplete all 9 tutorial quests above!\n**Reward:** 1500 chi"
]

MONTH_THEMES = {
    "10": ("Halloween", [
        "1️⃣ Haunted Bamboo Forest\nReact with 30 unique emojis across chats this month. 👻💀🕷️",
        "2️⃣ Panda Story Spinner\nWrite a spooky story (100+ words) with panda characters. 🕸️📖",
        "3️⃣ Costume Craze\nUpdate your nickname/profile with Halloween theme. 👹🎭",
        "4️⃣ Trick-or-Treat Trickster\nGive a friend a panda riddle or puzzle. 🕷️🍬",
        "5️⃣ Creepy Collector\nShare 5 Halloween-themed panda memes. 🕷️📸",
        "6️⃣ Community Helper\nAssist 3 members meaningfully this month. 🐼💚",
        "7️⃣ Ghost Whisperer\nWelcome a new member warmly. 👻🤝",
        "8️⃣ Emoji Overload\nSend a panda/Halloween-themed emoji message (20+ emojis). 🎃🕸️",
        "9️⃣ Pandaween Creator\nSuggest a Halloween server idea/event. 🕸️✨",
        "🔟 Bamboo Shadow Hunt\nFind and tag hidden 'ghost pandas' in server images/emoji hunts."
    ]),
    "11": ("Thanksgiving", [
        "1️⃣ Panda Gratitude\nThank 3 different members this month. 🦃💛",
        "2️⃣ Recipe Share\nShare a Thanksgiving-themed panda snack/dish. 🍗🥧",
        "3️⃣ Event Master\nParticipate in any Bamboo Forest event actively. 🏆🎉",
        "4️⃣ Helping Hand\nAssist 3 members with advice/guidance. 🐼💚",
        "5️⃣ Emoji Gratitude Flood\nSend a positive emoji message (20+ emojis). 😊🦃",
        "6️⃣ Story Teller\nWrite a Thanksgiving story featuring pandas. 📖🍁",
        "7️⃣ Community Creator\nSuggest a new Thanksgiving server activity. 🕸️✨",
        "8️⃣ Collector\nShare 5 safe-for-work Thanksgiving memes/images. 🦃📸",
        "9️⃣ Engage!\nGet 5+ reactions on a helpful post. 👍✨",
        "🔟 New Member Welcome\nHelp a new member feel welcome. 🤝🐼"
    ]),
    "12": ("Winter", [
        "1️⃣ Winter Emoji Hunt\nReact with 30 winter/panda-themed emojis. ❄️⛄🎄",
        "2️⃣ Holiday Story Spinner\nWrite a winter holiday story (100+ words). 📖❄️",
        "3️⃣ Event Master\nParticipate actively in server events. 🏆🎉",
        "4️⃣ Gift Giver\nSuggest creative holiday gift ideas for the server. 🎁✨",
        "5️⃣ Winter Costume\nUpdate profile/nickname with winter theme. ⛄❄️",
        "6️⃣ Emoji Overload\nSend winter-themed emoji message (20+ emojis). 🎄⛄❄️",
        "7️⃣ Collector\nShare 5 winter/holiday panda memes/pics. 🖼️❄️",
        "8️⃣ Community Helper\nAssist 3 members meaningfully. 🐼💚",
        "9️⃣ Server Event Creator\nSuggest a holiday event. ✨🎄",
        "🔟 New Member Welcome\nWelcome a new member warmly. 🤝🐼"
    ])
}

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix=["P!"], intents=intents, help_command=None)

# Slash command /help (does not interfere with prefix help)
@bot.tree.command(name="help", description="Show help for the bot")
async def help_slash(interaction: discord.Interaction):
    await interaction.response.send_message("This is the slash command help! Use !help for the prefix version.")

async def log_event(event_type: str, description: str, guild, color: discord.Color = discord.Color.blue()):
    """Log important bot events to the designated log channel
    
    Args:
        event_type: Type of event being logged
        description: Event description
        guild: Guild object or guild_id (int/str)
        color: Embed color (default: blue)
    """
    try:
        # Get guild object if guild_id was passed
        if isinstance(guild, (int, str)):
            guild_obj = bot.get_guild(int(guild))
            if not guild_obj:
                print(f"Failed to log event: Guild {guild} not found")
                return
        else:
            guild_obj = guild
        
        guild_id = str(guild_obj.id)
        
        # Try to get log channel from guild config
        log_channel_id = get_config_value(guild_id, "channels.log_channel_id")
        log_channel = None
        
        if log_channel_id:
            log_channel = bot.get_channel(int(log_channel_id))
        
        # Fallback: Use first available text channel with send permissions
        if not log_channel:
            log_channel = next(
                (ch for ch in guild_obj.text_channels 
                 if ch.permissions_for(guild_obj.me).send_messages), 
                None
            )
        
        # Send log embed if we have a valid channel
        if log_channel and isinstance(log_channel, discord.TextChannel):
            embed = discord.Embed(
                title=f"📋 {event_type}",
                description=description,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Panda Bot Event Log")
            await log_channel.send(embed=embed)
        else:
            print(f"No valid log channel found for guild {guild_id}")
            
    except Exception as e:
        print(f"Failed to log event: {e}")

command_cooldowns = {}
chi_cooldowns = {}
team_base_cooldowns = {}  # Format: {user_id: {activity_type: timestamp}}
COMMAND_COOLDOWN = 30
CHI_COOLDOWN = 30
FEED_COOLDOWN = 60
ADMIN_BYPASS_COMMANDS = ["stop", "start", "blacklist"]
COOLDOWN_COMMANDS = ["claim", "buy", "rebirth", "feed"]
pax_active = True
event_active = False
event_claimer = None
current_event_message = None
active_duel = None
active_training = None
active_npc_training = None  # Format: {"player_id": int, "npc_key": str, "npc_hp": int, "player_hp": int, "player_max_hp": int, "turn": str, "channel_id": int, "guild_id": int, "start_time": datetime}
active_team_event = None  # Format: {"name": str, "registered_teams": [team_ids]}
active_boss_battle = None  # Format: {"player_id": int, "boss_key": str, "boss_hp": int, "player_hp": int, "player_max_hp": int, "turn": int, "burn_turns": 0, "channel_id": int, "guild_id": int, "start_time": datetime}
current_event_type = "positive"
next_event_time = None
chi_party_messages = []
chi_party_active = False
chi_party_tokens = []
chi_party_claims = {}
chi_party_last_spawn = 0
active_food_event = None
active_rift_battle = None  # Format: {"boss_hp": int, "boss_max_hp": int, "participants": {}, "spawned_at": datetime, "channel_id": int}
rift_event_participants = []  # Users who used P!enter during rift event
CHI_PARTY_THRESHOLD = 5
CHI_PARTY_WINDOW = 10
CHI_PARTY_TOKEN_COUNT = 5
CHI_PARTY_COOLDOWN = 300

# ============================================
# POTION ENGINE - Effect Processing System
# ============================================

def get_active_potion_effects(user_id: str, duel_context: dict) -> dict:
    """Get all active potion effects for a user in the current duel"""
    effects = duel_context.get("potion_effects", {}).get(user_id, {})
    return effects

def apply_potion_effect(user_id: str, potion_key: str, duel_context: dict):
    """Apply a potion effect to a user in the current duel"""
    if "potion_effects" not in duel_context:
        duel_context["potion_effects"] = {}
    if user_id not in duel_context["potion_effects"]:
        duel_context["potion_effects"][user_id] = {}
    
    potion = POTION_CATALOG.get(potion_key)
    if not potion:
        return False
    
    duel_context["potion_effects"][user_id][potion_key] = {
        "effect_type": potion["effect_type"],
        "effect_value": potion["effect_value"],
        "active": True
    }
    return True

def calculate_damage_with_potions(base_damage: int, attacker_id: str, defender_id: str, duel_context: dict) -> tuple:
    """Calculate final damage after applying all potion effects
    Returns: (final_damage, combat_log_messages list)"""
    damage = base_damage
    messages = []
    
    # Get effects for both players
    attacker_effects = get_active_potion_effects(str(attacker_id), duel_context)
    defender_effects = get_active_potion_effects(str(defender_id), duel_context)
    
    # ATTACKER EFFECTS
    # Strength Potion: +10% damage
    if "strength_potion" in attacker_effects:
        boost = int(damage * 0.10)
        damage += boost
        messages.append(f"💪 Strength potion boosted attack by {boost} damage!")
    
    # Berserker's Fury: +50% damage
    if "berserker_fury" in attacker_effects:
        boost = int(damage * 0.50)
        damage += boost
        messages.append(f"😤 Berserker's Fury unleashed +{boost} damage!")
    
    # Speed Potion: -30% damage penalty
    if "speed_potion" in attacker_effects:
        penalty = int(damage * 0.30)
        damage -= penalty
        messages.append(f"⚡ Speed cost: -{penalty} damage")
    
    # Dragon's Blessing: +15% all stats
    if "dragon_blessing" in attacker_effects:
        boost = int(damage * 0.15)
        damage += boost
        messages.append(f"🐉 Dragon's Blessing empowered the attack (+{boost})!")
    
    # DEFENDER EFFECTS
    # Resistance Potion: -45% damage reduction
    if "resistance_potion" in defender_effects:
        reduction = int(damage * 0.45)
        damage -= reduction
        messages.append(f"🛡️ Resistance potion blocked {reduction} damage!")
    
    # Shadow Veil: 30% dodge chance
    if "shadow_veil" in defender_effects:
        if random.random() < 0.30:
            messages.append(f"🌑 **DODGED!** Shadow Veil helped evade the attack!")
            return (0, messages)
    
    # Ensure damage doesn't go negative
    damage = max(1, damage)
    
    return (damage, messages)

def process_on_attack_effects(attacker_id: str) -> str:
    """Process effects that trigger when attacker attacks
    Returns: message string (empty if no effects)"""
    if str(attacker_id) not in chi_data:
        return ""
    
    inventory = chi_data[str(attacker_id)].get("inventory", {})
    messages = []
    
    # Regeneration Potion: Heal 5 HP per attack (passive effect, just show message)
    if inventory.get("regeneration_potion_active", 0) > 0:
        messages.append(f"💚 Regeneration active!")
    
    return "\n".join(messages) if messages else ""

def process_poison_effect(victim_id: str) -> str:
    """Process poison damage on victim (5 HP if poisoned)
    Returns: message string (empty if not poisoned)"""
    if str(victim_id) not in chi_data:
        return ""
    
    inventory = chi_data[str(victim_id)].get("inventory", {})
    
    # Poison Potion: 5 HP per attack
    if inventory.get("poison_potion_active", 0) > 0:
        return f"☠️ Poison dealt 5 damage!"
    
    return ""

def check_speed_double_attack(attacker_id: str, duel_context: dict) -> bool:
    """Check if speed potion triggers double attack (25% chance)"""
    attacker_effects = get_active_potion_effects(str(attacker_id), duel_context)
    
    if "speed_potion" in attacker_effects:
        if random.random() < 0.25:
            return True
    return False

def check_shadow_counter(defender_id: str, duel_context: dict) -> bool:
    """Check if shadow veil triggers counter attack (20% chance after dodge)"""
    defender_effects = get_active_potion_effects(str(defender_id), duel_context)
    
    if "shadow_veil" in defender_effects:
        if random.random() < 0.20:
            return True
    return False

def check_phoenix_revive(user_id: str) -> bool:
    """Check if phoenix elixir can revive the user and consume it
    Returns: True if revived, False otherwise"""
    if str(user_id) not in chi_data:
        return False
    
    inventory = chi_data[str(user_id)].get("inventory", {})
    
    # Phoenix Elixir: One-time auto-revive at 50% HP
    if inventory.get("phoenix_elixir", 0) > 0:
        # Consume the elixir
        inventory["phoenix_elixir"] -= 1
        if inventory["phoenix_elixir"] <= 0:
            del inventory["phoenix_elixir"]
        save_data()
        return True
    
    return False

def check_berserker_healing_block(user_id: str, duel_context: dict) -> bool:
    """Check if berserker fury is blocking healing"""
    user_effects = get_active_potion_effects(str(user_id), duel_context)
    
    if "berserker_fury" in user_effects:
        return True
    return False

def check_status_immunity(user_id: str, duel_context: dict) -> bool:
    """Check if dragon's blessing provides status immunity"""
    user_effects = get_active_potion_effects(str(user_id), duel_context)
    
    if "dragon_blessing" in user_effects:
        return True
    return False

def throw_poison_potion(thrower_id: str, target_id: str, duel_context: dict) -> tuple:
    """Throw poison potion at target with backfire chance
    Returns: (success bool, backfired bool, message)"""
    # 20% backfire chance
    if random.random() < 0.20:
        # Backfire! Apply to thrower instead
        apply_potion_effect(str(thrower_id), "poison_potion", duel_context)
        thrower = discord.utils.get(bot.get_all_members(), id=int(thrower_id))
        message = f"☠️ *Oh no {thrower.mention} tried to throw a poison potion but dropped it on themselves...*"
        return (False, True, message)
    else:
        # Success! Apply to target
        # Check if target has status immunity
        if check_status_immunity(str(target_id), duel_context):
            message = f"🐉 Dragon's Blessing blocked the poison!"
            return (False, False, message)
        
        apply_potion_effect(str(target_id), "poison_potion", duel_context)
        message = f"☠️ Poison potion successfully thrown! Target will take 5 HP per attack!"
        return (True, False, message)

# ============================================
# BREWING/CRAFTING SYSTEM
# ============================================

def check_has_ingredients(user_id: str, recipe: dict) -> tuple:
    """Check if user has required ingredients for recipe
    Returns: (has_all bool, missing_ingredients dict)"""
    user_inventory = chi_data.get(str(user_id), {}).get("inventory", {})
    missing = {}
    
    for ingredient_key, amount_needed in recipe["ingredients"].items():
        amount_have = user_inventory.get(ingredient_key, 0)
        if amount_have < amount_needed:
            missing[ingredient_key] = amount_needed - amount_have
    
    return (len(missing) == 0, missing)

def consume_ingredients(user_id: str, recipe: dict):
    """Remove ingredients from user inventory"""
    user_inventory = chi_data.get(str(user_id), {}).get("inventory", {})
    
    for ingredient_key, amount in recipe["ingredients"].items():
        if ingredient_key in user_inventory:
            user_inventory[ingredient_key] -= amount
            if user_inventory[ingredient_key] <= 0:
                del user_inventory[ingredient_key]

def add_potion_to_inventory(user_id: str, potion_key: str, amount: int = 1):
    """Add potion to user's inventory"""
    if str(user_id) not in chi_data:
        chi_data[str(user_id)] = {"chi": 0, "rebirths": 0, "inventory": {}}
    if "inventory" not in chi_data[str(user_id)]:
        chi_data[str(user_id)]["inventory"] = {}
    
    inventory = chi_data[str(user_id)]["inventory"]
    inventory[potion_key] = inventory.get(potion_key, 0) + amount

def get_potion_count(user_id: str, potion_key: str) -> int:
    """Get count of specific potion in inventory"""
    return chi_data.get(str(user_id), {}).get("inventory", {}).get(potion_key, 0)

def use_potion_from_inventory(user_id: str, potion_key: str) -> bool:
    """Remove one potion from inventory
    Returns: True if potion was removed, False if not enough"""
    count = get_potion_count(user_id, potion_key)
    if count <= 0:
        return False
    
    chi_data[str(user_id)]["inventory"][potion_key] -= 1
    if chi_data[str(user_id)]["inventory"][potion_key] <= 0:
        del chi_data[str(user_id)]["inventory"][potion_key]
    return True

def get_user_potions(user_id: str) -> dict:
    """Get all potions in user's inventory
    Returns: {potion_key: count}"""
    inventory = chi_data.get(str(user_id), {}).get("inventory", {})
    potions = {}
    
    for item_key, count in inventory.items():
        if item_key in POTION_CATALOG:
            potions[item_key] = count
    
    return potions

def get_user_ingredients(user_id: str) -> dict:
    """Get all ingredients in user's inventory
    Returns: {ingredient_key: count}"""
    inventory = chi_data.get(str(user_id), {}).get("inventory", {})
    ingredients = {}
    
    for item_key, count in inventory.items():
        if item_key in INGREDIENT_CATALOG:
            ingredients[item_key] = count
    
    return ingredients

try:
    with open(DATA_FILE, "r") as f:
        chi_data = json.load(f)
except FileNotFoundError:
    chi_data = {}

try:
    with open(TEAMS_DATA_FILE, "r") as f:
        teams_data = json.load(f)
    if "teams" not in teams_data:
        teams_data["teams"] = {}
    if "user_teams" not in teams_data:
        teams_data["user_teams"] = {}
    if "pending_invites" not in teams_data:
        teams_data["pending_invites"] = {}
    
    # Migrate existing teams to include new fields (backward compatibility)
    migration_needed = False
    for team_id, team in teams_data["teams"].items():
        if "base_color" not in team:
            team["base_color"] = "white"
            migration_needed = True
        if "decorations" not in team:
            team["decorations"] = []
            migration_needed = True
        if "gym_equipment" not in team:
            team["gym_equipment"] = []
            migration_needed = True
        if "team_score" not in team:
            team["team_score"] = 0
            migration_needed = True
        if "allies" not in team:
            team["allies"] = []
            migration_needed = True
        if "enemies" not in team:
            team["enemies"] = []
            migration_needed = True
    
    # Persist migration changes to disk
    if migration_needed:
        with open(TEAMS_DATA_FILE, "w") as f:
            json.dump(teams_data, f, indent=2)
except FileNotFoundError:
    teams_data = {"teams": {}, "user_teams": {}, "pending_invites": {}}


try:
    with open(QUEST_DATA_FILE, "r") as f:
        quest_data = json.load(f)
except FileNotFoundError:
    quest_data = {"quests": [], "month": "", "user_progress": {}}

try:
    with open(SHOP_DATA_FILE, "r") as f:
        shop_data = json.load(f)
except FileNotFoundError:
    shop_data = {
        "items": [
            {"name": "Nitro (DM Psy)", "cost": 1, "type": "default"},
            {"name": "1 Level", "cost": 1, "type": "default"},
            {"name": "Custom Role", "cost": 2, "type": "default"},
            {"name": "4 Levels", "cost": 2, "type": "default"},
            {"name": "Discord Decoration Pack", "cost": 5, "type": "default"},
            {"name": "7 Levels", "cost": 5, "type": "default"},
            {"name": "15 Free Levels", "cost": 10, "type": "default"}
        ]
    }
    with open(SHOP_DATA_FILE, "w") as f:
        json.dump(shop_data, f, indent=4)

try:
    with open(CHI_SHOP_DATA_FILE, "r") as f:
        chi_shop_data = json.load(f)
except FileNotFoundError:
    chi_shop_data = {
        "items": [
            {"name": "Bamboo Sword", "cost": 105, "type": "default"},  # Reduced by 30%
            {"name": "Pax's Tea", "cost": 140, "type": "default"},  # Reduced by 30%
            {"name": "Katana", "cost": 1050, "type": "default"},  # Reduced by 30%
            {"name": "Pirate Hat", "cost": 18, "type": "default"}  # Reduced by 30%
        ]
    }
    with open(CHI_SHOP_DATA_FILE, "w") as f:
        json.dump(chi_shop_data, f, indent=4)

try:
    with open(BLACKLIST_FILE, "r") as f:
        blacklisted_users = json.load(f)
except FileNotFoundError:
    blacklisted_users = []

try:
    with open(ARTIFACT_STATE_FILE, "r") as f:
        artifact_state = json.load(f)
except FileNotFoundError:
    artifact_state = {"active_artifact": None, "next_spawn_at": None, "last_spawn_at": None}
    with open(ARTIFACT_STATE_FILE, "w") as f:
        json.dump(artifact_state, f, indent=2)

try:
    with open(PET_CATALOG_FILE, "r") as f:
        pet_catalog = json.load(f)
except FileNotFoundError:
    pet_catalog = {"pets": [], "foods": []}
    with open(PET_CATALOG_FILE, "w") as f:
        json.dump(pet_catalog, f, indent=2)

try:
    with open(GARDENS_DATA_FILE, "r") as f:
        gardens_data = json.load(f)
    if "gardens" not in gardens_data:
        gardens_data["gardens"] = {}
    if "garden_event" not in gardens_data:
        gardens_data["garden_event"] = {"active": False, "end_time": None}
except FileNotFoundError:
    gardens_data = {"gardens": {}, "garden_event": {"active": False, "end_time": None}}
    with open(GARDENS_DATA_FILE, "w") as f:
        json.dump(gardens_data, f, indent=2)

try:
    with open(POTIONS_DATA_FILE, "r") as f:
        potions_data = json.load(f)
except FileNotFoundError:
    potions_data = {"ingredients": {}, "potions": [], "recipes": []}
    with open(POTIONS_DATA_FILE, "w") as f:
        json.dump(potions_data, f, indent=2)

try:
    with open(ACHIEVEMENTS_DATA_FILE, "r") as f:
        achievements_data = json.load(f)
except FileNotFoundError:
    achievements_data = {"achievements": [], "categories": {}, "tiers": {}}
    with open(ACHIEVEMENTS_DATA_FILE, "w") as f:
        json.dump(achievements_data, f, indent=2)

try:
    with open(PLAYER_SHOPS_FILE, "r") as f:
        player_shops_data = json.load(f)
except FileNotFoundError:
    player_shops_data = {"shops": {}, "next_shop_id": 1, "global_sales": 0}
    with open(PLAYER_SHOPS_FILE, "w") as f:
        json.dump(player_shops_data, f, indent=2)

try:
    with open(ERROR_LOG_FILE, "r") as f:
        data = json.load(f)
        raw_logs = data.get("logs", [])
        
        # Prune logs older than 7 days with defensive validation
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=ERROR_LOG_RETENTION_DAYS)
        error_logs = []
        for log in raw_logs:
            try:
                # Validate required fields exist
                if not isinstance(log, dict):
                    continue
                if "timestamp" not in log or "id" not in log:
                    continue
                
                # Parse timestamp and check age
                timestamp = datetime.fromisoformat(log["timestamp"])
                if timestamp > cutoff_date:
                    error_logs.append(log)
            except (ValueError, KeyError, TypeError):
                # Skip malformed entries
                continue
        
        # Set counter to max existing ID to prevent collisions
        if error_logs:
            try:
                max_id = max(int(log["id"][1:]) for log in error_logs if log.get("id", "L0").startswith("L"))
                error_log_counter = max_id
            except (ValueError, KeyError):
                error_log_counter = 0
        else:
            error_log_counter = 0
        
        # Persist cleaned logs immediately
        with open(ERROR_LOG_FILE, "w") as f_out:
            json.dump({"logs": error_logs, "counter": error_log_counter}, f_out, indent=2)
            
except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
    print(f"⚠️ Error log initialization issue (using safe defaults): {e}")
    error_logs = []
    error_log_counter = 0

try:
    with open(LOG_CONFIG_FILE, "r") as f:
        log_config = json.load(f)
        # Validate structure
        if not isinstance(log_config, dict):
            raise ValueError("Invalid config structure")
        if "error_channel_id" not in log_config:
            log_config["error_channel_id"] = None
except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
    print(f"⚠️ Log config initialization issue (using safe defaults): {e}")
    log_config = {"error_channel_id": None}
    try:
        with open(LOG_CONFIG_FILE, "w") as f:
            json.dump(log_config, f, indent=2)
    except Exception:
        pass  # Don't crash if we can't write defaults

# Define save functions first (needed for migration)
def save_data():
    """Save chi data to JSON file (database writes happen async)"""
    with open(DATA_FILE, "w") as f:
        json.dump(chi_data, f, indent=4)

def save_quests():
    with open(QUEST_DATA_FILE, "w") as f:
        json.dump(quest_data, f, indent=4)

def save_shop():
    with open(SHOP_DATA_FILE, "w") as f:
        json.dump(shop_data, f, indent=4)

def save_teams():
    """Save teams data to JSON file (database writes happen async)"""
    with open(TEAMS_DATA_FILE, "w") as f:
        json.dump(teams_data, f, indent=4)

def save_artifact_state():
    with open(ARTIFACT_STATE_FILE, "w") as f:
        json.dump(artifact_state, f, indent=2)

def save_chi_shop():
    with open(CHI_SHOP_DATA_FILE, "w") as f:
        json.dump(chi_shop_data, f, indent=4)

def save_blacklist():
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(blacklisted_users, f, indent=4)

def save_gardens():
    """Save gardens data to JSON file (database writes happen async)"""
    with open(GARDENS_DATA_FILE, "w") as f:
        json.dump(gardens_data, f, indent=2)

def save_pet_catalog():
    with open(PET_CATALOG_FILE, "w") as f:
        json.dump(pet_catalog, f, indent=2)

def save_potions():
    with open(POTIONS_DATA_FILE, "w") as f:
        json.dump(potions_data, f, indent=2)

def save_player_shops():
    """Save player shops data to JSON file"""
    with open(PLAYER_SHOPS_FILE, "w") as f:
        json.dump(player_shops_data, f, indent=2)

def _save_error_logs_sync():
    """Synchronous save for error logs (called via asyncio.to_thread)"""
    with open(ERROR_LOG_FILE, "w") as f:
        json.dump({"logs": error_logs, "counter": error_log_counter}, f, indent=2)

async def save_error_logs():
    """Save error logs to JSON file (non-blocking)"""
    await asyncio.to_thread(_save_error_logs_sync)

def _save_log_config_sync():
    """Synchronous save for log config (called via asyncio.to_thread)"""
    with open(LOG_CONFIG_FILE, "w") as f:
        json.dump(log_config, f, indent=2)

async def save_log_config():
    """Save log configuration to JSON file (non-blocking)"""
    await asyncio.to_thread(_save_log_config_sync)

def cleanup_old_logs():
    """Remove logs older than ERROR_LOG_RETENTION_DAYS"""
    global error_logs
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=ERROR_LOG_RETENTION_DAYS)
    error_logs = [
        log for log in error_logs 
        if datetime.fromisoformat(log["timestamp"]) > cutoff_date
    ]

def log_error(error_msg, command=None, user=None, message_link=None, error_code=None):
    """Log an error with timestamp, unique ID, and details (fire-and-forget save)"""
    global error_logs, error_log_counter
    
    error_log_counter += 1
    
    error_entry = {
        "id": f"L{error_log_counter}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": error_msg,
        "command": command,
        "user": str(user) if user else None,
        "message_link": message_link,
        "error_code": error_code
    }
    
    error_logs.append(error_entry)
    
    # Cleanup old logs first
    cleanup_old_logs()
    
    # Keep only last MAX_ERROR_LOGS entries
    if len(error_logs) > MAX_ERROR_LOGS:
        error_logs = error_logs[-MAX_ERROR_LOGS:]
    
    # Save to file (fire-and-forget, non-blocking)
    try:
        asyncio.create_task(save_error_logs())
    except RuntimeError:
        # No event loop running (shouldn't happen, but just in case)
        pass
    
    return error_entry

# Database dual-write helpers (async)
async def sync_user_to_db(user_id: int):
    """Sync user data from chi_data to database"""
    if not db.pool or not bot.guilds:
        return
    
    try:
        user_id_str = str(user_id)
        if user_id_str not in chi_data:
            return
        
        user_data = chi_data[user_id_str]
        # Use primary guild (first guild) for now - TODO: make guild-aware
        guild_id = bot.guilds[0].id
        await db.create_or_update_user(
            user_id=user_id,
            guild_id=guild_id,
            chi=user_data.get("chi", 0),
            rebirths=user_data.get("rebirths", 0),
            milestones_claimed=user_data.get("milestones_claimed", []),
            mini_quests=user_data.get("mini_quests", []),
            active_pet=user_data.get("active_pet")
        )
    except Exception as e:
        print(f"⚠️ Failed to sync user {user_id} to database: {e}")

async def sync_team_to_db(team_id: int):
    """Sync team data to database"""
    if not db.pool or not bot.guilds:
        return
    
    try:
        team_id_str = str(team_id)
        teams = teams_data.get("teams", {})
        if team_id_str not in teams:
            return
        
        team = teams[team_id_str]
        
        # Use primary guild (first guild) for now - TODO: make guild-aware
        guild_id = bot.guilds[0].id
        # Update team chi
        await db.update_team_chi(team_id=team_id, guild_id=guild_id, team_chi=team.get("team_chi", 0))
    except Exception as e:
        print(f"⚠️ Failed to sync team {team_id} to database: {e}")

async def sync_garden_to_db(user_id: int):
    """Sync garden data from gardens_data to database"""
    if not db.pool or not bot.guilds:
        return
    
    try:
        user_id_str = str(user_id)
        gardens = gardens_data.get("gardens", {})
        if user_id_str not in gardens:
            return
        
        garden = gardens[user_id_str]
        
        # Validate plants data - accept both old and new formats
        valid_plants = []
        if "plants" in garden:
            for plant in garden["plants"]:
                # Skip corrupted string data
                if isinstance(plant, str):
                    print(f"⚠️ Skipping corrupted plant (string) for user {user_id}")
                    continue
                
                # Validate dict structure - accept old ("seed") or new ("name") format
                if isinstance(plant, dict):
                    has_name = "name" in plant or "seed" in plant
                    has_time = "planted_at" in plant or "mature_at" in plant
                    
                    if has_name and has_time:
                        valid_plants.append(plant)
                    else:
                        print(f"⚠️ Skipping invalid plant (missing required fields) for user {user_id}")
            
            garden["plants"] = valid_plants
        
        # Use primary guild (first guild) for now - TODO: make guild-aware
        guild_id = bot.guilds[0].id
        # Save to database using db_service
        await db.create_or_update_garden(
            user_id=user_id,
            guild_id=guild_id,
            tier=garden.get("tier", "rare"),
            level=garden.get("level", 1),
            plants=garden.get("plants", [])
        )
    except Exception as e:
        print(f"⚠️ Failed to sync garden {user_id} to database: {e}")

def schedule_db_sync(user_id: int = None, team_id: int = None, garden_user_id: int = None):
    """Schedule a database sync in the background (non-blocking)"""
    async def do_sync():
        try:
            if user_id is not None:
                await sync_user_to_db(user_id)
            if team_id is not None:
                await sync_team_to_db(team_id)
            if garden_user_id is not None:
                await sync_garden_to_db(garden_user_id)
        except Exception as e:
            pass  # Silently fail to not interrupt main bot flow
    
    # Schedule as background task
    if bot:
        asyncio.create_task(do_sync())

def migrate_rebirths():
    """One-time migration: combine positive_rebirths and negative_rebirths into single rebirths field."""
    migrated = False
    for user_id, data in chi_data.items():
        if "positive_rebirths" in data or "negative_rebirths" in data:
            if "rebirths" not in data:
                old_positive = data.get("positive_rebirths", 0)
                old_negative = data.get("negative_rebirths", 0)
                data["rebirths"] = old_positive + old_negative
                migrated = True
            if "positive_rebirths" in data:
                del data["positive_rebirths"]
            if "negative_rebirths" in data:
                del data["negative_rebirths"]
            migrated = True
    if migrated:
        save_data()
        print(f"✅ Migrated {len([u for u in chi_data.values() if 'rebirths' in u])} users to combined rebirth system")

migrate_rebirths()

# Migrate existing users to have new fields and convert legacy garden seeds
migration_needed = False
for user_id in chi_data:
    if "artifacts" not in chi_data[user_id]:
        chi_data[user_id]["artifacts"] = []
        migration_needed = True
    if "pets" not in chi_data[user_id]:
        chi_data[user_id]["pets"] = []
        migration_needed = True
    if "trade_requests" not in chi_data[user_id]:
        chi_data[user_id]["trade_requests"] = []
        migration_needed = True
    if "active_pet" not in chi_data[user_id]:
        chi_data[user_id]["active_pet"] = None
        migration_needed = True
    if "training_bonuses" not in chi_data[user_id]:
        chi_data[user_id]["training_bonuses"] = {
            "melee_strength": 0.0,
            "speed": 0.0,
            "range_strength": 0.0,
            "bonus_hp": 0
        }
        migration_needed = True
    if "pet_food" not in chi_data[user_id]:
        chi_data[user_id]["pet_food"] = {}
        migration_needed = True
    if "boss_keys" not in chi_data[user_id]:
        chi_data[user_id]["boss_keys"] = []
        migration_needed = True
    
    # CRITICAL: Migrate legacy "owned" garden seeds to numeric 0
    if "garden_inventory" in chi_data[user_id]:
        garden_inv = chi_data[user_id]["garden_inventory"]
        # Fix corrupted data: garden_inventory should be a dict, not a string
        if not isinstance(garden_inv, dict):
            print(f"[Migration] Fixing corrupted garden_inventory for user {user_id} (was {type(garden_inv).__name__})")
            chi_data[user_id]["garden_inventory"] = {}
            migration_needed = True
        else:
            for item_name, quantity in list(garden_inv.items()):
                if quantity == "owned":
                    chi_data[user_id]["garden_inventory"][item_name] = 0
                    migration_needed = True
                    print(f"[Migration] Converted {user_id}'s {item_name} from 'owned' to 0")
    
    # CRITICAL: Migrate old pet format to new pet format (Nov 1, 2025)
    if "pets" in chi_data[user_id] and chi_data[user_id]["pets"]:
        for i, pet in enumerate(chi_data[user_id]["pets"]):
            # Check if pet has old format (missing "type" field)
            if "type" not in pet and "id" in pet:
                print(f"[Migration] Converting old pet format for user {user_id}")
                
                # Map old pet IDs to new pet types (best effort)
                # Old pet system had different IDs, we'll default to "ox" for unknown pets
                old_id_to_type = {
                    "panda": "panda",
                    "tiger": "tiger",
                    "dragon": "dragon"
                }
                
                pet_type = old_id_to_type.get(pet.get("id", "").lower(), "ox")
                pet_data = PET_DATA.get(pet_type, PET_DATA["ox"])
                
                # Create new pet structure
                chi_data[user_id]["pets"][i] = {
                    "type": pet_type,
                    "name": pet_data["name"],
                    "emoji": pet_data["emoji"],
                    "nickname": pet.get("nickname"),
                    "health": pet.get("health", pet_data["base_hp"]),
                    "max_health": pet.get("max_health", pet_data["base_hp"]),
                    "level": 1,
                    "xp": 0,
                    "battles_won": 0,
                    "battles_lost": 0,
                    "purchased_at": pet.get("purchased_at", datetime.now(timezone.utc).isoformat())
                }
                migration_needed = True
                
        # Migrate active_pet from ID to type
        if chi_data[user_id].get("active_pet") and isinstance(chi_data[user_id]["active_pet"], str):
            old_active = chi_data[user_id]["active_pet"]
            if old_active not in PET_DATA:  # It's an old ID, not a type
                # Try to find matching pet in user's pets
                for pet in chi_data[user_id]["pets"]:
                    if pet.get("type"):
                        chi_data[user_id]["active_pet"] = pet["type"]
                        break
                migration_needed = True

# Save migrations if any were performed
if migration_needed:
    save_data()
    print("[Migration] User data migration complete and saved!")

def check_command_cooldown(user_id, command_name):
    """Check if user is on cooldown for a specific command. Returns (on_cooldown, time_remaining)."""
    current_time = time.time()
    
    if user_id not in command_cooldowns:
        command_cooldowns[user_id] = {}
    
    last_use = command_cooldowns[user_id].get(command_name, 0)
    time_since_last = current_time - last_use
    
    cooldown_time = FEED_COOLDOWN if command_name == "feed" else COMMAND_COOLDOWN
    
    if time_since_last < cooldown_time:
        time_remaining = cooldown_time - time_since_last
        return True, time_remaining
    return False, 0

def update_command_cooldown(user_id, command_name):
    """Update user's cooldown timestamp for a specific command."""
    if user_id not in command_cooldowns:
        command_cooldowns[user_id] = {}
    command_cooldowns[user_id][command_name] = time.time()

def check_chi_cooldown(user_id):
    """Check if user is on cooldown for chi earning. Returns (on_cooldown, time_remaining)."""
    current_time = time.time()
    last_chi = chi_cooldowns.get(user_id, 0)
    time_since_last = current_time - last_chi
    
    if time_since_last < CHI_COOLDOWN:
        time_remaining = CHI_COOLDOWN - time_since_last
        return True, time_remaining
    return False, 0

def update_chi_cooldown(user_id):
    """Update user's chi earning cooldown timestamp."""
    chi_cooldowns[user_id] = time.time()

def get_cooldown_time_str(seconds):
    """Convert seconds to a readable time string."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

def get_current_theme():
    return ("Tutorial Quests", TUTORIAL_QUESTS)

def check_words(message, word_list):
    return any(re.search(rf"\b{word}\b", message.content.lower()) for word in word_list)

def has_context_words(message):
    """Check if message has at least one word that isn't a positive/negative word."""
    message_lower = message.content.lower()
    words = re.findall(r'\b\w+\b', message_lower)
    
    all_chi_words = set(POSITIVE_WORDS + NEGATIVE_WORDS)
    
    for word in words:
        if word not in all_chi_words:
            return True
    
    return False

def update_chi(user_id, delta):
    if str(user_id) not in chi_data:
        chi_data[str(user_id)] = {
            "chi": 0, 
            "milestones_claimed": [], 
            "mini_quests": [],
            "rebirths": 0,
            "purchased_items": []
        }
    if "mini_quests" not in chi_data[str(user_id)]:
        chi_data[str(user_id)]["mini_quests"] = []
    if "rebirths" not in chi_data[str(user_id)]:
        old_positive = chi_data[str(user_id)].get("positive_rebirths", 0)
        old_negative = chi_data[str(user_id)].get("negative_rebirths", 0)
        chi_data[str(user_id)]["rebirths"] = old_positive + old_negative
    if "purchased_items" not in chi_data[str(user_id)]:
        chi_data[str(user_id)]["purchased_items"] = []
    
    chi_data[str(user_id)]["chi"] += delta
    
    # Update team chi if user is in a team (only for positive delta)
    user_id_str = str(user_id)
    if delta > 0 and user_id_str in teams_data["user_teams"]:
        team_id = teams_data["user_teams"][user_id_str]
        if team_id in teams_data["teams"]:
            teams_data["teams"][team_id]["team_chi"] += delta
            save_teams()
    
    # AUTO REBIRTH DISABLED - Users must manually rebirth with P!rebirth command
    # rebirth_msg = None
    # if chi_data[str(user_id)]["chi"] >= CHI_REBIRTH_THRESHOLD:
    #     chi_data[str(user_id)]["rebirths"] += 1
    #     chi_data[str(user_id)]["chi"] = 0
    #     total_rebirths = chi_data[str(user_id)]["rebirths"]
    #     rebirth_msg = f"✨🐼 REBIRTH! Chi reset to 0. Total Rebirths: {total_rebirths}"
    #     # Log rebirth
    #     asyncio.create_task(log_event(
    #         "User Rebirth",
    #         f"**User ID:** {user_id}\n**Type:** Positive Rebirth\n**Total Rebirths:** {total_rebirths}",
    #         discord.Color.gold()
    #     ))
    # elif chi_data[str(user_id)]["chi"] <= -CHI_REBIRTH_THRESHOLD:
    #     chi_data[str(user_id)]["rebirths"] += 1
    #     chi_data[str(user_id)]["chi"] = 0
    #     total_rebirths = chi_data[str(user_id)]["rebirths"]
    #     rebirth_msg = f"💀🐼 REBIRTH! Chi reset to 0. Total Rebirths: {total_rebirths}"
    #     # Log rebirth
    #     asyncio.create_task(log_event(
    #         "User Rebirth",
    #         f"**User ID:** {user_id}\n**Type:** Negative Rebirth\n**Total Rebirths:** {total_rebirths}",
    #         discord.Color.dark_red()
    #     ))
    
    save_data()
    return None  # No auto-rebirth messages anymore


async def auto_complete_tutorial_quest(user_id, quest_index, channel=None):
    """Auto-complete a tutorial quest and award the reward."""
    user_id_str = str(user_id)
    
    # Initialize user data if needed
    if user_id_str not in chi_data:
        chi_data[user_id_str] = {
            "chi": 0,
            "milestones_claimed": [],
            "mini_quests": [],
            "rebirths": 0,
            "purchased_items": [],
            "artifacts": []
        }
    
    # Check if quest is already completed
    if quest_index in quest_data["user_progress"].get(user_id_str, []):
        return None  # Already completed
    
    # Define quest rewards (50, 100, 150, 200, 300, 400, 500, 600, 800, 1000)
    quest_rewards = [50, 100, 150, 200, 300, 400, 500, 600, 800, 1000]
    
    if quest_index < 0 or quest_index >= len(quest_rewards):
        return None
    
    reward = quest_rewards[quest_index]
    
    # Mark quest as complete
    if user_id_str not in quest_data["user_progress"]:
        quest_data["user_progress"][user_id_str] = []
    quest_data["user_progress"][user_id_str].append(quest_index)
    
    # Award reward
    update_chi(int(user_id), reward)
    save_quests()
    
    # Check if all 9 tutorial quests (0-8) are complete, auto-complete quest 9
    completed_quests = quest_data["user_progress"][user_id_str]
    if quest_index != 9 and all(i in completed_quests for i in range(9)) and 9 not in completed_quests:
        # Auto-complete the final quest
        await auto_complete_tutorial_quest(user_id, 9, channel)
    
    # Send congratulations message
    if channel:
        quest_name = TUTORIAL_QUESTS[quest_index].split("\n")[0]
        embed = discord.Embed(
            title="🎉 Tutorial Quest Completed!",
            description=f"**{quest_name}**\n\n"
                       f"✨ Reward: **+{reward} chi**\n"
                       f"📊 Completed: **{len(completed_quests)}/10** tutorial quests",
            color=discord.Color.gold()
        )
        
        if quest_index == 9:
            embed.add_field(
                name="🏆 Tutorial Master!",
                value="You've completed all tutorial quests! You're ready for anything!",
                inline=False
            )
        
        try:
            await channel.send(embed=embed)
        except:
            pass
    
    return reward

def get_user_level(user_id):
    """Calculate user's level based on chi (500 chi per level, max 20)."""
    user_id_str = str(user_id)
    if user_id_str not in chi_data:
        return 0
    
    chi = chi_data[user_id_str].get("chi", 0)
    if chi < 0:
        return 0
    level = min(chi // 500, 20)
    return level

def get_item_level(user_id, item_name):
    """Get the upgrade level of a specific item for a user."""
    user_id_str = str(user_id)
    if user_id_str not in chi_data:
        return 0
    
    item_levels = chi_data[user_id_str].get("item_levels", {})
    return item_levels.get(item_name, 0)

def calculate_damage_with_level(base_damage, user_level, item_level):
    """Calculate damage with level bonuses (5% per user level + 5% per item level)."""
    total_level = user_level + item_level
    multiplier = 1.0 + (total_level * 0.05)
    return int(base_damage * multiplier)

def calculate_healing_with_level(base_healing, user_level, item_level):
    """Calculate healing with level bonuses (5% per user level + 5% per item level)."""
    total_level = user_level + item_level
    multiplier = 1.0 + (total_level * 0.05)
    return int(base_healing * multiplier)

def get_user_highest_artifact_tier(user_id):
    """Get the highest tier of artifacts a user owns."""
    user_id_str = str(user_id)
    if user_id_str not in chi_data or "artifacts" not in chi_data[user_id_str]:
        return None
    
    artifacts = chi_data[user_id_str]["artifacts"]
    if not artifacts:
        return None
    
    # Check for eternal first, then legendary, then rare
    for artifact in artifacts:
        if artifact.get("tier") == "eternal":
            return "eternal"
    for artifact in artifacts:
        if artifact.get("tier") == "legendary":
            return "legendary"
    for artifact in artifacts:
        if artifact.get("tier") == "rare":
            return "rare"
    
    return None

def calculate_max_hp(user_id):
    """Calculate user's maximum HP based on artifacts and permanent upgrades.
    
    Base HP: 250
    Artifact Bonuses (stack):
      - Rare: +250 HP
      - Legendary: +400 HP
      - Eternal: +500 HP
    Permanent HP Upgrades: From rebirth shop purchases
    """
    user_id_str = str(user_id)
    if user_id_str not in chi_data:
        return 250  # Base HP
    
    max_hp = 250  # Base HP (changed from 100)
    
    # Add artifact bonuses (all stack!)
    artifacts = chi_data[user_id_str].get("artifacts", [])
    has_rare = any(art.get("tier") == "rare" for art in artifacts)
    has_legendary = any(art.get("tier") == "legendary" for art in artifacts)
    has_eternal = any(art.get("tier") == "eternal" for art in artifacts)
    
    if has_rare:
        max_hp += 250
    if has_legendary:
        max_hp += 400
    if has_eternal:
        max_hp += 500
    
    # Add permanent HP upgrades from rebirth shop
    permanent_hp = chi_data[user_id_str].get("permanent_hp", 0)
    max_hp += permanent_hp
    
    return max_hp

async def check_and_reset_oversized_garden(user_id, user_name="Unknown", guild=None):
    """Check if a garden exceeds tier-specific plant limit and reset with compensation if needed.
    
    Tier-based limits:
    - Rare (Tier 1): 200 plants
    - Legendary (Tier 2): 300 plants
    - Eternal (Tier 3): 500 plants
    """
    user_id_str = str(user_id)
    
    if user_id_str not in gardens_data["gardens"]:
        return False
    
    garden_data = gardens_data["gardens"][user_id_str]
    total_plants = len(garden_data["plants"])
    
    # Get tier-specific limit
    garden_tier = garden_data.get("tier", "rare")
    tier_limits = {
        "rare": 200,
        "legendary": 300,
        "eternal": 500
    }
    plant_limit = tier_limits.get(garden_tier, 200)
    
    if total_plants > plant_limit:
        # Reset the garden and give compensation
        garden_data["plants"] = []
        
        # Initialize garden_inventory if needed
        if user_id_str not in chi_data:
            chi_data[user_id_str] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        if "garden_inventory" not in chi_data[user_id_str]:
            chi_data[user_id_str]["garden_inventory"] = {}
        
        # Give compensation: 5 Silverdew + 50 Lavender
        garden_inv = chi_data[user_id_str]["garden_inventory"]
        garden_inv["Silverdew"] = garden_inv.get("Silverdew", 0) + 5
        garden_inv["Lavender"] = garden_inv.get("Lavender", 0) + 50
        
        save_gardens()
        save_data()
        
        # Log the reset (only if guild is provided)
        if guild:
            tier_info = GARDEN_TIERS[garden_tier]
            await log_event(
                "Garden Reset",
                f"**User:** {user_name}\n**Garden:** {tier_info['emoji']} {tier_info['name']} (Tier {garden_tier})\n**Reason:** Garden exceeded {plant_limit} plant limit ({total_plants} plants)\n**Compensation:** 5 Silverdew + 50 Lavender seeds",
                guild, ctx.guild, discord.Color.orange())
        
        return True
    
    return False

async def initialize_garden(user_id, tier, user_name="Unknown", guild=None):
    """Initialize a garden for a user (50 chi is deducted by the caller)."""
    user_id_str = str(user_id)
    gardens_data["gardens"][user_id_str] = {
        "tier": tier,
        "level": 1,
        "plants": [],
        "last_watered": {}
    }
    # Initialize garden_inventory in chi_data if needed
    if user_id_str not in chi_data:
        chi_data[user_id_str] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id_str]:
        chi_data[user_id_str]["garden_inventory"] = {}
    
    save_gardens()
    save_data()
    
    # Log garden creation (only if guild is provided)
    if guild:
        tier_info = GARDEN_TIERS[tier]
        await log_event(
            "Garden Created",
            f"**User:** {user_name}\n**Garden Type:** {tier_info['emoji']} {tier_info['name']}\n**Cost:** 50 chi",
            guild, ctx.guild, discord.Color.green())
    
    # Auto-complete tutorial quest 1: Create a garden
    # Note: Channel context is not available here, quest completion message won't be sent
    await auto_complete_tutorial_quest(user_id, 1, None)

def get_pet_bonuses(user_id):
    """Get garden bonuses from user's active pet."""
    user_id_str = str(user_id)
    
    # Default bonuses (no pet)
    bonuses = {
        "chi_yield": 0.0,
        "growth_speed": 0.0,
        "rare_drop": 0.0
    }
    
    if user_id_str not in chi_data:
        return bonuses
    
    active_pet_type = chi_data[user_id_str].get("active_pet")
    if not active_pet_type:
        return bonuses
    
    # Verify user owns this pet
    has_pet = False
    for pet in chi_data[user_id_str].get("pets", []):
        if pet.get("type") == active_pet_type:
            has_pet = True
            break
    
    if not has_pet or active_pet_type not in PET_DATA:
        return bonuses
    
    # Return the pet's garden bonuses
    return PET_DATA[active_pet_type]["garden_bonus"].copy()

def calculate_grow_time(base_minutes, has_fertilizer, garden_tier="rare", user_id=None, plant_name=None, garden_data=None):
    """Calculate adjusted growth time with fertilizer, garden tier bonus, pet bonus, and watering bonus."""
    grow_time = base_minutes
    
    # Apply garden tier speed bonus (5-15% for tiers)
    tier_speed_bonus = GARDEN_TIERS.get(garden_tier, {}).get("speed_bonus", 0.0)
    if tier_speed_bonus > 0:
        grow_time = grow_time * (1 - tier_speed_bonus)
    
    # Apply fertilizer bonus (25% faster)
    if has_fertilizer:
        grow_time = grow_time * 0.75
    
    # Apply pet growth speed bonus
    if user_id:
        pet_bonuses = get_pet_bonuses(user_id)
        growth_speed_bonus = pet_bonuses["growth_speed"]
        if growth_speed_bonus > 0:
            grow_time = grow_time * (1 - growth_speed_bonus)
    
    # Apply watering bonus (5% faster growth)
    if garden_data and plant_name:
        last_watered = garden_data.get("last_watered", {}).get(plant_name, 0)
        current_time = time.time()
        time_since_water = current_time - last_watered
        
        # If watered within last 24 hours, apply 5% speed boost
        if time_since_water < 86400:  # 24 hours
            grow_time = grow_time * 0.95
    
    return grow_time

def get_garden_max_capacity(garden_tier):
    """Get the max plant capacity for a garden tier."""
    return GARDEN_TIERS.get(garden_tier, {}).get("max_capacity", 200)

def is_garden_event_active():
    """Check if the garden event is currently active."""
    if not gardens_data["garden_event"]["active"]:
        return False
    
    end_time = gardens_data["garden_event"]["end_time"]
    if end_time and datetime.now(timezone.utc).timestamp() < end_time:
        return True
    
    # Event expired, deactivate it
    gardens_data["garden_event"]["active"] = False
    gardens_data["garden_event"]["end_time"] = None
    save_gardens()
    return False

def parse_weapon_id(attack_input):
    """
    Parse weapon IDs like K1, DW2, BS3 etc. and return (weapon_name, attack_name, damage_info).
    Returns None if not a valid weapon ID.
    
    Weapon IDs:
    - BS1-BS3: Bamboo Sword attacks
    - K1-K3: Katana attacks
    - BC1-BC3: Bamboo Crossbow attacks
    - YS1-YS3: Yoogway Staff attacks
    - DW1-DW3: Dragon Warrior Blast attacks
    """
    attack_input = attack_input.strip().upper()
    
    # Find matching weapon by weapon_id
    for item in chi_shop_data["items"]:
        if "weapon_id" not in item or "weapon" not in item.get("tags", []):
            continue
        
        weapon_id = item["weapon_id"]
        if not attack_input.startswith(weapon_id):
            continue
        
        # Extract attack number (e.g., "K1" -> "1")
        attack_num_str = attack_input[len(weapon_id):]
        if not attack_num_str.isdigit():
            continue
        
        attack_num = int(attack_num_str)
        
        # Get the attack from custom_attacks (1-indexed)
        custom_attacks = item.get("custom_attacks", {})
        attack_list = list(custom_attacks.items())
        
        if 1 <= attack_num <= len(attack_list):
            attack_name, damage_info = attack_list[attack_num - 1]
            return (item["name"], attack_name, damage_info)
    
    return None

def process_duel_bets(winner_id, guild):
    """Process all bets from the active duel and return results."""
    global active_duel
    
    if not active_duel or "bets" not in active_duel:
        return []
    
    bet_results = []
    
    for bet in active_duel["bets"]:
        bettor_id = str(bet["bettor_id"])
        bet_amount = bet["bet_amount"]
        bet_on_user_id = bet["bet_on_user_id"]
        
        bettor = guild.get_member(bet["bettor_id"])
        bettor_mention = bettor.mention if bettor else f"<@{bet['bettor_id']}>"
        
        if bet_on_user_id == winner_id:
            update_chi(bettor_id, bet_amount * 2)
            bet_results.append(f"✅ {bettor_mention}: Won {bet_amount * 2} chi (net +{bet_amount} chi)")
        else:
            bet_results.append(f"❌ {bettor_mention}: Lost {bet_amount} chi")
    
    return bet_results


# --- Bot Owner IDs for admin permissions ---
BOT_OWNER_IDS = {1382187068373074001, 1311394031640776716, 1300838678280671264}

def is_bot_owner():
    async def predicate(ctx):
        return ctx.author.id in BOT_OWNER_IDS
    return commands.check(predicate)

def migrate_garden_inventory():
    """Migrate garden inventory from gardens_data to chi_data"""
    migrated_count = 0
    for user_id, garden_data in gardens_data.get("gardens", {}).items():
        if "inventory" in garden_data and garden_data["inventory"]:
            # Initialize user in chi_data if needed
            if user_id not in chi_data:
                chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
            
            # Initialize garden_inventory if needed
            if "garden_inventory" not in chi_data[user_id]:
                chi_data[user_id]["garden_inventory"] = {}
            
            # Migrate inventory items
            for item_name, quantity in garden_data["inventory"].items():
                if quantity > 0:
                    chi_data[user_id]["garden_inventory"][item_name] = quantity
            
            # Remove old inventory field
            del garden_data["inventory"]
            migrated_count += 1
    
    if migrated_count > 0:
        save_data()
        save_gardens()
        print(f"🌸 Migrated garden inventory for {migrated_count} user(s)")

def sanitize_datetime_fields(data_dict):
    """Remove or convert datetime fields to prevent JSON serialization errors"""
    if not isinstance(data_dict, dict):
        return data_dict
    
    sanitized = {}
    for key, value in data_dict.items():
        # Skip datetime fields entirely (they're not used in bot logic)
        if key in ['updated_at', 'created_at', 'last_updated', 'timestamp']:
            continue
        # Recursively sanitize nested dicts
        elif isinstance(value, dict):
            sanitized[key] = sanitize_datetime_fields(value)
        # Recursively sanitize lists
        elif isinstance(value, list):
            sanitized[key] = [sanitize_datetime_fields(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized

async def load_data_from_database():
    """Load all data from PostgreSQL database on startup for persistence"""
    global chi_data, teams_data, gardens_data
    
    # Clear existing data to avoid mixing old and new state
    temp_chi_data = {}
    temp_teams_data = {"teams": {}}
    temp_gardens_data = {"gardens": {}, "garden_event": {"active": False, "end_time": None}}
    
    loaded_successfully = False
    
    # Use primary guild for data loading - TODO: support multi-guild storage
    if not bot.guilds:
        print("⚠️ No guilds available yet, skipping database load")
        return False
    
    guild_id = bot.guilds[0].id
    
    try:
        # Load all users with granular error handling
        try:
            all_users = await db.get_all_users(guild_id=guild_id)
            if all_users:
                for user_id, user_dict in all_users.items():
                    # Sanitize datetime fields before storing
                    sanitized_data = sanitize_datetime_fields(user_dict)
                    temp_chi_data[str(user_id)] = sanitized_data
                print(f"📊 Loaded {len(all_users)} users from database")
        except Exception as e:
            print(f"⚠️ Failed to load users from database: {e}")
        
        # Load all teams with granular error handling
        try:
            all_teams = await db.get_all_teams(guild_id=guild_id)
            if all_teams:
                for team_id, team_dict in all_teams.items():
                    # Sanitize datetime fields before storing
                    sanitized_data = sanitize_datetime_fields(team_dict)
                    temp_teams_data["teams"][str(team_id)] = sanitized_data
                print(f"👥 Loaded {len(all_teams)} teams from database")
        except Exception as e:
            print(f"⚠️ Failed to load teams from database: {e}")
        
        # Load all gardens with granular error handling
        try:
            all_gardens = await db.get_all_gardens(guild_id=guild_id)
            if all_gardens:
                for user_id, garden_dict in all_gardens.items():
                    # Sanitize datetime fields before storing
                    sanitized_data = sanitize_datetime_fields(garden_dict)
                    temp_gardens_data["gardens"][str(user_id)] = sanitized_data
                print(f"🌸 Loaded {len(all_gardens)} gardens from database")
        except Exception as e:
            print(f"⚠️ Failed to load gardens from database: {e}")
        
        # Update each global ONLY if that section loaded successfully
        sections_loaded = 0
        
        if temp_chi_data:
            chi_data.clear()
            chi_data.update(temp_chi_data)
            sections_loaded += 1
        else:
            print("⚠️ No user data loaded, preserving existing chi_data")
        
        if temp_teams_data["teams"]:
            teams_data["teams"] = temp_teams_data["teams"]
            sections_loaded += 1
        else:
            print("⚠️ No team data loaded, preserving existing teams_data")
        
        if temp_gardens_data["gardens"]:
            gardens_data["gardens"] = temp_gardens_data["gardens"]
            sections_loaded += 1
        else:
            print("⚠️ No garden data loaded, preserving existing gardens_data")
        
        if sections_loaded > 0:
            loaded_successfully = True
            print(f"✅ Loaded {sections_loaded}/3 data sections from database successfully!")
        else:
            print("⚠️ No data loaded from database, using existing JSON data")
        
        return loaded_successfully
    except Exception as e:
        print(f"⚠️ Critical error during database load: {e}")
        return False

# ==================== ACHIEVEMENTS SYSTEM ====================

async def unlock_achievement(user_id, achievement_id, guild):
    """Unlock an achievement and DM the user"""
    user_id_str = str(user_id)
    
    # Initialize user achievements if needed
    if user_id_str not in chi_data:
        chi_data[user_id_str] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "achievements" not in chi_data[user_id_str]:
        chi_data[user_id_str]["achievements"] = []
    
    # Check if already unlocked
    if achievement_id in chi_data[user_id_str]["achievements"]:
        return False
    
    # Find achievement data
    achievement = None
    for ach in achievements_data.get("achievements", []):
        if ach["id"] == achievement_id:
            achievement = ach
            break
    
    if not achievement:
        return False
    
    # Unlock achievement
    chi_data[user_id_str]["achievements"].append(achievement_id)
    
    # Award chi reward
    reward_chi = achievement.get("reward_chi", 0)
    if reward_chi > 0:
        update_chi(user_id_str, reward_chi)
    
    save_data()
    
    # DM the user
    try:
        user = guild.get_member(user_id)
        if user:
            tier_data = achievements_data.get("tiers", {}).get(achievement["tier"], {})
            tier_emoji = tier_data.get("emoji", "⚪")
            tier_color = tier_data.get("color", 0)
            
            embed = discord.Embed(
                title=f"🏆 ACHIEVEMENT UNLOCKED! {tier_emoji}",
                description=f"**{achievement['emoji']} {achievement['name']}**\n\n*{achievement['description']}*",
                color=discord.Color(tier_color)
            )
            embed.add_field(name="Tier", value=f"{tier_emoji} {achievement['tier'].capitalize()}", inline=True)
            embed.add_field(name="Category", value=f"{achievement['emoji']} {achievement['category']}", inline=True)
            if reward_chi > 0:
                embed.add_field(name="Reward", value=f"💎 +{reward_chi:,} chi", inline=True)
            embed.set_footer(text="View all achievements with P!achievements")
            
            await user.send(embed=embed)
    except discord.Forbidden:
        pass  # User has DMs disabled
    except Exception as e:
        print(f"Failed to DM achievement unlock: {e}")
    
    return True

@bot.command(name="achievements", aliases=["achieve", "ach"])
async def view_achievements(ctx, category: str = ""):
    """View your achievements and progress"""
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "achievements" not in chi_data[user_id]:
        chi_data[user_id]["achievements"] = []
    
    user_achievements = chi_data[user_id]["achievements"]
    all_achievements = achievements_data.get("achievements", [])
    categories_data = achievements_data.get("categories", {})
    
    # Filter by category if specified
    if category:
        category_match = None
        for cat_name, cat_data in categories_data.items():
            if cat_name.lower() == category.lower():
                category_match = cat_name
                break
        
        if category_match:
            all_achievements = [ach for ach in all_achievements if ach["category"] == category_match]
        else:
            await ctx.send(f"❌ Unknown category! Available: {', '.join(categories_data.keys())}")
            return
    
    # Count unlocked achievements
    unlocked_count = len([ach for ach in all_achievements if ach["id"] in user_achievements])
    total_count = len(all_achievements)
    
    # Calculate completion percentage
    completion = (unlocked_count / total_count * 100) if total_count > 0 else 0
    
    # Build embed
    if category:
        title = f"🏆 {category} Achievements"
    else:
        title = f"🏆 {ctx.author.display_name}'s Achievements"
    
    embed = discord.Embed(
        title=title,
        description=f"**Progress:** {unlocked_count}/{total_count} ({completion:.1f}%)",
        color=discord.Color.gold()
    )
    
    # Group by tier for better organization
    tiers_order = ["legendary", "epic", "rare", "common"]
    for tier in tiers_order:
        tier_achievements = [ach for ach in all_achievements if ach["tier"] == tier]
        
        if not tier_achievements:
            continue
        
        tier_data = achievements_data.get("tiers", {}).get(tier, {})
        tier_emoji = tier_data.get("emoji", "⚪")
        
        field_text = []
        for ach in tier_achievements[:10]:  # Limit to 10 per tier
            unlocked = ach["id"] in user_achievements
            if unlocked:
                field_text.append(f"✅ {ach['emoji']} **{ach['name']}**")
            elif not ach.get("hidden", False):
                field_text.append(f"🔒 {ach['emoji']} {ach['name']}")
        
        if field_text:
            embed.add_field(
                name=f"{tier_emoji} {tier.capitalize()} Achievements",
                value="\n".join(field_text),
                inline=False
            )
    
    # Show categories if no category specified
    if not category and categories_data:
        cat_text = []
        for cat_name, cat_data in categories_data.items():
            cat_count = len([ach for ach in all_achievements if ach["category"] == cat_name and ach["id"] in user_achievements])
            cat_total = len([ach for ach in all_achievements if ach["category"] == cat_name])
            cat_text.append(f"{cat_data['emoji']} **{cat_name}:** {cat_count}/{cat_total}")
        
        embed.add_field(
            name="📊 Categories",
            value="\n".join(cat_text),
            inline=False
        )
        embed.set_footer(text="Use P!achievements <category> to view specific category")
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    global next_event_time
    
    # Track bot start time for uptime monitoring
    bot.start_time = time.time()
    
    # Connect to database for persistent storage
    try:
        await db.connect()
        print("✅ Database connected - data will persist across updates!")
        
        # Load data from database (this ensures persistence across republishes!)
        await load_data_from_database()
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        print("   Falling back to JSON file storage")
    
    print(f"✅ {bot.user} is online!")
    print(f"📊 Monitoring {len(bot.guilds)} guild(s)")
    
    # Run migration for garden inventory
    migrate_garden_inventory()
    
    if not daily_chi_evaluation.is_running():
        daily_chi_evaluation.start()
    if not monthly_reset_check.is_running():
        monthly_reset_check.start()
    if not chi_event_scheduler.is_running():
        chi_event_scheduler.start()
    if not duel_timeout_check.is_running():
        duel_timeout_check.start()
    if not training_timeout_check.is_running():
        training_timeout_check.start()
    if not artifact_spawner.is_running():
        artifact_spawner.start()
    if not database_sync_task.is_running():
        database_sync_task.start()
    
    next_event_time = datetime.now(timezone.utc) + timedelta(seconds=random.randint(CHI_EVENT_MIN_INTERVAL, CHI_EVENT_MAX_INTERVAL))

@bot.event
async def on_command_error(ctx, error):
    """Global error handler - logs all command errors automatically"""
    
    # Create message link
    message_link = f"https://discord.com/channels/{ctx.guild.id if ctx.guild else '@me'}/{ctx.channel.id}/{ctx.message.id}"
    
    # Log the error
    error_entry = log_error(
        error_msg=str(error),
        command=f"P!{ctx.command.name}" if ctx.command else "Unknown",
        user=ctx.author,
        message_link=message_link,
        error_code=type(error).__name__
    )
    
    # Post to logging channel if configured (with validation and error handling)
    if log_config.get("error_channel_id"):
        try:
            log_channel = bot.get_channel(log_config["error_channel_id"])
            if log_channel and isinstance(log_channel, discord.TextChannel):
                # Check if we have permission to send messages
                permissions = log_channel.permissions_for(log_channel.guild.me)
                if permissions.send_messages and permissions.embed_links:
                    embed = discord.Embed(
                        title=f"⚠️ Error Log: {error_entry['id']}",
                        description=f"**Error:** {str(error)[:200]}",
                        color=discord.Color.red(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    embed.add_field(
                        name="Details",
                        value=f"**Command:** {error_entry['command']}\n"
                              f"**User:** {error_entry['user']}\n"
                              f"**Code:** `{error_entry['error_code']}`",
                        inline=False
                    )
                    embed.add_field(
                        name="Jump to Message",
                        value=f"[Click Here]({message_link})",
                        inline=False
                    )
                    await log_channel.send(embed=embed)
            else:
                # Channel not found or invalid - disable auto-posting
                print(f"⚠️ Logging channel {log_config['error_channel_id']} not found or invalid")
        except discord.Forbidden:
            print(f"⚠️ Missing permissions to post to logging channel")
        except discord.HTTPException:
            # Avoid log loops - don't log errors about logging
            pass
        except Exception as e:
            print(f"⚠️ Unexpected error posting to logging channel: {e}")
    
    # Don't send messages for specific error types (let command-specific handlers deal with them)
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    
    # For other errors, send a generic message
    if not isinstance(error, (commands.MissingRequiredArgument, commands.MemberNotFound)):
        await ctx.send(f"❌ An error occurred: {str(error)[:100]}")

@bot.event
async def on_disconnect():
    print("⚠️ Disconnected from Discord")

@bot.event
async def on_resumed():
    print("🔄 Reconnected to Discord")
    
    if not daily_chi_evaluation.is_running():
        daily_chi_evaluation.start()
    if not monthly_reset_check.is_running():
        monthly_reset_check.start()
    if not chi_event_scheduler.is_running():
        chi_event_scheduler.start()
    if not duel_timeout_check.is_running():
        duel_timeout_check.start()
    if not training_timeout_check.is_running():
        training_timeout_check.start()
    if not artifact_spawner.is_running():
        artifact_spawner.start()
    if not database_sync_task.is_running():
        database_sync_task.start()

@bot.event
async def on_guild_remove(guild):
    """
    Automatically clean up all data when bot leaves a server.
    Protects PSY's data across all servers.
    """
    print(f"👋 Bot removed from guild: {guild.name} (ID: {guild.id})")
    
    try:
        # Delete all guild data from database (protects PSY automatically)
        stats = await db.delete_guild_data(guild.id)
        total_deleted = sum(stats.values())
        
        if total_deleted > 0:
            print(f"✅ Cleaned up {total_deleted} database rows for guild {guild.id}")
        
        # Remove guild config from server_config.json
        configs = load_server_configs()
        guild_id_str = str(guild.id)
        
        if guild_id_str in configs["guilds"]:
            del configs["guilds"][guild_id_str]
            save_server_configs(configs)
            print(f"✅ Removed server config for guild {guild.id}")
        
        # Reload in-memory data from database to reflect deletions
        # This ensures data is consistent after guild removal
        await load_data_from_database()
        print(f"✅ Reloaded data from database after guild removal")
        
    except Exception as e:
        print(f"❌ Error cleaning up guild {guild.id}: {e}")

# ==================== FUN UTILITY COMMANDS ====================

@bot.command(name="coinflip", aliases=["flip", "coin"])
async def coinflip_command(ctx):
    """Flip a coin - with a 2% chance to land on its side!"""
    roll = random.randint(1, 100)
    
    if roll <= 2:  # 2% chance
        result = "**SIDE**"
        emoji = "🪙"
        message = f"{emoji} The coin defied physics and landed on its **SIDE**! What are the odds?! (2%)"
    elif roll <= 51:  # 49% chance for heads
        result = "**HEADS**"
        emoji = "👑"
        message = f"{emoji} The coin landed on {result}!"
    else:  # 49% chance for tails
        result = "**TAILS**"
        emoji = "🦅"
        message = f"{emoji} The coin landed on {result}!"
    
    await ctx.send(message)

@bot.command(name="quote", aliases=["unmotivational", "demotivate"])
async def quote_command(ctx):
    """Get a random unmotivational quote"""
    quotes = [
        "\"Dreams don't work unless you wake up.\" - But who wants to wake up?",
        "\"Rome wasn't built in a day.\" - It also wasn't built by you.",
        "\"The expert in anything was once a beginner.\" - And you're still a beginner.",
        "\"Success is 1% inspiration, 99% perspiration.\" - You're probably just sweating from anxiety.",
        "\"Every master was once a disaster.\" - Some just stayed disasters.",
        "\"You miss 100% of the shots you don't take.\" - You also miss most of the shots you DO take.",
        "\"Believe you can and you're halfway there.\" - The other half is actually doing it.",
        "\"The only limit is yourself.\" - Well, and money. And time. And talent.",
        "\"Fall down seven times, stand up eight.\" - Or just stay down, it's more comfortable.",
        "\"Hard work beats talent.\" - Unless the talented person also works hard.",
        "\"You can do anything!\" - Except the things you can't.",
        "\"Live, laugh, love.\" - Or just sit there. That works too.",
        "\"It's never too late.\" - Except when it literally is.",
        "\"Shoot for the moon!\" - You'll probably miss and float forever in space.",
        "\"Follow your dreams!\" - Unless they're unrealistic. Then maybe don't.",
        "\"Good things come to those who wait.\" - But better things come to people who actually do stuff.",
        "\"Be yourself!\" - Unless yourself is the problem.",
        "\"Winners never quit!\" - Sometimes quitting is the smart move though.",
        "\"Think positive!\" - Thinking doesn't change reality.",
        "\"You're one in a million!\" - So there are 8,000 people just like you."
    ]
    
    quote = random.choice(quotes)
    await ctx.send(f"💭 {quote}")

@bot.command(name="hydrate", aliases=["water", "drink"])
async def hydrate_command(ctx):
    """Get a sarcastic reminder to drink water"""
    messages = [
        "💧 Oh wow, you need a bot to tell you to drink water? Revolutionary.",
        "💧 Your body is 60% water. Don't let it become 59%. Drink up.",
        "💧 Reminder: Water exists. You should probably consume some.",
        "💧 Imagine being so dehydrated you ask a Discord bot for help. Drink water.",
        "💧 Breaking news: Local human forgets basic survival needs. More at 11. (Drink water)",
        "💧 Water: That clear stuff that keeps you alive. Yes, THAT one. Drink it.",
        "💧 *sigh* Go drink water. Your kidneys are judging you.",
        "💧 H2O. Two hydrogen, one oxygen. Ancient recipe. Still works. Try it.",
        "💧 Fun fact: You can drink water BEFORE you're dying of thirst. Wild, I know.",
        "💧 Your cells are screaming. Water would help. Just saying.",
        "💧 Congratulations! You've unlocked the secret to life: drinking water. Groundbreaking.",
        "💧 The year is 2025. Humans still need reminders to drink water. Drink some.",
        "💧 Plot twist: That headache might be dehydration. Crazy concept. Drink water.",
        "💧 Water won't solve all your problems, but it'll solve the dehydration one. Start there.",
        "💧 Roses are red, violets are blue, your body needs water, and so do you."
    ]
    
    message = random.choice(messages)
    await ctx.send(message)

# Global dictionary to track active reminders
active_reminders = {}

@bot.command(name="remind", aliases=["reminder", "remindme"])
async def remind_command(ctx, time_str: str = ""):
    """Set a reminder - Usage: P!remind 30m or P!remind 2h30m or P!remind 1d"""
    if not time_str:
        await ctx.send("⏰ **Usage:** `P!remind <time>`\n\n"
                      "**Examples:**\n"
                      "`P!remind 30m` - 30 minutes\n"
                      "`P!remind 2h` - 2 hours\n"
                      "`P!remind 1d` - 1 day\n"
                      "`P!remind 1w` - 1 week\n"
                      "`P!remind 2h30m` - 2 hours 30 minutes\n\n"
                      "Formats: `w`(weeks), `d`(days), `h`(hours), `m`(minutes), `s`(seconds)")
        return
    
    try:
        # Parse time string
        total_seconds = 0
        time_parts = []
        current_num = ""
        
        for char in time_str.lower():
            if char.isdigit():
                current_num += char
            elif char in ['w', 'd', 'h', 'm', 's']:
                if current_num:
                    num = int(current_num)
                    if char == 'w':
                        total_seconds += num * 604800  # weeks
                        time_parts.append(f"{num} week{'s' if num != 1 else ''}")
                    elif char == 'd':
                        total_seconds += num * 86400  # days
                        time_parts.append(f"{num} day{'s' if num != 1 else ''}")
                    elif char == 'h':
                        total_seconds += num * 3600  # hours
                        time_parts.append(f"{num} hour{'s' if num != 1 else ''}")
                    elif char == 'm':
                        total_seconds += num * 60  # minutes
                        time_parts.append(f"{num} minute{'s' if num != 1 else ''}")
                    elif char == 's':
                        total_seconds += num  # seconds
                        time_parts.append(f"{num} second{'s' if num != 1 else ''}")
                    current_num = ""
        
        if total_seconds == 0:
            await ctx.send("❌ Invalid time format! Use: `30m`, `2h`, `1d`, etc.")
            return
        
        if total_seconds > 604800:  # Max 1 week
            await ctx.send("❌ Maximum reminder time is 1 week (7 days)!")
            return
        
        time_display = ", ".join(time_parts)
        
        # Confirm reminder set
        await ctx.send(f"⏰ Reminder set for **{time_display}**! I'll ping you when time's up.")
        
        # Wait for the specified time
        await asyncio.sleep(total_seconds)
        
        # Send reminder
        await ctx.send(f"⏰ {ctx.author.mention} **REMINDER!** It's been {time_display}!")
        
    except ValueError:
        await ctx.send("❌ Invalid time format! Use numbers followed by: `w` (weeks), `d` (days), `h` (hours), `m` (minutes), `s` (seconds)\n"
                      "**Example:** `P!remind 30m` or `P!remind 2h30m`")
    except Exception as e:
        await ctx.send(f"❌ An error occurred setting your reminder: {str(e)}")

@bot.command(name="8ball", aliases=["eightball", "magic8ball"])
async def eightball_command(ctx, *, question: str = ""):
    """Ask the magic 8-ball a question"""
    if not question:
        await ctx.send("🎱 You need to ask a question! Example: `P!8ball Will I win my next duel?`")
        return
    
    responses = [
        "It is certain.",
        "Without a doubt.",
        "Yes definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful.",
        "Absolutely not.",
        "The spirits are unclear.",
        "Pax says no.",
        "The pandas have spoken: Maybe."
    ]
    
    answer = random.choice(responses)
    await ctx.send(f"🎱 **Question:** {question}\n**Answer:** {answer}")

@bot.command(name="roast")
async def roast_command(ctx, target: discord.Member = None):
    """Get roasted (or roast someone else)"""
    if target is None:
        target = ctx.author
    
    roasts = [
        "I'd agree with you, but then we'd both be wrong.",
        "You're not stupid; you just have bad luck thinking.",
        "I'm not saying you're dumb, but you have bad luck when it comes to thinking.",
        "If I wanted to hear from an idiot, I'd watch a political debate.",
        "You bring everyone so much joy... when you leave the room.",
        "I'd explain it to you, but I left my crayons at home.",
        "You're proof that evolution can go in reverse.",
        "Somewhere out there is a tree tirelessly producing oxygen for you. You owe it an apology.",
        "I'm not insulting you. I'm describing you.",
        "You're like a cloud. When you disappear, it's a beautiful day.",
        "You have the perfect face for radio.",
        "If you were any more inbred, you'd be a sandwich.",
        "You're the reason the gene pool needs a lifeguard."
    ]
    
    roast = random.choice(roasts)
    await ctx.send(f"🔥 {target.mention} {roast}")

@bot.command(name="compliment")
async def compliment_command(ctx, target: discord.Member = None):
    """Give a compliment (to yourself or someone else)"""
    if target is None:
        target = ctx.author
    
    compliments = [
        "You're doing amazing, sweetie!",
        "Your positive energy is contagious!",
        "You light up every room you enter!",
        "The world is better with you in it!",
        "You're one of a kind!",
        "Your smile could light up the darkest room!",
        "You make a difference!",
        "You're stronger than you think!",
        "You're appreciated more than you know!",
        "You're breathtaking!",
        "Pax approves of your vibe!",
        "The pandas are proud of you!",
        "You're absolutely legendary!",
        "Your chi is radiant today!",
        "You're a gift to this community!"
    ]
    
    compliment = random.choice(compliments)
    await ctx.send(f"✨ {target.mention} {compliment}")

@bot.command(name="help")
async def help_command(ctx, category: str = None):
    """Display help for bot commands organized by category"""
    
    if category is None:
        embed = discord.Embed(
            title="🐼 Panda Chi Bot - Command Categories",
            description="Use `P!help <category>` to see commands for each category!\n\n**Example:** `P!help chi` to see Chi commands",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="📚 Available Categories",
            value=(
                "**`chi`** - Chi tracking, earning, and rebirth commands\n"
                "**`duel`** - Combat and dueling commands\n"
                "**`boss`** - Epic boss battles for legendary keys\n"
                "**`pet`** - Pet adoption and management\n"
                "**`team`** - Team creation and management\n"
                "**`garden`** - Garden farming system with artifact-gated areas\n"
                "**`trading`** - Trading system for chi, artifacts, and pets\n"
                "**`fun`** - Fun utility commands (coinflip, quotes, reminders, etc.)\n"
                "**`admin`** - Administrator commands (admins only)"
            ),
            inline=False
        )
        embed.set_footer(text="🐼 Pax is watching over your community!")
        await ctx.send(embed=embed)
        return
    
    category = category.lower()
    
    if category == "chi":
        embed = discord.Embed(
            title="🐼 Chi Commands",
            description="Earn chi through positive words, manage your chi, and shop for rewards!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Earning & Viewing",
            value=(
                "`P!chi [@user]` - Check your (or someone's) chi and stats\n"
                "`P!level [@user]` - Check your (or someone's) level and progress\n"
                "`P!leaderboard [category]` - View leaderboards (chi/rebirth/team/artifact)\n"
                "`P!inv` - View your inventory (items, artifacts, pets, food)"
            ),
            inline=False
        )
        embed.add_field(
            name="🛍️ Shopping",
            value=(
                "`P!shop` - View rebirth shop items\n"
                "`P!cshop` - View chi shop items\n"
                "`P!buy <item>` - Purchase an item from chi shop\n"
                "`P!rshop` - View rebirth shop\n"
                "`P!rbuy <item>` - Purchase from rebirth shop\n"
                "`P!search <shop> <category> [price]` - Search shops by category or price"
            ),
            inline=False
        )
        embed.add_field(
            name="⚡ Progression",
            value=(
                "`P!rebirth` - Manually rebirth (at ±100,000 chi)\n"
                "`P!upgrade <item>` - Upgrade an item (+1 level for 500 chi)\n"
                "`P!claim` - Claim chi from events/parties\n"
                "`P!claim food` - Claim food from food events"
            ),
            inline=False
        )
        embed.add_field(
            name="🎮 Other",
            value=(
                "`P!translate <message_id> <language>` - Translate any message\n"
                "`P!feed <item>` - Feed Pax during specific hours\n"
                "`P!riddle` - Get a random riddle (answer in DM)\n"
                "`P!whisper` & `P!listen` - Secret quest commands"
            ),
            inline=False
        )
        
    elif category == "duel":
        embed = discord.Embed(
            title="⚔️ Duel Commands",
            description="Challenge players to turn-based combat!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="⚔️ Combat",
            value=(
                "`P!duel @user` - Challenge someone to a duel\n"
                "`P!duel accept` - Accept a duel challenge\n"
                "`P!duel attack <weapon>` - Attack with a weapon\n"
                "`P!duel heal <item>` - Heal yourself with an item\n"
                "`P!duel run` - Forfeit the duel (-100 chi)"
            ),
            inline=False
        )
        embed.add_field(
            name="💰 Betting",
            value="`P!duel bet <amount> @user` - Bet chi on a duel (spectators)",
            inline=False
        )
        embed.add_field(
            name="✨ Artifacts",
            value="`P!find artifact` - Claim spawned artifacts (heal in duels)",
            inline=False
        )
        
    elif category == "boss":
        embed = discord.Embed(
            title="🐉 Boss Battle Commands",
            description="Challenge epic bosses and earn legendary keys for the Pirate World!",
            color=discord.Color.dark_gold()
        )
        embed.add_field(
            name="⚔️ Boss Battles",
            value=(
                "`P!boss list` - View all available bosses\n"
                "`P!boss fight <boss>` - Challenge a boss (fang/ironhide/emberclaw)\n"
                "`P!boss attack <weapon>` - Attack the boss with a weapon\n"
                "`P!boss heal <item>` - Heal yourself with an item or artifact\n"
                "`P!boss run` - Flee from battle (-100 chi penalty)"
            ),
            inline=False
        )
        embed.add_field(
            name="🎁 Rewards",
            value=(
                "**Fang of the Bamboo** 🐉: Bamboo Key + 100 chi\n"
                "**Ironhide Titan** 🪨: Titan Key + 200 chi\n"
                "**Emberclaw the Eternal** 🔥: Eternal Key + 500 chi + 5% artifact chance"
            ),
            inline=False
        )
        embed.add_field(
            name="✨ Special Abilities",
            value=(
                "Each boss has unique abilities:\n"
                "• **Bamboo Strike** - Ignores defense 10% of the time\n"
                "• **Iron Wall** - Heals 10% HP every 3 turns\n"
                "• **Infernal Roar** - Burns you for 25 HP over 3 turns"
            ),
            inline=False
        )
        
    elif category == "pet":
        embed = discord.Embed(
            title="🐾 Pet Commands",
            description="Adopt pets, feed them, and use them in battle!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🐾 Pet Management",
            value=(
                "`P!pet store` - View available pets for adoption\n"
                "`P!pet buy <name>` - Purchase a pet\n"
                "`P!pet name <nickname>` - Give your pet a nickname\n"
                "`P!pet feed <food>` - Feed your pet to restore health\n"
                "`P!pet health` - Check your pet's health status\n"
                "`P!pet attack` - Use pet attack (duels only)"
            ),
            inline=False
        )
        
    elif category == "team":
        embed = discord.Embed(
            title="👥 Team Commands",
            description="Create teams, customize bases, and compete!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="👥 Team Management",
            value=(
                "`P!team create <name>` - Create a new team\n"
                "`P!team info` - View your team's details\n"
                "`P!team list` - List all teams in the server\n"
                "`P!team members` - View your team members\n"
                "`P!team add @user` - Add member (leader only)\n"
                "`P!team remove @user` - Remove member (leader only)\n"
                "`P!team leave` - Leave your current team\n"
                "`P!team disband` - Disband team (leader only)"
            ),
            inline=False
        )
        embed.add_field(
            name="🏠 Base Customization",
            value=(
                "`P!team base view` - View your team base\n"
                "`P!team base paint <color>` - Paint the base (leader only)\n"
                "`P!team base decorate <item>` - Add decorations\n"
                "`P!team base gym <equipment>` - Add gym equipment"
            ),
            inline=False
        )
        embed.add_field(
            name="⬆️ Upgrades",
            value=(
                "`P!team upgrade base <module>` - Upgrade base modules\n"
                "`P!team upgrade gym` - Upgrade team gym\n"
                "`P!team upgrade arena` - Upgrade team arena"
            ),
            inline=False
        )
    
    elif category == "garden":
        embed = discord.Embed(
            title="🌸 Garden Commands",
            description="Grow plants to earn chi! Requires artifacts to unlock.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🌱 Garden Basics",
            value=(
                "`P!garden` - View your garden status\n"
                "`P!garden shop` - View available seeds and tools\n"
                "`P!garden shop buy <item> [quantity]` - Purchase seeds or tools\n"
                "`P!sell <seed> [quantity]` - Sell seeds for 1 chi each\n"
                "`P!garden seed <name>` - Get info about a specific seed"
            ),
            inline=False
        )
        embed.add_field(
            name="🌿 Farming",
            value=(
                "`P!garden plant <seed>` - Plant a seed from inventory\n"
                "`P!garden water <plant>` - Water for +5% growth speed (24hr cooldown)\n"
                "`P!garden harvest <plant>` - Harvest mature plants for chi"
            ),
            inline=False
        )
        embed.add_field(
            name="📊 Info & Upgrades",
            value=(
                "`P!garden about [@user]` - View garden information\n"
                "`P!garden upgrade` - Upgrade your garden level"
            ),
            inline=False
        )
        embed.add_field(
            name="🌸 Garden Tiers (Artifact-Gated)",
            value=(
                "🪷 **Pond Garden** - Requires Rare artifact\n"
                "🎋 **Chi Grove** - Requires Legendary artifact\n"
                "🌸 **Hépíng sēnlín** - Requires Eternal artifact"
            ),
            inline=False
        )
        
    elif category == "trading":
        embed = discord.Embed(
            title="💱 Trading Commands",
            description="Trade chi, artifacts, and pets with other players!",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="💱 Trading System",
            value=(
                "`P!trade chi @user <amount>` - Trade chi with someone\n"
                "`P!trade artifact @user <item>` - Trade an artifact\n"
                "`P!trade pet @user <name>` - Trade a pet"
            ),
            inline=False
        )
        embed.add_field(
            name="ℹ️ How Trading Works",
            value="Both players must confirm the trade. You cannot trade with yourself or bots.",
            inline=False
        )
        
    elif category == "fun":
        embed = discord.Embed(
            title="🎉 Fun & Utility Commands",
            description="Fun commands to spice up your Discord experience!",
            color=discord.Color.from_rgb(255, 105, 180)  # Hot pink
        )
        embed.add_field(
            name="🎲 Games & Random",
            value=(
                "`P!coinflip` or `P!flip` - Flip a coin (2% chance to land on side!)\n"
                "`P!8ball <question>` - Ask the magic 8-ball a question\n"
                "`P!quote` - Get an unmotivational quote\n"
                "`P!roast [@user]` - Get roasted (or roast someone)\n"
                "`P!compliment [@user]` - Give a wholesome compliment"
            ),
            inline=False
        )
        embed.add_field(
            name="⏰ Utilities",
            value=(
                "`P!remind <time>` - Set a reminder (e.g., `P!remind 30m`)\n"
                "`P!hydrate` - Sarcastic water drinking reminder\n"
                "`P!translate <text> <language>` - Translate text to any language"
            ),
            inline=False
        )
        embed.add_field(
            name="📝 Examples",
            value=(
                "`P!coinflip` - Flip a coin\n"
                "`P!8ball Will I win my next duel?` - Ask a question\n"
                "`P!remind 2h30m` - Set a 2.5 hour reminder\n"
                "`P!translate Hello how are you spanish` - Translate to Spanish"
            ),
            inline=False
        )
        embed.set_footer(text="Have fun! 🎉")
        
    elif category == "admin":
        embed = discord.Embed(
            title="👑 Admin Commands",
            description="Administrative commands (requires Administrator permission)",
            color=discord.Color.dark_purple()
        )
        embed.add_field(
            name="🛡️ Bot Control",
            value=(
                "`P!stop` - Stop bot functionality\n"
                "`P!start` - Start bot functionality\n"
                "`P!reset` - Reset all chi to 0 (with confirmation)"
            ),
            inline=False
        )
        embed.add_field(
            name="🎪 Event Control",
            value=(
                "`P!event party` - Spawn a chi party\n"
                "`P!event chi` - Spawn a chi mini-event\n"
                "`P!event food` - Spawn a food event\n"
                "`P!event garden` - Activate spiritual journey boost (10min)\n"
                "`P!event rare/legendary/eternal` - Spawn artifacts\n"
                "`P!event rift` - Start Rift Event (boss battle)\n"
                "`P!event end` - Force-end all active events"
            ),
            inline=False
        )
        embed.add_field(
            name="🛍️ Shop Management",
            value=(
                "`P!shop <rebirth/chi> <add/remove> <item> <price>` - Manage shops"
            ),
            inline=False
        )
        embed.add_field(
            name="⚔️ Tournament",
            value=(
                "`P!tournament @user1 @user2` - Force a tournament duel\n"
                "`P!tourn @user1 @user2` - Shortcut for tournament"
            ),
            inline=False
        )
        embed.add_field(
            name="👤 User Management",
            value=(
                "`P!blacklist add <user_id>` - Blacklist a user\n"
                "`P!blacklist remove <user_id>` - Remove from blacklist\n"
                "`P!arebirth @user <amount>` - Add rebirths to user\n"
                "`P!rrebirth @user <amount>` - Remove rebirths from user"
            ),
            inline=False
        )
        embed.add_field(
            name="📊 Leaderboards & Statistics",
            value=(
                "`P!team leaderboard` - View team leaderboard (admin only)\n"
                "`P!message <total/human/bot/channel>` - View server message stats"
            ),
            inline=False
        )
        embed.add_field(
            name="🔧 System Monitoring",
            value=(
                "`P!log` - View bot errors, system status, and dev portal\n"
                "└ Shows errors from past hour with message links"
            ),
            inline=False
        )
        embed.add_field(
            name="🌐 Web Admin Panel",
            value="Access `/api/admin` in your browser for full control panel with shop management, duel config, teams overview, and more!",
            inline=False
        )
        
    else:
        embed = discord.Embed(
            title="❌ Invalid Category",
            description=f"Category `{category}` not found.\n\nUse `P!help` to see all available categories!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embed.set_footer(text=f"Category: {category.title()} | Use P!help to see all categories")
    await ctx.send(embed=embed)

@bot.before_invoke
async def check_cooldown_before_command(ctx):
    """Check if user is on cooldown for this specific command before executing."""
    global command_cooldowns
    
    user_id = ctx.author.id
    command_name = ctx.command.name if ctx.command else None
    
    if command_name in ADMIN_BYPASS_COMMANDS:
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return
    
    if command_name not in COOLDOWN_COMMANDS:
        return
    
    on_cooldown, time_remaining = check_command_cooldown(user_id, command_name)
    if on_cooldown:
        time_str = get_cooldown_time_str(time_remaining)
        embed = discord.Embed(
            title="⏱️ Cooldown Active",
            description=f"Please wait **{time_str}** before using `{command_name}` again!\n\nYou can still use other commands!",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, delete_after=10)
        raise commands.CheckFailure(f"User on cooldown for command {command_name}")

@bot.event
async def on_command_completion(ctx):
    """Update user's cooldown for this specific command only after successful execution."""
    user_id = ctx.author.id
    command_name = ctx.command.name if ctx.command else None
    
    if command_name in ADMIN_BYPASS_COMMANDS:
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return
    
    if command_name in COOLDOWN_COMMANDS:
        update_command_cooldown(user_id, command_name)

async def spawn_chi_party(channel):
    """Spawns a chi party with 5 claimable tokens."""
    global chi_party_active, chi_party_tokens, chi_party_claims
    
    if chi_party_active:
        return
    
    chi_party_active = True
    chi_party_tokens = []
    chi_party_claims = {}
    
    for i in range(CHI_PARTY_TOKEN_COUNT):
        chi_amount = random.randint(100, 500)
        chi_party_tokens.append({
            "id": i + 1,
            "amount": chi_amount,
            "claimed_by": None
        })
    
    embed = discord.Embed(
        title="🎉🐼 CHI PARTY!",
        description=f"**{CHI_PARTY_TOKEN_COUNT} Chi Tokens** have spawned!\n\nType `P!claim` to grab one!\nEach token contains **100-500 chi**!",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Available Tokens",
        value=f"{CHI_PARTY_TOKEN_COUNT} tokens remaining",
        inline=False
    )
    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Process commands
    
    global chi_party_messages, pax_active
    
    user_id = message.author.id
    
    if pax_active and user_id not in blacklisted_users:
        current_time = time.time()
        
        global chi_party_last_spawn
        
        chi_party_messages.append((current_time, message.channel.id))
        chi_party_messages = [(t, c) for t, c in chi_party_messages if current_time - t <= CHI_PARTY_WINDOW]
        
        time_since_last_party = current_time - chi_party_last_spawn
        
        if len(chi_party_messages) >= CHI_PARTY_THRESHOLD and not chi_party_active and time_since_last_party >= CHI_PARTY_COOLDOWN:
            channel_counts = {}
            for t, c in chi_party_messages:
                channel_counts[c] = channel_counts.get(c, 0) + 1
            
            for channel_id, count in channel_counts.items():
                if count >= CHI_PARTY_THRESHOLD:
                    chi_party_messages = []
                    channel = bot.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        # Check if this channel is allowed for events (use guild config)
                        guild_id = str(channel.guild.id)
                        event_channel_id = get_config_value(guild_id, "channels.log_channel_id")
                        
                        # Allow spawn if: configured channel matches OR no channel configured (universal fallback)
                        if not event_channel_id or channel.id == int(event_channel_id):
                            # Verify bot has permissions
                            if channel.permissions_for(channel.guild.me).send_messages:
                                await spawn_chi_party(channel)
                                chi_party_last_spawn = current_time
                    break
        
        on_cooldown, time_remaining = check_chi_cooldown(user_id)
        if not on_cooldown:
            chi_awarded = False
            message_lower = message.content.lower()
            
            for secret_word, (min_chi, max_chi) in SECRET_WORDS.items():
                if re.search(r'\b' + re.escape(secret_word) + r'\b', message_lower):
                    secret_chi = random.randint(min_chi, max_chi)
                    rebirth_msg = update_chi(user_id, secret_chi)
                    update_chi_cooldown(user_id)
                    chi_awarded = True
                    try:
                        await message.add_reaction("🎁")
                        await message.add_reaction("✨")
                    except Exception as e:
                        print(f"Failed to add secret word reaction: {e}")
                    await message.channel.send(f"🎁 Secret word found! +{secret_chi} chi!")
                    if rebirth_msg:
                        await message.channel.send(rebirth_msg)
                    break

            if not chi_awarded and check_words(message, POSITIVE_WORDS) and has_context_words(message):
                positive_chi = random.randint(1, 8)  # Harder to earn - avg 4.5 chi (was avg 7 before)
                update_chi(user_id, positive_chi)
                update_chi_cooldown(user_id)
                chi_awarded = True
                
                # React with PandaAngel emoji for positive words
                try:
                    await message.add_reaction("<:PandaAngel:1413967718972915843>")
                except Exception as e:
                    print(f"Failed to add positive word reaction: {e}")
                
                # Track positive words for tutorial quest 0
                user_id_str = str(user_id)
                if user_id_str in chi_data:
                    if "positive_word_count" not in chi_data[user_id_str]:
                        chi_data[user_id_str]["positive_word_count"] = 0
                    chi_data[user_id_str]["positive_word_count"] += 1
                    
                    # Auto-complete quest 0 when 5 positive words are said
                    if chi_data[user_id_str]["positive_word_count"] >= 5:
                        await auto_complete_tutorial_quest(user_id, 0, message.channel)

            elif not chi_awarded and check_words(message, NEGATIVE_WORDS) and has_context_words(message):
                negative_chi = random.randint(5, 15)
                update_chi(user_id, -negative_chi)
                update_chi_cooldown(user_id)
                chi_awarded = True
                
                # React with PandaDevil emoji for negative words
                try:
                    await message.add_reaction("<:PE_PandaDevil:728260784244654148>")
                except Exception as e:
                    print(f"Failed to add negative word reaction: {e}")

    await bot.process_commands(message)

@bot.command()
async def chi(ctx):
    user_data = chi_data.get(str(ctx.author.id), {"chi": 0, "rebirths": 0})
    chi_score = user_data.get("chi", 0)
    rebirths = user_data.get("rebirths", 0)
    
    embed = discord.Embed(
        title=f"🐼 {ctx.author.display_name}'s Chi",
        description=f"Your current chi: **{chi_score}**",
        color=discord.Color.green() if chi_score >= 0 else discord.Color.red()
    )
    embed.add_field(name="🔄 Total Rebirths", value=str(rebirths), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="chiadd")
async def chi_add(ctx, member: discord.Member, amount: int):
    # PSY-only command (hardcoded user ID restriction)
    if ctx.author.id != 1382187068373074001:
        await ctx.send("❌ This command is restricted to PSY only!")
        return
    
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number!")
        return
    
    rebirth_msg = update_chi(member.id, amount)
    new_chi = chi_data[str(member.id)]["chi"]
    
    embed = discord.Embed(
        title="✅ Chi Added",
        description=f"Added **{amount}** chi to {member.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="New Chi Balance", value=f"**{new_chi}**")
    await ctx.send(embed=embed)
    if rebirth_msg:
        await ctx.send(rebirth_msg)
    
    # Send DM notification to bot owner
    try:
        owner = await bot.fetch_user(PSY_DM_ID)
        dm_embed = discord.Embed(
            title="🔔 Chi Add Command Used",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        dm_embed.add_field(name="👤 Used By", value=f"{ctx.author} ({ctx.author.id})", inline=False)
        dm_embed.add_field(name="🎯 Target User", value=f"{member} ({member.id})", inline=False)
        dm_embed.add_field(name="💰 Amount Added", value=f"+{amount} chi", inline=True)
        dm_embed.add_field(name="💚 New Balance", value=f"{new_chi} chi", inline=True)
        dm_embed.add_field(name="🏰 Server", value=f"{ctx.guild.name} (ID: {ctx.guild.id})", inline=False)
        dm_embed.set_footer(text=f"Command: P!chiadd")
        await owner.send(embed=dm_embed)
    except Exception as e:
        print(f"Failed to send DM notification: {e}")

@bot.command(name="chiremove")
@is_bot_owner()
async def chi_remove(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number!")
        return
    
    rebirth_msg = update_chi(member.id, -amount)
    new_chi = chi_data[str(member.id)]["chi"]
    
    embed = discord.Embed(
        title="✅ Chi Removed",
        description=f"Removed **{amount}** chi from {member.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name="New Chi Balance", value=f"**{new_chi}**")
    await ctx.send(embed=embed)
    if rebirth_msg:
        await ctx.send(rebirth_msg)
    
    # Send DM notification to bot owner
    try:
        owner = await bot.fetch_user(PSY_DM_ID)
        dm_embed = discord.Embed(
            title="🔔 Chi Remove Command Used",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        dm_embed.add_field(name="👤 Used By", value=f"{ctx.author} ({ctx.author.id})", inline=False)
        dm_embed.add_field(name="🎯 Target User", value=f"{member} ({member.id})", inline=False)
        dm_embed.add_field(name="💸 Amount Removed", value=f"-{amount} chi", inline=True)
        dm_embed.add_field(name="💔 New Balance", value=f"{new_chi} chi", inline=True)
        dm_embed.add_field(name="🏰 Server", value=f"{ctx.guild.name} (ID: {ctx.guild.id})", inline=False)
        dm_embed.set_footer(text=f"Command: P!chiremove")
        await owner.send(embed=dm_embed)
    except Exception as e:
        print(f"Failed to send DM notification: {e}")

@chi_add.error
async def chi_add_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command! Only administrators can manage chi.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Please mention a valid member.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `P!chiadd @member amount`")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

@chi_remove.error
async def chi_remove_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command! Only administrators can manage chi.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Please mention a valid member.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `P!chiremove @member amount`")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

@bot.command(name="arebirth")
@is_bot_owner()
async def add_rebirth(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number!")
        return
    
    user_id = str(member.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    chi_data[user_id]["rebirths"] = chi_data[user_id].get("rebirths", 0) + amount
    save_data()
    
    total_rebirths = chi_data[user_id].get("rebirths", 0)
    
    embed = discord.Embed(
        title="✅ Rebirths Added",
        description=f"Added **{amount}** rebirth{'s' if amount > 1 else ''} to {member.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="🔄 Total Rebirths", value=str(total_rebirths), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="rrebirth")
@is_bot_owner()
async def remove_rebirth(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number!")
        return
    
    user_id = str(member.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    current_rebirths = chi_data[user_id].get("rebirths", 0)
    
    if current_rebirths < amount:
        await ctx.send(f"❌ Cannot remove {amount} rebirths! {member.mention} only has **{current_rebirths}** rebirths.")
        return
    
    chi_data[user_id]["rebirths"] = current_rebirths - amount
    save_data()
    
    total_rebirths = chi_data[user_id].get("rebirths", 0)
    
    embed = discord.Embed(
        title="✅ Rebirths Removed",
        description=f"Removed **{amount}** rebirth{'s' if amount > 1 else ''} from {member.mention}",
        color=discord.Color.red()
    )
    embed.add_field(name="🔄 Total Rebirths", value=str(total_rebirths), inline=True)
    await ctx.send(embed=embed)

@add_rebirth.error
async def add_rebirth_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command! Only administrators can manage rebirths.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Please mention a valid member.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `P!arebirth <amount> @member`")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

@remove_rebirth.error
async def remove_rebirth_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command! Only administrators can manage rebirths.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Please mention a valid member.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Usage: `P!rrebirth <amount> @member`")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

# ==================== SERVER SETUP COMMAND ====================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """🔧 Interactive server setup wizard for Panda Bot
    
    This command helps you configure the bot for your Discord server.
    It can automatically create channels, set up roles, and configure all features.
    
    **Requirements:** You must be a server administrator to use this command.
    """
    embed = discord.Embed(
        title="🐼 Welcome to Panda Bot Setup!",
        description=(
            "This wizard will help you configure the bot for your server.\n\n"
            "**What will be configured:**\n"
            "✨ Event Logging Channel\n"
            "🌱 Garden System Channels\n"
            "⚔️ Dueling & Combat Channels\n"
            "🐾 Pet System Channels\n"
            "👑 Admin Roles\n"
            "🎭 Chi Reward Roles\n\n"
            "React with ✅ to start automatic setup, or ❌ to cancel."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="You can also configure manually with P!config later!")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await ctx.send("❌ Setup cancelled!")
            return
        
        # Start automatic setup
        await ctx.send("🔧 Starting automatic setup... This will create channels and configure the bot!")
        
        guild = ctx.guild
        
        # Track what was created
        created_roles = []
        created_channels = []
        
        # Create category for bot channels
        category = await guild.create_category("🐼 Panda Bot")
        
        # Create or find log channel
        log_channel = discord.utils.get(guild.text_channels, name="panda-bot-logs")
        if not log_channel:
            log_channel = await guild.create_text_channel("panda-bot-logs", category=category)
            # Set permissions: read-only for @everyone, send for bot
            await log_channel.set_permissions(guild.default_role, read_messages=True, send_messages=False)
            await log_channel.set_permissions(guild.me, read_messages=True, send_messages=True)
            created_channels.append(f"📊 {log_channel.mention} - Event logging")
        
        # Create other channels if they don't exist
        garden_channel = discord.utils.get(guild.text_channels, name="panda-garden")
        if not garden_channel:
            garden_channel = await guild.create_text_channel("panda-garden", category=category)
            created_channels.append(f"🌱 {garden_channel.mention} - Garden system")
        
        duel_channel = discord.utils.get(guild.text_channels, name="panda-duels")
        if not duel_channel:
            duel_channel = await guild.create_text_channel("panda-duels", category=category)
            created_channels.append(f"⚔️ {duel_channel.mention} - Dueling & combat")
        
        pet_channel = discord.utils.get(guild.text_channels, name="panda-pets")
        if not pet_channel:
            pet_channel = await guild.create_text_channel("panda-pets", category=category)
            created_channels.append(f"🐾 {pet_channel.mention} - Pet system")
        
        updates_channel = discord.utils.get(guild.text_channels, name="panda-updates")
        if not updates_channel:
            updates_channel = await guild.create_text_channel("panda-updates", category=category)
            created_channels.append(f"📢 {updates_channel.mention} - Bot updates")
        
        # Update config with new channels
        channel_updates = {
            "channels": {
                "log_channel_id": log_channel.id,
                "garden_channels": [garden_channel.id],
                "duel_channels": [duel_channel.id],
                "pet_channels": [pet_channel.id],
                "updates_channel_id": updates_channel.id
            },
            "features": {
                "setup_complete": True
            }
        }
        
        # Create roles if they don't exist
        role_ids = {}
        try:
            # Check for Positive Chi role
            positive_role = discord.utils.get(guild.roles, name="Positive Chi")
            if not positive_role:
                positive_role = await guild.create_role(name="Positive Chi", color=discord.Color.green())
                created_roles.append(f"💚 **Positive Chi** - Earned by using positive words")
            
            # Check for Negative Chi role
            negative_role = discord.utils.get(guild.roles, name="Negative Chi")
            if not negative_role:
                negative_role = await guild.create_role(name="Negative Chi", color=discord.Color.red())
                created_roles.append(f"❤️ **Negative Chi** - Given for using negative words")
            
            # Check for Quest Completer role
            quest_role = discord.utils.get(guild.roles, name="Quest Completer")
            if not quest_role:
                quest_role = await guild.create_role(name="Quest Completer", color=discord.Color.gold())
                created_roles.append(f"🏆 **Quest Completer** - Awarded for completing tutorial quests")
            
            role_ids = {
                "positive_role_id": positive_role.id,
                "negative_role_id": negative_role.id,
                "quest_completer_role_id": quest_role.id
            }
            channel_updates["roles"] = role_ids
        except discord.Forbidden:
            await ctx.send("⚠️ I don't have permission to create roles! You can set them up manually later with `P!config`")
        
        # Save configuration for THIS guild
        config = update_guild_config(guild.id, channel_updates)
        
        # Send success message
        success_embed = discord.Embed(
            title="✅ Panda Bot Setup Complete!",
            description="Your server is now fully configured for Panda Bot!",
            color=discord.Color.green()
        )
        
        if created_channels:
            success_embed.add_field(
                name="📝 Channels Created",
                value="\n".join(created_channels),
                inline=False
            )
        else:
            success_embed.add_field(
                name="📝 Channels",
                value="All channels already exist! ✓",
                inline=False
            )
        
        if created_roles:
            success_embed.add_field(
                name="🎭 Roles Created",
                value="\n".join(created_roles),
                inline=False
            )
        else:
            success_embed.add_field(
                name="🎭 Roles",
                value="All roles already exist! ✓",
                inline=False
            )
        
        success_embed.add_field(
            name="🚀 Next Steps",
            value=(
                "• Use `P!help` to see all available commands\n"
                "• Use `P!tutorial` to start the interactive tutorial\n"
                "• Use `P!config` to view or modify settings\n"
                "• Start earning chi by sending positive messages!"
            ),
            inline=False
        )
        success_embed.set_footer(text="Welcome to the Panda Gang Community! 🐼")
        
        await ctx.send(embed=success_embed)
        
        # Send welcome message to log channel
        welcome_embed = discord.Embed(
            title="🐼 Panda Bot is Now Active!",
            description=(
                "This channel will log all important bot events:\n"
                "• Chi milestones and rebirths\n"
                "• Artifact claims\n"
                "• Team events\n"
                "• Boss battle victories\n"
                "• And more!"
            ),
            color=discord.Color.blue()
        )
        await log_channel.send(embed=welcome_embed)
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Setup timed out! Run `P!setup` again when you're ready.")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permissions to run setup!")
    else:
        await ctx.send(f"❌ Setup error: {error}")

# ==================== CONFIG COMMAND ====================
@bot.command(name="config")
@commands.has_permissions(administrator=True)
async def config_command(ctx, action: str = None, setting: str = None, *, value: str = None):
    """View or modify server configuration (Admin only)"""
    
    guild_id = ctx.guild.id
    config = get_guild_config(guild_id)
    
    if not action:
        # Show current configuration
        embed = discord.Embed(
            title="⚙️ Server Configuration",
            description=f"Configuration for **{ctx.guild.name}**",
            color=discord.Color.blue()
        )
        
        # Channels
        channels_text = []
        log_ch = ctx.guild.get_channel(config["channels"].get("log_channel_id")) if config["channels"].get("log_channel_id") else None
        updates_ch = ctx.guild.get_channel(config["channels"].get("updates_channel_id")) if config["channels"].get("updates_channel_id") else None
        
        channels_text.append(f"📊 **Log Channel:** {log_ch.mention if log_ch else 'Not set'}")
        channels_text.append(f"📢 **Updates Channel:** {updates_ch.mention if updates_ch else 'Not set'}")
        
        # Garden channels
        garden_chs = [ctx.guild.get_channel(ch_id) for ch_id in config["channels"].get("garden_channels", [])]
        garden_chs = [ch for ch in garden_chs if ch]
        if garden_chs:
            channels_text.append(f"🌱 **Garden Channels:** {', '.join(ch.mention for ch in garden_chs)}")
        
        embed.add_field(
            name="📝 Channels",
            value="\n".join(channels_text) if channels_text else "No channels configured",
            inline=False
        )
        
        # Roles
        roles_text = []
        positive_role = ctx.guild.get_role(config["roles"].get("positive_role_id")) if config["roles"].get("positive_role_id") else None
        negative_role = ctx.guild.get_role(config["roles"].get("negative_role_id")) if config["roles"].get("negative_role_id") else None
        quest_role = ctx.guild.get_role(config["roles"].get("quest_completer_role_id")) if config["roles"].get("quest_completer_role_id") else None
        
        roles_text.append(f"✨ **Positive Role:** {positive_role.mention if positive_role else 'Not set'}")
        roles_text.append(f"😈 **Negative Role:** {negative_role.mention if negative_role else 'Not set'}")
        roles_text.append(f"🎯 **Quest Master:** {quest_role.mention if quest_role else 'Not set'}")
        
        embed.add_field(
            name="🎭 Roles",
            value="\n".join(roles_text),
            inline=False
        )
        
        # Features
        setup_status = "✅ Complete" if config["features"].get("setup_complete") else "❌ Incomplete"
        embed.add_field(
            name="🚀 Status",
            value=f"**Setup:** {setup_status}",
            inline=False
        )
        
        embed.set_footer(text="Use P!config set <setting> <value> to change settings")
        await ctx.send(embed=embed)
        
    elif action.lower() == "set" and setting and value:
        # Set a configuration value
        setting = setting.lower().replace("-", "_")
        
        # Parse channel/role mentions
        if setting in ["log_channel", "updates_channel"]:
            # Extract channel ID from mention
            channel = None
            if value.startswith("<#") and value.endswith(">"):
                channel_id = int(value[2:-1])
                channel = ctx.guild.get_channel(channel_id)
            else:
                try:
                    channel_id = int(value)
                    channel = ctx.guild.get_channel(channel_id)
                except ValueError:
                    await ctx.send(f"❌ Invalid channel! Please mention a channel or provide a channel ID.")
                    return
            
            if not channel:
                await ctx.send(f"❌ Channel not found!")
                return
            
            # Update config
            config_key = f"{setting}_id"
            updates = {"channels": {config_key: channel.id}}
            update_guild_config(guild_id, updates)
            await ctx.send(f"✅ Set {setting.replace('_', ' ').title()} to {channel.mention}")
            
        elif setting in ["positive_role", "negative_role", "quest_role"]:
            # Extract role ID from mention
            role = None
            if value.startswith("<@&") and value.endswith(">"):
                role_id = int(value[3:-1])
                role = ctx.guild.get_role(role_id)
            else:
                try:
                    role_id = int(value)
                    role = ctx.guild.get_role(role_id)
                except ValueError:
                    await ctx.send(f"❌ Invalid role! Please mention a role or provide a role ID.")
                    return
            
            if not role:
                await ctx.send(f"❌ Role not found!")
                return
            
            # Map setting names to config keys
            role_mapping = {
                "positive_role": "positive_role_id",
                "negative_role": "negative_role_id",
                "quest_role": "quest_completer_role_id"
            }
            
            config_key = role_mapping.get(setting)
            if config_key:
                updates = {"roles": {config_key: role.id}}
                update_guild_config(guild_id, updates)
                await ctx.send(f"✅ Set {setting.replace('_', ' ').title()} to {role.mention}")
        else:
            await ctx.send(f"❌ Unknown setting: `{setting}`\n\nAvailable settings:\n**Channels:** log_channel, updates_channel\n**Roles:** positive_role, negative_role, quest_role")
    
    elif action.lower() == "help":
        help_embed = discord.Embed(
            title="⚙️ Config Command Help",
            description="Manage your server's bot configuration",
            color=discord.Color.blue()
        )
        help_embed.add_field(
            name="📖 Commands",
            value=(
                "`P!config` - View current configuration\n"
                "`P!config set <setting> <value>` - Change a setting\n"
                "`P!config help` - Show this help message"
            ),
            inline=False
        )
        help_embed.add_field(
            name="⚙️ Available Settings",
            value=(
                "**Channels:**\n"
                "• `log_channel` - Where bot events are logged\n"
                "• `updates_channel` - Bot update announcements\n\n"
                "**Roles:**\n"
                "• `positive_role` - Role for positive chi earners\n"
                "• `negative_role` - Role for negative word users\n"
                "• `quest_role` - Role for quest completers"
            ),
            inline=False
        )
        help_embed.add_field(
            name="📝 Examples",
            value=(
                "`P!config set log_channel #panda-logs`\n"
                "`P!config set positive_role @Positive Vibes`"
            ),
            inline=False
        )
        await ctx.send(embed=help_embed)
    else:
        await ctx.send("❌ Invalid usage! Use `P!config help` for instructions.")

@config_command.error
async def config_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permissions to manage server configuration!")
    else:
        await ctx.send(f"❌ Config error: {error}")

# ==================== HIDDEN ADMIN COMMAND (PSY ONLY) ====================
@bot.group(name="psy", invoke_without_command=True, hidden=True)
async def psy_admin(ctx):
    """Hidden admin command for testing (PSY only)"""
    # Only allow user ID 1382187068373074001
    if ctx.author.id != 1382187068373074001:
        return
    
    embed = discord.Embed(
        title="🔧 PSY Admin Commands",
        description="Full admin control panel",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="📦 Give/Remove Items",
        value=(
            "`P!psy give <category> <name>` - Give items with validation\n"
            "`P!psy remove <category> <name>` - Remove items\n"
            "**Categories:** pet, weapon, potion, artifact, food, tool, chi, rebirth"
        ),
        inline=False
    )
    embed.add_field(
        name="👁️ Inspect Users",
        value=(
            "`P!psy inspect @user` - View user stats\n"
            "`P!psy reset @user` - Reset user data\n"
            "`P!psy admin garden/inv/team/base @user` - View user data"
        ),
        inline=False
    )
    embed.add_field(
        name="🌸 Quick Reference",
        value=(
            "**Pets:** Ox, Snake, Tiger, Panda, Dragon\n"
            "**Weapons:** Use codes (C1, K1, BS1, etc.)\n"
            "**Artifacts:** Common, Rare, Legendary, Eternal, Mythical"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@psy_admin.command(name="guilds", hidden=True)
async def psy_guilds(ctx):
    """Show all guilds the bot is connected to (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    embed = discord.Embed(
        title="🌐 Connected Guilds",
        description=f"Bot is monitoring {len(bot.guilds)} guild(s)",
        color=discord.Color.blue()
    )
    
    for guild in bot.guilds:
        members = len(guild.members)
        embed.add_field(
            name=f"🏰 {guild.name}",
            value=f"**ID:** `{guild.id}`\n**Members:** {members}\n**Owner:** {guild.owner}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@psy_admin.command(name="give", hidden=True)
async def psy_give(ctx, member: discord.Member = None, category: str = "", *, item_name: str = ""):
    """Give any user any item with category validation (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    # If member is provided, use them; otherwise use yourself
    target_user = member if member else ctx.author
    
    if not category or not item_name:
        await ctx.send("❌ Usage: `P!psy give [@user] <category> <name>`\n"
                      "**Examples:**\n"
                      "`P!psy give @user pet Panda` - Give user a Panda pet\n"
                      "`P!psy give pet Panda` - Give yourself a Panda pet\n"
                      "`P!psy give @user chi 50000` - Give user 50k chi\n"
                      "`P!psy give weapon C2` - Give yourself weapon C2\n"
                      "`P!psy give @user artifact Legendary` - Give user legendary artifact")
        return
    
    user_id = str(target_user.id)
    
    # Initialize user data
    if user_id not in chi_data:
        chi_data[user_id] = {
            "chi": 0,
            "rebirths": 0,
            "milestones_claimed": [],
            "mini_quests": [],
            "purchased_items": [],
            "inventory": {},
            "pets": [],
            "active_pet": None,
            "chest": []
        }
    
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    if "pets" not in chi_data[user_id]:
        chi_data[user_id]["pets"] = []
    
    category = category.lower()
    
    # CHI
    if category == "chi":
        try:
            amount = int(item_name)
            chi_data[user_id]["chi"] = chi_data[user_id].get("chi", 0) + amount
            save_data()
            await ctx.send(f"✅ Added **{amount:,} chi** to {target_user.mention}!\n💰 New Balance: **{chi_data[user_id]['chi']:,} chi**")
            return
        except ValueError:
            await ctx.send("❌ For chi, provide a number! Example: `P!psy give @user chi 50000`")
            return
    
    # REBIRTH
    if category in ["rebirth", "rebirths"]:
        try:
            amount = int(item_name)
            chi_data[user_id]["rebirths"] = chi_data[user_id].get("rebirths", 0) + amount
            save_data()
            await ctx.send(f"✅ Added **{amount} rebirth(s)** to {target_user.mention}!\n🔄 Total: **{chi_data[user_id]['rebirths']}**")
            return
        except ValueError:
            await ctx.send("❌ For rebirths, provide a number! Example: `P!psy give @user rebirth 10`")
            return
    
    # PET
    if category == "pet":
        pet_key = item_name.lower()
        if pet_key not in PET_DATA:
            await ctx.send(f"❌ Invalid pet! Available: **{', '.join([p['name'] for p in PET_DATA.values()])}**")
            return
        
        # Check if already owns pet
        has_pet = any(p.get("type") == pet_key for p in chi_data[user_id]["pets"])
        if has_pet:
            await ctx.send(f"❌ {target_user.mention} already owns a **{PET_DATA[pet_key]['name']}**!")
            return
        
        # Add pet (matching P!pet buy structure)
        pet_data = {
            "type": pet_key,
            "name": PET_DATA[pet_key]["name"],
            "emoji": PET_DATA[pet_key]["emoji"],
            "nickname": None,
            "health": PET_DATA[pet_key]["base_hp"],
            "max_health": PET_DATA[pet_key]["base_hp"],
            "level": 1,
            "xp": 0,
            "battles_won": 0,
            "battles_lost": 0,
            "purchased_at": datetime.now(timezone.utc).isoformat()
        }
        chi_data[user_id]["pets"].append(pet_data)
        
        # Set as active if first pet
        if not chi_data[user_id].get("active_pet"):
            chi_data[user_id]["active_pet"] = pet_key
        
        save_data()
        await ctx.send(f"✅ Added **{PET_DATA[pet_key]['emoji']} {PET_DATA[pet_key]['name']}** to {target_user.mention}'s collection!\n"
                      f"HP: **{PET_DATA[pet_key]['base_hp']}** | Price: **{PET_DATA[pet_key]['price']:,} chi**")
        return
    
    # WEAPON
    if category == "weapon":
        # Try finding by name in chi shop
        weapon_found = None
        for item in chi_shop_data.get("items", []):
            if item["name"].lower() == item_name.lower():
                weapon_found = item
                break
        
        if not weapon_found:
            # Just add it as a custom weapon
            formatted_weapon = item_name.title()
            chi_data[user_id]["inventory"][formatted_weapon] = chi_data[user_id]["inventory"].get(formatted_weapon, 0) + 1
            save_data()
            await ctx.send(f"✅ Added **⚔️ {formatted_weapon}** to inventory!")
            return
        
        # Add found weapon to inventory
        chi_data[user_id]["inventory"][weapon_found["name"]] = chi_data[user_id]["inventory"].get(weapon_found["name"], 0) + 1
        save_data()
        await ctx.send(f"✅ Added **⚔️ {weapon_found['name']}**!\n"
                      f"Price: **{weapon_found['cost']:,} chi**")
        return
    
    # POTION
    if category == "potion":
        potion_found = None
        for potion_key, potion_data in POTION_CATALOG.items():
            if potion_data["name"].lower() == item_name.lower():
                potion_found = potion_data
                break
        
        if not potion_found:
            await ctx.send(f"❌ Potion not found! Available potions: **Healing Potion, Phoenix Elixir, Dragon's Blessing**, etc.")
            return
        
        # Add to inventory
        chi_data[user_id]["inventory"][potion_found["name"]] = chi_data[user_id]["inventory"].get(potion_found["name"], 0) + 1
        save_data()
        await ctx.send(f"✅ Added **{potion_found['emoji']} {potion_found['name']}**!\n"
                      f"Rarity: **{potion_found['rarity']}** | Effect: **{potion_found['description']}**")
        return
    
    # ARTIFACT
    if category == "artifact":
        tier = item_name.lower()
        if tier not in ARTIFACT_CONFIG:
            await ctx.send(f"❌ Invalid tier! Available: **{', '.join(ARTIFACT_CONFIG.keys())}**")
            return
        
        # Generate random artifact from tier
        import random
        artifact_emoji = random.choice(ARTIFACT_CONFIG[tier]["emojis"])
        artifact_name = random.choice(ARTIFACT_CONFIG[tier]["names"])
        
        # Add to inventory
        artifact_key = f"{tier.capitalize()} Artifact: {artifact_name}"
        chi_data[user_id]["inventory"][artifact_key] = chi_data[user_id]["inventory"].get(artifact_key, 0) + 1
        save_data()
        await ctx.send(f"✅ Added **{artifact_emoji} {tier.capitalize()} Artifact: {artifact_name}**!\n"
                      f"Heal Power: **{ARTIFACT_CONFIG[tier]['heal_percent']}%**")
        return
    
    # FOOD/TOOL (generic inventory items)
    if category in ["food", "tool", "item"]:
        formatted_item = item_name.title()
        chi_data[user_id]["inventory"][formatted_item] = chi_data[user_id]["inventory"].get(formatted_item, 0) + 1
        save_data()
        await ctx.send(f"✅ Added **{formatted_item}** to inventory!")
        return
    
    # Invalid category
    await ctx.send("❌ Invalid category! Use: **pet, weapon, potion, artifact, food, tool, chi, rebirth**")

@psy_admin.command(name="remove", hidden=True)
async def psy_remove(ctx, category: str = "", *, item_name: str = ""):
    """Remove items from inventory (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not category or not item_name:
        await ctx.send("❌ Usage: `P!psy remove <category> <item>`\n"
                      "**Examples:**\n"
                      "`P!psy remove pet Panda` - Remove Panda pet\n"
                      "`P!psy remove weapon Katana` - Remove Katana\n"
                      "`P!psy remove potion Healing Potion` - Remove potion")
        return
    
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data:
        await ctx.send("❌ No user data found!")
        return
    
    category = category.lower()
    
    # Remove pet
    if category == "pet":
        pet_key = item_name.lower()
        if "pets" not in chi_data[user_id]:
            await ctx.send("❌ No pets found!")
            return
        
        # Find and remove pet
        removed = False
        for i, pet in enumerate(chi_data[user_id]["pets"]):
            if pet.get("type") == pet_key:
                chi_data[user_id]["pets"].pop(i)
                removed = True
                # Clear active pet if it was this one
                if chi_data[user_id].get("active_pet") == pet_key:
                    chi_data[user_id]["active_pet"] = None
                break
        
        if removed:
            save_data()
            await ctx.send(f"✅ Removed **{item_name.capitalize()}** pet!")
        else:
            await ctx.send(f"❌ Pet **{item_name.capitalize()}** not found in collection!")
        return
    
    # Remove from inventory
    if category in ["weapon", "potion", "food", "tool", "item", "artifact"]:
        if "inventory" not in chi_data[user_id]:
            await ctx.send("❌ No inventory found!")
            return
        
        # Try exact match first
        if item_name in chi_data[user_id]["inventory"]:
            del chi_data[user_id]["inventory"][item_name]
            save_data()
            await ctx.send(f"✅ Removed **{item_name}** from inventory!")
            return
        
        # Try title case
        formatted_item = item_name.title()
        if formatted_item in chi_data[user_id]["inventory"]:
            del chi_data[user_id]["inventory"][formatted_item]
            save_data()
            await ctx.send(f"✅ Removed **{formatted_item}** from inventory!")
            return
        
        # Try finding partial match
        for inv_item in chi_data[user_id]["inventory"]:
            if item_name.lower() in inv_item.lower():
                del chi_data[user_id]["inventory"][inv_item]
                save_data()
                await ctx.send(f"✅ Removed **{inv_item}** from inventory!")
                return
        
        await ctx.send(f"❌ Item **{item_name}** not found in inventory!")
        return
    
    await ctx.send("❌ Invalid category! Use: **pet, weapon, potion, artifact, food, tool, item**")

@psy_admin.command(name="inspect", hidden=True)
async def psy_inspect(ctx, member: discord.Member = None):
    """View detailed user stats (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        member = ctx.author
    
    user_id = str(member.id)
    
    if user_id not in chi_data:
        await ctx.send(f"❌ **{member.display_name}** has no data!")
        return
    
    data = chi_data[user_id]
    
    embed = discord.Embed(
        title=f"🔍 {member.display_name}'s Profile",
        color=discord.Color.purple()
    )
    
    # Basic stats
    embed.add_field(
        name="💰 Economy",
        value=f"Chi: **{data.get('chi', 0):,}**\nRebirths: **{data.get('rebirths', 0)}**",
        inline=True
    )
    
    # Inventory count
    inv_count = len(data.get("inventory", {}))
    pets_count = len(data.get("pets", []))
    embed.add_field(
        name="📦 Collections",
        value=f"Inventory Items: **{inv_count}**\nPets: **{pets_count}**",
        inline=True
    )
    
    # Active pet
    active_pet = data.get("active_pet")
    if active_pet and active_pet in PET_DATA:
        embed.add_field(
            name="🐼 Active Pet",
            value=f"{PET_DATA[active_pet]['emoji']} **{PET_DATA[active_pet]['name']}**",
            inline=True
        )
    
    # Garden
    if user_id in gardens_data.get("gardens", {}):
        garden = gardens_data["gardens"][user_id]
        plant_count = len(garden.get("plants", []))
        tier = garden.get("tier", "rare")
        embed.add_field(
            name="🌸 Garden",
            value=f"Tier: **{GARDEN_TIERS[tier]['emoji']} {GARDEN_TIERS[tier]['name']}**\nPlants: **{plant_count}**",
            inline=False
        )
    
    await ctx.send(embed=embed)

@psy_admin.command(name="reset", hidden=True)
async def psy_reset(ctx, member: discord.Member = None):
    """Reset user data (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        await ctx.send("❌ Usage: `P!psy reset @user`")
        return
    
    user_id = str(member.id)
    
    if user_id in chi_data:
        del chi_data[user_id]
    
    if user_id in gardens_data.get("gardens", {}):
        del gardens_data["gardens"][user_id]
    
    save_data()
    save_gardens()
    
    await ctx.send(f"✅ Reset all data for **{member.display_name}**!")

# ==================== P!PSY ADMIN SUBCOMMANDS (PSY ONLY) ====================
@psy_admin.group(name="admin", invoke_without_command=True, hidden=True)
async def psy_admin_view(ctx):
    """View user data (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    await ctx.send("**👁️ P!psy admin View Commands**\n"
                  "`P!psy admin garden @user` - View user's garden\n"
                  "`P!psy admin inv @user` - View user's inventory\n"
                  "`P!psy admin team @user` - View user's team\n"
                  "`P!psy admin base @user` - View team base")

@psy_admin_view.command(name="garden", hidden=True)
async def admin_garden(ctx, member: discord.Member = None):
    """View user's garden (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        await ctx.send("❌ Usage: `P!psy admin garden @user`")
        return
    
    user_id = str(member.id)
    
    if user_id not in gardens_data.get("gardens", {}):
        await ctx.send(f"❌ **{member.display_name}** doesn't have a garden!")
        return
    
    garden = gardens_data["gardens"][user_id]
    tier = garden.get("tier", "rare")
    tier_info = GARDEN_TIERS[tier]
    
    embed = discord.Embed(
        title=f"{tier_info['emoji']} {member.display_name}'s Garden",
        description=f"**{tier_info['name']}** (Level {garden.get('level', 1)})",
        color=discord.Color.green()
    )
    
    # Plants
    plant_count = len(garden.get("plants", []))
    max_capacity = tier_info["max_capacity"]
    
    if plant_count > 0:
        plant_list = []
        for plant in garden.get("plants", []):
            plant_name = plant.get("name", "Unknown")
            if plant_name in GARDEN_SHOP_ITEMS["seeds"]:
                seed_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
                plant_list.append(f"{seed_info['emoji']} {plant_name}")
        
        plants_display = "\n".join(plant_list[:10])  # Show first 10
        if plant_count > 10:
            plants_display += f"\n... and {plant_count - 10} more"
        
        embed.add_field(name=f"🌱 Plants ({plant_count}/{max_capacity})", value=plants_display, inline=False)
    else:
        embed.add_field(name=f"🌱 Plants (0/{max_capacity})", value="No plants", inline=False)
    
    await ctx.send(embed=embed)

@psy_admin_view.command(name="inv", hidden=True)
async def admin_inv(ctx, member: discord.Member = None):
    """View user's inventory (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        await ctx.send("❌ Usage: `P!psy admin inv @user`")
        return
    
    user_id = str(member.id)
    
    if user_id not in chi_data:
        await ctx.send(f"❌ **{member.display_name}** has no data!")
        return
    
    inventory = chi_data[user_id].get("inventory", {})
    
    embed = discord.Embed(
        title=f"📦 {member.display_name}'s Inventory",
        description=f"Total Items: **{len(inventory)}**",
        color=discord.Color.blue()
    )
    
    if inventory:
        # Show first 15 items
        items_list = []
        for i, (item, qty) in enumerate(list(inventory.items())[:15]):
            if isinstance(qty, int):
                items_list.append(f"{item} x**{qty}**")
            else:
                items_list.append(f"{item}")
        
        embed.add_field(name="Items", value="\n".join(items_list), inline=False)
        
        if len(inventory) > 15:
            embed.set_footer(text=f"... and {len(inventory) - 15} more items")
    else:
        embed.add_field(name="Items", value="Empty inventory", inline=False)
    
    await ctx.send(embed=embed)

@psy_admin_view.command(name="team", hidden=True)
async def admin_team(ctx, member: discord.Member = None):
    """View user's team (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        await ctx.send("❌ Usage: `P!psy admin team @user`")
        return
    
    user_id = str(member.id)
    
    # Check if user is on a team
    user_team = None
    for team_name, team_data in teams_data.items():
        if user_id in team_data.get("members", []):
            user_team = (team_name, team_data)
            break
    
    if not user_team:
        await ctx.send(f"❌ **{member.display_name}** is not on a team!")
        return
    
    team_name, team_data = user_team
    
    embed = discord.Embed(
        title=f"🏆 {team_name}",
        description=f"**{member.display_name}** is a member",
        color=discord.Color.gold()
    )
    
    # Team stats
    member_count = len(team_data.get("members", []))
    score = team_data.get("score", 0)
    
    embed.add_field(name="👥 Members", value=str(member_count), inline=True)
    embed.add_field(name="⭐ Score", value=str(score), inline=True)
    
    # Leader
    leader_id = team_data.get("leader")
    if leader_id:
        leader = ctx.guild.get_member(int(leader_id))
        if leader:
            embed.add_field(name="👑 Leader", value=leader.display_name, inline=True)
    
    await ctx.send(embed=embed)

@psy_admin_view.command(name="base", hidden=True)
async def admin_base(ctx, member: discord.Member = None):
    """View team base (PSY ONLY)"""
    if ctx.author.id != 1382187068373074001:
        return
    
    if not member:
        await ctx.send("❌ Usage: `P!psy admin base @user`")
        return
    
    user_id = str(member.id)
    
    # Find user's team
    user_team = None
    for team_name, team_data in teams_data.items():
        if user_id in team_data.get("members", []):
            user_team = (team_name, team_data)
            break
    
    if not user_team:
        await ctx.send(f"❌ **{member.display_name}** is not on a team!")
        return
    
    team_name, team_data = user_team
    base = team_data.get("base", {})
    
    embed = discord.Embed(
        title=f"🏠 {team_name}'s Base",
        color=discord.Color.dark_gold()
    )
    
    # Decorations
    decorations = base.get("decorations", [])
    if decorations:
        embed.add_field(name="🎨 Decorations", value=", ".join(decorations[:5]), inline=False)
    
    # Equipment
    equipment = base.get("equipment", [])
    if equipment:
        embed.add_field(name="💪 Gym Equipment", value=", ".join(equipment[:5]), inline=False)
    
    # Upgrades
    upgrades = base.get("upgrades", {})
    if upgrades:
        upgrade_list = [f"{k}: Lv{v}" for k, v in upgrades.items()]
        embed.add_field(name="⬆️ Upgrades", value=", ".join(upgrade_list), inline=False)
    
    if not decorations and not equipment and not upgrades:
        embed.description = "Base has no decorations or upgrades yet"
    
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx, category: str = "chi"):
    """Show different leaderboards - Usage: P!leaderboard <chi/rebirth/team/artifact>"""
    category = category.lower()
    
    if category == "chi":
        sorted_chi = sorted(chi_data.items(), key=lambda x: x[1]["chi"], reverse=True)
        embed = discord.Embed(
            title="🐼 Top Chi Earners",
            description="Top 10 users with the most chi!",
            color=discord.Color.gold()
        )
        for i, (user_id_str, data) in enumerate(sorted_chi[:10], start=1):
            member = ctx.guild.get_member(int(user_id_str))
            if member:
                emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🐼"
                rebirths = data.get("rebirths", 0)
                rebirth_text = f" | 🔄{rebirths}" if rebirths > 0 else ""
                embed.add_field(
                    name=f"{emoji} #{i} - {member.display_name}",
                    value=f"**Chi:** {data['chi']:,}{rebirth_text}",
                    inline=False
                )
        embed.set_footer(text="Keep earning positive chi to climb the ranks! 🌟")
        
    elif category == "rebirth":
        sorted_rebirths = sorted(
            chi_data.items(),
            key=lambda x: x[1].get("rebirths", 0),
            reverse=True
        )
        embed = discord.Embed(
            title="🔄 Top Rebirth Masters",
            description="Top 5 users with the most rebirths!",
            color=discord.Color.purple()
        )
        count = 0
        for user_id_str, data in sorted_rebirths:
            rebirths = data.get("rebirths", 0)
            if rebirths > 0:
                member = ctx.guild.get_member(int(user_id_str))
                if member:
                    count += 1
                    emoji = "👑" if count == 1 else "🥈" if count == 2 else "🥉" if count == 3 else "⭐"
                    chi = data.get("chi", 0)
                    embed.add_field(
                        name=f"{emoji} #{count} - {member.display_name}",
                        value=f"**Rebirths:** {rebirths} | **Chi:** {chi:,}",
                        inline=False
                    )
                    if count >= 5:
                        break
        if count == 0:
            embed.description = "No one has rebirthed yet! Reach ±100,000 chi to rebirth!"
        embed.set_footer(text="Rebirth at ±100,000 chi to reset and gain power! 🔄")
        
    elif category == "team":
        if "teams" not in teams_data or not teams_data["teams"]:
            embed = discord.Embed(
                title="👥 Team Leaderboard",
                description="No teams have been created yet! Use `P!team create` to start one!",
                color=discord.Color.blue()
            )
        else:
            sorted_teams = sorted(
                teams_data["teams"].items(),
                key=lambda x: x[1].get("team_score", 0),
                reverse=True
            )
            embed = discord.Embed(
                title="👥 Top Teams",
                description="Top 3 teams with the highest scores!",
                color=discord.Color.blue()
            )
            for i, (team_id, team_data) in enumerate(sorted_teams[:3], start=1):
                emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉"
                team_name = team_data.get("name", "Unknown Team")
                team_score = team_data.get("team_score", 0)
                member_count = len(team_data.get("members", []))
                duel_stats = team_data.get("duel_stats", {})
                wins = duel_stats.get("wins", 0)
                losses = duel_stats.get("losses", 0)
                
                value_text = f"**Score:** {team_score:,}\n**Members:** {member_count}\n**Duels:** {wins}W - {losses}L"
                embed.add_field(
                    name=f"{emoji} #{i} - {team_name}",
                    value=value_text,
                    inline=False
                )
            embed.set_footer(text="Build your team and dominate the leaderboard! 💪")
            
    elif category == "artifact":
        users_with_artifacts = []
        for user_id_str, data in chi_data.items():
            artifacts = data.get("artifacts", [])
            if artifacts:
                artifact_count = len(artifacts)
                users_with_artifacts.append((user_id_str, artifact_count, artifacts))
        
        sorted_artifacts = sorted(users_with_artifacts, key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="💎 Top Artifact Collectors",
            description="Top 7 users with the most artifacts!",
            color=discord.Color.from_rgb(138, 43, 226)
        )
        
        if not sorted_artifacts:
            embed.description = "No artifacts have been collected yet! Wait for them to spawn!"
        else:
            for i, (user_id_str, count, artifacts) in enumerate(sorted_artifacts[:7], start=1):
                member = ctx.guild.get_member(int(user_id_str))
                if member:
                    emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "💎"
                    
                    rare_count = sum(1 for a in artifacts if a.get("tier") == "rare")
                    legendary_count = sum(1 for a in artifacts if a.get("tier") == "legendary")
                    eternal_count = sum(1 for a in artifacts if a.get("tier") == "eternal")
                    
                    value_text = f"**Total:** {count} artifacts\n"
                    if rare_count > 0:
                        value_text += f"💎 Rare: {rare_count} "
                    if legendary_count > 0:
                        value_text += f"👑 Legendary: {legendary_count} "
                    if eternal_count > 0:
                        value_text += f"🌌 Eternal: {eternal_count}"
                    
                    embed.add_field(
                        name=f"{emoji} #{i} - {member.display_name}",
                        value=value_text,
                        inline=False
                    )
        embed.set_footer(text="Artifacts spawn randomly! Be quick to claim them! ⚡")
        
    else:
        embed = discord.Embed(
            title="❌ Invalid Category",
            description="Please use one of these categories:\n\n"
                       "**`P!leaderboard chi`** - Top 10 chi earners\n"
                       "**`P!leaderboard rebirth`** - Top 5 rebirth masters\n"
                       "**`P!leaderboard team`** - Top 3 teams by score\n"
                       "**`P!leaderboard artifact`** - Top 7 artifact collectors",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

@bot.command(name="Month")
async def month_reset(ctx):
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You are not authorized to reset quests.")
        return
    theme_name, quests = get_current_theme()
    quest_data["quests"] = quests
    quest_data["month"] = theme_name
    quest_data["user_progress"] = {}
    save_quests()
    embed = discord.Embed(title=f"🎯 {theme_name} Quests for this Month", color=discord.Color.orange())
    for q in quests:
        embed.add_field(name="\u200b", value=q, inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def see(ctx):
    user_id = str(ctx.author.id)
    completed = quest_data["user_progress"].get(user_id, [])
    embed = discord.Embed(title=f"✅ {ctx.author.display_name}'s Completed Quests", color=discord.Color.green())
    if not completed:
        embed.description = "You haven't completed any quests yet!"
    else:
        for i in completed:
            embed.add_field(name="\u200b", value=quest_data["quests"][i], inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def todo(ctx):
    user_id_str = str(ctx.author.id)
    completed = quest_data["user_progress"].get(user_id_str, [])
    remaining = [q for i, q in enumerate(quest_data["quests"]) if i not in completed]
    embed = discord.Embed(title=f"📝 {ctx.author.display_name}'s Quests To Do", color=discord.Color.blue())
    if not remaining:
        embed.description = "✅ You have completed all quests!"
    else:
        for q in remaining:
            embed.add_field(name="\u200b", value=q, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="tutorial", aliases=["tut", "guide"])
async def tutorial_command(ctx):
    """Display tutorial quest progress and available quests"""
    user_id = str(ctx.author.id)
    
    # Read from quest_data where tutorial quests are actually stored
    completed_quests = quest_data["user_progress"].get(user_id, [])
    
    # Create embed
    embed = discord.Embed(
        title="🐼 Tutorial Quest System",
        description="Complete these quests to learn how to use the bot and earn chi!",
        color=discord.Color.blue()
    )
    
    # Add quest fields
    for i, quest in enumerate(TUTORIAL_QUESTS):
        status = "✅" if i in completed_quests else "❌"
        quest_text = quest.split("\n")[0]  # Just the title
        quest_details = "\n".join(quest.split("\n")[1:])  # Details and reward
        
        embed.add_field(
            name=f"{status} {quest_text}",
            value=quest_details,
            inline=False
        )
    
    # Add progress footer
    total_quests = len(TUTORIAL_QUESTS)
    completed_count = len(completed_quests)
    progress_bar = "█" * completed_count + "░" * (total_quests - completed_count)
    
    embed.set_footer(text=f"Progress: {completed_count}/{total_quests} | {progress_bar}")
    
    await ctx.send(embed=embed)

@bot.command(name="questleaderboard")
async def quest_leaderboard(ctx):
    leaderboard_list = sorted(quest_data["user_progress"].items(), key=lambda x: len(x[1]), reverse=True)
    embed = discord.Embed(title="🏆 Panda Quest Leaderboard", color=discord.Color.purple())
    if not leaderboard_list:
        embed.description = "No quests completed yet!"
    else:
        for i, (user_id, completed) in enumerate(leaderboard_list[:10], start=1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                embed.add_field(name=f"{i}. {member.display_name}", value=f"Completed {len(completed)} quests", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def claim(ctx, *, args: str = ""):
    global event_active, event_claimer, current_event_message, current_event_type, chi_party_active, chi_party_tokens, chi_party_claims, active_food_event
    user_id = str(ctx.author.id)
    
    # Handle food event claiming
    if args.lower() == "food":
        if not active_food_event:
            await ctx.send("❌ No active food event to claim right now!")
            return
        
        if active_food_event.get("claimed_by"):
            await ctx.send("❌ This food has already been claimed!")
            return
        
        # Ensure user data exists
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": [], "pets": [], "trade_requests": [], "active_pet": None, "food_inventory": {}}
        
        # Add food inventory if not exists
        if "food_inventory" not in chi_data[user_id]:
            chi_data[user_id]["food_inventory"] = {}
        
        food_name = active_food_event["food_name"]
        quantity = active_food_event["quantity"]
        
        # Add to inventory
        if food_name in chi_data[user_id]["food_inventory"]:
            chi_data[user_id]["food_inventory"][food_name] += quantity
        else:
            chi_data[user_id]["food_inventory"][food_name] = quantity
        
        active_food_event["claimed_by"] = user_id
        save_data()
        
        await ctx.send(f"🍱 {ctx.author.display_name} claimed **{quantity}x {food_name}**! Check your inventory with `P!inv`!")
        
        # Clear food event
        active_food_event = None
        return
    
    if chi_party_active:
        if user_id in chi_party_claims:
            await ctx.send(f"❌ {ctx.author.display_name}, you already claimed a chi party token!")
            return
        
        available_tokens = [t for t in chi_party_tokens if t["claimed_by"] is None]
        if not available_tokens:
            chi_party_active = False
            await ctx.send(f"❌ All chi party tokens have been claimed!")
            return
        
        token = available_tokens[0]
        token["claimed_by"] = user_id
        chi_party_claims[user_id] = token["amount"]
        
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        rebirth_msg = update_chi(ctx.author.id, token["amount"])
        remaining_tokens = len([t for t in chi_party_tokens if t["claimed_by"] is None])
        
        msg = f"🎉 {ctx.author.display_name} claimed a chi party token worth **{token['amount']} chi**! Total chi: **{chi_data[user_id]['chi']}**\n"
        msg += f"**{remaining_tokens}** tokens remaining!"
        
        if rebirth_msg:
            msg += f"\n{rebirth_msg}"
        
        if remaining_tokens == 0:
            chi_party_active = False
            msg += "\n\n🎊 All chi party tokens have been claimed!"
        
        await ctx.send(msg)
        return
    
    if not event_active or event_claimer is not None:
        await ctx.send(f"❌ No active Chi Event or Chi Party to claim right now, {ctx.author.display_name}.")
        return
    
    event_active = False
    event_claimer = user_id
    event_type = current_event_type
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if event_type == "positive":
        chi_amount = random.randint(50, 200)
        rebirth_msg = update_chi(ctx.author.id, chi_amount)
        msg = f"✨🐼 {ctx.author.display_name} claimed a **POSITIVE CHI EVENT** and gained **{chi_amount} chi**! Total chi: **{chi_data[user_id]['chi']}**"
        if rebirth_msg:
            msg += f"\n{rebirth_msg}"
    else:
        chi_amount = random.randint(50, 200)
        rebirth_msg = update_chi(ctx.author.id, -chi_amount)
        msg = f"💀🐼 {ctx.author.display_name} claimed a **NEGATIVE CHI EVENT** and lost **{chi_amount} chi**! Total chi: **{chi_data[user_id]['chi']}**"
        if rebirth_msg:
            msg += f"\n{rebirth_msg}"
    
    await ctx.send(msg)

@bot.command(name="find")
async def find_artifact(ctx, *, args: str = ""):
    """Claim an active artifact"""
    global artifact_state
    user_id = str(ctx.author.id)
    
    if not args or "artifact" not in args.lower():
        await ctx.send("❌ Usage: `P!find artifact`")
        return
    
    # Check if there's an active artifact
    if not artifact_state.get("active_artifact"):
        await ctx.send("❌ No active artifact to find right now! Keep watching for mystical artifacts to appear.")
        return
    
    active_artifact = artifact_state["active_artifact"]
    
    # Check if already claimed
    if active_artifact.get("claimed_by"):
        await ctx.send("❌ This artifact has already been claimed!")
        return
    
    # Check if expired
    expires_at = datetime.fromisoformat(active_artifact["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        await ctx.send("❌ The artifact has already vanished...")
        artifact_state["active_artifact"] = None
        save_artifact_state()
        return
    
    # Ensure user data exists
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": [], "pets": [], "trade_requests": [], "active_pet": None}
    
    # Claim the artifact
    tier = active_artifact["tier"]
    emoji = active_artifact["emoji"]
    artifact_name = active_artifact.get("name", "Unknown Artifact")
    artifact_id = active_artifact["id"]
    
    # Add to user's artifact inventory
    chi_data[user_id]["artifacts"].append({
        "id": artifact_id,
        "tier": tier,
        "emoji": emoji,
        "name": artifact_name,
        "claimed_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Mark as claimed
    artifact_state["active_artifact"]["claimed_by"] = user_id
    save_artifact_state()
    save_data()
    
    # Success message
    heal_percent = ARTIFACT_CONFIG[tier]["heal_percent"]
    tier_colors = {
        "common": discord.Color.light_grey(),
        "rare": discord.Color.purple(),
        "legendary": discord.Color.gold(),
        "eternal": discord.Color.dark_blue(),
        "mythical": discord.Color.from_rgb(255, 0, 255)  # Magenta
    }
    
    embed = discord.Embed(
        title=f"{emoji} Artifact Claimed!",
        description=f"**{ctx.author.display_name}** found the **{artifact_name}**!\n\n"
                   f"✨ Rarity: **{tier.upper()}**\n"
                   f"💊 Healing Power: **{heal_percent}% HP** in duels\n"
                   f"📦 Total Artifacts: **{len(chi_data[user_id]['artifacts'])}**\n\n"
                   f"Use artifacts in duels to heal yourself!",
        color=tier_colors.get(tier, discord.Color.blue())
    )
    embed.set_footer(text=f"{artifact_name} • ID: {artifact_id}")
    await ctx.send(embed=embed)
    
    # Chance for bonus tool drop (15% chance)
    tool_drop_chance = random.random()
    if tool_drop_chance < 0.15:
        # Get tools that can be found via artifact search
        searchable_tools = {k: v for k, v in GARDEN_TOOLS.items() if v.get("acquisition") == "artifact_search"}
        
        if searchable_tools:
            # Weight-based random selection
            total_weight = sum(tool.get("rarity_weight", 1) for tool in searchable_tools.values())
            roll = random.uniform(0, total_weight)
            
            cumulative_weight = 0
            found_tool_key = None
            for tool_key, tool in searchable_tools.items():
                cumulative_weight += tool.get("rarity_weight", 1)
                if roll <= cumulative_weight:
                    found_tool_key = tool_key
                    break
            
            if found_tool_key:
                found_tool = GARDEN_TOOLS[found_tool_key]
                
                # Add tool to user's garden_tools
                if "garden_tools" not in chi_data[user_id]:
                    chi_data[user_id]["garden_tools"] = {}
                if found_tool_key not in chi_data[user_id]["garden_tools"]:
                    chi_data[user_id]["garden_tools"][found_tool_key] = 0
                chi_data[user_id]["garden_tools"][found_tool_key] += 1
                
                save_data()
                
                # Send bonus tool message
                tool_embed = discord.Embed(
                    title="🎁 Bonus Tool Found!",
                    description=f"While searching, you also found {found_tool['emoji']} **{found_tool['name']}**!",
                    color=discord.Color.gold()
                )
                tool_embed.add_field(
                    name="🛠️ Tool Bonuses",
                    value=found_tool['description'],
                    inline=False
                )
                tool_embed.set_footer(text="Use P!tools to view all your garden tools!")
                await ctx.send(embed=tool_embed)
    
    # Clear active artifact after short delay
    await asyncio.sleep(3)
    artifact_state["active_artifact"] = None
    save_artifact_state()

@bot.command(name="event")
@is_bot_owner()
async def event_command(ctx, event_type: str = ""):
    """Admin command to spawn events manually"""
    global chi_party_last_spawn, artifact_state
    global event_active, event_claimer, current_event_message, current_event_type
    global chi_party_active, chi_party_tokens, chi_party_claims
    global active_food_event, active_rift_battle, rift_event_participants
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to summon events.")
        return
    
    if not event_type:
        await ctx.send("❌ Usage: `P!event <party/chi/food/garden/eternal/legendary/rare/rift/end>`\n"
                      "**party** - Summon a chi party\n"
                      "**chi** - Spawn a small chi mini-event\n"
                      "**food** - Spawn a food mini-event (for feeding pets/Pax)\n"
                      "**garden** - Activate spiritual journey boost (10 minutes)\n"
                      "**eternal** - Summon an eternal artifact\n"
                      "**legendary/legend** - Summon a legendary artifact\n"
                      "**rare** - Summon a rare artifact\n"
                      "**rift** - Start the Rift Event (boss battle + rewards)\n"
                      "**end** - Force-end all active events")
        return
    
    event_type = event_type.lower()
    
    # Chi Party Event
    if event_type == "party":
        current_time = time.time()
        time_since_last = current_time - chi_party_last_spawn
        
        if time_since_last < CHI_PARTY_COOLDOWN:
            remaining = int(CHI_PARTY_COOLDOWN - time_since_last)
            minutes = remaining // 60
            seconds = remaining % 60
            await ctx.send(f"⏳ Chi party is on cooldown! Wait {minutes}m {seconds}s.")
            return
        
        if chi_party_active:
            await ctx.send("❌ A chi party is already active!")
            return
        
        chi_party_last_spawn = current_time
        await spawn_chi_party(ctx.channel)
    
    # Small Chi Event
    elif event_type == "chi":
        amount = random.randint(25, 100)
        is_positive = random.choice([True, False])
        
        embed = discord.Embed(
            title="🌸 Mini Chi Event!" if is_positive else "🍂 Mini Chi Event!",
            description=f"A small chi disturbance appeared! Type `P!claim` to interact!\n\n"
                       f"Chi Amount: **{'+'if is_positive else '-'}{amount} chi**",
            color=discord.Color.green() if is_positive else discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        # Trigger the chi event system
        global event_active, current_event_type, event_claimer
        event_active = True
        current_event_type = "positive" if is_positive else "negative"
        event_claimer = None
    
    # Food Event
    elif event_type == "food":
        # Select random food from pet catalog
        available_foods = pet_catalog.get("foods", [])
        if not available_foods:
            await ctx.send("❌ No foods available in the catalog!")
            return
        
        selected_food = random.choice(available_foods)
        food_name = selected_food["name"]
        food_quantity = random.randint(1, 3)
        
        embed = discord.Embed(
            title="🍱 Food Event!",
            description=f"**{food_quantity}x {food_name}** appeared!\n\n"
                       f"Type `P!claim food` to grab it within **1 minute**!\n\n"
                       f"💚 Hunger: +{selected_food['hunger_restore']}\n"
                       f"❤️ Health: +{selected_food['health_restore']}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Use food to feed Pax or your pets!")
        await ctx.send(embed=embed)
        
        # Set up food event state
        global active_food_event
        active_food_event = {
            "food_name": food_name,
            "quantity": food_quantity,
            "spawned_at": datetime.now(timezone.utc).isoformat(),
            "claimed_by": None
        }
        
        # Auto-expire after 60 seconds
        async def expire_food():
            await asyncio.sleep(60)
            global active_food_event
            if active_food_event and active_food_event.get("food_name") == food_name and not active_food_event.get("claimed_by"):
                await ctx.send(f"🍱 The **{food_name}** vanished unclaimed...")
                active_food_event = None
        
        asyncio.create_task(expire_food())
    
    # Garden Event
    elif event_type == "garden":
        # Activate spiritual journey boost for 10 minutes
        if gardens_data["garden_event"]["active"]:
            await ctx.send("❌ The spiritual journey boost is already active!")
            return
        
        # Activate event
        gardens_data["garden_event"]["active"] = True
        gardens_data["garden_event"]["end_time"] = (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()
        save_gardens()
        
        # Count affected gardens
        affected_count = len(gardens_data["gardens"])
        
        embed = discord.Embed(
            title="🌸✨ Spiritual Journey Activated!",
            description=f"All gardens are blessed with spiritual energy!\n\n"
                       f"**Duration:** 10 minutes\n"
                       f"**Effect:** All plants are instantly ready to harvest!\n"
                       f"**Gardens Affected:** {affected_count}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Harvest your plants now with P!garden harvest <plant_name>!")
        await ctx.send(embed=embed)
        
        # Auto-expire after 10 minutes
        async def expire_garden_event():
            await asyncio.sleep(600)  # 10 minutes
            if gardens_data["garden_event"]["active"]:
                gardens_data["garden_event"]["active"] = False
                gardens_data["garden_event"]["end_time"] = None
                save_gardens()
                await ctx.send("🌸 The spiritual journey has ended. Gardens return to normal.")
        
        asyncio.create_task(expire_garden_event())
    
    # Artifact Events
    elif event_type in ["eternal", "legendary", "legend", "rare"]:
        # Normalize legendary
        if event_type == "legend":
            event_type = "legendary"
        
        if artifact_state.get("active_artifact"):
            await ctx.send("❌ There's already an active artifact! Wait for it to be claimed or expire.")
            return
        
        # Spawn artifact of specified tier
        now = datetime.now(timezone.utc)
        emoji_index = random.randint(0, len(ARTIFACT_CONFIG[event_type]["emojis"]) - 1)
        selected_emoji = ARTIFACT_CONFIG[event_type]["emojis"][emoji_index]
        selected_name = ARTIFACT_CONFIG[event_type]["names"][emoji_index]
        artifact_id = f"{event_type}_admin_{int(now.timestamp())}"
        
        # Set up artifact state
        artifact_state["active_artifact"] = {
            "id": artifact_id,
            "emoji": selected_emoji,
            "name": selected_name,
            "tier": event_type,
            "spawned_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ARTIFACT_CLAIM_TIME)).isoformat(),
            "claimed_by": None
        }
        save_artifact_state()
        
        # Post announcement
        embed = discord.Embed(
            title=f"{selected_emoji} MYSTICAL ARTIFACT SUMMONED!",
            description=f"**{selected_name}**\n"
                       f"An admin summoned a **{event_type.upper()}** artifact!\n\n"
                       f"Type `P!find artifact` to claim it within **5 minutes**!\n\n"
                       f"💊 Healing Power: **{ARTIFACT_CONFIG[event_type]['heal_percent']}% HP** in duels",
            color=discord.Color.purple() if event_type == "rare" else 
                  discord.Color.gold() if event_type == "legendary" else
                  discord.Color.dark_blue()
        )
        embed.set_footer(text=f"{selected_name} • Summoned by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        # Start expiration task in background (don't block)
        async def expire_artifact():
            await asyncio.sleep(ARTIFACT_CLAIM_TIME)
            if artifact_state.get("active_artifact") and artifact_state["active_artifact"]["id"] == artifact_id:
                if not artifact_state["active_artifact"].get("claimed_by"):
                    await ctx.send(f"{selected_emoji} The **{selected_name}** vanished unclaimed...")
                    artifact_state["active_artifact"] = None
                    save_artifact_state()
        
        asyncio.create_task(expire_artifact())
    
    # Rift Event
    elif event_type == "rift":
        global active_rift_battle, rift_event_participants
        
        if active_rift_battle:
            await ctx.send("❌ A Rift Battle is already active!")
            return
        
        # Reset participants list
        rift_event_participants = []
        
        # Post the GIF and event announcement
        embed = discord.Embed(
            title="🌀⚔️ THE RIFT HAS OPENED! ⚔️🌀",
            description="**A tear in reality has appeared!**\n\n"
                       "Type `P!enter` to receive:\n"
                       "• ⚔️ **Celestial Warhammer** (Legendary Weapon)\n"
                       "• 🐯 **Tiger** (Battle Pet)\n"
                       "• 💊 **Standard Recovery Potion**\n\n"
                       "**WARNING:** A powerful boss awaits those who enter...",
            color=discord.Color.from_rgb(138, 43, 226)  # Purple
        )
        embed.set_image(url="https://tenor.com/view/kung-fu-panda-dragon-power-dragon-energy-dragon-kung-fu-panda-gif-14325240")
        embed.set_footer(text="Prepare yourself, warrior! Type P!enter to join the battle!")
        await ctx.send(embed=embed)
        
        # Set up rift battle state (will be activated when first person uses P!rift attack)
        active_rift_battle = {
            "boss_hp": 2500,
            "boss_max_hp": 2500,
            "participants": {},  # {user_id: {"damage_dealt": int, "entered": bool}}
            "spawned_at": datetime.utcnow(),
            "channel_id": ctx.channel.id,
            "active": False  # Becomes True when first attack happens
        }
        
        await ctx.send("🌀 **The Rifter awaits!** Use `P!rift attack <weapon_attack>` to begin the battle!")
    
    # End All Events
    elif event_type == "end":
        # Track which events were active
        ended_events = []
        
        # End mini chi events
        if event_active:
            event_active = False
            event_claimer = None
            current_event_message = None
            current_event_type = "positive"
            ended_events.append("Mini Chi Event")
        
        # End chi party
        if chi_party_active:
            chi_party_active = False
            chi_party_tokens.clear()
            chi_party_claims.clear()
            ended_events.append("Chi Party")
        
        # End food event
        if active_food_event:
            active_food_event = None
            ended_events.append("Food Event")
        
        # End artifact event
        if artifact_state.get("active_artifact"):
            artifact_state["active_artifact"] = None
            save_artifact_state()
            ended_events.append("Artifact Hunt")
        
        # End garden spiritual journey
        if gardens_data["garden_event"]["active"]:
            gardens_data["garden_event"]["active"] = False
            gardens_data["garden_event"]["end_time"] = None
            save_gardens()
            ended_events.append("Spiritual Journey")
        
        # End rift battle
        if active_rift_battle:
            active_rift_battle = None
            rift_event_participants.clear()
            ended_events.append("Rift Battle")
        
        if ended_events:
            embed = discord.Embed(
                title="🛑 Events Forcefully Ended",
                description=f"**Admin {ctx.author.display_name}** has ended all active events!\n\n"
                           f"**Ended Events:**\n" + "\n".join([f"• {event}" for event in ended_events]),
                color=discord.Color.red()
            )
            embed.set_footer(text="All event states have been cleared")
            await ctx.send(embed=embed)
        else:
            await ctx.send("✅ No active events to end.")
    
    else:
        await ctx.send("❌ Invalid event type! Use: `party`, `chi`, `food`, `garden`, `eternal`, `legendary`, `rare`, `rift`, or `end`")

@bot.command(name="enter")
async def enter_rift(ctx):
    """Enter the Rift Event and receive starter items"""
    global active_rift_battle, rift_event_participants
    user_id = str(ctx.author.id)
    
    if not active_rift_battle:
        await ctx.send("❌ There is no active rift event! An admin must start one with `P!event rift`")
        return
    
    if user_id in rift_event_participants:
        await ctx.send("❌ You've already entered the rift!")
        return
    
    # Add user to participants
    rift_event_participants.append(user_id)
    
    # Initialize user if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    # Give rewards
    # 1. Celestial Warhammer weapon
    chi_data[user_id]["inventory"]["Celestial Warhammer"] = chi_data[user_id]["inventory"].get("Celestial Warhammer", 0) + 1
    
    # 2. Tiger pet (add to owned_pets)
    if "owned_pets" not in chi_data[user_id]:
        chi_data[user_id]["owned_pets"] = []
    
    # Check if they already have a Tiger
    has_tiger = any(pet.get("pet_type") == "Tiger" for pet in chi_data[user_id]["owned_pets"])
    if not has_tiger:
        tiger_id = f"tiger_{user_id}_{int(time.time())}"
        chi_data[user_id]["owned_pets"].append({
            "id": tiger_id,
            "pet_type": "Tiger",
            "nickname": None,
            "health": 3000,
            "max_health": 3000,
            "attack": 100,
            "level": 1,
            "xp": 0
        })
    
    # 3. Standard Recovery Potion
    chi_data[user_id]["inventory"]["standard_recovery"] = chi_data[user_id]["inventory"].get("standard_recovery", 0) + 1
    
    save_data()
    
    # Send confirmation
    embed = discord.Embed(
        title="🌀 Entered the Rift!",
        description=f"**{ctx.author.display_name}** has stepped through the portal!\n\n"
                   f"**Rewards Received:**\n"
                   f"⚔️ Celestial Warhammer (Legendary Weapon)\n"
                   f"🐯 Tiger Battle Pet (3000 HP)\n"
                   f"💊 Standard Recovery Potion\n\n"
                   f"💀 **The Rifter** awaits your challenge!\n"
                   f"Use `P!rift attack <weapon_attack>` to engage!",
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Total Warriors: {len(rift_event_participants)}")
    await ctx.send(embed=embed)

# Helper function for HP bars
def create_hp_bar(current_hp, max_hp, length=20):
    """Create a visual HP bar"""
    if max_hp == 0:
        ratio = 0
    else:
        ratio = max(0, min(1, current_hp / max_hp))
    filled = int(ratio * length)
    empty = length - filled
    return "█" * filled + "░" * empty

# Define legendary weapon attacks for rift battle
LEGENDARY_WEAPONS = [
    {
        "name": "Celestial Warhammer",
        "attacks": [
            {"name": "Heaven's Smite", "damage_min": 80, "damage_max": 200},
            {"name": "Divine Judgment", "damage_min": 100, "damage_max": 250},
            {"name": "Celestial Fury", "damage_min": 60, "damage_max": 300}
        ]
    },
    {
        "name": "Dragon Blade",
        "attacks": [
            {"name": "Dragon's Wrath", "damage_min": 90, "damage_max": 220},
            {"name": "Flame Strike", "damage_min": 70, "damage_max": 180},
            {"name": "Dragon Claw", "damage_min": 110, "damage_max": 240}
        ]
    },
    {
        "name": "Death Scythe",
        "attacks": [
            {"name": "Reaper's Harvest", "damage_min": 100, "damage_max": 230},
            {"name": "Soul Drain", "damage_min": 85, "damage_max": 190},
            {"name": "Shadow Strike", "damage_min": 95, "damage_max": 210}
        ]
    }
]

# Rift Battle Command Group
@bot.group(name="rift", invoke_without_command=True)
async def rift(ctx):
    """Rift battle commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("❌ Usage: `P!rift attack <weapon_attack>` or `P!rift run`")

@rift.command(name="attack")
async def rift_attack(ctx, *, attack_name: str = ""):
    """Attack the Rifter boss"""
    global active_rift_battle
    user_id = str(ctx.author.id)
    
    if not active_rift_battle:
        await ctx.send("❌ There is no active rift battle! An admin must start one with `P!event rift`")
        return
    
    if user_id not in rift_event_participants:
        await ctx.send("❌ You must use `P!enter` first to join the rift battle!")
        return
    
    if not attack_name:
        await ctx.send("❌ Specify an attack! Usage: `P!rift attack <weapon_attack>`\n"
                      "Example: `P!rift attack Dragon's Wrath`")
        return
    
    # Find the weapon attack
    weapon_attack = None
    for weapon in LEGENDARY_WEAPONS:
        for attack in weapon["attacks"]:
            if attack["name"].lower() == attack_name.lower():
                weapon_attack = attack
                break
        if weapon_attack:
            break
    
    if not weapon_attack:
        await ctx.send(f"❌ **{attack_name}** is not a valid weapon attack!\n"
                      f"Use attacks from your legendary weapons (e.g., Dragon's Wrath, Reaper's Harvest)")
        return
    
    # Calculate damage
    base_damage = random.randint(weapon_attack["damage_min"], weapon_attack["damage_max"])
    
    # Track participation
    if user_id not in active_rift_battle["participants"]:
        active_rift_battle["participants"][user_id] = {"damage_dealt": 0, "attacks": 0}
    
    active_rift_battle["participants"][user_id]["damage_dealt"] += base_damage
    active_rift_battle["participants"][user_id]["attacks"] += 1
    
    # Apply damage to boss
    active_rift_battle["boss_hp"] -= base_damage
    active_rift_battle["active"] = True
    
    # Boss counterattack
    boss_damage = random.randint(BOSS_DATA["rifter"]["damage_min"], BOSS_DATA["rifter"]["damage_max"])
    
    # Check if boss is defeated
    if active_rift_battle["boss_hp"] <= 0:
        # Boss defeated! Distribute rewards
        embed = discord.Embed(
            title="🌀⚔️ THE RIFTER HAS BEEN DEFEATED! ⚔️🌀",
            description=f"**{ctx.author.display_name}** dealt the final blow!\n\n"
                       f"**Total Participants:** {len(active_rift_battle['participants'])}\n\n"
                       f"**All warriors who attacked receive:**\n"
                       f"💎 **1,500 chi**\n"
                       f"🌀 **Rift Shard** (Sell for 1 rebirth OR upgrade garden to Rift tier!)",
            color=discord.Color.gold()
        )
        
        # Give rewards to all participants who attacked
        for participant_id, stats in active_rift_battle["participants"].items():
            if stats["attacks"] > 0:  # Only those who attacked
                update_chi(int(participant_id), 1500)
                
                # Give Rift Shard
                if participant_id not in chi_data:
                    chi_data[participant_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
                if "inventory" not in chi_data[participant_id]:
                    chi_data[participant_id]["inventory"] = {}
                
                chi_data[participant_id]["inventory"]["Rift Shard"] = chi_data[participant_id]["inventory"].get("Rift Shard", 0) + 1
        
        save_data()
        
        # List top damage dealers
        sorted_participants = sorted(active_rift_battle["participants"].items(), key=lambda x: x[1]["damage_dealt"], reverse=True)
        top_3 = sorted_participants[:3]
        
        leaderboard = "\n".join([
            f"{i+1}. <@{uid}>: {stats['damage_dealt']:,} damage"
            for i, (uid, stats) in enumerate(top_3)
        ])
        
        embed.add_field(name="🏆 Top Damage Dealers", value=leaderboard or "None", inline=False)
        embed.set_footer(text="The rift has closed. Well fought, warriors!")
        await ctx.send(embed=embed)
        
        # Clear rift battle
        active_rift_battle = None
        rift_event_participants.clear()
        
    else:
        # Battle continues
        hp_bar = create_hp_bar(active_rift_battle["boss_hp"], active_rift_battle["boss_max_hp"])
        
        embed = discord.Embed(
            title=f"🌀 {BOSS_DATA['rifter']['name']}",
            description=f"**{ctx.author.display_name}** attacks with **{weapon_attack['name']}**!\n\n"
                       f"⚔️ Dealt **{base_damage} damage**!\n"
                       f"💥 Boss retaliates for **{boss_damage} damage**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Boss HP", value=f"{hp_bar}\n{active_rift_battle['boss_hp']:,}/{active_rift_battle['boss_max_hp']:,} HP", inline=False)
        embed.set_footer(text=f"Your damage: {active_rift_battle['participants'][user_id]['damage_dealt']:,} | Use P!rift attack <attack> to continue!")
        await ctx.send(embed=embed)

@rift.command(name="run")
async def rift_run(ctx):
    """Flee from the rift battle (no rewards)"""
    global rift_event_participants
    user_id = str(ctx.author.id)
    
    if not active_rift_battle:
        await ctx.send("❌ There is no active rift battle!")
        return
    
    if user_id not in rift_event_participants:
        await ctx.send("❌ You haven't entered the rift!")
        return
    
    # Remove from participants
    rift_event_participants.remove(user_id)
    if user_id in active_rift_battle["participants"]:
        del active_rift_battle["participants"][user_id]
    
    await ctx.send(f"🏃 **{ctx.author.display_name}** fled from the rift! You will not receive rewards.")

@bot.command(name="message")
@is_bot_owner()
async def message_stats(ctx, mode: str = ""):
    """Admin command to show message statistics in the server"""
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to view message statistics.")
        return
    
    if not mode:
        await ctx.send("❌ Usage: `P!message <total/human/bot/channel>`\n"
                      "**total** - Total messages across entire server\n"
                      "**human** - Messages sent by humans only\n"
                      "**bot** - Messages sent by bots only\n"
                      "**channel** - Messages in current channel only")
        return
    
    mode = mode.lower()
    
    if mode not in ["total", "human", "bot", "channel"]:
        await ctx.send("❌ Invalid mode! Use: `total`, `human`, `bot`, or `channel`")
        return
    
    # Send loading message
    loading_msg = await ctx.send("🔍 Scanning messages... This may take a while!")
    
    try:
        total_messages = 0
        human_messages = 0
        bot_messages = 0
        channel_breakdown = {}
        
        if mode == "channel":
            # Count messages in current channel only
            async for message in ctx.channel.history(limit=None):
                total_messages += 1
            
            embed = discord.Embed(
                title="📊 Channel Message Statistics",
                description=f"**Channel:** {ctx.channel.mention}\n"
                           f"**Total Messages:** {total_messages:,}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            
        else:
            # Scan all text channels
            for channel in ctx.guild.text_channels:
                try:
                    channel_count = 0
                    async for message in channel.history(limit=None):
                        channel_count += 1
                        total_messages += 1
                        
                        if message.author.bot:
                            bot_messages += 1
                        else:
                            human_messages += 1
                    
                    if channel_count > 0:
                        channel_breakdown[channel.name] = channel_count
                        
                except discord.Forbidden:
                    # Skip channels we can't access
                    continue
            
            # Create embed based on mode
            if mode == "total":
                embed = discord.Embed(
                    title="📊 Server Message Statistics",
                    description=f"**Total Messages:** {total_messages:,}\n"
                               f"👤 Human Messages: {human_messages:,}\n"
                               f"🤖 Bot Messages: {bot_messages:,}\n"
                               f"📝 Channels Scanned: {len(channel_breakdown)}",
                    color=discord.Color.green()
                )
                
                # Add top 5 most active channels
                if channel_breakdown:
                    sorted_channels = sorted(channel_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_channels = "\n".join([f"**#{name}:** {count:,} messages" for name, count in sorted_channels])
                    embed.add_field(
                        name="📈 Top 5 Most Active Channels",
                        value=top_channels,
                        inline=False
                    )
                
            elif mode == "human":
                embed = discord.Embed(
                    title="👤 Human Message Statistics",
                    description=f"**Human Messages:** {human_messages:,}\n"
                               f"📊 {(human_messages/total_messages*100) if total_messages > 0 else 0:.1f}% of all messages\n"
                               f"📝 Channels Scanned: {len(channel_breakdown)}",
                    color=discord.Color.purple()
                )
                
            elif mode == "bot":
                embed = discord.Embed(
                    title="🤖 Bot Message Statistics",
                    description=f"**Bot Messages:** {bot_messages:,}\n"
                               f"📊 {(bot_messages/total_messages*100) if total_messages > 0 else 0:.1f}% of all messages\n"
                               f"📝 Channels Scanned: {len(channel_breakdown)}",
                    color=discord.Color.orange()
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name} • Server: {ctx.guild.name}")
        
        await loading_msg.edit(content=None, embed=embed)
        
    except Exception as e:
        await loading_msg.edit(content=f"❌ Error scanning messages: {str(e)}")

@bot.command(name="log")
@is_bot_owner()
async def log_command(ctx, mode: str = None, target: str = None):
    """Enhanced admin command: P!log [page/command/channel] [value]"""
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to view logs.")
        return
    
    # MODE 1: P!log channel <#channel> - Set logging channel
    if mode and mode.lower() == "channel":
        if not target:
            # Show current config
            current_channel_id = log_config.get("error_channel_id")
            if current_channel_id:
                channel = bot.get_channel(current_channel_id)
                if channel:
                    await ctx.send(f"✅ Error logging channel: {channel.mention}\n\nUse `P!log channel #new-channel` to change it.")
                else:
                    await ctx.send("⚠️ Configured channel not found. Use `P!log channel #channel` to set a new one.")
            else:
                await ctx.send("ℹ️ No error logging channel configured.\n\nUse `P!log channel #channel` to set one.")
            return
        
        # Set new channel
        if ctx.message.channel_mentions:
            new_channel = ctx.message.channel_mentions[0]
            log_config["error_channel_id"] = new_channel.id
            await save_log_config()
            await ctx.send(f"✅ Error logging channel set to {new_channel.mention}\n\nAll future errors will be automatically posted there!")
        else:
            await ctx.send("❌ Please mention a channel! Example: `P!log channel #bot-logs`")
        return
    
    # MODE 2: P!log command <command_name> - Filter by command
    if mode and mode.lower() == "command":
        if not target:
            await ctx.send("❌ Please specify a command! Example: `P!log command duel`")
            return
        
        command_filter = target.lower()
        filtered_logs = [
            log for log in error_logs
            if log.get("command") and command_filter in log["command"].lower()
        ]
        
        if not filtered_logs:
            await ctx.send(f"✅ No errors found for command containing `{command_filter}` in the past 7 days!")
            return
        
        # Show stats
        total_errors = len(filtered_logs)
        unique_users = len(set(log.get("user") for log in filtered_logs if log.get("user")))
        error_types = {}
        for log in filtered_logs:
            code = log.get("error_code", "Unknown")
            error_types[code] = error_types.get(code, 0) + 1
        
        embed = discord.Embed(
            title=f"📋 Command Error Report: `{command_filter}`",
            description=f"**Total Errors:** {total_errors}\n"
                       f"**Unique Users Affected:** {unique_users}\n"
                       f"**Date Range:** Past 7 days",
            color=discord.Color.orange()
        )
        
        # Error types breakdown
        error_breakdown = "\n".join([f"**{code}**: {count}x" for code, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]])
        embed.add_field(
            name="🔍 Most Common Errors",
            value=error_breakdown,
            inline=False
        )
        
        # Recent examples (last 5)
        examples_text = ""
        for log in filtered_logs[-5:]:
            timestamp = datetime.fromisoformat(log["timestamp"])
            time_ago = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if time_ago < 3600:
                time_str = f"{int(time_ago/60)}m ago"
            elif time_ago < 86400:
                time_str = f"{int(time_ago/3600)}h ago"
            else:
                time_str = f"{int(time_ago/86400)}d ago"
            
            examples_text += f"**{log['id']}** ({time_str})\n"
            examples_text += f"└ {log['error'][:100]}...\n"
            if log.get("message_link"):
                examples_text += f"└ [Jump]({log['message_link']})\n"
        
        embed.add_field(
            name="📝 Recent Examples",
            value=examples_text if examples_text else "No examples",
            inline=False
        )
        
        embed.set_footer(text=f"Use P!log <page> to browse all {len(error_logs)} logs")
        await ctx.send(embed=embed)
        return
    
    # MODE 3: P!log [page] - Paginated view of all errors (default mode)
    page = 1
    if mode:
        try:
            page = int(mode)
            if page < 1:
                page = 1
        except ValueError:
            await ctx.send("❌ Invalid usage! Use:\n"
                          "`P!log [page]` - Browse all errors\n"
                          "`P!log command <name>` - Filter by command\n"
                          "`P!log channel #channel` - Set auto-post channel")
            return
    
    # Get all errors (already filtered to 7 days on load)
    LOGS_PER_PAGE = 10
    total_logs = len(error_logs)
    total_pages = (total_logs + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE if total_logs > 0 else 1
    
    if page > total_pages:
        page = total_pages
    
    # Calculate slice
    start_idx = (page - 1) * LOGS_PER_PAGE
    end_idx = start_idx + LOGS_PER_PAGE
    page_logs = list(reversed(error_logs))[start_idx:end_idx]  # Reverse to show newest first
    
    # Create embed
    embed = discord.Embed(
        title=f"🔧 Pax Dev Portal - Error Logs (Page {page}/{total_pages})",
        description=f"**System Status:** {'✅ RUNNING' if bot.is_ready() else '⚠️ STARTING'}\n"
                   f"**Uptime:** {time.time() - bot.start_time if hasattr(bot, 'start_time') else 0:.0f}s\n"
                   f"**Total Logs:** {total_logs} (past 7 days)",
        color=discord.Color.blue() if total_logs == 0 else discord.Color.orange()
    )
    
    # System Statistics
    guild_count = len(bot.guilds)
    user_count = len(chi_data)
    team_count = len(teams_data.get("teams", {}))
    garden_count = len(gardens_data.get("gardens", {}))
    
    embed.add_field(
        name="📊 System Stats",
        value=f"**Guilds:** {guild_count}\n**Users:** {user_count}\n**Teams:** {team_count}\n**Gardens:** {garden_count}",
        inline=True
    )
    
    # Active Events
    active_events = []
    if chi_party_active:
        active_events.append("Chi Party")
    if event_active:
        active_events.append(f"{current_event_type.title()} Event")
    if active_food_event:
        active_events.append("Food Event")
    if active_rift_battle:
        active_events.append("Rift Battle")
    if gardens_data.get("garden_event", {}).get("active", False):
        active_events.append("Spiritual Journey")
    
    embed.add_field(
        name="🎮 Active Events",
        value="\n".join([f"• {event}" for event in active_events[:3]]) if active_events else "None",
        inline=True
    )
    
    # Error logs for this page
    if page_logs:
        error_text = ""
        for log in page_logs:
            timestamp = datetime.fromisoformat(log["timestamp"])
            time_ago = (datetime.now(timezone.utc) - timestamp).total_seconds()
            
            if time_ago < 60:
                time_str = f"{int(time_ago)}s ago"
            elif time_ago < 3600:
                time_str = f"{int(time_ago/60)}m ago"
            elif time_ago < 86400:
                time_str = f"{int(time_ago/3600)}h ago"
            else:
                time_str = f"{int(time_ago/86400)}d ago"
            
            error_line = f"**{log['id']}** ({time_str})\n"
            error_line += f"└ `{log['error'][:60]}...`\n"
            error_line += f"└ {log.get('command', 'Unknown')} | {log.get('error_code', 'N/A')}\n"
            if log.get("message_link"):
                error_line += f"└ [Jump]({log['message_link']})\n"
            
            error_text += error_line
        
        embed.add_field(
            name=f"📋 Error Log Entries ({start_idx+1}-{min(end_idx, total_logs)})",
            value=error_text if len(error_text) < 1024 else error_text[:1020] + "...",
            inline=False
        )
    else:
        embed.add_field(
            name="✅ System Health",
            value="No errors detected in the past 7 days!",
            inline=False
        )
    
    # Navigation footer
    nav_text = f"Page {page}/{total_pages} • Use `P!log {page+1}` for next page" if page < total_pages else f"Page {page}/{total_pages}"
    if total_pages > 1:
        nav_text += f"\n`P!log command <name>` to filter | `P!log channel #channel` to configure"
    
    embed.set_footer(text=nav_text)
    
    await ctx.send(embed=embed)

@bot.group(name="artifact", invoke_without_command=True)
async def artifact_group(ctx):
    """Artifact management commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("❌ Usage: `P!artifact give <@user> <rare/legendary/eternal>`")

@artifact_group.command(name="give")
async def artifact_give(ctx, target: discord.Member = None, artifact_type: str = ""):
    """Admin command to give a user a random artifact of specified tier"""
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to give artifacts.")
        return
    
    if not target:
        await ctx.send("❌ Please mention a user! Usage: `P!artifact give <@user> <rare/legendary/eternal>`")
        return
    
    if not artifact_type:
        await ctx.send("❌ Please specify artifact type! Usage: `P!artifact give <@user> <rare/legendary/eternal>`")
        return
    
    # Normalize artifact type
    artifact_type = artifact_type.lower()
    if artifact_type == "legend":
        artifact_type = "legendary"
    
    # Validate artifact type
    if artifact_type not in ["rare", "legendary", "eternal"]:
        await ctx.send("❌ Invalid artifact type! Choose: `rare`, `legendary`, or `eternal`")
        return
    
    # Initialize user data
    target_id = str(target.id)
    if target_id not in chi_data:
        chi_data[target_id] = {
            "chi": 0, 
            "milestones_claimed": [], 
            "mini_quests": [], 
            "rebirths": 0, 
            "purchased_items": [], 
            "artifacts": [], 
            "pets": [], 
            "trade_requests": [], 
            "active_pet": None
        }
    if "artifacts" not in chi_data[target_id]:
        chi_data[target_id]["artifacts"] = []
    
    # Generate random artifact of specified tier
    now = datetime.now(timezone.utc)
    emoji_index = random.randint(0, len(ARTIFACT_CONFIG[artifact_type]["emojis"]) - 1)
    selected_emoji = ARTIFACT_CONFIG[artifact_type]["emojis"][emoji_index]
    selected_name = ARTIFACT_CONFIG[artifact_type]["names"][emoji_index]
    artifact_id = f"{artifact_type}_gift_{int(now.timestamp())}"
    
    # Add to user's artifact inventory
    chi_data[target_id]["artifacts"].append({
        "id": artifact_id,
        "tier": artifact_type,
        "emoji": selected_emoji,
        "name": selected_name,
        "claimed_at": now.isoformat()
    })
    save_data()
    
    # Send confirmation embed
    heal_percent = ARTIFACT_CONFIG[artifact_type]["heal_percent"]
    embed = discord.Embed(
        title=f"{selected_emoji} Artifact Gifted!",
        description=f"**{ctx.author.display_name}** gave **{target.display_name}** a gift!\n\n"
                   f"🎁 **{selected_name}**\n"
                   f"✨ Rarity: **{artifact_type.upper()}**\n"
                   f"💊 Healing Power: **{heal_percent}% HP** in duels\n"
                   f"📦 Total Artifacts: **{len(chi_data[target_id]['artifacts'])}**",
        color=discord.Color.purple() if artifact_type == "rare" else 
              discord.Color.gold() if artifact_type == "legendary" else
              discord.Color.dark_blue()
    )
    embed.set_footer(text=f"{selected_name} • ID: {artifact_id}")
    await ctx.send(embed=embed)
    
    # Log artifact gift
    await log_event(
        "Artifact Gift",
        f"**Admin:** {ctx.author.mention} ({ctx.author.name})\n"
        f"**Recipient:** {target.mention} ({target.name})\n"
        f"**Artifact:** {selected_emoji} {selected_name}\n"
        f"**Tier:** {artifact_type.upper()}\n"
        f"**ID:** {artifact_id}",
        ctx.guild,
        discord.Color.purple() if artifact_type == "rare" else 
        discord.Color.gold() if artifact_type == "legendary" else
        discord.Color.dark_blue()
    )

@bot.command(name="debug")
async def debug_events(ctx):
    global event_active, event_claimer, current_event_message, chi_party_active, chi_party_tokens, chi_party_claims
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to use debug commands.")
        return
    
    event_active = False
    event_claimer = None
    current_event_message = None
    chi_party_active = False
    chi_party_tokens = []
    chi_party_claims = {}
    
    await ctx.send("🔧 Debug: All chi events and chi parties have been cleared!")

@bot.command()
@is_bot_owner()
async def stop(ctx):
    global pax_active
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to stop Pax.")
        return
    
    if not pax_active:
        await ctx.send("⏸️ Pax is already paused!")
        return
    
    pax_active = False
    embed = discord.Embed(
        title="⏸️ Pax Has Been Paused",
        description="Pax has been completely stopped.\n❌ No chi detection\n❌ No reactions\n❌ No commands will work\n\nUse `P!start` to resume.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command()
@is_bot_owner()
async def start(ctx):
    global pax_active
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to start Pax.")
        return
    
    if pax_active:
        await ctx.send("▶️ Pax is already running!")
        return
    
    pax_active = True
    embed = discord.Embed(
        title="▶️ Pax Has Been Resumed",
        description="Pax is now back online and will react to messages and award chi!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="blacklist")
@is_bot_owner()
async def blacklist_cmd(ctx, action: str = "", user_id: str = ""):
    global blacklisted_users
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to manage the blacklist.")
        return
    
    if not action or action.lower() not in ["add", "remove"]:
        await ctx.send("❌ Usage: `P!blacklist <add/remove> <user_id>`")
        return
    
    if not user_id or not user_id.isdigit():
        await ctx.send("❌ Please provide a valid user ID!")
        return
    
    user_id_int = int(user_id)
    action = action.lower()
    
    if action == "add":
        if user_id_int in blacklisted_users:
            await ctx.send(f"❌ User `{user_id}` is already blacklisted!")
            return
        
        blacklisted_users.append(user_id_int)
        save_blacklist()
        
        embed = discord.Embed(
            title="🚫 User Blacklisted",
            description=f"User ID `{user_id}` has been added to the blacklist.\nThey will no longer earn chi or trigger Pax reactions.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    elif action == "remove":
        if user_id_int not in blacklisted_users:
            await ctx.send(f"❌ User `{user_id}` is not in the blacklist!")
            return
        
        blacklisted_users.remove(user_id_int)
        save_blacklist()
        
        embed = discord.Embed(
            title="✅ User Removed from Blacklist",
            description=f"User ID `{user_id}` has been removed from the blacklist.\nThey can now earn chi again.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command(name="reset")
@is_bot_owner()
async def reset_all_chi(ctx):
    """Reset EVERYTHING for all users - chi, rebirths, gardens, inventory, everything! (admin only)"""
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    # Confirmation embed
    confirm_embed = discord.Embed(
        title="⚠️ CONFIRM TOTAL RESET",
        description=(
            "Are you sure you want to reset **EVERYTHING** for all users?\n\n"
            "This will reset:\n"
            "• Chi and Rebirths\n"
            "• Inventory (armor, weapons, tools, items)\n"
            "• Gardens and plants\n"
            "• Teams and team data\n"
            "• Artifacts and pets\n"
            "• Mining cooldowns\n"
            "• Purchased items\n"
            "• All progress and data\n\n"
            "**This action cannot be undone!**\n\n"
            "React with ✅ to confirm or ❌ to cancel."
        ),
        color=discord.Color.red()
    )
    confirm_msg = await ctx.send(embed=confirm_embed)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await ctx.send("❌ Reset cancelled.")
            return
        
        # Reset EVERYTHING
        reset_count = len(chi_data)
        
        # Reset all user data to default (but preserve chest!)
        for user_id in list(chi_data.keys()):
            # Preserve the permanent chest
            preserved_chest = chi_data[user_id].get("chest", [])
            
            chi_data[user_id] = {
                "chi": 0,
                "milestones_claimed": [],
                "mini_quests": [],
                "rebirths": 0,
                "purchased_items": [],
                "rebirth_purchases": [],
                "artifacts": [],
                "pets": [],
                "active_pet": None,
                "inventory": {},
                "garden_inventory": {},
                "custom_attacks": {},
                "mining_cooldown": 0,
                "garden_id": None,
                "chi_cooldown": 0,
                "duel_stats": {"wins": 0, "losses": 0},
                "boss_battles": {},
                "chest": preserved_chest  # NEVER reset the chest!
            }
        
        # Reset teams to proper structure
        teams_data["teams"] = {}
        teams_data["user_teams"] = {}
        teams_data["pending_invites"] = {}
        
        # Reset gardens to proper structure
        gardens_data["gardens"] = {}
        gardens_data["garden_event"] = {"active": False, "end_time": None}
        
        # Clear all active duels, trainings, boss battles
        global active_duel, active_training, active_npc_training, active_boss_battle
        active_duel = None
        active_training = None
        active_npc_training = None
        active_boss_battle = None
        
        save_data()
        save_teams()
        save_gardens()
        
        # Database sync disabled - deprecated bulk methods replaced with guild-aware operations
        # await db.sync_all_data(chi_data, teams_data, gardens_data)
        
        success_embed = discord.Embed(
            title="✅ Total Reset Complete",
            description=(
                f"**EVERYTHING** has been reset for **{reset_count}** users!\n\n"
                "All data wiped:\n"
                "✅ Chi & Rebirths\n"
                "✅ Inventory & Purchases\n"
                "✅ Gardens & Plants\n"
                "✅ Teams & Bases\n"
                "✅ Artifacts & Pets\n"
                "✅ Mining Cooldowns\n"
                "✅ All Progress\n\n"
                "Everyone starts fresh!"
            ),
            color=discord.Color.green()
        )
        success_embed.set_footer(text=f"Reset by {ctx.author.name}")
        await ctx.send(embed=success_embed)
        
        await log_event(
            "🔄 Total Reset Executed",
            f"{ctx.author.mention} reset EVERYTHING for all {reset_count} users", ctx.guild, discord.Color.red())
        
    except asyncio.TimeoutError:
        await ctx.send("⏰ Reset confirmation timed out. No changes were made.")

# P!save command disabled per user request - auto-sync happens every 5 minutes
# @bot.command(name="save")
# async def save_all_data(ctx):
#     """Save all bot data to PostgreSQL database (admin only)"""
#     if not ctx.guild or not ctx.author.guild_permissions.administrator:
#         await ctx.send("❌ You don't have permission to use this command.")
#         return
#    
#    # Check if database is connected
#    if not db or not db.pool:
#        status_msg = f"Database object: {db is not None}, Pool: {db.pool if db else 'N/A'}"
#        print(f"⚠️ P!save failed - {status_msg}")
#        
#        # Try to reconnect
#        try:
#            await ctx.send("🔄 Database not connected. Attempting to reconnect...")
#            await db.connect()
#            await ctx.send("✅ Database reconnected successfully!")
#        except Exception as e:
#            await ctx.send(f"❌ Database connection failed! Error: {str(e)}\n\nPlease contact an admin.")
#            print(f"Database reconnection error: {e}")
#            return
#    
#    processing_msg = await ctx.send("💾 Saving all data to database... This may take a moment.")
#    
#    try:
#        users_saved = await db.save_all_user_data(chi_data)
#        
#        teams_saved = await db.save_all_teams_data(teams_data)
#        
#        gardens_saved = await db.save_all_gardens_data(gardens_data)
#        
#        success_embed = discord.Embed(
#            title="✅ Data Saved Successfully!",
#            description=(
#                "All bot data has been safely saved to the PostgreSQL database!\n\n"
#                "**Saved Data:**\n"
#                f"👥 **Users:** {users_saved} users\n"
#                f"🏆 **Teams:** {teams_saved} teams\n"
#                f"🌱 **Gardens:** {gardens_saved} gardens\n\n"
#                "**What's Saved:**\n"
#                "✅ Chi and Rebirths\n"
#                "✅ Inventory (armor, weapons, tools, items)\n"
#                "✅ Gardens and plants\n"
#                "✅ Teams and team data\n"
#                "✅ Artifacts and pets\n"
#                "✅ Mining cooldowns\n"
#                "✅ Purchased items\n"
#                "✅ All progress and data\n\n"
#                "🔒 Your data is now safe even if the bot restarts or the app is republished!"
#            ),
#            color=discord.Color.green()
#        )
#        success_embed.set_footer(text=f"Saved by {ctx.author.name}")
#        
#        await processing_msg.edit(content=None, embed=success_embed)
#        
#        await log_event(
#            "💾 Data Saved to Database",
#            f"{ctx.author.mention} saved all bot data\n**Users:** {users_saved} | **Teams:** {teams_saved} | **Gardens:** {gardens_saved}",
#            discord.Color.blue()
#        )
#        
#    except Exception as e:
#        error_embed = discord.Embed(
#            title="❌ Save Failed!",
#            description=f"An error occurred while saving data:\n```{str(e)}```\n\nPlease try again or contact the bot administrator.",
#            color=discord.Color.red()
#        )
#        await processing_msg.edit(content=None, embed=error_embed)
#        print(f"Error in P!save command: {e}")

@bot.command()
async def next(ctx):
    global next_event_time
    if next_event_time:
        time_remaining = (next_event_time - datetime.now(timezone.utc)).total_seconds()
        if time_remaining > 0:
            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            await ctx.send(f"⏰ Next Chi Event in approximately **{minutes}m {seconds}s**")
        else:
            await ctx.send("🐼 A Chi Event should appear very soon!")
    else:
        await ctx.send("⏰ Chi Event timer not initialized yet.")

@bot.command()
async def spawn(ctx, event_type: str = "positive"):
    global event_active, event_claimer, current_event_message, current_event_type
    
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to spawn chi events.")
        return
    
    event_type = event_type.lower()
    if event_type not in ["positive", "negative"]:
        await ctx.send("❌ Event type must be `positive` or `negative`! Usage: `P!spawn positive` or `P!spawn negative`")
        return
    
    if event_active:
        await ctx.send("⚠️ A chi event is already active! Wait for it to expire or be claimed.")
        return
    
    if event_type == "positive":
        embed = discord.Embed(
            title="✨🐼 POSITIVE CHI EVENT!",
            description=f"Be the first to claim it! Type `P!claim` within {CHI_EVENT_CLAIM_TIME} seconds!",
            color=discord.Color.gold()
        )
    else:
        embed = discord.Embed(
            title="💀🐼 NEGATIVE CHI EVENT!",
            description=f"Be the first to claim it! Type `P!claim` within {CHI_EVENT_CLAIM_TIME} seconds!\n⚠️ Warning: This will REMOVE chi!",
            color=discord.Color.dark_red()
        )
    
    current_event_message = await ctx.send(embed=embed)
    event_active = True
    event_claimer = None
    current_event_type = event_type
    
    await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=CHI_EVENT_CLAIM_TIME))
    if event_active:
        event_active = False
        event_claimer = None
        await current_event_message.edit(embed=discord.Embed(
            title=f"{'✨' if event_type == 'positive' else '💀'}🐼 Chi Event Expired!",
            description="No one claimed it in time… maybe next round!",
            color=discord.Color.dark_grey()
        ))

@bot.command(name="rshop")
async def rebirth_shop(ctx):
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    total_rebirths = chi_data[user_id].get("rebirths", 0)
    
    embed = discord.Embed(
        title="🏪 Rebirth Shop",
        description=f"**Your Total Rebirths**: {total_rebirths}\n\nAvailable items:",
        color=discord.Color.purple()
    )
    
    for idx, item in enumerate(shop_data["items"], start=1):
        embed.add_field(
            name=f"R{idx}: {item['name']} - {item['cost']} Rebirth{'s' if item['cost'] > 1 else ''}",
            value="\u200b",
            inline=False
        )
    
    embed.set_footer(text="Use P!rbuy <item_name or R#> to purchase items! Example: P!rbuy R1")
    
    # Add functional UI buttons
    shop_view = ShopView(ctx.author.id, chi_data, shop_data, "Rebirth Shop")
    msg = await ctx.send(embed=embed, view=shop_view)
    shop_view.message = msg

@bot.command()
async def rbuy(ctx, *, item_name: str = ""):
    """Purchase items from the Rebirth Shop using rebirths"""
    if not item_name:
        await ctx.send("❌ Usage: `P!rbuy <item_name or ID>`\nExample: `P!rbuy Level` or `P!rbuy R1`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "rebirth_purchases": []}
    
    if "rebirth_purchases" not in chi_data[user_id]:
        chi_data[user_id]["rebirth_purchases"] = []
    
    found_item = None
    
    # Check if using shop ID (R1, R2, etc.)
    if item_name.upper().startswith("R") and item_name[1:].isdigit():
        item_index = int(item_name[1:]) - 1
        if 0 <= item_index < len(shop_data["items"]):
            found_item = shop_data["items"][item_index]
        else:
            await ctx.send(f"❌ Invalid ID '{item_name.upper()}'! Use `P!rshop` to see available items.")
            return
    else:
        # Search by item name
        for item in shop_data["items"]:
            if item["name"].lower() == item_name.lower():
                found_item = item
                break
    
    if not found_item:
        await ctx.send(f"❌ Item '{item_name}' not found in the Rebirth Shop! Use `P!rshop` to see available items.")
        return
    
    total_rebirths = chi_data[user_id].get("rebirths", 0)
    
    if total_rebirths < found_item["cost"]:
        await ctx.send(f"❌ You don't have enough rebirths! You need **{found_item['cost']} rebirth{'s' if found_item['cost'] > 1 else ''}** but only have **{total_rebirths}**.")
        return
    
    chi_data[user_id]["rebirths"] -= found_item["cost"]
    chi_data[user_id]["rebirth_purchases"].append(found_item["name"])
    
    # Handle permanent HP purchases
    if found_item.get("type") == "permanent_hp":
        hp_bonus = found_item.get("hp_bonus", 0)
        if "permanent_hp" not in chi_data[user_id]:
            chi_data[user_id]["permanent_hp"] = 0
        chi_data[user_id]["permanent_hp"] += hp_bonus
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You purchased **{found_item['name']}** for **{found_item['cost']} rebirth{'s' if found_item['cost'] > 1 else ''}**!\n\n💪 **+{hp_bonus} Permanent HP** added to all future duels, boss battles, and training!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Total Permanent HP", value=f"+{chi_data[user_id]['permanent_hp']} HP", inline=True)
        embed.add_field(name="Remaining Rebirths", value=str(chi_data[user_id]["rebirths"]), inline=True)
        embed.set_footer(text="Your max HP has been permanently increased!")
    else:
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You purchased **{found_item['name']}** for **{found_item['cost']} rebirth{'s' if found_item['cost'] > 1 else ''}**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Remaining Rebirths", value=str(chi_data[user_id]["rebirths"]), inline=True)
        embed.set_footer(text="DM Psy to redeem your purchase!")
    
    save_data()
    await ctx.send(embed=embed)

@bot.command()
async def cshop(ctx):
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    current_chi = chi_data[user_id].get("chi", 0)
    
    embed = discord.Embed(
        title="🏪 Chi Shop",
        description=f"**Your Current Chi**: {current_chi}\n\nAvailable cosmetic items:",
        color=discord.Color.gold()
    )
    
    for idx, item in enumerate(chi_shop_data["items"], start=1):
        embed.add_field(
            name=f"C{idx}: {item['name']} - {item['cost']} Chi",
            value="\u200b",
            inline=False
        )
    
    embed.set_footer(text="Use P!buy <item_name or C#> to purchase items! Example: P!buy C1")
    
    # Add functional UI buttons
    shop_view = ShopView(ctx.author.id, chi_data, chi_shop_data, "Chi Shop")
    msg = await ctx.send(embed=embed, view=shop_view)
    shop_view.message = msg


@bot.command()
async def health(ctx):
    """List all available healing items from the Chi Shop"""
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    current_chi = chi_data[user_id].get("chi", 0)
    
    embed = discord.Embed(
        title="💊 Healing Items",
        description=f"**Your Current Chi**: {current_chi}\n\nAll available healing items:",
        color=discord.Color.green()
    )
    
    healing_items = [item for item in chi_shop_data["items"] if "healing" in item.get("tags", [])]
    
    for item in healing_items:
        tier = item.get("tier", "common").capitalize()
        embed.add_field(
            name=f"{item['item_id']}: {item['name']} - {item['cost']} Chi",
            value=f"❤️ Heals: {item.get('healing', 0)} HP | 🏆 Tier: {tier}",
            inline=False
        )
    
    embed.set_footer(text="Use P!buy <item_name or C#> to purchase healing items!")
    await ctx.send(embed=embed)

@bot.command()
async def potions(ctx):
    """List all craftable potions"""
    embed = discord.Embed(
        title="🧪 Craftable Potions",
        description="All potions you can craft using ingredients:\n\n",
        color=discord.Color.purple()
    )
    
    potions = potions_data.get("potions", [])
    
    for potion in potions:
        emoji = potion.get("emoji", "🧪")
        effect_type = potion.get("effect", {}).get("type", "unknown")
        description = potion.get("description", "No description")
        
        embed.add_field(
            name=f"{emoji} {potion['item_id']}: {potion['name']}",
            value=f"{description}",
            inline=False
        )
    
    embed.set_footer(text="Use P!potion craft <P#> to craft a potion! | P!potion ingredients to see required materials")
    await ctx.send(embed=embed)

@bot.command()
async def item(ctx, *, item_query: str = ""):
    """Get detailed information about any item or view custom attacks
    Usage: 
    - P!item <item_name or ID> info - View item details
    - P!item <weapon_name> attacks - View custom attacks for a weapon
    Example: P!item Katana info, P!item Katana attacks, P!item C1 info
    """
    if not item_query:
        await ctx.send("❌ Usage:\n"
                      "`P!item <item_name or ID> info` - View item details\n"
                      "`P!item <weapon_name> attacks` - View custom attacks\n"
                      "Example: `P!item Katana info` or `P!item Katana attacks`")
        return
    
    # Check if this is an "attacks" query
    if item_query.lower().endswith(" attacks"):
        weapon_name = item_query[:-8].strip()
        
        # Find the weapon in chi shop
        weapon_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == weapon_name.lower() and "weapon" in item.get("tags", []):
                weapon_found = item
                break
        
        if not weapon_found:
            await ctx.send(f"❌ '{weapon_name}' is not a valid weapon! Check `P!cshop` for available weapons.")
            return
        
        user_id = str(ctx.author.id)
        
        embed = discord.Embed(
            title=f"⚔️ {weapon_found['name']} - Custom Attacks",
            description=f"All available custom attacks for **{weapon_found['name']}**:",
            color=discord.Color.red()
        )
        
        # Get pre-configured attacks from the item definition
        preconfigured_attacks = weapon_found.get("custom_attacks", {})
        
        if preconfigured_attacks:
            attacks_list = []
            for attack_name, damage_info in preconfigured_attacks.items():
                min_dmg = damage_info.get("min_damage", 0)
                max_dmg = damage_info.get("max_damage", 0)
                attacks_list.append(f"• **{attack_name}** - {min_dmg}-{max_dmg} HP")
            embed.add_field(
                name="🏛️ Pre-configured Attacks (Pandian Realm)",
                value="\n".join(attacks_list),
                inline=False
            )
        
        # Get user-created custom attacks
        user_custom_attacks = []
        if user_id in chi_data and "custom_attacks" in chi_data[user_id]:
            user_custom_attacks = chi_data[user_id]["custom_attacks"].get(weapon_found["name"], [])
        
        if user_custom_attacks:
            user_attacks_list = "\n".join([f"• *{attack}*" for attack in user_custom_attacks])
            embed.add_field(
                name="✨ Your Custom Attacks",
                value=user_attacks_list,
                inline=False
            )
        
        if not preconfigured_attacks and not user_custom_attacks:
            embed.add_field(
                name="No Custom Attacks",
                value=f"This weapon has no pre-configured attacks.\n\n"
                      f"Use `P!duel attack {weapon_found['name']} <Attack Name>` in a duel to create your own!",
                inline=False
            )
        else:
            embed.add_field(
                name="💡 How to Use",
                value=f"In a duel, use: `P!duel attack {weapon_found['name']} <Attack Name>`\n"
                      f"⚠️ Can't use the same attack twice in a row!",
                inline=False
            )
        
        embed.set_footer(text=f"Realm: {weapon_found.get('realm', 'Unknown')}")
        await ctx.send(embed=embed)
        return
    
    # Check if this is an "info" query
    if not item_query.lower().endswith(" info"):
        await ctx.send("❌ Usage:\n"
                      "`P!item <item_name or ID> info` - View item details\n"
                      "`P!item <weapon_name> attacks` - View custom attacks\n"
                      "Example: `P!item Katana info` or `P!item Katana attacks`")
        return
    
    # Remove " info" from the end
    item_name = item_query[:-5].strip()
    
    if not item_name:
        await ctx.send("❌ Please specify an item name or ID!")
        return
    
    found_item = None
    shop_type = None
    item_id = None
    
    # Check Chi Shop (C#)
    if item_name.upper().startswith("C") and item_name[1:].isdigit():
        item_index = int(item_name[1:]) - 1
        if 0 <= item_index < len(chi_shop_data["items"]):
            found_item = chi_shop_data["items"][item_index]
            shop_type = "Chi Shop"
            item_id = f"C{item_index + 1}"
    else:
        for idx, item in enumerate(chi_shop_data["items"], start=1):
            if item["name"].lower() == item_name.lower():
                found_item = item
                shop_type = "Chi Shop"
                item_id = f"C{idx}"
                break
    
    # Check Rebirth Shop (R#)
    if not found_item:
        if item_name.upper().startswith("R") and item_name[1:].isdigit():
            item_index = int(item_name[1:]) - 1
            if 0 <= item_index < len(shop_data["items"]):
                found_item = shop_data["items"][item_index]
                shop_type = "Rebirth Shop"
                item_id = f"R{item_index + 1}"
        else:
            for idx, item in enumerate(shop_data["items"], start=1):
                if item["name"].lower() == item_name.lower():
                    found_item = item
                    shop_type = "Rebirth Shop"
                    item_id = f"R{idx}"
                    break
    
    # Check Garden Shop (G#)
    if not found_item:
        if item_name.upper().startswith("G") and item_name[1:].isdigit():
            item_index = int(item_name[1:]) - 1
            all_items = []
            for tool_name, tool_info in GARDEN_SHOP_ITEMS["tools"].items():
                all_items.append(("tools", tool_name, tool_info))
            for seed_name, seed_info in GARDEN_SHOP_ITEMS["seeds"].items():
                all_items.append(("seeds", seed_name, seed_info))
            
            if 0 <= item_index < len(all_items):
                category, name, info = all_items[item_index]
                found_item = {**info, "name": name, "category": category}
                shop_type = "Garden Shop"
                item_id = f"G{item_index + 1}"
        else:
            idx = 1
            for tool_name, tool_info in GARDEN_SHOP_ITEMS["tools"].items():
                if tool_name.lower() == item_name.lower():
                    found_item = {**tool_info, "name": tool_name, "category": "tools"}
                    shop_type = "Garden Shop"
                    item_id = f"G{idx}"
                    break
                idx += 1
            
            if not found_item:
                tool_count = len(GARDEN_SHOP_ITEMS["tools"])
                idx = tool_count + 1
                for seed_name, seed_info in GARDEN_SHOP_ITEMS["seeds"].items():
                    if seed_name.lower() == item_name.lower():
                        found_item = {**seed_info, "name": seed_name, "category": "seeds"}
                        shop_type = "Garden Shop"
                        item_id = f"G{idx}"
                        break
                    idx += 1
    
    if not found_item:
        await ctx.send(f"❌ Item '{item_name}' not found in any shop! Check `P!cshop`, `P!rshop`, or `P!garden shop`.")
        return
    
    # Build detailed embed
    if shop_type == "Garden Shop":
        color = discord.Color.green()
    elif shop_type == "Chi Shop":
        color = discord.Color.gold()
    else:
        color = discord.Color.purple()
    
    embed = discord.Embed(
        title=f"{found_item.get('emoji', '📦')} {found_item['name']}",
        description=found_item.get("description", "No description available."),
        color=color
    )
    
    embed.add_field(name="🏪 Shop", value=shop_type, inline=True)
    embed.add_field(name="🆔 ID", value=item_id, inline=True)
    
    # Display cost with appropriate currency
    if shop_type == "Chi Shop" or shop_type == "Garden Shop":
        embed.add_field(name="💰 Cost", value=f"{found_item['cost']} chi", inline=True)
    else:
        embed.add_field(name="💰 Cost", value=f"{found_item['cost']} rebirth{'s' if found_item['cost'] > 1 else ''}", inline=True)
    
    # Display type and tags (for chi/rebirth shop items)
    if "type" in found_item:
        embed.add_field(name="📋 Type", value=found_item["type"], inline=True)
    
    if "tags" in found_item and found_item["tags"]:
        embed.add_field(name="🏷️ Tags", value=", ".join(found_item["tags"]), inline=True)
    
    # Display damage (for weapons)
    if "damage" in found_item:
        embed.add_field(name="⚔️ Base Damage", value=str(found_item["damage"]), inline=True)
    
    # Display healing (for healing items)
    if "healing" in found_item:
        embed.add_field(name="💚 Healing", value=str(found_item["healing"]), inline=True)
    
    # Display uses (for consumable items)
    if "uses" in found_item:
        embed.add_field(name="🔢 Uses", value=str(found_item["uses"]), inline=True)
    
    # Garden-specific fields
    if "harvest_chi" in found_item:
        embed.add_field(name="✨ Harvest Reward", value=f"+{found_item['harvest_chi']} chi", inline=True)
    
    if "grow_time_minutes" in found_item:
        embed.add_field(name="⏱️ Growth Time", value=f"{found_item['grow_time_minutes']} minutes", inline=True)
    
    if "category" in found_item:
        embed.add_field(name="📦 Category", value=found_item["category"].capitalize(), inline=True)
    
    embed.set_footer(text=f"Use P!buy {item_id} to purchase from {shop_type}")
    await ctx.send(embed=embed)

@bot.command(name="rebirth")
async def manual_rebirth(ctx):
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        await ctx.send("❌ You don't have any chi to rebirth!")
        return
    
    current_chi = chi_data[user_id]["chi"]
    
    if current_chi == 0:
        await ctx.send("❌ You already have 0 chi! Gain some chi first before rebirthing.")
        return
    
    if current_chi < CHI_REBIRTH_THRESHOLD and current_chi > -CHI_REBIRTH_THRESHOLD:
        await ctx.send(f"❌ You need at least **{CHI_REBIRTH_THRESHOLD}** chi or **-{CHI_REBIRTH_THRESHOLD}** chi to manually rebirth! Your current chi: **{current_chi}**")
        return
    
    # INCREMENTAL REBIRTH: Subtract 500k per rebirth, keep excess chi
    chi_data[user_id]["rebirths"] = chi_data[user_id].get("rebirths", 0) + 1
    if current_chi >= CHI_REBIRTH_THRESHOLD:
        chi_data[user_id]["chi"] = current_chi - CHI_REBIRTH_THRESHOLD
    else:
        chi_data[user_id]["chi"] = current_chi + CHI_REBIRTH_THRESHOLD
    save_data()
    
    total_rebirths = chi_data[user_id].get("rebirths", 0)
    remaining_chi = chi_data[user_id]["chi"]
    
    embed = discord.Embed(
        title=f"🔄 Rebirth Complete!",
        description=f"You spent **{CHI_REBIRTH_THRESHOLD:,}** chi to rebirth!\nRemaining chi: **{remaining_chi:,}**\nYou now have **{total_rebirths}** total rebirth{'s' if total_rebirths > 1 else ''}!",
        color=discord.Color.purple()
    )
    embed.add_field(name="🔄 Total Rebirths", value=str(total_rebirths), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def shop(ctx, shop_name: str = "", action: str = "", cost_or_item: str = "", *, item_or_nothing: str = ""):
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You don't have permission to manage shops.")
        return
    
    if not shop_name or not action:
        await ctx.send("❌ Usage: `P!shop <rebirth/chi> <add/remove> <item_name> <price if adding>`")
        return
    
    shop_name = shop_name.lower()
    action = action.lower()
    
    if shop_name not in ["rebirth", "chi"]:
        await ctx.send("❌ Shop name must be `rebirth` or `chi`!")
        return
    
    if action not in ["add", "remove"]:
        await ctx.send("❌ Action must be `add` or `remove`!")
        return
    
    shop_target = shop_data if shop_name == "rebirth" else chi_shop_data
    save_func = save_shop if shop_name == "rebirth" else save_chi_shop
    shop_display_name = "Rebirth Shop" if shop_name == "rebirth" else "Chi Shop"
    currency = "Rebirth" if shop_name == "rebirth" else "Chi"
    
    if action == "add":
        if not cost_or_item or not item_or_nothing:
            await ctx.send(f"❌ Usage: `P!shop {shop_name} add <item_name> <price>`")
            return
        
        parts = item_or_nothing.split()
        if not parts:
            await ctx.send(f"❌ Usage: `P!shop {shop_name} add <item_name> <price>`")
            return
        
        try:
            cost = int(parts[-1])
        except ValueError:
            await ctx.send("❌ Price must be a valid number!")
            return
        
        item_name_parts = [cost_or_item] + parts[:-1]
        item_name = " ".join(item_name_parts)
        
        if cost <= 0:
            await ctx.send("❌ Cost must be a positive number!")
            return
        
        for item in shop_target["items"]:
            if item["name"].lower() == item_name.lower():
                await ctx.send(f"❌ An item with the name '{item_name}' already exists in the {shop_display_name}!")
                return
        
        shop_target["items"].append({"name": item_name, "cost": cost, "type": "custom"})
        save_func()
        
        embed = discord.Embed(
            title=f"✅ Item Added to {shop_display_name}",
            description=f"**{item_name}** - {cost} {currency}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    elif action == "remove":
        item_name = cost_or_item if not item_or_nothing else cost_or_item + " " + item_or_nothing
        
        for i, item in enumerate(shop_target["items"]):
            if item["name"].lower() == item_name.lower():
                removed_item = shop_target["items"].pop(i)
                save_func()
                embed = discord.Embed(
                    title=f"✅ Item Removed from {shop_display_name}",
                    description=f"**{removed_item['name']}** - {removed_item['cost']} {currency}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        await ctx.send(f"❌ No item found with the name '{item_name}' in the {shop_display_name}")

@bot.command()
async def buy(ctx, *, item_name: str = ""):
    if not item_name:
        await ctx.send("❌ Usage: `P!buy <item_name or ID>`\nExample: `P!buy Bamboo Sword` or `P!buy C1` or `P!buy P3`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "potions": []}
    
    if "purchased_items" not in chi_data[user_id]:
        chi_data[user_id]["purchased_items"] = []
    if "potions" not in chi_data[user_id]:
        chi_data[user_id]["potions"] = []
    
    found_item = None
    is_potion = False
    
    # Check if using potion ID (P1, P2, etc.)
    if item_name.upper().startswith("P") and item_name[1:].isdigit():
        # Search for potion by ID
        for potion in potions_data["potions"]:
            if potion["item_id"].upper() == item_name.upper():
                found_item = potion
                is_potion = True
                break
        
        if not found_item:
            await ctx.send(f"❌ Invalid potion ID '{item_name.upper()}'! Use `P!potion shop` to see available potions.")
            return
    # Check if using chi shop ID (C1, C2, etc.)
    elif item_name.upper().startswith("C") and item_name[1:].isdigit():
        item_index = int(item_name[1:]) - 1
        if 0 <= item_index < len(chi_shop_data["items"]):
            found_item = chi_shop_data["items"][item_index]
        else:
            await ctx.send(f"❌ Invalid ID '{item_name.upper()}'! Use `P!cshop` to see available items.")
            return
    else:
        # Search by item name (chi shop)
        for item in chi_shop_data["items"]:
            if item["name"].lower() == item_name.lower():
                found_item = item
                break
        
        # Search by potion name if not found
        if not found_item:
            for potion in potions_data["potions"]:
                if potion["name"].lower() == item_name.lower():
                    found_item = potion
                    is_potion = True
                    break
    
    if not found_item:
        await ctx.send(f"❌ Item '{item_name}' not found! Use `P!cshop` or `P!potion shop` to see available items.")
        return
    
    current_chi = chi_data[user_id].get("chi", 0)
    
    if current_chi < found_item["cost"]:
        await ctx.send(f"❌ You don't have enough chi! You need **{found_item['cost']:,} chi** but only have **{current_chi:,} chi**.")
        return
    
    # Handle potion purchase (can buy multiple)
    if is_potion:
        chi_data[user_id]["chi"] -= found_item["cost"]
        chi_data[user_id]["potions"].append(found_item["name"])
        save_data()
        
        # Log potion purchase
        await log_event(
            "Potion Purchase",
            f"**User:** {ctx.author.mention} ({ctx.author.name})\n**Potion:** {found_item['emoji']} {found_item['name']}\n**Cost:** {found_item['cost']:,} chi\n**Remaining Chi:** {chi_data[user_id]['chi']:,}", ctx.guild, discord.Color.purple())
        
        embed = discord.Embed(
            title="🧪 Potion Purchased!",
            description=f"You purchased **{found_item['emoji']} {found_item['name']}** for **{found_item['cost']:,} chi**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Effect", value=found_item["description"], inline=False)
        embed.add_field(name="Remaining Chi", value=f"{chi_data[user_id]['chi']:,}", inline=True)
        embed.set_footer(text="Use potions in combat or view them with P!potion list!")
        await ctx.send(embed=embed)
        return
    
    # Handle chi shop purchase (one-time)
    if found_item["name"] in chi_data[user_id]["purchased_items"]:
        await ctx.send(f"❌ You already own **{found_item['name']}**!")
        return
    
    chi_data[user_id]["chi"] -= found_item["cost"]
    chi_data[user_id]["purchased_items"].append(found_item["name"])
    save_data()
    
    # Log shop purchase
    await log_event(
        "Shop Purchase",
        f"**User:** {ctx.author.mention} ({ctx.author.name})\n**Item:** {found_item['name']}\n**Cost:** {found_item['cost']:,} chi\n**Remaining Chi:** {chi_data[user_id]['chi']:,}", ctx.guild, discord.Color.gold())
    
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"You purchased **{found_item['name']}** for **{found_item['cost']:,} chi**!",
        color=discord.Color.green()
    )
    embed.add_field(name="Remaining Chi", value=f"{chi_data[user_id]['chi']:,}", inline=True)
    embed.set_footer(text="Check your inventory with P!inv!")
    await ctx.send(embed=embed)

@bot.command(name="inventory", aliases=["inv"])
async def inventory(ctx):
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if "purchased_items" not in chi_data[user_id]:
        chi_data[user_id]["purchased_items"] = []
    
    purchased_items = chi_data[user_id].get("purchased_items", [])
    inventory_dict = chi_data[user_id].get("inventory", {})
    
    embed = discord.Embed(
        title=f"🎒 {ctx.author.display_name}'s Complete Inventory",
        description=f"💎 **Chi:** {chi_data[user_id].get('chi', 0):,} | ♻️ **Rebirths:** {chi_data[user_id].get('rebirths', 0)}",
        color=discord.Color.purple()
    )
    
    # Categorize purchased items
    weapons = []
    armor = []
    healing = []
    misc_items = []
    
    for item_name in purchased_items:
        item_level = get_item_level(ctx.author.id, item_name)
        level_str = f" +{item_level} ⚡" if item_level > 0 else ""
        
        # Categorize by keywords
        item_lower = item_name.lower()
        if any(w in item_lower for w in ["sword", "katana", "blade", "staff", "dagger", "spear", "bamboo strike"]):
            weapons.append(f"⚔️ **{item_name}**{level_str}")
        elif any(a in item_lower for a in ["coat", "armor", "shield", "helmet", "aura", "robe", "hat"]):
            armor.append(f"🛡️ **{item_name}**{level_str}")
        elif any(h in item_lower for h in ["tea", "potion", "orb", "bamboo orb", "heal"]):
            healing.append(f"💚 **{item_name}**{level_str}")
        else:
            misc_items.append(f"📦 **{item_name}**{level_str}")
    
    # Add categorized sections
    if weapons:
        embed.add_field(name="⚔️ Weapons", value="\n".join(weapons[:10]), inline=True)
    if armor:
        embed.add_field(name="🛡️ Armor & Protection", value="\n".join(armor[:10]), inline=True)
    if healing:
        embed.add_field(name="💚 Healing Items", value="\n".join(healing[:10]), inline=True)
    
    # Add ALL inventory items (from inventory dict)
    general_inventory = []
    for item_name, quantity in inventory_dict.items():
        if quantity > 0:
            # Find emoji or use default
            item_emoji = "📦"
            item_lower = item_name.lower()
            
            # Categorize items
            if any(o in item_lower for o in ["ore", "crystal", "voidstone", "gem", "mineral", "stone"]):
                item_emoji = "💎"
            elif any(w in item_lower for w in ["sword", "katana", "blade", "dagger", "spear", "bamboo"]):
                item_emoji = "⚔️"
            elif any(a in item_lower for a in ["armor", "shield", "helmet"]):
                item_emoji = "🛡️"
            elif any(p in item_lower for p in ["potion", "elixir", "brew"]):
                item_emoji = "🧪"
            elif any(h in item_lower for h in ["herb", "petal", "leaf", "blossom", "root", "flower"]):
                item_emoji = "🌿"
            elif any(f in item_lower for f in ["quartz", "shard"]):
                item_emoji = "💠"
            
            general_inventory.append(f"{item_emoji} **{item_name}** x{quantity}")
    
    if general_inventory:
        embed.add_field(name="🎒 Inventory Items", value="\n".join(general_inventory[:15]), inline=False)
    
    if misc_items:
        embed.add_field(name="📦 Other Items", value="\n".join(misc_items[:10]), inline=False)
    
    food_inventory = chi_data[user_id].get("food_inventory", {})
    if food_inventory:
        food_display = []
        for food_name, quantity in food_inventory.items():
            food_display.append(f"• **{food_name}** x{quantity}")
        
        embed.add_field(
            name="🍱 Food Inventory",
            value="\n".join(food_display) if food_display else "No food items",
            inline=False
        )
    
    artifacts = chi_data[user_id].get("artifacts", [])
    if artifacts:
        artifact_display = []
        for artifact in artifacts:
            artifact_display.append(f"• {artifact['emoji']} **{artifact['name']}** ({artifact['tier'].capitalize()})")
        
        embed.add_field(
            name="💎 Artifacts",
            value="\n".join(artifact_display[:10]) if artifact_display else "No artifacts",
            inline=False
        )
    
    pets = chi_data[user_id].get("pets", [])
    if pets:
        pet_display = []
        for pet in pets:
            pet_display.append(f"• 🐾 **{pet.get('name', 'Unknown')}** (HP: {pet.get('health', 0)}/{pet.get('max_health', 100)})")
        
        embed.add_field(
            name="🐾 Pets",
            value="\n".join(pet_display[:5]) if pet_display else "No pets",
            inline=False
        )
    
    garden_inventory = chi_data[user_id].get("garden_inventory", {})
    # CRITICAL: Ensure garden_inventory is a dict before calling .items()
    if not isinstance(garden_inventory, dict):
        print(f"⚠️ ERROR: garden_inventory is {type(garden_inventory).__name__}, not dict! Resetting for user {user_id}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
        garden_inventory = {}
    
    if garden_inventory:
        garden_display = []
        for item_name, quantity in garden_inventory.items():
            # Skip items with zero quantity (but include "owned" for seeds)
            if isinstance(quantity, int) and quantity <= 0:
                continue
            if quantity == 0:
                continue
            
            # Find emoji from shop items
            emoji = "📦"
            if item_name in GARDEN_SHOP_ITEMS["tools"]:
                emoji = GARDEN_SHOP_ITEMS["tools"][item_name]["emoji"]
            elif item_name in GARDEN_SHOP_ITEMS["seeds"]:
                emoji = GARDEN_SHOP_ITEMS["seeds"][item_name]["emoji"]
            
            # Display quantity (numeric for both seeds and tools)
            if quantity == "owned":
                quantity = 0  # Handle legacy "owned" values
            if isinstance(quantity, int) and quantity > 0:
                if item_name in GARDEN_SHOP_ITEMS["seeds"]:
                    garden_display.append(f"• {emoji} **{item_name}** x{quantity} seeds")
                else:
                    garden_display.append(f"• {emoji} **{item_name}** x{quantity}")
        
        if garden_display:
            embed.add_field(
                name="🌸 Garden Items",
                value="\n".join(garden_display),
                inline=False
            )
    
    boss_keys = chi_data[user_id].get("boss_keys", [])
    if boss_keys:
        keys_display = []
        for key in boss_keys:
            keys_display.append(f"• {key}")
        
        embed.add_field(
            name="🔑 Boss Keys",
            value="\n".join(keys_display) if keys_display else "No keys",
            inline=False
        )
    
    # Display potions
    potions = chi_data[user_id].get("potions", [])
    if potions:
        potion_counts = {}
        for potion_name in potions:
            potion_counts[potion_name] = potion_counts.get(potion_name, 0) + 1
        
        potion_display = []
        for potion_name, count in potion_counts.items():
            # Find potion emoji
            emoji = "🧪"
            for p in potions_data["potions"]:
                if p["name"] == potion_name:
                    emoji = p["emoji"]
                    break
            potion_display.append(f"• {emoji} **{potion_name}** x{count}")
        
        embed.add_field(
            name="🧪 Potions",
            value="\n".join(potion_display[:10]) if potion_display else "No potions",
            inline=False
        )
    
    # Display ingredients
    ingredients = chi_data[user_id].get("ingredients", {})
    if ingredients:
        ingredient_display = []
        for ing_id, quantity in ingredients.items():
            if quantity > 0 and ing_id in potions_data["ingredients"]:
                ing_data = potions_data["ingredients"][ing_id]
                ingredient_display.append(f"• {ing_data['emoji']} **{ing_data['name']}** x{quantity}")
        
        if ingredient_display:
            embed.add_field(
                name="🌿 Crafting Ingredients",
                value="\n".join(ingredient_display[:10]),
                inline=False
            )
    
    embed.set_footer(text="Use P!potion list for detailed potion info | P!quest list for quest progress!")
    await ctx.send(embed=embed)

@bot.command()
async def tools(ctx):
    """View your garden tools and their bonuses
    
    Tools provide percentage bonuses to harvest chi, growth speed, and flat chi bonuses.
    Acquire tools by purchasing from Chi Shop, crafting, or finding during artifact searches!
    """
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id) if ctx.guild else "0"
    
    if user_id not in chi_data:
        chi_data[user_id] = initialize_user_data(user_id, guild_id)
    
    # Get user's tools from inventory
    user_tools = chi_data[user_id].get("garden_tools", {})
    
    embed = discord.Embed(
        title=f"🛠️ {ctx.author.display_name}'s Garden Tools",
        description="Garden tools boost harvest chi, growth speed, and provide bonuses!",
        color=discord.Color.green()
    )
    
    if not user_tools:
        embed.add_field(
            name="📦 No Tools Yet",
            value=(
                "You don't have any garden tools yet!\n\n"
                "**How to Get Tools:**\n"
                "🛒 Purchase basic tools from **`P!cshop tools`**\n"
                "⚒️ Craft advanced tools with **`P!craft`**\n"
                "🔍 Find rare tools during **`P!find artifact`** searches"
            ),
            inline=False
        )
    else:
        # Group tools by tier
        tools_by_tier = {"Basic": [], "Advanced": [], "Elite": [], "Mythic": []}
        total_harvest_bonus = 0
        total_speed_bonus = 0
        total_flat_bonus = 0
        
        for tool_key, quantity in user_tools.items():
            if quantity > 0 and tool_key in GARDEN_TOOLS:
                tool = GARDEN_TOOLS[tool_key]
                tier = tool["tier"]
                tools_by_tier[tier].append((tool, quantity))
                
                # Calculate totals (bonuses stack additively)
                total_harvest_bonus += tool["harvest_bonus_percent"]
                total_speed_bonus += tool["speed_bonus_percent"]
                total_flat_bonus += tool["flat_chi_bonus"]
        
        # Display tools by tier
        for tier in ["Basic", "Advanced", "Elite", "Mythic"]:
            if tools_by_tier[tier]:
                tier_display = []
                for tool, quantity in tools_by_tier[tier]:
                    bonuses = []
                    if tool["harvest_bonus_percent"] > 0:
                        bonuses.append(f"+{tool['harvest_bonus_percent']}% harvest")
                    if tool["speed_bonus_percent"] > 0:
                        bonuses.append(f"+{tool['speed_bonus_percent']}% speed")
                    if tool["flat_chi_bonus"] > 0:
                        bonuses.append(f"+{tool['flat_chi_bonus']} chi")
                    if "special_effect" in tool:
                        bonuses.append(tool["special_effect"])
                    
                    bonus_text = ", ".join(bonuses) if bonuses else "No bonuses"
                    tier_display.append(f"• {tool['emoji']} **{tool['name']}** x{quantity}\n  └ {bonus_text}")
                
                embed.add_field(
                    name=f"{'⭐' if tier == 'Basic' else '✨' if tier == 'Advanced' else '💫' if tier == 'Elite' else '🌟'} {tier} Tier",
                    value="\n".join(tier_display),
                    inline=False
                )
        
        # Display total bonuses
        embed.add_field(
            name="📊 Total Active Bonuses",
            value=(
                f"🌾 **Harvest Bonus:** +{total_harvest_bonus}% chi\n"
                f"⚡ **Growth Speed:** +{total_speed_bonus}% faster\n"
                f"💰 **Flat Chi Bonus:** +{total_flat_bonus} per harvest"
            ),
            inline=False
        )
    
    embed.set_footer(text="Use P!craft to create advanced tools | P!cshop tools to purchase basic tools")
    await ctx.send(embed=embed)

@bot.command()
async def craft(ctx, *, tool_name: str = ""):
    """Craft advanced garden tools using artifacts and materials
    
    Usage:
    - P!craft - List craftable tools
    - P!craft <tool_name> - Craft a specific tool
    
    Examples:
    - P!craft
    - P!craft Silverdew Scythe
    - P!craft Eternal Planters
    """
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id) if ctx.guild else "0"
    
    if user_id not in chi_data:
        chi_data[user_id] = initialize_user_data(user_id, guild_id)
    
    # Get craftable tools (those with crafting recipes)
    craftable_tools = {k: v for k, v in GARDEN_TOOLS.items() if "crafting_recipe" in v}
    
    # List all craftable tools
    if not tool_name:
        embed = discord.Embed(
            title="⚒️ Craftable Garden Tools",
            description="Use artifacts and materials to craft powerful garden tools!",
            color=discord.Color.gold()
        )
        
        # Group by tier
        tools_by_tier = {"Advanced": [], "Elite": [], "Mythic": []}
        for tool_key, tool in craftable_tools.items():
            tier = tool["tier"]
            if tier in tools_by_tier:
                tools_by_tier[tier].append((tool_key, tool))
        
        for tier in ["Advanced", "Elite", "Mythic"]:
            if tools_by_tier[tier]:
                tier_display = []
                for tool_key, tool in tools_by_tier[tier]:
                    recipe_text = ", ".join([f"{qty}x {item}" for item, qty in tool["crafting_recipe"].items()])
                    tier_display.append(
                        f"{tool['emoji']} **{tool['name']}**\n"
                        f"  └ **Recipe:** {recipe_text}\n"
                        f"  └ **Bonuses:** {tool['description']}"
                    )
                
                embed.add_field(
                    name=f"{'✨' if tier == 'Advanced' else '💫' if tier == 'Elite' else '🌟'} {tier} Tier",
                    value="\n".join(tier_display),
                    inline=False
                )
        
        embed.set_footer(text="Use P!craft <tool_name> to craft a specific tool")
        await ctx.send(embed=embed)
        return
    
    # Find the tool to craft
    tool_key = None
    tool_data = None
    for key, tool in craftable_tools.items():
        if tool["name"].lower() == tool_name.lower():
            tool_key = key
            tool_data = tool
            break
    
    if not tool_data:
        await ctx.send(f"❌ Tool **{tool_name}** not found or not craftable! Use `P!craft` to see all craftable tools.")
        return
    
    # Check if user has all required materials
    user_inv = chi_data[user_id].get("inventory", [])
    user_ores = chi_data[user_id].get("ores", {})
    user_artifacts = chi_data[user_id].get("permanent_chest", {}).get("artifacts", [])
    
    missing_materials = []
    materials_to_consume = []
    
    for material, required_qty in tool_data["crafting_recipe"].items():
        # Check in different inventories
        if "Ore" in material:
            # Check ores
            current_qty = user_ores.get(material, 0)
            if current_qty < required_qty:
                missing_materials.append(f"{material} (have {current_qty}, need {required_qty})")
            else:
                materials_to_consume.append(("ores", material, required_qty))
        elif "Artifact" in material or "Shard" in material or "Scale" in material or "Crystal" in material or "Dust" in material:
            # Check permanent chest artifacts/items
            artifact_count = user_artifacts.count(material)
            if artifact_count < required_qty:
                missing_materials.append(f"{material} (have {artifact_count}, need {required_qty})")
            else:
                materials_to_consume.append(("artifacts", material, required_qty))
        else:
            # Check regular inventory
            item_count = user_inv.count(material)
            if item_count < required_qty:
                missing_materials.append(f"{material} (have {item_count}, need {required_qty})")
            else:
                materials_to_consume.append(("inventory", material, required_qty))
    
    if missing_materials:
        embed = discord.Embed(
            title="❌ Missing Materials",
            description=f"You don't have enough materials to craft **{tool_data['name']}**!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Missing:",
            value="\n".join([f"• {mat}" for mat in missing_materials]),
            inline=False
        )
        embed.set_footer(text="Gather materials from mining, boss battles, and artifact searches!")
        await ctx.send(embed=embed)
        return
    
    # Consume materials
    for storage_type, material, qty in materials_to_consume:
        if storage_type == "ores":
            user_ores[material] -= qty
            if user_ores[material] <= 0:
                del user_ores[material]
        elif storage_type == "artifacts":
            for _ in range(qty):
                user_artifacts.remove(material)
        else:  # inventory
            for _ in range(qty):
                user_inv.remove(material)
    
    # Add tool to user's garden_tools
    if "garden_tools" not in chi_data[user_id]:
        chi_data[user_id]["garden_tools"] = {}
    
    if tool_key not in chi_data[user_id]["garden_tools"]:
        chi_data[user_id]["garden_tools"][tool_key] = 0
    chi_data[user_id]["garden_tools"][tool_key] += 1
    
    save_data()
    
    # Success message
    embed = discord.Embed(
        title="⚒️ Tool Crafted!",
        description=f"You successfully crafted {tool_data['emoji']} **{tool_data['name']}**!",
        color=discord.Color.green()
    )
    embed.add_field(
        name="✨ Bonuses",
        value=tool_data['description'],
        inline=False
    )
    embed.set_footer(text="Use P!tools to view all your garden tools and bonuses!")
    await ctx.send(embed=embed)

@bot.command()
async def bundle(ctx, action: str = "", *, bundle_name: str = ""):
    """View and purchase garden bundles
    
    Usage:
    - P!bundle - View all available bundles
    - P!bundle buy <bundle_name> - Purchase a bundle
    
    Examples:
    - P!bundle
    - P!bundle buy Sickle Bundle
    - P!bundle buy heroic
    """
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id) if ctx.guild else "0"
    
    # Initialize user data
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    if action.lower() == "buy" and bundle_name:
        # Find bundle (case-insensitive search)
        found_bundle = None
        actual_bundle_name = None
        
        for bundle_key, bundle_info in GARDEN_SHOP_ITEMS["bundles"].items():
            if bundle_key.lower() == bundle_name.lower() or bundle_name.lower() in bundle_key.lower():
                found_bundle = bundle_info
                actual_bundle_name = bundle_key
                break
        
        if not found_bundle:
            await ctx.send(f"❌ Bundle '{bundle_name}' not found!\n"
                          f"Use `P!bundle` to see all available bundles.")
            return
        
        # Check if user has enough chi
        bundle_cost = found_bundle["cost"]
        user_chi = chi_data[user_id].get("chi", 0)
        
        if user_chi < bundle_cost:
            await ctx.send(f"❌ You need **{bundle_cost:,} chi** to buy **{actual_bundle_name}**!\n"
                          f"You have **{user_chi:,} chi**.")
            return
        
        # Initialize garden_inventory if needed
        if "garden_inventory" not in chi_data[user_id]:
            chi_data[user_id]["garden_inventory"] = {}
        
        # CRITICAL: Ensure garden_inventory is a dict
        if not isinstance(chi_data[user_id]["garden_inventory"], dict):
            print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}!")
            chi_data[user_id]["garden_inventory"] = {}
        
        # Deduct chi
        chi_data[user_id]["chi"] -= bundle_cost
        
        # Add all bundle contents to inventory
        items_added = []
        for item_name, item_quantity in found_bundle["contents"].items():
            # Add to garden inventory
            current_qty = chi_data[user_id]["garden_inventory"].get(item_name, 0)
            if current_qty == "owned":  # Handle legacy values
                current_qty = 0
            chi_data[user_id]["garden_inventory"][item_name] = current_qty + item_quantity
            
            # Find emoji from shop items
            item_emoji = "📦"
            for category in ["tools", "seeds"]:
                if item_name in GARDEN_SHOP_ITEMS.get(category, {}):
                    item_emoji = GARDEN_SHOP_ITEMS[category][item_name]["emoji"]
                    break
            
            items_added.append(f"{item_emoji} {item_name} x{item_quantity}")
        
        save_data()
        
        # Log bundle purchase
        await log_event(
            "Bundle Purchase",
            f"**User:** {ctx.author.mention} ({ctx.author.name})\n"
            f"**Bundle:** {found_bundle['emoji']} {actual_bundle_name}\n"
            f"**Cost:** {bundle_cost:,} chi\n"
            f"**Contents:** {', '.join(items_added)}\n"
            f"**Remaining Chi:** {chi_data[user_id]['chi']:,}",
            discord.Color.gold()
        )
        
        # Success message
        embed = discord.Embed(
            title=f"{found_bundle['emoji']} Bundle Purchased!",
            description=f"**{actual_bundle_name}** purchased for **{bundle_cost:,} chi**!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📦 Bundle Contents",
            value="\n".join(items_added),
            inline=False
        )
        embed.add_field(
            name="💰 New Chi Balance",
            value=f"**{chi_data[user_id]['chi']:,} chi**",
            inline=False
        )
        embed.set_footer(text="Items added to your garden inventory! Use P!inv to view them.")
        await ctx.send(embed=embed)
    
    else:
        # Display all bundles
        embed = discord.Embed(
            title="📦 Garden Bundles",
            description="Premium bundles with tools, seeds, and items!\n\n"
                       "**Buy a bundle:** `P!bundle buy <bundle_name>`",
            color=discord.Color.gold()
        )
        
        for idx, (bundle_name, bundle_info) in enumerate(GARDEN_SHOP_ITEMS["bundles"].items(), start=1):
            # Build contents list
            contents_list = []
            for item_name, item_qty in bundle_info["contents"].items():
                # Find emoji
                item_emoji = "📦"
                for category in ["tools", "seeds"]:
                    if item_name in GARDEN_SHOP_ITEMS.get(category, {}):
                        item_emoji = GARDEN_SHOP_ITEMS[category][item_name]["emoji"]
                        break
                contents_list.append(f"{item_emoji} {item_name} x{item_qty}")
            
            embed.add_field(
                name=f"{bundle_info['emoji']} {bundle_name} - {bundle_info['cost']:,} chi",
                value=f"*{bundle_info['description']}*\n\n**Contains:**\n" + "\n".join(contents_list),
                inline=False
            )
        
        embed.set_footer(text="Example: P!bundle buy Sickle Bundle")
        await ctx.send(embed=embed)

@bot.command()
async def say(ctx, *, text: str = ""):
    """Make the bot say something (requires Manage Messages or Administrator permission)
    
    Usage: P!say <text>
    Example: P!say Hello everyone!
    """
    # Check if user has Manage Messages or Administrator permission
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server!")
        return
    
    if not (ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator):
        await ctx.send("❌ You need **Manage Messages** or **Administrator** permission to use this command!")
        return
    
    if not text:
        await ctx.send("❌ Please provide text for me to say!\n"
                      "Usage: `P!say <text>`\n"
                      "Example: `P!say Hello everyone!`")
        return
    
    # Delete the user's command message if bot has permissions
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Send the text
    await ctx.send(text)

@bot.command()
async def sell(ctx, seed_name: str = "", quantity: int = 1):
    """Sell garden seeds for 1 chi each
    
    Usage:
    - P!sell <seed_name> [quantity]
    - P!sell "Peace Lily" 5
    - P!sell Lavender
    """
    user_id = str(ctx.author.id)
    
    # Check if user provided a seed name
    if not seed_name:
        await ctx.send("❌ Usage: `P!sell <seed_name> [quantity]`\n"
                      "Example: `P!sell Lavender 5` - sells 5 Lavender seeds for 5 chi\n\n"
                      "📋 View your seeds with `P!inv` (Garden Items section)")
        return
    
    # Initialize user data
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    # Initialize garden_inventory if needed
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}!")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    garden_inventory = chi_data[user_id]["garden_inventory"]
    
    # Validate quantity
    if quantity < 1:
        await ctx.send("❌ Quantity must be at least 1!")
        return
    
    if quantity > 1000:
        await ctx.send("❌ You can only sell up to 1000 seeds at once!")
        return
    
    # Find seed in inventory (case-insensitive search)
    matching_seed = None
    for inv_seed_name in garden_inventory.keys():
        if inv_seed_name.lower() == seed_name.lower():
            matching_seed = inv_seed_name
            break
    
    if not matching_seed:
        await ctx.send(f"❌ You don't have any **{seed_name}** seeds in your inventory!\n"
                      f"View your garden inventory with `P!inv` or buy seeds with `P!garden shop`")
        return
    
    # Check if it's actually a seed (not a tool)
    if matching_seed not in GARDEN_SHOP_ITEMS["seeds"]:
        await ctx.send(f"❌ **{matching_seed}** is not a seed! You can only sell seeds.\n"
                      f"Tools cannot be sold.")
        return
    
    # Get current seed count
    current_seeds = garden_inventory[matching_seed]
    
    # Handle legacy "owned" values
    if current_seeds == "owned":
        current_seeds = 0
    
    if not isinstance(current_seeds, int):
        current_seeds = 0
    
    # Check if user has enough seeds
    if current_seeds < quantity:
        # Funny seed bug message
        await ctx.send(f"❌ You only have **{current_seeds}x {matching_seed}** seeds!\n"
                      f"You tried to sell **{quantity}** seeds.\n\n"
                      f"*nyuom nyuom nyuom thx for da seeds very yum yum in my tum tum* 🐼")
        return
    
    # Calculate chi earned (30% of seed cost)
    seed_cost = GARDEN_SHOP_ITEMS["seeds"][matching_seed]["cost"]
    chi_per_seed = int(seed_cost * 0.30)  # 30% of purchase price
    chi_earned = quantity * chi_per_seed
    
    # Update inventory and chi
    garden_inventory[matching_seed] -= quantity
    chi_data[user_id]["chi"] += chi_earned
    
    # Remove seed from inventory if count reaches 0
    if garden_inventory[matching_seed] <= 0:
        del garden_inventory[matching_seed]
    
    save_data()
    
    # Get seed emoji
    seed_emoji = GARDEN_SHOP_ITEMS["seeds"][matching_seed]["emoji"]
    
    # Log the sale
    await log_event(
        "Seed Sale",
        f"**User:** {ctx.author.mention} ({ctx.author.name})\n"
        f"**Seeds Sold:** {quantity}x {seed_emoji} {matching_seed}\n"
        f"**Chi Earned:** {chi_earned:,} chi\n"
        f"**New Chi Balance:** {chi_data[user_id]['chi']:,} chi", ctx.guild, discord.Color.gold())
    
    # Send confirmation
    remaining = garden_inventory.get(matching_seed, 0)
    remaining_text = f"\nRemaining: **{remaining}x {matching_seed}**" if remaining > 0 else ""
    
    await ctx.send(f"💰 Sold **{quantity}x {seed_emoji} {matching_seed}** for **{chi_earned:,} chi**!{remaining_text}\n"
                  f"New chi balance: **{chi_data[user_id]['chi']:,} chi**")

@bot.command()
async def chest(ctx, *args):
    """Permanent storage chest that never resets
    
    Usage:
    - P!chest - View chest contents
    - P!chest <item name> add - Store an item
    - P!chest <item name> remove - Retrieve an item
    
    Note: Cannot store chi, rebirths, pets, or locked garden plants
    """
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    # Initialize chest if not exists
    if "chest" not in chi_data[user_id]:
        chi_data[user_id]["chest"] = []
    
    # View chest contents
    if not args:
        chest_items = chi_data[user_id].get("chest", [])
        
        embed = discord.Embed(
            title=f"📦 {ctx.author.display_name}'s Permanent Chest",
            description="Items stored here will **never** be reset, even with `P!reset`!\n\n*Cannot store: Chi, Rebirths, Pets, or Locked Garden Plants*",
            color=discord.Color.from_rgb(139, 69, 19)
        )
        
        if not chest_items:
            embed.add_field(
                name="Empty Chest",
                value="Use `P!chest <item> add` to store items safely!",
                inline=False
            )
        else:
            # Count duplicates
            item_counts = {}
            for item in chest_items:
                item_counts[item] = item_counts.get(item, 0) + 1
            
            # Display items
            display_items = []
            for item_name, count in sorted(item_counts.items()):
                if count > 1:
                    display_items.append(f"📦 **{item_name}** x{count}")
                else:
                    display_items.append(f"📦 **{item_name}**")
            
            embed.add_field(
                name=f"Stored Items ({len(chest_items)} total)",
                value="\n".join(display_items[:25]) if display_items else "Empty",
                inline=False
            )
        
        embed.set_footer(text="P!chest <item> add/remove | Safe storage forever!")
        await ctx.send(embed=embed)
        return
    
    # Parse command: P!chest <item name> <add/remove>
    if len(args) < 2:
        await ctx.send("❌ Usage: `P!chest <item name> <add/remove>`\nExample: `P!chest Dragon Sword add`")
        return
    
    action = args[-1].lower()
    item_name = " ".join(args[:-1])
    
    if action not in ["add", "remove"]:
        await ctx.send("❌ Action must be `add` or `remove`\nExample: `P!chest Dragon Sword add`")
        return
    
    # ADD to chest
    if action == "add":
        # Check if item is forbidden
        forbidden_keywords = ["chi", "rebirth", "pet", "locked"]
        item_lower = item_name.lower()
        
        if any(keyword in item_lower for keyword in forbidden_keywords):
            await ctx.send(f"❌ You cannot store **{item_name}** in the chest! (Chi, rebirths, pets, and locked plants are not allowed)")
            return
        
        # Check if user owns the item
        purchased_items = chi_data[user_id].get("purchased_items", [])
        inventory_dict = chi_data[user_id].get("inventory", {})
        garden_inventory = chi_data[user_id].get("garden_inventory", {})
        artifacts = chi_data[user_id].get("artifacts", [])
        potions = chi_data[user_id].get("potions", [])
        
        found = False
        
        # Check purchased items
        if item_name in purchased_items:
            purchased_items.remove(item_name)
            chi_data[user_id]["chest"].append(item_name)
            found = True
        
        # Check inventory (ores, crystals)
        elif item_name in inventory_dict and inventory_dict[item_name] > 0:
            inventory_dict[item_name] -= 1
            if inventory_dict[item_name] <= 0:
                del inventory_dict[item_name]
            chi_data[user_id]["chest"].append(item_name)
            found = True
        
        # Check garden inventory (seeds, tools)
        elif item_name in garden_inventory and garden_inventory[item_name] > 0:
            # Block locked seeds
            if "locked" in str(garden_inventory.get(item_name, "")).lower():
                await ctx.send(f"❌ Cannot store locked garden plants!")
                return
            
            garden_inventory[item_name] -= 1
            if garden_inventory[item_name] <= 0:
                del garden_inventory[item_name]
            chi_data[user_id]["chest"].append(item_name)
            found = True
        
        # Check artifacts
        elif any(art["name"] == item_name for art in artifacts):
            artifact = next(art for art in artifacts if art["name"] == item_name)
            artifacts.remove(artifact)
            chi_data[user_id]["chest"].append(item_name)
            found = True
        
        # Check potions
        elif item_name in potions:
            potions.remove(item_name)
            chi_data[user_id]["chest"].append(item_name)
            found = True
        
        if found:
            save_data()
            embed = discord.Embed(
                title="✅ Item Stored in Chest",
                description=f"**{item_name}** has been safely stored in your permanent chest!",
                color=discord.Color.green()
            )
            embed.set_footer(text="This item will NEVER be reset, even with P!reset!")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ You don't own **{item_name}**! Check your inventory with `P!inv`")
    
    # REMOVE from chest
    elif action == "remove":
        chest_items = chi_data[user_id].get("chest", [])
        
        if item_name not in chest_items:
            await ctx.send(f"❌ **{item_name}** is not in your chest! Use `P!chest` to view stored items.")
            return
        
        # Remove from chest and add to purchased_items
        chest_items.remove(item_name)
        
        if "purchased_items" not in chi_data[user_id]:
            chi_data[user_id]["purchased_items"] = []
        
        chi_data[user_id]["purchased_items"].append(item_name)
        save_data()
        
        embed = discord.Embed(
            title="✅ Item Retrieved from Chest",
            description=f"**{item_name}** has been moved back to your inventory!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Check your inventory with P!inv")
        await ctx.send(embed=embed)

@bot.command()
async def quest(ctx, subcommand: str = ""):
    if not subcommand or subcommand.lower() not in ["list", "completed", "todo"]:
        await ctx.send("❌ Usage: `P!quest <list/completed/todo>`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if "purchased_items" not in chi_data[user_id]:
        chi_data[user_id]["purchased_items"] = []
    
    user_purchased_items = chi_data[user_id].get("purchased_items", [])
    
    completed_quests = []
    todo_quests = []
    
    for quest in ITEM_QUESTS:
        if quest["item_needed"] in user_purchased_items:
            completed_quests.append(quest)
        else:
            todo_quests.append(quest)
    
    subcommand = subcommand.lower()
    
    if subcommand == "list":
        embed = discord.Embed(
            title="📋 Quest List",
            description="Here are all available quests:",
            color=discord.Color.blue()
        )
        
        for quest in ITEM_QUESTS:
            is_completed = quest["item_needed"] in user_purchased_items
            status_icon = "✅" if is_completed else "❌"
            dialogue = quest["dialogue"].format(user=ctx.author.name)
            
            embed.add_field(
                name=f"{status_icon} {quest['name']}",
                value=f"*Pax says: {dialogue}*\n**Item needed:** {quest['item_needed']}",
                inline=False
            )
        
        total_completed = len(completed_quests)
        total_quests = len(ITEM_QUESTS)
        embed.set_footer(text=f"Completed: {total_completed}/{total_quests} quests")
        await ctx.send(embed=embed)
    
    elif subcommand == "completed":
        if not completed_quests:
            await ctx.send("❌ You haven't completed any quests yet! Use `P!quest todo` to see what you need.")
            return
        
        embed = discord.Embed(
            title="✅ Completed Quests",
            description=f"You've completed {len(completed_quests)} quest{'s' if len(completed_quests) > 1 else ''}!",
            color=discord.Color.green()
        )
        
        for quest in completed_quests:
            dialogue = quest["dialogue"].format(user=ctx.author.name)
            embed.add_field(
                name=f"✅ {quest['name']}",
                value=f"*Pax says: {dialogue}*\n**Item obtained:** {quest['item_needed']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    elif subcommand == "todo":
        if not todo_quests:
            await ctx.send("🎉 Congratulations! You've completed all quests!")
            return
        
        embed = discord.Embed(
            title="📝 Quests To Do",
            description=f"You have {len(todo_quests)} quest{'s' if len(todo_quests) > 1 else ''} remaining!",
            color=discord.Color.orange()
        )
        
        for quest in todo_quests:
            dialogue = quest["dialogue"].format(user=ctx.author.name)
            
            item_cost = None
            for item in chi_shop_data["items"]:
                if item["name"] == quest["item_needed"]:
                    item_cost = item["cost"]
                    break
            
            value_text = f"*Pax says: {dialogue}*\n**Item needed:** {quest['item_needed']}"
            if item_cost:
                value_text += f"\n**Cost:** {item_cost} chi"
            
            embed.add_field(
                name=f"❌ {quest['name']}",
                value=value_text,
                inline=False
            )
        
        embed.set_footer(text="Purchase items with P!buy <item_name>")
        await ctx.send(embed=embed)

@bot.command()
async def feed(ctx, *, item: str = ""):
    """Quest 3: Pax's Midnight Snack - Feed Pax between 9 PM - 3 AM UTC"""
    if not item:
        await ctx.send("❌ Usage: `P!feed <item>` - Try feeding Pax something! 🍪")
        return
    
    now = datetime.utcnow()
    current_hour = now.hour
    
    if not (21 <= current_hour or current_hour < 3):
        await ctx.send(f"🐼 Pax isn't hungry right now... come back between 9 PM - 3 AM UTC! (It's currently {current_hour}:00 UTC)")
        return
    
    accepted_items = ["cookie", "bamboo", "honey", "leaf", "fish", "rice"]
    item_lower = item.lower().strip()
    
    if item_lower not in accepted_items:
        await ctx.send(f"🐼 Pax sniffs the {item} and walks away... maybe try something else?\n*Hint: Pax likes {', '.join(accepted_items)}*")
        return
    
    pax_likes = {
        "cookie": (200, 300, "😋"),
        "bamboo": (250, 300, "🤤"),
        "honey": (150, 250, "😊"),
        "leaf": (100, 150, "🙂"),
        "fish": (150, 200, "😐"),
        "rice": (100, 150, "😋")
    }
    
    min_chi, max_chi, emoji = pax_likes[item_lower]
    chi_reward = random.randint(min_chi, max_chi)
    
    user_id = ctx.author.id
    rebirth_msg = update_chi(user_id, chi_reward)
    
    reactions = ["🍪", "🐼", emoji]
    for reaction in reactions:
        try:
            await ctx.message.add_reaction(reaction)
        except:
            pass
    
    embed = discord.Embed(
        title=f"{emoji} Pax ate the {item_lower}!",
        description=f"Pax loved it! You earned **+{chi_reward} chi**!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="🌙 Quest: Pax's Midnight Snack")
    
    await ctx.send(embed=embed)
    if rebirth_msg:
        await ctx.send(rebirth_msg)

@bot.command(name="whisper")
async def whisper_command(ctx):
    """Quest 2: Hidden command for Echoes of the Lost Grove"""
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if "echoes_grove" not in chi_data[user_id].get("mini_quests", []):
        chi_data[user_id].setdefault("mini_quests", []).append("echoes_grove")
        rebirth_msg = update_chi(user_id, 250)
        save_data()
        
        embed = discord.Embed(
            title="🕯️ The Grove Responds...",
            description="*You hear Pax's voice echoing through the bamboo...*\n\n\"You've found the secret... the grove remembers those who listen.\"\n\n✨ **Quest Complete: Echoes of the Lost Grove**\n+250 Chi earned!",
            color=discord.Color.dark_green()
        )
        embed.set_footer(text="You've unlocked the 'Whisper of the Grove' title!")
        await ctx.send(embed=embed)
        if rebirth_msg:
            await ctx.send(rebirth_msg)
    else:
        await ctx.send("🕯️ *The grove is silent... you've already discovered its secrets.*")

@bot.command(name="listen")
async def listen_command(ctx):
    """Alternative hidden command for Echoes of the Lost Grove"""
    await whisper_command(ctx)

@bot.command(name="translate")
async def translate_command(ctx, *args):
    """Translate text or a message to another language
    Usage: 
    - P!translate <text> <language> - Translate direct text
    - P!translate <message_id> <language> - Translate a message by ID
    
    Examples:
    - P!translate Hello world spanish
    - P!translate 123456789 french
    - P!translate How are you today? japanese
    """
    if len(args) < 2:
        embed = discord.Embed(
            title="🌐 Translation Command",
            description="Translate text or messages to any language!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📝 Translate Text",
            value="`P!translate <text> <language>`\n**Example:** `P!translate Hello world spanish`",
            inline=False
        )
        embed.add_field(
            name="💬 Translate Message",
            value="`P!translate <message_id> <language>`\n**Example:** `P!translate 123456789 french`",
            inline=False
        )
        embed.add_field(
            name="🗣️ Supported Languages",
            value="english, spanish, french, german, italian, japanese, korean, chinese (simplified/traditional), portuguese, russian, arabic, hindi, dutch, and 100+ more!\n\nUse language names or codes (e.g., 'es', 'ja', 'zh-cn')",
            inline=False
        )
        embed.set_footer(text="Tip: Right-click a message → Copy ID to get the message ID")
        await ctx.send(embed=embed)
        return
    
    try:
        # Parse arguments: last arg is language, everything else is text or message ID
        language = args[-1]
        content_args = args[:-1]
        
        # Determine if first arg is a message ID (numeric)
        is_message_id = False
        text_to_translate = None
        original_author = None
        
        if len(content_args) == 1 and content_args[0].isdigit():
            # Message ID format: P!translate <message_id> <language>
            is_message_id = True
            try:
                msg_id = int(content_args[0])
                message = await ctx.channel.fetch_message(msg_id)
                if not message.content:
                    await ctx.send("❌ This message has no text content to translate!")
                    return
                text_to_translate = message.content
                original_author = message.author.display_name
            except discord.NotFound:
                await ctx.send("❌ Message not found in this channel!")
                return
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to access that message!")
                return
        else:
            # Direct text format: P!translate <text...> <language>
            text_to_translate = " ".join(content_args)
            original_author = ctx.author.display_name
        
        # Initialize translator with retry logic
        translator = Translator()
        
        # Normalize language input
        lang_code = language.lower()
        
        # Check if language is a language name or code
        if lang_code not in LANGUAGES.values() and lang_code not in LANGUAGES.keys():
            # Try to find language by name (case-insensitive)
            found = False
            for code, name in LANGUAGES.items():
                if name.lower() == lang_code:
                    lang_code = code
                    found = True
                    break
            
            if not found:
                # Try partial match
                for code, name in LANGUAGES.items():
                    if lang_code in name.lower():
                        lang_code = code
                        found = True
                        break
            
            if not found:
                await ctx.send(f"❌ Language '{language}' not recognized!\n\nUse a language name (e.g., 'spanish', 'japanese') or code (e.g., 'es', 'ja')\n\nPopular languages: english, spanish, french, german, italian, japanese, korean, chinese, portuguese, russian")
                return
        
        # If it's a language name, get the code
        if lang_code in LANGUAGES.values():
            for code, name in LANGUAGES.items():
                if name == lang_code:
                    lang_code = code
                    break
        
        # Perform translation with retry for better accuracy
        max_retries = 2
        translation = None
        for attempt in range(max_retries):
            try:
                translation = translator.translate(text_to_translate, dest=lang_code)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(0.5)
        
        # Detect source language
        source_lang = LANGUAGES.get(translation.src, translation.src).title()
        target_lang = LANGUAGES.get(lang_code, lang_code).title()
        
        # Build plain text response (no embed)
        if is_message_id and original_author:
            # Show who's message it is
            response = f"🌐 **{source_lang} → {target_lang}**\n{translation.text}"
        else:
            # For direct text translation, just show the translation
            response = f"🌐 **{target_lang}:** {translation.text}"
        
        await ctx.send(response)
        
    except Exception as e:
        error_msg = str(e)
        if "HTTPSConnectionPool" in error_msg or "Connection" in error_msg:
            await ctx.send("❌ Translation service temporarily unavailable. Please try again in a moment!")
        elif "invalid destination language" in error_msg.lower():
            lang_mention = target_lang if 'target_lang' in locals() else "the specified language"
            await ctx.send(f"❌ '{lang_mention}' is not a valid language code!\n\nTry: english, spanish, french, german, italian, japanese, korean, chinese, portuguese, russian")
        else:
            await ctx.send(f"❌ Translation failed: {error_msg}\n\nTry again or use a different language!")

@bot.command()
async def weapons(ctx):
    """Show your weapons with simplified attack codes"""
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data or "purchased_items" not in chi_data[user_id]:
        await ctx.send("❌ You don't have any weapons yet! Buy some from `P!cshop`")
        return
    
    user_weapons = []
    for item in chi_shop_data.get("items", []):
        if "weapon" in item.get("tags", []) and item["name"] in chi_data[user_id]["purchased_items"]:
            user_weapons.append(item)
    
    if not user_weapons:
        await ctx.send("❌ You don't have any weapons yet! Buy some from `P!cshop`")
        return
    
    embed = discord.Embed(
        title=f"⚔️ {ctx.author.display_name}'s Weapons",
        description="Use attack codes for quick dueling!",
        color=discord.Color.red()
    )
    
    for weapon in user_weapons[:5]:
        weapon_id = weapon.get("weapon_id", "")
        attacks = weapon.get("custom_attacks", {})
        
        attack_list = []
        for attack_name, attack_data in list(attacks.items())[:5]:
            attack_id = attack_data.get("attack_id", "")
            dmg_range = f"{attack_data['min_damage']}-{attack_data['max_damage']}"
            simple_name = attack_name.split()[0]
            attack_list.append(f"**{attack_id}**: {simple_name} ({dmg_range} dmg)")
        
        if attack_list:
            embed.add_field(
                name=f"{weapon['emoji']} {weapon['name'][:30]}",
                value="\n".join(attack_list),
                inline=False
            )
    
    embed.set_footer(text="Usage: P!duel attack <code> - Example: P!duel attack VW1")
    await ctx.send(embed=embed)

@bot.command(name="dueltutorial", aliases=["dtut"])
async def duel_tutorial(ctx):
    """Complete beginner's guide to the dueling system (sent via DM)"""
    
    pages = []
    
    # Page 1: Getting Started
    page1 = discord.Embed(
        title="⚔️ DUEL TUTORIAL - Page 1/5",
        description="**Welcome to the Chi Bot Dueling System!**\n\nDuels are turn-based PvP battles where you can win chi, show off your weapons, and prove you're the best!",
        color=discord.Color.red()
    )
    page1.add_field(
        name="📍 Getting Started",
        value="• You need weapons from `P!cshop`\n• Higher HP gives better chances\n• Turn-based combat (one action per turn)\n• Works in any channel!",
        inline=False
    )
    page1.add_field(
        name="🏆 Rewards",
        value="• Winner gets 10% of loser's chi (max 500)\n• Win/loss tracked in stats\n• Show off your legendary weapons!",
        inline=False
    )
    page1.set_footer(text="Next: How to Start a Duel → Sent via DM to avoid chat spam!")
    pages.append(page1)
    
    # Page 2: Starting a Duel
    page2 = discord.Embed(
        title="⚔️ DUEL TUTORIAL - Page 2/5",
        description="**How to Challenge Someone**",
        color=discord.Color.orange()
    )
    page2.add_field(
        name="1️⃣ Challenge",
        value="`P!duel @username`\nChallenges a user to duel",
        inline=False
    )
    page2.add_field(
        name="2️⃣ Accept/Deny",
        value="Challenged player:\n• `P!duel accept` - Start the fight!\n• `P!duel deny` - No thanks",
        inline=False
    )
    page2.add_field(
        name="⚠️ Important Rules",
        value="• Can't duel teammates\n• Can't duel allied teams\n• Can't duel yourself (obviously!)\n• Only 1 duel at a time",
        inline=False
    )
    page2.set_footer(text="Next: Combat Basics")
    pages.append(page2)
    
    # Page 3: Combat
    page3 = discord.Embed(
        title="⚔️ DUEL TUTORIAL - Page 3/5",
        description="**Fighting in a Duel**",
        color=discord.Color.gold()
    )
    page3.add_field(
        name="⚔️ Attacking (EASIEST WAY)",
        value="**Use Attack Codes!**\n\n"
        "1. Type `P!weapons` to see your codes\n"
        "2. Use the code: `P!duel attack VW1`\n\n"
        "**Old Way (still works):**\n"
        "`P!duel attack Verdant Windblade Emerald Laceration`",
        inline=False
    )
    page3.add_field(
        name="💚 Healing",
        value="`P!duel heal <item>`\n\nExample: `P!duel heal Jasmine Tea`\nRestores HP during your turn",
        inline=False
    )
    page3.add_field(
        name="🐼 Pet Attacks",
        value="`P!pet attack`\nUse your pet's special move! (if you have a pet)",
        inline=False
    )
    page3.set_footer(text="Next: Advanced Tactics")
    pages.append(page3)
    
    # Page 4: Advanced
    page4 = discord.Embed(
        title="⚔️ DUEL TUTORIAL - Page 4/5",
        description="**Advanced Tactics**",
        color=discord.Color.purple()
    )
    page4.add_field(
        name="🧪 Potions (Use BEFORE Duel)",
        value="`P!potion drink <potion>`\n\n"
        "Effects:\n"
        "• Strength = More damage\n"
        "• Defense = Less damage taken\n"
        "• Poison = Enemy takes damage per turn\n"
        "• Regeneration = Heal each turn",
        inline=False
    )
    page4.add_field(
        name="💎 Artifacts",
        value="Artifacts give HP bonuses automatically!\n"
        "• Higher tiers = more HP\n"
        "• Equip by claiming them\n"
        "• See `P!inv` for your artifacts",
        inline=False
    )
    page4.add_field(
        name="❤️ HP Upgrades",
        value="Buy permanent HP from `P!rshop`!\n"
        "• Base HP: 1000\n"
        "• +100 HP per upgrade\n"
        "• Stacks with artifacts!",
        inline=False
    )
    page4.set_footer(text="Next: Spectating & Betting")
    pages.append(page4)
    
    # Page 5: Spectating
    page5 = discord.Embed(
        title="⚔️ DUEL TUTORIAL - Page 5/5",
        description="**Spectating & Betting**",
        color=discord.Color.blue()
    )
    page5.add_field(
        name="💰 How to Bet",
        value="`P!duel bet <amount> @duelist`\n\n"
        "Example: `P!duel bet 500 @Pax`\n\n"
        "• Win = 2x your bet (net +500)\n"
        "• Lose = Lose your bet",
        inline=False
    )
    page5.add_field(
        name="🏃 Forfeit",
        value="`P!duel run`\n\n"
        "Instantly lose the duel + 100 chi penalty\n"
        "Use when you know you can't win!",
        inline=False
    )
    page5.add_field(
        name="🎯 Quick Reference",
        value="• `P!weapons` - See attack codes\n"
        "• `P!inv` - Check your items\n"
        "• `P!cshop` - Buy weapons\n"
        "• `P!rshop` - Buy HP upgrades\n"
        "• `P!dueltutorial` - See this again",
        inline=False
    )
    page5.set_footer(text="✅ Tutorial Complete! Ready to duel!")
    pages.append(page5)
    
    # Send confirmation in channel
    await ctx.send(f"📚 {ctx.author.mention} Check your DMs for the complete duel tutorial!")
    
    # Send all pages via DM
    try:
        for i, page in enumerate(pages, 1):
            await ctx.author.send(embed=page)
            if i < len(pages):
                await asyncio.sleep(1.5)
    except discord.Forbidden:
        await ctx.send(f"❌ {ctx.author.mention} I can't DM you! Please enable DMs from server members.")

@bot.command()
async def duel(ctx, action_or_user: str = "", *, item_name: str = ""):
    """Duel system - challenge players to combat!
    Usage: 
    - P!duel @user - Challenge someone
    - P!duel accept/deny - Respond to challenge
    - P!duel attack <item> - Attack with weapon
    - P!duel heal <item> - Heal with item
    """
    global active_duel
    
    if not action_or_user:
        await ctx.send("❌ Usage:\n`P!duel @user` - Challenge someone\n`P!duel accept/deny` - Respond to challenge\n`P!duel attack <item>` - Attack with weapon\n`P!duel heal <item>` - Heal with item\n`P!duel run` - Flee from duel (lose 100 chi)\n`P!duel bet <amount> @user` - Bet on who will win!")
        return
    
    action_or_user = action_or_user.lower()
    
    # Check for betting FIRST before processing mentions (betting has mentions too)
    if action_or_user == "bet":
        if active_duel is None or active_duel["status"] != "active":
            await ctx.send("⚔️ There's no active duel to bet on right now!")
            return
        
        if ctx.author.id in [active_duel["challenger"], active_duel["challenged"]]:
            await ctx.send("💰 You can't bet on a duel you're in!")
            return
        
        if not ctx.message.mentions:
            await ctx.send("❌ Usage: `P!duel bet <amount> @user` - Bet on who will win!")
            return
        
        # Extract bet amount from item_name (which contains amount + @user)
        try:
            # item_name will be something like "500 @user" or just "500" with mention
            bet_amount_str = item_name.split()[0] if item_name else "0"
            bet_amount = int(bet_amount_str)
        except (ValueError, IndexError):
            await ctx.send("❌ Usage: `P!duel bet <amount> @user` - Amount must be a number!")
            return
        
        if bet_amount <= 0:
            await ctx.send("❌ Bet amount must be greater than 0!")
            return
        
        bet_on_user = ctx.message.mentions[0]
        
        if bet_on_user.id not in [active_duel["challenger"], active_duel["challenged"]]:
            await ctx.send("⚔️ You can only bet on one of the duelists!")
            return
        
        bettor_id = str(ctx.author.id)
        if bettor_id not in chi_data:
            chi_data[bettor_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        if chi_data[bettor_id]["chi"] < bet_amount:
            await ctx.send(f"❌ You don't have enough chi! You have {chi_data[bettor_id]['chi']} chi.")
            return
        
        for bet in active_duel["bets"]:
            if bet["bettor_id"] == ctx.author.id:
                await ctx.send("💰 You've already placed a bet on this duel!")
                return
        
        active_duel["bets"].append({
            "bettor_id": ctx.author.id,
            "bet_amount": bet_amount,
            "bet_on_user_id": bet_on_user.id
        })
        
        update_chi(bettor_id, -bet_amount)
        
        embed = discord.Embed(
            title="💰 BET PLACED!",
            description=f"{ctx.author.mention} bet **{bet_amount} chi** on {bet_on_user.mention}!\n\n✅ **Win:** Gain {bet_amount * 2} chi (net +{bet_amount} chi)\n❌ **Lose:** Lose {bet_amount} chi",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Total bets on this duel: {len(active_duel['bets'])}")
        await ctx.send(embed=embed)
        return
    
    # Now check for challenge mentions
    if ctx.message.mentions and action_or_user not in ["bet", "accept", "deny", "attack", "heal", "run"]:
        target = ctx.message.mentions[0]
        
        if target.bot:
            await ctx.send("🐼 Pax doesn't fight with bots... they're too predictable!")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🐼 You can't duel yourself! That's just... sad.")
            return
        
        # Check if both users are on the same team
        challenger_id = str(ctx.author.id)
        target_id = str(target.id)
        if challenger_id in teams_data["user_teams"] and target_id in teams_data["user_teams"]:
            challenger_team_id = teams_data["user_teams"][challenger_id]
            target_team_id = teams_data["user_teams"][target_id]
            
            # Can't duel own teammates
            if challenger_team_id == target_team_id:
                await ctx.send("⚔️ You can't duel your own teammate! Teams cannot battle themselves.")
                return
            
            # Can't duel allied teams
            challenger_team = teams_data["teams"][challenger_team_id]
            if target_team_id in challenger_team.get("allies", []):
                target_team_name = teams_data["teams"][target_team_id]["name"]
                await ctx.send(f"🤝 You cannot duel members of **{target_team_name}** - your teams are allies!\n"
                              f"💡 Allied teams can train together but not duel each other.")
                return
        
        if active_duel is not None:
            await ctx.send("⚔️ A duel is already in progress! Wait for it to finish.")
            return
        
        active_duel = {
            "challenger": ctx.author.id,
            "challenged": target.id,
            "status": "pending",
            "start_time": datetime.utcnow(),
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "is_tournament": False,
            "bets": []
        }
        
        embed = discord.Embed(
            title="⚔️ DUEL CHALLENGE!",
            description=f"{ctx.author.mention} has challenged {target.mention} to a duel!\n\n{target.mention}, type `P!duel accept` or `P!duel deny`!",
            color=discord.Color.red()
        )
        embed.set_footer(text="You have 2 minutes to respond!")
        await ctx.send(embed=embed)
        
        await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=2))
        if active_duel and active_duel["status"] == "pending":
            active_duel = None
            await ctx.send(f"⚔️ {target.mention} didn't respond in time. The challenge has expired.")
        return
    
    if action_or_user == "accept":
        if active_duel is None:
            await ctx.send("⚔️ There's no active duel challenge!")
            return
        
        if ctx.author.id != active_duel["challenged"]:
            await ctx.send("⚔️ This challenge isn't for you!")
            return
        
        if active_duel["status"] != "pending":
            await ctx.send("⚔️ This duel has already started!")
            return
        
        challenger_id = str(active_duel["challenger"])
        challenged_id = str(active_duel["challenged"])
        
        if challenger_id not in chi_data:
            chi_data[challenger_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        if challenged_id not in chi_data:
            chi_data[challenged_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        # Calculate HP based on artifacts and permanent upgrades
        challenger_hp = calculate_max_hp(active_duel["challenger"])
        challenged_hp = calculate_max_hp(active_duel["challenged"])
        
        active_duel["status"] = "active"
        active_duel["challenger_hp"] = challenger_hp
        active_duel["challenged_hp"] = challenged_hp
        active_duel["challenger_max_hp"] = challenger_hp
        active_duel["challenged_max_hp"] = challenged_hp
        
        # Auto-complete tutorial quest 3: Start a duel
        await auto_complete_tutorial_quest(active_duel["challenger"], 3, ctx.channel)
        await auto_complete_tutorial_quest(active_duel["challenged"], 3, ctx.channel)
        active_duel["turn"] = active_duel["challenger"]
        active_duel["start_time"] = datetime.utcnow()
        active_duel["item_uses"] = {}
        
        challenger = ctx.guild.get_member(active_duel["challenger"])
        challenged = ctx.guild.get_member(active_duel["challenged"])
        
        embed = discord.Embed(
            title="⚔️ DUEL BEGINS!",
            description=f"{challenger.mention} vs {challenged.mention}",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="❤️ Health Points",
            value=f"{challenger.mention}: **{challenger_hp}** HP\n{challenged.mention}: **{challenged_hp}** HP",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Quick Actions",
            value=(
                "**Attack:** `P!duel attack <code>` *(e.g., VW1)*\n"
                "**Heal:** `P!duel heal <item>`\n"
                "**Pet:** `P!pet attack`\n"
                "**Forfeit:** `P!duel run`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Pro Tips",
            value=(
                "• Use `P!weapons` to see all your attack codes\n"
                "• First time? Try `P!dueltutorial` for full guide!\n"
                "• Click buttons below for instant help"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"🎯 {challenger.display_name}'s turn! • Duel expires in 10 minutes")
        
        session_key = f"duel_{ctx.channel.id}"
        duel_view = DuelView(active_duel, session_key, session_manager)
        session_manager.create_session(session_key, active_duel)
        
        message = await ctx.send(embed=embed, view=duel_view)
        duel_view.message = message
        return
    
    if action_or_user == "deny":
        if active_duel is None:
            await ctx.send("⚔️ There's no active duel challenge!")
            return
        
        if ctx.author.id != active_duel["challenged"]:
            await ctx.send("⚔️ This challenge isn't for you!")
            return
        
        if active_duel["status"] != "pending":
            await ctx.send("⚔️ This duel has already started!")
            return
        
        challenger = ctx.guild.get_member(active_duel["challenger"])
        active_duel = None
        
        await ctx.send(f"🐼 *Aw sorry... {ctx.author.mention} doesn't want to battle you, {challenger.mention}. How about we try peace, if that doesn't work then we can always use fists!*")
        return
    
    if action_or_user == "attack":
        if active_duel is None or active_duel["status"] != "active":
            await ctx.send("⚔️ There's no active duel right now!")
            return
        
        if ctx.author.id != active_duel["turn"]:
            await ctx.send("⚔️ It's not your turn!")
            return
        
        if not item_name:
            await ctx.send("❌ Usage: `P!duel attack <weapon_id>` or `P!duel attack <weapon> <attack>`\nExample: `P!duel attack K1` or `P!duel attack Katana Swift Slash`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        # Try weapon ID first (K1, DW2, BS3, etc.)
        weapon_id_result = parse_weapon_id(item_name)
        
        if weapon_id_result:
            weapon_name, attack_name, damage_info = weapon_id_result
            
            # Check if user owns this weapon
            if weapon_name not in user_items:
                await ctx.send(f"❌ You don't own **{weapon_name}**! Buy it from `P!cshop`")
                return
            
            # Find the weapon item
            item_found = None
            for item in chi_shop_data["items"]:
                if item["name"] == weapon_name:
                    item_found = item
                    break
            
            if not item_found:
                await ctx.send(f"❌ Weapon not found!")
                return
            
            # Use the weapon ID attack as a custom attack
            custom_attack = attack_name
        else:
            # Parse weapon name and REQUIRED attack name
            # Find the weapon by trying to match from all available weapons (supports multi-word names)
            item_found = None
            custom_attack = None
            parts = item_name.split()
            
            # Get all weapons and sort by word count (longest first) to match longest weapon names first
            weapons = [item for item in chi_shop_data["items"] if "weapon" in item.get("tags", [])]
            weapons.sort(key=lambda x: len(x["name"].split()), reverse=True)
            
            # Try to match weapon names from longest to shortest
            for item in weapons:
                weapon_words = item["name"].split()
                weapon_word_count = len(weapon_words)
                
                # Check if input starts with this weapon name
                if len(parts) >= weapon_word_count:
                    input_weapon_part = " ".join(parts[:weapon_word_count])
                    if input_weapon_part.lower() == item["name"].lower():
                        item_found = item
                        # Everything after the weapon name is the custom attack
                        if len(parts) > weapon_word_count:
                            custom_attack = " ".join(parts[weapon_word_count:])
                        break
            
            if not item_found:
                await ctx.send(f"❌ '{item_name}' is not a valid weapon! Check your inventory with `P!inv`")
                return
            
            # Check ownership for regular weapon names
            if item_found["name"] not in user_items:
                await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
                return
            
            # REQUIRE an attack name when using weapon name
            if not custom_attack:
                await ctx.send(f"❌ You must specify an attack! Use `P!duel attack <weapon_id>` (e.g., K1) or `P!duel attack {item_found['name']} <attack_name>`")
                return
        
        base_damage = item_found.get("damage", 0)
        user_level = get_user_level(ctx.author.id)
        item_level = get_item_level(ctx.author.id, item_found["name"])
        damage = calculate_damage_with_level(base_damage, user_level, item_level)
        
        if "uses" in item_found:
            use_key = f"{user_id}_{item_found['name']}"
            current_uses = active_duel["item_uses"].get(use_key, 0)
            if current_uses >= item_found["uses"]:
                await ctx.send(f"❌ {item_found['name']} has no uses left! You need to buy it again.")
                return
            active_duel["item_uses"][use_key] = current_uses + 1
        
        if ctx.author.id == active_duel["challenger"]:
            opponent_id = active_duel["challenged"]
            active_duel["challenged_hp"] -= damage
            opponent_hp = active_duel["challenged_hp"]
            active_duel["turn"] = active_duel["challenged"]
        else:
            opponent_id = active_duel["challenger"]
            active_duel["challenger_hp"] -= damage
            opponent_hp = active_duel["challenger_hp"]
            active_duel["turn"] = active_duel["challenger"]
        
        opponent = ctx.guild.get_member(opponent_id)
        
        # Handle custom attacks
        if custom_attack:
            weapon_name = item_found['name']
            
            # Initialize custom_attacks if needed (for user-created attacks)
            if "custom_attacks" not in chi_data[user_id]:
                chi_data[user_id]["custom_attacks"] = {}
            if weapon_name not in chi_data[user_id]["custom_attacks"]:
                chi_data[user_id]["custom_attacks"][weapon_name] = []
            
            # Check if using same attack as last turn
            last_attack = active_duel.get("last_attack", {}).get(str(ctx.author.id))
            if last_attack and last_attack.lower() == custom_attack.lower():
                await ctx.send(f"❌ You can't use the same attack **{custom_attack}** twice in a row! Choose a different attack.")
                return
            
            # Store this attack as the last used
            if "last_attack" not in active_duel:
                active_duel["last_attack"] = {}
            active_duel["last_attack"][str(ctx.author.id)] = custom_attack
            
            # Check if this is a pre-configured attack from the weapon
            preconfigured_attacks = item_found.get("custom_attacks", {})
            attack_found = None
            
            # Check for pre-configured attack (case-insensitive)
            for attack_name, attack_info in preconfigured_attacks.items():
                if attack_name.lower() == custom_attack.lower():
                    attack_found = attack_info
                    custom_attack = attack_name  # Use proper casing
                    break
            
            if attack_found:
                # Use pre-configured attack damage (no level bonuses - damage matches exactly as shown)
                import random
                min_dmg = attack_found.get("min_damage", damage)
                max_dmg = attack_found.get("max_damage", damage)
                
                modified_damage = random.randint(min_dmg, max_dmg)
                
                # Update opponent HP
                if ctx.author.id == active_duel["challenger"]:
                    active_duel["challenged_hp"] += damage  # Undo base damage
                    active_duel["challenged_hp"] -= modified_damage
                    opponent_hp = active_duel["challenged_hp"]
                else:
                    active_duel["challenger_hp"] += damage  # Undo base damage
                    active_duel["challenger_hp"] -= modified_damage
                    opponent_hp = active_duel["challenger_hp"]
                
                await ctx.send(f"⚔️ {ctx.author.mention} used **{weapon_name}** to unleash *{custom_attack}* and dealt **{modified_damage} damage** to {opponent.mention}! 🏛️")
            else:
                # User-created custom attack - use hash-based variation
                # Add custom attack if not already in list
                if custom_attack not in chi_data[user_id]["custom_attacks"][weapon_name]:
                    chi_data[user_id]["custom_attacks"][weapon_name].append(custom_attack)
                    save_data()
                
                # Each custom attack does different damage (vary by +/-20%)
                attack_hash = sum(ord(c) for c in custom_attack.lower())
                damage_variation = (attack_hash % 41) - 20  # Range: -20 to +20
                modified_damage = max(1, damage + damage_variation)
                
                # Update opponent HP with modified damage
                if ctx.author.id == active_duel["challenger"]:
                    active_duel["challenged_hp"] += damage  # Undo original damage
                    active_duel["challenged_hp"] -= modified_damage
                    opponent_hp = active_duel["challenged_hp"]
                else:
                    active_duel["challenger_hp"] += damage  # Undo original damage
                    active_duel["challenger_hp"] -= modified_damage
                    opponent_hp = active_duel["challenger_hp"]
                
                await ctx.send(f"⚔️ {ctx.author.mention} used **{weapon_name}** to unleash *{custom_attack}* and dealt **{modified_damage} damage** to {opponent.mention}!")
        else:
            await ctx.send(f"⚔️ {ctx.author.mention} attacked with **{item_found['name']}** and dealt **{damage} damage** to {opponent.mention}!")
        
        if opponent_hp <= 0:
            winner = ctx.author
            loser = opponent
            is_tournament = active_duel.get("is_tournament", False)
            
            bet_results = process_duel_bets(winner.id, ctx.guild)
            active_duel = None
            
            winner_id = str(winner.id)
            loser_id = str(loser.id)
            
            if is_tournament:
                chi_reward = 150
                update_chi(winner_id, chi_reward)
                # Loser no longer loses chi - encourages participation
                win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for winning a tournament!"
            else:
                chi_reward = 75  # Moderate 50% increase from 50
                update_chi(winner_id, chi_reward)
                # Loser no longer loses chi - removes participation penalty
                win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for defeating your opponent in a duel!"
            
            # Unlock first duel win achievement
            await unlock_achievement(winner.id, "first_duel_win", ctx.guild)
            
            # Update team duel stats
            if winner_id in teams_data["user_teams"]:
                winner_team_id = teams_data["user_teams"][winner_id]
                teams_data["teams"][winner_team_id]["duel_stats"]["wins"] += 1
                # Increment team score by 1 for each win
                teams_data["teams"][winner_team_id]["team_score"] = teams_data["teams"][winner_team_id].get("team_score", 0) + 1
                save_teams()
            
            if loser_id in teams_data["user_teams"]:
                loser_team_id = teams_data["user_teams"][loser_id]
                teams_data["teams"][loser_team_id]["duel_stats"]["losses"] += 1
                save_teams()
            
            # Initialize ingredients if needed
            if "ingredients" not in chi_data[winner_id]:
                chi_data[winner_id]["ingredients"] = {}
            
            # Duel ingredient drops (winner only, 25% chance each)
            ingredient_drops = []
            if random.random() < 0.25:
                chi_data[winner_id]["ingredients"]["I4"] = chi_data[winner_id]["ingredients"].get("I4", 0) + 1
                ingredient_drops.append("💎 Blood Crystal")
            if random.random() < 0.15:
                chi_data[winner_id]["ingredients"]["I5"] = chi_data[winner_id]["ingredients"].get("I5", 0) + 1
                ingredient_drops.append("🌑 Shadow Essence")
            
            save_data()
            
            # Log duel victory
            duel_type = "Tournament" if is_tournament else "Regular Duel"
            await log_event(
                "Duel Victory",
                f"**Type:** {duel_type}\n**Winner:** {winner.mention} ({winner.name})\n**Loser:** {loser.mention} ({loser.name})\n**Chi Reward:** +{chi_reward} chi to winner", ctx.guild, discord.Color.red())
            
            description = f"**{win_message}**\n\n{loser.mention} has been defeated!\n\n**Rewards:**\n{winner.mention}: +{chi_reward} chi"
            
            if ingredient_drops:
                description += f"\n🧪 Ingredients: {', '.join(ingredient_drops)}"
            
            if bet_results:
                description += f"\n\n**💰 Betting Results:**\n" + "\n".join(bet_results)
            
            embed = discord.Embed(
                title="🏆 DUEL COMPLETE!",
                description=description,
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
        else:
            next_turn_user = ctx.guild.get_member(active_duel["turn"])
            
            challenger = ctx.guild.get_member(active_duel["challenger"])
            challenged = ctx.guild.get_member(active_duel["challenged"])
            
            embed = discord.Embed(
                title="⚔️ Duel Status",
                description=f"**HP:**\n{challenger.mention}: {active_duel['challenger_hp']}/{active_duel['challenger_max_hp']} HP\n{challenged.mention}: {active_duel['challenged_hp']}/{active_duel['challenged_max_hp']} HP\n\n{next_turn_user.mention}'s turn!",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        return
    
    if action_or_user == "heal":
        if active_duel is None or active_duel["status"] != "active":
            await ctx.send("⚔️ There's no active duel right now!")
            return
        
        if ctx.author.id != active_duel["turn"]:
            await ctx.send("⚔️ It's not your turn!")
            return
        
        if not item_name:
            await ctx.send("❌ Usage: `P!duel heal <item_name>`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        item_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == item_name.lower() and "healing" in item.get("tags", []):
                item_found = item
                break
        
        if not item_found:
            await ctx.send(f"❌ '{item_name}' is not a valid healing item! Check your inventory with `P!inv`")
            return
        
        if item_found["name"] not in user_items:
            await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
            return
        
        base_healing = item_found.get("healing", 0)
        user_level = get_user_level(ctx.author.id)
        item_level = get_item_level(ctx.author.id, item_found["name"])
        healing = calculate_healing_with_level(base_healing, user_level, item_level)
        
        if ctx.author.id == active_duel["challenger"]:
            old_hp = active_duel["challenger_hp"]
            active_duel["challenger_hp"] = min(active_duel["challenger_hp"] + healing, active_duel["challenger_max_hp"])
            actual_healing = active_duel["challenger_hp"] - old_hp
            active_duel["turn"] = active_duel["challenged"]
        else:
            old_hp = active_duel["challenged_hp"]
            active_duel["challenged_hp"] = min(active_duel["challenged_hp"] + healing, active_duel["challenged_max_hp"])
            actual_healing = active_duel["challenged_hp"] - old_hp
            active_duel["turn"] = active_duel["challenger"]
        
        await ctx.send(f"💚 {ctx.author.mention} used **{item_found['name']}** and healed for **{actual_healing} HP**!")
        
        next_turn_user = ctx.guild.get_member(active_duel["turn"])
        
        challenger = ctx.guild.get_member(active_duel["challenger"])
        challenged = ctx.guild.get_member(active_duel["challenged"])
        
        embed = discord.Embed(
            title="⚔️ Duel Status",
            description=f"**HP:**\n{challenger.mention}: {active_duel['challenger_hp']}/{active_duel['challenger_max_hp']} HP\n{challenged.mention}: {active_duel['challenged_hp']}/{active_duel['challenged_max_hp']} HP\n\n{next_turn_user.mention}'s turn!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    
    if action_or_user == "run":
        if active_duel is None or active_duel["status"] != "active":
            await ctx.send("⚔️ There's no active duel to run from!")
            return
        
        if ctx.author.id not in [active_duel["challenger"], active_duel["challenged"]]:
            await ctx.send("⚔️ You're not in this duel!")
            return
        
        runner = ctx.author
        if ctx.author.id == active_duel["challenger"]:
            winner_id = active_duel["challenged"]
        else:
            winner_id = active_duel["challenger"]
        
        winner = ctx.guild.get_member(winner_id)
        if not winner:
            await ctx.send("⚔️ Error: Could not find the other duelist!")
            active_duel = None
            return
        
        bet_results = process_duel_bets(winner_id, ctx.guild)
        active_duel = None
        
        runner_id = str(runner.id)
        winner_id_str = str(winner_id)
        
        update_chi(runner_id, -100)
        update_chi(winner_id_str, 100)
        
        # Update team duel stats
        if winner_id_str in teams_data["user_teams"]:
            winner_team_id = teams_data["user_teams"][winner_id_str]
            teams_data["teams"][winner_team_id]["duel_stats"]["wins"] += 1
            # Increment team score by 1 for each win
            teams_data["teams"][winner_team_id]["team_score"] = teams_data["teams"][winner_team_id].get("team_score", 0) + 1
            save_teams()
        
        if runner_id in teams_data["user_teams"]:
            runner_team_id = teams_data["user_teams"][runner_id]
            teams_data["teams"][runner_team_id]["duel_stats"]["losses"] += 1
            save_teams()
        
        # Log duel forfeit
        await log_event(
            "Duel Forfeit",
            f"**Winner (by forfeit):** {winner.mention} ({winner.name})\n**Runner:** {runner.mention} ({runner.name})\n**Chi Changes:** Winner +100 chi, Runner -100 chi", ctx.guild, discord.Color.orange())
        
        description = f"{runner.mention} ran away from the duel!\n\n{winner.mention} wins by default!\n\n**Chi Changes:**\n{runner.mention}: -100 chi (coward penalty)\n{winner.mention}: +100 chi (victory by forfeit)"
        
        if bet_results:
            description += f"\n\n**💰 Betting Results:**\n" + "\n".join(bet_results)
        
        embed = discord.Embed(
            title="🏃 COWARD!",
            description=description,
            color=discord.Color.dark_grey()
        )
        await ctx.send(embed=embed)
        return

@bot.command(aliases=["tourn"])
@is_bot_owner()
async def tournament(ctx, user1: discord.Member = None, user2: discord.Member = None):
    """Admin-only: Force two users to duel in a tournament"""
    if not ctx.guild or not ctx.author.guild_permissions.administrator:
        await ctx.send("⚔️ This command requires administrator permissions!")
        return
    
    if not user1 or not user2:
        await ctx.send("❌ Usage: `P!tournament @User1 @User2` or `P!tourn @User1 @User2`")
        return
    
    if user1.bot or user2.bot:
        await ctx.send("🐼 Pax doesn't allow bots in tournaments!")
        return
    
    if user1.id == user2.id:
        await ctx.send("🐼 A user can't fight themselves in a tournament!")
        return
    
    global active_duel
    
    if active_duel is not None:
        await ctx.send("⚔️ A duel is already in progress! Wait for it to finish.")
        return
    
    user1_id = str(user1.id)
    user2_id = str(user2.id)
    
    if user1_id not in chi_data:
        chi_data[user1_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if user2_id not in chi_data:
        chi_data[user2_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    user1_hp = 100 + (chi_data[user1_id].get("rebirths", 0) * 25)
    user2_hp = 100 + (chi_data[user2_id].get("rebirths", 0) * 25)
    
    active_duel = {
        "challenger": user1.id,
        "challenged": user2.id,
        "status": "active",
        "start_time": datetime.utcnow(),
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "is_tournament": True,
        "challenger_hp": user1_hp,
        "challenged_hp": user2_hp,
        "challenger_max_hp": user1_hp,
        "challenged_max_hp": user2_hp,
        "turn": user1.id,
        "item_uses": {},
        "bets": []
    }
    
    embed = discord.Embed(
        title="🏆 TOURNAMENT MATCH!",
        description=f"**{ctx.author.mention} has started a tournament!**\n\n{user1.mention} vs {user2.mention}\n\n**HP:**\n{user1.mention}: {user1_hp} HP\n{user2.mention}: {user2_hp} HP\n\n{user1.mention}'s turn!\n\n*Winner receives 150 chi!*",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Use P!duel attack <item> or P!duel heal <item> • Duel ends in 10 minutes")
    await ctx.send(embed=embed)

@bot.command()
async def boss(ctx, action: str = "", *, item_name: str = ""):
    """Fight epic bosses and earn legendary keys!
    Usage:
    - P!boss list - View all available bosses
    - P!boss fight <boss_name> - Challenge a boss
    - P!boss attack <item> - Attack the boss with a weapon
    - P!boss heal <item> - Heal yourself
    - P!boss run - Forfeit and flee (lose 100 chi)
    """
    global active_boss_battle
    
    if not action:
        await ctx.send("❌ Usage:\n`P!boss list` - View all bosses\n`P!boss fight <boss_name>` - Challenge a boss\n`P!boss attack <item>` - Attack with weapon\n`P!boss heal <item>` - Heal\n`P!boss run` - Flee (lose 100 chi)")
        return
    
    action = action.lower()
    
    if action == "list":
        embed = discord.Embed(
            title="🎯 LEGENDARY BOSSES",
            description="Challenge these epic bosses to earn legendary keys!\n\n*Keys will unlock access to the Pirate World (coming soon)*",
            color=discord.Color.gold()
        )
        
        for boss_key, boss_info in BOSS_DATA.items():
            special_desc = boss_info["special"]["description"]
            rewards = boss_info["rewards"]
            artifact_text = f" + {int(rewards['artifact_chance']*100)}% unique artifact" if rewards["artifact_chance"] > 0 else ""
            
            boss_text = (
                f"{boss_info['emoji']} **{boss_info['name']}**\n"
                f"❤️ HP: {boss_info['hp']}\n"
                f"⚔️ Damage: {boss_info['damage_min']}-{boss_info['damage_max']}\n"
                f"✨ Special: {boss_info['special']['name']} ({special_desc})\n"
                f"🎁 Reward: {rewards['key']} + {rewards['chi']} Chi{artifact_text}\n"
                f"*Use: `P!boss fight {boss_key}`*"
            )
            embed.add_field(name=f"{boss_info['name']}", value=boss_text, inline=False)
        
        await ctx.send(embed=embed)
        return
    
    if action == "fight":
        if active_boss_battle is not None:
            await ctx.send("⚔️ A boss battle is already in progress!")
            return
        
        if not item_name:
            await ctx.send("❌ Usage: `P!boss fight <boss_name>`\nExample: `P!boss fight fang`\nUse `P!boss list` to see all bosses!")
            return
        
        boss_key = item_name.lower().strip()
        if boss_key not in BOSS_DATA:
            await ctx.send(f"❌ Unknown boss! Use `P!boss list` to see all available bosses.\nValid names: {', '.join(BOSS_DATA.keys())}")
            return
        
        user_id = str(ctx.author.id)
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "boss_keys": []}
        
        boss_info = BOSS_DATA[boss_key]
        # Calculate HP based on artifacts and permanent upgrades
        player_hp = calculate_max_hp(ctx.author.id)
        
        active_boss_battle = {
            "player_id": ctx.author.id,
            "boss_key": boss_key,
            "boss_hp": boss_info["hp"],
            "boss_max_hp": boss_info["hp"],
            "player_hp": player_hp,
            "player_max_hp": player_hp,
            "turn": 1,
            "burn_turns": 0,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "start_time": datetime.utcnow(),
            "item_uses": {}
        }
        
        embed = discord.Embed(
            title=f"{boss_info['emoji']} BOSS BATTLE STARTED!",
            description=(
                f"{ctx.author.mention} challenges **{boss_info['name']}**!\n\n"
                f"**Boss HP:** {boss_info['hp']}\n"
                f"**Your HP:** {player_hp}\n\n"
                f"⚠️ {boss_info['special']['name']}: {boss_info['special']['description']}\n\n"
                f"*Use `P!boss attack <weapon>` to strike!*"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Reward: {boss_info['rewards']['key']} + {boss_info['rewards']['chi']} Chi")
        await ctx.send(embed=embed)
        return
    
    if action == "attack":
        if active_boss_battle is None:
            await ctx.send("⚔️ There's no active boss battle! Use `P!boss fight <boss_name>` to start one.")
            return
        
        if ctx.author.id != active_boss_battle["player_id"]:
            await ctx.send("⚔️ This is not your boss battle!")
            return
        
        if not item_name:
            await ctx.send("❌ Usage: `P!boss attack <weapon>` or `P!boss attack <weapon_id>`\nExample: `P!boss attack Katana` or `P!boss attack K1`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        # Try weapon ID first (K1, DW2, BS3, etc.)
        weapon_id_result = parse_weapon_id(item_name)
        
        if weapon_id_result:
            weapon_name, attack_name, damage_info = weapon_id_result
            
            # Check if user owns this weapon
            if weapon_name not in user_items:
                await ctx.send(f"❌ You don't own **{weapon_name}**! Buy it from `P!cshop`")
                return
            
            # Find the weapon item
            item_found = None
            for item in chi_shop_data["items"]:
                if item["name"] == weapon_name:
                    item_found = item
                    break
            
            if not item_found:
                await ctx.send(f"❌ Weapon not found!")
                return
        else:
            # Standard weapon name lookup
            item_found = None
            for item in chi_shop_data["items"]:
                if item["name"].lower() == item_name.lower() and "weapon" in item.get("tags", []):
                    item_found = item
                    break
            
            if not item_found:
                await ctx.send(f"❌ **{item_name}** is not a valid weapon! Use `P!cshop` to see available weapons.")
                return
            
            # Check ownership for regular weapon names
            if item_found["name"] not in user_items:
                await ctx.send(f"❌ You don't own **{item_found['name']}**! Purchase it from the Chi Shop first.")
                return
        
        boss_info = BOSS_DATA[active_boss_battle["boss_key"]]
        
        weapon_damage = item_found.get("damage", 10)
        min_dmg = int(weapon_damage * 0.8)
        max_dmg = int(weapon_damage * 1.2)
        base_damage = random.randint(min_dmg, max_dmg)
        user_level = get_user_level(user_id)
        item_level = get_item_level(user_id, item_found["name"])
        damage = calculate_damage_with_level(base_damage, user_level, item_level)
        
        active_boss_battle["boss_hp"] -= damage
        
        attack_message = f"⚔️ {ctx.author.mention} attacks with **{item_found['name']}** for **{damage} damage**!"
        
        if active_boss_battle["boss_hp"] <= 0:
            active_boss_battle["boss_hp"] = 0
            
            rewards = boss_info["rewards"]
            chi_data[user_id]["chi"] += rewards["chi"]
            chi_data[user_id]["boss_keys"].append(rewards["key"])
            
            artifact_won = None
            if rewards["artifact_chance"] > 0 and random.random() < rewards["artifact_chance"]:
                artifact_tiers = ["rare", "legendary", "eternal"]
                artifact_weights = [60, 35, 5]
                tier = random.choices(artifact_tiers, weights=artifact_weights, k=1)[0]
                artifact_config = ARTIFACT_CONFIG[tier]
                selected_emoji = random.choice(artifact_config["emojis"])
                selected_name = random.choice(artifact_config["names"])
                artifact_id = f"{tier}_{int(time.time())}"
                
                chi_data[user_id]["artifacts"].append({
                    "id": artifact_id,
                    "tier": tier,
                    "emoji": selected_emoji,
                    "name": selected_name,
                    "claimed_at": datetime.utcnow().isoformat()
                })
                artifact_won = f"{selected_emoji} **{selected_name}** ({tier.title()})"
            
            # Initialize inventory if needed
            if "inventory" not in chi_data[user_id]:
                chi_data[user_id]["inventory"] = {}
            
            # Winter Wonderland - Boss-specific ingredient drops!
            ingredient_drops = []
            boss_key = active_boss_battle["boss_key"]
            
            # GUARANTEED boss essence drop (1-2 pieces)
            essence_amount = random.randint(1, 2)
            if boss_key == "fang":
                chi_data[user_id]["inventory"]["bamboo_essence"] = chi_data[user_id]["inventory"].get("bamboo_essence", 0) + essence_amount
                ingredient_drops.append(f"🎋 Bamboo Essence x{essence_amount}")
            elif boss_key == "ironhide":
                chi_data[user_id]["inventory"]["titan_core"] = chi_data[user_id]["inventory"].get("titan_core", 0) + essence_amount
                ingredient_drops.append(f"⚙️ Titan Core x{essence_amount}")
            elif boss_key == "emberclaw":
                chi_data[user_id]["inventory"]["eternal_flame"] = chi_data[user_id]["inventory"].get("eternal_flame", 0) + essence_amount
                ingredient_drops.append(f"🔥 Eternal Flame x{essence_amount}")
            
            # Bonus rare ingredients (50% chance for 1-3 items)
            if random.random() < 0.50:
                bonus_count = random.randint(1, 3)
                chi_data[user_id]["inventory"]["phoenix_coal"] = chi_data[user_id]["inventory"].get("phoenix_coal", 0) + bonus_count
                ingredient_drops.append(f"🔥 Phoenix Coal x{bonus_count}")
            
            # Common ingredients (70% chance for 2-5 items)
            if random.random() < 0.70:
                common_count = random.randint(2, 5)
                common_ing = random.choice(["iron_ore", "crystal_shard", "shadow_stone"])
                chi_data[user_id]["inventory"][common_ing] = chi_data[user_id]["inventory"].get(common_ing, 0) + common_count
                ing_data = INGREDIENT_CATALOG.get(common_ing, {})
                ingredient_drops.append(f"{ing_data.get('emoji', '💎')} {common_ing.replace('_', ' ').title()} x{common_count}")
            
            save_data()
            
            await log_event(
                "Boss Victory",
                f"**Champion:** {ctx.author.mention} ({ctx.author.name})\n**Boss:** {boss_info['name']}\n**Rewards:** {rewards['key']} + {rewards['chi']} chi{' + ' + artifact_won if artifact_won else ''}", ctx.guild, discord.Color.gold())
            
            description = (
                f"💥 {attack_message}\n\n"
                f"🎉 **VICTORY!** {ctx.author.mention} has defeated **{boss_info['name']}**!\n\n"
                f"**Rewards:**\n"
                f"🔑 {rewards['key']}\n"
                f"💰 +{rewards['chi']} Chi\n"
            )
            if artifact_won:
                description += f"✨ BONUS: {artifact_won}!\n"
            if ingredient_drops:
                description += f"🧪 Ingredients: {', '.join(ingredient_drops)}\n"
            
            description += f"\n*Use `P!inventory` to view your keys!*"
            
            embed = discord.Embed(
                title=f"{boss_info['emoji']} BOSS DEFEATED!",
                description=description,
                color=discord.Color.gold()
            )
            
            active_boss_battle = None
            await ctx.send(embed=embed)
            return
        
        boss_damage = random.randint(boss_info["damage_min"], boss_info["damage_max"])
        
        special_activated = False
        if boss_info["special"].get("chance"):
            if random.random() < boss_info["special"]["chance"]:
                boss_damage = boss_info["damage_max"]
                attack_message += f"\n💥 **{boss_info['special']['name']}!** (Maximum damage dealt!)"
                special_activated = True
        
        if boss_info["special"].get("trigger_turn") and active_boss_battle["turn"] % boss_info["special"]["trigger_turn"] == 0:
            heal_amount = int(boss_info["hp"] * boss_info["special"]["heal_percent"])
            active_boss_battle["boss_hp"] = min(active_boss_battle["boss_hp"] + heal_amount, boss_info["hp"])
            attack_message += f"\n🛡️ **{boss_info['special']['name']}!** Boss healed {heal_amount} HP!"
        
        if "burn_damage" in boss_info["special"] and active_boss_battle["burn_turns"] == 0 and active_boss_battle["turn"] == 1:
            active_boss_battle["burn_turns"] = boss_info["special"]["burn_turns"]
            attack_message += f"\n🔥 **{boss_info['special']['name']}!** You are burning for {boss_info['special']['burn_turns']} turns!"
        
        attack_message += f"\n⚔️ **{boss_info['name']}** strikes back for **{boss_damage} damage**!"
        active_boss_battle["player_hp"] -= boss_damage
        
        if active_boss_battle["burn_turns"] > 0:
            burn_damage = boss_info["special"]["burn_damage"]
            active_boss_battle["player_hp"] -= burn_damage
            active_boss_battle["burn_turns"] -= 1
            attack_message += f"\n🔥 Burn damage: {burn_damage} HP (Burn: {active_boss_battle['burn_turns']} turns remaining)"
        
        if active_boss_battle["player_hp"] <= 0:
            active_boss_battle["player_hp"] = 0
            
            update_chi(user_id, -100)
            save_data()
            
            embed = discord.Embed(
                title=f"💀 DEFEATED!",
                description=(
                    f"{attack_message}\n\n"
                    f"☠️ {ctx.author.mention} has been defeated by **{boss_info['name']}**!\n\n"
                    f"**Penalty:** -100 Chi\n\n"
                    f"*Train harder and try again!*"
                ),
                color=discord.Color.dark_red()
            )
            
            active_boss_battle = None
            await ctx.send(embed=embed)
            return
        
        active_boss_battle["turn"] += 1
        
        embed = discord.Embed(
            title=f"{boss_info['emoji']} BOSS BATTLE",
            description=(
                f"{attack_message}\n\n"
                f"**Boss HP:** {active_boss_battle['boss_hp']}/{boss_info['hp']}\n"
                f"**Your HP:** {active_boss_battle['player_hp']}/{active_boss_battle['player_max_hp']}\n\n"
                f"*Your turn! Use `P!boss attack <weapon>` or `P!boss heal <item>`*"
            ),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    if action == "heal":
        if active_boss_battle is None:
            await ctx.send("⚔️ There's no active boss battle!")
            return
        
        if ctx.author.id != active_boss_battle["player_id"]:
            await ctx.send("⚔️ This is not your boss battle!")
            return
        
        if not item_name:
            await ctx.send("❌ Usage: `P!boss heal <item>`\nExample: `P!boss heal Peace Orb`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        item_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == item_name.lower() and "healing" in item.get("tags", []):
                item_found = item
                break
        
        if not item_found:
            user_artifacts = chi_data.get(user_id, {}).get("artifacts", [])
            for artifact in user_artifacts:
                if artifact["name"].lower() == item_name.lower():
                    tier = artifact["tier"]
                    heal_percent = ARTIFACT_CONFIG[tier]["heal_percent"]
                    base_healing = int(active_boss_battle["player_max_hp"] * (heal_percent / 100))
                    
                    old_hp = active_boss_battle["player_hp"]
                    active_boss_battle["player_hp"] = min(active_boss_battle["player_hp"] + base_healing, active_boss_battle["player_max_hp"])
                    actual_healing = active_boss_battle["player_hp"] - old_hp
                    
                    chi_data[user_id]["artifacts"].remove(artifact)
                    save_data()
                    
                    boss_info = BOSS_DATA[active_boss_battle["boss_key"]]
                    boss_damage = random.randint(boss_info["damage_min"], boss_info["damage_max"])
                    
                    heal_message = f"💚 {ctx.author.mention} used **{artifact['emoji']} {artifact['name']}** and healed for **{actual_healing} HP**!"
                    
                    if boss_info["special"].get("chance"):
                        if random.random() < boss_info["special"]["chance"]:
                            boss_damage = boss_info["damage_max"]
                            heal_message += f"\n💥 **{boss_info['special']['name']}!** (Maximum damage dealt!)"
                    
                    if boss_info["special"].get("trigger_turn") and active_boss_battle["turn"] % boss_info["special"]["trigger_turn"] == 0:
                        heal_amount = int(boss_info["hp"] * boss_info["special"]["heal_percent"])
                        active_boss_battle["boss_hp"] = min(active_boss_battle["boss_hp"] + heal_amount, boss_info["hp"])
                        heal_message += f"\n🛡️ **{boss_info['special']['name']}!** Boss healed {heal_amount} HP!"
                    
                    if "burn_damage" in boss_info["special"] and active_boss_battle["burn_turns"] == 0 and active_boss_battle["turn"] == 1:
                        active_boss_battle["burn_turns"] = boss_info["special"]["burn_turns"]
                        heal_message += f"\n🔥 **{boss_info['special']['name']}!** You are burning for {boss_info['special']['burn_turns']} turns!"
                    
                    heal_message += f"\n⚔️ **{boss_info['name']}** strikes for **{boss_damage} damage**!"
                    active_boss_battle["player_hp"] -= boss_damage
                    
                    if active_boss_battle["burn_turns"] > 0:
                        burn_damage = boss_info["special"]["burn_damage"]
                        active_boss_battle["player_hp"] -= burn_damage
                        active_boss_battle["burn_turns"] -= 1
                        heal_message += f"\n🔥 Burn damage: {burn_damage} HP (Burn: {active_boss_battle['burn_turns']} turns remaining)"
                    
                    if active_boss_battle["player_hp"] <= 0:
                        active_boss_battle["player_hp"] = 0
                        update_chi(user_id, -100)
                        save_data()
                        
                        embed = discord.Embed(
                            title=f"💀 DEFEATED!",
                            description=(
                                f"{heal_message}\n\n"
                                f"☠️ {ctx.author.mention} has been defeated by **{boss_info['name']}**!\n\n"
                                f"**Penalty:** -100 Chi"
                            ),
                            color=discord.Color.dark_red()
                        )
                        
                        active_boss_battle = None
                        await ctx.send(embed=embed)
                        return
                    
                    active_boss_battle["turn"] += 1
                    
                    embed = discord.Embed(
                        title=f"{boss_info['emoji']} BOSS BATTLE",
                        description=(
                            f"{heal_message}\n\n"
                            f"**Boss HP:** {active_boss_battle['boss_hp']}/{boss_info['hp']}\n"
                            f"**Your HP:** {active_boss_battle['player_hp']}/{active_boss_battle['player_max_hp']}"
                        ),
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    return
            
            await ctx.send(f"❌ **{item_name}** is not a valid healing item! Use healing items from Chi Shop or artifacts.")
            return
        
        if item_found["name"] not in user_items:
            await ctx.send(f"❌ You don't own **{item_found['name']}**!")
            return
        
        base_healing = item_found["healing"]
        user_level = get_user_level(user_id)
        item_level = get_item_level(user_id, item_found["name"])
        healing = calculate_healing_with_level(base_healing, user_level, item_level)
        
        old_hp = active_boss_battle["player_hp"]
        active_boss_battle["player_hp"] = min(active_boss_battle["player_hp"] + healing, active_boss_battle["player_max_hp"])
        actual_healing = active_boss_battle["player_hp"] - old_hp
        
        boss_info = BOSS_DATA[active_boss_battle["boss_key"]]
        boss_damage = random.randint(boss_info["damage_min"], boss_info["damage_max"])
        
        heal_message = f"💚 {ctx.author.mention} used **{item_found['name']}** and healed for **{actual_healing} HP**!"
        
        if boss_info["special"].get("chance"):
            if random.random() < boss_info["special"]["chance"]:
                boss_damage = boss_info["damage_max"]
                heal_message += f"\n💥 **{boss_info['special']['name']}!** (Maximum damage dealt!)"
        
        if boss_info["special"].get("trigger_turn") and active_boss_battle["turn"] % boss_info["special"]["trigger_turn"] == 0:
            heal_amount = int(boss_info["hp"] * boss_info["special"]["heal_percent"])
            active_boss_battle["boss_hp"] = min(active_boss_battle["boss_hp"] + heal_amount, boss_info["hp"])
            heal_message += f"\n🛡️ **{boss_info['special']['name']}!** Boss healed {heal_amount} HP!"
        
        if "burn_damage" in boss_info["special"] and active_boss_battle["burn_turns"] == 0 and active_boss_battle["turn"] == 1:
            active_boss_battle["burn_turns"] = boss_info["special"]["burn_turns"]
            heal_message += f"\n🔥 **{boss_info['special']['name']}!** You are burning for {boss_info['special']['burn_turns']} turns!"
        
        heal_message += f"\n⚔️ **{boss_info['name']}** strikes for **{boss_damage} damage**!"
        active_boss_battle["player_hp"] -= boss_damage
        
        if active_boss_battle["burn_turns"] > 0:
            burn_damage = boss_info["special"]["burn_damage"]
            active_boss_battle["player_hp"] -= burn_damage
            active_boss_battle["burn_turns"] -= 1
            heal_message += f"\n🔥 Burn damage: {burn_damage} HP (Burn: {active_boss_battle['burn_turns']} turns remaining)"
        
        if active_boss_battle["player_hp"] <= 0:
            active_boss_battle["player_hp"] = 0
            update_chi(user_id, -100)
            save_data()
            
            embed = discord.Embed(
                title=f"💀 DEFEATED!",
                description=(
                    f"{heal_message}\n\n"
                    f"☠️ {ctx.author.mention} has been defeated by **{boss_info['name']}**!\n\n"
                    f"**Penalty:** -100 Chi"
                ),
                color=discord.Color.dark_red()
            )
            
            active_boss_battle = None
            await ctx.send(embed=embed)
            return
        
        active_boss_battle["turn"] += 1
        
        embed = discord.Embed(
            title=f"{boss_info['emoji']} BOSS BATTLE",
            description=(
                f"{heal_message}\n\n"
                f"**Boss HP:** {active_boss_battle['boss_hp']}/{boss_info['hp']}\n"
                f"**Your HP:** {active_boss_battle['player_hp']}/{active_boss_battle['player_max_hp']}"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    
    if action == "run":
        if active_boss_battle is None:
            await ctx.send("⚔️ There's no active boss battle to flee from!")
            return
        
        if ctx.author.id != active_boss_battle["player_id"]:
            await ctx.send("⚔️ This is not your boss battle!")
            return
        
        user_id = str(ctx.author.id)
        boss_info = BOSS_DATA[active_boss_battle["boss_key"]]
        
        update_chi(user_id, -100)
        save_data()
        
        embed = discord.Embed(
            title="🏃 RETREAT!",
            description=(
                f"{ctx.author.mention} fled from **{boss_info['name']}**!\n\n"
                f"**Penalty:** -100 Chi\n\n"
                f"*Train harder and return when you're ready!*"
            ),
            color=discord.Color.dark_grey()
        )
        
        active_boss_battle = None
        await ctx.send(embed=embed)
        return

@bot.command()
async def train(ctx, action_or_user: str = "", mode_or_item: str = "", *, item_name: str = ""):
    """Training system - practice combat with teammates or NPCs!
    Usage: 
    - P!train @user [mode] - Challenge a teammate
    - P!train <dummy/easy/medium/hard> - Train with NPC
    - P!train accept/deny - Respond to challenge
    - P!train attack <item> - Attack with weapon
    - P!train heal <item> - Heal with item
    """
    global active_training, active_npc_training
    
    if not action_or_user:
        await ctx.send("❌ **Training Usage:**\n`P!train @user [mode]` - Challenge a teammate\n`P!train <dummy/easy/medium/hard>` - Train with NPC\n`P!train accept/deny` - Respond to challenge\n`P!train attack <item>` - Attack with weapon\n`P!train heal <item>` - Heal with item\n`P!train run` - Flee from training\n`P!train bet <amount> @user` - Bet on who will win!")
        return
    
    action_or_user = action_or_user.lower()
    
    # Check if training against NPC
    if action_or_user in ["dummy", "easy", "medium", "hard"]:
        if active_npc_training is not None:
            await ctx.send("🎯 An NPC training session is already in progress! Finish it first.")
            return
        
        if active_training is not None:
            await ctx.send("🥊 A player training session is already in progress! Wait for it to finish.")
            return
        
        npc_key = action_or_user
        npc_info = NPC_DATA[npc_key]
        user_id = str(ctx.author.id)
        
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        # Calculate HP based on artifacts and permanent upgrades
        player_hp = calculate_max_hp(ctx.author.id)
        
        active_npc_training = {
            "player_id": ctx.author.id,
            "npc_key": npc_key,
            "npc_hp": npc_info["hp"],
            "npc_max_hp": npc_info["hp"],
            "player_hp": player_hp,
            "player_max_hp": player_hp,
            "turn": "player",  # Always player's turn first
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "start_time": datetime.utcnow(),
            "item_uses": {}
        }
        
        embed = discord.Embed(
            title=f"{npc_info['emoji']} NPC TRAINING BEGINS!",
            description=f"{ctx.author.mention} vs **{npc_info['name']}**\n\n*{npc_info['description']}*\n\n**HP:**\n{ctx.author.mention}: {player_hp} HP\n{npc_info['emoji']} {npc_info['name']}: {npc_info['hp']} HP\n\n{ctx.author.mention}'s turn!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use P!train attack <item> or P!train heal <item>")
        await ctx.send(embed=embed)
        return
    
    if ctx.message.mentions:
        target = ctx.message.mentions[0]
        
        if target.bot:
            await ctx.send("🐼 Pax doesn't train with bots... they're too predictable!")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🐼 You can't train with yourself! That's just... sad.")
            return
        
        # Check team relationships for training
        challenger_id = str(ctx.author.id)
        target_id = str(target.id)
        
        # Both users must be in teams to train
        if challenger_id not in teams_data["user_teams"] or target_id not in teams_data["user_teams"]:
            await ctx.send("🥊 You can only train with teammates or allies! Both of you must be in a team.")
            return
        
        challenger_team_id = teams_data["user_teams"][challenger_id]
        target_team_id = teams_data["user_teams"][target_id]
        challenger_team = teams_data["teams"][challenger_team_id]
        target_team = teams_data["teams"][target_team_id]
        
        # Same team: can train
        # Allied teams: can train
        # Enemy teams: cannot train
        # Neutral teams: cannot train
        
        if challenger_team_id == target_team_id:
            # Same team - can train
            pass
        elif target_team_id in challenger_team.get("allies", []):
            # Allied teams - can train
            pass
        elif target_team_id in challenger_team.get("enemies", []):
            # Enemy teams - cannot train
            await ctx.send(f"⚔️ You cannot train with members of **{target_team['name']}** - your teams are enemies!\n"
                          f"💡 Enemy teams can duel each other but not train together.")
            return
        else:
            # Neutral teams - cannot train
            await ctx.send(f"🥊 You can only train with teammates or allied teams!\n"
                          f"**{challenger_team['name']}** and **{target_team['name']}** are not allies.\n"
                          f"💡 Use `P!team ally add @team_leader` to form an alliance!")
            return
        
        if active_training is not None:
            await ctx.send("🥊 A training session is already in progress! Wait for it to finish.")
            return
        
        active_training = {
            "challenger": ctx.author.id,
            "challenged": target.id,
            "status": "pending",
            "start_time": datetime.utcnow(),
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "is_tournament": False,
            "bets": []
        }
        
        embed = discord.Embed(
            title="🥊 TRAINING CHALLENGE!",
            description=f"{ctx.author.mention} has challenged {target.mention} to a training session!\n\n{target.mention}, type `P!train accept` or `P!train deny`!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="You have 2 minutes to respond!")
        await ctx.send(embed=embed)
        
        await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=2))
        if active_training and active_training["status"] == "pending":
            active_training = None
            await ctx.send(f"🥊 {target.mention} didn't respond in time. The challenge has expired.")
        return
    
    if action_or_user == "accept":
        if active_training is None:
            await ctx.send("🥊 There's no active training challenge!")
            return
        
        if ctx.author.id != active_training["challenged"]:
            await ctx.send("🥊 This challenge isn't for you!")
            return
        
        if active_training["status"] != "pending":
            await ctx.send("🥊 This training has already started!")
            return
        
        challenger_id = str(active_training["challenger"])
        challenged_id = str(active_training["challenged"])
        
        if challenger_id not in chi_data:
            chi_data[challenger_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        if challenged_id not in chi_data:
            chi_data[challenged_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        challenger_hp = 100 + (chi_data[challenger_id].get("rebirths", 0) * 25)
        challenged_hp = 100 + (chi_data[challenged_id].get("rebirths", 0) * 25)
        
        active_training["status"] = "active"
        active_training["challenger_hp"] = challenger_hp
        active_training["challenged_hp"] = challenged_hp
        active_training["challenger_max_hp"] = challenger_hp
        active_training["challenged_max_hp"] = challenged_hp
        active_training["turn"] = active_training["challenger"]
        active_training["start_time"] = datetime.utcnow()
        active_training["item_uses"] = {}
        
        challenger = ctx.guild.get_member(active_training["challenger"])
        challenged = ctx.guild.get_member(active_training["challenged"])
        
        embed = discord.Embed(
            title="🥊 TRAINING BEGINS!",
            description=f"{challenger.mention} vs {challenged.mention}\n\n**HP:**\n{challenger.mention}: {challenger_hp} HP\n{challenged.mention}: {challenged_hp} HP\n\n{challenger.mention}'s turn!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use P!train attack <item> or P!train heal <item> • Training ends in 10 minutes")
        await ctx.send(embed=embed)
        return
    
    if action_or_user == "deny":
        if active_training is None:
            await ctx.send("🥊 There's no active training challenge!")
            return
        
        if ctx.author.id != active_training["challenged"]:
            await ctx.send("🥊 This challenge isn't for you!")
            return
        
        if active_training["status"] != "pending":
            await ctx.send("🥊 This training has already started!")
            return
        
        challenger = ctx.guild.get_member(active_training["challenger"])
        active_training = None
        
        await ctx.send(f"🐼 *Aw sorry... {ctx.author.mention} doesn't want to train with you, {challenger.mention}. Maybe another time!*")
        return
    
    if action_or_user == "attack":
        # Check for NPC training first
        if active_npc_training is not None:
            if ctx.author.id != active_npc_training["player_id"]:
                await ctx.send("🎯 This is not your NPC training session!")
                return
            
            # For mode_or_item parameter handling
            actual_item_name = f"{mode_or_item} {item_name}".strip() if mode_or_item else ""
            if not actual_item_name:
                await ctx.send("❌ Usage: `P!train attack <weapon_id>` or `P!train attack <weapon> <attack>`\nExample: `P!train attack K1` or `P!train attack Katana Swift Slash`")
                return
            
            user_id = str(ctx.author.id)
            user_items = chi_data.get(user_id, {}).get("purchased_items", [])
            
            # Try weapon ID first (K1, DW2, BS3, etc.)
            weapon_id_result = parse_weapon_id(actual_item_name)
            
            if weapon_id_result:
                weapon_name, attack_name, damage_info = weapon_id_result
                
                # Check if user owns this weapon
                if weapon_name not in user_items:
                    await ctx.send(f"❌ You don't own **{weapon_name}**! Buy it from `P!cshop`")
                    return
                
                # Find the weapon item
                item_found = None
                for item in chi_shop_data["items"]:
                    if item["name"] == weapon_name:
                        item_found = item
                        break
                
                if not item_found:
                    await ctx.send(f"❌ Weapon not found!")
                    return
                
                custom_attack = attack_name
            else:
                # Parse weapon name and REQUIRED attack name
                # Find the weapon by trying to match from all available weapons (supports multi-word names)
                item_found = None
                custom_attack = None
                parts = actual_item_name.split()
                
                # Get all weapons and sort by word count (longest first) to match longest weapon names first
                weapons = [item for item in chi_shop_data["items"] if "weapon" in item.get("tags", [])]
                weapons.sort(key=lambda x: len(x["name"].split()), reverse=True)
                
                # Try to match weapon names from longest to shortest
                for item in weapons:
                    weapon_words = item["name"].split()
                    weapon_word_count = len(weapon_words)
                    
                    # Check if input starts with this weapon name
                    if len(parts) >= weapon_word_count:
                        input_weapon_part = " ".join(parts[:weapon_word_count])
                        if input_weapon_part.lower() == item["name"].lower():
                            item_found = item
                            # Everything after the weapon name is the custom attack
                            if len(parts) > weapon_word_count:
                                custom_attack = " ".join(parts[weapon_word_count:])
                            break
                
                if not item_found:
                    await ctx.send(f"❌ '{actual_item_name}' is not a valid weapon! Check your inventory with `P!inv`")
                    return
                
                # Check ownership for regular weapon names
                if item_found["name"] not in user_items:
                    await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
                    return
                
                # REQUIRE an attack name when using weapon name
                if not custom_attack:
                    await ctx.send(f"❌ You must specify an attack! Use `P!train attack <weapon_id>` (e.g., K1) or `P!train attack {item_found['name']} <attack_name>`")
                    return
            
            base_damage = item_found.get("damage", 0)
            user_level = get_user_level(ctx.author.id)
            item_level = get_item_level(ctx.author.id, item_found["name"])
            damage = calculate_damage_with_level(base_damage, user_level, item_level)
            
            # Handle custom attacks
            if custom_attack:
                weapon_name = item_found['name']
                
                # Initialize custom_attacks if needed (for user-created attacks)
                if "custom_attacks" not in chi_data[user_id]:
                    chi_data[user_id]["custom_attacks"] = {}
                if weapon_name not in chi_data[user_id]["custom_attacks"]:
                    chi_data[user_id]["custom_attacks"][weapon_name] = []
                
                # Check if using same attack as last turn
                last_attack = active_npc_training.get("last_attack")
                if last_attack and last_attack.lower() == custom_attack.lower():
                    await ctx.send(f"❌ You can't use the same attack **{custom_attack}** twice in a row! Choose a different attack.")
                    return
                
                # Store this attack as the last used
                active_npc_training["last_attack"] = custom_attack
                
                preconfigured_attacks = item_found.get("custom_attacks", {})
                attack_found = None
                
                # Check for pre-configured attack (case-insensitive)
                for attack_name_check, attack_info in preconfigured_attacks.items():
                    if attack_name_check.lower() == custom_attack.lower():
                        attack_found = attack_info
                        custom_attack = attack_name_check  # Use proper casing
                        break
                
                if attack_found:
                    # Use pre-configured attack damage (no level bonuses - damage matches exactly as shown)
                    import random
                    min_dmg = attack_found.get("min_damage", damage)
                    max_dmg = attack_found.get("max_damage", damage)
                    
                    damage = random.randint(min_dmg, max_dmg)
                else:
                    # User-created custom attack - use hash-based variation
                    # Add custom attack if not already in list
                    if custom_attack not in chi_data[user_id]["custom_attacks"][weapon_name]:
                        chi_data[user_id]["custom_attacks"][weapon_name].append(custom_attack)
                        save_data()
                    
                    # Each custom attack does different damage (vary by +/-20%)
                    attack_hash = sum(ord(c) for c in custom_attack.lower())
                    damage_variation = (attack_hash % 41) - 20  # Range: -20 to +20
                    damage = max(1, damage + damage_variation)
            
            active_npc_training["npc_hp"] -= damage
            npc_info = NPC_DATA[active_npc_training["npc_key"]]
            
            if custom_attack:
                await ctx.send(f"🎯 {ctx.author.mention} used **{item_found['name']}** to unleash *{custom_attack}* and dealt **{damage} damage** to {npc_info['emoji']} {npc_info['name']}!")
            else:
                await ctx.send(f"🎯 {ctx.author.mention} attacked with **{item_found['name']}** and dealt **{damage} damage** to {npc_info['emoji']} {npc_info['name']}!")
            
            # Check if NPC is defeated
            if active_npc_training["npc_hp"] <= 0:
                chi_reward = {"dummy": 0, "easy": 40, "medium": 75, "hard": 150}[active_npc_training["npc_key"]]  # Moderate 50-60% increase
                if chi_reward > 0:
                    update_chi(user_id, chi_reward)
                
                active_npc_training = None
                
                embed = discord.Embed(
                    title="🏆 TRAINING COMPLETE!",
                    description=f"{ctx.author.mention} defeated **{npc_info['emoji']} {npc_info['name']}**!\n\n**Reward:** +{chi_reward} chi" if chi_reward > 0 else f"{ctx.author.mention} defeated the Training Dummy!\n\n*Great practice session!*",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                return
            
            # NPC's turn (except dummy)
            if active_npc_training["npc_key"] != "dummy":
                npc_damage = random.randint(npc_info["damage_min"], npc_info["damage_max"])
                active_npc_training["player_hp"] -= npc_damage
                
                await ctx.send(f"{npc_info['emoji']} {npc_info['name']} counterattacks for **{npc_damage} damage**!")
                
                # Check if player is defeated
                if active_npc_training["player_hp"] <= 0:
                    update_chi(user_id, -50)
                    active_npc_training = None
                    
                    embed = discord.Embed(
                        title="💀 DEFEATED!",
                        description=f"{ctx.author.mention} was defeated by **{npc_info['emoji']} {npc_info['name']}**!\n\n**Penalty:** -50 chi\n\n*Train harder and try again!*",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
            
            # Display status
            embed = discord.Embed(
                title=f"{npc_info['emoji']} Training Status",
                description=f"**HP:**\n{ctx.author.mention}: {active_npc_training['player_hp']}/{active_npc_training['player_max_hp']} HP\n{npc_info['emoji']} {npc_info['name']}: {active_npc_training['npc_hp']}/{active_npc_training['npc_max_hp']} HP\n\n{ctx.author.mention}'s turn!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Regular player vs player training
        if active_training is None or active_training["status"] != "active":
            await ctx.send("🥊 There's no active training session right now!")
            return
        
        if ctx.author.id != active_training["turn"]:
            await ctx.send("🥊 It's not your turn!")
            return
        
        # For mode_or_item parameter handling
        actual_item_name = f"{mode_or_item} {item_name}".strip() if mode_or_item else ""
        if not actual_item_name:
            await ctx.send("❌ Usage: `P!train attack <weapon_id>` or `P!train attack <weapon> <attack>`\nExample: `P!train attack K1` or `P!train attack Katana Swift Slash`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        # Try weapon ID first (K1, DW2, BS3, etc.)
        weapon_id_result = parse_weapon_id(actual_item_name)
        
        if weapon_id_result:
            weapon_name, attack_name, damage_info = weapon_id_result
            
            # Check if user owns this weapon
            if weapon_name not in user_items:
                await ctx.send(f"❌ You don't own **{weapon_name}**! Buy it from `P!cshop`")
                return
            
            # Find the weapon item
            item_found = None
            for item in chi_shop_data["items"]:
                if item["name"] == weapon_name:
                    item_found = item
                    break
            
            if not item_found:
                await ctx.send(f"❌ Weapon not found!")
                return
            
            custom_attack = attack_name
        else:
            # Parse weapon name and REQUIRED attack name
            # Find the weapon by trying to match from all available weapons (supports multi-word names)
            item_found = None
            custom_attack = None
            parts = actual_item_name.split()
            
            # Get all weapons and sort by word count (longest first) to match longest weapon names first
            weapons = [item for item in chi_shop_data["items"] if "weapon" in item.get("tags", [])]
            weapons.sort(key=lambda x: len(x["name"].split()), reverse=True)
            
            # Try to match weapon names from longest to shortest
            for item in weapons:
                weapon_words = item["name"].split()
                weapon_word_count = len(weapon_words)
                
                # Check if input starts with this weapon name
                if len(parts) >= weapon_word_count:
                    input_weapon_part = " ".join(parts[:weapon_word_count])
                    if input_weapon_part.lower() == item["name"].lower():
                        item_found = item
                        # Everything after the weapon name is the custom attack
                        if len(parts) > weapon_word_count:
                            custom_attack = " ".join(parts[weapon_word_count:])
                        break
            
            if not item_found:
                await ctx.send(f"❌ '{actual_item_name}' is not a valid weapon! Check your inventory with `P!inv`")
                return
            
            # Check ownership for regular weapon names
            if item_found["name"] not in user_items:
                await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
                return
            
            # REQUIRE an attack name when using weapon name
            if not custom_attack:
                await ctx.send(f"❌ You must specify an attack! Use `P!train attack <weapon_id>` (e.g., K1) or `P!train attack {item_found['name']} <attack_name>`")
                return
        
        base_damage = item_found.get("damage", 0)
        user_level = get_user_level(ctx.author.id)
        item_level = get_item_level(ctx.author.id, item_found["name"])
        damage = calculate_damage_with_level(base_damage, user_level, item_level)
        
        if "uses" in item_found:
            use_key = f"{user_id}_{item_found['name']}"
            current_uses = active_training["item_uses"].get(use_key, 0)
            if current_uses >= item_found["uses"]:
                await ctx.send(f"❌ {item_found['name']} has no uses left! You need to buy it again.")
                return
            active_training["item_uses"][use_key] = current_uses + 1
        
        if ctx.author.id == active_training["challenger"]:
            active_training["challenged_hp"] -= damage
            opponent_id = active_training["challenged"]
            opponent_hp = active_training["challenged_hp"]
            active_training["turn"] = active_training["challenged"]
        else:
            active_training["challenger_hp"] -= damage
            opponent_id = active_training["challenger"]
            opponent_hp = active_training["challenger_hp"]
            active_training["turn"] = active_training["challenger"]
        
        opponent = ctx.guild.get_member(opponent_id)
        
        # Handle custom attacks
        if custom_attack:
            weapon_name = item_found['name']
            
            # Initialize custom_attacks if needed (for user-created attacks)
            if "custom_attacks" not in chi_data[user_id]:
                chi_data[user_id]["custom_attacks"] = {}
            if weapon_name not in chi_data[user_id]["custom_attacks"]:
                chi_data[user_id]["custom_attacks"][weapon_name] = []
            
            # Check if using same attack as last turn
            last_attack = active_training.get("last_attack", {}).get(str(ctx.author.id))
            if last_attack and last_attack.lower() == custom_attack.lower():
                await ctx.send(f"❌ You can't use the same attack **{custom_attack}** twice in a row! Choose a different attack.")
                return
            
            # Store this attack as the last used
            if "last_attack" not in active_training:
                active_training["last_attack"] = {}
            active_training["last_attack"][str(ctx.author.id)] = custom_attack
            
            preconfigured_attacks = item_found.get("custom_attacks", {})
            attack_found = None
            
            # Check for pre-configured attack (case-insensitive)
            for attack_name_check, attack_info in preconfigured_attacks.items():
                if attack_name_check.lower() == custom_attack.lower():
                    attack_found = attack_info
                    custom_attack = attack_name_check  # Use proper casing
                    break
            
            if attack_found:
                # Use pre-configured attack damage (no level bonuses - damage matches exactly as shown)
                import random
                min_dmg = attack_found.get("min_damage", damage)
                max_dmg = attack_found.get("max_damage", damage)
                
                modified_damage = random.randint(min_dmg, max_dmg)
                
                # Update opponent HP with modified damage
                if ctx.author.id == active_training["challenger"]:
                    active_training["challenged_hp"] += damage  # Undo base damage
                    active_training["challenged_hp"] -= modified_damage
                    opponent_hp = active_training["challenged_hp"]
                else:
                    active_training["challenger_hp"] += damage  # Undo base damage
                    active_training["challenger_hp"] -= modified_damage
                    opponent_hp = active_training["challenger_hp"]
                
                await ctx.send(f"🥊 {ctx.author.mention} used **{weapon_name}** to unleash *{custom_attack}* and dealt **{modified_damage} damage** to {opponent.mention}!")
            else:
                # User-created custom attack - use hash-based variation
                # Add custom attack if not already in list
                if custom_attack not in chi_data[user_id]["custom_attacks"][weapon_name]:
                    chi_data[user_id]["custom_attacks"][weapon_name].append(custom_attack)
                    save_data()
                
                # Each custom attack does different damage (vary by +/-20%)
                attack_hash = sum(ord(c) for c in custom_attack.lower())
                damage_variation = (attack_hash % 41) - 20  # Range: -20 to +20
                modified_damage = max(1, damage + damage_variation)
                
                # Update opponent HP with modified damage
                if ctx.author.id == active_training["challenger"]:
                    active_training["challenged_hp"] += damage  # Undo base damage
                    active_training["challenged_hp"] -= modified_damage
                    opponent_hp = active_training["challenged_hp"]
                else:
                    active_training["challenger_hp"] += damage  # Undo base damage
                    active_training["challenger_hp"] -= modified_damage
                    opponent_hp = active_training["challenger_hp"]
                
                await ctx.send(f"🥊 {ctx.author.mention} used **{weapon_name}** to unleash *{custom_attack}* and dealt **{modified_damage} damage** to {opponent.mention}!")
        else:
            await ctx.send(f"🥊 {ctx.author.mention} attacked with **{item_found['name']}** and dealt **{damage} damage** to {opponent.mention}!")
        
        if opponent_hp <= 0:
            winner = ctx.author
            loser = opponent
            is_tournament = active_training.get("is_tournament", False)
            
            bet_results = process_duel_bets(winner.id, ctx.guild)
            active_training = None
            
            winner_id = str(winner.id)
            loser_id = str(loser.id)
            
            # Training gives same chi rewards as duels
            if is_tournament:
                chi_reward = 150
                update_chi(winner_id, chi_reward)
                # Loser no longer loses chi in training - encourages practice
                win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for winning the training!"
            else:
                chi_reward = 75  # Moderate 50% increase from 50
                update_chi(winner_id, chi_reward)
                # Loser no longer loses chi - removes risk from practice
                win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for winning the training session!"
            
            # Update team duel stats (training counts as duel stats but NOT team score)
            if winner_id in teams_data["user_teams"]:
                winner_team_id = teams_data["user_teams"][winner_id]
                teams_data["teams"][winner_team_id]["duel_stats"]["wins"] += 1
                save_teams()
            
            if loser_id in teams_data["user_teams"]:
                loser_team_id = teams_data["user_teams"][loser_id]
                teams_data["teams"][loser_team_id]["duel_stats"]["losses"] += 1
                save_teams()
            
            description = f"**{win_message}**\n\n{loser.mention} has been defeated!\n\n**Rewards:**\n{winner.mention}: +{chi_reward} chi"
            
            if bet_results:
                description += f"\n\n**💰 Betting Results:**\n" + "\n".join(bet_results)
            
            embed = discord.Embed(
                title="🏆 TRAINING COMPLETE!",
                description=description,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            next_turn_user = ctx.guild.get_member(active_training["turn"])
            
            challenger = ctx.guild.get_member(active_training["challenger"])
            challenged = ctx.guild.get_member(active_training["challenged"])
            
            embed = discord.Embed(
                title="🥊 Training Status",
                description=f"**HP:**\n{challenger.mention}: {active_training['challenger_hp']}/{active_training['challenger_max_hp']} HP\n{challenged.mention}: {active_training['challenged_hp']}/{active_training['challenged_max_hp']} HP\n\n{next_turn_user.mention}'s turn!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        return
    
    if action_or_user == "heal":
        # Check for NPC training first
        if active_npc_training is not None:
            if ctx.author.id != active_npc_training["player_id"]:
                await ctx.send("🎯 This is not your NPC training session!")
                return
            
            # For mode_or_item parameter handling
            actual_item_name = f"{mode_or_item} {item_name}".strip() if mode_or_item else ""
            if not actual_item_name:
                await ctx.send("❌ Usage: `P!train heal <item_name>`")
                return
            
            user_id = str(ctx.author.id)
            user_items = chi_data.get(user_id, {}).get("purchased_items", [])
            
            item_found = None
            for item in chi_shop_data["items"]:
                if item["name"].lower() == actual_item_name.lower() and "healing" in item.get("tags", []):
                    item_found = item
                    break
            
            if not item_found:
                await ctx.send(f"❌ '{actual_item_name}' is not a valid healing item! Check your inventory with `P!inv`")
                return
            
            if item_found["name"] not in user_items:
                await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
                return
            
            base_healing = item_found.get("healing", 0)
            user_level = get_user_level(ctx.author.id)
            item_level = get_item_level(ctx.author.id, item_found["name"])
            healing = calculate_healing_with_level(base_healing, user_level, item_level)
            
            old_hp = active_npc_training["player_hp"]
            active_npc_training["player_hp"] = min(active_npc_training["player_hp"] + healing, active_npc_training["player_max_hp"])
            actual_healing = active_npc_training["player_hp"] - old_hp
            
            npc_info = NPC_DATA[active_npc_training["npc_key"]]
            await ctx.send(f"💚 {ctx.author.mention} used **{item_found['name']}** and healed for **{actual_healing} HP**!")
            
            # NPC's turn (except dummy)
            if active_npc_training["npc_key"] != "dummy":
                npc_damage = random.randint(npc_info["damage_min"], npc_info["damage_max"])
                active_npc_training["player_hp"] -= npc_damage
                
                await ctx.send(f"{npc_info['emoji']} {npc_info['name']} attacks for **{npc_damage} damage**!")
                
                # Check if player is defeated
                if active_npc_training["player_hp"] <= 0:
                    update_chi(user_id, -50)
                    active_npc_training = None
                    
                    embed = discord.Embed(
                        title="💀 DEFEATED!",
                        description=f"{ctx.author.mention} was defeated by **{npc_info['emoji']} {npc_info['name']}**!\n\n**Penalty:** -50 chi\n\n*Train harder and try again!*",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
            
            # Display status
            embed = discord.Embed(
                title=f"{npc_info['emoji']} Training Status",
                description=f"**HP:**\n{ctx.author.mention}: {active_npc_training['player_hp']}/{active_npc_training['player_max_hp']} HP\n{npc_info['emoji']} {npc_info['name']}: {active_npc_training['npc_hp']}/{active_npc_training['npc_max_hp']} HP\n\n{ctx.author.mention}'s turn!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
        
        # Regular player vs player training attack
        if active_training is None or active_training["status"] != "active":
            await ctx.send("🥊 There's no active training session right now!")
            return
        
        if ctx.author.id != active_training["turn"]:
            await ctx.send("🥊 It's not your turn!")
            return
        
        # For mode_or_item parameter handling
        actual_item_name = f"{mode_or_item} {item_name}".strip() if mode_or_item else ""
        if not actual_item_name:
            await ctx.send("❌ Usage: `P!train heal <item_name>`")
            return
        
        user_id = str(ctx.author.id)
        user_items = chi_data.get(user_id, {}).get("purchased_items", [])
        
        item_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == actual_item_name.lower() and "healing" in item.get("tags", []):
                item_found = item
                break
        
        if not item_found:
            await ctx.send(f"❌ '{actual_item_name}' is not a valid healing item! Check your inventory with `P!inv`")
            return
        
        if item_found["name"] not in user_items:
            await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop`")
            return
        
        base_healing = item_found.get("healing", 0)
        user_level = get_user_level(ctx.author.id)
        item_level = get_item_level(ctx.author.id, item_found["name"])
        healing = calculate_healing_with_level(base_healing, user_level, item_level)
        
        if ctx.author.id == active_training["challenger"]:
            old_hp = active_training["challenger_hp"]
            active_training["challenger_hp"] = min(active_training["challenger_hp"] + healing, active_training["challenger_max_hp"])
            actual_healing = active_training["challenger_hp"] - old_hp
            active_training["turn"] = active_training["challenged"]
        else:
            old_hp = active_training["challenged_hp"]
            active_training["challenged_hp"] = min(active_training["challenged_hp"] + healing, active_training["challenged_max_hp"])
            actual_healing = active_training["challenged_hp"] - old_hp
            active_training["turn"] = active_training["challenger"]
        
        await ctx.send(f"💚 {ctx.author.mention} used **{item_found['name']}** and healed for **{actual_healing} HP**!")
        
        next_turn_user = ctx.guild.get_member(active_training["turn"])
        
        challenger = ctx.guild.get_member(active_training["challenger"])
        challenged = ctx.guild.get_member(active_training["challenged"])
        
        embed = discord.Embed(
            title="🥊 Training Status",
            description=f"**HP:**\n{challenger.mention}: {active_training['challenger_hp']}/{active_training['challenger_max_hp']} HP\n{challenged.mention}: {active_training['challenged_hp']}/{active_training['challenged_max_hp']} HP\n\n{next_turn_user.mention}'s turn!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    
    if action_or_user == "run":
        # Check for NPC training first
        if active_npc_training is not None:
            if ctx.author.id != active_npc_training["player_id"]:
                await ctx.send("🎯 This is not your NPC training session!")
                return
            
            user_id = str(ctx.author.id)
            npc_info = NPC_DATA[active_npc_training["npc_key"]]
            
            update_chi(user_id, -50)
            active_npc_training = None
            
            embed = discord.Embed(
                title="🏃 RETREAT!",
                description=f"{ctx.author.mention} fled from **{npc_info['emoji']} {npc_info['name']}**!\n\n**Penalty:** -50 chi\n\n*Train harder and return when you're ready!*",
                color=discord.Color.dark_grey()
            )
            await ctx.send(embed=embed)
            return
        
        # Regular player vs player training run
        if active_training is None or active_training["status"] != "active":
            await ctx.send("🥊 There's no active training to run from!")
            return
        
        if ctx.author.id not in [active_training["challenger"], active_training["challenged"]]:
            await ctx.send("🥊 You're not in this training!")
            return
        
        runner = ctx.author
        if ctx.author.id == active_training["challenger"]:
            winner_id = active_training["challenged"]
        else:
            winner_id = active_training["challenger"]
        
        winner = ctx.guild.get_member(winner_id)
        if not winner:
            await ctx.send("🥊 Error: Could not find the other person!")
            active_training = None
            return
        
        bet_results = process_duel_bets(winner_id, ctx.guild)
        active_training = None
        
        runner_id = str(runner.id)
        winner_id_str = str(winner_id)
        
        update_chi(runner_id, -100)
        update_chi(winner_id_str, 100)
        
        # Update team duel stats (training doesn't count toward team score)
        if winner_id_str in teams_data["user_teams"]:
            winner_team_id = teams_data["user_teams"][winner_id_str]
            teams_data["teams"][winner_team_id]["duel_stats"]["wins"] += 1
            save_teams()
        
        if runner_id in teams_data["user_teams"]:
            runner_team_id = teams_data["user_teams"][runner_id]
            teams_data["teams"][runner_team_id]["duel_stats"]["losses"] += 1
            save_teams()
        
        description = f"{runner.mention} ran away from the training!\n\n{winner.mention} wins by default!\n\n**Chi Changes:**\n{runner.mention}: -100 chi (coward penalty)\n{winner.mention}: +100 chi (victory by forfeit)"
        
        if bet_results:
            description += f"\n\n**💰 Betting Results:**\n" + "\n".join(bet_results)
        
        embed = discord.Embed(
            title="🏃 COWARD!",
            description=description,
            color=discord.Color.dark_grey()
        )
        await ctx.send(embed=embed)
        return
    
    if action_or_user == "bet":
        if active_training is None or active_training["status"] != "active":
            await ctx.send("🥊 There's no active training to bet on right now!")
            return
        
        if ctx.author.id in [active_training["challenger"], active_training["challenged"]]:
            await ctx.send("💰 You can't bet on a training you're in!")
            return
        
        if not ctx.message.mentions:
            await ctx.send("❌ Usage: `P!train bet <amount> @user` - Bet on who will win!")
            return
        
        try:
            bet_amount = int(item_name) if item_name else 0
        except ValueError:
            await ctx.send("❌ Usage: `P!train bet <amount> @user` - Amount must be a number!")
            return
        
        if bet_amount <= 0:
            await ctx.send("❌ Bet amount must be greater than 0!")
            return
        
        bet_on_user = ctx.message.mentions[0]
        
        if bet_on_user.id not in [active_training["challenger"], active_training["challenged"]]:
            await ctx.send("🥊 You can only bet on one of the trainers!")
            return
        
        bettor_id = str(ctx.author.id)
        if bettor_id not in chi_data:
            chi_data[bettor_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
        
        if chi_data[bettor_id]["chi"] < bet_amount:
            await ctx.send(f"❌ You don't have enough chi! You have {chi_data[bettor_id]['chi']} chi.")
            return
        
        for bet in active_training["bets"]:
            if bet["bettor_id"] == ctx.author.id:
                await ctx.send("💰 You've already placed a bet on this training!")
                return
        
        active_training["bets"].append({
            "bettor_id": ctx.author.id,
            "bet_amount": bet_amount,
            "bet_on_user_id": bet_on_user.id
        })
        
        update_chi(bettor_id, -bet_amount)
        
        embed = discord.Embed(
            title="💰 BET PLACED!",
            description=f"{ctx.author.mention} bet **{bet_amount} chi** on {bet_on_user.mention}!\n\n✅ **Win:** Gain {bet_amount * 2} chi (net +{bet_amount} chi)\n❌ **Lose:** Lose {bet_amount} chi",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Total bets on this training: {len(active_training['bets'])}")
        await ctx.send(embed=embed)
        return

@bot.command()
async def town(ctx, subcommand: str = "", *, destination: str = ""):
    """Explore the Pandian Realm Towns!
    Usage:
    - P!town info - Learn about the towns
    - P!town go <Panda/Lushsoul> - Visit a town
    - P!town about - Town history and lore
    - P!town artifact - Artifact shop
    - P!town quests - Town quest board
    """
    if not subcommand:
        embed = discord.Embed(
            title="🏘️ Pandian Realm - Towns",
            description=(
                "**Welcome to the Pandian Realm!**\n\n"
                "Explore different towns and discover new adventures!\n\n"
                "**Available Commands:**\n"
                "`P!town info` - Learn about the towns\n"
                "`P!town go <Panda/Lushsoul>` - Visit a town\n"
                "`P!town about` - Town history and lore\n"
                "`P!town artifact` - Artifact information\n"
                "`P!town quests` - Town quest board"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Choose your destination wisely!")
        await ctx.send(embed=embed)
        return
    
    subcommand = subcommand.lower()
    
    if subcommand == "info":
        embed = discord.Embed(
            title="🏘️ Pandian Realm - Town Information",
            description=(
                "**The Pandian Realm** is home to multiple unique towns, each with their own culture and secrets!\n\n"
                "**Available Towns:**\n\n"
                "🏘️ **Panda Town**\n"
                "A peaceful settlement in the heart of the realm. Home to shops, quest boards, and training grounds.\n\n"
                "⛏️ **Lushsoul Cavern**\n"
                "A mysterious cave town deep underground. Rich in ores and minerals, with the famous Lusharmory shop!\n\n"
                "Use `P!town go <town_name>` to visit a town!"
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    if subcommand == "go":
        if not destination:
            await ctx.send("❌ Please specify where you want to go!\n\n"
                          "**Available destinations:**\n"
                          "`P!town go Panda` - Visit Panda Town\n"
                          "`P!town go Lushsoul` - Visit Lushsoul Cavern")
            return
        
        destination = destination.lower()
        
        if destination == "panda":
            embed = discord.Embed(
                title="🏘️ Welcome to Panda Town!",
                description=(
                    "You step through the bamboo gates into the bustling town square...\n\n"
                    "🏪 Shops line the cobblestone streets\n"
                    "📜 Quest boards display new adventures\n"
                    "🎯 Training grounds echo with sparring warriors\n"
                    "🌸 Cherry blossoms drift gently in the breeze\n"
                    "⛲ A peaceful fountain bubbles at the center\n\n"
                    "**What would you like to do?**\n"
                    "🚧 More features coming soon!"
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text="Panda Town - Heart of the Pandian Realm")
            
            # Add interactive town buttons
            town_view = TownView("Panda Town", ctx.author.id)
            message = await ctx.send(embed=embed, view=town_view)
            town_view.message = message
            return
        
        elif destination == "lushsoul":
            embed = discord.Embed(
                title="⛏️ Welcome to Lushsoul Cavern!",
                description=(
                    "You descend into the glowing underground cavern...\n\n"
                    "💎 Crystals illuminate the cave walls\n"
                    "🛡️ The Lusharmory gleams in the distance\n"
                    "⚒️ Miners dig deep for precious ores\n"
                    "🤝 NPCs trade goods near the market stalls\n"
                    "🌑 Mysterious voidstone pulses with dark energy\n\n"
                    "**Available Features:**\n"
                    "`P!lusharmory` - Visit the armory shop\n"
                    "`P!mine` - Mine for resources\n"
                    "`P!npc list` - Trade with NPCs ✨ NEW!\n"
                ),
                color=discord.Color.dark_purple()
            )
            embed.set_footer(text="Lushsoul Cavern - Where Fortune Favors the Bold")
            
            # Add interactive town buttons
            town_view = TownView("Lushsoul Cavern", ctx.author.id)
            message = await ctx.send(embed=embed, view=town_view)
            town_view.message = message
            return
        
        else:
            await ctx.send(f"❌ Unknown destination: `{destination}`\n\n"
                          "**Available destinations:**\n"
                          "`P!town go Panda` - Visit Panda Town\n"
                          "`P!town go Lushsoul` - Visit Lushsoul Cavern")
            return
    
    if subcommand == "about":
        embed = discord.Embed(
            title="📖 Pandian Realm - History & Lore",
            description=(
                "**Legend of the Pandian Realm**\n\n"
                "Founded centuries ago by the Ancient Pandas, the Pandian Realm has stood as a beacon of peace and prosperity.\n\n"
                "**Panda Town** - The chi flows from the Sacred Bamboo Forest, granting strength to all who dwell here.\n\n"
                "**Lushsoul Cavern** - Discovered deep beneath the mountains, this underground city thrives on rare minerals and mysterious energies.\n\n"
                "Tales speak of ancient artifacts hidden in both locations, waiting for brave adventurers to uncover their secrets."
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="The Pandian Realm - Where Legends Are Born")
        await ctx.send(embed=embed)
        return
    
    if subcommand == "artifact":
        embed = discord.Embed(
            title="✨ Pandian Realm - Artifact Shop",
            description=(
                "**Master Chen's Artifact Emporium**\n\n"
                "\"Welcome, traveler! I have artifacts of great power... but they're not for sale just yet!\"\n\n"
                "💡 **Artifacts can be obtained through:**\n"
                "• Artifact spawn events (`P!artifact claim`)\n"
                "• Boss battles and special quests\n"
                "• Trading with other users\n\n"
                "Use `P!artifact list` to see your collection!"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Check back later for special artifact sales!")
        await ctx.send(embed=embed)
        return
    
    if subcommand == "quests":
        user_id = str(ctx.author.id)
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        
        completed_quests = chi_data[user_id].get("mini_quests", [])
        
        embed = discord.Embed(
            title="📜 Pandian Realm - Quest Board",
            description=(
                "**Welcome to the Quest Board!**\n\n"
                "Complete quests to earn chi and unlock special rewards!\n\n"
                "**Available Quest Types:**\n"
                "🎯 **Tutorial Quests** - For new adventurers (`P!quest todo`)\n"
                "🌙 **Monthly Quests** - Seasonal challenges (`P!quest list`)\n"
                "⚔️ **Boss Keys** - Defeat bosses for legendary keys (`P!boss keys`)\n\n"
                f"**Your Progress:** {len(completed_quests)} quests completed"
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎁 Active Rewards",
            value=(
                "• Complete 5 quests → **500 chi bonus**\n"
                "• Complete 10 quests → **1,000 chi bonus**\n"
                "• Complete all monthly quests → **Special title**"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use P!quest list to see all available quests!")
        await ctx.send(embed=embed)
        return

@bot.command()
async def npc(ctx, action: str = "", npc_name: str = "", item_name: str = "", quantity: int = 1):
    """Trade with NPCs in Panda Realm
    
    Usage:
    - P!npc list - View all NPCs
    - P!npc <name> - View NPC's shop
    - P!npc sell <name> <item> [qty] - Sell items to NPC
    - P!npc buy <name> <item> [qty] - Buy items from NPC
    """
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    # LIST all NPCs
    if not action or action.lower() == "list":
        embed = discord.Embed(
            title="🤝 NPC Traders - Pandian Realm",
            description="Trade items with NPCs for chi and special goods!",
            color=discord.Color.blue()
        )
        
        # Panda Town NPCs
        panda_npcs = []
        for npc_id, npc_data in PANDA_NPC_TRADERS["panda_town"].items():
            panda_npcs.append(f"{npc_data['emoji']} **{npc_data['name']}** - {npc_data['location']}")
        embed.add_field(name="🏘️ Panda Town", value="\n".join(panda_npcs), inline=False)
        
        # Lushsoul Cavern NPCs
        lush_npcs = []
        for npc_id, npc_data in PANDA_NPC_TRADERS["lushsoul_cavern"].items():
            lush_npcs.append(f"{npc_data['emoji']} **{npc_data['name']}** - {npc_data['location']}")
        embed.add_field(name="⛏️ Lushsoul Cavern", value="\n".join(lush_npcs), inline=False)
        
        embed.add_field(
            name="📖 How to Trade",
            value=(
                "`P!npc <npc_name>` - View NPC's shop\n"
                "`P!npc sell <npc_name> <item> [qty]` - Sell items\n"
                "`P!npc buy <npc_name> <item> [qty]` - Buy items\n\n"
                "**Example:** `P!npc sell Mei Lavender 5`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        return
    
    # VIEW specific NPC
    if action.lower() not in ["sell", "buy"]:
        # Find NPC by name (case-insensitive)
        found_npc = None
        npc_location = None
        npc_id = None
        
        for location, npcs in PANDA_NPC_TRADERS.items():
            for npc_key, npc_data in npcs.items():
                if action.lower() in npc_data['name'].lower() or action.lower() == npc_key.lower():
                    found_npc = npc_data
                    npc_location = location
                    npc_id = npc_key
                    break
            if found_npc:
                break
        
        if not found_npc:
            await ctx.send(f"❌ NPC '{action}' not found! Use `P!npc list` to see all available NPCs.")
            return
        
        # Display NPC shop
        embed = discord.Embed(
            title=f"{found_npc['emoji']} {found_npc['name']}",
            description=f"*\"{found_npc['dialogue']}\"*\n\n📍 Location: {found_npc['location']}",
            color=discord.Color.green()
        )
        
        # Show what NPC buys
        if found_npc['buys']:
            buys_list = []
            for item, price in found_npc['buys'].items():
                buys_list.append(f"• **{item}** → {price} chi")
            embed.add_field(name="💰 I Buy (You Sell)", value="\n".join(buys_list), inline=False)
        
        # Show what NPC sells
        if found_npc['sells']:
            sells_list = []
            for item, price in found_npc['sells'].items():
                sells_list.append(f"• **{item}** → {price} chi")
            embed.add_field(name="🛒 I Sell (You Buy)", value="\n".join(sells_list), inline=False)
        
        embed.set_footer(text=f"Use P!npc sell {found_npc['name'].split()[0]} <item> to trade!")
        await ctx.send(embed=embed)
        return
    
    # SELL to NPC
    if action.lower() == "sell":
        if not npc_name or not item_name:
            await ctx.send("❌ Usage: `P!npc sell <npc_name> <item> [quantity]`\n"
                          "Example: `P!npc sell Mei Lavender 5`")
            return
        
        # Find NPC
        found_npc = None
        for location, npcs in PANDA_NPC_TRADERS.items():
            for npc_key, npc_data in npcs.items():
                if npc_name.lower() in npc_data['name'].lower():
                    found_npc = npc_data
                    break
            if found_npc:
                break
        
        if not found_npc:
            await ctx.send(f"❌ NPC '{npc_name}' not found!")
            return
        
        # Find item in inventory
        inventory = chi_data[user_id].get("purchased_items", [])
        garden_inv = chi_data[user_id].get("garden_inventory", {})
        
        # Check if item exists in NPC's buy list
        if item_name not in found_npc['buys']:
            await ctx.send(f"❌ {found_npc['name']} doesn't buy **{item_name}**!\n"
                          f"Use `P!npc {found_npc['name'].split()[0]}` to see what they buy.")
            return
        
        # Check if player has the item
        has_item = False
        item_count = 0
        
        # Check garden inventory (for seeds)
        if item_name in garden_inv:
            item_count = garden_inv.get(item_name, 0)
            if isinstance(item_count, int) and item_count >= quantity:
                has_item = True
        
        # Check regular inventory
        elif item_name in inventory:
            item_count = inventory.count(item_name)
            if item_count >= quantity:
                has_item = True
        
        if not has_item or item_count < quantity:
            await ctx.send(f"❌ You don't have **{quantity}x {item_name}**!\n"
                          f"You have: {item_count}x {item_name}")
            return
        
        # Calculate chi earned
        chi_per_item = found_npc['buys'][item_name]
        total_chi = chi_per_item * quantity
        
        # Remove items and give chi
        if item_name in garden_inv:
            garden_inv[item_name] -= quantity
            if garden_inv[item_name] <= 0:
                del garden_inv[item_name]
        else:
            for _ in range(quantity):
                inventory.remove(item_name)
        
        chi_data[user_id]["chi"] += total_chi
        save_data()
        
        # Log trade
        await log_event(
            "NPC Trade",
            f"**User:** {ctx.author.mention}\n"
            f"**NPC:** {found_npc['name']}\n"
            f"**Sold:** {quantity}x {item_name}\n"
            f"**Earned:** {total_chi:,} chi", ctx.guild, discord.Color.gold())
        
        await ctx.send(f"✅ Sold **{quantity}x {item_name}** to {found_npc['emoji']} **{found_npc['name']}**!\n"
                      f"💰 Earned: **{total_chi:,} chi**\n"
                      f"New balance: **{chi_data[user_id]['chi']:,} chi**")
        return
    
    # BUY from NPC
    if action.lower() == "buy":
        if not npc_name or not item_name:
            await ctx.send("❌ Usage: `P!npc buy <npc_name> <item> [quantity]`\n"
                          "Example: `P!npc buy Mei \"Healing Potion\" 2`")
            return
        
        # Find NPC
        found_npc = None
        for location, npcs in PANDA_NPC_TRADERS.items():
            for npc_key, npc_data in npcs.items():
                if npc_name.lower() in npc_data['name'].lower():
                    found_npc = npc_data
                    break
            if found_npc:
                break
        
        if not found_npc:
            await ctx.send(f"❌ NPC '{npc_name}' not found!")
            return
        
        # Check if item exists in NPC's sell list
        if item_name not in found_npc['sells']:
            await ctx.send(f"❌ {found_npc['name']} doesn't sell **{item_name}**!\n"
                          f"Use `P!npc {found_npc['name'].split()[0]}` to see what they sell.")
            return
        
        # Calculate total cost
        chi_per_item = found_npc['sells'][item_name]
        total_cost = chi_per_item * quantity
        
        # Check if player has enough chi
        if chi_data[user_id]['chi'] < total_cost:
            await ctx.send(f"❌ You need **{total_cost:,} chi** to buy **{quantity}x {item_name}**!\n"
                          f"You have: **{chi_data[user_id]['chi']:,} chi**")
            return
        
        # Complete purchase
        chi_data[user_id]["chi"] -= total_cost
        
        if "purchased_items" not in chi_data[user_id]:
            chi_data[user_id]["purchased_items"] = []
        
        for _ in range(quantity):
            chi_data[user_id]["purchased_items"].append(item_name)
        
        save_data()
        
        # Log trade
        await log_event(
            "NPC Trade",
            f"**User:** {ctx.author.mention}\n"
            f"**NPC:** {found_npc['name']}\n"
            f"**Bought:** {quantity}x {item_name}\n"
            f"**Cost:** {total_cost:,} chi", ctx.guild, discord.Color.green())
        
        await ctx.send(f"✅ Bought **{quantity}x {item_name}** from {found_npc['emoji']} **{found_npc['name']}**!\n"
                      f"💰 Spent: **{total_cost:,} chi**\n"
                      f"New balance: **{chi_data[user_id]['chi']:,} chi**")
        return

@bot.command()
async def lusharmory(ctx, *, item_query: str = ""):
    """Visit the Lusharmory shop in Lushsoul Cavern
    Usage:
    - P!lusharmory - View all items
    - P!lusharmory buy <item_name or A#> - Purchase an item
    """
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if not item_query:
        embed = discord.Embed(
            title="🛡️ Lusharmory - Lushsoul Cavern",
            description="**Welcome to the finest armory in the underground!**\n\nForge your destiny with our exclusive items:",
            color=discord.Color.dark_purple()
        )
        
        for item_id, item_info in LUSHARMORY_ITEMS.items():
            cost_display = f"{item_info['cost']} {item_info['cost_type']}"
            embed.add_field(
                name=f"{item_id}: {item_info['emoji']} {item_info['name']} - {cost_display}",
                value=item_info['description'],
                inline=False
            )
        
        embed.set_footer(text="Use P!lusharmory buy <item_name or A#> to purchase! Example: P!lusharmory buy A1")
        await ctx.send(embed=embed)
        return
    
    if not item_query.lower().startswith("buy "):
        await ctx.send("❌ Usage: `P!lusharmory buy <item_name or A#>`\nExample: `P!lusharmory buy A1` or `P!lusharmory buy Pickaxe`")
        return
    
    item_name = item_query[4:].strip()
    
    found_item = None
    found_id = None
    
    if item_name.upper() in LUSHARMORY_ITEMS:
        found_id = item_name.upper()
        found_item = LUSHARMORY_ITEMS[found_id]
    else:
        for item_id, item_info in LUSHARMORY_ITEMS.items():
            if item_info["name"].lower() == item_name.lower():
                found_id = item_id
                found_item = item_info
                break
    
    if not found_item:
        await ctx.send(f"❌ Item '{item_name}' not found in the Lusharmory! Use `P!lusharmory` to see available items.")
        return
    
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    if found_item["cost_type"] == "chi":
        current_chi = chi_data[user_id].get("chi", 0)
        if current_chi < found_item["cost"]:
            await ctx.send(f"❌ You don't have enough chi! You need **{found_item['cost']} chi** but only have **{current_chi}**.")
            return
        
        chi_data[user_id]["chi"] -= found_item["cost"]
        chi_data[user_id]["inventory"][found_item["name"]] = chi_data[user_id]["inventory"].get(found_item["name"], 0) + 1
        save_data()
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You purchased **{found_item['emoji']} {found_item['name']}** for **{found_item['cost']} chi**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining Chi", value=str(chi_data[user_id]["chi"]), inline=True)
        await ctx.send(embed=embed)
        
        await log_event(
            "🛡️ Lusharmory Purchase",
            f"{ctx.author.mention} purchased **{found_item['name']}** for {found_item['cost']} chi", ctx.guild, discord.Color.dark_purple())
    else:
        required_ore = found_item["cost_type"]
        ore_count = chi_data[user_id]["inventory"].get(required_ore, 0)
        
        if ore_count < found_item["cost"]:
            await ctx.send(f"❌ You don't have enough {required_ore}! You need **{found_item['cost']}** but only have **{ore_count}**.")
            return
        
        chi_data[user_id]["inventory"][required_ore] -= found_item["cost"]
        if chi_data[user_id]["inventory"][required_ore] == 0:
            del chi_data[user_id]["inventory"][required_ore]
        
        chi_data[user_id]["inventory"][found_item["name"]] = chi_data[user_id]["inventory"].get(found_item["name"], 0) + 1
        save_data()
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You forged **{found_item['emoji']} {found_item['name']}** using **{found_item['cost']} {required_ore}**!",
            color=discord.Color.green()
        )
        embed.add_field(name=f"Remaining {required_ore}", value=str(chi_data[user_id]["inventory"].get(required_ore, 0)), inline=True)
        await ctx.send(embed=embed)
        
        await log_event(
            "🛡️ Lusharmory Forge",
            f"{ctx.author.mention} forged **{found_item['name']}** using {found_item['cost']} {required_ore}", ctx.guild, discord.Color.dark_purple())

@bot.command()
async def mine(ctx, target: str = ""):
    """Mine for ores and treasures in Lushsoul Cavern
    Usage:
    - P!mine - Mine for random items
    - P!mine ore - Mine specifically for ores (requires pickaxe)
    """
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    if "mining_cooldown" not in chi_data[user_id]:
        chi_data[user_id]["mining_cooldown"] = 0
    
    current_time = time.time()
    cooldown_remaining = chi_data[user_id]["mining_cooldown"] - current_time
    
    if cooldown_remaining > 0:
        minutes = int(cooldown_remaining // 60)
        seconds = int(cooldown_remaining % 60)
        await ctx.send(f"⏰ You're exhausted from mining! Rest for **{minutes}m {seconds}s** before mining again.")
        return
    
    has_pickaxe = chi_data[user_id]["inventory"].get("Pickaxe", 0) > 0
    has_echo_lantern = chi_data[user_id]["inventory"].get("Echo Lantern", 0) > 0
    
    if target.lower() == "ore":
        if not has_pickaxe:
            await ctx.send("❌ You need a **Pickaxe** to mine for ores! Purchase one at the Lusharmory (`P!lusharmory`).")
            return
        
        found_items = []
        
        for ore_name, ore_info in MINING_ORES.items():
            if ore_info.get("eclipse_only", False):
                continue
            
            if random.randint(1, 100) <= ore_info["chance"]:
                amount = random.randint(1, 3)
                chi_data[user_id]["inventory"][ore_name] = chi_data[user_id]["inventory"].get(ore_name, 0) + amount
                found_items.append(f"{ore_info['emoji']} **{ore_name}** x{amount}")
        
        if not found_items:
            found_items.append("🪨 Nothing but rocks...")
        
        chi_data[user_id]["mining_cooldown"] = current_time + 300
        save_data()
        
        embed = discord.Embed(
            title="⛏️ Ore Mining Results",
            description=f"{ctx.author.mention} strikes the cavern walls with their pickaxe!\n\n**Found:**\n" + "\n".join(found_items),
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text="Mining cooldown: 5 minutes")
        await ctx.send(embed=embed)
        
        await log_event(
            "⛏️ Ore Mining",
            f"{ctx.author.mention} mined for ores in Lushsoul Cavern", ctx.guild, discord.Color.dark_gold())
    else:
        found_items = []
        bonus_chance = 10 if has_echo_lantern else 0
        
        for item_name, item_info in MINING_ITEMS.items():
            adjusted_chance = item_info["chance"] + bonus_chance
            
            if random.randint(1, 100) <= adjusted_chance:
                amount = random.randint(1, 2)
                chi_data[user_id]["inventory"][item_name] = chi_data[user_id]["inventory"].get(item_name, 0) + amount
                found_items.append(f"{item_info['emoji']} **{item_name}** x{amount} ({item_info['rarity']})")
        
        if not found_items:
            chi_reward = random.randint(5, 15)
            chi_data[user_id]["chi"] += chi_reward
            found_items.append(f"✨ **{chi_reward} chi** (consolation prize)")
        
        chi_data[user_id]["mining_cooldown"] = current_time + 180
        save_data()
        
        embed = discord.Embed(
            title="⛏️ Mining Results",
            description=f"{ctx.author.mention} explores the cavern depths!\n\n**Found:**\n" + "\n".join(found_items),
            color=discord.Color.purple()
        )
        if has_echo_lantern:
            embed.add_field(name="🏮 Echo Lantern Bonus", value="+10% find chance!", inline=False)
        embed.set_footer(text="Mining cooldown: 3 minutes")
        await ctx.send(embed=embed)
        
        await log_event(
            "⛏️ Cavern Mining",
            f"{ctx.author.mention} mined in Lushsoul Cavern", ctx.guild, discord.Color.purple())

# Old NPC command removed - replaced with new comprehensive NPC trading system above

@bot.command()
async def riddle(ctx):
    """Get a random riddle from Pax"""
    riddles = [
        {
            "riddle": "I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?",
            "answer": "A map"
        },
        {
            "riddle": "What has hands but cannot clap?",
            "answer": "A clock"
        },
        {
            "riddle": "I'm light as a feather, yet the strongest person can't hold me for five minutes. What am I?",
            "answer": "Your breath"
        },
        {
            "riddle": "What can travel around the world while staying in a corner?",
            "answer": "A stamp"
        },
        {
            "riddle": "The more you take, the more you leave behind. What am I?",
            "answer": "Footsteps"
        },
        {
            "riddle": "What has a head and a tail but no body?",
            "answer": "A coin"
        },
        {
            "riddle": "What gets wetter the more it dries?",
            "answer": "A towel"
        },
        {
            "riddle": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?",
            "answer": "An echo"
        },
        {
            "riddle": "What can fill a room but takes up no space?",
            "answer": "Light"
        },
        {
            "riddle": "If you drop me I'm sure to crack, but give me a smile and I'll always smile back. What am I?",
            "answer": "A mirror"
        },
        {
            "riddle": "What has one eye but cannot see?",
            "answer": "A needle"
        },
        {
            "riddle": "What runs, but never walks. Murmurs, but never talks. Has a bed, but never sleeps. And has a mouth, but never eats?",
            "answer": "A river"
        }
    ]
    
    selected_riddle = random.choice(riddles)
    
    embed = discord.Embed(
        title="🐼 Pax's Riddle",
        description=f"*Pax strokes his chin thoughtfully...*\n\n**{selected_riddle['riddle']}**",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Think you know? The answer is hidden... for now! 🤔")
    
    await ctx.send(embed=embed)
    
    await ctx.author.send(f"🤫 **Secret Answer:** ||{selected_riddle['answer']}||")
    await ctx.send(f"*Pax whispered the answer to {ctx.author.mention} in DMs!*")

@bot.command()
async def level(ctx, user: discord.Member = None):
    """Check user's level (500 chi per level, max 20)"""
    target_user = user if user else ctx.author
    user_id = str(target_user.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    chi = chi_data[user_id].get("chi", 0)
    user_level = get_user_level(target_user.id)
    chi_to_next_level = 500 - (chi % 500) if user_level < 20 else 0
    
    embed = discord.Embed(
        title=f"📊 {target_user.display_name}'s Level",
        description=f"**Level:** {user_level}/20\n**Chi:** {chi}\n**Chi to next level:** {chi_to_next_level if user_level < 20 else 'MAX LEVEL'}",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="💪 Level Bonus",
        value=f"+{user_level * 5}% damage and healing",
        inline=False
    )
    embed.set_footer(text="Gain 1 level every 500 chi • Max level: 20")
    await ctx.send(embed=embed)

@bot.command()
async def upgrade(ctx, *, item_name: str = ""):
    """Upgrade an item permanently (+1 level, resets your level to 0)
    Usage: P!upgrade <item_name>
    Cost: Your current chi (resets chi to 0 and level to 0)
    """
    if not item_name:
        await ctx.send("❌ Usage: `P!upgrade <item_name>`\nExample: `P!upgrade Katana`")
        return
    
    user_id = str(ctx.author.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    user_items = chi_data[user_id].get("purchased_items", [])
    
    item_found = None
    for shop_item in chi_shop_data["items"]:
        if shop_item["name"].lower() == item_name.lower():
            item_found = shop_item
            break
    
    if not item_found:
        await ctx.send(f"❌ '{item_name}' is not a valid item! Check available items with `P!cshop`")
        return
    
    if item_found["name"] not in user_items:
        await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop` first.")
        return
    
    user_level = get_user_level(ctx.author.id)
    current_chi = chi_data[user_id].get("chi", 0)
    
    if current_chi < 500:
        await ctx.send(f"❌ You need at least 500 chi to upgrade an item! You have {current_chi} chi.")
        return
    
    if "item_levels" not in chi_data[user_id]:
        chi_data[user_id]["item_levels"] = {}
    
    current_item_level = chi_data[user_id]["item_levels"].get(item_found["name"], 0)
    
    chi_data[user_id]["item_levels"][item_found["name"]] = current_item_level + 1
    chi_data[user_id]["chi"] = 0
    
    save_data()
    
    new_item_level = current_item_level + 1
    
    embed = discord.Embed(
        title="⚡ ITEM UPGRADED!",
        description=f"**{item_found['name']}** upgraded to level {new_item_level}!\n\n**Item Bonus:** +{new_item_level * 5}% damage/healing\n\n**Cost:**\n❌ Chi reset to 0 (was {current_chi})\n❌ User level reset to 0 (was {user_level})",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Item levels are permanent! Your user level will rebuild as you gain chi.")
    await ctx.send(embed=embed)

@tasks.loop(seconds=30)
async def duel_timeout_check():
    """Check if active duel has exceeded 10 minute time limit"""
    global active_duel
    
    if active_duel is not None and active_duel["status"] == "active":
        time_elapsed = (datetime.utcnow() - active_duel["start_time"]).total_seconds()
        
        if time_elapsed >= 600:
            guild = bot.get_guild(active_duel["guild_id"])
            if guild:
                channel = guild.get_channel(active_duel["channel_id"])
                if channel and isinstance(channel, discord.TextChannel):
                    challenger = guild.get_member(active_duel["challenger"])
                    challenged = guild.get_member(active_duel["challenged"])
                    
                    if challenger and challenged:
                        description = f"The duel between {challenger.mention} and {challenged.mention} has exceeded 10 minutes!\n\n**Final HP:**\n{challenger.mention}: {active_duel['challenger_hp']} HP\n{challenged.mention}: {active_duel['challenged_hp']} HP\n\nNo winner declared!"
                        
                        if active_duel.get("bets"):
                            description += f"\n\n**💰 All bets refunded due to timeout!**"
                            for bet in active_duel["bets"]:
                                bettor_id = str(bet["bettor_id"])
                                bet_amount = bet["bet_amount"]
                                update_chi(bettor_id, bet_amount)
                        
                        # Update team duel stats - both teams get a tie
                        challenger_id = str(active_duel["challenger"])
                        challenged_id = str(active_duel["challenged"])
                        
                        if challenger_id in teams_data["user_teams"]:
                            challenger_team_id = teams_data["user_teams"][challenger_id]
                            teams_data["teams"][challenger_team_id]["duel_stats"]["ties"] += 1
                        
                        if challenged_id in teams_data["user_teams"]:
                            challenged_team_id = teams_data["user_teams"][challenged_id]
                            teams_data["teams"][challenged_team_id]["duel_stats"]["ties"] += 1
                        
                        save_teams()
                        
                        embed = discord.Embed(
                            title="⏱️ DUEL TIMEOUT!",
                            description=description,
                            color=discord.Color.dark_grey()
                        )
                        await channel.send(embed=embed)
            
            active_duel = None

@tasks.loop(seconds=30)
async def training_timeout_check():
    """Check if active training has exceeded 10 minute time limit"""
    global active_training
    
    if active_training is not None and active_training["status"] == "active":
        time_elapsed = (datetime.utcnow() - active_training["start_time"]).total_seconds()
        
        if time_elapsed >= 600:
            guild = bot.get_guild(active_training["guild_id"])
            if guild:
                channel = guild.get_channel(active_training["channel_id"])
                if channel and isinstance(channel, discord.TextChannel):
                    challenger = guild.get_member(active_training["challenger"])
                    challenged = guild.get_member(active_training["challenged"])
                    
                    if challenger and challenged:
                        description = f"The training between {challenger.mention} and {challenged.mention} has exceeded 10 minutes!\n\n**Final HP:**\n{challenger.mention}: {active_training['challenger_hp']} HP\n{challenged.mention}: {active_training['challenged_hp']} HP\n\nNo winner declared!"
                        
                        if active_training.get("bets"):
                            description += f"\n\n**💰 All bets refunded due to timeout!**"
                            for bet in active_training["bets"]:
                                bettor_id = str(bet["bettor_id"])
                                bet_amount = bet["bet_amount"]
                                update_chi(bettor_id, bet_amount)
                        
                        # Update team duel stats - both teams get a tie
                        challenger_id = str(active_training["challenger"])
                        challenged_id = str(active_training["challenged"])
                        
                        if challenger_id in teams_data["user_teams"]:
                            challenger_team_id = teams_data["user_teams"][challenger_id]
                            teams_data["teams"][challenger_team_id]["duel_stats"]["ties"] += 1
                        
                        if challenged_id in teams_data["user_teams"]:
                            challenged_team_id = teams_data["user_teams"][challenged_id]
                            teams_data["teams"][challenged_team_id]["duel_stats"]["ties"] += 1
                        
                        save_teams()
                        
                        embed = discord.Embed(
                            title="⏱️ TRAINING TIMEOUT!",
                            description=description,
                            color=discord.Color.dark_grey()
                        )
                        await channel.send(embed=embed)
            
            active_training = None

@tasks.loop(seconds=60)
async def chi_event_scheduler():
    global event_active, event_claimer, current_event_message, current_event_type, next_event_time
    if event_active:
        return
    
    now = datetime.utcnow()
    if next_event_time is None or now < next_event_time:
        return
    
    guild = bot.guilds[0] if bot.guilds else None
    if not guild:
        return
    
    # Use guild config to get event channel, fallback to first available text channel
    guild_id = str(guild.id)
    event_channel_id = get_config_value(guild_id, "channels.log_channel_id")
    
    if event_channel_id:
        channel = guild.get_channel(int(event_channel_id))
    else:
        # Fallback: use first available text channel with send permissions
        channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
    
    if not channel or not isinstance(channel, discord.TextChannel):
        return
    
    event_type = random.choice(["positive", "negative"])
    current_event_type = event_type
    
    if event_type == "positive":
        embed = discord.Embed(
            title="✨🐼 POSITIVE CHI EVENT!",
            description=f"Be the first to claim it! Type `P!claim` within {CHI_EVENT_CLAIM_TIME} seconds!",
            color=discord.Color.gold()
        )
    else:
        embed = discord.Embed(
            title="💀🐼 NEGATIVE CHI EVENT!",
            description=f"Be the first to claim it! Type `P!claim` within {CHI_EVENT_CLAIM_TIME} seconds!\n⚠️ Warning: This will REMOVE chi!",
            color=discord.Color.dark_red()
        )
    
    current_event_message = await channel.send(embed=embed)
    event_active = True
    event_claimer = None
    
    next_event_time = datetime.utcnow() + timedelta(seconds=random.randint(CHI_EVENT_MIN_INTERVAL, CHI_EVENT_MAX_INTERVAL))
    
    await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=CHI_EVENT_CLAIM_TIME))
    if event_active:
        event_active = False
        event_claimer = None
        await current_event_message.edit(embed=discord.Embed(
            title=f"{'✨' if event_type == 'positive' else '💀'}🐼 Chi Event Expired!",
            description="No one claimed it in time… maybe next round!",
            color=discord.Color.dark_grey()
        ))

@tasks.loop(minutes=30)
async def artifact_spawner():
    """Spawn random artifacts at intervals between 1-12 hours"""
    global artifact_state
    
    now = datetime.utcnow()
    
    # Initialize next spawn time if not set
    if not artifact_state.get("next_spawn_at"):
        # Ensure minimum 1 hour delay
        hours = random.randint(ARTIFACT_SPAWN_MIN_HOURS, ARTIFACT_SPAWN_MAX_HOURS)
        if hours < ARTIFACT_SPAWN_MIN_HOURS:
            hours = ARTIFACT_SPAWN_MIN_HOURS
        artifact_state["next_spawn_at"] = (now + timedelta(hours=hours)).isoformat()
        save_artifact_state()
        print(f"[Artifact] Next spawn scheduled in {hours} hours at {artifact_state['next_spawn_at']}")
        return
    
    next_spawn = datetime.fromisoformat(artifact_state["next_spawn_at"])
    
    # Check if it's time to spawn
    if now < next_spawn:
        return
    
    # Don't spawn if there's an active artifact
    if artifact_state.get("active_artifact"):
        return
    
    # Select artifact tier based on weights
    tiers = list(ARTIFACT_CONFIG.keys())
    weights = [ARTIFACT_CONFIG[t]["weight"] for t in tiers]
    selected_tier = random.choices(tiers, weights=weights)[0]
    
    # Select random emoji and name for this tier
    emoji_index = random.randint(0, len(ARTIFACT_CONFIG[selected_tier]["emojis"]) - 1)
    selected_emoji = ARTIFACT_CONFIG[selected_tier]["emojis"][emoji_index]
    selected_name = ARTIFACT_CONFIG[selected_tier]["names"][emoji_index]
    
    # Create artifact ID
    artifact_id = f"{selected_tier}_{int(now.timestamp())}"
    
    # Set up artifact state
    artifact_state["active_artifact"] = {
        "id": artifact_id,
        "emoji": selected_emoji,
        "name": selected_name,
        "tier": selected_tier,
        "spawned_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ARTIFACT_CLAIM_TIME)).isoformat(),
        "claimed_by": None
    }
    artifact_state["last_spawn_at"] = now.isoformat()
    save_artifact_state()
    
    # Post to configured channels
    tier_colors = {
        "common": discord.Color.light_grey(),
        "rare": discord.Color.purple(),
        "legendary": discord.Color.gold(),
        "eternal": discord.Color.dark_blue(),
        "mythical": discord.Color.from_rgb(255, 0, 255)  # Magenta
    }
    
    embed = discord.Embed(
        title=f"{selected_emoji} MYSTICAL ARTIFACT APPEARED!",
        description=f"**{selected_name}**\n"
                   f"A **{selected_tier.upper()}** artifact has materialized!\n\n"
                   f"Type `P!find artifact` to claim it within **5 minutes**!\n\n"
                   f"💊 Healing Power: **{ARTIFACT_CONFIG[selected_tier]['heal_percent']}% HP** in duels",
        color=tier_colors.get(selected_tier, discord.Color.blue())
    )
    embed.set_footer(text=f"{selected_name} • ID: {artifact_id}")
    
    # Post to all guilds using their configured event channel or fallback
    for guild in bot.guilds:
        guild_id = str(guild.id)
        event_channel_id = get_config_value(guild_id, "channels.log_channel_id")
        
        if event_channel_id:
            channel = guild.get_channel(int(event_channel_id))
        else:
            # Fallback: use first available text channel with send permissions
            channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
        
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
    
    # Schedule next spawn (ensure minimum 1 hour)
    hours = random.randint(ARTIFACT_SPAWN_MIN_HOURS, ARTIFACT_SPAWN_MAX_HOURS)
    if hours < ARTIFACT_SPAWN_MIN_HOURS:
        hours = ARTIFACT_SPAWN_MIN_HOURS
    artifact_state["next_spawn_at"] = (now + timedelta(hours=hours)).isoformat()
    save_artifact_state()
    print(f"[Artifact] Next spawn scheduled in {hours} hours")
    
    # Start timeout task
    await asyncio.sleep(ARTIFACT_CLAIM_TIME)
    
    # Check if artifact was claimed
    if artifact_state.get("active_artifact") and artifact_state["active_artifact"]["id"] == artifact_id:
        if not artifact_state["active_artifact"].get("claimed_by"):
            # Artifact expired
            artifact_state["active_artifact"] = None
            save_artifact_state()
            
            expired_embed = discord.Embed(
                title=f"{selected_emoji} Artifact Vanished...",
                description="The mystical artifact faded away unclaimed.",
                color=discord.Color.dark_grey()
            )
            
            # Post to all guilds using their configured event channel or fallback
            for guild in bot.guilds:
                guild_id = str(guild.id)
                event_channel_id = get_config_value(guild_id, "channels.log_channel_id")
                
                if event_channel_id:
                    channel = guild.get_channel(int(event_channel_id))
                else:
                    # Fallback: use first available text channel with send permissions
                    channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
                
                if channel and isinstance(channel, discord.TextChannel):
                    await channel.send(embed=expired_embed)

@tasks.loop(hours=1)
async def monthly_reset_check():
    now = datetime.utcnow()
    theme_name, quests = get_current_theme()
    if quest_data.get("month") != theme_name:
        quest_data["month"] = theme_name
        quest_data["quests"] = quests
        quest_data["user_progress"] = {}
        save_quests()
        guild = bot.guilds[0] if bot.guilds else None
        if guild:
            channel = guild.get_channel(CHANNEL_ID)
            if channel and isinstance(channel, discord.TextChannel):
                embed = discord.Embed(title=f"🎯 {theme_name} Quests for this Month", color=discord.Color.orange())
                for q in quests:
                    embed.add_field(name="\u200b", value=q, inline=False)
                await channel.send(embed=embed)

@tasks.loop(minutes=1)
async def database_sync_task():
    """Periodically sync all critical data to database for persistence (every 1 minute for fast persistence)"""
    if not db.pool:
        return
    
    try:
        # Sync ALL users to database (fast bulk operation)
        for user_id_str in list(chi_data.keys()):
            try:
                await sync_user_to_db(int(user_id_str))
            except Exception:
                pass
        
        # Sync all teams data (FULL data including members, decorations, upgrades)
        # DISABLED: Deprecated bulk method - use guild-aware team sync instead
        # try:
        #     await db.save_all_teams_data(teams_data)
        # except Exception as e:
        #     print(f"⚠️ Failed to sync teams to database: {e}")
        
        # Sync ALL gardens to database (critical for persistence)
        gardens = gardens_data.get("gardens", {})
        for user_id_str in list(gardens.keys()):
            try:
                await sync_garden_to_db(int(user_id_str))
            except Exception:
                pass
                
    except Exception as e:
        print(f"⚠️ Database sync failed: {e}")

@tasks.loop(minutes=1)
async def daily_chi_evaluation():
    now = datetime.utcnow()
    if now.hour == 23 and now.minute == 59:
        if not bot.guilds:
            return
        guild = bot.guilds[0]
        channel = guild.get_channel(CHANNEL_ID)
        if not channel:
            return

        positive_role = guild.get_role(POSITIVE_ROLE_ID)

        if not positive_role:
            print("Error: Could not find positive role")
            return

        for member in guild.members:
            try:
                if positive_role in member.roles:
                    await member.remove_roles(positive_role)
            except:
                pass

        positive_members = []
        negative_members = []

        for user_id_str, data in chi_data.items():
            member = guild.get_member(int(user_id_str))
            if member:
                if data["chi"] > 0:
                    positive_members.append((member, data["chi"]))
                elif data["chi"] < 0:
                    negative_members.append((member, data["chi"]))

        positive_members.sort(key=lambda x: x[1], reverse=True)
        negative_members.sort(key=lambda x: x[1])
        
        if positive_members:
            try:
                await positive_members[0][0].add_roles(positive_role)
            except:
                pass

        embed = discord.Embed(title="🐼 Daily Panda Chi Summary", color=discord.Color.blue())
        embed.add_field(name="Top 3 Positive Chi", value="\n".join(
            [f"{i+1}. {m.display_name} 🐼✨ (Chi: {chi})" for i, (m, chi) in enumerate(positive_members[:3])]
        ) or "No positive chi today!", inline=False)

        embed.add_field(name="Top 3 Negative Chi", value="\n".join(
            [f"{i+1}. {m.display_name} 🐾💀 (Chi: {chi})" for i, (m, chi) in enumerate(negative_members[:3])]
        ) or "No negative chi today!", inline=False)

        embed.add_field(name="Totals", value=f"Positive: {len(positive_members)}\nNegative: {len(negative_members)}", inline=False)

        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.emoji) != "✅":
        return
    if not reaction.message.guild or not user.guild_permissions.administrator:
        return
    
    msg_author = reaction.message.author
    user_id = str(msg_author.id)
    
    if user_id not in quest_data["user_progress"]:
        quest_data["user_progress"][user_id] = []
    
    for i, quest in enumerate(quest_data["quests"]):
        if quest in reaction.message.content:
            if i not in quest_data["user_progress"][user_id]:
                quest_data["user_progress"][user_id].append(i)
                save_quests()
                try:
                    await msg_author.send(f"✅ You have completed a quest: {quest.splitlines()[0]}!")
                except:
                    pass
                
                if len(quest_data["user_progress"][user_id]) == len(quest_data["quests"]):
                    role = reaction.message.guild.get_role(QUEST_COMPLETER_ROLE_ID)
                    if role:
                        member = reaction.message.guild.get_member(int(user_id))
                        try:
                            await member.add_roles(role)
                        except:
                            pass
            break

# ==================== TEAM DUEL SYSTEM ====================

# Global team duel state
active_team_duel = None
active_team_boss_battle = None

def calculate_team_members_hp(team_id):
    """Calculate HP for all team members based on their individual stats"""
    team = teams_data["teams"].get(team_id)
    if not team:
        return {}
    
    member_hp = {}
    for member_id in team["members"]:
        max_hp = calculate_max_hp(int(member_id))
        member_hp[member_id] = {
            "max_hp": max_hp,
            "current_hp": max_hp,
            "status": "active",  # active, defending, stunned, ko
            "defense_bonus": 0
        }
    
    return member_hp

@bot.command(name="teamduel")
async def teamduel(ctx, action_or_target = None):
    """Challenge another team to an RPG-style battle! (Leader only)
    
    Team leaders strategically command their members in turn-based combat.
    Choose who attacks, heals, defends, or uses special abilities!
    
    Usage:
    - P!teamduel @leader - Challenge a team
    - P!teamduel accept - Accept challenge
    - P!teamduel deny - Deny challenge
    """
    global active_team_duel
    
    # Handle accept/deny if there's an active challenge
    if active_team_duel and isinstance(action_or_target, str):
        action = action_or_target.lower()
        user_id = str(ctx.author.id)
        
        if action == "accept":
            # Must be challenged leader
            if ctx.author.id != active_team_duel["challenged_leader"]:
                await ctx.send("❌ Only the challenged team leader can accept!")
                return
            
            if active_team_duel["status"] != "pending":
                await ctx.send("❌ This challenge has already been responded to!")
                return
            
            active_team_duel["status"] = "active"
            
            challenger_team = teams_data["teams"][active_team_duel["challenger_team_id"]]
            challenged_team = teams_data["teams"][active_team_duel["challenged_team_id"]]
            challenger_leader = await bot.fetch_user(active_team_duel["challenger_leader"])
            
            # Build team roster display
            challenger_roster = ""
            for i, member_id in enumerate(challenger_team["members"], 1):
                member = await bot.fetch_user(int(member_id))
                hp_data = active_team_duel["challenger_members"][member_id]
                challenger_roster += f"{i}. {member.mention} - {hp_data['current_hp']}/{hp_data['max_hp']} HP\n"
            
            challenged_roster = ""
            for i, member_id in enumerate(challenged_team["members"], 1):
                member = await bot.fetch_user(int(member_id))
                hp_data = active_team_duel["challenged_members"][member_id]
                challenged_roster += f"{i}. {member.mention} - {hp_data['current_hp']}/{hp_data['max_hp']} HP\n"
            
            embed = discord.Embed(
                title="⚔️ TEAM BATTLE BEGINS!",
                description=f"**{challenger_team['name']}** vs **{challenged_team['name']}**\n\n"
                           f"Leaders command your teams to victory!",
                color=discord.Color.red()
            )
            embed.add_field(
                name=f"🔵 {challenger_team['name']}",
                value=challenger_roster,
                inline=True
            )
            embed.add_field(
                name=f"🔴 {challenged_team['name']}",
                value=challenged_roster,
                inline=True
            )
            embed.add_field(
                name="⚡ Turn",
                value=f"{challenger_leader.mention}'s turn to command!\n\nUse `P!tduel status` to see available commands!",
                inline=False
            )
            embed.set_footer(text="First team to eliminate all opponents wins!")
            await ctx.send(embed=embed)
            return
        
        elif action == "deny":
            # Must be challenged leader
            if ctx.author.id != active_team_duel["challenged_leader"]:
                await ctx.send("❌ Only the challenged team leader can deny!")
                return
            
            if active_team_duel["status"] != "pending":
                await ctx.send("❌ This challenge has already been responded to!")
                return
            
            challenger_team = teams_data["teams"][active_team_duel["challenger_team_id"]]
            challenged_team = teams_data["teams"][active_team_duel["challenged_team_id"]]
            
            await ctx.send(f"❌ **{challenged_team['name']}** declined the challenge from **{challenger_team['name']}**!")
            active_team_duel = None
            return
        
        # Invalid action for existing challenge
        await ctx.send("❌ Use `P!teamduel accept` or `P!teamduel deny` to respond to the challenge!")
        return
    
    # Handle new challenge
    target = action_or_target
    user_id = str(ctx.author.id)
    
    if not target or not isinstance(target, discord.Member):
        await ctx.send("❌ Usage: `P!teamduel @team_leader`\n"
                      "Challenge another team's leader to an epic team battle!")
        return
    
    # Check if user is in a team
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team! Create one with `P!team create <name>`")
        return
    
    challenger_team_id = teams_data["user_teams"][user_id]
    challenger_team = teams_data["teams"][challenger_team_id]
    
    # Check if user is team leader
    if challenger_team["leader"] != user_id:
        leader = await bot.fetch_user(int(challenger_team["leader"]))
        await ctx.send(f"❌ Only the team leader ({leader.mention}) can challenge other teams!")
        return
    
    # Check if there's already an active team duel
    if active_team_duel is not None:
        await ctx.send("⚔️ A team duel is already in progress! Please wait for it to finish.")
        return
    
    # Check if target is in a team
    target_id = str(target.id)
    if target_id not in teams_data["user_teams"]:
        await ctx.send(f"❌ {target.mention} is not in a team!")
        return
    
    challenged_team_id = teams_data["user_teams"][target_id]
    challenged_team = teams_data["teams"][challenged_team_id]
    
    # Check if target is team leader
    if challenged_team["leader"] != target_id:
        leader = await bot.fetch_user(int(challenged_team["leader"]))
        await ctx.send(f"❌ You must challenge the team leader ({leader.mention})!")
        return
    
    # Can't duel own team
    if challenger_team_id == challenged_team_id:
        await ctx.send("❌ You can't duel your own team!")
        return
    
    # Check minimum team size (at least 1 member each)
    if len(challenger_team["members"]) == 0 or len(challenged_team["members"]) == 0:
        await ctx.send("❌ Both teams need at least 1 member to duel!")
        return
    
    # Initialize team duel state
    active_team_duel = {
        "challenger_team_id": challenger_team_id,
        "challenged_team_id": challenged_team_id,
        "challenger_leader": ctx.author.id,
        "challenged_leader": target.id,
        "status": "pending",
        "start_time": datetime.utcnow(),
        "guild_id": ctx.guild.id,
        "channel_id": ctx.channel.id,
        "turn": "challenger",  # alternates between challenger/challenged
        "turn_count": 0,
        "challenger_members": calculate_team_members_hp(challenger_team_id),
        "challenged_members": calculate_team_members_hp(challenged_team_id),
        "action_log": []
    }
    
    # Send challenge embed
    embed = discord.Embed(
        title="⚔️ TEAM DUEL CHALLENGE!",
        description=f"**{challenger_team['name']}** challenges **{challenged_team['name']}** to an epic team battle!\n\n"
                   f"**{challenger_team['name']}** ({len(challenger_team['members'])} members)\n"
                   f"**Leader:** {ctx.author.mention}\n\n"
                   f"**{challenged_team['name']}** ({len(challenged_team['members'])} members)\n"
                   f"**Leader:** {target.mention}\n\n"
                   f"{target.mention}, use `P!teamduel accept` to accept or `P!teamduel deny` to decline!",
        color=discord.Color.orange()
    )
    embed.set_footer(text="Challenge expires in 2 minutes")
    await ctx.send(embed=embed)

@bot.command(name="tduel")
async def tduel_action(ctx, action: str = "", member_num: str = "", *, target_or_item: str = ""):
    """Team duel tactical commands - Leader strategically commands team members!
    
    Commands:
    - P!tduel status - View current battle status
    - P!tduel attack <member#> <target#> <weapon> - Member attacks enemy
    - P!tduel heal <member#> <item> - Heal team member
    - P!tduel defend <member#> - Member defends (50% damage reduction next turn)
    - P!tduel special <member#> <target#> - Use member's special ability
    - P!tduel forfeit - Surrender (leader only)
    """
    global active_team_duel
    
    if not active_team_duel or active_team_duel["status"] != "active":
        await ctx.send("❌ No active team duel! Use `P!teamduel @leader` to challenge a team.")
        return
    
    user_id = str(ctx.author.id)
    
    # Determine which team the user leads
    is_challenger_turn = active_team_duel["turn"] == "challenger"
    current_leader = active_team_duel["challenger_leader"] if is_challenger_turn else active_team_duel["challenged_leader"]
    
    if ctx.author.id != current_leader:
        await ctx.send("❌ It's not your turn to command! Wait for the other leader's action.")
        return
    
    action = action.lower()
    
    # Get team data
    challenger_team = teams_data["teams"][active_team_duel["challenger_team_id"]]
    challenged_team = teams_data["teams"][active_team_duel["challenged_team_id"]]
    my_team = challenger_team if is_challenger_turn else challenged_team
    enemy_team = challenged_team if is_challenger_turn else challenger_team
    my_members = active_team_duel["challenger_members"] if is_challenger_turn else active_team_duel["challenged_members"]
    enemy_members = active_team_duel["challenged_members"] if is_challenger_turn else active_team_duel["challenger_members"]
    
    if action == "status":
        # Display current battle status
        challenger_roster = ""
        for i, member_id in enumerate(challenger_team["members"], 1):
            member = await bot.fetch_user(int(member_id))
            hp_data = active_team_duel["challenger_members"][member_id]
            status_icon = "💀" if hp_data["status"] == "ko" else "🛡️" if hp_data["status"] == "defending" else "⚡"
            challenger_roster += f"{status_icon} {i}. {member.display_name} - **{hp_data['current_hp']}/{hp_data['max_hp']} HP** ({hp_data['status']})\n"
        
        challenged_roster = ""
        for i, member_id in enumerate(challenged_team["members"], 1):
            member = await bot.fetch_user(int(member_id))
            hp_data = active_team_duel["challenged_members"][member_id]
            status_icon = "💀" if hp_data["status"] == "ko" else "🛡️" if hp_data["status"] == "defending" else "⚡"
            challenged_roster += f"{status_icon} {i}. {member.display_name} - **{hp_data['current_hp']}/{hp_data['max_hp']} HP** ({hp_data['status']})\n"
        
        current_leader_user = await bot.fetch_user(current_leader)
        
        embed = discord.Embed(
            title=f"⚔️ TEAM BATTLE - Turn {active_team_duel['turn_count'] + 1}",
            description=f"**{challenger_team['name']}** vs **{challenged_team['name']}**",
            color=discord.Color.blue() if is_challenger_turn else discord.Color.red()
        )
        embed.add_field(
            name=f"🔵 {challenger_team['name']}",
            value=challenger_roster or "No members",
            inline=True
        )
        embed.add_field(
            name=f"🔴 {challenged_team['name']}",
            value=challenged_roster or "No members",
            inline=True
        )
        embed.add_field(
            name="⚡ Current Turn",
            value=f"{current_leader_user.mention}'s turn to command!",
            inline=False
        )
        
        if active_team_duel["action_log"]:
            recent_actions = "\n".join(active_team_duel["action_log"][-3:])
            embed.add_field(name="📜 Recent Actions", value=recent_actions, inline=False)
        
        embed.set_footer(text="Use P!tduel attack/heal/defend/special to command your team!")
        await ctx.send(embed=embed)
        return
    
    elif action == "attack":
        if not member_num or not target_or_item:
            await ctx.send("❌ Usage: `P!tduel attack <your_member#> <enemy#> <weapon>`\n"
                          "Example: `P!tduel attack 1 2 Bamboo Staff`")
            return
        
        try:
            attacker_index = int(member_num) - 1
            target_parts = target_or_item.split(maxsplit=1)
            target_index = int(target_parts[0]) - 1
            weapon_name = target_parts[1] if len(target_parts) > 1 else ""
        except (ValueError, IndexError):
            await ctx.send("❌ Invalid format! Use: `P!tduel attack <your_member#> <enemy#> <weapon>`")
            return
        
        # Validate attacker
        if attacker_index < 0 or attacker_index >= len(my_team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(my_team['members'])} members.")
            return
        
        attacker_id = my_team["members"][attacker_index]
        attacker_data = my_members[attacker_id]
        
        if attacker_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out and cannot act!")
            return
        
        # Validate target
        if target_index < 0 or target_index >= len(enemy_team["members"]):
            await ctx.send(f"❌ Invalid target number! Enemy team has {len(enemy_team['members'])} members.")
            return
        
        target_id = enemy_team["members"][target_index]
        target_data = enemy_members[target_id]
        
        if target_data["status"] == "ko":
            await ctx.send("❌ That enemy is already knocked out! Choose another target.")
            return
        
        # Find weapon
        if not weapon_name:
            await ctx.send("❌ You must specify a weapon! Example: `P!tduel attack 1 1 Bamboo Staff`")
            return
        
        user_items = chi_data.get(attacker_id, {}).get("purchased_items", [])
        weapon_found = None
        for item in chi_shop_data["items"]:
            if "weapon" in item.get("tags", []) and item["name"].lower() == weapon_name.lower():
                weapon_found = item
                break
        
        if not weapon_found:
            await ctx.send(f"❌ '{weapon_name}' is not a valid weapon!")
            return
        
        if weapon_found["name"] not in user_items:
            await ctx.send(f"❌ Member {member_num} doesn't own {weapon_found['name']}!")
            return
        
        # Calculate damage
        base_damage = weapon_found.get("damage", 20)
        attacker_level = get_user_level(int(attacker_id))
        damage = calculate_damage_with_level(base_damage, attacker_level, 1)
        
        # Apply defense bonus
        if target_data["status"] == "defending":
            damage = int(damage * 0.5)
            target_data["status"] = "active"  # Defense breaks after use
        
        target_data["current_hp"] -= damage
        
        attacker = await bot.fetch_user(int(attacker_id))
        target = await bot.fetch_user(int(target_id))
        
        action_text = f"⚔️ {attacker.display_name} attacks {target.display_name} with **{weapon_found['name']}** for **{damage} damage**!"
        
        # Check if target is KO'd
        if target_data["current_hp"] <= 0:
            target_data["current_hp"] = 0
            target_data["status"] = "ko"
            action_text += f"\n💀 **{target.display_name} has been knocked out!**"
        
        active_team_duel["action_log"].append(action_text)
        
        # Check for team victory
        enemy_alive = sum(1 for m in enemy_members.values() if m["status"] != "ko")
        if enemy_alive == 0:
            # Victory!
            winning_team = my_team
            losing_team = enemy_team
            
            # Distribute rewards
            chi_reward = 500 * len(winning_team["members"])
            for member_id in winning_team["members"]:
                if member_id in chi_data:
                    update_chi(int(member_id), chi_reward)
            
            # Update team stats
            winning_team["duel_stats"]["wins"] += 1
            winning_team["team_score"] += 100
            losing_team["duel_stats"]["losses"] += 1
            save_teams()
            save_data()
            
            embed = discord.Embed(
                title="🏆 VICTORY!",
                description=f"{action_text}\n\n"
                           f"**{winning_team['name']}** has won the team battle!\n\n"
                           f"**Rewards:**\n"
                           f"💰 {chi_reward:,} Chi per member\n"
                           f"🏆 +100 Team Score\n"
                           f"📊 Team Record: {winning_team['duel_stats']['wins']}W-{winning_team['duel_stats']['losses']}L",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            active_team_duel = None
            return
        
        # Switch turns
        active_team_duel["turn"] = "challenged" if is_challenger_turn else "challenger"
        active_team_duel["turn_count"] += 1
        
        next_leader = await bot.fetch_user(active_team_duel["challenged_leader"] if is_challenger_turn else active_team_duel["challenger_leader"])
        
        await ctx.send(f"{action_text}\n\n⚡ **{next_leader.mention}'s turn to command!**\nUse `P!tduel status` to see the battlefield.")
    
    elif action == "heal":
        if not member_num or not target_or_item:
            await ctx.send("❌ Usage: `P!tduel heal <member#> <item>`\n"
                          "Example: `P!tduel heal 2 Herbal Tea`")
            return
        
        try:
            target_index = int(member_num) - 1
            item_name = target_or_item
        except ValueError:
            await ctx.send("❌ Invalid member number!")
            return
        
        # Validate target
        if target_index < 0 or target_index >= len(my_team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(my_team['members'])} members.")
            return
        
        target_id = my_team["members"][target_index]
        target_data = my_members[target_id]
        
        if target_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out and cannot be healed!")
            return
        
        # Find healing item
        healing_item = None
        for item in chi_shop_data["items"]:
            if "healing" in item.get("tags", []) and item["name"].lower() == item_name.lower():
                healing_item = item
                break
        
        if not healing_item:
            await ctx.send(f"❌ '{item_name}' is not a valid healing item!")
            return
        
        # Check ownership (leader must have the item)
        leader_items = chi_data.get(user_id, {}).get("purchased_items", [])
        if healing_item["name"] not in leader_items:
            await ctx.send(f"❌ You don't own {healing_item['name']}!")
            return
        
        # Calculate healing
        base_healing = healing_item.get("healing", 50)
        healing = calculate_healing_with_level(base_healing, get_user_level(ctx.author.id), 1)
        
        old_hp = target_data["current_hp"]
        target_data["current_hp"] = min(target_data["current_hp"] + healing, target_data["max_hp"])
        actual_healing = target_data["current_hp"] - old_hp
        
        target = await bot.fetch_user(int(target_id))
        action_text = f"💚 {target.display_name} was healed with **{healing_item['name']}** for **{actual_healing} HP**!"
        
        active_team_duel["action_log"].append(action_text)
        
        # Switch turns
        active_team_duel["turn"] = "challenged" if is_challenger_turn else "challenger"
        active_team_duel["turn_count"] += 1
        
        next_leader = await bot.fetch_user(active_team_duel["challenged_leader"] if is_challenger_turn else active_team_duel["challenger_leader"])
        
        await ctx.send(f"{action_text}\n\n⚡ **{next_leader.mention}'s turn to command!**")
    
    elif action == "defend":
        if not member_num:
            await ctx.send("❌ Usage: `P!tduel defend <member#>`\n"
                          "Member will take 50% damage on next attack!")
            return
        
        try:
            defender_index = int(member_num) - 1
        except ValueError:
            await ctx.send("❌ Invalid member number!")
            return
        
        if defender_index < 0 or defender_index >= len(my_team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(my_team['members'])} members.")
            return
        
        defender_id = my_team["members"][defender_index]
        defender_data = my_members[defender_id]
        
        if defender_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out!")
            return
        
        defender_data["status"] = "defending"
        defender = await bot.fetch_user(int(defender_id))
        
        action_text = f"🛡️ {defender.display_name} takes a defensive stance! (50% damage reduction next turn)"
        active_team_duel["action_log"].append(action_text)
        
        # Switch turns
        active_team_duel["turn"] = "challenged" if is_challenger_turn else "challenger"
        active_team_duel["turn_count"] += 1
        
        next_leader = await bot.fetch_user(active_team_duel["challenged_leader"] if is_challenger_turn else active_team_duel["challenger_leader"])
        
        await ctx.send(f"{action_text}\n\n⚡ **{next_leader.mention}'s turn to command!**")
    
    elif action == "forfeit":
        winning_team = enemy_team
        losing_team = my_team
        
        # Update stats
        winning_team["duel_stats"]["wins"] += 1
        winning_team["team_score"] += 50
        losing_team["duel_stats"]["losses"] += 1
        losing_team["team_score"] = max(0, losing_team["team_score"] - 25)
        save_teams()
        
        await ctx.send(f"🏳️ **{my_team['name']}** has forfeited! **{enemy_team['name']}** wins by forfeit!")
        active_team_duel = None
    
    else:
        await ctx.send("❌ Invalid action! Use `P!tduel status`, `attack`, `heal`, `defend`, `special`, or `forfeit`")

# ==================== TEAM BOSS RAID SYSTEM ====================

# Team Boss Data - Scaled for team battles
TEAM_BOSS_DATA = {
    "guardian": {
        "name": "Ancient Bamboo Guardian",
        "emoji": "🌳",
        "base_hp": 2000,
        "hp_per_member": 500,  # Scales with team size
        "damage_min": 40,
        "damage_max": 120,
        "special": {
            "name": "Root Entangle",
            "description": "Stuns a random team member for 1 turn",
            "chance": 0.15
        },
        "rewards_per_member": {
            "chi": 1000,
            "artifact_chance": 0.25
        },
        "description": "A massive guardian of the ancient bamboo forests. Its roots pierce the earth itself!"
    },
    "titan": {
        "name": "Shadow Panda Titan",
        "emoji": "🐼",
        "base_hp": 3500,
        "hp_per_member": 750,
        "damage_min": 60,
        "damage_max": 180,
        "special": {
            "name": "Shadow Slash",
            "description": "Hits all team members for reduced damage",
            "aoe_multiplier": 0.6,
            "chance": 0.20
        },
        "rewards_per_member": {
            "chi": 2000,
            "artifact_chance": 0.35
        },
        "description": "A colossal shadow panda infused with dark chi energy. Only the strongest teams dare challenge it!"
    },
    "dragon": {
        "name": "Eternal Dragon Emperor",
        "emoji": "🐉",
        "base_hp": 5000,
        "hp_per_member": 1000,
        "damage_min": 80,
        "damage_max": 250,
        "special": {
            "name": "Dragon's Fury",
            "description": "Burns all team members for 3 turns",
            "burn_damage_per_turn": 50,
            "burn_turns": 3,
            "chance": 0.25
        },
        "rewards_per_member": {
            "chi": 3500,
            "artifact_chance": 0.50
        },
        "description": "The legendary dragon that guards the realm of eternal chi. Defeating it is the ultimate team achievement!"
    }
}

@bot.command(name="teamboss")
async def teamboss(ctx, boss_name: str = ""):
    """Challenge a boss as a team! (Leader only)
    
    Epic team-based PvE battles against scaled campaign bosses!
    
    Usage:
    - P!teamboss guardian - Fight the Ancient Bamboo Guardian
    - P!teamboss titan - Fight the Shadow Panda Titan  
    - P!teamboss dragon - Fight the Eternal Dragon Emperor
    """
    global active_team_boss_battle
    
    user_id = str(ctx.author.id)
    
    # Check if user is in a team
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You must be in a team to challenge bosses! Create one with `P!team create <name>`")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is team leader
    if team["leader"] != user_id:
        leader = await bot.fetch_user(int(team["leader"]))
        await ctx.send(f"❌ Only the team leader ({leader.mention}) can start boss raids!")
        return
    
    # Check if there's already an active boss battle
    if active_team_boss_battle is not None:
        await ctx.send("🐉 A team boss battle is already in progress! Finish it first.")
        return
    
    # Check if there's an active team duel
    if active_team_duel is not None:
        await ctx.send("⚔️ Your team is currently in a duel! Finish it before challenging a boss.")
        return
    
    if not boss_name:
        # Show boss list
        embed = discord.Embed(
            title="🐉 TEAM BOSS RAIDS",
            description="Challenge epic bosses as a team! The more members, the stronger the boss becomes.\n\n"
                       "**Available Bosses:**",
            color=discord.Color.purple()
        )
        
        for key, boss in TEAM_BOSS_DATA.items():
            team_size = len(team["members"])
            scaled_hp = boss["base_hp"] + (boss["hp_per_member"] * team_size)
            embed.add_field(
                name=f"{boss['emoji']} {boss['name']}",
                value=f"{boss['description']}\n"
                      f"**HP (for your team):** {scaled_hp:,}\n"
                      f"**Special:** {boss['special']['name']} - {boss['special']['description']}\n"
                      f"**Rewards:** {boss['rewards_per_member']['chi']:,} chi per member\n"
                      f"**Command:** `P!teamboss {key}`",
                inline=False
            )
        
        embed.set_footer(text=f"Your team: {team['name']} ({team_size} members)")
        await ctx.send(embed=embed)
        return
    
    # Validate boss name
    boss_name = boss_name.lower()
    if boss_name not in TEAM_BOSS_DATA:
        await ctx.send(f"❌ Invalid boss! Choose from: guardian, titan, dragon\nUse `P!teamboss` to see all bosses.")
        return
    
    boss_template = TEAM_BOSS_DATA[boss_name]
    team_size = len(team["members"])
    scaled_hp = boss_template["base_hp"] + (boss_template["hp_per_member"] * team_size)
    
    # Calculate team members HP
    team_members_hp = calculate_team_members_hp(team_id)
    
    # Initialize team boss battle
    active_team_boss_battle = {
        "team_id": team_id,
        "boss_key": boss_name,
        "boss_hp": scaled_hp,
        "boss_max_hp": scaled_hp,
        "team_members": team_members_hp,
        "turn_count": 0,
        "action_log": [],
        "status_effects": {},  # Track burns, stuns, etc per member
        "start_time": datetime.utcnow()
    }
    
    # Build team roster
    team_roster = ""
    for i, member_id in enumerate(team["members"], 1):
        member = await bot.fetch_user(int(member_id))
        hp_data = team_members_hp[member_id]
        team_roster += f"{i}. {member.mention} - {hp_data['current_hp']}/{hp_data['max_hp']} HP\n"
    
    embed = discord.Embed(
        title=f"{boss_template['emoji']} TEAM BOSS RAID BEGINS!",
        description=f"**{team['name']}** vs **{boss_template['name']}**\n\n"
                   f"*{boss_template['description']}*\n\n"
                   f"The boss scales with your team size - fight strategically!",
        color=discord.Color.dark_purple()
    )
    embed.add_field(
        name=f"👥 {team['name']} ({team_size} members)",
        value=team_roster,
        inline=True
    )
    embed.add_field(
        name=f"{boss_template['emoji']} {boss_template['name']}",
        value=f"**{scaled_hp:,} / {scaled_hp:,} HP**\n\n"
              f"⚡ **{boss_template['special']['name']}**\n"
              f"{boss_template['special']['description']}",
        inline=True
    )
    embed.add_field(
        name="⚡ Battle Start!",
        value=f"{ctx.author.mention}, it's your turn to command!\n\nUse `P!tboss status` to see commands!",
        inline=False
    )
    embed.set_footer(text="Defeat the boss before your team is wiped out!")
    await ctx.send(embed=embed)

@bot.command(name="tboss")
async def tboss_action(ctx, action: str = "", member_num: str = "", *, target_or_item: str = ""):
    """Team boss raid tactical commands - Lead your team to victory!
    
    Commands:
    - P!tboss status - View current battle status
    - P!tboss attack <member#> <weapon> - Member attacks boss
    - P!tboss heal <member#> <item> - Heal team member
    - P!tboss defend <member#> - Member defends (50% damage reduction next turn)
    - P!tboss forfeit - Flee from battle (no rewards)
    """
    global active_team_boss_battle
    
    if not active_team_boss_battle:
        await ctx.send("❌ No active team boss battle! Use `P!teamboss <boss>` to start one.")
        return
    
    user_id = str(ctx.author.id)
    team_id = active_team_boss_battle["team_id"]
    team = teams_data["teams"][team_id]
    
    # Only team leader can command
    if team["leader"] != user_id:
        leader = await bot.fetch_user(int(team["leader"]))
        await ctx.send(f"❌ Only the team leader ({leader.mention}) can command in boss battles!")
        return
    
    action = action.lower()
    boss_template = TEAM_BOSS_DATA[active_team_boss_battle["boss_key"]]
    team_members = active_team_boss_battle["team_members"]
    
    if action == "status":
        # Display current battle status
        team_roster = ""
        for i, member_id in enumerate(team["members"], 1):
            member = await bot.fetch_user(int(member_id))
            hp_data = team_members[member_id]
            status_icon = "💀" if hp_data["status"] == "ko" else "🛡️" if hp_data["status"] == "defending" else "🔥" if hp_data["status"] == "burning" else "⚡"
            
            status_text = hp_data["status"]
            if member_id in active_team_boss_battle["status_effects"]:
                effects = active_team_boss_battle["status_effects"][member_id]
                if "burn" in effects:
                    status_text += f" (🔥{effects['burn']} turns)"
                if "stun" in effects:
                    status_text += " (😵 stunned)"
            
            team_roster += f"{status_icon} {i}. {member.display_name} - **{hp_data['current_hp']}/{hp_data['max_hp']} HP** ({status_text})\n"
        
        embed = discord.Embed(
            title=f"{boss_template['emoji']} BOSS RAID - Turn {active_team_boss_battle['turn_count'] + 1}",
            description=f"**{team['name']}** vs **{boss_template['name']}**",
            color=discord.Color.dark_red()
        )
        embed.add_field(
            name=f"👥 {team['name']}",
            value=team_roster or "Team wiped!",
            inline=True
        )
        embed.add_field(
            name=f"{boss_template['emoji']} {boss_template['name']}",
            value=f"**{active_team_boss_battle['boss_hp']:,} / {active_team_boss_battle['boss_max_hp']:,} HP**\n\n"
                  f"⚡ {boss_template['special']['name']}",
            inline=True
        )
        
        if active_team_boss_battle["action_log"]:
            recent_actions = "\n".join(active_team_boss_battle["action_log"][-4:])
            embed.add_field(name="📜 Recent Actions", value=recent_actions, inline=False)
        
        embed.set_footer(text="Use P!tboss attack/heal/defend to command your team!")
        await ctx.send(embed=embed)
        return
    
    elif action == "attack":
        if not member_num or not target_or_item:
            await ctx.send("❌ Usage: `P!tboss attack <member#> <weapon>`\n"
                          "Example: `P!tboss attack 1 Bamboo Staff`")
            return
        
        try:
            attacker_index = int(member_num) - 1
            weapon_name = target_or_item
        except ValueError:
            await ctx.send("❌ Invalid member number!")
            return
        
        # Validate attacker
        if attacker_index < 0 or attacker_index >= len(team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(team['members'])} members.")
            return
        
        attacker_id = team["members"][attacker_index]
        attacker_data = team_members[attacker_id]
        
        if attacker_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out!")
            return
        
        # Check if stunned
        if attacker_id in active_team_boss_battle["status_effects"]:
            if "stun" in active_team_boss_battle["status_effects"][attacker_id]:
                del active_team_boss_battle["status_effects"][attacker_id]["stun"]
                await ctx.send("❌ That member is stunned and cannot act this turn!")
                return
        
        # Find weapon
        user_items = chi_data.get(attacker_id, {}).get("purchased_items", [])
        weapon_found = None
        for item in chi_shop_data["items"]:
            if "weapon" in item.get("tags", []) and item["name"].lower() == weapon_name.lower():
                weapon_found = item
                break
        
        if not weapon_found:
            await ctx.send(f"❌ '{weapon_name}' is not a valid weapon!")
            return
        
        if weapon_found["name"] not in user_items:
            await ctx.send(f"❌ Member {member_num} doesn't own {weapon_found['name']}!")
            return
        
        # Calculate damage
        base_damage = weapon_found.get("damage", 20)
        attacker_level = get_user_level(int(attacker_id))
        damage = calculate_damage_with_level(base_damage, attacker_level, 1)
        
        active_team_boss_battle["boss_hp"] -= damage
        
        attacker = await bot.fetch_user(int(attacker_id))
        action_text = f"⚔️ {attacker.display_name} attacks {boss_template['emoji']} **{boss_template['name']}** with **{weapon_found['name']}** for **{damage} damage**!"
        
        # Check if boss is defeated
        if active_team_boss_battle["boss_hp"] <= 0:
            active_team_boss_battle["boss_hp"] = 0
            
            # VICTORY! Distribute rewards
            chi_per_member = boss_template["rewards_per_member"]["chi"]
            artifact_chance = boss_template["rewards_per_member"]["artifact_chance"]
            
            total_chi = 0
            artifacts_earned = []
            
            for member_id in team["members"]:
                if member_id in chi_data:
                    update_chi(int(member_id), chi_per_member)
                    total_chi += chi_per_member
                    
                    # Artifact chance
                    if random.random() < artifact_chance:
                        # Generate random artifact for boss reward
                        tiers = list(ARTIFACT_CONFIG.keys())
                        weights = [ARTIFACT_CONFIG[t]["weight"] for t in tiers]
                        selected_tier = random.choices(tiers, weights=weights)[0]
                        
                        emoji_index = random.randint(0, len(ARTIFACT_CONFIG[selected_tier]["emojis"]) - 1)
                        selected_emoji = ARTIFACT_CONFIG[selected_tier]["emojis"][emoji_index]
                        selected_name = ARTIFACT_CONFIG[selected_tier]["names"][emoji_index]
                        artifact_id = f"{selected_tier}_{int(datetime.utcnow().timestamp())}"
                        
                        artifact = {
                            "id": artifact_id,
                            "tier": selected_tier,
                            "emoji": selected_emoji,
                            "name": selected_name
                        }
                        
                        if member_id not in chi_data:
                            chi_data[member_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": []}
                        if "artifacts" not in chi_data[member_id]:
                            chi_data[member_id]["artifacts"] = []
                        chi_data[member_id]["artifacts"].append(artifact)
                        artifacts_earned.append(f"{artifact['emoji']} **{artifact['name']}** (to <@{member_id}>)")
            
            # Update team stats
            team["team_score"] += 200
            if "boss_victories" not in team:
                team["boss_victories"] = {}
            if active_team_boss_battle["boss_key"] not in team["boss_victories"]:
                team["boss_victories"][active_team_boss_battle["boss_key"]] = 0
            team["boss_victories"][active_team_boss_battle["boss_key"]] += 1
            
            save_teams()
            save_data()
            
            embed = discord.Embed(
                title="🏆 BOSS DEFEATED!",
                description=f"{action_text}\n\n"
                           f"**{team['name']}** has defeated the **{boss_template['name']}**!\n\n"
                           f"**Team Rewards:**\n"
                           f"💰 {total_chi:,} Total Chi ({chi_per_member:,} per member)\n"
                           f"🏆 +200 Team Score\n"
                           f"📊 Boss Victories: {team.get('boss_victories', {}).get(active_team_boss_battle['boss_key'], 1)}",
                color=discord.Color.gold()
            )
            
            if artifacts_earned:
                embed.add_field(
                    name="🎁 Artifacts Earned!",
                    value="\n".join(artifacts_earned),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            active_team_boss_battle = None
            return
        
        active_team_boss_battle["action_log"].append(action_text)
        
        # BOSS TURN - Boss attacks back!
        boss_action = await execute_boss_turn(ctx, team, team_members, boss_template)
        
        # Check if team is wiped
        alive_members = sum(1 for m in team_members.values() if m["status"] != "ko")
        if alive_members == 0:
            # DEFEAT!
            team["team_score"] = max(0, team["team_score"] - 50)
            save_teams()
            
            embed = discord.Embed(
                title="💀 TEAM WIPED!",
                description=f"{boss_action}\n\n"
                           f"**{team['name']}** has been defeated by the **{boss_template['name']}**!\n\n"
                           f"**Penalty:** -50 Team Score\n\n"
                           f"*Grow stronger and return to challenge the boss again!*",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            active_team_boss_battle = None
            return
        
        active_team_boss_battle["turn_count"] += 1
        await ctx.send(f"{action_text}\n\n{boss_action}\n\n⚡ **Your turn to command!** Use `P!tboss status` to see the battlefield.")
    
    elif action == "heal":
        if not member_num or not target_or_item:
            await ctx.send("❌ Usage: `P!tboss heal <member#> <item>`\n"
                          "Example: `P!tboss heal 2 Herbal Tea`")
            return
        
        try:
            target_index = int(member_num) - 1
            item_name = target_or_item
        except ValueError:
            await ctx.send("❌ Invalid member number!")
            return
        
        if target_index < 0 or target_index >= len(team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(team['members'])} members.")
            return
        
        target_id = team["members"][target_index]
        target_data = team_members[target_id]
        
        if target_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out and cannot be healed!")
            return
        
        # Find healing item
        healing_item = None
        for item in chi_shop_data["items"]:
            if "healing" in item.get("tags", []) and item["name"].lower() == item_name.lower():
                healing_item = item
                break
        
        if not healing_item:
            await ctx.send(f"❌ '{item_name}' is not a valid healing item!")
            return
        
        # Check ownership (leader must have the item)
        leader_items = chi_data.get(user_id, {}).get("purchased_items", [])
        if healing_item["name"] not in leader_items:
            await ctx.send(f"❌ You don't own {healing_item['name']}!")
            return
        
        # Calculate healing
        base_healing = healing_item.get("healing", 50)
        healing = calculate_healing_with_level(base_healing, get_user_level(ctx.author.id), 1)
        
        old_hp = target_data["current_hp"]
        target_data["current_hp"] = min(target_data["current_hp"] + healing, target_data["max_hp"])
        actual_healing = target_data["current_hp"] - old_hp
        
        target = await bot.fetch_user(int(target_id))
        action_text = f"💚 {target.display_name} was healed with **{healing_item['name']}** for **{actual_healing} HP**!"
        active_team_boss_battle["action_log"].append(action_text)
        
        # BOSS TURN
        boss_action = await execute_boss_turn(ctx, team, team_members, boss_template)
        
        # Check if team is wiped
        alive_members = sum(1 for m in team_members.values() if m["status"] != "ko")
        if alive_members == 0:
            team["team_score"] = max(0, team["team_score"] - 50)
            save_teams()
            
            embed = discord.Embed(
                title="💀 TEAM WIPED!",
                description=f"{boss_action}\n\n**{team['name']}** has been defeated!\n\n**Penalty:** -50 Team Score",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            active_team_boss_battle = None
            return
        
        active_team_boss_battle["turn_count"] += 1
        await ctx.send(f"{action_text}\n\n{boss_action}\n\n⚡ **Your turn!**")
    
    elif action == "defend":
        if not member_num:
            await ctx.send("❌ Usage: `P!tboss defend <member#>`\n"
                          "Member will take 50% damage on next attack!")
            return
        
        try:
            defender_index = int(member_num) - 1
        except ValueError:
            await ctx.send("❌ Invalid member number!")
            return
        
        if defender_index < 0 or defender_index >= len(team["members"]):
            await ctx.send(f"❌ Invalid member number! Your team has {len(team['members'])} members.")
            return
        
        defender_id = team["members"][defender_index]
        defender_data = team_members[defender_id]
        
        if defender_data["status"] == "ko":
            await ctx.send("❌ That member is knocked out!")
            return
        
        defender_data["status"] = "defending"
        defender = await bot.fetch_user(int(defender_id))
        
        action_text = f"🛡️ {defender.display_name} takes a defensive stance!"
        active_team_boss_battle["action_log"].append(action_text)
        
        # BOSS TURN
        boss_action = await execute_boss_turn(ctx, team, team_members, boss_template)
        
        # Check if team is wiped
        alive_members = sum(1 for m in team_members.values() if m["status"] != "ko")
        if alive_members == 0:
            team["team_score"] = max(0, team["team_score"] - 50)
            save_teams()
            
            embed = discord.Embed(
                title="💀 TEAM WIPED!",
                description=f"{boss_action}\n\n**{team['name']}** has been defeated!\n\n**Penalty:** -50 Team Score",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            active_team_boss_battle = None
            return
        
        active_team_boss_battle["turn_count"] += 1
        await ctx.send(f"{action_text}\n\n{boss_action}\n\n⚡ **Your turn!**")
    
    elif action == "forfeit":
        team["team_score"] = max(0, team["team_score"] - 25)
        save_teams()
        
        await ctx.send(f"🏳️ **{team['name']}** has fled from the {boss_template['emoji']} **{boss_template['name']}**!\n**Penalty:** -25 Team Score")
        active_team_boss_battle = None
    
    else:
        await ctx.send("❌ Invalid action! Use `P!tboss status`, `attack`, `heal`, `defend`, or `forfeit`")

async def execute_boss_turn(ctx, team, team_members, boss_template):
    """Execute the boss's turn and return action text"""
    global active_team_boss_battle
    
    # Get alive members
    alive_members = [mid for mid, data in team_members.items() if data["status"] != "ko"]
    
    if not alive_members:
        return ""
    
    # Check for special ability
    special_triggered = random.random() < boss_template["special"]["chance"]
    
    if special_triggered:
        special_name = boss_template["special"]["name"]
        
        if "aoe_multiplier" in boss_template["special"]:
            # AoE attack - hits all members
            multiplier = boss_template["special"]["aoe_multiplier"]
            base_damage = random.randint(boss_template["damage_min"], boss_template["damage_max"])
            aoe_damage = int(base_damage * multiplier)
            
            hit_members = []
            for member_id in alive_members:
                member_data = team_members[member_id]
                damage = aoe_damage
                
                if member_data["status"] == "defending":
                    damage = int(damage * 0.5)
                    member_data["status"] = "active"
                
                member_data["current_hp"] -= damage
                member = await bot.fetch_user(int(member_id))
                
                if member_data["current_hp"] <= 0:
                    member_data["current_hp"] = 0
                    member_data["status"] = "ko"
                    hit_members.append(f"{member.display_name} ({damage} dmg - 💀 **KO!**)")
                else:
                    hit_members.append(f"{member.display_name} ({damage} dmg)")
            
            action_text = f"💥 {boss_template['emoji']} **{special_name}!** AoE attack hits the entire team!\n" + ", ".join(hit_members)
            
        elif "burn_damage_per_turn" in boss_template["special"]:
            # Burn all members
            for member_id in alive_members:
                if member_id not in active_team_boss_battle["status_effects"]:
                    active_team_boss_battle["status_effects"][member_id] = {}
                active_team_boss_battle["status_effects"][member_id]["burn"] = boss_template["special"]["burn_turns"]
                team_members[member_id]["status"] = "burning"
            
            action_text = f"🔥 {boss_template['emoji']} **{special_name}!** All team members are burning for {boss_template['special']['burn_turns']} turns!"
            
        elif "description" in boss_template["special"] and "stun" in boss_template["special"]["description"].lower():
            # Stun random member
            target_id = random.choice(alive_members)
            if target_id not in active_team_boss_battle["status_effects"]:
                active_team_boss_battle["status_effects"][target_id] = {}
            active_team_boss_battle["status_effects"][target_id]["stun"] = 1
            
            target = await bot.fetch_user(int(target_id))
            action_text = f"😵 {boss_template['emoji']} **{special_name}!** {target.display_name} is stunned for 1 turn!"
        else:
            # Default special - normal attack
            target_id = random.choice(alive_members)
            target_data = team_members[target_id]
            damage = random.randint(boss_template["damage_min"], boss_template["damage_max"])
            
            if target_data["status"] == "defending":
                damage = int(damage * 0.5)
                target_data["status"] = "active"
            
            target_data["current_hp"] -= damage
            target = await bot.fetch_user(int(target_id))
            
            if target_data["current_hp"] <= 0:
                target_data["current_hp"] = 0
                target_data["status"] = "ko"
                action_text = f"⚔️ {boss_template['emoji']} **{special_name}!** Hits {target.display_name} for **{damage} damage**! 💀 **KO!**"
            else:
                action_text = f"⚔️ {boss_template['emoji']} **{special_name}!** Hits {target.display_name} for **{damage} damage**!"
    else:
        # Normal attack - random target
        target_id = random.choice(alive_members)
        target_data = team_members[target_id]
        damage = random.randint(boss_template["damage_min"], boss_template["damage_max"])
        
        if target_data["status"] == "defending":
            damage = int(damage * 0.5)
            target_data["status"] = "active"
        
        target_data["current_hp"] -= damage
        target = await bot.fetch_user(int(target_id))
        
        if target_data["current_hp"] <= 0:
            target_data["current_hp"] = 0
            target_data["status"] = "ko"
            action_text = f"⚔️ {boss_template['emoji']} attacks {target.display_name} for **{damage} damage**! 💀 **KO!**"
        else:
            action_text = f"⚔️ {boss_template['emoji']} attacks {target.display_name} for **{damage} damage**!"
    
    # Process burn damage
    burn_texts = []
    for member_id in list(active_team_boss_battle["status_effects"].keys()):
        if "burn" in active_team_boss_battle["status_effects"][member_id]:
            if team_members[member_id]["status"] != "ko":
                burn_damage = boss_template["special"].get("burn_damage_per_turn", 0)
                team_members[member_id]["current_hp"] -= burn_damage
                member = await bot.fetch_user(int(member_id))
                
                if team_members[member_id]["current_hp"] <= 0:
                    team_members[member_id]["current_hp"] = 0
                    team_members[member_id]["status"] = "ko"
                    burn_texts.append(f"🔥 {member.display_name} takes {burn_damage} burn damage! 💀 **KO!**")
                else:
                    burn_texts.append(f"🔥 {member.display_name} takes {burn_damage} burn damage!")
                
                active_team_boss_battle["status_effects"][member_id]["burn"] -= 1
                if active_team_boss_battle["status_effects"][member_id]["burn"] <= 0:
                    del active_team_boss_battle["status_effects"][member_id]["burn"]
                    if team_members[member_id]["status"] == "burning":
                        team_members[member_id]["status"] = "active"
    
    if burn_texts:
        action_text += "\n" + "\n".join(burn_texts)
    
    active_team_boss_battle["action_log"].append(action_text)
    return action_text

# ==================== TEAM SYSTEM ====================

@bot.group(name="team", invoke_without_command=True)
async def team(ctx):
    """Team system commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("**🐼 Team System Commands**\n"
                      "`P!team create <name>` - Create a new team\n"
                      "`P!team info` - View your team info\n"
                      "`P!team list` - List all teams\n"
                      "`P!team invite @user` - Invite a member to your team (leader only)\n"
                      "`P!team invite accept` - Accept a pending team invite\n"
                      "`P!team invite deny` - Deny a pending team invite\n"
                      "`P!team add @user` - Add a member to your team (leader only)\n"
                      "`P!team remove @user` - Remove a member from your team (leader only)\n"
                      "`P!team members` - View team members\n"
                      "`P!team leave` - Leave your current team\n"
                      "`P!team disband` - Disband your team (leader only)\n"
                      "`P!team ally <add/remove> @team_leader` - Manage alliances (leader only)\n"
                      "`P!team enemy <add/remove> @team_leader` - Manage enemies (leader only)\n"
                      "`P!team base` - View your team base\n"
                      "`P!team base paint <color>` - Paint your base (leader only)\n"
                      "`P!team base decorate <item>` - Add decorations to your base\n"
                      "`P!team base gym <equipment>` - Add gym equipment\n"
                      "`P!team upgrade <base/gym/arena> [module]` - Upgrade team facilities\n"
                      "`P!team leaderboard` - View team leaderboard (admin only)\n"
                      "`P!team event <name>` - Start a team event (admin only)\n"
                      "`P!team register <event>` - Register for active event (leader only)")

@team.command(name="create")
async def team_create(ctx, *, team_name: str):
    """Create a new team"""
    user_id = str(ctx.author.id)
    
    # Check if user already in a team
    if user_id in teams_data["user_teams"]:
        await ctx.send("❌ You're already in a team! Leave your current team first with `P!team leave`")
        return
    
    # Check if team name already exists
    for team_id, team in teams_data["teams"].items():
        if team["name"].lower() == team_name.lower():
            await ctx.send(f"❌ A team with the name '{team_name}' already exists!")
            return
    
    # Create team
    team_id = str(len(teams_data["teams"]) + 1)
    teams_data["teams"][team_id] = {
        "name": team_name,
        "leader": user_id,
        "members": [user_id],
        "created_at": datetime.utcnow().isoformat(),
        "base_tier": "solo",
        "base_color": "white",
        "base_modules": {
            "training_area": 0,
            "armory": 0,
            "garden": 0
        },
        "decorations": [],
        "gym_equipment": [],
        "gym_level": 0,
        "arena_level": 0,
        "duel_stats": {
            "wins": 0,
            "losses": 0,
            "ties": 0
        },
        "team_chi": 0,
        "team_score": 0,
        "allies": [],
        "enemies": []
    }
    teams_data["user_teams"][user_id] = team_id
    save_teams()
    
    # Log team creation
    await log_event(
        "Team Created",
        f"**Team:** {team_name}\n**Leader:** {ctx.author.mention} ({ctx.author.name})\n**Team ID:** {team_id}", ctx.guild, discord.Color.green())
    
    # Auto-complete tutorial quest 2: Create or join a team
    await auto_complete_tutorial_quest(ctx.author.id, 2, ctx.channel)
    
    embed = discord.Embed(title="🏰 Team Created!", color=discord.Color.green())
    embed.add_field(name="Team Name", value=team_name, inline=False)
    embed.add_field(name="Leader", value=ctx.author.mention, inline=False)
    embed.add_field(name="Base Tier", value="Solo Base", inline=False)
    embed.set_footer(text="Use P!team add @user to invite members!")
    await ctx.send(embed=embed)

@team.command(name="info")
async def team_info(ctx):
    """View your team information"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team! Create one with `P!team create <name>`")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Initialize missing fields for legacy teams
    if "base_modules" not in team:
        team["base_modules"] = {"training_area": 0, "armory": 0, "garden": 0}
    if "gym_level" not in team:
        team["gym_level"] = 0
    if "arena_level" not in team:
        team["arena_level"] = 0
    if "duel_stats" not in team:
        team["duel_stats"] = {"wins": 0, "losses": 0, "ties": 0}
    if "team_chi" not in team:
        team["team_chi"] = 0
    
    # Get leader
    leader = await bot.fetch_user(int(team["leader"]))
    
    # Get member count
    member_count = len(team["members"])
    
    # Determine base tier
    base_tier = "Team Base (up to 20 members)" if member_count > 1 else "Solo Base"
    
    embed = discord.Embed(title=f"🏰 {team['name']}", color=discord.Color.blue())
    embed.add_field(name="Leader", value=leader.mention, inline=True)
    embed.add_field(name="Members", value=f"{member_count}/20", inline=True)
    embed.add_field(name="Team Chi", value=f"✨ {team['team_chi']}", inline=True)
    
    embed.add_field(name="\u200b", value="**📊 Duel Stats**", inline=False)
    embed.add_field(name="Wins", value=f"🏆 {team['duel_stats']['wins']}", inline=True)
    embed.add_field(name="Losses", value=f"💔 {team['duel_stats']['losses']}", inline=True)
    embed.add_field(name="Ties", value=f"🤝 {team['duel_stats']['ties']}", inline=True)
    
    embed.add_field(name="\u200b", value="**🏛️ Facilities**", inline=False)
    embed.add_field(name="Base Tier", value=base_tier, inline=False)
    embed.add_field(name="Training Area", value=f"Level {team['base_modules']['training_area']}", inline=True)
    embed.add_field(name="Armory", value=f"Level {team['base_modules']['armory']}", inline=True)
    embed.add_field(name="Garden", value=f"Level {team['base_modules']['garden']}", inline=True)
    embed.add_field(name="Gym", value=f"Level {team['gym_level']}", inline=True)
    embed.add_field(name="Arena", value=f"Level {team['arena_level']}", inline=True)
    
    # Add interactive buttons for team management
    is_leader = str(ctx.author.id) == team["leader"]
    team_view = TeamView(team_id, is_leader, ctx.author.id)
    message = await ctx.send(embed=embed, view=team_view)
    team_view.message = message

@team.command(name="list")
async def team_list(ctx):
    """List all teams"""
    if not teams_data["teams"]:
        await ctx.send("❌ No teams have been created yet!")
        return
    
    embed = discord.Embed(title="🏰 All Teams", color=discord.Color.gold())
    
    for team_id, team in teams_data["teams"].items():
        leader = await bot.fetch_user(int(team["leader"]))
        member_count = len(team["members"])
        wins = team["duel_stats"]["wins"]
        
        embed.add_field(
            name=f"{team['name']}",
            value=f"Leader: {leader.name}\nMembers: {member_count}/20\nWins: {wins}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@team.command(name="invite")
async def team_invite(ctx, member: discord.Member = None, action: str = ""):
    """Invite system - Send/accept/deny team invites"""
    user_id = str(ctx.author.id)
    
    # Handle when member parameter is actually the action word
    if member and not action:
        # Check if "member" is actually "accept" or "deny"
        member_str = str(member).lower()
        if member_str in ["accept", "deny"]:
            action = member_str
            member = None
    
    # Case 1: Accept invite
    if action == "accept" or (not member and ctx.message.content.lower().endswith("accept")):
        if user_id not in teams_data["pending_invites"]:
            await ctx.send("❌ You don't have any pending team invites!")
            return
        
        team_id = teams_data["pending_invites"][user_id]
        team = teams_data["teams"][team_id]
        
        # Check if team still exists
        if team_id not in teams_data["teams"]:
            del teams_data["pending_invites"][user_id]
            save_teams()
            await ctx.send("❌ That team no longer exists!")
            return
        
        # Check if team is full
        if len(team["members"]) >= 20:
            del teams_data["pending_invites"][user_id]
            save_teams()
            await ctx.send(f"❌ **{team['name']}** is full! (Maximum 20 members)")
            return
        
        # Check if user is already in a team
        if user_id in teams_data["user_teams"]:
            del teams_data["pending_invites"][user_id]
            save_teams()
            await ctx.send("❌ You're already in a team! Leave your current team first.")
            return
        
        # Add member to team
        team["members"].append(user_id)
        teams_data["user_teams"][user_id] = team_id
        
        # Update base tier if needed
        if len(team["members"]) > 1:
            team["base_tier"] = "team"
        
        # Clear invite
        del teams_data["pending_invites"][user_id]
        save_teams()
        
        # Get leader for notification
        leader = await bot.fetch_user(int(team["leader"]))
        
        # Log team join
        await log_event(
            "Team Member Joined",
            f"**Team:** {team['name']}\n**New Member:** {ctx.author.mention} ({ctx.author.name})\n**Total Members:** {len(team['members'])}/20", ctx.guild, discord.Color.green())
        
        # Auto-complete tutorial quest 2: Join a team
        await auto_complete_tutorial_quest(ctx.author.id, 2, ctx.channel)
        
        await ctx.send(f"✅ You've joined **{team['name']}**! 🎉\nTeam Leader: {leader.mention}")
        return
    
    # Case 2: Deny invite
    if action == "deny" or (not member and ctx.message.content.lower().endswith("deny")):
        if user_id not in teams_data["pending_invites"]:
            await ctx.send("❌ You don't have any pending team invites!")
            return
        
        team_id = teams_data["pending_invites"][user_id]
        team = teams_data["teams"].get(team_id, {"name": "Unknown Team"})
        
        del teams_data["pending_invites"][user_id]
        save_teams()
        
        await ctx.send(f"❌ You declined the invitation from **{team['name']}**")
        return
    
    # Case 3: Send invite (leader only)
    if member:
        
        # Check if sender is in a team
        if user_id not in teams_data["user_teams"]:
            await ctx.send("❌ You're not in a team!")
            return
        
        team_id = teams_data["user_teams"][user_id]
        team = teams_data["teams"][team_id]
        
        # Check if user is leader
        if team["leader"] != user_id:
            await ctx.send("❌ Only the team leader can send invites!")
            return
        
        # Check if team is full
        if len(team["members"]) >= 20:
            await ctx.send("❌ Your team is full! (Maximum 20 members)")
            return
        
        # Check if member is already in a team
        member_id = str(member.id)
        if member_id in teams_data["user_teams"]:
            await ctx.send(f"❌ {member.display_name} is already in a team!")
            return
        
        # Check if member already has a pending invite
        if member_id in teams_data["pending_invites"]:
            existing_team_id = teams_data["pending_invites"][member_id]
            existing_team = teams_data["teams"].get(existing_team_id, {"name": "Unknown Team"})
            await ctx.send(f"❌ {member.display_name} already has a pending invite from **{existing_team['name']}**!")
            return
        
        # Send invite
        teams_data["pending_invites"][member_id] = team_id
        save_teams()
        
        # Notify invitee
        try:
            invite_embed = discord.Embed(
                title="🎉 Team Invitation!",
                description=f"You've been invited to join **{team['name']}**!",
                color=discord.Color.blue()
            )
            invite_embed.add_field(name="Team Leader", value=ctx.author.mention, inline=False)
            invite_embed.add_field(name="Current Members", value=f"{len(team['members'])}/20", inline=False)
            invite_embed.add_field(
                name="How to Respond",
                value=f"`P!team invite accept` - Join the team\n`P!team invite deny` - Decline invitation",
                inline=False
            )
            await member.send(embed=invite_embed)
        except:
            pass
        
        await ctx.send(f"✅ Invitation sent to {member.mention}!\n💌 They can accept with `P!team invite accept`")
        
        # Log invite
        await log_event(
            "Team Invite Sent",
            f"**Team:** {team['name']}\n**Invited:** {member.mention} ({member.name})\n**By:** {ctx.author.mention}", ctx.guild, discord.Color.blue())
        return
    
    # Invalid usage
    await ctx.send(
        "**🎫 Team Invite System**\n\n"
        "**Send invite (leader only):**\n"
        "`P!team invite @user`\n\n"
        "**Accept invite:**\n"
        "`P!team invite accept`\n\n"
        "**Deny invite:**\n"
        "`P!team invite deny`"
    )

@team.command(name="add")
async def team_add(ctx, member: discord.Member):
    """Add a member to your team (leader only)"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is leader
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can add members!")
        return
    
    # Check if team is full
    if len(team["members"]) >= 20:
        await ctx.send("❌ Your team is full! (Maximum 20 members)")
        return
    
    # Check if member is already in a team
    member_id = str(member.id)
    if member_id in teams_data["user_teams"]:
        await ctx.send(f"❌ {member.display_name} is already in a team!")
        return
    
    # Add member
    team["members"].append(member_id)
    teams_data["user_teams"][member_id] = team_id
    
    # Update base tier if needed
    if len(team["members"]) > 1:
        team["base_tier"] = "team"
    
    save_teams()
    
    # Log team join
    await log_event(
        "Team Member Added",
        f"**Team:** {team['name']}\n**New Member:** {member.mention} ({member.name})\n**Added by:** {ctx.author.mention}\n**Total Members:** {len(team['members'])}/20", ctx.guild, discord.Color.blue())
    
    await ctx.send(f"✅ {member.mention} has been added to **{team['name']}**! 🎉")

@team.command(name="remove")
async def team_remove(ctx, member: discord.Member):
    """Remove a member from your team (leader only)"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is leader
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can remove members!")
        return
    
    member_id = str(member.id)
    
    # Can't remove self (use leave or disband instead)
    if member_id == user_id:
        await ctx.send("❌ Use `P!team leave` or `P!team disband` instead!")
        return
    
    # Check if member is in the team
    if member_id not in team["members"]:
        await ctx.send(f"❌ {member.display_name} is not in your team!")
        return
    
    # Remove member
    team["members"].remove(member_id)
    del teams_data["user_teams"][member_id]
    
    # Update base tier if needed
    if len(team["members"]) == 1:
        team["base_tier"] = "solo"
    
    save_teams()
    
    await ctx.send(f"✅ {member.display_name} has been removed from **{team['name']}**")

@team.command(name="members")
async def team_members(ctx):
    """View team members"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    embed = discord.Embed(title=f"👥 {team['name']} Members", color=discord.Color.purple())
    
    for i, member_id in enumerate(team["members"], 1):
        member = await bot.fetch_user(int(member_id))
        role = "👑 Leader" if member_id == team["leader"] else "👤 Member"
        embed.add_field(name=f"{i}. {member.name}", value=role, inline=False)
    
    embed.set_footer(text=f"{len(team['members'])}/20 members")
    await ctx.send(embed=embed)

@team.command(name="leave")
async def team_leave(ctx):
    """Leave your current team"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    team_name = team["name"]
    
    # If user is leader, transfer leadership or disband
    if team["leader"] == user_id:
        if len(team["members"]) > 1:
            # Transfer leadership to next member
            if user_id in team["members"]:
                team["members"].remove(user_id)
            team["leader"] = team["members"][0]
            del teams_data["user_teams"][user_id]
            
            new_leader = await bot.fetch_user(int(team["leader"]))
            
            # Update base tier if needed
            if len(team["members"]) == 1:
                team["base_tier"] = "solo"
            
            save_teams()
            
            await ctx.send(f"✅ You've left **{team_name}**. Leadership transferred to {new_leader.mention}")
        else:
            # Disband team
            del teams_data["teams"][team_id]
            del teams_data["user_teams"][user_id]
            save_teams()
            
            await ctx.send(f"✅ You've left and disbanded **{team_name}**")
    else:
        # Regular member leaving
        if user_id in team["members"]:
            team["members"].remove(user_id)
        del teams_data["user_teams"][user_id]
        
        # Update base tier if needed
        if len(team["members"]) == 1:
            team["base_tier"] = "solo"
        
        save_teams()
        
        await ctx.send(f"✅ You've left **{team_name}**")

@team.command(name="disband")
async def team_disband(ctx):
    """Disband your team (leader only)"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is leader
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can disband the team!")
        return
    
    team_name = team["name"]
    
    # Remove all members from user_teams
    for member_id in team["members"]:
        if member_id in teams_data["user_teams"]:
            del teams_data["user_teams"][member_id]
    
    # Delete team
    del teams_data["teams"][team_id]
    save_teams()
    
    await ctx.send(f"💥 **{team_name}** has been disbanded!")

@team.command(name="ally")
async def team_ally(ctx, action: str = "", target: discord.Member = None):
    """Manage team alliances (leader only)
    Usage: P!team ally <add/remove> @team_leader
    Allied teams can train together but cannot duel each other
    """
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can manage alliances!")
        return
    
    if not action or not target:
        await ctx.send("❌ Usage: `P!team ally <add/remove> @team_leader`\n"
                      "Allied teams can train together but cannot duel each other.")
        return
    
    action = action.lower()
    target_id = str(target.id)
    
    if target_id not in teams_data["user_teams"]:
        await ctx.send(f"❌ {target.mention} is not in a team!")
        return
    
    target_team_id = teams_data["user_teams"][target_id]
    target_team = teams_data["teams"][target_team_id]
    
    if target_team_id == team_id:
        await ctx.send("❌ You can't ally with your own team!")
        return
    
    if action == "add":
        if target_team_id in team["allies"]:
            await ctx.send(f"❌ You're already allied with **{target_team['name']}**!")
            return
        
        # Add alliance (bidirectional)
        team["allies"].append(target_team_id)
        target_team["allies"].append(team_id)
        
        # Remove from enemies if present
        if target_team_id in team["enemies"]:
            team["enemies"].remove(target_team_id)
        if team_id in target_team["enemies"]:
            target_team["enemies"].remove(team_id)
        
        save_teams()
        
        await ctx.send(f"🤝 **{team['name']}** and **{target_team['name']}** are now allies!\n"
                      f"✅ Members can train together\n"
                      f"❌ Members cannot duel each other")
    
    elif action == "remove":
        if target_team_id not in team["allies"]:
            await ctx.send(f"❌ You're not allied with **{target_team['name']}**!")
            return
        
        # Remove alliance (bidirectional)
        team["allies"].remove(target_team_id)
        target_team["allies"].remove(team_id)
        save_teams()
        
        await ctx.send(f"💔 **{team['name']}** and **{target_team['name']}** are no longer allies!")
    
    else:
        await ctx.send("❌ Invalid action! Use `add` or `remove`")

@team.command(name="enemy")
async def team_enemy(ctx, action: str = "", target: discord.Member = None):
    """Manage team enemies (leader only)
    Usage: P!team enemy <add/remove> @team_leader
    Enemy teams can always duel but cannot train together
    """
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can declare enemies!")
        return
    
    if not action or not target:
        await ctx.send("❌ Usage: `P!team enemy <add/remove> @team_leader`\n"
                      "Enemy teams can always duel but cannot train together.")
        return
    
    action = action.lower()
    target_id = str(target.id)
    
    if target_id not in teams_data["user_teams"]:
        await ctx.send(f"❌ {target.mention} is not in a team!")
        return
    
    target_team_id = teams_data["user_teams"][target_id]
    target_team = teams_data["teams"][target_team_id]
    
    if target_team_id == team_id:
        await ctx.send("❌ You can't be enemies with your own team!")
        return
    
    if action == "add":
        if target_team_id in team["enemies"]:
            await ctx.send(f"❌ You're already enemies with **{target_team['name']}**!")
            return
        
        # Add enemy relationship (bidirectional)
        team["enemies"].append(target_team_id)
        target_team["enemies"].append(team_id)
        
        # Remove from allies if present
        if target_team_id in team["allies"]:
            team["allies"].remove(target_team_id)
        if team_id in target_team["allies"]:
            target_team["allies"].remove(team_id)
        
        save_teams()
        
        await ctx.send(f"⚔️ **{team['name']}** and **{target_team['name']}** are now enemies!\n"
                      f"✅ Members can always duel each other\n"
                      f"❌ Members cannot train together")
    
    elif action == "remove":
        if target_team_id not in team["enemies"]:
            await ctx.send(f"❌ You're not enemies with **{target_team['name']}**!")
            return
        
        # Remove enemy relationship (bidirectional)
        team["enemies"].remove(target_team_id)
        target_team["enemies"].remove(team_id)
        save_teams()
        
        await ctx.send(f"🕊️ **{team['name']}** and **{target_team['name']}** are no longer enemies!")
    
    else:
        await ctx.send("❌ Invalid action! Use `add` or `remove`")

@team.command(name="upgrade")
async def team_upgrade(ctx, facility: str, module: str = None):
    """Upgrade team facilities using duel wins"""
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is leader
    if team["leader"] != user_id:
        await ctx.send("❌ Only the team leader can upgrade facilities!")
        return
    
    facility = facility.lower()
    wins = team["duel_stats"]["wins"]
    
    # Base module upgrades
    if facility == "base":
        if module is None:
            await ctx.send("❌ Please specify a module: `training_area`, `armory`, or `garden`\n"
                          "Example: `P!team upgrade base training_area`")
            return
        
        module = module.lower()
        if module not in ["training_area", "armory", "garden"]:
            await ctx.send("❌ Invalid module! Choose: `training_area`, `armory`, or `garden`")
            return
        
        current_level = team["base_modules"][module]
        cost = (current_level + 1) * 5  # 5 wins for level 1, 10 for level 2, etc.
        
        if wins < cost:
            await ctx.send(f"❌ Not enough duel wins! Need {cost} wins, have {wins}")
            return
        
        team["base_modules"][module] += 1
        team["duel_stats"]["wins"] -= cost
        save_teams()
        
        module_name = module.replace("_", " ").title()
        await ctx.send(f"✅ **{module_name}** upgraded to Level {team['base_modules'][module]}!\n"
                      f"Cost: {cost} duel wins\nRemaining wins: {team['duel_stats']['wins']}")
    
    # Gym upgrades
    elif facility == "gym":
        current_level = team["gym_level"]
        cost = (current_level + 1) * 10  # 10 wins for level 1, 20 for level 2, etc.
        
        if wins < cost:
            await ctx.send(f"❌ Not enough duel wins! Need {cost} wins, have {wins}")
            return
        
        team["gym_level"] += 1
        team["duel_stats"]["wins"] -= cost
        save_teams()
        
        await ctx.send(f"✅ **Gym** upgraded to Level {team['gym_level']}!\n"
                      f"Cost: {cost} duel wins\nRemaining wins: {team['duel_stats']['wins']}")
    
    # Arena upgrades
    elif facility == "arena":
        current_level = team["arena_level"]
        cost = (current_level + 1) * 15  # 15 wins for level 1, 30 for level 2, etc.
        
        if wins < cost:
            await ctx.send(f"❌ Not enough duel wins! Need {cost} wins, have {wins}")
            return
        
        team["arena_level"] += 1
        team["duel_stats"]["wins"] -= cost
        save_teams()
        
        await ctx.send(f"✅ **Arena** upgraded to Level {team['arena_level']}!\n"
                      f"Cost: {cost} duel wins\nRemaining wins: {team['duel_stats']['wins']}")
    
    else:
        await ctx.send("❌ Invalid facility! Choose: `base`, `gym`, or `arena`")

@team.command(name="base")
async def team_base(ctx, action: str = "", *, args: str = ""):
    """Manage your team base
    Usage:
    - P!team base view - View your base
    - P!team base paint <color> - Paint your base (leader only)
    - P!team base decorate <item> - Add decoration to your base
    """
    user_id = str(ctx.author.id)
    
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team!")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Ensure backward compatibility with old teams
    if "base_color" not in team:
        team["base_color"] = "white"
    if "decorations" not in team:
        team["decorations"] = []
    if "gym_equipment" not in team:
        team["gym_equipment"] = []
    if "team_score" not in team:
        team["team_score"] = 0
    
    if not action or action == "view":
        # Display base
        embed = discord.Embed(
            title=f"🏰 {team['name']}'s Base",
            description=f"A cozy {team['base_color']} base for your team!",
            color=discord.Color.from_str(f"#{team.get('base_color', 'white').lower().replace('white', 'ffffff').replace('red', 'ff0000').replace('blue', '0000ff').replace('green', '00ff00').replace('yellow', 'ffff00').replace('purple', '800080').replace('orange', 'ffa500').replace('pink', 'ffc0cb').replace('black', '000000')}" if team.get('base_color', 'white') in ['white', 'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'black'] else "#ffffff")
        )
        
        embed.add_field(name="🎨 Base Color", value=team['base_color'].title(), inline=True)
        embed.add_field(name="👥 Members", value=f"{len(team['members'])}/20", inline=True)
        embed.add_field(name="⭐ Team Score", value=team.get('team_score', 0), inline=True)
        
        if team['decorations']:
            decorations_str = ", ".join(team['decorations'])
            embed.add_field(name="🪑 Decorations", value=decorations_str, inline=False)
        else:
            embed.add_field(name="🪑 Decorations", value="None - buy some from P!cshop!", inline=False)
        
        if team['gym_equipment']:
            equipment_str = ", ".join(team['gym_equipment'])
            embed.add_field(name="💪 Gym Equipment", value=equipment_str, inline=False)
        else:
            embed.add_field(name="💪 Gym Equipment", value="None - buy some from P!cshop!", inline=False)
        
        embed.set_footer(text="Use P!team base paint <color> to change color • P!team base decorate <item> to add items")
        await ctx.send(embed=embed)
        return
    
    if action == "paint":
        # Check if user is leader
        if team["leader"] != user_id:
            await ctx.send("❌ Only the team leader can paint the base!")
            return
        
        if not args:
            await ctx.send("❌ Please specify a color!\nAvailable colors: white, red, blue, green, yellow, purple, orange, pink, black")
            return
        
        color = args.lower()
        allowed_colors = ["white", "red", "blue", "green", "yellow", "purple", "orange", "pink", "black"]
        
        if color not in allowed_colors:
            await ctx.send(f"❌ Invalid color! Available colors: {', '.join(allowed_colors)}")
            return
        
        team["base_color"] = color
        save_teams()
        
        await ctx.send(f"🎨 Base successfully painted {color}! Use `P!team base view` to see it!")
        return
    
    if action == "decorate":
        if not args:
            await ctx.send("❌ Please specify an item to add!\nAvailable: Couch (25 chi), Flower Seeds (50 chi), TV (100 chi), Bed (150 chi)")
            return
        
        item_name = args
        
        # Find the item in chi shop
        item_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == item_name.lower() and "decoration" in item.get("tags", []):
                item_found = item
                break
        
        if not item_found:
            await ctx.send(f"❌ '{item_name}' is not a valid decoration item! Check `P!cshop`")
            return
        
        # Check if user owns the item
        if item_found["name"] not in chi_data.get(user_id, {}).get("purchased_items", []):
            await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop` first.")
            return
        
        # Check if item is already in base
        if item_found["name"] in team["decorations"]:
            await ctx.send(f"❌ Your base already has a {item_found['name']}!")
            return
        
        # Add decoration to base (and remove from user's inventory since it's now in the base)
        team["decorations"].append(item_found["name"])
        chi_data[user_id]["purchased_items"].remove(item_found["name"])
        save_teams()
        save_data()
        
        await ctx.send(f"✨ Added {item_found['name']} to your team base! Use `P!team base view` to see it!")
        return
    
    if action == "gym":
        if not args:
            await ctx.send("❌ Please specify gym equipment to add!\nAvailable: Treadmill (50 chi), Weight Bench (75 chi), Punching Bag (100 chi)")
            return
        
        item_name = args
        
        # Find the item in chi shop
        item_found = None
        for item in chi_shop_data["items"]:
            if item["name"].lower() == item_name.lower() and "gym" in item.get("tags", []):
                item_found = item
                break
        
        if not item_found:
            await ctx.send(f"❌ '{item_name}' is not valid gym equipment! Check `P!cshop`")
            return
        
        # Check if user owns the item
        if item_found["name"] not in chi_data.get(user_id, {}).get("purchased_items", []):
            await ctx.send(f"❌ You don't own {item_found['name']}! Buy it from `P!cshop` first.")
            return
        
        # Check if item is already in gym
        if item_found["name"] in team["gym_equipment"]:
            await ctx.send(f"❌ Your gym already has a {item_found['name']}!")
            return
        
        # Add equipment to gym
        team["gym_equipment"].append(item_found["name"])
        chi_data[user_id]["purchased_items"].remove(item_found["name"])
        save_teams()
        save_data()
        
        await ctx.send(f"💪 Added {item_found['name']} to your team gym! Use `P!team base view` to see it!")
        return
    
    if action == "train":
        if not args:
            await ctx.send("❌ Please specify equipment to train with!\nAvailable: Punching Bag, Treadmill, Weight Bench")
            return
        
        equipment = args.title()  # Normalize to title case
        
        # Check if team has this equipment
        if equipment not in team["gym_equipment"]:
            await ctx.send(f"❌ Your team gym doesn't have a {equipment}! Add it with `P!team base gym <equipment>`")
            return
        
        # Equipment-specific cooldowns and bonuses
        equipment_config = {
            "Punching Bag": {"cooldown": 1800, "bonus_type": "melee_strength", "bonus_amount": 1.0, "emoji": "🥊"},  # 30 min
            "Treadmill": {"cooldown": 900, "bonus_type": "speed", "bonus_amount": 1.5, "emoji": "🏃"},  # 15 min
            "Weight Bench": {"cooldown": 600, "bonus_type": "range_strength", "bonus_amount": 2.0, "emoji": "🏋️"}  # 10 min
        }
        
        if equipment not in equipment_config:
            await ctx.send("❌ Invalid equipment! Choose: Punching Bag, Treadmill, or Weight Bench")
            return
        
        config = equipment_config[equipment]
        
        # Check cooldown
        current_time = time.time()
        if user_id not in team_base_cooldowns:
            team_base_cooldowns[user_id] = {}
        
        activity_key = f"train_{equipment.lower().replace(' ', '_')}"
        if activity_key in team_base_cooldowns[user_id]:
            time_since_last = current_time - team_base_cooldowns[user_id][activity_key]
            if time_since_last < config["cooldown"]:
                remaining = config["cooldown"] - time_since_last
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await ctx.send(f"⏳ You're still recovering from your last training! Wait **{minutes}m {seconds}s**")
                return
        
        # Apply bonus
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        if "training_bonuses" not in chi_data[user_id]:
            chi_data[user_id]["training_bonuses"] = {"melee_strength": 0.0, "speed": 0.0, "range_strength": 0.0, "bonus_hp": 0}
        
        chi_data[user_id]["training_bonuses"][config["bonus_type"]] += config["bonus_amount"]
        team_base_cooldowns[user_id][activity_key] = current_time
        save_data()
        
        total_bonus = chi_data[user_id]["training_bonuses"][config["bonus_type"]]
        await ctx.send(f"{config['emoji']} {ctx.author.mention} trained with the **{equipment}**!\n"
                      f"**+{config['bonus_amount']}%** {config['bonus_type'].replace('_', ' ').title()} bonus!\n"
                      f"Total bonus: **{total_bonus}%**")
        return
    
    if action == "relax":
        if not args:
            await ctx.send("❌ Please specify where to relax!\nAvailable: TV, Bed, Couch")
            return
        
        location = args.upper() if args.upper() == "TV" else args.title()
        
        # Check if team has this decoration
        if location not in team["decorations"]:
            await ctx.send(f"❌ Your team base doesn't have a {location}! Add it with `P!team base decorate <item>`")
            return
        
        # Location-specific cooldowns and rewards
        location_config = {
            "TV": {
                "cooldown": 21600,  # 6 hours
                "emoji": "📺",
                "prompts": [
                    "Nothing is on.",
                    "We should train instead.",
                    "Check your garden.",
                    "Oh look Kung Fu Panda is on."
                ]
            },
            "Bed": {
                "cooldown": 43200,  # 12 hours
                "emoji": "🛏️",
                "message": "You had a good rest!"
            },
            "Couch": {
                "cooldown": 21600,  # 6 hours
                "emoji": "🛋️",
                "message": "Oh lucky you. You found some left over chi."
            }
        }
        
        if location not in location_config:
            await ctx.send("❌ Invalid location! Choose: TV, Bed, or Couch")
            return
        
        config = location_config[location]
        
        # Check cooldown
        current_time = time.time()
        if user_id not in team_base_cooldowns:
            team_base_cooldowns[user_id] = {}
        
        activity_key = f"relax_{location.lower()}"
        if activity_key in team_base_cooldowns[user_id]:
            time_since_last = current_time - team_base_cooldowns[user_id][activity_key]
            if time_since_last < config["cooldown"]:
                remaining = config["cooldown"] - time_since_last
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                await ctx.send(f"⏳ This is still occupied! Wait **{hours}h {minutes}m**")
                return
        
        # Apply reward based on location
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        
        if location == "TV":
            prompt = random.choice(config["prompts"])
            chi_data[user_id]["chi"] += 2
            team_base_cooldowns[user_id][activity_key] = current_time
            save_data()
            await ctx.send(f"{config['emoji']} {ctx.author.mention} watched TV...\n"
                          f"*{prompt}*\n"
                          f"**+2 chi**")
        elif location == "Bed":
            if "training_bonuses" not in chi_data[user_id]:
                chi_data[user_id]["training_bonuses"] = {"melee_strength": 0.0, "speed": 0.0, "range_strength": 0.0, "bonus_hp": 0}
            chi_data[user_id]["training_bonuses"]["bonus_hp"] += 1
            team_base_cooldowns[user_id][activity_key] = current_time
            save_data()
            total_hp = chi_data[user_id]["training_bonuses"]["bonus_hp"]
            await ctx.send(f"{config['emoji']} {ctx.author.mention} rested in bed!\n"
                          f"*{config['message']}*\n"
                          f"**+1 HP** for battles (Total: **+{total_hp} HP**)")
        elif location == "Couch":
            chi_data[user_id]["chi"] += 1
            team_base_cooldowns[user_id][activity_key] = current_time
            save_data()
            await ctx.send(f"{config['emoji']} {ctx.author.mention} relaxed on the couch!\n"
                          f"*{config['message']}*\n"
                          f"**+1 chi**")
        return
    
    await ctx.send("❌ Invalid action! Use `P!team base view`, `P!team base paint <color>`, `P!team base decorate <item>`, `P!team base gym <equipment>`, `P!team base train <equipment>`, or `P!team base relax <location>`")

@team.command(name="leaderboard")
async def team_leaderboard(ctx):
    """View team leaderboard (admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ This command is for administrators only!")
        return
    
    if not teams_data["teams"]:
        await ctx.send("❌ No teams have been created yet!")
        return
    
    # Sort teams by team_score
    sorted_teams = []
    for team_id, team in teams_data["teams"].items():
        score = team.get("team_score", 0)
        sorted_teams.append((team, score))
    
    sorted_teams.sort(key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="🏆 Team Leaderboard - Top 10", color=discord.Color.gold())
    
    for i, (team, score) in enumerate(sorted_teams[:10], 1):
        leader = await bot.fetch_user(int(team["leader"]))
        wins = team["duel_stats"]["wins"]
        losses = team["duel_stats"]["losses"]
        ties = team["duel_stats"]["ties"]
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        embed.add_field(
            name=f"{medal} {team['name']}",
            value=f"Leader: {leader.name}\n"
                  f"Score: {score} points\n"
                  f"W: {wins} | L: {losses} | T: {ties}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@team.command(name="event")
async def team_event(ctx, *, event_name: str = ""):
    """Admin only: Start a team event for registration"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ This command is for administrators only!")
        return
    
    global active_team_event
    
    if not event_name:
        await ctx.send("❌ Usage: `P!team event <event_name>`\nExample: `P!team event Summer Tournament`")
        return
    
    active_team_event = {
        "name": event_name,
        "registered_teams": []
    }
    
    # Log event creation
    await log_event(
        "Team Event Started",
        f"**Event:** {event_name}\n**Started by:** {ctx.author.mention} ({ctx.author.name})\n**Status:** Open for registration", ctx.guild, discord.Color.gold())
    
    embed = discord.Embed(
        title="🎉 TEAM EVENT STARTED!",
        description=f"**Event:** {event_name}\n\n🏆 Team leaders can now register their teams!\n\n**How to Register:**\nTeam leaders use: `P!team register {event_name}`",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Only team leaders can register their teams!")
    await ctx.send(embed=embed)

@team.command(name="register")
async def team_register(ctx, *, event_name: str = ""):
    """Register your team for an active event (leader only)"""
    global active_team_event
    user_id = str(ctx.author.id)
    
    # Check if there's an active event
    if not active_team_event:
        await ctx.send("❌ There's no active team event right now! Wait for an admin to start one with `P!team event <name>`")
        return
    
    # Check if user is in a team
    if user_id not in teams_data["user_teams"]:
        await ctx.send("❌ You're not in a team! Create or join one first.")
        return
    
    team_id = teams_data["user_teams"][user_id]
    team = teams_data["teams"][team_id]
    
    # Check if user is the team leader
    if team["leader"] != user_id:
        leader = await bot.fetch_user(int(team["leader"]))
        await ctx.send(f"❌ Only the team leader ({leader.mention}) can register the team for events!")
        return
    
    # Check if event name matches
    if not event_name:
        await ctx.send(f"❌ Please specify the event name!\nUsage: `P!team register {active_team_event['name']}`")
        return
    
    if event_name.lower() != active_team_event["name"].lower():
        await ctx.send(f"❌ Event name doesn't match! The active event is: **{active_team_event['name']}**\n"
                      f"Use: `P!team register {active_team_event['name']}`")
        return
    
    # Check if team already registered
    if team_id in active_team_event["registered_teams"]:
        await ctx.send(f"✅ Your team **{team['name']}** is already registered for **{active_team_event['name']}**!")
        return
    
    # Register the team
    active_team_event["registered_teams"].append(team_id)
    
    embed = discord.Embed(
        title="✅ TEAM REGISTERED!",
        description=f"**Team:** {team['name']}\n**Event:** {active_team_event['name']}\n**Leader:** {ctx.author.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="Registered Teams", value=str(len(active_team_event["registered_teams"])), inline=False)
    embed.set_footer(text="Good luck in the event!")
    
    await ctx.send(embed=embed)
    
    # Log team registration
    await log_event(
        "Team Event Registration",
        f"**Team:** {team['name']}\n**Event:** {active_team_event['name']}\n**Leader:** {ctx.author.mention} ({ctx.author.name})\n**Total Registered:** {len(active_team_event['registered_teams'])}", ctx.guild, discord.Color.purple())


# ==================== PET SYSTEM ====================

@bot.group(name="pet", invoke_without_command=True)
async def pet(ctx):
    """Pet system commands"""
    if ctx.invoked_subcommand is None:
        await ctx.send("**🐾 Pet System Commands**\n"
                      "`P!pet store` - View available pets\n"
                      "`P!pet buy <name>` - Purchase a pet\n"
                      "`P!pet info` - View active pet details\n"
                      "`P!pet list` - View all your pets\n"
                      "`P!pet switch <name>` - Change active pet\n"
                      "`P!pet attacks` - View all pet attacks with IDs (P1-P15)\n"
                      "`P!pet name <nickname>` - Nickname your active pet\n"
                      "`P!pet feed <food>` - Feed your active pet\n"
                      "`P!pet duel P# <attack_id>` - Use pet attack in duels (e.g., P!pet duel P1)\n"
                      "`P!pet health` - View your pet's health\n"
                      "`P!pet train <type>` - Train your pet (heal/health/attack/special)")

@pet.command(name="store")
async def pet_store(ctx):
    """View the pet shop with all 5 pets"""
    embed = discord.Embed(
        title="🏪 Pax's Pet Emporium",
        description="Welcome! Choose your companion wisely. Each pet enhances your garden!\n",
        color=discord.Color.blue()
    )
    
    # Display pets in tier order (best to worst)
    sorted_pets = sorted(PET_DATA.items(), key=lambda x: x[1]["tier"])
    
    for pet_key, pet in sorted_pets:
        garden_bonus = pet["garden_bonus"]
        
        value_text = (
            f"{pet['description']}\n"
            f"❤️ **HP:** {pet['base_hp']:,}\n"
            f"💰 **Cost:** {pet['price']:,} chi\n\n"
            f"**Garden Bonuses:**\n"
            f"🌱 Chi Yield: +{int(garden_bonus['chi_yield']*100)}%\n"
            f"⚡ Growth Speed: +{int(garden_bonus['growth_speed']*100)}%\n"
            f"✨ Rare Drops: +{int(garden_bonus['rare_drop']*100)}%"
        )
        
        embed.add_field(
            name=f"{pet['emoji']} {pet['name']} (Tier {pet['tier']})",
            value=value_text,
            inline=False
        )
    
    embed.set_footer(text="Use P!pet buy <name> to purchase a pet! Pet bonuses apply to ALL your gardens.")
    await ctx.send(embed=embed)

@pet.command(name="buy")
async def pet_buy(ctx, *, pet_name: str = ""):
    """Buy a pet from the pet store"""
    if not pet_name:
        await ctx.send("❌ Please specify a pet name! Use `P!pet store` to see available pets.")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "pets": [], "active_pet": None}
    
    if "pets" not in chi_data[user_id]:
        chi_data[user_id]["pets"] = []
    if "active_pet" not in chi_data[user_id]:
        chi_data[user_id]["active_pet"] = None
    
    # Find the pet in PET_DATA
    found_pet_key = None
    found_pet = None
    for pet_key, pet_data in PET_DATA.items():
        if pet_data["name"].lower() == pet_name.lower():
            found_pet_key = pet_key
            found_pet = pet_data
            break
    
    if not found_pet:
        await ctx.send(f"❌ Pet '{pet_name}' not found! Use `P!pet store` to see available pets.")
        return
    
    # Check if user already owns this pet type
    for owned_pet in chi_data[user_id]["pets"]:
        if owned_pet["type"] == found_pet_key:
            await ctx.send(f"❌ You already own a **{found_pet['name']}**! Each user can only own one of each pet type.")
            return
    
    current_chi = chi_data[user_id].get("chi", 0)
    
    if current_chi < found_pet["price"]:
        await ctx.send(f"❌ You don't have enough chi! You need **{found_pet['price']:,} chi** but only have **{current_chi:,} chi**.")
        return
    
    # Check food requirement (10x primary food)
    # Find primary food for this pet
    primary_food_key = None
    primary_food_data = None
    for food_key, food_data in PET_FOOD.items():
        if food_data.get("primary_for") == found_pet_key:
            primary_food_key = food_key
            primary_food_data = food_data
            break
    
    if not primary_food_key:
        await ctx.send(f"❌ Error: No primary food defined for {found_pet['name']}!")
        return
    
    # Initialize pet_food inventory if needed
    if "pet_food" not in chi_data[user_id]:
        chi_data[user_id]["pet_food"] = {}
    
    # Check if user has 10x primary food
    current_food = chi_data[user_id]["pet_food"].get(primary_food_key, 0)
    required_food = 10
    
    if current_food < required_food:
        await ctx.send(
            f"❌ You need **{required_food}x {primary_food_data['emoji']} {primary_food_data['name']}** to adopt a {found_pet['name']}!\n"
            f"You currently have: **{current_food}x**\n\n"
            f"Buy food from `P!pet shop buy {primary_food_data['name']}`"
        )
        return
    
    # Deduct food and chi
    chi_data[user_id]["pet_food"][primary_food_key] -= required_food
    chi_data[user_id]["chi"] -= found_pet["price"]
    
    new_pet = {
        "type": found_pet_key,  # ox, snake, tiger, panda, dragon
        "name": found_pet["name"],
        "emoji": found_pet["emoji"],
        "nickname": None,
        "health": found_pet["base_hp"],
        "max_health": found_pet["base_hp"],
        "level": 1,
        "xp": 0,
        "battles_won": 0,
        "battles_lost": 0,
        "purchased_at": str(ctx.message.created_at)
    }
    
    chi_data[user_id]["pets"].append(new_pet)
    
    # Set as active pet if they don't have one
    if not chi_data[user_id]["active_pet"]:
        chi_data[user_id]["active_pet"] = found_pet_key
    
    save_data()
    
    # Unlock Dragon achievement if applicable
    if found_pet_key == "dragon":
        await unlock_achievement(ctx.author.id, "first_dragon", ctx.guild)
    
    # Log pet purchase
    await log_event(
        "Pet Purchase",
        f"**User:** {ctx.author.mention} ({ctx.author.name})\n**Pet:** {found_pet['emoji']} {found_pet['name']}\n**Cost:** {found_pet['price']:,} chi\n**Remaining Chi:** {chi_data[user_id]['chi']:,}", ctx.guild, discord.Color.purple())
    
    garden_bonus = found_pet["garden_bonus"]
    
    embed = discord.Embed(
        title=f"🐾 {found_pet['emoji']} {found_pet['name']} Adopted!",
        description=f"You adopted a **{found_pet['name']}** for **{found_pet['price']:,} chi**!\n\n{found_pet['description']}",
        color=discord.Color.green()
    )
    embed.add_field(name="❤️ Health", value=f"{new_pet['health']:,}/{new_pet['max_health']:,}", inline=True)
    embed.add_field(name="⭐ Level", value=str(new_pet['level']), inline=True)
    embed.add_field(name="💰 Remaining Chi", value=f"{chi_data[user_id]['chi']:,}", inline=True)
    
    embed.add_field(
        name="\n🌱 Garden Bonuses (Applied Immediately!)",
        value=(
            f"🌱 Chi Yield: +{int(garden_bonus['chi_yield']*100)}%\n"
            f"⚡ Growth Speed: +{int(garden_bonus['growth_speed']*100)}%\n"
            f"✨ Rare Drops: +{int(garden_bonus['rare_drop']*100)}%"
        ),
        inline=False
    )
    
    if chi_data[user_id]["active_pet"] == found_pet_key:
        embed.set_footer(text="This pet is now your active companion! Use P!pet info to see attacks.")
    else:
        embed.set_footer(text="Use P!pet switch to make this your active pet!")
    
    await ctx.send(embed=embed)

@pet.command(name="shop")
async def pet_shop(ctx, action: str = "", *, item_name: str = ""):
    """Buy pet food from the shop
    Usage: P!pet shop buy <food_name>
    """
    user_id = str(ctx.author.id)
    
    if not action:
        # Display shop
        embed = discord.Embed(
            title="🍱 Pet Food Shop",
            description="Buy food to restore your pet's health!",
            color=discord.Color.orange()
        )
        
        for food_key, food_data in PET_FOOD.items():
            embed.add_field(
                name=f"{food_data['emoji']} {food_data['name']} - {food_data['price']:,} chi",
                value=f"{food_data['description']}\n❤️ Heals: +{food_data['healing']} HP",
                inline=True
            )
        
        # Show user's current food inventory
        if user_id in chi_data and chi_data[user_id].get("pet_food"):
            inventory = chi_data[user_id]["pet_food"]
            if inventory:
                inv_str = ", ".join([f"{count}x {food_key}" for food_key, count in inventory.items()])
                embed.add_field(name="\n📦 Your Inventory", value=inv_str, inline=False)
        
        embed.set_footer(text="Use P!pet shop buy <food_name> to purchase food!")
        await ctx.send(embed=embed)
        return
    
    if action.lower() == "buy":
        if not item_name:
            await ctx.send("❌ Please specify food to buy! Usage: `P!pet shop buy <food_name>`")
            return
        
        # Initialize user data if needed
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        if "pet_food" not in chi_data[user_id]:
            chi_data[user_id]["pet_food"] = {}
        
        # Find the food in PET_FOOD
        food_key = None
        food_data = None
        search_name = item_name.lower().replace(" ", "_")
        
        for fk, fd in PET_FOOD.items():
            if fk == search_name or fd["name"].lower() == item_name.lower():
                food_key = fk
                food_data = fd
                break
        
        if not food_data:
            await ctx.send(f"❌ '{item_name}' is not available! Use `P!pet shop` to see available foods.")
            return
        
        current_chi = chi_data[user_id].get("chi", 0)
        
        if current_chi < food_data["price"]:
            await ctx.send(f"❌ You don't have enough chi! You need **{food_data['price']:,} chi** but only have **{current_chi:,} chi**.")
            return
        
        # Purchase the food
        chi_data[user_id]["chi"] -= food_data["price"]
        
        if food_key not in chi_data[user_id]["pet_food"]:
            chi_data[user_id]["pet_food"][food_key] = 0
        chi_data[user_id]["pet_food"][food_key] += 1
        
        save_data()
        
        embed = discord.Embed(
            title="🍱 Purchase Successful!",
            description=f"You bought **{food_data['emoji']} {food_data['name']}** for **{food_data['price']:,} chi**!",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ Healing", value=f"+{food_data['healing']} HP", inline=True)
        embed.add_field(name="📦 You have", value=f"{chi_data[user_id]['pet_food'][food_key]}x {food_data['name']}", inline=True)
        embed.add_field(name="💰 Remaining Chi", value=f"{chi_data[user_id]['chi']:,}", inline=False)
        embed.set_footer(text="Use P!pet feed <food_name> to feed your active pet!")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Invalid action! Use `P!pet shop` to view or `P!pet shop buy <food>` to purchase.")

@pet.command(name="name")
async def pet_rename(ctx, *, nickname: str = ""):
    """Nickname your active pet"""
    if not nickname:
        await ctx.send("❌ Please provide a nickname! Usage: `P!pet name <nickname>`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet!")
        return
    
    # Validate nickname length
    if len(nickname) > 30:
        await ctx.send("❌ Nickname is too long! Maximum 30 characters.")
        return
    
    if len(nickname) < 2:
        await ctx.send("❌ Nickname is too short! Minimum 2 characters.")
        return
    
    # Find active pet
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    for p in chi_data[user_id].get("pets", []):
        if p["type"] == active_pet_type:
            pet = p
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    # Update nickname
    old_name = pet.get("nickname") or pet["name"]
    pet["nickname"] = nickname
    save_data()
    
    embed = discord.Embed(
        title="🎉 Pet Renamed!",
        description=f"Your {pet['emoji']} **{pet['name']}** is now called **{nickname}**!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Previous Name", value=old_name, inline=True)
    embed.add_field(name="New Nickname", value=nickname, inline=True)
    embed.set_footer(text="Use P!pet info to see your pet's details!")
    
    await ctx.send(embed=embed)

@pet.command(name="feed")
async def pet_feed(ctx, *, food: str = ""):
    """Feed your active pet to restore health"""
    if not food:
        await ctx.send("❌ Please specify food to feed! Usage: `P!pet feed <food>`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet to feed!")
        return
    
    # Initialize pet_food if needed
    if "pet_food" not in chi_data[user_id]:
        chi_data[user_id]["pet_food"] = {}
    
    # Find the food in PET_FOOD
    food_key = None
    food_data = None
    search_name = food.lower().replace(" ", "_")
    
    for fk, fd in PET_FOOD.items():
        if fk == search_name or fd["name"].lower() == food.lower():
            food_key = fk
            food_data = fd
            break
    
    if not food_data:
        await ctx.send(f"❌ '{food}' is not a valid pet food! Use `P!pet shop` to see available foods.")
        return
    
    # Check if user has this food
    if food_key not in chi_data[user_id]["pet_food"] or chi_data[user_id]["pet_food"][food_key] <= 0:
        await ctx.send(f"❌ You don't have any **{food_data['name']}**! Buy it from `P!pet shop`")
        return
    
    # Get active pet
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    for p in chi_data[user_id].get("pets", []):
        if p["type"] == active_pet_type:
            pet = p
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    # Restore health
    old_health = pet["health"]
    max_health = pet["max_health"]
    pet["health"] = min(max_health, pet["health"] + food_data["healing"])
    health_restored = pet["health"] - old_health
    
    # Consume food
    chi_data[user_id]["pet_food"][food_key] -= 1
    if chi_data[user_id]["pet_food"][food_key] <= 0:
        del chi_data[user_id]["pet_food"][food_key]
    
    save_data()
    
    pet_name = pet.get("nickname") or pet["name"]
    embed = discord.Embed(
        title=f"{food_data['emoji']} {pet['emoji']} {pet_name} enjoyed the {food_data['name']}!",
        description=f"{ctx.author.mention} fed their pet!",
        color=discord.Color.green()
    )
    embed.add_field(name="❤️ Health Restored", value=f"+{health_restored} HP", inline=True)
    embed.add_field(name="Current Health", value=f"{pet['health']:,}/{max_health:,} HP", inline=True)
    
    remaining_food = chi_data[user_id]["pet_food"].get(food_key, 0)
    if remaining_food > 0:
        embed.set_footer(text=f"Remaining {food_data['name']}: {remaining_food}")
    
    await ctx.send(embed=embed)

@pet.command(name="info")
async def pet_info(ctx):
    """View detailed info about your active pet including attacks"""
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet! Use `P!pet store` to see available pets.")
        return
    
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    for p in chi_data[user_id].get("pets", []):
        if p["type"] == active_pet_type:
            pet = p
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    pet_data = PET_DATA[active_pet_type]
    garden_bonus = pet_data["garden_bonus"]
    
    pet_name = pet.get("nickname") or pet["name"]
    
    embed = discord.Embed(
        title=f"{pet['emoji']} {pet_name}'s Info",
        description=pet_data["description"],
        color=discord.Color.blue()
    )
    
    embed.add_field(name="❤️ HP", value=f"{pet['health']:,}/{pet['max_health']:,}", inline=True)
    embed.add_field(name="⭐ Level", value=str(pet['level']), inline=True)
    embed.add_field(name="🏆 Tier", value=f"{pet_data['tier']}/5", inline=True)
    
    embed.add_field(name="⚔️ Battles Won", value=str(pet.get('battles_won', 0)), inline=True)
    embed.add_field(name="💀 Battles Lost", value=str(pet.get('battles_lost', 0)), inline=True)
    embed.add_field(name="✨ XP", value=f"{pet.get('xp', 0):,}", inline=True)
    
    embed.add_field(
        name="\n🌱 Garden Bonuses",
        value=(
            f"🌱 Chi Yield: +{int(garden_bonus['chi_yield']*100)}%\n"
            f"⚡ Growth Speed: +{int(garden_bonus['growth_speed']*100)}%\n"
            f"✨ Rare Drops: +{int(garden_bonus['rare_drop']*100)}%"
        ),
        inline=False
    )
    
    # Show all 3 attacks
    attacks_text = ""
    for attack_key, attack_data in pet_data["attacks"].items():
        attacks_text += f"**{attack_data['emoji']} {attack_data['name']}**\n"
        attacks_text += f"💥 {attack_data['base_damage']} DMG - {attack_data['description']}\n\n"
    
    embed.add_field(name="⚔️ Special Attacks", value=attacks_text, inline=False)
    embed.set_footer(text="Use P!pet duel to battle other pets!")
    
    await ctx.send(embed=embed)

@pet.command(name="attacks")
async def pet_attacks(ctx):
    """View all pet attacks with their attack IDs (P1-P15)"""
    embed = discord.Embed(
        title="⚔️ All Pet Attacks",
        description="Use `P!pet duel P#` during a duel to use these attacks!\n\n",
        color=discord.Color.red()
    )
    
    # Sort pets by tier (Dragon = tier 1, Panda = tier 2, Tiger = tier 3, Snake = tier 4, Ox = tier 5)
    sorted_pets = sorted(PET_DATA.items(), key=lambda x: x[1]["tier"])
    
    attack_counter = 1
    for pet_key, pet_data in sorted_pets:
        attacks_text = ""
        pet_attacks = list(pet_data["attacks"].items())
        
        for attack_key, attack_info in pet_attacks:
            attack_id = f"P{attack_counter}"
            dmg_range = f"{attack_info['damage_range'][0]}-{attack_info['damage_range'][1]}"
            attacks_text += f"**{attack_id}** - {attack_info['emoji']} **{attack_info['name']}**\n"
            attacks_text += f"💥 Damage: {dmg_range} HP\n"
            attacks_text += f"📝 {attack_info['description']}\n\n"
            attack_counter += 1
        
        embed.add_field(
            name=f"{pet_data['emoji']} {pet_data['name']} (Tier {pet_data['tier']})",
            value=attacks_text,
            inline=False
        )
    
    embed.set_footer(text="In duels: P!pet duel P# | Example: P!pet duel P1 (Dragon Fire Breath)")
    await ctx.send(embed=embed)

@pet.command(name="list")
async def pet_list(ctx):
    """View all your owned pets"""
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("pets"):
        await ctx.send("❌ You don't own any pets yet! Use `P!pet store` to see available pets.")
        return
    
    pets = chi_data[user_id]["pets"]
    active_pet_type = chi_data[user_id].get("active_pet")
    
    embed = discord.Embed(
        title="🐾 Your Pet Collection",
        description=f"You own **{len(pets)}** pet(s):",
        color=discord.Color.purple()
    )
    
    for pet in pets:
        pet_type = pet["type"]
        pet_data = PET_DATA[pet_type]
        pet_name = pet.get("nickname") or pet["name"]
        
        is_active = "⭐ (ACTIVE)" if pet_type == active_pet_type else ""
        
        value_text = (
            f"❤️ HP: {pet['health']:,}/{pet['max_health']:,} | "
            f"⭐ Level: {pet['level']} | "
            f"🏆 Tier: {pet_data['tier']}/5\n"
            f"⚔️ Won: {pet.get('battles_won', 0)} | 💀 Lost: {pet.get('battles_lost', 0)}"
        )
        
        embed.add_field(
            name=f"{pet['emoji']} {pet_name} {is_active}",
            value=value_text,
            inline=False
        )
    
    embed.set_footer(text="Use P!pet switch <name> to change your active pet!")
    await ctx.send(embed=embed)

@pet.command(name="switch")
async def pet_switch(ctx, *, pet_name: str = ""):
    """Switch your active pet"""
    if not pet_name:
        await ctx.send("❌ Please specify which pet to make active! Usage: `P!pet switch <pet_name>`")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("pets"):
        await ctx.send("❌ You don't own any pets!")
        return
    
    # Find the pet
    found_pet = None
    for pet in chi_data[user_id]["pets"]:
        if pet["name"].lower() == pet_name.lower() or (pet.get("nickname") and pet["nickname"].lower() == pet_name.lower()):
            found_pet = pet
            break
    
    if not found_pet:
        await ctx.send(f"❌ You don't own a pet named '{pet_name}'! Use `P!pet list` to see your pets.")
        return
    
    # Set as active
    chi_data[user_id]["active_pet"] = found_pet["type"]
    save_data()
    
    display_name = found_pet.get("nickname") or found_pet["name"]
    
    embed = discord.Embed(
        title="🔄 Active Pet Changed!",
        description=f"**{found_pet['emoji']} {display_name}** is now your active companion!",
        color=discord.Color.green()
    )
    embed.add_field(name="❤️ HP", value=f"{found_pet['health']:,}/{found_pet['max_health']:,}", inline=True)
    embed.add_field(name="⭐ Level", value=str(found_pet['level']), inline=True)
    embed.set_footer(text="Garden bonuses are now applied!")
    
    await ctx.send(embed=embed)

@pet.command(name="attack", aliases=["duel"])
async def pet_attack(ctx, attack_id: str = ""):
    """Use pet attack in duels (e.g., P!pet duel P1 or P!pet attack P1)"""
    global active_duel
    
    if active_duel is None or active_duel["status"] != "active":
        await ctx.send("⚔️ There's no active duel right now! Pet attacks can only be used during duels.")
        return
    
    if ctx.author.id != active_duel["turn"]:
        await ctx.send("⚔️ It's not your turn!")
        return
    
    if not attack_id:
        await ctx.send("❌ Please specify an attack ID! Usage: `P!pet duel P#`\nExample: `P!pet duel P1`\nUse `P!pet attacks` to see all attack IDs.")
        return
    
    # Parse attack ID (P1-P15)
    if not attack_id.upper().startswith("P"):
        await ctx.send("❌ Invalid attack ID! Use format P# (e.g., P1, P5, P12)\nUse `P!pet attacks` to see all available attacks.")
        return
    
    try:
        attack_num = int(attack_id[1:])
        if attack_num < 1 or attack_num > 15:
            await ctx.send("❌ Attack ID must be between P1 and P15! Use `P!pet attacks` to see all attacks.")
            return
    except ValueError:
        await ctx.send("❌ Invalid attack ID format! Use P# (e.g., P1, P5, P12)\nUse `P!pet attacks` to see all available attacks.")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet! Use `P!pet buy` to get one.")
        return
    
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    for p in chi_data[user_id].get("pets", []):
        if p["type"] == active_pet_type:
            pet = p
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    # Map attack number to pet and attack
    # Dragon (tier 1): P1-P3, Panda (tier 2): P4-P6, Tiger (tier 3): P7-P9, Snake (tier 4): P10-P12, Ox (tier 5): P13-P15
    sorted_pets = sorted(PET_DATA.items(), key=lambda x: x[1]["tier"])
    
    attack_counter = 1
    selected_attack = None
    attack_pet_type = None
    
    for pet_key, pet_data in sorted_pets:
        for attack_key, attack_info in pet_data["attacks"].items():
            if attack_counter == attack_num:
                selected_attack = attack_info
                attack_pet_type = pet_key
                break
            attack_counter += 1
        if selected_attack:
            break
    
    if not selected_attack:
        await ctx.send("❌ Attack not found! Use `P!pet attacks` to see all available attacks.")
        return
    
    # Check if user's pet matches the attack
    if active_pet_type != attack_pet_type:
        pet_name_for_attack = PET_DATA[attack_pet_type]["name"]
        await ctx.send(f"❌ You can only use {PET_DATA[attack_pet_type]['emoji']} **{pet_name_for_attack}** attacks!\n"
                      f"Your active pet is {pet['emoji']} **{pet.get('nickname') or pet['name']}**.\n"
                      f"Use `P!pet attacks` to see which attacks you can use.")
        return
    
    # Calculate damage from selected attack
    import random
    damage = random.randint(selected_attack["damage_range"][0], selected_attack["damage_range"][1])
    
    # Deal damage to opponent
    if ctx.author.id == active_duel["challenger"]:
        active_duel["challenged_hp"] -= damage
        opponent_id = active_duel["challenged"]
        opponent_hp = active_duel["challenged_hp"]
        active_duel["turn"] = active_duel["challenged"]
    else:
        active_duel["challenger_hp"] -= damage
        opponent_id = active_duel["challenger"]
        opponent_hp = active_duel["challenger_hp"]
        active_duel["turn"] = active_duel["challenger"]
    
    opponent = ctx.guild.get_member(opponent_id)
    pet_name = pet.get("nickname") or pet["name"]
    
    await ctx.send(f"🐾 {ctx.author.mention}'s {pet['emoji']} **{pet_name}** used **{selected_attack['emoji']} {selected_attack['name']}** and dealt **{damage} damage** to {opponent.mention}!\n"
                  f"📝 {selected_attack['description']}")
    
    # Check for winner
    if opponent_hp <= 0:
        winner = ctx.author
        loser = opponent
        is_tournament = active_duel.get("is_tournament", False)
        
        bet_results = process_duel_bets(winner.id, ctx.guild)
        active_duel = None
        
        winner_id = str(winner.id)
        loser_id = str(loser.id)
        
        if is_tournament:
            chi_reward = 150
            update_chi(winner_id, chi_reward)
            # Loser no longer loses chi - encourages pet battles
            win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for winning a tournament!"
        else:
            chi_reward = 75  # Moderate 50% increase from 50
            update_chi(winner_id, chi_reward)
            # Loser no longer loses chi - reduces risk in pet duels
            win_message = f"The winner is... {winner.mention}! Congrats {winner.mention}, here is {chi_reward} chi for defeating your opponent in a duel!"
        
        # Update team duel stats
        if winner_id in teams_data["user_teams"]:
            winner_team_id = teams_data["user_teams"][winner_id]
            teams_data["teams"][winner_team_id]["duel_stats"]["wins"] += 1
            teams_data["teams"][winner_team_id]["team_score"] = teams_data["teams"][winner_team_id].get("team_score", 0) + 1
            save_teams()
        
        if loser_id in teams_data["user_teams"]:
            loser_team_id = teams_data["user_teams"][loser_id]
            teams_data["teams"][loser_team_id]["duel_stats"]["losses"] += 1
            save_teams()
        
        # Log duel victory to event channel
        try:
            guild_id = str(ctx.guild.id)
            log_channel_id = get_config_value(guild_id, "channels.log_channel_id")
            event_channel = None
            
            if log_channel_id:
                event_channel = bot.get_channel(int(log_channel_id))
            
            # Fallback: Use first available text channel
            if not event_channel:
                event_channel = next(
                    (ch for ch in ctx.guild.text_channels 
                     if ch.permissions_for(ctx.guild.me).send_messages), 
                    None
                )
            
            if event_channel:
                log_embed = discord.Embed(
                    title="⚔️ Duel Victory",
                    description=f"{winner.mention} defeated {loser.mention} in a duel using their pet **{pet_name}**!",
                    color=discord.Color.gold()
                )
                log_embed.add_field(name="Chi Reward", value=f"+{chi_reward} chi", inline=True)
                log_embed.set_footer(text=f"User ID: {winner_id}")
                await event_channel.send(embed=log_embed)
        except Exception as e:
            print(f"Failed to log duel victory: {e}")
        
        await ctx.send(win_message)
        if bet_results:
            await ctx.send(bet_results)

@pet.command(name="health")
async def pet_health(ctx):
    """View pet health"""
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet!")
        return
    
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    for p in chi_data[user_id].get("pets", []):
        if p.get("type") == active_pet_type:
            pet = p
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    pet_name = pet.get("nickname") or pet["name"]
    health_level = pet.get("health_level", 0)
    current_health = pet.get("health", 50)
    max_health = pet.get("max_health", 50)
    
    embed = discord.Embed(
        title=f"🐾 {pet_name}'s Health",
        description=f"**Current Health**: {current_health}/{max_health}\n"
                   f"**Health Training Level**: {health_level}/1 (Peace Orb upgrade)",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@pet.command(name="train")
async def pet_train(ctx, training_type: str = ""):
    """Train your pet to improve its abilities
    Usage: P!pet train <heal/health/attack/special>
    - heal: Train healing ability (cost: 500 chi)
    - health: Upgrade max health (cost: 1 Peace Orb, one-time only)
    - attack: Upgrade attack damage (cost: 1 artifact, max level 10)
    - special: Special training (requires max level garden, cost: 1000 chi)
    """
    if not training_type:
        await ctx.send("❌ Usage: `P!pet train <heal/health/attack/special>`\n\n"
                      "**Training Types:**\n"
                      "🔹 `heal` - Train healing ability (+5% per level, cost: 500 chi)\n"
                      "🔹 `health` - Upgrade max health (cost: 1 Peace Orb, one-time only)\n"
                      "🔹 `attack` - Upgrade attack damage (+10% per level, cost: 1 artifact, max level 10)\n"
                      "🔹 `special` - Special training (requires max level garden, cost: 1000 chi)")
        return
    
    user_id = str(ctx.author.id)
    if user_id not in chi_data or not chi_data[user_id].get("active_pet"):
        await ctx.send("❌ You don't have an active pet! Use `P!pet buy` to get one.")
        return
    
    active_pet_type = chi_data[user_id]["active_pet"]
    pet = None
    pet_index = None
    for idx, p in enumerate(chi_data[user_id].get("pets", [])):
        if p.get("type") == active_pet_type:
            pet = p
            pet_index = idx
            break
    
    if not pet:
        await ctx.send("❌ Your active pet could not be found!")
        return
    
    training_type = training_type.lower()
    pet_name = pet.get("nickname") or pet["name"]
    
    if training_type == "heal":
        # Train healing ability - costs chi
        heal_level = pet.get("heal_level", 0)
        cost = 500
        
        if chi_data[user_id].get("chi", 0) < cost:
            await ctx.send(f"❌ You need **{cost} chi** to train healing! You have **{chi_data[user_id].get('chi', 0)} chi**.")
            return
        
        chi_data[user_id]["chi"] -= cost
        pet["heal_level"] = heal_level + 1
        save_data()
        
        new_level = pet["heal_level"]
        heal_bonus = new_level * 5
        
        await ctx.send(f"✨ **{pet_name}** trained healing!\n"
                      f"🔸 Heal Level: **{new_level}** (+{heal_bonus}% healing)\n"
                      f"💰 Cost: **{cost} chi**")
    
    elif training_type == "health":
        # Upgrade max health - costs Peace Orb (one-time only)
        health_level = pet.get("health_level", 0)
        
        if health_level >= 1:
            await ctx.send(f"❌ **{pet_name}** has already received the Peace Orb health upgrade! This can only be done once.")
            return
        
        # Check if user owns Peace Orb
        peace_orb_owned = "Peace Orb" in chi_data[user_id].get("purchased_items", [])
        
        if not peace_orb_owned:
            await ctx.send(f"❌ You need a **Peace Orb** to upgrade health! Buy it from `P!rshop` (R8).")
            return
        
        # Remove Peace Orb from inventory
        chi_data[user_id]["purchased_items"].remove("Peace Orb")
        
        # Upgrade health
        old_max = pet.get("max_health", 50)
        new_max = old_max + 50  # +50 max health
        pet["max_health"] = new_max
        pet["health"] = new_max  # Also heal to full
        pet["health_level"] = 1
        save_data()
        
        await ctx.send(f"✨ **{pet_name}** consumed the Peace Orb!\n"
                      f"💚 Max Health: **{old_max}** → **{new_max}** (+50)\n"
                      f"🔸 Health fully restored!")
    
    elif training_type == "attack":
        # Upgrade attack - costs artifacts
        attack_level = pet.get("attack_level", 0)
        
        if attack_level >= 10:
            await ctx.send(f"❌ **{pet_name}** has reached max attack level (10)!")
            return
        
        # Check if user has any artifacts
        user_artifacts = chi_data[user_id].get("artifacts", [])
        if not user_artifacts:
            await ctx.send(f"❌ You need an artifact to train attack! Find artifacts with `P!find artifact`.")
            return
        
        # Consume one artifact
        consumed_artifact = user_artifacts.pop(0)
        pet["attack_level"] = attack_level + 1
        save_data()
        
        new_level = pet["attack_level"]
        attack_bonus = new_level * 10
        
        await ctx.send(f"✨ **{pet_name}** consumed {consumed_artifact['emoji']} **{consumed_artifact['name']}**!\n"
                      f"⚔️ Attack Level: **{new_level}**/10 (+{attack_bonus}% damage)")
    
    elif training_type == "special":
        # Special training - requires max level garden
        if user_id not in gardens_data or not gardens_data[user_id]:
            await ctx.send("❌ You don't have a garden! Special training requires a max level (5) garden.")
            return
        
        # Check garden level
        garden_level = gardens_data[user_id].get("level", 1)
        if garden_level < 5:
            await ctx.send(f"❌ Your garden must be max level (5) for special training! Current level: **{garden_level}**/5")
            return
        
        cost = 1000
        if chi_data[user_id].get("chi", 0) < cost:
            await ctx.send(f"❌ You need **{cost} chi** for special training! You have **{chi_data[user_id].get('chi', 0)} chi**.")
            return
        
        special_level = pet.get("special_level", 0)
        chi_data[user_id]["chi"] -= cost
        pet["special_level"] = special_level + 1
        save_data()
        
        new_level = pet["special_level"]
        
        await ctx.send(f"✨ **{pet_name}** completed special training!\n"
                      f"🌟 Special Level: **{new_level}** (Unlocks unique abilities)\n"
                      f"💰 Cost: **{cost} chi**")
    
    else:
        await ctx.send("❌ Invalid training type! Use `heal`, `health`, `attack`, or `special`.")



# ==================== TRADING SYSTEM ====================

@bot.command(name="pay")
async def pay(ctx, target: discord.Member = None, amount: str = "", currency: str = "chi"):
    """Pay chi or rebirths to another user
    Usage: 
    - P!pay @user 100 - Pay 100 chi
    - P!pay @user 100 chi - Pay 100 chi
    - P!pay @user 1 rebirth - Pay 1 rebirth
    """
    if not target or not amount:
        await ctx.send("❌ Usage: `P!pay @user <amount> [chi/rebirth]`\n"
                      "Examples:\n"
                      "`P!pay @user 100` - Pay 100 chi\n"
                      "`P!pay @user 100 chi` - Pay 100 chi\n"
                      "`P!pay @user 1 rebirth` - Pay 1 rebirth")
        return
    
    if target.id == ctx.author.id:
        await ctx.send("❌ You can't pay yourself!")
        return
    
    if target.bot:
        await ctx.send("❌ You can't pay bots!")
        return
    
    # Initialize user data
    sender_id = str(ctx.author.id)
    receiver_id = str(target.id)
    
    if sender_id not in chi_data:
        chi_data[sender_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if receiver_id not in chi_data:
        chi_data[receiver_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    # Parse currency type
    currency_lower = currency.lower()
    if currency_lower in ["rebirth", "rebirths", "rb"]:
        currency_type = "rebirth"
    else:
        currency_type = "chi"
    
    # Parse amount
    try:
        pay_amount = int(amount)
    except ValueError:
        await ctx.send("❌ Please specify a valid amount (must be a number)!")
        return
    
    if pay_amount <= 0:
        await ctx.send("❌ Amount must be greater than 0!")
        return
    
    # Process payment based on currency type
    if currency_type == "rebirth":
        # Pay rebirths
        sender_rebirths = chi_data[sender_id].get("rebirths", 0)
        
        if sender_rebirths < pay_amount:
            await ctx.send(f"❌ You don't have enough rebirths! You have **{sender_rebirths}** rebirth(s) but tried to pay **{pay_amount}**.")
            return
        
        # Transfer rebirths
        chi_data[sender_id]["rebirths"] -= pay_amount
        chi_data[receiver_id]["rebirths"] = chi_data[receiver_id].get("rebirths", 0) + pay_amount
        save_data()
        
        # Log rebirth transfer
        await log_event(
            "Rebirth Transfer",
            f"**From:** {ctx.author.mention} ({ctx.author.name})\n**To:** {target.mention} ({target.name})\n**Amount:** {pay_amount} rebirth(s)\n**Sender Balance:** {chi_data[sender_id]['rebirths']} rebirths\n**Receiver Balance:** {chi_data[receiver_id]['rebirths']} rebirths", ctx.guild, discord.Color.blue())
        
        embed = discord.Embed(
            title="✅ Payment Successful!",
            description=f"{ctx.author.mention} paid **{pay_amount} rebirth(s)** to {target.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{ctx.author.display_name}'s Rebirths", value=str(chi_data[sender_id]["rebirths"]), inline=True)
        embed.add_field(name=f"{target.display_name}'s Rebirths", value=str(chi_data[receiver_id]["rebirths"]), inline=True)
        await ctx.send(embed=embed)
        
    else:
        # Pay chi
        sender_chi = chi_data[sender_id].get("chi", 0)
        
        if sender_chi < pay_amount:
            await ctx.send(f"❌ You don't have enough chi! You have **{sender_chi}** chi but tried to pay **{pay_amount}**.")
            return
        
        # Transfer chi
        chi_data[sender_id]["chi"] -= pay_amount
        chi_data[receiver_id]["chi"] = chi_data[receiver_id].get("chi", 0) + pay_amount
        save_data()
        
        # Log chi transfer
        await log_event(
            "Chi Transfer",
            f"**From:** {ctx.author.mention} ({ctx.author.name})\n**To:** {target.mention} ({target.name})\n**Amount:** {pay_amount:,} chi\n**Sender Balance:** {chi_data[sender_id]['chi']:,} chi\n**Receiver Balance:** {chi_data[receiver_id]['chi']:,} chi", ctx.guild, discord.Color.gold())
        
        embed = discord.Embed(
            title="💰 Payment Successful!",
            description=f"{ctx.author.mention} paid **{pay_amount} chi** to {target.mention}!",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"{ctx.author.display_name}'s Chi", value=str(chi_data[sender_id]["chi"]), inline=True)
        embed.add_field(name=f"{target.display_name}'s Chi", value=str(chi_data[receiver_id]["chi"]), inline=True)
        await ctx.send(embed=embed)

@bot.command(name="search")
async def search_shop(ctx, shop_type: str = "", category: str = "", price: str = ""):
    """Search for items across shops by category or price
    Usage: P!search <chi shop/rebirth shop/garden shop> <category> [price]
    Examples:
    - P!search garden shop seeds
    - P!search chi shop 150
    - P!search rebirth shop default 1
    """
    if not shop_type or not category:
        await ctx.send("❌ Usage: `P!search <chi shop/rebirth shop/garden shop> <category> [price]`\n\n"
                      "Examples:\n"
                      "• `P!search garden shop seeds`\n"
                      "• `P!search garden shop tools`\n"
                      "• `P!search chi shop 150`\n"
                      "• `P!search rebirth shop 1`")
        return
    
    # Normalize shop type
    shop_normalized = shop_type.lower()
    if "garden" in shop_normalized:
        shop_name = "Garden Shop"
        shop_emoji = "🌸"
    elif "chi" in shop_normalized:
        shop_name = "Chi Shop"
        shop_emoji = "💎"
    elif "rebirth" in shop_normalized:
        shop_name = "Rebirth Shop"
        shop_emoji = "♻️"
    else:
        await ctx.send("❌ Invalid shop type! Choose: `chi shop`, `rebirth shop`, or `garden shop`")
        return
    
    results = []
    
    # Search by category first
    if shop_name == "Garden Shop":
        category_lower = category.lower()
        
        if "seed" in category_lower:
            for seed_name, seed_info in GARDEN_SHOP_ITEMS["seeds"].items():
                item_price = seed_info["cost"]
                if price and str(item_price) != price:
                    continue
                results.append({
                    "name": seed_name,
                    "cost": seed_info["cost"],
                    "category": "Seeds",
                    "emoji": seed_info["emoji"],
                    "description": f"Harvest: +{seed_info['harvest_chi']} chi • Grow: {seed_info['grow_time_minutes']}m"
                })
        elif "tool" in category_lower:
            for tool_name, tool_info in GARDEN_SHOP_ITEMS["tools"].items():
                item_price = tool_info["cost"]
                if price and str(item_price) != price:
                    continue
                results.append({
                    "name": tool_name,
                    "cost": tool_info["cost"],
                    "category": "Tools",
                    "emoji": tool_info["emoji"],
                    "description": tool_info["description"]
                })
        
        # If no category match, search by price
        if not results and category.isdigit():
            search_price = int(category)
            for seed_name, seed_info in GARDEN_SHOP_ITEMS["seeds"].items():
                if seed_info["cost"] == search_price:
                    results.append({
                        "name": seed_name,
                        "cost": seed_info["cost"],
                        "category": "Seeds",
                        "emoji": seed_info["emoji"],
                        "description": f"Harvest: +{seed_info['harvest_chi']} chi • Grow: {seed_info['grow_time_minutes']}m"
                    })
            for tool_name, tool_info in GARDEN_SHOP_ITEMS["tools"].items():
                if tool_info["cost"] == search_price:
                    results.append({
                        "name": tool_name,
                        "cost": tool_info["cost"],
                        "category": "Tools",
                        "emoji": tool_info["emoji"],
                        "description": tool_info["description"]
                    })
    
    elif shop_name == "Chi Shop":
        # Search by type/category
        for item in chi_shop_data.get("items", []):
            item_type = item.get("type", "default")
            item_price = item["cost"]
            
            # Check if category matches type or if searching by price
            if category.lower() in item_type.lower() or (category.isdigit() and int(category) == item_price):
                if price and str(item_price) != price:
                    continue
                results.append({
                    "name": item["name"],
                    "cost": item["cost"],
                    "category": item_type.capitalize(),
                    "emoji": "⚔️" if "sword" in item["name"].lower() or "katana" in item["name"].lower() else 
                             "🍵" if "tea" in item["name"].lower() else
                             "🧥" if "coat" in item["name"].lower() or "hat" in item["name"].lower() else "📦",
                    "description": f"Type: {item_type}"
                })
    
    elif shop_name == "Rebirth Shop":
        # Search by type/category
        for item in shop_data.get("items", []):
            item_type = item.get("type", "default")
            item_price = item["cost"]
            
            # Check if category matches type or if searching by price
            if category.lower() in item_type.lower() or (category.isdigit() and int(category) == item_price):
                if price and str(item_price) != price:
                    continue
                results.append({
                    "name": item["name"],
                    "cost": item["cost"],
                    "category": item_type.capitalize(),
                    "emoji": "📈" if "level" in item["name"].lower() else
                             "🎨" if "role" in item["name"].lower() or "decoration" in item["name"].lower() else
                             "💎" if "nitro" in item["name"].lower() else "📦",
                    "description": f"Type: {item_type}"
                })
    
    # Display results
    if not results:
        await ctx.send(f"❌ No items found in **{shop_name}** for category/price: `{category}`\n\n"
                      f"Try searching by:\n"
                      f"• Category: `seeds`, `tools` (Garden Shop)\n"
                      f"• Type: `default` (Chi/Rebirth Shop)\n"
                      f"• Price: Any number")
        return
    
    embed = discord.Embed(
        title=f"{shop_emoji} {shop_name} - Search Results",
        description=f"Found {len(results)} item(s) matching your search:",
        color=discord.Color.green()
    )
    
    for item in results[:10]:  # Limit to 10 results
        embed.add_field(
            name=f"{item['emoji']} {item['name']} - {item['cost']} {'chi' if shop_name != 'Rebirth Shop' else 'rebirth(s)'}",
            value=f"{item['description']}\n*Category: {item['category']}*",
            inline=False
        )
    
    if len(results) > 10:
        embed.set_footer(text=f"Showing 10 of {len(results)} results. Refine your search for fewer results.")
    else:
        embed.set_footer(text=f"Use P!{shop_name.lower().replace(' ', '')} to view the full shop")
    
    await ctx.send(embed=embed)


# ==================== GARDEN SYSTEM ====================

@bot.group(name="garden", invoke_without_command=True)
async def garden(ctx):
    """Manage your spiritual garden"""
    user_id = str(ctx.author.id)
    
    # Initialize chi_data if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    # Initialize garden if user doesn't have one
    if user_id not in gardens_data["gardens"]:
        # Check if user has enough chi
        if chi_data[user_id].get("chi", 0) < 50:
            await ctx.send("🌸 **You need 50 chi to create your garden!**\n\n"
                          "Farm chi by chatting positively, completing quests, or harvesting from your garden!\n"
                          "Use `P!chi` to check your current balance.")
            return
        
        # Deduct 50 chi and create garden
        chi_data[user_id]["chi"] -= 50
        await initialize_garden(ctx.author.id, "rare", ctx.author.name, ctx.guild)
        tier_info = GARDEN_TIERS["rare"]
        save_data()
        
        await ctx.send(f"{tier_info['emoji']} **Garden Created!**\n"
                      f"You've created a **{tier_info['name']}** for 50 chi!\n\n"
                      f"Use `P!garden shop` to buy seeds and tools!\n"
                      f"Plant seeds with `P!garden plant <seed_name>`")
        return
    
    # Check and reset oversized gardens (>200 plants)
    was_reset = await check_and_reset_oversized_garden(ctx.author.id, ctx.author.name, ctx.guild)
    if was_reset:
        await ctx.send(f"⚠️ **Garden Reset Notice**\n\n"
                      f"Your garden exceeded the **{MAX_GARDEN_SEEDS}** plant limit and has been reset.\n\n"
                      f"**Compensation:**\n"
                      f"🌱 5x Silverdew seeds\n"
                      f"🌸 50x Lavender seeds\n\n"
                      f"You can now plant up to **{MAX_GARDEN_SEEDS}** total seeds in your garden!")
    
    # Show garden info
    garden_data = gardens_data["gardens"][user_id]
    
    # Validate and fix plants data - accept both old and new formats
    if "plants" in garden_data:
        valid_plants = []
        for plant in garden_data["plants"]:
            # Skip corrupted string data
            if isinstance(plant, str):
                print(f"⚠️ Skipping corrupted plant (string) for user {user_id}")
                continue
            
            # Validate dict structure - accept old ("seed") or new ("name") format
            if isinstance(plant, dict):
                has_name = "name" in plant or "seed" in plant
                has_time = "planted_at" in plant or "mature_at" in plant
                
                if has_name and has_time:
                    valid_plants.append(plant)
                else:
                    print(f"⚠️ Skipping invalid plant (missing required fields) for user {user_id}")
        
        # Only save if we found valid plants or the list was empty
        if valid_plants or not garden_data["plants"]:
            garden_data["plants"] = valid_plants
            save_gardens()
        else:
            print(f"⚠️ Not saving - all plants appear invalid for user {user_id}")
    
    tier_info = GARDEN_TIERS[garden_data["tier"]]
    
    embed = discord.Embed(
        title=f"{tier_info['emoji']} {tier_info['name']}",
        description=f"**Level {garden_data['level']}** Garden",
        color=discord.Color.green()
    )
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    # Show plants (compact format grouped by type)
    if garden_data["plants"]:
        # Count plants by type and readiness
        plant_counts = {}
        has_fertilizer = chi_data[user_id]["garden_inventory"].get("Fertilizer Bag", 0) > 0
        garden_tier = garden_data.get("tier", "rare")
        
        for plant in garden_data["plants"]:
            plant_name = plant.get("name")
            if not plant_name or plant_name not in GARDEN_SHOP_ITEMS["seeds"]:
                # Skip corrupted or invalid plants
                continue
            
            plant_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
            planted_time = datetime.fromtimestamp(plant["planted_at"])
            
            grow_minutes = calculate_grow_time(plant_info["grow_time_minutes"], has_fertilizer, garden_tier, user_id, plant_name, garden_data)
            ready_time = planted_time + timedelta(minutes=grow_minutes)
            
            # Check if ready to harvest or event is active
            is_ready = datetime.utcnow() >= ready_time or is_garden_event_active()
            
            # Initialize counters for this plant type
            if plant_name not in plant_counts:
                plant_counts[plant_name] = {"ready": 0, "not_ready": 0, "emoji": plant_info["emoji"]}
            
            # Count ready vs not ready
            if is_ready:
                plant_counts[plant_name]["ready"] += 1
            else:
                plant_counts[plant_name]["not_ready"] += 1
        
        # Build compact display
        plant_list = []
        total_plants = len(garden_data["plants"])
        
        for plant_name, counts in plant_counts.items():
            emoji = counts["emoji"]
            if counts["ready"] > 0:
                plant_list.append(f"{emoji} {plant_name} x{counts['ready']} ✅")
            if counts["not_ready"] > 0:
                plant_list.append(f"{emoji} {plant_name} x{counts['not_ready']} ❌")
        
        plants_display = "\n".join(plant_list)
        max_capacity = get_garden_max_capacity(garden_data.get("tier", "rare"))
        embed.add_field(name=f"🌿 Your Plants ({total_plants}/{max_capacity})", value=plants_display, inline=False)
    else:
        max_capacity = get_garden_max_capacity(garden_data.get("tier", "rare"))
        embed.add_field(name=f"🌿 Your Plants (0/{max_capacity})", value="No plants yet! Use `P!garden shop` to buy seeds.", inline=False)
    
    # Show inventory
    garden_inv = chi_data[user_id]["garden_inventory"]
    # CRITICAL: Ensure garden_inventory is a dict before calling .items()
    if not isinstance(garden_inv, dict):
        print(f"⚠️ ERROR: garden_inventory is {type(garden_inv).__name__}, not dict! Resetting for user {user_id}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
        garden_inv = {}
    
    if garden_inv:
        inv_list = []
        for item_name, quantity in garden_inv.items():
            # Find emoji from shop items
            emoji = "📦"
            if item_name in GARDEN_SHOP_ITEMS["tools"]:
                emoji = GARDEN_SHOP_ITEMS["tools"][item_name]["emoji"]
                if quantity > 0:
                    inv_list.append(f"{emoji} {item_name}: {quantity}")
            elif item_name in GARDEN_SHOP_ITEMS["seeds"]:
                emoji = GARDEN_SHOP_ITEMS["seeds"][item_name]["emoji"]
                # Handle legacy "owned" values
                if quantity == "owned":
                    quantity = 0
                if isinstance(quantity, int) and quantity > 0:
                    inv_list.append(f"{emoji} {item_name}: {quantity} seeds")
        
        if inv_list:
            embed.add_field(name="🎒 Garden Inventory", value="\n".join(inv_list) + "\n\n*View all in `P!inv`*", inline=False)
    
    # Show garden event status
    if is_garden_event_active():
        embed.add_field(name="✨ Spiritual Journey Boost Active!", 
                       value="All plants are instantly ready to harvest!", inline=False)
    
    embed.set_footer(text="Use P!garden shop to see available items • P!garden help for commands")
    
    # Add functional UI buttons
    garden_view = GardenView(ctx.author.id, chi_data, gardens_data["gardens"], GARDEN_SHOP_ITEMS)
    msg = await ctx.send(embed=embed, view=garden_view)
    garden_view.message = msg

@garden.command(name="shop")
async def garden_shop(ctx, action: str = "", item_name: str = "", quantity: int = 1):
    """View or buy from the garden shop"""
    user_id = str(ctx.author.id)
    
    # Check if user has garden
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You need to create a garden first! Use `P!garden` to get started (costs 50 chi).")
        return
    
    if action.lower() == "buy" and item_name:
        # Buy item
        if user_id not in chi_data:
            chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
        
        # Validate quantity
        if quantity < 1:
            await ctx.send("❌ Quantity must be at least 1!")
            return
        if quantity > 100:
            await ctx.send("❌ You can only buy up to 100 items at once!")
            return
        
        # Find item (support both G# IDs and names, case-insensitive)
        item_found = False
        item_cost = 0
        item_category = None
        actual_item_name = None
        
        # Check if using shop ID (G1, G2, etc.)
        if item_name.upper().startswith("G") and item_name[1:].isdigit():
            item_index = int(item_name[1:]) - 1
            all_items = []
            
            # Build ordered list of all items (tools first, then seeds)
            for tool_name in GARDEN_SHOP_ITEMS["tools"].keys():
                all_items.append(("tools", tool_name))
            for seed_name in GARDEN_SHOP_ITEMS["seeds"].keys():
                all_items.append(("seeds", seed_name))
            
            if 0 <= item_index < len(all_items):
                item_category, actual_item_name = all_items[item_index]
                item_cost = GARDEN_SHOP_ITEMS[item_category][actual_item_name]["cost"]
                item_found = True
            else:
                await ctx.send(f"❌ Invalid ID '{item_name.upper()}'! Use `P!garden shop` to see available items.")
                return
        else:
            # Search by item name (case-insensitive)
            for category in ["tools", "seeds"]:
                for shop_item_name, shop_item_info in GARDEN_SHOP_ITEMS[category].items():
                    if shop_item_name.lower() == item_name.lower():
                        item_found = True
                        item_cost = shop_item_info["cost"]
                        item_category = category
                        actual_item_name = shop_item_name
                        break
                if item_found:
                    break
        
        if not item_found:
            await ctx.send(f"❌ Item '{item_name}' not found in shop!")
            return
        
        # Use the actual item name for consistency
        item_name = actual_item_name
        
        # Check tier restrictions for locked seeds
        if item_category == "seeds":
            garden_data = gardens_data["gardens"][user_id]
            current_tier = garden_data.get("tier", "rare")
            
            # Check if Moonshade (requires legendary tier)
            if item_name == "Moonshade" and current_tier == "rare":
                await ctx.send(f"🔒 **{item_name}** is locked!\n\n"
                              f"Upgrade your garden to **{GARDEN_TIERS['legendary']['emoji']} Chi Grove** (legendary tier) to unlock this seed.\n"
                              f"Use `P!garden upgrade` to see upgrade options.")
                return
            
            # Check if Heartvine (requires eternal tier)
            if item_name == "Heartvine" and current_tier in ["rare", "legendary"]:
                await ctx.send(f"🔒 **{item_name}** is locked!\n\n"
                              f"Upgrade your garden to **{GARDEN_TIERS['eternal']['emoji']} Hépíng sēnlín** (eternal tier) to unlock this seed.\n"
                              f"Use `P!garden upgrade` to see upgrade options.")
                return
        
        # Calculate total cost
        total_cost = item_cost * quantity
        
        # Check if user has enough chi
        user_chi = chi_data[user_id].get("chi", 0)
        if user_chi < total_cost:
            await ctx.send(f"❌ You need **{total_cost:,} chi** to buy **{quantity}x {item_name}**! You have **{user_chi:,} chi**.")
            return
        
        # Initialize garden_inventory if needed
        if "garden_inventory" not in chi_data[user_id]:
            chi_data[user_id]["garden_inventory"] = {}
        
        # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
        if not isinstance(chi_data[user_id]["garden_inventory"], dict):
            print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
            chi_data[user_id]["garden_inventory"] = {}
            save_data()
        
        # Purchase items
        chi_data[user_id]["chi"] -= total_cost
        
        # For seeds: add quantity (consumable). For tools: add quantity
        if item_category == "seeds":
            current_seeds = chi_data[user_id]["garden_inventory"].get(item_name, 0)
            
            # Handle legacy "owned" values - convert to 0
            if current_seeds == "owned":
                current_seeds = 0
            
            # Add purchased quantity
            chi_data[user_id]["garden_inventory"][item_name] = current_seeds + quantity
            item_info = GARDEN_SHOP_ITEMS[item_category][item_name]
            purchase_message = f"🌱 Purchased **{quantity}x {item_info['emoji']} {item_name}** for **{total_cost:,} chi**!\n💡 Plant them and harvest to get seeds back (10% bonus chance!)"
        else:
            # Tools: add to quantity as before
            item_info = GARDEN_SHOP_ITEMS[item_category][item_name]
            chi_data[user_id]["garden_inventory"][item_name] = chi_data[user_id]["garden_inventory"].get(item_name, 0) + quantity
            purchase_message = f"✅ Purchased **{quantity}x {item_info['emoji']} {item_name}** for **{total_cost:,} chi**!"
        
        save_data()
        
        # Log garden shop purchase
        item_info = GARDEN_SHOP_ITEMS[item_category][item_name]
        quantity_text = f"{quantity}x " if quantity > 1 and item_category != "seeds" else ""
        await log_event(
            "Garden Shop Purchase",
            f"**User:** {ctx.author.mention} ({ctx.author.name})\n**Item:** {quantity_text}{item_info['emoji']} {item_name}\n**Cost:** {total_cost:,} chi\n**Remaining Chi:** {chi_data[user_id]['chi']:,}", ctx.guild, discord.Color.green())
        
        await ctx.send(f"{purchase_message}\n"
                      f"New chi balance: **{chi_data[user_id]['chi']:,} chi**")
    else:
        # Show shop
        embed = discord.Embed(
            title="🌸 Garden Shop",
            description="Purchase seeds and tools for your garden!",
            color=discord.Color.green()
        )
        
        # Show tools
        tools_list = []
        for idx, (tool_name, tool_info) in enumerate(GARDEN_SHOP_ITEMS["tools"].items(), start=1):
            tools_list.append(f"G{idx}: {tool_info['emoji']} **{tool_name}** - {tool_info['cost']} chi\n*{tool_info['description']}*")
        embed.add_field(name="🛠️ Tools", value="\n\n".join(tools_list), inline=False)
        
        # Show seeds (continue numbering from tools, mark locked seeds)
        garden_data = gardens_data["gardens"][user_id]
        current_tier = garden_data.get("tier", "rare")
        
        seeds_list = []
        tool_count = len(GARDEN_SHOP_ITEMS["tools"])
        for idx, (seed_name, seed_info) in enumerate(GARDEN_SHOP_ITEMS["seeds"].items(), start=tool_count + 1):
            # Check if seed is locked
            locked = False
            lock_text = ""
            if seed_name == "Moonshade" and current_tier == "rare":
                locked = True
                lock_text = " 🔒 *Requires Chi Grove tier*"
            elif seed_name == "Heartvine" and current_tier in ["rare", "legendary"]:
                locked = True
                lock_text = " 🔒 *Requires Hépíng sēnlín tier*"
            
            seeds_list.append(f"G{idx}: {seed_info['emoji']} **{seed_name}** - {seed_info['cost']} chi{lock_text}\n"
                            f"Harvest: +{seed_info['harvest_chi']} chi • Grow Time: {seed_info['grow_time_minutes']}m")
        embed.add_field(name="🌱 Seeds", value="\n\n".join(seeds_list), inline=False)
        
        embed.set_footer(text="Use P!garden shop buy <item_name or G#> [quantity] to purchase • Example: P!garden shop buy G1 5")
        await ctx.send(embed=embed)

@garden.command(name="plant")
async def garden_plant(ctx, action: str = "", *, seed_identifier: str = ""):
    """Plant seeds from your inventory. Use quantity to plant multiple: P!garden plant <seed> <quantity>"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    garden_data = gardens_data["gardens"][user_id]
    
    # Check if using "plant all" syntax
    if action.lower() == "all":
        await ctx.send("❌ The `plant all` command has been removed.\n"
                      "Seeds are now unlimited once purchased! Just use `P!garden plant <seed> <quantity>` to plant multiple.\n"
                      "Example: `P!garden plant Lavender 10`\n"
                      "They auto-replant after harvest, so you don't need to plant them again!")
        return
    
    # Parse plant name and quantity
    # Check if last word is a number
    quantity = 1
    full_input = action + (" " + seed_identifier if seed_identifier else "")
    parts = full_input.strip().split()
    
    if not parts:
        await ctx.send("❌ Please specify a plant to grow! Usage: `P!garden plant <plant_name> [quantity]`")
        return
    
    # Check if last part is a number (quantity)
    if len(parts) > 1 and parts[-1].isdigit():
        quantity = int(parts[-1])
        plant_name = " ".join(parts[:-1])
    else:
        plant_name = full_input.strip()
    
    # Validate quantity
    if quantity <= 0:
        await ctx.send("❌ Quantity must be at least 1!")
        return
    
    if quantity > 50:
        await ctx.send("❌ You can only plant up to 50 seeds at once! (To prevent spam)")
        return
    
    # Check if seed exists
    if plant_name not in GARDEN_SHOP_ITEMS["seeds"]:
        await ctx.send(f"❌ '{plant_name}' is not a valid seed!")
        return
    
    # Check if planting would exceed garden limit
    current_plant_count = len(garden_data["plants"])
    max_capacity = get_garden_max_capacity(garden_data.get("tier", "rare"))
    if current_plant_count + quantity > max_capacity:
        remaining_capacity = max_capacity - current_plant_count
        await ctx.send(f"❌ Your garden can only hold **{max_capacity}** total plants!\n"
                      f"Current: **{current_plant_count}** plants\n"
                      f"Trying to plant: **{quantity}** seeds\n"
                      f"Available space: **{remaining_capacity}** seeds\n\n"
                      f"💡 Harvest some plants first with `P!garden harvest all` to make space, or upgrade your garden tier!")
        return
    
    # Check if user has enough seeds
    current_seeds = chi_data[user_id]["garden_inventory"].get(plant_name, 0)
    
    # Handle legacy "owned" values - convert to 0 (they need to buy new seeds)
    if current_seeds == "owned":
        current_seeds = 0
        chi_data[user_id]["garden_inventory"][plant_name] = 0
        save_data()
    
    if current_seeds < quantity:
        await ctx.send(f"❌ You don't have enough **{plant_name}** seeds!\n"
                      f"You have **{current_seeds}**, need **{quantity}**\n"
                      f"Buy more from `P!garden shop`")
        return
    
    # Consume the seeds
    chi_data[user_id]["garden_inventory"][plant_name] = current_seeds - quantity
    save_data()
    
    # Plant the seeds (multiple times)
    seed_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
    for _ in range(quantity):
        garden_data["plants"].append({
            "name": plant_name,
            "planted_at": datetime.utcnow().timestamp()
        })
    save_gardens()
    schedule_db_sync(garden_user_id=int(user_id))  # Immediate sync to database
    
    has_fertilizer = chi_data[user_id]["garden_inventory"].get("Fertilizer Bag", 0) > 0
    garden_tier = garden_data.get("tier", "rare")
    grow_minutes = calculate_grow_time(seed_info["grow_time_minutes"], has_fertilizer, garden_tier, user_id, plant_name, garden_data)
    
    # Get pet bonuses for display
    pet_bonuses = get_pet_bonuses(user_id)
    pet_growth_bonus = pet_bonuses["growth_speed"]
    
    # Check if watering bonus is active
    last_watered = garden_data.get("last_watered", {}).get(plant_name, 0)
    current_time = time.time()
    time_since_water = current_time - last_watered
    is_watered = time_since_water < 86400  # 24 hours
    
    tier_bonus = GARDEN_TIERS[garden_tier]["speed_bonus"]
    tier_text = f" + {int(tier_bonus*100)}% tier bonus" if tier_bonus > 0 else ""
    fertilizer_text = " + 25% fertilizer" if has_fertilizer else ""
    pet_text = f" + {int(pet_growth_bonus*100)}% pet bonus" if pet_growth_bonus > 0 else ""
    water_text = " + 5% watering 💧" if is_watered else ""
    bonus_text = (tier_text + fertilizer_text + pet_text + water_text) if (tier_text or fertilizer_text or pet_text or water_text) else ""
    quantity_text = f"{quantity}x " if quantity > 1 else ""
    remaining_seeds = chi_data[user_id]["garden_inventory"][plant_name]
    
    await ctx.send(f"🌱 Planted **{quantity_text}{seed_info['emoji']} {plant_name}**!\n"
                  f"Growth time: **{grow_minutes:.1f} minutes**{bonus_text}\n"
                  f"Harvest reward: **+{seed_info['harvest_chi']} chi** each\n"
                  f"💡 Harvest to get seeds back (10% chance of bonus seed!)\n"
                  f"🌱 Remaining seeds: **{remaining_seeds}**")

@garden.command(name="water")
async def garden_water(ctx, *, plant_name: str = ""):
    """Water your plants (currently decorative)"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    garden_data = gardens_data["gardens"][user_id]
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    # Check if user has watering can
    has_bucket = chi_data[user_id]["garden_inventory"].get("Watering Bucket", 0) > 0
    has_golden = chi_data[user_id]["garden_inventory"].get("Golden Watering Can", 0) > 0
    
    if not has_bucket and not has_golden:
        await ctx.send("❌ You need a **Watering Bucket** or **Golden Watering Can** to water plants! Buy one from `P!garden shop`.")
        return
    
    # Check if garden event is active
    if is_garden_event_active():
        await ctx.send("✨ Your plants are already blessed by the spiritual journey! No watering needed.")
        return
    
    if not plant_name:
        await ctx.send("❌ Please specify which plant to water! Usage: `P!garden water <plant_name>`")
        return
    
    # Find the plant
    plant_found = None
    for plant in garden_data["plants"]:
        if plant["name"].lower() == plant_name.lower():
            plant_found = plant
            break
    
    if not plant_found:
        await ctx.send(f"❌ You don't have a **{plant_name}** planted!")
        return
    
    # Water the plant
    last_watered = garden_data["last_watered"].get(plant_name, 0)
    current_time = time.time()
    time_since_water = current_time - last_watered
    
    if time_since_water < 86400:  # 24 hours
        hours_left = (86400 - time_since_water) / 3600
        await ctx.send(f"💧 This plant was recently watered! Wait **{hours_left:.1f} hours** before watering again.")
        return
    
    garden_data["last_watered"][plant_name] = current_time
    save_gardens()
    schedule_db_sync(garden_user_id=int(user_id))  # Immediate sync to database
    
    seed_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
    can_type = "Golden Watering Can" if has_golden else "Watering Bucket"
    await ctx.send(f"💧 Watered **{seed_info['emoji']} {plant_name}** with your {can_type}!\n"
                  f"✨ This plant will grow **5% faster** for the next 24 hours! 🌿")

@garden.command(name="fertilize")
async def garden_fertilize(ctx):
    """Use Fertilizer Bag to speed up all plant growth (10 uses max)"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    if "fertilizer_uses" not in chi_data[user_id]:
        chi_data[user_id]["fertilizer_uses"] = 0
    
    # Check if user has fertilizer bag
    has_fertilizer = chi_data[user_id]["garden_inventory"].get("Fertilizer Bag", 0) > 0
    
    if not has_fertilizer:
        await ctx.send("❌ You don't have a **Fertilizer Bag**! Buy one from `P!garden shop` for 500 chi.")
        return
    
    # Check fertilizer uses
    uses = chi_data[user_id]["fertilizer_uses"]
    
    if uses >= 10:
        await ctx.send("❌ Your **Fertilizer Bag** is empty! (10/10 uses)\n💡 Buy a new one from `P!garden shop` for 500 chi.")
        # Remove depleted fertilizer
        chi_data[user_id]["garden_inventory"]["Fertilizer Bag"] = 0
        chi_data[user_id]["fertilizer_uses"] = 0
        save_data()
        return
    
    # Use 10% of fertilizer (1 use out of 10)
    chi_data[user_id]["fertilizer_uses"] += 1
    uses_remaining = 10 - chi_data[user_id]["fertilizer_uses"]
    save_data()
    
    embed = discord.Embed(
        title="🌿 Fertilizer Applied!",
        description="Your plants will now grow **25% faster**!",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Fertilizer Bag Status",
        value=f"🧪 **{uses_remaining}/10 uses remaining**",
        inline=False
    )
    
    if uses_remaining == 0:
        embed.add_field(
            name="⚠️ Bag Empty",
            value="Your Fertilizer Bag is now empty. Buy a new one from `P!garden shop`!",
            inline=False
        )
    
    await ctx.send(embed=embed)

@garden.command(name="harvest")
async def garden_harvest(ctx, *, plant_name: str = ""):
    """Harvest mature plants for chi"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    if not plant_name:
        await ctx.send("❌ Please specify which plant to harvest! Usage: `P!garden harvest <plant_name>`")
        return
    
    garden_data = gardens_data["gardens"][user_id]
    
    # Find the plant
    plant_found = None
    plant_index = -1
    for i, plant in enumerate(garden_data["plants"]):
        if plant["name"].lower() == plant_name.lower():
            plant_found = plant
            plant_index = i
            break
    
    if not plant_found:
        await ctx.send(f"❌ You don't have a **{plant_name}** planted!")
        return
    
    # Check if plant is ready
    seed_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
    planted_time = datetime.fromtimestamp(plant_found["planted_at"])
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    has_fertilizer = chi_data[user_id]["garden_inventory"].get("Fertilizer Bag", 0) > 0
    garden_tier = garden_data.get("tier", "rare")
    grow_minutes = calculate_grow_time(seed_info["grow_time_minutes"], has_fertilizer, garden_tier, user_id, plant_name, garden_data)
    ready_time = planted_time + timedelta(minutes=grow_minutes)
    
    is_ready = datetime.utcnow() >= ready_time or is_garden_event_active()
    
    if not is_ready:
        time_left = ready_time - datetime.utcnow()
        minutes_left = int(time_left.total_seconds() / 60)
        await ctx.send(f"🌱 **{plant_name}** is still growing! Wait **{minutes_left} minutes**.")
        return
    
    # Harvest the plant
    # Calculate chi reward with garden level bonus AND pet bonus AND tool bonuses
    base_chi = seed_info["harvest_chi"]
    garden_level = garden_data.get("level", 1)
    level_bonus = min((garden_level - 1) * 0.10, 0.50)  # +10% per level, max +50%
    
    # Apply pet chi yield bonus
    pet_bonuses = get_pet_bonuses(ctx.author.id)
    pet_chi_bonus = pet_bonuses["chi_yield"]
    
    # Apply tool bonuses (percentage + flat)
    tool_harvest_bonus = 0.0
    tool_flat_bonus = 0
    user_tools = chi_data[user_id].get("garden_tools", {})
    for tool_key, quantity in user_tools.items():
        if quantity > 0 and tool_key in GARDEN_TOOLS:
            tool = GARDEN_TOOLS[tool_key]
            tool_harvest_bonus += tool["harvest_bonus_percent"] / 100.0  # Convert % to decimal
            tool_flat_bonus += tool["flat_chi_bonus"]
    
    # Calculate total: base * (1 + all % bonuses) + flat bonuses
    total_chi = int(base_chi * (1 + level_bonus + pet_chi_bonus + tool_harvest_bonus) + tool_flat_bonus)
    
    update_chi(ctx.author.id, total_chi)
    
    # Remove the harvested plant (don't auto-replant)
    garden_data["plants"].pop(plant_index)
    
    # Give back seed + track harvest count for bonus seeds (1-5 bonus every 3 harvest COMMANDS)
    import random
    base_seeds = 1
    
    # Initialize harvest command counter if not exists
    if "harvest_command_count" not in chi_data[user_id]:
        chi_data[user_id]["harvest_command_count"] = 0
    
    # Increment harvest COMMAND count (not individual plants)
    chi_data[user_id]["harvest_command_count"] += 1
    
    # Only give bonus seeds every 3 harvest commands (3rd, 6th, 9th, etc.)
    bonus_seeds = 0
    if chi_data[user_id]["harvest_command_count"] % 3 == 0:
        bonus_seeds = random.randint(1, 5)  # 1-5 bonus seeds every 3 harvest commands
    
    seeds_returned = base_seeds + bonus_seeds
    
    # Add seeds back to inventory
    current_seeds = chi_data[user_id]["garden_inventory"].get(plant_name, 0)
    # Handle legacy "owned" values
    if current_seeds == "owned":
        current_seeds = 0
    chi_data[user_id]["garden_inventory"][plant_name] = current_seeds + seeds_returned
    
    # Initialize inventory if needed
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    # Winter Wonderland - Garden herb ingredient drops WITH PET BONUSES!
    ingredient_drops = []
    garden_tier = garden_data.get("tier", "rare")
    pet_rare_bonus = pet_bonuses["rare_drop"]  # Already calculated above
    
    # Common herbs (60% + pet bonus chance for 1-2 items from any harvest)
    if random.random() < (0.60 + pet_rare_bonus):
        herb_count = random.randint(1, 2)
        common_herbs = ["moonpetal", "winterleaf", "sunbloom"]
        herb_key = random.choice(common_herbs)
        chi_data[user_id]["inventory"][herb_key] = chi_data[user_id]["inventory"].get(herb_key, 0) + herb_count
        herb_data = INGREDIENT_CATALOG.get(herb_key, {})
        ingredient_drops.append(f"{herb_data.get('emoji', '🌙')} {herb_key.replace('_', ' ').title()} x{herb_count}")
    
    # Moonflower (20% + pet bonus chance from any harvest)
    if random.random() < (0.20 + pet_rare_bonus):
        chi_data[user_id]["inventory"]["moonflower"] = chi_data[user_id]["inventory"].get("moonflower", 0) + 1
        ingredient_drops.append("🌙 Moonflower")
    
    # Chi Blossom (10% + pet bonus from legendary+ gardens)
    if garden_tier in ["legendary", "eternal"] and random.random() < (0.10 + pet_rare_bonus):
        chi_data[user_id]["inventory"]["chi_blossom"] = chi_data[user_id]["inventory"].get("chi_blossom", 0) + 1
        ingredient_drops.append("🌸 Chi Blossom")
    
    # Rare herbs (15% from eternal gardens only, 1-2 items)
    if garden_tier == "eternal" and random.random() < 0.15:
        herb_count = random.randint(1, 2)
        chi_data[user_id]["inventory"]["emberroot"] = chi_data[user_id]["inventory"].get("emberroot", 0) + herb_count
        herb_data = INGREDIENT_CATALOG.get("emberroot", {})
        ingredient_drops.append(f"{herb_data.get('emoji', '🔥')} Emberroot x{herb_count}")
    
    save_data()
    save_gardens()
    schedule_db_sync(user_id=int(user_id), garden_user_id=int(user_id))  # Immediate sync to database
    
    event_bonus = " (Spiritual Journey Boost!)" if is_garden_event_active() else ""
    level_bonus_text = f" (+{int(level_bonus * 100)}% from garden level {garden_level})" if level_bonus > 0 else ""
    pet_bonus_text = f" (+{int(pet_chi_bonus * 100)}% pet bonus 🐾)" if pet_chi_bonus > 0 else ""
    bonus_seed_text = f" 🎁 **+{bonus_seeds} BONUS!**" if bonus_seeds > 0 else ""
    ingredient_text = f"\n🧪 Found: {', '.join(ingredient_drops)}" if ingredient_drops else ""
    
    await ctx.send(f"✨ Harvested **{seed_info['emoji']} {plant_name}**!\n"
                  f"💚 Gained **{total_chi} chi**{level_bonus_text}{pet_bonus_text}{event_bonus}\n"
                  f"🌱 Received **{seeds_returned} seed(s)**{bonus_seed_text}{ingredient_text}")

@garden.command(name="harvestall")
async def garden_harvest_all(ctx, *, plant_name: str = ""):
    """Harvest all plants of a specific type at once"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    if not plant_name:
        await ctx.send("❌ Please specify which plant to harvest! Usage: `P!garden harvestall <plant_name>`")
        return
    
    garden_data = gardens_data["gardens"][user_id]
    
    # Find ALL plants of this type
    matching_plants = []
    for i, plant in enumerate(garden_data["plants"]):
        if plant["name"].lower() == plant_name.lower():
            matching_plants.append((i, plant))
    
    if not matching_plants:
        await ctx.send(f"❌ You don't have any **{plant_name}** planted!")
        return
    
    # Verify the plant exists in shop
    if plant_name not in GARDEN_SHOP_ITEMS["seeds"]:
        await ctx.send(f"❌ '{plant_name}' is not a valid seed!")
        return
    
    seed_info = GARDEN_SHOP_ITEMS["seeds"][plant_name]
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    # CRITICAL: Ensure garden_inventory is a dict, not a corrupted string
    if not isinstance(chi_data[user_id]["garden_inventory"], dict):
        print(f"⚠️ CRITICAL ERROR: garden_inventory corrupted for user {user_id}! Type: {type(chi_data[user_id]['garden_inventory']).__name__}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
    
    has_fertilizer = chi_data[user_id]["garden_inventory"].get("Fertilizer Bag", 0) > 0
    garden_tier = garden_data.get("tier", "rare")
    grow_minutes = calculate_grow_time(seed_info["grow_time_minutes"], has_fertilizer, garden_tier, user_id, plant_name, garden_data)
    
    # Check which plants are ready
    ready_plants = []
    not_ready_plants = []
    
    for index, plant in matching_plants:
        planted_time = datetime.fromtimestamp(plant["planted_at"])
        ready_time = planted_time + timedelta(minutes=grow_minutes)
        is_ready = datetime.utcnow() >= ready_time or is_garden_event_active()
        
        if is_ready:
            ready_plants.append(index)
        else:
            not_ready_plants.append((index, ready_time))
    
    if not ready_plants:
        # None are ready
        next_ready_time = min(not_ready_plants, key=lambda x: x[1])[1]
        time_left = next_ready_time - datetime.utcnow()
        minutes_left = int(time_left.total_seconds() / 60)
        await ctx.send(f"🌱 None of your **{plant_name}** plants are ready yet!\n"
                      f"Next harvest in **{minutes_left} minutes**.")
        return
    
    # Calculate total chi with garden level bonus
    base_chi = seed_info["harvest_chi"]
    garden_level = garden_data.get("level", 1)
    level_bonus = min((garden_level - 1) * 0.10, 0.50)  # +10% per level, max +50%
    chi_per_plant = int(base_chi * (1 + level_bonus))
    total_chi = chi_per_plant * len(ready_plants)
    
    # Harvest all ready plants
    update_chi(ctx.author.id, total_chi)
    
    # Remove all harvested plants and give back seeds (1-5 bonus every 3 harvest COMMANDS)
    import random
    
    # Initialize harvest command counter if not exists
    if "harvest_command_count" not in chi_data[user_id]:
        chi_data[user_id]["harvest_command_count"] = 0
    
    # Increment harvest COMMAND count once per command (not per plant)
    chi_data[user_id]["harvest_command_count"] += 1
    
    # Check if this is a bonus harvest (every 3rd command)
    bonus_seeds = 0
    if chi_data[user_id]["harvest_command_count"] % 3 == 0:
        bonus_seeds = random.randint(1, 5)  # 1-5 bonus seeds every 3 harvest commands
    
    # Give base seeds + bonus (if applicable)
    total_seeds_returned = len(ready_plants) + bonus_seeds
    
    # Remove plants in reverse order to avoid index issues
    for index in sorted(ready_plants, reverse=True):
        garden_data["plants"].pop(index)
    
    # Add seeds back to inventory
    current_seeds = chi_data[user_id]["garden_inventory"].get(plant_name, 0)
    # Handle legacy "owned" values
    if current_seeds == "owned":
        current_seeds = 0
    chi_data[user_id]["garden_inventory"][plant_name] = current_seeds + total_seeds_returned
    
    # Initialize ingredients if needed
    if "ingredients" not in chi_data[user_id]:
        chi_data[user_id]["ingredients"] = {}
    
    # Random ingredient drops based on garden tier (each plant has a chance)
    ingredient_drops = {}
    garden_tier = garden_data.get("tier", "rare")
    
    for _ in range(len(ready_plants)):
        # Common ingredient: Moonflower (20% chance per plant)
        if random.random() < 0.20:
            ingredient_drops["Moonflower"] = ingredient_drops.get("Moonflower", 0) + 1
            chi_data[user_id]["ingredients"]["I3"] = chi_data[user_id]["ingredients"].get("I3", 0) + 1
        
        # Uncommon ingredient: Chi Blossom (10% from legendary+ gardens)
        if garden_tier in ["legendary", "eternal"] and random.random() < 0.10:
            ingredient_drops["Chi Blossom"] = ingredient_drops.get("Chi Blossom", 0) + 1
            chi_data[user_id]["ingredients"]["I6"] = chi_data[user_id]["ingredients"].get("I6", 0) + 1
        
        # Rare ingredient: Eternal Dewdrop (5% from eternal gardens only)
        if garden_tier == "eternal" and random.random() < 0.05:
            ingredient_drops["Eternal Dewdrop"] = ingredient_drops.get("Eternal Dewdrop", 0) + 1
            chi_data[user_id]["ingredients"]["I8"] = chi_data[user_id]["ingredients"].get("I8", 0) + 1
    
    save_data()
    save_gardens()
    schedule_db_sync(user_id=int(user_id), garden_user_id=int(user_id))  # Immediate sync to database
    
    event_bonus = " (Spiritual Journey Boost!)" if is_garden_event_active() else ""
    level_bonus_text = f" (+{int(level_bonus * 100)}% from garden level {garden_level})" if level_bonus > 0 else ""
    bonus_seed_text = f" 🎁 **+{bonus_seeds} BONUS!**" if bonus_seeds > 0 else ""
    
    result_message = f"✨ **MASS HARVEST!**\n"
    result_message += f"🌿 Harvested **{len(ready_plants)}x {seed_info['emoji']} {plant_name}**!\n"
    result_message += f"💚 Gained **{total_chi} chi** total ({chi_per_plant} chi each){level_bonus_text}{event_bonus}\n"
    result_message += f"🌱 Received **{total_seeds_returned} seed(s)**{bonus_seed_text}"
    
    if ingredient_drops:
        ingredient_text = ", ".join([f"🧪 {qty}x {ing_emoji} {name}" for name, (ing_emoji, qty) in {
            "Moonflower": ("🌙", ingredient_drops.get("Moonflower", 0)),
            "Chi Blossom": ("🌸", ingredient_drops.get("Chi Blossom", 0)),
            "Eternal Dewdrop": ("💧", ingredient_drops.get("Eternal Dewdrop", 0))
        }.items() if qty > 0])
        result_message += f"\n{ingredient_text}"
    
    if not_ready_plants:
        result_message += f"\n\n⏳ {len(not_ready_plants)} plant(s) still growing"
    
    await ctx.send(result_message)

@garden.command(name="seed")
async def garden_seed_info(ctx, *, seed_name: str = ""):
    """Get information about a specific seed"""
    if not seed_name:
        await ctx.send("❌ Please specify a seed name! Usage: `P!garden seed <seed_name>`")
        return
    
    if seed_name not in GARDEN_SHOP_ITEMS["seeds"]:
        await ctx.send(f"❌ '{seed_name}' is not a valid seed!")
        return
    
    seed_info = GARDEN_SHOP_ITEMS["seeds"][seed_name]
    
    embed = discord.Embed(
        title=f"{seed_info['emoji']} {seed_name}",
        description=seed_info["description"],
        color=discord.Color.green()
    )
    embed.add_field(name="💰 Cost", value=f"{seed_info['cost']} chi", inline=True)
    embed.add_field(name="⏱️ Growth Time", value=f"{seed_info['grow_time_minutes']} minutes", inline=True)
    embed.add_field(name="✨ Harvest Reward", value=f"+{seed_info['harvest_chi']} chi", inline=True)
    
    await ctx.send(embed=embed)

@garden.command(name="about")
async def garden_about(ctx, user: discord.Member = None):
    """View garden information for yourself or another user"""
    target = user or ctx.author
    user_id = str(target.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send(f"🌸 {target.display_name} doesn't have a garden yet!")
        return
    
    garden_data = gardens_data["gardens"][user_id]
    tier_info = GARDEN_TIERS[garden_data["tier"]]
    
    # Initialize garden_inventory if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    if "garden_inventory" not in chi_data[user_id]:
        chi_data[user_id]["garden_inventory"] = {}
    
    embed = discord.Embed(
        title=f"{tier_info['emoji']} {target.display_name}'s {tier_info['name']}",
        description=f"**Level {garden_data['level']}** Garden",
        color=discord.Color.green()
    )
    
    # Count plants
    total_plants = len(garden_data["plants"])
    ready_plants = 0
    for plant in garden_data["plants"]:
        plant_info = GARDEN_SHOP_ITEMS["seeds"][plant["name"]]
        planted_time = datetime.fromtimestamp(plant["planted_at"])
        
        # Ensure garden_inventory is a dict before accessing it
        garden_inv = chi_data[user_id].get("garden_inventory", {})
        if not isinstance(garden_inv, dict):
            chi_data[user_id]["garden_inventory"] = {}
            garden_inv = {}
        has_fertilizer = garden_inv.get("Fertilizer Bag", 0) > 0
        garden_tier = garden_data.get("tier", "rare")
        plant_name_var = plant.get("name")
        grow_minutes = calculate_grow_time(plant_info["grow_time_minutes"], has_fertilizer, garden_tier, user_id, plant_name_var, garden_data)
        ready_time = planted_time + timedelta(minutes=grow_minutes)
        
        if datetime.utcnow() >= ready_time or is_garden_event_active():
            ready_plants += 1
    
    embed.add_field(name="🌿 Plants", value=f"{total_plants} total\n{ready_plants} ready to harvest", inline=True)
    
    # Count inventory items (handle both numeric and "owned" string values)
    # CRITICAL: Ensure garden_inventory is a dict before calling .items()
    garden_inv = chi_data[user_id]["garden_inventory"]
    if not isinstance(garden_inv, dict):
        print(f"⚠️ ERROR: garden_inventory is {type(garden_inv).__name__}, not dict! Resetting for user {user_id}")
        chi_data[user_id]["garden_inventory"] = {}
        save_data()
        inventory_count = 0
    else:
        inventory_count = len([k for k, v in garden_inv.items() if (isinstance(v, int) and v > 0) or v == "owned"])
    
    embed.add_field(name="📦 Inventory Items", value=str(inventory_count), inline=True)
    
    await ctx.send(embed=embed)

@garden.command(name="upgrade")
async def garden_upgrade(ctx):
    """Upgrade your garden tier (Pond Garden → Chi Grove → Hépíng sēnlín)"""
    user_id = str(ctx.author.id)
    
    if user_id not in gardens_data["gardens"]:
        await ctx.send("🌸 You don't have a garden yet! Use `P!garden` to create one for 50 chi.")
        return
    
    # Initialize chi_data if needed
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0}
    
    garden_data = gardens_data["gardens"][user_id]
    current_tier = garden_data.get("tier", "rare")
    current_tier_info = GARDEN_TIERS[current_tier]
    
    # Determine next tier
    tier_progression = ["rare", "legendary", "eternal"]
    current_index = tier_progression.index(current_tier)
    
    if current_index >= len(tier_progression) - 1:
        await ctx.send(f"✨ Your **{current_tier_info['emoji']} {current_tier_info['name']}** is already at the maximum tier!")
        return
    
    next_tier = tier_progression[current_index + 1]
    next_tier_info = GARDEN_TIERS[next_tier]
    
    # Check costs
    chi_cost = next_tier_info["upgrade_cost_chi"]
    rebirth_cost = next_tier_info["upgrade_cost_rebirths"]
    
    user_chi = chi_data[user_id].get("chi", 0)
    user_rebirths = chi_data[user_id].get("rebirths", 0)
    
    # Build cost display and check if user can afford
    cost_parts = []
    can_afford = True
    
    if chi_cost and chi_cost > 0:
        cost_parts.append(f"**{chi_cost} chi**")
        if user_chi < chi_cost:
            can_afford = False
    
    if rebirth_cost and rebirth_cost > 0:
        cost_parts.append(f"**{rebirth_cost} rebirth(s)**")
        if user_rebirths < rebirth_cost:
            can_afford = False
    
    cost_display = " + ".join(cost_parts)
    
    if not can_afford:
        await ctx.send(f"❌ You cannot afford the upgrade to **{next_tier_info['emoji']} {next_tier_info['name']}**!\n\n"
                      f"**Cost:** {cost_display}\n"
                      f"**You have:** {user_chi} chi, {user_rebirths} rebirth(s)")
        return
    
    # Deduct costs
    if chi_cost and chi_cost > 0:
        chi_data[user_id]["chi"] -= chi_cost
    if rebirth_cost and rebirth_cost > 0:
        chi_data[user_id]["rebirths"] -= rebirth_cost
    
    # Upgrade garden tier
    garden_data["tier"] = next_tier
    save_data()
    save_gardens()
    
    # Unlock tier 3 achievement
    if next_tier == "eternal":
        await unlock_achievement(ctx.author.id, "tier3_garden", ctx.guild)
    
    # Build benefits list
    benefits = []
    benefits.append(f"📦 **Max Capacity:** {next_tier_info['max_capacity']} plants (+{next_tier_info['max_capacity'] - current_tier_info['max_capacity']})")
    benefits.append(f"⚡ **Growth Speed:** {int(next_tier_info['speed_bonus']*100)}% faster")
    if next_tier_info.get("unlocks_seed"):
        benefits.append(f"🌱 **Unlocked Seed:** {next_tier_info['unlocks_seed']}")
    
    await ctx.send(f"✨ **Garden Tier Upgraded!**\n"
                  f"{current_tier_info['emoji']} **{current_tier_info['name']}** → {next_tier_info['emoji']} **{next_tier_info['name']}**\n\n"
                  f"**Benefits:**\n" + "\n".join(benefits) + f"\n\n"
                  f"**Cost:** {cost_display}")

@bot.command(name="trade")
async def trade(ctx, trade_type: str = "", target: discord.Member = None, *, amount_or_item: str = ""):
    """Trade chi, artifacts, or pets with another user"""
    user_id = str(ctx.author.id)
    
    if not trade_type or not target or not amount_or_item:
        await ctx.send("❌ Usage: `P!trade <chi/artifact/pet> <@user> <amount/item_name>`\n"
                      "Examples:\n"
                      "`P!trade chi @user 100`\n"
                      "`P!trade artifact @user rare_artifact_123`\n"
                      "`P!trade pet @user PetName`")
        return
    
    if target.id == ctx.author.id:
        await ctx.send("❌ You can't trade with yourself!")
        return
    
    if target.bot:
        await ctx.send("❌ You can't trade with bots!")
        return
    
    trade_type = trade_type.lower()
    
    if trade_type == "chi":
        try:
            amount = int(amount_or_item)
        except ValueError:
            await ctx.send("❌ Please specify a valid chi amount!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        if user_id not in chi_data or chi_data[user_id].get("chi", 0) < amount:
            await ctx.send(f"❌ You don't have {amount} chi to trade!")
            return
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="💱 Confirm Trade",
            description=f"{ctx.author.mention} wants to trade **{amount} chi** to {target.mention}\n\n"
                       f"React with ✅ to confirm or ❌ to cancel.",
            color=discord.Color.orange()
        )
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Trade cancelled.")
                return
            
            # Execute trade
            target_id = str(target.id)
            if target_id not in chi_data:
                chi_data[target_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": [], "pets": [], "trade_requests": [], "active_pet": None}
            
            chi_data[user_id]["chi"] -= amount
            chi_data[target_id]["chi"] += amount
            save_data()
            
            success_embed = discord.Embed(
                title="✅ Trade Complete!",
                description=f"{ctx.author.mention} traded **{amount} chi** to {target.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=success_embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Trade confirmation timed out.")
    
    elif trade_type == "artifact":
        # Find artifact by name
        if user_id not in chi_data or "artifacts" not in chi_data[user_id]:
            await ctx.send("❌ You don't have any artifacts to trade!")
            return
        
        user_artifacts = chi_data[user_id]["artifacts"]
        if not user_artifacts:
            await ctx.send("❌ You don't have any artifacts to trade!")
            return
        
        artifact_to_trade = None
        for artifact in user_artifacts:
            if artifact["name"].lower() == amount_or_item.lower() or artifact["id"].lower() == amount_or_item.lower():
                artifact_to_trade = artifact
                break
        
        if not artifact_to_trade:
            await ctx.send(f"❌ You don't own an artifact named '{amount_or_item}'!")
            return
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="💱 Confirm Artifact Trade",
            description=f"{ctx.author.mention} wants to trade:\n"
                       f"{artifact_to_trade['emoji']} **{artifact_to_trade['name']}** ({artifact_to_trade['tier']})\n"
                       f"to {target.mention}\n\n"
                       f"React with ✅ to confirm or ❌ to cancel.",
            color=discord.Color.purple()
        )
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Trade cancelled.")
                return
            
            # Execute trade
            target_id = str(target.id)
            if target_id not in chi_data:
                chi_data[target_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": [], "pets": [], "trade_requests": [], "active_pet": None}
            if "artifacts" not in chi_data[target_id]:
                chi_data[target_id]["artifacts"] = []
            
            # Remove from sender, add to receiver
            chi_data[user_id]["artifacts"].remove(artifact_to_trade)
            chi_data[target_id]["artifacts"].append(artifact_to_trade)
            save_data()
            
            success_embed = discord.Embed(
                title="✅ Artifact Trade Complete!",
                description=f"{ctx.author.mention} traded {artifact_to_trade['emoji']} **{artifact_to_trade['name']}** to {target.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=success_embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Trade confirmation timed out.")
    
    elif trade_type == "pet":
        # Find pet by name or type
        if user_id not in chi_data or "pets" not in chi_data[user_id]:
            await ctx.send("❌ You don't have any pets to trade!")
            return
        
        user_pets = chi_data[user_id]["pets"]
        if not user_pets:
            await ctx.send("❌ You don't have any pets to trade!")
            return
        
        # Find the pet
        pet_to_trade = None
        search_name = amount_or_item.lower()
        for pet in user_pets:
            pet_name = (pet.get("nickname") or pet["name"]).lower()
            if pet_name == search_name or pet["type"].lower() == search_name:
                pet_to_trade = pet
                break
        
        if not pet_to_trade:
            await ctx.send(f"❌ You don't own a pet named '{amount_or_item}'!")
            return
        
        # Can't trade active pet
        if chi_data[user_id].get("active_pet") == pet_to_trade["type"]:
            await ctx.send(f"❌ You can't trade your active pet! Use `P!pet switch <name>` to switch first.")
            return
        
        pet_display_name = pet_to_trade.get("nickname") or pet_to_trade["name"]
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="💱 Confirm Pet Trade",
            description=f"{ctx.author.mention} wants to trade:\n"
                       f"{pet_to_trade['emoji']} **{pet_display_name}** ({pet_to_trade['name']})\n"
                       f"❤️ HP: {pet_to_trade['health']:,}/{pet_to_trade['max_health']:,}\n"
                       f"⭐ Level: {pet_to_trade['level']}\n"
                       f"to {target.mention}\n\n"
                       f"React with ✅ to confirm or ❌ to cancel.",
            color=discord.Color.purple()
        )
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ Trade cancelled.")
                return
            
            # Execute trade
            target_id = str(target.id)
            if target_id not in chi_data:
                chi_data[target_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": [], "artifacts": [], "pets": [], "trade_requests": [], "active_pet": None}
            if "pets" not in chi_data[target_id]:
                chi_data[target_id]["pets"] = []
            
            # Remove from sender, add to receiver
            chi_data[user_id]["pets"].remove(pet_to_trade)
            chi_data[target_id]["pets"].append(pet_to_trade)
            save_data()
            
            success_embed = discord.Embed(
                title="✅ Pet Trade Complete!",
                description=f"{ctx.author.mention} traded {pet_to_trade['emoji']} **{pet_display_name}** to {target.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=success_embed)
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Trade confirmation timed out.")
    
    else:
        await ctx.send("❌ Invalid trade type! Use `chi`, `artifact`, or `pet`")


# ==================== PET FOOD SHOP ====================

@bot.command(name="petfood")
async def petfood_shop(ctx):
    """🍱 Pet Food Shop - Buy food for your pets!"""
    user_id = str(ctx.author.id)
    
    # Initialize user data
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "pet_food" not in chi_data[user_id]:
        chi_data[user_id]["pet_food"] = {}
    
    embed = discord.Embed(
        title="🍱 Pet Food Emporium",
        description="Welcome! Purchase nutritious food to keep your pets healthy and strong!",
        color=discord.Color.orange()
    )
    
    # Group foods by pet type
    food_categories = {
        "Ox Food 🐂": [],
        "Snake Food 🐍": [],
        "Tiger Food 🐅": [],
        "Panda Food 🐼": [],
        "Dragon Food 🐉": [],
        "Universal Food 🌟": []
    }
    
    for food_key, food_data in PET_FOOD.items():
        emoji = food_data['emoji']
        name = food_data['name']
        price = food_data['price']
        healing = food_data['healing']
        desc = food_data['description']
        
        food_text = f"{emoji} **{name}** - {price:,} chi\n❤️ Heals {healing} HP\n*{desc}*"
        
        # Categorize
        primary_for = food_data.get('primary_for')
        if primary_for == 'ox':
            food_categories["Ox Food 🐂"].append(food_text)
        elif primary_for == 'snake':
            food_categories["Snake Food 🐍"].append(food_text)
        elif primary_for == 'tiger':
            food_categories["Tiger Food 🐅"].append(food_text)
        elif primary_for == 'panda':
            food_categories["Panda Food 🐼"].append(food_text)
        elif primary_for == 'dragon':
            food_categories["Dragon Food 🐉"].append(food_text)
        else:
            food_categories["Universal Food 🌟"].append(food_text)
    
    # Add categories to embed
    for category, foods in food_categories.items():
        if foods:
            embed.add_field(
                name=category,
                value="\n\n".join(foods),
                inline=False
            )
    
    # Show user's current food inventory
    inventory = chi_data[user_id].get("pet_food", {})
    if inventory:
        inv_items = []
        for food_key, count in sorted(inventory.items()):
            if count > 0 and food_key in PET_FOOD:
                inv_items.append(f"{PET_FOOD[food_key]['emoji']} {PET_FOOD[food_key]['name']} x{count}")
        
        if inv_items:
            embed.add_field(
                name="📦 Your Inventory",
                value="\n".join(inv_items[:10]),  # Show first 10
                inline=False
            )
    
    embed.add_field(
        name="💰 Your Chi",
        value=f"{chi_data[user_id].get('chi', 0):,} chi",
        inline=True
    )
    
    embed.set_footer(text="Use the dropdown below to purchase food! • Feed your pet with P!pet feed <food>")
    
    # Create dropdown for purchasing
    options = []
    for food_key, food_data in sorted(PET_FOOD.items(), key=lambda x: x[1]['price']):
        options.append(
            discord.SelectOption(
                label=f"{food_data['name']} - {food_data['price']:,} chi",
                value=food_key,
                description=f"❤️ {food_data['healing']} HP | {food_data['description'][:50]}",
                emoji=food_data['emoji']
            )
        )
    
    select = discord.ui.Select(
        placeholder="🛒 Choose food to purchase...",
        options=options[:25],  # Discord limit
        custom_id="petfood_purchase"
    )
    
    async def purchase_callback(interaction: discord.Interaction):
        if interaction.user.id != ctx.author.id:
            await interaction.response.send_message("❌ This isn't your shop!", ephemeral=True)
            return
        
        selected_food = interaction.data["values"][0]
        food_data = PET_FOOD[selected_food]
        
        # Check chi
        current_chi = chi_data[user_id].get("chi", 0)
        if current_chi < food_data["price"]:
            await interaction.response.send_message(
                f"❌ Not enough chi! You need **{food_data['price']:,} chi** but only have **{current_chi:,} chi**.",
                ephemeral=True
            )
            return
        
        # Purchase
        chi_data[user_id]["chi"] -= food_data["price"]
        if selected_food not in chi_data[user_id]["pet_food"]:
            chi_data[user_id]["pet_food"][selected_food] = 0
        chi_data[user_id]["pet_food"][selected_food] += 1
        
        save_data()
        
        # Confirmation
        conf_embed = discord.Embed(
            title="🎉 Purchase Complete!",
            description=f"You bought **{food_data['emoji']} {food_data['name']}**!",
            color=discord.Color.green()
        )
        conf_embed.add_field(name="💰 Spent", value=f"{food_data['price']:,} chi", inline=True)
        conf_embed.add_field(name="💵 Remaining", value=f"{chi_data[user_id]['chi']:,} chi", inline=True)
        conf_embed.add_field(name="📦 You now have", value=f"{chi_data[user_id]['pet_food'][selected_food]}x {food_data['name']}", inline=False)
        conf_embed.set_footer(text=f"Use P!pet feed {food_data['name']} to feed your pet!")
        
        await interaction.response.send_message(embed=conf_embed)
    
    select.callback = purchase_callback
    
    view = discord.ui.View(timeout=180)
    view.add_item(select)
    
    await ctx.send(embed=embed, view=view)


# ==================== PLAYER SHOP SYSTEM ====================

@bot.group(name="pshop", invoke_without_command=True)
async def pshop(ctx):
    """Player shop system - Create your own shop and sell items!"""
    user_id = str(ctx.author.id)
    
    # Check if user has a shop
    user_shop_id = None
    for shop_id, shop_data in player_shops_data["shops"].items():
        if str(shop_data["owner_id"]) == user_id:
            user_shop_id = shop_id
            break
    
    if not user_shop_id:
        embed = discord.Embed(
            title="🏪 Player Shop System",
            description="Welcome to the Player Shop System! Create your own shop and sell items to other players!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📝 Getting Started",
            value="`P!pshop create <shop name>` - Create your shop",
            inline=False
        )
        embed.add_field(
            name="🔍 Browse Shops",
            value=(
                "`P!pshop list` - View all shops\n"
                "`P!pshop search <item>` - Find specific items\n"
                "`P!pshop view <shop_id>` - View a shop's listings"
            ),
            inline=False
        )
        embed.set_footer(text="💡 TIP: Create a shop to start selling your inventory items!")
        await ctx.send(embed=embed)
    else:
        # Show user's own shop
        await view_shop_display(ctx, user_shop_id, is_owner=True)

async def view_shop_display(ctx, shop_id, is_owner=False):
    """Display a shop's information"""
    if shop_id not in player_shops_data["shops"]:
        await ctx.send("❌ Shop not found!")
        return
    
    shop = player_shops_data["shops"][shop_id]
    owner = ctx.guild.get_member(int(shop["owner_id"]))
    owner_name = owner.display_name if owner else f"User {shop['owner_id']}"
    
    embed = discord.Embed(
        title=f"🏪 {shop['name']}",
        description=f"**Owner:** {owner_name}\n**Shop ID:** {shop_id}\n**Total Sales:** {shop.get('total_sales', 0)} transactions",
        color=discord.Color.gold()
    )
    
    if not shop["listings"]:
        embed.add_field(
            name="📦 Listings",
            value="*This shop has no items for sale*",
            inline=False
        )
    else:
        # Group listings by category
        categories = {}
        for listing in shop["listings"]:
            cat = listing.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(listing)
        
        # Display listings by category
        for category, items in categories.items():
            items_text = []
            for item in items[:10]:  # Limit to 10 per category
                qty_text = f"x{item['quantity']}" if item.get('quantity', 1) > 1 else ""
                items_text.append(f"• **{item['item_name']}** {qty_text} - {item['price']:,} chi")
            
            embed.add_field(
                name=f"📦 {category}",
                value="\n".join(items_text),
                inline=False
            )
    
    if is_owner:
        embed.add_field(
            name="🛠️ Shop Management",
            value=(
                "`P!pshop sell <item> <price>` - Add item to shop\n"
                "`P!pshop remove <item>` - Remove listing\n"
                "`P!pshop stats` - View detailed statistics"
            ),
            inline=False
        )
    else:
        embed.set_footer(text=f"Use P!pshop buy {shop_id} <item> to purchase")
    
    await ctx.send(embed=embed)

@pshop.command(name="create")
async def pshop_create(ctx, *, shop_name: str = ""):
    """Create your own player shop"""
    if not shop_name:
        await ctx.send("❌ Please provide a shop name! Example: `P!pshop create Bob's Bazaar`")
        return
    
    if len(shop_name) > 50:
        await ctx.send("❌ Shop name too long! Maximum 50 characters.")
        return
    
    user_id = str(ctx.author.id)
    
    # Check if user already has a shop
    for shop_id, shop_data in player_shops_data["shops"].items():
        if str(shop_data["owner_id"]) == user_id:
            await ctx.send(f"❌ You already own a shop! View it with `P!pshop`")
            return
    
    # Check if shop name is taken
    for shop_data in player_shops_data["shops"].values():
        if shop_data["name"].lower() == shop_name.lower():
            await ctx.send("❌ A shop with this name already exists! Please choose a different name.")
            return
    
    # Create shop
    shop_id = f"S{player_shops_data['next_shop_id']}"
    player_shops_data["next_shop_id"] += 1
    
    player_shops_data["shops"][shop_id] = {
        "owner_id": user_id,
        "name": shop_name,
        "listings": [],
        "created_at": str(ctx.message.created_at),
        "total_sales": 0,
        "total_revenue": 0
    }
    
    save_player_shops()
    
    embed = discord.Embed(
        title="🎉 Shop Created!",
        description=f"**{shop_name}**\n\nYour shop is now open for business!",
        color=discord.Color.green()
    )
    embed.add_field(name="Shop ID", value=shop_id, inline=True)
    embed.add_field(name="Owner", value=ctx.author.mention, inline=True)
    embed.add_field(
        name="📝 Next Steps",
        value=(
            "1. `P!pshop sell <item> <price>` - Add items to sell\n"
            "2. `P!pshop` - View your shop anytime\n"
            "3. Customers can buy with `P!pshop buy " + shop_id + " <item>`"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Log shop creation
    await log_event(
        "Player Shop Created",
        f"**Owner:** {ctx.author.mention} ({ctx.author.name})\n**Shop Name:** {shop_name}\n**Shop ID:** {shop_id}", ctx.guild, discord.Color.gold())

@pshop.command(name="sell")
async def pshop_sell(ctx):
    """Add an item from your inventory to your shop - Interactive UI"""
    user_id = str(ctx.author.id)
    
    # Find user's shop
    user_shop_id = None
    for shop_id, shop_data in player_shops_data["shops"].items():
        if str(shop_data["owner_id"]) == user_id:
            user_shop_id = shop_id
            break
    
    if not user_shop_id:
        await ctx.send("❌ You don't have a shop! Create one with `P!pshop create <name>`")
        return
    
    # Initialize user data
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    inventory = chi_data[user_id]["inventory"]
    
    # Check if inventory has items
    if not inventory or all(qty <= 0 for qty in inventory.values()):
        await ctx.send("❌ Your inventory is empty! Buy items from shops first.")
        return
    
    # Show interactive inventory selector
    shop = player_shops_data["shops"][user_shop_id]
    embed = discord.Embed(
        title=f"🏪 Sell Items - {shop['name']}",
        description="Select an item from your inventory to list for sale.\nYou'll set the price in the next step.",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="📦 Your Inventory",
        value=f"{len([i for i in inventory.values() if i > 0])} items available",
        inline=True
    )
    embed.add_field(
        name="🏷️ Current Listings",
        value=f"{len(shop['listings'])} items listed",
        inline=True
    )
    
    view = PlayerShopInventorySelect(
        user_id,
        inventory,
        user_shop_id,
        chi_data,
        player_shops_data,
        chi_shop_data,
        save_data,
        save_player_shops
    )
    
    await ctx.send(embed=embed, view=view)

@pshop.command(name="buy")
async def pshop_buy(ctx, shop_id: str = "", *, item_name: str = ""):
    """Buy an item from a player shop"""
    if not shop_id or not item_name:
        await ctx.send("❌ Usage: `P!pshop buy <shop_id> <item>`\nExample: `P!pshop buy S1 Bamboo Sword`")
        return
    
    user_id = str(ctx.author.id)
    
    # Validate shop exists
    if shop_id not in player_shops_data["shops"]:
        await ctx.send(f"❌ Shop **{shop_id}** not found! Use `P!pshop list` to see all shops.")
        return
    
    shop = player_shops_data["shops"][shop_id]
    
    # Can't buy from own shop
    if str(shop["owner_id"]) == user_id:
        await ctx.send("❌ You can't buy from your own shop!")
        return
    
    # Find item in shop
    found_listing = None
    for listing in shop["listings"]:
        if listing["item_name"].lower() == item_name.lower():
            found_listing = listing
            break
    
    if not found_listing:
        await ctx.send(f"❌ **{item_name}** is not for sale in this shop! Use `P!pshop view {shop_id}` to see available items.")
        return
    
    # Initialize buyer data
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    buyer_chi = chi_data[user_id].get("chi", 0)
    item_price = found_listing["price"]
    
    # Check if buyer can afford
    if buyer_chi < item_price:
        await ctx.send(f"❌ Not enough chi! You need **{item_price:,} chi** but only have **{buyer_chi:,} chi**.")
        return
    
    # Process transaction
    seller_id = str(shop["owner_id"])
    if seller_id not in chi_data:
        chi_data[seller_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    
    # Transfer chi
    chi_data[user_id]["chi"] -= item_price
    chi_data[seller_id]["chi"] += item_price
    
    # Transfer item
    chi_data[user_id]["inventory"][found_listing["item_name"]] = chi_data[user_id]["inventory"].get(found_listing["item_name"], 0) + 1
    
    # Remove from shop
    shop["listings"].remove(found_listing)
    shop["total_sales"] += 1
    shop["total_revenue"] = shop.get("total_revenue", 0) + item_price
    player_shops_data["global_sales"] += 1
    
    save_data()
    save_player_shops()
    
    # Notify buyer
    embed = discord.Embed(
        title="🎉 Purchase Complete!",
        description=f"You bought **{found_listing['item_name']}** from **{shop['name']}**!",
        color=discord.Color.green()
    )
    embed.add_field(name="Price Paid", value=f"{item_price:,} chi", inline=True)
    embed.add_field(name="Remaining Chi", value=f"{chi_data[user_id]['chi']:,}", inline=True)
    embed.set_footer(text=f"Item added to your inventory! Check with P!inventory")
    
    await ctx.send(embed=embed)
    
    # Try to DM seller
    try:
        seller = ctx.guild.get_member(int(seller_id))
        if seller:
            seller_embed = discord.Embed(
                title="💰 Item Sold!",
                description=f"{ctx.author.display_name} bought **{found_listing['item_name']}** from your shop!",
                color=discord.Color.gold()
            )
            seller_embed.add_field(name="Sale Price", value=f"+{item_price:,} chi", inline=True)
            seller_embed.add_field(name="Your Chi", value=f"{chi_data[seller_id]['chi']:,}", inline=True)
            await seller.send(embed=seller_embed)
    except:
        pass  # Seller has DMs disabled
    
    # Log transaction
    await log_event(
        "Player Shop Sale",
        f"**Buyer:** {ctx.author.mention}\n**Seller:** {shop['name']} ({shop_id})\n**Item:** {found_listing['item_name']}\n**Price:** {item_price:,} chi", ctx.guild, discord.Color.gold())

@pshop.command(name="search")
async def pshop_search(ctx, *, query: str = ""):
    """Search for items across all player shops"""
    if not query:
        await ctx.send("❌ Usage: `P!pshop search <item or category>`\nExample: `P!pshop search sword`")
        return
    
    query_lower = query.lower()
    results = []
    
    # Search all shops
    for shop_id, shop in player_shops_data["shops"].items():
        for listing in shop["listings"]:
            # Check if query matches item name or category
            if query_lower in listing["item_name"].lower() or query_lower in listing.get("category", "").lower():
                results.append({
                    "shop_id": shop_id,
                    "shop_name": shop["name"],
                    "item": listing["item_name"],
                    "price": listing["price"],
                    "category": listing.get("category", "Other")
                })
    
    if not results:
        await ctx.send(f"❌ No items found matching **{query}**")
        return
    
    # Sort by price (lowest first)
    results.sort(key=lambda x: x["price"])
    
    embed = discord.Embed(
        title=f"🔍 Search Results: '{query}'",
        description=f"Found {len(results)} item(s) across {len(set(r['shop_id'] for r in results))} shop(s)",
        color=discord.Color.blue()
    )
    
    # Show top 15 results
    for i, result in enumerate(results[:15], 1):
        embed.add_field(
            name=f"{i}. {result['item']} - {result['price']:,} chi",
            value=f"🏪 {result['shop_name']} ({result['shop_id']})\n`P!pshop buy {result['shop_id']} {result['item']}`",
            inline=False
        )
    
    if len(results) > 15:
        embed.set_footer(text=f"Showing top 15 of {len(results)} results (sorted by price)")
    
    await ctx.send(embed=embed)

@pshop.command(name="list")
async def pshop_list(ctx):
    """View all active player shops"""
    if not player_shops_data["shops"]:
        await ctx.send("❌ No player shops exist yet! Create the first one with `P!pshop create <name>`")
        return
    
    embed = discord.Embed(
        title="🏪 Active Player Shops",
        description=f"Total Shops: {len(player_shops_data['shops'])} | Global Sales: {player_shops_data.get('global_sales', 0)}",
        color=discord.Color.gold()
    )
    
    # Sort shops by total sales
    sorted_shops = sorted(
        player_shops_data["shops"].items(),
        key=lambda x: x[1].get("total_sales", 0),
        reverse=True
    )
    
    for i, (shop_id, shop) in enumerate(sorted_shops[:20], 1):  # Top 20 shops
        owner = ctx.guild.get_member(int(shop["owner_id"]))
        owner_name = owner.display_name if owner else f"User {shop['owner_id']}"
        
        items_count = len(shop["listings"])
        sales = shop.get("total_sales", 0)
        
        value_text = (
            f"**Owner:** {owner_name}\n"
            f"**Items:** {items_count} | **Sales:** {sales}\n"
            f"`P!pshop view {shop_id}` to browse"
        )
        
        embed.add_field(
            name=f"{i}. {shop['name']} ({shop_id})",
            value=value_text,
            inline=False
        )
    
    if len(player_shops_data["shops"]) > 20:
        embed.set_footer(text=f"Showing top 20 of {len(player_shops_data['shops'])} shops")
    
    await ctx.send(embed=embed)

@pshop.command(name="view")
async def pshop_view(ctx, shop_id: str = ""):
    """View a specific shop's listings"""
    if not shop_id:
        await ctx.send("❌ Usage: `P!pshop view <shop_id>`\nExample: `P!pshop view S1`")
        return
    
    await view_shop_display(ctx, shop_id, is_owner=False)

@pshop.command(name="remove")
async def pshop_remove(ctx, *, item_name: str = ""):
    """Remove an item from your shop"""
    if not item_name:
        await ctx.send("❌ Usage: `P!pshop remove <item>`\nExample: `P!pshop remove Bamboo Sword`")
        return
    
    user_id = str(ctx.author.id)
    
    # Find user's shop
    user_shop_id = None
    for shop_id, shop_data in player_shops_data["shops"].items():
        if str(shop_data["owner_id"]) == user_id:
            user_shop_id = shop_id
            break
    
    if not user_shop_id:
        await ctx.send("❌ You don't have a shop!")
        return
    
    shop = player_shops_data["shops"][user_shop_id]
    
    # Find listing
    found_listing = None
    for listing in shop["listings"]:
        if listing["item_name"].lower() == item_name.lower():
            found_listing = listing
            break
    
    if not found_listing:
        await ctx.send(f"❌ **{item_name}** is not listed in your shop!")
        return
    
    # Return item to inventory
    if user_id not in chi_data:
        chi_data[user_id] = {"chi": 0, "milestones_claimed": [], "mini_quests": [], "rebirths": 0, "purchased_items": []}
    if "inventory" not in chi_data[user_id]:
        chi_data[user_id]["inventory"] = {}
    
    chi_data[user_id]["inventory"][found_listing["item_name"]] = chi_data[user_id]["inventory"].get(found_listing["item_name"], 0) + 1
    
    # Remove listing
    shop["listings"].remove(found_listing)
    
    save_data()
    save_player_shops()
    
    await ctx.send(f"✅ **{found_listing['item_name']}** removed from your shop and returned to your inventory!")

@pshop.command(name="stats")
async def pshop_stats(ctx):
    """View your shop's detailed statistics"""
    user_id = str(ctx.author.id)
    
    # Find user's shop
    user_shop_id = None
    for shop_id, shop_data in player_shops_data["shops"].items():
        if str(shop_data["owner_id"]) == user_id:
            user_shop_id = shop_id
            break
    
    if not user_shop_id:
        await ctx.send("❌ You don't have a shop! Create one with `P!pshop create <name>`")
        return
    
    shop = player_shops_data["shops"][user_shop_id]
    
    embed = discord.Embed(
        title=f"📊 {shop['name']} Statistics",
        description=f"Shop ID: {user_shop_id}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="💰 Total Revenue", value=f"{shop.get('total_revenue', 0):,} chi", inline=True)
    embed.add_field(name="📦 Total Sales", value=f"{shop.get('total_sales', 0)} transactions", inline=True)
    embed.add_field(name="🏷️ Active Listings", value=f"{len(shop['listings'])} items", inline=True)
    
    # Most expensive listing
    if shop["listings"]:
        most_expensive = max(shop["listings"], key=lambda x: x["price"])
        embed.add_field(
            name="💎 Highest Priced Item",
            value=f"{most_expensive['item_name']} - {most_expensive['price']:,} chi",
            inline=False
        )
    
    # Average price
    if shop["listings"]:
        avg_price = sum(l["price"] for l in shop["listings"]) / len(shop["listings"])
        embed.add_field(name="📈 Average Price", value=f"{int(avg_price):,} chi", inline=True)
    
    # Shop rank
    all_shops = list(player_shops_data["shops"].items())
    sorted_shops = sorted(all_shops, key=lambda x: x[1].get("total_sales", 0), reverse=True)
    shop_rank = next((i + 1 for i, (sid, _) in enumerate(sorted_shops) if sid == user_shop_id), 0)
    
    embed.add_field(name="🏆 Shop Rank", value=f"#{shop_rank} of {len(player_shops_data['shops'])}", inline=True)
    
    await ctx.send(embed=embed)


# ==================== WINTER WONDERLAND - POTION SYSTEM ====================

@bot.group(name="potion", invoke_without_command=True)
async def potion(ctx):
    """Potion management and usage commands"""
    await ctx.send("**🧪 Potion System Commands**\n"
                  "`P!potion list` - View all available potions\n"
                  "`P!potion inventory` - View your potions\n"
                  "`P!potion info <potion_name>` - View potion details\n"
                  "`P!potion use <potion_name>` - Use a potion (in or before duel)\n"
                  "`P!potion throw <potion_name> @user` - Throw poison at enemy (in duel)\n\n"
                  "**🧙 Brewing Commands**\n"
                  "`P!brew list` - View all brewing recipes\n"
                  "`P!brew info <potion_name>` - View recipe details\n"
                  "`P!brew craft <potion_name>` - Craft a potion\n"
                  "`P!brew ingredients` - View your ingredients")

@potion.command(name="list")
async def potion_list(ctx):
    """View all available potions"""
    embed = discord.Embed(title="🧪 Potion Catalog - Winter Wonderland Update", color=discord.Color.purple())
    
    # Group by rarity
    rarities = {"common": [], "uncommon": [], "rare": [], "epic": [], "legendary": [], "mythic": []}
    
    for potion_key, potion in POTION_CATALOG.items():
        rarity = potion["rarity"]
        if rarity in rarities:
            rarities[rarity].append(f"{potion['emoji']} **{potion['name']}** - {potion['description']}")
    
    # Add fields by rarity
    rarity_colors = {
        "common": "⬜ Common",
        "uncommon": "🟢 Uncommon",
        "rare": "🔵 Rare",
        "epic": "🟣 Epic",
        "legendary": "🟠 Legendary",
        "mythic": "🔴 Mythic"
    }
    
    for rarity, potions in rarities.items():
        if potions:
            embed.add_field(
                name=rarity_colors.get(rarity, rarity.title()),
                value="\n".join(potions),
                inline=False
            )
    
    embed.set_footer(text="Use P!potion info <name> for details | P!brew to craft potions")
    await ctx.send(embed=embed)

@potion.command(name="inventory")
async def potion_inventory(ctx):
    """View your potion inventory"""
    user_id = str(ctx.author.id)
    potions = get_user_potions(user_id)
    
    if not potions:
        await ctx.send("❌ You don't have any potions! Use `P!brew craft` to brew some.")
        return
    
    embed = discord.Embed(title=f"🧪 {ctx.author.name}'s Potion Inventory", color=discord.Color.blue())
    
    for potion_key, count in potions.items():
        potion = POTION_CATALOG.get(potion_key)
        if potion:
            embed.add_field(
                name=f"{potion['emoji']} {potion['name']} x{count}",
                value=potion['description'],
                inline=False
            )
    
    embed.set_footer(text="Use P!potion use <name> to use a potion")
    await ctx.send(embed=embed)

@potion.command(name="info")
async def potion_info(ctx, *, potion_name: str):
    """View detailed info about a specific potion"""
    # Find potion
    potion_key = None
    for key, potion in POTION_CATALOG.items():
        if potion["name"].lower() == potion_name.lower() or key == potion_name.lower():
            potion_key = key
            break
    
    if not potion_key:
        await ctx.send(f"❌ Potion '{potion_name}' not found! Use `P!potion list` to see all potions.")
        return
    
    potion = POTION_CATALOG[potion_key]
    recipe = POTION_RECIPES.get(potion_key)
    
    embed = discord.Embed(
        title=f"{potion['emoji']} {potion['name']}",
        description=potion['description'],
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Rarity", value=potion['rarity'].title(), inline=True)
    embed.add_field(name="Effect Type", value=potion['effect_type'].replace('_', ' ').title(), inline=True)
    embed.add_field(name="Throwable", value="Yes" if potion.get('throwable') else "No", inline=True)
    
    if potion.get('pre_duel_only'):
        embed.add_field(name="⚠️ Usage", value="Must be used BEFORE duel starts!", inline=False)
    
    if recipe:
        ingredients_list = []
        for ing_key, amount in recipe['ingredients'].items():
            ing = INGREDIENT_CATALOG.get(ing_key)
            if ing:
                ingredients_list.append(f"{ing['emoji']} {ing_key.replace('_', ' ').title()} x{amount}")
        
        embed.add_field(name="📜 Crafting Recipe", value="\n".join(ingredients_list), inline=False)
        embed.add_field(name="Chi Cost", value=f"✨ {recipe['chi_cost']}", inline=True)
        embed.add_field(name="Success Rate", value=f"{int(recipe['success_rate']*100)}%", inline=True)
        embed.add_field(name="Brew Time", value=f"{recipe['brew_time']}s", inline=True)
    
    # Show how many user has
    user_count = get_potion_count(str(ctx.author.id), potion_key)
    if user_count > 0:
        embed.set_footer(text=f"You have {user_count} of this potion")
    else:
        embed.set_footer(text="You don't own this potion yet")
    
    await ctx.send(embed=embed)

@bot.group(name="brew", invoke_without_command=True)
async def brew(ctx):
    """Brewing and crafting commands"""
    await ctx.send("**🧙 Brewing System Commands**\n"
                  "`P!brew list` - View all brewing recipes\n"
                  "`P!brew info <potion_name>` - View recipe details\n"
                  "`P!brew craft <potion_name>` - Craft a potion\n"
                  "`P!brew ingredients` - View your ingredients\n\n"
                  "Gather ingredients from gardens, mining, boss battles, and NPC trading!")

@brew.command(name="list")
async def brew_list(ctx):
    """View all brewing recipes"""
    embed = discord.Embed(title="📜 Brewing Recipes - Winter Wonderland", color=discord.Color.gold())
    
    # Group by tier
    tiers = {"common": [], "uncommon": [], "rare": [], "epic": [], "legendary": [], "mythic": []}
    
    for potion_key, recipe in POTION_RECIPES.items():
        potion = POTION_CATALOG.get(potion_key)
        if potion:
            tier = recipe.get("tier", "common")
            if tier in tiers:
                tiers[tier].append(
                    f"{potion['emoji']} **{potion['name']}** - {recipe['chi_cost']} chi, "
                    f"{int(recipe['success_rate']*100)}% success"
                )
    
    tier_labels = {
        "common": "⬜ Common Recipes",
        "uncommon": "🟢 Uncommon Recipes",
        "rare": "🔵 Rare Recipes",
        "epic": "🟣 Epic Recipes",
        "legendary": "🟠 Legendary Recipes",
        "mythic": "🔴 Mythic Recipes"
    }
    
    for tier, recipes in tiers.items():
        if recipes:
            embed.add_field(
                name=tier_labels.get(tier, tier.title()),
                value="\n".join(recipes),
                inline=False
            )
    
    embed.set_footer(text="Use P!brew info <name> for recipe details")
    await ctx.send(embed=embed)

@brew.command(name="ingredients")
async def brew_ingredients(ctx):
    """View your ingredient inventory"""
    user_id = str(ctx.author.id)
    ingredients = get_user_ingredients(user_id)
    
    if not ingredients:
        await ctx.send("❌ You don't have any ingredients yet!\n"
                      "**Get ingredients from:**\n"
                      "🌸 Gardens - Harvest herbs\n"
                      "⛏️ Mining - Find ores and crystals\n"
                      "⚔️ Boss Battles - Rare essences\n"
                      "🏪 NPC Trading - Special items")
        return
    
    embed = discord.Embed(title=f"🧪 {ctx.author.name}'s Ingredients", color=discord.Color.green())
    
    # Group by source
    sources = {"garden": [], "mining": [], "boss": [], "npc_trade": []}
    
    for ing_key, count in ingredients.items():
        ing = INGREDIENT_CATALOG.get(ing_key)
        if ing:
            source = ing.get("source", "unknown")
            if ":" in source:
                source = "boss"
            if source not in sources:
                sources[source] = []
            sources[source].append(f"{ing['emoji']} {ing_key.replace('_', ' ').title()} x{count}")
    
    source_labels = {
        "garden": "🌸 Garden Herbs",
        "mining": "⛏️ Mined Materials",
        "boss": "⚔️ Boss Essences",
        "npc_trade": "🏪 NPC Items"
    }
    
    for source, items in sources.items():
        if items:
            embed.add_field(
                name=source_labels.get(source, source.title()),
                value="\n".join(items),
                inline=False
            )
    
    await ctx.send(embed=embed)

@brew.command(name="craft")
async def brew_craft(ctx, *, potion_name: str):
    """Craft a potion using ingredients"""
    user_id = str(ctx.author.id)
    
    # Find potion
    potion_key = None
    for key, potion in POTION_CATALOG.items():
        if potion["name"].lower() == potion_name.lower() or key == potion_name.lower():
            potion_key = key
            break
    
    if not potion_key:
        await ctx.send(f"❌ Potion '{potion_name}' not found! Use `P!brew list` to see all recipes.")
        return
    
    recipe = POTION_RECIPES.get(potion_key)
    if not recipe:
        await ctx.send(f"❌ No recipe found for '{potion_name}'!")
        return
    
    potion = POTION_CATALOG[potion_key]
    
    # Check chi cost
    user_chi = chi_data.get(user_id, {}).get("chi", 0)
    if user_chi < recipe["chi_cost"]:
        await ctx.send(f"❌ Not enough chi! Need ✨ {recipe['chi_cost']}, you have ✨ {user_chi}")
        return
    
    # Check ingredients
    has_all, missing = check_has_ingredients(user_id, recipe)
    if not has_all:
        missing_list = []
        for ing_key, amount in missing.items():
            ing = INGREDIENT_CATALOG.get(ing_key)
            if ing:
                missing_list.append(f"{ing['emoji']} {ing_key.replace('_', ' ').title()} x{amount}")
        
        await ctx.send(f"❌ Missing ingredients:\n" + "\n".join(missing_list))
        return
    
    # Show crafting confirmation
    ingredients_list = []
    for ing_key, amount in recipe['ingredients'].items():
        ing = INGREDIENT_CATALOG.get(ing_key)
        if ing:
            ingredients_list.append(f"{ing['emoji']} {ing_key.replace('_', ' ').title()} x{amount}")
    
    confirm_embed = discord.Embed(
        title=f"🧙 Brew {potion['emoji']} {potion['name']}?",
        description=f"**Ingredients Required:**\n" + "\n".join(ingredients_list) +
                   f"\n\n**Chi Cost:** ✨ {recipe['chi_cost']}\n"
                   f"**Success Rate:** {int(recipe['success_rate']*100)}%\n"
                   f"**Brew Time:** {recipe['brew_time']} seconds\n\n"
                   f"React with 🧪 to start brewing!",
        color=discord.Color.purple()
    )
    
    confirm_msg = await ctx.send(embed=confirm_embed)
    await confirm_msg.add_reaction("🧪")
    await confirm_msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["🧪", "❌"] and reaction.message.id == confirm_msg.id
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await ctx.send("❌ Brewing cancelled.")
            return
        
        # Start brewing
        brewing_msg = await ctx.send(f"🧙 Brewing {potion['emoji']} **{potion['name']}**... ⏰ {recipe['brew_time']}s")
        await asyncio.sleep(recipe['brew_time'])
        
        # Roll for success
        success = random.random() < recipe['success_rate']
        
        if success:
            # Consume ingredients and chi
            consume_ingredients(user_id, recipe)
            chi_data[user_id]["chi"] -= recipe["chi_cost"]
            
            # Add potion
            add_potion_to_inventory(user_id, potion_key, 1)
            save_data()
            
            success_embed = discord.Embed(
                title="✅ Brewing Successful!",
                description=f"{ctx.author.mention} crafted {potion['emoji']} **{potion['name']}**!\n\n"
                           f"The potion has been added to your inventory.",
                color=discord.Color.green()
            )
            await ctx.send(embed=success_embed)
            
            # Log event
            await log_event(
                "Potion Brewed",
                f"**User:** {ctx.author.mention}\n**Potion:** {potion['emoji']} {potion['name']}\n**Chi Cost:** {recipe['chi_cost']}", ctx.guild, discord.Color.purple())
        else:
            # Brewing failed! Consume ingredients and chi anyway
            consume_ingredients(user_id, recipe)
            chi_data[user_id]["chi"] -= recipe["chi_cost"]
            save_data()
            
            fail_embed = discord.Embed(
                title="💥 Brewing Failed!",
                description=f"The potion exploded! Ingredients and chi were lost.\n\n"
                           f"Better luck next time...",
                color=discord.Color.red()
            )
            await ctx.send(embed=fail_embed)
        
    except asyncio.TimeoutError:
        await ctx.send("⏰ Brewing confirmation timed out.")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`\n"
                      f"Use `P!help` for command usage info.")
        return
    
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found! Please mention a valid member.")
        return
    
    if isinstance(error, commands.CheckFailure):
        return
    
    if isinstance(error, commands.CommandInvokeError):
        original = error.original
        if isinstance(original, KeyError):
            await ctx.send(f"⚠️ A data error occurred. Please try again or contact an admin if this persists.\n"
                          f"Error details: Missing key `{original.args[0]}`")
            print(f"KeyError in command {ctx.command}: {original}")
            import traceback
            traceback.print_exc()
            return
        
        await ctx.send(f"⚠️ An error occurred while executing this command. Please contact an admin.\n"
                      f"Error: {str(original)}")
        print(f"Error in command {ctx.command}: {original}")
        import traceback
        traceback.print_exc()
        return
    
    await ctx.send(f"⚠️ An unexpected error occurred: {str(error)}")
    print(f"Unhandled error in command {ctx.command}: {error}")
    import traceback
    traceback.print_exc()
