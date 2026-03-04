# Ludus Bot — Full Documentation Part 15: Deployment

> **Covers:** All deployment methods, configuration, environment variables, data persistence, startup scripts, and operational procedures for running Ludus Bot locally and on Render.com.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
   - 2.1 [Python Version](#21-python-version)
   - 2.2 [System Dependencies](#22-system-dependencies)
   - 2.3 [Python Packages](#23-python-packages)
3. [Configuration Files](#3-configuration-files)
   - 3.1 [config.json](#31-configjson)
   - 3.2 [.env File](#32-env-file)
4. [Local Development Setup](#4-local-development-setup)
   - 4.1 [Initial Setup](#41-initial-setup)
   - 4.2 [Launching the Bot](#42-launching-the-bot)
   - 4.3 [Data Directory (Local)](#43-data-directory-local)
5. [Docker Deployment](#5-docker-deployment)
   - 5.1 [Dockerfile](#51-dockerfile)
   - 5.2 [Building and Running](#52-building-and-running)
   - 5.3 [Data Persistence with Docker](#53-data-persistence-with-docker)
6. [Render.com Deployment](#6-rendercom-deployment)
   - 6.1 [render.yaml](#61-renderyaml)
   - 6.2 [Environment Variables on Render](#62-environment-variables-on-render)
   - 6.3 [Persistent Disk Configuration](#63-persistent-disk-configuration)
   - 6.4 [Startup Script (start.sh)](#64-startup-script-startsh)
7. [Data Persistence Architecture](#7-data-persistence-architecture)
   - 7.1 [RENDER_DISK_PATH Pattern](#71-render_disk_path-pattern)
   - 7.2 [Files That Must Persist](#72-files-that-must-persist)
   - 7.3 [Atomic Write Safety](#73-atomic-write-safety)
8. [Discord Application Setup](#8-discord-application-setup)
   - 8.1 [Required Intents](#81-required-intents)
   - 8.2 [Required Bot Permissions](#82-required-bot-permissions)
   - 8.3 [Emoji Servers](#83-emoji-servers)
9. [Startup Sequence Reference](#9-startup-sequence-reference)
10. [Operational Procedures](#10-operational-procedures)
    - 10.1 [Reloading Cogs](#101-reloading-cogs)
    - 10.2 [Restarting the Bot](#102-restarting-the-bot)
    - 10.3 [Migrating User Data](#103-migrating-user-data)
    - 10.4 [Backing Up Data Files](#104-backing-up-data-files)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Overview

Ludus Bot can be deployed in three ways:

| Method | Use Case | Data Persistence |
|--------|----------|-----------------|
| **Local (direct)** | Development, testing | `./data/` in project directory |
| **Docker** | Self-hosted production | Volume mount to host path |
| **Render.com** | Cloud production | Render persistent disk at `RENDER_DISK_PATH` |

All three methods share the same codebase. The deployment environment is detected at runtime via the `RENDER_DISK_PATH` environment variable — if it is set, the bot uses it as the data directory; otherwise it falls back to `./data/`.

---

## 2. Prerequisites

### 2.1 Python Version

**Required:** Python **3.11** (specified in both `render.yaml` and Dockerfile)

```yaml
# render.yaml
envVars:
  - key: PYTHON_VERSION
    value: 3.11.0
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
```

Python 3.10+ is required at minimum for discord.py 2.x. Python 3.11 is the tested and specified version.

### 2.2 System Dependencies

**FFmpeg** — required for Discord voice features (music, voice cogs):

- **Local (Windows):** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to `PATH`
- **Local (Linux/macOS):** `sudo apt install ffmpeg` / `brew install ffmpeg`
- **Docker:** Installed in the Dockerfile via `apt-get install -y ffmpeg`
- **Render.com:** Installed in `buildCommand` via `apt-get install -y ffmpeg`

**Opus library** — required for Discord voice encoding. `bot.py` attempts to load automatically:

```python
try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus.so.0')
except Exception:
    print('[BOT] Warning: Opus library not found; voice features disabled')
```

If Opus is not found, the bot starts normally with voice features disabled (non-fatal).

### 2.3 Python Packages

**File:** `requirements.txt`

| Package | Version | Purpose |
|---------|---------|---------|
| `discord.py` | ≥ 2.6.4 | Core Discord API library |
| `yt-dlp` | ≥ 2024.12.23 | YouTube/audio downloading for music cogs |
| `PyNaCl` | ≥ 1.5.0 | Voice encryption (required for Discord voice) |
| `aiohttp` | ≥ 3.9.0 | Async HTTP client (used by various cogs for API calls) |
| `python-dotenv` | ≥ 1.0.0 | `.env` file loading for local development |
| `Pillow` | ≥ 10.0.0 | Image generation for card games and mining visuals |
| `aiofiles` | ≥ 23.2.1 | Async file I/O for activity worker in bot.py |
| `chess` | ≥ 1.10.0 | Chess game logic for `chess_checkers.py` |
| `googletrans` | (any) | Translation for multilingual responses |
| `fuzzywuzzy` | ≥ 0.18.0 | Fuzzy string matching for help system and card search |
| `python-Levenshtein` | ≥ 0.21.0 | C extension to speed up fuzzywuzzy matching |
| `psycopg2-binary` | ≥ 2.9.9 | PostgreSQL adapter (used by `utils/database.py` if PostgreSQL backend is configured) |

**Install:**
```bash
pip install -r requirements.txt
```

---

## 3. Configuration Files

### 3.1 config.json

**File:** `config.json` (project root, committed to repo)

```json
{
  "prefix": "L!",
  "owner_ids": [1138720397567742014, 1382187068373074001, 1311394031640776716, 1310134550566797352],
  "emojiServerId": [1445021753846796371, 1327316480983040000, 1455492650009624589, 1441089572628074700]
}
```

| Key | Type | Description |
|-----|------|-------------|
| `prefix` | string | Command prefix for all prefix-based commands (e.g. `L!help`) |
| `owner_ids` | int[] | Discord user IDs with bot-owner privileges; used by `Owner` cog's `cog_check` and stored in `bot.owner_ids` |
| `emojiServerId` | int[] | Discord server IDs the bot uses to host custom emoji (UNO cards, TCG cards, etc.) |

**To add a new bot owner:** Add their Discord user ID to `owner_ids` and restart the bot.

**To change the prefix:** Edit `prefix` and restart. All help text and documentation will reflect the new prefix automatically since commands reference `ctx.prefix`.

### 3.2 .env File

**File:** `.env` (project root, **NOT committed** — add to `.gitignore`)

```env
LUDUS_TOKEN=your_discord_bot_token_here
RENDER_DISK_PATH=/var/data
```

| Variable | Required | Description |
|----------|----------|-------------|
| `LUDUS_TOKEN` | ✅ Yes | Discord bot token from the [Developer Portal](https://discord.com/developers/applications). The bot exits immediately with `[FATAL]` if this is not set. |
| `RENDER_DISK_PATH` | ❌ No | Path to the persistent disk. Set automatically by Render.com. Omit for local development (falls back to `./data/`). |

`start.py` validates `LUDUS_TOKEN` before launching `bot.py`:
```python
if not os.environ.get('LUDUS_TOKEN'):
    print('LUDUS_TOKEN not set!')
    sys.exit(1)
```

`bot.py` also validates it:
```python
TOKEN = os.environ.get("LUDUS_TOKEN")
if not TOKEN:
    print("[FATAL] LUDUS_TOKEN environment variable not set!")
    sys.exit(1)
```

---

## 4. Local Development Setup

### 4.1 Initial Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd Ludus-Bot

# 2. Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
echo LUDUS_TOKEN=your_token_here > .env

# 5. Verify config.json has your Discord user ID in owner_ids
# Edit config.json and add your user ID to owner_ids
```

### 4.2 Launching the Bot

**Recommended (via start.py):**
```bash
python start.py
```

`start.py` loads the `.env` file, validates `LUDUS_TOKEN`, then launches `bot.py` as a subprocess:
```python
subprocess.run([sys.executable, 'bot.py'], check=True)
```

**Direct (for debugging):**
```bash
python bot.py
```

Launching `bot.py` directly also works — `bot.py` calls `dotenv.load_dotenv()` at the top, so the `.env` file is still loaded.

**Expected startup output:**
```
[COGS] Loading extensions...
  ✅ economy
  ✅ gambling
  ✅ fishing
  ... (all cogs)
==================================================
🚀 BOT IS READY!
👤 Account: Ludus#1234
📊 Guilds: 5
📁 Data Dir: C:\...\Ludus-Bot\data
==================================================
🌍 Syncing global commands...
✅ Successfully synced 47 commands.
```

Any cog that fails to load prints `❌ cogname -> <error>` but does not stop the bot from starting.

### 4.3 Data Directory (Local)

On local development (no `RENDER_DISK_PATH` set), data is stored in:
```
Ludus-Bot/
└── data/
    ├── economy.json
    ├── inventory.json
    ├── profiles.json
    ├── fishing_data.json
    ├── mining_data.json
    └── ... (all other data files)
```

`bot.py` creates this directory automatically:
```python
BASE_DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(BASE_DATA_DIR, exist_ok=True)
```

The `data/` directory should be added to `.gitignore` to prevent committing user data to the repository.

---

## 5. Docker Deployment

### 5.1 Dockerfile

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Install FFmpeg (required for Discord voice)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* 

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Run the bot
CMD ["python", "bot.py"]
```

**Key decisions:**
- `python:3.11-slim` — minimal Debian-based image; `slim` excludes development tools, reducing image size
- FFmpeg is installed in a single `RUN` layer with `apt-get clean` and `rm -rf /var/lib/apt/lists/*` to minimize layer size
- `--no-cache-dir` on pip install avoids storing package cache in the image
- Entrypoint is `bot.py` directly (not `start.py`) — Docker handles the process lifetime; `start.py`'s subprocess launch is unnecessary in a container

### 5.2 Building and Running

```bash
# Build the image
docker build -t ludus-bot .

# Run with environment variable and data volume
docker run -d \
  --name ludus-bot \
  --env LUDUS_TOKEN=your_token_here \
  --env RENDER_DISK_PATH=/data \
  --volume /host/path/to/data:/data \
  --restart unless-stopped \
  ludus-bot
```

### 5.3 Data Persistence with Docker

Without a volume mount, all data files inside the container are lost when the container is removed.

**Volume mount pattern:**
```bash
--volume /host/path/to/data:/data
--env RENDER_DISK_PATH=/data
```

Setting `RENDER_DISK_PATH=/data` tells all cogs to store their JSON files in `/data/` inside the container, which maps to `/host/path/to/data` on the host.

**docker-compose example:**
```yaml
version: '3.8'
services:
  ludus-bot:
    build: .
    environment:
      LUDUS_TOKEN: ${LUDUS_TOKEN}
      RENDER_DISK_PATH: /data
    volumes:
      - ./bot-data:/data
    restart: unless-stopped
```

With a `docker-compose.yml` and `.env` containing `LUDUS_TOKEN=...`:
```bash
docker-compose up -d
```

---

## 6. Render.com Deployment

### 6.1 render.yaml

**File:** `render.yaml`

```yaml
services:
  - type: web
    name: ludus-bot
    env: python
    region: oregon
    plan: free
    branch: main
    buildCommand: "pip install -r requirements.txt && apt-get update && apt-get install -y ffmpeg"
    startCommand: "python bot.py"
    envVars:
      - key: DISCORD_TOKEN
        sync: false
      - key: PYTHON_VERSION
        value: 3.11.0
```

| Field | Value | Notes |
|-------|-------|-------|
| `type` | `web` | Render web service (always-on process) |
| `name` | `ludus-bot` | Service name in Render dashboard |
| `env` | `python` | Python runtime |
| `region` | `oregon` | US West (Oregon) datacenter |
| `plan` | `free` | Free tier (512MB RAM, shared CPU) |
| `branch` | `main` | Auto-deploy from `main` branch |
| `buildCommand` | pip + ffmpeg | Installs Python deps and system FFmpeg |
| `startCommand` | `python bot.py` | Launches bot directly |
| `PYTHON_VERSION` | `3.11.0` | Pins Python version |
| `DISCORD_TOKEN` | `sync: false` | Must be set manually in Render dashboard (not synced from repo) |

**Important:** `render.yaml` references `DISCORD_TOKEN` but `bot.py` reads `LUDUS_TOKEN`. If deploying via `render.yaml`, ensure the actual environment variable key in the Render dashboard is `LUDUS_TOKEN` or update `render.yaml` to match.

### 6.2 Environment Variables on Render

Set these in the Render dashboard under **Service → Environment**:

| Variable | Value | How to Set |
|----------|-------|-----------|
| `LUDUS_TOKEN` | Your Discord bot token | Manual — Render dashboard → Environment |
| `RENDER_DISK_PATH` | `/var/data` | Automatic when disk is attached, or set manually |
| `PYTHON_VERSION` | `3.11.0` | From `render.yaml` (auto-synced) |

**To set `LUDUS_TOKEN` in the Render dashboard:**
1. Go to your service → **Environment** tab
2. Click **Add Environment Variable**
3. Key: `LUDUS_TOKEN`, Value: `Bot <your-token>` or just the token string
4. Click **Save Changes** — Render will redeploy automatically

### 6.3 Persistent Disk Configuration

**Why it's needed:** Render web services (and Docker containers) have an ephemeral filesystem — any files written during runtime are lost on the next deployment or restart. Without a persistent disk, all economy data, user profiles, gambling stats, fishing progress, etc. are wiped on every deploy.

**Setting up a Render disk:**
1. In Render dashboard → your service → **Disks** tab
2. Click **Add Disk**
3. Name: `ludus-data` (or any name)
4. Mount Path: `/var/data`
5. Size: 1 GB (minimum; adjust based on user count)
6. Save — Render mounts the disk and automatically sets `RENDER_DISK_PATH=/var/data`

**Result:** All data files are written to `/var/data/` and survive deployments, restarts, and container replacements.

**Storage estimate:**
- Each active user: ~5–20 KB across all JSON files
- 1,000 active users: ~5–20 MB
- 10,000 active users: ~50–200 MB
- 1 GB disk supports tens of thousands of active users

### 6.4 Startup Script (start.sh)

**File:** `start.sh` — an alternative entrypoint for Render that initializes data files before starting the bot.

```bash
#!/bin/bash

echo "🤖 Starting Ludus Bot..."
DATA_DIR="${RENDER_DISK_PATH:-.}"
mkdir -p "$DATA_DIR"

DATA_FILES=(
    "economy.json"
    "inventory.json"
    "pets.json"
    "gambling_stats.json"
    "leaderboard_stats.json"
    "fishing_data.json"
    "wyr_questions.json"
    "stories.json"
    "quests_data.json"
    "achievements_data.json"
)

for file in "${DATA_FILES[@]}"; do
    filepath="$DATA_DIR/$file"
    if [ ! -f "$filepath" ]; then
        echo "📝 Creating $file..."
        echo "{}" > "$filepath"
    fi
done

python bot.py
```

**What it does:**
1. Reads `RENDER_DISK_PATH` (defaults to `.` if not set)
2. Creates the data directory if missing
3. Pre-initializes 10 critical data files as `{}` if they don't exist — prevents `FileNotFoundError` on first run before any user has interacted with the system
4. Launches `bot.py`

**To use `start.sh` as the entrypoint** on Render, change `startCommand` in `render.yaml`:
```yaml
startCommand: "bash start.sh"
```

Or for Docker:
```dockerfile
CMD ["bash", "start.sh"]
```

The individual cogs also initialize their own files on first access, so `start.sh` is a safety net rather than a strict requirement.

---

## 7. Data Persistence Architecture

### 7.1 RENDER_DISK_PATH Pattern

Every cog that writes persistent data follows the same envvar pattern:

```python
import os

# Module-level constant (evaluated once at import time)
DATA_FILE = os.path.join(os.getenv("RENDER_DISK_PATH", "data"), "cog_data.json")
```

This means:
- **On Render with disk:** `RENDER_DISK_PATH=/var/data` → files go to `/var/data/cog_data.json`
- **Locally:** `RENDER_DISK_PATH` not set → files go to `./data/cog_data.json`
- **Docker with volume:** `RENDER_DISK_PATH=/data` → files go to `/data/cog_data.json`

Some cogs use `bot.data_dir` (set in `bot.py`) instead of reading `RENDER_DISK_PATH` directly, but both resolve to the same directory.

### 7.2 Files That Must Persist

The following files contain user data that **must** be on a persistent disk in production:

| File | Owner Cog | Data Lost Without Persistence |
|------|-----------|-------------------------------|
| `economy.json` | Economy | All user coin balances, streaks |
| `inventory.json` | Economy | All user item inventories |
| `profiles.json` | Profile | All user profiles (bio, badges, stats) |
| `fishing_data.json` | Fishing | All fishing progress, catches, gear |
| `mining_data.json` | Mining | All mining progress, upgrades |
| `pets.json` | Pets | All adopted pets and their stats |
| `farms.json` | Farming | All farm plots and crop progress |
| `gambling_stats.json` | Gambling | All gambling history and win/loss stats |
| `leaderboard_stats.json` | Leaderboards | All game scores and rankings |
| `quests_data.json` | Quests | All active and completed quests |
| `user_achievements.json` | Achievements | All awarded achievements |
| `blacklist.json` | Blacklist | All blacklisted users and servers |
| `confession_config.json` | Confessions | Per-guild confession channel config |
| `server_configs.json` | ServerConfig | Per-guild bot configuration |
| `custom_roles.json` | Owner | All custom Mafia/Werewolf roles |
| `stories.json` | Activities | Community story content |
| `lottery.json` | Lottery | Active lottery state and participants |
| `counting.json` | Counting | Per-guild counting game progress |
| `starboard.json` | Starboard | Posted starboard message map |
| `global_consent.json` | GlobalLeaderboard | Server opt-in consent records |
| `data/economy.json` (in data/) | Economy | Same as economy.json — verify path |

**Files that do NOT need persistence** (regenerated at startup):
- `logs/` — Log files; losing them is acceptable
- `user_activity.json` — Activity log; append-only, historical only
- `__pycache__/` — Python bytecode cache

### 7.3 Atomic Write Safety

All cogs that save data use the atomic write pattern to prevent corruption:

```python
import os

def save_data(data, filepath):
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)  # Atomic on all POSIX systems
```

`os.replace()` is atomic on Linux/macOS/POSIX filesystems — the file either fully replaces the old version or doesn't change at all. This prevents partial writes that could corrupt JSON if the process is killed mid-write (e.g., during a Render deployment restart).

---

## 8. Discord Application Setup

### 8.1 Required Intents

The bot requires these Gateway Intents enabled in the [Discord Developer Portal](https://discord.com/developers/applications) under **Bot → Privileged Gateway Intents**:

| Intent | Setting in Portal | Why Required |
|--------|------------------|--------------|
| **Message Content Intent** | ✅ Must enable | Reading message content for prefix commands, counting game, confessions |
| **Server Members Intent** | ✅ Must enable | Accessing member lists for rain coins, marriage, user info |
| **Presence Intent** | Optional | `rain_coins` filters offline members; presence events in BotLogger |

**In bot.py:**
```python
intents = discord.Intents.default()
intents.message_content = True   # Privileged
intents.members = True           # Privileged
intents.voice_states = True      # For voice/music features
```

Without `message_content = True`: prefix commands won't receive message text (all `L!` commands break).
Without `members = True`: member list access fails (rain coins, some leaderboard features break).

### 8.2 Required Bot Permissions

The bot needs these permissions when added to a server (set in OAuth2 URL generator):

| Permission | Why |
|-----------|-----|
| Send Messages | Core functionality |
| Send Messages in Threads | Thread-based game sessions |
| Embed Links | All command responses use embeds |
| Attach Files | Card game images, fishing images, mining images |
| Read Message History | Starboard, counting, confession cleanup |
| Add Reactions | Starboard reactions, raid boss (spawn command) |
| Manage Messages | Purge command, counting violation deletion |
| Manage Roles | Counting milestone role rewards (if configured) |
| Use External Emojis | UNO cards, TCG cards from emoji servers |
| Connect | Voice features |
| Speak | Voice/music features |

**Recommended permission integer:** `397284884032` (covers all the above)

**OAuth2 invite URL format:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=397284884032&scope=bot%20applications.commands
```

The `applications.commands` scope is required for slash command registration.

### 8.3 Emoji Servers

Ludus Bot uses custom emoji hosted on dedicated Discord servers for UNO cards, TCG cards, and other visual assets.

**Configured in `config.json`:**
```json
"emojiServerId": [1445021753846796371, 1327316480983040000, 1455492650009624589, 1441089572628074700]
```

The bot must be a member of these servers (with the "Use External Emojis" permission) to render card images and game visuals correctly. Without access to these servers, games still function but emoji display as missing/unknown characters.

**UNO emoji mapping** is loaded at startup in `setup_hook()`:
```python
from cogs.uno import uno_logic
emoji_mapping = uno_logic.load_emoji_mapping('classic')
back_emoji_id = emoji_mapping.get('uno_back.png')
if back_emoji_id:
    constants.UNO_BACK_EMOJI = f"<:uno_back:{back_emoji_id}>"
```

---

## 9. Startup Sequence Reference

Complete ordered sequence from process launch to fully operational bot:

```
python start.py
│
├─ dotenv.load_dotenv()              ← loads .env into os.environ
├─ validate LUDUS_TOKEN              ← exits with error if missing
└─ subprocess.run(['python', 'bot.py'])
        │
        ├─ dotenv.load_dotenv()      ← loads .env again (redundant but harmless)
        ├─ detect RENDER_DISK_PATH   ← sets BASE_DATA_DIR
        ├─ os.makedirs(BASE_DATA_DIR)
        ├─ open("config.json")       ← loads prefix, owner_ids, emojiServerId
        ├─ discord.Intents.default() + message_content + members + voice_states
        ├─ BotCommandTree created
        ├─ commands.Bot() initialized
        ├─ bot.data_dir = BASE_DATA_DIR
        ├─ ludus_logging.init(bot)
        │
        └─ bot.run(TOKEN)
                │
                ├─ setup_hook()      ← fires before Discord connection
                │       ├─ load UNO emoji mapping → constants.UNO_BACK_EMOJI
                │       ├─ load_cogs()
                │       │       └─ iterate ./cogs/ → load_extension("cogs.X")
                │       │           Each cog's __init__ runs:
                │       │           ├─ Load own JSON data files
                │       │           ├─ Start background tasks (if any)
                │       │           └─ Register commands with bot.tree
                │       ├─ user_storage.init_user_storage_worker(bot.loop)
                │       └─ asyncio.create_task(activity_worker())
                │
                └─ on_ready()        ← fires after connected to Discord
                        ├─ stat_hooks.us_set_bot(bot)
                        ├─ Print ready summary
                        ├─ bot.tree.sync()  ← register slash commands globally
                        │   (takes 1-60 min to propagate to all Discord clients)
                        └─ bot.change_presence(activity=discord.Game("minigames"))
```

**First-run notes:**
- Slash commands registered via `bot.tree.sync()` take **up to 1 hour** to appear in all Discord clients globally. They are available immediately in the server where sync was triggered.
- Data JSON files are created on first use by each cog — no manual initialization required (unless using `start.sh` as a safety net).

---

## 10. Operational Procedures

### 10.1 Reloading Cogs

While the bot is running, cogs can be hot-reloaded without a full restart. This is the primary way to deploy small code changes to a single cog:

**Reload a single cog:**
```
L!reload <cog_name>
```
Examples:
```
L!reload economy
L!reload gambling
L!reload fishing
```

**Reload all cogs at once:**
```
L!reloadall
```

Returns a breakdown of successful and failed reloads. Failed cogs remain running with their previous code.

**Limitations of hot-reload:**
- Does **not** re-register slash commands — run `L!sync` or use a full restart to update slash command definitions
- Module-level constants (like `CUSTOM_ROLES_FILE` path) are re-evaluated on reload
- Any in-memory game state held in the reloaded cog (active games, lobby data) is lost

### 10.2 Restarting the Bot

**Via owner command (graceful):**
```
L!restart
```

Sends a "Restarting..." message, closes the Discord connection cleanly, then re-executes the bot process via:
```python
os.execv(sys.executable, [sys.executable] + sys.argv)
```

This replaces the current process with a fresh instance, reloading all code and re-connecting from scratch. On Render.com, if `os.execv` fails, it falls back to `os._exit(0)` which causes Render to restart the service automatically.

**After a code deployment on Render:**
Render automatically restarts the service on every push to `main`. No manual action required.

**Manual restart on Render:**
Render dashboard → Service → **Manual Deploy** button, or push a commit to `main`.

### 10.3 Migrating User Data

**File:** `migrate_users.py` (project root)

This utility script handles data migration between schema versions. Run it when upgrading the bot to a new version that changes JSON data structures:

```bash
python migrate_users.py
```

**When to run:**
- After pulling a major bot update that adds new fields to existing data files
- After a version that changes the schema of `economy.json`, `profiles.json`, or other core files

**Before running:** Always back up all data files first (see §10.4).

### 10.4 Backing Up Data Files

**On Render (with persistent disk):**
Render does not automatically back up disk contents. Manual backup options:

1. **Download via SSH** (Render paid plans): SSH into service, `tar -czf backup.tar.gz /var/data/`
2. **Bot command export**: Implement a periodic backup command that dumps data to a Discord channel or external storage
3. **Copy to S3**: Write a cron-style task that copies `/var/data/` to an S3 bucket using `aiohttp`

**Locally:**
```bash
# Copy the entire data directory
cp -r data/ data_backup_$(date +%Y%m%d)/

# Or just key files
cp data/economy.json data/economy.backup.json
cp data/profiles.json data/profiles.backup.json
```

**On Docker:**
```bash
docker cp ludus-bot:/data ./data_backup_$(date +%Y%m%d)/
```

---

## 11. Troubleshooting

### Bot shows as offline / doesn't start

1. Check `LUDUS_TOKEN` is set correctly — token starts with bot-specific prefix
2. Verify the token hasn't been regenerated in the Developer Portal (regenerating invalidates the old token)
3. Check terminal for `[FATAL]` output

### Slash commands don't appear

1. Wait up to 1 hour after first deployment (global sync delay)
2. Confirm invite URL includes `applications.commands` scope
3. Run `L!reload` then restart to force re-sync
4. Check `bot.tree.sync()` completed without error in startup logs

### Cog fails to load (`❌ cogname -> ...`)

1. Read the full error message — most are `ImportError` (missing package) or `SyntaxError` (broken code)
2. For `ImportError`: install the missing package from `requirements.txt`
3. For `ModuleNotFoundError` on a util: verify the file exists in `utils/`
4. Other cogs continue loading normally; the failed cog's commands simply won't be available

### Data files not persisting between restarts (Render)

1. Verify `RENDER_DISK_PATH` environment variable is set in Render dashboard
2. Verify the disk is attached and mounted at the correct path
3. Check cog code uses `os.getenv("RENDER_DISK_PATH", "data")` — not a hardcoded relative path
4. Confirm the disk isn't full (`df -h /var/data`)

### Economy / profile data missing after deploy

The most common cause: the disk was not attached when the bot ran, so all data was written to the ephemeral container filesystem instead of the persistent disk. The data is lost.

Prevention: Always set up the persistent disk **before** the first run in production.

### `Opus library not found`

Voice features (music) are disabled but the bot starts normally. To fix:
- **Linux:** `sudo apt-get install libopus0`
- **Docker:** Add `apt-get install -y libopus-dev` to Dockerfile
- **Render:** Add `libopus-dev` to `buildCommand`

### `fuzzywuzzy` / `Levenshtein` warnings

If you see `UserWarning: Using slow pure-python SequenceMatcher`, `python-Levenshtein` is not installed. Install it:
```bash
pip install python-Levenshtein
```
This is listed in `requirements.txt` but may not install on all platforms without C compiler tools.

---

*Part 15 complete — full documentation series finished. See [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) for the complete documentation map across all 15 parts.*
