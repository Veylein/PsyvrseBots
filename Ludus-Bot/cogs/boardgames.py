import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, List

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView
try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

class BoardGames(commands.Cog):
    """Classic board games - Chess, Checkers, Connect4, Tic-Tac-Toe, and more"""

    @app_commands.command(name="boardgames", description="View all board game commands and info (paginated)")
    async def boardgames_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Board Games"
        category_desc = "Play classic and new board games! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.player_games = {}  # Track which game each player is in

    # ==================== TIC-TAC-TOE ====================
    
    # Slash command groups
    ttt_group = app_commands.Group(name="ttt", description="Tic-Tac-Toe game")
    
    @commands.group(name="ttt", invoke_without_command=True)
    async def ttt(self, ctx):
        """Tic-Tac-Toe commands"""
        await ctx.send("**Tic-Tac-Toe Commands:**\n`L!ttt start [@player]` - Start a game (vs player or AI)\n`L!ttt move <1-9>` - Make a move\n`L!ttt quit` - Quit current game")

    @ttt.command(name="start")
    async def ttt_start(self, ctx, opponent: Optional[discord.Member] = None, difficulty: str = "hard"):
        """Start a Tic-Tac-Toe game"""
        await self._start_ttt(ctx.author, opponent, difficulty, ctx, None)

    @ttt_group.command(name="start", description="Start a Tic-Tac-Toe game")
    @app_commands.describe(
        opponent="Player to challenge (optional, defaults to AI)",
        difficulty="AI difficulty: easy, medium, or hard (default: hard)"
    )
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard (Unbeatable)", value="hard")
    ])
    async def ttt_slash(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None, difficulty: str = "hard"):
        await interaction.response.defer()
        await self._start_ttt(interaction.user, opponent, difficulty, None, interaction)

    async def _start_ttt(self, player1, opponent, difficulty, ctx, interaction):
        if player1.id in self.player_games:
            msg = "❌ You're already in a game! Finish it first with `L!ttt quit`"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Initialize game
        is_ai = opponent is None
        player2 = "AI" if is_ai else opponent
        
        if not is_ai and opponent.id in self.player_games:
            msg = f"❌ {opponent.mention} is already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        game_id = f"ttt_{player1.id}_{random.randint(1000, 9999)}"
        board = [" " for _ in range(9)]
        
        game_state = {
            "type": "ttt",
            "board": board,
            "players": [player1.id, player2 if is_ai else player2.id],
            "current_turn": player1.id,
            "symbols": {player1.id: "X", (player2 if is_ai else player2.id): "O"},
            "is_ai": is_ai,
            "difficulty": difficulty if is_ai else None,
            "channel": ctx.channel.id if ctx else interaction.channel.id
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player1.id] = game_id
        if not is_ai:
            self.player_games[opponent.id] = game_id

        embed = self._create_ttt_embed(game_state, player1, player2)
        if is_ai:
            embed.add_field(name="AI Difficulty", value=f"**{difficulty.title()}**", inline=False)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _create_ttt_embed(self, game_state, player1, player2):
        board = game_state["board"]
        # Show position numbers for empty spaces
        display_board = [board[i] if board[i] != " " else str(i+1) for i in range(9)]
        board_display = f"```\n {display_board[0]} │ {display_board[1]} │ {display_board[2]} \n───┼───┼───\n {display_board[3]} │ {display_board[4]} │ {display_board[5]} \n───┼───┼───\n {display_board[6]} │ {display_board[7]} │ {display_board[8]} \n```"
        
        current_player = self.bot.get_user(game_state["current_turn"]) if not game_state["is_ai"] or game_state["current_turn"] != "AI" else "AI"
        
        embed = discord.Embed(
            title="⭕ Tic-Tac-Toe ❌",
            description=board_display,
            color=discord.Color.blue()
        )
        
        p1_name = player1.display_name if hasattr(player1, 'display_name') else str(player1)
        p2_name = "AI" if game_state["is_ai"] else (player2.display_name if hasattr(player2, 'display_name') else str(player2))
        
        embed.add_field(name="Players", value=f"❌ {p1_name} vs ⭕ {p2_name}", inline=False)
        embed.add_field(name="Current Turn", value=f"**{current_player.display_name if hasattr(current_player, 'display_name') else current_player}**", inline=False)
        embed.add_field(name="How to Play", value="Use `L!ttt move <1-9>` or `/ttt-move <1-9>` to make a move", inline=False)
        
        return embed

    @ttt.command(name="move")
    async def ttt_move(self, ctx, position: int):
        """Make a move in Tic-Tac-Toe"""
        await self._make_ttt_move(ctx.author, position, ctx, None)

    @ttt_group.command(name="move", description="Make a Tic-Tac-Toe move")
    @app_commands.describe(position="Position to place your symbol (1-9)")
    async def ttt_move_slash(self, interaction: discord.Interaction, position: int):
        await interaction.response.defer()
        await self._make_ttt_move(interaction.user, position, None, interaction)

    async def _make_ttt_move(self, player, position, ctx, interaction):
        if player.id not in self.player_games:
            msg = "❌ You're not in a game! Start one with `L!ttt start`"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        game_id = self.player_games[player.id]
        game_state = self.active_games[game_id]
        
        if game_state["current_turn"] != player.id:
            msg = "❌ It's not your turn!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if position < 1 or position > 9:
            msg = "❌ Position must be between 1 and 9!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if game_state["board"][position - 1] != " ":
            msg = "❌ That position is already taken!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Make move
        symbol = game_state["symbols"][player.id]
        game_state["board"][position - 1] = symbol

        # Check for win
        winner = self._check_ttt_winner(game_state["board"])
        
        if winner:
            embed = self._create_ttt_embed(game_state, player, game_state["players"][1])
            embed.title = f"🎉 {player.display_name} wins!"
            embed.color = discord.Color.green()
            
            # Award coins
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(player.id, 50, "ttt_win")
                embed.add_field(name="Reward", value="+50 PsyCoins", inline=False)
            # Chance to award a basic TCG card for simple minigame win
            if tcg_manager:
                try:
                    awarded = tcg_manager.award_for_game_event(str(player.id), 'basic')
                    if awarded:
                        names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                        embed.add_field(name='🎴 Bonus Card', value=', '.join(names), inline=False)
                except Exception:
                    pass
            
            # Clean up game
            for p_id in game_state["players"]:
                if p_id in self.player_games:
                    del self.player_games[p_id]
            del self.active_games[game_id]
            
            if interaction:
                await interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        # Check for draw
        if " " not in game_state["board"]:
            embed = self._create_ttt_embed(game_state, player, game_state["players"][1])
            embed.title = "🤝 It's a draw!"
            embed.color = discord.Color.orange()
            
            # Clean up game
            for p_id in game_state["players"]:
                if p_id in self.player_games:
                    del self.player_games[p_id]
            del self.active_games[game_id]
            
            if interaction:
                await interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        # Switch turn
        if game_state["is_ai"]:
            # AI turn
            game_state["current_turn"] = "AI"
            difficulty = game_state.get("difficulty", "hard")
            ai_move = self._get_ai_ttt_move(game_state["board"], difficulty)
            game_state["board"][ai_move] = "O"
            
            # Check AI win
            winner = self._check_ttt_winner(game_state["board"])
            if winner:
                embed = self._create_ttt_embed(game_state, player, "AI")
                embed.title = "🤖 AI wins!"
                embed.color = discord.Color.red()
                
                # Clean up game
                del self.player_games[player.id]
                del self.active_games[game_id]
                
                if interaction:
                    await interaction.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                return
            
            game_state["current_turn"] = player.id
        else:
            # Switch to other player
            current_idx = game_state["players"].index(game_state["current_turn"])
            game_state["current_turn"] = game_state["players"][1 - current_idx]

        # Show updated board
        p2 = "AI" if game_state["is_ai"] else self.bot.get_user(game_state["players"][1])
        embed = self._create_ttt_embed(game_state, player, p2)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _check_ttt_winner(self, board):
        """Check if there's a winner in Tic-Tac-Toe"""
        wins = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
        
        for combo in wins:
            if board[combo[0]] == board[combo[1]] == board[combo[2]] != " ":
                return board[combo[0]]
        return None

    def _get_ai_ttt_move(self, board, difficulty="hard"):
        """Smart AI for Tic-Tac-Toe with difficulty levels"""
        if difficulty == "easy":
            # Random move
            available = [i for i in range(9) if board[i] == " "]
            return random.choice(available)
        
        elif difficulty == "medium":
            # 50% chance of smart move, 50% random
            if random.random() < 0.5:
                return self._minimax_ttt(board, "O")[1]
            available = [i for i in range(9) if board[i] == " "]
            return random.choice(available)
        
        else:  # hard
            # Minimax algorithm - perfect play
            return self._minimax_ttt(board, "O")[1]
    
    def _minimax_ttt(self, board, player):
        """Minimax algorithm for perfect Tic-Tac-Toe AI"""
        winner = self._check_ttt_winner(board)
        if winner == "O":
            return (1, None)
        elif winner == "X":
            return (-1, None)
        elif " " not in board:
            return (0, None)
        
        if player == "O":
            best = (-2, None)
            for i in range(9):
                if board[i] == " ":
                    board[i] = "O"
                    score = self._minimax_ttt(board, "X")[0]
                    board[i] = " "
                    if score > best[0]:
                        best = (score, i)
            return best
        else:
            best = (2, None)
            for i in range(9):
                if board[i] == " ":
                    board[i] = "X"
                    score = self._minimax_ttt(board, "O")[0]
                    board[i] = " "
                    if score < best[0]:
                        best = (score, i)
            return best

    # ==================== CONNECT 4 ====================
    
    connect4_group = app_commands.Group(name="connect4", description="Connect 4 game")
    
    @commands.group(name="connect4", aliases=["c4"], invoke_without_command=True)
    async def connect4(self, ctx):
        """Connect 4 commands"""
        await ctx.send("**Connect 4 Commands:**\n`L!connect4 start [@player]` - Start a game\n`L!connect4 drop <1-7>` - Drop a piece\n`L!connect4 quit` - Quit current game")

    @connect4.command(name="start")
    async def c4_start(self, ctx, opponent: Optional[discord.Member] = None):
        """Start a Connect 4 game"""
        await self._start_connect4(ctx.author, opponent, ctx, None)

    @connect4_group.command(name="start", description="Start a Connect 4 game")
    @app_commands.describe(opponent="Player to challenge (optional, defaults to AI)")
    async def connect4_slash(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        await interaction.response.defer()
        await self._start_connect4(interaction.user, opponent, None, interaction)

    async def _start_connect4(self, player1, opponent, ctx, interaction):
        if player1.id in self.player_games:
            msg = "❌ You're already in a game! Finish it first."
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        is_ai = opponent is None
        player2 = "AI" if is_ai else opponent
        
        if not is_ai and opponent.id in self.player_games:
            msg = f"❌ {opponent.mention} is already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        game_id = f"c4_{player1.id}_{random.randint(1000, 9999)}"
        board = [[" " for _ in range(7)] for _ in range(6)]
        
        game_state = {
            "type": "connect4",
            "board": board,
            "players": [player1.id, player2 if is_ai else player2.id],
            "current_turn": player1.id,
            "symbols": {player1.id: "🔴", (player2 if is_ai else player2.id): "🟡"},
            "is_ai": is_ai,
            "channel": ctx.channel.id if ctx else interaction.channel.id
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player1.id] = game_id
        if not is_ai:
            self.player_games[opponent.id] = game_id

        embed = self._create_c4_embed(game_state, player1, player2)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _create_c4_embed(self, game_state, player1, player2):
        board = game_state["board"]
        board_display = "```\n 1   2   3   4   5   6   7\n"
        board_display += "╔═══╦═══╦═══╦═══╦═══╦═══╦═══╗\n"
        for i, row in enumerate(board):
            board_display += "║ " + " ║ ".join([cell if cell != " " else " " for cell in row]) + " ║\n"
            if i < 5:
                board_display += "╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣\n"
        board_display += "╚═══╩═══╩═══╩═══╩═══╩═══╩═══╝\n```"
        
        current_player = self.bot.get_user(game_state["current_turn"]) if not game_state["is_ai"] or game_state["current_turn"] != "AI" else "AI"
        
        embed = discord.Embed(
            title="🔴 Connect 4 🟡",
            description=board_display,
            color=discord.Color.blue()
        )
        
        p1_name = player1.display_name if hasattr(player1, 'display_name') else str(player1)
        p2_name = "AI" if game_state["is_ai"] else (player2.display_name if hasattr(player2, 'display_name') else str(player2))
        
        embed.add_field(name="Players", value=f"🔴 {p1_name} vs 🟡 {p2_name}", inline=False)
        embed.add_field(name="Current Turn", value=f"**{current_player.display_name if hasattr(current_player, 'display_name') else current_player}**", inline=False)
        embed.add_field(name="How to Play", value="Use `L!connect4 drop <1-7>` or `/c4-drop <1-7>` to drop a piece", inline=False)
        
        return embed

    @connect4.command(name="drop")
    async def c4_drop(self, ctx, column: int):
        """Drop a piece in Connect 4"""
        await self._make_c4_move(ctx.author, column, ctx, None)

    @connect4_group.command(name="drop", description="Drop a Connect 4 piece")
    @app_commands.describe(column="Column to drop piece (1-7)")
    async def c4_drop_slash(self, interaction: discord.Interaction, column: int):
        await interaction.response.defer()
        await self._make_c4_move(interaction.user, column, None, interaction)

    async def _make_c4_move(self, player, column, ctx, interaction):
        if player.id not in self.player_games:
            msg = "❌ You're not in a game! Start one with `L!connect4 start`"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        game_id = self.player_games[player.id]
        game_state = self.active_games[game_id]
        
        if game_state["type"] != "connect4":
            msg = "❌ You're not in a Connect 4 game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return
        
        if game_state["current_turn"] != player.id:
            msg = "❌ It's not your turn!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if column < 1 or column > 7:
            msg = "❌ Column must be between 1 and 7!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Find lowest empty row in column
        col_idx = column - 1
        row_idx = None
        for r in range(5, -1, -1):
            if game_state["board"][r][col_idx] == " ":
                row_idx = r
                break

        if row_idx is None:
            msg = "❌ That column is full!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Make move
        symbol = game_state["symbols"][player.id]
        game_state["board"][row_idx][col_idx] = symbol

        # Check for win
        if self._check_c4_winner(game_state["board"], row_idx, col_idx):
            embed = self._create_c4_embed(game_state, player, game_state["players"][1])
            embed.title = f"🎉 {player.display_name} wins!"
            embed.color = discord.Color.green()
            
            # Award coins
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(player.id, 75, "c4_win")
                embed.add_field(name="Reward", value="+75 PsyCoins", inline=False)
            
            # Clean up game
            for p_id in game_state["players"]:
                if p_id != "AI" and p_id in self.player_games:
                    del self.player_games[p_id]
            del self.active_games[game_id]
            
            if interaction:
                await interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        # Check for draw
        if all(game_state["board"][0][c] != " " for c in range(7)):
            embed = self._create_c4_embed(game_state, player, game_state["players"][1])
            embed.title = "🤝 It's a draw!"
            embed.color = discord.Color.orange()
            
            # Clean up game
            for p_id in game_state["players"]:
                if p_id != "AI" and p_id in self.player_games:
                    del self.player_games[p_id]
            del self.active_games[game_id]
            
            if interaction:
                await interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        # Switch turn or AI move
        if game_state["is_ai"]:
            game_state["current_turn"] = "AI"
            ai_col = self._get_ai_c4_move(game_state["board"], "🟡", "🔴")
            
            for r in range(5, -1, -1):
                if game_state["board"][r][ai_col] == " ":
                    game_state["board"][r][ai_col] = "🟡"
                    
                    if self._check_c4_winner(game_state["board"], r, ai_col):
                        embed = self._create_c4_embed(game_state, player, "AI")
                        embed.title = "🤖 AI wins!"
                        embed.color = discord.Color.red()
                        
                        del self.player_games[player.id]
                        del self.active_games[game_id]
                        
                        if interaction:
                            await interaction.followup.send(embed=embed)
                        else:
                            await ctx.send(embed=embed)
                        return
                    break
            
            game_state["current_turn"] = player.id
        else:
            current_idx = game_state["players"].index(game_state["current_turn"])
            game_state["current_turn"] = game_state["players"][1 - current_idx]

        # Show updated board
        p2 = "AI" if game_state["is_ai"] else self.bot.get_user(game_state["players"][1])
        embed = self._create_c4_embed(game_state, player, p2)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _check_c4_winner(self, board, row, col):
        """Check if there's a winner in Connect 4"""
        symbol = board[row][col]
        if symbol == " ":
            return False

        # Check directions: horizontal, vertical, diagonal
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            count = 1
            
            # Check positive direction
            r, c = row + dr, col + dc
            while 0 <= r < 6 and 0 <= c < 7 and board[r][c] == symbol:
                count += 1
                r += dr
                c += dc
            
            # Check negative direction
            r, c = row - dr, col - dc
            while 0 <= r < 6 and 0 <= c < 7 and board[r][c] == symbol:
                count += 1
                r -= dr
                c -= dc
            
            if count >= 4:
                return True
        
        return False
    
    def _get_ai_c4_move(self, board, ai_symbol, player_symbol):
        """Strategic AI for Connect 4 with lookahead"""
        available = [c for c in range(7) if board[0][c] == " "]
        
        # 1. Try to win immediately
        for col in available:
            test_board = [row[:] for row in board]
            for r in range(5, -1, -1):
                if test_board[r][col] == " ":
                    test_board[r][col] = ai_symbol
                    if self._check_c4_winner(test_board, r, col):
                        return col
                    break
        
        # 2. Block player from winning
        for col in available:
            test_board = [row[:] for row in board]
            for r in range(5, -1, -1):
                if test_board[r][col] == " ":
                    test_board[r][col] = player_symbol
                    if self._check_c4_winner(test_board, r, col):
                        return col
                    break
        
        # 3. Prefer center columns (stronger position)
        center_cols = [3, 2, 4, 1, 5, 0, 6]
        for col in center_cols:
            if col in available:
                # Check if move doesn't create winning opportunity for opponent above
                test_board = [row[:] for row in board]
                row_idx = None
                for r in range(5, -1, -1):
                    if test_board[r][col] == " ":
                        row_idx = r
                        break
                
                if row_idx is not None and row_idx > 0:
                    # Check if opponent can win in the row above
                    test_board[row_idx][col] = ai_symbol
                    test_board[row_idx - 1][col] = player_symbol
                    if not self._check_c4_winner(test_board, row_idx - 1, col):
                        return col
                elif row_idx == 0:
                    return col
        
        # 4. Fallback to any available move
        return available[0] if available else 3

    # ==================== HANGMAN ====================
    
    @commands.command(name="hangman")
    async def hangman(self, ctx):
        """Start a Hangman game"""
        await self._start_hangman(ctx.author, ctx, None)

    @app_commands.command(name="hangman", description="Play Hangman")
    async def hangman_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_hangman(interaction.user, None, interaction)

    async def _start_hangman(self, player, ctx, interaction):
        if player.id in self.player_games:
            msg = "❌ You're already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Expanded word categories
        word_categories = {
            "Animals": ["ELEPHANT", "GIRAFFE", "PENGUIN", "DOLPHIN", "BUTTERFLY", "CROCODILE", "KANGAROO", "OCTOPUS"],
            "Games": ["MINECRAFT", "FORTNITE", "POKEMON", "ZELDA", "SONIC", "MARIO", "OVERWATCH", "VALORANT"],
            "Movies": ["AVATAR", "INCEPTION", "GLADIATOR", "TITANIC", "FROZEN", "AVENGERS", "SPIDERMAN", "BATMAN"],
            "Food": ["PIZZA", "BURGER", "SUSHI", "TACO", "CHOCOLATE", "PANCAKE", "SANDWICH", "LASAGNA"],
            "Countries": ["AMERICA", "BRAZIL", "CANADA", "FRANCE", "JAPAN", "AUSTRALIA", "GERMANY", "ITALY"],
            "Tech": ["COMPUTER", "INTERNET", "SOFTWARE", "HARDWARE", "PYTHON", "DISCORD", "CODING", "DIGITAL"],
            "Space": ["GALAXY", "PLANET", "ASTRONAUT", "ROCKET", "METEOR", "NEBULA", "COMET", "SATELLITE"],
            "Music": ["GUITAR", "PIANO", "DRUMS", "VIOLIN", "CONCERT", "SYMPHONY", "MELODY", "RHYTHM"]
        }
        
        category = random.choice(list(word_categories.keys()))
        word = random.choice(word_categories[category])
        
        game_id = f"hangman_{player.id}"
        game_state = {
            "type": "hangman",
            "word": word,
            "category": category,
            "guessed": set(),
            "wrong": 0,
            "max_wrong": 6,
            "hints_used": 0,
            "channel": ctx.channel.id if ctx else interaction.channel.id
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player.id] = game_id

        embed = self._create_hangman_embed(game_state, player)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _create_hangman_embed(self, game_state, player):
        word = game_state["word"]
        guessed = game_state["guessed"]
        wrong = game_state["wrong"]
        max_wrong = game_state["max_wrong"]
        category = game_state.get("category", "Unknown")
        
        display = " ".join([c if c in guessed else "_" for c in word])
        
        hangman_stages = [
            "```\n  +---+\n      |\n      |\n      |\n     ===\n```",
            "```\n  +---+\n  O   |\n      |\n      |\n     ===\n```",
            "```\n  +---+\n  O   |\n  |   |\n      |\n     ===\n```",
            "```\n  +---+\n  O   |\n /|   |\n      |\n     ===\n```",
            "```\n  +---+\n  O   |\n /|\\  |\n      |\n     ===\n```",
            "```\n  +---+\n  O   |\n /|\\  |\n /    |\n     ===\n```",
            "```\n  +---+\n  O   |\n /|\\  |\n / \\  |\n     ===\n```"
        ]
        
        embed = discord.Embed(
            title=f"🎮 Hangman - {category}",
            description=hangman_stages[wrong],
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Word", value=f"`{display}`", inline=False)
        embed.add_field(name="Letters", value=f"Length: {len(word)}", inline=True)
        embed.add_field(name="Guessed Letters", value=", ".join(sorted(guessed)) if guessed else "None", inline=False)
        embed.add_field(name="Wrong Guesses", value=f"{wrong}/{max_wrong}", inline=False)
        embed.add_field(name="How to Play", value="Type a letter or type `hint` for a clue (max 2)", inline=False)
        
        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for hangman guesses"""
        if message.author.bot:
            return
        
        if message.author.id not in self.player_games:
            return
        
        game_id = self.player_games[message.author.id]
        game_state = self.active_games.get(game_id)
        
        if not game_state or game_state["type"] != "hangman":
            return
        
        if message.channel.id != game_state["channel"]:
            return
        
        content = message.content.upper().strip()
        
        # Handle hint request
        if content == "HINT":
            if game_state.get("hints_used", 0) >= 2:
                await message.channel.send("❌ You've used all your hints!")
                return
            
            # Reveal a random unrevealed letter
            unrevealed = [c for c in game_state["word"] if c not in game_state["guessed"]]
            if unrevealed:
                hint_letter = random.choice(unrevealed)
                game_state["guessed"].add(hint_letter)
                game_state["hints_used"] = game_state.get("hints_used", 0) + 1
                
                embed = self._create_hangman_embed(game_state, message.author)
                embed.add_field(name="💡 Hint Used", value=f"Revealed: **{hint_letter}**", inline=False)
                await message.channel.send(embed=embed)
            return
        
        # Handle letter guess
        if len(content) != 1 or not content.isalpha():
            return
        
        guess = content
        
        if guess in game_state["guessed"]:
            await message.channel.send(f"❌ You already guessed **{guess}**!")
            return
        
        game_state["guessed"].add(guess)
        
        if guess in game_state["word"]:
            # Correct guess
            if all(c in game_state["guessed"] for c in game_state["word"]):
                # Won
                embed = self._create_hangman_embed(game_state, message.author)
                embed.title = f"🎉 You won! - {game_state.get('category', 'Unknown')}"
                embed.color = discord.Color.green()
                display = " ".join(game_state["word"])
                embed.add_field(name="Word", value=f"**{display}**", inline=False)
                
                # Award coins (reduced if hints used)
                economy_cog = self.bot.get_cog("Economy")
                if economy_cog:
                    hints_used = game_state.get("hints_used", 0)
                    reward = 100 - (hints_used * 20)
                    economy_cog.add_coins(message.author.id, reward, "hangman_win")
                    embed.add_field(name="Reward", value=f"+{reward} PsyCoins", inline=False)
                    if hints_used > 0:
                        embed.add_field(name="Hints Used", value=f"{hints_used} (-{hints_used * 20} coins)", inline=False)
                
                await message.channel.send(embed=embed)
                
                del self.player_games[message.author.id]
                del self.active_games[game_id]
            else:
                embed = self._create_hangman_embed(game_state, message.author)
                await message.channel.send(f"✅ **{guess}** is in the word!", embed=embed)
        else:
            # Wrong guess
            game_state["wrong"] += 1
            
            if game_state["wrong"] >= game_state["max_wrong"]:
                # Lost
                embed = self._create_hangman_embed(game_state, message.author)
                embed.title = "💀 Game Over!"
                embed.color = discord.Color.red()
                embed.add_field(name="The word was", value=f"**{game_state['word']}**", inline=False)
                
                await message.channel.send(embed=embed)
                
                del self.player_games[message.author.id]
                del self.active_games[game_id]
            else:
                embed = self._create_hangman_embed(game_state, message.author)
                await message.channel.send(f"❌ **{guess}** is not in the word!", embed=embed)

async def setup(bot):
    await bot.add_cog(BoardGames(bot))
