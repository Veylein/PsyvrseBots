import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional, Dict, List
import time

from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView

# Import TCG system for card rewards
try:
    from cogs.psyvrse_tcg import inventory as tcg_inventory, generate_card_from_seed
except ImportError:
    tcg_inventory = None
    generate_card_from_seed = None

# ==================== HELPER FUNCTIONS ====================

def generate_board_view(game_id, board, size, disabled=False, symbols=None):
    """Generate interactive board view for Tic-Tac-Toe"""
    if symbols is None:
        symbols = {1: 'X', 2: 'O'}
    
    view = discord.ui.View(timeout=None)
    for i in range(size * size):
        row = i // size
        state = board[i]
        btn = discord.ui.Button(custom_id=f"ttt_move_{game_id}_{i}", row=row)
        if state == 1:
            btn.label = symbols[1]
            btn.style = discord.ButtonStyle.primary
            btn.disabled = True
        elif state == 2:
            btn.label = symbols[2]
            btn.style = discord.ButtonStyle.danger
            btn.disabled = True
        else:
            btn.label = "\u200b"
            btn.style = discord.ButtonStyle.secondary
            btn.disabled = disabled
        view.add_item(btn)
    return view

def generate_lobby_embed(lobby, host_user):
    """Generate embed for TTT lobby"""
    embed = discord.Embed(title="🎮 Tic-Tac-Toe Lobby", color=discord.Color.blue())
    try:
        embed.set_thumbnail(url=host_user.display_avatar.url)
    except Exception:
        pass
    players_list = ["🤖 BOT" if pid == 'BOT_AI' else f"<@{pid}>" for pid in lobby['players']]
    starter_names = {'host_starts': 'Host Starts', 'guest_starts': 'Guest Starts', 'random': 'Random Order'}
    mode_names = {'normal': 'Normal', 'sliding': 'Disappearing Symbols'}
    embed.add_field(name="👑 Host", value=f"<@{lobby['hostId']}>")
    embed.add_field(name="Players", value=f"{len(lobby['players'])}/{lobby['maxPlayers']}")
    embed.add_field(name="Size", value=f"{lobby.get('boardSize','?')}x{lobby.get('boardSize','?')}")
    embed.add_field(name="Starter", value=starter_names.get(lobby.get('starter','host_starts'), lobby.get('starter','')))
    embed.add_field(name="Mode", value=mode_names.get(lobby.get('mode','normal'), lobby.get('mode','')))
    embed.add_field(name="Joined", value="\n".join(players_list), inline=False)
    return embed

def generate_lobby_view(lobby_id, lobby_state):
    """Generate lobby control buttons"""
    view = discord.ui.View(timeout=None)
    is_bot_game = 'BOT_AI' in lobby_state['players']
    is_full = len(lobby_state['players']) >= lobby_state.get('maxPlayers', 2)
    view.add_item(discord.ui.Button(label="Join", style=discord.ButtonStyle.success, custom_id=f"ttt_lobby_join_{lobby_id}", disabled=(is_full or is_bot_game)))
    view.add_item(discord.ui.Button(label="🤖 Bot", style=discord.ButtonStyle.primary, custom_id=f"ttt_lobby_bot_{lobby_id}", disabled=(len(lobby_state['players']) > 1)))
    view.add_item(discord.ui.Button(label="Leave", style=discord.ButtonStyle.secondary, custom_id=f"ttt_lobby_leave_{lobby_id}"))
    view.add_item(discord.ui.Button(label="⚙️ Settings", style=discord.ButtonStyle.primary, custom_id=f"ttt_lobby_settings_{lobby_id}", row=1))
    view.add_item(discord.ui.Button(label="Start", style=discord.ButtonStyle.success, custom_id=f"ttt_lobby_start_{lobby_id}", disabled=not (is_full or is_bot_game), row=1))
    return view

def generate_settings_selects(lobby_id, current_state):
    """Generate settings selection menus"""
    view = discord.ui.View(timeout=300)
    size_options = [
        discord.SelectOption(label="3x3 (classic)", value="3", default=current_state['boardSize'] == 3),
        discord.SelectOption(label="5x5 (larger)", value="5", default=current_state['boardSize'] == 5)
    ]
    view.add_item(discord.ui.Select(
        placeholder=f"Size: {current_state['boardSize']}x{current_state['boardSize']}",
        options=size_options,
        custom_id=f"ttt_set_size_{lobby_id}"
    ))
    starter_options = [
        discord.SelectOption(label="Host Starts", value="host_starts", default=current_state['starter'] == 'host_starts'),
        discord.SelectOption(label="Guest Starts", value="guest_starts", default=current_state['starter'] == 'guest_starts'),
        discord.SelectOption(label="Random Order", value="random", default=current_state['starter'] == 'random')
    ]
    view.add_item(discord.ui.Select(
        placeholder=f"Who Starts: {current_state['starter']}",
        options=starter_options,
        custom_id=f"ttt_set_starter_{lobby_id}"
    ))
    mode_options = [
        discord.SelectOption(label="Normal (classic)", value="normal", default=current_state['mode'] == 'normal'),
        discord.SelectOption(label="Disappearing Symbols", value="sliding", default=current_state['mode'] == 'sliding')
    ]
    view.add_item(discord.ui.Select(
        placeholder=f"Mode: {current_state['mode']}",
        options=mode_options,
        custom_id=f"ttt_set_mode_{lobby_id}"
    ))
    return view

def get_symbols(game_state):
    """Get symbols for the game"""
    return {1: 'X', 2: 'O'}

def get_host_background(game_state, guild_id):
    """Get background URL for the game (optional)"""
    return None  # Can be implemented later if needed

# ==================== GAME LOGIC ====================

def check_winner(board, size):
    """Check if there's a winner - 3x3 needs 3, 4x4 needs 4, 5x5 needs 4"""
    # Determine win condition based on board size
    if size == 3:
        win_length = 3
    elif size == 4:
        win_length = 4
    else:  # 5x5 or larger
        win_length = 4
    
    # Check all possible lines
    for row in range(size):
        for col in range(size):
            if board[row * size + col] == 0:
                continue
            
            player = board[row * size + col]
            
            # Check horizontal (right)
            if col + win_length <= size:
                if all(board[row * size + col + i] == player for i in range(win_length)):
                    return player
            
            # Check vertical (down)
            if row + win_length <= size:
                if all(board[(row + i) * size + col] == player for i in range(win_length)):
                    return player
            
            # Check diagonal (down-right)
            if row + win_length <= size and col + win_length <= size:
                if all(board[(row + i) * size + col + i] == player for i in range(win_length)):
                    return player
            
            # Check anti-diagonal (down-left)
            if row + win_length <= size and col - win_length >= -1:
                if all(board[(row + i) * size + col - i] == player for i in range(win_length)):
                    return player
    
    return None

def evaluate_position(board, size, player, opponent):
    """Heuristic evaluation for larger boards"""
    score = 0
    
    # Check all rows, columns, and diagonals
    for row in range(size):
        for col in range(size):
            if board[row * size + col] != 0:
                continue
            # Evaluate potential of this position
            threats = 0
            opportunities = 0
            
            # Check row
            row_player = sum(1 for c in range(size) if board[row * size + c] == player)
            row_opponent = sum(1 for c in range(size) if board[row * size + c] == opponent)
            if row_opponent == 0 and row_player > 0:
                opportunities += row_player ** 2
            if row_player == 0 and row_opponent > 0:
                threats += row_opponent ** 2
                
            # Check column
            col_player = sum(1 for r in range(size) if board[r * size + col] == player)
            col_opponent = sum(1 for r in range(size) if board[r * size + col] == opponent)
            if col_opponent == 0 and col_player > 0:
                opportunities += col_player ** 2
            if col_player == 0 and col_opponent > 0:
                threats += col_opponent ** 2
    
    return opportunities - threats

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
    
    # Depth limit - use heuristic evaluation
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

def choose_move(board, size, player):
    """AI chooses optimal move - unbeatable on 3x3, very strong on larger boards"""
    opponent = 3 - player
    
    # Set depth limit based on board size
    if size == 3:
        max_depth = 9  # Full search for 3x3
    elif size == 4:
        max_depth = 5  # Medium depth for 4x4
    else:  # 5x5 or larger
        max_depth = 3  # Shallow search with heuristic for 5x5
    
    # Priority moves for larger boards (optimization)
    if size >= 4:
        # 1. Check for immediate win
        for i in range(len(board)):
            if board[i] == 0:
                board[i] = player
                if check_winner(board, size):
                    board[i] = 0
                    return i
                board[i] = 0
        
        # 2. Block immediate opponent win
        for i in range(len(board)):
            if board[i] == 0:
                board[i] = opponent
                if check_winner(board, size):
                    board[i] = 0
                    return i
                board[i] = 0
    
    best_score = -float('inf')
    best_moves = []
    
    # Evaluate all possible moves
    for i in range(len(board)):
        if board[i] == 0:
            board[i] = player
            score = minimax(board, size, 0, False, -float('inf'), float('inf'), player, opponent, max_depth)
            board[i] = 0
            
            if score > best_score:
                best_score = score
                best_moves = [i]
            elif score == best_score:
                best_moves.append(i)
    
    # If multiple moves have same score, prefer center positions
    if len(best_moves) > 1:
        center = size // 2
        center_positions = []
        for move in best_moves:
            row = move // size
            col = move % size
            dist = abs(row - center) + abs(col - center)
            center_positions.append((dist, move))
        center_positions.sort()
        return center_positions[0][1]
    
    return best_moves[0] if best_moves else 0

async def process_move(bot, interaction, game_id, game, idx):
    player_num = game['turn']
    size = game['size']
    game['last_activity'] = time.time()

    if game['board'][idx] != 0:
        if hasattr(interaction.response, 'send_message'):
            return await interaction.response.send_message("This field is already taken.", ephemeral=True)
        else:
            return

    if game.get('mode') == 'sliding':
        hist = game['history'][str(player_num)]
        hist.append(idx)
        # 3x3: max 3 symbols, 5x5: max 4 symbols
        limit = 3 if size == 3 else 4
        if len(hist) > limit:
            old_idx = hist.pop(0)
            if game['board'][old_idx] == player_num:
                game['board'][old_idx] = 0

    game['board'][idx] = player_num

    winner = check_winner(game['board'], size)
    is_draw = 0 not in game['board'] and not winner

    symbols = get_symbols(game)

    if winner or is_draw:
        bot.pending_rematches[game_id] = {
            'size': game['size'],
            'mode': game['mode'],
            'players': game['players'],
            'messageId': game.get('messageId')
        }
        bot.active_games.pop(game_id, None)

        if winner:
            win_id = game['players'][str(winner)]
            lose_id = game['players']['1' if winner==2 else '2']
            is_multiplayer = win_id != 'BOT_AI' and lose_id != 'BOT_AI'
            
            # Record game statistics using GameStats cog
            game_stats_cog = bot.get_cog("GameStats")
            if game_stats_cog and win_id != 'BOT_AI':
                duration = int(time.time() - game.get('start_time', time.time()))
                guild_id = interaction.guild.id if interaction.guild else None
                game_stats_cog.record_game(int(win_id), "ttt", won=True, coins_earned=50, playtime_seconds=duration, category="board_games", guild_id=guild_id)
            
            if win_id != 'BOT_AI':
                # Award coins using Economy cog
                economy_cog = bot.get_cog("Economy")
                if economy_cog:
                    economy_cog.add_coins(int(win_id), 50, reason="boardgame_win")
                
                # 40% chance to award a basic TCG card
                if tcg_inventory and generate_card_from_seed and random.random() < 0.4:
                    try:
                        seed = random.randrange(1000000)
                        tcg_inventory.add_card(int(win_id), str(seed))
                        card = generate_card_from_seed(seed)
                        try:
                            await interaction.channel.send(f"🎴 **Bonus!** <@{win_id}> received a TCG card: **{card.name}** ({card.rarity})!", delete_after=10)
                        except:
                            pass
                    except Exception:
                        pass
            
            winner_mention = "🤖 BOT" if win_id == 'BOT_AI' else f"<@{win_id}>"
            embed = discord.Embed(title="Game Over!", description=f"{winner_mention} won!", color=discord.Color.green())
        else:
            # Draw - no coins awarded
            p1, p2 = game['players']['1'], game['players']['2']
            embed = discord.Embed(title="Draw!", color=discord.Color.orange())

        view = generate_board_view(game_id, game['board'], size, disabled=True, symbols=symbols)
        await interaction.message.edit(embed=embed, view=view)
        
        # Send separate message with rematch button
        rematch_view = discord.ui.View(timeout=60)
        rematch_btn = discord.ui.Button(label="🔄 Rematch", style=discord.ButtonStyle.success, custom_id=f"ttt_rematch_{game_id}")
        rematch_view.add_item(rematch_btn)
        rematch_msg = await interaction.channel.send("Want to play again?", view=rematch_view)
        
        # Save rematch message ID
        if game_id in bot.pending_rematches:
            bot.pending_rematches[game_id]['rematch_message_id'] = rematch_msg.id
        
        return

    game['turn'] = 2 if player_num == 1 else 1
    next_pid = game['players'][str(game['turn'])]

    p_name = "🤖 BOT" if next_pid == 'BOT_AI' else f"<@{next_pid}>"
    embed = discord.Embed(title=f"Game {size}x{size}", description=f"Turn: {p_name} ({symbols[game['turn']]})")
    view = generate_board_view(game_id, game['board'], size, symbols=symbols)

    await interaction.message.edit(embed=embed, view=view)

    if next_pid == 'BOT_AI':
        await handle_bot_move(bot, interaction.message, game_id, game)

async def handle_bot_move(bot, message, game_id, game):
    await asyncio.sleep(1)
    bot_player = game['turn']
    move_idx = choose_move(game['board'], game['size'], bot_player)

    class FakeInteraction:
        def __init__(self, msg):
            self.message = msg
            self.channel = msg.channel
            self.guild = msg.guild
            self.response = self
            self.user = type('obj', (object,), {'id': 'BOT_AI'})
        def is_done(self): return True
        async def edit_message(self, embed=None, view=None):
            return await self.message.edit(embed=embed, view=view)
        async def send_message(self, content, ephemeral=True):
            return
        async def edit(self, **kwargs):
            return await self.message.edit(**kwargs)

    await process_move(bot, FakeInteraction(message), game_id, game, move_idx)

# ==================== BOARD GAMES COG ====================

class BoardGames(commands.Cog):
    """Classic board games - Chess, Checkers, Connect4, Tic-Tac-Toe, and more"""

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.player_games = {}  # Track which game each player is in

    @app_commands.command(name="boardgames", description="View all board game commands and info (paginated)")
    async def boardgames_slash(self, interaction: discord.Interaction):
        commands_list = []
        prefix = self.bot.command_prefix
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"{prefix}{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Board Games"
        category_desc = "Play classic and new board games! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()

    # ==================== TIC-TAC-TOE ====================
    
    @commands.command(name="tictactoe", aliases=["ttt"])
    async def tictactoe_prefix(self, ctx):
        """Create a Tic-Tac-Toe lobby"""
        lobby_id = f"ttt_lobby_{ctx.channel.id}_{ctx.author.id}"
        uid_str = str(ctx.author.id)

        # Prevent creating a TTT lobby if user is already in any game/lobby
        for g in self.bot.active_games.values():
            if uid_str in g.get('players', {}).values():
                return await ctx.send("You can't create a lobby while in another active game.")
        for mg in self.bot.active_minigames.values():
            if mg.get('type') == 'solo' and str(mg.get('user_id')) == uid_str:
                return await ctx.send("You can't create a lobby while in an active hangman game.")
            if mg.get('type') == 'multi' and uid_str in mg.get('players', []):
                return await ctx.send("You can't create a lobby while in an active hangman game.")
        for lid, l in self.bot.active_lobbies.items():
            if uid_str in l.get('players', []) or l.get('hostId') == uid_str:
                return await ctx.send("You can't create a new lobby while already in a lobby.")

        if lobby_id in self.bot.active_lobbies:
            return await ctx.send("You already have an active lobby!")

        lobby_state = {
            'hostId': str(ctx.author.id),
            'players': [str(ctx.author.id)],
            'maxPlayers': 2,
            'boardSize': 3,
            'starter': 'host_starts',
            'mode': 'normal',
            'messageId': None,
            'last_activity': time.time(),
            'start_time': time.time()
        }

        embed = generate_lobby_embed(lobby_state, ctx.author)
        view = generate_lobby_view(lobby_id, lobby_state)
        msg = await ctx.send(embed=embed, view=view)
        lobby_state['messageId'] = msg.id
        self.bot.active_lobbies[lobby_id] = lobby_state
    
    @app_commands.command(name="tictactoe", description="Create a Tic-Tac-Toe lobby")
    async def tictactoe(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        lobby_id = f"ttt_lobby_{interaction.channel_id}_{interaction.user.id}"
        uid_str = str(interaction.user.id)

        # Prevent creating a TTT lobby if user is already in any game/lobby
        for g in self.bot.active_games.values():
            if uid_str in g.get('players', {}).values():
                return await interaction.followup.send("You can't create a lobby while in another active game.", ephemeral=True)
        for mg in self.bot.active_minigames.values():
            if mg.get('type') == 'solo' and str(mg.get('user_id')) == uid_str:
                return await interaction.followup.send("You can't create a lobby while in an active hangman game.", ephemeral=True)
            if mg.get('type') == 'multi' and uid_str in mg.get('players', []):
                return await interaction.followup.send("You can't create a lobby while in an active hangman game.", ephemeral=True)
        for lid, l in self.bot.active_lobbies.items():
            if uid_str in l.get('players', []) or l.get('hostId') == uid_str:
                return await interaction.followup.send("You can't create a new lobby while already in a lobby.", ephemeral=True)

        if lobby_id in self.bot.active_lobbies:
            return await interaction.followup.send("You already have an active lobby!", ephemeral=True)

        lobby_state = {
            'hostId': str(interaction.user.id),
            'players': [str(interaction.user.id)],
            'maxPlayers': 2,
            'boardSize': 3,
            'starter': 'host_starts',
            'mode': 'normal',
            'messageId': None,
            'last_activity': time.time(),
            'start_time': time.time()
        }

        embed = generate_lobby_embed(lobby_state, interaction.user)
        view = generate_lobby_view(lobby_id, lobby_state)
        msg = await interaction.followup.send(embed=embed, view=view, wait=True)
        lobby_state['messageId'] = msg.id
        self.bot.active_lobbies[lobby_id] = lobby_state

    # TTT INTERACTION HANDLERS

    async def handle_ttt_interaction(self, interaction: discord.Interaction, cid: str):
        """Main router for all TTT-related interactions"""
        if cid.startswith('ttt_set_'):
            await self.handle_ttt_settings(interaction, cid)
        elif cid.startswith('ttt_lobby_'):
            await self.handle_ttt_lobby(interaction, cid)
        elif cid.startswith('ttt_move_'):
            await self.handle_ttt_move(interaction, cid)
        elif cid.startswith('ttt_rematch_'):
            await self.handle_ttt_rematch(interaction, cid)

    async def handle_ttt_settings(self, interaction: discord.Interaction, cid: str):
        """Handle TTT lobby settings changes (board size, starter, mode)"""
        uid = str(interaction.user.id)
        parts = cid.split('_')
        setting = parts[2]
        lobby_id = "_".join(parts[3:])
        new_value = interaction.data['values'][0]
        
        lobby = self.bot.active_lobbies.get(lobby_id)
        if not lobby:
            return await interaction.response.edit_message(content="Lobby doesn't exist.", view=None)

        if uid != lobby['hostId']:
            return await interaction.response.send_message("Only the Host can change settings.", ephemeral=True)
        
        msg_info = ""
        if setting == 'size':
            lobby['boardSize'] = int(new_value)
            msg_info = f"Board size changed to **{new_value}x{new_value}**."
        elif setting == 'starter':
            lobby['starter'] = new_value
            starter_name = {
                'host_starts': 'Host Starts', 
                'guest_starts': 'Guest Starts', 
                'random': 'Random Order'
            }.get(new_value, new_value)
            msg_info = f"Starter changed to **{starter_name}**."
        elif setting == 'mode':
            lobby['mode'] = new_value
            mode_name = {
                'normal': 'Normal', 
                'sliding': 'Disappearing Symbols'
            }.get(new_value, new_value)
            msg_info = f"Game mode changed to **{mode_name}**."
        else:
            return await interaction.response.edit_message(content="Unknown setting.", view=None)

        host = await self.bot.fetch_user(int(lobby['hostId']))
        main_lobby_msg = interaction.channel.get_partial_message(lobby['messageId'])
        await main_lobby_msg.edit(
            embed=generate_lobby_embed(lobby, host), 
            view=generate_lobby_view(lobby_id, lobby)
        )

        await interaction.response.edit_message(
            content=f"⚙️ **Lobby Settings**\n{msg_info}", 
            view=generate_settings_selects(lobby_id, lobby)
        )

    async def handle_ttt_lobby(self, interaction: discord.Interaction, cid: str):
        """Handle TTT lobby actions: join, bot, leave, settings, start"""
        parts = cid.split('_')
        action = parts[2]
        prefix = f"ttt_lobby_{action}_"
        lobby_id = cid[len(prefix):]
        
        lobby = self.bot.active_lobbies.get(lobby_id)
        if not lobby:
            return await interaction.response.send_message("Lobby doesn't exist.", ephemeral=True)

        uid = str(interaction.user.id)
        host = await self.bot.fetch_user(int(lobby['hostId']))

        if action == 'join':
            await self.handle_lobby_join(interaction, lobby, lobby_id, uid, host)
        elif action == 'bot':
            await self.handle_lobby_bot(interaction, lobby, lobby_id, uid, host)
        elif action == 'leave':
            await self.handle_lobby_leave(interaction, lobby, lobby_id, uid, host)
        elif action == 'start':
            await self.handle_lobby_start(interaction, lobby, lobby_id, uid)
        elif action == 'settings':
            await self.handle_lobby_settings(interaction, lobby, lobby_id, uid)

    async def handle_lobby_join(self, interaction, lobby, lobby_id, uid, host):
        """Handle player joining TTT lobby"""
        if uid not in lobby['players']:
            if 'BOT_AI' in lobby['players']:
                lobby['players'].remove('BOT_AI')
            
            lobby['players'].append(uid)
            lobby['last_activity'] = time.time()
            await interaction.message.edit(
                embed=generate_lobby_embed(lobby, host), 
                view=generate_lobby_view(lobby_id, lobby)
            )
            await interaction.response.defer()
        else:
            await interaction.response.send_message("You're already here.", ephemeral=True)

    async def handle_lobby_bot(self, interaction, lobby, lobby_id, uid, host):
        """Handle adding/removing bot from TTT lobby"""
        if uid == lobby['hostId']:
            if len(lobby['players']) > 1 and lobby['players'][1] != 'BOT_AI':
                lobby['players'].pop(1)

            if 'BOT_AI' not in lobby['players']:
                lobby['players'].append('BOT_AI')
            lobby['last_activity'] = time.time()
            await interaction.response.defer()
            await interaction.message.edit(
                embed=generate_lobby_embed(lobby, host), 
                view=generate_lobby_view(lobby_id, lobby)
            )

    async def handle_lobby_leave(self, interaction, lobby, lobby_id, uid, host):
        """Handle player leaving TTT lobby"""
        if uid in lobby['players']:
            if len(lobby['players']) == 2 and 'BOT_AI' in lobby['players'] and uid == lobby['hostId']:
                lobby['players'].remove('BOT_AI')
                
            lobby['players'].remove(uid)
            lobby['last_activity'] = time.time()
            if not lobby['players']:
                await interaction.message.delete()
                del self.bot.active_lobbies[lobby_id]
                return await interaction.response.send_message("Lobby disbanded (was empty).", ephemeral=True)
            
            await interaction.response.defer()
            await interaction.message.edit(
                embed=generate_lobby_embed(lobby, host), 
                view=generate_lobby_view(lobby_id, lobby)
            )

    async def handle_lobby_start(self, interaction, lobby, lobby_id, uid):
        """Handle starting TTT game from lobby"""
        if uid == lobby['hostId'] and (len(lobby['players']) == lobby['maxPlayers'] or 'BOT_AI' in lobby['players']):
            del self.bot.active_lobbies[lobby_id]

            p1_id_original = lobby['players'][0]
            p2_id_original = lobby['players'][1]
            p1 = p1_id_original
            p2 = p2_id_original

            if lobby.get('starter') == 'random':
                if random.choice([True, False]):
                    p1, p2 = p2, p1
            elif lobby.get('starter') == 'guest_starts':
                p1, p2 = p2, p1
                
            game_id = f"ttt_game_{interaction.channel_id}_{p1_id_original}_{int(time.time())}"
            game_state = {
                'board': [0] * (int(lobby['boardSize']) ** 2),
                'size': int(lobby['boardSize']),
                'players': {'1': p1, '2': p2},
                'turn': 1,
                'mode': lobby['mode'],
                'history': {'1': [], '2': []},
                'start_time': time.time(),
                'last_activity': time.time(),
                'messageId': lobby['messageId']
            }
            self.bot.active_games[game_id] = game_state
            
            symbols = get_symbols(game_state)
            p1_name = "🤖 BOT" if p1 == 'BOT_AI' else f"<@{p1}>"
            p2_name = "🤖 BOT" if p2 == 'BOT_AI' else f"<@{p2}>"
            
            embed = discord.Embed(
                title=f"Tic-Tac-Toe {game_state['size']}x{game_state['size']}", 
                description=f"Turn: {p1_name} ({symbols[1]})"
            )
            bg_url = get_host_background(game_state, interaction.guild.id if interaction.guild else None)
            if bg_url:
                embed.set_image(url=bg_url)
            view = generate_board_view(game_id, game_state['board'], game_state['size'], symbols=symbols)
            
            await interaction.response.edit_message(content=f"{p1_name} vs {p2_name}", embed=embed, view=view)
            
            if p1 == 'BOT_AI':
                await handle_bot_move(self.bot, interaction.message, game_id, game_state)
        else:
            await interaction.response.send_message("Start conditions not met (e.g. missing player).", ephemeral=True)

    async def handle_lobby_settings(self, interaction, lobby, lobby_id, uid):
        """Handle opening settings menu for TTT lobby"""
        if uid == lobby['hostId']:
            view = generate_settings_selects(lobby_id, lobby)
            await interaction.response.send_message("⚙️ **Lobby Settings** (only Host can change)", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("Only the Host can change settings.", ephemeral=True)

    async def handle_ttt_move(self, interaction: discord.Interaction, cid: str):
        """Handle TTT move button clicks"""
        parts = cid.split('_')
        idx = int(parts[-1])
        game_id = "_".join(parts[2:-1])
        
        game = self.bot.active_games.get(game_id)
        if not game:
            if interaction.message.components:
                await interaction.message.edit(content="Game inactive.", view=None)
            return await interaction.response.send_message("Game inactive.", ephemeral=True)
            
        current_player_id = game['players'][str(game['turn'])]
        if str(interaction.user.id) != current_player_id:
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        
        # Defer response for AI processing
        if not interaction.response.is_done():
            await interaction.response.defer()
        
        await process_move(self.bot, interaction, game_id, game, idx)

    async def handle_ttt_rematch(self, interaction: discord.Interaction, cid: str):
        """Handle TTT rematch requests and responses"""
        if cid.startswith('ttt_rematch_accept_') or cid.startswith('ttt_rematch_deny_'):
            await self.handle_rematch_response(interaction, cid)
        else:
            await self.handle_rematch_request(interaction, cid)

    async def handle_rematch_request(self, interaction: discord.Interaction, cid: str):
        """Handle initial rematch button click"""
        game_id = cid[len('ttt_rematch_'):]
        requester_id = str(interaction.user.id)

        rematch_state = self.bot.pending_rematches.get(game_id)
        if not rematch_state:
            return await interaction.response.send_message("No data about previous game. Rematch impossible.", ephemeral=True)
        
        p1_original = rematch_state['players']['1']
        p2_original = rematch_state['players']['2']
        
        if requester_id not in [p1_original, p2_original]:
            return await interaction.response.send_message("You weren't a player in this game.", ephemeral=True)
            
        opponent_id = p2_original if requester_id == p1_original else p1_original
        opponent_mention = "🤖 BOT" if opponent_id == 'BOT_AI' else f"<@{opponent_id}>"

        if opponent_id == 'BOT_AI':
            await self.start_rematch_game(interaction, game_id, rematch_state, p1_original, p2_original)
        else:
            if 'requested_by' not in self.bot.pending_rematches[game_id]:
                self.bot.pending_rematches[game_id]['requested_by'] = requester_id
                
                try:
                    await interaction.message.delete()
                except:
                    pass
                
                await interaction.channel.send(
                    f"Rematch Request: {opponent_mention}, {interaction.user.mention} asks for a **rematch**!", 
                    view=self.generate_rematch_accept_view(game_id, opponent_id),
                    allowed_mentions=discord.AllowedMentions(users=True)
                )
            else:
                await interaction.response.send_message("You already requested a rematch, wait for opponent's response.", ephemeral=True)

    async def handle_rematch_response(self, interaction: discord.Interaction, cid: str):
        """Handle accept/deny rematch button clicks"""
        parts = cid.rsplit('_', 1)
        if len(parts) != 2:
            return await interaction.response.send_message("Error parsing custom_id.", ephemeral=True)

        target_id = parts[1]
        cid_prefix = parts[0]

        if cid_prefix.startswith('ttt_rematch_accept_'):
            action = 'accept'
            game_id = cid_prefix[len('ttt_rematch_accept_'):]
        elif cid_prefix.startswith('ttt_rematch_deny_'):
            action = 'deny'
            game_id = cid_prefix[len('ttt_rematch_deny_'):]
        else:
            return await interaction.response.send_message("Error in rematch action.", ephemeral=True)

        if str(interaction.user.id) != target_id:
            return await interaction.response.send_message("You're not the player this request is addressed to.", ephemeral=True)

        rematch_state = self.bot.pending_rematches.get(game_id)
        if not rematch_state:
            return await interaction.response.edit_message(content="Rematch request expired or already handled.", view=None)

        if action == 'accept':
            p1_original = rematch_state['players']['1']
            p2_original = rematch_state['players']['2']
            await self.start_rematch_game(interaction, game_id, rematch_state, p1_original, p2_original)
        else:
            self.bot.pending_rematches.pop(game_id, None)
            try:
                await interaction.message.delete()
            except:
                pass

    async def start_rematch_game(self, interaction, old_game_id, rematch_state, p1_original, p2_original):
        """Start a new rematch game (swap starting player)"""
        new_p1 = rematch_state['players']['2']
        new_p2 = rematch_state['players']['1']

        new_game_id = f"ttt_game_{interaction.channel.id}_{p2_original}_{int(time.time())}"
        new_game_state = {
            'board': [0] * (rematch_state['size'] ** 2),
            'size': rematch_state['size'],
            'players': {'1': new_p1, '2': new_p2},
            'turn': 1,
            'mode': rematch_state['mode'],
            'history': {'1': [], '2': []},
            'start_time': time.time(),
            'messageId': rematch_state.get('messageId')
        }
        self.bot.active_games[new_game_id] = new_game_state
        self.bot.pending_rematches.pop(old_game_id, None)

        symbols = get_symbols(new_game_state)
        p1_name = "🤖 BOT" if new_p1 == 'BOT_AI' else f"<@{new_p1}>"
        p2_name = "🤖 BOT" if new_p2 == 'BOT_AI' else f"<@{new_p2}>"

        embed = discord.Embed(
            title=f"Tic-Tac-Toe {new_game_state['size']}x{new_game_state['size']}",
            description=f"REMATCH! Turn: {p1_name} ({symbols[1]})"
        )
        view = generate_board_view(new_game_id, new_game_state['board'], new_game_state['size'], symbols=symbols)

        try:
            await interaction.message.delete()
        except:
            pass
        
        msg = await interaction.channel.send(content=f"{p1_name} vs {p2_name}", embed=embed, view=view)
        new_game_state['messageId'] = msg.id

        if new_p1 == 'BOT_AI':
            await handle_bot_move(self.bot, msg, new_game_id, new_game_state)

    def generate_rematch_accept_view(self, game_id: str, target_id: str):
        """Generate view with accept/deny buttons for rematch request"""
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="✅ Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"ttt_rematch_accept_{game_id}_{target_id}"
        ))
        view.add_item(discord.ui.Button(
            label="❌ Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"ttt_rematch_deny_{game_id}_{target_id}"
        ))
        return view

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
