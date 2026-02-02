import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import json
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class AchievementManager:
    """Manages 200+ achievements across all bot activities"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.achievements_file = os.path.join(data_dir, "user_achievements.json")
        self.user_achievements = self.load_achievements()
        
        # Define all 200+ achievements
        self.achievements = {
            # ECONOMY ACHIEVEMENTS (30)
            "first_coins": {"name": "First Steps", "description": "Earn your first PsyCoin", "reward": 10, "points": 5, "emoji": "💰", "category": "Economy"},
            "hundred_coins": {"name": "Getting Started", "description": "Accumulate 100 PsyCoins", "reward": 50, "points": 10, "emoji": "💵", "category": "Economy"},
            "thousand_coins": {"name": "Entrepreneur", "description": "Accumulate 1,000 PsyCoins", "reward": 100, "points": 15, "emoji": "💸", "category": "Economy"},
            "ten_thousand_coins": {"name": "Business Mogul", "description": "Accumulate 10,000 PsyCoins", "reward": 500, "points": 25, "emoji": "💎", "category": "Economy"},
            "hundred_thousand_coins": {"name": "Wealthy", "description": "Accumulate 100,000 PsyCoins", "reward": 2000, "points": 50, "emoji": "👑", "category": "Economy"},
            "millionaire": {"name": "Millionaire", "description": "Accumulate 1,000,000 PsyCoins", "reward": 10000, "points": 100, "emoji": "🏆", "category": "Economy"},
            
            "daily_starter": {"name": "Daily Habit", "description": "Claim daily reward 7 days in a row", "reward": 100, "points": 15, "emoji": "📅", "category": "Economy"},
            "daily_dedication": {"name": "Dedicated", "description": "Claim daily reward 30 days in a row", "reward": 500, "points": 30, "emoji": "📆", "category": "Economy"},
            "daily_legend": {"name": "Daily Legend", "description": "Claim daily reward 100 days in a row", "reward": 2000, "points": 75, "emoji": "⭐", "category": "Economy"},
            
            "big_spender": {"name": "Big Spender", "description": "Spend 10,000 PsyCoins total", "reward": 250, "points": 20, "emoji": "💳", "category": "Economy"},
            "shopaholic": {"name": "Shopaholic", "description": "Spend 100,000 PsyCoins total", "reward": 1000, "points": 40, "emoji": "🛍️", "category": "Economy"},
            
            "business_owner": {"name": "Business Owner", "description": "Create your first business", "reward": 200, "points": 25, "emoji": "🏪", "category": "Economy"},
            "first_sale": {"name": "First Sale", "description": "Make your first business sale", "reward": 100, "points": 15, "emoji": "🤝", "category": "Economy"},
            "merchant": {"name": "Merchant", "description": "Make 50 business sales", "reward": 500, "points": 35, "emoji": "🏬", "category": "Economy"},
            "tycoon": {"name": "Business Tycoon", "description": "Make 500 business sales", "reward": 2000, "points": 75, "emoji": "🏭", "category": "Economy"},
            
            # GAMBLING ACHIEVEMENTS (25)
            "lucky_start": {"name": "Lucky Start", "description": "Win your first gambling game", "reward": 50, "points": 10, "emoji": "🎰", "category": "Gambling"},
            "gambler": {"name": "Gambler", "description": "Play 100 gambling games", "reward": 200, "points": 20, "emoji": "🎲", "category": "Gambling"},
            "high_roller": {"name": "High Roller", "description": "Play 1,000 gambling games", "reward": 1000, "points": 50, "emoji": "💎", "category": "Gambling"},
            
            "slots_novice": {"name": "Slots Novice", "description": "Play slots 50 times", "reward": 100, "points": 15, "emoji": "🎰", "category": "Gambling"},
            "slots_master": {"name": "Slots Master", "description": "Play slots 500 times", "reward": 500, "points": 35, "emoji": "🎰", "category": "Gambling"},
            
            "blackjack_player": {"name": "Blackjack Player", "description": "Play blackjack 50 times", "reward": 100, "points": 15, "emoji": "🃏", "category": "Gambling"},
            "blackjack_ace": {"name": "Blackjack Ace", "description": "Win 100 blackjack games", "reward": 500, "points": 40, "emoji": "🃏", "category": "Gambling"},
            
            "big_win": {"name": "Big Win!", "description": "Win 1,000+ coins in one game", "reward": 200, "points": 25, "emoji": "💰", "category": "Gambling"},
            "huge_win": {"name": "Huge Win!", "description": "Win 10,000+ coins in one game", "reward": 1000, "points": 50, "emoji": "💸", "category": "Gambling"},
            "jackpot": {"name": "JACKPOT!", "description": "Win 100,000+ coins in one game", "reward": 5000, "points": 100, "emoji": "🏆", "category": "Gambling"},
            
            "winning_streak": {"name": "On Fire!", "description": "Win 5 gambling games in a row", "reward": 300, "points": 30, "emoji": "🔥", "category": "Gambling"},
            "unstoppable": {"name": "Unstoppable", "description": "Win 10 gambling games in a row", "reward": 1000, "points": 60, "emoji": "⚡", "category": "Gambling"},
            
            # MINIGAMES ACHIEVEMENTS (30)
            "gamer": {"name": "Gamer", "description": "Play 50 minigames", "reward": 100, "points": 15, "emoji": "🎮", "category": "Gaming"},
            "game_master": {"name": "Game Master", "description": "Play 500 minigames", "reward": 500, "points": 40, "emoji": "🎮", "category": "Gaming"},
            "ultimate_gamer": {"name": "Ultimate Gamer", "description": "Play 2,000 minigames", "reward": 2000, "points": 80, "emoji": "🎮", "category": "Gaming"},
            
            "wordle_beginner": {"name": "Word Seeker", "description": "Win 10 Wordle games", "reward": 100, "points": 15, "emoji": "📝", "category": "Gaming"},
            "wordle_expert": {"name": "Word Master", "description": "Win 100 Wordle games", "reward": 500, "points": 40, "emoji": "📝", "category": "Gaming"},
            
            "riddle_solver": {"name": "Riddle Solver", "description": "Solve 25 riddles", "reward": 100, "points": 20, "emoji": "🧩", "category": "Gaming"},
            "riddle_master": {"name": "Riddle Master", "description": "Solve 100 riddles", "reward": 500, "points": 45, "emoji": "🧩", "category": "Gaming"},
            
            "trivia_novice": {"name": "Trivia Novice", "description": "Answer 50 trivia questions correctly", "reward": 100, "points": 20, "emoji": "❓", "category": "Gaming"},
            "trivia_genius": {"name": "Trivia Genius", "description": "Answer 500 trivia questions correctly", "reward": 1000, "points": 50, "emoji": "❓", "category": "Gaming"},
            
            "speed_demon": {"name": "Speed Demon", "description": "Get 100+ WPM in typerace", "reward": 200, "points": 30, "emoji": "⚡", "category": "Gaming"},
            "typing_god": {"name": "Typing God", "description": "Get 150+ WPM in typerace", "reward": 500, "points": 50, "emoji": "⚡", "category": "Gaming"},
            
            # TCG ACHIEVEMENTS (25)
            "tcg_beginner": {"name": "TCG Beginner", "description": "Play your first TCG battle", "reward": 50, "points": 10, "emoji": "⚔️", "category": "TCG"},
            "tcg_fighter": {"name": "TCG Fighter", "description": "Win 25 TCG battles", "reward": 200, "points": 25, "emoji": "⚔️", "category": "TCG"},
            "tcg_warrior": {"name": "TCG Warrior", "description": "Win 100 TCG battles", "reward": 500, "points": 40, "emoji": "⚔️", "category": "TCG"},
            "tcg_champion": {"name": "TCG Champion", "description": "Win 500 TCG battles", "reward": 2000, "points": 75, "emoji": "⚔️", "category": "TCG"},
            
            "ranked_debut": {"name": "Ranked Debut", "description": "Play your first ranked match", "reward": 100, "points": 15, "emoji": "🏅", "category": "TCG"},
            "silver_rank": {"name": "Silver Rank", "description": "Reach Silver tier in ranked", "reward": 200, "points": 25, "emoji": "🥈", "category": "TCG"},
            "gold_rank": {"name": "Gold Rank", "description": "Reach Gold tier in ranked", "reward": 500, "points": 40, "emoji": "🥇", "category": "TCG"},
            "diamond_rank": {"name": "Diamond Rank", "description": "Reach Diamond tier in ranked", "reward": 1000, "points": 60, "emoji": "💎", "category": "TCG"},
            "master_rank": {"name": "Master Rank", "description": "Reach Master tier in ranked", "reward": 2000, "points": 80, "emoji": "👑", "category": "TCG"},
            
            "card_collector": {"name": "Card Collector", "description": "Own 50 TCG cards", "reward": 200, "points": 20, "emoji": "🎴", "category": "TCG"},
            "card_hoarder": {"name": "Card Hoarder", "description": "Own 200 TCG cards", "reward": 1000, "points": 50, "emoji": "🎴", "category": "TCG"},
            
            "tournament_entry": {"name": "Tournament Entry", "description": "Enter your first tournament", "reward": 100, "points": 15, "emoji": "🏆", "category": "TCG"},
            "tournament_winner": {"name": "Tournament Winner", "description": "Win a tournament", "reward": 1000, "points": 75, "emoji": "🏆", "category": "TCG"},
            
            # SOCIAL ACHIEVEMENTS (25)
            "friendly": {"name": "Friendly", "description": "Give 10 compliments", "reward": 50, "points": 10, "emoji": "💖", "category": "Social"},
            "kind_soul": {"name": "Kind Soul", "description": "Give 100 compliments", "reward": 300, "points": 30, "emoji": "💖", "category": "Social"},
            "angel": {"name": "Angel", "description": "Give 500 compliments", "reward": 1000, "points": 60, "emoji": "😇", "category": "Social"},
            
            "popular": {"name": "Popular", "description": "Receive 50 compliments", "reward": 200, "points": 25, "emoji": "⭐", "category": "Social"},
            "celebrity": {"name": "Celebrity", "description": "Receive 200 compliments", "reward": 1000, "points": 50, "emoji": "🌟", "category": "Social"},
            
            "roaster": {"name": "Roast Master", "description": "Give 50 roasts", "reward": 100, "points": 15, "emoji": "🔥", "category": "Social"},
            "savage": {"name": "Savage", "description": "Give 200 roasts", "reward": 500, "points": 35, "emoji": "🔥", "category": "Social"},
            
            "pet_owner": {"name": "Pet Owner", "description": "Adopt your first pet", "reward": 100, "points": 15, "emoji": "🐾", "category": "Social"},
            "pet_lover": {"name": "Pet Lover", "description": "Feed your pet 100 times", "reward": 300, "points": 25, "emoji": "🐾", "category": "Social"},
            "pet_master": {"name": "Pet Master", "description": "Max out pet happiness 50 times", "reward": 1000, "points": 50, "emoji": "🐾", "category": "Social"},
            
            "storyteller": {"name": "Storyteller", "description": "Contribute to 25 stories", "reward": 200, "points": 20, "emoji": "📖", "category": "Social"},
            "author": {"name": "Author", "description": "Contribute to 100 stories", "reward": 500, "points": 40, "emoji": "📖", "category": "Social"},
            
            # FISHING ACHIEVEMENTS (20)
            "first_catch": {"name": "First Catch", "description": "Catch your first fish", "reward": 50, "points": 10, "emoji": "🎣", "category": "Fishing"},
            "angler": {"name": "Angler", "description": "Catch 100 fish", "reward": 200, "points": 20, "emoji": "🎣", "category": "Fishing"},
            "fishing_expert": {"name": "Fishing Expert", "description": "Catch 500 fish", "reward": 500, "points": 40, "emoji": "🎣", "category": "Fishing"},
            "master_angler": {"name": "Master Angler", "description": "Catch 2,000 fish", "reward": 2000, "points": 80, "emoji": "🎣", "category": "Fishing"},
            
            "rare_fisher": {"name": "Rare Fisher", "description": "Catch 10 rare fish", "reward": 200, "points": 25, "emoji": "🐟", "category": "Fishing"},
            "rare_hunter": {"name": "Rare Hunter", "description": "Catch 50 rare fish", "reward": 1000, "points": 50, "emoji": "🐟", "category": "Fishing"},
            
            "legendary_fisher": {"name": "Legendary Fisher", "description": "Catch your first legendary fish", "reward": 500, "points": 50, "emoji": "🐋", "category": "Fishing"},
            "legend_hunter": {"name": "Legend Hunter", "description": "Catch 10 legendary fish", "reward": 2000, "points": 80, "emoji": "🐋", "category": "Fishing"},
            
            "big_catch": {"name": "Big Catch", "description": "Catch a fish weighing 50+ kg", "reward": 300, "points": 30, "emoji": "🐟", "category": "Fishing"},
            "monster_catch": {"name": "Monster Catch", "description": "Catch a fish weighing 100+ kg", "reward": 1000, "points": 60, "emoji": "🐋", "category": "Fishing"},
            
            # QUEST ACHIEVEMENTS (15)
            "quest_starter": {"name": "Quest Starter", "description": "Complete your first quest", "reward": 50, "points": 10, "emoji": "📜", "category": "Quests"},
            "quest_hunter": {"name": "Quest Hunter", "description": "Complete 25 quests", "reward": 200, "points": 25, "emoji": "📜", "category": "Quests"},
            "quest_master": {"name": "Quest Master", "description": "Complete 100 quests", "reward": 1000, "points": 50, "emoji": "📜", "category": "Quests"},
            "quest_legend": {"name": "Quest Legend", "description": "Complete 500 quests", "reward": 5000, "points": 100, "emoji": "📜", "category": "Quests"},
            
            "daily_quester": {"name": "Daily Quester", "description": "Complete 10 daily quests", "reward": 100, "points": 15, "emoji": "📅", "category": "Quests"},
            "daily_champion": {"name": "Daily Champion", "description": "Complete 100 daily quests", "reward": 1000, "points": 50, "emoji": "📅", "category": "Quests"},
            
            # EVENT ACHIEVEMENTS (15)
            "event_participant": {"name": "Event Participant", "description": "Join your first event", "reward": 100, "points": 15, "emoji": "🎉", "category": "Events"},
            "event_enthusiast": {"name": "Event Enthusiast", "description": "Join 10 events", "reward": 300, "points": 25, "emoji": "🎉", "category": "Events"},
            "event_legend": {"name": "Event Legend", "description": "Join 50 events", "reward": 1000, "points": 50, "emoji": "🎉", "category": "Events"},
            
            "event_winner": {"name": "Event Winner", "description": "Win your first event", "reward": 500, "points": 40, "emoji": "🏆", "category": "Events"},
            "event_champion": {"name": "Event Champion", "description": "Win 10 events", "reward": 2000, "points": 75, "emoji": "🏆", "category": "Events"},
            
            # BOARD GAME ACHIEVEMENTS (15)
            "ttt_player": {"name": "Tic-Tac-Toe Player", "description": "Play 25 Tic-Tac-Toe games", "reward": 100, "points": 15, "emoji": "❌", "category": "Board Games"},
            "ttt_master": {"name": "Tic-Tac-Toe Master", "description": "Win 50 Tic-Tac-Toe games", "reward": 300, "points": 30, "emoji": "❌", "category": "Board Games"},
            
            "connect4_player": {"name": "Connect4 Player", "description": "Play 25 Connect4 games", "reward": 100, "points": 15, "emoji": "🔴", "category": "Board Games"},
            "connect4_master": {"name": "Connect4 Master", "description": "Win 50 Connect4 games", "reward": 300, "points": 30, "emoji": "🔴", "category": "Board Games"},
            
            "hangman_player": {"name": "Hangman Player", "description": "Play 25 Hangman games", "reward": 100, "points": 15, "emoji": "🎯", "category": "Board Games"},
            "hangman_master": {"name": "Hangman Master", "description": "Win 50 Hangman games", "reward": 300, "points": 30, "emoji": "🎯", "category": "Board Games"},
            
            # MILESTONE ACHIEVEMENTS (10)
            "active_user": {"name": "Active User", "description": "Use 1,000 commands", "reward": 500, "points": 40, "emoji": "⚡", "category": "Milestones"},
            "power_user": {"name": "Power User", "description": "Use 10,000 commands", "reward": 2000, "points": 75, "emoji": "⚡", "category": "Milestones"},
            "legendary_user": {"name": "Legendary User", "description": "Use 50,000 commands", "reward": 10000, "points": 150, "emoji": "⚡", "category": "Milestones"},
            
            "chatty": {"name": "Chatty", "description": "Send 1,000 messages", "reward": 200, "points": 20, "emoji": "💬", "category": "Milestones"},
            "conversationalist": {"name": "Conversationalist", "description": "Send 10,000 messages", "reward": 1000, "points": 50, "emoji": "💬", "category": "Milestones"},
            
            "veteran": {"name": "Veteran", "description": "Be active for 30 days", "reward": 500, "points": 40, "emoji": "🎖️", "category": "Milestones"},
            "ancient": {"name": "Ancient One", "description": "Be active for 365 days", "reward": 5000, "points": 100, "emoji": "👴", "category": "Milestones"},
        }
    
    def load_achievements(self):
        """Load user achievements from JSON"""
        if os.path.exists(self.achievements_file):
            try:
                with open(self.achievements_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_achievements(self):
        """Save achievements to JSON"""
        try:
            with open(self.achievements_file, 'w') as f:
                json.dump(self.user_achievements, f, indent=4)
        except Exception as e:
            print(f"Error saving achievements: {e}")
    
    def get_user_achievements(self, user_id):
        """Get or create user achievement data"""
        user_id = str(user_id)
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = {
                "unlocked": [],
                "progress": {},
                "points": 0,
                "unlocked_at": {}
            }
            self.save_achievements()
        return self.user_achievements[user_id]
    
    def check_achievement(self, user_id, achievement_id):
        """Check if user has unlocked an achievement"""
        user_data = self.get_user_achievements(user_id)
        return achievement_id in user_data["unlocked"]
    
    def unlock_achievement(self, user_id, achievement_id):
        """Unlock an achievement for a user"""
        if achievement_id not in self.achievements:
            return None
        
        user_data = self.get_user_achievements(user_id)
        
        if achievement_id in user_data["unlocked"]:
            return None  # Already unlocked
        
        achievement = self.achievements[achievement_id]
        user_data["unlocked"].append(achievement_id)
        user_data["points"] += achievement["points"]
        user_data["unlocked_at"][achievement_id] = datetime.utcnow().isoformat()
        
        self.save_achievements()
        return achievement
    
    def get_achievements_by_category(self, category):
        """Get all achievements in a category"""
        return {k: v for k, v in self.achievements.items() if v["category"] == category}
    
    def get_user_progress(self, user_id):
        """Get user's achievement progress"""
        user_data = self.get_user_achievements(user_id)
        total = len(self.achievements)
        unlocked = len(user_data["unlocked"])
        percentage = (unlocked / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "unlocked": unlocked,
            "percentage": percentage,
            "points": user_data["points"]
        }
    
    def get_category_progress(self, user_id, category):
        """Get progress in a specific category"""
        user_data = self.get_user_achievements(user_id)
        category_achievements = self.get_achievements_by_category(category)
        
        total = len(category_achievements)
        unlocked = sum(1 for ach_id in category_achievements.keys() if ach_id in user_data["unlocked"])
        percentage = (unlocked / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "unlocked": unlocked,
            "percentage": percentage
        }

class AchievementView(View):
    def __init__(self, ctx, manager, user):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.manager = manager
        self.user = user
        self.current_category = "all"
        
        # Add category selector
        options = [
            discord.SelectOption(label="All Achievements", value="all", emoji="🏆"),
            discord.SelectOption(label="Economy", value="Economy", emoji="💰"),
            discord.SelectOption(label="Gambling", value="Gambling", emoji="🎰"),
            discord.SelectOption(label="Gaming", value="Gaming", emoji="🎮"),
            discord.SelectOption(label="TCG", value="TCG", emoji="⚔️"),
            discord.SelectOption(label="Social", value="Social", emoji="💖"),
            discord.SelectOption(label="Fishing", value="Fishing", emoji="🎣"),
            discord.SelectOption(label="Quests", value="Quests", emoji="📜"),
            discord.SelectOption(label="Events", value="Events", emoji="🎉"),
            discord.SelectOption(label="Board Games", value="Board Games", emoji="🎯"),
            discord.SelectOption(label="Milestones", value="Milestones", emoji="⚡"),
        ]
        
        select = Select(placeholder="Choose a category", options=options)
        select.callback = self.category_callback
        self.add_item(select)
    
    async def category_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            return
        
        self.current_category = interaction.data['values'][0]
        embed = self._create_embed()
        await interaction.response.edit_message(embed=embed)
    
    def _create_embed(self):
        """Create achievement embed for current category"""
        user_data = self.manager.get_user_achievements(self.user.id)
        
        if self.current_category == "all":
            # Overview page
            progress = self.manager.get_user_progress(self.user.id)
            progress_bar = EmbedBuilder.progress_bar(progress['percentage'], 15)
            
            embed = EmbedBuilder.create(
                title=f"{Emojis.TROPHY} {self.user.display_name}'s Achievements",
                description=f"**Progress:** {progress_bar}\n"
                           f"**{progress['unlocked']}/{progress['total']}** unlocked ({progress['percentage']:.1f}%)\n"
                           f"**{progress['points']} Achievement Points**\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━",
                color=Colors.WARNING
            )
            
            # Show category breakdown
            categories = ["Economy", "Gambling", "Gaming", "TCG", "Social", "Fishing", "Quests", "Events", "Board Games", "Milestones"]
            
            for category in categories:
                cat_progress = self.manager.get_category_progress(self.user.id, category)
                cat_bar = EmbedBuilder.progress_bar(cat_progress['percentage'], 8)
                
                embed.add_field(
                    name=f"{self._get_category_emoji(category)} {category}",
                    value=f"{cat_bar} {cat_progress['unlocked']}/{cat_progress['total']}",
                    inline=True
                )
            
            # Show most recent unlocks
            recent = sorted(user_data.get("unlocked_at", {}).items(), key=lambda x: x[1], reverse=True)[:5]
            if recent:
                recent_text = ""
                for ach_id, timestamp in recent:
                    if ach_id in self.manager.achievements:
                        ach = self.manager.achievements[ach_id]
                        recent_text += f"{ach['emoji']} **{ach['name']}**\n"
                
                embed.add_field(
                    name=f"{Emojis.SPARKLES} Recent Unlocks",
                    value=recent_text,
                    inline=False
                )
        
        else:
            # Category page
            category_achievements = self.manager.get_achievements_by_category(self.current_category)
            cat_progress = self.manager.get_category_progress(self.user.id, self.current_category)
            progress_bar = EmbedBuilder.progress_bar(cat_progress['percentage'], 15)
            
            embed = EmbedBuilder.create(
                title=f"{self._get_category_emoji(self.current_category)} {self.current_category} Achievements",
                description=f"**Progress:** {progress_bar}\n"
                           f"**{cat_progress['unlocked']}/{cat_progress['total']}** unlocked\n\n",
                color=Colors.PRIMARY
            )
            
            # Show achievements (max 25 fields)
            count = 0
            for ach_id, ach in list(category_achievements.items())[:25]:
                unlocked = ach_id in user_data["unlocked"]
                status = "✅" if unlocked else "🔒"
                
                value = f"{ach['description']}\n"
                value += f"💰 Reward: {ach['reward']} coins • {ach['points']} pts"
                
                embed.add_field(
                    name=f"{status} {ach['emoji']} {ach['name']}",
                    value=value,
                    inline=False
                )
                count += 1
        
        embed.set_thumbnail(url=self.user.display_avatar.url)
        embed.set_footer(text="Use the dropdown to switch categories!")
        
        return embed
    
    def _get_category_emoji(self, category):
        emojis = {
            "Economy": "💰",
            "Gambling": "🎰",
            "Gaming": "🎮",
            "TCG": "⚔️",
            "Social": "💖",
            "Fishing": "🎣",
            "Quests": "📜",
            "Events": "🎉",
            "Board Games": "🎯",
            "Milestones": "⚡"
        }
        return emojis.get(category, "🏆")

class Achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = AchievementManager(data_dir)
        
    
    async def _send_achievement_notification(self, ctx, achievement):
        """Send achievement unlock notification"""
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Achievement Unlocked!",
            description=f"**{achievement['emoji']} {achievement['name']}**\n"
                       f"*{achievement['description']}*\n\n"
                       f"💰 Reward: **{achievement['reward']} PsyCoins**\n"
                       f"⭐ Points: **+{achievement['points']}**",
            color=Colors.WARNING
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="myachievements", aliases=["ach", "achieve", "mych"])
    async def achievements_command(self, ctx, user: discord.User = None):
        """View your achievements"""
        target = user or ctx.author
        
        view = AchievementView(ctx, self.manager, target)
        embed = view._create_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="achievements", description="View your achievements")
    async def achievements_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Slash command for achievements"""
        await interaction.response.defer()
        
        target = user or interaction.user
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
        
        fake_ctx = FakeContext(interaction)
        view = AchievementView(fake_ctx, self.manager, target)
        embed = view._create_embed()
        
        await interaction.followup.send(embed=embed, view=view)
    
    @commands.command(name="achleaderboard", aliases=["achlb", "achtop"])
    async def leaderboard_command(self, ctx, category: str = "points"):
        """View achievement leaderboards"""
        all_users = self.manager.user_achievements
        
        if category.lower() in ["points", "pts", "achievement"]:
            # Sort by achievement points
            sorted_users = sorted(
                all_users.items(),
                key=lambda x: x[1].get("points", 0),
                reverse=True
            )[:10]
            
            embed = EmbedBuilder.create(
                title=f"{Emojis.TROPHY} Top Achievement Hunters",
                description="Users with the most achievement points!",
                color=Colors.WARNING
            )
            
            leaderboard_text = ""
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    points = data.get("points", 0)
                    unlocked = len(data.get("unlocked", []))
                    
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    leaderboard_text += f"{medal} {user.mention} - **{points} pts** ({unlocked} unlocked)\n"
                except:
                    continue
            
            embed.description += f"\n\n{leaderboard_text}"
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Achievements(bot))
