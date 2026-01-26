import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional, List, Tuple
import copy

class ChessGame:
    """Full chess implementation with rules validation"""
    
    def __init__(self, player1, player2):
        self.player1 = player1  # White
        self.player2 = player2  # Black
        self.current_turn = player1
        self.board = self.create_board()
        self.move_history = []
        self.captured_pieces = {"white": [], "black": []}
        self.game_over = False
        self.winner = None
        
    def create_board(self):
        """Initialize chess board"""
        # Unicode chess pieces
        board = [
            ["♜", "♞", "♝", "♛", "♚", "♝", "♞", "♜"],  # Black back rank
            ["♟"] * 8,  # Black pawns
            ["·"] * 8,
            ["·"] * 8,
            ["·"] * 8,
            ["·"] * 8,
            ["♙"] * 8,  # White pawns
            ["♖", "♘", "♗", "♕", "♔", "♗", "♘", "♖"]   # White back rank
        ]
        return board
    
    def display_board(self):
        """Create a nice board display"""
        lines = ["```\n  a  b  c  d  e  f  g  h"]
        for i, row in enumerate(self.board):
            line = f"{8-i} " + " ".join(row) + f" {8-i}"
            lines.append(line)
        lines.append("  a  b  c  d  e  f  g  h\n```")
        return "\n".join(lines)
    
    def parse_move(self, move_str):
        """Convert chess notation to board coordinates"""
        # e.g., "e2e4" -> (6,4) to (4,4)
        if len(move_str) != 4:
            return None
        
        try:
            from_col = ord(move_str[0].lower()) - ord('a')
            from_row = 8 - int(move_str[1])
            to_col = ord(move_str[2].lower()) - ord('a')
            to_row = 8 - int(move_str[3])
            
            if all(0 <= x < 8 for x in [from_col, from_row, to_col, to_row]):
                return ((from_row, from_col), (to_row, to_col))
        except:
            pass
        return None
    
    def is_valid_move(self, from_pos, to_pos):
        """Validate if move is legal"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        piece = self.board[from_row][from_col]
        target = self.board[to_row][to_col]
        
        # Can't move empty square
        if piece == "·":
            return False
        
        # Check piece color matches turn
        white_pieces = "♔♕♖♗♘♙"
        black_pieces = "♚♛♜♝♞♟"
        
        if self.current_turn == self.player1 and piece not in white_pieces:
            return False
        if self.current_turn == self.player2 and piece not in black_pieces:
            return False
        
        # Can't capture own piece
        if target != "·":
            if piece in white_pieces and target in white_pieces:
                return False
            if piece in black_pieces and target in black_pieces:
                return False
        
        # Piece-specific movement rules
        if piece in ["♙", "♟"]:  # Pawn
            return self.is_valid_pawn_move(from_pos, to_pos, piece)
        elif piece in ["♖", "♜"]:  # Rook
            return self.is_valid_rook_move(from_pos, to_pos)
        elif piece in ["♘", "♞"]:  # Knight
            return self.is_valid_knight_move(from_pos, to_pos)
        elif piece in ["♗", "♝"]:  # Bishop
            return self.is_valid_bishop_move(from_pos, to_pos)
        elif piece in ["♕", "♛"]:  # Queen
            return self.is_valid_queen_move(from_pos, to_pos)
        elif piece in ["♔", "♚"]:  # King
            return self.is_valid_king_move(from_pos, to_pos)
        
        return False
    
    def is_valid_pawn_move(self, from_pos, to_pos, piece):
        """Pawn movement rules"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        direction = -1 if piece == "♙" else 1  # White moves up (-), black moves down (+)
        start_row = 6 if piece == "♙" else 1
        
        # Forward one square
        if to_col == from_col and to_row == from_row + direction:
            return self.board[to_row][to_col] == "·"
        
        # Forward two squares from start
        if to_col == from_col and from_row == start_row and to_row == from_row + (2 * direction):
            return (self.board[to_row][to_col] == "·" and 
                    self.board[from_row + direction][from_col] == "·")
        
        # Diagonal capture
        if abs(to_col - from_col) == 1 and to_row == from_row + direction:
            return self.board[to_row][to_col] != "·"
        
        return False
    
    def is_valid_rook_move(self, from_pos, to_pos):
        """Rook movement (straight lines)"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        if from_row != to_row and from_col != to_col:
            return False
        
        return self.is_path_clear(from_pos, to_pos)
    
    def is_valid_bishop_move(self, from_pos, to_pos):
        """Bishop movement (diagonals)"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        if abs(from_row - to_row) != abs(from_col - to_col):
            return False
        
        return self.is_path_clear(from_pos, to_pos)
    
    def is_valid_queen_move(self, from_pos, to_pos):
        """Queen movement (rook + bishop)"""
        return (self.is_valid_rook_move(from_pos, to_pos) or 
                self.is_valid_bishop_move(from_pos, to_pos))
    
    def is_valid_knight_move(self, from_pos, to_pos):
        """Knight movement (L-shape)"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        
        return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)
    
    def is_valid_king_move(self, from_pos, to_pos):
        """King movement (one square any direction)"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        return abs(to_row - from_row) <= 1 and abs(to_col - from_col) <= 1
    
    def is_path_clear(self, from_pos, to_pos):
        """Check if path between two positions is clear"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        row_step = 0 if from_row == to_row else (1 if to_row > from_row else -1)
        col_step = 0 if from_col == to_col else (1 if to_col > from_col else -1)
        
        current_row, current_col = from_row + row_step, from_col + col_step
        
        while (current_row, current_col) != (to_row, to_col):
            if self.board[current_row][current_col] != "·":
                return False
            current_row += row_step
            current_col += col_step
        
        return True
    
    def make_move(self, from_pos, to_pos):
        """Execute a move"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]
        
        # Capture piece if present
        if captured != "·":
            color = "white" if captured in "♔♕♖♗♘♙" else "black"
            self.captured_pieces[color].append(captured)
        
        # Move piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = "·"
        
        # Record move
        move_notation = f"{chr(from_col + ord('a'))}{8-from_row}{chr(to_col + ord('a'))}{8-to_row}"
        self.move_history.append(move_notation)
        
        # Check for checkmate (simplified - just check if king captured)
        if captured in ["♔", "♚"]:
            self.game_over = True
            self.winner = self.current_turn
        
        # Switch turns
        self.current_turn = self.player2 if self.current_turn == self.player1 else self.player1

class CheckersGame:
    """Checkers implementation"""
    
    def __init__(self, player1, player2):
        self.player1 = player1  # Red
        self.player2 = player2  # Black
        self.current_turn = player1
        self.board = self.create_board()
        self.move_history = []
        self.game_over = False
        self.winner = None
    
    def create_board(self):
        """Initialize checkers board"""
        board = [
            ["·", "⚫", "·", "⚫", "·", "⚫", "·", "⚫"],
            ["⚫", "·", "⚫", "·", "⚫", "·", "⚫", "·"],
            ["·", "⚫", "·", "⚫", "·", "⚫", "·", "⚫"],
            ["·"] * 8,
            ["·"] * 8,
            ["🔴", "·", "🔴", "·", "🔴", "·", "🔴", "·"],
            ["·", "🔴", "·", "🔴", "·", "🔴", "·", "🔴"],
            ["🔴", "·", "🔴", "·", "🔴", "·", "🔴", "·"]
        ]
        return board
    
    def display_board(self):
        """Display checkers board"""
        lines = ["```\n  1 2 3 4 5 6 7 8"]
        for i, row in enumerate(self.board):
            line = f"{chr(65+i)} " + " ".join(row) + f" {chr(65+i)}"
            lines.append(line)
        lines.append("  1 2 3 4 5 6 7 8\n```")
        return "\n".join(lines)
    
    def parse_move(self, move_str):
        """Parse checkers move like A1B2"""
        if len(move_str) < 4:
            return None
        
        try:
            from_row = ord(move_str[0].upper()) - ord('A')
            from_col = int(move_str[1]) - 1
            to_row = ord(move_str[2].upper()) - ord('A')
            to_col = int(move_str[3]) - 1
            
            if all(0 <= x < 8 for x in [from_row, from_col, to_row, to_col]):
                return ((from_row, from_col), (to_row, to_col))
        except:
            pass
        return None
    
    def is_valid_move(self, from_pos, to_pos):
        """Validate checkers move"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        piece = self.board[from_row][from_col]
        target = self.board[to_row][to_col]
        
        # Must be valid piece and empty target
        if piece == "·" or target != "·":
            return False
        
        # Check turn
        red_pieces = ["🔴", "👑"]
        black_pieces = ["⚫", "⚪"]
        
        if self.current_turn == self.player1 and piece not in red_pieces:
            return False
        if self.current_turn == self.player2 and piece not in black_pieces:
            return False
        
        # Diagonal movement only
        row_diff = to_row - from_row
        col_diff = abs(to_col - from_col)
        
        if col_diff != abs(row_diff):
            return False
        
        # Regular pieces move forward only (kings can move any diagonal)
        if piece == "🔴" and row_diff > 0:
            return False
        if piece == "⚫" and row_diff < 0:
            return False
        
        # Single move or jump
        if abs(row_diff) == 1:
            return True
        elif abs(row_diff) == 2:
            # Jump over opponent
            mid_row = (from_row + to_row) // 2
            mid_col = (from_col + to_col) // 2
            mid_piece = self.board[mid_row][mid_col]
            
            if piece in red_pieces:
                return mid_piece in black_pieces
            else:
                return mid_piece in red_pieces
        
        return False
    
    def make_move(self, from_pos, to_pos):
        """Execute checkers move"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        piece = self.board[from_row][from_col]
        
        # Handle jump
        if abs(to_row - from_row) == 2:
            mid_row = (from_row + to_row) // 2
            mid_col = (from_col + to_col) // 2
            self.board[mid_row][mid_col] = "·"
        
        # Move piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = "·"
        
        # Check for king promotion
        if piece == "🔴" and to_row == 0:
            self.board[to_row][to_col] = "👑"
        elif piece == "⚫" and to_row == 7:
            self.board[to_row][to_col] = "⚪"
        
        # Check win condition (opponent has no pieces)
        red_count = sum(row.count("🔴") + row.count("👑") for row in self.board)
        black_count = sum(row.count("⚫") + row.count("⚪") for row in self.board)
        
        if red_count == 0:
            self.game_over = True
            self.winner = self.player2
        elif black_count == 0:
            self.game_over = True
            self.winner = self.player1
        
        # Switch turns
        self.current_turn = self.player2 if self.current_turn == self.player1 else self.player1

class ChessCheckers(commands.Cog):
    """Chess and Checkers games"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_chess_games = {}
        self.active_checkers_games = {}
    
    @app_commands.command(name="chess", description="Start a chess game with another player")
    async def chess(self, interaction: discord.Interaction, opponent: discord.Member):
        """Start chess game"""
        if opponent.bot:
            await interaction.response.send_message("❌ Cannot play against bots!")
            return
        
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ Cannot play against yourself!")
            return
        
        game_id = f"{interaction.guild.id}_{interaction.channel.id}"
        
        if game_id in self.active_chess_games:
            await interaction.response.send_message("❌ There's already a chess game in this channel!")
            return
        
        game = ChessGame(interaction.user, opponent)
        self.active_chess_games[game_id] = game
        
        embed = discord.Embed(
            title="♟️ Chess Game Started!",
            description=f"**White:** {interaction.user.mention}\n**Black:** {opponent.mention}\n\n"
                       f"{game.display_board()}\n\n"
                       f"**{interaction.user.mention}'s turn** (White)\n"
                       f"Use: `/chessmove e2e4` (from-square to-square)",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="chessmove", description="Make a chess move")
    async def chessmove(self, interaction: discord.Interaction, move: str):
        """Make a chess move"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}"
        
        if game_id not in self.active_chess_games:
            await interaction.response.send_message("❌ No active chess game in this channel! Start one with `/chess`")
            return
        
        game = self.active_chess_games[game_id]
        
        if interaction.user != game.current_turn:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        # Validate move format
        try:
            positions = game.parse_move(move.lower())
            if not positions:
                await interaction.response.send_message("❌ Invalid move format! Use: e2e4 (from-square to-square)", ephemeral=True)
                return
        except Exception as e:
            await interaction.response.send_message(f"❌ Error parsing move: {str(e)}", ephemeral=True)
            return
        
        from_pos, to_pos = positions
        
        if not game.is_valid_move(from_pos, to_pos):
            await interaction.response.send_message("❌ Invalid move! Check the rules.", ephemeral=True)
            return
        
        game.make_move(from_pos, to_pos)
        
        if game.game_over:
            # Award coins
            reward = 200
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(game.winner.id, reward, "chess_win")
            
            reward_text = f"\n+{reward} PsyCoins!" if economy_cog else ""
            embed = discord.Embed(
                title="♟️ Chess Game Over!",
                description=f"{game.display_board()}\n\n🏆 **{game.winner.mention} wins!**{reward_text}",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            del self.active_chess_games[game_id]
        else:
            embed = discord.Embed(
                title="♟️ Chess Game",
                description=f"{game.display_board()}\n\n**{game.current_turn.mention}'s turn**",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="checkers", description="Start a checkers game")
    async def checkers(self, interaction: discord.Interaction, opponent: discord.Member):
        """Start checkers game"""
        if opponent.bot:
            await interaction.response.send_message("❌ Cannot play against bots!")
            return
        
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ Cannot play against yourself!")
            return
        
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_checkers"
        
        if game_id in self.active_checkers_games:
            await interaction.response.send_message("❌ There's already a checkers game in this channel!")
            return
        
        game = CheckersGame(interaction.user, opponent)
        self.active_checkers_games[game_id] = game
        
        embed = discord.Embed(
            title="🔴 Checkers Game Started!",
            description=f"**Red (🔴):** {interaction.user.mention}\n**Black (⚫):** {opponent.mention}\n\n"
                       f"{game.display_board()}\n\n"
                       f"**{interaction.user.mention}'s turn**\n"
                       f"Use: `/checkersmove A1B2` (from to)",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="checkersmove", description="Make a checkers move")
    async def checkersmove(self, interaction: discord.Interaction, move: str):
        """Make a checkers move"""
        game_id = f"{interaction.guild.id}_{interaction.channel.id}_checkers"
        
        if game_id not in self.active_checkers_games:
            await interaction.response.send_message("❌ No active checkers game! Start one with `/checkers`")
            return
        
        game = self.active_checkers_games[game_id]
        
        if interaction.user != game.current_turn:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        # Validate move format
        try:
            positions = game.parse_move(move.upper())
            if not positions:
                await interaction.response.send_message("❌ Invalid move format! Use: A1B2 (from to)", ephemeral=True)
                return
        except Exception as e:
            await interaction.response.send_message(f"❌ Error parsing move: {str(e)}", ephemeral=True)
            return
        
        from_pos, to_pos = positions
        
        if not game.is_valid_move(from_pos, to_pos):
            await interaction.response.send_message("❌ Invalid move!", ephemeral=True)
            return
        
        game.make_move(from_pos, to_pos)
        
        if game.game_over:
            reward = 150
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(game.winner.id, reward, "checkers_win")
            
            reward_text = f"\n+{reward} PsyCoins!" if economy_cog else ""
            embed = discord.Embed(
                title="🔴 Checkers Game Over!",
                description=f"{game.display_board()}\n\n🏆 **{game.winner.mention} wins!**{reward_text}",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            del self.active_checkers_games[game_id]
        else:
            embed = discord.Embed(
                title="🔴 Checkers Game",
                description=f"{game.display_board()}\n\n**{game.current_turn.mention}'s turn**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ChessCheckers(bot))
