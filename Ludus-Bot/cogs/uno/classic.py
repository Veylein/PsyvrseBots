import discord
from discord import app_commands
from discord.ext import commands
import time
import asyncio
import random
from constants import UNO_BACK_EMOJI
from . import uno_logic
from .flip import UnoFlipHandler
from .no_mercy import UnoNoMercyHandler
from .no_mercy_plus import UnoNoMercyPlusHandler

class UnoCog(commands.Cog):
    # List of random names for bots
    def __init__(self, bot):
        self.bot = bot
        # Bot names are dynamically fetched from bot owners
        self.flip_handler = UnoFlipHandler(bot, self)
        self.no_mercy_handler = UnoNoMercyHandler(bot)
        self.no_mercy_plus_handler = UnoNoMercyPlusHandler(bot)
    
    async def get_bot_owner_names(self):
        """Fetch names of bot owners to use as bot player names"""
        names = []
        for owner_id in self.bot.owner_ids:
            try:
                user = await self.bot.fetch_user(owner_id)
                names.append(user.display_name or user.name)
            except:
                pass
        return names if names else ['BOT']
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER FUNCTIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_lang(self, game_or_lobby):
        """Get language setting from game/lobby, default to 'en'"""
        # Check both 'lang' and 'language' keys for compatibility
        return game_or_lobby.get('lang') or game_or_lobby.get('language', 'en')
    
    def t(self, key_path, game_or_lobby=None, lang=None):
        """
        Translate text using key path
        Args:
            key_path: dot-separated path to translation key
            game_or_lobby: game or lobby dict (to get lang setting) - optional
            lang: override language ('pl' or 'en') - if provided, uses this directly
        """
        if lang is None and game_or_lobby:
            lang = self.get_lang(game_or_lobby)
        if lang is None:
            lang = 'en'
        try:
            result = uno_logic.get_text(key_path, lang)
            return result
        except Exception as e:
            print(f"[UNO] Translation error for '{key_path}' (lang={lang}): {e}")
            return key_path
    
    def get_color_name(self, color, lang='en'):
        """Get translated color name"""
        return self.t(f'colors.{color}', lang=lang)
    
    def get_turn_direction_text(self, direction, lang='en'):
        """Get translated turn direction text"""
        if direction == 1:
            return self.t('game.turn_down', lang=lang)
        else:
            return self.t('game.turn_up', lang=lang)
    
    def get_uno_back_emoji(self):
        """Dynamicznie pobiera emoji tyłu karty UNO z mapowania"""
        try:
            return uno_logic.get_uno_back_emoji()
        except:
            return "🎴"  # Fallback
    
    def get_bot_display_name(self, player_id, game_or_lobby):
        """Zwraca wyświetlaną nazwę gracza (mention dla ludzi, nazwa dla botów)"""
        if not player_id.startswith('BOT_'):
            return f"<@{player_id}>"
        bot_names = game_or_lobby.get('bot_names', {})
        bot_name = bot_names.get(player_id, f"BOT {player_id.split('_')[1]}")
        # Get bot prefix from translations
        lang = self.get_lang(game_or_lobby)
        bot_prefix = self.t('bots.prefix', lang=lang)
        # Replace "BOT" with translated prefix if it's the default name
        if bot_name.startswith('BOT '):
            bot_name = f"{bot_prefix} {player_id.split('_')[1]}"
        return f"🤖 {bot_name}"
    
    def format_card_effect_notes(self, game, effects, can_continue=False, lang=None):
        """
        Format card effect notes for player feedback
        Returns: list of strings describing card effects
        """
        if lang is None:
            lang = self.get_lang(game)
        
        settings = game.get('settings', {})
        extra_notes = []
        
        # Reverse effect
        if len(game['players']) == 2 and effects.get('reverse'):
            extra_notes.append(f"♻️ **{self.t('messages.play_again_2p_reverse', lang=lang)}** {self.t('messages.reverse_2p_note', lang=lang)}")
        elif effects.get('reverse'):
            extra_notes.append(f"🔄 **{self.t('messages.direction_reversed', lang=lang)}**")
        
        # Skip effect
        if effects.get('skip_next'):
            extra_notes.append(f"⏭️ **{self.t('messages.next_player_skipped', lang=lang)}**")
        
        # Rotate hands (card 0)
        if effects.get('rotate_hands'):
            direction_text = self.t('messages.down', lang=lang) if game['direction'] == 1 else self.t('messages.up', lang=lang)
            extra_notes.append(f"🔄 **{self.t('messages.all_hands_rotated', lang=lang)} {direction_text}!**")
        
        # Draw penalty
        if effects.get('draw_penalty'):
            extra_notes.append(f"➕ **{self.t('messages.added_to_stack', lang=lang)} +{effects['draw_penalty']} {self.t('messages.to_stack', lang=lang)}**")
        
        # Can continue playing (stack colors/numbers)
        if can_continue:
            if settings.get('stack_colors', False) and settings.get('stack_numbers', False):
                extra_notes.append(f"🎯 **{self.t('messages.can_play_again_color_number', lang=lang)}** {self.t('messages.same_color_or_value', lang=lang)}")
            elif settings.get('stack_colors', False):
                extra_notes.append(f"🎨 **{self.t('messages.can_play_again_color_number', lang=lang)}** {self.t('messages.same_color', lang=lang)}")
            elif settings.get('stack_numbers', False):
                extra_notes.append(f"🔢 **{self.t('messages.can_play_again_color_number', lang=lang)}** {self.t('messages.same_value', lang=lang)}")
        
        return extra_notes
    
    def format_color_selected_message(self, color, extra_text="", lang='en'):
        """Format 'Color selected' message"""
        return f"✅ {self.t('messages.selected_color_prefix', lang=lang)}: {uno_logic.COLOR_EMOJIS[color]}{extra_text}"
    
    def format_draw_cards_message(self, count, reason="", lang='en'):
        """Format 'Drew X cards' message with optional reason"""
        if count == 1:
            return f"📥 {self.t('messages.drew_one_card', lang=lang)}"
        
        base = f"📥 {self.t('messages.drew_cards', count=count, lang=lang)}"
        if reason:
            return f"{base} {reason}"
        return base
    
    async def check_elimination(self, game_id, game, player_id, channel):
        """
        Check if player should be eliminated (≥25 cards)
        Returns True if player was eliminated, False otherwise
        """
        settings = game.get('settings', {})
        if not settings.get('elimination', False):
            return False
        
        hand = game['hands'].get(player_id, [])
        if len(hand) < 25:  # Changed from >= to < to fix elimination logic
            return False
        
        # Player has 25+ cards - Check if they can use MERCY coin as last chance!
        variant = settings.get('variant', 'classic')
        if variant == 'no_mercy_plus':
            coins = game.get('coins', {})
            player_coins = coins.get(str(player_id), {})
            
            # Check if player has MERCY coin and hasn't used it
            has_mercy = False
            for coin_name, coin_data in player_coins.items():
                if coin_name.startswith('MERCY') and not coin_data.get('used', False):
                    has_mercy = True
                    break
            
            if has_mercy:
                # Player has MERCY coin! Ask if they want to use it
                player_display = self.get_bot_display_name(player_id, game)
                
                try:
                    lang = self.get_lang(game)
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    mercy_id = mapping.get('mercy_coin.png')
                    mercy_emoji = f"<:mercy_coin:{mercy_id}>" if mercy_id else "🪙"
                    await channel.send(
                        f"💀➡️✨ **{player_display} {self.t('messages.was_on_edge_elimination', lang=lang)}!** (25+ {self.t('messages.cards', lang=lang)})\n\n"
                        f"{mercy_emoji} **{self.t('messages.mercy_auto_used', lang=lang)}!** {self.t('messages.discarded_all_drew_7', lang=lang)}",
                        delete_after=10
                    )
                except Exception:
                    pass
                
                if await self.check_elimination(game_id, game, player_id, channel):
                    return  # Bot was eliminated
                
                # Recalculate playable cards after drawing new cards
                hand = game['hands'][player_id]
                settings = game.get('settings', {})
                top_card = game['discard'][-1]
                current_color = game['current_color']
                draw_stack = game.get('draw_stack', 0)
                
                # Find MERCY coin and use it
                for coin_name, coin_data in player_coins.items():
                    if coin_name.startswith('MERCY') and not coin_data.get('used', False):
                        # Use MERCY coin!
                        uno_back = self.get_uno_back_emoji()
                        
                        # Mark coin as used
                        coin_data['used'] = True
                        
                        # Discard all cards and draw 7 new
                        old_count = len(hand)
                        hand.clear()
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        new_cards = uno_logic.draw_cards(game['deck'], 7)
                        hand.extend(new_cards)
                        
                        # Update hand_message if exists
                        hand_messages = game.get('hand_messages', {})
                        if player_id in hand_messages:
                            try:
                                old_interaction, old_msg = hand_messages[player_id]
                                
                                new_hand = game['hands'][player_id]
                                uno_back = self.get_uno_back_emoji()
                                lang = self.get_lang(game)
                                
                                mercy_embed = discord.Embed(
                                    title=f"{uno_back} 💀➡️✨ {self.t('coins.mercy_used', lang=lang).upper()}!",
                                    description=f"✨ **{self.t('coins.saved_from_elimination', lang=lang)}** ({old_count} {self.t('messages.cards', lang=lang)})\n\n"
                                                f"🗑️ {self.t('coins.discarded_all', lang=lang)}\n"
                                                f"🃏 {self.t('coins.drew_7_new', lang=lang)}\n\n"
                                                f"{self.t('messages.you_have_now', lang=lang)} **{len(new_hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}.",
                                    color=0x00ff00
                                )
                                
                                hand_view = self.create_uno_hand_view(game_id, game, player_id)
                                await old_msg.edit(embed=mercy_embed, view=hand_view)
                            except Exception:
                                pass
                        
                        return False  # Player survived with MERCY!
                
                return False  # MERCY saved the player
        
        # Player has 25+ cards and no MERCY coin - ELIMINATE!
        card_count = len(hand)  # Save count before deleting hand
        uno_back = self.get_uno_back_emoji()
        
        # Track eliminated player
        if 'eliminated_players' not in game:
            game['eliminated_players'] = []
        game['eliminated_players'].append(player_id)
        
        game['players'].remove(player_id)
        del game['hands'][player_id]
        
        # DON'T add to podium - eliminated players are tracked separately
        # They don't occupy podium positions, only shown at bottom with skull
        
        player_display = self.get_bot_display_name(player_id, game)
        
        # Check if only one player left
        if len(game['players']) == 1:
            winner = game['players'][0]
            winner_display = self.get_bot_display_name(winner, game)
            if not winner.startswith('BOT_'):
                is_multiplayer = len([p for p in game.get('original_players', game['players']) if not p.startswith('BOT_')]) > 1
                guild_id = channel.guild.id if hasattr(channel, 'guild') and channel.guild else None
                # Record game stats and award coins
                economy_cog = self.bot.get_cog("Economy")
                if economy_cog and not winner.startswith('BOT_'):
                    economy_cog.add_coins(int(winner), 30, reason="uno_win")
                    # Record game statistics
                    game_stats_cog = self.bot.get_cog("GameStats")
                    if game_stats_cog:
                        duration = int(time.time() - game.get('start_time', time.time()))
                        guild_id = game.get('guild_id')
                        game_stats_cog.record_game(int(winner), "uno", won=True, coins_earned=30, playtime_seconds=duration, category="strategy_games", guild_id=guild_id)
            
            lang = self.get_lang(game)
            embed = discord.Embed(
                title=f"{uno_back} {self.t('messages.game_over', lang=lang)}",
                description=f"🏆 {self.t('messages.winner', lang=lang)}: {winner_display}\n\n💀 {player_display} {self.t('messages.was_eliminated', lang=lang)} (≥25 {self.t('messages.cards', lang=lang)})",
                color=discord.Color.gold()
            )
            try:
                if game.get('messageId'):
                    msg = channel.get_partial_message(game['messageId'])
                    await msg.edit(embed=embed, view=None)
            except Exception:
                pass
            self.bot.active_games.pop(game_id, None)
            return True
        
        # Continue game
        try:
            lang = self.get_lang(game)
            await channel.send(
                f"💀 **{player_display} {self.t('messages.eliminated', lang=lang)}!**\n\n{self.t('messages.reason', lang=lang)}: {self.t('messages.reached', lang=lang)} {card_count} {self.t('messages.cards', lang=lang)} ({self.t('messages.limit', lang=lang)}: 25)\n\n{self.t('messages.remaining', lang=lang)} {len(game['players'])} {self.t('messages.players', lang=lang)}.",
                delete_after=10
            )
        except Exception:
            pass
        
        # Adjust current_turn if needed
        if game['current_turn'] >= len(game['players']):
            game['current_turn'] = 0
        
        # Refresh game board after elimination
        try:
            current_player = game['players'][game['current_turn']]
            embed_main, file_main = self.create_uno_game_embed(game)
            view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
            
            if game.get('messageId'):
                msg = channel.get_partial_message(game['messageId'])
                files_main = [file_main] if file_main else []
                await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
            
            # Trigger bot turn if current player is bot
            if current_player.startswith('BOT_'):
                await asyncio.sleep(1.5)
                await self.play_bot_uno_turn(channel, game_id, game)
            else:
                await self.auto_refresh_player_hand(game_id, game, current_player, channel)
                
        except Exception:
            pass
        
        return True
    
    async def handle_player_win(self, game_id, game, player_id, interaction, channel, extra_msg=""):
        """
        Handle player winning - either first_win or last_standing mode
        Returns True if game ended, False if game continues
        """
        uno_back = self.get_uno_back_emoji()
        lang = self.get_lang(game)
        first_win = game.get('settings', {}).get('first_win', True)
        
        if first_win:
            # First win mode - game ends immediately
            is_multiplayer = len([p for p in game['players'] if not p.startswith('BOT_')]) > 1
            guild_id = channel.guild.id if hasattr(channel, 'guild') and channel.guild else None
            # Record game stats and award coins
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog and not player_id.startswith('BOT_'):
                economy_cog.add_coins(int(player_id), 30, reason="uno_win")
                # Record game statistics
                game_stats_cog = self.bot.get_cog("GameStats")
                if game_stats_cog:
                    duration = int(time.time() - game.get('start_time', time.time()))
                    guild_id = game.get('guild_id')
                    game_stats_cog.record_game(int(player_id), "uno", won=True, coins_earned=30, playtime_seconds=duration, category="strategy_games", guild_id=guild_id)
            #await check_achievements(player_id, channel)
            
            # Create win embed
            winner_display = f"<@{player_id}>"
            description = f"🏆 {self.t('messages.winner', lang=lang)}: {winner_display}"
            if extra_msg:
                description += f"\n\n{extra_msg}"
            
            embed = discord.Embed(
                title=f"{uno_back} {self.t('messages.game_over', lang=lang)}",
                description=description,
                color=discord.Color.gold()
            )
            
            # Update main game board
            try:
                if game.get('messageId'):
                    msg = channel.get_partial_message(game['messageId'])
                    await msg.edit(embed=embed, view=None, attachments=[])
            except Exception:
                pass
            
            # Clear all hand messages to prevent callbacks
            game['hand_messages'] = {}
            
            # Notify player
            if interaction:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"🎉 **{self.t('messages.you_won', lang=lang)}** +30 {self.t('messages.coins_reward', lang=lang)}!", ephemeral=True)
                    else:
                        await interaction.followup.send(f"🎉 **{self.t('messages.you_won', lang=lang)}** +30 {self.t('messages.coins_reward', lang=lang)}!", ephemeral=True)
                except:
                    pass
            
            self.bot.active_games.pop(game_id, None)
            return True
        
        else:
            # Last player standing mode - eliminate this player
            game['players'].remove(player_id)
            del game['hands'][player_id]
            
            # Track podium positions
            if 'podium' not in game:
                game['podium'] = []
            game['podium'].append(player_id)
            
            # Check if only one player left
            if len(game['players']) == 1:
                loser = game['players'][0]
                winner = game['podium'][0]
                
                # Award winner
                if not winner.startswith('BOT_'):
                    is_multiplayer = len(game.get('podium', [])) > 1
                    guild_id = channel.guild.id if hasattr(channel, 'guild') and channel.guild else None
                    # Record game stats and award coins
                    economy_cog = self.bot.get_cog("Economy")
                    if economy_cog and not winner.startswith('BOT_'):
                        economy_cog.add_coins(int(winner), 30, reason="uno_win")
                        # Record game statistics
                        game_stats_cog = self.bot.get_cog("GameStats")
                        if game_stats_cog:
                            duration = int(time.time() - game.get('start_time', time.time()))
                            guild_id = game.get('guild_id')
                            game_stats_cog.record_game(int(winner), "uno", won=True, coins_earned=30, playtime_seconds=duration, category="strategy_games", guild_id=guild_id)
                    #await check_achievements(winner, channel)
                
                # Create podium display
                podium_medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
                podium_text = ""
                
                for idx, pid in enumerate(game['podium']):
                    medal = podium_medals[idx] if idx < 10 else f"{idx+1}."
                    player_display = self.get_bot_display_name(pid, game)
                    podium_text += f"{medal} {player_display}\n"
                
                # Add loser
                loser_place = len(game['podium']) + 1
                loser_display = self.get_bot_display_name(loser, game)
                podium_text += f"\n💀 **{loser_place}.** {loser_display} *({self.t('messages.stayed_with_cards_lost', lang=lang)})*\n"
                
                # Add eliminated players
                eliminated = game.get('eliminated_players', [])
                if eliminated:
                    podium_text += "\n**--- WYELIMINOWANI (≥25 kart) ---**\n"
                    for elim_player in reversed(eliminated):
                        elim_display = self.get_bot_display_name(elim_player, game)
                        podium_text += f"💀 {elim_display}\n"
                
                embed = discord.Embed(
                    title=f"{uno_back} {self.t('messages.game_over', lang=lang)}",
                    description=f"🏆 **PODIUM:**\n\n{podium_text}\n🎉 Gratulacje zwycięzcom!",
                    color=discord.Color.gold()
                )
                
                try:
                    if game.get('messageId'):
                        msg = channel.get_partial_message(game['messageId'])
                        await msg.edit(embed=embed, view=None)
                except Exception:
                    pass
                
                # Clear all hand messages to prevent callbacks
                game['hand_messages'] = {}
                
                self.bot.active_games.pop(game_id, None)
                return True
            
            # Game continues - notify player
            position = len(game['podium'])
            player_display = self.get_bot_display_name(player_id, game)
            
            if interaction:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"✅ Ukończyłeś grę! Miejsce: #{position}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"✅ Ukończyłeś grę! Miejsce: #{position}", ephemeral=True)
                except:
                    pass
            
            # Adjust turn if needed
            if game['current_turn'] >= len(game['players']):
                game['current_turn'] = 0
            
            # Update game board
            current_player = game['players'][game['current_turn']]
            embed_main, file_main = self.create_uno_game_embed(game)
            view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
            
            try:
                if game.get('messageId'):
                    msg = channel.get_partial_message(game['messageId'])
                    files_main = [file_main] if file_main else []
                    await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
            except Exception:
                pass
            
            # Trigger bot or refresh hand
            if current_player.startswith('BOT_'):
                await self.play_bot_uno_turn(channel, game_id, game)
            else:
                await self.auto_refresh_player_hand(game_id, game, current_player, channel)
            
            return False
    
    def format_uno_lobby_settings(self, settings, lang='en'):
        """Formatuje ustawienia UNO dla lobby (pokazuje wszystkie)"""
        s = settings
        lines = []
        uno_back = self.get_uno_back_emoji()
        
        # Tryb gry
        variant = s.get('variant', 'classic')
        variant_names = {
            'classic': self.t(f'variants.classic', lang=lang),
            'flip': self.t(f'variants.flip', lang=lang),
            'no_mercy': self.t(f'variants.no_mercy', lang=lang),
            'no_mercy_plus': self.t(f'variants.no_mercy_plus', lang=lang)
        }
        variant_name = variant_names.get(variant, self.t('variants.classic', lang=lang))
        lines.append(f"🎮 {self.t('settings.mode', lang=lang)}: **{variant_name}**")
        
        lines.append(f"{uno_back} {self.t('settings.starting_cards', lang=lang)}: **{s.get('starting_cards', 7)}**")
        if variant == 'flip':
            lines.append(f"➕ {self.t('settings.stack_draw', lang=lang)}: {'✅' if s.get('stack_flip_draw', True) else '❌'}")
        elif variant in ['no_mercy', 'no_mercy_plus']:
            lines.append(f"➕ {self.t('settings.stack_no_mercy', lang=lang)}: ✅ {self.t('settings.locked', lang=lang)}")
            lines.append(f"🔄 {self.t('settings.stack_combined', lang=lang)}: ✅ {self.t('settings.locked', lang=lang)}")
            if variant == 'no_mercy_plus':
                lines.append(f"🪙 {self.t('settings.coins', lang=lang)}: ✅ (1/{self.t('lobby.players', lang=lang).lower()})")
        else:
            lines.append(f"➕ {self.t('settings.stack_plus_two', lang=lang)}: {'✅' if s.get('stack_plus_two', True) else '❌'}")
            lines.append(f"⚡ {self.t('settings.stack_plus_four', lang=lang)}: {'✅' if s.get('stack_plus_four', False) else '❌'}")
        
        if variant != 'no_mercy':
            lines.append(f"🔄 {self.t('settings.stack_combined', lang=lang)}: {'✅' if s.get('stack_combined', False) else '❌'}")
        
        lines.append(f"🎨 {self.t('settings.stack_colors', lang=lang)}: {'✅' if s.get('stack_colors', False) else '❌'}")
        lines.append(f"🔢 {self.t('settings.stack_numbers', lang=lang)}: {'✅' if s.get('stack_numbers', False) else '❌'}")
        lines.append(f"🤖 {self.t('settings.auto_draw', lang=lang)}: {'✅' if s.get('auto_draw', False) else '❌'}")
        lines.append(f"📥 {self.t('settings.draw_until_play', lang=lang)}: {'✅' if s.get('draw_until_play', False) else '❌'}")
        lines.append(f"⏩ {self.t('settings.skip_after_draw', lang=lang)}: {'✅' if s.get('skip_after_draw', True) else '❌'}")
        lines.append(f"⚠️ {self.t('settings.must_play', lang=lang)}: {'✅' if s.get('must_play', False) else '❌'}")
        
        if variant == 'classic':
            lines.append(f"🔄 {self.t('settings.seven_zero', lang=lang)}: {'✅' if s.get('seven_zero', False) else '❌'}")
        elif variant in ['no_mercy', 'no_mercy_plus']:
            lines.append(f"🔄 {self.t('settings.seven_zero', lang=lang)}: ✅ {self.t('settings.locked', lang=lang)}")
        
        lines.append(f"🎯 {self.t('settings.jump_in', lang=lang)}: {'✅' if s.get('jump_in', False) else '❌'}")
        lines.append(f"📢 {self.t('settings.uno_callout', lang=lang)}: {'✅' if s.get('uno_callout', False) else '❌'}")
        
        # Elimination rule
        if variant in ['no_mercy', 'no_mercy_plus']:
            lines.append(f"💀 {self.t('settings.elimination', lang=lang)}: ✅ {self.t('settings.locked', lang=lang)}")
        else:
            lines.append(f"💀 {self.t('settings.elimination', lang=lang)}: {'✅' if s.get('elimination', False) else '❌'}")
        
        first_win_text = self.t('settings.first_win', lang=lang) if s.get('first_win', True) else self.t('settings.last_player', lang=lang)
        lines.append(f"🏆 {self.t('settings.end_condition', lang=lang)}: {first_win_text}")
        return "\n".join(lines)

    def create_uno_lobby_embed_and_view(self, lobby, lobby_id, host):
        """Tworzy embed i view dla lobby UNO - bez duplikacji kodu"""
        uno_back = self.get_uno_back_emoji()
        lang = self.get_lang(lobby)
        bot_names = lobby.get('bot_names', {})
        player_list = "\n".join([
            f"<@{p}>" if not p.startswith('BOT_') else f"🤖 {bot_names.get(p, 'BOT')}"
            for p in lobby['players']
        ])
        
        embed = discord.Embed(
            title=f"{uno_back} {self.t('lobby.title', lang=lang)}",
            description=f"{self.t('lobby.host', lang=lang)}: <@{lobby['hostId']}>\n{self.t('lobby.players', lang=lang)}: {len(lobby['players'])}/{lobby['maxPlayers']}\n\n{self.t('lobby.waiting', lang=lang)}",
            color=discord.Color.red()
        )
        embed.add_field(name=self.t('lobby.player_list_title', lang=lang), value=player_list, inline=False)
        
        # Initialize settings if missing (for old lobbies)
        if 'settings' not in lobby:
            lobby['settings'] = {
                'variant': 'classic',  # classic, flip, or no_mercy
                'starting_cards': 7, 'stack_plus_two': True, 'stack_plus_four': False, 'stack_combined': False,
                'stack_colors': False, 'stack_numbers': False,
                'auto_draw': False, 'draw_until_play': False, 'skip_after_draw': True,
                'must_play': False, 'uno_callout': True, 'penalty_cards': 2,
                'penalty_false_uno': 2, 'seven_zero': False, 'jump_in': False, 'first_win': True,
                'elimination': False  # New rule: eliminate players with >=25 cards
            }
        
        # Ensure variant exists (backward compatibility)
        if 'variant' not in lobby['settings']:
            lobby['settings']['variant'] = 'classic'
        
        # Ensure elimination exists (backward compatibility)
        if 'elimination' not in lobby['settings']:
            lobby['settings']['elimination'] = False
        
        # Ensure lang exists (default to 'en')
        if 'lang' not in lobby:
            lobby['lang'] = 'en'
        
        # Force specific rules for No Mercy variant
        variant = lobby['settings'].get('variant', 'classic')
        if variant in ['no_mercy', 'no_mercy_plus']:
            # No Mercy/No Mercy+ have forced rules that cannot be changed
            lobby['settings']['stack_no_mercy_draw'] = True  # Always stack +4/+6/+10
            lobby['settings']['stack_combined'] = True  # Always stack all draw cards together
            lobby['settings']['seven_zero'] = True  # Always enabled
            lobby['settings']['elimination'] = True  # Always eliminate at 25+ cards
        
        embed.add_field(name=self.t('lobby.settings_title', lang=lang), value=self.format_uno_lobby_settings(lobby['settings'], lang), inline=False)
        
        view = discord.ui.View(timeout=None)
        # Row 0: Bot management
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_bot_add', lang=lang),
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_lobby_bot_add_{lobby_id}",
            disabled=len(lobby['players']) >= lobby['maxPlayers'],
            row=0
        ))
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_bot_remove', lang=lang),
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_lobby_bot_remove_{lobby_id}",
            row=0
        ))
        # Row 1: Join/Leave
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_join', lang=lang),
            style=discord.ButtonStyle.success,
            custom_id=f"uno_lobby_join_{lobby_id}",
            disabled=len(lobby['players']) >= lobby['maxPlayers'],
            row=1
        ))
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_leave', lang=lang),
            style=discord.ButtonStyle.danger,
            custom_id=f"uno_lobby_leave_{lobby_id}",
            row=1
        ))
        # Row 2: Settings/Start/Language
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_settings', lang=lang),
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_lobby_settings_{lobby_id}",
            row=2
        ))
        view.add_item(discord.ui.Button(
            label="🌐 PL" if lang == 'pl' else "🌐 EN",
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_lobby_lang_{lobby_id}",
            row=2
        ))
        view.add_item(discord.ui.Button(
            label=self.t('lobby.button_start', lang=lang),
            style=discord.ButtonStyle.success,
            custom_id=f"uno_lobby_start_{lobby_id}",
            disabled=len(lobby['players']) < lobby['minPlayers'],
            row=2
        ))
        
        return embed, view

    def create_uno_settings_view_and_description(self, lobby_id, settings, lang='en'):
        """Tworzy view z przyciskami ustawień UNO i description - bez duplikacji kodu"""
        uno_back = self.get_uno_back_emoji()
        s = settings
        
        settings_view = discord.ui.View(timeout=None)
        
        # Row 0: Wariant gry + Karty początkowe
        variant = s.get('variant', 'classic')
        variant_select = discord.ui.Select(
            placeholder=f"{self.t('settings.variant_placeholder', lang=lang)}: {self.t(f'variants.{variant}', lang=lang)}",
            options=[
                discord.SelectOption(label=self.t('variants.classic', lang=lang), value="classic", description=self.t('variants.classic_desc', lang=lang), default=variant=='classic'),
                discord.SelectOption(label=self.t('variants.flip', lang=lang), value="flip", description=self.t('variants.flip_desc', lang=lang), default=variant=='flip'),
                discord.SelectOption(label=self.t('variants.no_mercy', lang=lang), value="no_mercy", description=self.t('variants.no_mercy_desc', lang=lang), default=variant=='no_mercy'),
                discord.SelectOption(label=self.t('variants.no_mercy_plus', lang=lang), value="no_mercy_plus", description=self.t('variants.no_mercy_plus_desc', lang=lang), default=variant=='no_mercy_plus')
            ],
            custom_id=f"uno_setting_variant_{lobby_id}",
            row=0
        )
        settings_view.add_item(variant_select)
        
        # Row 1: Karty początkowe - jeden przycisk cykliczny
        current_cards = s.get('starting_cards', 7)
        settings_view.add_item(discord.ui.Button(
            label=f"🃏 {self.t('settings.cards_start_label', lang=lang)}: {current_cards}",
            style=discord.ButtonStyle.success,
            custom_id=f"uno_setting_cards_cycle_{lobby_id}",
            row=1
        ))
        
        # Row 2: Sumowanie
        if variant in ['no_mercy', 'no_mercy_plus']:
            # No Mercy/No Mercy+ - locked stacking rules
            settings_view.add_item(discord.ui.Button(
                label=f"✅ {self.t('settings.stack_no_mercy', lang=lang)} {self.t('settings.locked', lang=lang)}",
                style=discord.ButtonStyle.success,
                custom_id=f"uno_setting_stack_no_mercy_{lobby_id}", row=2,
                disabled=True
            ))
        elif variant == 'flip':
            settings_view.add_item(discord.ui.Button(
                label=f"{'✅' if s.get('stack_flip_draw', True) else '❌'} {self.t('settings.stack_draw', lang=lang)}",
                style=discord.ButtonStyle.success if s.get('stack_flip_draw', True) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_stack_flip_draw_{lobby_id}", row=2
            ))
        else:
            settings_view.add_item(discord.ui.Button(
                label=f"{'✅' if s.get('stack_plus_two', True) else '❌'} {self.t('settings.stack_plus_two', lang=lang)}",
                style=discord.ButtonStyle.success if s.get('stack_plus_two', True) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_stack_plus_two_{lobby_id}", row=2
            ))
            settings_view.add_item(discord.ui.Button(
                label=f"{'✅' if s.get('stack_plus_four', False) else '❌'} {self.t('settings.stack_plus_four', lang=lang)}",
                style=discord.ButtonStyle.success if s.get('stack_plus_four', False) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_stack_plus_four_{lobby_id}", row=2
            ))
        
        # Combined stacking - locked for No Mercy
        if variant in ['no_mercy', 'no_mercy_plus']:
            settings_view.add_item(discord.ui.Button(
                label=f"✅ {self.t('settings.together', lang=lang)} {self.t('settings.locked', lang=lang)}",
                style=discord.ButtonStyle.success,
                custom_id=f"uno_setting_stack_combined_{lobby_id}", row=2,
                disabled=True
            ))
        else:
            settings_view.add_item(discord.ui.Button(
                label=f"{'✅' if s.get('stack_combined', False) else '❌'} {self.t('settings.together', lang=lang)}",
                style=discord.ButtonStyle.success if s.get('stack_combined', False) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_stack_combined_{lobby_id}", row=2
            ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('stack_colors', False) else '❌'} {self.t('settings.stack_colors', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('stack_colors', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_stack_colors_{lobby_id}", row=2
        ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('stack_numbers', False) else '❌'} {self.t('settings.stack_numbers', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('stack_numbers', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_stack_numbers_{lobby_id}", row=2
        ))
        
        # Row 3: Dobieranie
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('auto_draw', False) else '❌'} {self.t('settings.auto_draw', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('auto_draw', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_auto_draw_{lobby_id}", row=3
        ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('draw_until_play', False) else '❌'} {self.t('settings.draw_until_play', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('draw_until_play', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_draw_until_play_{lobby_id}", row=3
        ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('skip_after_draw', True) else '❌'} {self.t('settings.skip_after_draw', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('skip_after_draw', True) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_skip_after_draw_{lobby_id}", row=3
        ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('must_play', False) else '❌'} {self.t('settings.must_play', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('must_play', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_must_play_{lobby_id}", row=3
        ))
        
        # Row 4: Specjalne
        # 7-0 Rule only available in Classic mode (No Mercy has it locked on)
        if variant == 'classic':
            settings_view.add_item(discord.ui.Button(
                label=f"{'✅' if s.get('seven_zero', False) else '❌'} {self.t('settings.seven_zero', lang=lang)}",
                style=discord.ButtonStyle.success if s.get('seven_zero', False) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_seven_zero_{lobby_id}", row=4
            ))
        elif variant in ['no_mercy', 'no_mercy_plus']:
            # Show locked 7-0 Rule for No Mercy/No Mercy+ (cannot be changed)
            settings_view.add_item(discord.ui.Button(
                label="✅ 7-0 Rule 🔒",
                style=discord.ButtonStyle.success,
                custom_id=f"uno_setting_seven_zero_{lobby_id}", row=4,
                disabled=True
            ))
        
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('jump_in', False) else '❌'} {self.t('settings.jump_in', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('jump_in', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_jump_in_{lobby_id}", row=4
        ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('uno_callout', False) else '❌'} {self.t('settings.uno_callout', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('uno_callout', False) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_uno_callout_{lobby_id}", row=4
        ))
        
        # Elimination - available in Classic/Flip, locked on in No Mercy
        if variant in ['no_mercy', 'no_mercy_plus']:
            settings_view.add_item(discord.ui.Button(
                label=f"💀 {self.t('settings.elimination', lang=lang)} 🔒",
                style=discord.ButtonStyle.danger,
                custom_id=f"uno_setting_elimination_{lobby_id}", row=4,
                disabled=True
            ))
        else:
            settings_view.add_item(discord.ui.Button(
                label=f"{'💀' if s.get('elimination', False) else '❌'} {self.t('settings.elimination', lang=lang)}",
                style=discord.ButtonStyle.danger if s.get('elimination', False) else discord.ButtonStyle.secondary,
                custom_id=f"uno_setting_elimination_{lobby_id}", row=4
            ))
        settings_view.add_item(discord.ui.Button(
            label=f"{'✅' if s.get('first_win', True) else '❌'} {self.t('settings.one_winner', lang=lang)}",
            style=discord.ButtonStyle.success if s.get('first_win', True) else discord.ButtonStyle.secondary,
            custom_id=f"uno_setting_first_win_{lobby_id}", row=4
        ))
        
        # Description text
        variant_names = {
            'classic': self.t('variants.classic', lang=lang),
            'flip': self.t('variants.flip', lang=lang),
            'no_mercy': self.t('variants.no_mercy', lang=lang)
        }
        variant_name = variant_names.get(variant, self.t('variants.classic', lang=lang))
        settings_desc = f"**{self.t('settings_desc.mode_label', lang=lang)}** {variant_name}\n\n"
        settings_desc += f"**{uno_back} {self.t('settings_desc.cards_start_label', lang=lang)}** {self.t('settings_desc.cards_start_click', lang=lang)}\n\n"
        settings_desc += f"**{self.t('settings_desc.stacking_label', lang=lang)}**\n"
        if variant == 'no_mercy':
            settings_desc += f"• {self.t('settings_desc.no_mercy_stack_locked', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.no_mercy_combined_locked', lang=lang)}\n\n"
        elif variant == 'flip':
            settings_desc += f"• {self.t('settings_desc.flip_stack_11_55', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.flip_combined', lang=lang)}\n\n"
        else:
            settings_desc += f"• {self.t('settings_desc.classic_stack_2', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.classic_stack_4', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.classic_combined', lang=lang)}\n\n"
        settings_desc += f"**{self.t('settings_desc.layering_label', lang=lang)}**\n"
        settings_desc += f"• {self.t('settings_desc.colors_desc', lang=lang)}\n"
        settings_desc += f"• {self.t('settings_desc.numbers_desc', lang=lang)}\n\n"
        settings_desc += f"**{self.t('settings_desc.drawing_label', lang=lang)}** {self.t('settings_desc.drawing_note', lang=lang)}:\n"
        settings_desc += f"• {self.t('settings_desc.auto_desc', lang=lang)}\n"
        settings_desc += f"• {self.t('settings_desc.draw_until_desc', lang=lang)}\n"
        settings_desc += f"• {self.t('settings_desc.skip_after_desc', lang=lang)}\n"
        settings_desc += f"• {self.t('settings_desc.must_play_desc', lang=lang)}\n\n"
        settings_desc += f"**{self.t('settings_desc.special_label', lang=lang)}**\n"
        if variant == 'no_mercy':
            settings_desc += f"• {self.t('settings_desc.no_mercy_seven_zero_locked', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.no_mercy_elimination_locked', lang=lang)}\n"
        elif variant == 'classic':
            settings_desc += f"• {self.t('settings_desc.classic_seven_zero', lang=lang)}\n"
        
        if variant != 'no_mercy':
            settings_desc += f"• {self.t('settings_desc.jump_in_desc', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.uno_callout_desc', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.elimination_desc', lang=lang)}\n"
        else:
            settings_desc += f"• {self.t('settings_desc.jump_in_desc', lang=lang)}\n"
            settings_desc += f"• {self.t('settings_desc.uno_callout_desc', lang=lang)}\n"
        
        settings_desc += f"• {self.t('settings_desc.first_win_desc', lang=lang)}"
        
        return settings_view, settings_desc
    
    def create_uno_game_embed(self, game_state):
        """Create embed for UNO game state with card image - returns (embed, file)"""
        uno_back = self.get_uno_back_emoji()
        lang = self.get_lang(game_state)
        
        variant = game_state.get('settings', {}).get('variant', 'classic')
        top_card = game_state['discard'][-1]
        current_player = game_state['players'][game_state['current_turn']]
        cp_display = self.get_bot_display_name(current_player, game_state)
        
        # Get card color for embed
        card_color = game_state['current_color']
        color_map = {
            'red': 0xE74C3C,
            'blue': 0x3498DB,
            'green': 0x2ECC71,
            'yellow': 0xF1C40F,
            'teal': 0x1ABC9C,
            'purple': 0x9B59B6,
            'pink': 0xE91E63,
            'orange': 0xFF5722,
            'wild': 0x95A5A6
        }
        
        # Create professional description with card name
        top_card_display = uno_logic.card_to_string(top_card, compact=True)
        
        # Turn direction indicator
        direction = game_state.get('direction', 1)
        direction_arrow = "↻" if direction == 1 else "↺"
        direction_text = self.get_turn_direction_text(direction, lang)
        
        # Color display maps
        color_emoji_map = {
            'red': '🔴',
            'blue': '🔵',
            'green': '🟢',
            'yellow': '🟡',
            'teal': '🔵',
            'purple': '🟣',
            'pink': '🩷',
            'orange': '🟠',
            'wild': '🌈'
        }
        
        desc = f"**{self.t('game.now_playing', lang=lang)}: {cp_display}!**\n"
        desc += f"{direction_arrow} **{self.t('game.turn_order', lang=lang)}:** {direction_text}\n"
        
        # Show selected wild color if wild card is on top
        if top_card['color'] == 'wild' and card_color in color_emoji_map:
            color_emoji = color_emoji_map.get(card_color, '⚪')
            color_name = self.get_color_name(card_color, lang)
            desc += f"🎨 **{self.t('game.color', lang=lang)}:** {color_emoji} **{color_name}**\n"
        
        desc += "\n"
        
        # Show draw stack if active
        draw_stack = game_state.get('draw_stack', 0)
        if draw_stack > 0:
            color_emoji = color_emoji_map.get(card_color, '⚪')
            color_name = self.get_color_name(card_color, lang)
            desc += f"🔥 **{self.t('game.stacking', lang=lang)}: +{draw_stack} {self.t('game.cards', lang=lang)}** {self.t('game.color', lang=lang).lower()} {color_emoji} **{color_name}**\n"
        
        embed = discord.Embed(
            title=f"{uno_back} {self.t('game.title', lang=lang)}",
            description=desc,
            color=color_map.get(card_color, 0xE74C3C)
        )
        # Get card image file - auto-detects variant from card properties
        card_file = uno_logic.card_to_image(top_card)
        
        if card_file:
            embed.set_image(url=f"attachment://{card_file.filename}")
        
        # Show players in a table-like format
        player_info = ""
        eliminated = game_state.get('eliminated_players', [])
        coins = game_state.get('coins', {})
        variant = game_state.get('settings', {}).get('variant', 'classic')
        
        # Show active players
        for p in game_state['players']:
            is_turn = p == current_player
            player_name = self.get_bot_display_name(p, game_state)
            card_count = len(game_state['hands'][p])
            turn_indicator = "📍" if is_turn else ""
            
            # Add coin indicator for No Mercy+
            coin_indicator = ""
            if variant == 'no_mercy_plus' and p in coins:
                coin_data = coins[p]
                if coin_data.get('selected', False) and not coin_data.get('used', False):
                    # Gracz wybrał typ monety i jeszcze jej nie użył
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    if coin_data.get('type') == 'mercy':
                        emoji_id = mapping.get('mercy_coin.png')
                        if emoji_id:
                            coin_indicator = f" <:mercy_coin:{emoji_id}>"
                    elif coin_data.get('type') == 'no_mercy':
                        emoji_id = mapping.get('nomercy_coin.png')
                        if emoji_id:
                            coin_indicator = f" <:nomercy_coin:{emoji_id}>"
                elif coin_data.get('used', False):
                    # Moneta użyta - pokazujemy szarą/zużytą ikonę
                    coin_indicator = " 🪙❌"
            
            player_info += f"{player_name} | **{card_count} {self.t('game.cards', lang=lang)}** {turn_indicator}{coin_indicator}\n"
        
        # Show eliminated players with skull
        for p in eliminated:
            player_name = self.get_bot_display_name(p, game_state)
            player_info += f"{player_name} | 💀 **{self.t('game.eliminated', lang=lang)}**\n"
        
        embed.add_field(name=f"👥 {self.t('game.players_title', lang=lang)}", value=player_info, inline=False)
        
        # Deck info with UNO logo emoji
        deck_remaining = len(game_state['deck'])
        deck_total = 108
        discarded = len(game_state['discard'])
        
        # Calculate game duration
        start_time = game_state.get('start_time', time.time())
        duration_seconds = int(time.time() - start_time)
        if duration_seconds < 60:
            duration_text = f"{duration_seconds}s"
        else:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_text = f"{minutes}:{seconds:02d}"
        
        deck_info = f"{uno_back} **{self.t('game.deck', lang=lang)}:** {deck_remaining}/{deck_total}\n📤 **{self.t('game.discarded', lang=lang)}:** {discarded}\n🕒 **{self.t('game.game_time', lang=lang)}:** {duration_text}\n🃏 **{self.t('game.card', lang=lang)}:** {top_card_display}"
        
        embed.add_field(name=f"📊 {self.t('game.stats_title', lang=lang)}", value=deck_info, inline=False)
        
        return embed, card_file

    def create_uno_legacy_game_view(self, game_id, game_state, player_id):
        """Legacy view kept for compatibility - shows buttons for ALL players"""
        uno_back = self.get_uno_back_emoji()
        lang = self.get_lang(game_state)
        view = discord.ui.View(timeout=None)
        
        variant = game_state.get('settings', {}).get('variant', 'classic')
        
        # Przyciski dostępne dla WSZYSTKICH graczy (nie tylko current player)
        uno_emoji = uno_logic.get_uno_back_partial_emoji()
        
        # Calculate total cards across all players for display (in case player_id not in game)
        total_cards = sum(len(hand) for hand in game_state.get('hands', {}).values())
        player_card_count = len(game_state.get('hands', {}).get(str(player_id), [])) if player_id else total_cards
        
        view.add_item(discord.ui.Button(
            label=f"{self.t('hand.title', lang=lang)} ({player_card_count})",
            emoji=uno_emoji,
            style=discord.ButtonStyle.primary,
            custom_id=f"uno_show_hand_{game_id}",
            row=0
        ))
        
        # Flip mode: Add button to see opponents' cards
        if variant == 'flip':
            view.add_item(discord.ui.Button(
                label=self.t('hand.button_opponents', lang=lang),
                style=discord.ButtonStyle.secondary,
                custom_id=f"uno_show_opponents_{game_id}",
                row=0
            ))
        
        # Rules button
        view.add_item(discord.ui.Button(
            label=self.t('hand.button_rules', lang=lang),
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_rules_{game_id}",
            row=0
        ))
        
        # Leave button
        view.add_item(discord.ui.Button(
            label=self.t('hand.button_leave', lang=lang),
            style=discord.ButtonStyle.secondary,
            custom_id=f"uno_leave_{game_id}",
            row=0
        ))
        
        return view

    def create_uno_hand_view(self, game_id, game_state, player_id, page=0):
        """Create ephemeral view with card emoji buttons (UNO online style)"""
        view = discord.ui.View(timeout=None)
        
        variant = game_state.get('settings', {}).get('variant', 'classic')
        hand = game_state['hands'][player_id]
        top_card = game_state['discard'][-1]
        current_color = game_state['current_color']
        draw_stack = game_state.get('draw_stack', 0)
        settings = game_state.get('settings', {})
        playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
        
        # Check if it's this player's turn
        current_player = game_state['players'][game_state['current_turn']]
        is_current_turn = (player_id == current_player)
        
        # No Mercy+: If player hasn't selected coin type, show selection buttons instead
        if variant == 'no_mercy_plus':
            coins = game_state.get('coins', {})
            player_id_str = str(player_id)
            if player_id_str in coins and not coins[player_id_str].get('selected', False):
                # Show coin selection buttons
                mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                
                mercy_id = mapping.get('mercy_coin.png')
                nomercy_id = mapping.get('nomercy_coin.png')
                
                mercy_emoji = discord.PartialEmoji(name='mercy_coin', id=mercy_id) if mercy_id else None
                nomercy_emoji = discord.PartialEmoji(name='nomercy_coin', id=nomercy_id) if nomercy_id else None
                
                lang = self.get_lang(game_state)
                view.add_item(discord.ui.Button(
                    label=self.t('coins.mercy', lang=lang),
                    emoji=mercy_emoji,
                    style=discord.ButtonStyle.primary,
                    custom_id=f"uno_select_coin_{game_id}:mercy",
                    row=0
                ))
                view.add_item(discord.ui.Button(
                    label=self.t('coins.no_mercy', lang=lang),
                    emoji=nomercy_emoji,
                    style=discord.ButtonStyle.danger,
                    custom_id=f"uno_select_coin_{game_id}:no_mercy",
                    row=0
                ))
                return view  # Return early with only coin selection buttons
        
        # Pagination: max 15 cards per page (3 rows x 5 buttons), rows 3-4 for action buttons
        # Discord limit: 25 components per view. With up to 7 action buttons, we need space.
        CARDS_PER_PAGE = 15
        total_pages = (len(hand) + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
        page = max(0, min(page, total_pages - 1))  # Zabezpieczenie przed błędnym numerem strony
        
        start_idx = page * CARDS_PER_PAGE
        end_idx = min(start_idx + CARDS_PER_PAGE, len(hand))
        
        # Check if multi-select mode is enabled
        settings = game_state.get('settings', {})
        multi_select_enabled = settings.get('stack_colors', False) or settings.get('stack_numbers', False)
        
        # Get selected cards for this player
        selected_cards = game_state.get('selected_cards', {}).get(player_id, set())
        
        # Show cards as emoji buttons (max 15 = 3 rows x 5 buttons)
        for idx, i in enumerate(range(start_idx, end_idx)):
            card = hand[i]
            card_emoji = uno_logic.card_to_emoji(card, variant=variant)
            is_playable = i in playable
            is_selected = i in selected_cards
            
            # In multi-select mode, Wild cards cannot be toggled (no consistent color/value)
            is_wild = card['color'] == 'wild'
            
            # Disable all cards if it's not this player's turn
            is_disabled = not is_current_turn or not is_playable
            
            # Button style based on playability and selection
            if not is_current_turn:
                # Gray out all cards when not player's turn
                style = discord.ButtonStyle.secondary
            elif is_selected:
                style = discord.ButtonStyle.primary  # Blue = selected
            elif is_playable and not (multi_select_enabled and is_wild):
                style = discord.ButtonStyle.success  # Green = playable
            else:
                style = discord.ButtonStyle.secondary  # Gray = not playable or wild in multi-select
            
            # In multi-select mode, use toggle; otherwise single play
            action = "toggle" if multi_select_enabled else "play"
            
            view.add_item(discord.ui.Button(
                emoji=card_emoji,
                style=style,
                custom_id=f"uno_{action}_{game_id}_{i}",
                disabled=is_disabled,
                row=idx // 5  # Rows 0-2 for cards (15 cards = 3 rows)
            ))
        
        # Rows 3-4: Action buttons
        draw_stack = game_state.get('draw_stack', 0)
        
        # If multi-select enabled and cards selected, show "Play cards" button
        lang = self.get_lang(game_state)
        if multi_select_enabled and selected_cards:
            view.add_item(discord.ui.Button(
                label=f"✅ {self.t('hand.button_play_cards', lang=lang)} ({len(selected_cards)})",
                style=discord.ButtonStyle.success,
                custom_id=f"uno_play_multi_{game_id}",
                disabled=not is_current_turn,
                row=3
            ))
        
        # Draw button (only if auto_draw is OFF)
        # When auto_draw is ON, drawing is automatic - no button needed
        lang = self.get_lang(game_state)
        if not settings.get('auto_draw', False):
            if draw_stack > 0:
                button_label = f"{self.t('hand.button_draw_plus', lang=lang)} +{draw_stack}"
            else:
                button_label = self.t('hand.button_draw', lang=lang)
            view.add_item(discord.ui.Button(
                label=button_label,
                style=discord.ButtonStyle.danger,
                custom_id=f"uno_draw_{game_id}",
                disabled=not is_current_turn,
                row=3
            ))
        
        # UNO button (can be called even when not your turn, for callout mechanics)
        view.add_item(discord.ui.Button(
            label=self.t('hand.button_uno', lang=lang),
            style=discord.ButtonStyle.success,
            custom_id=f"uno_call_{game_id}",
            row=3
        ))
        
        # No Mercy+: Coin activation button (only in player's turn, after coin selection)
        if variant == 'no_mercy_plus':
            coins = game_state.get('coins', {})
            player_id_str = str(player_id)
            if player_id_str in coins:
                coin_data = coins[player_id_str]
                # Show button only if: selected coin, not used, and is current turn
                if coin_data.get('selected', False) and not coin_data.get('used', False) and is_current_turn:
                    coin_type = coin_data.get('type', 'mercy')
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    
                    coin_filename = 'mercy_coin.png' if coin_type == 'mercy' else 'nomercy_coin.png'
                    emoji_id = mapping.get(coin_filename)
                    coin_emoji = discord.PartialEmoji(name=coin_filename.replace('.png', ''), id=emoji_id) if emoji_id else None
                    
                    lang = self.get_lang(game_state)
                    view.add_item(discord.ui.Button(
                        label=self.t('coins.activate', lang=lang),
                        emoji=coin_emoji,
                        style=discord.ButtonStyle.primary,
                        custom_id=f"uno_coin_{game_id}",
                        row=3
                    ))
        
        # Navigation buttons on row 4
        if total_pages > 1:
            lang = self.get_lang(game_state)
            # Previous page button
            view.add_item(discord.ui.Button(
                label="◀️",
                style=discord.ButtonStyle.secondary,
                custom_id=f"uno_hand_prev_{game_id}_{page}",
                disabled=(page == 0),
                row=4
            ))
            
            # Page indicator
            view.add_item(discord.ui.Button(
                label=f"{self.t('hand.page', lang=lang)} {page + 1}/{total_pages}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"uno_hand_page_{game_id}_{page}",
                disabled=True,
                row=4
            ))
            
            # Next page button
            view.add_item(discord.ui.Button(
                label="▶️",
                style=discord.ButtonStyle.secondary,
                custom_id=f"uno_hand_next_{game_id}_{page}",
                disabled=(page >= total_pages - 1),
                row=4
            ))
        
        return view

    def create_color_select_view(self, game_id, side='light', lang='en'):
        """Create view for selecting wild card color"""
        view = discord.ui.View(timeout=None)
        
        if side == 'dark':
            # Dark side colors: teal, purple, pink, orange
            view.add_item(discord.ui.Button(
                label=f"🔵 {self.get_color_name('teal', lang)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"uno_color_{game_id}_teal",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🟣 {self.get_color_name('purple', lang)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"uno_color_{game_id}_purple",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🩷 {self.get_color_name('pink', lang)}",
                style=discord.ButtonStyle.danger,
                custom_id=f"uno_color_{game_id}_pink",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🟠 {self.get_color_name('orange', lang)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"uno_color_{game_id}_orange",
                row=0
            ))
        else:
            # Light side colors: red, yellow, green, blue
            view.add_item(discord.ui.Button(
                label=f"🔴 {self.get_color_name('red', lang)}",
                style=discord.ButtonStyle.danger,
                custom_id=f"uno_color_{game_id}_red",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🟡 {self.get_color_name('yellow', lang)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"uno_color_{game_id}_yellow",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🟢 {self.get_color_name('green', lang)}",
                style=discord.ButtonStyle.success,
                custom_id=f"uno_color_{game_id}_green",
                row=0
            ))
            view.add_item(discord.ui.Button(
                label=f"🔵 {self.get_color_name('blue', lang)}",
                style=discord.ButtonStyle.primary,
                custom_id=f"uno_color_{game_id}_blue",
                row=0
            ))
        
        return view
    
    async def check_and_apply_auto_draw(self, game, player_id, channel):
        """Check if auto-draw should be applied and execute it"""
        settings = game.get('settings', {})
        if not settings.get('auto_draw', False):
            return False  # Auto-draw not enabled
        
        current_player = game['players'][game['current_turn']]
        if player_id != current_player:
            return False  # Not player's turn
        
        hand = game['hands'].get(player_id, [])
        top_card = game['discard'][-1]
        current_color = game['current_color']
        draw_stack = game.get('draw_stack', 0)
        playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
        
        # If there's a draw stack and no playable cards, auto-draw the stack
        if draw_stack > 0 and not playable:
            # Draw entire stack
            uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
            drawn = uno_logic.draw_cards(game['deck'], draw_stack)
            if drawn:
                hand.extend(drawn)
            game['draw_stack'] = 0  # Clear the stack
            
            # Check for elimination after drawing stack
            if await self.check_elimination(game_id, game, player_id, channel):
                return  # Bot was eliminated
            
            # Clear UNO called status
            if 'uno_called' in game and player_id in game['uno_called']:
                game['uno_called'].discard(player_id)
            
            # Clear selected cards (multiselect mode)
            if 'selected_cards' in game and player_id in game['selected_cards']:
                game['selected_cards'][player_id] = set()
            
            # Pass turn automatically
            game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
            
            # Update main game display
            try:
                if game.get('messageId'):
                    current_player_new = game['players'][game['current_turn']]
                    embed_game, card_file_game = self.create_uno_game_embed(game)
                    view_game = self.create_uno_legacy_game_view(game.get('game_id', 'unknown'), game, current_player_new)
                    msg_game = channel.get_partial_message(game['messageId'])
                    files_game = [card_file_game] if card_file_game else []
                    await msg_game.edit(embed=embed_game, view=view_game, attachments=files_game)
            except Exception:
                pass
            
            # Odśwież opponent_views dla trybu Flip
            await self.refresh_opponent_views(game)
            
            # Odśwież rękę gracza który dostał karę
            hand_messages = game.get('hand_messages', {})
            if player_id in hand_messages:
                try:
                    old_interaction, old_msg = hand_messages[player_id]
                    lang = self.get_lang(game)
                    
                    penalty_embed = discord.Embed(
                        title=f"💥 {self.t('messages.auto_drew_penalty', lang=lang)}",
                        description=f"{self.t('messages.auto_drew', lang=lang)} **{len(drawn)} {self.t('messages.cards', lang=lang)}** (+{draw_stack} {self.t('messages.penalty', lang=lang)})\n\n{self.t('messages.you_have', lang=lang)} {self.t('messages.now', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}",
                        color=0xe74c3c
                    )
                    
                    # Show current top card
                    top_card = game['discard'][-1]
                    table_card_file = uno_logic.card_to_image(top_card)
                    if table_card_file:
                        penalty_embed.set_image(url=f"attachment://{table_card_file.filename}")
                        files_hand = [table_card_file]
                    else:
                        files_hand = []
                    
                    view_hand = self.create_uno_hand_view(game.get('game_id', 'unknown'), game, player_id)
                    await old_msg.edit(embed=penalty_embed, view=view_hand, attachments=files_hand)
                except Exception:
                    pass
            
            # Check if next player is BOT
            next_player = game['players'][game['current_turn']]
            if next_player.startswith('BOT_'):
                game_id = game.get('game_id', 'unknown')
                await asyncio.sleep(1.5)
                await self.play_bot_uno_turn(channel, game_id, game)
            
            return True  # Auto-draw stack was applied
        
        # If no playable cards and no draw stack, auto-draw single card
        if not playable and draw_stack == 0:
            # Auto-draw a card
            uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
            drawn = uno_logic.draw_cards(game['deck'], 1)
            if not drawn:
                return False
            
            hand.extend(drawn)
            
            # Check for elimination after auto-draw
            if await self.check_elimination(game_id, game, player_id, channel):
                return True  # Bot was eliminated
            
            # Clear UNO called status
            if 'uno_called' in game and player_id in game['uno_called']:
                game['uno_called'].discard(player_id)
            
            # Clear selected cards (multiselect mode)
            if 'selected_cards' in game and player_id in game['selected_cards']:
                game['selected_cards'][player_id] = set()
            
            # Pass turn automatically
            game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
        
        # Update main game display
        try:
            if game.get('messageId'):
                current_player_new = game['players'][game['current_turn']]
                embed_game, card_file_game = self.create_uno_game_embed(game)
                view_game = self.create_uno_legacy_game_view(game.get('game_id', 'unknown'), game, current_player_new)
                msg_game = channel.get_partial_message(game['messageId'])
                files_game = [card_file_game] if card_file_game else []
                await msg_game.edit(embed=embed_game, view=view_game, attachments=files_game)
        except Exception:
            pass
        
        # Odśwież opponent_views dla trybu Flip
        await self.refresh_opponent_views(game)
        
        # Check if next player is BOT
        next_player = game['players'][game['current_turn']]
        if next_player.startswith('BOT_'):
            game_id = game.get('game_id', 'unknown')
            await asyncio.sleep(1.5)
            await self.play_bot_uno_turn(channel, game_id, game)
        
        return True  # Auto-draw was applied
    
    async def refresh_opponent_views(self, game):
        """Refresh only ephemeral opponent card views (for Flip mode)"""
        variant = game.get('settings', {}).get('variant', 'classic')
        if variant == 'flip':
            
            current_side = game.get('current_side', 'light')
            opposite_side = 'dark' if current_side == 'light' else 'light'
            card_mapping = game.get('card_mapping', None)
            lang = self.get_lang(game)
            
            opponent_views = game.get('opponent_views', {})
            for viewer_uid, view_data in list(opponent_views.items()):
                try:
                    msg = view_data['message']
                    
                    current_side_text = self.t('messages.light', lang=lang) if current_side == 'light' else self.t('messages.dark', lang=lang)
                    opposite_side_text = self.t('messages.dark', lang=lang) if opposite_side == 'dark' else self.t('messages.light', lang=lang)
                    
                    embed = discord.Embed(
                        title=f"👥 {self.t('messages.opponent_cards_title', lang=lang)}",
                        description=f"{self.t('messages.flip_see_opposite', lang=lang)}\n\n🎴 {self.t('messages.flip_game_side', lang=lang)} **🌅 {current_side_text}**\n👁️ {self.t('messages.flip_you_see', lang=lang)} **🌙 {opposite_side_text}**",
                        color=0x9B59B6
                    )
                    
                    has_opponents = False
                    
                    for player_id in game['players']:
                        if player_id == viewer_uid:
                            continue
                        
                        if player_id not in game['hands']:
                            continue
                        
                        has_opponents = True
                        hand = game['hands'][player_id]
                        
                        player_name = self.get_bot_display_name(player_id, game)
                        
                        card_display = ""
                        for i, card in enumerate(hand, 1):
                            flipped_card = self.flip_handler.flip_card(card, card_mapping)
                            emoji = uno_logic.card_to_emoji(flipped_card, variant='flip')
                            # Convert emoji to string format for embed
                            if isinstance(emoji, discord.PartialEmoji):
                                card_display += f"<:{emoji.name}:{emoji.id}> "
                            else:
                                card_display += str(emoji) + " "
                            if i % 8 == 0:
                                card_display += "\n"
                        
                        if not card_display:
                            card_display = "*(brak kart)*"
                        
                        embed.add_field(
                            name=f"{player_name} - {len(hand)} kart",
                            value=card_display,
                            inline=False
                        )
                    
                    if not has_opponents:
                        embed.description = self.t('messages.no_other_players', lang=lang)
                    
                    await msg.edit(embed=embed)
                except Exception:
                    opponent_views.pop(viewer_uid, None)

    async def auto_refresh_player_hand(self, game_id, game, player_id, channel):
        """Auto-refresh player's hand view when it's their turn (z pętlą auto-draw)"""
        uno_back = self.get_uno_back_emoji()
        checked_players = set()
        
        # FIRST: Check if player needs to handle DRAW COLOR selection
        if 'pending_draw_color' in game and game['pending_draw_color']['player'] == player_id:
            draw_color_data = game['pending_draw_color']
            card = draw_color_data['card']
            initiator = draw_color_data['initiator']
            initiator_display = self.get_bot_display_name(initiator, game)
            
            # Get variant to determine color selection
            variant = game.get('settings', {}).get('variant', 'classic')
            
            # For Flip, use current_side; for others, always use light side colors
            if variant == 'flip':
                current_side = game.get('current_side', 'light')
                color_side = current_side
            else:
                color_side = 'light'
            
            # Get card name based on variant
            lang = self.get_lang(game)
            card_name = "WILD COLOR ROULETTE" if variant == 'no_mercy' else "WILD DRAW COLOR"
            
            # Show color selection for draw_color
            hand_embed = discord.Embed(
                title=f"🎨 {card_name}!",
                description=f"{initiator_display} {self.t('messages.played_card', lang=lang)} **{card_name}**!\n\n⬇️ **{self.t('messages.select_color_wild', lang=lang)}**",
                color=0xe74c3c
            )
            
            wild_card_file = uno_logic.card_to_image(card)
            files = []
            if wild_card_file:
                hand_embed.set_image(url=f"attachment://{wild_card_file.filename}")
                files.append(wild_card_file)
            
            color_view = self.create_color_select_view(game_id, side=color_side, lang=self.get_lang(game))
            
            # Send or update hand message
            hand_msg_data = game.get('hand_messages', {}).get(player_id)
            if hand_msg_data:
                old_interaction, old_message = hand_msg_data
                try:
                    await old_message.edit(embed=hand_embed, view=color_view, attachments=files)
                except Exception:
                    # If edit fails, remove old reference
                    game.get('hand_messages', {}).pop(player_id, None)
            
            return  # Don't show normal hand, wait for color selection
        
        while True:
            if player_id.startswith('BOT_') or player_id in checked_players:
                return
            checked_players.add(player_id)
            auto_drawn = await self.check_and_apply_auto_draw(game, player_id, channel)
            if not auto_drawn:
                break
            # Tura przeszła dalej, sprawdź nowego gracza
            player_id = game['players'][game['current_turn']]
        
        # Clear selected cards for new player (multiselect mode)
        if 'selected_cards' not in game:
            game['selected_cards'] = {}
        game['selected_cards'][player_id] = set()
        
        hand = game['hands'].get(player_id)
        if not hand:
            return
        top_card = game['discard'][-1]
        current_color = game['current_color']
        lang = self.get_lang(game)
        embed = discord.Embed(
            title=f"{uno_back} {self.t('hand.title', lang=lang)} - {self.t('messages.your_turn_caps', lang=lang)}!",
            description=f"✅ **{self.t('messages.your_turn', lang=lang)}!** {self.t('messages.play_or_draw', lang=lang)}\n\n{self.t('messages.you_have', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}",
            color=0x2ECC71
        )
        table_card_file = uno_logic.card_to_image(top_card)
        files = []
        if table_card_file:
            files.append(table_card_file)
            embed.set_image(url=f"attachment://{table_card_file.filename}")
        view = self.create_uno_hand_view(game_id, game, player_id)
        hand_msg_data = game.get('hand_messages', {}).get(player_id)
        if hand_msg_data:
            old_interaction, old_message = hand_msg_data
            try:
                await old_message.edit(embed=embed, view=view, attachments=files)
            except Exception:
                game.get('hand_messages', {}).pop(player_id, None)
    
    async def play_bot_uno_turn(self, channel, game_id, game_state):
        """Bot plays UNO turn"""
        uno_back = self.get_uno_back_emoji()
        
        game = self.bot.active_games.get(game_id)
        if not game:
            return
        
        game['last_activity'] = time.time()  # Aktualizuj aktywność
        
        # Check if current_turn is valid (game might have ended or player eliminated)
        if game['current_turn'] >= len(game['players']):
            return
        
        current_player = game['players'][game['current_turn']]
        if not current_player.startswith('BOT_'):
            return
        
        hand = game['hands'][current_player]
        top_card = game['discard'][-1]
        current_color = game['current_color']
        draw_stack = game.get('draw_stack', 0)
        settings = game.get('settings', {})
        variant = settings.get('variant', 'classic')
        
        # No Mercy+: Bot coin logic
        if variant == 'no_mercy_plus':
            coins = game.get('coins', {})
            if current_player in coins:
                coin_data = coins[current_player]
                if coin_data.get('selected', False) and not coin_data.get('used', False):
                    coin_type = coin_data.get('type')
                    
                    # MERCY: Use when hand >= 23 cards (close to elimination at 25)
                    # Auto-use at 25 is handled by check_elimination as "drugie życie"
                    if coin_type == 'mercy' and len(hand) >= 23:
                        self.no_mercy_plus_handler.use_mercy_coin(game, current_player)
                        coins[current_player]['used'] = True
                        
                        bot_name = self.get_bot_display_name(current_player, game)
                        try:
                            lang = self.get_lang(game)
                            mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                            mercy_id = mapping.get('mercy_coin.png')
                            mercy_emoji = f"<:mercy_coin:{mercy_id}>" if mercy_id else "🪙"
                            await channel.send(
                                f"{mercy_emoji} **{bot_name} {self.t('coins.used_mercy', lang=lang)}!**\n\n{self.t('coins.mercy_effect', lang=lang)}",
                                silent=True,
                                delete_after=8
                            )
                        except Exception:
                            pass
                        
                        # Update hand reference after MERCY
                        hand = game['hands'][current_player]
                    
                    # NO MERCY: Use when about to play draw card with stack
                    elif coin_type == 'no_mercy' and draw_stack > 0:
                        # Check if bot has draw card to play
                        playable_check = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
                        if playable_check:
                            card_to_check = hand[playable_check[0]]
                            if card_to_check.get('value') in ['draw_2', 'wild+4', 'wild_draw_color', '+6', '+10', 'reverse_draw_8']:
                                # Activate NO MERCY before playing draw card
                                coins[current_player]['pending_no_mercy'] = True
                                coins[current_player]['used'] = True
                                
                                bot_name = self.get_bot_display_name(current_player, game)
                                try:
                                    lang = self.get_lang(game)
                                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                                    nomercy_id = mapping.get('nomercy_coin.png')
                                    nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                                    await channel.send(
                                        f"{nomercy_emoji} **{bot_name} {self.t('coins.activated_nomercy', lang=lang)}!**\n\n{self.t('coins.nomercy_effect', lang=lang)}",
                                        silent=True,
                                        delete_after=8
                                    )
                                except Exception:
                                    pass
        
        # Check if bot can play any card (considering draw_stack)
        playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
        
        if playable:
            # Bot chooses from playable cards
            card_idx = playable[0]  # Simple: pick first playable
        else:
            card_idx = None
        
        if card_idx is not None:
            # Play card
            card = hand.pop(card_idx)
            game['discard'].append(card)
            
            # Check if bot wins
            if uno_logic.check_winner(hand):
                if await self.handle_player_win(game_id, game, current_player, None, channel):
                    return  # Game ended
                
                # Game continues (last standing mode)
                current_player = game['players'][game['current_turn']]
                embed_main, file_main = self.create_uno_game_embed(game)
                view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                try:
                    if game.get('messageId'):
                        msg = channel.get_partial_message(game['messageId'])
                        files_main = [file_main] if file_main else []
                        await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                except Exception:
                    pass
                
                # Trigger bot again if still bot's turn, or refresh player hand
                if current_player.startswith('BOT_'):
                    await self.play_bot_uno_turn(channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, channel)
            
            # Apply card effects
            variant = game.get('settings', {}).get('variant', 'classic')
            
            # Handle discard_all_card effect (No Mercy/No Mercy+)
            if (variant == 'no_mercy' or variant == 'no_mercy_plus') and card['value'] == 'discard_all_card':
                discard_color = card['color']
                # Bot discards all cards of the same color
                cards_to_discard = [c for c in hand if c['color'] == discard_color]
                if cards_to_discard:
                    hand[:] = [c for c in hand if c['color'] != discard_color]
                    game['discard'].extend(cards_to_discard)
                    
                    # Check if bot wins AFTER discarding
                    if uno_logic.check_winner(hand):
                        if await self.handle_player_win(game_id, game, current_player, None, channel):
                            return  # Game ended
                        
                        # Game continues (last standing mode)
                        current_player = game['players'][game['current_turn']]
                        embed_main, file_main = self.create_uno_game_embed(game)
                        view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                        try:
                            if game.get('messageId'):
                                msg = channel.get_partial_message(game['messageId'])
                                await msg.edit(embed=embed_main, view=view_main, attachments=[file_main] if file_main else [])
                        except Exception:
                            pass
                        
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(channel, game_id, game)
                        else:
                            await self.auto_refresh_player_hand(game_id, game, current_player, channel)
                        return
            
            # Calculate effects BEFORE flip (for flip cards)
            effects = uno_logic.apply_card_effect(card, game)
            
            # Handle FLIP card in Flip mode
            if variant == 'flip' and card['value'] == 'flip':
                flip_message = await self.flip_handler.handle_flip_card_played(game)
                # After flip, update card reference to the flipped card from discard pile
                # BUT keep the original effects (don't recalculate for flipped card)
                if game['discard']:
                    card = game['discard'][-1]
                # Notify about flip
                try:
                    lang = self.get_lang(game)
                    flip_embed = discord.Embed(
                        title=f"🔄 {self.t('messages.flip_card', lang=lang).upper()}!",
                        description=flip_message,
                        color=0x9B59B6
                    )
                    await channel.send(embed=flip_embed, delete_after=5)
                except Exception:
                    pass
            
            if card['color'] == 'wild' or card['value'] == 'wild+4':
                game['current_color'] = uno_logic.bot_choose_color(hand)
            else:
                game['current_color'] = card['color']
            
            # Handle No Mercy+ special cards
            if variant == 'no_mercy_plus':
                if effects.get('sudden_death'):
                    # Wild Sudden Death: All players draw to 24 cards
                    draws = self.no_mercy_plus_handler.handle_wild_sudden_death(game)
                    
                    # Notify channel
                    try:
                        bot_name = self.get_bot_display_name(current_player, game)
                        lang = self.get_lang(game)
                        draw_text = "\n".join([
                            f"{self.get_bot_display_name(pid, game)}: +{count}" 
                            for pid, count in draws.items() if count > 0
                        ])
                        await channel.send(
                            f"💀⚡ **{bot_name} {self.t('messages.sudden_death_played', lang=lang)}!**\n\n"
                            f"{self.t('messages.all_draw_to_24', lang=lang)}\n\n{draw_text}",
                            silent=True,
                            delete_after=10
                        )
                    except Exception:
                        pass
                
                elif effects.get('wild_discard_all'):
                    # Wild Discard All: Bot chooses color and discards all cards of that color
                    chosen_color = uno_logic.bot_choose_color(hand)
                    game['current_color'] = chosen_color
                    
                    # Execute discard all for chosen color
                    self.no_mercy_plus_handler.handle_wild_discard_all(game, current_player, chosen_color)
                    
                    bot_name = self.get_bot_display_name(current_player, game)
                    lang = self.get_lang(game)
                    try:
                        await channel.send(
                            f"🗑️ **{bot_name} {self.t('messages.wild_discard_played', lang=lang)}!**\n\n"
                            f"🎨 {self.t('messages.chosen_color', lang=lang)}: **{chosen_color.upper()}**\n"
                            f"{self.t('messages.discarded_all_color', lang=lang)} {uno_logic.COLOR_EMOJIS.get(chosen_color, chosen_color)}",
                            silent=True,
                            delete_after=8
                        )
                    except Exception:
                        pass
                    
                    # Check if bot wins AFTER discarding
                    if uno_logic.check_winner(hand):
                        if await self.handle_player_win(game_id, game, current_player, None, channel):
                            return  # Game ended
                        
                        # Game continues (last standing mode)
                        current_player = game['players'][game['current_turn']]
                        embed_main, file_main = self.create_uno_game_embed(game)
                        view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                        try:
                            if game.get('messageId'):
                                msg = channel.get_partial_message(game['messageId'])
                                files_main = [file_main] if file_main else []
                                await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                        except Exception:
                            pass
                        
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(channel, game_id, game)
                        else:
                            await self.auto_refresh_player_hand(game_id, game, current_player, channel)
                        return
                
                elif effects.get('final_attack'):
                    # Wild Final Attack: Reveal bot's hand, draw based on action cards
                    next_player_id, main_draw, all_draw, action_count = self.no_mercy_plus_handler.handle_wild_final_attack(game, current_player)
                    
                    bot_name = self.get_bot_display_name(current_player, game)
                    bot_hand = game['hands'][current_player]
                    
                    # Show bot's hand (reveal cards)
                    hand_emojis = []
                    for c in bot_hand:
                        emoji = uno_logic.card_to_emoji(c, variant)
                        if isinstance(emoji, discord.PartialEmoji):
                            hand_emojis.append(f"<:{emoji.name}:{emoji.id}>")
                        else:
                            hand_emojis.append(str(emoji))
                    hand_display = " ".join(hand_emojis)
                    
                    lang = self.get_lang(game)
                    try:
                        if all_draw:
                            # MEGA ATTACK (7+ action cards)
                            next_name = self.get_bot_display_name(next_player_id, game)
                            await channel.send(
                                f"⚔️💥 **{bot_name} {self.t('messages.final_attack_played', lang=lang)}!**\n\n"
                                f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                                f"**{action_count} {self.t('messages.action_cards', lang=lang)}!** (≥7)\n\n"
                                f"💀 **{self.t('messages.mega_attack', lang=lang)}:**\n"
                                f"• {next_name}: +25 {self.t('messages.cards', lang=lang)}\n"
                                f"• {self.t('messages.all_others', lang=lang)}: +5 {self.t('messages.cards', lang=lang)}",
                                silent=True,
                                delete_after=12
                            )
                            # Next player draws 25
                            uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                            drawn = uno_logic.draw_cards(game['deck'], main_draw)
                            if drawn:
                                game['hands'][next_player_id].extend(drawn)
                            
                            # All others draw 5
                            for pid in game['players']:
                                if pid != current_player and pid != next_player_id:
                                    uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                    drawn = uno_logic.draw_cards(game['deck'], 5)
                                    if drawn:
                                        game['hands'][pid].extend(drawn)
                        else:
                            # Normal attack
                            next_name = self.get_bot_display_name(next_player_id, game)
                            await channel.send(
                                f"⚔️ **{bot_name} {self.t('messages.final_attack_played', lang=lang)}!**\n\n"
                                f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                                f"**{action_count} {self.t('messages.action_cards', lang=lang)}**\n\n"
                                f"{next_name} {self.t('messages.auto_drew', lang=lang)} +{action_count} {self.t('messages.cards', lang=lang)}!",
                                silent=True,
                                delete_after=10
                            )
                            # Next player draws
                            uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                            drawn = uno_logic.draw_cards(game['deck'], main_draw)
                            if drawn:
                                game['hands'][next_player_id].extend(drawn)
                    except Exception:
                        pass
            
            # Handle 7-0 Rule effects for bot
            if effects.get('swap_hands'):
                # Bot played a 7 - swap with player who has most cards
                other_players = [p for p in game['players'] if not p.startswith('BOT_')]
                if other_players:
                    target = max(other_players, key=lambda p: len(game['hands'][p]))
                    hands = game['hands']
                    temp_hand = hands[current_player]
                    hands[current_player] = hands[target]
                    hands[target] = temp_hand
                    hand = hands[current_player]  # Update reference
                    
                    # Check if bot wins after swap
                    if uno_logic.check_winner(hand):
                        if await self.handle_player_win(game_id, game, current_player, None, channel):
                            return  # Game ended
                        
                        # Game continues (last standing mode)
                        current_player = game['players'][game['current_turn']]
                        embed_main, file_main = self.create_uno_game_embed(game)
                        view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                        try:
                            if game.get('messageId'):
                                msg = channel.get_partial_message(game['messageId'])
                                files_main = [file_main] if file_main else []
                                await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                        except Exception:
                            pass
                        
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(channel, game_id, game)
                        else:
                            await self.auto_refresh_player_hand(game_id, game, current_player, channel)
                        return
                    
                    # Notify the swapped player via their hand message (ephemeral)
                    hand_messages = game.get('hand_messages', {})
                    if target in hand_messages:
                        try:
                            old_interaction, old_msg = hand_messages[target]
                            target_hand = hands[target]
                            bot_name = self.get_bot_display_name(current_player, game)
                            lang = self.get_lang(game)
                            swap_embed = discord.Embed(
                                title=f"🔄 {self.t('messages.card_7_swap', lang=lang)}!",
                                description=f"{bot_name} {self.t('messages.swapped_hands', lang=lang)}\n\n{self.t('messages.you_now_have', lang=lang)} **{len(target_hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}",
                                color=0x9b59b6
                            )
                            swap_hand_view = self.create_uno_hand_view(game_id, game, target)
                            await old_msg.edit(embed=swap_embed, view=swap_hand_view, attachments=[])
                        except Exception:
                            pass
                    
                    # Odśwież opponent_views dla trybu Flip
                    await self.refresh_opponent_views(game)
                    
            elif effects.get('rotate_hands'):
                # Bot played a 0 - rotate all hands in play direction
                players = game['players']
                hands = game['hands']
                
                direction_text = "w dół ⬇️" if game['direction'] == 1 else "w górę ⬆️"
                
                if game['direction'] == 1:
                    # Clockwise rotation: last player's hand goes to first
                    temp_hand = hands[players[-1]]
                    for i in range(len(players) - 1, 0, -1):
                        hands[players[i]] = hands[players[i-1]]
                    hands[players[0]] = temp_hand
                else:
                    # Counter-clockwise rotation: first player's hand goes to last
                    temp_hand = hands[players[0]]
                    for i in range(len(players) - 1):
                        hands[players[i]] = hands[players[i+1]]
                    hands[players[-1]] = temp_hand
                
                hand = hands[current_player]  # Update reference
                
                # Check if bot wins after rotation
                if uno_logic.check_winner(hand):
                    if await self.handle_player_win(game_id, game, current_player, None, channel):
                        return  # Game ended
                    
                    # Game continues (last standing mode)
                    current_player = game['players'][game['current_turn']]
                    embed_main, file_main = self.create_uno_game_embed(game)
                    view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                    try:
                        if game.get('messageId'):
                            msg = channel.get_partial_message(game['messageId'])
                            files_main = [file_main] if file_main else []
                            await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                    except Exception:
                        pass
                    
                    if current_player.startswith('BOT_'):
                        await self.play_bot_uno_turn(channel, game_id, game)
                    else:
                        await self.auto_refresh_player_hand(game_id, game, current_player, channel)
                    return

                # Odśwież rękę każdego gracza po rotacji
                hand_messages = game.get('hand_messages', {})
                for pid in players:
                    if pid in hand_messages:
                        try:
                            old_interaction, old_msg = hand_messages[pid]
                            embed_hand, card_file_hand = self.create_uno_hand_embed(game_id, game, pid)
                            view_hand = self.create_uno_hand_view(game_id, game, pid)
                            files_hand = [card_file_hand] if card_file_hand else []
                            await old_msg.edit(embed=embed_hand, view=view_hand, attachments=files_hand)
                        except Exception:
                            pass
                
                # Odśwież opponent_views dla trybu Flip
                await self.refresh_opponent_views(game)

                # Send single notification about rotation
                player_mentions = [f"<@{p}>" for p in players if not p.startswith('BOT_')]
                bot_name = self.get_bot_display_name(current_player, game)
                lang = self.get_lang(game)
                rotate_notify = discord.Embed(
                    title=f"🔄 {self.t('messages.card_0_rotation', lang=lang)}!",
                    description=f"{bot_name} {self.t('messages.played_card_0', lang=lang)}\n\n**{self.t('messages.all_hands_moved', lang=lang)} {direction_text}**\n\n{self.t('messages.hands_updated', lang=lang)}",
                    color=0x9b59b6
                )
                try:
                    await channel.send(
                        " ".join(player_mentions),
                        embed=rotate_notify,
                        delete_after=5
                    )
                except Exception:
                    pass
            
            if effects.get('reverse'):
                if len(game['players']) == 2:
                    pass
                else:
                    game['direction'] *= -1
            
            skip_turn = False
            if effects.get('skip_next'):
                skip_turn = True
            if effects.get('draw_penalty'):
                # Stack the draw penalty - next player can counter or must draw all
                draw_amount = effects['draw_penalty']
                
                # Check if bot has pending NO MERCY coin (doubles draw penalty)
                if variant == 'no_mercy_plus':
                    coins = game.get('coins', {})
                    if current_player in coins and coins[current_player].get('pending_no_mercy', False):
                        draw_amount = draw_amount * 2
                        coins[current_player]['pending_no_mercy'] = False  # Use it up
                        
                        bot_name = self.get_bot_display_name(current_player, game)
                        try:
                            mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                            nomercy_id = mapping.get('nomercy_coin.png')
                            nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                            await channel.send(
                                f"{nomercy_emoji} **NO MERCY!** {bot_name} podwoił karę: +{effects['draw_penalty']} → +{draw_amount}!",
                                silent=True,
                                delete_after=15
                            )
                        except Exception:
                            pass
                
                game['draw_stack'] = game.get('draw_stack', 0) + draw_amount
            
            # Next turn
            if effects.get('play_again'):
                # Card 10: Play Again - keep current turn (extra turn)
                pass  # Don't change current_turn
            elif len(game['players']) == 2 and effects.get('reverse'):
                # With 2 players and reverse, bot keeps their turn (plays again)
                pass  # Don't change current_turn
            elif skip_turn:
                game['current_turn'] = (game['current_turn'] + game['direction'] * 2) % len(game['players'])
            else:
                game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
            
        else:
            # Bot draws card(s) - check for draw stack
            if draw_stack > 0:
                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                drawn = uno_logic.draw_cards(game['deck'], draw_stack)
                if drawn:
                    hand.extend(drawn)
                game['draw_stack'] = 0
                
                # Check for elimination after drawing stack
                if await self.check_elimination(game_id, game, current_player, channel):
                    return  # Bot was eliminated
            else:
                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                drawn = uno_logic.draw_cards(game['deck'], 1)
                if drawn:
                    hand.extend(drawn)
                
                # Check for elimination after drawing single card
                if await self.check_elimination(game_id, game, current_player, channel):
                    return  # Bot was eliminated
            
            game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
        
        # Update display
        current_player = game['players'][game['current_turn']]
        embed, card_file = self.create_uno_game_embed(game)
        view = self.create_uno_legacy_game_view(game_id, game, current_player)
        
        try:
            if game.get('messageId'):
                msg = channel.get_partial_message(game['messageId'])
                files = [card_file] if card_file else []
                await msg.edit(embed=embed, view=view, attachments=files)
        except Exception:
            pass
        
        # Odśwież opponent_views dla trybu Flip
        await self.refresh_opponent_views(game)
        
        # Auto-refresh hand for next player
        if not current_player.startswith('BOT_'):
            await self.auto_refresh_player_hand(game_id, game, current_player, channel)
        
        # Continue bot chain if needed
        if current_player.startswith('BOT_'):
            await asyncio.sleep(2)
            await self.play_bot_uno_turn(channel, game_id, game)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMANDS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @app_commands.command(name="uno", description="Create an UNO lobby")
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def uno(self, interaction: discord.Interaction):
        try:
            lobby_id = f"uno_lobby_{interaction.channel_id}_{interaction.user.id}"
            uid_str = str(interaction.user.id)

            # Prevent creating while in other game/lobby
            for g in self.bot.active_games.values():
                if uid_str in g.get('players', []):
                    return await interaction.response.send_message("You cannot create a lobby while in another active game.", ephemeral=True)
            for lid, l in self.bot.active_lobbies.items():
                if uid_str in l.get('players', []) or l.get('hostId') == uid_str:
                    return await interaction.response.send_message("You cannot create a new lobby while already in a lobby.", ephemeral=True)

            if lobby_id in self.bot.active_lobbies:
                return await interaction.response.send_message("You already have an active UNO lobby in this channel.", ephemeral=True)

            # Ensure player exists in economy (get_balance creates if needed)
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.get_balance(interaction.user.id)

            lobby_state = {
                'hostId': str(interaction.user.id),
                'players': [str(interaction.user.id)],
                'maxPlayers': 10,
                'minPlayers': 2,
                'messageId': None,
                'last_activity': time.time(),
                'start_time': time.time(),
                'bot_names': {},  # Mapowanie bot_id -> nazwa
                'lang': 'en',  # Default language: English
                'guild_id': interaction.guild.id if interaction.guild else None,
                'settings': {
                    'starting_cards': 7,
                    'stack_plus_two': True, 'stack_plus_four': False, 'stack_combined': False,
                    'stack_colors': False, 'stack_numbers': False,
                    'auto_draw': False, 'draw_until_play': False, 'skip_after_draw': True,
                    'must_play': False, 'uno_callout': True, 'penalty_cards': 2,
                    'penalty_false_uno': 2, 'seven_zero': False, 'jump_in': False, 'first_win': True
                }
            }

            # Use create_uno_lobby_embed_and_view for consistency
            try:
                host = await self.bot.fetch_user(int(lobby_state['hostId']))
            except:
                host = interaction.user
            
            embed, view = self.create_uno_lobby_embed_and_view(lobby_state, lobby_id, host)
            
            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()
            lobby_state['messageId'] = msg.id
            self.bot.active_lobbies[lobby_id] = lobby_state
        except Exception as e:
            print(f"[UNO] ERROR creating lobby: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Error creating lobby: {e}", ephemeral=True)
            except:
                pass
    
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTERACTION HANDLER
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def handle_uno_interaction(self, interaction, cid):
        """Główny handler dla wszystkich interakcji UNO"""
        uid = str(interaction.user.id)
        
        # --- UNO: LOBBY ---
        if cid.startswith('uno_lobby_'):
            # Sprawdź czy to nowe przyciski botów
            if cid.startswith('uno_lobby_bot_add_'):
                action = 'add'
                lobby_id = cid[len('uno_lobby_bot_add_'):]
            elif cid.startswith('uno_lobby_bot_remove_'):
                action = 'remove'
                lobby_id = cid[len('uno_lobby_bot_remove_'):]
            else:
                parts = cid.split('_')
                action = parts[2]
                lobby_id = "_".join(parts[3:])
            
            lobby = self.bot.active_lobbies.get(lobby_id)
            if not lobby:
                return await interaction.response.send_message("Lobby inactive.", ephemeral=True)
            
            try:
                host = await self.bot.fetch_user(int(lobby['hostId']))
            except (discord.errors.DiscordServerError, discord.errors.HTTPException):
                # Discord API tymczasowo niedostępne - użyj cache lub pomiń
                host = self.bot.get_user(int(lobby['hostId']))
                if not host:
                    # If not in cache, create a replacement object
                    class FakeUser:
                        def __init__(self, user_id):
                            self.id = int(user_id)
                            self.mention = f"<@{user_id}>"
                    host = FakeUser(lobby['hostId'])
            
            if action == 'join':
                if uid in lobby['players']:
                    return await interaction.response.send_message("You're already in the lobby!", ephemeral=True)
                if len(lobby['players']) >= lobby['maxPlayers']:
                    return await interaction.response.send_message("Lobby is full!", ephemeral=True)
                
                lobby['players'].append(uid)
                lobby['last_activity'] = time.time()
                
                await interaction.response.defer()
                embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'bot':
                # Stary handler - może być usunięty
                if 'add' in parts or 'remove' in parts:
                    pass  # Supported by the new handlers below
                elif uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can add bots!", ephemeral=True)
                elif len(lobby['players']) >= lobby['maxPlayers']:
                    return await interaction.response.send_message("Lobby is full!", ephemeral=True)
                else:
                    # Find next available bot ID
                    bot_count = len([p for p in lobby['players'] if p.startswith('BOT_')])
                    new_bot_id = f'BOT_{bot_count + 1}'
                    
                    # Assign a random name from the bot owners
                    if 'bot_names' not in lobby:
                        lobby['bot_names'] = {}
                    used_names = set(lobby['bot_names'].values())
                    owner_names = await self.get_bot_owner_names()
                    available_names = [n for n in owner_names if n not in used_names]
                    if available_names:
                        lobby['bot_names'][new_bot_id] = random.choice(available_names)
                    else:
                        lobby['bot_names'][new_bot_id] = f'BOT {bot_count + 1}'
                    
                    lobby['players'].append(new_bot_id)
                    lobby['last_activity'] = time.time()
                    
                    await interaction.response.defer()
                    embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                    await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'add':
                # Nowy handler dla 🤖➕
                if uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can add bots!", ephemeral=True)
                if len(lobby['players']) >= lobby['maxPlayers']:
                    return await interaction.response.send_message("Lobby is full!", ephemeral=True)
                
                # Find next available bot ID
                bot_count = len([p for p in lobby['players'] if p.startswith('BOT_')])
                new_bot_id = f'BOT_{bot_count + 1}'
                
                # Przypisz losową nazwę z właścicieli bota
                if 'bot_names' not in lobby:
                    lobby['bot_names'] = {}
                used_names = set(lobby['bot_names'].values())
                owner_names = await self.get_bot_owner_names()
                available_names = [n for n in owner_names if n not in used_names]
                if available_names:
                    lobby['bot_names'][new_bot_id] = random.choice(available_names)
                else:
                    lobby['bot_names'][new_bot_id] = f'BOT {bot_count + 1}'
                
                lobby['players'].append(new_bot_id)
                lobby['last_activity'] = time.time()
                
                await interaction.response.defer()
                embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'remove':
                # Nowy handler dla 🤖➖
                if uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can remove bots!", ephemeral=True)
                
                # Znajdź ostatniego bota
                bot_players = [p for p in lobby['players'] if p.startswith('BOT_')]
                if not bot_players:
                    return await interaction.response.send_message("❌ No bots!", ephemeral=True)
                
                # Usuń ostatniego bota
                last_bot = bot_players[-1]
                lobby['players'].remove(last_bot)
                if 'bot_names' in lobby and last_bot in lobby['bot_names']:
                    del lobby['bot_names'][last_bot]
                lobby['last_activity'] = time.time()
                
                await interaction.response.defer()
                embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'leave':
                if uid not in lobby['players']:
                    return await interaction.response.send_message("You're not in this lobby!", ephemeral=True)
                
                lobby['players'].remove(uid)
                lobby['last_activity'] = time.time()
                
                if not lobby['players'] or uid == lobby['hostId']:
                    try:
                        await interaction.message.delete()
                    except Exception:
                        pass
                    del self.bot.active_lobbies[lobby_id]
                    return await interaction.response.send_message("Lobby disbanded.", ephemeral=True)
                
                await interaction.response.defer()
                embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'settings':
                if uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can change settings!", ephemeral=True)
                
                lang = self.get_lang(lobby)
                settings_view, settings_desc = self.create_uno_settings_view_and_description(lobby_id, lobby['settings'], lang=lang)
                
                await interaction.response.send_message(
                    f"⚙️ **{self.t('settings.title', lang=lang)}**\n\n{settings_desc}",
                    view=settings_view,
                    ephemeral=True
                )
            
            elif action == 'lang':
                # Toggle language between PL and EN
                if uid != lobby['hostId']:
                    lang = self.get_lang(lobby)
                    return await interaction.response.send_message(
                        f"Only the host can change language!" if lang == 'en' else "Tylko host może zmienić język!",
                        ephemeral=True
                    )
                
                # Toggle language
                current_lang = lobby.get('lang', 'en')
                new_lang = 'en' if current_lang == 'pl' else 'pl'
                lobby['lang'] = new_lang
                lobby['last_activity'] = time.time()
                
                await interaction.response.defer()
                embed, view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, host)
                await interaction.message.edit(embed=embed, view=view)
            
            elif action == 'start':
                if uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can start the game!", ephemeral=True)
                if len(lobby['players']) < lobby['minPlayers']:
                    return await interaction.response.send_message(f"Need at least {lobby['minPlayers']} players!", ephemeral=True)
                
                del self.bot.active_lobbies[lobby_id]
                game_id = f"uno_game_{interaction.channel_id}_{lobby['hostId']}_{int(time.time())}"
                
                # Check variant and create appropriate deck
                variant = lobby.get('settings', {}).get('variant', 'classic')
                card_mapping = None  # For UNO Flip random card mapping
                
                if variant == 'flip':
                    # UNO Flip: Start with light side and random card pairings
                    deck, card_mapping = self.flip_handler.create_double_sided_flip_deck()
                    current_side = 'light'
                elif variant == 'no_mercy':
                    # UNO No Mercy: Hardcore chaos mode
                    deck = self.no_mercy_handler.create_no_mercy_deck()
                    current_side = None
                elif variant == 'no_mercy_plus':
                    # UNO No Mercy+: No Mercy + Expansion Pack
                    deck = self.no_mercy_plus_handler.create_no_mercy_plus_deck()
                    current_side = None
                else:
                    # UNO Classic
                    deck = uno_logic.create_deck()
                    uno_logic.shuffle_deck(deck)
                    current_side = None
                
                starting_cards = lobby.get('settings', {}).get('starting_cards', 7)
                hands = {}
                discard = []  # Initialize discard pile for reshuffle function
                for player_id in lobby['players']:
                    if variant != 'flip':
                        uno_logic.reshuffle_discard_into_deck(deck, discard)
                    hands[player_id] = uno_logic.draw_cards(deck, starting_cards)
                
                top_card = deck.pop()
                while top_card['color'] == 'wild':
                    deck.insert(0, top_card)
                    if variant != 'flip':
                        uno_logic.shuffle_deck(deck)
                    top_card = deck.pop()
                
                game_state = {
                    'game_id': game_id,
                    'players': lobby['players'],
                    'hands': hands,
                    'deck': deck,
                    'discard': [top_card],
                    'current_turn': 0,
                    'direction': 1,
                    'current_color': top_card['color'],
                    'current_side': current_side,  # For Flip: 'light' or 'dark'
                    'draw_stack': 0,
                    'messageId': lobby.get('messageId'),
                    'start_time': time.time(),
                    'last_activity': time.time(),
                    'hand_messages': {},
                    'settings': lobby.get('settings', {}),
                    'selected_cards': {},
                    'original_players': lobby['players'].copy(),  # Track all players for multiplayer detection
                    'bot_names': lobby.get('bot_names', {}),  # Nazwy botów
                    'lang': lobby.get('lang', 'en'),  # Język z lobby
                    'guild_id': lobby.get('guild_id')  # ID serwera Discord
                }
                
                # Add card mapping for UNO Flip
                if card_mapping:
                    game_state['card_mapping'] = card_mapping
                
                # Initialize coins for No Mercy+
                if variant == 'no_mercy_plus':
                    game_state['coins'] = self.no_mercy_plus_handler.initialize_player_coins(lobby['players'])
                
                self.bot.active_games[game_id] = game_state
                
                current_player = game_state['players'][game_state['current_turn']]
                uno_back = self.get_uno_back_emoji()
                
                embed, card_file = self.create_uno_game_embed(game_state)
                embed.title = f"{uno_back} UNO - Gra rozpoczęta!"
                
                settings = lobby.get('settings', {})
                settings_info = []
                lang = self.get_lang(lobby)
                
                settings_info.append(f"🃏 {self.t('settings.cards_start_label', lang=lang)}: {settings.get('starting_cards', 7)} {self.t('messages.cards', lang=lang)}")
                
                if settings.get('stack_plus_two'):
                    settings_info.append(self.t('lobby.stack_plus_two_label', lang=lang))
                if settings.get('stack_plus_four'):
                    settings_info.append(self.t('lobby.stack_plus_four_label', lang=lang))
                if settings.get('stack_combined'):
                    settings_info.append(self.t('lobby.stack_combined_label', lang=lang))
                if settings.get('stack_colors'):
                    settings_info.append(self.t('lobby.stack_colors_label', lang=lang))
                if settings.get('stack_numbers'):
                    settings_info.append(self.t('lobby.stack_numbers_label', lang=lang))
                
                if settings.get('auto_draw'):
                    settings_info.append(self.t('lobby.auto_draw_label', lang=lang))
                if settings.get('draw_until_play'):
                    settings_info.append(self.t('lobby.draw_until_play_label', lang=lang))
                if settings.get('skip_after_draw', True):
                    settings_info.append(self.t('lobby.skip_after_draw_on_label', lang=lang))
                else:
                    settings_info.append(self.t('lobby.skip_after_draw_off_label', lang=lang))
                if settings.get('must_play'):
                    settings_info.append(self.t('lobby.must_play_label', lang=lang))
                
                if settings.get('seven_zero'):
                    settings_info.append(self.t('lobby.seven_zero_label', lang=lang))
                if settings.get('jump_in'):
                    settings_info.append(self.t('lobby.jump_in_label', lang=lang))
                if settings.get('uno_callout'):
                    settings_info.append(self.t('lobby.uno_callout_label', lang=lang))
                if settings.get('first_win', True):
                    settings_info.append(self.t('lobby.first_win_label', lang=lang))
                else:
                    settings_info.append(self.t('lobby.last_standing_label', lang=lang))
                
                if settings_info:
                    embed.add_field(name=f"⚙️ {self.t('lobby.active_rules', lang=lang)}", value="\n".join(settings_info), inline=False)
                
                game_state['settings'] = settings
                
                view = self.create_uno_legacy_game_view(game_id, game_state, current_player)
                
                files = [card_file] if card_file else []
                await interaction.response.edit_message(embed=embed, view=view, attachments=files)
                
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game_state)
        
        # --- UNO: USTAWIENIA LOBBY ---
        if cid.startswith('uno_setting_') or cid.startswith('uno_variant_'):
            uno_back = self.get_uno_back_emoji()
            
            # Handle variant select
            if cid.startswith('uno_setting_variant_'):
                # Format: uno_setting_variant_LOBBY_ID
                lobby_id = cid[len('uno_setting_variant_'):]
                variant_type = interaction.data['values'][0]  # 'classic' or 'flip'
                
                lobby = self.bot.active_lobbies.get(lobby_id)
                if not lobby:
                    return await interaction.response.send_message("Lobby nieaktywne.", ephemeral=True)
                
                if uid != lobby['hostId']:
                    return await interaction.response.send_message("Only the host can change settings!", ephemeral=True)
                
                if 'settings' not in lobby:
                    lobby['settings'] = {}
                
                lobby['settings']['variant'] = variant_type
                
                # Auto-configure settings for Flip mode
                if variant_type == 'flip':
                    # Enable stacking for +1, +5 and combined in Flip
                    lobby['settings']['stack_plus_two'] = False  # No +2 in Flip
                    lobby['settings']['stack_plus_four'] = False  # No +4 in Flip
                    lobby['settings']['stack_flip_draw'] = True  # Stack +1 and +5
                    lobby['settings']['stack_combined'] = True  # Allow +1 on +5 and vice versa
                    lobby['settings']['seven_zero'] = False  # Disable 7-0 Rule in Flip
                else:
                    # Classic mode defaults
                    lobby['settings']['stack_plus_two'] = True
                    lobby['settings']['stack_plus_four'] = False
                    lobby['settings']['stack_flip_draw'] = False
                    lobby['settings']['stack_combined'] = False
                
                # Show updated settings
                lang = self.get_lang(lobby)
                settings_view, settings_desc = self.create_uno_settings_view_and_description(lobby_id, lobby['settings'], lang=lang)
                await interaction.response.edit_message(
                    content=f"⚙️ **{self.t('settings.title', lang=lang)}**\n\n{settings_desc}",
                    view=settings_view
                )
                
                # Update main lobby message to reflect variant change
                try:
                    if lobby.get('messageId'):
                        lobby_embed, lobby_view = self.create_uno_lobby_embed_and_view(lobby, lobby_id, None)
                        msg = interaction.channel.get_partial_message(lobby['messageId'])
                        await msg.edit(embed=lobby_embed, view=lobby_view)
                except Exception:
                    pass
                
                return
            
            # Parse setting name and lobby ID
            setting_name = None
            lobby_id = None
            
            # Check for starting cards cycle button
            if cid.startswith('uno_setting_cards_cycle_'):
                lobby_id = cid[len('uno_setting_cards_cycle_'):]
                setting_name = 'starting_cards'
                is_number_setting = True
                is_cycle = True
            elif cid.startswith('uno_setting_cards_'):
                parts = cid[len('uno_setting_cards_'):].split('_')
                cards_count = int(parts[0])
                lobby_id = '_'.join(parts[1:])
                setting_name = 'starting_cards'
                is_number_setting = True
                is_cycle = False
            else:
                is_cycle = False
                # Map all boolean settings
                setting_map = {
                    'uno_setting_stack_plus_two_': 'stack_plus_two',
                    'uno_setting_stack_plus_four_': 'stack_plus_four',
                    'uno_setting_stack_flip_draw_': 'stack_flip_draw',
                    'uno_setting_stack_combined_': 'stack_combined',
                    'uno_setting_stack_colors_': 'stack_colors',
                    'uno_setting_stack_numbers_': 'stack_numbers',
                    'uno_setting_auto_draw_': 'auto_draw',
                    'uno_setting_draw_until_play_': 'draw_until_play',
                    'uno_setting_skip_after_draw_': 'skip_after_draw',
                    'uno_setting_must_play_': 'must_play',
                    'uno_setting_uno_callout_': 'uno_callout',
                    'uno_setting_seven_zero_': 'seven_zero',
                    'uno_setting_jump_in_': 'jump_in',
                    'uno_setting_first_win_': 'first_win',
                    'uno_setting_elimination_': 'elimination'
                }
                
                is_number_setting = False
                for prefix, name in setting_map.items():
                    if cid.startswith(prefix):
                        setting_name = name
                        lobby_id = cid[len(prefix):]
                        break
                
                if not setting_name:
                    return await interaction.response.send_message("Nieznane ustawienie.", ephemeral=True)
            
            lobby = self.bot.active_lobbies.get(lobby_id)
            if not lobby:
                return await interaction.response.send_message("Lobby nieaktywne.", ephemeral=True)
            
            if uid != lobby['hostId']:
                return await interaction.response.send_message("Only the host can change settings!", ephemeral=True)
            
            # Settings should already exist from commands/uno.py
            if 'settings' not in lobby:
                return await interaction.response.send_message("Error: lobby settings missing.", ephemeral=True)
            
            # Update setting
            if is_number_setting:
                if is_cycle:
                    current = lobby['settings'].get('starting_cards', 7)
                    cycle_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                    try:
                        current_idx = cycle_values.index(current)
                        next_idx = (current_idx + 1) % len(cycle_values)
                        lobby['settings']['starting_cards'] = cycle_values[next_idx]
                    except ValueError:
                        lobby['settings']['starting_cards'] = 1
                else:
                    lobby['settings']['starting_cards'] = cards_count
            else:
                # Toggle setting
                new_value = not lobby['settings'].get(setting_name, False)
                
                # Sprawdzenie: nie pozwól wyłączyć ostatniej opcji dobierania
                draw_options = ['auto_draw', 'draw_until_play', 'skip_after_draw', 'must_play']
                if setting_name in draw_options and not new_value:
                    # Sprawdź czy po wyłączeniu zostanie jakaś inna włączona
                    remaining_active = any(
                        lobby['settings'].get(opt, False) 
                        for opt in draw_options 
                        if opt != setting_name
                    )
                    if not remaining_active:
                        # Nie pozwól wyłączyć ostatniej opcji
                        await interaction.response.send_message(
                            "❌ Przynajmniej jedna opcja dobierania musi być aktywna!",
                            ephemeral=True
                        )
                        return
                
                lobby['settings'][setting_name] = new_value
                
                # Logika wzajemnego wykluczania dla opcji dobierania
                if new_value:  # Tylko gdy włączamy opcję
                    if setting_name == 'auto_draw':
                        # Auto dobierz wyklucza: "Dobieraj aż", "Musisz zagrać"
                        lobby['settings']['draw_until_play'] = False
                        lobby['settings']['must_play'] = False
                    elif setting_name == 'draw_until_play':
                        # Dobieraj aż wyklucza: "Auto dobierz", "Pomin po dobieraniu"
                        lobby['settings']['auto_draw'] = False
                        lobby['settings']['skip_after_draw'] = False
                    elif setting_name == 'skip_after_draw':
                        # Pomin po dobieraniu wyklucza: "Dobieraj aż"
                        lobby['settings']['draw_until_play'] = False
                    elif setting_name == 'must_play':
                        # Musisz zagrać wyklucza: "Auto dobierz"
                        lobby['settings']['auto_draw'] = False
            
            # Recreate settings menu
            lang = self.get_lang(lobby)
            settings_view, settings_desc = self.create_uno_settings_view_and_description(lobby_id, lobby['settings'], lang=lang)
            
            await interaction.response.edit_message(
                content=f"⚙️ **{self.t('settings.title', lang=lang)}**\n\n{settings_desc}",
                view=settings_view
            )
            
            # Update lobby message
            try:
                if lobby.get('messageId'):
                    # Dummy host object - we only need it for the function signature
                    lobby_embed, _ = self.create_uno_lobby_embed_and_view(lobby, lobby_id, None)
                    msg = interaction.channel.get_partial_message(lobby['messageId'])
                    await msg.edit(embed=lobby_embed)
            except Exception:
                pass
        
        # --- UNO: WIDOK STOŁU ---
        if cid.startswith('uno_table_'):
            game_id = cid[len('uno_table_'):]
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            lang = self.get_lang(game)
            
            # Create table info embed
            embed = discord.Embed(
                title=self.t('game.table_title', lang=lang),
                color=0x5865F2
            )
            
            # Show all players and their card counts
            player_info = ""
            current_player = game['players'][game['current_turn']]
            for p in game['players']:
                is_turn = p == current_player
                player_name = self.get_bot_display_name(p, game)
                card_count = len(game['hands'][p])
                turn_indicator = "📍" if is_turn else ""
                player_info += f"{player_name} | **{card_count} {self.t('messages.cards', lang=lang)}** {turn_indicator}\n"
            
            embed.add_field(name="", value=player_info, inline=False)
            
            # Deck info
            deck_info = f"**{self.t('game.decks', lang=lang)}: 1(108) | {self.t('game.remaining', lang=lang)}: {len(game['deck'])} | {self.t('game.discarded', lang=lang)}: {len(game['discard'])}**"
            embed.add_field(name="", value=deck_info, inline=False)
            embed.set_footer(text=self.t('game.ephemeral_footer', lang=lang))
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # --- UNO SHOW OPPONENTS (FLIP MODE) ---
        if cid.startswith('uno_show_opponents_'):
            game_id = cid[len('uno_show_opponents_'):]
            await self.flip_handler.show_opponents_cards(interaction, game_id)
            return
        
        # --- UNO SELECT COIN (No Mercy+) ---
        if cid.startswith('uno_select_coin_'):
            # Parse: uno_select_coin_{game_id}:choice
            rest = cid[len('uno_select_coin_'):]
            parts = rest.split(':', 1)
            game_id = parts[0]
            choice = parts[1] if len(parts) > 1 else 'mercy'
            
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            uid = str(interaction.user.id)
            if uid not in game['hands']:
                return await interaction.response.send_message(self.t('messages.not_player', lang='en'), ephemeral=True)
            
            coins = game.get('coins', {})
            if uid not in coins:
                return await interaction.response.send_message("❌ Nie masz monety!", ephemeral=True)
            
            # Zapisz wybór gracza
            coins[uid]['type'] = choice
            coins[uid]['selected'] = True
            
            # Wyślij potwierdzenie i pokaż rękę
            hand = game['hands'][uid]
            top_card = game['discard'][-1]
            
            mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
            coin_filename = 'mercy_coin.png' if choice == 'mercy' else 'nomercy_coin.png'
            emoji_id = mapping.get(coin_filename)
            coin_emoji = f"<:{coin_filename.replace('.png', '')}:{emoji_id}>" if emoji_id else "🪙"
            coin_name = self.t(f'coins.{choice}', lang=self.get_lang(game))
            
            lang = self.get_lang(game)
            embed = discord.Embed(
                title=f"{self.get_uno_back_emoji()} {self.t('hand.title', lang=lang)}",
                description=f"✅ **{self.t('coins.selected', lang=lang)}: {coin_emoji} {coin_name}**\n\n{self.t('coins.plan_moves', lang=lang)}",
                color=0x2B2D31
            )
            
            table_card_file = uno_logic.card_to_image(top_card)
            files = []
            if table_card_file:
                files.append(table_card_file)
                embed.set_image(url=f"attachment://{table_card_file.filename}")
            
            view = self.create_uno_hand_view(game_id, game, uid)
            
            await interaction.response.edit_message(embed=embed, view=view, attachments=files)
            return
        
        # --- UNO COIN (No Mercy+) ---
        if cid.startswith('uno_coin_'):
            game_id = cid[len('uno_coin_'):]
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            uid = str(interaction.user.id)
            if uid not in game['hands']:
                lang = self.get_lang(game)
                return await interaction.response.send_message(self.t('messages.not_in_game', lang=lang), ephemeral=True)
            
            coins = game.get('coins', {})
            if uid not in coins:
                lang = self.get_lang(game)
                return await interaction.response.send_message(f"❌ {self.t('coins.no_coin', lang=lang)}", ephemeral=True)
            
            coin_data = coins[uid]
            if coin_data.get('used', False):
                lang = self.get_lang(game)
                return await interaction.response.send_message(f"❌ {self.t('coins.already_used', lang=lang)}", ephemeral=True)
            
            if not coin_data.get('selected', False):
                lang = self.get_lang(game)
                return await interaction.response.send_message(f"❌ {self.t('coins.must_select', lang=lang)}", ephemeral=True)
            
            # Aktywuj wybrany typ monety
            choice = coin_data['type']
            
            if choice == 'mercy':
                # MERCY: Odrzuć całą rękę i dobierz 7 nowych kart
                hand = game['hands'][uid]
                old_count = len(hand)
                
                # Odrzuć wszystkie karty
                game['discard'].extend(hand)
                hand.clear()
                
                # Dobierz 7 nowych kart
                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                new_cards = uno_logic.draw_cards(game['deck'], 7)
                hand.extend(new_cards)
                
                # Oznacz monetę jako użytą
                coin_data['used'] = True
                
                # Update game board
                current_player = game['players'][game['current_turn']]
                embed_game, file_game = self.create_uno_game_embed(game)
                view_game = self.create_uno_legacy_game_view(game_id, game, current_player)
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [file_game] if file_game else []
                        await msg.edit(embed=embed_game, view=view_game, attachments=files)
                except Exception:
                    pass
                
                # Odśwież rękę gracza
                hand_messages = game.get('hand_messages', {})
                if uid in hand_messages:
                    try:
                        old_interaction, old_msg = hand_messages[uid]
                        top_card = game['discard'][-1]
                        lang = self.get_lang(game)
                        
                        embed_hand = discord.Embed(
                            title=f"{self.get_uno_back_emoji()} {self.t('hand.title', lang=lang)}",
                            description=f"💙 **{self.t('coins.mercy', lang=lang).upper()} {self.t('coins.used', lang=lang)}!** {self.t('coins.discarded', lang=lang)} **{old_count} {self.t('messages.cards', lang=lang)}** {self.t('coins.and_drew', lang=lang)} **7 {self.t('coins.new', lang=lang)}** {self.t('messages.cards', lang=lang)}!\n\n{self.t('coins.plan_moves', lang=lang)}",
                            color=0x2B2D31
                        )
                        
                        table_card_file = uno_logic.card_to_image(top_card)
                        files_hand = [table_card_file] if table_card_file else []
                        if table_card_file:
                            embed_hand.set_image(url=f"attachment://{table_card_file.filename}")
                        
                        view_hand = self.create_uno_hand_view(game_id, game, uid)
                        await old_msg.edit(embed=embed_hand, view=view_hand, attachments=files_hand)
                    except Exception:
                        pass
                
                await interaction.response.send_message(
                    f"💙 **{self.t('messages.mercy_used', lang=lang)}**\n\n"
                    f"{self.t('messages.discarded_cards', lang=lang)} **{old_count} {self.t('messages.cards', lang=lang)}** {self.t('messages.and_drew_new', lang=lang)} **7 {self.t('messages.new_cards', lang=lang)}**",
                    ephemeral=True
                )
                
                # Wyślij publiczny komunikat do kanału
                try:
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    mercy_id = mapping.get('mercy_coin.png')
                    mercy_emoji = f"<:mercy_coin:{mercy_id}>" if mercy_id else "💙"
                    lang = self.get_lang(game)
                    await interaction.channel.send(
                        f"{mercy_emoji} <@{uid}> {self.t('coins.used_mercy', lang=lang)}! {self.t('coins.discarded', lang=lang)} **{old_count} {self.t('messages.cards', lang=lang)}** {self.t('coins.and_drew', lang=lang)} **7 {self.t('coins.new', lang=lang)}**!",
                        silent=True
                    )
                except Exception:
                    pass
            else:
                # NO MERCY: Zaznacz że następna karta dobierająca będzie podwojona
                coin_data['pending_no_mercy'] = True
                lang = self.get_lang(game)
                await interaction.response.send_message(
                    f"💀 **{self.t('coins.nomercy_activated', lang=lang)}!**\n\n"
                    f"⚡ {self.t('coins.nomercy_next_effect', lang=lang)}",
                    ephemeral=True
                )
                
                # Wyślij publiczny komunikat do kanału
                try:
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    nomercy_id = mapping.get('nomercy_coin.png')
                    nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                    lang = self.get_lang(game)
                    await interaction.channel.send(
                        f"{nomercy_emoji} <@{uid}> {self.t('coins.activated_nomercy', lang=lang)}! {self.t('coins.nomercy_public', lang=lang)}",
                        silent=True
                    )
                except Exception:
                    pass
            return
        
        # --- UNO SHOW HAND ---
        if cid.startswith('uno_show_hand_'):
            uno_back = self.get_uno_back_emoji()
            game_id = cid[len('uno_show_hand_'):]
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            # Ensure uid is string (might have been overwritten)
            uid = str(interaction.user.id)
            
            if uid not in game['hands']:
                return await interaction.response.send_message(self.t('messages.not_player', lang='en'), ephemeral=True)
            
            # Check if player needs to handle DRAW COLOR selection
            if 'pending_draw_color' in game and game['pending_draw_color']['player'] == uid:
                
                draw_color_data = game['pending_draw_color']
                card = draw_color_data['card']
                initiator = draw_color_data['initiator']
                initiator_display = self.get_bot_display_name(initiator, game)
                
                # Get variant to determine color selection
                variant = game.get('settings', {}).get('variant', 'classic')
                
                # For Flip, use current_side; for others (Classic, No Mercy), always use light side colors
                if variant == 'flip':
                    current_side = game.get('current_side', 'light')
                    color_side = current_side
                else:
                    color_side = 'light'  # Always use standard colors for Classic and No Mercy
                
                # Get card name based on variant
                card_name = "WILD COLOR ROULETTE" if variant == 'no_mercy' else "WILD DRAW COLOR"
                
                # Show color selection for draw_color
                hand_embed = discord.Embed(
                    title=f"🎨 {card_name}!",
                    description=f"{initiator_display} {self.t('messages.played_wild_draw_color', lang=lang)} **{card_name}**!\n\n⬇️ **{self.t('messages.select_color_draw_until', lang=lang)}**",
                    color=0xe74c3c
                )
                
                wild_card_file = uno_logic.card_to_image(card)
                if wild_card_file:
                    hand_embed.set_image(url=f"attachment://{wild_card_file.filename}")
                    files = [wild_card_file]
                else:
                    files = []
                
                color_view = self.create_color_select_view(game_id, side=color_side, lang=self.get_lang(game))
                
                await interaction.response.send_message(embed=hand_embed, view=color_view, files=files, ephemeral=True)
                return
            
            hand = game['hands'][uid]
            top_card = game['discard'][-1]
            current_color = game['current_color']
            
            # Check if this is coin selection screen for No Mercy+
            variant = game.get('settings', {}).get('variant', 'classic')
            if variant == 'no_mercy_plus':
                coins = game.get('coins', {})
                if uid in coins and not coins[uid].get('selected', False):
                    # Show coin selection embed
                    mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                    mercy_id = mapping.get('mercy_coin.png')
                    nomercy_id = mapping.get('nomercy_coin.png')
                    mercy_emoji = f"<:mercy_coin:{mercy_id}>" if mercy_id else "💙"
                    nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                    lang = self.get_lang(game)
                    
                    embed = discord.Embed(
                        title=f"🪙 {self.t('coins.choose_title', lang=lang)}",
                        description=(
                            f"{self.t('coins.choose_desc', lang=lang)}\n\n"
                            f"{mercy_emoji} **{self.t('coins.mercy_name', lang=lang)}**\n"
                            f"└ {self.t('coins.mercy_desc', lang=lang)}\n"
                            f"└ {self.t('coins.mercy_when', lang=lang)}\n\n"
                            f"{nomercy_emoji} **{self.t('coins.nomercy_name', lang=lang)}**\n"
                            f"└ {self.t('coins.nomercy_desc', lang=lang)}\n"
                            f"└ {self.t('coins.nomercy_when', lang=lang)}\n\n"
                            f"⚠️ **{self.t('coins.choose_warning', lang=lang)}**"
                        ),
                        color=0xFFD700
                    )
                    
                    view = self.create_uno_hand_view(game_id, game, uid)
                    
                    try:
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                        return
                    except discord.InteractionResponded:
                        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                        return
            
            lang = self.get_lang(game)
            embed = discord.Embed(
                title=f"{uno_back} {self.t('hand.title', lang=lang)}",
                description=self.t('coins.plan_moves', lang=lang),
                color=0x2B2D31
            )
            
            # Get playable cards info
            settings = game.get('settings', {})
            current_player = game['players'][game['current_turn']]
            draw_stack = game.get('draw_stack', 0)
            playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
            
            # AUTO-DRAW: If auto_draw enabled, current turn, and no playable cards
            
            # Don't auto-draw if there's a draw stack (player must accept penalty or counter)
            if settings.get('auto_draw', False) and uid == current_player and not playable and draw_stack == 0:
                # Automatically draw a card
                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                drawn = uno_logic.draw_cards(game['deck'], 1)
                if drawn:
                    hand.extend(drawn)
                    lang = self.get_lang(game)
                    embed.add_field(
                        name=f"🤖 {self.t('coins.auto_draw_title', lang=lang)}",
                        value=f"{self.t('coins.auto_draw_desc', lang=lang)}\n\n{self.t('coins.you_now_have', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}**",
                        inline=False
                    )
                    # Clear UNO called status
                    if 'uno_called' in game and uid in game['uno_called']:
                        game['uno_called'].discard(uid)
                    # Pass turn automatically
                    game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                    # Update main game display
                    try:
                        if game.get('messageId'):
                            current_player_new = game['players'][game['current_turn']]
                            embed_game, card_file_game = self.create_uno_game_embed(game)
                            view_game = self.create_uno_legacy_game_view(game_id, game, current_player_new)
                            msg_game = interaction.channel.get_partial_message(game['messageId'])
                            files_game = [card_file_game] if card_file_game else []
                            await msg_game.edit(embed=embed_game, view=view_game, attachments=files_game)
                    except Exception:
                        pass
                    # Odśwież opponent_views dla trybu Flip
                    await self.refresh_opponent_views(game)
                    # Odśwież rękę gracza po auto-dobieraniu (jeśli istnieje hand_message)
                    hand_messages = game.get('hand_messages', {})
                    if uid in hand_messages:
                        try:
                            old_interaction, old_msg = hand_messages[uid]
                            embed_hand, card_file_hand = self.create_uno_hand_embed(game_id, game, uid)
                            view_hand = self.create_uno_hand_view(game_id, game, uid)
                            files_hand = [card_file_hand] if card_file_hand else []
                            await old_msg.edit(embed=embed_hand, view=view_hand, attachments=files_hand)
                        except Exception:
                            pass
                    # Check if next player is BOT
                    next_player = game['players'][game['current_turn']]
                    if next_player.startswith('BOT_'):
                        await asyncio.sleep(1.5)
                        await self.play_bot_uno_turn(interaction.channel, game_id, game)
            
            # Show table card with emoji as image
            table_card_file = uno_logic.card_to_image(top_card)
            files = []
            if table_card_file:
                files.append(table_card_file)
                embed.set_image(url=f"attachment://{table_card_file.filename}")
            
            # Create hand view with emoji card buttons
            view = self.create_uno_hand_view(game_id, game, uid)
            
            try:
                await interaction.response.send_message(embed=embed, view=view, files=files, ephemeral=True)
                # Store reference to this message for future updates
                try:
                    msg = await interaction.original_response()
                    game.setdefault('hand_messages', {})[uid] = (interaction, msg)
                except Exception:
                    pass
            except discord.InteractionResponded:
                # Jeśli już odpowiedziano na interakcję (np. przez auto-dobieranie), użyj followup
                await interaction.followup.send(embed=embed, view=view, files=files, ephemeral=True)
        
        # --- UNO HAND NAVIGATION (Previous/Next Page) ---
        if cid.startswith('uno_hand_prev_') or cid.startswith('uno_hand_next_'):
            uno_back = self.get_uno_back_emoji()
            
            # Parse: uno_hand_prev_{game_id}_{current_page} or uno_hand_next_{game_id}_{current_page}
            is_next = cid.startswith('uno_hand_next_')
            prefix = 'uno_hand_next_' if is_next else 'uno_hand_prev_'
            rest = cid[len(prefix):]
            parts = rest.rsplit('_', 1)
            game_id = parts[0]
            current_page = int(parts[1]) if len(parts) > 1 else 0
            
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive_short', lang='pl'), ephemeral=True)
            
            # Ensure uid is string
            uid = str(interaction.user.id)
            
            if uid not in game['hands']:
                lang = self.get_lang(game)
                return await interaction.response.send_message(self.t('messages.not_player', lang=lang), ephemeral=True)
            
            # Calculate new page
            new_page = current_page + 1 if is_next else current_page - 1
            
            hand = game['hands'][uid]
            top_card = game['discard'][-1]
            current_color = game['current_color']
            
            # Create embed
            lang = self.get_lang(game)
            embed = discord.Embed(
                title=f"{uno_back} {self.t('hand.title', lang=lang)}",
                description=self.t('coins.plan_moves', lang=lang),
                color=0x2B2D31
            )
            
            # Show table card with emoji as image
            table_card_file = uno_logic.card_to_image(top_card)
            files = []
            if table_card_file:
                files.append(table_card_file)
                embed.set_image(url=f"attachment://{table_card_file.filename}")
            
            # Create hand view with new page
            view = self.create_uno_hand_view(game_id, game, uid, page=new_page)
            
            await interaction.response.edit_message(embed=embed, view=view, attachments=files)
        
        # --- UNO COLOR SELECT ---
        if cid.startswith('uno_color_'):
            uno_back = self.get_uno_back_emoji()
            # Format: uno_color_{game_id}_{color}
            parts = cid.split('_')
            color = parts[-1]  # Last part is color
            game_id = "_".join(parts[2:-1])  # Everything between 'uno_color_' and color
            
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.edit_message(content=self.t('messages.game_ended', lang='pl'), view=None)
            
            game['last_activity'] = time.time()  # Aktualizuj aktywność
            
            # Check if this is DRAW COLOR selection (next player choosing)
            if 'pending_draw_color' in game and game['pending_draw_color']['player'] == uid:
                
                draw_color_data = game['pending_draw_color']
                initiator = draw_color_data['initiator']
                del game['pending_draw_color']
                
                # Set chosen color
                game['current_color'] = color
                
                # Player draws until they get a card of chosen color
                hand = game['hands'][uid]
                drawn_cards = []
                
                while True:
                    uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                    drawn = uno_logic.draw_cards(game['deck'], 1)
                    if not drawn:
                        break
                    drawn_cards.extend(drawn)
                    hand.extend(drawn)
                    # Check if drawn card matches chosen color
                    if drawn[0]['color'] == color:
                        break
                    # Safety limit to prevent infinite loop
                    if len(drawn_cards) >= 25:
                        break
                
                # Clear UNO called status
                if 'uno_called' in game and uid in game['uno_called']:
                    game['uno_called'].discard(uid)
                
                # Check for elimination after draw_color
                if await self.check_elimination(game_id, game, uid, interaction.channel):
                    return  # Player was eliminated
                
                # Notify player
                lang = self.get_lang(game)
                await interaction.response.edit_message(
                    content=self.format_color_selected_message(color, f"\n\n{self.format_draw_cards_message(len(drawn_cards), lang=lang)}", lang),
                    embed=None,
                    view=None
                )
                
                # Notify channel
                lang = self.get_lang(game)
                variant = game.get('settings', {}).get('variant', 'classic')
                card_name = "WILD COLOR ROULETTE" if variant == 'no_mercy' else "WILD DRAW COLOR"
                initiator_display = self.get_bot_display_name(initiator, game)
                await interaction.channel.send(
                    f"🎨 <@{uid}> {self.t('messages.player_selected_color', lang=lang)} **{color.upper()}** {self.t('messages.and', lang=lang)} {self.t('messages.drew_cards_prefix', lang=lang).lower()} **{len(drawn_cards)} {self.t('messages.cards', lang=lang)}** ({card_name} {self.t('messages.from', lang='pl' if lang=='pl' else 'en')} {initiator_display})!",
                    delete_after=8
                )
                
                # Update game display
                current_player = game['players'][game['current_turn']]
                embed, card_file = self.create_uno_game_embed(game)
                view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [card_file] if card_file else []
                        await msg.edit(embed=embed, view=view, attachments=files)
                except Exception:
                    pass
                
                # Odśwież opponent_views dla trybu Flip
                await self.refresh_opponent_views(game)
                
                # Auto-refresh hand for current player
                await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                
                # Bot turn if current player is BOT
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                
                return
            
            # Check if this is WILD DISCARD ALL color selection
            if 'pending_wild_discard_all' in game and game['pending_wild_discard_all']['player'] == uid:
                
                discard_data = game['pending_wild_discard_all']
                del game['pending_wild_discard_all']
                
                # Set chosen color
                game['current_color'] = color
                
                # Discard all cards of chosen color
                lang = self.get_lang(game)
                hand = game['hands'][uid]
                cards_to_discard = [c for c in hand if c['color'] == color]
                
                if cards_to_discard:
                    # Remove from hand
                    hand[:] = [c for c in hand if c['color'] != color]
                    # Add to discard pile
                    game['discard'].extend(cards_to_discard)
                    
                    discard_msg = f"✅ {self.t('messages.selected_color', lang=lang)}: {uno_logic.COLOR_EMOJIS[color]}\n\n🗑️ {self.t('messages.discarded_all_color', lang=lang)} **{len(cards_to_discard)} {self.t('messages.cards', lang=lang)}**!"
                else:
                    discard_msg = f"✅ {self.t('messages.selected_color', lang=lang)}: {uno_logic.COLOR_EMOJIS[color]}\n\n⚠️ {self.t('messages.no_cards_of_color', lang=lang)}"
                
                # Clear UNO called status if needed
                if 'uno_called' in game and uid in game['uno_called'] and len(hand) != 1:
                    game['uno_called'].discard(uid)
                
                # Check if player won
                if len(hand) == 0:
                    await interaction.response.edit_message(content=discard_msg, embed=None, view=None)
                    channel = interaction.channel
                    if await self.handle_player_win(game_id, game, uid, interaction, channel):
                        return  # Game ended
                    
                    # Game continues (last standing mode)
                    current_player = game['players'][game['current_turn']]
                    embed, card_file = self.create_uno_game_embed(game)
                    view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                # Notify player
                await interaction.response.edit_message(content=discard_msg, embed=None, view=None)
                
                # Notify channel
                player_display = self.get_bot_display_name(uid, game)
                await interaction.channel.send(
                    f"🗑️ {player_display} {self.t('messages.used_wild_discard', lang=lang)} **WILD DISCARD ALL** {self.t('messages.and', lang=lang)} {self.t('messages.discarded_lowercase', lang=lang)} **{len(cards_to_discard)} {self.t('messages.cards', lang=lang)} {self.t('messages.color', lang=lang).lower()} {uno_logic.COLOR_EMOJIS[color]}**!",
                    delete_after=8
                )
                
                # Move turn
                game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                
                # Update display
                current_player = game['players'][game['current_turn']]
                embed, card_file = self.create_uno_game_embed(game)
                view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [card_file] if card_file else []
                        await msg.edit(embed=embed, view=view, attachments=files)
                except Exception:
                    pass
                
                # Refresh hand or trigger bot
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                
                return
            
            # Check if this is WILD SUDDEN DEATH color selection
            if 'pending_wild_sudden_death' in game and game['pending_wild_sudden_death']['player'] == uid:
                
                sudden_data = game['pending_wild_sudden_death']
                del game['pending_wild_sudden_death']
                
                # Set chosen color
                game['current_color'] = color
                
                # Execute sudden death effect
                draws = self.no_mercy_plus_handler.handle_wild_sudden_death(game)
                
                # Notify player
                lang = self.get_lang(game)
                await interaction.response.edit_message(
                    content=self.format_color_selected_message(color, f"\n\n💀 SUDDEN DEATH {self.t('messages.activated', lang=lang)}!", lang),
                    embed=None,
                    view=None
                )
                
                # Notify channel
                player_name = self.get_bot_display_name(uid, game)
                draw_text = "\n".join([
                    f"{self.get_bot_display_name(pid, game)}: +{count}" 
                    for pid, count in draws.items() if count > 0
                ])
                await interaction.channel.send(
                    f"💀⚡ **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} SUDDEN DEATH!**\n\n"
                    f"🎨 {self.t('messages.selected_color', lang=lang)}: **{color.upper()}**\n\n"
                    f"{self.t('messages.all_draw_24', lang=lang)}\n\n{draw_text}",
                    silent=True
                )
                
                # Check for eliminations
                for pid in list(game['players']):
                    if await self.check_elimination(game_id, game, pid, interaction.channel):
                        continue
                
                # Move turn
                game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                
                # Update display
                current_player = game['players'][game['current_turn']]
                embed, card_file = self.create_uno_game_embed(game)
                view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [card_file] if card_file else []
                        await msg.edit(embed=embed, view=view, attachments=files)
                except Exception:
                    pass
                
                # Trigger bot or refresh hand
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                
                return
            
            # Check if this is WILD FINAL ATTACK color selection
            if 'pending_wild_final_attack' in game and game['pending_wild_final_attack']['player'] == uid:
                
                attack_data = game['pending_wild_final_attack']
                del game['pending_wild_final_attack']
                
                # Set chosen color
                game['current_color'] = color
                
                # Execute final attack effect
                next_player_id, main_draw, all_draw, action_count = self.no_mercy_plus_handler.handle_wild_final_attack(game, uid)
                
                player_name = self.get_bot_display_name(uid, game)
                player_hand = game['hands'][uid]
                
                # Show player's hand (reveal cards)
                hand_emojis = []
                for c in player_hand:
                    emoji = uno_logic.card_to_emoji(c, 'no_mercy_plus')
                    if isinstance(emoji, discord.PartialEmoji):
                        hand_emojis.append(f"<:{emoji.name}:{emoji.id}>")
                    else:
                        hand_emojis.append(str(emoji))
                hand_display = " ".join(hand_emojis)
                
                # Notify player
                lang = self.get_lang(game)
                await interaction.response.edit_message(
                    content=self.format_color_selected_message(color, f"\n\n⚔️ FINAL ATTACK {self.t('messages.activated', lang=lang)}!", lang),
                    embed=None,
                    view=None
                )
                
                # Notify channel with attack
                try:
                    if all_draw:
                        # MEGA ATTACK (7+ action cards)
                        next_name = self.get_bot_display_name(next_player_id, game)
                        await interaction.channel.send(
                            f"⚔️💥 **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} FINAL ATTACK!**\n\n"
                            f"🎨 {self.t('messages.selected_color', lang=lang)}: **{color.upper()}**\n\n"
                            f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                            f"**{action_count} {self.t('messages.action_wild_cards', lang=lang)}!** (≥7)\n\n"
                            f"💀 **{self.t('messages.mega_attack', lang=lang)}:**\n"
                            f"• {next_name}: +25 {self.t('messages.cards', lang=lang)}\n"
                            f"• {self.t('messages.all_others', lang=lang)}: +5 {self.t('messages.cards', lang=lang)}",
                            silent=True,
                            delete_after=12
                        )
                        # Next player draws 25
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], main_draw)
                        if drawn:
                            game['hands'][next_player_id].extend(drawn)
                        
                        # All others draw 5
                        for pid in game['players']:
                            if pid != uid and pid != next_player_id:
                                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                drawn = uno_logic.draw_cards(game['deck'], 5)
                                if drawn:
                                    game['hands'][pid].extend(drawn)
                    else:
                        # Normal attack
                        next_name = self.get_bot_display_name(next_player_id, game)
                        await interaction.channel.send(
                            f"⚔️ **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} FINAL ATTACK!**\n\n"
                            f"🎨 {self.t('messages.selected_color', lang=lang)}: **{color.upper()}**\n\n"
                            f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                            f"**{action_count} {self.t('messages.action_wild_cards', lang=lang)}**\n\n"
                            f"{next_name} {self.t('messages.draws_cards', lang=lang)} +{action_count} {self.t('messages.cards', lang=lang)}!",
                            silent=True,
                            delete_after=10
                        )
                        # Next player draws
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], main_draw)
                        if drawn:
                            game['hands'][next_player_id].extend(drawn)
                    
                    # Check eliminations
                    for pid in list(game['players']):
                        if await self.check_elimination(game_id, game, pid, interaction.channel):
                            continue
                except Exception:
                    pass
                
                # Update display
                current_player = game['players'][game['current_turn']]
                embed, card_file = self.create_uno_game_embed(game)
                view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [card_file] if card_file else []
                        await msg.edit(embed=embed, view=view, attachments=files)
                except Exception:
                    pass
                
                # Trigger bot or refresh hand
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                
                return
            
            # Set color from pending wild card
            if 'pending_wild' in game and game['pending_wild']['player'] == uid:
                game['current_color'] = color
                pending_data = game['pending_wild']  # Save before deleting
                card = pending_data['card']
                is_multi_select = pending_data.get('multi_select', False)
                effects = pending_data.get('effects', {})
                del game['pending_wild']
                
                await interaction.response.edit_message(
                    content=f"Kolor: {uno_logic.COLOR_EMOJIS[color]}",
                    view=None
                )
                
                # If multi-select, effects already applied - just update display and check bot
                if is_multi_select:
                    # Update display
                    current_player = game['players'][game['current_turn']]
                    embed, card_file = self.create_uno_game_embed(game)
                    view = self.create_uno_legacy_game_view(game_id, game, current_player)
                    
                    try:
                        if game.get('messageId'):
                            msg = interaction.channel.get_partial_message(game['messageId'])
                            files = [card_file] if card_file else []
                            await msg.edit(embed=embed, view=view, attachments=files)
                    except Exception:
                        pass
                    
                    # Auto-refresh hand for next player
                    if not current_player.startswith('BOT_'):
                        await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                    
                    # Bot turn
                    if current_player.startswith('BOT_'):
                        await asyncio.sleep(2)
                        await self.play_bot_uno_turn(interaction.channel, game_id, game)
                    
                    return
                
                # Single-select mode: apply saved effects and continue normal flow
                hand = game['hands'][uid]
                
                # Apply effects that affect turn order
                skip_turn = False
                if effects.get('skip_next'):
                    skip_turn = True
                if effects.get('draw_penalty'):
                    draw_amount = effects['draw_penalty']
                    
                    # Check if player has NO MERCY coin active
                    coins = game.get('coins', {})
                    if uid in coins and coins[uid].get('pending_no_mercy', False):
                        draw_amount *= 2
                        coins[uid]['pending_no_mercy'] = False  # Use it up
                        # Notify about doubled penalty
                        try:
                            lang = self.get_lang(game)
                            mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                            nomercy_id = mapping.get('nomercy_coin.png')
                            nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                            await interaction.channel.send(
                                f"{nomercy_emoji} **{self.t('messages.no_mercy_caps', lang=lang)}!** {self.t('messages.penalty_doubled', lang=lang)}: +{effects['draw_penalty']} → +{draw_amount}!",
                                silent=True,
                                delete_after=8
                            )
                        except Exception:
                            pass
                    
                    game['draw_stack'] = game.get('draw_stack', 0) + draw_amount
                
                if effects.get('reverse'):
                    if len(game['players']) == 2:
                        pass  # Don't change direction, current player keeps turn
                    else:
                        game['direction'] *= -1
                
                # Determine if player can continue (stack colors/numbers)
                can_continue = False
                settings = game.get('settings', {})
                
                # Next turn calculation
                if effects.get('play_again'):
                    pass  # Card 10: Play Again - keep current turn
                elif len(game['players']) == 2 and effects.get('reverse'):
                    pass  # Player keeps turn
                elif skip_turn:
                    game['current_turn'] = (game['current_turn'] + game['direction'] * 2) % len(game['players'])
                elif can_continue:
                    pass  # Player keeps turn
                else:
                    game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                
                # Close color selection message (this is the color button interaction)
                lang = self.get_lang(game)
                try:
                    await interaction.response.edit_message(content=self.format_color_selected_message(color, "", lang), embed=None, view=None)
                except discord.errors.InteractionResponded:
                    # If already responded, use followup
                    try:
                        await interaction.followup.send(content=self.format_color_selected_message(color, "", lang), ephemeral=True)
                    except:
                        pass
                
                # Update hand message with confirmation and updated hand
                hand_msg_data = game.get('hand_messages', {}).get(uid)
                if hand_msg_data:
                    old_interaction, old_message = hand_msg_data
                    lang = self.get_lang(game)
                    
                    # Use helper method to generate effect notes
                    extra_notes = self.format_card_effect_notes(game, effects, can_continue=False, lang=lang)
                    extra_text = "\n" + "\n".join(extra_notes) if extra_notes else ""
                    
                    hand_embed = discord.Embed(
                        title=f"✅ {self.t('messages.wild_card_played', lang=lang)}",
                        description=f"**{self.t('messages.selected_color', lang=lang)}:** {uno_logic.COLOR_EMOJIS[color]}{extra_text}\n\n{self.t('messages.you_have_x_cards', lang=lang)} **{len(hand)} {self.t('messages.cards_on_hand', lang=lang)}**",
                        color=0x2ecc71
                    )
                    
                    hand_view = self.create_uno_hand_view(game_id, game, uid)
                    
                    try:
                        await old_message.edit(embed=hand_embed, view=hand_view)
                    except:
                        pass
                
                # Update main game display
                current_player = game['players'][game['current_turn']]
                embed, card_file = self.create_uno_game_embed(game)
                view = self.create_uno_legacy_game_view(game_id, game, current_player)
                
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files = [card_file] if card_file else []
                        await msg.edit(embed=embed, view=view, attachments=files)
                except Exception:
                    pass
                
                # Odśwież opponent_views dla trybu Flip
                await self.refresh_opponent_views(game)
                
                # Auto-refresh hand for next player
                if not current_player.startswith('BOT_') and current_player != uid:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                
                # Bot turn
                if current_player.startswith('BOT_'):
                    await asyncio.sleep(2)
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
            else:
                # No pending wild or wrong player clicked
                lang = self.get_lang(game)
                return await interaction.response.edit_message(content=self.t('messages.color_choice_expired', lang=lang), view=None)
        
        # --- UNO RULES ---
        if cid.startswith('uno_rules_'):
            uno_back = self.get_uno_back_emoji()
            game_id = cid[len('uno_rules_'):]
            game = self.bot.active_games.get(game_id)
            
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            # Show game rules
            lang = self.get_lang(game)
            settings = game.get('settings', {})
            variant = settings.get('variant', 'classic')
            variant_emoji = {
                'classic': '🎴',
                'flip': '🔄',
                'no_mercy': '💀',
                'no_mercy_plus': '💀⚡'
            }
            emoji = variant_emoji.get(variant, '🎴')
            variant_name = f"{emoji} {self.t(f'variants.{variant}', lang=lang)}"
            
            rules_embed = discord.Embed(
                title=f"{uno_back} {self.t('rules.title', lang=lang)}",
                description=f"**🎮 {self.t('rules.game_mode', lang=lang)}:** {variant_name}\n\n{self.t('rules.active_rules', lang=lang)}:",
                color=0x3498db
            )
            
            # Starting cards
            rules_embed.add_field(
                name=f"{uno_back} {self.t('rules.starting_cards_title', lang=lang)}",
                value=f"{self.t('rules.each_player_starts', lang=lang)} **{settings.get('starting_cards', 7)} {self.t('rules.cards', lang=lang)}**",
                inline=False
            )
            
            # Stacking
            stack_rules = []
            if variant in ['no_mercy', 'no_mercy_plus']:
                stack_rules.append(f"✅ **{self.t('stacking.no_mercy', lang=lang)}:** {self.t('rules.stack_locked', lang=lang)} - {self.t('rules.stack_desc_mercy', lang=lang)}")
                stack_rules.append(f"✅ **{self.t('rules.together', lang=lang)}:** {self.t('rules.stack_locked', lang=lang)} - {self.t('rules.stack_desc_together', lang=lang)}")
                if variant == 'no_mercy_plus':
                    stack_rules.append(f"🪙 **{self.t('rules.coins', lang=lang)}:** {self.t('rules.coins_desc', lang=lang)}")
            elif variant == 'flip':
                if settings.get('stack_flip_draw', True):
                    stack_rules.append(f"✅ **{self.t('rules.stacking_flip', lang=lang)}:** {self.t('rules.can_respond', lang=lang)} +1 {self.t('hand.on', lang=lang)} +1 {self.t('hand.or', lang=lang)} +5 {self.t('hand.on', lang=lang)} +5 ({self.t('rules.stack_grows', lang=lang)})")
                if settings.get('stack_combined', False):
                    stack_rules.append(f"✅ **{self.t('rules.together', lang=lang)}:** {self.t('rules.can_layer', lang=lang)} +1 {self.t('hand.and', lang=lang)} +5 {self.t('rules.together', lang=lang)}")
            else:
                if settings.get('stack_plus_two', True):
                    stack_rules.append(f"✅ **{self.t('stacking.plus_two', lang=lang)}:** {self.t('rules.can_respond', lang=lang)} +2 {self.t('hand.on', lang=lang)} +2 ({self.t('rules.stack_grows', lang=lang)})")
                if settings.get('stack_plus_four', False):
                    stack_rules.append(f"✅ **{self.t('stacking.plus_four', lang=lang)}:** {self.t('rules.can_respond', lang=lang)} +4 {self.t('hand.on', lang=lang)} +4 ({self.t('rules.stack_grows', lang=lang)})")
                if settings.get('stack_combined', False):
                    stack_rules.append(f"✅ **{self.t('rules.together', lang=lang)}:** {self.t('rules.can_layer', lang=lang)} +2 {self.t('hand.and', lang=lang)} +4 {self.t('rules.together', lang=lang)}")
            
            if stack_rules:
                if variant in ['no_mercy', 'no_mercy_plus']:
                    stack_title = self.t('rules.stacking_no_mercy', lang=lang)
                elif variant == 'flip':
                    stack_title = self.t('rules.stacking_flip', lang=lang)
                else:
                    stack_title = self.t('rules.stacking_classic', lang=lang)
                rules_embed.add_field(
                    name=f"➕ {stack_title}",
                    value="\n".join(stack_rules),
                    inline=False
                )
            
            # Layering
            stack_other = []
            if settings.get('stack_colors', False):
                stack_other.append(f"✅ **{self.t('rules.colors', lang=lang)}:** {self.t('rules.layer_same_color', lang=lang)}")
            if settings.get('stack_numbers', False):
                stack_other.append(f"✅ **{self.t('rules.numbers', lang=lang)}:** {self.t('rules.layer_same_number', lang=lang)}")
            
            if stack_other:
                rules_embed.add_field(
                    name=f"📚 {self.t('rules.layering_title', lang=lang)}",
                    value="\n".join(stack_other),
                    inline=False
                )
            
            # Drawing
            draw_rules = []
            if settings.get('auto_draw', False):
                draw_rules.append(f"✅ **{self.t('rules.auto_draw', lang=lang)}:** {self.t('rules.auto_draw_desc', lang=lang)}")
            if settings.get('draw_until_play', False):
                draw_rules.append(f"✅ **{self.t('rules.draw_until', lang=lang)}:** {self.t('rules.draw_until_desc', lang=lang)}")
            if settings.get('skip_after_draw', True):
                draw_rules.append(f"✅ **{self.t('rules.skip_after', lang=lang)}:** {self.t('rules.skip_after_desc', lang=lang)}")
            if settings.get('must_play', False):
                draw_rules.append(f"✅ **{self.t('rules.must_play', lang=lang)}:** {self.t('rules.must_play_desc', lang=lang)}")
            
            if draw_rules:
                rules_embed.add_field(
                    name=self.t('rules.drawing_title', lang=lang),
                    value="\n".join(draw_rules),
                    inline=False
                )
            
            # Special
            special_rules = []
            if variant == 'no_mercy':
                special_rules.append(f"✅ **{self.t('rules.seven_zero', lang=lang)}:** {self.t('rules.seven_zero_locked', lang=lang)}")
                special_rules.append(f"💀 **{self.t('rules.elimination', lang=lang)}:** {self.t('rules.elimination_locked', lang=lang)}")
            elif variant == 'classic' and settings.get('seven_zero', False):
                special_rules.append(f"✅ **{self.t('rules.seven_zero', lang=lang)}:** {self.t('rules.seven_zero_desc', lang=lang)}")
            
            if settings.get('elimination', False) and variant != 'no_mercy':
                special_rules.append(f"💀 **{self.t('rules.elimination', lang=lang)}:** {self.t('rules.elimination_desc', lang=lang)}")
            
            if settings.get('jump_in', False):
                special_rules.append(f"✅ **{self.t('rules.jump_in', lang=lang)}:** {self.t('rules.jump_in_desc', lang=lang)}")
            if settings.get('uno_callout', False):
                special_rules.append(f"✅ **{self.t('rules.uno_callout', lang=lang)}:** {self.t('rules.uno_callout_desc', lang=lang)}")
            
            if special_rules:
                rules_embed.add_field(
                    name=self.t('rules.special_title', lang=lang),
                    value="\n".join(special_rules),
                    inline=False
                )
            
            # Win condition
            win_mode = f"🏆 **{self.t('rules.first_win', lang=lang)}:** {self.t('rules.first_win_desc', lang=lang)}" if settings.get('first_win', True) else f"🏅 **{self.t('rules.last_standing', lang=lang)}:** {self.t('rules.last_standing_desc', lang=lang)}"
            rules_embed.add_field(
                name=self.t('rules.win_condition', lang=lang),
                value=win_mode,
                inline=False
            )
            
            rules_embed.set_footer(text=self.t('rules.footer', lang=lang))
            
            return await interaction.response.send_message(embed=rules_embed, ephemeral=True)
        
        # --- UNO 7-0 SWAP HANDLER ---
        if cid.startswith('uno_swap_'):
            uno_back = self.get_uno_back_emoji()
            # Format: uno_swap_{game_id}|||{target_player}
            # Use ||| as separator to avoid conflicts with underscores in game_id or player_id
            parts = cid[len('uno_swap_'):].split('|||')
            if len(parts) == 2:
                game_id = parts[0]
                target_player = parts[1]
            else:
                return await interaction.response.send_message(self.t('messages.swap_error', lang='en'), ephemeral=True)
            
            game = self.bot.active_games.get(game_id)
            if not game:
                # Debug: print available game IDs
                available_games = list(self.bot.active_games.keys())
                return await interaction.response.send_message(f"Gra nieaktywna.\nDebug: Szukano: {game_id}\nDostępne: {available_games[:3] if available_games else 'Brak'}", ephemeral=True)
            
            lang = game.get('language', 'en')
            pending_swap = game.get('pending_seven_swap')
            if not pending_swap:
                return await interaction.response.send_message(f"{self.t('messages.no_pending_swap', lang=lang)}\nDebug: pending_seven_swap = {pending_swap}", ephemeral=True)
            
            if pending_swap['player'] != uid:
                return await interaction.response.send_message(f"{self.t('messages.cannot_swap', lang=lang)}\nDebug: Oczekiwany gracz: {pending_swap['player']}, Ty: {uid}", ephemeral=True)
            
            # Swap hands

            hands = game['hands']
            temp_hand = hands[uid]
            hands[uid] = hands[target_player]
            hands[target_player] = temp_hand

            # Clear pending swap
            del game['pending_seven_swap']

            # Get updated hand
            hand = hands[uid]

            # Send confirmation with new hand
            target_name = self.get_bot_display_name(target_player, game)
            swap_confirm_embed = discord.Embed(
                title=f"🔄 {self.t('messages.card_7_swap', lang=lang)}",
                description=f"**{self.t('messages.swapped_hands_with', lang=lang)} {target_name}!**\n\n{self.t('messages.received_their_cards', lang=lang)} {self.t('messages.you_have_x_cards', lang=lang)} **{len(hand)} {self.t('messages.cards_on_hand', lang=lang)}**",
                color=0x9b59b6
            )

            hand_view = self.create_uno_hand_view(game_id, game, uid)
            await interaction.response.send_message(embed=swap_confirm_embed, view=hand_view, ephemeral=True)

            # Odśwież hand_message obu graczy po zamianie
            hand_messages = game.get('hand_messages', {})
            for pid in [uid, target_player]:
                if pid in hand_messages:
                    try:
                        old_interaction, old_msg = hand_messages[pid]
                        embed_hand, card_file_hand = self.create_uno_hand_embed(game_id, game, pid)
                        view_hand = self.create_uno_hand_view(game_id, game, pid)
                        files_hand = [card_file_hand] if card_file_hand else []
                        await old_msg.edit(embed=embed_hand, view=view_hand, attachments=files_hand)
                    except Exception:
                        pass
            
            # Odśwież opponent_views dla trybu Flip
            await self.refresh_opponent_views(game)

            # Send hand update to the swapped player if not BOT
            if not target_player.startswith('BOT_'):
                try:
                    target_user = await self.bot.fetch_user(int(target_player))
                    target_hand = hands[target_player]
                    lang = self.get_lang(game)
                    target_swap_embed = discord.Embed(
                        title=f"🔄 {self.t('messages.hands_swapped', lang=lang)}!",
                        description=f"<@{uid}> {self.t('messages.played_card_7_swapped', lang=lang)}\n\n{self.t('messages.you_have_now', lang=lang)} **{len(target_hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}.",
                        color=0x9b59b6
                    )
                    target_hand_view = self.create_uno_hand_view(game_id, game, target_player)
                    # Refresh target player's hand message if exists
                    if target_player in hand_messages:
                        try:
                            old_interaction, old_msg = hand_messages[target_player]
                            await old_msg.edit(embed=target_swap_embed, view=target_hand_view, attachments=[])
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # Progress turn - card 7 doesn't advance turn yet (done after swap selection)
            # Skip turn advancement as per UNO 7-0 rules (card effect already applied)
            # Next player's turn
            if game['current_turn'] >= len(game['players']):
                game['current_turn'] = 0
            game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
            
            # Update game display
            current_player = game['players'][game['current_turn']]
            embed, card_file = self.create_uno_game_embed(game)
            view = self.create_uno_legacy_game_view(game_id, game, current_player)
            
            try:
                if game.get('messageId'):
                    msg = interaction.channel.get_partial_message(game['messageId'])
                    files = [card_file] if card_file else []
                    await msg.edit(embed=embed, view=view, attachments=files)
            except Exception:
                pass
            
            # Odśwież opponent_views dla trybu Flip
            await self.refresh_opponent_views(game)
            
            # Auto-refresh hand for next player
            if not current_player.startswith('BOT_'):
                await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
            
            # Bot turn if needed
            if current_player.startswith('BOT_'):
                await asyncio.sleep(1.5)
                await self.play_bot_uno_turn(interaction.channel, game_id, game)
            
            return
        
        # --- UNO TOGGLE SELECTION (multi-select mode) ---
        if cid.startswith('uno_toggle_'):
            uno_back = self.get_uno_back_emoji()
            
            parts = cid.split('_')
            card_idx = int(parts[-1])
            game_id = "_".join(parts[2:-1])
            
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            lang = game.get('language', 'en')
            current_player = game['players'][game['current_turn']]
            if uid != current_player:
                return await interaction.response.send_message(self.t('messages.not_your_turn', lang=lang), ephemeral=True)
            
            # Initialize selected_cards if not exists
            if 'selected_cards' not in game:
                game['selected_cards'] = {}
            if uid not in game['selected_cards']:
                game['selected_cards'][uid] = set()
            
            # Toggle selection
            if card_idx in game['selected_cards'][uid]:
                game['selected_cards'][uid].remove(card_idx)
            else:
                game['selected_cards'][uid].add(card_idx)
            
            # Re-send hand view with updated selection
            hand_view = self.create_uno_hand_view(game_id, game, uid)
            await interaction.response.edit_message(view=hand_view)
            return
        
        # --- UNO PLAY MULTIPLE CARDS (stack_colors/stack_numbers) ---
        if cid.startswith('uno_play_multi_'):
            uno_back = self.get_uno_back_emoji()
            
            game_id = cid[len('uno_play_multi_'):]
            game = self.bot.active_games.get(game_id)
            if not game:
                return await interaction.response.send_message(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            lang = game.get('language', 'en')
            current_player = game['players'][game['current_turn']]
            if uid != current_player:
                return await interaction.response.send_message(self.t('messages.not_your_turn', lang=lang), ephemeral=True)
            
            # Get selected cards
            selected_cards = game.get('selected_cards', {}).get(uid, set())
            if not selected_cards:
                # Jeśli nie wybrano żadnych kart, wtedy sprawdź auto-draw
                auto_drawn = await self.check_and_apply_auto_draw(game, uid, interaction.channel)
                if auto_drawn:
                    await interaction.response.defer(ephemeral=True)
                    await interaction.followup.send("🤖 Auto-dobrano kartę (brak zagrywnych). Tura przeszła.", ephemeral=True)
                    # Odśwież rękę nowego gracza jeśli tura przeszła
                    current_player = game['players'][game['current_turn']]
                    if current_player != uid and not current_player.startswith('BOT_'):
                        await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                    return
                return await interaction.response.send_message("❌ Nie wybrano żadnych kart!", ephemeral=True)
            
            hand = game['hands'][uid]
            settings = game.get('settings', {})
            
            # Sort indices to play in order
            selected_indices = sorted(list(selected_cards), reverse=True)  # reverse to remove from back first
            
            # Get cards and validate
            cards_to_play = []
            for idx in sorted(selected_indices):  # forward order for validation
                if idx >= len(hand):
                    return await interaction.response.send_message(f"❌ Nieprawidłowy indeks karty: {idx}", ephemeral=True)
                cards_to_play.append(hand[idx])
            
            # W multi-select: jeśli wybrano Wilda, można zagrać tylko jednego Wilda naraz
            if settings.get('stack_colors', False) or settings.get('stack_numbers', False):
                wild_count = sum(1 for c in cards_to_play if c['color'] == 'wild')
                if wild_count > 0 and len(cards_to_play) > 1:
                    return await interaction.response.send_message(
                        "❌ **Nie możesz zagrać Wilda razem z innymi kartami w multi-select!**",
                        ephemeral=True
                    )
            
            # Validate: all cards must be same color OR same value
            stack_colors = settings.get('stack_colors', False)
            stack_numbers = settings.get('stack_numbers', False)
            
            if stack_colors:
                # All cards must be same color
                first_color = cards_to_play[0]['color']
                if not all(c['color'] == first_color for c in cards_to_play):
                    lang = self.get_lang(game)
                    return await interaction.response.send_message(
                        f"❌ **Stack Colors:** {self.t('messages.stack_colors_error', lang=lang)}",
                        ephemeral=True
                    )
            elif stack_numbers:
                # All cards must be same value
                first_value = cards_to_play[0]['value']
                if not all(c['value'] == first_value for c in cards_to_play):
                    lang = self.get_lang(game)
                    return await interaction.response.send_message(
                        f"❌ **Stack Numbers:** {self.t('messages.stack_numbers_error', lang=lang)}",
                        ephemeral=True
                    )
            else:
                return await interaction.response.send_message("❌ Stack Colors/Numbers nie jest włączony!", ephemeral=True)
            
            # Validate first card can be played
            top_card = game['discard'][-1]
            current_color = game['current_color']
            draw_stack = game.get('draw_stack', 0)
            
            if not uno_logic.can_play_card(cards_to_play[0], top_card, current_color, draw_stack, settings):
                return await interaction.response.send_message(
                    f"❌ {self.t('messages.first_card_cannot_play', lang=lang)}\n\n**{self.t('messages.current', lang=lang)}:** {uno_logic.card_to_string(top_card, lang=lang)}\n**{self.t('game.color', lang=lang)}:** {current_color.upper()}",
                    ephemeral=True
                )
            
            # Play all cards
            game['last_activity'] = time.time()
            played_cards = []
            
            variant = game.get('settings', {}).get('variant', 'classic')
            flip_triggered = False
            
            for idx in selected_indices:  # Remove from back to front
                card = hand.pop(idx)
                game['discard'].append(card)
                played_cards.append(card)
                
                # Check if FLIP card in Flip mode
                if variant == 'flip' and card['value'] == 'flip':
                    flip_triggered = True
                
                # Update current color
                if card['color'] in ['red', 'blue', 'green', 'yellow', 'teal', 'purple', 'pink', 'orange']:
                    game['current_color'] = card['color']
                
                # Apply card effects (only last card matters for +2/+4/Skip/Reverse)
                if card['value'] == '+2':
                    game['draw_stack'] = game.get('draw_stack', 0) + 2
                elif card['value'] == '+4':
                    game['draw_stack'] = game.get('draw_stack', 0) + 4
                elif card['value'] == '+1':  # Flip light side
                    game['draw_stack'] = game.get('draw_stack', 0) + 1
                elif card['value'] == '+5':  # Flip dark side
                    game['draw_stack'] = game.get('draw_stack', 0) + 5
            
            # Handle FLIP card
            if flip_triggered:
                flip_message = await self.flip_handler.handle_flip_card_played(game)
                # After flip, update played_cards to reflect flipped cards
                if game['discard']:
                    # Get the flipped cards from discard pile
                    played_cards = game['discard'][-len(played_cards):]
            
            # Handle last card special effects
            last_card = played_cards[-1]
            if last_card['value'] == 'skip':
                game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
            elif last_card['value'] == 'skip_everyone':  # Flip dark side
                # Skip everyone except current player - advance by number of players
                game['current_turn'] = (game['current_turn'] + len(game['players'])) % len(game['players'])
            elif last_card['value'] == 'Reverse' or last_card['value'] == 'reverse':
                if len(game['players']) == 2:
                    game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                else:
                    game['direction'] *= -1
            
            # Clear selection
            game['selected_cards'][uid] = set()
            
            # Check if last card is wild - if so, need color selection
            if last_card['color'] == 'wild':
                game['current_color'] = 'wybieranie...'
                game['pending_wild'] = {'player': uid, 'card': last_card, 'multi_select': True}
                
                # Update game board
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        embed_main, file_main = self.create_uno_game_embed(game)
                        embed_main.add_field(name=f"⏳ {self.t('messages.waiting', lang=lang)}", value=f"<@{uid}> {self.t('messages.selecting_color', lang=lang)} {self.t('messages.for_wild_card', lang=lang)}", inline=False)
                        files_main = [file_main] if file_main else []
                        await msg.edit(embed=embed_main, attachments=files_main)
                except Exception:
                    pass
                
                # Send color selection
                cards_str = ", ".join([uno_logic.card_to_string(c, compact=True) for c in played_cards])
                wild_embed = discord.Embed(
                    title=f"🌈 {self.t('messages.last_card_wild', lang=lang)}",
                    description=f"**{self.t('messages.played_cards', lang=lang)}:** {cards_str}\n\n⬇️ **{self.t('messages.select_color', lang=lang)}:**",
                    color=0x9b59b6
                )
                wild_card_file = uno_logic.card_to_image(last_card)
                if wild_card_file:
                    wild_embed.set_image(url=f"attachment://{wild_card_file.filename}")
                    files_wild = [wild_card_file]
                else:
                    files_wild = []
                
                color_view = self.create_color_select_view(game_id, lang=self.get_lang(game))
                await interaction.response.send_message(embed=wild_embed, view=color_view, files=files_wild, ephemeral=True)
                return  # Wait for color selection before continuing
            
            # Check UNO penalty - if player has 1 card left and didn't call UNO
            if len(hand) == 1:
                # Check if player called UNO before playing second-to-last card
                if settings.get('uno_callout', False):
                    uno_called_set = game.get('uno_called', set())
                    if uid not in uno_called_set:
                        # Penalty - player must draw cards
                        penalty = settings.get('penalty_uno', 2)
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], penalty)
                        if drawn:
                            hand.extend(drawn)
                        
                        lang = self.get_lang(game)
                        await interaction.response.send_message(
                            f"❌ **{self.t('messages.uno_not_called_title', lang=lang)}**\n\n💥 {self.t('messages.uno_penalty', lang=lang)} +{penalty} {self.t('messages.uno_penalty_cards', lang=lang)}\n\n{self.t('messages.uno_must_call_before', lang=lang)}",
                            ephemeral=True
                        )
                        
                        # Update hand view
                        hand_view = self.create_uno_hand_view(game_id, game, uid)
                        await interaction.message.edit(view=hand_view)
                        return  # Don't process play, player has penalty
            
            # Check for win (after UNO penalty check)
            if len(hand) == 0:
                channel = interaction.channel
                extra_msg = f"✨ {self.t('messages.played_simultaneously', lang=lang)} {len(played_cards)} {self.t('messages.cards_at_once', lang=lang)}"
                if await self.handle_player_win(game_id, game, uid, interaction, channel, extra_msg):
                    return  # Game ended
                
                # Game continues (last standing mode) - Adjust current_turn if needed
                if game['current_turn'] >= len(game['players']):
                    game['current_turn'] = 0
                
                # Update game board
                current_player = game['players'][game['current_turn']]
                embed_main, file_main = self.create_uno_game_embed(game)
                view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files_main = [file_main] if file_main else []
                        await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                except Exception:
                    pass
                
                # Trigger bot or refresh next player's hand
                if current_player.startswith('BOT_'):
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                return
            
            # Send confirmation and finish (no turn change if wild - that happens in uno_color_)
            cards_str = ", ".join([uno_logic.card_to_string(c, compact=True) for c in played_cards])
            await interaction.response.send_message(
                f"✅ {self.t('messages.card_played_multi', lang=lang)} **{len(played_cards)} {self.t('messages.cards_plural', lang=lang)}:**\n{cards_str}\n\n{self.t('messages.cards_remaining', lang=lang)} **{len(hand)}**",
                ephemeral=True
            )
            # Odśwież hand_message gracza po multi-select/auto-draw
            hand_messages = game.get('hand_messages', {})
            if uid in hand_messages:
                try:
                    old_interaction, old_msg = hand_messages[uid]
                    embed_hand, card_file_hand = self.create_uno_hand_embed(game_id, game, uid)
                    view_hand = self.create_uno_hand_view(game_id, game, uid)
                    files_hand = [card_file_hand] if card_file_hand else []
                    await old_msg.edit(embed=embed_hand, view=view_hand, attachments=files_hand)
                except Exception:
                    pass
            
            # Pass turn (already applied Skip/Reverse effects above)
            game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
            
            # Update game board
            try:
                if game.get('messageId'):
                    msg = interaction.channel.get_partial_message(game['messageId'])
                    embed_main, file_main = self.create_uno_game_embed(game)
                    files_main = [file_main] if file_main else []
                    await msg.edit(embed=embed_main, attachments=files_main)
            except Exception as e:
                print(f"Błąd aktualizacji gry: {e}")
            
            # Auto-refresh hand for next player
            next_player = game['players'][game['current_turn']]
            await self.auto_refresh_player_hand(game_id, game, next_player, interaction.channel)
            
            # Check if next player is BOT
            if next_player.startswith('BOT_'):
                await asyncio.sleep(1.5)
                await self.play_bot_uno_turn(interaction.channel, game_id, game)
            
            return
        
        # --- UNO GAME ACTIONS ---
        if cid.startswith('uno_play_') or cid.startswith('uno_draw_') or cid.startswith('uno_call_') or cid.startswith('uno_leave_'):
            # Helper function to send response (handles both response and followup)
            async def send_response(content=None, embed=None, view=None, files=None, ephemeral=True):
                # Convert None to empty list for files
                if files is None:
                    files = []
                # Convert None to MISSING for view (discord.py doesn't accept None)
                if view is None:
                    view = discord.utils.MISSING
                try:
                    if interaction.response.is_done():
                        # Interaction already responded, use followup
                        return await interaction.followup.send(content=content, embed=embed, view=view, files=files, ephemeral=ephemeral)
                    else:
                        # First response, use response.send_message
                        return await interaction.response.send_message(content=content, embed=embed, view=view, files=files, ephemeral=ephemeral)
                except discord.errors.NotFound:
                    # Interaction expired (10062 error), try followup as last resort
                    try:
                        return await interaction.followup.send(content=content or "Interakcja wygasła.", embed=embed, view=view, files=files, ephemeral=True)
                    except:
                        pass  # Give up silently
            
            async def edit_response(content=discord.utils.MISSING, embed=discord.utils.MISSING, view=discord.utils.MISSING, attachments=discord.utils.MISSING):
                try:
                    if interaction.response.is_done():
                        # Already responded, edit the original response
                        return await interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
                    else:
                        # First interaction, use response.edit_message
                        return await interaction.response.edit_message(content=content, embed=embed, view=view, attachments=attachments)
                except discord.errors.NotFound:
                    # Interaction expired, try editing original response
                    try:
                        return await interaction.edit_original_response(content=content, embed=embed, view=view, attachments=attachments)
                    except:
                        pass  # Give up silently
            
            uno_back = self.get_uno_back_emoji()
            
            if cid.startswith('uno_play_select_'):
                # Handle select menu card choice
                game_id = cid[len('uno_play_select_'):]
                card_idx = int(interaction.data['values'][0])
            elif cid.startswith('uno_play_'):
                parts = cid.split('_')
                card_idx = int(parts[-1])
                game_id = "_".join(parts[2:-1])
            elif cid.startswith('uno_draw_'):
                game_id = cid[len('uno_draw_'):]
            elif cid.startswith('uno_call_'):
                game_id = cid[len('uno_call_'):]
            else:  # uno_leave_
                game_id = cid[len('uno_leave_'):]
            
            game = self.bot.active_games.get(game_id)
            if not game:
                return await send_response(self.t('messages.game_inactive', lang='en'), ephemeral=True)
            
            lang = game.get('language', 'en')
            current_player = game['players'][game['current_turn']]
            
            if cid.startswith('uno_leave_'):
                if uid not in game['players']:
                    return await send_response(self.t('messages.not_in_game', lang=lang), ephemeral=True)
                
                # Player leaves - they lose
                game['players'].remove(uid)
                del game['hands'][uid]
                
                if len(game['players']) == 1:
                    winner = game['players'][0]
                    winner_display = self.get_bot_display_name(winner, game)
                    
                    # Award win to remaining player
                    if not winner.startswith('BOT_'):
                        lang = self.get_lang(game)
                        economy_cog = self.bot.get_cog("Economy")
                        if economy_cog:
                            economy_cog.add_coins(int(winner), 30, reason="uno_win")
                            # Record game statistics
                            game_stats_cog = self.bot.get_cog("GameStats")
                            if game_stats_cog:
                                duration = int(time.time() - game.get('start_time', time.time()))
                                guild_id = game.get('guild_id')
                                game_stats_cog.record_game(int(winner), "uno", won=True, coins_earned=30, playtime_seconds=duration, category="strategy_games", guild_id=guild_id)
                        #await check_achievements(winner, interaction.channel)
                    
                    embed = discord.Embed(
                        title=f"{uno_back} {self.t('messages.game_over', lang=lang)}",
                        description=f"🏆 {self.t('messages.winner', lang=lang)}: {winner_display}",
                        color=discord.Color.gold()
                    )
                    await send_response(self.t('messages.you_left_game', lang=lang), ephemeral=True)
                    try:
                        if game.get('messageId'):
                            msg = interaction.channel.get_partial_message(game['messageId'])
                            await msg.edit(embed=embed, view=None)
                    except Exception:
                        pass
                    self.bot.active_games.pop(game_id, None)
                    return
                
                # Continue game - adjust turn if needed
                if game['current_turn'] >= len(game['players']):
                    game['current_turn'] = 0
                
                await send_response(self.t('messages.you_left_game', lang=lang), ephemeral=True)
                
                # Update game board and continue
                current_player = game['players'][game['current_turn']]
                embed_main, file_main = self.create_uno_game_embed(game)
                view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                try:
                    if game.get('messageId'):
                        msg = interaction.channel.get_partial_message(game['messageId'])
                        files_main = [file_main] if file_main else []
                        await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                except Exception:
                    pass
                
                # Trigger bot or refresh next player's hand
                if current_player.startswith('BOT_'):
                    await self.play_bot_uno_turn(interaction.channel, game_id, game)
                else:
                    await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                return
            
            if cid.startswith('uno_call_'):
                # UNO call - mark player as called UNO
                game = self.bot.active_games.get(game_id)
                if not game:
                    return await send_response("Gra nieaktywna.", ephemeral=True)
                
                settings = game.get('settings', {})
                
                # Initialize uno_called tracking if not exists
                if 'uno_called' not in game:
                    game['uno_called'] = set()
                
                hand = game['hands'].get(uid, [])
                
                lang = self.get_lang(game)
                uno_back = self.get_uno_back_emoji()
                
                # Check if player has exactly 2 cards (before playing second-to-last)
                if len(hand) == 2:
                    game['uno_called'].add(uid)
                    return await send_response(f"🔥 UNO! {uno_back}\n\n{self.t('messages.uno_called_success', lang=lang)}", ephemeral=True)
                elif len(hand) == 1:
                    return await send_response(f"⚠️ {self.t('messages.uno_too_late', lang=lang)}", ephemeral=True)
                elif len(hand) == 0:
                    return await send_response(f"✅ {self.t('messages.uno_already_won', lang=lang)}", ephemeral=True)
                else:
                    # False UNO call - penalty
                    if settings.get('uno_callout', False):
                        penalty = settings.get('penalty_false_uno', 2)
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], penalty)
                        if drawn:
                            hand.extend(drawn)
                        
                        # Check for elimination
                        if await self.check_elimination(game_id, game, uid, interaction.channel):
                            return  # Player was eliminated
                        
                        # Send updated hand to player
                        uno_back = self.get_uno_back_emoji()
                        hand_embed = discord.Embed(
                            title=f"{uno_back} {self.t('messages.uno_false_call', lang=lang)}",
                            description=f"❌ {self.t('messages.uno_false_call', lang=lang)} - {self.t('messages.you_have', lang=lang)} {len(hand)} {self.t('game.cards', lang=lang)}!\n\n💥 {self.t('messages.uno_false_penalty', lang=lang)} +{penalty} {self.t('messages.uno_penalty_cards', lang=lang)}\n\n{self.t('messages.you_have', lang=lang)} **{len(hand)} {self.t('game.cards', lang=lang)}** {self.t('hand.cards_in_hand', lang=lang)}.",
                            color=0xe74c3c
                        )
                        hand_view = self.create_uno_hand_view(game_id, game, uid)
                        
                        try:
                            await edit_response(embed=hand_embed, view=hand_view, attachments=[])
                        except:
                            await send_response(embed=hand_embed, view=hand_view, ephemeral=True)
                        
                        # Update display and trigger bot if it's bot's turn
                        current_player = game['players'][game['current_turn']]
                        embed, card_file = self.create_uno_game_embed(game)
                        view = self.create_uno_legacy_game_view(game_id, game, current_player)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files = [card_file] if card_file else []
                                await msg.edit(embed=embed, view=view, attachments=files)
                        except Exception:
                            pass
                        
                        # Trigger bot turn if needed
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(interaction.channel, game_id, game)
                        else:
                            # Auto-refresh hand for next player
                            await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                        return
                    else:
                        return await send_response(f"⚠️ Masz {len(hand)} kart, nie 1!", ephemeral=True)
            
            # Check if it's player's turn OR if jump-in is allowed
            settings = game.get('settings', {})
            is_current_turn = (uid == current_player)
            allow_jump_in = settings.get('jump_in', False)
            
            hand = game['hands'][uid]
            top_card = game['discard'][-1]
            current_color = game['current_color']
            
            # If not current turn, check jump-in eligibility (only for play, not draw)
            if not is_current_turn and cid.startswith('uno_play_'):
                if not allow_jump_in:
                    return await send_response(self.t('messages.not_your_turn', lang=lang), ephemeral=True)
                
                # Jump-in: card must be IDENTICAL (same color AND value)
                # Parse card index
                parts = cid.split('_')
                card_idx_jump = int(parts[-1])
                if card_idx_jump >= len(hand):
                    return await send_response(f"❌ {self.t('messages.invalid_card', lang=lang)}", ephemeral=True)
                
                card_jump = hand[card_idx_jump]
                
                # Check if IDENTICAL (not just matching)
                if card_jump['color'] != top_card['color'] or card_jump['value'] != top_card['value']:
                    return await send_response(
                        f"❌ **{self.t('messages.jump_in_identical', lang=lang)}**\n\n**{self.t('messages.current', lang=lang)}:** {uno_logic.card_to_string(top_card, lang=lang)}\n**{self.t('messages.your', lang=lang)}:** {uno_logic.card_to_string(card_jump, lang=lang)}\n\n{self.t('messages.must_be_same', lang=lang)}",
                        ephemeral=True
                    )
                
                # Jump-in successful! Change turn to this player
                game['current_turn'] = game['players'].index(uid)
                # Continue with normal play logic below
            elif not is_current_turn:
                return await send_response(self.t('messages.not_your_turn', lang=lang), ephemeral=True)
            
            if cid.startswith('uno_draw_'):
                # Draw card(s) - check if there's a draw stack
                game['last_activity'] = time.time()  # Aktualizuj aktywność
                
                # WALIDACJA: Sprawdź czy gracz MUSI zagrać (jeśli ma zagrywną kartę)
                settings = game.get('settings', {})
                draw_stack = game.get('draw_stack', 0)
                if settings.get('must_play', False):
                    # Sprawdź czy gracz ma jakąś zagrywną kartę
                    playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
                    if playable:
                        return await send_response(
                            f"❌ **Musisz zagrać!**\n\nMasz zagrywne karty na ręce. Nie możesz dobierać gdy możesz zagrać.\n\n**Aktualna karta:** {uno_logic.card_to_string(top_card, compact=True)}\n**Kolor:** {current_color.upper()}",
                            ephemeral=True
                        )
                
                draw_stack = game.get('draw_stack', 0)
                found_playable = False  # Initialize before if/else
                draw_msg = ""  # Initialize draw_msg
                
                if draw_stack > 0:
                    # Player must draw all stacked cards
                    uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                    drawn = uno_logic.draw_cards(game['deck'], draw_stack)
                    if drawn:
                        hand.extend(drawn)
                    game['draw_stack'] = 0  # Clear the stack
                    draw_msg = f"💥 {self.t('messages.drew_cards_prefix', lang=lang)} **{draw_stack} {self.t('messages.cards', lang=lang)}** {self.t('messages.through_stacking', lang=lang)}!\n\n{self.t('messages.stack_cleared', lang=lang)}"
                    
                    # Check for elimination (No Mercy or optional rule)
                    if await self.check_elimination(game_id, game, uid, interaction.channel):
                        return  # Player was eliminated
                else:
                    # Normal draw OR draw_until_play
                    if settings.get('draw_until_play', False):
                        # Dobieraj aż znajdziesz zagrywną kartę
                        cards_drawn = 0
                        max_draws = 20  # Zabezpieczenie przed nieskończoną pętlą
                        
                        while cards_drawn < max_draws:
                            uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                            drawn = uno_logic.draw_cards(game['deck'], 1)
                            if drawn:
                                hand.extend(drawn)
                                cards_drawn += 1
                                
                                # Sprawdź czy dobrана karta jest zagrywna
                                playable = uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)
                                if playable:
                                    draw_msg = f"✅ Dobrano **{cards_drawn} kart** - znaleziono zagrywną!\n\nMożesz teraz zagrać."
                                    found_playable = True
                                    break
                            else:
                                break  # Deck pusty
                        else:
                            draw_msg = f"⚠️ Dobrano **{cards_drawn} kart** (limit osiągnięty)"
                        
                        if cards_drawn > 0 and not any(uno_logic.get_playable_cards(hand, top_card, current_color, draw_stack, settings)):
                            draw_msg = f"❌ Dobrano **{cards_drawn} kart** - brak zagrywnych"
                        
                        # Check for elimination after draw_until_play
                        if cards_drawn > 0:
                            if await self.check_elimination(game_id, game, uid, interaction.channel):
                                return  # Player was eliminated
                    else:
                        # Normal single draw
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], 1)
                        if drawn:
                            hand.extend(drawn)
                        draw_msg = "Dobrano 1 kartę"
                        
                        # Check for elimination after normal draw
                        if await self.check_elimination(game_id, game, uid, interaction.channel):
                            return  # Player was eliminated
                
                # Send combined message with card drawn and updated hand
                lang = self.get_lang(game)
                hand_embed = discord.Embed(
                    title=f"{uno_back} {self.t('messages.drawing_card', lang=lang)}",
                    description=f"{draw_msg}\n\n{self.t('messages.you_have_now', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}.",
                    color=0x3498db
                )
                
                files = []
                
                hand_view = self.create_uno_hand_view(game_id, game, uid)
                
                # Try to edit existing hand message, or send new one
                try:
                    await edit_response(embed=hand_embed, view=hand_view, attachments=files)
                except:
                    # If editing fails, send new message and store it
                    await send_response(embed=hand_embed, view=hand_view, files=files, ephemeral=True)
                    try:
                        msg = await interaction.original_response()
                        game.setdefault('hand_messages', {})[uid] = (interaction, msg)
                    except:
                        pass
                
                # Clear UNO called status (player now has more than 1 card)
                if 'uno_called' in game and uid in game['uno_called']:
                    game['uno_called'].discard(uid)
                
                # Determine if turn should pass:
                # - If draw_until_play found playable card: keep turn (ignore skip_after_draw)
                # - If normal draw and skip_after_draw is ON: pass turn
                # - Otherwise: keep turn
                turn_changed = False
                skip_after_draw = settings.get('skip_after_draw', True)
                draw_until_play_active = settings.get('draw_until_play', False)
                
                if draw_until_play_active and found_playable:
                    # draw_until_play found a playable card - player keeps turn to play it
                    # This overrides skip_after_draw (the point of draw_until_play is to play the card)
                    turn_changed = False
                elif skip_after_draw:
                    # Normal draw with skip_after_draw enabled - pass turn
                    game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                    turn_changed = True
                else:
                    # Normal draw with skip_after_draw disabled - keep turn
                    turn_changed = False
                
                # Update main game display only if turn changed
                if turn_changed:
                    current_player = game['players'][game['current_turn']]
                    embed_main, card_file_main = self.create_uno_game_embed(game)
                    view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                    
                    try:
                        if game.get('messageId'):
                            msg_main = interaction.channel.get_partial_message(game['messageId'])
                            files_main = [card_file_main] if card_file_main else []
                            await msg_main.edit(embed=embed_main, view=view_main, attachments=files_main)
                    except Exception:
                        pass
                    
                    # Auto-refresh hand for next player
                    if not current_player.startswith('BOT_'):
                        await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                    
                    # Bot turn
                    if current_player.startswith('BOT_'):
                        await asyncio.sleep(2)
                        await self.play_bot_uno_turn(interaction.channel, game_id, game)
                
            elif cid.startswith('uno_play_'):
                # Play card
                game['last_activity'] = time.time()  # Aktualizuj aktywność
                if card_idx >= len(hand):
                    return await send_response(f"❌ {self.t('messages.invalid_card', lang=lang)}", ephemeral=True)
                
                card = hand[card_idx]
                
                # VALIDATION: Check if card can be played
                draw_stack = game.get('draw_stack', 0)
                settings = game.get('settings', {})
                if not uno_logic.can_play_card(card, top_card, current_color, draw_stack, settings):
                    # Show error with card image
                    if draw_stack > 0:
                        variant = settings.get('variant', 'classic')
                        if variant == 'no_mercy':
                            error_msg = f"**Stack:** {draw_stack} kart do dobrania!\n\nMożesz zagrać tylko **colored +4** lub **wild +6/+10/+4 Reverse** aby dodać do stacku w zależności od ustawień, albo dobierz wszystkie karty!"
                        elif variant == 'flip':
                            error_msg = f"**Stack:** {draw_stack} kart do dobrania!\n\nMożesz zagrać tylko **+1** lub **+5** aby dodać do stacku w zależności od ustawień, albo dobierz wszystkie karty!"
                        else:
                            error_msg = f"**Stack:** {draw_stack} kart do dobrania!\n\nMożesz zagrać tylko **+2** lub **+4** aby dodać do stacku w zależności od ustawień, albo dobierz wszystkie karty!"
                    else:
                        error_msg = f"**Aktualna karta:** {uno_logic.card_to_string(top_card, compact=True)}\n**Aktualny kolor:** {current_color.upper()}\n\nWybierz kartę tego samego koloru, liczby/akcji lub kartę WILD!"
                    
                    error_embed = discord.Embed(
                        title=f"❌ {self.t('messages.cannot_play_card', lang=lang)}!",
                        description=f"**{self.t('messages.you_tried_play', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n{error_msg}",
                        color=0xe74c3c
                    )
                    error_card_file = uno_logic.card_to_image(card)
                    if error_card_file:
                        error_embed.set_thumbnail(url=f"attachment://{error_card_file.filename}")
                        return await send_response(embed=error_embed, files=[error_card_file], ephemeral=True)
                    else:
                        return await send_response(embed=error_embed, ephemeral=True)
                
                # Remove card from hand
                hand.pop(card_idx)
                game['discard'].append(card)
                
                # Check UNO callout penalty (if player has 1 card left and didn't call UNO)
                settings = game.get('settings', {})
                if len(hand) == 1 and settings.get('uno_callout', False):
                    # Player has 1 card left - check if they called UNO when they had 2 cards
                    uno_called_set = game.get('uno_called', set())
                    if uid not in uno_called_set:
                        # Didn't call UNO - penalty!
                        penalty = settings.get('penalty_cards', 2)
                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                        drawn = uno_logic.draw_cards(game['deck'], penalty)
                        if drawn:
                            hand.extend(drawn)
                        
                        # Check for elimination after UNO penalty
                        if await self.check_elimination(game_id, game, uid, interaction.channel):
                            return  # Player was eliminated
                        
                        # Put card back and undo play
                        hand.append(card)
                        game['discard'].pop()
                        
                        # Send updated hand to player
                        uno_back = self.get_uno_back_emoji()
                        lang = self.get_lang(game)
                        hand_embed = discord.Embed(
                            title=f"{uno_back} {self.t('messages.didnt_call_uno', lang=lang)}!",
                            description=f"❌ **{self.t('messages.didnt_call_uno_caps', lang=lang)}!**\n\n{self.t('messages.must_call_uno_before', lang=lang)}\n\n💥 {self.t('messages.penalty', lang=lang)}: +{penalty} {self.t('messages.cards', lang=lang)} + {self.t('messages.card_returns', lang=lang)}\n\n{self.t('messages.you_have_now', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}** {self.t('messages.in_hand', lang=lang)}.",
                            color=0xe74c3c
                        )
                        hand_view = self.create_uno_hand_view(game_id, game, uid)
                        
                        try:
                            await edit_response(embed=hand_embed, view=hand_view, attachments=[])
                        except:
                            await send_response(embed=hand_embed, view=hand_view, ephemeral=True)
                        
                        # Pass turn
                        game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                        
                        # Update display
                        current_player = game['players'][game['current_turn']]
                        embed, card_file = self.create_uno_game_embed(game)
                        view = self.create_uno_legacy_game_view(game_id, game, current_player)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files = [card_file] if card_file else []
                                await msg.edit(embed=embed, view=view, attachments=files)
                        except Exception:
                            pass
                        
                        # Trigger bot turn if needed
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(interaction.channel, game_id, game)
                        else:
                            # Auto-refresh hand for next player
                            await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                        
                        return
                
                # Check if player wins
                if uno_logic.check_winner(hand):
                    channel = interaction.channel
                    if await self.handle_player_win(game_id, game, uid, interaction, channel):
                        return  # Game ended
                    
                    # Game continues (last standing mode)
                    # Update game board
                    current_player = game['players'][game['current_turn']]
                    embed_main, file_main = self.create_uno_game_embed(game)
                    view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                    try:
                        if game.get('messageId'):
                            msg = interaction.channel.get_partial_message(game['messageId'])
                            files_main = [file_main] if file_main else []
                            await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                    except Exception:
                        pass
                    
                    # Trigger bot or refresh next player's hand
                    if current_player.startswith('BOT_'):
                        await self.play_bot_uno_turn(interaction.channel, game_id, game)
                    else:
                        await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                    
                    return
                
                # Handle wild card color selection
                if card['color'] == 'wild':
                    # Get effects FIRST to check if it's draw_color or wild_discard_all
                    effects = uno_logic.apply_card_effect(card, game)
                    
                    # Check if this is WILD DISCARD ALL
                    if effects.get('wild_discard_all'):
                        # Wild Discard All: Choose color and discard all cards of that color
                        game['current_color'] = 'wybieranie...'
                        
                        # Update game display
                        embed_temp, card_file_temp = self.create_uno_game_embed(game)
                        embed_temp.add_field(name=f"⏳ {self.t('messages.waiting', lang=lang)}", value=f"<@{uid}> {self.t('messages.selecting_color', lang=lang)} {self.t('messages.for_discard', lang=lang)}", inline=False)
                        view_temp = self.create_uno_legacy_game_view(game_id, game, uid)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files_temp = [card_file_temp] if card_file_temp else []
                                await msg.edit(embed=embed_temp, view=view_temp, attachments=files_temp)
                        except Exception:
                            pass
                        
                        # Show color selection for discard
                        lang = self.get_lang(game)
                        current_side = game.get('current_side', 'light')
                        discard_embed = discord.Embed(
                            title=f"🗑️ {self.t('messages.wild_discard_all', lang=lang).upper()}",
                            description=f"**{self.t('messages.played_card', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n\n⬇️ **{self.t('messages.select_color_discard', lang=lang)}:**\n\n{self.t('messages.all_cards_will_discard', lang=lang)}",
                            color=0xff6b6b
                        )
                        
                        # Attach card image
                        discard_card_file = uno_logic.card_to_image(card)
                        if discard_card_file:
                            discard_embed.set_image(url=f"attachment://{discard_card_file.filename}")
                            files_discard = [discard_card_file]
                        else:
                            files_discard = []
                        
                        color_view = self.create_color_select_view(game_id, side=current_side, lang=self.get_lang(game))
                        await send_response(embed=discard_embed, view=color_view, files=files_discard, ephemeral=True)
                        
                        try:
                            color_msg = await interaction.original_response()
                        except:
                            color_msg = None
                        
                        # Store pending wild_discard_all
                        game['pending_wild_discard_all'] = {
                            'player': uid,
                            'card': card,
                            'game_id': game_id,
                            'color_msg': color_msg
                        }
                        return
                    
                    # Check if this is WILD SUDDEN DEATH
                    if effects.get('sudden_death'):
                        # Wild Sudden Death: Choose color first, then all draw to 24
                        game['current_color'] = 'wybieranie...'
                        
                        # Update game display
                        embed_temp, card_file_temp = self.create_uno_game_embed(game)
                        embed_temp.add_field(name=f"⏳ {self.t('messages.waiting', lang=lang)}", value=f"<@{uid}> {self.t('messages.selecting_color', lang=lang)} {self.t('messages.for_sudden_death', lang=lang)}", inline=False)
                        view_temp = self.create_uno_legacy_game_view(game_id, game, uid)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files_temp = [card_file_temp] if card_file_temp else []
                                await msg.edit(embed=embed_temp, view=view_temp, attachments=files_temp)
                        except Exception:
                            pass
                        
                        # Show color selection
                        lang = self.get_lang(game)
                        current_side = game.get('current_side', 'light')
                        sudden_embed = discord.Embed(
                            title=f"💀⚡ {self.t('messages.wild_sudden_death', lang=lang).upper()}",
                            description=f"**{self.t('messages.played_card', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n\n⬇️ **{self.t('messages.select_color', lang=lang)}:**\n\n⚠️ {self.t('messages.all_draw_to_24', lang=lang)}",
                            color=0x000000
                        )
                        
                        sudden_card_file = uno_logic.card_to_image(card)
                        if sudden_card_file:
                            sudden_embed.set_image(url=f"attachment://{sudden_card_file.filename}")
                            files_sudden = [sudden_card_file]
                        else:
                            files_sudden = []
                        
                        color_view = self.create_color_select_view(game_id, side=current_side, lang=self.get_lang(game))
                        await send_response(embed=sudden_embed, view=color_view, files=files_sudden, ephemeral=True)
                        
                        try:
                            color_msg = await interaction.original_response()
                        except:
                            color_msg = None
                        
                        # Store pending sudden_death
                        game['pending_wild_sudden_death'] = {
                            'player': uid,
                            'card': card,
                            'game_id': game_id,
                            'color_msg': color_msg
                        }
                        return
                    
                    # Check if this is WILD FINAL ATTACK
                    if effects.get('final_attack'):
                        # Wild Final Attack: Choose color first, then reveal and attack
                        game['current_color'] = 'wybieranie...'
                        
                        # Update game display
                        embed_temp, card_file_temp = self.create_uno_game_embed(game)
                        embed_temp.add_field(name=f"⏳ {self.t('messages.waiting', lang=lang)}", value=f"<@{uid}> {self.t('messages.selecting_color', lang=lang)} {self.t('messages.for_final_attack', lang=lang)}", inline=False)
                        view_temp = self.create_uno_legacy_game_view(game_id, game, uid)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files_temp = [card_file_temp] if card_file_temp else []
                                await msg.edit(embed=embed_temp, view=view_temp, attachments=files_temp)
                        except Exception:
                            pass
                        
                        # Show color selection
                        lang = self.get_lang(game)
                        current_side = game.get('current_side', 'light')
                        attack_embed = discord.Embed(
                            title=f"⚔️💥 {self.t('messages.wild_final_attack', lang=lang).upper()}",
                            description=f"**{self.t('messages.played_card', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n\n⬇️ **{self.t('messages.select_color', lang=lang)}:**\n\n⚠️ {self.t('messages.hand_revealed', lang=lang)}\n{self.t('messages.opponent_draws', lang=lang)}",
                            color=0xdc143c
                        )
                        
                        attack_card_file = uno_logic.card_to_image(card)
                        if attack_card_file:
                            attack_embed.set_image(url=f"attachment://{attack_card_file.filename}")
                            files_attack = [attack_card_file]
                        else:
                            files_attack = []
                        
                        color_view = self.create_color_select_view(game_id, side=current_side, lang=self.get_lang(game))
                        await send_response(embed=attack_embed, view=color_view, files=files_attack, ephemeral=True)
                        
                        try:
                            color_msg = await interaction.original_response()
                        except:
                            color_msg = None
                        
                        # Store pending final_attack
                        game['pending_wild_final_attack'] = {
                            'player': uid,
                            'card': card,
                            'game_id': game_id,
                            'color_msg': color_msg
                        }
                        return
                    
                    # Check if this is WILD DRAW COLOR (dark side Flip)
                    if effects.get('draw_color'):
                        # Draw Color: Pass turn to next player, THEY choose color and draw
                        game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                        next_player = game['players'][game['current_turn']]
                        
                        # Set temporary color
                        game['current_color'] = 'wybieranie...'
                        
                        # Store pending draw_color for next player
                        game['pending_draw_color'] = {
                            'player': next_player,  # Next player chooses
                            'card': card,
                            'initiator': uid  # Who played the card
                        }
                        
                        # Update game display
                        embed_temp, card_file_temp = self.create_uno_game_embed(game)
                        next_player_display = self.get_bot_display_name(next_player, game)
                        
                        # Get card name based on variant
                        variant = game.get('settings', {}).get('variant', 'classic')
                        card_name = "WILD COLOR ROULETTE" if variant == 'no_mercy' else "WILD DRAW COLOR"
                        
                        embed_temp.add_field(name=f"🎨 {card_name}!", value=f"{next_player_display} musi wybrać kolor i dobierać karty aż dostanie kartę tego koloru!", inline=False)
                        view_temp = self.create_uno_legacy_game_view(game_id, game, next_player)
                        
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files_temp = [card_file_temp] if card_file_temp else []
                                await msg.edit(embed=embed_temp, view=view_temp, attachments=files_temp)
                        except Exception:
                            pass
                        
                        # Odśwież opponent_views dla trybu Flip
                        await self.refresh_opponent_views(game)
                        
                        # Notify current player
                        variant = game.get('settings', {}).get('variant', 'classic')
                        card_name = "WILD COLOR ROULETTE" if variant == 'no_mercy' else "WILD DRAW COLOR"
                        await send_response(
                            f"✅ {self.t('messages.card_played', lang=lang)} **{card_name}**!\n\n{next_player_display} {self.t('messages.must_choose_color', lang=lang)}",
                            ephemeral=True
                        )
                        
                        # If next player is BOT, handle automatically
                        if next_player.startswith('BOT_'):
                            await asyncio.sleep(2)
                            # Bot chooses random color based on variant
                            variant = game.get('settings', {}).get('variant', 'classic')
                            if variant == 'flip':
                                current_side = game.get('current_side', 'light')
                                if current_side == 'dark':
                                    bot_color = random.choice(['teal', 'purple', 'pink', 'orange'])
                                else:
                                    bot_color = random.choice(['red', 'yellow', 'green', 'blue'])
                            else:
                                # Classic and No Mercy always use standard colors
                                bot_color = random.choice(['red', 'yellow', 'green', 'blue'])
                            game['current_color'] = bot_color
                            del game['pending_draw_color']
                            
                            # Bot draws until gets that color
                            bot_hand = game['hands'][next_player]
                            drawn_cards = []
                            while True:
                                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                drawn = uno_logic.draw_cards(game['deck'], 1)
                                if not drawn:
                                    break
                                drawn_cards.extend(drawn)
                                bot_hand.extend(drawn)
                                # Check if drawn card matches chosen color
                                if drawn[0]['color'] == bot_color:
                                    break
                                # Safety limit
                                if len(drawn_cards) >= 20:
                                    break
                            
                            # Notify
                            bot_display = self.get_bot_display_name(next_player, game)
                            await interaction.channel.send(
                                f"{bot_display} {self.t('messages.player_selected_color', lang=lang)} **{bot_color.upper()}** {self.t('messages.and', lang=lang)} {self.t('messages.drew_lowercase', lang=lang)} **{len(drawn_cards)} {self.t('messages.cards', lang=lang)}**!",
                                delete_after=5
                            )
                            
                            # Update display and continue
                            embed, card_file = self.create_uno_game_embed(game)
                            view = self.create_uno_legacy_game_view(game_id, game, next_player)
                            
                            try:
                                if game.get('messageId'):
                                    msg = interaction.channel.get_partial_message(game['messageId'])
                                    files = [card_file] if card_file else []
                                    await msg.edit(embed=embed, view=view, attachments=files)
                            except Exception:
                                pass
                            
                            await self.refresh_opponent_views(game)
                            
                            # Bot's turn
                            await asyncio.sleep(1.5)
                            await self.play_bot_uno_turn(interaction.channel, game_id, game)
                        
                        return
                    
                    # Normal wild card (not draw_color) - current player chooses color
                    # WAŻNE: Aktualizuj widok gry NAJPIERW (pokaż zagraną kartę)
                    # Ustaw tymczasowy kolor dla wyświetlania (zostanie zmieniony po wyborze)
                    game['current_color'] = 'wybieranie...'
                    
                    # Aktualizuj główny widok gry
                    embed_temp, card_file_temp = self.create_uno_game_embed(game)
                    embed_temp.add_field(name=f"⏳ {self.t('messages.waiting', lang=lang)}", value=f"<@{uid}> {self.t('messages.selecting_color', lang=lang)} {self.t('messages.for_wild_card', lang=lang)}", inline=False)
                    view_temp = self.create_uno_legacy_game_view(game_id, game, uid)
                    
                    try:
                        if game.get('messageId'):
                            msg = interaction.channel.get_partial_message(game['messageId'])
                            files_temp = [card_file_temp] if card_file_temp else []
                            await msg.edit(embed=embed_temp, view=view_temp, attachments=files_temp)
                    except Exception:
                        pass
                    
                    # Determine which side we're on for color selection
                    current_side = game.get('current_side', 'light')
                    
                    # Edit existing hand message with color selection
                    hand_embed = discord.Embed(
                        title=f"🌈 {self.t('messages.wild_card_played_rainbow', lang=lang)}",
                        description=f"**{self.t('messages.played_card_label', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n\n⬇️ **{self.t('messages.select_color_below', lang=lang)}**",
                        color=0x9b59b6
                    )
                    
                    # Attach wild card image
                    wild_card_file = uno_logic.card_to_image(card)
                    if wild_card_file:
                        hand_embed.set_image(url=f"attachment://{wild_card_file.filename}")
                        files = [wild_card_file]
                    else:
                        files = []
                    
                    color_view = self.create_color_select_view(game_id, side=current_side, lang=self.get_lang(game))
                    
                    # Send new color selection message (don't edit hand message)
                    await send_response(embed=hand_embed, view=color_view, files=files, ephemeral=True)
                    
                    # Get the color selection message reference
                    try:
                        color_msg = await interaction.original_response()
                    except:
                        color_msg = None
                    
                    # Wait for color selection before continuing (NIE ZMIENIA TURY!)
                    # Store effects to apply after color selection
                    game['pending_wild'] = {
                        'player': uid,
                        'card': card,
                        'effects': effects,
                        'hand': hand.copy(),  # Current hand state
                        'game_id': game_id,
                        'color_msg': color_msg  # Message to close after selection
                    }
                    return
                else:
                    game['current_color'] = card['color']
                    # Apply card effects for non-wild cards
                    effects = uno_logic.apply_card_effect(card, game)
                
                # Handle No Mercy+ special cards
                variant = game.get('settings', {}).get('variant', 'classic')
                if variant == 'no_mercy_plus':
                    if effects.get('sudden_death'):
                        # Wild Sudden Death: All players draw to 24 cards
                        draws = self.no_mercy_plus_handler.handle_wild_sudden_death(game)
                        
                        # Notify channel
                        try:
                            player_name = self.get_bot_display_name(uid, game)
                            draw_text = "\n".join([
                                f"{self.get_bot_display_name(pid, game)}: +{count}" 
                                for pid, count in draws.items() if count > 0
                            ])
                            await interaction.channel.send(
                                f"💀⚡ **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} SUDDEN DEATH!**\n\n"
                                f"{self.t('messages.all_draw_24', lang=lang)}\n\n{draw_text}",
                                silent=True,
                                delete_after=10
                            )
                        except Exception:
                            pass
                        
                        # Check for eliminations after drawing
                        for pid in list(game['players']):
                            if await self.check_elimination(game_id, game, pid, interaction.channel):
                                # Player was eliminated, continue to next
                                continue
                    
                    elif effects.get('final_attack'):
                        # Wild Final Attack: Reveal player's hand, draw based on action cards
                        next_player_id, main_draw, all_draw, action_count = self.no_mercy_plus_handler.handle_wild_final_attack(game, uid)
                        
                        player_name = self.get_bot_display_name(uid, game)
                        player_hand = game['hands'][uid]
                        
                        # Show player's hand (reveal cards)
                        hand_emojis = []
                        for c in player_hand:
                            emoji = uno_logic.card_to_emoji(c, variant)
                            if isinstance(emoji, discord.PartialEmoji):
                                hand_emojis.append(f"<:{emoji.name}:{emoji.id}>")
                            else:
                                hand_emojis.append(str(emoji))
                        hand_display = " ".join(hand_emojis)
                        
                        try:
                            if all_draw:
                                # MEGA ATTACK (7+ action cards)
                                next_name = self.get_bot_display_name(next_player_id, game)
                                await interaction.channel.send(
                                    f"⚔️💥 **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} FINAL ATTACK!**\n\n"
                                    f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                                    f"**{action_count} {self.t('messages.action_wild_cards', lang=lang)}!** (≥7)\n\n"
                                    f"💀 **{self.t('messages.mega_attack', lang=lang)}:**\n"
                                    f"• {next_name}: +25 {self.t('messages.cards', lang=lang)}\n"
                                    f"• {self.t('messages.all_others', lang=lang)}: +5 {self.t('messages.cards', lang=lang)}",
                                    silent=True
                                )
                                # Next player draws 25
                                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                drawn = uno_logic.draw_cards(game['deck'], main_draw)
                                if drawn:
                                    game['hands'][next_player_id].extend(drawn)
                                
                                # All others draw 5
                                for pid in game['players']:
                                    if pid != uid and pid != next_player_id:
                                        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                        drawn = uno_logic.draw_cards(game['deck'], 5)
                                        if drawn:
                                            game['hands'][pid].extend(drawn)
                            else:
                                # Normal attack
                                next_name = self.get_bot_display_name(next_player_id, game)
                                await interaction.channel.send(
                                    f"⚔️ **{player_name} {self.t('messages.played_wild_draw_color', lang=lang)} FINAL ATTACK!**\n\n"
                                    f"🃏 **{self.t('messages.revealed_hand', lang=lang)}:** {hand_display}\n"
                                    f"**{action_count} {self.t('messages.action_wild_cards', lang=lang)}**\n\n"
                                    f"{next_name} {self.t('messages.draws_cards', lang=lang)} +{action_count} {self.t('messages.cards', lang=lang)}!",
                                    silent=True
                                )
                                # Next player draws
                                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                                drawn = uno_logic.draw_cards(game['deck'], main_draw)
                                if drawn:
                                    game['hands'][next_player_id].extend(drawn)
                            
                            # Check eliminations
                            for pid in list(game['players']):
                                if await self.check_elimination(game_id, game, pid, interaction.channel):
                                    continue
                        except Exception:
                            pass
                
                # Handle FLIP card in Flip mode
                if variant == 'flip' and effects.get('flip'):
                    flip_message = await self.flip_handler.handle_flip_card_played(game)
                    # After flip, update card reference to the flipped card from discard pile
                    # DON'T recalculate effects - they were already calculated before flip
                    if game['discard']:
                        card = game['discard'][-1]
                        # Update current_color to the flipped card's color (not wild cards)
                        if card['color'] != 'wild':
                            game['current_color'] = card['color']
                    # Notify about flip
                    try:
                        lang = self.get_lang(game)
                        flip_embed = discord.Embed(
                            title=f"🔄 {self.t('messages.flip_card', lang=lang).upper()}!",
                            description=flip_message,
                            color=0x9B59B6
                        )
                        await interaction.channel.send(embed=flip_embed, delete_after=5)
                    except Exception:
                        pass
                
                # Handle 7-0 Rule effects
                if effects.get('swap_hands'):
                    # Player played a 7 - choose someone to swap hands with
                    game['pending_seven_swap'] = {'player': uid, 'card': card}
                    
                    # Create player selection view
                    swap_view = discord.ui.View(timeout=None)
                    other_players = [p for p in game['players'] if p != uid]
                    
                    for target_player in other_players:
                        player_name = self.get_bot_display_name(target_player, game)
                        swap_view.add_item(discord.ui.Button(
                            label=f"Zamień z {player_name}",
                            custom_id=f"uno_swap_{game_id}|||{target_player}",
                            style=discord.ButtonStyle.primary
                        ))
                    
                    swap_embed = discord.Embed(
                        title=f"🔄 {self.t('messages.card_7_swap', lang=lang)}",
                        description=f"**{self.t('messages.played_card_label', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}\n\n⬇️ **{self.t('messages.select_player_swap', lang=lang)}**",
                        color=0x9b59b6
                    )
                    
                    swap_card_file = uno_logic.card_to_image(card)
                    if swap_card_file:
                        swap_embed.set_image(url=f"attachment://{swap_card_file.filename}")
                        await send_response(embed=swap_embed, view=swap_view, files=[swap_card_file], ephemeral=True)
                    else:
                        await send_response(embed=swap_embed, view=swap_view, ephemeral=True)
                    
                    return  # Wait for player selection
                    
                elif effects.get('rotate_hands'):
                    # Player played a 0 - rotate all hands in play direction
                    players = game['players']
                    hands = game['hands']
                    
                    direction_text = "w dół ⬇️" if game['direction'] == 1 else "w górę ⬆️"
                    
                    if game['direction'] == 1:
                        # Clockwise rotation: last player's hand goes to first
                        temp_hand = hands[players[-1]]
                        for i in range(len(players) - 1, 0, -1):
                            hands[players[i]] = hands[players[i-1]]
                        hands[players[0]] = temp_hand
                    else:
                        # Counter-clockwise rotation: first player's hand goes to last
                        temp_hand = hands[players[0]]
                        for i in range(len(players) - 1):
                            hands[players[i]] = hands[players[i+1]]
                        hands[players[-1]] = temp_hand
                    
                    # Update hand reference for current player
                    hand = hands[uid]
                    
                    # Send single notification about rotation
                    player_mentions = [f"<@{p}>" for p in players if not p.startswith('BOT_')]
                    rotate_notify = discord.Embed(
                        title=f"🔄 {self.t('messages.card_0_rotation', lang=lang)}",
                        description=f"<@{uid}> {self.t('messages.played_card_0', lang=lang)}\n\n**{self.t('messages.all_hands_shifted', lang=lang)} {direction_text}**\n\n{self.t('messages.check_your_turn', lang=lang)}",
                        color=0x9b59b6
                    )
                    
                    try:
                        await interaction.channel.send(
                            " ".join(player_mentions),
                            embed=rotate_notify,
                            delete_after=5
                        )
                    except Exception:
                        pass
                
                # Handle No Mercy Discard All Card
                if effects.get('discard_all'):
                    discard_color = effects['discard_all']
                    # Remove all cards matching the color of Discard All Card (already played)
                    cards_to_discard = [c for c in hand if c['color'] == discard_color]
                    if len(cards_to_discard) > 0:  # Any cards of that color left
                        # Remove matching cards from hand
                        hand[:] = [c for c in hand if c['color'] != discard_color]
                        # Add to discard pile
                        game['discard'].extend(cards_to_discard)

                        # Check for immediate win after discarding all matching cards
                        if len(hand) == 0:
                            channel = interaction.channel
                            if await self.handle_player_win(game_id, game, uid, interaction, channel):
                                return  # Game ended
                            
                            # Game continues (last standing mode)
                            current_player = game['players'][game['current_turn']]
                            embed_main, file_main = self.create_uno_game_embed(game)
                            view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                            try:
                                if game.get('messageId'):
                                    msg = interaction.channel.get_partial_message(game['messageId'])
                                    files_main = [file_main] if file_main else []
                                    await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                            except Exception:
                                pass
                            if current_player.startswith('BOT_'):
                                await self.play_bot_uno_turn(interaction.channel, game_id, game)
                            else:
                                await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                            return

                        # Refresh hand view silently (no notification needed, cards auto-removed)
                        hand_messages = game.get('hand_messages', {})
                        if uid in hand_messages:
                            try:
                                old_interaction, old_msg = hand_messages[uid]
                                hand_view = self.create_uno_hand_view(game_id, game, uid)
                                lang = self.get_lang(game)
                                hand_embed = discord.Embed(
                                    title=f"{uno_back} {self.t('hand.title', lang=lang)}",
                                    description=f"{self.t('messages.you_have', lang=lang)} **{len(hand)} {self.t('messages.cards', lang=lang)}**",
                                    color=0x3498db
                                )
                                await old_msg.edit(embed=hand_embed, view=hand_view, attachments=[])
                            except:
                                pass
                
                # Handle No Mercy Skip Everyone
                if effects.get('skip_everyone'):
                    # Current player gets to play again - don't change turn
                    pass  # Will be handled in turn logic below
                
                if effects.get('reverse'):
                    if len(game['players']) == 2:
                        # With 2 players, reverse = skip opponent (play again)
                        pass  # Don't change direction, current player keeps turn
                    else:
                        game['direction'] *= -1
                
                skip_turn = False
                if effects.get('skip_next'):
                    skip_turn = True
                if effects.get('draw_penalty'):
                    draw_amount = effects['draw_penalty']
                    
                    # Check if player has NO MERCY coin active
                    coins = game.get('coins', {})
                    if uid in coins and coins[uid].get('pending_no_mercy', False):
                        draw_amount *= 2
                        coins[uid]['pending_no_mercy'] = False  # Use it up
                        # Notify about doubled penalty
                        try:
                            mapping = uno_logic.load_emoji_mapping('no_mercy_plus')
                            nomercy_id = mapping.get('nomercy_coin.png')
                            nomercy_emoji = f"<:nomercy_coin:{nomercy_id}>" if nomercy_id else "💀"
                            await interaction.channel.send(
                                f"{nomercy_emoji} **NO MERCY!** Kara została podwojona: +{effects['draw_penalty']} → +{draw_amount}!",
                                silent=True,
                                delete_after=8
                            )
                        except Exception:
                            pass
                    
                    # Stack the draw penalty - next player can counter or must draw all
                    game['draw_stack'] = game.get('draw_stack', 0) + draw_amount
                
                # Check for stack_colors/stack_numbers continuation
                can_continue = False
                settings = game.get('settings', {})
                
                if settings.get('stack_colors', False):
                    # Can continue if has more cards of the same color
                    same_color_cards = [c for c in hand if c['color'] == card['color'] and c['color'] != 'wild']
                    if same_color_cards:
                        can_continue = True
                        
                if settings.get('stack_numbers', False):
                    # Can continue if has more cards of the same value
                    same_value_cards = [c for c in hand if c['value'] == card['value'] and c['color'] != 'wild']
                    if same_value_cards:
                        can_continue = True
                
                # Next turn
                if effects.get('play_again'):
                    # Card 10: Play Again - keep current turn (extra turn)
                    pass  # Don't change current_turn
                elif effects.get('skip_everyone'):
                    # Skip Everyone in No Mercy: Current player keeps turn
                    pass  # Don't change current_turn
                elif len(game['players']) == 2 and effects.get('reverse'):
                    # With 2 players and reverse, current player keeps their turn (doesn't change)
                    pass  # Don't change current_turn - player plays again
                elif skip_turn:
                    # Skip next player
                    game['current_turn'] = (game['current_turn'] + game['direction'] * 2) % len(game['players'])
                elif can_continue:
                    # Stack colors/numbers - player can continue playing
                    pass  # Don't change current_turn - player can play again
                else:
                    # Normal turn progression
                    game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
                
                # Check for win
                if len(hand) == 0:
                    channel = interaction.channel
                    if await self.handle_player_win(game_id, game, uid, interaction, channel):
                        return  # Game ended
                    
                    # Game continues (last standing mode) - Adjust current_turn if needed
                    if game['current_turn'] >= len(game['players']):
                        game['current_turn'] = 0
                        
                        current_player = game['players'][game['current_turn']]
                        embed_main, file_main = self.create_uno_game_embed(game)
                        view_main = self.create_uno_legacy_game_view(game_id, game, current_player)
                        try:
                            if game.get('messageId'):
                                msg = interaction.channel.get_partial_message(game['messageId'])
                                files_main = [file_main] if file_main else []
                                await msg.edit(embed=embed_main, view=view_main, attachments=files_main)
                        except Exception:
                            pass
                        
                        # Trigger bot or refresh next player's hand
                        if current_player.startswith('BOT_'):
                            await self.play_bot_uno_turn(interaction.channel, game_id, game)
                        else:
                            await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
                        return
                
                # Send combined message with card played and updated hand
                lang = self.get_lang(game)
                title = f"✅ {self.t('messages.card_played', lang=lang)}"
                
                # Override title for rotate_hands (card 0)
                if effects.get('rotate_hands'):
                    title = f"🔄 {self.t('messages.card_0_rotation', lang=lang)}"
                
                # Use helper method to generate effect notes
                extra_notes = self.format_card_effect_notes(game, effects, can_continue=can_continue, lang=lang)
                extra_text = "\n" + "\n".join(extra_notes) if extra_notes else ""
                
                hand_embed = discord.Embed(
                    title=title,
                    description=f"**{self.t('messages.played_card_label', lang=lang)}:** {uno_logic.card_to_string(card, lang=lang)}{extra_text}\n\n{self.t('messages.you_have_now', lang=lang)} **{len(hand)} {self.t('messages.cards_in_hand_count', lang=lang)}**",
                    color=0x2ecc71
                )
                
                # Attach played card image
                played_card_file = uno_logic.card_to_image(card)
                if played_card_file:
                    hand_embed.set_image(url=f"attachment://{played_card_file.filename}")
                    files = [played_card_file]
                else:
                    files = []
                
                hand_view = self.create_uno_hand_view(game_id, game, uid)
                
                # Try to edit existing hand message, or send new one
                try:
                    await edit_response(embed=hand_embed, view=hand_view, attachments=files)
                except:
                    # If editing fails (e.g., not from hand message), send new message and store it
                    await send_response(embed=hand_embed, view=hand_view, files=files, ephemeral=True)
                    try:
                        msg = await interaction.original_response()
                        game.setdefault('hand_messages', {})[uid] = (interaction, msg)
                    except:
                        pass
            
            # Update display
            current_player = game['players'][game['current_turn']]
            embed, card_file = self.create_uno_game_embed(game)
            
            view = self.create_uno_legacy_game_view(game_id, game, current_player)
            
            try:
                if game.get('messageId'):
                    msg = interaction.channel.get_partial_message(game['messageId'])
                    files = [card_file] if card_file else []
                    await msg.edit(embed=embed, view=view, attachments=files)
            except Exception:
                pass
            
            # Odśwież opponent_views dla trybu Flip
            await self.refresh_opponent_views(game)
            
            # Auto-refresh hand for next player
            if not current_player.startswith('BOT_'):
                await self.auto_refresh_player_hand(game_id, game, current_player, interaction.channel)
            
            # Bot turn
            if current_player.startswith('BOT_'):
                await asyncio.sleep(2)
                await self.play_bot_uno_turn(interaction.channel, game_id, game)
        

async def setup(bot):
    await bot.add_cog(UnoCog(bot))