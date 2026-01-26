import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import random
import json
import os
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class GameChallenges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.challenges_file = os.path.join(self.data_dir, "game_challenges.json")
        self.personal_bests_file = os.path.join(self.data_dir, "personal_bests.json")
        self.streaks_file = os.path.join(self.data_dir, "game_streaks.json")
        
        # Define all game challenges FIRST before loading data
        self.all_challenges = {
            "daily": [
                {"id": "win_5_games", "name": "Quintuple Win", "desc": "Win any 5 minigames", "reward": 500, "emoji": "🏆", "target": 5},
                {"id": "earn_1000", "name": "Money Maker", "desc": "Earn 1000 coins from games", "reward": 300, "emoji": "💰", "target": 1000},
                {"id": "perfect_streak", "name": "Perfect Streak", "desc": "Win 3 games in a row", "reward": 400, "emoji": "🔥", "target": 3},
                {"id": "play_variety", "name": "Game Explorer", "desc": "Play 8 different minigames", "reward": 600, "emoji": "🎮", "target": 8},
                {"id": "speed_demon", "name": "Speed Demon", "desc": "Complete any game in under 30 seconds", "reward": 350, "emoji": "⚡", "target": 1},
                {"id": "word_master", "name": "Word Master", "desc": "Win 3 word games (wordle, riddle, anagram)", "reward": 450, "emoji": "📝", "target": 3},
                {"id": "math_genius", "name": "Math Genius", "desc": "Win 3 math games (calculator, quickmaths)", "reward": 450, "emoji": "🧮", "target": 3},
                {"id": "social_butterfly", "name": "Social Butterfly", "desc": "Play 3 games with other players", "reward": 500, "emoji": "👥", "target": 3},
            ],
            "weekly": [
                {"id": "win_30_games", "name": "Weekly Champion", "desc": "Win 30 minigames this week", "reward": 2000, "emoji": "👑", "target": 30},
                {"id": "earn_5000", "name": "Coin Collector", "desc": "Earn 5000 coins from games", "reward": 1500, "emoji": "💎", "target": 5000},
                {"id": "master_all", "name": "Jack of All Games", "desc": "Play 20 different minigames", "reward": 2500, "emoji": "🎯", "target": 20},
                {"id": "perfect_10", "name": "Perfect 10", "desc": "Win 10 games in a row", "reward": 3000, "emoji": "💯", "target": 10},
                {"id": "board_game_king", "name": "Board Game King", "desc": "Win 15 board games (tictactoe, connect4, hangman)", "reward": 1800, "emoji": "🎲", "target": 15},
                {"id": "puzzle_master", "name": "Puzzle Master", "desc": "Complete 10 puzzle games", "reward": 1600, "emoji": "🧩", "target": 10},
                {"id": "trivia_champion", "name": "Trivia Champion", "desc": "Answer 50 trivia questions correctly", "reward": 2200, "emoji": "🧠", "target": 50},
            ]
        }
        
        # Now load data after all_challenges is defined
        self.challenges = self._load_data(self.challenges_file, self._default_challenges())
        self.personal_bests = self._load_data(self.personal_bests_file, {})
        self.streaks = self._load_data(self.streaks_file, {})
    
    def _load_data(self, filepath, default):
        """Load JSON data from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_data(self, filepath, data):
        """Save JSON data to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def _default_challenges(self):
        """Generate default challenge structure"""
        return {
            "daily": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "challenges": random.sample(self.all_challenges["daily"], 3),
                "completed": {}
            },
            "weekly": {
                "week": self._get_week_number(),
                "challenges": random.sample(self.all_challenges["weekly"], 3),
                "completed": {}
            }
        }
    
    def _get_week_number(self):
        """Get current week number"""
        return datetime.now().isocalendar()[1]
    
    def _check_and_reset_challenges(self):
        """Check if challenges need to be reset"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_week = self._get_week_number()
        
        # Reset daily challenges
        if self.challenges["daily"]["date"] != today:
            self.challenges["daily"] = {
                "date": today,
                "challenges": random.sample(self.all_challenges["daily"], 3),
                "completed": {}
            }
            self._save_data(self.challenges_file, self.challenges)
        
        # Reset weekly challenges
        if self.challenges["weekly"]["week"] != current_week:
            self.challenges["weekly"] = {
                "week": current_week,
                "challenges": random.sample(self.all_challenges["weekly"], 3),
                "completed": {}
            }
            self._save_data(self.challenges_file, self.challenges)
    
    @commands.command(name="challenges", aliases=["challenge", "dailychallenge", "weeklychallenge"])
    async def view_challenges(self, ctx):
        """View today's daily and weekly challenges"""
        self._check_and_reset_challenges()
        
        user_id = str(ctx.author.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Game Challenges",
            description=f"**Complete challenges for bonus rewards!**\n"
                       f"Progress resets daily/weekly.\n\n",
            color=Colors.PRIMARY
        )
        
        # Daily Challenges
        daily_text = "**📅 DAILY CHALLENGES**\n"
        for challenge in self.challenges["daily"]["challenges"]:
            completed = self.challenges["daily"]["completed"].get(user_id, {}).get(challenge["id"], False)
            status = "✅" if completed else "⬜"
            progress = self.challenges["daily"]["completed"].get(user_id, {}).get(f"{challenge['id']}_progress", 0)
            daily_text += f"{status} {challenge['emoji']} **{challenge['name']}**\n"
            daily_text += f"   └ {challenge['desc']}\n"
            daily_text += f"   └ Progress: {progress}/{challenge['target']} | Reward: {challenge['reward']} {Emojis.COIN}\n\n"
        
        embed.add_field(name="Daily Challenges", value=daily_text, inline=False)
        
        # Weekly Challenges
        weekly_text = "**📆 WEEKLY CHALLENGES**\n"
        for challenge in self.challenges["weekly"]["challenges"]:
            completed = self.challenges["weekly"]["completed"].get(user_id, {}).get(challenge["id"], False)
            status = "✅" if completed else "⬜"
            progress = self.challenges["weekly"]["completed"].get(user_id, {}).get(f"{challenge['id']}_progress", 0)
            weekly_text += f"{status} {challenge['emoji']} **{challenge['name']}**\n"
            weekly_text += f"   └ {challenge['desc']}\n"
            weekly_text += f"   └ Progress: {progress}/{challenge['target']} | Reward: {challenge['reward']} {Emojis.COIN}\n\n"
        
        embed.add_field(name="Weekly Challenges", value=weekly_text, inline=False)
        
        embed.set_footer(text="Play minigames to complete challenges!")
        await ctx.send(embed=embed)
    
    @commands.command(name="personalbest", aliases=["pb", "highscore", "highscores"])
    async def personal_best(self, ctx, game: str = None):
        """View your personal best scores for games"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.personal_bests:
            await ctx.send(f"{Emojis.WARNING} You don't have any personal bests yet! Play some games first!")
            return
        
        user_bests = self.personal_bests[user_id]
        
        if game:
            # Show specific game
            game = game.lower()
            if game in user_bests:
                best = user_bests[game]
                embed = EmbedBuilder.create(
                    title=f"{Emojis.TROPHY} Personal Best: {game.title()}",
                    description=f"**Your Record:**\n"
                               f"🏆 Score: {best['score']}\n"
                               f"⏱️ Time: {best.get('time', 'N/A')}\n"
                               f"📅 Set on: {best['date']}\n\n"
                               f"Keep playing to beat your record!",
                    color=Colors.SUCCESS
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"{Emojis.WARNING} No personal best for `{game}` yet!")
        else:
            # Show all bests
            embed = EmbedBuilder.create(
                title=f"{Emojis.TROPHY} Your Personal Bests",
                description="**Your top scores across all games:**\n\n",
                color=Colors.PRIMARY
            )
            
            # Sort by score
            sorted_bests = sorted(user_bests.items(), key=lambda x: x[1].get('score', 0), reverse=True)[:10]
            
            best_text = ""
            for i, (game_name, data) in enumerate(sorted_bests, 1):
                best_text += f"**{i}.** {game_name.title()}\n"
                best_text += f"   └ Score: {data['score']} | Date: {data['date']}\n"
            
            embed.add_field(name="Top 10 Games", value=best_text or "No records yet!", inline=False)
            embed.set_footer(text=f"Total games with records: {len(user_bests)}")
            
            await ctx.send(embed=embed)
    
    @commands.command(name="streak", aliases=["gamestreak", "winstreak"])
    async def view_streak(self, ctx):
        """View your current game streak"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.streaks:
            self.streaks[user_id] = {
                "current": 0,
                "best": 0,
                "last_game": None,
                "games_today": 0,
                "combo": 1.0
            }
        
        streak_data = self.streaks[user_id]
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} Your Game Streak",
            description=f"**Current Performance:**\n\n",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="🔥 Win Streak",
            value=f"Current: **{streak_data['current']}** wins\n"
                  f"Best Ever: **{streak_data['best']}** wins\n\n"
                  f"{'🏆 NEW RECORD!' if streak_data['current'] == streak_data['best'] and streak_data['current'] > 0 else ''}",
            inline=True
        )
        
        combo = streak_data['combo']
        combo_emoji = "🔥" if combo >= 2.0 else "⚡" if combo >= 1.5 else "✨"
        embed.add_field(
            name=f"{combo_emoji} Combo Multiplier",
            value=f"**{combo}x** coin bonus\n"
                  f"Win games to increase!\n\n"
                  f"{'💎 MAX COMBO!' if combo >= 2.0 else ''}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Today's Activity",
            value=f"Games Played: **{streak_data['games_today']}**\n"
                  f"Keep playing for daily challenge progress!",
            inline=False
        )
        
        # Streak rewards
        rewards_text = "**Streak Rewards:**\n"
        rewards_text += "3 wins = 1.25x bonus\n"
        rewards_text += "5 wins = 1.5x bonus\n"
        rewards_text += "10 wins = 2.0x bonus 🎉"
        
        embed.add_field(name="🎁 Rewards", value=rewards_text, inline=False)
        
        embed.set_footer(text="Win consecutive games to build your streak!")
        await ctx.send(embed=embed)
    
    @commands.command(name="randgame", aliases=["randomgame", "pickgame"])
    async def random_game(self, ctx):
        """Pick a random minigame for you to play!"""
        
        games = [
            {"name": "Wordle", "cmd": "L!wordle", "emoji": "📝", "desc": "Guess the 5-letter word"},
            {"name": "Riddle", "cmd": "L!riddle", "emoji": "🤔", "desc": "Solve the riddle"},
            {"name": "Trivia", "cmd": "L!trivia", "emoji": "🧠", "desc": "Test your knowledge"},
            {"name": "Type Race", "cmd": "L!typerace", "emoji": "⌨️", "desc": "Speed typing challenge"},
            {"name": "Guess the Number", "cmd": "L!gtn", "emoji": "🔢", "desc": "Guess 1-100"},
            {"name": "Anagram", "cmd": "L!anagram", "emoji": "🔤", "desc": "Unscramble words"},
            {"name": "Calculator", "cmd": "L!calculator", "emoji": "🧮", "desc": "Mental math"},
            {"name": "Memory Chain", "cmd": "L!memorychain", "emoji": "🧠", "desc": "Remember sequences"},
            {"name": "Reaction Test", "cmd": "L!reaction", "emoji": "⚡", "desc": "Test reflexes"},
            {"name": "Emoji Blitz", "cmd": "L!emojiblitz", "emoji": "😎", "desc": "Type emoji sequences"},
            {"name": "Quick Maths", "cmd": "L!quickmaths", "emoji": "🔥", "desc": "Rapid math problems"},
            {"name": "Lightning Round", "cmd": "L!lightning", "emoji": "⚡", "desc": "10 challenges in 60s"},
            {"name": "Maze Runner", "cmd": "L!maze", "emoji": "🗺️", "desc": "Navigate the maze"},
            {"name": "Nim", "cmd": "L!nim", "emoji": "🎲", "desc": "Strategy stone game"},
            {"name": "Tic-Tac-Toe", "cmd": "L!tictactoe", "emoji": "❌", "desc": "Classic board game"},
            {"name": "Hangman", "cmd": "L!hangman", "emoji": "🎯", "desc": "Guess the word"},
            {"name": "Connect 4", "cmd": "L!connect4", "emoji": "🔴", "desc": "Connect four in a row"},
            {"name": "Word Chain", "cmd": "L!wordchain", "emoji": "🔗", "desc": "Chain words together"},
            {"name": "Rhyme Time", "cmd": "L!rhymetime", "emoji": "🎵", "desc": "Find rhyming words"},
            {"name": "Category", "cmd": "L!category", "emoji": "📂", "desc": "Name items in category"},
        ]
        
        chosen = random.choice(games)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.GAME} Random Game Picker",
            description=f"**Your randomly selected game:**\n\n"
                       f"{chosen['emoji']} **{chosen['name']}**\n"
                       f"📝 {chosen['desc']}\n\n"
                       f"**To play:**\n"
                       f"`{chosen['cmd']}`\n\n"
                       f"Good luck! 🍀",
            color=Colors.PRIMARY
        )
        
        embed.set_footer(text="Can't decide? Let fate choose! Use L!randgame again for another game.")
        await ctx.send(embed=embed)
    
    @commands.command(name="gameduel", aliases=["gchallenge"])
    async def game_duel(self, ctx, opponent: discord.Member = None):
        """Challenge another player to a random game duel!"""
        if not opponent:
            await ctx.send(f"{Emojis.WARNING} Mention someone to challenge! `L!gameduel @user`")
            return
        
        if opponent.bot:
            await ctx.send(f"{Emojis.WARNING} You can't challenge bots!")
            return
        
        if opponent == ctx.author:
            await ctx.send(f"{Emojis.WARNING} You can't challenge yourself!")
            return
        
        # Pick random competitive game
        duel_games = ["wordle", "typerace", "quickmaths", "calculator", "trivia", "anagram"]
        chosen_game = random.choice(duel_games)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Game Duel Challenge!",
            description=f"**{ctx.author.mention} challenges {opponent.mention}!**\n\n"
                       f"🎮 Game: **{chosen_game.title()}**\n"
                       f"🏆 Winner takes glory!\n\n"
                       f"Both players should type:\n"
                       f"`L!{chosen_game}`\n\n"
                       f"Highest score wins! 🔥",
            color=Colors.WARNING
        )
        
        embed.set_footer(text="You have 5 minutes to complete the game!")
        await ctx.send(embed=embed)
    
    @app_commands.command(name="challenges", description="View daily and weekly game challenges")
    async def challenges_slash(self, interaction: discord.Interaction):
        """Slash command for challenges"""
        await interaction.response.defer()
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.followup.send
        
        fake_ctx = FakeContext(interaction)
        await self.view_challenges(fake_ctx)
    
    @app_commands.command(name="streak", description="View your game win streak")
    async def streak_slash(self, interaction: discord.Interaction):
        """Slash command for streak"""
        await interaction.response.defer()
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.followup.send
        
        fake_ctx = FakeContext(interaction)
        await self.view_streak(fake_ctx)
    
    @app_commands.command(name="randgame", description="Pick a random minigame to play!")
    async def randgame_slash(self, interaction: discord.Interaction):
        """Slash command for random game"""
        await interaction.response.defer()
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.followup.send
        
        fake_ctx = FakeContext(interaction)
        await self.random_game(fake_ctx)
    
    # Helper methods for tracking (called by other cogs)
    def update_personal_best(self, user_id, game_name, score, time=None):
        """Update personal best for a game"""
        user_id = str(user_id)
        if user_id not in self.personal_bests:
            self.personal_bests[user_id] = {}
        
        current_best = self.personal_bests[user_id].get(game_name, {}).get('score', 0)
        if score > current_best:
            self.personal_bests[user_id][game_name] = {
                'score': score,
                'time': time,
                'date': datetime.now().strftime("%Y-%m-%d")
            }
            self._save_data(self.personal_bests_file, self.personal_bests)
            return True  # New record!
        return False
    
    def update_streak(self, user_id, won=True):
        """Update win streak"""
        user_id = str(user_id)
        if user_id not in self.streaks:
            self.streaks[user_id] = {
                "current": 0,
                "best": 0,
                "last_game": None,
                "games_today": 0,
                "combo": 1.0
            }
        
        if won:
            self.streaks[user_id]["current"] += 1
            if self.streaks[user_id]["current"] > self.streaks[user_id]["best"]:
                self.streaks[user_id]["best"] = self.streaks[user_id]["current"]
            
            # Update combo
            current = self.streaks[user_id]["current"]
            if current >= 10:
                self.streaks[user_id]["combo"] = 2.0
            elif current >= 5:
                self.streaks[user_id]["combo"] = 1.5
            elif current >= 3:
                self.streaks[user_id]["combo"] = 1.25
        else:
            self.streaks[user_id]["current"] = 0
            self.streaks[user_id]["combo"] = 1.0
        
        self.streaks[user_id]["games_today"] += 1
        self.streaks[user_id]["last_game"] = datetime.now().isoformat()
        self._save_data(self.streaks_file, self.streaks)
        
        return self.streaks[user_id]["combo"]
    
    def get_combo_multiplier(self, user_id):
        """Get current combo multiplier"""
        user_id = str(user_id)
        if user_id in self.streaks:
            return self.streaks[user_id].get("combo", 1.0)
        return 1.0

async def setup(bot):
    await bot.add_cog(GameChallenges(bot))
