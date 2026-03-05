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
    print(f"👤 Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print(f"🛡️ Bot owner_ids: {bot.owner_ids}")
    try:
        app_info = await bot.application_info()
        print(f"👑 Application owner: {app_info.owner.id}")
    except:
        print(f"👑 Application owner: Unknown")

    print(f"\n📊 Statistics:")
    print(f"   • Guilds: {len(bot.guilds)}")
    print(f"   • Users: {len(bot.users)}")
    print(f"   • Cogs loaded: {len(bot.cogs)}")

    # List all loaded cogs
    print(f"\n🃏 Active Cogs ({len(bot.cogs)}):")
    for cog_name in sorted(bot.cogs.keys()):
        cog = bot.cogs[cog_name]
        cog_commands = [cmd for cmd in bot.walk_commands() if cmd.cog_name == cog_name]
        cog_app_commands = [cmd for cmd in bot.tree.walk_commands() if hasattr(cmd, 'binding') and cmd.binding == cog]
        total = len(cog_commands) + len(cog_app_commands)
        print(f"   • {cog_name} ({total} commands)")

    # Count and list commands
    text_commands = [c for c in bot.commands]

    # Get ALL app commands including those in groups
    all_app_commands = []
    for cmd in bot.tree.walk_commands():
        all_app_commands.append(cmd)

    print(f"\n⚡ Commands Summary:")
    print(f"   • Text commands: {len(text_commands)}")
    print(f"   • Slash commands: {len(all_app_commands)} (walk_commands)")
    print(f"   • Top-level slash: {len(bot.tree.get_commands())} (get_commands)")
    print(f"   • Total: {len(text_commands) + len(all_app_commands)}")

    # List text commands
    if text_commands:
        print(f"\n📜 Text Commands ({len(text_commands)}):")
        for cmd in sorted(text_commands, key=lambda x: x.name):
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            cog_name = cmd.cog_name if cmd.cog_name else "No Cog"
            print(f"   • {config['prefix']}{cmd.name}{aliases} [{cog_name}]")

    # List slash commands
    if all_app_commands:
        # Separate global and guild commands
        global_cmds = []
        guild_cmds = []

        for cmd in all_app_commands:
            if hasattr(cmd, 'guild_ids') and cmd.guild_ids:
                guild_cmds.append(cmd)
            else:
                global_cmds.append(cmd)

        print(f"\n⚡ Slash Commands ({len(all_app_commands)} total):")
        print(f"   🌍 Global: {len(global_cmds)}")
        print(f"   🏰 Guild-specific: {len(guild_cmds)}")

        if global_cmds:
            print(f"\n🌍 Global Commands ({len(global_cmds)}):")

            root_commands = {}
            subcommands = {}

            for cmd in global_cmds:
                if hasattr(cmd, 'parent') and cmd.parent:
                    parent_name = cmd.parent.qualified_name
                    if parent_name not in subcommands:
                        subcommands[parent_name] = []
                    subcommands[parent_name].append(cmd)
                else:
                    root_commands[cmd.name] = cmd

            for cmd_name in sorted(root_commands.keys()):
                cmd = root_commands[cmd_name]
                cog_name = cmd.binding.__cog_name__ if hasattr(cmd, 'binding') and cmd.binding else "Unknown"

                if cmd.qualified_name in subcommands:
                    print(f"   • /{cmd.name} [GROUP] ({cog_name})")
                    for subcmd in sorted(subcommands[cmd.qualified_name], key=lambda x: x.name):
                        print(f"      ├─ /{cmd.name} {subcmd.name}")
                else:
                    print(f"   • /{cmd.name} ({cog_name})")

            for parent_name, subs in subcommands.items():
                if parent_name not in root_commands:
                    print(f"   • /{parent_name} [MISSING PARENT]")
                    for subcmd in subs:
                        print(f"      ├─ {subcmd.name}")

        if guild_cmds:
            print(f"\n🏰 Guild-Specific Commands ({len(guild_cmds)}):")
            for cmd in sorted(guild_cmds, key=lambda x: x.qualified_name):
                guild_ids_str = f" [Guilds: {', '.join(str(g) for g in (cmd.guild_ids or [])[:3])}]"
                cog_name = cmd.binding.__cog_name__ if hasattr(cmd, 'binding') and cmd.binding else "Unknown"
                print(f"   • /{cmd.qualified_name} ({cog_name}){guild_ids_str}")

    # ===== DEV GUILD COMMAND SYNC SYSTEM =====
    print("\n" + "="*50)
    print("🔄 SYNCING SLASH COMMANDS...")
    print("="*50)

    # Delete Activity Entry Point commands before sync (Discord rejects bulk sync that removes them)
    try:
        app_id = bot.application_id
        global_cmds = await bot.http.get_global_commands(app_id)
        for gc in global_cmds:
            if gc.get("type") == 4:  # 4 = PRIMARY_ENTRY_POINT
                await bot.http.delete_global_command(app_id, gc["id"])
                print(f"   🗑️  Deleted Activity entry-point: '{gc['name']}' (id {gc['id']})")
    except Exception as ep_err:
        print(f"   ⚠️  Could not remove entry-point: {ep_err}")

    # Clear guild-specific commands from ALL guilds (removes duplicates)
    print("🧹 Clearing guild-specific commands (fixes duplicates)...")
    cleared = 0
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            cleared += 1
        except Exception:
            pass
    print(f"   ✅ Cleared guild commands from {cleared}/{len(bot.guilds)} guilds.")

    DEV_ONLY_COMMANDS = []  # Only non-entry-point commands for dev guild testing

    try:
        import os

        dev_guilds_raw = os.environ.get('DEV_GUILD_IDS') or os.environ.get('DEV_GUILD_ID')
        if dev_guilds_raw:
            print("🛠️ DEV_GUILD_ID detected - splitting commands")
            dev_guild_ids = [int(g.strip()) for g in dev_guilds_raw.split(',') if g.strip()]
            dev_guild_objs = [discord.Object(id=gid) for gid in dev_guild_ids]

            dev_only_roots = {name.lower() for name in DEV_ONLY_COMMANDS}
            restricted = []
            skipped_entry_point = []
            if dev_only_roots:
                for cmd_name_lower in list(dev_only_roots):
                    cmd = bot.tree.get_command(cmd_name_lower)
                    if cmd is None:
                        continue
                    cmd_type = getattr(cmd, "type", None)
                    is_entry_point = str(cmd_type).lower().endswith("primary_entry_point") or cmd_name_lower == "start"
                    if is_entry_point:
                        skipped_entry_point.append(cmd.name)
                        continue
                    bot.tree.remove_command(cmd_name_lower)
                    for guild_obj in dev_guild_objs:
                        bot.tree.add_command(cmd, guild=guild_obj)
                    restricted.append(cmd.name)

            if restricted:
                print(f"🔧 Dev-only commands: {', '.join(sorted(restricted))}")
            elif DEV_ONLY_COMMANDS:
                print("ℹ️ No matching commands found for DEV_ONLY_COMMANDS list.")

            if skipped_entry_point:
                print("   Warning: entry point command(s) cannot be dev-only and were left global.")
                print("   " + ", ".join(sorted(set(skipped_entry_point))))

            print("\n🌍 Syncing global commands (dev-only ones remain guild-scoped)...")
            try:
                synced_global = await bot.tree.sync()
                print(f"   • Synced {len(synced_global)} global commands.")
            except discord.HTTPException as http_error:
                if http_error.code == 50240:
                    print("   ⚠️ Global sync rejected (50240): entry-point command removal is not allowed.")
                    print("   ⚠️ Keeping entry-point commands global and continuing startup.")
                    print("   ⚠️ Remove the entry-point command from DEV_ONLY_COMMANDS to avoid this.")
                else:
                    raise

            if restricted:
                print(f"\n🏰 Syncing dev-only commands to {len(dev_guild_objs)} dev guild(s)...")
                for guild_obj in dev_guild_objs:
                    try:
                        synced_guild = await bot.tree.sync(guild=guild_obj)
                        print(f"   • Guild {guild_obj.id}: synced {len(synced_guild)} commands.")
                    except Exception as guild_sync_err:
                        print(f"   ❌ Guild {guild_obj.id} sync failed: {guild_sync_err}")
        else:
            # No dev guild configured, sync all commands globally
            print("🌍 Syncing all commands globally...")
            synced_commands = await bot.tree.sync()
            print(f"   • Synced {len(synced_commands)} commands.")

        print("🌍 Syncing global commands...")
        synced = await bot.tree.sync()
        print(f"✅ Successfully synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Error in command sync logic: {e}")
        traceback.print_exc()
        try:
            ludus_logging.log_exception(e, message="Failed during command sync")
        except Exception:
            pass

    print("="*50)

    # Set bot's presence
    try:
        game = discord.Game(name="minigames")
        await bot.change_presence(activity=game)
        print("✅ Presence updated to 'Playing minigames'")
    except Exception as e:
        print(f"❌ Failed to set presence: {e}")
        traceback.print_exc()

    print("="*50)
    print("✅ All startup tasks complete. Bot is fully operational.")
    print("="*50)

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
