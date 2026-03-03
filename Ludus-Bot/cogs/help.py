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
                    ("daily", "Claim daily reward (300–2000+ coins + streaks + pet bonus)"),
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
                    ("/slots <bet>", "Spin the slot machine (10-10,000)"),
                    ("/coinflip <bet>", "Flip a coin (10-10,000)"),
                    ("/higerlower <bet>", "Guess if next card is higher/lower (10-10,000)"),
                    ("dicegamble <bet> <number>", "Roll dice and bet on number (10-10,000)"),
                    ("/blackjack <bet>", "Play blackjack (10-10,000)"),
                    ("/poker <bet>", "5-card poker vs dealer (10-10,000)"),
                    ("/crash <bet>", "Crash multiplier game (10-10,000)"),
                    ("/mines <bet> <mines>", "Minesweeper gambling (1-24 mines)"),
                    ("/dice <bet> <number>", "Roll dice and bet on number"),
                    ("/roulette <bet> <choice>", "Classic roulette"),
                    ("/gambling_stats", "View your gambling statistics"),
                    ("/odds", "View odds for all gambling games"),
                    ("/strategy", "Gambling strategy tips and guides"),
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
                    ("/minigames", "Panel of all minigames"),
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
            "🚜🎣⛏️ Simulators": {
                "key": "sims",
                "desc": "Farming, fishing, mining",
                "commands": [
                    ("/farm view", "Check your farm"),
                    ("/farm plant <crop>", "Plant crops"),
                    ("/farm harvest", "Harvest ready crops"),
                    ("/farm sell", "Sell your harvest"),
                    ("/icecream", "Build custom sundae"),
                    ("fish", "Cast your line and go fishing!"),
                    ("/fish cast", "Cast your line with advanced options"),
                    ("/fish inventory", "View your catches and equipment"),
                    ("/fish shop", "Buy rods, bait, and boats"),
                    ("/fish craft", "Craft special items"),
                    ("/fish areas", "Explore fishing locations"),
                    ("/fish encyclopedia", "View all available fish"),
                    ("/fish stats", "Check your fishing statistics"),
                    ("/mine", "Launch mining game and dig for ores!"),
                ]
            },
            "🧡 Social": {
                "key": "social",
                "desc": "Social interactions & reactions",
                "commands": [
                    ("/ship @user", "Ship two people with GIF & compatibility score"),
                    ("/hug @user", "Hug someone with anime GIF"),
                    ("/kiss @user", "Kiss someone with anime GIF"),
                    ("/slap @user", "Slap someone with anime GIF"),
                    ("/petpet @user", "Petpet someone\u2019s avatar as animated GIF"),
                    ("roast @user", "Roast someone with a savage line"),
                    ("compliment @user", "Compliment someone nicely"),
                    ("pray @user", "Pray for someone (+coins blessing)"),
                    ("curse @user", "Curse someone (may backfire!)"),
                    ("marry @user", "Propose marriage to someone (10000 coins)"),
                    ("spouse [@user]", "View marriage info (spouse, days married, love points, shared bank"),
                    ("L!bank @user", "View your shared bank with your spouse"),
                    ("divorce", "End your marriage (5000 coins)"),
                    ("rep @user", "View reputation (tier, score, +/- breakdown, recent history, effects)"),
                    ("rep give @user [reason]", "Give reputation to someone (1 rep per 24 hours)"),
                    ("L!rep remove @user [reason]", "Give negative reputation to someone (1 rep per 24 hours)"),

                ]
            },
            "🌍 Global Events": {
                "key": "events",
                "desc": "Server vs Server competitions (Owner starts)",
                "commands": [
                    ("event war <hours>", "Server faction war"),
                    ("joinfaction <name>", "Join faction"),
                    ("warleaderboard", "War standings"),
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
                    ("8ball <question>", "Magic 8-ball"),
                    ("tarot", "Tarot card reading"),
                ]
            },
            "⚙️ Utility": {
                "key": "utility",
                "desc": "Helpful tools",
                "commands": [
                    ("guide [category]", "This help menu"),
                    ("about", "Full bot guide (DM)"),
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
                    ("/counting [channel]", "Setup counting game"),
                    ("/starboard <emoji> <channel> <amt>", "Setup starboard"),
                    ("serverconfig", "Configuration menu"),
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

    class CategorySelect(discord.ui.Select):
        def __init__(self, cog: 'Help', is_owner: bool):
            options = []
            # add regular categories
            for cat_name, cat_data in cog.categories.items():
                label = cat_name
                # value = key for matching
                value = cat_data.get('key') or cat_name
                options.append(discord.SelectOption(label=label, value=value, description=cat_data.get('desc', '')[:100]))

            # add owner categories if owner
            if is_owner:
                for cat_name, cat_data in cog.owner_category.items():
                    label = cat_name
                    value = cat_data.get('key') or cat_name
                    options.append(discord.SelectOption(label=label, value=value, description=cat_data.get('desc', '')[:100]))

            super().__init__(placeholder='Choose a category...', min_values=1, max_values=1, options=options)
            self.cog = cog

        async def callback(self, interaction: discord.Interaction):
            # selected value is category key
            sel = self.values[0]
            is_owner = interaction.user.id in getattr(self.cog.bot, 'owner_ids', [])
            # delegate to cog's category helper
            await self.cog._send_category_help(interaction, sel.lower(), is_owner, is_slash=True)

    class CategoryView(discord.ui.View):
        def __init__(self, cog: 'Help', is_owner: bool, timeout: int = 60):
            super().__init__(timeout=timeout)
            self.add_item(Help.CategorySelect(cog, is_owner))
    
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
        
        view = Help.CategoryView(self, is_owner)
        if is_slash:
            await ctx.response.send_message(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)
    
    async def _send_category_help(self, ctx, category_key, is_owner, is_slash=False):
        """Send help for a specific category"""
        def _normalize(text: str) -> str:
            # remove non-alphanumeric characters (including emoji/punctuation), collapse whitespace
            text = re.sub(r"[^\w\s]", '', text or '')
            return ' '.join(text.split()).strip().lower()
        
        # Special case: redirect owner/👑 to ownerhelp command
        raw_key = (category_key or '').strip()
        norm_key = _normalize(raw_key)
        if norm_key == 'owner' or raw_key == '👑':
            if is_owner:
                # Invoke ownerhelp command from owner.py
                owner_cog = self.bot.get_cog('Owner')
                if owner_cog:
                    ownerhelp_cmd = owner_cog.owner_help
                    if is_slash:
                        # Create fake context for prefix command that forwards to interaction followup
                        class FakeCtx:
                            def __init__(self, interaction: discord.Interaction):
                                self._interaction = interaction
                                self.author = interaction.user
                                self.guild = interaction.guild
                                self.channel = interaction.channel
                                self.bot = interaction.client

                            async def send(self, *args, **kwargs):
                                # use followup to send after deferring
                                return await self._interaction.followup.send(*args, **kwargs)

                        await ctx.response.defer()
                        fake_ctx = FakeCtx(ctx)
                        await ownerhelp_cmd(fake_ctx)
                    else:
                        await ownerhelp_cmd(ctx)
                    return
            else:
                msg = "❌ This category is owner-only!"
                if is_slash:
                    await ctx.response.send_message(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return
        
        # Find category
        category_data = None
        category_name = None

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
        
        if not category_data:
            msg = f"❌ Category `{category_key}` not found!\nUse `L!help` to see all categories."
            if is_slash:
                await ctx.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Create embed for normal categories
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
