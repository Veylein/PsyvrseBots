import discord
from discord.ext import commands
from discord import app_commands

class GameControl(commands.Cog):
    """Universal game control commands - stop any active game"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="stop")
    async def stop_prefix(self, ctx):
        """Stop any active game you're in"""
        await ctx.send("🛑 Attempting to stop your active games...")
        
        stopped = []
        
        # Check cardgames cog for UNO/Go-Fish
        cardgames_cog = self.bot.get_cog("CardGames")
        if cardgames_cog:
            if hasattr(cardgames_cog, 'active_games'):
                for game_id, game in list(cardgames_cog.active_games.items()):
                    if ctx.author.id in game.get('players', []):
                        del cardgames_cog.active_games[game_id]
                        stopped.append("UNO/Card Game")
        
        # Check fishing_fun for akinator
        fishing_cog = self.bot.get_cog("FishingAkinatorFun")
        if fishing_cog:
            if hasattr(fishing_cog, 'active_akinator'):
                if str(ctx.author.id) in fishing_cog.active_akinator:
                    del fishing_cog.active_akinator[str(ctx.author.id)]
                    stopped.append("Akinator")
            
            if hasattr(fishing_cog, 'active_drawings'):
                if ctx.channel.id in fishing_cog.active_drawings:
                    if fishing_cog.active_drawings[ctx.channel.id]['artist'] == ctx.author.id:
                        del fishing_cog.active_drawings[ctx.channel.id]
                        stopped.append("Drawing Game")
        
        # Check minigames for wordle/etc
        minigames_cog = self.bot.get_cog("MiniGames")
        if minigames_cog:
            if hasattr(minigames_cog, 'active_wordle'):
                if str(ctx.author.id) in minigames_cog.active_wordle:
                    del minigames_cog.active_wordle[str(ctx.author.id)]
                    stopped.append("Wordle")
            
            if hasattr(minigames_cog, 'active_trivia'):
                if ctx.channel.id in minigames_cog.active_trivia:
                    del minigames_cog.active_trivia[ctx.channel.id]
                    stopped.append("Trivia")
        
        # Check board games
        boardgames_cog = self.bot.get_cog("BoardGames")
        if boardgames_cog:
            if hasattr(boardgames_cog, 'active_games'):
                for game_id, game in list(boardgames_cog.active_games.items()):
                    if ctx.author.id in game.get('players', []):
                        del boardgames_cog.active_games[game_id]
                        stopped.append("Board Game")
        
        if stopped:
            await ctx.send(f"✅ Stopped: {', '.join(set(stopped))}")
        else:
            await ctx.send("❌ You don't have any active games running!")
    
    @app_commands.command(name="stop", description="Stop any active game you're in")
    async def stop_slash(self, interaction: discord.Interaction):
        """Stop any active game you're in"""
        await interaction.response.send_message("🛑 Attempting to stop your active games...")
        
        stopped = []
        
        # Check cardgames cog for UNO/Go-Fish
        cardgames_cog = self.bot.get_cog("CardGames")
        if cardgames_cog:
            if hasattr(cardgames_cog, 'active_games'):
                for game_id, game in list(cardgames_cog.active_games.items()):
                    if interaction.user.id in game.get('players', []):
                        del cardgames_cog.active_games[game_id]
                        stopped.append("UNO/Card Game")
        
        # Check fishing_fun for akinator
        fishing_cog = self.bot.get_cog("FishingAkinatorFun")
        if fishing_cog:
            if hasattr(fishing_cog, 'active_akinator'):
                if str(interaction.user.id) in fishing_cog.active_akinator:
                    del fishing_cog.active_akinator[str(interaction.user.id)]
                    stopped.append("Akinator")
            
            if hasattr(fishing_cog, 'active_drawings'):
                if interaction.channel.id in fishing_cog.active_drawings:
                    if fishing_cog.active_drawings[interaction.channel.id]['artist'] == interaction.user.id:
                        del fishing_cog.active_drawings[interaction.channel.id]
                        stopped.append("Drawing Game")
        
        # Check minigames for wordle/etc
        minigames_cog = self.bot.get_cog("MiniGames")
        if minigames_cog:
            if hasattr(minigames_cog, 'active_wordle'):
                if str(interaction.user.id) in minigames_cog.active_wordle:
                    del minigames_cog.active_wordle[str(interaction.user.id)]
                    stopped.append("Wordle")
            
            if hasattr(minigames_cog, 'active_trivia'):
                if interaction.channel.id in minigames_cog.active_trivia:
                    del minigames_cog.active_trivia[interaction.channel.id]
                    stopped.append("Trivia")
        
        # Check board games
        boardgames_cog = self.bot.get_cog("BoardGames")
        if boardgames_cog:
            if hasattr(boardgames_cog, 'active_games'):
                for game_id, game in list(boardgames_cog.active_games.items()):
                    if interaction.user.id in game.get('players', []):
                        del boardgames_cog.active_games[game_id]
                        stopped.append("Board Game")
        
        if stopped:
            await interaction.followup.send(f"✅ Stopped: {', '.join(set(stopped))}")
        else:
            await interaction.followup.send("❌ You don't have any active games running!")

async def setup(bot):
    await bot.add_cog(GameControl(bot))
