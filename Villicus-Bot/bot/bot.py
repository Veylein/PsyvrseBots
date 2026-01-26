# bot/bot.py
import discord
from discord.ext import commands
import discord
import asyncio
from core.config import get_prefix
try:
    from villicus.core import constants
except Exception:
    try:
        from core import constants
    except Exception:
        import importlib
        try:
            constants = importlib.import_module('core.constants')
        except Exception:
            class _DummyConstants:
                VILLICUS_EMOJI = '<:villicus:1171111111111111111>'
                LETTER_EMOJI = {}
                TICKET_EMOJI = '<:VTicket:1449884927003725834>'
                ERROR_EMOJI = '<:Error:1451834990102052864>'
                CHECK_EMOJI = '<:Check:1451835053972918316>'
            constants = _DummyConstants()


# Set all recommended intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True

# Channel ID for logging
LOG_CHANNEL_ID = 1442605619835179127

async def get_dynamic_prefix(bot, message):
    return await get_prefix(message.guild)

class VillicusBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ...existing code...

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        embed = discord.Embed(
            title="❌ Oops! Something went wrong...",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        if isinstance(error, commands.MissingRequiredArgument):
            embed.description = (
                f"{constants.VILLICUS_EMOJI} **Missing Required Input!**\n\n"
                f"**You must provide:** `{error.param.name}`\n\n"
                "*Tip: Use `/help <command>` or `/config` for guidance. All required fields are shown in the command preview above your message box.*"
            )
        elif isinstance(error, commands.BadArgument):
            embed.description = (
                f"{constants.VILLICUS_EMOJI} **Invalid input:** {error}\n\n"
                "Please check your command and try again."
            )
        elif isinstance(error, commands.MissingPermissions):
            embed.description = (
                f"{constants.VILLICUS_EMOJI} **You don't have permission to use this command.**\n"
                "If you believe this is a mistake, contact a server admin."
            )
        elif isinstance(error, commands.BotMissingPermissions):
            embed.description = (
                f"{constants.VILLICUS_EMOJI} **I need more permissions to do that!**\n"
                "Please check my role and permissions."
            )
        else:
            embed.description = (
                f"{constants.VILLICUS_EMOJI} **An unexpected error occurred.**\n"
                "If this keeps happening, contact the server owner or support."
            )
        embed.set_footer(text="Villicus | The Ultimate VIP Bot Experience ✨")
        try:
            await ctx.send(embed=embed, ephemeral=True)
        except Exception:
            pass




async def start_bot():
    print("[Villicus] Creating bot instance...")
    bot = commands.Bot(command_prefix=get_dynamic_prefix, intents=intents, help_command=None)

    try:
        print("[Villicus] Importing cogs dynamically...")
        import importlib, inspect

        cog_names = [
            'config_cog', 'moderation_cog', 'help_cog', 'mod_commands_cog', 'ticket_cog', 'leveling_cog',
            'actionlog_cog', 'antinuke_cog', 'autoresponder_cog', 'autorole_cog', 'avatar_cog', 'calculator_cog',
            'clean_cog', 'color_cog', 'deafen_cog', 'embed_cog', 'emoji_cog', 'forms_cog', 'giveaway_cog', 'info_cog',
            'lock_cog', 'nick_cog', 'owner_cog', 'purge_cog', 'reminder_cog', 'roleinfo_cog', 'servertag_cog',
            'slowmode_cog', 'translate_cog', 'userinfo_cog', 'warnings_cog', 'welcome_cog', 'automessage_cog',
            'automod_cog', 'invite_tracker_cog', 'polls_cog', 'reactionroles_cog', 'perfectlog_cog', 'appeals_cog',
            'welcomemedia_cog', 'serverbackup_cog', 'rule_cog', 'smartautomod_cog', 'rule_analytics_cog'
        ]

        modules = []
        for name in cog_names:
            try:
                mod = importlib.import_module(f'bot.{name}')
                modules.append(mod)
            except ModuleNotFoundError:
                print(f"[Villicus] Cog module not found: {name} (skipping)")

        # Prefer module-level async setup(bot) if present; otherwise find the first Cog subclass
        for mod in modules:
            try:
                if hasattr(mod, 'setup'):
                    setup_fn = getattr(mod, 'setup')
                    if inspect.iscoroutinefunction(setup_fn):
                        await setup_fn(bot)
                        continue
                # find Cog subclass
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    try:
                        if issubclass(obj, commands.Cog) and obj is not commands.Cog:
                            await bot.add_cog(obj(bot))
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[Villicus] Failed to load cog from module {mod.__name__}: {e}")
                import traceback
                traceback.print_exc()
        print("[Villicus] Cog import complete")
    except Exception as e:
        import traceback
        print(f"[Villicus] Cog import/add error: {e}")
        traceback.print_exc()
        raise

    async def log_message(bot, content):
        await bot.wait_until_ready()
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(content)

    @bot.event
    async def on_ready():
        print(f"Villicus is online as {bot.user}")
        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            await log_message(bot, f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            await log_message(bot, f"❌ Slash command sync failed: {e}")


    @bot.event
    async def on_command_error(ctx, error):
        import discord.ext.commands as dpycmds
        if isinstance(error, dpycmds.errors.CommandNotFound):
            # Silently ignore unknown commands
            return
        await log_message(bot, f"❌ Command error in `{getattr(ctx, 'command', None)}` by {ctx.author} in #{ctx.channel}: {error}")
        # Do not raise error to avoid duplicate error output

    @bot.event
    async def on_command_completion(ctx):
        await log_message(bot, f"✅ Command `{ctx.command}` used by {ctx.author} in #{ctx.channel}")

    @bot.event
    async def on_guild_join(guild):
        await log_message(bot, f"➕ Joined new guild: {guild.name} (ID: {guild.id}) | Members: {guild.member_count}")

    @bot.event
    async def on_guild_remove(guild):
        await log_message(bot, f"➖ Removed from guild: {guild.name} (ID: {guild.id})")

    import os
    token = os.environ.get('VILLICUS_TOKEN')
    if not token:
        raise RuntimeError('VILLICUS_TOKEN environment variable not set!')
    await bot.start(token)
