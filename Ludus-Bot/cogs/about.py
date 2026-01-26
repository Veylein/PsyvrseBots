import discord
from discord.ext import commands

class About(commands.Cog):
    """About command - Learn about the bot"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="about")
    async def about(self, ctx):
        """Learn everything about Ludus - The Ultimate Minigame Bot!"""
        
        pages = []
        
        # Page 1: Welcome
        page1 = discord.Embed(
            title="🎮 Welcome to LUDUS - The Ultimate Minigame Bot! 🎮",
            description="**Your all-in-one entertainment powerhouse!**\n\n"
                       "Ludus isn't just a bot... it's an **EXPERIENCE**!\n\n"
                       "💰 Economy System\n"
                       "🎲 Epic Minigames\n"
                       "🌍 Global Server Events\n"
                       "🐟 Fishing & Farming\n"
                       "🎪 Fun Commands\n"
                       "⚔️ PvP Battles\n\n"
                       "**Ready to dive in? Let's go!** →",
            color=discord.Color.gold()
        )
        page1.set_footer(text="Page 1/8 • React with ➡️ to continue")
        pages.append(page1)
        
        # Page 2: Economy
        page2 = discord.Embed(
            title="💰 ECONOMY SYSTEM",
            description="**Earn, save, and flex your PsyCoins!**\n\n"
                       "**💸 Earn Money:**\n"
                       "• `/work` - Get a job and earn coins\n"
                       "• `/daily` - Claim daily rewards\n"
                       "• `/fish` - Catch valuable fish\n"
                       "• `/slots` - Try your luck at the casino\n"
                       "• Win minigames for BIG payouts!\n\n"
                       "**📊 Check Stats:**\n"
                       "• `/balance` - See your wealth\n"
                       "• `/leaderboard` - Who's the richest?\n\n"
                       "**Pro Tip:** Save coins for fishing equipment and farm upgrades! 🎣🚜",
            color=discord.Color.green()
        )
        page2.set_footer(text="Page 2/8")
        pages.append(page2)
        
        # Page 3: Puzzle & Arcade Games
        page3 = discord.Embed(
            title="🎯 PUZZLE & ARCADE GAMES",
            description="**Brain teasers and fast-paced action!**\n\n"
                       "**🧩 Puzzle Games:**\n"
                       "• `/game minesweeper` - Click and pray! 💣\n"
                       "• `/game memory` - Remember the pattern 🧠\n"
                       "• `/game codebreaker` - Crack the code 🔐\n"
                       "• `/game clue` - Solve murder mysteries 🕵️\n\n"
                       "**🎮 Arcade Games:**\n"
                       "• `/arcade pacman` - Eat pellets, dodge ghosts! 👾\n"
                       "• `/arcade mathgame` - Speed math challenges 🧮\n"
                       "• `/arcade bombdefuse` - Cut the right wire! 💣\n\n"
                       "**Rewards:** Big coin payouts for winners! 💰",
            color=discord.Color.purple()
        )
        page3.set_footer(text="Page 3/8")
        pages.append(page3)
        
        # Page 4: Board & Card Games
        page4 = discord.Embed(
            title="🎲 BOARD & CARD GAMES",
            description="**Classic games with friends!**\n\n"
                       "**🎯 Board Games:**\n"
                       "• `/ttt start` - Tic-Tac-Toe\n"
                       "• `/connect4 start` - Connect Four\n"
                       "• `/chess` - Full chess game! ♟️\n"
                       "• `/checkers` - Classic checkers\n\n"
                       "**🃏 Card Games:**\n"
                       "• `/blackjack` - Beat the dealer! 21\n"
                       "• `/poker` - Texas Hold'em\n"
                       "• `/uno` - UNO! Say it loud! 🎉\n\n"
                       "**🎰 Casino:**\n"
                       "• `/slots` - Spin to win!\n"
                       "• `/roulette` - Red or black?\n\n"
                       "**Note:** Use command groups for efficiency!",
            color=discord.Color.blue()
        )
        page4.set_footer(text="Page 4/8")
        pages.append(page4)
        
        # Page 5: Fishing & Farming
        page5 = discord.Embed(
            title="🎣 FISHING & FARMING EMPIRE",
            description="**Build your aquatic & agricultural empire!**\n\n"
                       "**🐟 FISHING SYSTEM:**\n"
                       "• `/fish` - Cast your line! (30s cooldown)\n"
                       "• `/fishzone <zone>` - Travel to special zones:\n"
                       "  - 🌿 Pond (free) - Common fish\n"
                       "  - 🌊 Ocean (50 coins) - Better catches\n"
                       "  - ❄️ Arctic (100 coins) - Rare creatures\n"
                       "  - 🏝️ Tropical (75 coins) - Exotic fish\n"
                       "  - 🌑 Abyss (200 coins) - LEGENDARY fish!\n"
                       "• `/aquarium` - View your collection\n"
                       "• `/sellfish` - Convert to cash\n"
                       "• `/fishingrod` - Upgrade equipment\n"
                       "• `/fishingtournament` - Server competitions!\n\n"
                       "**🌾 FARMING:**\n"
                       "• `/farm view` - Check your farm\n"
                       "• `/farm plant <crop>` - Grow crops\n"
                       "• `/farm harvest` - Collect your harvest\n"
                       "• `/farm sell` - Profit! 💰\n"
                       "**Seasons** change daily with bonuses!",
            color=discord.Color.green()
        )
        page5.set_footer(text="Page 5/8")
        pages.append(page5)
        
        # Page 6: Fun & Social
        page6 = discord.Embed(
            title="🎪 FUN & SOCIAL COMMANDS",
            description="**Entertainment and laughs!**\n\n"
                       "**🎭 Fun Commands:**\n"
                       "• `/animal` - Random animal pics 🐶🐱\n"
                       "• `/fact <category>` - Cool facts!\n"
                       "  Categories: animal, car, human, history, random\n"
                       "• `/meme` - Browse meme templates\n"
                       "• `/guessthesong` - Music quiz! 🎵\n"
                       "• `/joke` - Get a random joke\n"
                       "• `/eightball <question>` - Ask the magic 8-ball\n"
                       "• `/akinator start` - Mind-reading game!\n"
                       "• `/icecream` - Build custom sundaes 🍦\n\n"
                       "**😎 Social:**\n"
                       "• `/profile` - Your stats\n"
                       "• `/marry` - Propose to someone!\n"
                       "• `/pet` - Adopt virtual pets\n\n"
                       "**Pro Tip:** Daily interaction = more coins!",
            color=discord.Color.orange()
        )
        page6.set_footer(text="Page 6/8")
        pages.append(page6)
        
        # Page 7: Global Events
        page7 = discord.Embed(
            title="🌍 GLOBAL SERVER EVENTS (Epic!)",
            description="**The ULTIMATE competitive experience!**\n\n"
                       "**⚔️ SERVER VS SERVER WAR:**\n"
                       "• Owner starts with `L!event war [hours]`\n"
                       "• Choose a faction: Iron Legion, Ashborn, Voidwalkers, Skybound\n"
                       "• Earn war points by winning games!\n"
                       "• `L!joinfaction <name>` to join\n"
                       "• `L!warleaderboard` to check standings\n"
                       "• **Winner takes all!** 💰👑\n\n"
                       "**🐉 WORLD BOSS RAIDS:**\n"
                       "• Owner spawns with `L!event worldboss`\n"
                       "• **GLOBAL HP** shared across ALL servers!\n"
                       "• `L!attack` to deal damage (30s cooldown)\n"
                       "• `L!bossstats` to check progress\n"
                       "• Top damage dealers + last hit = HUGE rewards!\n"
                       "• Everyone who participates gets paid! 💎\n\n"
                       "**🎯 TARGET HUNT:**\n"
                       "• Global scavenger hunt\n"
                       "• Random challenges appear\n"
                       "• First to complete = points!\n"
                       "• Server with most points wins\n\n"
                       "**More events coming soon!**",
            color=discord.Color.red()
        )
        page7.set_footer(text="Page 7/8")
        pages.append(page7)
        
        # Page 8: Tips & Help
        page8 = discord.Embed(
            title="💡 PRO TIPS & GETTING HELP",
            description="**Master the bot like a pro!**\n\n"
                       "**💰 Money Making Tips:**\n"
                       "1. Do your `/daily` EVERY DAY\n"
                       "2. Fish in better zones for rare catches\n"
                       "3. Upgrade your fishing rod ASAP\n"
                       "4. Plant high-value crops during bonus seasons\n"
                       "5. Participate in global events for MASSIVE payouts\n"
                       "6. Win minigames = instant cash!\n\n"
                       "**🎮 Gaming Tips:**\n"
                       "• Use command groups: `/ttt start` instead of separate commands\n"
                       "• Join tournaments for extra rewards\n"
                       "• Play different games to discover what you're best at!\n\n"
                       "**📚 Need Help?**\n"
                       "• `/help` - See all commands by category\n"
                       "• `/help <category>` - Detailed command info\n"
                       "• `L!help` - Prefix commands\n\n"
                       "**🌟 HAVE FUN! That's what Ludus is all about! 🎉**",
            color=discord.Color.gold()
        )
        page8.set_footer(text="Page 8/8 • You're ready to dominate!")
        pages.append(page8)
        
        # Send all pages sequentially in DMs
        try:
            for page in pages:
                await ctx.author.send(embed=page)
            
            await ctx.send(f"📬 Check your DMs, {ctx.author.mention}! I sent you the full guide (8 pages)! 🎮")
        
        except discord.Forbidden:
            await ctx.send(f"❌ {ctx.author.mention}, I couldn't DM you! Please enable DMs from server members.")

async def setup(bot):
    await bot.add_cog(About(bot))
