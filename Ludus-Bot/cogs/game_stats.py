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

class GameStatsView(View):
    def __init__(self, ctx, stats_cog):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.stats_cog = stats_cog
        self.current_page = "overview"
    
    @discord.ui.button(label="Overview", style=discord.ButtonStyle.primary, emoji="📊")
    async def overview_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't your stats page!", ephemeral=True)
            return
        self.current_page = "overview"
        embed = self.stats_cog._create_overview_embed(self.ctx.author)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Game Records", style=discord.ButtonStyle.success, emoji="🏆")
    async def records_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't your stats page!", ephemeral=True)
            return
        self.current_page = "records"
        embed = self.stats_cog._create_records_embed(self.ctx.author)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Achievements", style=discord.ButtonStyle.primary, emoji="⭐")
    async def achievements_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't your stats page!", ephemeral=True)
            return
        self.current_page = "achievements"
        embed = self.stats_cog._create_achievements_embed(self.ctx.author)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Streaks", style=discord.ButtonStyle.danger, emoji="🔥")
    async def streaks_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("This isn't your stats page!", ephemeral=True)
            return
        self.current_page = "streaks"
        embed = self.stats_cog._create_streaks_embed(self.ctx.author)
        await interaction.response.edit_message(embed=embed, view=self)

class GameStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = os.getenv("RENDER_DISK_PATH", "data")
        self.stats_file = os.path.join(self.data_dir, "game_stats.json")
        self.stats = self._load_stats()
    
    def _load_stats(self):
        """Load game statistics"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_stats(self):
        """Save game statistics"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def _get_user_stats(self, user_id):
        """Get stats for a user"""
        user_id = str(user_id)
        if user_id not in self.stats:
            self.stats[user_id] = {
                "total_games": 0,
                "games_won": 0,
                "games_lost": 0,
                "total_coins_earned": 0,
                "favorite_game": None,
                "game_counts": {},
                "total_playtime_minutes": 0,
                "achievements_unlocked": 0,
                "perfect_games": 0,
                "comeback_wins": 0,
                "speedrun_wins": 0,
                "first_game_date": datetime.now().strftime("%Y-%m-%d"),
                "last_game_date": datetime.now().strftime("%Y-%m-%d"),
                "daily_streak": 0,
                "best_daily_streak": 0,
                "categories": {
                    "word_games": 0,
                    "math_games": 0,
                    "board_games": 0,
                    "puzzle_games": 0,
                    "trivia_games": 0,
                    "speed_games": 0,
                    "memory_games": 0,
                    "strategy_games": 0
                }
            }
        return self.stats[user_id]
    
    def record_game(self, user_id, game_name, won=True, coins_earned=0, playtime_seconds=0, category=None, guild_id=None):
        """Record a game play"""
        stats = self._get_user_stats(user_id)
        
        stats["total_games"] += 1
        if won:
            stats["games_won"] += 1
        else:
            stats["games_lost"] += 1
        
        stats["total_coins_earned"] += coins_earned
        stats["total_playtime_minutes"] += playtime_seconds / 60
        stats["last_game_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Track game counts
        if game_name not in stats["game_counts"]:
            stats["game_counts"][game_name] = 0
        stats["game_counts"][game_name] += 1
        
        # Track per-guild stats if guild_id provided
        if guild_id:
            if "guild_stats" not in stats:
                stats["guild_stats"] = {}
            guild_key = str(guild_id)
            if guild_key not in stats["guild_stats"]:
                stats["guild_stats"][guild_key] = {
                    "total_games": 0,
                    "games_won": 0,
                    "game_counts": {}
                }
            stats["guild_stats"][guild_key]["total_games"] += 1
            if won:
                stats["guild_stats"][guild_key]["games_won"] += 1
            if game_name not in stats["guild_stats"][guild_key]["game_counts"]:
                stats["guild_stats"][guild_key]["game_counts"][game_name] = 0
            stats["guild_stats"][guild_key]["game_counts"][game_name] += 1
        
        # Update favorite game
        if stats["game_counts"]:
            stats["favorite_game"] = max(stats["game_counts"], key=stats["game_counts"].get)
        
        # Track categories
        if category and category in stats["categories"]:
            stats["categories"][category] += 1
        
        self._save_stats()
    
    def _create_overview_embed(self, user):
        """Create overview embed"""
        stats = self._get_user_stats(user.id)
        
        win_rate = (stats["games_won"] / stats["total_games"] * 100) if stats["total_games"] > 0 else 0
        avg_coins = stats["total_coins_earned"] / stats["total_games"] if stats["total_games"] > 0 else 0
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.CHART} {user.display_name}'s Game Statistics",
            description=f"**Complete gaming overview**\\n\\n",
            color=Colors.PRIMARY
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="📊 Overall Stats",
            value=f"🎮 Total Games: **{stats['total_games']}**\\n"
                  f"✅ Wins: **{stats['games_won']}**\\n"
                  f"❌ Losses: **{stats['games_lost']}**\\n"
                  f"📈 Win Rate: **{win_rate:.1f}%**\\n"
                  f"⏱️ Playtime: **{int(stats['total_playtime_minutes'])}** min",
            inline=True
        )
        
        embed.add_field(
            name="💰 Earnings",
            value=f"💎 Total Earned: **{stats['total_coins_earned']}** {Emojis.COIN}\\n"
                  f"📊 Avg per Game: **{int(avg_coins)}** {Emojis.COIN}\\n"
                  f"🎯 Best Game: **{stats.get('favorite_game', 'None')}**",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Achievements",
            value=f"⭐ Unlocked: **{stats['achievements_unlocked']}**/200+\\n"
                  f"💯 Perfect Games: **{stats['perfect_games']}**\\n"
                  f"⚡ Speedruns: **{stats['speedrun_wins']}**\\n"
                  f"🔄 Comebacks: **{stats['comeback_wins']}**",
            inline=True
        )
        
        # Category breakdown
        categories_text = ""
        for category, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)[:5]:
            bar_length = min(int(count / 10), 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)
            categories_text += f"{category.replace('_', ' ').title()}: {bar} {count}\\n"
        
        embed.add_field(
            name="📂 Game Categories",
            value=categories_text or "No games played yet!",
            inline=False
        )
        
        embed.add_field(
            name="📅 Activity",
            value=f"First Game: {stats['first_game_date']}\\n"
                  f"Last Game: {stats['last_game_date']}\\n"
                  f"Daily Streak: {stats['daily_streak']} days (Best: {stats['best_daily_streak']})",
            inline=False
        )
        
        embed.set_footer(text="Use buttons to view more detailed stats!")
        return embed
    
    def _create_records_embed(self, user):
        """Create records embed"""
        stats = self._get_user_stats(user.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} {user.display_name}'s Game Records",
            description=f"**Your top games and achievements**\\n\\n",
            color=Colors.WARNING
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Top games by play count
        if stats["game_counts"]:
            top_games = sorted(stats["game_counts"].items(), key=lambda x: x[1], reverse=True)[:10]
            games_text = ""
            for i, (game, count) in enumerate(top_games, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                games_text += f"{medal} **{game.title()}** - {count} plays\\n"
            
            embed.add_field(
                name="🎮 Most Played Games",
                value=games_text,
                inline=False
            )
        
        # Special achievements
        embed.add_field(
            name="🏆 Special Records",
            value=f"💯 Perfect Games: **{stats['perfect_games']}**\\n"
                  f"⚡ Speed Victories: **{stats['speedrun_wins']}**\\n"
                  f"🔄 Comeback Wins: **{stats['comeback_wins']}**\\n"
                  f"🔥 Best Win Streak: *Check /streak!*",
            inline=True
        )
        
        # Milestones
        milestones_text = ""
        if stats["total_games"] >= 100:
            milestones_text += "✅ Century Player (100 games)\\n"
        if stats["total_games"] >= 500:
            milestones_text += "✅ Veteran (500 games)\\n"
        if stats["total_games"] >= 1000:
            milestones_text += "✅ Legend (1000 games)\\n"
        if stats["games_won"] >= 50:
            milestones_text += "✅ Champion (50 wins)\\n"
        if stats["total_coins_earned"] >= 10000:
            milestones_text += "✅ Wealthy (10k coins earned)\\n"
        
        embed.add_field(
            name="🎯 Milestones Unlocked",
            value=milestones_text or "Keep playing to unlock milestones!",
            inline=True
        )
        
        embed.set_footer(text="Keep playing to set new records!")
        return embed
    
    def _create_achievements_embed(self, user):
        """Create achievements embed"""
        stats = self._get_user_stats(user.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.STAR} {user.display_name}'s Game Achievements",
            description=f"**Special accomplishments**\\n\\n",
            color=Colors.SUCCESS
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Calculate achievement progress (UI only)
        total_possible = 200
        unlocked = stats.get("achievements_unlocked", 0)
        progress = (unlocked / total_possible * 100) if total_possible > 0 else 0

        bar_length = int(progress / 10)
        progress_bar = "█" * bar_length + "░" * (10 - bar_length)

        embed.add_field(
            name="📊 Overall Progress",
            value=f"{progress_bar} **{progress:.1f}%**\\n"
                  f"Unlocked: **{unlocked}/{total_possible}**\\n"
                  f"Check `L!achievements` for full list!",
            inline=False
        )

        # Achievement categories (collection/crafting focused)
        embed.add_field(
            name="🃏 TCG Achievements",
            value=f"Cards Collected: {stats.get('total_games', 0)}/1000\\n"
                  f"Unique Cards: {stats.get('games_won', 0)}/500\\n"
                  f"Cards Crafted: {stats.get('perfect_games', 0)}/50",
            inline=True
        )

        embed.add_field(
            name="💰 Economy Achievements",
            value=f"Coins Earned: {stats.get('total_coins_earned', 0)}/100000\\n"
                  f"Check your profile for more!\\n"
                  f"Use `L!achievements` for details",
            inline=True
        )

        embed.add_field(
            name="🔥 Rare Achievements",
            value=f"📚 Collector Milestone: {stats.get('speedrun_wins', 0)}/25\\n"
                  f"🔨 Master Crafter: {stats.get('comeback_wins', 0)}/10\\n"
                  f"🔀 Fusion Master: {stats.get('perfect_games', 0)}/50",
            inline=False
        )

        embed.set_footer(text="Unlock achievements by collecting, crafting, and trading cards!")
        return embed
    
    def _create_streaks_embed(self, user):
        """Create streaks embed"""
        stats = self._get_user_stats(user.id)
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.FIRE} {user.display_name}'s Streaks",
            description=f"**Consistency tracking**\\n\\n",
            color=Colors.DANGER
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="📅 Daily Activity",
            value=f"Current Streak: **{stats['daily_streak']}** days\\n"
                  f"Best Streak: **{stats['best_daily_streak']}** days\\n"
                  f"Last Played: {stats['last_game_date']}",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Play Frequency",
            value=f"Total Games: {stats['total_games']}\\n"
                  f"Avg per Session: *Coming soon*\\n"
                  f"Most Active: *Coming soon*",
            inline=True
        )
        
        # Streak rewards
        embed.add_field(
            name="🎁 Streak Bonuses",
            value=f"✨ 7 day streak = 1.5x coins\\n"
                  f"💎 14 day streak = 2x coins\\n"
                  f"👑 30 day streak = 3x coins + title!\\n\\n"
                  f"**Check `L!streak` for win streaks!**",
            inline=False
        )
        
        embed.set_footer(text="Play daily to build your streak!")
        return embed
    
    @commands.command(name="gamestats", aliases=["mystats"])
    async def game_stats(self, ctx):
        """View your complete game statistics"""
        view = GameStatsView(ctx, self)
        embed = self._create_overview_embed(ctx.author)
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="gamestats", description="View your complete game statistics")
    async def gamestats_slash(self, interaction: discord.Interaction):
        """Slash command for game stats"""
        await interaction.response.defer()
        
        class FakeContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.followup.send
        
        fake_ctx = FakeContext(interaction)
        view = GameStatsView(fake_ctx, self)
        embed = self._create_overview_embed(interaction.user)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(GameStats(bot))
