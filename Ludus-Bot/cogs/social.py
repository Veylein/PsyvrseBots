import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
from typing import Optional

class Social(commands.Cog):
    """Social features - roasts, compliments, Would You Rather, Story Maker"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.wyr_file = os.path.join(data_dir, "wyr_questions.json")
        self.story_file = os.path.join(data_dir, "stories.json")
        self.wyr_data = self.load_wyr()
        self.story_data = self.load_stories()
        
        self.roasts = [
    "You're like a TikTok trend… everyone forgets you after 24 hours.",
    "You're like a lag spike… ruining everyone’s fun for no reason.",
    "You’re the human version of ‘loading…’",
    "You're like a screenshot… fake, blurry, and useless.",
    "You're like autocorrect… constantly making things worse.",
    "You’re the plot twist nobody asked for.",
    "You're like a cancelled series… nobody cares, but it still exists.",
    "You're like a bot trying to be human… cringy and failing.",
    "You're like a zoom call… nobody wants you on their screen.",
    "You’re like a bad tweet… everyone scrolls past you.",
    "You're like a password reset… annoying and unnecessary.",
    "You're like a broken meme… confusing and sad.",
    "You're like buffering TikTok… painful to watch.",
    "You're like a YouTube ad… nobody invited you.",
    "You're like a group chat notification… instantly regrettable.",
    "You're like an unskippable ad… annoying and unavoidable.",
    "You're like a glitch in Among Us… everyone hates you immediately.",
    "You're like a Discord ping at 3 AM… unwelcome and irritating.",
    "You're like a beta update… full of bugs and nobody wants it.",
    "You're like a Zoom filter gone wrong… terrifying.",
    "You're like a fake hypebeast… trying too hard and failing.",
    "You're like low-key cringe… mostly invisible, but painful when noticed.",
    "You're like a broken joystick… impossible to control.",
    "You're like a dead meme… somehow still here.",
    "You're like Fortnite dances in real life… embarrassing and unnecessary.",
    "You're like a canceled event… everyone’s better off without you.",
    "You're like a fake screenshot… everyone knows you’re lying.",
    "You're like a slow server… frustrating and unwanted.",
    "You're like a YouTube comment… irrelevant and full of errors.",
    "You're like an expired NFT… pointless and overpriced.",
    "You're like a Rickroll… nobody laughs anymore.",
    "You're like a loading screen in 2025… ridiculous.",
    "You're like a bad Discord server… empty, boring, and full of bots.",
    "You're like a Zoom background… trying to be cool but failing hard.",
    "You're like a game with pay-to-win… nobody respects you.",
    "You're like a laggy Minecraft server… everyone regrets joining.",
    "You're like a bot DM… annoying and ignored.",
    "You're like a trending hashtag… overhyped and instantly forgotten.",
    "You're like a bad filter on Instagram… trying to hide the truth, failing.",
    "You're like an unpatched game… full of errors and broken.",
    "You're like a Zoom mute button… you think you matter, but you don’t.",
    "You're like a low-effort meme… everyone sighs when they see you.",
    "You're like a fake flex… trying to be cool and failing spectacularly.",
    "You're like a Discord nitro scam… nobody trusts you.",
    "You're like a laggy Zoom call… painful for everyone involved.",
    "You're like a fake gamer profile… pretending to exist.",
    "You're like a dead server channel… useless and ignored.",
    "You're like a low-res anime… looks terrible and hard to watch.",
    "You're like an expired coupon in 2025… pointless and sad.",
    "You're like a broken TikTok challenge… nobody completes you.",
    "You're like a muted mic in a podcast… irrelevant and annoying.",
    "You're like a low-effort YouTube video… nobody clicks.",
    "You're like a bad Twitter roast… tries hard and fails.",
    "You're like a frozen Zoom window… stuck and useless.",
    "You're like a fake story screenshot… nobody believes you.",
    "You're like a laggy game lobby… everyone leaves immediately.",
    "You're like a scam link… nobody wants to touch you.",
    "You're like a broken app… crashes every time someone interacts with you."
        ]
        
        self.compliments = [
    "You’re the human version of a hug.",
    "Your smile could power a city.",
    "Talking to you is like hitting the refresh button on life.",
    "You make people feel like they actually matter.",
    "Your laugh should be bottled and sold as happiness.",
    "You have a way of turning ordinary moments into magic.",
    "Being around you is like sunshine after a week of rain.",
    "Your energy is like caffeine for the soul.",
    "You make people forget their bad days exist.",
    "You’re proof that awesome exists in human form.",
    "Your kindness could probably end wars.",
    "You have a smile that makes everything okay.",
    "Your jokes should be in a museum—they’re that good.",
    "You make everyone feel like they belong.",
    "Your creativity is literally contagious.",
    "Being in your chat is like a free spa day for the soul.",
    "You make even Mondays feel exciting.",
    "You have a heart that makes people want to be better.",
    "You radiate pure good vibes.",
    "Your confidence is inspiring as hell.",
    "You could make a room full of strangers feel like family.",
    "Your positivity should be a superpower.",
    "You make people feel seen in a world that often ignores them.",
    "Your brain is as brilliant as your smile is bright.",
    "You have a way of making everyone feel lighter just by existing.",
    "You’re like a walking 'good mood' button.",
    "Your presence makes everything feel safer and happier.",
    "You could make grumpy people giggle without trying.",
    "You’re proof that humans can be awesome.",
    "Your voice is like a warm blanket on a cold day.",
    "You have the kind of energy that makes memes jealous.",
    "Talking to you feels like a cheat code for happiness.",
    "You could brighten even the darkest chat with one word.",
    "Your mind works in ways that are endlessly impressive.",
    "You make people feel like everything is going to be okay.",
    "You have a smile that’s basically a life hack for joy.",
    "You’re like a VIP pass to good vibes only.",
    "Your laugh is basically a happiness bomb.",
    "You make people feel lighter just by being here.",
    "Your humor could cure a bad day instantly.",
    "You make the world feel less chaotic and more fun.",
    "Your personality should come with a warning: 'May cause extreme happiness.'",
    "You’re proof that humans can be cute AND smart at the same time.",
    "Being around you is like a happiness cheat code.",
    "Your energy is the kind that makes people want to dance.",
    "You have a talent for making people feel like they belong.",
    "Your kindness is the kind that changes lives quietly.",
    "You’re like a human coffee—instant mood boost.",
    "You make every chat better just by being in it.",
    "Your words could make anyone smile, even on a bad day.",
    "You’re the kind of person who makes people glad they exist.",
    "Your vibe is straight-up legendary.",
    "You could make a stone statue smile if you tried.",
    "You make happiness feel effortless."
        ]

    def load_wyr(self):
        if os.path.exists(self.wyr_file):
            with open(self.wyr_file, 'r') as f:
                return json.load(f)
        return {"questions": []}

    def save_wyr(self):
        with open(self.wyr_file, 'w') as f:
            json.dump(self.wyr_data, f, indent=2)

    def load_stories(self):
        if os.path.exists(self.story_file):
            with open(self.story_file, 'r') as f:
                return json.load(f)
        return {}

    def save_stories(self):
        with open(self.story_file, 'w') as f:
            json.dump(self.story_data, f, indent=2)

    @commands.command(name="roast")
    async def roast(self, ctx, member: Optional[discord.Member] = None):
        """Roast a user"""
        await self._roast_user(ctx.author, member, ctx, None)

    async def _roast_user(self, author, target, ctx, interaction):
        target = target or author
        roast = random.choice(self.roasts)
        
        embed = discord.Embed(
            title="🔥 Roasted!",
            description=f"{target.mention}, {roast}",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Just for fun! Don't take it seriously 😄")
        
        # Award coins for participation
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(author.id, 10, "social_interaction")
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="compliment")
    async def compliment(self, ctx, member: Optional[discord.Member] = None):
        """Compliment a user"""
        await self._compliment_user(ctx.author, member, ctx, None)

    async def _compliment_user(self, author, target, ctx, interaction):
        target = target or author
        compliment = random.choice(self.compliments)
        
        embed = discord.Embed(
            title="💝 Complimented!",
            description=f"{target.mention}, {compliment}",
            color=discord.Color.pink()
        )
        
        # Award coins for positivity
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(author.id, 15, "social_interaction")
            if target.id != author.id:
                economy_cog.add_coins(target.id, 10, "received_compliment")
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    # ==================== WOULD YOU RATHER ====================

    @commands.group(name="wouldyourather", aliases=["wyrgroup"], invoke_without_command=True)
    async def wyr(self, ctx):
        """Would You Rather game"""
        await ctx.send("**Would You Rather Commands:**\n`L!wouldyourather play` - Play the game\n`L!wouldyourather add <question>` - Add a question\n`L!wouldyourather list` - List all questions\n`L!wouldyourather remove <id>` - Remove a question")

    @wyr.command(name="play")
    async def wyr_play(self, ctx):
        """Play Would You Rather"""
        await self._play_wyr(ctx, None)

    async def _play_wyr(self, ctx, interaction):
        questions = self.wyr_data.get("questions", [])
        
        if not questions:
            # Add some default questions
            default_questions = [
                "Would you rather have the ability to fly OR be invisible?",
                "Would you rather live in the past OR the future?",
                "Would you rather have unlimited money OR unlimited time?",
                "Would you rather always be 10 minutes late OR always be 20 minutes early?",
                "Would you rather lose all your money OR lose all your photos?",
                "Would you rather be able to talk to animals OR speak every human language?",
                "Would you rather have no internet OR no phone?",
                "Would you rather be famous OR be the best friend of someone famous?",
                "Would you rather live forever OR have the perfect life for 100 years?",
                "Would you rather know when you die OR how you die?"
            ]
            self.wyr_data["questions"] = default_questions
            self.save_wyr()
            questions = default_questions
        
        question = random.choice(questions)
        
        embed = discord.Embed(
            title="🤔 Would You Rather?",
            description=question,
            color=discord.Color.purple()
        )
        embed.set_footer(text="React or type your choice in chat!")
        
        # Award coins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            user = ctx.author if ctx else interaction.user
            economy_cog.add_coins(user.id, 10, "wyr_play")
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @wyr.command(name="add")
    async def wyr_add(self, ctx, *, question: str):
        """Add a Would You Rather question"""
        await self._add_wyr(ctx.author, question, ctx, None)

    async def _add_wyr(self, author, question, ctx, interaction):
        if "would you rather" not in question.lower():
            question = f"Would you rather {question}"
        
        self.wyr_data["questions"].append(question)
        self.save_wyr()
        
        # Award coins for contribution
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(author.id, 25, "wyr_contribution")
        
        msg = f"✅ Question added! You earned **25 PsyCoins**. Total questions: {len(self.wyr_data['questions'])}"
        
        if interaction:
            await interaction.followup.send(msg)
        else:
            await ctx.send(msg)

    @wyr.command(name="list")
    async def wyr_list(self, ctx):
        """List all Would You Rather questions"""
        questions = self.wyr_data.get("questions", [])
        
        if not questions:
            await ctx.send("❌ No questions available! Add some with `L!wyr add`")
            return
        
        embed = discord.Embed(
            title="🤔 Would You Rather Questions",
            description=f"Total: {len(questions)} questions",
            color=discord.Color.purple()
        )
        
        for i, q in enumerate(questions[:10], 1):
            embed.add_field(name=f"{i}.", value=q, inline=False)
        
        if len(questions) > 10:
            embed.set_footer(text=f"Showing 10 of {len(questions)} questions")
        
        await ctx.send(embed=embed)

    # ==================== STORY MAKER ====================

    @commands.group(name="story", invoke_without_command=True)
    async def story(self, ctx):
        """Story Maker game"""
        await ctx.send("**Story Maker Commands:**\n`L!story start` - Start a new story\n`L!story read` - Read the current story\n`L!story end` - End and save the story")

    @story.command(name="start")
    async def story_start(self, ctx):
        """Start a collaborative story"""
        await self._start_story(ctx.channel, ctx.author, ctx, None)



    async def _start_story(self, channel, author, ctx, interaction):
        channel_id = str(channel.id)
        
        if channel_id in self.story_data:
            msg = "❌ A story is already in progress in this channel! Use `L!story end` to finish it first."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        self.story_data[channel_id] = {
            "words": [],
            "contributors": {},
            "started_by": author.id,
            "started_at": discord.utils.utcnow().isoformat()
        }
        self.save_stories()
        
        embed = discord.Embed(
            title="📖 Story Started!",
            description="Start typing words to build the story! Each message should be **one word** (or short phrase).\n\nContribute to earn PsyCoins!",
            color=discord.Color.blue()
        )
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @story.command(name="read")
    async def story_read(self, ctx):
        """Read the current story"""
        await self._read_story(ctx.channel, ctx, None)

    async def _read_story(self, channel, ctx, interaction):
        channel_id = str(channel.id)
        
        if channel_id not in self.story_data:
            msg = "❌ No story in progress! Start one with `L!story start`"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        story = self.story_data[channel_id]
        words = story.get("words", [])
        
        if not words:
            msg = "📖 The story is empty! Start adding words!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        story_text = " ".join(words)
        
        embed = discord.Embed(
            title="📖 Current Story",
            description=story_text[:4000],  # Discord limit
            color=discord.Color.blue()
        )
        embed.add_field(name="Word Count", value=len(words), inline=True)
        embed.add_field(name="Contributors", value=len(story.get("contributors", {})), inline=True)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @story.command(name="end")
    async def story_end(self, ctx):
        """End and save the current story"""
        await self._end_story(ctx.channel, ctx.author, ctx, None)

    async def _end_story(self, channel, author, ctx, interaction):
        channel_id = str(channel.id)
        
        if channel_id not in self.story_data:
            msg = "❌ No story in progress!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        story = self.story_data[channel_id]
        words = story.get("words", [])
        story_text = " ".join(words)
        
        # Award coins to contributors
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            for contributor_id, word_count in story.get("contributors", {}).items():
                reward = word_count * 5  # 5 coins per word
                economy_cog.add_coins(int(contributor_id), reward, "story_contribution")
        
        embed = discord.Embed(
            title="📖 Story Completed!",
            description=story_text[:4000],
            color=discord.Color.green()
        )
        embed.add_field(name="Total Words", value=len(words), inline=True)
        embed.add_field(name="Contributors", value=len(story.get("contributors", {})), inline=True)
        embed.set_footer(text="All contributors earned PsyCoins based on their word count!")
        
        # Remove from active stories
        del self.story_data[channel_id]
        self.save_stories()
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for story contributions"""
        if message.author.bot:
            return
        
        channel_id = str(message.channel.id)
        
        if channel_id not in self.story_data:
            return
        
        # Check if message starts with command prefix
        if message.content.startswith(("L!", "/", "!")):
            return
        
        # Add word to story
        word = message.content.strip()
        if len(word.split()) > 3:  # Limit to 3 words max
            await message.channel.send(f"❌ {message.author.mention}, keep it short! Max 3 words per message.")
            return
        
        story = self.story_data[channel_id]
        story["words"].append(word)
        
        # Track contributor
        user_id = str(message.author.id)
        if user_id not in story.get("contributors", {}):
            story["contributors"][user_id] = 0
        story["contributors"][user_id] += 1
        
        self.save_stories()
        
        # React to show it was added
        await message.add_reaction("📖")

    # ==================== NEW SOCIAL COMMANDS ====================
    
    @commands.command(name="ship")
    async def ship_prefix(self, ctx, user1: discord.Member, user2: discord.Member = None):
        """Ship two users together"""
        if user2 is None:
            user2 = ctx.author
        
        # Calculate ship percentage (deterministic based on user IDs)
        combined_id = user1.id + user2.id
        ship_percentage = (combined_id % 101)
        
        # Create ship name
        name1 = user1.display_name
        name2 = user2.display_name
        mid_point = len(name1) // 2
        ship_name = name1[:mid_point] + name2[mid_point:]
        
        # Determine message based on percentage
        if ship_percentage >= 90:
            message = "💕 Perfect Match! Soulmates! 💕"
            color = discord.Color.pink()
            emoji = "💖"
        elif ship_percentage >= 70:
            message = "❤️ Great compatibility! Love is in the air!"
            color = discord.Color.red()
            emoji = "❤️"
        elif ship_percentage >= 50:
            message = "💛 Could work out! Give it a shot!"
            color = discord.Color.gold()
            emoji = "💛"
        elif ship_percentage >= 30:
            message = "💙 Possible, but needs work..."
            color = discord.Color.blue()
            emoji = "💙"
        else:
            message = "💔 Better as friends..."
            color = discord.Color.greyple()
            emoji = "💔"
        
        # Create ship bar
        filled = int(ship_percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        embed = discord.Embed(
            title=f"{emoji} Shipping: {name1} × {name2}",
            description=f"**Ship Name:** {ship_name}\n\n{message}",
            color=color
        )
        embed.add_field(name="Compatibility", value=f"{bar} {ship_percentage}%", inline=False)
        embed.set_footer(text="❤️ Ship responsibly!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="pray")
    async def pray(self, ctx, user: Optional[discord.Member] = None):
        """Pray for yourself or another user"""
        target = user if user else ctx.author
        
        prayers = [
            f"🙏 {ctx.author.mention} prayed for {target.mention}!\n*May fortune smile upon you...*",
            f"✨ {ctx.author.mention} sent prayers to {target.mention}!\n*Good vibes incoming!*",
            f"🕊️ {ctx.author.mention} is praying for {target.mention}!\n*Blessings upon blessings...*",
            f"⭐ {ctx.author.mention} blessed {target.mention} with prayers!\n*Luck is on your side!*",
            f"🌟 {ctx.author.mention} prayed for {target.mention}!\n*The universe is listening...*",
            f"💫 {ctx.author.mention} sent divine prayers to {target.mention}!\n*May your days be prosperous!*"
        ]
        
        # Random coin reward (10-50)
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog and target:
            reward = random.randint(10, 50)
            economy_cog.add_coins(target.id, reward, "prayer_blessing")
            
            embed = discord.Embed(
                title="🙏 Prayer Sent",
                description=random.choice(prayers),
                color=discord.Color.gold()
            )
            embed.add_field(name="Divine Gift", value=f"+{reward} PsyCoins!", inline=False)
            embed.set_footer(text="Prayers grant small blessings...")
        else:
            embed = discord.Embed(
                description=random.choice(prayers),
                color=discord.Color.gold()
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="curse")
    async def curse(self, ctx, user: discord.Member):
        """Curse another user (for fun)"""
        if user.id == ctx.author.id:
            await ctx.send("❌ You can't curse yourself! (That's just sad...)")
            return
        
        curses = [
            f"😈 {ctx.author.mention} cursed {user.mention}!\n*May your socks always be slightly damp...*",
            f"👹 {ctx.author.mention} hexed {user.mention}!\n*May your phone always be at 1% when you need it...*",
            f"🧙‍♂️ {ctx.author.mention} cast a curse on {user.mention}!\n*May all your snacks be stale...*",
            f"💀 {ctx.author.mention} cursed {user.mention}!\n*May you always step on LEGOs...*",
            f"🔮 {ctx.author.mention} hexed {user.mention}!\n*May your pillow always be warm...*",
            f"⚡ {ctx.author.mention} cursed {user.mention}!\n*May your chargers only work at weird angles...*",
            f"🌙 {ctx.author.mention} cast dark magic on {user.mention}!\n*May you always forget what you walked into a room for...*",
            f"🕷️ {ctx.author.mention} cursed {user.mention}!\n*May your sleeves always slide down when washing hands...*"
        ]
        
        # Backfire chance (10%)
        if random.random() < 0.1:
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                penalty = random.randint(5, 20)
                if economy_cog.remove_coins(ctx.author.id, penalty):
                    embed = discord.Embed(
                        title="⚡ Curse Backfired!",
                        description=f"😱 {ctx.author.mention}'s curse backfired!\n"
                                   f"*The dark magic returned to sender...*\n\n"
                                   f"**Lost:** {penalty} PsyCoins",
                        color=discord.Color.purple()
                    )
                    embed.set_footer(text="Karma is real...")
                    await ctx.send(embed=embed)
                    return
        
        embed = discord.Embed(
            title="😈 Curse Cast",
            description=random.choice(curses),
            color=discord.Color.purple()
        )
        embed.set_footer(text="All curses are in good fun... right?")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="socialprofile", aliases=["sprof", "sp"])
    async def social_profile(self, ctx, user: Optional[discord.Member] = None):
        """Display comprehensive user profile"""
        target = user if user else ctx.author
        
        embed = discord.Embed(
            title=f"📊 {target.display_name}'s Profile",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Economy stats
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            balance = economy_cog.get_balance(target.id)
            embed.add_field(name="💰 PsyCoins", value=f"{balance:,}", inline=True)
        
        # Leveling stats
        leveling_cog = self.bot.get_cog("Leveling")
        if leveling_cog:
            try:
                if hasattr(leveling_cog, 'user_levels'):
                    user_data = leveling_cog.user_levels.get(str(target.id), {"level": 1, "xp": 0})
                    embed.add_field(name="⭐ Level", value=user_data.get("level", 1), inline=True)
                    embed.add_field(name="✨ XP", value=f"{user_data.get('xp', 0):,}", inline=True)
            except Exception:
                pass
        
        # Fishing stats
        fishing_cog = self.bot.get_cog("Fishing")
        if fishing_cog:
            try:
                if hasattr(fishing_cog, 'get_user_data'):
                    fish_data = fishing_cog.get_user_data(target.id)
                    total_fish = sum(fish_data.get("fish_caught", {}).values())
                    embed.add_field(name="🎣 Fish Caught", value=f"{total_fish:,}", inline=True)
            except Exception:
                pass
        
        # Pets stats
        pets_cog = self.bot.get_cog("Pets")
        if pets_cog:
            try:
                if hasattr(pets_cog, 'user_data'):
                    pet_data = pets_cog.user_data.get(str(target.id), {})
                    pet_count = len(pet_data.get("pets", []))
                    embed.add_field(name="🐾 Pets Owned", value=pet_count, inline=True)
            except Exception:
                pass
        
        # Zoo stats
        zoo_cog = self.bot.get_cog("Zoo")
        if zoo_cog:
            try:
                if hasattr(zoo_cog, 'load_zoo_data'):
                    zoo_data = zoo_cog.load_zoo_data()
                    user_zoo = zoo_data.get(str(target.id), {})
                    animal_count = len(user_zoo)
                    embed.add_field(name="🦁 Zoo Animals", value=animal_count, inline=True)
            except Exception:
                pass
        
        # Gambling stats
        gambling_cog = self.bot.get_cog("Gambling")
        if gambling_cog:
            try:
                if hasattr(gambling_cog, 'user_stats'):
                    stats = gambling_cog.user_stats.get(str(target.id), {})
                    total_played = stats.get("games_played", 0)
                    total_won = stats.get("games_won", 0)
                    win_rate = (total_won / total_played * 100) if total_played > 0 else 0
                    if total_played > 0:
                        embed.add_field(name="🎰 Games Won", value=f"{total_won}/{total_played} ({win_rate:.1f}%)", inline=True)
            except Exception:
                pass
        
        # Farming stats (if exists)
        farming_cog = self.bot.get_cog("Farming")
        if farming_cog:
            try:
                if hasattr(farming_cog, 'get_user_data'):
                    farm_data = farming_cog.get_user_data(target.id)
                    crops = farm_data.get("crops_harvested", 0)
                    if crops > 0:
                        embed.add_field(name="🌾 Crops Harvested", value=f"{crops:,}", inline=True)
            except Exception:
                pass
        
        # TCG stats (if exists). Support legacy `TCG` cog or the new `PsyvrseTCG` module.
        tcg_cog = self.bot.get_cog("TCG") or self.bot.get_cog("PsyvrseTCG")
        if tcg_cog:
            try:
                if hasattr(tcg_cog, 'user_decks'):
                    cards = tcg_cog.user_decks.get(str(target.id), {}).get("collection", [])
                    count = len(cards)
                else:
                    # Fallback to psyvrse_tcg module inventory
                    try:
                        from cogs import psyvrse_tcg
                        user = psyvrse_tcg.inventory.get_user(target.id)
                        count = len(user.get('cards', []))
                    except Exception:
                        count = 0
                if count > 0:
                    embed.add_field(name="🃏 Cards Owned", value=count, inline=True)
            except Exception:
                pass
        
        # Set footer with join date if available
        if target.joined_at:
            embed.set_footer(text=f"Member since {target.joined_at.strftime('%B %d, %Y')}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="avatar")
    async def avatar(self, ctx, user: Optional[discord.Member] = None):
        """Display user's avatar"""
        target = user if user else ctx.author
        
        embed = discord.Embed(
            title=f"🖼️ {target.display_name}'s Avatar",
            color=target.color if target.color != discord.Color.default() else discord.Color.blue()
        )
        
        avatar_url = target.display_avatar.url
        embed.set_image(url=avatar_url)
        
        # Add download links
        formats = ["png", "jpg", "webp"]
        if target.display_avatar.is_animated():
            formats.append("gif")
        
        links = [f"[{fmt.upper()}]({target.display_avatar.replace(format=fmt, size=1024)})" for fmt in formats]
        embed.add_field(name="Download Links", value=" • ".join(links), inline=False)
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Social(bot))
