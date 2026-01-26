import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import time

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class ArcadeGames(commands.Cog):
    """Arcade-style games"""

    @app_commands.command(name="arcadehelp", description="View all arcade game commands and info (paginated)")
    async def arcadehelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Arcade Games"
        category_desc = "Play fast-paced arcade games! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
    
    @app_commands.command(name="arcade", description="Arcade games")
    @app_commands.choices(game=[
        app_commands.Choice(name="👻 PacMan", value="pacman"),
        app_commands.Choice(name="🧮 Math Game", value="mathgame"),
        app_commands.Choice(name="💣 Bomb Defuse", value="bombdefuse")
    ])
    async def arcade_command(self, interaction: discord.Interaction, game: app_commands.Choice[str]):
        """Unified arcade command with game dropdown"""
        game_value = game.value if isinstance(game, app_commands.Choice) else game
        
        if game_value == "pacman":
            await self.arcade_pacman_action(interaction)
        elif game_value == "mathgame":
            await self.arcade_mathgame_action(interaction)
        elif game_value == "bombdefuse":
            await self.arcade_bombdefuse_action(interaction)
    
    async def arcade_pacman_action(self, interaction: discord.Interaction):
        """PacMan game"""
        # 10x10 grid
        size = 10
        pac_pos = [5, 5]
        ghosts = [[1, 1], [8, 8], [1, 8]]
        pellets = [(i, j) for i in range(size) for j in range(size) if (i, j) not in [(5, 5)] + [(g[0], g[1]) for g in ghosts]]
        score = 0
        moves = 0
        max_moves = 50
        
        game_id = f"{interaction.guild.id}_{interaction.user.id}_pacman"
        self.active_games[game_id] = {
            "pac_pos": pac_pos,
            "ghosts": ghosts,
            "pellets": pellets,
            "score": score,
            "moves": moves
        }
        
        def render_game():
            game = self.active_games.get(game_id)
            if not game:
                return "Game ended"
            
            grid = [["⬛" for _ in range(size)] for _ in range(size)]
            
            # Place pellets
            for px, py in game["pellets"]:
                grid[px][py] = "🟡"
            
            # Place ghosts
            for gx, gy in game["ghosts"]:
                if 0 <= gx < size and 0 <= gy < size:
                    grid[gx][gy] = "👻"
            
            # Place PacMan
            px, py = game["pac_pos"]
            if 0 <= px < size and 0 <= py < size:
                grid[px][py] = "🟨"
            
            return "\n".join(["".join(row) for row in grid])
        
        embed = discord.Embed(
            title="👾 PacMan",
            description=f"{render_game()}\n\n"
                       f"Score: {score} | Moves: {moves}/{max_moves}\n\n"
                       "React: ⬆️ ⬇️ ⬛ ➡️ to move\n"
                       "Collect pellets 🟡 | Avoid ghosts 👻",
            color=discord.Color.yellow()
        )
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        for emoji in ["⬆️", "⬇️", "⬛", "➡️"]:
            await msg.add_reaction(emoji)
        
        def check(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) in ["⬆️", "⬇️", "⬛", "➡️"]
        
        while game_id in self.active_games:
            game = self.active_games[game_id]
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=60.0)
                
                # Move PacMan
                old_pos = game["pac_pos"].copy()
                if str(reaction.emoji) == "⬆️":
                    game["pac_pos"][0] = max(0, game["pac_pos"][0] - 1)
                elif str(reaction.emoji) == "⬇️":
                    game["pac_pos"][0] = min(size - 1, game["pac_pos"][0] + 1)
                elif str(reaction.emoji) == "⬛":
                    game["pac_pos"][1] = max(0, game["pac_pos"][1] - 1)
                elif str(reaction.emoji) == "➡️":
                    game["pac_pos"][1] = min(size - 1, game["pac_pos"][1] + 1)
                
                game["moves"] += 1
                
                # Check pellet collection
                pac_tuple = tuple(game["pac_pos"])
                if pac_tuple in game["pellets"]:
                    game["pellets"].remove(pac_tuple)
                    game["score"] += 10
                
                # Move ghosts randomly
                for ghost in game["ghosts"]:
                    direction = random.choice(["up", "down", "left", "right"])
                    if direction == "up":
                        ghost[0] = max(0, ghost[0] - 1)
                    elif direction == "down":
                        ghost[0] = min(size - 1, ghost[0] + 1)
                    elif direction == "left":
                        ghost[1] = max(0, ghost[1] - 1)
                    elif direction == "right":
                        ghost[1] = min(size - 1, ghost[1] + 1)
                
                # Check collision
                if game["pac_pos"] in game["ghosts"]:
                    embed = discord.Embed(
                        title="💀 Game Over!",
                        description=f"A ghost caught you!\n\nFinal Score: {game['score']}",
                        color=discord.Color.red()
                    )
                    await msg.edit(embed=embed)
                    # Chance to award a difficult TCG card for arcade win
                    if tcg_manager:
                        try:
                            awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'difficult')
                            if awarded:
                                names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                                await msg.channel.send(f"🎴 Bonus TCG reward: {', '.join(names)}")
                        except Exception:
                            pass
                    del self.active_games[game_id]
                    break
                
                # Check win
                if not game["pellets"] or game["moves"] >= max_moves:
                    reward = game["score"] * 2
                    embed = discord.Embed(
                        title="🎉 Game Complete!" if not game["pellets"] else "⏰ Time's Up!",
                        description=f"Final Score: {game['score']}\n\n**+{reward} PsyCoins!** 🪙",
                        color=discord.Color.gold()
                    )
                    await msg.edit(embed=embed)
                    del self.active_games[game_id]
                    break
                
                # Update display
                embed = discord.Embed(
                    title="👾 PacMan",
                    description=f"{render_game()}\n\n"
                               f"Score: {game['score']} | Moves: {game['moves']}/{max_moves}\n\n"
                               "React to move!",
                    color=discord.Color.yellow()
                )
                await msg.edit(embed=embed)
                await msg.remove_reaction(reaction, user)
                
            except asyncio.TimeoutError:
                if game_id in self.active_games:
                    embed = discord.Embed(
                        title="⏰ Game Timeout",
                        description=f"Final Score: {game['score']}",
                        color=discord.Color.orange()
                    )
                    await msg.edit(embed=embed)
                    del self.active_games[game_id]
                break
    
    @app_commands.describe(difficulty="Easy, Medium, or Hard")
    async def arcade_mathgame_action(self, interaction: discord.Interaction, difficulty: str = "medium"):
        """Math game challenges"""
        difficulties = {
            "easy": (1, 20, ["+", "-"], 10),
            "medium": (10, 100, ["+", "-", "*"], 15),
            "hard": (20, 200, ["+", "-", "*", "//"], 20)
        }
        
        if difficulty.lower() not in difficulties:
            await interaction.response.send_message("❌ Choose: easy, medium, or hard", ephemeral=True)
            return
        
        min_val, max_val, operations, num_questions = difficulties[difficulty.lower()]
        
        score = 0
        start_time = time.time()
        
        embed = discord.Embed(
            title="🧮 Math Game",
            description=f"**{num_questions} questions** | {difficulty.title()} difficulty\n\nGet ready!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(2)
        
        for i in range(num_questions):
            a = random.randint(min_val, max_val)
            b = random.randint(min_val, max_val)
            op = random.choice(operations)
            
            if op == "+":
                answer = a + b
                question = f"{a} + {b}"
            elif op == "-":
                answer = a - b
                question = f"{a} - {b}"
            elif op == "*":
                answer = a * b
                question = f"{a} × {b}"
            else:  # //
                b = max(1, b)  # Avoid division by zero
                answer = a // b
                question = f"{a} ÷ {b}"
            
            embed = discord.Embed(
                title=f"🧮 Question {i + 1}/{num_questions}",
                description=f"**{question} = ?**\n\nType your answer!",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=embed)
            
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                
                try:
                    user_answer = int(msg.content)
                    if user_answer == answer:
                        score += 10
                        await msg.add_reaction("✅")
                    else:
                        await msg.add_reaction("❌")
                        await msg.reply(f"Correct answer: {answer}")
                except ValueError:
                    await msg.add_reaction("❌")
                    
            except asyncio.TimeoutError:
                await interaction.followup.send(f"⏰ Time's up! Answer: {answer}")
        
        elapsed = time.time() - start_time
        reward = int(score * (1 + (num_questions * 10 - elapsed) / 100))
        
        embed = discord.Embed(
            title="🎉 Math Game Complete!",
            description=f"**Score: {score}/{num_questions * 10}**\n"
                       f"Time: {elapsed:.1f}s\n\n"
                       f"**+{reward} PsyCoins!** 🪙",
            color=discord.Color.gold()
        )
        await interaction.edit_original_response(embed=embed)
        # Chance to award a difficult TCG card for math-game completion
        if tcg_manager:
            try:
                awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'difficult')
                if awarded:
                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                    await interaction.followup.send(f"🎴 Bonus TCG reward: {', '.join(names)}")
            except Exception:
                pass
    
    async def arcade_bombdefuse_action(self, interaction: discord.Interaction):
        """Bomb defuser game"""
        wires = ["🔴", "🔵", "🟢", "🟡", "⚪", "🟠"]
        num_wires = random.randint(4, 6)
        bomb_wires = random.sample(wires, num_wires)
        correct_wire = random.choice(bomb_wires)
        
        # Generate clues
        clues = []
        if correct_wire in ["🔴", "🟠"]:
            clues.append("The correct wire is a warm color")
        else:
            clues.append("The correct wire is a cool color")
        
        if bomb_wires.index(correct_wire) < len(bomb_wires) // 2:
            clues.append("Cut one of the first wires")
        else:
            clues.append("Cut one of the last wires")
        
        game_id = f"{interaction.guild.id}_{interaction.user.id}_bomb"
        self.active_games[game_id] = {
            "wires": bomb_wires,
            "correct": correct_wire,
            "attempts": 3,
            "clues_shown": 1
        }
        
        wire_display = " ".join([f"{i+1}️⃣ {w}" for i, w in enumerate(bomb_wires)])
        
        embed = discord.Embed(
            title="💣 BOMB DEFUSAL",
            description=f"**⏰ BOMB ACTIVE ⏰**\n\n"
                       f"{wire_display}\n\n"
                       f"**Clue:** {clues[0]}\n\n"
                       f"Cut the correct wire!\n"
                       f"Type the wire number (1-{num_wires})\n\n"
                       f"**Attempts: 3** | React 🔍 for another clue",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🔍")
        
        def check_reaction(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) == "🔍"
        
        def check_message(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        while game_id in self.active_games:
            game = self.active_games[game_id]
            
            done, pending = await asyncio.wait([
                asyncio.create_task(self.bot.wait_for('reaction_add', check=check_reaction, timeout=45.0)),
                asyncio.create_task(self.bot.wait_for('message', check=check_message, timeout=45.0))
            ], return_when=asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()
            
            try:
                result = done.pop().result()
                
                if isinstance(result, tuple):  # Reaction - show clue
                    if game["clues_shown"] < len(clues):
                        await interaction.followup.send(f"🔍 **Clue:** {clues[game['clues_shown']]}")
                        game["clues_shown"] += 1
                    else:
                        await interaction.followup.send("🔍 No more clues!")
                
                else:  # Message - wire cut attempt
                    try:
                        choice = int(result.content)
                        if 1 <= choice <= len(game["wires"]):
                            chosen_wire = game["wires"][choice - 1]
                            
                            if chosen_wire == game["correct"]:
                                reward = game["attempts"] * 200
                                embed = discord.Embed(
                                    title="✅ BOMB DEFUSED!",
                                    description=f"You cut the {chosen_wire} wire!\n\n"
                                               f"**+{reward} PsyCoins!** 🪙",
                                    color=discord.Color.green()
                                )
                                await result.reply(embed=embed)
                                # Chance to award a difficult TCG card for bomb defuse win
                                if tcg_manager:
                                    try:
                                        awarded = tcg_manager.award_for_game_event(str(result.author.id), 'difficult')
                                        if awarded:
                                            names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                                            await result.reply(f"🎴 Bonus TCG reward: {', '.join(names)}")
                                    except Exception:
                                        pass
                                del self.active_games[game_id]
                                break
                            else:
                                game["attempts"] -= 1
                                if game["attempts"] <= 0:
                                    embed = discord.Embed(
                                        title="💥 BOOM!",
                                        description=f"The bomb exploded!\n\n"
                                                   f"Correct wire was {game['correct']}",
                                        color=discord.Color.dark_red()
                                    )
                                    await result.reply(embed=embed)
                                    del self.active_games[game_id]
                                    break
                                else:
                                    await result.reply(f"❌ Wrong wire! **{game['attempts']} attempts left!**")
                        else:
                            await result.reply(f"❌ Choose 1-{len(game['wires'])}")
                    except ValueError:
                        await result.reply("❌ Type a number!")
            
            except asyncio.TimeoutError:
                if game_id in self.active_games:
                    embed = discord.Embed(
                        title="💥 TIMEOUT - BOOM!",
                        description=f"You ran out of time!\n\nCorrect wire: {game['correct']}",
                        color=discord.Color.dark_red()
                    )
                    await interaction.followup.send(embed=embed)
                    del self.active_games[game_id]
                break

async def setup(bot):
    await bot.add_cog(ArcadeGames(bot))
