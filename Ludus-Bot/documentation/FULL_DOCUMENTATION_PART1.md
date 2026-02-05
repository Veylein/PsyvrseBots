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
- **discord.py**: 2.3.2 (with Components v2)
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
├── bot.py                      # Main bot entry point (475 lines)
├── start.py                    # Production launcher
├── config.json                 # Bot configuration
├── constants.py                # Global constants
├── requirements.txt            # Dependencies
├── .env                        # Environment variables (token)
│
├── cogs/                       # Feature modules (70+ files)
│   ├── economy.py             # Currency system (918 lines)
│   ├── fishing.py             # Fishing simulator (3400+ lines)
│   ├── farming.py             # Farming system (1200+ lines)
│   ├── mining.py              # Mining game (3249 lines)
│   ├── gambling.py            # Casino games (1200+ lines)
│   ├── minigames.py           # 100+ mini-games (2000+ lines)
│   ├── pets.py                # Pet system (800+ lines)
│   ├── achievements.py        # Achievement tracking (600+ lines)
│   ├── quests.py              # Quest system (500+ lines)
│   ├── dnd.py                 # D&D campaigns (1500+ lines)
│   ├── multiplayer_games.py  # Social deduction (800+ lines)
│   ├── boardgames.py          # Chess, Checkers, etc (1000+ lines)
│   ├── cardgames.py           # Poker, Blackjack (900+ lines)
│   ├── uno_gofish.py          # UNO implementation (1200+ lines)
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
│   └── ... (50+ more cogs)
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

### 2.1 Main Bot File (bot.py) - Line-by-Line Analysis

#### 2.1.1 Imports and Environment Setup (Lines 1-35)

```python
import sys
import discord
from discord.ext import commands
import json
import os
import asyncio
import traceback
import dotenv
import constants

dotenv.load_dotenv()
if not os.environ.get("LUDUS_TOKEN"):
    print("LUDUS_TOKEN not set!")
    sys.exit(1)
```

**Purpose**: 
- Load Discord bot token from environment variables
- Fail fast if token is missing (prevents runtime errors)
- Import constants for global values

#### 2.1.2 Opus Library Loading (Lines 17-30)

```python
try:
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('libopus.so.0')
        except Exception:
            try:
                discord.opus.load_opus()
            except Exception:
                print('[BOT] Warning: Opus library not found; voice features disabled')
except Exception:
    print('[BOT] Warning: could not initialize opus; continuing without voice')
```

**Purpose**: 
- Enable voice channel support (for music features)
- Gracefully degrade if Opus library is not available
- Prevents bot from crashing if voice features are unavailable

**Technical Detail**: Opus is required for audio encoding/decoding in Discord voice channels

#### 2.1.3 Configuration Loading (Lines 32-38)

```python
with open("config.json") as f:
    config = json.load(f)

print(f"[BOT] Loaded config: {config}")
print(f"[BOT] Owner IDs from config: {config.get('owner_ids', [])}")
```

**Config Structure** (`config.json`):
```json
{
  "prefix": "L!",
  "owner_ids": [123456789, 987654321],
  "music_enabled": true,
  "dev_guild_ids": [123456789]
}
```

#### 2.1.4 Discord Intents (Lines 40-43)

```python
intents = discord.Intents.default()
intents.message_content = True  # Required for prefix commands
intents.members = True          # Required for member events
intents.voice_states = True     # Required for voice features
```

**Why These Intents?**
- `message_content`: Read message content for prefix commands (`L!command`)
- `members`: Access member list, track joins/leaves
- `voice_states`: Detect voice channel activity for music player

**Important**: These must be enabled in Discord Developer Portal!

#### 2.1.5 Bot Initialization (Lines 45-57)

```python
owner_ids_set = set(config.get("owner_ids", []))
print(f"[BOT] Creating bot with owner_ids: {owner_ids_set}")

bot = commands.Bot(
    command_prefix=config["prefix"],  # "L!"
    intents=intents,
    owner_ids=owner_ids_set,          # For owner-only commands
    help_command=None,                # Disable default help (use custom)
    description="🎮 The ultimate Discord minigame & music bot!"
)
```

**Key Parameters**:
- `command_prefix`: The text that triggers prefix commands (e.g., `L!balance`)
- `owner_ids`: Set of user IDs with owner permissions (can use admin commands)
- `help_command=None`: Disables discord.py's default help command (we use custom help.py)
- `description`: Shown in bot status and help menus

#### 2.1.6 Global Game State Storage (Lines 59-63)

```python
bot.active_games = {}        # Chess, checkers, UNO games
bot.active_lobbies = {}      # Multiplayer game lobbies
bot.active_minigames = {}    # Running minigames
bot.pending_rematches = {}   # Rematch requests
```

**Purpose**: 
- Store temporary game state across cogs
- Shared data structure for multiplayer games
- Prevents memory leaks by cleaning up finished games

**Example Usage**:
```python
# Store chess game
bot.active_games['chess_12345'] = {
    'players': {123: 'white', 456: 'black'},
    'board': chess_board_state,
    'turn': 'white'
}

# Check if game exists
if 'chess_12345' in bot.active_games:
    game = bot.active_games['chess_12345']
```

#### 2.1.7 Command Tree Duplicate Protection (Lines 66-101)

```python
_original_add_command = bot.tree.add_command
bot._original_tree_add_command = _original_add_command

def _safe_add_command(command, **kwargs):
    try:
        name = getattr(command, 'name', None) or getattr(command, '__name__', None)
    except Exception:
        name = None
    
    # Skip if command already exists
    try:
        if name and bot.tree.get_command(name) is not None:
            print(f"[BOT] Skipping duplicate app command registration: {name}")
            return bot.tree.get_command(name)
    except Exception:
        pass
    
    try:
        return _original_add_command(command, **kwargs)
    except Exception as e:
        from discord.app_commands import CommandAlreadyRegistered
        if isinstance(e, CommandAlreadyRegistered) or 'already registered' in str(e):
            print(f"[BOT] Duplicate app command detected and ignored: {name}")
            return bot.tree.get_command(name)
        raise

bot.tree.add_command = _safe_add_command
```

**Why This Exists**:
- Multiple cogs sometimes try to register the same slash command
- Without this, bot crashes with `CommandAlreadyRegistered` error
- This monkeypatch gracefully handles duplicates

**Technical Detail**: 
- Wraps `bot.tree.add_command` with duplicate checking
- Stores original function for cogs that need it
- Returns existing command instead of crashing

#### 2.1.8 Setup Hook (Lines 103-119)

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
        print(f"[BOT] Failed to load UNO emoji: {e}")
        traceback.print_exc()
    
    await load_cogs()
```

**Purpose**:
- Runs before bot connects to Discord
- Loads custom UNO card emojis
- Loads all cog files from `cogs/` directory

**Why UNO Emojis Here?**
- UNO cards use custom Discord emojis
- Must be loaded before UNO cog initializes
- Stored in constants.py for global access

#### 2.1.9 Cog Loading System (Lines 121-166)

```python
async def load_cogs():
    for entry in os.listdir("./cogs"):
        path = os.path.join("./cogs", entry)

        # Handle both .py files and package directories
        if entry.endswith(".py"):
            cog_name = entry[:-3]
        elif os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
            cog_name = entry
        else:
            continue

        # Skip disabled/legacy cogs
        if cog_name == "music_new":
            print("Skipping music_new (using music.py instead)")
            continue
        if cog_name == "uno_gofish":
            print("Skipping uno_gofish (legacy - using cardgames.py instead)")
            continue
        if cog_name == "leveling":
            print("Skipping leveling (disabled - causes issues)")
            continue
        if cog_name == "music" and not config.get("music_enabled", True):
            print("Skipping music cog (disabled in config.json)")
            continue
        if cog_name == "tcg":
            print("Skipping legacy cog 'tcg' to avoid command conflicts")
            continue

        try:
            await bot.load_extension(f"cogs.{cog_name}")
            print(f"Loaded cog: {cog_name}")
        except Exception as e:
            print(f"Failed to load cog {cog_name}: {e}")
            traceback.print_exc()
```

**How It Works**:
1. Scans `cogs/` directory for files and folders
2. Loads `.py` files as cogs (e.g., `economy.py` → `cogs.economy`)
3. Loads directories with `__init__.py` as package cogs (e.g., `uno/` → `cogs.uno`)
4. Skips disabled/legacy cogs based on hardcoded list
5. Prints success/failure for each cog

**Skipped Cogs Explained**:
- `music_new`: Experimental music player, using stable `music.py` instead
- `uno_gofish`: Old implementation, replaced by `cardgames.py`
- `leveling`: Causes database conflicts, disabled until fixed
- `music`: Can be disabled via config if voice features not needed
- `tcg`: Old TCG system, replaced by `psyvrse_tcg.py`

#### 2.1.10 on_ready Event (Lines 168-240)

```python
@bot.event
async def on_ready():
    print(f"[BOT] {bot.user} is online!")
    print(f"[BOT] Bot owner_ids: {bot.owner_ids}")
    print(f"[BOT] Bot application info owner: {(await bot.application_info()).owner.id if bot.application else 'Unknown'}")
```

**Purpose**: Runs when bot successfully connects to Discord

**Slash Command Sync System**:
```python
DEV_ONLY_COMMANDS = []  # Commands to sync only to dev guild

# Log all commands
print(f"[BOT] Total app commands in tree: {len(bot.tree.get_commands())}")

try:
    dev_guilds_raw = os.environ.get('DEV_GUILD_IDS') or os.environ.get('DEV_GUILD_ID')
    if dev_guilds_raw:
        print(f"[BOT] DEV_GUILD_ID detected - splitting commands")
        guild_ids = [g.strip() for g in dev_guilds_raw.split(',') if g.strip()]
        
        # Save dev-only commands
        dev_commands = {}
        for cmd_name in DEV_ONLY_COMMANDS:
            cmd = bot.tree.get_command(cmd_name)
            if cmd:
                dev_commands[cmd_name] = cmd
                bot.tree.remove_command(cmd_name)
        
        # Sync global commands
        synced_global = await bot.tree.sync()
        print(f"[BOT] ✅ Synced {len(synced_global)} commands globally")
        
        # Sync dev commands to guild
        for dev_gid in guild_ids:
            guild_obj = discord.Object(id=int(dev_gid))
            bot.tree.clear_commands(guild=guild_obj)
            for cmd_name, cmd in dev_commands.items():
                bot.tree.add_command(cmd, guild=guild_obj)
            synced_guild = await bot.tree.sync(guild=guild_obj)
            print(f"[BOT] ✅ Synced {len(synced_guild)} dev commands to guild {dev_gid}")
    else:
        synced = await bot.tree.sync()
        print(f"[BOT] ✅ Synced {len(synced)} commands globally")
except Exception as e:
    print(f"[BOT] Error syncing commands: {e}")
    traceback.print_exc()
```

**Command Sync Explained**:
- **Global Sync**: Commands appear in all servers (takes ~1 hour to propagate)
- **Guild Sync**: Commands appear only in specific server (instant)
- **Dev Guild System**: Test commands in dev server before global release
- **Split Sync**: Dev commands go to guild, production commands go global

**Why Split Sync?**
- Global sync is slow (1 hour delay)
- Guild sync is instant (for testing)
- Keeps experimental commands private
- Prevents command spam in production servers

#### 2.1.11 Blacklist System (Lines 242-258)

```python
def load_blacklist():
    """Load blacklist data"""
    if os.path.exists("blacklist.json"):
        with open("blacklist.json", 'r') as f:
            return json.load(f)
    return {"users": [], "servers": []}

def is_blacklisted(user_id: int = None, guild_id: int = None) -> bool:
    """Check if user or guild is blacklisted"""
    blacklist = load_blacklist()
    if user_id and user_id in blacklist.get("users", []):
        return True
    if guild_id and guild_id in blacklist.get("servers", []):
        return True
    return False
```

**Blacklist File Structure** (`blacklist.json`):
```json
{
  "users": [123456789, 987654321],
  "servers": [111222333444]
}
```

**Usage**:
- Bot owners can blacklist abusive users
- Bot owners can blacklist problematic servers
- Blacklisted users/servers cannot use any commands
- Managed via owner commands (`L!blacklist add/remove`)

#### 2.1.12 Server Configuration Loader (Lines 260-276)

```python
def load_server_config(guild_id):
    """Load server-specific configuration"""
    config_file = "data/server_configs.json"
    try:
        with open(config_file, 'r') as f:
            configs = json.load(f)
            return configs.get(str(guild_id), {
                "welcome_dm": True,
                "personality_reactions": True,
                "disabled_commands": [],
                "rate_limit_enabled": True
            })
    except FileNotFoundError:
        return {
            "welcome_dm": True,
            "personality_reactions": True,
            "disabled_commands": [],
            "rate_limit_enabled": True
        }
```

**Server Config Structure**:
```json
{
  "123456789": {
    "welcome_dm": true,
    "personality_reactions": true,
    "disabled_commands": ["gambling", "nsfw"],
    "rate_limit_enabled": true,
    "prefix": "!",
    "starboard_enabled": true,
    "confession_channel": 987654321
  }
}
```

**Configuration Options**:
- `welcome_dm`: Send welcome DM to first-time users
- `personality_reactions`: Bot reacts to certain messages
- `disabled_commands`: List of commands to disable in this server
- `rate_limit_enabled`: Enable rate limiting for commands
- `prefix`: Custom prefix for this server (overrides global)
- `starboard_enabled`: Enable starboard feature
- `confession_channel`: Channel ID for anonymous confessions

#### 2.1.13 Global Interaction Check (Lines 278-288)

```python
@bot.tree.interaction_check
async def global_interaction_check(interaction: discord.Interaction) -> bool:
    """Global check for all slash commands - blocks blacklisted users/servers"""
    if is_blacklisted(user_id=interaction.user.id, guild_id=interaction.guild_id if interaction.guild else None):
        await interaction.response.send_message(
            "🚫 You or this server has been blacklisted from using this bot.",
            ephemeral=True
        )
        return False
    return True
```

**Purpose**:
- Runs before EVERY slash command
- Blocks blacklisted users/servers from using any commands
- Returns False to prevent command execution
- Sends ephemeral message (only visible to user)

**Technical Detail**: 
- `interaction_check` is called before command handler
- Returning False cancels command execution
- Ephemeral messages don't clutter channels

#### 2.1.14 Command Error Handler (Lines 290-314)

```python
@bot.event
async def on_command_error(ctx, error):
    """Global error handler for prefix commands"""
    if isinstance(error, commands.CheckFailure):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command.")
        else:
            await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silently ignore
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`\n💡 Use `L!help {ctx.command.name}` for usage info.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ I'm missing permissions: {', '.join(error.missing_permissions)}")
    else:
        print(f"[BOT] Command error in {ctx.command}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send("❌ An error occurred. Please try again or contact a server administrator.")
```

**Error Types Handled**:
1. **CheckFailure**: Permission denied
2. **MissingPermissions**: User lacks required permissions
3. **CommandNotFound**: Invalid command (silently ignored)
4. **MissingRequiredArgument**: Missing command argument
5. **CommandOnCooldown**: Command used too soon
6. **BotMissingPermissions**: Bot lacks required permissions
7. **Generic Errors**: Logged and shown to user

**User-Friendly Messages**:
- ❌ Clear error indicator
- 💡 Helpful suggestions
- ⏰ Cooldown information
- No technical jargon exposed to users

---

