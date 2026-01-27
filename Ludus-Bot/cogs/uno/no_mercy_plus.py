"""
UNO No Mercy+ - No Mercy + Expansion Pack
The ultimate UNO experience with coins and devastating new cards
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
import time

class UnoNoMercyPlusHandler:
    """Handles UNO No Mercy+ specific game logic - includes expansion pack"""
    
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
    
    def create_no_mercy_plus_deck(self):
        """
        Create UNO No Mercy+ deck - 180+ cards with expansion
        
        Base No Mercy cards PLUS:
        - 10's Play Again (immediate extra turn)
        - Wild Discard All (choose color, discard all of that color)
        - Wild Reverse Draw 8 (reverse + draw 8)
        - Wild Final Attack (reveal hand, opponent draws based on action/wild cards)
        - Wild Sudden Death (all players draw to 24 cards)
        """
        deck = []
        colors = ['red', 'yellow', 'green', 'blue']
        
        # Numbers 0-9 (0 twice, 1-9 three times each)
        for color in colors:
            deck.append({'color': color, 'value': 0, 'variant': 'no_mercy_plus'})
            deck.append({'color': color, 'value': 0, 'variant': 'no_mercy_plus'})
            for num in range(1, 10):
                for _ in range(3):
                    deck.append({'color': color, 'value': num, 'variant': 'no_mercy_plus'})
        
        # NEW: 10's Play Again (2 per color) - immediate extra turn
        for color in colors:
            for _ in range(2):
                deck.append({'color': color, 'value': 10, 'variant': 'no_mercy_plus', 'effect': 'play_again'})
        
        # Action cards from No Mercy (3 per color)
        for color in colors:
            # +4 in colors (3 per color)
            for _ in range(3):
                deck.append({'color': color, 'value': '+4', 'variant': 'no_mercy_plus'})
            
            # Skip Everyone (2 per color)
            for _ in range(2):
                deck.append({'color': color, 'value': 'skip_everyone', 'variant': 'no_mercy_plus'})
            
            # Discard All Card (2 per color)
            for _ in range(2):
                deck.append({'color': color, 'value': 'discard_all_card', 'variant': 'no_mercy_plus'})
            
            # Reverse (3 per color)
            for _ in range(3):
                deck.append({'color': color, 'value': 'reverse', 'variant': 'no_mercy_plus'})
            
            # Skip (3 per color)
            for _ in range(3):
                deck.append({'color': color, 'value': 'skip', 'variant': 'no_mercy_plus'})
        
        # Wild cards from No Mercy
        for _ in range(3):
            deck.append({'color': 'wild', 'value': '+6', 'variant': 'no_mercy_plus'})
        for _ in range(2):
            deck.append({'color': 'wild', 'value': '+10', 'variant': 'no_mercy_plus'})
        for _ in range(3):
            deck.append({'color': 'wild', 'value': '+4_reverse', 'variant': 'no_mercy_plus'})
        for _ in range(2):
            deck.append({'color': 'wild', 'value': 'color_roulette', 'variant': 'no_mercy_plus'})
        
        # NEW EXPANSION WILD CARDS
        # Wild Discard All (2 cards) - choose color and discard all of that color
        for _ in range(2):
            deck.append({'color': 'wild', 'value': 'discard_all', 'variant': 'no_mercy_plus'})
        
        # Wild Reverse Draw 8 (2 cards) - reverse direction + next player draws 8
        for _ in range(2):
            deck.append({'color': 'wild', 'value': 'reverse_draw_8', 'variant': 'no_mercy_plus'})
        
        # Wild Final Attack (1 card) - reveal hand, opponent draws based on action cards
        deck.append({'color': 'wild', 'value': 'final_attack', 'variant': 'no_mercy_plus'})
        
        # Wild Sudden Death (1 card) - all players draw to 24 cards
        deck.append({'color': 'wild', 'value': 'sudden_death', 'variant': 'no_mercy_plus'})
        
        random.shuffle(deck)
        return deck
    
    def can_play_no_mercy_plus_card(self, card, top_card, current_color):
        """Check if a No Mercy+ card can be played"""
        # Wild cards can always be played
        if card['color'] == 'wild':
            return True
        
        # Discard All Card can be played on matching color OR matching number
        if card['value'] == 'discard_all_card':
            if card['color'] == current_color:
                return True
            if isinstance(top_card.get('value'), int) and card['color'] == top_card['color']:
                return True
        
        # 10's Play Again - can play on matching color or matching value (another 10)
        if card.get('value') == 10:
            if card['color'] == current_color:
                return True
            if top_card.get('value') == 10:
                return True
        
        # Match color or value
        if card['color'] == current_color:
            return True
        
        if card['value'] == top_card.get('value'):
            return True
        
        return False
    
    def get_card_display_name(self, card):
        """Get display name for No Mercy+ cards"""
        color = card['color'].capitalize()
        value = card['value']
        
        if value == 10:
            return f"{color} 10 (Play Again)"
        elif value == 'discard_all':
            return "Wild Discard All"
        elif value == 'reverse_draw_8':
            return "Wild Reverse Draw 8"
        elif value == 'final_attack':
            return "Wild Final Attack"
        elif value == 'sudden_death':
            return "Wild Sudden Death"
        elif value == '+6':
            return "Wild +6"
        elif value == '+10':
            return "Wild +10"
        elif value == '+4_reverse':
            return "Wild +4 Reverse"
        elif value == 'color_roulette':
            return "Wild Color Roulette"
        elif value == '+4':
            return f"{color} +4"
        elif value == 'skip_everyone':
            return f"{color} Skip Everyone"
        elif value == 'discard_all_card':
            return f"{color} Discard All"
        elif value == 'reverse':
            return f"{color} Reverse"
        elif value == 'skip':
            return f"{color} Skip"
        else:
            return f"{color} {value}"
    
    def initialize_player_coins(self, players):
        """Give each player 1 coin at game start"""
        coins = {}
        for player in players:
            # Boty dostają losowy typ monety od razu
            if player.startswith('BOT_'):
                import random
                coin_type = random.choice(['mercy', 'no_mercy'])
                coins[player] = {
                    'type': coin_type,
                    'used': False,
                    'selected': True  # Bot już wybrał
                }
            else:
                coins[player] = {
                    'type': None,  # 'mercy' or 'no_mercy' - wybrane przez gracza
                    'used': False,  # czy moneta została użyta
                    'selected': False  # czy gracz już wybrał typ monety
                }
        return coins
    
    def use_mercy_coin(self, game, player_id):
        """
        MERCY: Discard entire hand, draw 7 fresh cards
        Can be used to avoid elimination (>25 cards)
        """
        from . import uno_logic
        
        # Discard entire hand
        hand = game['hands'][player_id]
        if hand:
            game['discard'].extend(hand)
        
        # Draw 7 fresh cards
        game['hands'][player_id] = []
        uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
        drawn = uno_logic.draw_cards(game['deck'], 7)
        game['hands'][player_id] = drawn
        
        return True
    
    def use_no_mercy_coin(self, game, player_id, draw_value):
        """
        NO MERCY: Double the penalty of any draw card you play
        Can only be used BEFORE playing a draw card
        Returns doubled value
        """
        # NO MERCY doubling is handled directly in classic.py where draw_penalty is applied
        # This function is kept for backward compatibility but not actively used
        return draw_value * 2
    
    def handle_wild_discard_all(self, game, player_id, chosen_color):
        """
        Wild Discard All: Choose a color and discard all cards of that color
        Returns: (cards_discarded_count, remaining_hand)
        """
        hand = game['hands'][player_id]
        discarded = []
        new_hand = []
        
        for card in hand:
            if card['color'] == chosen_color:
                discarded.append(card)
            else:
                new_hand.append(card)
        
        # Add discarded cards to discard pile
        game['discard'].extend(discarded)
        game['hands'][player_id] = new_hand
        
        return len(discarded), new_hand
    
    def handle_wild_reverse_draw_8(self, game):
        """
        Wild Reverse Draw 8: Reverse direction + next player draws 8
        Returns: (next_player, draw_amount)
        """
        # Reverse direction
        game['direction'] *= -1
        
        # Get next player
        game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
        next_player = game['players'][game['current_turn']]
        
        return next_player, 8
    
    def handle_wild_final_attack(self, game, player_id):
        """
        Wild Final Attack: Reveal hand, next player draws based on action/wild cards
        7+ action/wild cards = opponent draws 25 + all others draw 5
        Otherwise = opponent draws 1 per action/wild card
        Returns: (next_player, draw_amount, all_players_draw)
        """
        hand = game['hands'][player_id]
        
        # Count action and wild cards
        action_wild_count = 0
        for card in hand:
            # Count all non-number cards (action + wild)
            if card['value'] not in range(11):  # 0-10 are numbers
                action_wild_count += 1
        
        # Move to next player
        game['current_turn'] = (game['current_turn'] + game['direction']) % len(game['players'])
        next_player = game['players'][game['current_turn']]
        
        if action_wild_count >= 7:
            # MEGA ATTACK: Next player draws 25, all others draw 5
            return next_player, 25, True, action_wild_count
        else:
            # Normal: Next player draws 1 per action/wild card
            return next_player, action_wild_count, False, action_wild_count
    
    def handle_wild_sudden_death(self, game):
        """
        Wild Sudden Death: All players draw to 24 cards
        Returns: dict of {player_id: cards_drawn}
        """
        from . import uno_logic
        draws = {}
        
        for player_id in game['players']:
            current_cards = len(game['hands'][player_id])
            if current_cards < 24:
                to_draw = 24 - current_cards
                # Draw cards using proper deck management
                uno_logic.reshuffle_discard_into_deck(game['deck'], game['discard'])
                drawn = uno_logic.draw_cards(game['deck'], to_draw)
                if drawn:
                    game['hands'][player_id].extend(drawn)
                draws[player_id] = len(drawn)
            else:
                draws[player_id] = 0
        
        return draws
    
    def handle_10_play_again(self, game):
        """
        10's Play Again: Player gets immediate extra turn
        Don't advance current_turn
        Returns: True (to indicate play again effect)
        """
        # Don't change current_turn - player plays again
        return True
