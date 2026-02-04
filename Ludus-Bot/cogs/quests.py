import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class Quests(commands.Cog):
    """Quest and achievement system"""

    @app_commands.command(name="questshelp", description="View all quest commands and info (paginated)")
    async def questshelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Quests"
        category_desc = "Complete quests and earn rewards! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        self.quests_file = os.path.join(data_dir, "quests_data.json")
        self.achievements_file = os.path.join(data_dir, "achievements_data.json")
        self.quests_data = self.load_quests()
        self.achievements_data = self.load_achievements()
        self.check_daily_reset.start()
        
        # Define available quests
        self.daily_quests = [
            {"id": "play_5_games", "name": "Game Master", "desc": "Play 5 different minigames", "reward": 100, "target": 5},
            {"id": "social_butterfly", "name": "Social Butterfly", "desc": "Use 3 social commands", "reward": 75, "target": 3},
            {"id": "coin_collector", "name": "Coin Collector", "desc": "Earn 200 PsyCoins", "reward": 150, "target": 200},
            {"id": "pet_caretaker", "name": "Pet Caretaker", "desc": "Interact with your pet 5 times", "reward": 80, "target": 5},
            {"id": "win_streak", "name": "Winning Streak", "desc": "Win 3 games in a row", "reward": 200, "target": 3},
        ]
        
        # Define achievements
        self.all_achievements = {
            "first_win": {"name": "🏆 First Victory", "desc": "Win your first game", "reward": 50},
            "money_maker": {"name": "💰 Money Maker", "desc": "Earn 1000 total PsyCoins", "reward": 100},
            "social_expert": {"name": "🎭 Social Expert", "desc": "Use 50 social commands", "reward": 150},
            "game_master": {"name": "🎮 Game Master", "desc": "Play 100 total games", "reward": 200},
            "pet_lover": {"name": "🐾 Pet Lover", "desc": "Adopt and care for a pet for 7 days", "reward": 100},
            "quest_hunter": {"name": "📜 Quest Hunter", "desc": "Complete 10 quests", "reward": 250},
            "millionaire": {"name": "💎 Millionaire", "desc": "Accumulate 10,000 PsyCoins", "reward": 500},
            "daily_devotee": {"name": "🔥 Daily Devotee", "desc": "Maintain a 7-day login streak", "reward": 200},
            "board_game_pro": {"name": "♟️ Board Game Pro", "desc": "Win 10 board games", "reward": 150},
            "card_shark": {"name": "🃏 Card Shark", "desc": "Win 10 card games", "reward": 150},
        }

    def load_quests(self):
        if os.path.exists(self.quests_file):
            with open(self.quests_file, 'r') as f:
                return json.load(f)
        return {}

    def save_quests(self):
        with open(self.quests_file, 'w') as f:
            json.dump(self.quests_data, f, indent=2)

    def load_achievements(self):
        if os.path.exists(self.achievements_file):
            with open(self.achievements_file, 'r') as f:
                return json.load(f)
        return {}

    def save_achievements(self):
        with open(self.achievements_file, 'w') as f:
            json.dump(self.achievements_data, f, indent=2)

    def get_user_quests(self, user_id: int):
        """Get user's current quests"""
        user_key = str(user_id)
        if user_key not in self.quests_data:
            # Assign random daily quests
            daily_quest = random.choice(self.daily_quests)
            self.quests_data[user_key] = {
                "active_quests": [daily_quest],
                "completed_today": 0,
                "total_completed": 0,
                "last_reset": datetime.now().isoformat(),
                "progress": {daily_quest["id"]: 0}
            }
            self.save_quests()
        return self.quests_data[user_key]

    def update_quest_progress(self, user_id: int, quest_type: str, amount: int = 1):
        """Update progress for a specific quest type"""
        user_data = self.get_user_quests(user_id)
        
        for quest in user_data["active_quests"]:
            if quest["id"] == quest_type:
                if quest_type not in user_data["progress"]:
                    user_data["progress"][quest_type] = 0
                
                user_data["progress"][quest_type] += amount
                
                # Check if quest is complete
                if user_data["progress"][quest_type] >= quest["target"]:
                    return self._complete_quest(user_id, quest)
        
        self.save_quests()
        return None

    def _complete_quest(self, user_id: int, quest):
        """Complete a quest and award rewards"""
        user_data = self.get_user_quests(user_id)
        
        # Remove from active quests
        user_data["active_quests"].remove(quest)
        user_data["completed_today"] += 1
        user_data["total_completed"] += 1
        
        # Remove progress tracker
        if quest["id"] in user_data["progress"]:
            del user_data["progress"][quest["id"]]
        
        # Award coins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(user_id, quest["reward"], "quest_completion")
        # Chance to award a mythic TCG card for quest completion
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(user_id), 'mythic')
                if awarded:
                    try:
                        user = self.bot.get_user(user_id)
                        names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                        if user:
                            asyncio.create_task(user.send(f"🎴 You received TCG card(s): {', '.join(names)}"))
                    except Exception:
                        pass
            except Exception:
                pass
        
        self.save_quests()
        
        # Check for quest hunter achievement
        if user_data["total_completed"] >= 10:
            self.unlock_achievement(user_id, "quest_hunter")
        
        return quest

    def get_user_achievements(self, user_id: int):
        """Get user's achievements"""
        user_key = str(user_id)
        if user_key not in self.achievements_data:
            self.achievements_data[user_key] = {
                "unlocked": [],
                "progress": {}
            }
            self.save_achievements()
        return self.achievements_data[user_key]

    def unlock_achievement(self, user_id: int, achievement_id: str):
        """Unlock an achievement for a user"""
        user_data = self.get_user_achievements(user_id)
        
        if achievement_id in user_data["unlocked"]:
            return False  # Already unlocked
        
        if achievement_id not in self.all_achievements:
            return False  # Invalid achievement
        
        achievement = self.all_achievements[achievement_id]
        user_data["unlocked"].append(achievement_id)
        
        # Award coins
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(user_id, achievement["reward"], "achievement")
        # Chance to award a mythic TCG card for unlocking achievements
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(user_id), 'mythic')
                if awarded:
                    try:
                        user = self.bot.get_user(user_id)
                        names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                        if user:
                            asyncio.create_task(user.send(f"🎴 Achievement bonus: You received TCG card(s): {', '.join(names)}"))
                    except Exception:
                        pass
            except Exception:
                pass
        
        self.save_achievements()
        
        # Notify user
        try:
            user = self.bot.get_user(user_id)
            if user:
                embed = discord.Embed(
                    title="🏆 Achievement Unlocked!",
                    description=f"**{achievement['name']}**\n{achievement['desc']}\n\n+{achievement['reward']} PsyCoins",
                    color=discord.Color.gold()
                )
                asyncio.create_task(user.send(embed=embed))
        except:
            pass
        
        return True

    @tasks.loop(hours=24)
    async def check_daily_reset(self):
        """Reset daily quests at midnight"""
        now = datetime.now()
        
        for user_id, data in self.quests_data.items():
            last_reset = datetime.fromisoformat(data["last_reset"])
            
            if now.date() > last_reset.date():
                # Reset daily quests
                daily_quest = random.choice(self.daily_quests)
                data["active_quests"] = [daily_quest]
                data["completed_today"] = 0
                data["last_reset"] = now.isoformat()
                data["progress"] = {daily_quest["id"]: 0}
        
        self.save_quests()

    @check_daily_reset.before_loop
    async def before_check_daily_reset(self):
        await self.bot.wait_until_ready()

    @commands.command(name="quests")
    async def quests(self, ctx):
        """View your active quests"""
        await self._show_quests(ctx.author, ctx, None)

    async def _show_quests(self, user, ctx, interaction):
        user_data = self.get_user_quests(user.id)
        
        embed = discord.Embed(
            title="📜 Your Active Quests",
            description=f"Completed today: **{user_data['completed_today']}**\nTotal completed: **{user_data['total_completed']}**",
            color=discord.Color.blue()
        )
        
        for quest in user_data["active_quests"]:
            progress = user_data["progress"].get(quest["id"], 0)
            target = quest["target"]
            progress_bar = self._create_progress_bar(progress, target)
            
            embed.add_field(
                name=f"🎯 {quest['name']}",
                value=f"{quest['desc']}\n{progress_bar} {progress}/{target}\n**Reward:** {quest['reward']} PsyCoins",
                inline=False
            )
        
        if not user_data["active_quests"]:
            embed.add_field(name="No Active Quests", value="Check back tomorrow for new quests!", inline=False)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="achievements")
    async def achievements(self, ctx, member: Optional[discord.Member] = None):
        """View your or someone else's achievements"""
        await self._show_achievements(member or ctx.author, ctx, None)

    async def _show_achievements(self, member, ctx, interaction):
        user_data = self.get_user_achievements(member.id)
        unlocked = user_data["unlocked"]
        
        embed = discord.Embed(
            title=f"🏆 {member.display_name}'s Achievements",
            description=f"Unlocked: **{len(unlocked)}/{len(self.all_achievements)}**",
            color=discord.Color.gold()
        )
        
        for ach_id, achievement in self.all_achievements.items():
            if ach_id in unlocked:
                status = "✅"
            else:
                status = "🔒"
            
            embed.add_field(
                name=f"{status} {achievement['name']}",
                value=f"{achievement['desc']}\n*Reward: {achievement['reward']} PsyCoins*",
                inline=True
            )
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _create_progress_bar(self, current, target, length=10):
        """Create a visual progress bar"""
        filled = int((current / target) * length) if target > 0 else 0
        filled = min(filled, length)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"

import random
import asyncio

async def setup(bot):
    await bot.add_cog(Quests(bot))
