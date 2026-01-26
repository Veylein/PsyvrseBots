import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, List, Tuple

class BoardGamesEnhanced(commands.Cog):
    """Enhanced board games - Scrabble, Backgammon, Tetris, and more!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.player_games = {}
        
        # Scrabble setup
        self.scrabble_tiles = self._initialize_scrabble_tiles()
        self.scrabble_letter_values = {
            'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4,
            'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3,
            'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8,
            'Y': 4, 'Z': 10, '_': 0  # Blank tile
        }
        
        # Load dictionary for word validation
        self.valid_words = self._load_scrabble_dictionary()
        
        # Backgammon setup
        self.backgammon_initial_board = self._initialize_backgammon_board()
        
        # Tetris pieces
        self.tetris_pieces = {
            'I': [[1, 1, 1, 1]],
            'O': [[1, 1], [1, 1]],
            'T': [[0, 1, 0], [1, 1, 1]],
            'S': [[0, 1, 1], [1, 1, 0]],
            'Z': [[1, 1, 0], [0, 1, 1]],
            'J': [[1, 0, 0], [1, 1, 1]],
            'L': [[0, 0, 1], [1, 1, 1]]
        }

    def _initialize_scrabble_tiles(self) -> List[str]:
        """Initialize Scrabble tile bag"""
        tiles = (
            ['A'] * 9 + ['B'] * 2 + ['C'] * 2 + ['D'] * 4 + ['E'] * 12 +
            ['F'] * 2 + ['G'] * 3 + ['H'] * 2 + ['I'] * 9 + ['J'] * 1 +
            ['K'] * 1 + ['L'] * 4 + ['M'] * 2 + ['N'] * 6 + ['O'] * 8 +
            ['P'] * 2 + ['Q'] * 1 + ['R'] * 6 + ['S'] * 4 + ['T'] * 6 +
            ['U'] * 4 + ['V'] * 2 + ['W'] * 2 + ['X'] * 1 + ['Y'] * 2 +
            ['Z'] * 1 + ['_'] * 2  # Blank tiles
        )
        return tiles

    def _load_scrabble_dictionary(self) -> set:
        """Load valid Scrabble words - simplified dictionary"""
        # For now, use a basic word list - can be expanded with full dictionary
        return {
            "CAT", "DOG", "HOUSE", "TREE", "GAME", "PLAY", "WORD", "BOOK",
            "PHONE", "WATER", "LIGHT", "MUSIC", "HAPPY", "QUICK", "BROWN",
            "JUMPS", "OVER", "LAZY", "GOOD", "BEST", "FAST", "SLOW", "BIG",
            "SMALL", "HOT", "COLD", "NEW", "OLD", "YOUNG", "TALL", "SHORT",
            "LONG", "HIGH", "LOW", "NEAR", "FAR", "EARLY", "LATE", "EASY",
            "HARD", "OPEN", "CLOSE", "START", "END", "YES", "NO", "UP", "DOWN",
            "LEFT", "RIGHT", "STOP", "GO", "COME", "LEAVE", "STAY", "GIVE",
            "TAKE", "MAKE", "BREAK", "FIX", "BUILD", "HELP", "WORK", "REST",
            "EAT", "DRINK", "SLEEP", "WAKE", "WALK", "RUN", "JUMP", "SWIM",
            "FLY", "DRIVE", "RIDE", "SIT", "STAND", "LIE", "FALL", "RISE",
            "LOVE", "HATE", "LIKE", "WANT", "NEED", "HOPE", "WISH", "DREAM",
            "THINK", "KNOW", "LEARN", "TEACH", "TELL", "ASK", "ANSWER", "SAY",
            "TALK", "SPEAK", "HEAR", "LISTEN", "SEE", "LOOK", "WATCH", "READ",
            "WRITE", "DRAW", "PAINT", "SING", "DANCE", "ACT", "PLAY", "WIN",
            "LOSE", "TRY", "FAIL", "PASS", "CATCH", "THROW", "KICK", "HIT",
            "PUSH", "PULL", "LIFT", "DROP", "CARRY", "HOLD", "TOUCH", "FEEL"
        }

    def _initialize_backgammon_board(self) -> Dict:
        """Initialize Backgammon board position"""
        return {
            1: {'white': 2}, 12: {'white': 5}, 17: {'white': 3}, 19: {'white': 5},
            24: {'black': 2}, 13: {'black': 5}, 8: {'black': 3}, 6: {'black': 5},
            'bar': {'white': 0, 'black': 0},
            'off': {'white': 0, 'black': 0}
        }

    # ==================== SCRABBLE ====================
    
    @commands.command(name="scrabble")
    async def scrabble(self, ctx, opponent: Optional[discord.Member] = None):
        """🔤 Start a Scrabble game (2 players)"""
        await self._start_scrabble(ctx.author, opponent, ctx, None)

    @app_commands.command(name="scrabble", description="Start a Scrabble game")
    @app_commands.describe(opponent="Player to challenge")
    async def scrabble_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        await interaction.response.defer()
        await self._start_scrabble(interaction.user, opponent, None, interaction)

    async def _start_scrabble(self, player1, opponent, ctx, interaction):
        if player1.id in self.player_games:
            msg = "❌ You're already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if not opponent or opponent.bot:
            msg = "❌ Please specify a valid player to play against!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if opponent.id in self.player_games:
            msg = f"❌ {opponent.mention} is already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Initialize game
        game_id = f"scrabble_{player1.id}_{random.randint(1000, 9999)}"
        tile_bag = self.scrabble_tiles.copy()
        random.shuffle(tile_bag)
        
        # Draw initial tiles (7 each)
        player1_hand = [tile_bag.pop() for _ in range(7)]
        player2_hand = [tile_bag.pop() for _ in range(7)]
        
        game_state = {
            "type": "scrabble",
            "players": [player1.id, opponent.id],
            "current_turn": player1.id,
            "tile_bag": tile_bag,
            "hands": {
                player1.id: player1_hand,
                opponent.id: player2_hand
            },
            "scores": {player1.id: 0, opponent.id: 0},
            "board": [[" " for _ in range(15)] for _ in range(15)],  # 15x15 board
            "words_played": [],
            "channel": ctx.channel.id if ctx else interaction.channel.id,
            "passes": 0  # Game ends after 6 consecutive passes
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player1.id] = game_id
        self.player_games[opponent.id] = game_id

        embed = self._create_scrabble_embed(game_state, player1, opponent)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        
        # Send hands via DM
        await self._send_scrabble_hand(player1, player1_hand)
        await self._send_scrabble_hand(opponent, player2_hand)

    def _create_scrabble_embed(self, game_state, player1, player2):
        """Create Scrabble game display"""
        board = game_state["board"]
        
        # Show center 7x7 portion of board for brevity
        board_display = "```\n"
        board_display += "  | 4 5 6 7 8 9 10\n"
        board_display += "--|----------------\n"
        for i in range(4, 11):
            board_display += f"{i:2}| "
            for j in range(4, 11):
                board_display += board[i][j] + " "
            board_display += "\n"
        board_display += "```"
        
        current_player = self.bot.get_user(game_state["current_turn"])
        
        embed = discord.Embed(
            title="🔤 Scrabble",
            description=board_display,
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Players",
            value=f"**{player1.display_name}**: {game_state['scores'][player1.id]} pts\n"
                  f"**{player2.display_name}**: {game_state['scores'][player2.id]} pts",
            inline=False
        )
        embed.add_field(
            name="Current Turn",
            value=f"**{current_player.display_name}**",
            inline=False
        )
        embed.add_field(
            name="Tiles Remaining",
            value=f"{len(game_state['tile_bag'])} tiles",
            inline=False
        )
        embed.add_field(
            name="How to Play",
            value="Use `L!scrabble play <word> <row> <col> <h/v>` to place a word\n"
                  "`L!scrabble hand` - View your hand (DM)\n"
                  "`L!scrabble pass` - Pass your turn\n"
                  "`L!scrabble swap <letters>` - Swap tiles",
            inline=False
        )
        
        return embed

    async def _send_scrabble_hand(self, player, hand):
        """Send player's hand via DM"""
        try:
            hand_str = " ".join(hand)
            values_str = " ".join([str(self.scrabble_letter_values.get(letter, 0)) for letter in hand])
            
            embed = discord.Embed(
                title="🔤 Your Scrabble Hand",
                description=f"**Letters:** `{hand_str}`\n**Values:** `{values_str}`",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Keep this secret! Don't share your hand.")
            
            await player.send(embed=embed)
        except:
            pass  # If DMs are closed, skip

    @commands.command(name="scrabble-play")
    async def scrabble_play(self, ctx, word: str, row: int, col: int, direction: str):
        """Play a word in Scrabble"""
        if ctx.author.id not in self.player_games:
            await ctx.send("❌ You're not in a Scrabble game!")
            return
        
        game_id = self.player_games[ctx.author.id]
        game_state = self.active_games[game_id]
        
        if game_state["type"] != "scrabble":
            return
        
        if game_state["current_turn"] != ctx.author.id:
            await ctx.send("❌ It's not your turn!")
            return
        
        word = word.upper()
        direction = direction.lower()
        
        # Validate word
        if word not in self.valid_words:
            await ctx.send(f"❌ **{word}** is not a valid word!")
            return
        
        # Validate direction
        if direction not in ['h', 'v']:
            await ctx.send("❌ Direction must be 'h' (horizontal) or 'v' (vertical)!")
            return
        
        # Check if word can be placed
        hand = game_state["hands"][ctx.author.id]
        if not self._can_place_word(word, hand, game_state["board"], row, col, direction):
            await ctx.send("❌ You don't have the right tiles or position is invalid!")
            return
        
        # Place word and calculate score
        score = self._place_scrabble_word(game_state, word, row, col, direction, ctx.author.id)
        
        game_state["scores"][ctx.author.id] += score
        game_state["words_played"].append(word)
        game_state["passes"] = 0
        
        # Refill hand
        self._refill_scrabble_hand(game_state, ctx.author.id)
        
        # Switch turn
        players = game_state["players"]
        current_idx = players.index(ctx.author.id)
        game_state["current_turn"] = players[(current_idx + 1) % 2]
        
        await ctx.send(f"✅ **{word}** played for **{score} points**!")
        
        # Update board display
        player1 = self.bot.get_user(players[0])
        player2 = self.bot.get_user(players[1])
        embed = self._create_scrabble_embed(game_state, player1, player2)
        await ctx.send(embed=embed)
        
        # Send updated hand
        await self._send_scrabble_hand(ctx.author, game_state["hands"][ctx.author.id])

    def _can_place_word(self, word: str, hand: List[str], board: List[List[str]], 
                        row: int, col: int, direction: str) -> bool:
        """Check if word can be placed"""
        # Basic validation - can be expanded
        if direction == 'h':
            if col + len(word) > 15:
                return False
        else:
            if row + len(word) > 15:
                return False
        
        # Check if player has tiles
        temp_hand = hand.copy()
        for letter in word:
            if letter in temp_hand:
                temp_hand.remove(letter)
            elif '_' in temp_hand:  # Blank tile
                temp_hand.remove('_')
            else:
                return False
        
        return True

    def _place_scrabble_word(self, game_state: Dict, word: str, row: int, col: int, 
                            direction: str, player_id: int) -> int:
        """Place word on board and return score"""
        score = 0
        board = game_state["board"]
        hand = game_state["hands"][player_id]
        
        for i, letter in enumerate(word):
            if direction == 'h':
                board[row][col + i] = letter
            else:
                board[row + i][col] = letter
            
            # Remove tile from hand
            if letter in hand:
                hand.remove(letter)
            elif '_' in hand:
                hand.remove('_')
            
            score += self.scrabble_letter_values.get(letter, 0)
        
        return score

    def _refill_scrabble_hand(self, game_state: Dict, player_id: int):
        """Refill player's hand to 7 tiles"""
        hand = game_state["hands"][player_id]
        tile_bag = game_state["tile_bag"]
        
        while len(hand) < 7 and tile_bag:
            hand.append(tile_bag.pop())

    # ==================== BACKGAMMON ====================
    
    @commands.command(name="backgammon")
    async def backgammon(self, ctx, opponent: discord.Member):
        """🎲 Start a Backgammon game"""
        await self._start_backgammon(ctx.author, opponent, ctx, None)

    @app_commands.command(name="backgammon", description="Start a Backgammon game")
    @app_commands.describe(opponent="Player to challenge")
    async def backgammon_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        await interaction.response.defer()
        await self._start_backgammon(interaction.user, opponent, None, interaction)

    async def _start_backgammon(self, player1, opponent, ctx, interaction):
        if player1.id in self.player_games:
            msg = "❌ You're already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        if opponent.bot or opponent.id in self.player_games:
            msg = "❌ That player cannot start a game right now!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Initialize game
        game_id = f"backgammon_{player1.id}_{random.randint(1000, 9999)}"
        
        # Roll for first turn
        p1_roll = random.randint(1, 6)
        p2_roll = random.randint(1, 6)
        while p1_roll == p2_roll:
            p1_roll = random.randint(1, 6)
            p2_roll = random.randint(1, 6)
        
        first_player = player1.id if p1_roll > p2_roll else opponent.id
        
        game_state = {
            "type": "backgammon",
            "players": [player1.id, opponent.id],
            "colors": {player1.id: "white", opponent.id: "black"},
            "current_turn": first_player,
            "board": self._initialize_backgammon_board(),
            "dice": [],
            "moves_remaining": [],
            "channel": ctx.channel.id if ctx else interaction.channel.id
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player1.id] = game_id
        self.player_games[opponent.id] = game_id

        embed = self._create_backgammon_embed(game_state, player1, opponent, p1_roll, p2_roll)
        
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    def _create_backgammon_embed(self, game_state, player1, player2, roll1=None, roll2=None):
        """Create Backgammon game display"""
        board = game_state["board"]
        
        # Simplified board display
        board_display = "```\n"
        board_display += "13 14 15 16 17 18 | BAR | 19 20 21 22 23 24\n"
        board_display += "──────────────────┼─────┼──────────────────\n"
        
        # Show point counts (simplified)
        for point in range(13, 25):
            if point in board:
                count = sum(board[point].values())
                board_display += f" {count:2} "
            else:
                board_display += "  . "
        
        board_display += "\n"
        board_display += "12 11 10  9  8  7 | BAR |  6  5  4  3  2  1\n"
        board_display += "```"
        
        current_player = self.bot.get_user(game_state["current_turn"])
        
        embed = discord.Embed(
            title="🎲 Backgammon",
            description=board_display,
            color=discord.Color.orange()
        )
        
        if roll1 and roll2:
            embed.add_field(
                name="Opening Roll",
                value=f"{player1.display_name}: **{roll1}**\n{player2.display_name}: **{roll2}**",
                inline=False
            )
        
        p1_color = "⚪" if game_state["colors"][player1.id] == "white" else "⚫"
        p2_color = "⚪" if game_state["colors"][player2.id] == "white" else "⚫"
        
        embed.add_field(
            name="Players",
            value=f"{p1_color} {player1.display_name}\n{p2_color} {player2.display_name}",
            inline=False
        )
        embed.add_field(
            name="Current Turn",
            value=f"**{current_player.display_name}**",
            inline=False
        )
        embed.add_field(
            name="How to Play",
            value="`L!bg roll` - Roll dice\n"
                  "`L!bg move <from> <to>` - Move a checker\n"
                  "`L!bg quit` - Quit game",
            inline=False
        )
        
        return embed

    # ==================== TETRIS ====================
    
    @commands.command(name="tetris")
    async def tetris(self, ctx):
        """🟦 Play single-player Tetris!"""
        await self._start_tetris(ctx.author, ctx, None)

    @app_commands.command(name="tetris", description="Play single-player Tetris!")
    async def tetris_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._start_tetris(interaction.user, None, interaction)

    async def _start_tetris(self, player, ctx, interaction):
        if player.id in self.player_games:
            msg = "❌ You're already in a game!"
            if interaction:
                await interaction.followup.send(msg)
            else:
                await ctx.send(msg)
            return

        # Initialize game
        game_id = f"tetris_{player.id}_{random.randint(1000, 9999)}"
        
        game_state = {
            "type": "tetris",
            "player": player.id,
            "board": [[0 for _ in range(10)] for _ in range(20)],  # 10x20 grid
            "current_piece": self._get_random_piece(),
            "next_piece": self._get_random_piece(),
            "piece_x": 3,  # Starting X position
            "piece_y": 0,  # Starting Y position
            "score": 0,
            "level": 1,
            "lines_cleared": 0,
            "game_over": False,
            "channel": ctx.channel.id if ctx else interaction.channel.id
        }
        
        self.active_games[game_id] = game_state
        self.player_games[player.id] = game_id

        embed = self._create_tetris_embed(game_state, player)
        view = TetrisView(self, game_id, player.id)
        
        if interaction:
            msg = await interaction.followup.send(embed=embed, view=view)
        else:
            msg = await ctx.send(embed=embed, view=view)
        
        game_state["message"] = msg

    def _get_random_piece(self) -> Dict:
        """Get random Tetris piece"""
        piece_type = random.choice(list(self.tetris_pieces.keys()))
        return {
            "type": piece_type,
            "shape": self.tetris_pieces[piece_type],
            "rotation": 0
        }

    def _create_tetris_embed(self, game_state, player):
        """Create Tetris game display"""
        board = game_state["board"]
        piece = game_state["current_piece"]
        px, py = game_state["piece_x"], game_state["piece_y"]
        
        # Create display board with current piece
        display_board = [row[:] for row in board]  # Copy
        
        # Add current piece to display
        piece_shape = piece["shape"]
        for y, row in enumerate(piece_shape):
            for x, cell in enumerate(row):
                if cell and 0 <= py + y < 20 and 0 <= px + x < 10:
                    display_board[py + y][px + x] = 1
        
        # Create visual
        board_display = "```\n"
        board_display += "╔" + "═" * 20 + "╗\n"
        for row in display_board[:10]:  # Show top 10 rows
            board_display += "║"
            for cell in row:
                board_display += "██" if cell else "  "
            board_display += "║\n"
        board_display += "╚" + "═" * 20 + "╝\n"
        board_display += "```"
        
        piece_symbols = {
            'I': '🟦', 'O': '🟨', 'T': '🟪',
            'S': '🟩', 'Z': '🟥', 'J': '🟦', 'L': '🟧'
        }
        
        embed = discord.Embed(
            title="🟦 Tetris",
            description=board_display,
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Score",
            value=f"**{game_state['score']}**",
            inline=True
        )
        embed.add_field(
            name="Level",
            value=f"**{game_state['level']}**",
            inline=True
        )
        embed.add_field(
            name="Lines",
            value=f"**{game_state['lines_cleared']}**",
            inline=True
        )
        embed.add_field(
            name="Current Piece",
            value=piece_symbols.get(piece["type"], "🟦"),
            inline=True
        )
        embed.add_field(
            name="Next Piece",
            value=piece_symbols.get(game_state["next_piece"]["type"], "🟦"),
            inline=True
        )
        
        if game_state["game_over"]:
            embed.title = "💀 Game Over!"
            embed.color = discord.Color.red()
            embed.add_field(
                name="Final Score",
                value=f"**{game_state['score']} points**",
                inline=False
            )
        
        return embed

    def _move_piece(self, game_state: Dict, dx: int, dy: int) -> bool:
        """Move piece by dx, dy. Returns True if successful."""
        new_x = game_state["piece_x"] + dx
        new_y = game_state["piece_y"] + dy
        
        if self._is_valid_position(game_state, new_x, new_y):
            game_state["piece_x"] = new_x
            game_state["piece_y"] = new_y
            return True
        return False

    def _is_valid_position(self, game_state: Dict, x: int, y: int) -> bool:
        """Check if piece position is valid"""
        piece_shape = game_state["current_piece"]["shape"]
        board = game_state["board"]
        
        for py, row in enumerate(piece_shape):
            for px, cell in enumerate(row):
                if cell:
                    new_x = x + px
                    new_y = y + py
                    
                    # Check boundaries
                    if new_x < 0 or new_x >= 10 or new_y >= 20:
                        return False
                    
                    # Check collision with existing pieces
                    if new_y >= 0 and board[new_y][new_x]:
                        return False
        
        return True

    def _lock_piece(self, game_state: Dict):
        """Lock piece in place and spawn new one"""
        piece = game_state["current_piece"]
        px, py = game_state["piece_x"], game_state["piece_y"]
        board = game_state["board"]
        
        # Lock piece
        for y, row in enumerate(piece["shape"]):
            for x, cell in enumerate(row):
                if cell and py + y >= 0:
                    board[py + y][px + x] = 1
        
        # Clear lines
        lines_cleared = self._clear_lines(game_state)
        
        if lines_cleared > 0:
            game_state["lines_cleared"] += lines_cleared
            game_state["score"] += [0, 100, 300, 500, 800][lines_cleared] * game_state["level"]
            
            # Level up every 10 lines
            game_state["level"] = game_state["lines_cleared"] // 10 + 1
        
        # Spawn new piece
        game_state["current_piece"] = game_state["next_piece"]
        game_state["next_piece"] = self._get_random_piece()
        game_state["piece_x"] = 3
        game_state["piece_y"] = 0
        
        # Check game over
        if not self._is_valid_position(game_state, 3, 0):
            game_state["game_over"] = True

    def _clear_lines(self, game_state: Dict) -> int:
        """Clear completed lines and return count"""
        board = game_state["board"]
        lines_to_clear = []
        
        for y, row in enumerate(board):
            if all(cell for cell in row):
                lines_to_clear.append(y)
        
        for y in lines_to_clear:
            del board[y]
            board.insert(0, [0] * 10)
        
        return len(lines_to_clear)

    def _rotate_piece(self, game_state: Dict):
        """Rotate piece clockwise"""
        piece = game_state["current_piece"]
        shape = piece["shape"]
        
        # Rotate 90 degrees clockwise
        rotated = [[shape[y][x] for y in range(len(shape) - 1, -1, -1)] 
                   for x in range(len(shape[0]))]
        
        # Test if rotation is valid
        old_shape = piece["shape"]
        piece["shape"] = rotated
        
        if not self._is_valid_position(game_state, game_state["piece_x"], game_state["piece_y"]):
            piece["shape"] = old_shape  # Revert
        else:
            piece["rotation"] = (piece["rotation"] + 1) % 4

class TetrisView(discord.ui.View):
    """Interactive Tetris controls"""
    
    def __init__(self, cog, game_id: str, player_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.game_id = game_id
        self.player_id = player_id

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, row=0)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        game_state = self.cog.active_games.get(self.game_id)
        if not game_state or game_state["game_over"]:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        self.cog._move_piece(game_state, -1, 0)
        
        embed = self.cog._create_tetris_embed(game_state, interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.primary, row=0)
    async def rotate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        game_state = self.cog.active_games.get(self.game_id)
        if not game_state or game_state["game_over"]:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        self.cog._rotate_piece(game_state)
        
        embed = self.cog._create_tetris_embed(game_state, interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, row=0)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        game_state = self.cog.active_games.get(self.game_id)
        if not game_state or game_state["game_over"]:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        self.cog._move_piece(game_state, 1, 0)
        
        embed = self.cog._create_tetris_embed(game_state, interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬇️ Drop", style=discord.ButtonStyle.success, row=1)
    async def drop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        game_state = self.cog.active_games.get(self.game_id)
        if not game_state or game_state["game_over"]:
            await interaction.response.send_message("❌ Game is over!", ephemeral=True)
            return
        
        # Drop piece down
        while self.cog._move_piece(game_state, 0, 1):
            pass
        
        # Lock piece
        self.cog._lock_piece(game_state)
        
        embed = self.cog._create_tetris_embed(game_state, interaction.user)
        
        if game_state["game_over"]:
            # Award coins
            economy_cog = self.cog.bot.get_cog("Economy")
            if economy_cog:
                coins = game_state["score"] // 10
                economy_cog.add_coins(interaction.user.id, coins, "tetris")
                embed.add_field(name="Reward", value=f"+{coins} PsyCoins", inline=False)
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            del self.cog.player_games[self.player_id]
            del self.cog.active_games[self.game_id]
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Quit", style=discord.ButtonStyle.danger, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        game_state = self.cog.active_games.get(self.game_id)
        if game_state:
            del self.cog.player_games[self.player_id]
            del self.cog.active_games[self.game_id]
        
        await interaction.response.edit_message(content="Game ended!", view=None)

async def setup(bot):
    await bot.add_cog(BoardGamesEnhanced(bot))
