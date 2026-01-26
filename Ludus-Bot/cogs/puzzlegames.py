import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class PuzzleGames(commands.Cog):
    """Puzzle and mystery games"""

    @app_commands.command(name="puzzleshelp", description="View all puzzle game commands and info (paginated)")
    async def puzzleshelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Puzzles"
        category_desc = "Solve challenging puzzles! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        
    # Command for puzzle games
    @app_commands.command(name="game", description="Puzzle and mystery games")
    @app_commands.choices(game=[
        app_commands.Choice(name="💣 Minesweeper", value="minesweeper"),
        app_commands.Choice(name="🧠 Memory Grid", value="memory"),
        app_commands.Choice(name="🔢 Code Breaker", value="codebreaker"),
        app_commands.Choice(name="🔍 Detective Mystery", value="detective")
    ])
    @app_commands.describe(difficulty="Game difficulty: easy, medium, or hard")
    async def game_command(self, interaction: discord.Interaction, game: app_commands.Choice[str], difficulty: str = "medium"):
        """Unified game command with game dropdown"""
        game_value = game.value if isinstance(game, app_commands.Choice) else game
        
        if game_value == "minesweeper":
            await self.game_minesweeper_action(interaction, difficulty)
        elif game_value == "memory":
            await self.game_memory_action(interaction, difficulty)
        elif game_value == "codebreaker":
            await self.game_codebreaker_action(interaction, difficulty)
        elif game_value == "detective":
            await self.game_detective_action(interaction)
    
    @app_commands.describe(difficulty="Easy (8x8, 10 mines), Medium (12x12, 20 mines), Hard (16x16, 40 mines)")
    async def game_minesweeper_action(self, interaction: discord.Interaction, difficulty: str = "medium"):
        """Play Minesweeper"""
        difficulties = {
            "easy": (8, 8, 10),
            "medium": (12, 12, 20),
            "hard": (16, 16, 40)
        }
        
        if difficulty.lower() not in difficulties:
            await interaction.response.send_message("❌ Choose: easy, medium, or hard", ephemeral=True)
            return
        
        rows, cols, mines = difficulties[difficulty.lower()]
        
        # Generate board
        board = [[0 for _ in range(cols)] for _ in range(rows)]
        mine_positions = set()
        
        # Place mines
        while len(mine_positions) < mines:
            r, c = random.randint(0, rows-1), random.randint(0, cols-1)
            mine_positions.add((r, c))
        
        for r, c in mine_positions:
            board[r][c] = -1
        
        # Calculate numbers
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == -1:
                            count += 1
                board[r][c] = count
        
        # Create spoiler board
        lines = []
        for row in board:
            line = ""
            for cell in row:
                if cell == -1:
                    line += "||💣||"
                elif cell == 0:
                    line += "||⬜||"
                else:
                    line += f"||{cell}️⃣||"
            lines.append(line)
        
        embed = discord.Embed(
            title=f"💣 Minesweeper - {difficulty.title()}",
            description=f"**{mines} mines hidden!**\n\nClick tiles to reveal. Don't hit a mine!\n\n" + "\n".join(lines),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Good luck, {interaction.user.name}!")
        
        await interaction.response.send_message(embed=embed)
    
    async def game_memory_action(self, interaction: discord.Interaction, difficulty: str = "medium"):
        """Memory Grid game"""
        emojis = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚫", "⚪", "🟤"]
        
        # Generate 3x3 grid
        grid = [random.choice(emojis) for _ in range(9)]
        
        # Show grid
        grid_display = ""
        for i in range(3):
            grid_display += " ".join(grid[i*3:(i+1)*3]) + "\n"
        
        embed = discord.Embed(
            title="🧠 Memory Grid",
            description=f"**Remember this pattern!**\n\n{grid_display}\n\n*Memorizing... (5 seconds)*",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        
        # Hide grid
        hidden_display = ""
        for i in range(3):
            hidden_display += "⬛ ⬛ ⬛\n"
        
        # Store game
        game_id = f"{interaction.guild.id}_{interaction.user.id}"
        self.active_games[game_id] = {
            "type": "memory",
            "grid": grid,
            "user": interaction.user.id
        }
        
        embed = discord.Embed(
            title="🧠 Memory Grid",
            description=f"**What was the pattern?**\n\n{hidden_display}\n\nType the 9 emojis in order (no spaces)\nExample: 🔴🔵🟢🟡🟣🟠⚫⚪🟤",
            color=discord.Color.gold()
        )
        
        await interaction.edit_original_response(embed=embed)
        
        # Wait for answer
        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            user_answer = msg.content.replace(" ", "")
            correct_answer = "".join(grid)
            
            if user_answer == correct_answer:
                reward = random.randint(100, 300)
                # Add coins (you'll need economy integration)
                embed = discord.Embed(
                    title="✅ PERFECT MEMORY!",
                    description=f"You remembered the pattern correctly!\n\n{grid_display}\n\n**+{reward} PsyCoins!** 🪙",
                    color=discord.Color.green()
                )
                # Chance to award a mythic TCG card for puzzle win
                if tcg_manager:
                    try:
                        awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'mythic')
                        if awarded:
                            names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                            embed.add_field(name='🎴 Bonus Card', value=', '.join(names), inline=False)
                    except Exception:
                        pass
            else:
                embed = discord.Embed(
                    title="❌ Wrong Pattern!",
                    description=f"**Correct:**\n{grid_display}\n\n**You typed:**\n{user_answer}\n\nBetter luck next time!",
                    color=discord.Color.red()
                )
            
            await msg.reply(embed=embed)
            del self.active_games[game_id]
            
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You ran out of time!\n\n**Correct pattern:**\n{grid_display}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            del self.active_games[game_id]
    
    @app_commands.describe(difficulty="Easy (3 digits), Medium (4 digits), Hard (5 digits)")
    async def game_codebreaker_action(self, interaction: discord.Interaction, difficulty: str = "medium"):
        """Code Breaker game"""
        difficulties = {
            "easy": 3,
            "medium": 4,
            "hard": 5
        }
        
        if difficulty.lower() not in difficulties:
            await interaction.response.send_message("❌ Choose: easy, medium, or hard", ephemeral=True)
            return
        
        code_length = difficulties[difficulty.lower()]
        secret_code = [random.randint(0, 9) for _ in range(code_length)]
        
        game_id = f"{interaction.guild.id}_{interaction.user.id}_code"
        self.active_games[game_id] = {
            "type": "codebreaker",
            "code": secret_code,
            "attempts": 0,
            "max_attempts": 10,
            "user": interaction.user.id
        }
        
        # Generate hint
        hint_options = [
            f"The sum of all digits is {sum(secret_code)}",
            f"The first digit is {'even' if secret_code[0] % 2 == 0 else 'odd'}",
            f"The last digit is {'even' if secret_code[-1] % 2 == 0 else 'odd'}",
            f"The code contains the digit {random.choice(secret_code)}",
            f"The highest digit is {max(secret_code)}",
            f"The lowest digit is {min(secret_code)}"
        ]
        
        hint = random.choice(hint_options)
        
        embed = discord.Embed(
            title="🔐 Code Breaker",
            description=f"**Crack the {code_length}-digit code!**\n\n**Hint:** {hint}\n\n"
                       f"Type your guess (example: {'1234' if code_length == 4 else '123'})\n"
                       f"⚫ = Correct digit, wrong position\n"
                       f"🟢 = Correct digit, correct position\n\n"
                       f"**Attempts: 0/10**",
            color=discord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Wait for guesses
        while self.active_games.get(game_id):
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.content.isdigit()
            
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                guess = [int(d) for d in msg.content]
                
                if len(guess) != code_length:
                    await msg.reply(f"❌ Must be {code_length} digits!")
                    continue
                
                game_data = self.active_games[game_id]
                game_data["attempts"] += 1
                
                # Check guess
                feedback = []
                temp_code = secret_code.copy()
                temp_guess = guess.copy()
                
                # First pass: correct position
                for i in range(code_length):
                    if guess[i] == secret_code[i]:
                        feedback.append("🟢")
                        temp_code[i] = None
                        temp_guess[i] = None
                
                # Second pass: correct digit, wrong position
                for i in range(code_length):
                    if temp_guess[i] is not None and temp_guess[i] in temp_code:
                        feedback.append("⚫")
                        temp_code[temp_code.index(temp_guess[i])] = None
                
                feedback_str = " ".join(feedback) if feedback else "❌ No correct digits"
                
                if guess == secret_code:
                    reward = 500 - (game_data["attempts"] * 30)
                    embed = discord.Embed(
                        title="🎉 CODE CRACKED!",
                        description=f"**Secret Code:** {''.join(map(str, secret_code))}\n\n"
                                   f"Attempts: {game_data['attempts']}/10\n\n"
                                   f"**+{reward} PsyCoins!** 🪙",
                        color=discord.Color.gold()
                    )
                    await msg.reply(embed=embed)
                    del self.active_games[game_id]
                    break
                
                elif game_data["attempts"] >= 10:
                    embed = discord.Embed(
                        title="💥 Out of Attempts!",
                        description=f"**Secret Code:** {''.join(map(str, secret_code))}\n\nBetter luck next time!",
                        color=discord.Color.red()
                    )
                    await msg.reply(embed=embed)
                    del self.active_games[game_id]
                    break
                
                else:
                    embed = discord.Embed(
                        title="🔐 Code Breaker",
                        description=f"**Guess:** {''.join(map(str, guess))}\n"
                                   f"**Feedback:** {feedback_str}\n\n"
                                   f"**Attempts: {game_data['attempts']}/10**",
                        color=discord.Color.blue()
                    )
                    await msg.reply(embed=embed)
                
            except asyncio.TimeoutError:
                if game_id in self.active_games:
                    embed = discord.Embed(
                        title="⏰ Time's Up!",
                        description=f"**Secret Code:** {''.join(map(str, secret_code))}\n\nGame ended due to inactivity.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    del self.active_games[game_id]
                break
    
    async def game_detective_action(self, interaction: discord.Interaction):
        """Clue board game mystery"""
        suspects = ["Colonel Mustard", "Miss Scarlet", "Professor Plum", "Mrs. Peacock", "Mr. Green", "Mrs. White"]
        weapons = ["Candlestick", "Knife", "Lead Pipe", "Revolver", "Rope", "Wrench"]
        rooms = ["Kitchen", "Ballroom", "Conservatory", "Dining Room", "Library", "Lounge", "Study", "Hall", "Billiard Room"]
        
        # Generate solution
        murderer = random.choice(suspects)
        murder_weapon = random.choice(weapons)
        murder_room = random.choice(rooms)
        
        # Generate clues
        clues = [
            f"🔍 The weapon was not found in the {random.choice([r for r in rooms if r != murder_room])}",
            f"👤 {random.choice([s for s in suspects if s != murderer])} has an alibi",
            f"🔪 The {random.choice([w for w in weapons if w != murder_weapon])} was not used",
            f"🏠 Someone saw suspicious activity near the {murder_room}",
            f"👥 {random.choice([s for s in suspects if s != murderer])} was seen elsewhere during the murder",
        ]
        
        game_id = f"{interaction.guild.id}_{interaction.user.id}_detective"
        self.active_games[game_id] = {
            "type": "detective",
            "solution": (murderer, murder_weapon, murder_room),
            "clues_shown": 0,
            "user": interaction.user.id
        }
        
        embed = discord.Embed(
            title="🕵️ Detective Mystery",
            description="**A murder has occurred!**\n\n"
                       "Solve the mystery:\n"
                       "• WHO did it?\n"
                       "• WHAT weapon?\n"
                       "• WHERE did it happen?\n\n"
                       f"**Clue #1:** {clues[0]}\n\n"
                       "React with 🔍 for more clues\n"
                       "Type your accusation: `[suspect], [weapon], [room]`",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="Suspects", value="\n".join(suspects), inline=True)
        embed.add_field(name="Weapons", value="\n".join(weapons), inline=True)
        embed.add_field(name="Rooms", value="\n".join(rooms), inline=False)
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🔍")
        
        def check_reaction(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) == "🔍" and reaction.message.id == msg.id
        
        def check_message(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id
        
        # Game loop
        while game_id in self.active_games:
            done, pending = await asyncio.wait([
                asyncio.create_task(self.bot.wait_for('reaction_add', check=check_reaction, timeout=120.0)),
                asyncio.create_task(self.bot.wait_for('message', check=check_message, timeout=120.0))
            ], return_when=asyncio.FIRST_COMPLETED)
            
            for task in pending:
                task.cancel()
            
            try:
                result = done.pop().result()
                
                if isinstance(result, tuple):  # Reaction
                    game_data = self.active_games.get(game_id)
                    if not game_data:
                        break
                    
                    game_data["clues_shown"] += 1
                    if game_data["clues_shown"] < len(clues):
                        await interaction.followup.send(f"🔍 **Clue #{game_data['clues_shown'] + 1}:** {clues[game_data['clues_shown']]}")
                    else:
                        await interaction.followup.send("🔍 No more clues available! Make your accusation!")
                    
                else:  # Message
                    accusation = result.content
                    
                    # Parse accusation
                    parts = [part.strip() for part in accusation.split(",")]
                    if len(parts) != 3:
                        await result.reply("❌ Format: `[suspect], [weapon], [room]`")
                        continue
                    
                    if parts == [murderer, murder_weapon, murder_room]:
                        reward = 1000 - (game_data["clues_shown"] * 100)
                        embed = discord.Embed(
                            title="🎉 CASE SOLVED!",
                            description=f"**You cracked the case!**\n\n"
                                       f"👤 Murderer: {murderer}\n"
                                       f"🔪 Weapon: {murder_weapon}\n"
                                       f"🏠 Location: {murder_room}\n\n"
                                       f"**+{reward} PsyCoins!** 🪙",
                            color=discord.Color.green()
                        )
                        # Chance to award a mythic TCG card for solving detective puzzle
                        if tcg_manager:
                            try:
                                awarded = tcg_manager.award_for_game_event(str(result.author.id), 'mythic')
                                if awarded:
                                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                                    embed.add_field(name='🎴 Bonus Card', value=', '.join(names), inline=False)
                            except Exception:
                                pass
                        await result.reply(embed=embed)
                        del self.active_games[game_id]
                        break
                    else:
                        await result.reply("❌ **Wrong accusation!** Try again or get more clues with 🔍")
            
            except asyncio.TimeoutError:
                if game_id in self.active_games:
                    embed = discord.Embed(
                        title="⏰ Case Closed - Unsolved",
                        description=f"**The truth:**\n"
                                   f"👤 {murderer}\n"
                                   f"🔪 {murder_weapon}\n"
                                   f"🏠 {murder_room}",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)
                    del self.active_games[game_id]
                break

async def setup(bot):
    await bot.add_cog(PuzzleGames(bot))
