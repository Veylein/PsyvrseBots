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

# Initialize game state storage for UNO and other games
bot.active_games = {}
bot.active_lobbies = {}
bot.active_minigames = {}
bot.pending_rematches = {}


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
    
    # Now load all cogs
    await load_cogs()


async def load_cogs():
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

@bot.event
async def on_ready():
    print(f"[BOT] {bot.user} is online!")
    print(f"[BOT] Bot owner_ids: {bot.owner_ids}")
    print(f"[BOT] Bot application info owner: {(await bot.application_info()).owner.id if bot.application else 'Unknown'}")
    
    # ===== DEV GUILD COMMAND SYNC SYSTEM =====
    # Commands in DEV_ONLY_COMMANDS list sync ONLY to dev guild (fast testing)
    # All other commands sync globally
    DEV_ONLY_COMMANDS = []  # Add command names here for dev guild testing
    
    # Log all commands available before sync
    print(f"[BOT] Total app commands in tree: {len(bot.tree.get_commands())}")
    
    try:
        import os
        dev_guilds_raw = os.environ.get('DEV_GUILD_IDS') or os.environ.get('DEV_GUILD_ID')
        if dev_guilds_raw:
            print(f"[BOT] DEV_GUILD_ID detected - splitting commands")
            guild_ids = [g.strip() for g in dev_guilds_raw.split(',') if g.strip()]
            
            # Save references to dev-only commands before removing
            dev_commands = {}
            for cmd_name in DEV_ONLY_COMMANDS:
                cmd = bot.tree.get_command(cmd_name)
                if cmd:
                    dev_commands[cmd_name] = cmd
                    bot.tree.remove_command(cmd_name)
                    print(f"[BOT] Saved {cmd_name} for dev guild only")
            
            # Sync global commands (without dev-only)
            print(f"[BOT] Syncing global commands...")
            synced_global = await bot.tree.sync()
            print(f"[BOT] ✅ Synced {len(synced_global)} commands globally")
            for cmd in synced_global:
                print(f"  - /{cmd.name} (global)")
            
            # Sync dev-only commands to guild
            for dev_gid in guild_ids:
                try:
                    guild_obj = discord.Object(id=int(dev_gid))
                    bot.tree.clear_commands(guild=guild_obj)
                    
                    # Add saved dev commands to guild tree
                    for cmd_name, cmd in dev_commands.items():
                        bot.tree.add_command(cmd, guild=guild_obj)
                        print(f"[BOT] Added {cmd_name} to guild {dev_gid}")
                    
                    synced_guild = await bot.tree.sync(guild=guild_obj)
                    print(f"[BOT] ✅ Synced {len(synced_guild)} dev commands to guild {dev_gid}")
                    for cmd in synced_guild:
                        print(f"  - /{cmd.name} (guild {dev_gid})")
                except Exception as e:
                    print(f"[BOT] ❌ Failed to sync to guild {dev_gid}: {e}")
                    traceback.print_exc()
        else:
            synced = await bot.tree.sync()
            print(f"[BOT] ✅ Synced {len(synced)} commands globally")
            for cmd in synced:
                print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"[BOT] Error syncing commands: {e}")
        traceback.print_exc()

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
        
        # Add other game handlers here as needed
        
    except Exception as e:
        print(f"[BOT] Error handling interaction: {e}")
        import traceback
        traceback.print_exc()
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing your interaction.", ephemeral=True)
        except:
            pass

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
        print("ERROR: Invalid Discord token!")

# --- FIXED: Removed duplicate config reload (it served no purpose) ---

if __name__ == "__main__":
    asyncio.run(main())
