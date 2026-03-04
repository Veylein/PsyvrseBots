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

# Import local modules
import constants
import ludus_logging
from utils import user_storage
import aiofiles

# 1. PATH CONFIGURATION (PRIORITY)
dotenv.load_dotenv()

# Check if running on Render with a persistent disk attached
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH")
if RENDER_DISK_PATH:
    BASE_DATA_DIR = RENDER_DISK_PATH
else:
    # Local fallback for development
    BASE_DATA_DIR = os.path.join(os.getcwd(), "data")

# Ensure the data directory exists
try:
    os.makedirs(BASE_DATA_DIR, exist_ok=True)
except PermissionError:
    # If /var/data is restricted, fallback to current working directory
    BASE_DATA_DIR = os.path.join(os.getcwd(), "data")
    os.makedirs(BASE_DATA_DIR, exist_ok=True)

# Define file paths based on BASE_DATA_DIR
LUDUS_QA_PATH = os.path.join(BASE_DATA_DIR, 'ludus_qa.json')
LOG_DIR = os.path.join(BASE_DATA_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 2. DATA LOADING FUNCTIONS
def load_ludus_qa():
    """Load Q&A data from the persistent storage."""
    try:
        if not os.path.exists(LUDUS_QA_PATH):
            return {"questions": [], "users": {}}
        with open(LUDUS_QA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load QA data: {e}")
        return {"questions": [], "users": {}}

def save_ludus_qa(data):
    """Save Q&A data to the persistent storage."""
    try:
        with open(LUDUS_QA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving QA data: {e}")

# Initialize QA data
ludus_qa_data = load_ludus_qa()

# 3. LOGGING CONFIGURATION
handlers_list = [logging.StreamHandler()]
log_file_path = os.path.join(LOG_DIR, "ludus.log")

try:
    # Setup rotating file handler for logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path, 
        maxBytes=5 * 1024 * 1024, # 5MB per file
        backupCount=5, 
        encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    handlers_list.append(file_handler)
except Exception as e:
    print(f"Warning: Could not set up file logging: {e}")

logging.basicConfig(level=logging.INFO, handlers=handlers_list)
logger = logging.getLogger("ludus")

# 4. BOT CORE SETUP
TOKEN = os.environ.get("LUDUS_TOKEN")
if not TOKEN:
    print("[FATAL] LUDUS_TOKEN environment variable not set!")
    sys.exit(1)

# Attempt to load Opus for voice features
try:
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('libopus.so.0')
        except Exception:
            discord.opus.load_opus()
except Exception:
    print('[BOT] Warning: Opus library not found; voice features disabled')

# Load configuration from JSON
with open("config.json") as f:
    config = json.load(f)

# Set intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

owner_ids_set = set(config.get("owner_ids", []))

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

# Initialize Bot instance
bot = commands.Bot(
    command_prefix=config["prefix"],
    intents=intents,
    owner_ids=owner_ids_set,
    help_command=None,
    tree_cls=BotCommandTree,
    description="🎮 The ultimate Discord minigame & music bot!",
    max_messages=1000,
    chunk_guilds_at_startup=False,
    heartbeat_timeout=120.0,
)

# Attach persistent data directory to the bot object for Cog access
bot.data_dir = BASE_DATA_DIR

# Initialize external logging helpers
try:
    ludus_logging.init(bot)
except Exception:
    pass

# Initialize game states
bot.active_games = {}
bot.active_lobbies = {}
bot.active_minigames = {}
bot.pending_rematches = {}

# 5. ACTIVITY WORKERS & QUEUES
activity_queue = asyncio.Queue()
BATCH_SIZE = 50
BATCH_INTERVAL = 2.0

async def activity_worker():
    """Background worker to batch-save user activity to disk."""
    batch = []
    activity_file = os.path.join(bot.data_dir, "user_activity.json")
    while True:
        try:
            try:
                # Wait for data with a timeout to trigger saves even if batch isn't full
                data = await asyncio.wait_for(activity_queue.get(), timeout=BATCH_INTERVAL)
                batch.append(data)
                activity_queue.task_done()
            except asyncio.TimeoutError:
                pass

            # If the queue is busy, drain it up to BATCH_SIZE
            while len(batch) < BATCH_SIZE:
                try:
                    data = activity_queue.get_nowait()
                    batch.append(data)
                    activity_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if batch:
                async with aiofiles.open(activity_file, "a") as f:
                    lines = [json.dumps(entry) + "\n" for entry in batch]
                    await f.writelines(lines)
                batch.clear()
        except Exception as e:
            print(f"[ACTIVITY WORKER] Error saving activity: {e}")
            batch.clear()

def _record_user_activity(user_id, username, interaction_type, name, extra=None):
    """Helper to queue activity data."""
    data = {
        "user_id": user_id,
        "username": username,
        "type": interaction_type,
        "name": name,
        "extra": extra or {},
        "timestamp": str(datetime.utcnow())
    }
    activity_queue.put_nowait(data)

# 6. BOT EVENTS
@bot.event
async def setup_hook():
    """Initialization before the bot connects to Discord."""
    try:
        from cogs.uno import uno_logic
        emoji_mapping = uno_logic.load_emoji_mapping('classic')
        back_emoji_id = emoji_mapping.get('uno_back.png')
        if back_emoji_id:
            constants.UNO_BACK_EMOJI = f"<:uno_back:{back_emoji_id}>"
    except Exception as e:
        print(f"[BOT] Failed to load UNO assets: {e}")
    
    # Load all Cog extensions
    await load_cogs()
    
    # Start background tasks
    try:
        user_storage.init_user_storage_worker(bot.loop)
    except Exception as e:
        print(f"[BOT] Failed to init storage worker: {e}")
    
    bot.loop.create_task(activity_worker())

@bot.event
async def on_ready():
    """Triggered when the bot is online."""
    try:
        from utils.stat_hooks import us_set_bot
        us_set_bot(bot)
    except Exception:
        pass

    print("\n" + "="*50)
    print(f"🚀 BOT IS READY!")
    print(f"👤 Account: {bot.user}")
    print(f"📊 Guilds: {len(bot.guilds)}")
    print(f"📁 Data Dir: {bot.data_dir}")
    print("="*50)
    
    # Sync Slash Commands
    try:
        print("🌍 Syncing global commands...")
        synced = await bot.tree.sync()
        print(f"✅ Successfully synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Command sync failed: {e}")

    await bot.change_presence(activity=discord.Game(name="minigames"))

@bot.event
async def on_message(message):
    """Main message handler."""
    if message.author == bot.user:
        return

    # Create/Update user file in persistent storage
    try:
        asyncio.create_task(user_storage.touch_user(message.author.id, getattr(message.author, 'name', None)))
    except Exception:
        pass

    # Pass message to AI Personality cog if loaded
    personality_cog = bot.get_cog("LudusPersonality")
    if personality_cog:
        try:
            await personality_cog.on_message(message)
        except Exception:
            pass

    # Process standard prefix commands
    await bot.process_commands(message)

# 7. COG LOADING LOGIC
async def load_cogs():
    """Dynamically load Cog extensions from the /cogs directory."""
    if not os.path.exists("./cogs"):
        print("❌ Cogs directory missing!")
        return

    print("\n[COGS] Loading extensions...")
    for entry in os.listdir("./cogs"):
        cog_name = None
        if entry.endswith(".py"):
            cog_name = entry[:-3]
        elif os.path.isdir(os.path.join("./cogs", entry)) and os.path.exists(os.path.join("./cogs", entry, "__init__.py")):
            cog_name = entry

        if cog_name:
            try:
                await bot.load_extension(f"cogs.{cog_name}")
                print(f"  ✅ {cog_name}")
            except Exception as e:
                print(f"  ❌ {cog_name} -> {e}")
                traceback.print_exc()

# ENTRY POINT
if __name__ == "__main__":
    print("[MAIN] Launching Ludus Bot...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"[FATAL] Connection error: {e}")
