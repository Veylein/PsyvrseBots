# FULL DOCUMENTATION - PART 5B: BOARD GAMES & UNO SYSTEM

**Project:** Ludus Bot  
**Coverage:** Board Games (Tic-Tac-Toe, Connect 4, Hangman, Scrabble, Backgammon, Tetris, Chess, Checkers) + UNO System (4 Variants)  
**Total Lines:** 11,138 lines of code (LARGEST PART OF ENTIRE PROJECT)  
**Status:** ✅ COMPLETE  
**Date:** February 2026

---

## Table of Contents

1. [Part 5B Overview](#1-part-5b-overview)
2. [Tic-Tac-Toe System](#2-tic-tac-toe-system)
3. [Connect 4](#3-connect-4)
4. [Hangman](#4-hangman)
5. [Enhanced Board Games](#5-enhanced-board-games)
6. [Chess System](#6-chess-system)
7. [Checkers System](#7-checkers-system)
8. [UNO System - Overview](#8-uno-system-overview)
9. [UNO Classic](#9-uno-classic)
10. [UNO Flip](#10-uno-flip)
11. [UNO No Mercy](#11-uno-no-mercy)
12. [UNO No Mercy+](#12-uno-no-mercy-plus)
13. [Commands Reference](#13-commands-reference)
14. [Summary](#14-summary)

---

## 1. PART 5B OVERVIEW

**Files:**  
- `cogs/boardgames.py` (1,383 lines) - Tic-Tac-Toe, Connect 4, Hangman  
- `cogs/boardgames_enhanced.py` (811 lines) - Scrabble, Backgammon, Tetris  
- `cogs/chess_checkers.py` (1,947 lines) - Chess & Checkers with PIL rendering  
- `cogs/uno/classic.py` (5,506 lines) - **LARGEST SINGLE FILE**  
- `cogs/uno/flip.py` (355 lines)  
- `cogs/uno/no_mercy.py` (167 lines)  
- `cogs/uno/no_mercy_plus.py` (303 lines)  
- `cogs/uno/uno_logic.py` (657 lines) - Shared logic & translations  
- `cogs/uno/__init__.py` (9 lines)

### Part 5B Statistics

**Total Lines:** 11,138  
**Board Games:** 4,141 lines (37%)  
**UNO System:** 6,997 lines (63%)  

**Game Count:**
- 8 board games (Tic-Tac-Toe, Connect 4, Hangman, Scrabble, Backgammon, Tetris, Chess, Checkers)
- 4 UNO variants (Classic, Flip, No Mercy, No Mercy+)
- **12 games total** in Part 5B

**Key Technologies:**
- Python `chess` library for chess engine
- PIL (Pillow) for board rendering (chess & checkers)
- Interactive Discord UI (modals, buttons, dropdowns)
- Minimax AI with alpha-beta pruning (Tic-Tac-Toe)
- Bot opponents with difficulty levels
- Lobby system for multiplayer matchmaking
- Multi-language support (EN/PL for UNO)
- Custom emoji system with JSON mapping

---

## 2. TIC-TAC-TOE SYSTEM

**File:** `cogs/boardgames.py` Lines 1-730  
**Players:** 1-2 (vs bot or player)  
**Board Sizes:** 3x3, 5x5  
**Modes:** Normal, Disappearing Symbols

### Lobby System

**Features:**
- Host creates lobby with `/tictactoe`
- Configurable settings (size, starter, mode)
- Join/leave buttons
- Bot opponent option (🤖)
- Start button (enabled when 2 players)

**Lobby Settings:**
```python
lobby_state = {
    'hostId': str(user.id),
    'players': [str(user.id)],
    'maxPlayers': 2,
    'boardSize': 3,  # 3 or 5
    'starter': 'host_starts',  # host_starts, guest_starts, random
    'mode': 'normal',  # normal or sliding
    'messageId': None,
    'last_activity': time.time(),
    'start_time': time.time()
}
```

**Settings Customization:**
- **Board Size:** 3x3 (classic) or 5x5 (larger)
- **Starter:** Host starts, Guest starts, or Random
- **Mode:** Normal or Disappearing Symbols

### Game Modes

**Normal Mode:**
- Standard Tic-Tac-Toe rules
- 3x3 requires 3 in a row
- 4x4/5x5 requires 4 in a row
- First to complete line wins

**Disappearing Symbols Mode:**
```python
if game.get('mode') == 'sliding':
    hist = game['history'][str(player_num)]
    hist.append(idx)
    # 3x3: max 3 symbols, 5x5: max 4 symbols
    limit = 3 if size == 3 else 4
    if len(hist) > limit:
        old_idx = hist.pop(0)  # Remove oldest symbol
        if game['board'][old_idx] == player_num:
            game['board'][old_idx] = 0  # Clear from board
```

**Strategy:** Forces tactical play - old symbols vanish, preventing simple strategies.

### AI System (Minimax with Alpha-Beta Pruning)

**Implementation (Lines 110-265):**
```python
def minimax(board, size, depth, is_maximizing, alpha, beta, player, opponent, max_depth):
    """Minimax algorithm with alpha-beta pruning and depth limit"""
    winner = check_winner(board, size)
    
    # Terminal states
    if winner == player:
        return 100 - depth  # Prefer faster wins
    elif winner == opponent:
        return depth - 100  # Prefer slower losses
    elif all(cell != 0 for cell in board):
        return 0  # Draw
    
    # Depth limit - use heuristic evaluation for larger boards
    if depth >= max_depth:
        return evaluate_position(board, size, player, opponent)
    
    if is_maximizing:
        max_eval = -float('inf')
        for i in range(len(board)):
            if board[i] == 0:
                board[i] = player
                eval_score = minimax(board, size, depth + 1, False, alpha, beta, player, opponent, max_depth)
                board[i] = 0
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Beta cutoff
        return max_eval
    else:
        min_eval = float('inf')
        for i in range(len(board)):
            if board[i] == 0:
                board[i] = opponent
                eval_score = minimax(board, size, depth + 1, True, alpha, beta, player, opponent, max_depth)
                board[i] = 0
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha cutoff
        return min_eval
```

**AI Difficulty:**
- **3x3:** Unbeatable (full search depth 9, perfect play)
- **4x4:** Very strong (depth 5, highly competitive)
- **5x5:** Strong (depth 3 with heuristics, challenging)

**Heuristic Evaluation (Lines 145-175):**
```python
def evaluate_position(board, size, player, opponent):
    """Heuristic evaluation for larger boards"""
    score = 0
    
    for row in range(size):
        for col in range(size):
            if board[row * size + col] != 0:
                continue
            threats = 0
            opportunities = 0
            
            # Check row potential
            row_player = sum(1 for c in range(size) if board[row * size + c] == player)
            row_opponent = sum(1 for c in range(size) if board[row * size + c] == opponent)
            if row_opponent == 0 and row_player > 0:
                opportunities += row_player ** 2  # Exponential value
            if row_player == 0 and row_opponent > 0:
                threats += row_opponent ** 2
            
            # Check column potential
            col_player = sum(1 for r in range(size) if board[r * size + col] == player)
            col_opponent = sum(1 for r in range(size) if board[r * size + col] == opponent)
            if col_opponent == 0 and col_player > 0:
                opportunities += col_player ** 2
            if col_player == 0 and col_opponent > 0:
                threats += col_opponent ** 2
    
    return opportunities - threats  # Positive = good for AI
```

### Rematch System

**Flow:**
1. Game ends → Rematch button appears (60s timeout)
2. Either player clicks "Rematch"
3. If opponent is bot → Instant new game
4. If opponent is human → Accept/Deny buttons sent
5. Accept → New game with swapped starting player
6. Deny → Rematch cancelled

**Code (Lines 685-768):**
```python
async def handle_rematch_request(self, interaction, cid):
    game_id = cid[len('ttt_rematch_'):]
    requester_id = str(interaction.user.id)
    
    rematch_state = self.bot.pending_rematches.get(game_id)
    opponent_id = p2_original if requester_id == p1_original else p1_original
    
    if opponent_id == 'BOT_AI':
        # Instant rematch vs bot
        await self.start_rematch_game(interaction, game_id, rematch_state, p1_original, p2_original)
    else:
        # Send request to opponent
        await interaction.channel.send(
            f"Rematch Request: {opponent_mention}, {interaction.user.mention} asks for a **rematch**!",
            view=self.generate_rematch_accept_view(game_id, opponent_id)
        )
```

### Rewards

**Win Rewards:**
- **50 PsyCoins** for winning
- **40% chance** for TCG card reward (basic tier)
- **Game stats** recorded (wins, playtime, category: "board_games")

---

## 3. CONNECT 4

**File:** `cogs/boardgames.py` Lines 770-1080  
**Players:** 1-2 (vs AI or player)  
**Board:** 6 rows × 7 columns  
**Goal:** Connect 4 pieces in a row (horizontal, vertical, or diagonal)

### Game Mechanics

**Board Display (Lines 927-950):**
```
🔴 Connect 4 🟡
```
 1   2   3   4   5   6   7
╔═══╦═══╦═══╦═══╦═══╦═══╦═══╗
║   ║   ║   ║   ║   ║   ║   ║
╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣
║   ║   ║   ║   ║   ║   ║   ║
╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣
║   ║ 🔴 ║   ║   ║   ║   ║   ║
╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣
║   ║ 🟡 ║ 🔴 ║   ║   ║   ║   ║
╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣
║ 🔴 ║ 🔴 ║ 🟡 ║ 🟡 ║   ║   ║   ║
╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣
║ 🟡 ║ 🟡 ║ 🔴 ║ 🔴 ║ 🔴 ║   ║   ║
╚═══╩═══╩═══╩═══╩═══╩═══╩═══╝
```

**Drop Piece:**
```python
# Find lowest empty row in column
col_idx = column - 1
row_idx = None
for r in range(5, -1, -1):  # Bottom to top
    if game_state["board"][r][col_idx] == " ":
        row_idx = r
        break

if row_idx is None:
    return "Column is full!"

# Place piece
symbol = game_state["symbols"][player.id]  # 🔴 or 🟡
game_state["board"][row_idx][col_idx] = symbol
```

### Win Detection (Lines 1026-1057)

**Algorithm checks 4 directions from played piece:**
```python
def _check_c4_winner(self, board, row, col):
    symbol = board[row][col]
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # →, ↓, ↘, ↙
    
    for dr, dc in directions:
        count = 1  # Current piece
        
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
            return True  # Winner!
    
    return False
```

### AI Strategy (Lines 1058-1100)

**AI plays strategically in priority order:**

**1. Win Immediately:**
```python
for col in available:
    test_board = [row[:] for row in board]
    for r in range(5, -1, -1):
        if test_board[r][col] == " ":
            test_board[r][col] = ai_symbol
            if self._check_c4_winner(test_board, r, col):
                return col  # Winning move!
            break
```

**2. Block Player Win:**
```python
for col in available:
    test_board = [row[:] for row in board]
    for r in range(5, -1, -1):
        if test_board[r][col] == " ":
            test_board[r][col] = player_symbol
            if self._check_c4_winner(test_board, r, col):
                return col  # Block this!
            break
```

**3. Prefer Center Columns:**
```python
center_cols = [3, 2, 4, 1, 5, 0, 6]  # Center-out priority
for col in center_cols:
    if col in available:
        # Check if doesn't give opponent win opportunity above
        if row_idx > 0:
            test_board[row_idx][col] = ai_symbol
            test_board[row_idx - 1][col] = player_symbol
            if not self._check_c4_winner(test_board, row_idx - 1, col):
                return col
```

**4. Fallback:** First available column

### Rewards

- **75 PsyCoins** for winning
- Game stats recorded

---

## 4. HANGMAN

**File:** `cogs/boardgames.py` Lines 1082-1383  
**Players:** 1 (solo)  
**Max Wrong:** 6 guesses  
**Hints:** 2 per game (20 coins penalty each)

### Word Categories (Lines 1096-1107)

**8 Categories with themed words:**
```python
word_categories = {
    "Animals": ["ELEPHANT", "GIRAFFE", "PENGUIN", "DOLPHIN", ...],
    "Games": ["MINECRAFT", "FORTNITE", "POKEMON", "ZELDA", ...],
    "Movies": ["AVATAR", "INCEPTION", "GLADIATOR", "TITANIC", ...],
    "Food": ["PIZZA", "BURGER", "SUSHI", "TACO", ...],
    "Countries": ["AMERICA", "BRAZIL", "CANADA", "FRANCE", ...],
    "Tech": ["COMPUTER", "INTERNET", "SOFTWARE", "HARDWARE", ...],
    "Space": ["GALAXY", "PLANET", "ASTRONAUT", "ROCKET", ...],
    "Music": ["GUITAR", "PIANO", "DRUMS", "VIOLIN", ...]
}
```

### Hangman Stages (Lines 1137-1155)

**Visual progression (7 stages):**
```
Stage 0 (start):
  +---+
      |
      |
      |
     ===

Stage 1:
  +---+
  O   |
      |
      |
     ===

Stage 6 (game over):
  +---+
  O   |
 /|\  |
 / \  |
     ===
```

### Gameplay (Lines 1189-1294)

**Letter Guess:**
```python
@commands.Cog.listener()
async def on_message(self, message):
    # Check if player is in hangman game
    game_id = self.player_games.get(message.author.id)
    game_state = self.active_games.get(game_id)
    
    if not game_state or game_state["type"] != "hangman":
        return
    
    content = message.content.upper().strip()
    
    # Process single letter guesses
    if len(content) == 1 and content.isalpha():
        guess = content
        
        if guess in game_state["guessed"]:
            await message.channel.send(f"❌ You already guessed **{guess}**!")
            return
        
        game_state["guessed"].add(guess)
        
        if guess in game_state["word"]:
            # Correct!
            if all(c in game_state["guessed"] for c in game_state["word"]):
                # Won!
                hints_used = game_state.get("hints_used", 0)
                reward = 100 - (hints_used * 20)
                economy_cog.add_coins(message.author.id, reward, "hangman_win")
        else:
            # Wrong!
            game_state["wrong"] += 1
            if game_state["wrong"] >= game_state["max_wrong"]:
                # Lost!
                await message.channel.send(f"💀 Game Over! The word was **{game_state['word']}**")
```

**Hint System:**
```python
if content == "HINT":
    if game_state.get("hints_used", 0) >= 2:
        await message.channel.send("❌ You've used all your hints!")
        return
    
    # Reveal random unrevealed letter
    unrevealed = [c for c in game_state["word"] if c not in game_state["guessed"]]
    if unrevealed:
        hint_letter = random.choice(unrevealed)
        game_state["guessed"].add(hint_letter)
        game_state["hints_used"] = game_state.get("hints_used", 0) + 1
        
        await message.channel.send(f"💡 Revealed: **{hint_letter}**")
```

### Rewards

**Win Rewards (Lines 1269-1277):**
- Base: **100 PsyCoins**
- -20 coins per hint used
- Examples:
  - No hints: 100 coins
  - 1 hint: 80 coins
  - 2 hints: 60 coins

---

## 5. ENHANCED BOARD GAMES

**File:** `cogs/boardgames_enhanced.py` (811 lines)

### Scrabble (Lines 15-313)

**Players:** 2  
**Board:** 15×15 grid  
**Tiles:** 100 letter tiles with point values

**Tile Distribution:**
```python
tiles = (
    ['A'] * 9 + ['E'] * 12 + ['I'] * 9 + ['O'] * 8 +  # Vowels
    ['N'] * 6 + ['R'] * 6 + ['T'] * 6 + ['L'] * 4 +   # Common consonants
    ['S'] * 4 + ['U'] * 4 + ['D'] * 4 + ['G'] * 3 +   # Medium frequency
    ['B'] * 2 + ['C'] * 2 + ['M'] * 2 + ['P'] * 2 +   # Less common
    ['F'] * 2 + ['H'] * 2 + ['V'] * 2 + ['W'] * 2 +
    ['Y'] * 2 + ['K'] * 1 + ['J'] * 1 + ['X'] * 1 +   # Rare
    ['Q'] * 1 + ['Z'] * 1 + ['_'] * 2                 # Q, Z, Blanks
)
```

**Letter Values:**
```python
values = {
    'A': 1, 'E': 1, 'I': 1, 'O': 1, 'N': 1, 'R': 1, 'S': 1, 'T': 1, 'L': 1,  # 1 pt
    'D': 2, 'G': 2, 'U': 1,  # 2 pts
    'B': 3, 'C': 3, 'M': 3, 'P': 3, 'F': 4, 'H': 4, 'V': 4, 'W': 4, 'Y': 4,  # 3-4 pts
    'K': 5, 'J': 8, 'X': 8, 'Q': 10, 'Z': 10, '_': 0  # High value + blank
}
```

**Commands:**
- `L!scrabble play <word> <row> <col> <h/v>` - Place word (horizontal/vertical)
- `L!scrabble hand` - View your tiles (DM)
- `L!scrabble pass` - Skip turn
- `L!scrabble swap <letters>` - Exchange tiles

**Features:**
- DM-based tile privacy
- Word validation (simplified dictionary)
- Automatic tile refill (7 tiles)
- Score tracking

**Status:** Partially implemented (word placement working, premium squares not implemented)

### Backgammon (Lines 315-497)

**Players:** 2  
**Board:** 24 points  
**Pieces:** 15 checkers per player  
**Goal:** Bear off all pieces first

**Initial Board Setup:**
```python
board = {
    1: {'white': 2}, 12: {'white': 5}, 17: {'white': 3}, 19: {'white': 5},
    24: {'black': 2}, 13: {'black': 5}, 8: {'black': 3}, 6: {'black': 5},
    'bar': {'white': 0, 'black': 0},
    'off': {'white': 0, 'black': 0}
}
```

**Commands:**
- `L!bg roll` - Roll dice
- `L!bg move <from> <to>` - Move checker
- `L!bg quit` - Quit game

**Features:**
- Opening roll determines first player (higher roll starts)
- Hit opponents to send to bar
- Must re-enter from bar before other moves
- Bear off when all pieces in home board

**Status:** Partially implemented (basic structure, full rules pending)

### Tetris (Lines 499-811)

**Players:** 1 (solo)  
**Board:** 10 width × 20 height  
**Pieces:** I, O, T, S, Z, J, L

**Piece Shapes:**
```python
tetris_pieces = {
    'I': [[1, 1, 1, 1]],           # Line
    'O': [[1, 1], [1, 1]],         # Square
    'T': [[0, 1, 0], [1, 1, 1]],   # T-shape
    'S': [[0, 1, 1], [1, 1, 0]],   # S-shape
    'Z': [[1, 1, 0], [0, 1, 1]],   # Z-shape
    'J': [[1, 0, 0], [1, 1, 1]],   # J-shape
    'L': [[0, 0, 1], [1, 1, 1]]    # L-shape
}
```

**Interactive Controls (Lines 650-811):**
- **⬅️ Left** - Move piece left
- **🔄 Rotate** - Rotate piece clockwise
- **➡️ Right** - Move piece right
- **⬇️ Drop** - Hard drop (instant place)
- **❌ Quit** - End game

**Scoring:**
```python
# Lines cleared → Points × Level
points = {
    1: 100,   # Single
    2: 300,   # Double
    3: 500,   # Triple
    4: 800    # Tetris!
}
score += points[lines_cleared] * game['level']
```

**Leveling:**
- Level = (total_lines ÷ 10) + 1
- Higher levels = more points per line

**Line Clearing (Lines 763-775):**
```python
def _clear_lines(self, game_state):
    board = game_state["board"]
    lines_to_clear = []
    
    # Find completed lines
    for y, row in enumerate(board):
        if all(cell for cell in row):
            lines_to_clear.append(y)
    
    # Remove and add empty lines at top
    for y in lines_to_clear:
        del board[y]
        board.insert(0, [0] * 10)
    
    return len(lines_to_clear)
```

**Rewards:**
- Coins = Score ÷ 10
- Game stats recorded

---

## 6. CHESS SYSTEM

**File:** `cogs/chess_checkers.py` Lines 1-870  
**Library:** Python `chess` (python-chess)  
**Rendering:** PIL (Pillow) for board images  
**Players:** 1-2 (vs bot or player)

### Chess Engine Integration

**Uses `python-chess` library for:**
- Legal move validation
- Game state management
- Checkmate/stalemate detection
- Move notation parsing (e2e4, Nf3, etc.)

**Board Initialization:**
```python
import chess

board = chess.Board()  # Standard starting position
# Pieces automatically placed:
# rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

### Lobby System (Lines 249-352)

**Lobby Features:**
- Join/leave buttons
- Bot opponent option
- Board theme selection (from economy shop items)
- Start when 2 players ready

**Board Themes:**
```python
theme_map = {
    'chess_board_blue': 'blue',
    'chess_board_green': 'green',
    'chess_board_brown': 'brown',
    'chess_board_red': 'red',
    'chess_board_purple': 'purple',
    'classic': 'classic'  # Default
}
```

### Move System (Lines 114-230)

**Modal Input:**
```python
class ChessMoveModal(discord.ui.Modal):
    move_input = discord.ui.TextInput(
        label="Enter your move",
        placeholder="e.g., e2e4 or Nf3",
        max_length=10
    )
    
    async def on_submit(self, interaction):
        move_str = self.move_input.value.strip()
        move = parse_move(self.game['board'], move_str)
        
        if not move:
            return await interaction.response.send_message(
                f"❌ Invalid move: `{move_str}`",
                ephemeral=True
            )
        
        # Execute move
        self.game['board'].push(move)
        self.game['move_history'].append(move)
        
        # Check game status
        is_over, status_text = get_game_status(self.game['board'])
```

**Move Notation:**
- **Standard:** e2e4, d7d5, a1h8
- **SAN (Standard Algebraic):** Nf3, Qd4, O-O (castling)
- **Captures:** exd5, Nxd5
- **Promotions:** e8=Q, e1=N

### Game Status Detection (Chess library handles this)

**Checkmate:**
```python
if board.is_checkmate():
    winner = "White" if board.turn == chess.BLACK else "Black"
    return True, f"♔ **Checkmate!** {winner} wins!"
```

**Stalemate:**
```python
if board.is_stalemate():
    return True, "🤝 **Stalemate!** It's a draw."
```

**Other Draws:**
- Insufficient material (K vs K)
- Threefold repetition
- Fifty-move rule

### Board Rendering (PIL)

**Creates PNG image of board:**
```python
def create_board_image(board, last_move=None, board_theme='classic', piece_set='classic'):
    """Generate chess board image using PIL"""
    # Load theme colors
    if board_theme == 'blue':
        light_square = (222, 235, 247)  # Light blue
        dark_square = (100, 149, 237)   # Cornflower blue
    # ... other themes
    
    # Draw squares
    for row in range(8):
        for col in range(8):
            is_light = (row + col) % 2 == 0
            color = light_square if is_light else dark_square
            draw.rectangle([x, y, x+sq_size, y+sq_size], fill=color)
    
    # Highlight last move
    if last_move:
        from_square = last_move.from_square
        to_square = last_move.to_square
        # Draw yellow overlay on from/to squares
    
    # Draw pieces
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            # Load piece PNG and paste on board
            piece_img = Image.open(f"pieces/{piece_set}/{piece.symbol()}.png")
            board_img.paste(piece_img, (x, y), piece_img)
    
    return discord.File(buffer, filename="chess_board.png")
```

### Bot AI (Lines 865-960)

**Difficulty:** Easy (random legal move)

```python
def get_bot_move(board, difficulty='easy'):
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None
    
    if difficulty == 'easy':
        return random.choice(legal_moves)
    # Medium/Hard could use Stockfish or minimax
```

**Future Enhancements:**
- Medium: Basic evaluation (material count)
- Hard: Stockfish integration or deeper minimax

### Special Features

**Draw Offers (Lines 632-760):**
```python
# Player offers draw
game['draw_offer'] = {
    'offering_player': player_id,
    'opponent': opponent_id
}

# Opponent can accept/decline
if accept:
    # End game as draw, record stats for both
else:
    # Continue game
```

**Resign Button (Lines 584-630):**
- Instant forfeit
- Opponent wins automatically
- Awards 20 coins (30 for checkmate)

### Rewards

**Win Conditions:**
- **Checkmate:** 30 PsyCoins
- **Opponent Resigns:** 20 PsyCoins
- **Draw:** 0 PsyCoins (both players)

---

## 7. CHECKERS SYSTEM

**File:** `cogs/chess_checkers.py` Lines 1-100, 960-1339  
**Rendering:** PIL (Pillow) for board images  
**Players:** 1-2 (vs bot or player)  
**Board:** 8×8 with only dark squares used

### Board Representation

**Internal Structure:**
```python
# 8x8 board, but only 32 dark squares are playable
# Numbering: 1-32 (like official checkers notation)
#
# 8 |  1    2    3    4
# 7 |    5    6    7    8
# 6 |  9   10   11   12
# 5 |   13   14   15   16
# 4 | 17   18   19   20
# 3 |   21   22   23   24
# 2 | 25   26   27   28
# 1 |   29   30   31   32
#     a  b  c  d  e  f  g  h

board = {
    (row, col): {
        'piece': None,  # 'red', 'black', 'red_king', 'black_king'
        'playable': (row + col) % 2 == 1  # Only dark squares
    }
}
```

**Initial Setup:**
- Red: Positions 1-12 (top 3 rows)
- Black: Positions 21-32 (bottom 3 rows)
- Empty: Positions 13-20 (middle 2 rows)

### Move Notation

**Standard Format:**
- Simple move: `3b-4c` (from row 3, column b to row 4, column c)
- Jump: `3b5d` (jumps over opponent at 4c)
- Multi-jump: `3b5d7f` (captures two pieces)

**Move Validation:**
```python
def parse_checkers_move(board, move_str, current_player):
    """Parse and validate checkers move notation"""
    # Extract positions (e.g., "3b-4c" or "3b5d")
    positions = re.findall(r'(\d+)([a-h])', move_str.lower())
    
    if len(positions) < 2:
        return None
    
    from_pos = positions[0]  # (row, col)
    to_pos = positions[-1]
    
    # Check if piece exists at from_pos
    piece = board[from_pos].get('piece')
    if not piece or not piece.startswith(player_color):
        return None
    
    # Calculate move type
    row_diff = abs(to_pos[0] - from_pos[0])
    col_diff = abs(to_pos[1] - from_pos[1])
    
    if row_diff == 1 and col_diff == 1:
        # Simple move (diagonal)
        return ('move', from_pos, to_pos, None)
    elif row_diff == 2 and col_diff == 2:
        # Jump (must capture)
        captured_pos = ((from_pos[0] + to_pos[0]) // 2, 
                       (from_pos[1] + to_pos[1]) // 2)
        return ('jump', from_pos, to_pos, captured_pos)
    
    return None
```

### Game Rules

**Movement:**
- Regular pieces: Move diagonally forward only
- Kings: Move diagonally forward OR backward
- Must jump if jump is available (forced capture)

**Capturing:**
```python
def execute_checkers_move(board, from_pos, to_pos, captured):
    """Execute move and handle captures"""
    piece = board[from_pos]['piece']
    
    # Move piece
    board[from_pos]['piece'] = None
    board[to_pos]['piece'] = piece
    
    # Capture opponent piece
    if captured:
        board[captured]['piece'] = None
    
    # Check for king promotion
    if piece == 'red' and to_pos[0] == 8:
        board[to_pos]['piece'] = 'red_king'  # Reached opposite end
    elif piece == 'black' and to_pos[0] == 1:
        board[to_pos]['piece'] = 'black_king'
```

**Multi-Jump:**
```python
def check_additional_jumps(board, pos, player):
    """Check if player can make another jump from current position"""
    piece = board[pos]['piece']
    row, col = pos
    
    # Check all 4 diagonal directions
    directions = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
    
    for dr, dc in directions:
        land_pos = (row + dr, col + dc)
        mid_pos = (row + dr//2, col + dc//2)  # Jumped square
        
        # Validate: landing square empty, middle has opponent
        if (board[land_pos]['piece'] is None and
            board[mid_pos]['piece'] and
            not board[mid_pos]['piece'].startswith(player_color)):
            return True  # Can jump again!
    
    return False
```

### Modal Move Input (Lines 13-100)

**Similar to chess modal:**
```python
class CheckersMoveModal(discord.ui.Modal):
    move_input = discord.ui.TextInput(
        label="Enter your move",
        placeholder="e.g., 3b-4c or 3b5d (for jump)",
        max_length=10
    )
    
    async def on_submit(self, interaction):
        move_str = self.move_input.value.strip().lower()
        move = parse_checkers_move(self.game['board'], move_str, self.game['current_player'])
        
        if not move:
            return await interaction.response.send_message(
                f"❌ Invalid move: `{move_str}`",
                ephemeral=True
            )
        
        # Execute move
        from_pos, to_pos, captured = move
        execute_checkers_move(self.game['board'], from_pos, to_pos, captured)
        
        # Check for multi-jump
        can_jump_again = check_additional_jumps(self.game['board'], to_pos, self.game['current_player'])
        
        if not can_jump_again:
            # Switch turn
            self.game['current_player'] = 2 if self.game['current_player'] == 1 else 1
```

### Board Rendering (PIL)

**Similar structure to chess rendering:**
```python
def create_checkers_board_image(board, last_move=None):
    """Generate checkers board image"""
    # Create 8x8 board with alternating squares
    # Only draw pieces on dark squares
    # Highlight last move
    # Regular pieces: circles
    # Kings: circles with crown symbol
    
    return discord.File(buffer, filename="checkers_board.png")
```

### Bot AI (Lines 1264-1339)

**Strategy:**
1. **Capture if possible** (forced jump rule)
2. **Advance pieces** toward opponent's end
3. **Protect kings** (higher value)
4. **Random selection** among equal moves

```python
async def play_checkers_bot_move(self, channel, game_id, game):
    # Find all legal moves
    legal_moves = get_all_legal_checkers_moves(game['board'], game['current_player'])
    
    # Prioritize jumps (captures)
    jumps = [m for m in legal_moves if m['type'] == 'jump']
    if jumps:
        move = random.choice(jumps)
    else:
        move = random.choice(legal_moves)
    
    # Execute move
    execute_checkers_move(game['board'], move['from'], move['to'], move.get('captured'))
```

### Win Conditions

**Game ends when:**
1. **No pieces left** - Opponent wins
2. **No legal moves** - Opponent wins (blocked)
3. **Resign** - Opponent wins

### Rewards

- **25 PsyCoins** for winning
- Game stats recorded

---

## 8. UNO SYSTEM - OVERVIEW

**Total Lines:** 6,997 (63% of Part 5B)  
**Variants:** 4 (Classic, Flip, No Mercy, No Mercy+)  
**Languages:** EN, PL (full i18n support)

### Architecture

**Modular Design:**
```
cogs/uno/
├── classic.py (5,506 lines) - Main UNO cog, Classic variant
├── flip.py (355 lines) - Flip variant handler
├── no_mercy.py (167 lines) - No Mercy handler
├── no_mercy_plus.py (303 lines) - No Mercy+ with expansion
├── uno_logic.py (657 lines) - Shared utilities
└── __init__.py (9 lines)
```

**Handler Pattern:**
```python
class UnoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.flip_handler = UnoFlipHandler(bot, self)
        self.no_mercy_handler = UnoNoMercyHandler(bot)
        self.no_mercy_plus_handler = UnoNoMercyPlusHandler(bot)
```

### Custom Emoji System

**JSON Mapping (data/uno_emoji_mapping.json):**
```json
{
  "classic": {
    "red_0.png": "1234567890",
    "blue_skip.png": "9876543210",
    "wild_+4.png": "5555555555",
    "uno_back.png": "1111111111"
  },
  "flip": { ... },
  "no_mercy": { ... }
}
```

**Usage:**
```python
def card_to_emoji(card, variant='classic'):
    mapping = load_emoji_mapping(variant)
    filename = f"{card['color']}_{card['value']}.png"
    emoji_id = mapping.get(filename)
    
    if emoji_id:
        return discord.PartialEmoji(name='_', id=int(emoji_id))
    
    # Fallback to color emoji
    return COLOR_EMOJIS[card['color']]  # 🔴🟡🟢🔵
```

### Translation System (Lines 39-90 in classic.py)

**Multi-language Support:**
```python
# data/uno_translations.json structure
{
  "en": {
    "lobby": {
      "title": "UNO Lobby",
      "players": "Players",
      "waiting": "Waiting for players..."
    },
    "game": {
      "your_turn": "It's your turn!",
      "draw_cards": "Drew {count} cards"
    },
    "colors": {
      "red": "Red",
      "yellow": "Yellow",
      "green": "Green",
      "blue": "Blue"
    }
  },
  "pl": {
    "lobby": {
      "title": "Poczekalnia UNO",
      "players": "Gracze",
      "waiting": "Oczekiwanie na graczy..."
    },
    "game": {
      "your_turn": "Twoja kolej!",
      "draw_cards": "Dobrałeś {count} kart"
    },
    "colors": {
      "red": "Czerwony",
      "yellow": "Żółty",
      "green": "Zielony",
      "blue": "Niebieski"
    }
  }
}
```

**Translation Helper:**
```python
def t(self, key_path, game_or_lobby=None, lang=None):
    """
    Translate text using key path
    Example: t('game.your_turn', game, 'pl') → "Twoja kolej!"
    """
    if lang is None:
        lang = self.get_lang(game_or_lobby)  # From game settings
    
    translations = load_translations()
    keys = key_path.split('.')
    current = translations.get(lang, {})
    
    for key in keys:
        current = current.get(key, key_path)
    
    return current
```

### Shared Card Logic (uno_logic.py)

**Standard Deck Creation (Lines 195-220):**
```python
def create_deck():
    """Create standard UNO deck (108 cards)"""
    deck = []
    colors = ['red', 'yellow', 'green', 'blue']
    
    # Number cards: 0 (1 each), 1-9 (2 each)
    for color in colors:
        deck.append({'color': color, 'value': 0})
        for num in range(1, 10):
            deck.append({'color': color, 'value': num})
            deck.append({'color': color, 'value': num})
    
    # Action cards: 2 of each per color
    for color in colors:
        for _ in range(2):
            deck.append({'color': color, 'value': 'skip'})
            deck.append({'color': color, 'value': 'reverse'})
            deck.append({'color': color, 'value': '+2'})
    
    # Wild cards: 4 of each type
    for _ in range(4):
        deck.append({'color': 'wild', 'value': 'wild'})
        deck.append({'color': 'wild', 'value': 'wild+4'})
    
    return deck
```

**Reshuffle Logic (Lines 240-255):**
```python
def reshuffle_discard_into_deck(deck, discard):
    """When deck runs out, reshuffle discard pile"""
    if len(deck) < 5 and len(discard) > 1:
        top_card = discard[-1]  # Keep top card
        cards_to_reshuffle = discard[:-1].copy()
        discard.clear()
        discard.append(top_card)
        
        random.shuffle(cards_to_reshuffle)
        deck.extend(cards_to_reshuffle)
        return True
    return False
```

---

## 9. UNO CLASSIC

**File:** `cogs/uno/classic.py` (5,506 lines - LARGEST FILE)  
**Deck:** 108 cards (standard UNO)  
**Players:** 2-10 (with bot support)

### Lobby System (Lines 150-800)

**Comprehensive Settings:**
```python
lobby = {
    'variant': 'classic',
    'hostId': str(user.id),
    'players': [str(user.id)],
    'bot_slots': 0,  # Number of bot players
    'bot_names': {},  # {BOT_1: "Alice", BOT_2: "Bob"}
    'settings': {
        'starting_hand_size': 7,
        'max_hand_size': 25,          # Elimination at 25+
        'draw_until_playable': False,  # Draw until you can play
        'stack_draw_cards': True,      # +2 on +2, +4 on +4
        'jump_in': False,              # Play identical card out of turn
        'seven_swap': False,           # Playing 7 = swap hands
        'zero_rotate': False,          # Playing 0 = rotate all hands
        'force_play': False,           # Must play if possible
        'stack_colors': False,         # Play multiple same color
        'stack_numbers': False,        # Play multiple same number
        'challenge_draw4': True,       # Challenge illegal +4
        'progressive_uno': False       # Say UNO each time down to 1
    },
    'messageId': None,
    'language': 'en',  # or 'pl'
    'last_activity': time.time()
}
```

**Lobby Customization (Lines 300-600):**

**Settings Modal:**
```python
class LobbySettingsModal(discord.ui.Modal):
    starting_cards = discord.ui.TextInput(
        label="Starting Hand Size",
        placeholder="7 (default)",
        default="7",
        max_length=2
    )
    
    draw_mode = discord.ui.Select(
        options=[
            discord.SelectOption(label="Draw 1 card only", value="single"),
            discord.SelectOption(label="Draw until playable", value="until_playable")
        ]
    )
    
    # ... many more options
```

**Bot Management:**
- Add bots (up to 9 total players)
- Remove bots
- Custom bot names (defaults to owner names)
- Bot AI with strategic play

### Game Flow (Lines 800-3000)

**Turn Structure:**
```python
async def handle_turn(game_id, game, player_id):
    """Process a player's turn"""
    
    # 1. Check draw stack
    if game['draw_stack'] > 0:
        # Player must draw or play +2/+4 to counter
        can_counter = has_counter_card(game['hands'][player_id], game['top_card'])
        if not can_counter:
            # Must draw all stacked cards
            cards_to_draw = game['draw_stack']
            drawn = draw_cards(game['deck'], cards_to_draw)
            game['hands'][player_id].extend(drawn)
            game['draw_stack'] = 0
            
            # Check elimination (25+ cards)
            if len(game['hands'][player_id]) >= 25:
                await eliminate_player(game_id, game, player_id)
            
            # Skip to next player
            advance_turn(game)
            return
    
    # 2. Show hand and playable cards
    hand = game['hands'][player_id]
    playable = [c for c in hand if can_play_card(c, game['top_card'], game['current_color'])]
    
    if not playable and game['settings']['force_play']:
        # Force play disabled - can choose to draw
        pass
    
    # 3. Send play options (buttons/dropdowns)
    view = UnoGameView(game_id, player_id, playable)
    await send_turn_message(player_id, view)
    
    # 4. Bot auto-plays if bot turn
    if player_id.startswith('BOT_'):
        await asyncio.sleep(1.5)
        await bot_play_turn(game_id, game, player_id)
```

**Card Playing (Lines 1200-1800):**
```python
async def play_card(game_id, game, player_id, card_index):
    """Player plays a card"""
    hand = game['hands'][player_id]
    card = hand[card_index]
    
    # Remove from hand
    hand.pop(card_index)
    
    # Add to discard pile
    game['discard_pile'].append(card)
    game['top_card'] = card
    
    # Process card effects
    effects = process_card_effects(game, card, player_id)
    
    # Check for UNO call
    if len(hand) == 1 and not game.get(f'uno_called_{player_id}'):
        # Didn't call UNO! Penalty: draw 2
        if game['settings']['progressive_uno']:
            penalty = draw_cards(game['deck'], 2)
            hand.extend(penalty)
            await send_message(f"⚠️ {player_name} forgot to call UNO! +2 cards")
    
    # Check for win
    if len(hand) == 0:
        await handle_win(game_id, game, player_id)
        return
    
    # Apply card effects and advance turn
    await apply_effects(game_id, game, effects)
    
    # Check if can continue playing (stack colors/numbers)
    can_continue = check_stack_continue(game, card, hand)
    if not can_continue:
        advance_turn(game)
```

### Special Card Effects (Lines 1800-2500)

**Reverse:**
```python
if card['value'] == 'reverse':
    if len(game['players']) == 2:
        # 2 players: acts like Skip
        effects['skip_next'] = True
    else:
        # 3+ players: reverse direction
        game['direction'] *= -1  # 1 → -1 or -1 → 1
        effects['reverse'] = True
```

**Skip:**
```python
if card['value'] == 'skip':
    effects['skip_next'] = True
```

**+2 Draw:**
```python
if card['value'] == '+2':
    if game['settings']['stack_draw_cards']:
        # Add to stack - next player can counter
        game['draw_stack'] += 2
        effects['draw_penalty'] = 2
    else:
        # Next player draws immediately
        next_player = get_next_player(game)
        drawn = draw_cards(game['deck'], 2)
        game['hands'][next_player].extend(drawn)
        effects['draw_immediate'] = 2
        effects['skip_next'] = True  # Skip after drawing
```

**Wild +4:**
```python
if card['value'] == 'wild+4':
    # Player chooses color
    if game['settings']['challenge_draw4']:
        # Next player can challenge if suspect illegal play
        # Legal +4: only playable if no matching color in hand
        if has_matching_color(previous_hand, previous_top_card):
            # Illegal +4! Challenger wins
            effects['illegal_wild4'] = True
        else:
            # Legal +4! Challenger draws 6 instead
            effects['challenge_failed'] = True
    
    if game['settings']['stack_draw_cards']:
        game['draw_stack'] += 4
    else:
        next_player = get_next_player(game)
        drawn = draw_cards(game['deck'], 4)
        game['hands'][next_player].extend(drawn)
        effects['skip_next'] = True
```

**Seven Swap (Optional):**
```python
if card['value'] == 7 and game['settings']['seven_swap']:
    # Current player swaps hands with target player
    effects['seven_swap'] = True
    # Show player selection menu
    await show_swap_target_menu(game_id, player_id)
```

**Zero Rotate (Optional):**
```python
if card['value'] == 0 and game['settings']['zero_rotate']:
    # All hands rotate in current direction
    effects['zero_rotate'] = True
    rotate_all_hands(game)
```

### Advanced Features (Lines 2500-4000)

**Jump-In (Lines 2600-2700):**
```python
if game['settings']['jump_in']:
    # Players can play identical card out of turn
    # Example: Blue 7 on table, anyone with Blue 7 can jump in
    
    @bot.event
    async def on_reaction_add(reaction, user):
        if reaction.emoji == '🎯':  # Jump-in emoji
            game = find_game_by_channel(reaction.message.channel.id)
            if not game:
                return
            
            player_id = str(user.id)
            if player_id not in game['players']:
                return
            
            hand = game['hands'][player_id]
            top_card = game['top_card']
            
            # Find exact match in hand
            identical = [i for i, c in enumerate(hand) 
                        if c['color'] == top_card['color'] and 
                           c['value'] == top_card['value']]
            
            if identical:
                # Jump in! Play card immediately
                await play_card(game['game_id'], game, player_id, identical[0])
                # Current turn player loses turn
```

**Challenge System (Lines 2700-2900):**
```python
async def challenge_wild4(game_id, game, challenger_id):
    """Challenge if previous player illegally played Wild +4"""
    previous_player = game['previous_player']
    previous_hand = game['previous_hand_snapshot']  # Saved before play
    previous_top = game['previous_top_card']
    
    # Check if previous player had matching color
    had_color = any(c['color'] == previous_top['color'] 
                   for c in previous_hand 
                   if c['color'] != 'wild')
    
    if had_color:
        # Illegal +4! Challenger wins
        # Previous player draws 4 instead
        drawn = draw_cards(game['deck'], 4)
        game['hands'][previous_player].extend(drawn)
        
        await send_message(
            f"✅ Challenge successful! <@{previous_player}> had a matching color and draws 4!"
        )
    else:
        # Legal +4! Challenger draws 6 (4 + 2 penalty)
        drawn = draw_cards(game['deck'], 6)
        game['hands'][challenger_id].extend(drawn)
        
        await send_message(
            f"❌ Challenge failed! <@{challenger_id}> draws 6 cards!"
        )
```

**Elimination System (Lines 3000-3200):**
```python
async def check_elimination(game_id, game, player_id, channel):
    """Check if player should be eliminated (≥25 cards)"""
    hand = game['hands'][player_id]
    
    if len(hand) >= game['settings']['max_hand_size']:
        # Eliminate player
        game['players'].remove(player_id)
        game['eliminated'].append(player_id)
        
        # Distribute eliminated player's cards back to deck
        game['deck'].extend(hand)
        random.shuffle(game['deck'])
        del game['hands'][player_id]
        
        await channel.send(
            f"💀 <@{player_id}> eliminated with {len(hand)} cards!"
        )
        
        # Check if only 1 player remains
        if len(game['players']) == 1:
            winner = game['players'][0]
            await handle_win(game_id, game, winner)
```

### Bot AI Strategy (Lines 4000-4500)

**Strategic Decision Making:**
```python
async def bot_play_turn(game_id, game, bot_id):
    """Bot makes intelligent move"""
    hand = game['hands'][bot_id]
    top_card = game['top_card']
    current_color = game['current_color']
    
    # Get playable cards
    playable = [c for c in hand if can_play_card(c, top_card, current_color)]
    
    if not playable:
        # Must draw
        await bot_draw_card(game_id, game, bot_id)
        return
    
    # Strategy priorities:
    # 1. Play wild/action cards to disrupt opponents
    wilds = [c for c in playable if c['color'] == 'wild']
    actions = [c for c in playable if c['value'] in ['skip', 'reverse', '+2']]
    
    # 2. If only 1-2 cards left, play safe (number cards)
    if len(hand) <= 2:
        numbers = [c for c in playable if isinstance(c['value'], int)]
        if numbers:
            card = random.choice(numbers)
        else:
            card = random.choice(playable)
    
    # 3. If opponent has 1 card (UNO), play action to disrupt
    elif any(len(game['hands'][p]) == 1 for p in game['players'] if p != bot_id):
        if actions:
            card = random.choice(actions)
        elif wilds:
            card = random.choice(wilds)
        else:
            card = random.choice(playable)
    
    # 4. Otherwise, prefer playing high-value cards first
    else:
        # Sort by value priority
        def card_priority(c):
            if c['color'] == 'wild':
                return 100
            if c['value'] == '+2':
                return 50
            if c['value'] in ['skip', 'reverse']:
                return 40
            if isinstance(c['value'], int):
                return c['value']
            return 0
        
        playable.sort(key=card_priority, reverse=True)
        card = playable[0]
    
    # Play chosen card
    card_index = hand.index(card)
    await play_card(game_id, game, bot_id, card_index)
    
    # If wild card, choose color
    if card['color'] == 'wild':
        # Choose most common color in hand
        color_counts = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0}
        for c in hand:
            if c['color'] in color_counts:
                color_counts[c['color']] += 1
        
        best_color = max(color_counts, key=color_counts.get)
        game['current_color'] = best_color
```

### Win Conditions & Rewards (Lines 4500-5000)

**Victory Check:**
```python
async def handle_win(game_id, game, winner_id):
    """Handle game victory"""
    # Calculate points (unused cards in other players' hands)
    total_points = 0
    for player_id in game['players']:
        if player_id == winner_id:
            continue
        
        for card in game['hands'][player_id]:
            if card['color'] == 'wild':
                total_points += 50
            elif card['value'] in ['skip', 'reverse', '+2']:
                total_points += 20
            elif isinstance(card['value'], int):
                total_points += card['value']
    
    # Award coins
    economy_cog = bot.get_cog("Economy")
    if economy_cog and not winner_id.startswith('BOT_'):
        base_coins = 150
        bonus = min(total_points // 10, 50)  # Up to 50 bonus
        total_coins = base_coins + bonus
        
        economy_cog.add_coins(int(winner_id), total_coins, "uno_win")
    
    # Record stats
    game_stats_cog = bot.get_cog("GameStats")
    if game_stats_cog and not winner_id.startswith('BOT_'):
        duration = int(time.time() - game['start_time'])
        game_stats_cog.record_game(
            int(winner_id),
            f"uno_{game['variant']}",
            won=True,
            coins_earned=total_coins,
            playtime_seconds=duration,
            category="card_games"
        )
    
    # Display final leaderboard
    rankings = sorted(
        [(p, len(game['hands'].get(p, []))) for p in game['players']],
        key=lambda x: x[1]
    )
    
    embed = discord.Embed(
        title=f"🎉 {self.get_bot_display_name(winner_id, game)} WINS!",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Final Standings",
        value="\n".join([
            f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '📍'} "
            f"{self.get_bot_display_name(p, game)}: {cards} cards"
            for i, (p, cards) in enumerate(rankings)
        ])
    )
    embed.add_field(name="Points", value=f"{total_points}", inline=False)
    
    await channel.send(embed=embed)
    
    # Clean up game
    bot.active_games.pop(game_id, None)
```

---

## 10. UNO FLIP

**File:** `cogs/uno/flip.py` (355 lines)  
**Deck:** 112 cards (double-sided)  
**Unique Feature:** Cards have Light and Dark sides

### Flip Mechanics

**Card Structure:**
```python
{
    'side': 'light',  # or 'dark'
    'color': 'red',   # light: red/yellow/green/blue, dark: teal/purple/pink/orange
    'value': 5        # or action card
}
```

**Deck Composition (Lines 30-90):**

**Light Side:**
- Numbers 1-9 (2 each per color: red, yellow, green, blue)
- Skip, Reverse, +1 (2 each per color)
- Wild, Wild +2

**Dark Side:**
- Numbers 1-9 (2 each per color: teal, purple, pink, orange)
- Skip Everyone (skips all other players)
- Reverse, +5 (2 each per color)
- Wild, Wild Draw Color (draw until you get chosen color!)

**Flip Card:**
```python
# Special card that flips entire game
{
    'side': 'light',
    'color': 'red',
    'value': 'flip'
}

# When played:
async def execute_flip(game):
    """Flip all cards to opposite side"""
    # Flip top card
    game['top_card']['side'] = 'dark' if game['top_card']['side'] == 'light' else 'light'
    game['current_side'] = game['top_card']['side']
    
    # Flip deck
    for card in game['deck']:
        card['side'] = game['current_side']
    
    # Flip all player hands
    for player_id in game['players']:
        for card in game['hands'][player_id]:
            card['side'] = game['current_side']
    
    # Flip discard pile
    for card in game['discard_pile']:
        card['side'] = game['current_side']
    
    await channel.send(f"🔄 **FLIP!** Game switched to **{game['current_side'].upper()} SIDE**!")
```

### Dark Side Cards

**Skip Everyone (Lines 150-180):**
```python
if card['value'] == 'skip_everyone':
    # Skip all players except current
    # Turn returns to player who played it
    effects['skip_all'] = True
    effects['skip_next'] = False  # Don't skip just next player
    
    # Announce
    await channel.send(
        f"⏭️⏭️⏭️ **SKIP EVERYONE!** {player_name} plays again!"
    )
```

**+5 Draw (Lines 180-200):**
```python
if card['value'] == '+5':
    if game['settings']['stack_draw_cards']:
        game['draw_stack'] += 5
        effects['draw_penalty'] = 5
    else:
        next_player = get_next_player(game)
        drawn = draw_cards(game['deck'], 5)
        game['hands'][next_player].extend(drawn)
        effects['draw_immediate'] = 5
        effects['skip_next'] = True
```

**Wild Draw Color (Lines 200-250):**
```python
if card['value'] == 'draw_color':
    # Player chooses color
    chosen_color = await show_color_picker(player_id)
    game['current_color'] = chosen_color
    
    # Next player draws until they get that color
    next_player = get_next_player(game)
    drawn_count = 0
    
    while True:
        if not game['deck']:
            reshuffle_discard_into_deck(game['deck'], game['discard_pile'])
        
        card = game['deck'].pop()
        game['hands'][next_player].append(card)
        drawn_count += 1
        
        if card['color'] == chosen_color:
            break  # Got the color! Stop drawing
        
        if drawn_count >= 20:  # Safety limit
            break
    
    await channel.send(
        f"🎨 **WILD DRAW COLOR!** {next_player_name} drew **{drawn_count} cards** "
        f"until getting {COLOR_EMOJIS[chosen_color]}!"
    )
    
    effects['draw_color'] = drawn_count
    effects['skip_next'] = True
```

### Strategy Tips

**Light Side:**
- Fairly standard UNO
- +1 cards less punishing than Classic +2
- Save Flip cards for strategic moments

**Dark Side:**
- Much more chaotic
- Skip Everyone very powerful (play again!)
- +5 and Wild Draw Color extremely punishing
- Flip back to Light ASAP if losing

---

## 11. UNO NO MERCY

**File:** `cogs/uno/no_mercy.py` (167 lines)  
**Deck:** 168 cards (brutal edition)  
**Tagline:** "No mercy for anyone!"

### Enhanced Deck (Lines 20-80)

**More of everything:**
- Numbers 0-9 (0: 2 each, 1-9: 3 each per color) = 112 cards
- **Colored +4** (3 per color) = 12 cards - HUGE CHANGE
- Skip Everyone (2 per color) = 8 cards
- Discard All Card (2 per color) = 8 cards - NEW
- Reverse, Skip (3 each per color) = 24 cards
- Wild +6 (3 cards) = 3 cards - NEW
- Wild +10 (2 cards) = 2 cards - NEW
- Wild +4 Reverse (3 cards) = 3 cards - NEW
- Wild Color Roulette (2 cards) = 2 cards - NEW

**Total: 168 cards**

### New Card Types

**Colored +4 (Lines 90-110):**
```python
# +4 is NO LONGER wild-only!
{
    'color': 'red',  # Actual color!
    'value': '+4',
    'variant': 'no_mercy'
}

# Play rules: Must match color OR stack on another +4
if game['settings']['stack_draw_cards']:
    game['draw_stack'] += 4
else:
    next_player_draws(4)
```

**Skip Everyone (same as Flip dark side):**
```python
# Skips all other players, you go again
{
    'color': 'blue',
    'value': 'skip_everyone'
}
```

**Discard All Card (Lines 110-140):**
```python
# Play this card with a specific number
# All players (including you!) discard all cards matching that number
{
    'color': 'green',
    'value': 'discard_all_card'
}

async def execute_discard_all(game, chosen_number):
    """Everyone discards matching number"""
    total_discarded = 0
    
    for player_id in game['players']:
        hand = game['hands'][player_id]
        matching = [c for c in hand if c.get('value') == chosen_number]
        
        for card in matching:
            hand.remove(card)
            game['discard_pile'].append(card)
            total_discarded += 1
    
    await channel.send(
        f"🗑️ **DISCARD ALL {chosen_number}!** All players discarded {total_discarded} cards total!"
    )
```

**Wild +6 (Lines 140-155):**
```python
# Like Wild +4 but draws 6
{
    'color': 'wild',
    'value': '+6'
}

if game['settings']['stack_draw_cards']:
    game['draw_stack'] += 6
```

**Wild +10 (Lines 155-170):**
```python
# BRUTAL - draws 10 cards
{
    'color': 'wild',
    'value': '+10'
}

if game['settings']['stack_draw_cards']:
    game['draw_stack'] += 10  # Can stack to insane amounts!
```

**Wild +4 Reverse:**
```python
# Combines reverse and +4
{
    'color': 'wild',
    'value': '+4_reverse'
}

# Effects:
# 1. Next player draws 4
# 2. Direction reverses
# 3. Player after reversed direction goes next
```

**Wild Color Roulette:**
```python
# Random color selection!
{
    'color': 'wild',
    'value': 'color_roulette'
}

# Bot randomly picks color
chosen_color = random.choice(['red', 'yellow', 'green', 'blue'])
game['current_color'] = chosen_color

await channel.send(
    f"🎲 **COLOR ROULETTE!** Spun {COLOR_EMOJIS[chosen_color]}!"
)
```

### Strategy

**Key Differences from Classic:**
1. **Colored +4** - Can't save them forever, must use when color comes up
2. **Draw stacking** - Can reach +20 or higher in intense games
3. **Skip Everyone** - Critical for maintaining control
4. **Discard All** - Can turn game around instantly if you have numbers
5. **Wild +10** - Save for endgame disruption

---

## 12. UNO NO MERCY PLUS

**File:** `cogs/uno/no_mercy_plus.py` (303 lines)  
**Deck:** 180+ cards (No Mercy + Expansion Pack)  
**Tagline:** "The ULTIMATE UNO experience"

### Expansion Cards (Lines 40-90)

**All No Mercy cards PLUS:**

**10's Play Again (Lines 45-55):**
```python
# Number 10 card (2 per color) = 8 cards
{
    'color': 'red',
    'value': 10,
    'effect': 'play_again',
    'variant': 'no_mercy_plus'
}

# After playing: Immediate extra turn!
if card.get('effect') == 'play_again':
    effects['play_again'] = True
    # Don't advance turn - same player goes again
```

**Wild Discard All (Lines 60-100):**
```python
# Choose color - ALL players discard that color (2 cards)
{
    'color': 'wild',
    'value': 'discard_all',
    'variant': 'no_mercy_plus'
}

async def execute_wild_discard_all(game, chosen_color):
    """All players discard chosen color"""
    for player_id in game['players']:
        hand = game['hands'][player_id]
        matching_color = [c for c in hand if c['color'] == chosen_color]
        
        for card in matching_color:
            hand.remove(card)
            game['discard_pile'].append(card)
    
    await channel.send(
        f"🗑️💥 **WILD DISCARD ALL {COLOR_EMOJIS[chosen_color]}!** "
        f"Everyone discarded their {chosen_color} cards!"
    )
```

**Wild Reverse Draw 8 (Lines 100-130):**
```python
# Reverse direction + next player draws 8 (2 cards)
{
    'color': 'wild',
    'value': 'reverse_draw_8',
    'variant': 'no_mercy_plus'
}

# Effects:
game['direction'] *= -1  # Reverse
if game['settings']['stack_draw_cards']:
    game['draw_stack'] += 8
else:
    next_player_draws(8)

await channel.send(
    f"🔄➕ **WILD REVERSE +8!** Direction reversed and "
    f"{next_player_name} draws 8!"
)
```

**Wild Final Attack (Lines 130-180):**
```python
# Reveal your hand - opponent draws based on action/wild cards (1 card)
{
    'color': 'wild',
    'value': 'final_attack',
    'variant': 'no_mercy_plus'
}

async def execute_final_attack(game, player_id):
    """Count action/wild cards - opponent draws that many"""
    hand = game['hands'][player_id]
    
    # Count special cards
    special_count = 0
    for card in hand:
        if card['color'] == 'wild':
            special_count += 3  # Wild cards count as 3
        elif card['value'] in ['skip', 'reverse', 'skip_everyone', 
                               '+2', '+4', '+5', '+6', '+10']:
            special_count += 1
    
    # Next player draws
    next_player = get_next_player(game)
    if special_count > 0:
        drawn = draw_cards(game['deck'], special_count)
        game['hands'][next_player].extend(drawn)
        
        # Show revealed hand
        hand_display = ", ".join([card_to_string(c) for c in hand])
        
        await channel.send(
            f"⚔️ **FINAL ATTACK!** {player_name} revealed:\n"
            f"{hand_display}\n\n"
            f"💣 {next_player_name} draws **{special_count} cards**!"
        )
    else:
        await channel.send(
            f"⚔️ **FINAL ATTACK!** But {player_name} has no action cards! "
            f"{next_player_name} is safe!"
        )
```

**Wild Sudden Death (Lines 180-230):**
```python
# ALL players draw to 24 cards (1 card)
{
    'color': 'wild',
    'value': 'sudden_death',
    'variant': 'no_mercy_plus'
}

async def execute_sudden_death(game):
    """All players draw to 24 cards"""
    target = 24
    
    for player_id in game['players']:
        hand = game['hands'][player_id]
        current_count = len(hand)
        
        if current_count < target:
            to_draw = target - current_count
            drawn = draw_cards(game['deck'], to_draw)
            hand.extend(drawn)
            
            await dm_player(
                player_id,
                f"💀 **SUDDEN DEATH!** Drew {to_draw} cards (now have {target})"
            )
    
    await channel.send(
        f"💀💀💀 **SUDDEN DEATH!** All players now have 24 cards! "
        f"Chaos ensues!"
    )
```

### Coin System (Optional Feature)

**Coins as currency in-game:**
```python
# Players can spend coins for advantages
game['player_coins'] = {player_id: 100 for player_id in game['players']}

# Shop items:
# - Skip opponent turn (50 coins)
# - Force card swap (75 coins)
# - Peek at deck top (25 coins)
# - Immunity to next draw (100 coins)
```

**Not fully implemented in code shown, but structure exists for future expansion.**

### Ultimate Strategy

**No Mercy+ combines:**
1. All No Mercy brutality
2. 10's Play Again for momentum
3. Wild Discard All for mass elimination
4. Reverse Draw 8 for defensive plays
5. Final Attack for calculated endgame
6. Sudden Death for complete chaos

**This is the HARDEST UNO variant in the bot!**

---

## 13. COMMANDS REFERENCE

### Board Games Commands

| Command | Description | Players | Rewards |
|---------|-------------|---------|---------|
| `/tictactoe` | Create TTT lobby | 1-2 | 50 coins + 40% TCG card |
| `/connect4 start [@player]` | Start Connect 4 | 1-2 | 75 coins |
| `/hangman` | Play Hangman | 1 | 60-100 coins (hints penalty) |
| `/scrabble [@opponent]` | Start Scrabble | 2 | Points tracking |
| `/backgammon [@opponent]` | Start Backgammon | 2 | Pending |
| `/tetris` | Play Tetris | 1 | Score ÷ 10 coins |
| `/chess` | Create chess lobby | 1-2 | 20-30 coins |
| `/checkers` | Create checkers lobby | 1-2 | 25 coins |

### UNO Commands

| Command | Description | Variants |
|---------|-------------|----------|
| `/uno` | Create UNO lobby | All |
| `/uno-classic` | Classic UNO lobby | Classic |
| `/uno-flip` | UNO Flip lobby | Flip |
| `/uno-nomercy` | No Mercy lobby | No Mercy |
| `/uno-nomercyplus` | No Mercy+ lobby | No Mercy+ |

**In-Game Actions:**
- Click cards to play
- "Draw" button to draw card
- "UNO!" button when down to 1 card
- Color picker for wild cards
- Challenge button for +4 (Classic only)

### Lobby Management

**All lobbies support:**
- `/lobby settings` - Customize rules
- Join/Leave buttons
- Add/Remove bots
- Language selection (UNO)
- Start game button

---

## 14. SUMMARY

**Part 5B Coverage:**
- **11,138 lines** of code (LARGEST PART)
- **8 board games:** Tic-Tac-Toe, Connect 4, Hangman, Scrabble, Backgammon, Tetris, Chess, Checkers
- **4 UNO variants:** Classic (5,506 lines!), Flip, No Mercy, No Mercy+
- **12 total games** in this part

**Technical Achievements:**
- **Minimax AI** with alpha-beta pruning (Tic-Tac-Toe - unbeatable on 3x3)
- **Python chess library** integration (full legal move validation)
- **PIL rendering** for chess/checkers board images
- **Multi-language support** (EN/PL) with JSON translations
- **Custom emoji system** with Discord emoji mapping
- **Modal input forms** for move entry
- **Lobby system** with extensive customization
- **Bot opponents** with strategic AI
- **Interactive Discord UI** (buttons, dropdowns, select menus)

**UNO System Highlights:**
- **Largest single file** (classic.py: 5,506 lines)
- **2-10 player support** with bot AI
- **19+ customizable settings** per lobby
- **4 complete variants** (Classic, Flip, No Mercy, No Mercy+)
- **30+ unique card types** across variants
- **Challenge system** for Wild +4
- **Jump-in, Seven Swap, Zero Rotate** optional rules
- **Elimination system** (25+ cards)
- **Multi-language** (full EN/PL support)

**Rewards Summary:**
- Tic-Tac-Toe: 50 coins + 40% TCG card
- Connect 4: 75 coins
- Hangman: 60-100 coins (hint penalty)
- Tetris: Score ÷ 10 coins
- Chess: 20-30 coins (resign vs checkmate)
- Checkers: 25 coins
- UNO: 150-200 coins (based on points)

**File Statistics:**
- boardgames.py: 1,383 lines
- boardgames_enhanced.py: 811 lines
- chess_checkers.py: 1,947 lines
- uno/classic.py: 5,506 lines (LARGEST)
- uno/flip.py: 355 lines
- uno/no_mercy.py: 167 lines
- uno/no_mercy_plus.py: 303 lines
- uno/uno_logic.py: 657 lines
- uno/__init__.py: 9 lines
- **Total:** 11,138 lines

**Integration Points:**
- Economy system (coin rewards, shop items for chess boards)
- Profile system (game stats tracking)
- Game Stats cog (wins, losses, playtime, category tracking)
- Global Leaderboards (game performance)
- TCG system (card rewards for board game wins)

