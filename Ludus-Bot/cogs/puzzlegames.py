import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os
import io

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
from PIL import Image, ImageDraw
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class MinesweeperGame:
    """Represents a single Minesweeper game session"""
    
    def __init__(self, rows: int, cols: int, mines: int, user_id: int, bot=None):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.user_id = user_id
        
        # Load custom emoji from JSON
        defaults = {
            "mine": "💣", "flag": "🚩", "hidden": "🟦",
            "revealed_empty": "⬜", "exploded": "💥",
            "0": "⬜", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣",
            "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣"
        }
        
        try:
            with open("data/minesweeper_emoji_mapping.json", "r") as f:
                emoji_config = json.load(f)
            
            self.emoji = {}
            
            # Convert IDs to emoji objects if bot provided
            if bot:
                for key, value in emoji_config.items():
                    if isinstance(value, str):
                        value = value.strip()
                    
                    # Try to get custom emoji by ID
                    if isinstance(value, str) and value.isdigit():
                        emoji_obj = bot.get_emoji(int(value))
                        if emoji_obj:
                            self.emoji[key] = str(emoji_obj)
                        else:
                            self.emoji[key] = defaults.get(key, "❓")
                    else:
                        # Already an emoji or unicode
                        self.emoji[key] = value
            else:
                self.emoji = emoji_config
            
            # Fill missing keys with defaults
            for key, val in defaults.items():
                if key not in self.emoji:
                    self.emoji[key] = val
                    
        except Exception:
            self.emoji = defaults
        
        # Game state
        self.board = [[0 for _ in range(cols)] for _ in range(rows)]
        self.revealed = [[False for _ in range(cols)] for _ in range(rows)]
        self.flagged = [[False for _ in range(cols)] for _ in range(rows)]
        self.game_over = False
        self.won = False
        self.mines_placed = False
        self.mine_positions = set()
        self.moves = 0
    
    def place_mines(self, safe_r: int, safe_c: int):
        """Place mines avoiding the first clicked position"""
        placed = 0
        while placed < self.mines:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            
            # Avoid first click and adjacent cells
            if abs(r - safe_r) <= 1 and abs(c - safe_c) <= 1:
                continue
            
            if (r, c) not in self.mine_positions:
                self.mine_positions.add((r, c))
                self.board[r][c] = -1
                placed += 1
        
        # Calculate numbers
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self.board[nr][nc] == -1:
                                count += 1
                self.board[r][c] = count
        
        self.mines_placed = True
    
    def reveal(self, r: int, c: int) -> tuple[bool, str]:
        """Reveal a cell, return (success, message)"""
        if self.game_over:
            return False, "Game is over!"
        
        if self.flagged[r][c]:
            return False, "Remove flag first!"
        
        if self.revealed[r][c]:
            return False, "Already revealed!"
        
        # Place mines on first move
        if not self.mines_placed:
            self.place_mines(r, c)
        
        self.moves += 1
        
        # Hit a mine
        if self.board[r][c] == -1:
            self.revealed[r][c] = True
            self.game_over = True
            return True, "💥 BOOM! Hit a mine!"
        
        # Reveal cell
        self._flood_reveal(r, c)
        
        # Check win
        revealed_count = sum(sum(row) for row in self.revealed)
        if revealed_count == self.rows * self.cols - self.mines:
            self.game_over = True
            self.won = True
            return True, "🎉 You won!"
        
        return True, f"Revealed ({r}, {c})"
    
    def _flood_reveal(self, r: int, c: int):
        """Flood fill reveal for empty cells"""
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return
        if self.revealed[r][c] or self.flagged[r][c]:
            return
        
        self.revealed[r][c] = True
        
        # If cell has number, stop
        if self.board[r][c] > 0:
            return
        
        # If empty, reveal adjacent
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                self._flood_reveal(r + dr, c + dc)
    
    def toggle_flag(self, r: int, c: int) -> tuple[bool, str]:
        """Toggle flag on cell"""
        if self.game_over:
            return False, "Game is over!"
        
        if self.revealed[r][c]:
            return False, "Can't flag revealed cell!"
        
        self.flagged[r][c] = not self.flagged[r][c]
        action = "Flagged" if self.flagged[r][c] else "Unflagged"
        return True, f"{action} ({r}, {c})"
    
    def render_board(self) -> str:
        """Render board as emoji grid"""
        number_emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        lines = []
        
        # Column header
        header = "⬛"
        for c in range(min(self.cols, 10)):
            header += number_emojis[c]
        lines.append(header)
        
        for r in range(self.rows):
            line_parts = [number_emojis[r] if r < 10 else number_emojis[r % 10]]
            for c in range(self.cols):
                if self.flagged[r][c]:
                    line_parts.append(self.emoji["flag"])
                elif not self.revealed[r][c]:
                    line_parts.append(self.emoji["hidden"])
                elif self.board[r][c] == -1:
                    if self.game_over:
                        line_parts.append(self.emoji["exploded"])
                    else:
                        line_parts.append(self.emoji["mine"])
                elif self.board[r][c] == 0:
                    line_parts.append(self.emoji["revealed_empty"])
                else:
                    line_parts.append(self.emoji[str(self.board[r][c])])
            lines.append("".join(line_parts))
        
        return "\n".join(lines)
    
    def get_stats(self) -> str:
        """Get game statistics"""
        flags_placed = sum(sum(row) for row in self.flagged)
        cells_revealed = sum(sum(row) for row in self.revealed)
        cells_remaining = self.rows * self.cols - self.mines - cells_revealed
        
        return (f"💣 Mines: {self.mines} | 🚩 Flags: {flags_placed}\n"
                f"📊 Revealed: {cells_revealed} | Remaining: {cells_remaining}\n"
                f"🎯 Moves: {self.moves}")


class MinesweeperMoveModal(discord.ui.Modal, title="Make Move"):
    """Modal for inputting move coordinates"""
    
    row_input = discord.ui.TextInput(
        label="Row",
        placeholder="Enter row number",
        required=True,
        max_length=2
    )
    
    col_input = discord.ui.TextInput(
        label="Column",
        placeholder="Enter column number",
        required=True,
        max_length=2
    )
    
    def __init__(self, view: 'MinesweeperView'):
        super().__init__()
        self.view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle move submission"""
        try:
            r = int(self.row_input.value)
            c = int(self.col_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid numbers!", ephemeral=True)
            return
        
        game = self.view.game
        
        if r < 0 or r >= game.rows or c < 0 or c >= game.cols:
            await interaction.response.send_message(
                f"❌ Out of bounds! Row: 0-{game.rows-1}, Column: 0-{game.cols-1}",
                ephemeral=True
            )
            return
        
        # Make move
        if self.view.mode == "reveal":
            success, message = game.reveal(r, c)
        else:
            success, message = game.toggle_flag(r, c)
        
        if not success:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Update view
        self.view.build_ui()
        
        # Check if game ended
        if game.game_over:
            await interaction.response.edit_message(view=self.view)
            
            if game.won:
                reward = 500 - (game.moves * 10)
                reward_msg = f"🎉 **You won in {game.moves} moves!**\n\n**+{reward} PsyCoins!** 🪙"
                
                # Award TCG card for winning
                if tcg_manager:
                    try:
                        awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'mythic')
                        if awarded:
                            names = [CARD_DATABASE.get(card, {}).get('name', card) for card in awarded]
                            reward_msg += f"\n🎴 **Bonus Card:** {', '.join(names)}"
                    except:
                        pass
                
                await interaction.followup.send(reward_msg)
            else:
                await interaction.followup.send("💥 **Game Over!** Better luck next time!")
        else:
            await interaction.response.edit_message(view=self.view)


class MinesweeperView(discord.ui.LayoutView):
    """Minesweeper game interface"""
    
    def __init__(self, game: MinesweeperGame, user_id: int):
        self.game = game
        self.user_id = user_id
        self.message = None
        self.mode = "reveal"  # reveal or flag
        
        super().__init__(timeout=600)
        self.build_ui()
    
    def build_ui(self):
        """Build the UI layout"""
        self.clear_items()
        
        # Title and stats
        if self.game.game_over:
            if self.game.won:
                title = "# 🎉 VICTORY! YOU WON!"
            else:
                title = "# 💥 GAME OVER!"
        else:
            title = "# 💣 MINESWEEPER"
        
        board_display = self.game.render_board()
        stats = self.game.get_stats()
        
        content = f"{title}\n\n{stats}\n\n{board_display}\n\n**Mode:** {'⛏️ Reveal' if self.mode == 'reveal' else '🚩 Flag'}"
        
        container_items = [
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Only add buttons if game not over
        if not self.game.game_over:
            # Mode toggle button
            mode_btn = discord.ui.Button(
                style=discord.ButtonStyle.primary if self.mode == "reveal" else discord.ButtonStyle.danger,
                emoji="⛏️" if self.mode == "reveal" else "🚩",
                label="Switch Mode"
            )
            mode_btn.callback = self.toggle_mode_callback
            
            # Make move button
            move_btn = discord.ui.Button(
                style=discord.ButtonStyle.success,
                emoji="🎯",
                label="Make Move"
            )
            move_btn.callback = self.make_move_callback
            
            container_items.append(discord.ui.ActionRow(mode_btn, move_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour.red() if self.game.game_over else discord.Colour.blue()
        )
        
        self.add_item(self.container)
    
    async def toggle_mode_callback(self, interaction: discord.Interaction):
        """Toggle between reveal and flag mode"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        self.mode = "flag" if self.mode == "reveal" else "reveal"
        self.build_ui()
        
        await interaction.response.edit_message(view=self)
    
    async def make_move_callback(self, interaction: discord.Interaction):
        """Open modal for making a move"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        modal = MinesweeperMoveModal(self)
        await interaction.response.send_modal(modal)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow game owner to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.message:
            try:
                await self.message.edit(view=None)
            except:
                pass

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
        
        # Create game
        game = MinesweeperGame(rows, cols, mines, interaction.user.id, self.bot)
        game_id = f"{interaction.guild.id}_{interaction.user.id}_minesweeper"
        self.active_games[game_id] = game
        
        # Create view
        view = MinesweeperView(game, interaction.user.id)
        
        await interaction.response.send_message(view=view)
        view.message = await interaction.original_response()
    
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
