import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class TutorialView(View):
    def __init__(self, ctx):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ctx = ctx
        self.current_page = "welcome"
        
        # Add navigation dropdown
        options = [
            discord.SelectOption(label="🏠 Welcome", value="welcome", description="Start here!"),
            discord.SelectOption(label="💰 Economy Basics", value="economy", description="Earn and spend coins"),
            discord.SelectOption(label="🎮 Games & Fun", value="games", description="100+ minigames to play"),
            discord.SelectOption(label="🏪 Business Guide", value="business", description="Create your shop"),
            discord.SelectOption(label="🌾 Farming Guide", value="farming", description="Plant and harvest crops"),
            discord.SelectOption(label="👥 Social Features", value="social", description="Guilds, pets, friends"),
            discord.SelectOption(label="🏆 Achievements", value="achievements", description="200+ goals to unlock"),
            discord.SelectOption(label="⚡ Energy System", value="energy", description="Manage your energy"),
            discord.SelectOption(label="📊 Profile & Stats", value="profile", description="Track your progress"),
            discord.SelectOption(label="🎯 Quick Start", value="quickstart", description="Get started now!"),
        ]
        
        select = Select(placeholder="Choose a tutorial section", options=options)
        select.callback = self.section_callback
        self.add_item(select)
    
    async def section_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This tutorial isn't for you!", ephemeral=True)
            return
        
        self.current_page = interaction.data['values'][0]
        embed = self._create_embed()
        await interaction.response.edit_message(embed=embed)
    
    def _create_embed(self):
        """Create embed for current page"""
        embeds = {
            "welcome": self._welcome_page(),
            "economy": self._economy_page(),
            "games": self._games_page(),
            "business": self._business_page(),
            "farming": self._farming_page(),
            "social": self._social_page(),
            "achievements": self._achievements_page(),
            "energy": self._energy_page(),
            "profile": self._profile_page(),
            "quickstart": self._quickstart_page(),
        }
        return embeds.get(self.current_page, self._welcome_page())
    
    def _welcome_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.SPARKLES} Welcome to Ludus!",
            description="**The Ultimate Discord Bot Experience**\n\n"
                       "Ludus is a complete world inside Discord with:\n"
                       f"{Emojis.COIN} **Economy** - Earn, spend, and trade coins\n"
                       f"{Emojis.DICE} **100+ Minigames** - Quick games for fun\n"
                       f"{Emojis.TREASURE} **Business System** - Create your shop\n"
                       f"{Emojis.FIRE} **Farming** - Grow and sell crops\n"
                       f"{Emojis.CROWN} **Guilds** - Build communities\n"
                       f"{Emojis.TROPHY} **200+ Achievements** - Unlock goals\n"
                       f"{Emojis.HEART} **Social Features** - Pets, friends, events\n"
                       f"{Emojis.LEVEL_UP} **Progression** - Track everything!\n\n"
                       "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                       "**Use the dropdown below to explore each system!**",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name=f"{Emojis.ROCKET} First Steps",
            value=f"1️⃣ Claim daily: `L!daily`\n"
                  f"2️⃣ Check balance: `L!balance`\n"
                  f"3️⃣ Play a game: `L!wordle`\n"
                  f"4️⃣ View profile: `L!profile`",
            inline=False
        )
        
        embed.add_field(
            name=f"{Emojis.TOOLS} Essential Commands",
            value="`L!guide` - Full command list\n"
                  "`L!profile` - Your stats\n"
                  "`L!help mini` - All minigames\n"
                  "`/boardgame` - Play classics",
            inline=True
        )
        
        embed.add_field(
            name=f"{Emojis.STAR} Pro Tip",
            value="Every action earns coins and XP!\n"
                  "Check achievements for bonus rewards!",
            inline=True
        )
        
        embed.set_footer(text="Select a section from the dropdown to learn more!")
        return embed
    
    def _economy_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.COIN} Economy System Guide",
            description="**Earn, Spend, and Grow Your Wealth!**\n\n"
                       "PsyCoins are the currency of Ludus. Use them for everything!",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="💰 Earning Coins",
            value="**Daily Rewards:**\n"
                  "`L!daily` - 100-500 coins + streak bonuses!\n\n"
                  "**Minigames:**\n"
                  "`L!wordle` - 50-200 coins\n"
                  "`L!riddle` - 50+ coins\n"
                  "`L!typerace` - WPM-based rewards\n\n"
                  "**Gambling:**\n"
                  "`L!slots <bet>` - Risk for big wins\n"
                  "`L!blackjack <bet>` - Beat the dealer\n\n"
                  "**Business & Farming:**\n"
                  "Sell items on marketplace\n"
                  "Harvest and sell crops",
            inline=False
        )
        
        embed.add_field(
            name="💳 Spending Coins",
            value="**Shops:**\n"
                  "`L!shop cafe` - Energy items\n"
                  "`L!shop market` - Basic supplies\n"
                  "`L!shop fishsupplies` - Fishing gear\n\n"
                  "**Upgrades:**\n"
                  "`L!business create` - Start shop (500)\n"
                  "`L!farmupgrade` - Improve farm\n"
                  "`L!guild create` - Found guild (1000)",
            inline=True
        )
        
        embed.add_field(
            name="📊 Managing Money",
            value="`L!balance` - Check your coins\n"
                  "`L!give @user <amount>` - Send coins\n"
                  "`L!inventory` - View your items\n"
                  "`L!profile` - See earnings stats",
            inline=True
        )
        
        embed.set_footer(text="Pro Tip: Daily streaks give bonus coins! Don't miss a day!")
        return embed
    
    def _games_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.DICE} Games & Minigames Guide",
            description="**100+ Games to Play!**\n\n"
                       "Every game rewards coins and XP!",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name="🏆 Challenges & Rewards",
            value="`L!challenges` - Daily/weekly goals\n"
                  " `L!streak` - Track win streaks\n"
                  "` L!pb` - Personal best scores\n"
                  "` L!randgame` - Random game picker\n\n"
                  "💎 Complete challenges for BONUS coins!",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Board Games (Slash Commands)",
            value="`/boardgame` - Interactive menu\n"
                  "• Tic-Tac-Toe with AI\n"
                  "• Connect4 strategy\n"
                  "• Hangman with hints\n\n"
                  "Or use: `L!tictactoe`, `L!connect4`, `L!hangman`",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Popular Minigames",
            value="**Word Games:**\n"
                  "`L!wordle` - Guess 5-letter words\n"
                  "`L!riddle` - Solve riddles\n"
                  "`L!trivia` - Test knowledge\n\n"
                  "**Action Games:**\n"
                  "`L!typerace` - Speed typing\n"
                  "`L!gtn` - Guess the number\n"
                  "`L!reaction` - Quick reflexes",
            inline=True
        )
        
        embed.add_field(
            name="🃏 Card Games",
            value="`/cards` - Card game menu\n"
                  "• UNO\n"
                  "• Blackjack\n"
                  "• War\n"
                  "• Go Fish\n"
                  "• Solitaire",
            inline=True
        )
        
        embed.add_field(
            name="🎲 Gambling Games",
            value="`/gambling` - Gambling menu\n"
                  "`L!slots <bet>` - Slot machine\n"
                  "`L!roulette <bet> <choice>` - Spin wheel\n"
                  "`L!crash <bet>` - Time your cashout",
            inline=True
        )
        
        embed.add_field(
            name="📝 View All Games",
            value="`L!help mini` - Paginated list\n"
                  "Shows ALL 100+ minigames!\n"
                  "Use buttons to navigate pages.",
            inline=True
        )
        
        embed.set_footer(text="Pro Tip: Win streaks give bonus rewards!")
        return embed
    
    def _business_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.MONEY} Business System Guide",
            description="**Create Your Cross-Server Shop!**\n\n"
                       "Sell items to players across ALL servers!",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="🏪 Creating Your Business",
            value="**Step 1: Start Shop**\n"
                  "`L!business create <name>` (500 coins)\n\n"
                  "**Step 2: Stock Items**\n"
                  "Catch fish: `L!fish`\n"
                  "Harvest crops: `L!farm`\n"
                  "Then: `L!business stock <item>`\n\n"
                  "**Step 3: Set Prices**\n"
                  "`L!business price <item> <price>`\n"
                  "Check marketplace for competitive pricing!",
            inline=False
        )
        
        embed.add_field(
            name="🛒 Shopping",
            value="**NPC Shops:**\n"
                  "`L!shop` - View all shops\n"
                  "`L!shop cafe` - Energy items\n"
                  "`L!shop market` - Supplies\n"
                  "`L!buy <item>` - Purchase\n\n"
                  "**Player Marketplace:**\n"
                  "`L!marketplace` - Browse all\n"
                  "`L!business view @user` - Visit shop",
            inline=True
        )
        
        embed.add_field(
            name="📈 Business Tips",
            value="• Price 10-20% above NPC shops\n"
                  "• Stock high-demand items\n"
                  "• Check `L!business stats`\n"
                  "• Keep inventory fresh\n"
                  "• Build reputation!",
            inline=True
        )
        
        embed.set_footer(text="Pro Tip: Your shop works across ALL servers - more reach = more sales!")
        return embed
    
    def _farming_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} Farming System Guide",
            description="**Plant, Grow, Harvest, Profit!**\n\n"
                       "Seasonal crops with upgradeable farm!",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="🌾 Getting Started",
            value="**Step 1: View Your Farm**\n"
                  "`L!farm` - See your plots\n\n"
                  "**Step 2: Buy Seeds**\n"
                  "`L!seeds` - View available crops\n"
                  "`L!shop market` - Buy seeds\n\n"
                  "**Step 3: Plant**\n"
                  "`L!plant <crop> <plot>` - Plant seeds\n"
                  "Costs energy! Check with `L!energy`\n\n"
                  "**Step 4: Wait & Harvest**\n"
                  "Crops take time to grow\n"
                  "`L!harvest <plot>` - Collect crops",
            inline=False
        )
        
        embed.add_field(
            name="🌱 Crop Guide",
            value="**Fast Crops (20-30m):**\n"
                  "Lettuce, Wheat, Carrot\n\n"
                  "**Medium (40-60m):**\n"
                  "Potato, Corn, Tomato\n\n"
                  "**Slow (90-120m):**\n"
                  "Watermelon, Pumpkin\n\n"
                  "💡 Seasonal crops earn more!",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Farm Upgrades",
            value="`L!farmupgrade` - View upgrades\n\n"
                  "**Available:**\n"
                  "🟫 More plots\n"
                  "💧 Sprinkler (-20% time)\n"
                  "💩 Fertilizer (+50% price)\n"
                  "🏠 Greenhouse (all seasons)",
            inline=True
        )
        
        embed.add_field(
            name="💰 Profit Strategy",
            value="1. Plant fast crops first\n"
                  "2. Harvest and sell immediately\n"
                  "3. Buy sprinkler upgrade\n"
                  "4. Scale up production\n"
                  "5. Stock your business shop!",
            inline=False
        )
        
        embed.set_footer(text="Pro Tip: Check current season - seasonal crops sell for more!")
        return embed
    
    def _social_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.HEART} Social Features Guide",
            description="**Connect, Collaborate, Compete!**\n\n"
                       "Build communities and make friends!",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name="👥 Guilds",
            value="**Create/Join:**\n"
                  "`L!guild create <name>` (1000 coins)\n"
                  "`L!guild join <name>` - Join existing\n\n"
                  "**Participate:**\n"
                  "`L!guild info` - View guild stats\n"
                  "`L!guild deposit <amount>` - Donate\n"
                  "`L!guild top` - Leaderboards\n\n"
                  "• 50 members max\n"
                  "• Shared bank\n"
                  "• Cooperative goals",
            inline=False
        )
        
        embed.add_field(
            name="🐾 Virtual Pets",
            value="`/pets` - Pet menu\n"
                  "`L!adopt <name>` - Get a pet\n"
                  "`L!pet` - Check status\n"
                  "`L!feed` - Feed pet\n"
                  "`L!play` - Play together\n"
                  "`L!walk` - Walk pet\n\n"
                  "Happy pets = bonuses!",
            inline=True
        )
        
        embed.add_field(
            name="💬 Interactions",
            value="`L!compliment @user` - Spread love\n"
                  "`L!roast @user` - Friendly banter\n"
                  "`L!highfive @user` - Celebrate\n"
                  "`L!wyr` - Would You Rather\n"
                  "`L!story <text>` - Collaborative\n\n"
                  "Earn coins for socializing!",
            inline=True
        )
        
        embed.add_field(
            name="🎉 Events",
            value="Watch for special events!\n"
                  "• Seasonal competitions\n"
                  "• Limited-time rewards\n"
                  "• Community challenges\n"
                  "Track with `L!profile`",
            inline=False
        )
        
        embed.set_footer(text="Pro Tip: Guild donations help everyone - cooperate to succeed!")
        return embed
    
    def _achievements_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Achievement System Guide",
            description="**200+ Goals to Unlock!**\n\n"
                       "Track progress and earn rewards!",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="🏆 Achievement Categories",
            value="💰 **Economy** (30) - Earn millions\n"
                  "🎰 **Gambling** (25) - Win big\n"
                  "🎮 **Gaming** (30) - Play everything\n"
                  "⚔️ **TCG** (25) - Battle mastery\n"
                  "💖 **Social** (25) - Make friends\n"
                  "🎣 **Fishing** (20) - Catch legends\n"
                  "📜 **Quests** (15) - Complete all\n"
                  "🎉 **Events** (15) - Join competitions\n"
                  "🎯 **Board Games** (15) - Win streaks\n"
                  "⚡ **Milestones** (10) - Activity goals",
            inline=False
        )
        
        embed.add_field(
            name="📊 Viewing Progress",
            value="`L!achievements` - Full list\n"
                  "`/achievements` - Slash version\n\n"
                  "Use dropdown to browse categories!\n"
                  "See unlock progress & rewards",
            inline=True
        )
        
        embed.add_field(
            name="🎁 Rewards",
            value="Each achievement gives:\n"
                  "• PsyCoin bonuses\n"
                  "• Achievement points\n"
                  "• Special titles\n"
                  "• Bragging rights!\n\n"
                  "Earn thousands of coins!",
            inline=True
        )
        
        embed.add_field(
            name="🏅 Leaderboards",
            value="`L!leaderboard` - Top hunters\n\n"
                  "Compete for most:\n"
                  "• Achievement points\n"
                  "• Achievements unlocked\n"
                  "• Category completion",
            inline=False
        )
        
        embed.set_footer(text="Pro Tip: Every action tracks progress - achievements unlock automatically!")
        return embed
    
    def _energy_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} Energy System Guide",
            description="**Manage Your Energy Wisely!**\n\n"
                       "Energy powers your activities!",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="⚡ What is Energy?",
            value="Energy is used for activities:\n"
                  "• 🎣 Fishing trips\n"
                  "• 🌾 Planting crops\n"
                  "• ⚔️ Battle dungeons\n"
                  "• 🏃 Adventures\n\n"
                  "**Default:** 100/100 energy\n"
                  "Check with: `L!energy`",
            inline=False
        )
        
        embed.add_field(
            name="📊 Energy Costs",
            value="**Farming:**\n"
                  "Lettuce: 3 energy\n"
                  "Wheat: 5 energy\n"
                  "Pumpkin: 15 energy\n\n"
                  "**Fishing:**\n"
                  "5-10 energy per trip\n\n"
                  "**Battles:**\n"
                  "10-25 energy each",
            inline=True
        )
        
        embed.add_field(
            name="🔋 Restoring Energy",
            value="**At the Cafe:**\n"
                  "`L!shop cafe` - View items\n"
                  "☕ Coffee - 10 energy (15 coins)\n"
                  "🥪 Sandwich - 20 energy (25 coins)\n"
                  "🥤 Smoothie - 25 energy (30 coins)\n\n"
                  "**Auto-Restore:**\n"
                  "Energy regenerates over time!",
            inline=True
        )
        
        embed.add_field(
            name="💡 Energy Tips",
            value="1. Check before activities\n"
                  "2. Buy cafe items in bulk\n"
                  "3. Plan your day strategically\n"
                  "4. Let it regenerate overnight\n"
                  "5. Upgrades can reduce costs!",
            inline=False
        )
        
        embed.set_footer(text="Pro Tip: Stock up on energy items - they're cheap and essential!")
        return embed
    
    def _profile_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.CHART} Profile & Stats Guide",
            description="**Track Everything You Do!**\n\n"
                       "Your profile records all activities!",
            color=Colors.PRIMARY
        )
        
        embed.add_field(
            name="📊 Viewing Your Profile",
            value="`L!profile` or `L!p` - Full profile\n"
                  "`/profile` - Slash version\n\n"
                  "**4 Interactive Pages:**\n"
                  "📊 Overview - Top stats & energy\n"
                  "🎮 Gaming - All game stats\n"
                  "💰 Economy - Financial overview\n"
                  "👥 Social - Community engagement\n\n"
                  "Use buttons to switch pages!",
            inline=False
        )
        
        embed.add_field(
            name="📈 Tracked Stats (60+)",
            value="**Economy:**\n"
                  "• Coins earned/spent\n"
                  "• Business revenue\n"
                  "• Biggest wins/losses\n\n"
                  "**Gaming:**\n"
                  "• Every minigame\n"
                  "• Board game records\n"
                  "• TCG battles\n"
                  "• Fishing catches",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Use Cases",
            value="• Track progress\n"
                  "• Find favorite games\n"
                  "• See gambling ROI\n"
                  "• Monitor streaks\n"
                  "• Compare with friends\n"
                  "• Achievement hunting\n"
                  "• Flex your stats!",
            inline=True
        )
        
        embed.add_field(
            name="📱 Quick Stats",
            value="`L!balance` - Coins only\n"
                  "`L!energy` - Energy only\n"
                  "`L!inventory` - Items only\n"
                  "`L!farm` - Farm only\n"
                  "`L!business view` - Shop only",
            inline=False
        )
        
        embed.set_footer(text="Pro Tip: Every action updates your profile - nothing goes untracked!")
        return embed
    
    def _quickstart_page(self):
        embed = EmbedBuilder.create(
            title=f"{Emojis.ROCKET} Quick Start Guide",
            description="**Get Started in 5 Minutes!**\n\n"
                       "Follow these steps to begin your journey:",
            color=Colors.SUCCESS
        )
        
        embed.add_field(
            name="📅 Day 1: The Basics",
            value="1️⃣ `L!daily` - Claim free coins\n"
                  "2️⃣ `L!balance` - Check your money\n"
                  "3️⃣ `L!wordle` - Play a quick game\n"
                  "4️⃣ `L!profile` - See your stats\n"
                  "5️⃣ `L!shop cafe` - Buy energy items\n\n"
                  "**Goal:** Get familiar with commands",
            inline=False
        )
        
        embed.add_field(
            name="🎣 Day 2: First Activities",
            value="1️⃣ `L!daily` - Don't break streak!\n"
                  "2️⃣ `L!fish` - Catch some fish\n"
                  "3️⃣ `L!slots 50` - Try gambling\n"
                  "4️⃣ `L!adopt fluffy` - Get a pet\n"
                  "5️⃣ Play more minigames\n\n"
                  "**Goal:** Earn 500+ coins total",
            inline=False
        )
        
        embed.add_field(
            name="🏪 Day 3: Start Business",
            value="1️⃣ `L!daily` - Keep that streak!\n"
                  "2️⃣ `L!business create MyShop` - Start shop\n"
                  "3️⃣ `L!fish` - Catch more fish\n"
                  "4️⃣ `L!business stock fish` - Add inventory\n"
                  "5️⃣ `L!business price fish 30` - Set price\n\n"
                  "**Goal:** Make first sale",
            inline=False
        )
        
        embed.add_field(
            name="🌾 Day 4: Start Farming",
            value="1️⃣ `L!shop market` - Buy seeds\n"
                  "2️⃣ `L!plant wheat 0` - Plant crop\n"
                  "3️⃣ Wait 30 minutes...\n"
                  "4️⃣ `L!harvest 1` - Collect crop\n"
                  "5️⃣ Sell or stock in business\n\n"
                  "**Goal:** Complete harvest cycle",
            inline=False
        )
        
        embed.add_field(
            name="👥 Day 5: Go Social",
            value="1️⃣ `L!guild join` or create one\n"
                  "2️⃣ `L!compliment @friend` - Spread love\n"
                  "3️⃣ `L!achievements` - Check progress\n"
                  "4️⃣ `L!leaderboard` - See rankings\n"
                  "5️⃣ Keep playing & earning!\n\n"
                  "**Goal:** Join the community",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Pro Player Routine",
            value="**Every Day:**\n"
                  "• Claim daily reward\n"
                  "• Check `L!challenges`\n"
                  "• Harvest crops\n"
                  "• Check business sales\n"
                  "• Build win streak (bonus coins!)\n"
                  "• Feed your pet\n"
                  "• Buy energy items\n\n"
                  "**Weekly Goals:**\n"
                  "• Complete weekly challenges\n"
                  "• Unlock achievements\n"
                  "• Upgrade farm/business\n"
                  "• Climb leaderboards\n"
                  "• Help guild grow",
            inline=False
        )
        
        embed.set_footer(text="Remember: Every action earns coins and tracks stats. Have fun!")
        return embed

class Tutorial(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="tutorial", aliases=["tutorialstart"])
    async def tutorial_command(self, ctx):
        """Interactive tutorial system"""
        view = TutorialView(ctx)
        embed = view._create_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="tutorial", description="Interactive tutorial - learn how to use Ludus!")
    async def tutorial_slash(self, interaction: discord.Interaction):
        """Slash command for tutorial"""
        await interaction.response.defer()
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
        
        fake_ctx = FakeContext(interaction)
        view = TutorialView(fake_ctx)
        embed = view._create_embed()
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Tutorial(bot))
