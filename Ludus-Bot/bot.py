import sys
import discord
from discord.ext import commands
import json
import os
import asyncio
import traceback
import dotenv
import constants
import logging
import logging.handlers
from pathlib import Path
import ludus_logging
from utils import user_storage
from datetime import datetime
import aiofiles
from googletrans import Translator
import difflib

dotenv.load_dotenv()
# Configure logging to file+console. If Render provides a disk path, use it.
LOG_DIR = Path(os.getenv("RENDER_DISK_PATH", ".")) / "logs"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
log_file = LOG_DIR / "ludus.log"
handler = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), handler])
logger = logging.getLogger("ludus")

# Ensure asyncio unhandled exceptions are routed to our logger
def handle_asyncio_exception(loop, context):
    err = context.get("exception") or context.get("message")
    try:
        logger.exception("Unhandled async exception: %s", err)
    except Exception:
        print("Unhandled async exception:", err)

try:
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_asyncio_exception)
except Exception:
    pass
if not os.environ.get("LUDUS_TOKEN"):
        print("LUDUS_TOKEN not set!")
        sys.exit(1)

# Load Opus for voice support (optional) — don't crash if library missing
try:
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('libopus.so.0')
        except Exception:
            # attempt default platform loader; if still missing, skip voice features
            try:
                discord.opus.load_opus()
            except Exception:
                print('[BOT] Warning: Opus library not found; voice features disabled')
except Exception:
    # Some environments may not expose opus APIs; continue without voice
    print('[BOT] Warning: could not initialize opus; continuing without voice')

# Load config
with open("config.json") as f:
    config = json.load(f)

print(f"[BOT] Loaded config: {config}")
print(f"[BOT] Owner IDs from config: {config.get('owner_ids', [])}")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# Pass owner_ids directly to Bot constructor - this is the CORRECT way
owner_ids_set = set(config.get("owner_ids", []))
print(f"[BOT] Creating bot with owner_ids: {owner_ids_set}")

# Remove default help command so our custom help.py can work
bot = commands.Bot(
    command_prefix=config["prefix"], 
    intents=intents, 
    owner_ids=owner_ids_set,
    help_command=None,  # Disable default help to use custom help cog
    description="🎮 The ultimate Discord minigame & music bot! Use `L!about` and `L!help` to get started. Made with ❤️ by Psyvrse Development.",
    # Performance/stability settings for cloud hosting
    max_messages=1000,  # Limit message cache to reduce memory
    chunk_guilds_at_startup=False,  # Don't fetch all members on startup
    heartbeat_timeout=120.0,  # Increase heartbeat timeout for unstable connections (default: 60)
)

# Initialize Discord log forwarding helper (sends detailed logs to LOG_CHANNEL)
try:
    ludus_logging.init(bot)
except Exception:
    pass

# Initialize game state storage for UNO and other games
bot.active_games = {}
bot.active_lobbies = {}
bot.active_minigames = {}
bot.pending_rematches = {}


def _record_user_activity(user_id: int, username: str | None, activity_type: str, name: str, extra: dict | None = None):
    """Record user activity in background without blocking."""
    try:
        loop = bot.loop
        if loop and loop.is_running():
            # Use asyncio.create_task for async function
            asyncio.create_task(user_storage.record_activity(int(user_id), username, activity_type, name, extra))
    except Exception:
        pass


# Wrap CommandTree.add_command to ignore duplicate registrations gracefully.
# This prevents CommandAlreadyRegistered exceptions during cog injection
# when multiple cogs or bridge modules try to register the same slash name.
try:
    _original_add_command = bot.tree.add_command
    # Expose original add_command so cogs can bypass the duplicate-skip when
    # they intentionally want to register a guild-scoped copy of a command.
    bot._original_tree_add_command = _original_add_command

    def _safe_add_command(command, **kwargs):
        # command may be app_commands.Command or app_commands.Group
        try:
            name = getattr(command, 'name', None) or getattr(command, '__name__', None)
        except Exception:
            name = None
        # If command with same name already exists, skip silently
        try:
            if name and bot.tree.get_command(name) is not None:
                print(f"[BOT] Skipping duplicate app command registration: {name}")
                return bot.tree.get_command(name)
        except Exception:
            pass
        try:
            return _original_add_command(command, **kwargs)
        except Exception as e:
            # If it's a duplication error from discord internals, log and continue
            try:
                from discord.app_commands import CommandAlreadyRegistered
                if isinstance(e, CommandAlreadyRegistered) or 'already registered' in str(e):
                    print(f"[BOT] Duplicate app command detected and ignored: {name} -> {e}")
                    return bot.tree.get_command(name)
            except Exception:
                pass
            raise

    bot.tree.add_command = _safe_add_command
except Exception:
    # If anything goes wrong, continue without monkeypatching
    pass


# Setup hook to load UNO emoji before cogs initialize
@bot.event
async def setup_hook():
    try:
        from cogs.uno import uno_logic
        # Load emoji mapping and get back emoji
        emoji_mapping = uno_logic.load_emoji_mapping('classic')
        back_emoji_id = emoji_mapping.get('uno_back.png')
        if back_emoji_id:
            constants.UNO_BACK_EMOJI = f"<:uno_back:{back_emoji_id}>"
    except Exception as e:
        print(f"[BOT] Failed to load UNO emoji: {e}")
        traceback.print_exc()
        try:
            ludus_logging.log_exception(e, message="Failed to load UNO emoji during setup_hook")
        except Exception:
            pass
    
    # Now load all cogs
    await load_cogs()
    
    # Initialize user storage batch worker
    try:
        from utils import user_storage
        user_storage.init_user_storage_worker(bot.loop)
    except Exception as e:
        print(f"[BOT] Failed to initialize user storage worker: {e}")
        traceback.print_exc()
    
    # Start activity worker
    try:
        bot.loop.create_task(activity_worker())
        print("[BOT] Activity worker started")
    except Exception as e:
        print(f"[BOT] Failed to start activity worker: {e}")
        traceback.print_exc()


activity_queue = asyncio.Queue()
BATCH_SIZE = 50       # how many entries we collect before saving
BATCH_INTERVAL = 2.0  # save every 2 seconds, even if the batch is not full

async def activity_worker():
    batch = []
    while True:
        try:
            try:
                # wait for the first element of the batch with a timeout
                data = await asyncio.wait_for(activity_queue.get(), timeout=BATCH_INTERVAL)
                batch.append(data)
                activity_queue.task_done()
            except asyncio.TimeoutError:
                pass  # timeout, save whatever is in the batch

            # fetch additional elements until reaching BATCH_SIZE
            while len(batch) < BATCH_SIZE:
                try:
                    data = activity_queue.get_nowait()
                    batch.append(data)
                    activity_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if batch:
                async with aiofiles.open("user_activity.json", "a") as f:
                    lines = [json.dumps(entry) + "\n" for entry in batch]
                    await f.writelines(lines)
                batch.clear()
        except Exception as e:
            print(f"[ACTIVITY WORKER] Error saving activity: {e}")
            batch.clear()


def _record_user_activity(user_id, username, interaction_type, name, extra=None):
    data = {
        "user_id": user_id,
        "username": username,
        "type": interaction_type,
        "name": name,
        "extra": extra or {},
        "timestamp": str(datetime.utcnow())
    }
    activity_queue.put_nowait(data)


# Events
@bot.event
async def on_command_completion(ctx):
    cmd_name = getattr(ctx.command, "qualified_name", "unknown")
    _record_user_activity(ctx.author.id, getattr(ctx.author, "name", None), "command", cmd_name)

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    cmd_name = getattr(command, "qualified_name", None) or getattr(command, "name", None) or "app_command"
    _record_user_activity(interaction.user.id, getattr(interaction.user, "name", None), "app_command", cmd_name)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.type in (discord.InteractionType.component, discord.InteractionType.modal_submit):
            name = "component"
            extra = {}
            if interaction.data:
                name = interaction.data.get("custom_id", "component")
                extra["component_type"] = interaction.data.get("component_type")
            _record_user_activity(interaction.user.id, getattr(interaction.user, "name", None), "interaction", name, extra)
    except Exception:
        pass


async def load_cogs():
    loaded_cogs = []
    failed_cogs = []
    skipped_cogs = []
    
    print("\n" + "="*50)
    print("🔧 LOADING COGS...")
    print("="*50)
    
    for entry in os.listdir("./cogs"):
        path = os.path.join("./cogs", entry)

        # If it's a Python file, load as before
        if entry.endswith(".py"):
            cog_name = entry[:-3]
        # If it's a directory and a package (contains __init__.py), treat as an extension package
        elif os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
            cog_name = entry
        else:
            # skip non-py files and plain folders
            continue

        # Skip specific legacy or disabled cogs
        if cog_name == "music_new":
            skipped_cogs.append(f"{cog_name} (using music.py instead)")
            continue
        if cog_name == "uno_gofish":
            skipped_cogs.append(f"{cog_name} (legacy - using cardgames.py)")
            continue
        if cog_name == "leveling":
            skipped_cogs.append(f"{cog_name} (disabled - causes issues)")
            continue
        if cog_name == "music" and not config.get("music_enabled", True):
            skipped_cogs.append(f"{cog_name} (disabled in config.json)")
            continue
        if cog_name == "tcg":
            skipped_cogs.append(f"{cog_name} (legacy - conflicts)")
            continue

        try:
            await bot.load_extension(f"cogs.{cog_name}")
            loaded_cogs.append(cog_name)
            print(f"  ✅ {cog_name}")
        except Exception as e:
            failed_cogs.append((cog_name, str(e)))
            print(f"  ❌ {cog_name}: {e}")
            traceback.print_exc()
            try:
                ludus_logging.log_exception(e, message=f"Failed to load cog {cog_name}")
            except Exception:
                pass
    
    # Print summary
    print("\n" + "="*50)
    print("📊 COG LOADING SUMMARY")
    print("="*50)
    print(f"✅ Loaded: {len(loaded_cogs)} cogs")
    for cog in sorted(loaded_cogs):
        print(f"   • {cog}")
    
    if skipped_cogs:
        print(f"\n⏭️  Skipped: {len(skipped_cogs)} cogs")
        for skip_info in sorted(skipped_cogs):
            print(f"   • {skip_info}")
    
    if failed_cogs:
        print(f"\n❌ Failed: {len(failed_cogs)} cogs")
        for cog_name, error in sorted(failed_cogs):
            print(f"   • {cog_name}: {error[:80]}")
    
    print("="*50 + "\n")

@bot.event
async def on_connect():
    """Called when bot successfully connects to Discord"""
    print("✅ Connected to Discord!")
    logger.info("Bot connected to Discord")

@bot.event
async def on_disconnect():
    """Called when bot disconnects from Discord"""
    print("⚠️ Disconnected from Discord - will attempt reconnect")
    logger.warning("Bot disconnected from Discord")

@bot.event
async def on_resume():
    """Called when bot successfully resumes session after disconnect"""
    print("✅ Successfully resumed Discord session")
    logger.info("Bot resumed Discord session")

@bot.event
async def on_ready():
    print("\n" + "="*50)
    print("🚀 BOT IS READY!")
    print("="*50)
    print(f"👤 Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print(f"🔑 Bot owner_ids: {bot.owner_ids}")
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
    print(f"\n🔧 Active Cogs ({len(bot.cogs)}):")
    for cog_name in sorted(bot.cogs.keys()):
        cog = bot.cogs[cog_name]
        # Count commands in this cog
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
        print(f"\n📝 Text Commands ({len(text_commands)}):")
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
            # Check if command has guild_ids (guild-specific)
            if hasattr(cmd, 'guild_ids') and cmd.guild_ids:
                guild_cmds.append(cmd)
            else:
                global_cmds.append(cmd)
        
        print(f"\n⚡ Slash Commands ({len(all_app_commands)} total):")
        print(f"   🌍 Global: {len(global_cmds)}")
        print(f"   🏠 Guild-specific: {len(guild_cmds)}")
        
        # Show global commands
        if global_cmds:
            print(f"\n🌍 Global Commands ({len(global_cmds)}):")
            
            # Group by parent
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
            
            # Display root commands with their subcommands
            for cmd_name in sorted(root_commands.keys()):
                cmd = root_commands[cmd_name]
                cog_name = cmd.binding.__cog_name__ if hasattr(cmd, 'binding') and cmd.binding else "Unknown"
                
                # Check if it has subcommands
                if cmd.qualified_name in subcommands:
                    print(f"   • /{cmd.name} [GROUP] ({cog_name})")
                    for subcmd in sorted(subcommands[cmd.qualified_name], key=lambda x: x.name):
                        print(f"      ├─ /{cmd.name} {subcmd.name}")
                else:
                    print(f"   • /{cmd.name} ({cog_name})")
            
            # Show orphaned subcommands (shouldn't happen but just in case)
            for parent_name, subs in subcommands.items():
                if parent_name not in root_commands:
                    print(f"   • /{parent_name} [MISSING PARENT]")
                    for subcmd in subs:
                        print(f"      ├─ {subcmd.name}")
        
        # Show guild-specific commands
        if guild_cmds:
            print(f"\n🏠 Guild-Specific Commands ({len(guild_cmds)}):")
            for cmd in sorted(guild_cmds, key=lambda x: x.qualified_name):
                guild_ids_str = f" [Guilds: {', '.join(str(g) for g in (cmd.guild_ids or [])[:3])}]"
                cog_name = cmd.binding.__cog_name__ if hasattr(cmd, 'binding') and cmd.binding else "Unknown"
                print(f"   • /{cmd.qualified_name} ({cog_name}){guild_ids_str}")
    
    print("="*50)
    
    # ===== DEV GUILD COMMAND SYNC SYSTEM =====
    print("\n" + "="*50)
    print("🔄 SYNCING SLASH COMMANDS...")
    print("="*50)
    
    # Commands in DEV_ONLY_COMMANDS list sync ONLY to dev guild (fast testing)
    # All other commands sync globally
    DEV_ONLY_COMMANDS = ['dnd']  # Add command names here for dev guild testing
    
    try:
        import os
        dev_guilds_raw = os.environ.get('DEV_GUILD_IDS') or os.environ.get('DEV_GUILD_ID')
        if dev_guilds_raw:
            print(f"🔧 DEV_GUILD_ID detected - splitting commands")
            dev_guild_ids = [int(g.strip()) for g in dev_guilds_raw.split(',') if g.strip()]
            dev_guild_objs = [discord.Object(id=gid) for gid in dev_guild_ids]

            # Create a temporary tree for global commands
            global_tree = discord.app_commands.CommandTree(bot)
            
            # Add only global commands to the temporary tree
            for cmd in bot.tree.walk_commands():
                root_name = cmd.root_parent.name if cmd.root_parent else cmd.name
                if root_name not in DEV_ONLY_COMMANDS:
                    global_tree.add_command(cmd)

            # Sync the temporary global tree
            try:
                print(f"\n🌍 Syncing global commands...")
                synced_global = await global_tree.sync()
                print(f"   • Synced {len(synced_global)} global commands.")
            except Exception as e:
                print(f"   ❌ Error syncing global commands: {e}")
                traceback.print_exc()

            # Sync dev-only commands to each dev guild
            for guild in dev_guild_objs:
                try:
                    dev_tree = discord.app_commands.CommandTree(bot)
                    for cmd_name in DEV_ONLY_COMMANDS:
                        cmd = bot.tree.get_command(cmd_name)
                        if cmd:
                            dev_tree.add_command(cmd)

                    print(f"\n🏠 Syncing dev commands to guild {guild.id}...")
                    synced_dev = await dev_tree.sync(guild=guild)
                    print(f"   • Synced {len(synced_dev)} dev commands to {guild.id}.")
                except Exception as e:
                    print(f"   ❌ Error syncing dev commands to guild {guild.id}: {e}")
                    traceback.print_exc()
        else:
            # No dev guild, sync all commands globally
            print(f"🌍 Syncing all commands globally...")
            synced_commands = await bot.tree.sync()
            print(f"   • Synced {len(synced_commands)} commands.")

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
        # discord.Game no longer has a 'type' parameter.
        game = discord.Game(name="L!help")
        await bot.change_presence(activity=game)
        print("✅ Presence updated to 'Playing L!help'")
    except Exception as e:
        print(f"❌ Failed to set presence: {e}")
        traceback.print_exc()

    # Start auto-saving tasks
    try:
        from cogs.economy import auto_save_economy
        auto_save_economy.start(bot)
        print("✅ Economy auto-saving task started.")
    except Exception as e:
        print(f"❌ Failed to start economy auto-saving: {e}")
        traceback.print_exc()

    try:
        from cogs.reminders import check_reminders
        check_reminders.start(bot)
        print("✅ Reminders checking task started.")
    except Exception as e:
        print(f"❌ Failed to start reminder checking: {e}")
        traceback.print_exc()

    try:
        from cogs.dueling import update_duels
        update_duels.start(bot)
        print("✅ Dueling update task started.")
    except Exception as e:
        print(f"❌ Failed to start dueling updates: {e}")
        traceback.print_exc()

    try:
        from cogs.daily_rewards import reset_daily_claims
        reset_daily_claims.start(bot)
        print("✅ Daily reward reset task started.")
    except Exception as e:
        print(f"❌ Failed to start daily reward reset: {e}")
        traceback.print_exc()
        
    print("="*50)
    print("✅ All startup tasks complete. Bot is fully operational.")
    print("="*50)


@bot.event
async def on_message(message):
    # Don't respond to ourselves
    if message.author == bot.user:
        return

    # Check if the message is a direct mention or starts with "Hey Ludus"
    if bot.user.mentioned_in(message) or message.content.lower().startswith('hey ludus'):
        # You can add more sophisticated logic here to parse the question
        # For now, let's just send a simple reply.
        await message.channel.send(f"Hello {message.author.mention}! How can I help you today?")

    # This allows other on_message events and commands to continue processing
    await bot.process_commands(message)


# Main entry point
TOKEN = os.environ.get("LUDUS_TOKEN")
if not TOKEN:
    print("[FATAL] LUDUS_TOKEN environment variable not set. Cannot start bot.")
    sys.exit(1)

print("[MAIN] Starting Ludus Bot...")
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"[FATAL] An error occurred while running the bot: {e}")
    traceback.print_exc()