import discord
import re
from discord.ext import commands
from discord import app_commands
from typing import Optional

class Help(commands.Cog):
    """Modern categorized help system with embeds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.categories = {
            "💰 Economy": {
                "key": "economy",
                "desc": "Currency system and trading",
                "commands": [
                    ("balance", "Check your PsyCoin balance"),
                    ("daily", "Claim daily reward (100-500 coins + streaks)"),
                    ("shop", "Browse items for purchase"),
                    ("buy <item>", "Purchase an item"),
                    ("inventory", "View your items"),
                    ("use <item>", "Use/activate an item"),
                    ("give @user <amount>", "Send coins to someone"),
                    ("leaderboard", "Top earners"),
                    ("trade @user", "Trade items with players"),
                ]
            },
            "🎰 Gambling": {
                "key": "gambling",
                "desc": "Test your luck at the casino",
                "commands": [
                    ("slots <bet>", "Spin the slot machine (10-10,000)"),
                    ("blackjack <bet>", "Play blackjack (10-10,000)"),
                    ("poker <bet>", "5-card poker vs dealer (10-10,000)"),
                    ("crash <bet>", "Crash multiplier game (10-10,000)"),
                    ("mines <bet> <mines>", "Minesweeper gambling (1-24 mines)"),
                    ("dice <bet> <number>", "Roll dice and bet on number"),
                    ("roulette <bet> <choice>", "Classic roulette"),
                ]
            },
            "🎲 Board Games": {
                "key": "board",
                "desc": "Classic games with AI and PvP",
                "commands": [
                    ("ttt [@user]", "Tic-Tac-Toe (50 coins)"),
                    ("connect4 [@user]", "Connect 4 (75 coins)"),
                    ("hangman", "Hangman word game (100 coins)"),
                    ("chess @user", "Chess match"),
                    ("checkers @user", "Checkers match"),
                    ("/monopoly start", "Full Monopoly! 28 properties, houses, hotels, chance cards, jail, trading (2-6 players)"),
                ]
            },
            "🃏 Card Games": {
                "key": "cards",
                "desc": "Multiplayer card battles",
                "commands": [
                    ("/uno", "Start UNO game (2-10 players)"),
                    ("/gofish", "Go-Fish (2-5 players)"),
                    ("war [@user]", "Quick War card game"),
                ]
            },
            "🎮 Minigames": {
                "key": "mini",
                "desc": "Quick games and challenges",
                "commands": [
                    ("wordle", "5-letter word puzzle (50-200 coins)"),
                    ("riddle", "Brain-teasing riddles"),
                    ("typerace", "Speed typing (WPM rewards)"),
                    ("gtn", "Guess the Number (50-150 coins)"),
                    ("/trivia", "Trivia questions (50-150 coins)"),
                    ("/memory", "Memory pattern game"),
                    ("tod <choice>", "Truth or Dare"),
                    ("rps <choice>", "Rock Paper Scissors"),
                    ("coinflip", "Flip a coin"),
                    ("roll [sides]", "Roll dice (d6-d25)"),
                    ("8ball <question>", "Magic 8-ball"),
                    ("tarot", "Tarot card reading"),
                ]
            },
            "🧩 Puzzle Games": {
                "key": "puzzle",
                "desc": "Brain teasers and mysteries",
                "commands": [
                    ("/game minesweeper <difficulty>", "Classic minesweeper"),
                    ("/game memory", "Remember emoji pattern"),
                    ("/game codebreaker <difficulty>", "Crack secret codes"),
                    ("/game clue", "Solve murder mysteries"),
                ]
            },
            "👾 Arcade": {
                "key": "arcade",
                "desc": "Fast-paced action games",
                "commands": [
                    ("/arcade pacman", "Eat pellets, dodge ghosts"),
                    ("/arcade mathgame <difficulty>", "Speed math challenges"),
                    ("/arcade bombdefuse", "Cut the right wire!"),
                ]
            },
            "🎣 Fishing+": {
                "key": "fishing",
                "desc": "Enhanced fishing empire",
                "commands": [
                    ("/fish", "Cast your line (30s cooldown)"),
                    ("/fishingzones", "View all fishing zones"),
                    ("/fishzone <zone>", "Fish in specific zone"),
                    ("/aquarium [@user]", "View fish collection"),
                    ("/sellfish", "Sell all catches"),
                    ("/fishingrod", "View/upgrade equipment"),
                    ("/buyrod <name>", "Purchase rod upgrade"),
                    ("/fishingtournament <mins>", "Start server tournament"),
                ]
            },
            "🚜 Farm & Sims": {
                "key": "sims",
                "desc": "Farming and simulations",
                "commands": [
                    ("/farm view", "Check your farm"),
                    ("/farm plant <crop>", "Plant crops"),
                    ("/farm harvest", "Harvest ready crops"),
                    ("/farm sell", "Sell your harvest"),
                    ("/icecream", "Build custom sundae"),
                    ("/akinator start", "Mind-reading game"),
                ]
            },
            "🎪 Fun++": {
                "key": "funplus",
                "desc": "Extra entertainment",
                "commands": [
                    ("/animal", "Random animal images"),
                    ("/fact <category>", "Interesting facts"),
                    ("/meme", "Browse meme templates"),
                    ("/guessthesong", "Music quiz game"),
                    ("/joke", "Random jokes"),
                    ("/eightball <question>", "Magic 8-ball"),
                ]
            },
            "🌍 Global Events": {
                "key": "events",
                "desc": "Server vs Server competitions (Owner starts)",
                "commands": [
                    ("L!event war <hours>", "Server faction war"),
                    ("L!joinfaction <name>", "Join faction"),
                    ("L!warleaderboard", "War standings"),
                    ("L!event worldboss", "Global boss raid"),
                    ("L!attack", "Attack world boss"),
                    ("L!bossstats", "Boss health/stats"),
                    ("L!event hunt <mins>", "Global scavenger hunt"),
                    ("L!event list", "Active events"),
                    ("L!event end <type>", "End event"),
                ]
            },
            "👥 Social": {
                "key": "social",
                "desc": "Interact with community",
                "commands": [
                    ("compliment @user", "Give compliment (+15 coins)"),
                    ("roast @user", "Light roast (+10 coins)"),
                    ("wyr", "Would You Rather (10-25 coins)"),
                    ("wyr_add <A> <B>", "Submit WYR question (+20)"),
                    ("story <starter>", "Start collaborative story"),
                    ("story_view", "Read completed stories"),
                    ("highfive @user", "Celebrate (+5 coins)"),
                    ("reputation @user", "Check reputation"),
                    ("rep @user", "Give daily reputation point"),
                    ("L!slap @user", "Slap someone with GIF"),
                    ("L!punch @user", "Punch someone with GIF"),
                    ("L!kick @user", "Kick someone with GIF"),
                    ("L!kiss @user", "Kiss someone with GIF"),
                    ("L!dance @user", "Dance with someone with GIF"),
                    ("L!stab @user", "Stab someone with GIF"),
                    ("L!shoot @user", "Shoot someone with GIF"),
                ]
            },
            "🐾 Pets": {
                "key": "pets",
                "desc": "Virtual companion system",
                "commands": [
                    ("pet adopt", "Adopt a pet (9 types)"),
                    ("pet status", "Check pet stats"),
                    ("pet feed", "Feed your pet"),
                    ("pet play", "Play with pet"),
                    ("pet walk", "Walk your pet"),
                    ("pet rename <name>", "Rename pet"),
                ]
            },
            "📜 Quests": {
                "key": "quests",
                "desc": "Daily quests and achievements",
                "commands": [
                    ("quests", "View active daily quests"),
                    ("achievements", "View achievements"),
                    ("questclaim <id>", "Claim quest reward"),
                ]
            },
            "📊 Progression": {
                "key": "level",
                "desc": "XP, levels, and rankings",
                "commands": [
                    ("rank [@user]", "Check level and XP"),
                    ("leveltop", "Top 10 by level"),
                    ("profile [@user]", "Complete profile"),
                    ("duel @user <game>", "Competitive duel"),
                    ("tournament <game>", "Join tournament"),
                ]
            },
            "💼 Business": {
                "key": "business",
                "desc": "Passive income system",
                "commands": [
                    ("business buy <type>", "Buy a business"),
                    ("business collect", "Collect profits"),
                    ("business upgrade", "Upgrade business"),
                    ("business list", "View your businesses"),
                ]
            },
            "💎 Premium": {
                "key": "premium",
                "desc": "Cross-server systems",
                "commands": [
                    ("lottery", "View lottery jackpot"),
                    ("lottery buy <amount>", "Buy tickets (1-100)"),
                    ("lottery tickets", "View your tickets"),
                    ("heist create", "Start a heist"),
                    ("heist join", "Join active heist"),
                    ("marry @user", "Propose marriage"),
                    ("divorce", "End marriage"),
                ]
            },
            "🎨 Fun": {
                "key": "fun",
                "desc": "Random entertainment",
                "commands": [
                    ("joke", "Random joke"),
                    ("meme", "Random meme"),
                    ("quote", "Inspirational quote"),
                    ("dog", "Dog pictures"),
                    ("cat", "Cat pictures"),
                    ("panda", "Panda images"),
                    ("gif <search>", "Search GIFs"),
                    ("poll <question>", "Create poll"),
                ]
            },
            "🎵 Music": {
                "key": "music",
                "desc": "Voice channel music player",
                "commands": [
                    ("music play <song>", "Play song/URL"),
                    ("music pause", "Pause playback"),
                    ("music resume", "Resume playback"),
                    ("music skip", "Skip song"),
                    ("music stop", "Stop and disconnect"),
                    ("music queue", "View queue"),
                    ("music radio <genre>", "Start radio (18 genres)"),
                    ("music volume <0-100>", "Adjust volume"),
                ]
            },
            "⚙️ Utility": {
                "key": "utility",
                "desc": "Helpful tools",
                "commands": [
                    ("guide [category]", "This help menu"),
                    ("L!about", "Full bot guide (DM)"),
                    ("setup", "Bot setup guide"),
                    ("ping", "Check bot latency"),
                    ("invite", "Get bot invite link"),
                    ("serverinfo", "Server information"),
                    ("userinfo [@user]", "User information"),
                    ("avatar [@user]", "View avatar"),
                ]
            },
            "⚡ Admin": {
                "key": "admin",
                "desc": "Server configuration (Admin only)",
                "commands": [
                    ("setleveling <channel>", "Enable leveling"),
                    ("/counting [channel]", "Setup counting game"),
                    ("/starboard <emoji> <channel> <amt>", "Setup starboard"),
                    ("ludusconfig", "Configuration menu"),
                    ("purge <amount>", "Delete messages"),
                ]
            },
        }
        
        # Owner category (hidden from regular users)
        self.owner_category = {
            "👑 Owner": {
                "key": "owner",
                "desc": "Bot management (Owner only)",
                "commands": [
                    ("godmode", "Max out stats"),
                    ("/setcoins @user <amt>", "Set balance"),
                    ("/addcoins @user <amt>", "Add coins"),
                    ("giveitem @user <item>", "Give items"),
                    ("raincoins [amt]", "Give to all online"),
                    ("chaos", "Random server-wide reward"),
                    ("spawn", "Spawn raid boss"),
                    ("stats", "Bot statistics"),
                    ("reload <cog>", "Reload cog"),
                    ("announce <msg>", "Announcement"),
                    ("/botstatus <type> <text>", "Set bot status"),
                ]
            }
        }
    
    # Prefix-based help removed — slash-only help is provided below.
    
    @app_commands.command(name="help", description="View bot commands and categories")
    @app_commands.describe(category="Category to view (optional)")
    async def help_slash(self, interaction: discord.Interaction, category: Optional[str] = None):
        """Slash command version of help - /help [category]"""
        is_owner = interaction.user.id in getattr(self.bot, 'owner_ids', [])
        
        if category:
            await self._send_category_help(interaction, category.lower(), is_owner, is_slash=True)
        else:
            await self._send_main_help(interaction, is_owner, is_slash=True)

    @commands.command(name='help')
    async def help_prefix_command(self, ctx: commands.Context, *, category: Optional[str] = None):
        """Prefix command version of help registered on the Help cog.

        Usage: `L!help` or `L!help <category>`
        """
        is_owner = ctx.author.id in getattr(self.bot, 'owner_ids', [])
        if category:
            await self._send_category_help(ctx, category.lower(), is_owner, is_slash=False)
        else:
            await self._send_main_help(ctx, is_owner, is_slash=False)
    
    async def _send_main_help(self, ctx, is_owner, is_slash=False):
        """Send main help menu with all categories"""
        embed = discord.Embed(
            title="🎮 Ludus Bot - Command Categories",
            description="**The Ultimate Discord MMO Experience!**\n\n"
                       "Select a category to view detailed commands:\n"
                       "Usage: `L!help <category>` or `/help <category>`\n\n"
                       "**Quick Start:**\n"
                       "• `L!daily` - Claim daily reward\n"
                       "• `L!balance` - Check coins\n"
                       "• `L!slots 100` - Try your luck!",
            color=discord.Color.gold()
        )
        
        # Add regular categories
        for cat_name, cat_data in self.categories.items():
            embed.add_field(
                name=cat_name,
                value=f"`L!help {cat_data['key']}`\n{cat_data['desc']}",
                inline=True
            )
        
        # Add owner category if user is owner
        if is_owner:
            for cat_name, cat_data in self.owner_category.items():
                embed.add_field(
                    name=cat_name,
                    value=f"`L!help {cat_data['key']}`\n{cat_data['desc']}",
                    inline=True
                )
        
        embed.set_footer(text=f"Ludus v1.30.3 • {len(self.categories) + (1 if is_owner else 0)} Categories • Prefix: L! or /")
        
        if is_slash:
            await ctx.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    async def _send_category_help(self, ctx, category_key, is_owner, is_slash=False):
        """Send help for a specific category"""
        def _normalize(text: str) -> str:
            # remove non-alphanumeric characters (including emoji/punctuation), collapse whitespace
            text = re.sub(r"[^\w\s]", '', text or '')
            return ' '.join(text.split()).strip().lower()
        print(f"[HELP debug] _send_category_help called with category_key='{category_key}'")
        # Find category
        category_data = None
        category_name = None
        
        # Normalize input for robust matching (handles emoji, punctuation, case)
        raw_key = (category_key or '').strip()
        norm_key = _normalize(raw_key)

        # Check regular categories
        for cat_name, cat_data in self.categories.items():
            cat_name_lower = cat_name.lower()
            norm_cat = _normalize(cat_name_lower)
            # direct key match, substring in visible name, or normalized match
            if (
                cat_data.get('key') == raw_key
                or cat_data.get('key') == norm_key
                or raw_key in cat_name_lower
                or norm_key and norm_key in norm_cat
            ):
                category_data = cat_data
                category_name = cat_name
                break
        
        # Check owner category if owner
        if not category_data and is_owner:
            for cat_name, cat_data in self.owner_category.items():
                cat_name_lower = cat_name.lower()
                norm_cat = _normalize(cat_name_lower)
                if (
                    cat_data.get('key') == raw_key
                    or cat_data.get('key') == norm_key
                    or raw_key in cat_name_lower
                    or norm_key and norm_key in norm_cat
                ):
                    category_data = cat_data
                    category_name = cat_name
                    break
        
        if not category_data:
            msg = f"❌ Category `{category_key}` not found!\nUse `L!help` to see all categories."
            if is_slash:
                await ctx.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"{category_name} Commands",
            description=category_data['desc'],
            color=discord.Color.blue()
        )
        
        # Add commands
        for cmd, desc in category_data['commands']:
            # Format command with proper prefix
            if cmd.startswith('/'):
                cmd_display = cmd
            else:
                cmd_display = f"L!{cmd}"
            
            embed.add_field(
                name=cmd_display,
                value=desc,
                inline=False
            )
        
        embed.set_footer(text=f"Use L!help to return to category list • Prefix: L! or /")
        
        if is_slash:
            await ctx.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    # Add cog and ensure the slash command is registered with the app command tree
    cog = Help(bot)
    await bot.add_cog(cog)
    try:
        # `help_slash` is an app command defined on the cog; add it to the tree explicitly
        existing = bot.tree.get_command('help')
        if existing is None:
            bot.tree.add_command(cog.help_slash)
    except Exception:
        # If it fails, the cog may already have registered app commands — ignore
        pass
