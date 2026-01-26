from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

# Centralized hybrid command scaffold: prefix + slash groups following the
# pattern /<category> action:<subcommand> and `L!<category> <action>`.

CAT_CATEGORIES = [
    "boardgames",
    "cardgames",
    "minigames",
    "economy",
    "pets",
    "profile",
]


class CommandGroups(commands.Cog):
    """Scaffold cog that provides consistent prefix+slash group handlers.

    Each category exposes a slash `app_commands.Group` named after the category
    and a prefix command as a fallback. Subcommands are dispatched to the
    `handle_action` method which should be extended per-category.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Example slash groups (dynamically added in setup)
    # Provide a generic handler for action strings
    async def handle_action(self, interaction: Optional[discord.Interaction], ctx, category: str, action: str, *args):
        # If invoked as slash, interaction will be set. If prefix, ctx is commands.Context
        source = interaction.user if interaction else ctx.author
        reply_target = interaction.response if interaction else ctx
        text = f"[{category}] action: {action} — (expand this handler in cogs/{category}.py)"
        if interaction:
            await interaction.response.send_message(text, ephemeral=True)
        else:
            await ctx.send(text)


async def setup(bot: commands.Bot):
    # Add the scaffold cog
    if bot.get_cog('CommandGroups') is None:
        await bot.add_cog(CommandGroups(bot))

    # For each category, create a slash group and register a generic action command
    for cat in CAT_CATEGORIES:
        try:
            if bot.tree.get_command(cat) is None:
                grp = app_commands.Group(name=cat, description=f"{cat.title()} category commands")

                @grp.command(name="action", description="Perform an action in this category")
                async def _action(interaction: discord.Interaction, action: str):
                    # Dispatch to cog if available
                    cog = bot.get_cog('CommandGroups')
                    await cog.handle_action(interaction, None, cat, action)

                bot.tree.add_command(grp)
        except Exception:
            # ignore registration errors to avoid blocking bot startup
            pass

    # Create lightweight prefix command wrappers if command prefix is in use
    # These commands are simple and meant to be replaced by richer implementations
    for cat in CAT_CATEGORIES:
        cmd_name = cat
        if bot.get_command(cmd_name) is None:
            async def _prefix_wrapper(ctx, *, action: str = ''):
                cog = bot.get_cog('CommandGroups')
                await cog.handle_action(None, ctx, cat, action)
            # Bind the name dynamically
            _prefix_wrapper.__name__ = f"{cat}_cmd"
            bot.add_command(commands.Command(_prefix_wrapper, name=cmd_name))
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class BoardGameView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Tic-Tac-Toe", style=discord.ButtonStyle.primary, emoji="❌")
    async def tictactoe_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting Tic-Tac-Toe! Use `L!tictactoe @opponent` to play!")
        self.stop()
    
    @discord.ui.button(label="Connect 4", style=discord.ButtonStyle.primary, emoji="🔴")
    async def connect4_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting Connect 4! Use `L!connect4 @opponent` to play!")
        self.stop()
    
    @discord.ui.button(label="Hangman", style=discord.ButtonStyle.primary, emoji="🎯")
    async def hangman_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting Hangman! Use `L!hangman [category]` to play!\nCategories: animals, movies, countries, food, sports, tech, games, nature")
        self.stop()

class EconomyView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Balance", style=discord.ButtonStyle.success, emoji="💰")
    async def balance_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        cog = self.bot.get_cog('Economy')
        if cog:
            # Call the balance command
            ctx = await self.bot.get_context(interaction.message)
            ctx.author = interaction.user
            await cog.balance(ctx)
        self.stop()
    
    @discord.ui.button(label="Shop", style=discord.ButtonStyle.primary, emoji="🏪")
    async def shop_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Opening shop! Use `L!shop` to browse items!")
        self.stop()
    
    @discord.ui.button(label="Daily", style=discord.ButtonStyle.success, emoji="📅")
    async def daily_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Claiming daily! Use `L!daily` to get your reward!")
        self.stop()

class GamblingView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Slots", style=discord.ButtonStyle.danger, emoji="🎰")
    async def slots_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Spinning slots! Use `L!slots <amount>` to gamble!")
        self.stop()
    
    @discord.ui.button(label="Roulette", style=discord.ButtonStyle.danger, emoji="🎡")
    async def roulette_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing roulette! Use `L!roulette <bet> <choice>` to gamble!")
        self.stop()
    
    @discord.ui.button(label="Crash", style=discord.ButtonStyle.danger, emoji="💥")
    async def crash_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing crash! Use `L!crash <amount>` to gamble!")
        self.stop()

class PuzzleView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Wordle", style=discord.ButtonStyle.primary, emoji="📝")
    async def wordle_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting Wordle! Use `L!wordle` to play!")
        self.stop()
    
    @discord.ui.button(label="Riddles", style=discord.ButtonStyle.primary, emoji="🧩")
    async def riddle_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting riddle game! Use `L!riddle` to play!")
        self.stop()
    
    @discord.ui.button(label="Anagrams", style=discord.ButtonStyle.primary, emoji="🔤")
    async def anagram_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting anagram game! Use `L!anagram` to play!")
        self.stop()

class FunView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Joke", style=discord.ButtonStyle.success, emoji="😂")
    async def joke_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Getting a joke! Use `L!joke` for more!")
        self.stop()
    
    @discord.ui.button(label="Fact", style=discord.ButtonStyle.primary, emoji="💡")
    async def fact_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Getting a fun fact! Use `L!fact` for more!")
        self.stop()
    
    @discord.ui.button(label="8-Ball", style=discord.ButtonStyle.primary, emoji="🎱")
    async def eightball_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Shaking the 8-ball! Use `L!8ball <question>` to ask!")
        self.stop()
    
    @discord.ui.button(label="Tarot", style=discord.ButtonStyle.primary, emoji="🔮")
    async def tarot_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Drawing a tarot card! Use `L!tarot` for a reading!")
        self.stop()

class PetView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Adopt", style=discord.ButtonStyle.success, emoji="🐾")
    async def adopt_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Adopting a pet! Use `L!adopt <name>` to get started!")
        self.stop()
    
    @discord.ui.button(label="Status", style=discord.ButtonStyle.primary, emoji="📊")
    async def status_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Checking pet status! Use `L!pet` to view!")
        self.stop()
    
    @discord.ui.button(label="Feed", style=discord.ButtonStyle.success, emoji="🍖")
    async def feed_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Feeding your pet! Use `L!feed` to feed!")
        self.stop()

class SocialView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="Compliment", style=discord.ButtonStyle.success, emoji="💖")
    async def compliment_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Sending compliment! Use `L!compliment @user` to spread love!")
        self.stop()
    
    @discord.ui.button(label="Roast", style=discord.ButtonStyle.danger, emoji="🔥")
    async def roast_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Preparing roast! Use `L!roast @user` to roast!")
        self.stop()
    
    @discord.ui.button(label="Would You Rather", style=discord.ButtonStyle.primary, emoji="🤔")
    async def wyr_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting Would You Rather! Use `L!wyr` to play!")
        self.stop()

class CardGameView(View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot
        
    @discord.ui.button(label="UNO", style=discord.ButtonStyle.danger, emoji="🎴")
    async def uno_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Starting UNO! Use `L!uno @opponent` to play!")
        self.stop()
    
    @discord.ui.button(label="Blackjack", style=discord.ButtonStyle.primary, emoji="🃏")
    async def blackjack_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing Blackjack! Use `L!blackjack <bet>` to play!")
        self.stop()
    
    @discord.ui.button(label="War", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def war_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing War! Use `L!war @opponent` to battle!")
        self.stop()
    
    @discord.ui.button(label="Go Fish", style=discord.ButtonStyle.primary, emoji="🐟")
    async def gofish_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing Go Fish! Use `L!gofish @opponent` to play!")
        self.stop()
    
    @discord.ui.button(label="Solitaire", style=discord.ButtonStyle.success, emoji="♠️")
    async def solitaire_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.user:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        await interaction.response.defer()
        await interaction.followup.send(f"Playing Solitaire! Use `L!solitaire` to play!")
        self.stop()

class CommandGroups(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="boardgame", description="Play interactive board games!")
    async def boardgame_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.GAME} Board Games Menu",
            description="Select a board game to play!\n\n"
                       "🎮 **Available Games:**\n"
                       "❌ Tic-Tac-Toe - Classic 3x3 grid\n"
                       "🔴 Connect 4 - Strategic column game\n"
                       "🎯 Hangman - Guess the word!",
            color=Colors.PRIMARY
        )
        view = BoardGameView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="economy", description="View economy system options")
    async def economy_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.MONEY} Economy Menu",
            description="Manage your coins and purchases!\n\n"
                       "💰 **Options:**\n"
                       "💵 Balance - Check your coins\n"
                       "🏪 Shop - Browse items\n"
                       "📅 Daily - Claim daily reward",
            color=Colors.SUCCESS
        )
        view = EconomyView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="gambling", description="Try your luck with gambling games!")
    async def gambling_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.DICE} Gambling Menu",
            description="Risk your coins for big rewards!\n\n"
                       "🎰 **Games:**\n"
                       "🎰 Slots - Spin to win\n"
                       "🎡 Roulette - Bet on numbers\n"
                       "💥 Crash - Time your cashout",
            color=Colors.ERROR
        )
        view = GamblingView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="puzzle", description="Play brain-teasing puzzle games!")
    async def puzzle_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Puzzle Games Menu",
            description="Challenge your brain!\n\n"
                       "🧩 **Games:**\n"
                       "📝 Wordle - Guess the word\n"
                       "🧩 Riddles - Solve riddles\n"
                       "🔤 Anagrams - Unscramble letters",
            color=Colors.PRIMARY
        )
        view = PuzzleView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="fun", description="Enjoy fun and entertaining commands!")
    async def fun_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.STAR} Fun Menu",
            description="Entertainment at your fingertips!\n\n"
                       "🎉 **Options:**\n"
                       "😂 Joke - Get a random joke\n"
                       "💡 Fact - Learn something new\n"
                       "🎱 8-Ball - Ask a question\n"
                       "🔮 Tarot - Get a reading",
            color=Colors.WARNING
        )
        view = FunView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="pets", description="Manage your virtual pet!")
    async def pets_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.HEART} Pet System Menu",
            description="Take care of your virtual companion!\n\n"
                       "🐾 **Options:**\n"
                       "🐾 Adopt - Get a new pet\n"
                       "📊 Status - Check pet stats\n"
                       "🍖 Feed - Feed your pet",
            color=Colors.SUCCESS
        )
        view = PetView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="quests", description="View your active quests and achievements")
    async def quests_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Quests & Achievements",
            description="Track your progress!\n\n"
                       "Use `L!quests` to view all active quests\n"
                       "Complete quests for rewards!",
            color=Colors.PRIMARY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="business", description="Manage your cross-server shop and marketplace")
    async def business_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.MONEY} Business System",
            description="**Create & Manage Your Shop!**\n\n"
                       "💼 **Your Business:**\n"
                       "• Sell items from your inventory\n"
                       "• Set your own prices\n"
                       "• Works across ALL servers!\n\n"
                       "🏪 **NPC Shops:**\n"
                       "• ☕ Cozy Cafe - Energy & snacks\n"
                       "• 🏪 General Market - Basic supplies\n"
                       "• 🏭 Material Factory - Crafting items\n"
                       "• 🎣 Fish Supplies - Fishing gear\n"
                       "• 🐾 Pet Store - Pet food & toys\n"
                       "• 🔮 Magic Shop - Potions & spells\n\n"
                       "**Commands:**\n"
                       "`L!business create <name>` - Start shop (500 coins)\n"
                       "`L!business view [@user]` - Browse shops\n"
                       "`L!shop [npc]` - Visit NPC shops\n"
                       "`L!marketplace` - Cross-server market",
            color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="social", description="Interact with other users!")
    async def social_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.HEART} Social Menu",
            description="Connect with others!\n\n"
                       "💬 **Options:**\n"
                       "💖 Compliment - Spread positivity\n"
                       "🔥 Roast - Playful banter\n"
                       "🤔 Would You Rather - Fun choices",
            color=Colors.PRIMARY
        )
        view = SocialView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="admin", description="Server administration tools")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.CROWN} Admin Tools",
            description="Server management commands!\n\n"
                       "⚙️ **Available:**\n"
                       "Use prefix commands for:\n"
                       "• `L!setprefix` - Change bot prefix\n"
                       "• `L!levelconfig` - Configure leveling\n"
                       "• `L!countingchannel` - Set counting channel\n"
                       "• `L!starboard` - Configure starboard",
            color=Colors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="utility", description="Useful utility commands")
    async def utility_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.TOOLS} Utility Menu",
            description="Helpful tools for everyone!\n\n"
                       "🔧 **Available:**\n"
                       "• `L!remind` - Set reminders\n"
                       "• `L!poll` - Create polls\n"
                       "• `L!timer` - Set a timer\n"
                       "• `L!calculate` - Calculator",
            color=Colors.PRIMARY
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="events", description="Server events and scheduling")
    @app_commands.checks.has_permissions(manage_events=True)
    async def events_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.STAR} Events Menu",
            description="Manage server events!\n\n"
                       "📅 **Features:**\n"
                       "• `L!event create` - Create event\n"
                       "• `L!event list` - View events\n"
                       "• `L!event delete` - Remove event",
            color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cards", description="Play card games!")
    async def cards_slash(self, interaction: discord.Interaction):
        embed = EmbedBuilder.create(
            title=f"{Emojis.GAME} Card Games Menu",
            description="Choose your card game!\n\n"
                       "🃏 **Available Games:**\n"
                       "🎴 UNO - Reverse, skip, draw!\n"
                       "🃏 Blackjack - Beat the dealer\n"
                       "⚔️ War - Card battle\n"
                       "🐟 Go Fish - Collect pairs\n"
                       "♠️ Solitaire - Solo challenge",
            color=Colors.PRIMARY
        )
        view = CardGameView(interaction, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # Inventory slash command removed to avoid conflict with economy cog
    # @app_commands.command(name="inventory", description="View your universal inventory")
    # async def inventory_slash(self, interaction: discord.Interaction):
    #     Use L!inventory instead

async def setup(bot):
    await bot.add_cog(CommandGroups(bot))
