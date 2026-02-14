"""
Texas Hold'em Poker - Professional UI/UX
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import time
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json
import requests
from io import BytesIO


# Cache
active_games = {}
CARD_EMOJI_MAPPING = {}
_poker_bot = None  # Global bot reference for card deck access

def load_card_emoji_mapping():
    global CARD_EMOJI_MAPPING
    try:
        with open('data/cards_emoji_mapping.json', 'r', encoding='utf-8') as f:
            CARD_EMOJI_MAPPING = json.load(f)
        print(f"✅ Poker: Loaded {len(CARD_EMOJI_MAPPING)} card emojis")
    except FileNotFoundError:
        print("❌ Poker: Missing cards_emoji_mapping.json file")
        CARD_EMOJI_MAPPING = {}

def create_settings_view(lobby_id, settings):
    """Creates view with poker settings"""
    settings_view = discord.ui.View(timeout=60)
    
    # Row 0: Game mode
    mode_btn = discord.ui.Button(
        label=f"🎮 Mode: {'FREE' if settings['game_mode'] == 'free' else 'PAID'}",
        style=discord.ButtonStyle.success if settings['game_mode'] == 'free' else discord.ButtonStyle.primary,
        custom_id=f"poker_setting_mode_{lobby_id}",
        row=0
    )
    settings_view.add_item(mode_btn)
    
    # Row 1: Stack/Buy-in
    if settings['game_mode'] == 'free':
        stack_btn = discord.ui.Button(
            label=f"📊 Stack: {settings['starting_stack']}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poker_setting_stack_{lobby_id}",
            row=1
        )
        settings_view.add_item(stack_btn)
    else:
        buyin_btn = discord.ui.Button(
            label=f"💰 Buy-in: {settings['buy_in']}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poker_setting_buyin_{lobby_id}",
            row=1
        )
        settings_view.add_item(buyin_btn)
    
    # Row 2: Blinds
    sb_btn = discord.ui.Button(
        label=f"🃏 Small Blind: {settings['small_blind']}",
        style=discord.ButtonStyle.secondary,
        custom_id=f"poker_setting_sb_{lobby_id}",
        row=2
    )
    bb_btn = discord.ui.Button(
        label=f"🃏 Big Blind: {settings['big_blind']}",
        style=discord.ButtonStyle.secondary,
        custom_id=f"poker_setting_bb_{lobby_id}",
        row=2
    )
    settings_view.add_item(sb_btn)
    settings_view.add_item(bb_btn)
    
    # Row 3: Max players
    max_btn = discord.ui.Button(
        label=f"👤 Max: {settings['max_players']}",
        style=discord.ButtonStyle.secondary,
        custom_id=f"poker_setting_max_{lobby_id}",
        row=3
    )
    settings_view.add_item(max_btn)
    
    return settings_view

def get_card_emoji(card):
    """Returns emoji for card from mapping. Card is tuple (rank, suit)"""
    # Card is tuple (rank, suit) e.g. ('A', '♠️')
    rank, suit = card
    
    # Symbol mapping to file names
    rank_map = {
        'J': 'walet', 'Q': 'dama', 'K': 'krol', 'A': 'as',
        '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
        '7': '7', '8': '8', '9': '9', '10': '10'
    }
    suit_map = {
        '♠️': 'pik', '♥️': 'kier', '♦️': 'karo', '♣️': 'trefl'
    }
    
    rank_name = rank_map.get(rank, rank)
    suit_name = suit_map.get(suit, 'pik')
    
    # Face cards (walet, dama, krol) don't have .png in name, rest (including aces) do
    if rank in ['J', 'Q', 'K']:
        filename = f"{rank_name}_{suit_name}"
    else:
        filename = f"{rank_name}_{suit_name}.png"
    
    emoji_id = CARD_EMOJI_MAPPING.get(filename)
    
    if emoji_id:
        return f"<:card:{emoji_id}>"
    
    # Text fallback
    rank_display = rank
    return f"`{rank_display}{suit}`"

def get_card_back_emoji():
    """Returns card back emoji"""
    return "🎴"

def get_player_background_url(guild_id, user_id):
    """Gets player background URL from shop (disabled for now)"""
    # TODO: Re-implement with proper profile system
    return None

def get_player_card_deck(guild_id, user_id):
    """Gets player's active card deck from economy system"""
    global _poker_bot
    
    if _poker_bot:
        try:
            economy_cog = _poker_bot.get_cog('Economy')
            if economy_cog:
                return economy_cog.get_user_card_deck(user_id)
        except Exception as e:
            print(f"⚠️ Error getting player card deck: {e}")
    
    return 'classic'  # Default deck if economy not available


class PokerGame:
    """Game class"""
    
    def __init__(self, channel, lobby_data):
        self.channel = channel
        self.host_id = lobby_data['hostId']
        self.settings = lobby_data['settings']
        self.players = []  # {user, stack, cards, bet, folded, all_in, is_bot, bot_name}
        self.lobby_message_id = None  # Lobby message ID for editing
        self.waiting_for_player = None  # Current player ID
        self.action_event = asyncio.Event()  # Event for action synchronization
        
        # Set starting stack based on mode
        if self.settings['game_mode'] == 'paid':
            starting_stack = self.settings['buy_in']
        else:
            starting_stack = self.settings['starting_stack']
        
        # Convert lobby players to game players
        for player_data in lobby_data['players']:
            if player_data['is_bot']:
                self.players.append({
                    'user': type('obj', (object,), {
                        'id': player_data['id'],
                        'mention': player_data['mention'],
                        'display_name': player_data['display_name']
                    }),
                    'stack': starting_stack,
                    'cards': [],
                    'bet': 0,
                    'folded': False,
                    'all_in': False,
                    'is_bot': True,
                    'bot_name': player_data['display_name']
                })
            else:
                self.players.append({
                    'user': player_data['user'],
                    'stack': starting_stack,
                    'cards': [],
                    'bet': 0,
                    'folded': False,
                    'all_in': False,
                    'is_bot': False,
                    'bot_name': None
                })
        
        self.dealer_index = 0
        self.current_player = 0
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.round = 'preflop'
        self.game_active = True
        self.hand_messages = {}  # Przechowuj ephemeral wiadomości graczy {user_id: message}
    
    def new_hand(self):
        """Nowe rozdanie"""
        self.deck = create_deck()
        random.shuffle(self.deck)
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.round = 'preflop'
        
        for player in self.players:
            player['cards'] = []
            player['bet'] = 0
            player['folded'] = False
            player['all_in'] = False
        
        # Remove players without stack
        self.players = [p for p in self.players if p['stack'] > 0]
        if len(self.players) < 2:
            self.game_active = False
            return
        
        # Rozdaj 2 karty
        for _ in range(2):
            for player in self.players:
                player['cards'].append(self.deck.pop())
        
        # Blindy
        sb_idx = (self.dealer_index + 1) % len(self.players)
        bb_idx = (self.dealer_index + 2) % len(self.players)
        
        sb_amt = min(self.settings['small_blind'], self.players[sb_idx]['stack'])
        bb_amt = min(self.settings['big_blind'], self.players[bb_idx]['stack'])
        
        self.players[sb_idx]['bet'] = sb_amt
        self.players[sb_idx]['stack'] -= sb_amt
        self.players[bb_idx]['bet'] = bb_amt
        self.players[bb_idx]['stack'] -= bb_amt
        
        self.pot = sb_amt + bb_amt
        self.current_bet = bb_amt
        self.current_player = (bb_idx + 1) % len(self.players)
    
    def action_call(self, player):
        to_call = self.current_bet - player['bet']
        if to_call <= 0:
            return True, 0
        if player['stack'] <= to_call:
            amount = player['stack']
            player['stack'] = 0
            player['bet'] += amount
            player['all_in'] = True
            self.pot += amount
            return True, amount
        player['stack'] -= to_call
        player['bet'] += to_call
        self.pot += to_call
        return True, to_call
    
    def action_raise(self, player, amount):
        total_bet = self.current_bet + amount
        to_pay = total_bet - player['bet']
        if to_pay > player['stack']:
            return False, 0
        if to_pay == player['stack']:
            player['all_in'] = True
        player['stack'] -= to_pay
        player['bet'] = total_bet
        self.pot += to_pay
        self.current_bet = total_bet
        return True, to_pay
    
    def action_fold(self, player):
        player['folded'] = True
        return True
    
    def bot_action(self, player):
        """AI bota"""
        to_call = self.current_bet - player['bet']
        roll = random.random()
        
        if to_call == 0:
            return 'check', 0
        
        if roll < 0.3:
            self.action_fold(player)
            return 'fold', 0
        elif roll < 0.9:
            success, amt = self.action_call(player)
            return 'call', amt
        else:
            raise_amt = self.settings['big_blind'] * 2
            success, amt = self.action_raise(player, raise_amt)
            if success:
                return 'raise', amt
            success, amt = self.action_call(player)
            return 'call', amt
    
    def next_player(self):
        start = self.current_player
        while True:
            self.current_player = (self.current_player + 1) % len(self.players)
            p = self.players[self.current_player]
            if not p['folded'] and not p['all_in']:
                if p['bet'] < self.current_bet:
                    return p
            if self.current_player == start:
                return None
    
    def next_round(self):
        for p in self.players:
            p['bet'] = 0
        self.current_bet = 0
        
        if self.round == 'preflop':
            self.community_cards.extend([self.deck.pop(), self.deck.pop(), self.deck.pop()])
            self.round = 'flop'
        elif self.round == 'flop':
            self.community_cards.append(self.deck.pop())
            self.round = 'turn'
        elif self.round == 'turn':
            self.community_cards.append(self.deck.pop())
            self.round = 'river'
        elif self.round == 'river':
            self.round = 'showdown'
            return
        
        self.current_player = (self.dealer_index + 1) % len(self.players)
        while self.players[self.current_player]['folded'] or self.players[self.current_player]['all_in']:
            self.current_player = (self.current_player + 1) % len(self.players)
    
    def showdown(self):
        active = [p for p in self.players if not p['folded']]
        
        # Jeśli wszyscy dali fold - nie powinno się zdarzyć, ale dla bezpieczeństwa
        if len(active) == 0:
            return []
        
        if len(active) == 1:
            winner = active[0]
            winner['stack'] += self.pot
            return [(winner, self.pot, None)]
        
        results = []
        for player in active:
            all_cards = player['cards'] + self.community_cards
            best_hand, ranking, high_cards = get_best_hand(all_cards)
            results.append((player, best_hand, (ranking, high_cards)))
        
        results.sort(key=lambda x: (x[2][0], x[2][1]), reverse=True)
        winners = [results[0]]
        for i in range(1, len(results)):
            if compare_hands(results[i][2], results[0][2]) == 0:
                winners.append(results[i])
            else:
                break
        
        win_amt = self.pot // len(winners)
        for winner, hand, evaluation in winners:
            winner['stack'] += win_amt
        
        return [(w[0], win_amt, w[2]) for w in winners]


class PokerGameView(discord.ui.View):
    """Stały widok - podgląd kart"""
    
    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game
    
    @discord.ui.button(label="🃏 My cards", style=discord.ButtonStyle.gray, custom_id="poker_view_cards", row=0)
    async def show_cards(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = None
        for p in self.game.players:
            if not p['is_bot'] and p['user'].id == interaction.user.id:
                player = p
                break
        
        if not player:
            await interaction.response.send_message("❌ You are not in this game!", ephemeral=True)
            return
        
        if not player['cards']:
            await interaction.response.send_message("❌ You don't have any cards yet!", ephemeral=True)
            return
        
        # IMPORTANT: Defer immediately to avoid 3-second timeout
        await interaction.response.defer(ephemeral=True)
        
        # Konwertuj karty do formatu parsera
        hole_cards_str = []
        for card in player['cards']:
            rank, suit = card
            suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
            hole_cards_str.append(f"{rank}{suit_symbols.get(suit, 's')}")
        
        # Pobierz tło gracza
        guild_id = interaction.guild.id if interaction.guild else None
        background_url = get_player_background_url(guild_id, interaction.user.id)
        
        # Pobierz talię kart
        card_deck = get_player_card_deck(guild_id, interaction.user.id)
        
        # Generuj obrazek ręki (w osobnym wątku aby nie blokować event loop)
        hand_image = await asyncio.to_thread(create_hand_image, hole_cards_str, background_url, card_deck)
        
        # Also show best hand if there are community cards
        
        embed = discord.Embed(
            title="🃏 Your cards",
            description="Your hole cards:",
            color=discord.Color.gold()
        )
        
        # Dodaj obrazek ręki
        embed.set_image(url=f"attachment://{hand_image.filename}")
        
        if self.game.community_cards:
            all_cards = player['cards'] + self.game.community_cards
            best_hand, ranking, high_cards = get_best_hand(all_cards)
            hand_name = get_hand_name(ranking)
            best_cards_display = " ".join([get_card_emoji(c) for c in best_hand])
            embed.add_field(
                name=f"🏆 Twój najlepszy układ: {hand_name}",
                value=best_cards_display,
                inline=False
            )
        
        embed.add_field(name="💰 Stack", value=f"{player['stack']} 💠", inline=True)
        embed.add_field(name="🎴 Pula", value=f"{self.game.pot} 💠", inline=True)
        
        # If it's this player's turn, add action buttons
        if hasattr(self.game, 'waiting_for_player') and self.game.waiting_for_player == interaction.user.id:
            action_view = PokerActionView(self.game, player)
            msg_obj = await interaction.followup.send(embed=embed, view=action_view, file=hand_image, ephemeral=True, wait=True)
            # Save message for auto-refresh
            self.game.hand_messages[interaction.user.id] = msg_obj
        else:
            # Without buttons - just preview
            msg_obj = await interaction.followup.send(embed=embed, file=hand_image, ephemeral=True, wait=True)
            # Save message for auto-refresh
            self.game.hand_messages[interaction.user.id] = msg_obj
    
    @discord.ui.button(label="📊 Hand Rankings", style=discord.ButtonStyle.secondary, custom_id="poker_hierarchy", row=0)
    async def show_hierarchy(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Hierarchia układów w Texas Hold'em",
            description="Od najsilniejszego do najsłabszego:",
            color=discord.Color.blue()
        )
        
        # Przykładowe karty dla każdego układu
        royal = f"{get_card_emoji(('10', '♠️'))} {get_card_emoji(('J', '♠️'))} {get_card_emoji(('Q', '♠️'))} {get_card_emoji(('K', '♠️'))} {get_card_emoji(('A', '♠️'))}"
        straight_flush = f"{get_card_emoji(('5', '♥️'))} {get_card_emoji(('6', '♥️'))} {get_card_emoji(('7', '♥️'))} {get_card_emoji(('8', '♥️'))} {get_card_emoji(('9', '♥️'))}"
        four = f"{get_card_emoji(('K', '♠️'))} {get_card_emoji(('K', '♥️'))} {get_card_emoji(('K', '♦️'))} {get_card_emoji(('K', '♣️'))} {get_card_emoji(('2', '♠️'))}"
        full = f"{get_card_emoji(('Q', '♠️'))} {get_card_emoji(('Q', '♥️'))} {get_card_emoji(('Q', '♦️'))} {get_card_emoji(('J', '♠️'))} {get_card_emoji(('J', '♥️'))}"
        flush = f"{get_card_emoji(('A', '♦️'))} {get_card_emoji(('10', '♦️'))} {get_card_emoji(('7', '♦️'))} {get_card_emoji(('5', '♦️'))} {get_card_emoji(('3', '♦️'))}"
        straight = f"{get_card_emoji(('9', '♠️'))} {get_card_emoji(('8', '♥️'))} {get_card_emoji(('7', '♦️'))} {get_card_emoji(('6', '♣️'))} {get_card_emoji(('5', '♠️'))}"
        three = f"{get_card_emoji(('J', '♠️'))} {get_card_emoji(('J', '♥️'))} {get_card_emoji(('J', '♦️'))} {get_card_emoji(('A', '♠️'))} {get_card_emoji(('9', '♥️'))}"
        two_pair = f"{get_card_emoji(('10', '♠️'))} {get_card_emoji(('10', '♥️'))} {get_card_emoji(('7', '♦️'))} {get_card_emoji(('7', '♣️'))} {get_card_emoji(('K', '♠️'))}"
        pair = f"{get_card_emoji(('A', '♠️'))} {get_card_emoji(('A', '♥️'))} {get_card_emoji(('K', '♦️'))} {get_card_emoji(('Q', '♣️'))} {get_card_emoji(('J', '♠️'))}"
        high = f"{get_card_emoji(('A', '♠️'))} {get_card_emoji(('K', '♥️'))} {get_card_emoji(('Q', '♦️'))} {get_card_emoji(('8', '♣️'))} {get_card_emoji(('3', '♠️'))}"
        
        embed.add_field(
            name="1. 👑 Royal Flush",
            value=f"10-J-Q-K-A of the same suit\n{royal}",
            inline=False
        )
        embed.add_field(
            name="2. 💎 Straight Flush",
            value=f"5 consecutive cards of the same suit\n{straight_flush}",
            inline=False
        )
        embed.add_field(
            name="3. 🎴 Kareta (Four of a Kind)",
            value=f"4 cards of the same rank\n{four}",
            inline=False
        )
        embed.add_field(
            name="4. 🏠 Full House",
            value=f"Trójka + Para\n{full}",
            inline=False
        )
        embed.add_field(
            name="5. 🌈 Flush",
            value=f"5 cards of the same suit\n{flush}",
            inline=False
        )
        embed.add_field(
            name="6. 📈 Strit (Straight)",
            value=f"5 kolejnych kart\n{straight}",
            inline=False
        )
        embed.add_field(
            name="7. 🎯 Trójka (Three of a Kind)",
            value=f"3 cards of the same rank\n{three}",
            inline=False
        )
        embed.add_field(
            name="8. 👯 Dwie Pary (Two Pair)",
            value=f"Dwie różne pary\n{two_pair}",
            inline=False
        )
        embed.add_field(
            name="9. 🎲 Para (Pair)",
            value=f"2 cards of the same rank\n{pair}",
            inline=False
        )
        embed.add_field(
            name="10. 🃏 Wysoka Karta (High Card)",
            value=f"Najwyższa karta w ręce\n{high}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PokerActionView(discord.ui.View):
    """Akcje gracza"""
    
    def __init__(self, game, player):
        super().__init__(timeout=60)
        self.game = game
        self.player = player
        
        to_call = game.current_bet - player['bet']
        if to_call == 0:
            self.check_btn.label = "✅ Check"
        else:
            self.check_btn.label = f"📞 Call {to_call}"
        
        if to_call >= player['stack']:
            self.raise_btn.disabled = True
    
    @discord.ui.button(label="✅ Check/Call", style=discord.ButtonStyle.green, row=0)
    async def check_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player['user'].id:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        to_call = self.game.current_bet - self.player['bet']
        self.game.action_call(self.player)
        
        # Save action
        if to_call == 0:
            self.player['last_action'] = "✅ CHECK"
        else:
            self.player['last_action'] = f"📞 CALL {to_call}"
        
        self.player['acted_this_round'] = True
        
        # Disable wszystkie przyciski
        for item in self.children:
            item.disabled = True
        
        # Odblokuj czekanie na akcję
        self.game.action_event.set()
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="📈 Raise", style=discord.ButtonStyle.blurple, row=0)
    async def raise_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player['user'].id:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        modal = RaiseModal(self.game, self.player, self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="❌ Fold", style=discord.ButtonStyle.red, row=1)
    async def fold_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player['user'].id:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        self.game.action_fold(self.player)
        self.player['last_action'] = "❌ FOLD"
        self.player['acted_this_round'] = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Unlock waiting for action
        self.game.action_event.set()
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="💰 All-In", style=discord.ButtonStyle.danger, row=1)
    async def allin_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player['user'].id:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        amt = self.player['stack']
        self.game.action_raise(self.player, amt)
        self.player['last_action'] = f"💰 ALL-IN {amt}"
        self.player['acted_this_round'] = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Odblokuj czekanie na akcję
        self.game.action_event.set()
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="🚪 Leave", style=discord.ButtonStyle.secondary, row=2)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player['user'].id:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        self.game.action_fold(self.player)
        self.player['last_action'] = "🚪 LEFT GAME"
        self.player['acted_this_round'] = True
        self.player['folded'] = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Unlock waiting for action
        self.game.action_event.set()
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"🚪 **{self.player['user'].display_name}** left the game!", ephemeral=False)
        self.stop()


class RaiseModal(discord.ui.Modal, title="Raise"):
    amount = discord.ui.TextInput(label="Kwota", placeholder="Min: 2x Big Blind", required=True, max_length=10)
    
    def __init__(self, game, player, view):
        super().__init__()
        self.game = game
        self.player = player
        self.view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            amt = int(self.amount.value)
            min_raise = self.game.settings['big_blind'] * 2
            if amt < min_raise:
                await interaction.response.send_message(f"❌ Min: {min_raise}", ephemeral=True)
                return
            success, paid = self.game.action_raise(self.player, amt)
            if not success:
                await interaction.response.send_message("❌ Not enough stack!", ephemeral=True)
                return
            
            # Save action
            self.player['last_action'] = f"📈 RAISE {paid}"
            self.player['acted_this_round'] = True
            
            # Disable all buttons in view
            for item in self.view.children:
                item.disabled = True
            
            # Unlock waiting for action
            self.game.action_event.set()
            
            await interaction.response.edit_message(view=self.view)
            self.view.stop()
        except ValueError:
            await interaction.response.send_message("❌ Enter a number!", ephemeral=True)


class CustomBetModal(discord.ui.Modal, title='Custom Bet Amount'):
    """Modal for custom bet input"""
    
    bet_input = discord.ui.TextInput(
        label='Enter bet amount',
        placeholder='Enter amount between 50 and your balance...',
        required=True,
        min_length=2,
        max_length=10
    )
    
    def __init__(self, user_id, balance, game_type="poker"):
        super().__init__()
        self.user_id = user_id
        self.balance = balance
        self.game_type = game_type
        self.selected_bet = None
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bet = int(self.bet_input.value)
            if bet < 50:
                await interaction.response.send_message("❌ Minimum bet is 50 coins!", ephemeral=True)
                return
            if bet > self.balance:
                await interaction.response.send_message(f"❌ You only have {self.balance} coins!", ephemeral=True)
                return
            self.selected_bet = bet
            await interaction.response.send_message(f"✅ Bet set to {bet} 💠", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)


class BetSelectView(discord.ui.View):
    """View for selecting bet amount"""
    
    def __init__(self, user_id, balance, game_type="poker"):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_bet = None
        self.game_type = game_type
        self.balance = balance
        
        # Add bet buttons based on balance
        bet_options = [50, 100, 250, 500, 1000]
        for bet in bet_options:
            if bet <= balance:
                btn = discord.ui.Button(
                    label=f"{bet} 💠",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"bet_{bet}"
                )
                btn.callback = self.create_callback(bet)
                self.add_item(btn)
        
        # Add custom bet button
        custom_btn = discord.ui.Button(
            label="Custom 🎲",
            style=discord.ButtonStyle.secondary,
            custom_id="bet_custom"
        )
        custom_btn.callback = self.custom_bet_callback
        self.add_item(custom_btn)
    
    def create_callback(self, bet_amount):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
                return
            self.selected_bet = bet_amount
            await interaction.response.defer()
            self.stop()
        return callback
    
    async def custom_bet_callback(self, interaction: discord.Interaction):
        """Handle custom bet button"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
            return
        
        modal = CustomBetModal(self.user_id, self.balance, self.game_type)
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.selected_bet:
            self.selected_bet = modal.selected_bet
            self.stop()


class PokerLobbyView(discord.ui.View):
    """Professional lobby"""
    
    def __init__(self, lobby_id, lobby, economy_cog):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.lobby = lobby
        self.economy_cog = economy_cog
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on lobby status"""
        real_players = [p for p in self.lobby['players'] if not p.get('is_bot')]
        
        # Find start button and disable if insufficient real players
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "poker_lobby_start":
                # Need at least 2 real players for poker
                child.disabled = len(real_players) < 2
    
    @discord.ui.button(label="🤖➕", style=discord.ButtonStyle.secondary, custom_id="poker_lobby_bot_add", row=0)
    async def bot_add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        if len(self.lobby['players']) >= self.lobby['settings']['max_players']:
            await interaction.response.send_message("❌ Lobby is full!", ephemeral=True)
            return
        
        # Add bot - fetch name from owner_ids
        bot_num = sum(1 for p in self.lobby['players'] if p['is_bot']) + 1
        
        # Get bot instance from interaction
        bot_instance = interaction.client
        owner_ids = getattr(bot_instance.get_cog('PokerCog'), 'owner_ids', [])
        
        # Fetch username from Discord
        bot_name = f'Bot {bot_num}'
        if owner_ids and len(owner_ids) >= bot_num:
            try:
                owner_id = owner_ids[(bot_num - 1) % len(owner_ids)]
                user = await bot_instance.fetch_user(owner_id)
                bot_name = user.display_name or user.name
            except:
                pass
        
        self.lobby['players'].append({
            'id': f'bot_{bot_num}',
            'mention': f'🤖 {bot_name}',
            'display_name': bot_name,
            'is_bot': True
        })
        self.lobby['last_activity'] = time.time()
        
        # WAŻNE: defer() PRZED edit()
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="🤖➖", style=discord.ButtonStyle.secondary, custom_id="poker_lobby_bot_remove", row=0)
    async def bot_remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        # Find last bot
        bot_players = [p for p in self.lobby['players'] if p['is_bot']]
        if not bot_players:
            await interaction.response.send_message("❌ No bots!", ephemeral=True)
            return
        
        # Remove last bot
        last_bot = bot_players[-1]
        self.lobby['players'].remove(last_bot)
        self.lobby['last_activity'] = time.time()
        
        # IMPORTANT: defer() BEFORE edit()
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, custom_id="poker_lobby_join", row=1)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        
        # Check if full
        if len(self.lobby['players']) >= self.lobby['settings']['max_players']:
            await interaction.response.send_message("❌ Lobby is full!", ephemeral=True)
            return
        
        # Check if already in
        if any(p['user'].id == interaction.user.id for p in self.lobby['players'] if not p['is_bot']):
            await interaction.response.send_message("❌ You're already in the lobby!", ephemeral=True)
            return
        
        # Check balance
        if self.lobby['settings']['game_mode'] == 'paid':
            buy_in = self.lobby['settings']['buy_in']
            balance = self.economy_cog.get_balance(interaction.user.id)
            if balance < buy_in:
                await interaction.response.send_message(f"❌ You need **{buy_in}** 💠", ephemeral=True)
                return
            # Take buy-in
            self.economy_cog.remove_coins(interaction.user.id, buy_in)
        
        # Add player
        self.lobby['players'].append({
            'user': interaction.user,
            'is_bot': False
        })
        self.lobby['last_activity'] = time.time()
        
        # IMPORTANT: defer() BEFORE edit()
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, custom_id="poker_lobby_leave", row=1)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Find player
        player = None
        for i, p in enumerate(self.lobby['players']):
            if not p['is_bot'] and p['user'].id == interaction.user.id:
                player = p
                self.lobby['players'].pop(i)
                break
        
        if not player:
            await interaction.response.send_message("❌ You are not in the lobby!", ephemeral=True)
            return
        
        # Return buy-in only in paid mode
        if self.lobby['settings']['game_mode'] == 'paid':
            buy_in = self.lobby['settings']['buy_in']
            self.economy_cog.add_coins(interaction.user.id, buy_in, "poker_left_lobby")
        
        # IMPORTANT: defer() BEFORE edit()
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, custom_id="poker_lobby_settings", row=2)
    async def settings_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        # Create ephemeral view with settings using helper function
        settings_view = create_settings_view(self.lobby_id, self.lobby['settings'])
        
        embed = discord.Embed(
            title="⚙️ Poker Settings",
            description="Click a button to change value",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, view=settings_view, ephemeral=True)
    
    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, custom_id="poker_lobby_start", row=2)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        # Count only real players (not bots) - need at least 2 for poker
        real_players = [p for p in self.lobby['players'] if not p.get('is_bot')]
        if len(real_players) < 2:
            await interaction.response.send_message("❌ Need at least 2 real players!", ephemeral=True)
            return
        
        # Confirm interaction before stopping the View
        await interaction.response.send_message("🎮 Starting the game...", ephemeral=True)
        self.lobby['started'] = True
        self.stop()
    
    def create_lobby_embed(self):
        """Embed lobby"""
        settings = self.lobby['settings']
        
        # Lista graczy
        player_list = []
        for p in self.lobby['players']:
            if p['is_bot']:
                player_list.append(f"🤖 {p['display_name']}")
            else:
                player_list.append(p['user'].mention)
        
        players_text = "\n".join(player_list) if player_list else "*No players*"
        
        embed = discord.Embed(
            title="🎰 Texas Hold'em Poker",
            description=f"Host: <@{self.lobby['hostId']}>\nPlayers: {len(self.lobby['players'])}/{settings['max_players']}\n\nWaiting for players...",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="👥 Players", value=players_text, inline=False)
        
        # Description of settings depending on the mode
        mode_text = "🎮 **FREE**" if settings['game_mode'] == 'free' else "💰 **PAID**"
        if settings['game_mode'] == 'free':
            stack_info = f"📊 Starting stack: **{settings['starting_stack']}** 💠"
        else:
            stack_info = f"💰 Buy-in: **{settings['buy_in']}** 💠"
        
        embed.add_field(
            name="⚙️ Settings",
            value=f"{mode_text}\n"
                  f"{stack_info}\n"
                  f"🃏 Blinds: **{settings['small_blind']}/{settings['big_blind']}**\n"
                  f"👤 Max players: **{settings['max_players']}**",
            inline=False
        )
        
        return embed




class PokerCog(commands.Cog):
    def __init__(self, bot):
        global _poker_bot
        self.bot = bot
        _poker_bot = bot  # Set global reference
        load_card_emoji_mapping()
        
        # Load owner_ids from config.json
        self.owner_ids = []
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.owner_ids = config.get('owner_ids', [])
        except Exception as e:
            print(f"❌ Error loading owner_ids from config.json: {e}")
    
    def get_economy_cog(self):
        """Get economy cog for balance operations"""
        return self.bot.get_cog('Economy')
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle settings button interactions"""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get('custom_id', '')
        
        # Check if it's a poker settings button
        if custom_id.startswith('poker_setting_'):
            await self.handle_poker_settings(interaction, custom_id)
    
    @app_commands.command(name="poker", description="Texas Hold'em Poker")
    @app_commands.describe(mode="Game mode: fast (5-card vs Tryn) or long (Texas Hold'em lobby)")
    @app_commands.choices(mode=[
        app_commands.Choice(name="🎯 Fast - Quick game vs Dealer", value="fast"),
        app_commands.Choice(name="🎲 Long - Full Texas Hold'em with lobby", value="long")
    ])
    async def poker(self, interaction: discord.Interaction, mode: str = "fast"):
        """Start a Texas Hold'em poker game"""
        if mode == "fast":
            await self.play_fast_poker(interaction)
            return
        
        uid = str(interaction.user.id)
        economy_cog = self.get_economy_cog()
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
            return
        
        # Stwórz lobby
        lobby_id = f"poker_{interaction.channel.id}_{int(time.time())}"
        lobby = {
            'game': 'poker',
            'hostId': uid,
            'players': [
                {
                    'user': interaction.user,
                    'is_bot': False
                }
            ],
            'settings': {
                'game_mode': 'free',  # 'free' or 'paid'
                'starting_stack': 1000,  # for free mode
                'buy_in': 100,  # for paid mode
                'small_blind': 5,
                'big_blind': 10,
                'max_players': 10
            },
            'messageId': None,
            'last_activity': time.time(),
            'started': False
        }
        
        # Take buy-in from host only in paid mode
        if lobby['settings']['game_mode'] == 'paid':
            buy_in = lobby['settings']['buy_in']
            balance = economy_cog.get_balance(interaction.user.id)
            if balance < buy_in:
                await interaction.response.send_message(f"❌ You need **{buy_in}** 💠", ephemeral=True)
                return
            economy_cog.remove_coins(interaction.user.id, buy_in)
        
        self.bot.active_lobbies[lobby_id] = lobby
        
        view = PokerLobbyView(lobby_id, lobby, economy_cog)
        lobby['view'] = view  # Save view in lobby
        embed = view.create_lobby_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        lobby['messageId'] = msg.id
        
        # Wait for start
        await view.wait()
        
        if lobby.get('started'):
            await self.start_game(lobby, interaction.channel, economy_cog)
        else:
            # Cancelled - return buy-in only in paid mode
            if lobby['settings']['game_mode'] == 'paid':
                buy_in = lobby['settings']['buy_in']
                for p in lobby['players']:
                    if not p['is_bot']:
                        economy_cog.add_coins(p['user'].id, buy_in, "poker_cancelled")
            
            if lobby_id in self.bot.active_lobbies:
                del self.bot.active_lobbies[lobby_id]
    
    async def start_game(self, lobby, channel, economy_cog):
        """Start game"""
        # Check minimum players
        if len(lobby['players']) < 2:
            await channel.send("❌ Need at least 2 players to start poker!")
            return
        
        lobby_id = f"poker_{channel.id}_{int(lobby['last_activity'])}"
        
        if lobby_id in self.bot.active_lobbies:
            del self.bot.active_lobbies[lobby_id]
        
        game = PokerGame(channel, lobby)
        game.lobby_message_id = lobby.get('messageId')  # Save lobby message ID
        game.economy_cog = economy_cog  # Pass economy cog to game
        active_games[channel.id] = game
        
        game.new_hand()
        
        # Główna pętla gry
        while game.game_active:
            # Wyświetl aktualny stan
            await self.display_state(game)
            
            # Odśwież ręce graczy po rozdaniu nowych kart
            await self.refresh_all_hands(game)
            
            # Resetuj flagę "działał w tej rundzie" i akcje
            for p in game.players:
                p['acted_this_round'] = False
                if not p['folded'] and not p['all_in']:
                    p['last_action'] = ''
            
            # Runda licytacji
            betting_round_active = True
            while betting_round_active:
                player = game.players[game.current_player]
                
                # Sprawdź czy pozostał tylko jeden aktywny gracz (nie fold, nie all-in)
                active_players = [p for p in game.players if not p['folded'] and not p['all_in']]
                if len(active_players) == 0:
                    # Wszyscy dali fold lub all-in - kończymy rundę
                    betting_round_active = False
                    break
                
                # Pomiń gracza który sfoldował lub all-in
                if player['folded'] or player['all_in']:
                    game.current_player = (game.current_player + 1) % len(game.players)
                    continue
                
                # Sprawdź czy wszyscy wyrównali stawkę
                if all(p['bet'] == game.current_bet and p.get('acted_this_round', False) for p in active_players):
                    betting_round_active = False
                    break
                
                # Pomiń jeśli gracz już wyrównał i działał
                if player['bet'] == game.current_bet and player.get('acted_this_round', False):
                    game.current_player = (game.current_player + 1) % len(game.players)
                    continue
                
                player['acted_this_round'] = True
                
                # Bot
                if player['is_bot']:
                    action, amt = game.bot_action(player)
                    
                    # Save action
                    if action == 'check':
                        player['last_action'] = "✅ CHECK"
                    elif action == 'call':
                        player['last_action'] = f"📞 CALL {amt}"
                    elif action == 'raise':
                        player['last_action'] = f"📈 RAISE {amt}"
                    elif action == 'fold':
                        player['last_action'] = "❌ FOLD"
                    
                    # Odśwież stół po akcji bota
                    await self.display_state(game)
                    
                    await asyncio.sleep(0.5)
                    game.current_player = (game.current_player + 1) % len(game.players)
                    continue
                
                # Człowiek - ustaw waiting_for_player i czekaj na akcję
                game.waiting_for_player = player['user'].id
                game.action_event.clear()  # Reset event
                
                # Aktualizuj stół aby pokazać czyj jest ruch
                await self.display_state(game)
                
                # Odśwież ręke gracza którego kolej
                await self.refresh_all_hands(game, only_user_id=player['user'].id)
                
                # Czekaj na akcję gracza (max 120 sekund)
                try:
                    await asyncio.wait_for(game.action_event.wait(), timeout=120.0)
                except asyncio.TimeoutError:
                    # Timeout - fold
                    game.action_fold(player)
                    player['last_action'] = "❌ FOLD (timeout)"
                    player['acted_this_round'] = True
                
                game.waiting_for_player = None
                
                # Odśwież stół po akcji gracza
                await self.display_state(game)
                
                # Sprawdź czy po akcji gracza pozostał tylko jeden aktywny gracz
                active_check = [p for p in game.players if not p['folded']]
                if len(active_check) <= 1:
                    betting_round_active = False
                    break
                
                game.current_player = (game.current_player + 1) % len(game.players)
            
            # Sprawdź czy tylko jeden gracz pozostał
            active = [p for p in game.players if not p['folded']]
            if len(active) <= 1:
                winners = game.showdown()
                
                # Jeśli są zwycięzcy, wyświetl showdown
                if winners:
                    await self.display_showdown(game, winners)
                
                # Sprawdź czy tylko jeden gracz ma żetony
                players_with_chips = [p for p in game.players if p['stack'] > 0]
                if len(players_with_chips) == 1:
                    final_winner = players_with_chips[0]
                    if final_winner['is_bot']:
                        winner_name = f"🤖 {final_winner['bot_name']}"
                    else:
                        winner_name = final_winner['user'].mention
                    
                    # Display final message in table embed
                    await self.display_game_over(game, winner_name, final_winner['stack'])
                    game.game_active = False
                    game.game_ended_with_winner = True  # Flag that game ended via display_game_over
                    break
                
                # New deal - check if game is still active
                if not game.game_active:
                    break
                    
                game.dealer_index = (game.dealer_index + 1) % len(game.players)
                game.new_hand()
                await asyncio.sleep(3)
                
                # Sprawdź ponownie czy gra jest aktywna przed odświeżeniem
                if not game.game_active:
                    break
                    
                # Odśwież ręce graczy - nowe karty
                await self.refresh_all_hands(game)
                await asyncio.sleep(2)
                continue
            
            # Następna faza lub showdown
            if game.round == 'river':
                winners = game.showdown()
                
                # Jeśli są zwycięzcy, wyświetl showdown
                if winners:
                    await self.display_showdown(game, winners)
                
                # Sprawdź czy tylko jeden gracz ma żetony
                players_with_chips = [p for p in game.players if p['stack'] > 0]
                if len(players_with_chips) == 1:
                    final_winner = players_with_chips[0]
                    if final_winner['is_bot']:
                        winner_name = f"🤖 {final_winner['bot_name']}"
                    else:
                        winner_name = final_winner['user'].mention
                    
                    # Wyświetl komunikat końcowy w embedzie stołu
                    await self.display_game_over(game, winner_name, final_winner['stack'])
                    game.game_active = False
                    game.game_ended_with_winner = True  # Flaga że gra zakończyła się przez display_game_over
                    break
                
                # Nowe rozdanie
                game.dealer_index = (game.dealer_index + 1) % len(game.players)
                game.new_hand()
                await asyncio.sleep(3)
                # Odśwież ręce graczy - nowe karty
                await self.refresh_all_hands(game)
                await asyncio.sleep(2)
            else:
                game.next_round()
                # Refresh player hands after round change (new community cards = new best hand)
                await self.refresh_all_hands(game)
                await asyncio.sleep(1)
        
        # End - return stacks only in paid mode
        if game.settings['game_mode'] == 'paid':
            for p in game.players:
                if p['stack'] > 0 and not p['is_bot']:
                    game.economy_cog.add_coins(p['user'].id, p['stack'], "poker_winnings")
        
        if channel.id in active_games:
            del active_games[channel.id]
        
        # If game ended via display_game_over, don't delete message or send new one
        if not hasattr(game, 'game_ended_with_winner') or not game.game_ended_with_winner:
            # Delete table message only if game didn't end via winner
            if hasattr(game, 'lobby_message_id') and game.lobby_message_id:
                try:
                    msg = channel.get_partial_message(game.lobby_message_id)
                    await msg.delete()
                except:
                    pass
            
            await channel.send("🏁 **Game ended!**")
    
    async def play_fast_poker(self, interaction: discord.Interaction, preset_bet: int = None):
        """Fast 5-card poker vs Tryn bot"""
        economy_cog = self.get_economy_cog()
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
            return
        
        # Check balance
        balance = economy_cog.get_balance(interaction.user.id)
        
        if balance < 50:
            await interaction.response.send_message("❌ You need at least 50 coins to play!", ephemeral=True)
            return
        
        # Use preset bet or show selection
        if preset_bet:
            bet_amount = preset_bet
            if balance < bet_amount:
                await interaction.response.send_message(f"❌ You need at least {bet_amount} coins!", ephemeral=True)
                return
            await interaction.response.defer()
        else:
            # Show bet selection
            bet_view = BetSelectView(interaction.user.id, balance, "poker")
            embed = discord.Embed(
                title="5-Card Poker - Select Bet",
                description=f"Balance: **{balance}** 💠\nSelect your bet amount:",
                color=discord.Color.gold()
            )
            
            await interaction.response.send_message(embed=embed, view=bet_view, ephemeral=True)
            await bet_view.wait()
            
            if not bet_view.selected_bet:
                return
            
            bet_amount = bet_view.selected_bet
        
        # Deduct bet
        economy_cog.remove_coins(interaction.user.id, bet_amount)
        
        # Create deck and deal (using proper card format)
        deck = create_deck()
        random.shuffle(deck)
        
        # Deal 5 cards to each (cards are already in (rank, suit) format)
        player_cards = [deck.pop() for _ in range(5)]
        tryn_cards = [deck.pop() for _ in range(5)]
        
        # Evaluate hands
        player_hand = evaluate_hand(player_cards)
        tryn_hand = evaluate_hand(tryn_cards)
        
        # Determine winner
        result = compare_hands(player_hand, tryn_hand)
        
        player_hand_name = get_hand_name(player_hand[0])
        tryn_hand_name = get_hand_name(tryn_hand[0])
        
        # Get player's card deck
        player_deck = get_player_card_deck(interaction.guild.id if interaction.guild else None, interaction.user.id)
        
        # Create visual comparison image
        comparison_image = await asyncio.to_thread(
            create_fast_poker_comparison_image,
            interaction.user.display_name,
            player_cards,
            player_hand_name,
            tryn_cards,
            tryn_hand_name,
            result,
            player_deck
        )
        
        # Calculate winnings
        if result == 1:
            winnings = bet_amount * 2
            economy_cog.add_coins(interaction.user.id, winnings, "fast_poker_win")
            result_text = f"**You win!**\n+{winnings - bet_amount} coins"
            color = discord.Color.gold()
        elif result == -1:
            result_text = f"**Dealer wins!**\n-{bet_amount} coins"
            color = discord.Color.red()
        else:
            economy_cog.add_coins(interaction.user.id, bet_amount, "fast_poker_tie")
            result_text = "**Draw!**\nBet returned"
            color = discord.Color.blue()
        
        # Create embed
        embed = discord.Embed(
            title="5-Card Poker",
            description=result_text,
            color=color
        )
        
        new_balance = economy_cog.get_balance(interaction.user.id)
        embed.add_field(name="Balance", value=f"{new_balance} coins", inline=False)
        
        embed.set_image(url=f"attachment://{comparison_image.filename}")
        
        # Add "Play Again" and "Same Bet" buttons
        view = discord.ui.View(timeout=None)
        
        play_again_btn = discord.ui.Button(label="Play Again", style=discord.ButtonStyle.primary)
        same_bet_btn = discord.ui.Button(label=f"Same Bet ({bet_amount})", style=discord.ButtonStyle.success)
        disclaimer_btn = discord.ui.Button(label="⚠️", style=discord.ButtonStyle.secondary, row=1)
        
        async def play_again_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id != interaction.user.id:
                await btn_interaction.response.send_message("❌ This is not your game!", ephemeral=True)
                return
            await self.play_fast_poker(btn_interaction)
        
        async def same_bet_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id != interaction.user.id:
                await btn_interaction.response.send_message("❌ This is not your game!", ephemeral=True)
                return
            await self.play_fast_poker(btn_interaction, preset_bet=bet_amount)
        
        async def disclaimer_callback(btn_interaction: discord.Interaction):
            disclaimer_text = """
**⚠️ Our Stance on Gambling**

It is important to remember that **gambling is not a way to make money**, real or fake. It is a form of entertainment and should be treated as such.

**If you or someone you know is struggling with gambling addiction, please seek help.**

Additionally, please remember that **the odds are always in favor of the house. The house always wins.**

**⚠️ IMPORTANT:** You should **NEVER** spend real money to gamble in games. If someone is offering to sell you in-game currency for real money, they are breaking our listed rules and should be reported.

🆘 **Need Help?** 
• National Council on Problem Gambling: 1-800-522-4700
• Visit: ncpgambling.org
"""
            embed = discord.Embed(
                title="⚠️ Responsible Gaming Information",
                description=disclaimer_text,
                color=discord.Color.orange()
            )
            embed.set_footer(text="Please gamble responsibly. This is for entertainment only.")
            await btn_interaction.response.send_message(embed=embed, ephemeral=True)
        
        play_again_btn.callback = play_again_callback
        same_bet_btn.callback = same_bet_callback
        disclaimer_btn.callback = disclaimer_callback
        view.add_item(play_again_btn)
        view.add_item(same_bet_btn)
        view.add_item(disclaimer_btn)
        
        # Send to channel (non-ephemeral)
        await interaction.followup.send(embed=embed, file=comparison_image, view=view)
    
    async def display_state(self, game):
        """Wyświetl stan gry"""
        # Names for rounds
        round_names = {
            'preflop': 'Pre-Flop',
            'flop': 'Flop',
            'turn': 'Turn',
            'river': 'River'
        }
        round_name = round_names.get(game.round, game.round.upper())
        
        # Convert community cards to parser format
        community_cards_str = []
        for card in game.community_cards:
            rank, suit = card
            suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
            community_cards_str.append(f"{rank}{suit_symbols.get(suit, 's')}")
        
        # Prepare player data
        # Get guild_id
        guild_id = game.channel.guild.id if hasattr(game.channel, 'guild') and game.channel.guild else None
        
        players_data = []
        for i, p in enumerate(game.players):
            # Convert player cards
            player_cards = []
            for card in p.get('cards', []):
                rank, suit = card
                suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
                player_cards.append(f"{rank}{suit_symbols.get(suit, 's')}")
            
            # Get player deck
            player_deck = 'classic'
            if not p['is_bot']:
                player_deck = get_player_card_deck(guild_id, p['user'].id)
            
            players_data.append({
                'name': p['bot_name'] if p['is_bot'] else p['user'].display_name,
                'cards': player_cards,
                'stack': p['stack'],
                'folded': p['folded'],
                'is_current': i == game.current_player,
                'card_deck': player_deck
            })
        
        # Get host background
        background_url = get_player_background_url(guild_id, game.host_id)
        
        # Cards on tables always classic (everyone sees the same)
        card_deck = 'classic'
        
        # Generate table image (in separate thread to avoid blocking event loop)
        table_image = await asyncio.to_thread(
            create_poker_table_image,
            community_cards_str,
            game.pot,
            round_name,
            game.current_bet,
            players_data,
            False,
            background_url,
            card_deck
        )
        
        # Check whose turn and add timeout info with Discord timestamp
        current_player_info = ""
        if game.waiting_for_player:
            for p in game.players:
                if not p['is_bot'] and p['user'].id == game.waiting_for_player:
                    timeout_timestamp = int(time.time()) + 120
                    current_player_info = f"\n⏰ {p['user'].mention} - your turn ends <t:{timeout_timestamp}:R>"
                    break
        
        embed = discord.Embed(
            title=f"🎰 Texas Hold'em - {round_name}",
            description=f"Click the button below to see your cards{current_player_info}",
            color=discord.Color.gold()
        )
        
        # Add table image
        embed.set_image(url=f"attachment://{table_image.filename}")
        
        players_txt = ""
        for i, p in enumerate(game.players):
            # Base player name
            if p['is_bot']:
                name = f"🤖 **{p['bot_name']}**"
            else:
                name = p['user'].mention
            
            # Player action
            action = ""
            if p['folded']:
                action = "❌ FOLD"
            elif p['all_in']:
                action = "💰 ALL-IN"
            elif i == game.current_player:
                action = "⏰ Ruch"
            else:
                # Show player's last action
                last_action = p.get('last_action', '')
                if last_action:
                    action = last_action
            
            # Format: [Nickname] Action: Stack 💠
            if action:
                players_txt += f"{name} **{action}**: {p['stack']} 💠\n"
            else:
                players_txt += f"{name}: {p['stack']} 💠\n"
        
        embed.add_field(name="👥 Players", value=players_txt, inline=False)
        
        # View with button to see cards
        game_view = PokerGameView(game)
        
        # Edit lobby message
        if hasattr(game, 'lobby_message_id') and game.lobby_message_id:
            try:
                msg = game.channel.get_partial_message(game.lobby_message_id)
                await msg.edit(embed=embed, view=game_view, attachments=[table_image])
                # Auto-refresh only when the round changes (new community cards)
                # NOT after every move - it freezes the bot
                return
            except:
                pass
        
        # Fallback - send new message
        await game.channel.send(embed=embed, view=game_view, file=table_image)
    
    async def display_showdown(self, game, winners):
        """Display results"""
        
        # Convert cards to parser format
        community_cards_str = []
        for card in game.community_cards:
            rank, suit = card
            suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
            community_cards_str.append(f"{rank}{suit_symbols.get(suit, 's')}")
        
        # Get guild_id
        guild_id = game.channel.guild.id if hasattr(game.channel, 'guild') and game.channel.guild else None
        
        # Prepare player data with revealed cards
        players_data = []
        for i, p in enumerate(game.players):
            # Convert player cards
            player_cards = []
            for card in p.get('cards', []):
                rank, suit = card
                suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
                player_cards.append(f"{rank}{suit_symbols.get(suit, 's')}")
            
            # Get player deck
            player_deck = 'classic'
            if not p['is_bot']:
                player_deck = get_player_card_deck(guild_id, p['user'].id)
            
            players_data.append({
                'name': p['bot_name'] if p['is_bot'] else p['user'].display_name,
                'cards': player_cards,
                'stack': p['stack'],
                'folded': p['folded'],
                'is_current': False,
                'card_deck': player_deck
            })
        
        # Get host background
        background_url = get_player_background_url(guild_id, game.host_id)
        
        # Cards on tables always classic (everyone sees the same)
        card_deck = 'classic'
        
        # Generate table image with revealed cards (in separate thread to not block event loop)
        table_image = await asyncio.to_thread(
            create_poker_table_image,
            community_cards_str,
            game.pot,
            "Showdown",
            0,
            players_data,
            True,  # Reveal cards!
            background_url,
            card_deck
        )
        
        embed = discord.Embed(title="🏆 Showdown - End of hand!", color=discord.Color.green())
        
        # Add table image with revealed cards
        embed.set_image(url=f"attachment://{table_image.filename}")
        
        # Show winners with winnings
        winners_text = ""
        for winner, amt, evaluation in winners:
            if winner['is_bot']:
                name = f"🤖 {winner['bot_name']}"
            else:
                name = winner['user'].mention
            
            if evaluation:
                ranking = evaluation[0]
                hand_name = get_hand_name(ranking)
            else:
                hand_name = "Wszyscy sfoldowali"
            
            winners_text += f"👑 **{name}** - {hand_name} - Wygrana: **{amt}** 💠\n"
        
        embed.add_field(name="🎉 Zwycięzcy", value=winners_text, inline=False)
        
        # Edytuj wiadomość lobby zamiast wysyłać nową
        game_view = PokerGameView(game)
        if hasattr(game, 'lobby_message_id') and game.lobby_message_id:
            try:
                msg = game.channel.get_partial_message(game.lobby_message_id)
                await msg.edit(embed=embed, view=game_view, attachments=[table_image])
                return
            except:
                pass
        
        # Fallback - wyślij nową
        await game.channel.send(embed=embed, view=game_view, file=table_image)
        
        # Auto-refresh wszystkich otwartych rąk
        await self.refresh_all_hands(game)
    
    async def refresh_all_hands(self, game, only_user_id=None):
        """Automatically refreshes all open player hands (or just one)"""
        
        for user_id, msg in list(game.hand_messages.items()):
            # If only_user_id is set, skip other players
            if only_user_id is not None and user_id != only_user_id:
                continue
            try:
                # Find player
                player = None
                for p in game.players:
                    if not p['is_bot'] and p['user'].id == user_id:
                        player = p
                        break
                
                if not player or not player['cards']:
                    continue
                
                # convert player cards to parser format
                hole_cards_str = []
                for card in player['cards']:
                    rank, suit = card
                    suit_symbols = {'♠️': 's', '♥️': 'h', '♦️': 'd', '♣️': 'c'}
                    hole_cards_str.append(f"{rank}{suit_symbols.get(suit, 's')}")
                
                # Get player background
                guild_id = game.channel.guild.id if hasattr(game.channel, 'guild') and game.channel.guild else None
                background_url = get_player_background_url(guild_id, p['user'].id)
                
                # Get player deck
                card_deck = get_player_card_deck(guild_id, p['user'].id)
                
                # Generate hand image (in a separate thread to avoid blocking the event loop)
                hand_image = await asyncio.to_thread(create_hand_image, hole_cards_str, background_url, card_deck)
                
                embed = discord.Embed(
                    title="🃏 Your Cards",
                    description="Your hole cards:",
                    color=discord.Color.gold()
                )
                
                # Add hand image
                embed.set_image(url=f"attachment://{hand_image.filename}")
                
                if game.community_cards:
                    all_cards = player['cards'] + game.community_cards
                    best_hand, ranking, high_cards = get_best_hand(all_cards)
                    hand_name = get_hand_name(ranking)
                    best_cards_display = " ".join([get_card_emoji(c) for c in best_hand])
                    embed.add_field(
                        name=f"🏆 Your best hand: {hand_name}",
                        value=best_cards_display,
                        inline=False
                    )
                
                embed.add_field(name="💰 Stack", value=f"{player['stack']} 💠", inline=True)
                embed.add_field(name="🎴 Pot", value=f"{game.pot} 💠", inline=True)
                
                # If it's the player's turn, add action buttons
                if hasattr(game, 'waiting_for_player') and game.waiting_for_player == user_id:
                    action_view = PokerActionView(game, player)
                    await msg.edit(embed=embed, view=action_view, attachments=[hand_image])
                else:
                    await msg.edit(embed=embed, attachments=[hand_image])
            except:
                # If failed to update, remove from list
                game.hand_messages.pop(user_id, None)
    
    async def display_game_over(self, game, winner_name, final_stack):
        """Display final game message in table embed"""
        embed = discord.Embed(
            title="🎊 GAME ENDED! 🎊",
            description=f"👑 Tournament winner: {winner_name}\n💰 Final stack: {final_stack} 💠",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🏁 Game ended!",
            value="Congratulations to the winner!",
            inline=False
        )
        
        # Edit lobby message
        if hasattr(game, 'lobby_message_id') and game.lobby_message_id:
            try:
                msg = game.channel.get_partial_message(game.lobby_message_id)
                await msg.edit(embed=embed, view=None, attachments=[])
                return
            except:
                pass
        
        # Fallback - send a new message
        await game.channel.send(embed=embed)
    
    async def handle_poker_settings(self, interaction: discord.Interaction, cid: str):
        """Handles poker settings buttons"""
        # Extract lobby_id from custom_id (e.g. "poker_setting_mode_poker_123_456" -> "poker_123_456")
        parts = cid.split('_')
        if len(parts) >= 5:
            lobby_id = f"{parts[-3]}_{parts[-2]}_{parts[-1]}"
        else:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
            return
        
        lobby = self.bot.active_lobbies.get(lobby_id)
        
        if not lobby:
            await interaction.response.send_message("❌ Game already started or lobby doesn't exist!", ephemeral=True)
            return
        
        if str(interaction.user.id) != lobby['hostId']:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        # Find lobby message
        try:
            channel = interaction.channel
            lobby_msg = await channel.fetch_message(lobby['messageId'])
        except:
            await interaction.response.send_message("❌ Can't find lobby!", ephemeral=True)
            return
        
        # Game mode
        if 'poker_setting_mode_' in cid:
            # Toggle between free/paid
            current_mode = lobby['settings']['game_mode']
            new_mode = 'paid' if current_mode == 'free' else 'free'
            lobby['settings']['game_mode'] = new_mode
            
            # Edit lobby
            view = lobby.get('view')
            if view:
                await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
            
            # Edit ephemeral settings
            settings_view = create_settings_view(lobby_id, lobby['settings'])
            await interaction.response.edit_message(view=settings_view)
        
        # Starting stack (free mode)
        elif 'poker_setting_stack_' in cid:
            modal = discord.ui.Modal(title="Starting Stack")
            stack_input = discord.ui.TextInput(
                label="Starting Stack",
                placeholder="1000",
                default=str(lobby['settings']['starting_stack']),
                max_length=10,
                required=True
            )
            modal.add_item(stack_input)
            
            async def on_submit_stack(modal_interaction: discord.Interaction):
                try:
                    value = int(stack_input.value)
                    if value < 100:
                        await modal_interaction.response.send_message("❌ Min: 100", ephemeral=True)
                        return
                    lobby['settings']['starting_stack'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Stack: **{value}**", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_stack
            await interaction.response.send_modal(modal)
            return
        
        # Buy-in (paid mode)
        elif 'poker_setting_buyin_' in cid:
            modal = discord.ui.Modal(title="Buy-in")
            buyin_input = discord.ui.TextInput(
                label="Buy-in (entry cost)",
                placeholder="100",
                default=str(lobby['settings']['buy_in']),
                max_length=10,
                required=True
            )
            modal.add_item(buyin_input)
            
            async def on_submit_buyin(modal_interaction: discord.Interaction):
                try:
                    value = int(buyin_input.value)
                    if value < 1:
                        await modal_interaction.response.send_message("❌ Min: 1", ephemeral=True)
                        return
                    lobby['settings']['buy_in'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Buy-in: **{value}** 💠", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_buyin
            await interaction.response.send_modal(modal)
            return
        
        # Small Blind
        elif 'poker_setting_sb_' in cid:
            modal = discord.ui.Modal(title="Small Blind")
            sb_input = discord.ui.TextInput(
                label="Small Blind",
                placeholder="5",
                default=str(lobby['settings']['small_blind']),
                max_length=10,
                required=True
            )
            modal.add_item(sb_input)
            
            async def on_submit_sb(modal_interaction: discord.Interaction):
                try:
                    value = int(sb_input.value)
                    if value < 1:
                        await modal_interaction.response.send_message("❌ Min: 1", ephemeral=True)
                        return
                    lobby['settings']['small_blind'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Small Blind: **{value}**", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_sb
            await interaction.response.send_modal(modal)
            return
        
        # Big Blind
        elif 'poker_setting_bb_' in cid:
            modal = discord.ui.Modal(title="Big Blind")
            bb_input = discord.ui.TextInput(
                label="Big Blind",
                placeholder="10",
                default=str(lobby['settings']['big_blind']),
                max_length=10,
                required=True
            )
            modal.add_item(bb_input)
            
            async def on_submit_bb(modal_interaction: discord.Interaction):
                try:
                    value = int(bb_input.value)
                    sb = lobby['settings']['small_blind']
                    if value < sb * 2:
                        await modal_interaction.response.send_message(f"❌ Big Blind must be min 2x Small Blind ({sb*2})", ephemeral=True)
                        return
                    lobby['settings']['big_blind'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edytuj ephemeral settings
                    settings_view = create_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Big Blind: **{value}**", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_bb
            await interaction.response.send_modal(modal)
            return
        
        # Max players
        elif 'poker_setting_max_' in cid:
            modal = discord.ui.Modal(title="Max players")
            max_input = discord.ui.TextInput(
                label="Max players (2-9)",
                placeholder="6",
                default=str(lobby['settings']['max_players']),
                max_length=1,
                required=True
            )
            modal.add_item(max_input)
            
            async def on_submit_max(modal_interaction: discord.Interaction):
                try:
                    value = int(max_input.value)
                    if not 2 <= value <= 9:
                        await modal_interaction.response.send_message("❌ Range: 2-9", ephemeral=True)
                        return
                    lobby['settings']['max_players'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Max: **{value}**", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_max
            await interaction.response.send_modal(modal)
            return
        
        # Refresh lobby after changing mode
        view = PokerLobbyView(lobby_id, lobby)
        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)


async def setup(bot):
    await bot.add_cog(PokerCog(bot))

import random

def create_deck():
    """Creates a 52-card deck."""
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    suits = ['♠️', '♥️', '♦️', '♣️']
    return [(rank, suit) for rank in ranks for suit in suits]

def format_card(card):
    """Formats card to readable string."""
    return f"{card[0]}{card[1]}"

def evaluate_hand(cards):
    """
    Evaluates poker hand strength (5 cards).
    Returns tuple: (ranking, high_cards)
    Ranking: 9=Royal Flush, 8=Straight Flush, 7=Four of a Kind, 6=Full House,
             5=Flush, 4=Straight, 3=Three of a Kind, 2=Two Pair, 1=Pair, 0=High Card
    """
    if len(cards) != 5:
        return (0, [])
    
    # Sort cards by value
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    
    ranks = [rank_values[card[0]] for card in cards]
    suits = [card[1] for card in cards]
    ranks.sort(reverse=True)
    
    # count ranks
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    counts = sorted(rank_counts.values(), reverse=True)
    unique_ranks = sorted(rank_counts.keys(), reverse=True)
    
    # Check for flush
    is_flush = len(set(suits)) == 1
    
    # Check for straight
    is_straight = False
    if len(set(ranks)) == 5:
        if ranks[0] - ranks[4] == 4:
            is_straight = True
        # Check for Ace-2-3-4-5 (wheel)
        elif ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            ranks = [5, 4, 3, 2, 1]  # Ace has lower value in wheel
    
    # Royal Flush: 10-J-Q-K-A of the same suit
    if is_flush and is_straight and ranks[0] == 14 and ranks[4] == 10:
        return (9, ranks)
    
    # Straight Flush
    if is_flush and is_straight:
        return (8, ranks)
    
    # Four of a Kind
    if counts == [4, 1]:
        # Return four of a kind and kicker
        four_rank = [r for r, c in rank_counts.items() if c == 4][0]
        kicker = [r for r, c in rank_counts.items() if c == 1][0]
        return (7, [four_rank, four_rank, four_rank, four_rank, kicker])
    
    # Full House
    if counts == [3, 2]:
        three_rank = [r for r, c in rank_counts.items() if c == 3][0]
        pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
        return (6, [three_rank, three_rank, three_rank, pair_rank, pair_rank])
    
    # Flush
    if is_flush:
        return (5, ranks)
    
    # Straight
    if is_straight:
        return (4, ranks)
    
    # Three of a Kind
    if counts == [3, 1, 1]:
        three_rank = [r for r, c in rank_counts.items() if c == 3][0]
        kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
        return (3, [three_rank, three_rank, three_rank] + kickers)
    
    # Two Pair
    if counts == [2, 2, 1]:
        pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
        kicker = [r for r, c in rank_counts.items() if c == 1][0]
        return (2, [pairs[0], pairs[0], pairs[1], pairs[1], kicker])
    
    # Pair
    if counts == [2, 1, 1, 1]:
        pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
        kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
        return (1, [pair_rank, pair_rank] + kickers)
    
    # High Card
    return (0, ranks)

def get_best_hand(cards):
    """
        Znajduje najlepszy układ 5 kart z 7 dostępnych.
        Zwraca (best_hand, ranking, high_cards)
    """
    from itertools import combinations
    
    if len(cards) < 5:
        return ([], 0, [])
    
    best_ranking = -1
    best_high_cards = []
    best_hand = []
    
    # Check all combinations of 5 cards
    for combo in combinations(cards, 5):
        ranking, high_cards = evaluate_hand(list(combo))
        if ranking > best_ranking or (ranking == best_ranking and high_cards > best_high_cards):
            best_ranking = ranking
            best_high_cards = high_cards
            best_hand = list(combo)
    
    return (best_hand, best_ranking, best_high_cards)

def compare_hands(hand1_data, hand2_data):
    """
    Compares two hands.
    hand_data can be (hand, ranking, high_cards) or (ranking, high_cards)
    Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
    """
    # Handle both formats: (hand, ranking, high_cards) or (ranking, high_cards)
    if len(hand1_data) == 3:
        ranking1 = hand1_data[1]
        high_cards1 = hand1_data[2]
    else:
        ranking1 = hand1_data[0]
        high_cards1 = hand1_data[1]
    
    if len(hand2_data) == 3:
        ranking2 = hand2_data[1]
        high_cards2 = hand2_data[2]
    else:
        ranking2 = hand2_data[0]
        high_cards2 = hand2_data[1]
    
    if ranking1 > ranking2:
        return 1
    elif ranking1 < ranking2:
        return -1
    else:
        # Same ranking, compare high cards
        
        for i in range(len(high_cards1)):
            if high_cards1[i] > high_cards2[i]:
                return 1
            elif high_cards1[i] < high_cards2[i]:
                return -1
        
        return 0

def get_hand_name(ranking):
    """Returns hand name based on ranking."""
    names = {
        9: "Royal Flush",
        8: "Straight Flush",
        7: "Four of a Kind",
        6: "Full House",
        5: "Flush",
        4: "Straight",
        3: "Three of a Kind",
        2: "Two Pair",
        1: "Pair",
        0: "High Card"
    }
    return names.get(ranking, "Unknown hand")

"""
Visualization of poker table using PIL
"""

# Colors
FELT_GREEN = (53, 101, 77)  # Dark green table
FELT_DARK = (35, 70, 55)    # Darker green for border
CARD_WHITE = (255, 255, 255)
CARD_BORDER = (200, 200, 200)
TEXT_WHITE = (255, 255, 255)
TEXT_GOLD = (255, 215, 0)
POT_BG = (70, 120, 90)

# Sizes
CARD_WIDTH = 90
CARD_HEIGHT = 132
CARD_SPACING = 15
TABLE_WIDTH = 800
TABLE_HEIGHT = 500

# Cache for loaded PNG cards
CARD_IMAGE_CACHE = {}
DEFAULT_CARD_DECK = 'classic'  # Default deck

def get_card_image(rank, suit, deck='classic', size=None):
    """Loads card image from local PNG file"""
    # Convert Unicode suit to letter if needed
    suit_unicode_to_letter = {
        '♠️': 's', '♠': 's',
        '♥️': 'h', '♥': 'h',
        '♦️': 'd', '♦': 'd',
        '♣️': 'c', '♣': 'c'
    }
    
    # Convert suit to letter
    if suit in suit_unicode_to_letter:
        suit = suit_unicode_to_letter[suit]
    
    # Suit name mapping
    suit_names = {'h': 'kier', 'd': 'karo', 'c': 'trefl', 's': 'pik'}
    suit_name = suit_names.get(suit, 'pik')
    
    # Rank name mapping for file names
    rank_names = {
        'j': 'walet', 'q': 'dama', 'k': 'krol', 'a': 'as',
        '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
        '7': '7', '8': '8', '9': '9', '10': '10'
    }
    rank_name = rank_names.get(rank.lower(), rank)
    
    # File name
    filename = f"{rank_name}_{suit_name}.png"
    
    # File path
    if deck == 'classic':
        # Classic cards are in assets/cards/classic/
        card_path = os.path.join('assets', 'cards', 'classic', filename)
    else:
        # Other decks are in assets/cards/{deck_name}/
        card_path = os.path.join('assets', 'cards', deck, filename)
        if not os.path.exists(card_path):
            # Fallback to classic deck
            card_path = os.path.join('assets', 'cards', 'classic', filename)
    
    # Cache key
    cache_key = f"{deck}_{filename}_{size}"
    
    if cache_key in CARD_IMAGE_CACHE:
        return CARD_IMAGE_CACHE[cache_key]
    
    try:
        if os.path.exists(card_path):
            img = Image.open(card_path)
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            # Convert to RGBA
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            CARD_IMAGE_CACHE[cache_key] = img
            return img
    except Exception as e:
        print(f"❌ Error loading card {filename}: {e}")
    
    return None

def get_font(size, bold=False):
    """Get font from assets/fonts"""
    try:
        # Use Arial from assets/fonts (bold uses same file with larger size simulation)
        return ImageFont.truetype("assets/fonts/Arial.ttf", size)
    except:
        try:
            # Fallback to system fonts
            if bold:
                return ImageFont.truetype("arialbd.ttf", size)
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()

def draw_card(draw, x, y, rank, suit, width=CARD_WIDTH, height=CARD_HEIGHT, img_base=None, deck='classic'):
    """Draws a single card using local PNG files"""
    # Card background (in case PNG fails to load)
    draw.rounded_rectangle(
        [(x, y), (x + width, y + height)],
        radius=8,
        fill=CARD_WHITE,
        outline=CARD_BORDER,
        width=2
    )
    
    if img_base:
        # Get card image from PNG file
        card_size = (int(width * 0.95), int(height * 0.95))  # 95% of card size
        card_img = get_card_image(rank, suit, deck=deck, size=card_size)
        
        if card_img:
            # Paste card image (centered)
            try:
                offset_x = x + (width - card_size[0]) // 2
                offset_y = y + (height - card_size[1]) // 2
                img_base.paste(card_img, (offset_x, offset_y), card_img)
                return
            except Exception as e:
                print(f"❌ Error pasting card {rank}{suit}: {e}")
    
    # Fallback - use simple symbols
    # Convert Unicode suit to letter if needed
    suit_unicode_to_letter = {
        '♠️': 's', '♠': 's',
        '♥️': 'h', '♥': 'h',
        '♦️': 'd', '♦': 'd',
        '♣️': 'c', '♣': 'c'
    }
    
    suit_letter = suit_unicode_to_letter.get(suit, suit)
    
    suit_display = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
    suit_colors = {'h': (220, 20, 60), 'd': (220, 20, 60), 'c': (0, 0, 0), 's': (0, 0, 0)}
    
    suit_symbol = suit_display.get(suit_letter, '♠')
    color = suit_colors.get(suit_letter, (0, 0, 0))
    
    # Card rank (large)
    rank_font = get_font(32, bold=True)
    suit_font = get_font(36, bold=True)
    
    # Rank text (top left corner)
    rank_text = rank.upper() if rank in ['j', 'q', 'k', 'a'] else str(rank)
    draw.text((x + 8, y + 5), rank_text, fill=color, font=rank_font)
    
    # Suit (below rank)
    draw.text((x + 8, y + 40), suit_symbol, fill=color, font=suit_font)
    
    # Large center symbol
    center_font = get_font(48, bold=True)
    center_bbox = draw.textbbox((0, 0), suit_symbol, font=center_font)
    center_width = center_bbox[2] - center_bbox[0]
    center_height = center_bbox[3] - center_bbox[1]
    center_x = x + (width - center_width) // 2
    center_y = y + (height - center_height) // 2
    draw.text((center_x, center_y), suit_symbol, fill=color, font=center_font)

def draw_card_back(draw, x, y, width=CARD_WIDTH, height=CARD_HEIGHT, img_base=None, deck='classic'):
    """Rysuje rewers karty - wczytuje back.png z odpowiedniego folderu decku"""
    # Tło (fallback)
    draw.rounded_rectangle(
        [(x, y), (x + width, y + height)],
        radius=8,
        fill=(30, 60, 150),
        outline=CARD_BORDER,
        width=2
    )
    
    if img_base:
        # Get card back image from back.png file
        back_path = os.path.join('assets', 'cards', deck, 'back.png')
        if not os.path.exists(back_path):
            # Fallback to classic back
            back_path = os.path.join('assets', 'cards', 'classic', 'back.png')
        
        # Cache key
        cache_key = f"{deck}_back_{width}x{height}"
        
        if cache_key in CARD_IMAGE_CACHE:
            back_img = CARD_IMAGE_CACHE[cache_key]
        else:
            try:
                if os.path.exists(back_path):
                    back_img = Image.open(back_path)
                    back_size = (int(width * 0.95), int(height * 0.95))
                    back_img = back_img.resize(back_size, Image.Resampling.LANCZOS)
                    if back_img.mode != 'RGBA':
                        back_img = back_img.convert('RGBA')
                    CARD_IMAGE_CACHE[cache_key] = back_img
                else:
                    back_img = None
            except Exception as e:
                print(f"❌ Error loading card back {deck}: {e}")
                back_img = None
        
        if back_img:
            # Paste card back image (centered)
            try:
                back_size = (int(width * 0.95), int(height * 0.95))
                offset_x = x + (width - back_size[0]) // 2
                offset_y = y + (height - back_size[1]) // 2
                img_base.paste(back_img, (offset_x, offset_y), back_img)
                return
            except Exception as e:
                print(f"❌ Error pasting card back {deck}: {e}")
    
    # Fallback - pattern
    spacing = max(10, int(width / 8))
    dot_size = max(5, int(width / 12))
    pattern_color = (50, 100, 200)
    for i in range(5, height - 5, spacing):
        for j in range(5, width - 5, spacing):
            draw.ellipse([(x + j, y + i), (x + j + dot_size, y + i + dot_size)], fill=pattern_color)

def parse_card(card_str):
    """Parsuje kartę 'Ah' -> ('a', 'h') lub tuple (rank, suit) -> (rank, suit)"""
    # If already a tuple, return as is
    if isinstance(card_str, tuple) and len(card_str) == 2:
        return card_str
    
    # Parse string
    if isinstance(card_str, str) and len(card_str) >= 2:
        return card_str[:-1].lower(), card_str[-1].lower()
    
    return None, None

def create_poker_table_image(community_cards, pot, round_name="Pre-Flop", current_bet=0, players=None, show_cards=False, background_url=None, card_deck='classic'):
    """
    Creates an image of the poker table with community cards and players
    
    Args:
        community_cards: List of cards e.g. ['Ah', 'Kd', '5s', '9c', '2h']
        pot: Pot size
        round_name: Round name (Pre-Flop, Flop, Turn, River)
        current_bet: Current bet to call
        players: List of players with info (name, cards, stack, folded, is_current)
        show_cards: Whether to show player cards (True during showdown)
        background_url: Background URL from shop (optional)
        card_deck: Card deck name (classic, cyberpunk, neon, etc.)
    
    Returns:
        discord.File with PNG image
    """
    # Larger table if there are players
    table_height = TABLE_HEIGHT if not players else TABLE_HEIGHT + 250
    
    # Create image - load player background if available
    if background_url and requests and BytesIO:
        try:
            response = requests.get(background_url, timeout=5)
            bg_img = Image.open(BytesIO(response.content))
            bg_img = bg_img.resize((TABLE_WIDTH, table_height))
            img = bg_img.copy()
            # Add semi-transparent overlay for readability
            overlay = Image.new('RGBA', (TABLE_WIDTH, table_height), (*FELT_GREEN, 180))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        except Exception as e:
            print(f"❌ Error loading poker background: {e}")
            img = Image.new('RGB', (TABLE_WIDTH, table_height), FELT_GREEN)
    else:
        img = Image.new('RGB', (TABLE_WIDTH, table_height), FELT_GREEN)
    
    draw = ImageDraw.Draw(img)
    
    # Table border
    draw.rectangle([(0, 0), (TABLE_WIDTH, table_height)], outline=FELT_DARK, width=5)
    
    # Header with round name
    title_font = get_font(36, bold=True)
    title = f"{round_name}"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((TABLE_WIDTH - title_width) // 2, 20), title, fill=TEXT_GOLD, font=title_font)
    
    # Pot (top center) - larger and higher
    pot_font = get_font(36, bold=True)
    pot_text = f"Pot: {pot}"
    pot_bbox = draw.textbbox((0, 0), pot_text, font=pot_font)
    pot_width = pot_bbox[2] - pot_bbox[0]
    pot_height = pot_bbox[3] - pot_bbox[1]
    
    # Background for pot
    padding_horizontal = 25
    box_width = pot_width + 2 * padding_horizontal
    pot_x = (TABLE_WIDTH - box_width) // 2
    pot_y = 50
    draw.rounded_rectangle(
        [(pot_x, pot_y), (pot_x + box_width, pot_y + pot_height + 25)],
        radius=12,
        fill=POT_BG,
        outline=TEXT_GOLD,
        width=3
    )
    # Center text in the box
    text_x = pot_x + (box_width - pot_width) // 2
    draw.text((text_x, pot_y + 12), pot_text, fill=TEXT_WHITE, font=pot_font)
    
    # Community cards (community cards)
    if community_cards:
        num_cards = len(community_cards)
        total_cards_width = num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING
        start_x = (TABLE_WIDTH - total_cards_width) // 2
        cards_y = 155
        
        for i, card in enumerate(community_cards):
            rank, suit = parse_card(card)
            if rank and suit:
                x = start_x + i * (CARD_WIDTH + CARD_SPACING)
                draw_card(draw, x, cards_y, rank, suit, img_base=img, deck=card_deck)
    else:
        # Pre-flop - show 5 card backs
        num_cards = 5
        total_cards_width = num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING
        start_x = (TABLE_WIDTH - total_cards_width) // 2
        cards_y = 155
        
        for i in range(5):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            draw_card_back(draw, x, cards_y, img_base=img, deck=card_deck)
    
    # Current bet (if any)
    stake_y = table_height - 60 if not players else 305
    if current_bet > 0:
        bet_font = get_font(26, bold=True)
        bet_text = f"Current bet: {current_bet}"
        bet_bbox = draw.textbbox((0, 0), bet_text, font=bet_font)
        bet_width = bet_bbox[2] - bet_bbox[0]
        draw.text(((TABLE_WIDTH - bet_width) // 2, stake_y), bet_text, fill=TEXT_WHITE, font=bet_font)
    
    # Draw players around table
    if players:
        small_card_width = 55
        small_card_height = 77
        
        num_players = len(players)
        max_spacing = 140
        available_width = TABLE_WIDTH - 40
        
        # If more than 5 players, draw in two rows
        if num_players > 5:
            # Top row (5 players)
            top_row = players[:5]
            # Bottom row (rest)
            bottom_row = players[5:]
            
            rows = [
                {'players': top_row, 'y': 365},
                {'players': bottom_row, 'y': 540}
            ]
        else:
            # Single row (up to 5 players)
            rows = [{'players': players, 'y': 375}]
        
        for row in rows:
            row_players = row['players']
            player_y = row['y']
            num_in_row = len(row_players)
            
            # count spacing based on number of players in the row
            if num_in_row * max_spacing > available_width:
                spacing = available_width // num_in_row
            else:
                spacing = max_spacing
            
            total_width = num_in_row * spacing
            start_x = (TABLE_WIDTH - total_width) // 2 + spacing // 2 - 30  # Shift left by 30px
            
            for i, player in enumerate(row_players):
                x = start_x + i * spacing
                
                # Player background
                player_bg_color = (70, 120, 90) if player.get('is_current') else (40, 80, 60)
                if player.get('folded'):
                    player_bg_color = (60, 60, 60)
                
                draw.rounded_rectangle(
                    [(x - 12, player_y - 10), (x + 118, player_y + 145)],
                    radius=8,
                    fill=player_bg_color,
                    outline=TEXT_GOLD if player.get('is_current') else CARD_BORDER,
                    width=3 if player.get('is_current') else 1
                )
                
                # Player name
                name_font = get_font(15, bold=True)
                name = player.get('name', 'Player')[:10]
                draw.text((x, player_y), name, fill=TEXT_WHITE, font=name_font)
                
                # Stack
                stack_font = get_font(16, bold=True)
                stack_text = f"{player.get('stack', 0)}"
                draw.text((x, player_y + 22), stack_text, fill=TEXT_GOLD, font=stack_font)
                
                # Player cards
                cards = player.get('cards', [])
                if cards and (show_cards or not player.get('folded')):
                    # Center cards horizontally within box
                    cards_offset_x = -5
                    for j, card in enumerate(cards[:2]):
                        card_x = x + cards_offset_x + j * (small_card_width + 3)
                        card_y = player_y + 50
                        
                        if show_cards and not player.get('folded'):
                            # Revealed cards - use player's deck
                            rank, suit = parse_card(card)
                            if rank and suit:
                                player_deck = player.get('card_deck', 'classic')
                                draw_card(draw, card_x, card_y, rank, suit, 
                                        width=small_card_width, height=small_card_height, img_base=img, deck=player_deck)
                        else:
                            # Hidden cards - use player's deck
                            player_deck = player.get('card_deck', 'classic')
                            draw_card_back(draw, card_x, card_y, width=small_card_width, height=small_card_height, img_base=img, deck=player_deck)
                elif not player.get('folded'):
                    # No cards or hidden - center them
                    cards_offset_x = -5
                    for j in range(2):
                        card_x = x + cards_offset_x + j * (small_card_width + 3)
                        card_y = player_y + 50
                        player_deck = player.get('card_deck', 'classic')
                        draw_card_back(draw, card_x, card_y, width=small_card_width, height=small_card_height, img_base=img, deck=player_deck)
                else:
                    # Fold - show larger text
                    fold_font = get_font(26, bold=True)
                    draw.text((x + 8, player_y + 58), "FOLD", fill=(180, 180, 180), font=fold_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='poker_table.png')

def create_hand_image(hole_cards, background_url=None, card_deck='classic'):
    """
    Tworzy obrazek z kartami gracza (hole cards)
    
    Args:
        hole_cards: Lista 2 kart np. ['Ah', 'Kd']
        background_url: URL tła ze sklepu (opcjonalnie)
        card_deck: Nazwa talii kart (classic, neon, etc.)
    
    Returns:
        discord.File z obrazkiem PNG
    """
    width = 2 * CARD_WIDTH + CARD_SPACING + 40
    height = CARD_HEIGHT + 60
    
    # Create image - load player background if available
    if background_url and requests and BytesIO:
        try:
            response = requests.get(background_url, timeout=5)
            bg_img = Image.open(BytesIO(response.content))
            bg_img = bg_img.resize((width, height))
            img = bg_img.copy()
            # Add semi-transparent overlay for readability
            overlay = Image.new('RGBA', (width, height), (*FELT_GREEN, 180))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        except Exception as e:
            print(f"❌ Error loading poker background: {e}")
            img = Image.new('RGB', (width, height), FELT_GREEN)
    else:
        img = Image.new('RGB', (width, height), FELT_GREEN)
    
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=3)
    
    # Title
    title_font = get_font(20, bold=True)
    title = "Your Hand"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 10), title, fill=TEXT_GOLD, font=title_font)
    
    # cards
    if len(hole_cards) >= 2:
        start_x = 20
        cards_y = 40
        
        for i, card in enumerate(hole_cards[:2]):
            rank, suit = parse_card(card)
            if rank and suit:
                x = start_x + i * (CARD_WIDTH + CARD_SPACING)
                draw_card(draw, x, cards_y, rank, suit, img_base=img, deck=card_deck)
    
    # save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='poker_hand.png')

def create_fast_poker_comparison_image(player_name, player_cards, player_hand_name, dealer_cards, dealer_hand_name, result, player_deck='classic'):
    """
    Creates cleaner comparison image for fast poker
    
    Args:
        player_name: Player's display name
        player_cards: List of 5 cards [(rank, suit), ...]
        player_hand_name: Hand name
        dealer_cards: List of 5 dealer cards
        dealer_hand_name: Dealer's hand name
        result: 1 = player wins, -1 = dealer wins, 0 = tie
        player_deck: Player's card deck (classic/dark/platinum)
    
    Returns:
        discord.File with PNG image
    """
    # Simpler dimensions
    width = 1000
    height = 850
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width-1, height-1)], outline=FELT_DARK, width=4)
    
    # Title
    title_font = get_font(42, bold=True)
    title = "5-Card Poker Showdown"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 25), title, fill=TEXT_GOLD, font=title_font)
    
    # Card dimensions
    card_w = 120
    card_h = 168
    card_spacing = 15
    total_cards_width = 5 * card_w + 4 * card_spacing
    cards_start_x = (width - total_cards_width) // 2
    
    # Player section
    player_y = 100
    name_font = get_font(28, bold=True)
    
    # Player name and hand - centered
    player_label = f"{player_name}"
    player_label_bbox = draw.textbbox((0, 0), player_label, font=name_font)
    player_label_width = player_label_bbox[2] - player_label_bbox[0]
    draw.text(((width - player_label_width) // 2, player_y), player_label, fill=TEXT_WHITE, font=name_font)
    
    hand_font = get_font(24, bold=True)
    hand_bbox = draw.textbbox((0, 0), player_hand_name, font=hand_font)
    hand_width = hand_bbox[2] - hand_bbox[0]
    draw.text(((width - hand_width) // 2, player_y + 35), player_hand_name, fill=TEXT_GOLD, font=hand_font)
    
    # Player cards (uses player's deck)
    player_cards_y = player_y + 80
    for i, (rank, suit) in enumerate(player_cards):
        x = cards_start_x + i * (card_w + card_spacing)
        draw_card(draw, x, player_cards_y, rank, suit, width=card_w, height=card_h, img_base=img, deck=player_deck)
    
    # VS divider
    divider_y = player_cards_y + card_h + 40
    vs_font = get_font(48, bold=True)
    vs_text = "VS"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
    vs_width = vs_bbox[2] - vs_bbox[0]
    draw.text(((width - vs_width) // 2, divider_y), vs_text, fill=(255, 215, 0), font=vs_font)
    
    # Result text
    result_y = divider_y + 60
    result_font = get_font(32, bold=True)
    if result == 1:
        result_text = "YOU WIN!"
        result_color = (100, 255, 100)
    elif result == -1:
        result_text = "DEALER WINS"
        result_color = (255, 100, 100)
    else:
        result_text = "TIE"
        result_color = (255, 255, 100)
    
    result_bbox = draw.textbbox((0, 0), result_text, font=result_font)
    result_width = result_bbox[2] - result_bbox[0]
    draw.text(((width - result_width) // 2, result_y), result_text, fill=result_color, font=result_font)
    
    # Dealer section
    dealer_y = result_y + 55
    dealer_label = "Dealer"
    dealer_label_bbox = draw.textbbox((0, 0), dealer_label, font=name_font)
    dealer_label_width = dealer_label_bbox[2] - dealer_label_bbox[0]
    draw.text(((width - dealer_label_width) // 2, dealer_y), dealer_label, fill=TEXT_WHITE, font=name_font)
    
    dealer_hand_bbox = draw.textbbox((0, 0), dealer_hand_name, font=hand_font)
    dealer_hand_width = dealer_hand_bbox[2] - dealer_hand_bbox[0]
    draw.text(((width - dealer_hand_width) // 2, dealer_y + 35), dealer_hand_name, fill=TEXT_GOLD, font=hand_font)
    
    # Dealer cards (always classic deck)
    dealer_cards_y = dealer_y + 80
    for i, (rank, suit) in enumerate(dealer_cards):
        x = cards_start_x + i * (card_w + card_spacing)
        draw_card(draw, x, dealer_cards_y, rank, suit, width=card_w, height=card_h, img_base=img, deck='classic')
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='fast_poker.png')
