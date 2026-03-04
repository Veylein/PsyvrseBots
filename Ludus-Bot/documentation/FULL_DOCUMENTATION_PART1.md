# 🎮 Ludus Bot - Complete Technical Documentation (Part 1: Core Systems)

---

## 1. PROJECT OVERVIEW

### 1.1 What is Ludus Bot?

**Ludus** is a comprehensive, enterprise-grade Discord bot built in Python using discord.py 2.3+. It serves as a complete entertainment and gaming platform for Discord servers, featuring:

- **150+ Interactive Games** across 20+ categories
- **Full Economy System** with virtual currency (PsyCoins)
- **Simulation Games** (Fishing, Farming, Mining, Zoo)
- **Social Features** (Pets, Marriage, Reputation, Profiles)
- **RPG Elements** (D&D campaigns, Quests, Achievements)
- **Server Management** (Global events, Starboard, Counting, Confessions)
- **Persistent Progress** with automatic data saving

### 1.2 Project Statistics

```
Total Lines of Code: 50,000+
Number of Cogs: 70+
Number of Commands: 300+
Slash Commands: 150+
Prefix Commands: 150+
Data Files: 20+
Supported Games: 150+
Average Uptime: 99.5%
Servers: 50+
Active Users: 10,000+
```

### 1.3 Technology Stack

**Core Framework:**
- **Python**: 3.10+
- **discord.py**: 2.6.4 (with Components v2 — LayoutView, Container, TextDisplay)
- **asyncio**: For concurrent operations
- **aiohttp**: For async HTTP requests

**Data Storage:**
- **JSON**: Primary data format
- **File-based**: No external database required
- **Atomic Writes**: Prevent data corruption
- **Backup System**: Automatic daily backups

**Additional Libraries:**
```python
python-dotenv==1.0.0      # Environment variables
aiohttp==3.9.1            # Async HTTP client
Pillow==10.1.0            # Image processing
asyncio==3.4.3            # Async operations
```

### 1.4 Project Structure

```
Ludus-Bot/
│
├── bot.py                      # Main bot entry point (315 lines)
├── start.py                    # Production launcher
├── config.json                 # Bot configuration
├── constants.py                # Global constants
├── requirements.txt            # Dependencies
├── .env                        # Environment variables (token)
│
├── cogs/                       # Feature modules (80+ files)
│   ├── economy.py             # Currency system (1206 lines)
│   ├── fishing.py             # Fishing simulator (3400+ lines)
│   ├── farming.py             # Farming system (1200+ lines)
│   ├── mining.py              # Mining game (4053 lines)
│   ├── gambling.py            # Casino games (1404 lines)
│   ├── poker.py               # Texas Hold'em poker (2824 lines)
│   ├── leaderboard.py         # Server + global leaderboards (532 lines)
│   ├── minigames.py           # 100+ mini-games (2000+ lines)
│   ├── pets.py                # Pet system (800+ lines)
│   ├── achievements.py        # Achievement tracking (600+ lines)
│   ├── quests.py              # Quest system (500+ lines)
│   ├── multiplayer_games.py  # Social deduction (800+ lines)
│   ├── boardgames.py          # Chess, Checkers, etc (1000+ lines)
│   ├── cardgames.py           # Card games: Go Fish, War, etc (700+ lines)
│   ├── marriage.py            # Marriage system (400+ lines)
│   ├── profile.py             # User profiles (600+ lines)
│   ├── reputation.py          # Reputation system (300+ lines)
│   ├── social.py              # Social actions (500+ lines)
│   ├── guilds.py              # Guild system (400+ lines)
│   ├── globalevents.py        # Server events (700+ lines)
│   ├── starboard.py           # Message highlights (400+ lines)
│   ├── counting.py            # Counting game (300+ lines)
│   ├── confessions.py         # Anonymous system (300+ lines)
│   ├── help.py                # Help system (800+ lines)
│   ├── owner.py               # Admin commands (1100+ lines)
│   └── ... (55+ more cogs)
│
├── utils/                      # Utility modules
│   ├── embed_styles.py        # Consistent embed formatting
│   └── ...
│
├── data/                       # Persistent data (JSON files)
│   ├── economy.json           # User balances
│   ├── fishing_data.json      # Fishing progress
│   ├── inventory.json         # User inventories
│   ├── pets.json              # Pet ownership
│   ├── profiles.json          # User profiles
│   ├── achievements_data.json # Achievements
│   ├── quests_data.json       # Quest progress
│   ├── gambling_stats.json    # Gambling history
│   ├── game_stats.json        # Game statistics
│   ├── leaderboard_stats.json # Rankings
│   ├── server_configs.json    # Server settings
│   └── ... (15+ more files)
│
├── assets/                     # Static assets
│   ├── cards/                 # Playing card images
│   └── uno_cards/             # UNO card images
│
├── tests/                      # Test files (future)
│
└── DOCUMENTATION.md            # This file
```

### 1.5 Design Principles

1. **Modularity**: Each feature is a separate cog that can be loaded/unloaded independently
2. **Data Persistence**: All user progress is automatically saved with atomic writes
3. **Economy Integration**: Every activity rewards players with PsyCoins
4. **User Experience**: Intuitive interfaces using Discord's Components v2 (buttons, dropdowns, modals)
5. **Scalability**: Designed to handle 100+ servers and 10,000+ users
6. **Error Resilience**: Comprehensive error handling with automatic recovery
7. **Performance**: Async operations, caching, and optimized database access
8. **Security**: Input validation, permission checks, rate limiting
9. **Maintainability**: Clean code, consistent naming, comprehensive logging
10. **Extensibility**: Easy to add new games and features

---

## 2. BOT INITIALIZATION & SETUP

### 2.1 Main Bot File (bot.py) — 315 Lines

#### 2.1.1 Imports and Environment Setup (Lines 1-20)

```python
import sys
import os
import json
import asyncio
import traceback
import logging
import logging.handlers
import discord
import dotenv
from pathlib import Path
from datetime import datetime
from discord.ext import commands
from discord import app_commands

import constants
import ludus_logging
from utils import user_storage
import aiofiles

dotenv.load_dotenv()
```

**Purpose**:
- Load Discord bot token from `.env` via `python-dotenv`
- Import `aiofiles` for async activity logging
- Import `user_storage` (utils helper for persistent user files)
- Import `ludus_logging` for structured bot-wide logging
- Import `constants` for global values shared across cogs

#### 2.1.2 Path Configuration & Logging (Lines 21-82)

```python
# Render.com persistent disk support
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH")
BASE_DATA_DIR = RENDER_DISK_PATH if RENDER_DISK_PATH else os.path.join(os.getcwd(), "data")
os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Rotating log file (5 MB × 5 backups)
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(BASE_DATA_DIR, 'logs', 'ludus.log'),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding='utf-8'
)
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), file_handler])
logger = logging.getLogger("ludus")
```

**Why Rotating Logs?**
- Prevents log files from eating all disk space
- Keeps last 5 log files × 5 MB = max 25 MB log storage
- UTF-8 encoding for emoji in log messages

#### 2.1.3 Opus & Configuration Loading (Lines 84-104)

```python
try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus.so.0')
except Exception:
    print('[BOT] Warning: Opus library not found; voice features disabled')

with open("config.json") as f:
    config = json.load(f)
```

**Config Structure** (`config.json`):
```json
{
  "prefix": "L!",
  "owner_ids": [123456789, 987654321]
}
```

#### 2.1.4 BotCommandTree — Slash Command Guard (Lines 108-126)

```python
class BotCommandTree(app_commands.CommandTree):
    """Custom tree for handling command restrictions."""
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.command is None:
            return True
        server_config_cog = interaction.client.get_cog("ServerConfig")
        if not server_config_cog:
            return True
        guild_cfg = server_config_cog.get_server_config(str(interaction.guild.id))
        disabled = guild_cfg.get("disabled_commands", [])
        cmd_name = interaction.command.name
        if cmd_name in disabled:
            await interaction.response.send_message(
                f"❌ Command `{cmd_name}` is disabled on this server.",
                ephemeral=True
            )
            return False
        return True
```

**Key Change vs older versions**: Instead of a global monkeypatch that suppressed `CommandAlreadyRegistered`, the tree now subclasses `app_commands.CommandTree` and overrides `interaction_check`. This is the clean, official pattern.

**What it does**:
- Before every slash command, checks if the command is in the server's `disabled_commands` list
- Fetches config from `ServerConfig` cog (which owns `data/server_configs.json`)
- Returns `False` with an ephemeral error message if disabled

#### 2.1.5 Bot Initialization (Lines 128-156)

```python
bot = commands.Bot(
    command_prefix=config["prefix"],
    intents=intents,
    owner_ids=owner_ids_set,
    help_command=None,
    tree_cls=BotCommandTree,         # ← custom tree
    description="🎮 The ultimate Discord minigame & music bot!",
    max_messages=1000,
    chunk_guilds_at_startup=False,   # ← lazy chunking for faster boot
    heartbeat_timeout=120.0,
)

bot.data_dir = BASE_DATA_DIR  # Shared across all cogs
bot.active_games = {}
bot.active_lobbies = {}
bot.active_minigames = {}
bot.pending_rematches = {}
```

**Notable Parameters**:
- `tree_cls=BotCommandTree`: plugs in the custom slash-command guard
- `chunk_guilds_at_startup=False`: don't bulk-fetch all members on boot (saves CPU/RAM); cogs that need member lists call `guild.chunk()` lazily
- `max_messages=1000`: message cache size
- `bot.data_dir`: shared path injected here so every cog can do `self.bot.data_dir` instead of duplicating path logic

#### 2.1.6 Activity Worker — Async Batched Logging (Lines 158-196)

```python
activity_queue = asyncio.Queue()
BATCH_SIZE = 50
BATCH_INTERVAL = 2.0

async def activity_worker():
    """Background worker to batch-save user activity to disk."""
    batch = []
    activity_file = os.path.join(bot.data_dir, "user_activity.json")
    while True:
        try:
            data = await asyncio.wait_for(activity_queue.get(), timeout=BATCH_INTERVAL)
            batch.append(data)
            ...
            if batch:
                async with aiofiles.open(activity_file, "a") as f:
                    lines = [json.dumps(entry) + "\n" for entry in batch]
                    await f.writelines(lines)
                batch.clear()
        except Exception as e:
            ...

def _record_user_activity(user_id, username, interaction_type, name, extra=None):
    data = {"user_id": user_id, "username": username, "type": interaction_type,
            "name": name, "extra": extra or {}, "timestamp": str(datetime.utcnow())}
    activity_queue.put_nowait(data)
```

**Purpose**: Tracks every command / interaction fired by every user.
- Uses `asyncio.Queue` so no cog has to `await` a file write.
- Drained in batches every 2 seconds (or when 50 items accumulate).
- Written via `aiofiles` — non-blocking file I/O.
- Output format: one JSON object per line in `user_activity.json` (JSONL / append-only).

#### 2.1.7 setup_hook (Lines 198-214)

```python
@bot.event
async def setup_hook():
    try:
        from cogs.uno import uno_logic
        emoji_mapping = uno_logic.load_emoji_mapping('classic')
        back_emoji_id = emoji_mapping.get('uno_back.png')
        if back_emoji_id:
            constants.UNO_BACK_EMOJI = f"<:uno_back:{back_emoji_id}>"
    except Exception as e:
        print(f"[BOT] Failed to load UNO assets: {e}")

    await load_cogs()

    try:
        user_storage.init_user_storage_worker(bot.loop)
    except Exception as e:
        print(f"[BOT] Failed to init storage worker: {e}")

    bot.loop.create_task(activity_worker())
```

**Runs before the bot connects to Discord.** Three things happen:
1. Load UNO emoji mapping into `constants.UNO_BACK_EMOJI` — must happen before any UNO cog initialises.
2. Load all cogs from `cogs/`.
3. Start the `activity_worker` background coroutine.

#### 2.1.8 on_ready Event (Lines 216-242)

```python
@bot.event
async def on_ready():
    try:
        from utils.stat_hooks import us_set_bot
        us_set_bot(bot)
    except Exception:
        pass

    print(f"🚀 BOT IS READY! | Account: {bot.user} | Guilds: {len(bot.guilds)}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Successfully synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Command sync failed: {e}")

    await bot.change_presence(activity=discord.Game(name="minigames"))
```

**Simplified global sync only** — no dev-guild split sync logic. All slash commands sync to all guilds after every boot.

#### 2.1.9 on_message Event (Lines 244-262)

```python
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    asyncio.create_task(user_storage.touch_user(message.author.id, ...))
    
    personality_cog = bot.get_cog("LudusPersonality")
    if personality_cog:
        await personality_cog.on_message(message)
    
    await bot.process_commands(message)
```

**Responsibilities**:
- Ignore bot's own messages
- `user_storage.touch_user()` — create/update user presence file (async, non-blocking task)
- Forward to `LudusPersonality` cog for AI response checks
- `process_commands()` — handle prefix commands (`L!`)

> **Note**: There is no global `on_command_error` in bot.py — each cog handles its own errors.

#### 2.1.10 Cog Loading (Lines 264-290)

```python
async def load_cogs():
    for entry in os.listdir("./cogs"):
        cog_name = None
        if entry.endswith(".py"):
            cog_name = entry[:-3]
        elif os.path.isdir(...) and os.path.exists(os.path.join(..., "__init__.py")):
            cog_name = entry
        if cog_name:
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                print(f"  ✅ {cog_name}")
            except Exception as e:
                print(f"  ❌ {cog_name} -> {e}")
                traceback.print_exc()
```

**Key difference from older versions**: No hardcoded skip list. Every `.py` and every package directory with `__init__.py` under `cogs/` is attempted. Failed loads are logged but do not abort the boot.

---

