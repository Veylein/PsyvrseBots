import discord
from discord import app_commands
from discord.ext import commands
import time
import asyncio
import chess
import random
from PIL import Image, ImageDraw, ImageFont
import io


class CheckersMoveModal(discord.ui.Modal, title="Make Your Move"):
    """Modal form for entering checkers moves"""
    
    move_input = discord.ui.TextInput(
        label="Enter your move",
        placeholder="e.g., 3b-4c or 3b5d (for jump)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    def __init__(self, game_id: str, game: dict, cog):
        super().__init__()
        self.game_id = game_id
        self.game = game
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the move when form is submitted"""
        move_str = self.move_input.value.strip().lower()
        
        # Parse move
        move = parse_checkers_move(self.game['board'], move_str, self.game['current_player'])
        
        if not move:
            return await interaction.response.send_message(
                f"❌ Invalid move: `{move_str}`\nUse notation like `3b-4c` (from position to position)",
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        # Execute move
        from_pos, to_pos, captured = move
        execute_checkers_move(self.game['board'], from_pos, to_pos, captured)
        self.game['move_history'].append(move_str)
        self.game['last_activity'] = time.time()
        
        # Check for multi-jump
        can_jump_again = check_additional_jumps(self.game['board'], to_pos, self.game['current_player'])
        
        if not can_jump_again:
            self.game['current_player'] = 2 if self.game['current_player'] == 1 else 1
        
        # Check game status
        is_over, status_text = get_checkers_game_status(self.game['board'], self.game['current_player'])
        
        board_file = create_checkers_board_image(self.game['board'], last_move=(from_pos, to_pos))
        
        red_name = "🤖 BOT" if self.game['red_player'] == 'BOT_AI' else f"<@{self.game['red_player']}>"
        black_name = "🤖 BOT" if self.game['black_player'] == 'BOT_AI' else f"<@{self.game['black_player']}>"
        current_name = red_name if self.game['current_player'] == 1 else black_name
        
        if is_over:
            embed = discord.Embed(
                title="🔴⚫ Checkers - Game Over",
                description=f"**Red (🔴):** {red_name}\n**Black (⚫):** {black_name}\n\n{status_text}",
                color=discord.Color.gold()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            
            msg = interaction.channel.get_partial_message(self.game['messageId'])
            await msg.edit(embed=embed, view=None, attachments=[board_file])
            
            if "Winner" in status_text:
                winner_player = 1 if "Red" in status_text else 2
                winner_id = self.game['red_player'] if winner_player == 1 else self.game['black_player']
                if winner_id != 'BOT_AI':
                    economy_cog = self.cog.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(int(winner_id), 25, reason="checkers_win")
                    
                    game_stats_cog = self.cog.bot.get_cog("GameStats")
                    if game_stats_cog:
                        duration = int(time.time() - self.game['start_time'])
                        game_stats_cog.record_game(int(winner_id), "checkers", won=True, coins_earned=25, playtime_seconds=duration, category="board_games")
            
            self.cog.bot.active_games.pop(self.game_id, None)
        else:
            extra_info = "\n⚠️ **Multi-jump! Make another jump!**" if can_jump_again else ""
            embed = discord.Embed(
                title="🔴⚫ Checkers",
                description=f"**Red (🔴):** {red_name}\n**Black (⚫):** {black_name}\n\n**Turn:** {current_name}{extra_info}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(name="📝 Last move", value=f"`{move_str}`", inline=False)
            
            view = self.cog.create_checkers_game_view(self.game_id)
            msg = interaction.channel.get_partial_message(self.game['messageId'])
            await msg.edit(embed=embed, view=view, attachments=[board_file])
            
            if (self.game['current_player'] == 1 and self.game['red_player'] == 'BOT_AI') or \
               (self.game['current_player'] == 2 and self.game['black_player'] == 'BOT_AI'):
                await asyncio.sleep(1.5)
                await self.cog.play_checkers_bot_move(interaction.channel, self.game_id, self.game)


class ChessMoveModal(discord.ui.Modal, title="Make Your Move"):
    """Modal form for entering chess moves"""
    
    move_input = discord.ui.TextInput(
        label="Enter your move",
        placeholder="e.g., e2e4 or Nf3",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    def __init__(self, game_id: str, game: dict, cog):
        super().__init__()
        self.game_id = game_id
        self.game = game
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the move when form is submitted"""
        move_str = self.move_input.value.strip()
        
        # Parse move
        move = parse_move(self.game['board'], move_str)
        
        if not move:
            return await interaction.response.send_message(
                f"❌ Invalid move: `{move_str}`\nPlease use notation like `e2e4` or `Nf3`",
                ephemeral=True
            )
        
        # Defer the response since we'll be editing the game message
        await interaction.response.defer()
        
        # Execute move
        self.game['board'].push(move)
        self.game['move_history'].append(move)
        self.game['last_activity'] = time.time()
        
        # Change turn
        self.game['current_turn'] = self.game['black_player'] if self.game['current_turn'] == self.game['white_player'] else self.game['white_player']
        
        # Check game status
        is_over, status_text = get_game_status(self.game['board'])
        
        # Generate new board image
        board_file = create_board_image(
            self.game['board'],
            last_move=move,
            board_theme=self.game['board_theme'],
            piece_set=self.game['piece_set']
        )
        
        white_name = "🤖 BOT" if self.game['white_player'] == 'BOT_AI' else f"<@{self.game['white_player']}>"
        black_name = "🤖 BOT" if self.game['black_player'] == 'BOT_AI' else f"<@{self.game['black_player']}>"
        current_name = "🤖 BOT" if self.game['current_turn'] == 'BOT_AI' else f"<@{self.game['current_turn']}>"
        
        if is_over:
            # Game ended
            embed = discord.Embed(
                title="♟️ Chess - Game Over",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n{status_text}",
                color=discord.Color.gold()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📊 Statistics",
                value=f"Moves: {len(self.game['move_history'])}",
                inline=False
            )
            
            msg = interaction.channel.get_partial_message(self.game['messageId'])
            await msg.edit(embed=embed, view=None, attachments=[board_file])
            
            # Save result (if not a draw)
            if "Winner" in status_text or "Wins" in status_text:
                winner = self.game['white_player'] if "White" in status_text else self.game['black_player']
                if winner != 'BOT_AI':
                    duration = int((time.time() - self.game['start_time']) * 1000)
                    is_multiplayer = self.game['white_player'] != 'BOT_AI' and self.game['black_player'] != 'BOT_AI'
                    
                    # Award coins using Economy cog
                    economy_cog = self.cog.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(int(winner), 30, reason="chess_win")
                    
                    # Record game stats
                    game_stats_cog = self.cog.bot.get_cog("GameStats")
                    if game_stats_cog:
                        game_stats_cog.record_game(
                            int(winner),
                            "chess",
                            won=True,
                            coins_earned=30,
                            playtime_seconds=duration//1000,
                            category="board_games"
                        )
            
            self.cog.bot.active_games.pop(self.game_id, None)
        else:
            # Game continues
            embed = discord.Embed(
                title="♟️ Chess",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n**Turn:** {current_name}\n{status_text}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📝 Last move",
                value=f"`{move.uci()}`",
                inline=False
            )
            
            view = self.cog.create_chess_game_view(self.game_id)
            msg = interaction.channel.get_partial_message(self.game['messageId'])
            await msg.edit(embed=embed, view=view, attachments=[board_file])
            
            # If next player is bot
            if self.game['current_turn'] == 'BOT_AI':
                await asyncio.sleep(1.5)
                await self.cog.play_bot_move(interaction.channel, self.game_id, self.game)


class DrawOfferView(discord.ui.View):
    """View for accepting or declining draw offer"""
    
    def __init__(self, game_id: str, offering_player_id: str):
        super().__init__(timeout=60)
        self.game_id = game_id
        self.offering_player_id = offering_player_id
    
    @discord.ui.button(label="✅ Accept Draw", style=discord.ButtonStyle.success, custom_id="chess_draw_accept")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Will be handled by handle_chess_interaction
        pass
    
    @discord.ui.button(label="❌ Decline Draw", style=discord.ButtonStyle.danger, custom_id="chess_draw_decline")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Will be handled by handle_chess_interaction
        pass


class ChessCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def get_player_chess_theme(self, guild_id, player_id):
        """Get player's chess board theme"""
        if player_id == 'BOT_AI':
            return 'classic'
        
        # Try to get from Economy cog's shop items
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            return 'classic'
        
        user_data = economy_cog.economy_data.get(str(player_id), {})
        active_board = user_data.get('active_chess_board', 'classic')
        
        # Mapping shop IDs to theme names
        theme_map = {
            'chess_board_blue': 'blue',
            'chess_board_green': 'green',
            'chess_board_brown': 'brown',
            'chess_board_red': 'red',
            'chess_board_purple': 'purple',
            'classic': 'classic'
        }
        
        return theme_map.get(active_board, 'classic')
    
    def generate_chess_lobby_view(self, lobby_id, lobby):
        """Generate chess lobby view"""
        view = discord.ui.View(timeout=None)
        
        is_full = len(lobby['players']) >= 2
        is_bot_game = 'BOT_AI' in lobby['players']
        
        view.add_item(discord.ui.Button(
            label="Join",
            style=discord.ButtonStyle.success,
            custom_id=f"chess_lobby_join_{lobby_id}",
            disabled=(is_full or is_bot_game)
        ))
        
        view.add_item(discord.ui.Button(
            label="🤖 Play vs Bot",
            style=discord.ButtonStyle.primary,
            custom_id=f"chess_lobby_bot_{lobby_id}",
            disabled=is_bot_game
        ))
        
        view.add_item(discord.ui.Button(
            label="Leave",
            style=discord.ButtonStyle.secondary,
            custom_id=f"chess_lobby_leave_{lobby_id}"
        ))
        
        view.add_item(discord.ui.Button(
            label="Start",
            style=discord.ButtonStyle.success,
            custom_id=f"chess_lobby_start_{lobby_id}",
            disabled=not (is_full or is_bot_game),
            row=1
        ))
        
        return view
    
    @app_commands.command(name="chess", description="Create a chess lobby")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def chess_command(self, interaction: discord.Interaction):
        """Command to start a chess game"""
        uid = str(interaction.user.id)
        
        # Ensure player exists in economy
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.get_balance(int(uid))
        
        # Create lobby
        lobby_id = f"chess_{interaction.channel.id}_{int(time.time())}"
        lobby = {
            'game': 'chess',
            'hostId': uid,
            'players': [uid],
            'messageId': None,
            'last_activity': time.time()
        }
        
        self.bot.active_lobbies[lobby_id] = lobby
        
        embed = discord.Embed(
            title="♟️ Chess - Lobby",
            description=f"**Host:** <@{uid}>\n\n**Players:** 1/2\n<@{uid}>",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 How to play?",
            value="• Moves in notation: **e2e4** or **Nf3**\n• Click Start when ready!",
            inline=False
        )
        
        view = self.generate_chess_lobby_view(lobby_id, lobby)
        
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        lobby['messageId'] = msg.id
    
    async def handle_chess_interaction(self, interaction: discord.Interaction, cid: str):
        """Router for all chess interactions"""
        if cid.startswith('chess_lobby_'):
            await self.handle_chess_lobby(interaction, cid)
        elif cid.startswith('chess_move_'):
            await self.handle_chess_move(interaction, cid)
        elif cid.startswith('chess_resign_'):
            await self.handle_chess_resign(interaction, cid)
        elif cid.startswith('chess_draw_offer_'):
            await self.handle_chess_draw_offer(interaction, cid)
        elif cid == 'chess_draw_accept':
            await self.handle_chess_draw_response(interaction, accept=True)
        elif cid == 'chess_draw_decline':
            await self.handle_chess_draw_response(interaction, accept=False)
    
    async def handle_chess_lobby(self, interaction: discord.Interaction, cid: str):
        """Handle actions in chess lobby"""
        parts = cid.split('_')
        action = parts[2]
        lobby_id = "_".join(parts[3:])
        
        lobby = self.bot.active_lobbies.get(lobby_id)
        if not lobby:
            return await interaction.response.send_message("Lobby doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        
        # Ensure player exists in economy
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.get_balance(int(uid))
        
        if action == 'join':
            await self.handle_lobby_join(interaction, lobby, lobby_id, uid)
        elif action == 'bot':
            await self.handle_lobby_bot(interaction, lobby, lobby_id, uid)
        elif action == 'leave':
            await self.handle_lobby_leave(interaction, lobby, lobby_id, uid)
        elif action == 'start':
            await self.handle_lobby_start(interaction, lobby, lobby_id, uid)
    
    async def handle_lobby_join(self, interaction, lobby, lobby_id, uid):
        """Player joins lobby"""
        if uid not in lobby['players']:
            if 'BOT_AI' in lobby['players']:
                lobby['players'].remove('BOT_AI')
            
            lobby['players'].append(uid)
            lobby['last_activity'] = time.time()
            
            players_text = "\n".join([f"<@{p}>" for p in lobby['players']])
            embed = discord.Embed(
                title="♟️ Chess - Lobby",
                description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 How to play?",
                value="• Moves in notation: **e2e4** or **Nf3**\n• Click Start when ready!",
                inline=False
            )
            
            await interaction.message.edit(embed=embed, view=self.generate_chess_lobby_view(lobby_id, lobby))
            await interaction.response.defer()
        else:
            await interaction.response.send_message("You're already here.", ephemeral=True)
    
    async def handle_lobby_bot(self, interaction, lobby, lobby_id, uid):
        """Add bot to lobby"""
        if uid == lobby['hostId']:
            if len(lobby['players']) > 1:
                lobby['players'].pop(1)
            
            if 'BOT_AI' not in lobby['players']:
                lobby['players'].append('BOT_AI')
            
            players_text = "\n".join([f"<@{p}>" if p != 'BOT_AI' else "🤖 BOT" for p in lobby['players']])
            embed = discord.Embed(
                title="♟️ Chess - Lobby",
                description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 How to play?",
                value="• Moves in notation: **e2e4** or **Nf3**\n• Click Start when ready!",
                inline=False
            )
            
            await interaction.message.edit(embed=embed, view=self.generate_chess_lobby_view(lobby_id, lobby))
            await interaction.response.defer()
        else:
            await interaction.response.send_message("Only the host can add a bot.", ephemeral=True)
    
    async def handle_lobby_leave(self, interaction, lobby, lobby_id, uid):
        """Player leaves lobby"""
        if uid in lobby['players']:
            lobby['players'].remove(uid)
            
            if not lobby['players']:
                self.bot.active_lobbies.pop(lobby_id, None)
                await interaction.message.delete()
                await interaction.response.defer()
                return
            
            if uid == lobby['hostId']:
                lobby['hostId'] = lobby['players'][0]
            
            players_text = "\n".join([f"<@{p}>" if p != 'BOT_AI' else "🤖 BOT" for p in lobby['players']])
            embed = discord.Embed(
                title="♟️ Chess - Lobby",
                description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 How to play?",
                value="• Moves in notation: **e2e4** or **Nf3**\n• Click Start when ready!",
                inline=False
            )
            
            await interaction.message.edit(embed=embed, view=self.generate_chess_lobby_view(lobby_id, lobby))
            await interaction.response.defer()
        else:
            await interaction.response.send_message("You're not in this lobby.", ephemeral=True)
    
    async def handle_lobby_start(self, interaction, lobby, lobby_id, uid):
        """Start chess game"""
        if len(lobby['players']) < 2:
            return await interaction.response.send_message("Need 2 players!", ephemeral=True)
        
        
        game_id = lobby_id
        board = chess.Board()
        
        game = {
            'game_id': game_id,
            'players': lobby['players'].copy(),
            'board': board,
            'white_player': lobby['players'][0],
            'black_player': lobby['players'][1],
            'current_turn': lobby['players'][0],  # White starts
            'start_time': time.time(),
            'last_activity': time.time(),
            'move_history': [],
            'board_theme': self.get_player_chess_theme(interaction.guild.id if interaction.guild else None, lobby['players'][0]),
            'piece_set': 'classic'
        }
        
        self.bot.active_games[game_id] = game
        self.bot.active_lobbies.pop(lobby_id, None)
        
        # Generate board image
        board_file = create_board_image(board, board_theme=game['board_theme'])
        
        white_name = "🤖 BOT" if game['white_player'] == 'BOT_AI' else f"<@{game['white_player']}>"
        black_name = "🤖 BOT" if game['black_player'] == 'BOT_AI' else f"<@{game['black_player']}>"
        
        embed = discord.Embed(
            title="♟️ Chess - Game Started",
            description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n**Turn:** {white_name}",
            color=discord.Color.blue()
        )
        embed.set_image(url=f"attachment://{board_file.filename}")
        embed.add_field(
            name="📝 How to make a move?",
            value="Type move in notation: `e2e4` or `Nf3`",
            inline=False
        )
        
        view = self.create_chess_game_view(game_id)
        
        await interaction.message.edit(embed=embed, view=view, attachments=[board_file])
        await interaction.response.defer()
        
        # Save message ID
        game['messageId'] = interaction.message.id
        
        # If white is bot, make move
        if game['white_player'] == 'BOT_AI':
            await asyncio.sleep(1)
            await self.play_bot_move(interaction.channel, game_id, game)
    
    def create_chess_game_view(self, game_id):
        """Create game view"""
        view = discord.ui.View(timeout=None)
        
        view.add_item(discord.ui.Button(
            label="📝 Make Move",
            style=discord.ButtonStyle.primary,
            custom_id=f"chess_move_{game_id}"
        ))
        
        view.add_item(discord.ui.Button(
            label="🏳️ Resign",
            style=discord.ButtonStyle.danger,
            custom_id=f"chess_resign_{game_id}"
        ))
        
        view.add_item(discord.ui.Button(
            label="🤝 Offer Draw",
            style=discord.ButtonStyle.secondary,
            custom_id=f"chess_draw_offer_{game_id}"
        ))
        
        return view
    
    async def handle_chess_move(self, interaction, cid):
        """Handle move action - show modal form"""
        game_id = cid[len('chess_move_'):]
        game = self.bot.active_games.get(game_id)
        
        if not game:
            return await interaction.response.send_message("Game doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if uid not in game['players']:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        
        # Check if it's this player's turn
        if uid != game['current_turn']:
            current_player = "🤖 BOT" if game['current_turn'] == 'BOT_AI' else f"<@{game['current_turn']}>"
            return await interaction.response.send_message(f"It's not your turn! Current turn: {current_player}", ephemeral=True)
        
        # Show modal form
        modal = ChessMoveModal(game_id, game, self)
        await interaction.response.send_modal(modal)
    
    async def handle_chess_resign(self, interaction, cid):
        """Player resigns"""
        game_id = cid[len('chess_resign_'):]
        game = self.bot.active_games.get(game_id)
        
        if not game:
            return await interaction.response.send_message("Game doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if uid not in game['players']:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        
        winner = game['black_player'] if uid == game['white_player'] else game['white_player']
        winner_name = "🤖 BOT" if winner == 'BOT_AI' else f"<@{winner}>"
        
        embed = discord.Embed(
            title="♟️ Chess - Game Over",
            description=f"🏳️ <@{uid}> resigned!\n\n🏆 Winner: {winner_name}",
            color=discord.Color.red()
        )
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.defer()
        
        # Save result
        if winner != 'BOT_AI':
            duration = int((time.time() - game['start_time']) * 1000)
            is_multiplayer = game['white_player'] != 'BOT_AI' and game['black_player'] != 'BOT_AI'
            
            # Award coins using Economy cog
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(int(winner), 20, reason="chess_win")
            
            # Record game stats
            game_stats_cog = self.bot.get_cog("GameStats")
            if game_stats_cog:
                game_stats_cog.record_game(
                    int(winner),
                    "chess",
                    won=True,
                    coins_earned=20,
                    playtime_seconds=duration//1000,
                    category="board_games"
                )
        
        self.bot.active_games.pop(game_id, None)
    
    async def handle_chess_draw_offer(self, interaction, cid):
        """Player offers a draw"""
        game_id = cid[len('chess_draw_offer_'):]
        game = self.bot.active_games.get(game_id)
        
        if not game:
            return await interaction.response.send_message("Game doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if uid not in game['players']:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        
        # Can't offer draw to bot
        if 'BOT_AI' in game['players']:
            return await interaction.response.send_message("❌ You cannot offer a draw against the bot. Use Resign button instead.", ephemeral=True)
        
        # Get opponent
        opponent_id = game['black_player'] if uid == game['white_player'] else game['white_player']
        
        # Create draw offer message
        embed = discord.Embed(
            title="🤝 Draw Offer",
            description=f"<@{uid}> is offering a draw to <@{opponent_id}>.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="To accept or decline",
            value=f"<@{opponent_id}>, please click one of the buttons below.",
            inline=False
        )
        
        # Store draw offer info in game
        game['draw_offer'] = {
            'offering_player': uid,
            'opponent': opponent_id
        }
        
        view = DrawOfferView(game_id, uid)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def handle_chess_draw_response(self, interaction, accept: bool):
        """Handle acceptance or decline of draw offer"""
        uid = str(interaction.user.id)
        
        # Find the game with active draw offer
        game = None
        game_id = None
        for gid, g in self.bot.active_games.items():
            if gid.startswith('chess_') and g.get('draw_offer'):
                if g['draw_offer']['opponent'] == uid:
                    game = g
                    game_id = gid
                    break
        
        if not game:
            return await interaction.response.send_message("❌ No active draw offer found for you.", ephemeral=True)
        
        offering_player = game['draw_offer']['offering_player']
        
        if accept:
            # Accept draw - end game
            board_file = create_board_image(
                game['board'],
                board_theme=game['board_theme'],
                piece_set=game['piece_set']
            )
            
            white_name = f"<@{game['white_player']}>"
            black_name = f"<@{game['black_player']}>"
            
            embed = discord.Embed(
                title="♟️ Chess - Game Over",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n🤝 **Draw by agreement**",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📊 Statistics",
                value=f"Moves: {len(game['move_history'])}",
                inline=False
            )
            
            # Edit game message
            try:
                channel = interaction.channel
                msg = channel.get_partial_message(game['messageId'])
                await msg.edit(embed=embed, view=None, attachments=[board_file])
            except:
                pass
            
            # Delete draw offer message
            await interaction.message.delete()
            
            await interaction.response.send_message(
                f"✅ <@{uid}> accepted the draw offer. Game ended in a draw!",
                ephemeral=False
            )
            
            # Record draw for both players (no coins awarded)
            duration = int((time.time() - game['start_time']) * 1000)
            game_stats_cog = self.bot.get_cog("GameStats")
            if game_stats_cog:
                for player_id in [game['white_player'], game['black_player']]:
                    game_stats_cog.record_game(
                        int(player_id),
                        "chess",
                        won=False,
                        coins_earned=0,
                        playtime_seconds=duration//1000,
                        category="board_games"
                    )
            
            self.bot.active_games.pop(game_id, None)
        else:
            # Decline draw
            game.pop('draw_offer', None)
            
            await interaction.message.delete()
            await interaction.response.send_message(
                f"❌ <@{uid}> declined the draw offer from <@{offering_player}>. Game continues!",
                ephemeral=False
            )
    
    async def process_chess_move(self, message, game_id, game):
        """Process move from text message"""
        
        uid = str(message.author.id)
        
        # Check if it's this player's turn
        if uid != game['current_turn']:
            return
        
        # Parse move
        move = parse_move(game['board'], message.content)
        
        if not move:
            return  # Invalid move - ignore
        
        # Execute move
        game['board'].push(move)
        game['move_history'].append(move)
        game['last_activity'] = time.time()
        
        # Change turn
        game['current_turn'] = game['black_player'] if game['current_turn'] == game['white_player'] else game['white_player']
        
        # Check game status
        is_over, status_text = get_game_status(game['board'])
        
        # Generate new board image
        board_file = create_board_image(
            game['board'],
            last_move=move,
            board_theme=game['board_theme'],
            piece_set=game['piece_set']
        )
        
        white_name = "🤖 BOT" if game['white_player'] == 'BOT_AI' else f"<@{game['white_player']}>"
        black_name = "🤖 BOT" if game['black_player'] == 'BOT_AI' else f"<@{game['black_player']}>"
        current_name = "🤖 BOT" if game['current_turn'] == 'BOT_AI' else f"<@{game['current_turn']}>"
        
        if is_over:
            # Game ended
            embed = discord.Embed(
                title="♟️ Chess - Game Over",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n{status_text}",
                color=discord.Color.gold()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📊 Statistics",
                value=f"Moves: {len(game['move_history'])}",
                inline=False
            )
            
            msg = message.channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=None, attachments=[board_file])
            
            # Save result (if not a draw)
            if "Winner" in status_text or "Wins" in status_text:
                winner = game['white_player'] if "White" in status_text else game['black_player']
                if winner != 'BOT_AI':
                    duration = int((time.time() - game['start_time']) * 1000)
                    is_multiplayer = game['white_player'] != 'BOT_AI' and game['black_player'] != 'BOT_AI'
                    
                    # Award coins using Economy cog
                    economy_cog = self.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(int(winner), 30, reason="chess_win")
                    
                    # Record game stats
                    game_stats_cog = self.bot.get_cog("GameStats")
                    if game_stats_cog:
                        game_stats_cog.record_game(
                            int(winner),
                            "chess",
                            won=True,
                            coins_earned=30,
                            playtime_seconds=duration//1000,
                            category="board_games"
                        )
            
            self.bot.active_games.pop(game_id, None)
        else:
            # Game continues
            embed = discord.Embed(
                title="♟️ Chess",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n**Turn:** {current_name}\n{status_text}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📝 Last move",
                value=f"`{move.uci()}`",
                inline=False
            )
            
            view = self.create_chess_game_view(game_id)
            msg = message.channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=view, attachments=[board_file])
            
            # Delete player's message
            try:
                await message.delete()
            except:
                pass
            
            # If next player is bot
            if game['current_turn'] == 'BOT_AI':
                await asyncio.sleep(1.5)
                await self.play_bot_move(message.channel, game_id, game)
    
    async def play_bot_move(self, channel, game_id, game):
        """Bot makes a move"""
        
        move = get_bot_move(game['board'], difficulty='easy')
        
        if not move:
            return
        
        # Execute move
        game['board'].push(move)
        game['move_history'].append(move)
        game['last_activity'] = time.time()
        
        # Change turn
        game['current_turn'] = game['black_player'] if game['current_turn'] == game['white_player'] else game['white_player']
        
        # Check game status
        is_over, status_text = get_game_status(game['board'])
        
        # Generate new board image
        board_file = create_board_image(
            game['board'],
            last_move=move,
            board_theme=game['board_theme'],
            piece_set=game['piece_set']
        )
        
        white_name = "🤖 BOT" if game['white_player'] == 'BOT_AI' else f"<@{game['white_player']}>"
        black_name = "🤖 BOT" if game['black_player'] == 'BOT_AI' else f"<@{game['black_player']}>"
        current_name = "🤖 BOT" if game['current_turn'] == 'BOT_AI' else f"<@{game['current_turn']}>"
        
        if is_over:
            # Game ended
            embed = discord.Embed(
                title="♟️ Chess - Game Over",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n{status_text}",
                color=discord.Color.gold()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📊 Statistics",
                value=f"Moves: {len(game['move_history'])}",
                inline=False
            )
            
            msg = channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=None, attachments=[board_file])
            
            # Save result (if not a draw and player won)
            if "Winner" in status_text or "Wins" in status_text:
                winner = game['white_player'] if "White" in status_text else game['black_player']
                if winner != 'BOT_AI':
                    duration = int((time.time() - game['start_time']) * 1000)
                    
                    # Award coins using Economy cog
                    economy_cog = self.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(int(winner), 30, reason="chess_win")
                    
                    # Record game stats
                    game_stats_cog = self.bot.get_cog("GameStats")
                    if game_stats_cog:
                        game_stats_cog.record_game(
                            int(winner),
                            "chess",
                            won=True,
                            coins_earned=30,
                            playtime_seconds=duration//1000,
                            category="board_games"
                        )
            
            self.bot.active_games.pop(game_id, None)
        else:
            # Game continues
            embed = discord.Embed(
                title="♟️ Chess",
                description=f"**White (⬜):** {white_name}\n**Black (⬛):** {black_name}\n\n**Turn:** {current_name}\n{status_text}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="🤖 Bot played",
                value=f"`{move.uci()}`",
                inline=False
            )
            
            view = self.create_chess_game_view(game_id)
            msg = channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=view, attachments=[board_file])
    
    # === CHECKERS IMPLEMENTATION ===
    
    @app_commands.command(name="checkers", description="Create a checkers lobby")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def checkers_command(self, interaction: discord.Interaction):
        """Command to start a checkers game"""
        uid = str(interaction.user.id)
        
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.get_balance(int(uid))
        
        lobby_id = f"checkers_{interaction.channel.id}_{int(time.time())}"
        lobby = {
            'game': 'checkers',
            'hostId': uid,
            'players': [uid],
            'messageId': None,
            'last_activity': time.time()
        }
        
        self.bot.active_lobbies[lobby_id] = lobby
        
        embed = discord.Embed(
            title="🔴⚫ Checkers - Lobby",
            description=f"**Host:** <@{uid}>\n\n**Players:** 1/2\n<@{uid}>",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 How to play?",
            value="• Moves: **3b-4c** (row+column to row+column)\n• Jump over opponent pieces to capture!\n• Reach the other end to become a King 👑",
            inline=False
        )
        
        view = self.generate_checkers_lobby_view(lobby_id, lobby)
        
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        lobby['messageId'] = msg.id
    
    def generate_checkers_lobby_view(self, lobby_id, lobby):
        """Generate checkers lobby view"""
        view = discord.ui.View(timeout=None)
        
        is_full = len(lobby['players']) >= 2
        is_bot_game = 'BOT_AI' in lobby['players']
        
        view.add_item(discord.ui.Button(
            label="Join",
            style=discord.ButtonStyle.success,
            custom_id=f"checkers_lobby_join_{lobby_id}",
            disabled=(is_full or is_bot_game)
        ))
        
        view.add_item(discord.ui.Button(
            label="🤖 Play vs Bot",
            style=discord.ButtonStyle.primary,
            custom_id=f"checkers_lobby_bot_{lobby_id}",
            disabled=is_bot_game
        ))
        
        view.add_item(discord.ui.Button(
            label="Leave",
            style=discord.ButtonStyle.secondary,
            custom_id=f"checkers_lobby_leave_{lobby_id}"
        ))
        
        view.add_item(discord.ui.Button(
            label="Start",
            style=discord.ButtonStyle.success,
            custom_id=f"checkers_lobby_start_{lobby_id}",
            disabled=not (is_full or is_bot_game),
            row=1
        ))
        
        return view
    
    async def handle_checkers_interaction(self, interaction: discord.Interaction, cid: str):
        """Router for checkers interactions"""
        if cid.startswith('checkers_lobby_'):
            await self.handle_checkers_lobby(interaction, cid)
        elif cid.startswith('checkers_move_'):
            await self.handle_checkers_move(interaction, cid)
        elif cid.startswith('checkers_resign_'):
            await self.handle_checkers_resign(interaction, cid)
    
    async def handle_checkers_lobby(self, interaction: discord.Interaction, cid: str):
        """Handle checkers lobby actions"""
        parts = cid.split('_')
        action = parts[2]
        lobby_id = "_".join(parts[3:])
        
        lobby = self.bot.active_lobbies.get(lobby_id)
        if not lobby:
            return await interaction.response.send_message("Lobby doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.get_balance(int(uid))
        
        if action == 'join':
            if uid not in lobby['players']:
                if 'BOT_AI' in lobby['players']:
                    lobby['players'].remove('BOT_AI')
                
                lobby['players'].append(uid)
                lobby['last_activity'] = time.time()
                
                players_text = "\n".join([f"<@{p}>" for p in lobby['players']])
                embed = discord.Embed(
                    title="🔴⚫ Checkers - Lobby",
                    description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📋 How to play?",
                    value="• Moves: **3b-4c** (row+column to row+column)\n• Jump over opponent pieces to capture!\n• Reach the other end to become a King 👑",
                    inline=False
                )
                
                await interaction.message.edit(embed=embed, view=self.generate_checkers_lobby_view(lobby_id, lobby))
                await interaction.response.defer()
            else:
                await interaction.response.send_message("You're already here.", ephemeral=True)
        
        elif action == 'bot':
            if uid == lobby['hostId']:
                if len(lobby['players']) > 1:
                    lobby['players'].pop(1)
                
                if 'BOT_AI' not in lobby['players']:
                    lobby['players'].append('BOT_AI')
                
                players_text = "\n".join([f"<@{p}>" if p != 'BOT_AI' else "🤖 BOT" for p in lobby['players']])
                embed = discord.Embed(
                    title="🔴⚫ Checkers - Lobby",
                    description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📋 How to play?",
                    value="• Moves: **3b-4c** (row+column to row+column)\n• Jump over opponent pieces to capture!\n• Reach the other end to become a King 👑",
                    inline=False
                )
                
                await interaction.message.edit(embed=embed, view=self.generate_checkers_lobby_view(lobby_id, lobby))
                await interaction.response.defer()
            else:
                await interaction.response.send_message("Only the host can add a bot.", ephemeral=True)
        
        elif action == 'leave':
            if uid in lobby['players']:
                lobby['players'].remove(uid)
                
                if not lobby['players']:
                    self.bot.active_lobbies.pop(lobby_id, None)
                    await interaction.message.delete()
                    await interaction.response.defer()
                    return
                
                if uid == lobby['hostId']:
                    lobby['hostId'] = lobby['players'][0]
                
                players_text = "\n".join([f"<@{p}>" if p != 'BOT_AI' else "🤖 BOT" for p in lobby['players']])
                embed = discord.Embed(
                    title="🔴⚫ Checkers - Lobby",
                    description=f"**Host:** <@{lobby['hostId']}>\n\n**Players:** {len(lobby['players'])}/2\n{players_text}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="📋 How to play?",
                    value="• Moves: **3b-4c** (row+column to row+column)\n• Jump over opponent pieces to capture!\n• Reach the other end to become a King 👑",
                    inline=False
                )
                
                await interaction.message.edit(embed=embed, view=self.generate_checkers_lobby_view(lobby_id, lobby))
                await interaction.response.defer()
            else:
                await interaction.response.send_message("You're not in this lobby.", ephemeral=True)
        
        elif action == 'start':
            if len(lobby['players']) < 2:
                return await interaction.response.send_message("Need 2 players!", ephemeral=True)
            
            game_id = lobby_id
            board = create_empty_checkers_board()
            
            game = {
                'game_id': game_id,
                'players': lobby['players'].copy(),
                'board': board,
                'red_player': lobby['players'][0],
                'black_player': lobby['players'][1],
                'current_player': 1,  # Red starts
                'start_time': time.time(),
                'last_activity': time.time(),
                'move_history': []
            }
            
            self.bot.active_games[game_id] = game
            self.bot.active_lobbies.pop(lobby_id, None)
            
            board_file = create_checkers_board_image(board)
            
            red_name = "🤖 BOT" if game['red_player'] == 'BOT_AI' else f"<@{game['red_player']}>"
            black_name = "🤖 BOT" if game['black_player'] == 'BOT_AI' else f"<@{game['black_player']}>"
            
            embed = discord.Embed(
                title="🔴⚫ Checkers - Game Started",
                description=f"**Red (🔴):** {red_name}\n**Black (⚫):** {black_name}\n\n**Turn:** {red_name}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(
                name="📝 How to move?",
                value="Click **Make Move** button and enter: `3b-4c`\n• Format: row+column to row+column\n• Example: `3b-4c` or `5d-6e`",
                inline=False
            )
            
            view = self.create_checkers_game_view(game_id)
            
            await interaction.message.edit(embed=embed, view=view, attachments=[board_file])
            await interaction.response.defer()
            
            game['messageId'] = interaction.message.id
            
            if game['red_player'] == 'BOT_AI':
                await asyncio.sleep(1)
                await self.play_checkers_bot_move(interaction.channel, game_id, game)
    
    def create_checkers_game_view(self, game_id):
        """Create checkers game view"""
        view = discord.ui.View(timeout=None)
        
        view.add_item(discord.ui.Button(
            label="📝 Make Move",
            style=discord.ButtonStyle.primary,
            custom_id=f"checkers_move_{game_id}"
        ))
        
        view.add_item(discord.ui.Button(
            label="🏳️ Resign",
            style=discord.ButtonStyle.danger,
            custom_id=f"checkers_resign_{game_id}"
        ))
        
        return view
    
    async def handle_checkers_move(self, interaction, cid):
        """Show modal for checkers move"""
        game_id = cid[len('checkers_move_'):]
        game = self.bot.active_games.get(game_id)
        
        if not game:
            return await interaction.response.send_message("Game doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if uid not in game['players']:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        
        # Check turn
        current_player_id = game['red_player'] if game['current_player'] == 1 else game['black_player']
        if uid != current_player_id:
            return await interaction.response.send_message(f"It's not your turn!", ephemeral=True)
        
        modal = CheckersMoveModal(game_id, game, self)
        await interaction.response.send_modal(modal)
    
    async def handle_checkers_resign(self, interaction, cid):
        """Player resigns"""
        game_id = cid[len('checkers_resign_'):]
        game = self.bot.active_games.get(game_id)
        
        if not game:
            return await interaction.response.send_message("Game doesn't exist.", ephemeral=True)
        
        uid = str(interaction.user.id)
        if uid not in game['players']:
            return await interaction.response.send_message("You're not in this game.", ephemeral=True)
        
        resigner = 1 if uid == game['red_player'] else 2
        winner = 2 if resigner == 1 else 1
        winner_id = game['black_player'] if winner == 2 else game['red_player']
        winner_name = "🤖 BOT" if winner_id == 'BOT_AI' else f"<@{winner_id}>"
        
        embed = discord.Embed(
            title="🔴⚫ Checkers - Game Over",
            description=f"🏳️ <@{uid}> resigned!\n\n🏆 Winner: {winner_name}",
            color=discord.Color.red()
        )
        
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.defer()
        
        if winner_id != 'BOT_AI':
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(int(winner_id), 20, reason="checkers_win")
            
            game_stats_cog = self.bot.get_cog("GameStats")
            if game_stats_cog:
                duration = int(time.time() - game['start_time'])
                game_stats_cog.record_game(int(winner_id), "checkers", won=True, coins_earned=20, playtime_seconds=duration, category="board_games")
        
        self.bot.active_games.pop(game_id, None)
    
    async def play_checkers_bot_move(self, channel, game_id, game):
        """Bot makes a checkers move"""
        move = get_checkers_bot_move(game['board'], game['current_player'])
        
        if not move:
            return
        
        from_pos, to_pos, captured = move
        execute_checkers_move(game['board'], from_pos, to_pos, captured)
        
        # Format move string
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        move_str = f"{from_row+1}{chr(ord('a')+from_col)}-{to_row+1}{chr(ord('a')+to_col)}"
        game['move_history'].append(move_str)
        game['last_activity'] = time.time()
        
        # Check multi-jump
        can_jump_again = check_additional_jumps(game['board'], to_pos, game['current_player'])
        
        if not can_jump_again:
            game['current_player'] = 2 if game['current_player'] == 1 else 1
        
        is_over, status_text = get_checkers_game_status(game['board'], game['current_player'])
        
        board_file = create_checkers_board_image(game['board'], last_move=(from_pos, to_pos))
        
        red_name = "🤖 BOT" if game['red_player'] == 'BOT_AI' else f"<@{game['red_player']}>"
        black_name = "🤖 BOT" if game['black_player'] == 'BOT_AI' else f"<@{game['black_player']}>"
        current_name = red_name if game['current_player'] == 1 else black_name
        
        if is_over:
            embed = discord.Embed(
                title="🔴⚫ Checkers - Game Over",
                description=f"**Red (🔴):** {red_name}\n**Black (⚫):** {black_name}\n\n{status_text}",
                color=discord.Color.gold()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            
            msg = channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=None, attachments=[board_file])
            
            if "Winner" in status_text:
                winner_player = 1 if "Red" in status_text else 2
                winner_id = game['red_player'] if winner_player == 1 else game['black_player']
                if winner_id != 'BOT_AI':
                    economy_cog = self.bot.get_cog("Economy")
                    if economy_cog:
                        economy_cog.add_coins(int(winner_id), 25, reason="checkers_win")
                    
                    game_stats_cog = self.bot.get_cog("GameStats")
                    if game_stats_cog:
                        duration = int(time.time() - game['start_time'])
                        game_stats_cog.record_game(int(winner_id), "checkers", won=True, coins_earned=25, playtime_seconds=duration, category="board_games")
            
            self.bot.active_games.pop(game_id, None)
        else:
            extra_info = "\n⚠️ **Bot has multi-jump!**" if can_jump_again else ""
            embed = discord.Embed(
                title="🔴⚫ Checkers",
                description=f"**Red (🔴):** {red_name}\n**Black (⚫):** {black_name}\n\n**Turn:** {current_name}{extra_info}",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://{board_file.filename}")
            embed.add_field(name="🤖 Bot played", value=f"`{move_str}`", inline=False)
            
            view = self.create_checkers_game_view(game_id)
            msg = channel.get_partial_message(game['messageId'])
            await msg.edit(embed=embed, view=view, attachments=[board_file])
            
            if can_jump_again:
                await asyncio.sleep(1)
                await self.play_checkers_bot_move(channel, game_id, game)


async def setup(bot):
    await bot.add_cog(ChessCog(bot))


# Piece symbols mapped to Unicode emoji
PIECE_SYMBOLS = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',  # White
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'   # Black
}

# Board colors (cosmetics)
BOARD_THEMES = {
    'classic': {'light': (240, 217, 181), 'dark': (181, 136, 99)},
    'blue': {'light': (222, 227, 230), 'dark': (140, 162, 173)},
    'green': {'light': (238, 238, 210), 'dark': (118, 150, 86)},
    'brown': {'light': (240, 217, 181), 'dark': (149, 116, 88)},
    'red': {'light': (255, 206, 158), 'dark': (209, 139, 71)},
    'purple': {'light': (230, 220, 245), 'dark': (160, 130, 195)},
}

# Piece sets (cosmetics)
PIECE_SETS = {
    'classic': 'standard',  # Standard pieces
    'modern': 'modern',
    'fantasy': 'fantasy',
}


def create_board_image(board: chess.Board, last_move=None, board_theme='classic', piece_set='classic'):
    """
    Generate chess board image with current positions
    
    Args:
        board: chess.Board object
        last_move: Last move (chess.Move) to highlight
        board_theme: Board theme (classic, blue, green, etc.)
        piece_set: Piece set (classic, modern, fantasy)
    
    Returns:
        discord.File with board image
    """
    # Use PIL with text pieces
    square_size = 80
    board_size = 8 * square_size
    margin = 30
    img_size = board_size + 2 * margin
    
    img = Image.new('RGB', (img_size, img_size), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    
    theme = BOARD_THEMES.get(board_theme, BOARD_THEMES['classic'])
    light_color = theme['light']
    dark_color = theme['dark']
    
    for row in range(8):
        for col in range(8):
            x = margin + col * square_size
            y = margin + row * square_size
            
            is_light = (row + col) % 2 == 0
            color = light_color if is_light else dark_color
            
            if last_move:
                square = chess.square(col, 7 - row)
                if square == last_move.from_square or square == last_move.to_square:
                    color = tuple(int(c * 0.7 + 255 * 0.3) for c in color)
            
            draw.rectangle([x, y, x + square_size, y + square_size], fill=color)
            
            piece = board.piece_at(chess.square(col, 7 - row))
            if piece:
                # Use Unicode chess emoji
                symbol = piece.symbol()
                piece_char = PIECE_SYMBOLS.get(symbol, symbol)
                
                try:
                    # Segoe UI Symbol has good chess emoji
                    font = ImageFont.truetype("seguisym.ttf", 60)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", 60)
                    except:
                        font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), piece_char, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (square_size - text_width) // 2
                text_y = y + (square_size - text_height) // 2 - 5
                
                # White pieces: bright color with dark outline for visibility
                # Black pieces: dark color with bright outline for visibility
                if piece.color == chess.WHITE:
                    # Draw outline (dark stroke around white pieces)
                    outline_color = (40, 40, 40)
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                draw.text((text_x + dx, text_y + dy), piece_char, fill=outline_color, font=font)
                    # Draw piece (bright white fill)
                    draw.text((text_x, text_y), piece_char, fill=(255, 255, 255), font=font)
                else:
                    # Draw outline (light stroke around black pieces)
                    outline_color = (220, 220, 220)
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                draw.text((text_x + dx, text_y + dy), piece_char, fill=outline_color, font=font)
                    # Draw piece (black fill)
                    draw.text((text_x, text_y), piece_char, fill=(0, 0, 0), font=font)
    
    try:
        label_font = ImageFont.truetype("arial.ttf", 20)
    except:
        label_font = ImageFont.load_default()
    
    for i in range(8):
        letter = chr(ord('a') + i)
        x = margin + i * square_size + square_size // 2 - 5
        draw.text((x, img_size - margin + 5), letter, fill='white', font=label_font)
        draw.text((x, 5), letter, fill='white', font=label_font)
        
        number = str(8 - i)
        y = margin + i * square_size + square_size // 2 - 10
        draw.text((5, y), number, fill='white', font=label_font)
        draw.text((img_size - margin + 5, y), number, fill='white', font=label_font)
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(buffer, filename='chess_board.png')


def get_legal_moves_text(board: chess.Board, max_moves=20):
    """Return text with legal moves (shortened)"""
    legal_moves = list(board.legal_moves)
    
    if not legal_moves:
        return "No legal moves"
    
    moves_text = []
    for i, move in enumerate(legal_moves[:max_moves]):
        moves_text.append(move.uci())
    
    if len(legal_moves) > max_moves:
        moves_text.append(f"... and {len(legal_moves) - max_moves} more")
    
    return ", ".join(moves_text)


def parse_move(board: chess.Board, move_str: str):
    """
    Parse move from text (UCI or SAN notation)
    
    Args:
        board: Current board state
        move_str: Move string (e.g. "e2e4" or "Nf3")
    
    Returns:
        chess.Move or None if invalid
    """
    try:
        # Try UCI (e2e4)
        move = chess.Move.from_uci(move_str.lower())
        if move in board.legal_moves:
            return move
    except:
        pass
    
    try:
        # Try SAN (Nf3)
        move = board.parse_san(move_str)
        if move in board.legal_moves:
            return move
    except:
        pass
    
    return None


def get_bot_move(board: chess.Board, difficulty='easy'):
    """
    Simple AI for bot
    
    Args:
        board: Current board state
        difficulty: Difficulty level (easy, medium, hard)
    
    Returns:
        chess.Move
    """
    
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None
    
    if difficulty == 'easy':
        # Random move
        return random.choice(legal_moves)
    
    # For medium/hard: choose best move (simple heuristic)
    best_move = None
    best_score = -999999
    
    for move in legal_moves:
        board.push(move)
        score = evaluate_board(board)
        board.pop()
        
        if score > best_score:
            best_score = score
            best_move = move
    
    return best_move or random.choice(legal_moves)


def evaluate_board(board: chess.Board):
    """
    Simple position evaluation
    
    Returns:
        int: Score (positive = white advantage, negative = black advantage)
    """
    if board.is_checkmate():
        return -999999 if board.turn == chess.WHITE else 999999
    
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    
    # Piece values
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }
    
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            value = piece_values[piece.piece_type]
            if piece.color == chess.WHITE:
                score += value
            else:
                score -= value
    
    return score


def get_game_status(board: chess.Board):
    """
    Return game status
    
    Returns:
        tuple: (is_over, result_text)
    """
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return True, f"🏆 Checkmate! Winner: **{winner}**"
    
    if board.is_stalemate():
        return True, "🤝 Draw by stalemate"
    
    if board.is_insufficient_material():
        return True, "🤝 Draw by insufficient material"
    
    if board.is_fifty_moves():
        return True, "🤝 Draw by 50-move rule"
    
    if board.is_repetition(3):
        return True, "🤝 Draw by repetition"
    
    if board.is_check():
        return False, "⚠️ Check!"
    
    return False, ""


# ===============================================
# CHECKERS GAME LOGIC
# ===============================================

class __checkers_logic__:
    """Namespace for checkers logic functions"""
    pass


def create_empty_checkers_board():
    """Create initial checkers board (8x8)"""
    board = [[0 for _ in range(8)] for _ in range(8)]
    
    # Place red pieces (player 1) on rows 0-2
    for row in range(3):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = 1
    
    # Place black pieces (player 2) on rows 5-7
    for row in range(5, 8):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = 2
    
    return board


def parse_checkers_move(board, move_str, current_player):
    """Parse checkers move from string like '3b4c' or 'b3c4' (both formats supported)"""
    move_str = move_str.replace('-', '').replace(' ', '').lower()
    
    if len(move_str) < 4:
        return None
    
    try:
        # Detect format: check if first character is a digit (3b4c) or letter (b3c4)
        if move_str[0].isdigit():
            # Format: 3b4c (row+col to row+col)
            from_row = int(move_str[0]) - 1
            from_col = ord(move_str[1]) - ord('a')
            to_row = int(move_str[2]) - 1
            to_col = ord(move_str[3]) - ord('a')
        else:
            # Format: b3c4 (col+row to col+row) - chess-like notation
            from_col = ord(move_str[0]) - ord('a')
            from_row = int(move_str[1]) - 1
            to_col = ord(move_str[2]) - ord('a')
            to_row = int(move_str[3]) - 1
        
        if not (0 <= from_row < 8 and 0 <= from_col < 8 and 0 <= to_row < 8 and 0 <= to_col < 8):
            return None
        
        from_pos = (from_row, from_col)
        to_pos = (to_row, to_col)
        
        piece = board[from_row][from_col]
        
        if piece == 0 or (current_player == 1 and piece not in [1, 3]) or (current_player == 2 and piece not in [2, 4]):
            return None
        
        if board[to_row][to_col] != 0:
            return None
        
        is_king = piece in [3, 4]
        row_diff = to_row - from_row
        col_diff = to_col - from_col
        
        # Simple move
        if abs(row_diff) == 1 and abs(col_diff) == 1:
            if not is_king:
                if current_player == 1 and row_diff < 0:
                    return None
                if current_player == 2 and row_diff > 0:
                    return None
            return (from_pos, to_pos, [])
        
        # Jump move
        if abs(row_diff) == 2 and abs(col_diff) == 2:
            if not is_king:
                if current_player == 1 and row_diff < 0:
                    return None
                if current_player == 2 and row_diff > 0:
                    return None
            
            mid_row = from_row + row_diff // 2
            mid_col = from_col + col_diff // 2
            mid_piece = board[mid_row][mid_col]
            
            opponent_pieces = [2, 4] if current_player == 1 else [1, 3]
            if mid_piece in opponent_pieces:
                return (from_pos, to_pos, [(mid_row, mid_col)])
        
        return None
    except:
        return None


def execute_checkers_move(board, from_pos, to_pos, captured):
    """Execute a checkers move"""
    from_row, from_col = from_pos
    to_row, to_col = to_pos
    
    piece = board[from_row][from_col]
    board[from_row][from_col] = 0
    board[to_row][to_col] = piece
    
    for cap_row, cap_col in captured:
        board[cap_row][cap_col] = 0
    
    # King promotion
    if piece == 1 and to_row == 7:
        board[to_row][to_col] = 3
    elif piece == 2 and to_row == 0:
        board[to_row][to_col] = 4


def check_additional_jumps(board, pos, current_player):
    """Check if piece can make another jump"""
    row, col = pos
    piece = board[row][col]
    
    if piece == 0:
        return False
    
    is_king = piece in [3, 4]
    opponent_pieces = [2, 4] if current_player == 1 else [1, 3]
    
    directions = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
    
    for drow, dcol in directions:
        if not is_king:
            if current_player == 1 and drow < 0:
                continue
            if current_player == 2 and drow > 0:
                continue
        
        new_row, new_col = row + drow, col + dcol
        mid_row, mid_col = row + drow // 2, col + dcol // 2
        
        if 0 <= new_row < 8 and 0 <= new_col < 8:
            if board[new_row][new_col] == 0 and board[mid_row][mid_col] in opponent_pieces:
                return True
    
    return False


def get_all_possible_moves(board, current_player):
    """Get all possible moves for current player"""
    moves = []
    jumps = []
    
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == 0:
                continue
            
            if (current_player == 1 and piece not in [1, 3]) or (current_player == 2 and piece not in [2, 4]):
                continue
            
            is_king = piece in [3, 4]
            opponent_pieces = [2, 4] if current_player == 1 else [1, 3]
            
            simple_dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
            for drow, dcol in simple_dirs:
                if not is_king:
                    if current_player == 1 and drow < 0:
                        continue
                    if current_player == 2 and drow > 0:
                        continue
                
                new_row, new_col = row + drow, col + dcol
                if 0 <= new_row < 8 and 0 <= new_col < 8 and board[new_row][new_col] == 0:
                    moves.append(((row, col), (new_row, new_col), []))
            
            jump_dirs = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
            for drow, dcol in jump_dirs:
                if not is_king:
                    if current_player == 1 and drow < 0:
                        continue
                    if current_player == 2 and drow > 0:
                        continue
                
                new_row, new_col = row + drow, col + dcol
                mid_row, mid_col = row + drow // 2, col + dcol // 2
                
                if 0 <= new_row < 8 and 0 <= new_col < 8:
                    if board[new_row][new_col] == 0 and board[mid_row][mid_col] in opponent_pieces:
                        jumps.append(((row, col), (new_row, new_col), [(mid_row, mid_col)]))
    
    return jumps if jumps else moves


def get_checkers_game_status(board, current_player):
    """Check if game is over"""
    moves = get_all_possible_moves(board, current_player)
    
    if not moves:
        winner = "Black" if current_player == 1 else "Red"
        return True, f"🏆 Winner: **{winner}** (opponent has no moves)"
    
    opponent_player = 2 if current_player == 1 else 1
    opponent_pieces = [2, 4] if opponent_player == 2 else [1, 3]
    
    has_opponent_pieces = any(board[r][c] in opponent_pieces for r in range(8) for c in range(8))
    
    if not has_opponent_pieces:
        winner = "Red" if current_player == 1 else "Black"
        return True, f"🏆 Winner: **{winner}** (all opponent pieces captured)"
    
    return False, ""


def create_checkers_board_image(board, last_move=None):
    """Create checkers board image"""
    square_size = 80
    board_size = 8 * square_size
    margin = 30
    img_size = board_size + 2 * margin
    
    img = Image.new('RGB', (img_size, img_size), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    
    light_color = (240, 217, 181)
    dark_color = (139, 69, 19)
    
    for row in range(8):
        for col in range(8):
            x = margin + col * square_size
            y = margin + row * square_size
            
            is_dark = (row + col) % 2 == 1
            color = dark_color if is_dark else light_color
            
            if last_move:
                from_pos, to_pos = last_move
                if (row, col) == from_pos or (row, col) == to_pos:
                    color = tuple(int(c * 0.7 + 255 * 0.3) for c in color)
            
            draw.rectangle([x, y, x + square_size, y + square_size], fill=color)
            
            piece = board[row][col]
            if piece != 0:
                center_x = x + square_size // 2
                center_y = y + square_size // 2
                radius = 30
                
                if piece in [1, 3]:
                    piece_color = (220, 20, 20)
                else:
                    piece_color = (30, 30, 30)
                
                draw.ellipse(
                    [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                    fill=piece_color,
                    outline=(255, 255, 255),
                    width=3
                )
                
                if piece in [3, 4]:
                    try:
                        font = ImageFont.truetype("arial.ttf", 40)
                    except:
                        font = ImageFont.load_default()
                    
                    crown = "♔"
                    bbox = draw.textbbox((0, 0), crown, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    draw.text(
                        (center_x - text_width // 2, center_y - text_height // 2 - 5),
                        crown,
                        fill=(255, 215, 0),
                        font=font
                    )
    
    try:
        label_font = ImageFont.truetype("arial.ttf", 20)
    except:
        label_font = ImageFont.load_default()
    
    for i in range(8):
        letter = chr(ord('a') + i)
        x = margin + i * square_size + square_size // 2 - 5
        draw.text((x, img_size - margin + 5), letter, fill='white', font=label_font)
        draw.text((x, 5), letter, fill='white', font=label_font)
        
        number = str(i + 1)
        y = margin + i * square_size + square_size // 2 - 10
        draw.text((5, y), number, fill='white', font=label_font)
        draw.text((img_size - margin + 5, y), number, fill='white', font=label_font)
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(buffer, filename='checkers_board.png')


def get_checkers_bot_move(board, current_player):
    """Simple AI for checkers bot"""
    moves = get_all_possible_moves(board, current_player)
    
    if not moves:
        return None
    
    jumps = [m for m in moves if m[2]]
    if jumps:
        return random.choice(jumps)
    
    return random.choice(moves)


# Make functions accessible via __checkers_logic__ namespace
__checkers_logic__.create_empty_checkers_board = create_empty_checkers_board
__checkers_logic__.parse_checkers_move = parse_checkers_move
__checkers_logic__.execute_checkers_move = execute_checkers_move
__checkers_logic__.check_additional_jumps = check_additional_jumps
__checkers_logic__.get_all_possible_moves = get_all_possible_moves
__checkers_logic__.get_checkers_game_status = get_checkers_game_status
__checkers_logic__.create_checkers_board_image = create_checkers_board_image
__checkers_logic__.get_checkers_bot_move = get_checkers_bot_move