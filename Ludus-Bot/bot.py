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
        os.system(f"{sys.executable} bot.py")

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
    description="🎮 The ultimate Discord minigame & music bot! Use `L!about` and `L!help` to get started. Made with ❤️ by Psyvrse Development."
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
            loop.run_in_executor(None, user_storage.record_activity, int(user_id), username, activity_type, name, extra)
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


@bot.event
async def on_command_completion(ctx):
    try:
        cmd_name = ctx.command.qualified_name if ctx.command else "unknown"
    except Exception:
        cmd_name = "unknown"
    _record_user_activity(ctx.author.id, getattr(ctx.author, "name", None), "command", cmd_name)


@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command):
    try:
        cmd_name = getattr(command, "qualified_name", None) or getattr(command, "name", None) or "app_command"
    except Exception:
        cmd_name = "app_command"
    _record_user_activity(interaction.user.id, getattr(interaction.user, "name", None), "app_command", cmd_name)


@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        # Only record component/modal interactions to avoid duplicating app_command tracking
        itype = interaction.type
        if itype in (discord.InteractionType.component, discord.InteractionType.modal_submit):
            name = "component"
            extra = {}
            try:
                if interaction.data:
                    name = interaction.data.get("custom_id", "component")
                    extra["component_type"] = interaction.data.get("component_type")
            except Exception:
                pass
            _record_user_activity(interaction.user.id, getattr(interaction.user, "name", None), "interaction", name, extra or None)
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
    DEV_ONLY_COMMANDS = ['help']  # Add command names here for dev guild testing
    
    try:
        import os
        dev_guilds_raw = os.environ.get('DEV_GUILD_IDS') or os.environ.get('DEV_GUILD_ID')
        if dev_guilds_raw:
            print(f"🔧 DEV_GUILD_ID detected - splitting commands")
            guild_ids = [g.strip() for g in dev_guilds_raw.split(',') if g.strip()]
            
            # Save references to dev-only commands before removing
            dev_commands = {}
            for cmd_name in DEV_ONLY_COMMANDS:
                cmd = bot.tree.get_command(cmd_name)
                if cmd:
                    dev_commands[cmd_name] = cmd
                    bot.tree.remove_command(cmd_name)
                    print(f"  📌 Saved {cmd_name} for dev guild only")
            
            # Sync global commands (without dev-only)
            print(f"\n🌍 Syncing global commands...")
            synced_global = await bot.tree.sync()
            print(f"✅ Synced {len(synced_global)} commands globally")
            if len(synced_global) <= 20:
                for cmd in synced_global:
                    print(f"   • /{cmd.name}")
            else:
                print(f"   (Too many to list - {len(synced_global)} total)")
            
            # Sync dev-only commands to guild
            for dev_gid in guild_ids:
                try:
                    guild_obj = discord.Object(id=int(dev_gid))
                    bot.tree.clear_commands(guild=guild_obj)
                    
                    # Add saved dev commands to guild tree
                    for cmd_name, cmd in dev_commands.items():
                        bot.tree.add_command(cmd, guild=guild_obj)
                        print(f"  📌 Added {cmd_name} to guild {dev_gid}")
                    
                    synced_guild = await bot.tree.sync(guild=guild_obj)
                    print(f"✅ Synced {len(synced_guild)} dev commands to guild {dev_gid}")
                    if len(synced_guild) <= 20:
                        for cmd in synced_guild:
                            print(f"   • /{cmd.name}")
                except Exception as e:
                    print(f"❌ Failed to sync to guild {dev_gid}: {e}")
                    traceback.print_exc()
        else:
            print(f"\n🌍 Syncing all commands globally...")
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} commands globally")
            
            if len(synced) <= 30:
                # Show all commands with groups
                for cmd in sorted(synced, key=lambda x: x.name):
                    if hasattr(cmd, 'options') and cmd.options:
                        # Check if it's a group (has subcommands)
                        has_subcommands = any(opt.type == 1 for opt in cmd.options if hasattr(opt, 'type'))
                        if has_subcommands:
                            print(f"   • /{cmd.name} [GROUP with subcommands]")
                        else:
                            print(f"   • /{cmd.name}")
                    else:
                        print(f"   • /{cmd.name}")
            elif len(synced) <= 100:
                # Just show names
                cmd_names = sorted([cmd.name for cmd in synced])
                for i in range(0, len(cmd_names), 5):
                    batch = cmd_names[i:i+5]
                    print(f"   • {', '.join(batch)}")
            else:
                print(f"   (Too many to list - {len(synced)} total)")
                # Show first 20
                for cmd in sorted(synced, key=lambda x: x.name)[:20]:
                    print(f"   • /{cmd.name}")
                print(f"   ... and {len(synced) - 20} more")
        
        print("="*50 + "\n")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
        traceback.print_exc()
        try:
            ludus_logging.log_exception(e, message="Error syncing commands")
        except Exception:
            pass

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

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for prefix commands"""
    if isinstance(error, commands.CheckFailure):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command.")
        else:
            await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        # Silently ignore - don't spam for unknown commands
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`\n💡 Use `L!help {ctx.command.name}` for usage info.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"❌ I'm missing permissions: {', '.join(error.missing_permissions)}")
    else:
        # Log error but show clean message to users
        try:
            ludus_logging.log_exception(error, ctx=ctx, message=f"Command error in {ctx.command}")
        except Exception:
            pass
        print(f"[BOT] Command error in {ctx.command}: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send("❌ An error occurred. Please try again or contact a server administrator.")

@bot.event
async def on_command(ctx):
    """Track first-time command usage and send welcome DM"""
    if ctx.author.bot:
        return
    
    # Check if command is disabled in this server
    if ctx.guild:
        server_config = load_server_config(ctx.guild.id)
        if ctx.command.name in server_config["disabled_commands"]:
            await ctx.send("❌ This command has been disabled by server administrators.")
            raise commands.CheckFailure("Command disabled by server config")
    
    # Load first-time users tracking
    tracking_file = "data/first_time_users.json"
    os.makedirs("data", exist_ok=True)
    
    try:
        with open(tracking_file, 'r') as f:
            first_time_users = json.load(f)
    except FileNotFoundError:
        first_time_users = []
    
    # If user hasn't been welcomed yet AND server allows welcome DMs
    user_id = ctx.author.id
    if user_id not in first_time_users:
        # Check server config for welcome_dm setting
        welcome_enabled = True
        if ctx.guild:
            server_config = load_server_config(ctx.guild.id)
            welcome_enabled = server_config.get("welcome_dm", True)
        
        if welcome_enabled:
            first_time_users.append(user_id)
            
            # Save updated tracking
            with open(tracking_file, 'w') as f:
                json.dump(first_time_users, f)
            
            # Send welcome DM
            try:
                embed = discord.Embed(
                    title=f"🎮 Welcome to Ludus!",
                    description=f"Hey {ctx.author.mention}! Thanks for using Ludus!\n\n"
                           "**The Ultimate Discord Bot Experience**\n\n"
                           f"💰 **Economy** - Earn, spend, and trade coins\n"
                           f"🎲 **100+ Minigames** - Quick games for fun\n"
                           f"🏪 **Business System** - Create your shop\n"
                           f"🌾 **Farming** - Grow and sell crops\n"
                           f"👑 **Guilds** - Build communities\n"
                           f"🏆 **200+ Achievements** - Unlock goals\n"
                           f"❤️ **Social Features** - Pets, friends, events\n"
                           f"📊 **Progression** - Track everything!\n\n"
                           "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                           "**🚀 Quick Start:**\n"
                           f"• `L!daily` - Claim daily rewards\n"
                           f"• `L!balance` - Check your coins\n"
                           f"• `L!profile` - View your stats\n"
                           f"• `L!tutorial` - Full interactive guide\n"
                           f"• `L!help` - All commands\n\n"
                           "💡 **Pro Tip:** Every action earns coins and XP!",
                        color=0x00ff00
                )
                embed.set_footer(text="Use L!tutorial anytime for detailed guides")
                
                await ctx.author.send(embed=embed)
                print(f"[BOT] Sent welcome DM to {ctx.author} ({user_id})")
            except discord.Forbidden:
                print(f"[BOT] Couldn't send DM to {ctx.author} ({user_id}) - DMs disabled")
            except Exception as e:
                print(f"[BOT] Error sending welcome DM to {user_id}: {e}")

@bot.event
async def on_message(message):
    """Process messages and check blacklist for prefix commands"""
    if message.author.bot:
        return
    
    # Check for active chess games and process moves
    chess_cog = bot.get_cog('ChessCog')
    if chess_cog:
        # Check if there's an active chess game in this channel
        for game_id, game in list(bot.active_games.items()):
            if game_id.startswith('chess_') and game.get('messageId'):
                # Check if message is in the same channel as the game
                try:
                    game_message = await message.channel.fetch_message(game['messageId'])
                    if game_message.channel.id == message.channel.id:
                        # Check if the message author is a player in this game
                        if str(message.author.id) in game['players']:
                            # Try to process as a chess move
                            await chess_cog.process_chess_move(message, game_id, game)
                            return  # Don't process as command if it's a valid move attempt
                except:
                    pass
    
    # Check blacklist before processing commands
    if message.content.startswith(config["prefix"]):
        if is_blacklisted(user_id=message.author.id, guild_id=message.guild.id if message.guild else None):
            await message.channel.send("🚫 You or this server has been blacklisted from using this bot.")
            return
    
    await bot.process_commands(message)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button/select interactions for games"""
    # Only handle component interactions (buttons/selects), not slash commands
    if interaction.type != discord.InteractionType.component:
        # Let discord.py handle slash commands automatically
        return
    
    try:
        custom_id = interaction.data.get('custom_id', '')
        
        # UNO interactions
        if custom_id.startswith('uno_'):
            uno_cog = bot.get_cog('UnoCog')
            if uno_cog:
                await uno_cog.handle_uno_interaction(interaction, custom_id)
                return
        
        # TTT (Tic-Tac-Toe) interactions
        if custom_id.startswith('ttt_'):
            boardgames_cog = bot.get_cog('BoardGames')
            if boardgames_cog:
                await boardgames_cog.handle_ttt_interaction(interaction, custom_id)
                return
        
        # Chess interactions
        if custom_id.startswith('chess_'):
            chess_cog = bot.get_cog('ChessCog')
            if chess_cog:
                await chess_cog.handle_chess_interaction(interaction, custom_id)
                return
        
        # Checkers interactions
        if custom_id.startswith('checkers_'):
            chess_cog = bot.get_cog('ChessCog')
            if chess_cog:
                await chess_cog.handle_checkers_interaction(interaction, custom_id)
                return
        
        # Add other game handlers here as needed
        
    except Exception as e:
        logger.exception("Error handling interaction: %s", e)
        try:
            ludus_logging.log_exception(e, interaction=interaction, message="Error handling interaction")
        except Exception:
            pass
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing your interaction.", ephemeral=True)
        except:
            pass


@bot.event
async def on_error(event_method, *args, **kwargs):
    """Global fallback for uncaught errors in events."""
    try:
        logger.exception("Unhandled error in event %s", event_method)
        try:
            ludus_logging.log_message(level="ERROR", title="Unhandled event error", message=f"Event: {event_method}")
        except Exception:
            pass
    except Exception:
        print("Unhandled error in event", event_method)

# Blacklist checking
def is_blacklisted(user_id=None, guild_id=None):
    """Check if user or guild is blacklisted"""
    blacklist = load_blacklist()
    if user_id and str(user_id) in blacklist.get("users", []):
        return True
    if guild_id and str(guild_id) in blacklist.get("guilds", []):
        return True
    return False

async def main():
    # Cogs are now loaded in setup_hook (runs automatically before bot.start)
    token = os.getenv("LUDUS_TOKEN")
    if not token:
        print("Error: No Discord token found! Please set LUDUS_TOKEN in Secrets or add 'token' to config.json.")
        return
    try:
        await bot.start(token)
    except discord.errors.LoginFailure:
        logger.error("Invalid Discord token provided")
    except Exception as e:
        logger.exception("Bot stopped with exception: %s", e)

# --- FIXED: Removed duplicate config reload (it served no purpose) ---

if __name__ == "__main__":
    asyncio.run(main())
