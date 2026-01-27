import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
from typing import Optional
import asyncio
import json
import os
import math
import re
import time
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

ALLOWED_SAY_USER_ID = 1382187068373074001

class MinigamePaginator(View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0
        self.message = None
        
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])
    
    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        
        await interaction.message.delete()
        self.stop()


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.reminders_file = os.path.join(data_dir, "reminders.json")
        self.prefix_file = os.path.join(data_dir, "server_prefixes.json")
        self.reminders = self.load_reminders()
        self.prefixes = self.load_prefixes()
        
        # Start reminder checker (use cog_load hook instead of __init__)
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.check_reminders.start()
    
    @tasks.loop(seconds=60)
    async def check_reminders(self):
        """Check for due reminders"""
        current_time = datetime.utcnow()
        expired_reminders = []
        
        for user_id, user_reminders in self.reminders.items():
            for reminder in user_reminders[:]:
                remind_time = datetime.fromisoformat(reminder['time'])
                if current_time >= remind_time:
                    # Send reminder
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        embed = discord.Embed(
                            title="⏰ Reminder!",
                            description=reminder['message'],
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Set {reminder.get('set_ago', 'some time ago')}")
                        await user.send(embed=embed)
                    except:
                        pass
                    
                    user_reminders.remove(reminder)
                    expired_reminders.append((user_id, reminder))
        
        if expired_reminders:
            self.save_reminders()
    
    def load_reminders(self):
        """Load reminders from JSON"""
        if os.path.exists(self.reminders_file):
            try:
                with open(self.reminders_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def save_reminders(self):
        """Save reminders to JSON"""
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(self.reminders, f, indent=4)
        except Exception as e:
            print(f"Error saving reminders: {e}")
    
    def load_prefixes(self):
        """Load server prefixes from JSON"""
        if os.path.exists(self.prefix_file):
            try:
                with open(self.prefix_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_prefixes(self):
        """Save server prefixes to JSON"""
        try:
            with open(self.prefix_file, 'w') as f:
                json.dump(self.prefixes, f, indent=4)
        except Exception as e:
            print(f"Error saving prefixes: {e}")
    
    @commands.command(name="guide")
    async def help_command(self, ctx, category: str = None):
        """Comprehensive help command with all categories"""
        if category:
            embed = await self._get_category_help(ctx, category.lower())
            if embed:
                await ctx.send(embed=embed)
            # If embed is None, the function handled sending (e.g., paginated view)
        else:
            embed = await self._create_help_embed()
            await ctx.send(embed=embed)
    
    @app_commands.command(name="guide", description="View command guide and help")
    @app_commands.describe(category="Category to view (optional)")
    async def guide_slash(self, interaction: discord.Interaction, category: str = None):
        """Slash command for guide"""
        await interaction.response.defer()
        if category:
            # Create a fake ctx for the paginator to work with slash commands
            class FakeContext:
                def __init__(self, interaction):
                    self.author = interaction.user
                    self.send = interaction.followup.send
            
            fake_ctx = FakeContext(interaction)
            embed = await self._get_category_help(fake_ctx, category.lower())
            if embed:
                await interaction.followup.send(embed=embed)
            # If embed is None, the function handled sending (e.g., paginated view)
        else:
            embed = await self._create_help_embed()
            await interaction.followup.send(embed=embed)
            await interaction.followup.send(embed=embed)

    async def _create_help_embed(self):
        """Create main help overview with stunning visuals"""
        embed = discord.Embed(
            title="✨ **LUDUS** • The Ultimate Discord Experience",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{Emojis.SPARKLES} **Welcome to the most feature-rich Discord bot!**\n\n"
                f"{Emojis.COIN} **100+ Minigames** • {Emojis.TROPHY} **Competitive TCG** • {Emojis.LEVEL_UP} **Full RPG System**\n"
                f"{Emojis.MUSIC} **Music Player** • {Emojis.HEART} **Social Features** • {Emojis.FIRE} **Daily Quests**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**{Emojis.ROCKET} Quick Start:**\n"
                f"> {Emojis.COIN} `L!daily` - Claim daily rewards\n"
                f"> {Emojis.TREASURE} `L!balance` - Check your coins\n"
                f"> {Emojis.DICE} `L!ttt` - Play Tic-Tac-Toe\n"
                f"> {Emojis.CARDS} `/tcg` - Start your TCG journey\n\n"
                f"**Type `L!guide <category>` for detailed commands**"
            ),
            color=Colors.PRIMARY
        )
        
        # Category grid with beautiful emojis
        categories = [
            ("🎴", "TCG", "tcg", "Complete card game"),
            ("💰", "Economy", "economy", "Coins & shop"),
            ("🎲", "Board Games", "board", "Classics with AI"),
            ("🃏", "Card Games", "cards", "Multiplayer games"),
            ("🎮", "Minigames", "mini", "100+ quick games"),
            ("👥", "Social", "social", "Community fun"),
            ("🐾", "Pets", "pets", "Virtual companions"),
            ("📜", "Quests", "quests", "Daily objectives"),
            ("📊", "Leveling", "level", "XP & ranks"),
            ("🎨", "Fun", "fun", "Memes & jokes"),
            ("🎵", "Music", "music", "Voice player"),
            ("⚙️", "Admin", "admin", "Server tools"),
        ]
        
        # Add fields in a clean grid
        for emoji, name, cat_key, description in categories:
            embed.add_field(
                name=f"{emoji} **{name}**",
                value=f"*{description}*\n`L!guide {cat_key}`",
                inline=True
            )
        
        embed.set_footer(
            text=f"{Emojis.SPARKLES} Every action earns rewards! • Ludus v2.0.0 • Made with {Emojis.HEART}",
            icon_url="https://cdn.discordapp.com/emojis/123456789.png"  # Add bot icon
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        return embed

    async def _get_category_help(self, ctx, category: str):
        """Get detailed help for a specific category"""
        
        if category in ["tcg", "cards", "psyvrse"]:
            embed = discord.Embed(title="🎴 Psyvrse TCG Commands", color=discord.Color.purple())
            embed.description = "Complete trading card game with battles, ranked, tournaments, and achievements!"
            
            embed.add_field(
                name="⚔️ Core Commands",
                value="`/tcg` - Main hub & info\n"
                      "`/tcgbattle @user` - Challenge player\n"
                      "`/tcgbattleai [difficulty]` - Fight AI (Beginner to LEGENDARY)\n"
                      "`/tcganimate` - Preview animations",
                inline=False
            )
            
            embed.add_field(
                name="🎖️ Ranked System",
                value="`/tcgranked` - Queue for ranked match\n"
                      "`/tcgrank [@user]` - View ranked stats\n"
                      "`/tcgleaderboard` - Global rankings\n"
                      "**8 Tiers:** Bronze → Silver → Gold → Platinum → Diamond → Master → Grandmaster → Challenger",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Tournaments",
                value="`/tcgtournament <name> <fee>` - Create tournament\n"
                      "`/tcgjoin <name>` - Join tournament\n"
                      "`/tcgbracket <name>` - View bracket\n"
                      "`/tcgtournaments` - List active",
                inline=False
            )
            
            embed.add_field(
                name="🔨 Crafting",
                value="`/tcgcraft <card>` - Craft with dust\n"
                      "`/tcgfuse` - Fuse 3 cards → higher tier\n"
                      "`/tcgawaken <card>` - Power boost\n"
                      "`/tcgcards` - Browse all cards",
                inline=False
            )
            
            embed.add_field(
                name="👁️ Spectating",
                value="`/tcgspectate` - Watch random battle\n"
                      "`/tcgwatch <player>` - Watch specific\n"
                      "`/tcgspectators` - See who's watching",
                inline=False
            )
            
            embed.add_field(
                name="🏆 Achievements (113 Total!)",
                value="`/tcgachievements` - View all achievements\n"
                      "`/tcgachievement <name>` - View specific\n"
                      "`/tcgleaderboards` - Achievement rankings\n"
                      "**Track:** Battles, combos, ranked, crafting, spectating & more!",
                inline=False
            )
            
            embed.set_footer(text="⚡ 100+ cards • 50+ combos • 7 AI difficulties • Full competitive system!")
            return embed
        
        elif category in ["economy", "eco", "coins"]:
            embed = discord.Embed(title="💰 Economy Commands", color=discord.Color.gold())
            embed.description = "Manage your PsyCoins and items!"
            embed.add_field(name="L!balance / /balance", value="Check your PsyCoin balance", inline=False)
            embed.add_field(name="L!daily / /daily", value="Claim daily reward (100-500 coins + streaks!)", inline=False)
            embed.add_field(name="L!shop / /shop", value="Browse items you can buy", inline=False)
            embed.add_field(name="L!buy <item> / /buy", value="Purchase an item from shop", inline=False)
            embed.add_field(name="L!inventory / /inventory", value="View your owned items", inline=False)
            embed.add_field(name="L!use <item> / /use", value="Use/activate an item", inline=False)
            embed.add_field(name="L!give @user <amount>", value="Send coins to another user", inline=False)
            embed.add_field(name="L!leaderboard / /leaderboard", value="Top earners list", inline=False)
            return embed
        
        elif category in ["board", "boardgames", "games"]:
            embed = discord.Embed(title="🎲 Board Game Commands", color=discord.Color.blue())
            embed.description = "Classic games with AI and PvP!"
            embed.add_field(name="L!ttt [@user] / /ttt", value="Tic-Tac-Toe (50 coins) - Play vs AI or player", inline=False)
            embed.add_field(name="L!connect4 [@user] / /connect4", value="Connect 4 (75 coins) - Strategic column game", inline=False)
            embed.add_field(name="L!hangman / /hangman", value="Hangman (100 coins) - Guess the word!", inline=False)
            embed.set_footer(text="AI has multiple difficulty levels: Easy, Normal, Hard, Expert!")
            return embed
        
        elif category in ["cards", "cardgames", "card"]:
            embed = discord.Embed(title="🃏 Card Game Commands", color=discord.Color.red())
            embed.description = "Multiplayer card games and gambling!"
            embed.add_field(name="/uno", value="Start UNO game (2-10 players, 300+ coins)", inline=False)
            embed.add_field(name="L!gofish / /gofish", value="Go-Fish (2-5 players, 200 coins)", inline=False)
            embed.add_field(name="L!blackjack <bet> / /blackjack", value="Blackjack vs dealer (10-10,000 bet)", inline=False)
            embed.add_field(name="L!war [@user] / /war", value="Quick War card game (instant results)", inline=False)
            return embed
        
        elif category in ["mini", "minigames", "challenges"]:
            # Create paginated minigame list showing ALL 100+ games
            all_games = [
                # Word & Puzzle Games (20)
                ("L!wordle", "Guess the 5-letter word in 6 tries", "50-200 coins"),
                ("L!riddle", "Solve brain-teasing riddles", "Hints available"),
                ("L!trivia [category]", "Test your knowledge", "10-50 coins"),
                ("L!anagram", "Unscramble the letters", "20-100 coins"),
                ("L!hangman [category]", "Classic word guessing", "8 categories"),
                ("L!spelling", "Fix the misspelled word", "30 coins"),
                ("L!scramble", "Unscramble word puzzles", "25 coins"),
                ("L!crossword", "Mini crossword puzzles", "40 coins"),
                ("L!vocabulary", "Define the word", "15 coins"),
                ("L!rhyme <word>", "Find rhyming words", "10 coins"),
                
                # Quick Reaction Games (15)
                ("L!typerace", "Speed typing challenge", "WPM-based rewards"),
                ("L!fastest", "First to type wins", "30 coins"),
                ("L!reaction", "Click button fastest", "25 coins"),
                ("L!memorize", "Remember the pattern", "40 coins"),
                ("L!simonsays", "Follow the commands", "35 coins"),
                ("L!stopwatch", "Stop at exact time", "20 coins"),
                ("L!quickmath", "Solve math FAST", "25 coins"),
                ("L!colorguess", "Name the color", "15 coins"),
                ("L!emojirace", "Type the emoji", "10 coins"),
                ("L!countdown", "Count down correctly", "20 coins"),
                
                # Number & Math Games (10)
                ("L!gtn [max]", "Guess the number", "50-150 coins"),
                ("L!calculate <expr>", "Solve calculations", "10 coins"),
                ("L!mathrace", "Math speed challenge", "30 coins"),
                ("L!sequence", "Continue the pattern", "25 coins"),
                ("L!primecheck", "Is it prime?", "15 coins"),
                ("L!fibonacci <n>", "Find Fibonacci number", "20 coins"),
                ("L!factors <num>", "Find all factors", "10 coins"),
                ("L!percentage", "Percentage problems", "15 coins"),
                ("L!algebra", "Solve for X", "35 coins"),
                ("L!geometry", "Shape calculations", "25 coins"),
                
                # Logic & Strategy (12)
                ("L!mastermind", "Crack the code", "50 coins"),
                ("L!minesweeper", "Classic mine game", "40 coins"),
                ("L!sudoku", "Number puzzle", "60 coins"),
                ("L!2048", "Merge tiles to 2048", "100 coins"),
                ("L!chess_puzzle", "Solve chess mate", "50 coins"),
                ("L!logicpuzzle", "Deduction puzzles", "45 coins"),
                ("L!towers", "Tower of Hanoi", "30 coins"),
                ("L!pathfind", "Find shortest path", "35 coins"),
                ("L!bridge", "Bridge crossing puzzle", "25 coins"),
                ("L!knights", "Knight's tour puzzle", "40 coins"),
                ("L!maze", "Navigate the maze", "30 coins"),
                ("L!cryptogram", "Decode messages", "50 coins"),
                
                # Chance & Luck (8)
                ("L!coinflip", "Heads or tails", "Simple game"),
                ("L!dice [sides]", "Roll the dice", "Variable"),
                ("L!lottery", "Buy lottery tickets", "Big rewards"),
                ("L!scratchcard", "Scratch and win", "10-1000 coins"),
                ("L!wheelspin", "Spin the wheel", "Random prizes"),
                ("L!slotmini", "Quick slots", "Fast gambling"),
                ("L!fortune", "Fortune wheel", "Mystery rewards"),
                ("L!luckynum", "Pick lucky number", "Jackpot game"),
                
                # Social & Party (10)
                ("L!tod <choice>", "Truth or Dare", "10 coins"),
                ("L!wyr", "Would You Rather", "10-25 coins"),
                ("L!nhie", "Never Have I Ever", "15 coins"),
                ("L!poll <question>", "Create polls", "Community"),
                ("L!vote <id>", "Vote on polls", "5 coins"),
                ("L!story <starter>", "Collaborative story", "5 coins/word"),
                ("L!ratecard", "Rate user's card", "10 coins"),
                ("L!compliment @user", "Spread positivity", "15 coins both"),
                ("L!roast @user", "Playful banter", "10 coins"),
                ("L!highfive @user", "Celebrate together", "5 coins"),
                
                # Entertainment (8)
                ("L!8ball <question>", "Magic wisdom", "5 coins"),
                ("L!tarot", "Tarot reading", "10 coins"),
                ("L!fortune_cookie", "Get fortune", "5 coins"),
                ("L!horoscope [sign]", "Daily horoscope", "Free"),
                ("L!joke", "Random joke", "Laugh time"),
                ("L!fact", "Fun fact", "Learn something"),
                ("L!quote", "Inspirational quote", "Motivation"),
                ("L!meme", "Random meme", "Entertainment"),
                
                # Music & Audio (5)
                ("L!musicquiz", "Guess the song", "50 coins"),
                ("L!lyrics <song>", "Guess from lyrics", "30 coins"),
                ("L!instrument", "Name instrument", "20 coins"),
                ("L!beatbox", "Rhythm game", "25 coins"),
                ("L!karaoke", "Sing along", "Fun mode"),
                
                # Visual & Art (6)
                ("L!drawguess", "Drawing game", "40 coins"),
                ("L!colorblind", "Color test", "20 coins"),
                ("L!spot_diff", "Find differences", "35 coins"),
                ("L!memory_cards", "Match pairs", "30 coins"),
                ("L!pattern", "Remember pattern", "25 coins"),
                ("L!silhouette", "Guess shape", "15 coins"),
                
                # Trivia Categories (7)
                ("L!trivia movies", "Movie trivia", "30 coins"),
                ("L!trivia games", "Gaming trivia", "30 coins"),
                ("L!trivia science", "Science facts", "40 coins"),
                ("L!trivia history", "Historical events", "35 coins"),
                ("L!trivia geography", "World knowledge", "30 coins"),
                ("L!trivia sports", "Sports trivia", "25 coins"),
                ("L!trivia anime", "Anime knowledge", "30 coins"),
                
                # Collection & Trading (5)
                ("L!pokemon", "Catch Pokemon", "Collection"),
                ("L!trade @user", "Trade items", "Economy"),
                ("L!showcase", "Show collection", "Display"),
                ("L!hunt", "Hunt creatures", "20 coins"),
                ("L!fish", "Go fishing", "15-60 coins"),
                
                # RPG Elements (8)
                ("L!adventure", "Go on quest", "50-200 coins"),
                ("L!dungeon", "Explore dungeon", "100 coins"),
                ("L!boss", "Fight boss", "Big rewards"),
                ("L!quest", "Daily quests", "Objectives"),
                ("L!explore", "Explore world", "Random events"),
                ("L!treasure", "Find treasure", "30 coins"),
                ("L!loot", "Open lootbox", "Surprises"),
                ("L!raid @user", "Raid opponent", "PvP"),
            ]
            
            # Create pages with 12 games each
            games_per_page = 12
            pages = []
            total_pages = math.ceil(len(all_games) / games_per_page)
            
            for page_num in range(total_pages):
                start_idx = page_num * games_per_page
                end_idx = min(start_idx + games_per_page, len(all_games))
                page_games = all_games[start_idx:end_idx]
                
                embed = EmbedBuilder.create_embed(
                    title=f"{Emojis.GAME} Minigames Collection",
                    description=f"**{len(all_games)}+ Quick Games & Challenges!**\n"
                               f"All games reward coins and XP!\n\n"
                               f"━━━━━━━━━━━━━━━━━━━━━━━━",
                    color=Colors.PRIMARY
                )
                
                for cmd, desc, reward in page_games:
                    embed.add_field(
                        name=f"{cmd}",
                        value=f"{desc}\n💰 *{reward}*",
                        inline=True
                    )
                
                embed.set_footer(text=f"📄 Page {page_num + 1}/{total_pages} • Use buttons to navigate • All prefix commands only!")
                pages.append(embed)
            
            # Create paginator view and send
            view = MinigamePaginator(ctx, pages)
            message = await ctx.send(embed=pages[0], view=view)
            view.message = message
            return None  # Return None since we already sent the message
        
        elif category in ["social", "community"]:
            embed = discord.Embed(title="👥 Social Commands", color=discord.Color.green())
            embed.description = "Interact with the community!"
            embed.add_field(name="L!compliment @user / /compliment", value="Give a compliment (+15 coins for both)", inline=False)
            embed.add_field(name="L!roast @user / /roast", value="Light-hearted roast (+10 coins)", inline=False)
            embed.add_field(name="L!wyr / /wyr", value="Would You Rather voting (10-25 coins)", inline=False)
            embed.add_field(name="L!wyr_add <A> <B>", value="Submit your own WYR question (+20 coins)", inline=False)
            embed.add_field(name="L!story <starter> / /story-start", value="Start collaborative story (5 coins/word)", inline=False)
            embed.add_field(name="L!story_view / /story-view", value="Read completed stories", inline=False)
            embed.add_field(name="L!highfive @user", value="Celebrate together (+5 coins)", inline=False)
            return embed
        
        elif category in ["pets", "pet", "companions"]:
            embed = discord.Embed(title="🐾 Pet Commands", color=discord.Color.orange())
            embed.description = "Adopt and care for your virtual companion!"
            embed.add_field(name="L!pet adopt / /adopt", value="Adopt a pet (9 types: dog, cat, dragon, fox, etc.)", inline=False)
            embed.add_field(name="L!pet status / /pet status", value="Check hunger, happiness, and energy", inline=False)
            embed.add_field(name="L!pet feed / /feed", value="Feed your pet to restore hunger", inline=False)
            embed.add_field(name="L!pet play / /play", value="Play with pet to boost happiness", inline=False)
            embed.add_field(name="L!pet walk / /walk", value="Walk your pet to restore energy", inline=False)
            embed.set_footer(text="🌟 Happy pets give +5% gambling luck and XP bonuses!")
            return embed
        
        elif category in ["quests", "quest", "achievements", "achieve"]:
            embed = discord.Embed(title="📜 Quests & Achievements", color=discord.Color.gold())
            embed.description = "Complete objectives for rewards!"
            embed.add_field(name="L!quests / /quests", value="View available daily quests (reset at midnight)", inline=False)
            embed.add_field(name="L!achievements / /achievements", value="View achievement progress (permanent)", inline=False)
            embed.add_field(
                name="Daily Quests (Examples)",
                value="• Play 5 Games - 500 coins\n"
                      "• Social Butterfly - 400 coins\n"
                      "• Earn 1000 coins - 300 coins\n"
                      "• Win Streak - 750 coins + item",
                inline=False
            )
            embed.add_field(
                name="Achievements (Examples)",
                value="• First Victory - 100 coins\n"
                      "• Lucky Streak (7 days) - 500 coins\n"
                      "• Millionaire - 1000 coins + status",
                inline=False
            )
            return embed
        
        elif category in ["level", "leveling", "rank", "xp"]:
            embed = discord.Embed(title="📊 Leveling Commands", color=discord.Color.blue())
            embed.description = "Message-based XP progression!"
            embed.add_field(name="L!rank / /rank", value="Check your level and XP progress", inline=False)
            embed.add_field(name="L!leveltop / /leveltop", value="Top 10 users by level", inline=False)
            embed.add_field(name="L!profile / /profile", value="View complete profile stats", inline=False)
            embed.add_field(
                name="How Leveling Works",
                value="• Earn 5-15 XP per message (1min cooldown)\n"
                      "• Formula: Level² × 100 XP required\n"
                      "• Auto-roles at milestones (Level 5, 10, etc.)\n"
                      "• XP boosts available in shop!",
                inline=False
            )
            return embed
        
        elif category in ["fun", "misc"]:
            embed = discord.Embed(title="🎨 Fun Commands", color=discord.Color.magenta())
            embed.description = "Random fun and entertainment!"
            embed.add_field(name="L!joke / /joke", value="Get a random joke", inline=False)
            embed.add_field(name="L!meme / /meme", value="Random meme image", inline=False)
            embed.add_field(name="L!quote / /quote", value="Inspirational quote", inline=False)
            embed.add_field(name="L!dog / /dog", value="Cute dog pictures", inline=False)
            embed.add_field(name="L!cat / /cat", value="Adorable cat pictures", inline=False)
            embed.add_field(name="L!panda / /panda", value="Panda images", inline=False)
            embed.add_field(name="L!gif <search> / /gif", value="Search for GIFs", inline=False)
            embed.add_field(name="L!poll <question>", value="Create a quick poll", inline=False)
            return embed
        
        elif category in ["music", "audio", "voice"]:
            embed = discord.Embed(title="🎵 Music Commands", color=discord.Color.blue())
            embed.description = "Play music in voice channels!"
            embed.add_field(name="L!music play <song>", value="Play a song by name or URL", inline=False)
            embed.add_field(name="L!music pause", value="Pause current song", inline=False)
            embed.add_field(name="L!music resume", value="Resume playback", inline=False)
            embed.add_field(name="L!music skip", value="Skip to next song in queue", inline=False)
            embed.add_field(name="L!music stop", value="Stop music and leave voice", inline=False)
            embed.add_field(name="L!music queue", value="View current queue", inline=False)
            embed.add_field(name="L!music radio <genre>", value="Start radio station (lofi, pop, kpop, etc.)", inline=False)
            embed.add_field(name="L!music test <query>", value="Test music search (debug)", inline=False)
            embed.set_footer(text="🎧 Supports YouTube search and direct URLs!")
            return embed
        
        elif category in ["admin", "server", "config"]:
            embed = discord.Embed(title="⚙️ Admin Commands", color=discord.Color.dark_gray())
            embed.description = "Server configuration (Requires Admin permissions!)"
            embed.add_field(name="L!setleveling <channel>", value="Enable leveling system in channel", inline=False)
            embed.add_field(name="L!counting <channel>", value="Set up counting game channel", inline=False)
            embed.add_field(name="L!starboard <channel>", value="Enable starboard for popular messages", inline=False)
            embed.add_field(name="L!ludusconfig", value="Open configuration menu", inline=False)
            embed.add_field(name="L!ludusconfig toggle <feature>", value="Enable/disable features", inline=False)
            embed.add_field(name="L!ludusconfig set <key> <value>", value="Modify settings", inline=False)
            embed.add_field(name="L!ludusconfig reset", value="Reset to default settings", inline=False)
            return embed
        
        elif category in ["owner", "management", "admin"]:
            embed = discord.Embed(title="👑 Owner Commands", color=discord.Color.dark_red())
            embed.description = "Bot management (Owner only!)\n\nUse `L!owner` for full list."
            embed.add_field(
                name="Economy Management",
                value="`L!godmode` - Max stats\n"
                      "`L!setcoins @user <amt>` - Set balance\n"
                      "`L!addcoins @user <amt>` - Add coins\n"
                      "`L!giveitem @user <item>` - Give items",
                inline=False
            )
            embed.add_field(
                name="Fun & Events",
                value="`L!raincoins [amt]` - Give to all online\n"
                      "`L!chaos` - Random rewards\n"
                      "`L!lottery [prize]` - Random winner\n"
                      "`L!spawn` - Spawn raid boss",
                inline=False
            )
            embed.add_field(
                name="Management",
                value="`L!stats` - Bot statistics\n"
                      "`L!reload <cog>` - Reload cog\n"
                      "`L!purge [amt]` - Delete messages\n"
                      "`L!announce <msg>` - Announcement",
                inline=False
            )
            embed.set_footer(text="⚠️ These commands are restricted to bot owners only!")
            return embed
        
        return None

    @commands.command(name="setup")
    async def setup(self, ctx):
        embed = await self._create_setup_embed()
        await ctx.send(embed=embed)

    async def _create_setup_embed(self):
        embed = discord.Embed(
            title="🎮 Welcome to Ludus - Full MMO Experience!",
            description="Your ultimate Discord MMO/entertainment universe! Every action rewards you with PsyCoins!\n\nUse prefix `L!` or slash commands `/`",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Economy System",
            value="`L!balance` / `/balance` - Check PsyCoins\n"
                  "`L!daily` / `/daily` - Daily rewards\n"
                  "`L!shop` / `/shop` - Browse shop\n"
                  "`L!inventory` / `/inventory` - View items\n"
                  "`L!give` / `/give` - Send coins to friends",
            inline=False
        )
        
        embed.add_field(
            name="♟️ Board Games (PvP & AI)",
            value="`L!ttt` / `/ttt` - Tic-Tac-Toe (50 coins)\n"
                  "`L!connect4` / `/connect4` - Connect 4 (75 coins)\n"
                  "`L!hangman` / `/hangman` - Hangman (100 coins)",
            inline=False
        )
        
        embed.add_field(
            name="🃏 Card Games",
            value="`L!gofish` / `/gofish` - Go Fish\n"
                  "`L!blackjack` / `/blackjack` - Blackjack\n"
                  "`L!war` / `/war` - War (quick battle)",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Minigames & Challenges",
            value="`L!gtn` / `/gtn` - Guess the Number\n"
                  "`L!wordle` / `/wordle` - Wordle (50-200 coins)\n"
                  "`L!typerace` / `/typerace` - Typing speed test\n"
                  "`L!tarot` / `/tarot` - Tarot reading\n"
                  "`L!tod` / `/tod` - Truth or Dare\n"
                  "`L!rps` / `/rps` - Rock Paper Scissors\n"
                  "`L!coinflip` / `/coinflip` - Coin flip\n"
                  "`L!8ball` / `/8ball` - Magic 8-ball",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Social Features",
            value="`L!roast` / `/roast` - Roast someone\n"
                  "`L!compliment` / `/compliment` - Compliment\n"
                  "`L!wyr` / `/wyr` - Would You Rather\n"
                  "`L!story` / `/story-start` - Collaborative story",
            inline=False
        )
        
        embed.add_field(
            name="🐾 Virtual Pets",
            value="`L!pet adopt` / `/adopt` - Adopt a pet\n"
                  "`L!pet status` / `/pet status` - Check stats\n"
                  "`L!pet feed` / `/feed` - Feed pet\n"
                  "`L!pet play` / `/play` - Play with pet\n"
                  "`L!pet walk` / `/walk` - Walk pet",
            inline=False
        )
        
        embed.add_field(
            name="📜 Quests & Achievements",
            value="`L!quests` / `/quests` - View active quests\n"
                  "`L!achievements` / `/achievements` - View achievements\n"
                  "Complete daily quests for bonus rewards!",
            inline=False
        )
        
        embed.add_field(
            name="📊 Leveling & Leaderboards",
            value="`L!rank` / `/rank` - Check your rank\n"
                  "`L!leveltop` / `/leveltop` - Top 10 users\n"
                  "`L!leaderboard` / `/leaderboard` - PsyCoin leaderboard\n"
                  "`L!setleveling` / `/setleveling` - Enable leveling (Admin)",
            inline=False
        )
        
        embed.add_field(
            name="🎨 Fun Commands",
            value="`L!joke` / `/joke` - Random joke\n"
                  "`L!dog` / `/dog` - Dog images\n"
                  "`L!cat` / `/cat` - Cat images\n"
                  "`L!panda` / `/panda` - Panda images",
            inline=False
        )
        
        embed.add_field(
            name="🎵 Music System",
            value="`L!music play <song>` - Play music\n"
                  "`L!music pause/resume/skip/stop` - Controls\n"
                  "`L!music queue` - View queue",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Setup Commands (Admin)",
            value="`L!setleveling <channel>` - Enable leveling\n"
                  "`L!counting <channel>` - Enable counting\n"
                  "`L!starboard <channel>` - Enable starboard",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Pro Tips",
            value="• Earn PsyCoins from every activity!\n"
                  "• Complete daily quests for bonuses\n"
                  "• Buy items to boost your gameplay\n"
                  "• Unlock achievements for big rewards\n"
                  "• Maintain daily login streaks!",
            inline=False
        )
        
        embed.set_footer(text="Ludus - Your Living Discord MMO | Use /setup anytime to see this guide")
        
        return embed

    @commands.command(name="say")
    async def say(self, ctx, *, text: str = None):
        has_permission = False
        # Bot owners always allowed
        if ctx.author.id in getattr(self.bot, "owner_ids", []):
            has_permission = True
        # Original checks
        elif ctx.author.id == ALLOWED_SAY_USER_ID:
            has_permission = True
        elif ctx.guild and isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.manage_messages:
            has_permission = True
        
        if not has_permission:
            await ctx.send("❌ You need the **Manage Messages** permission to use this command!")
            return
        
        if not text:
            await ctx.send("❌ Please provide text for me to say! Example: `L!say Hello everyone!`")
            return
        
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        
        await ctx.send(text)

async def setup(bot):
    await bot.add_cog(Utilities(bot))

