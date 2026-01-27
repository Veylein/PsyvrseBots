"""
UNO No Mercy - Hardcore chaos mode
The most brutal UNO variant with devastating card effects
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
import time

class UnoNoMercyHandler:
    """Handles UNO No Mercy specific game logic - pure chaos"""
    
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
    
    def create_no_mercy_deck(self):
        """
        Create UNO No Mercy deck - 168 cards of pure chaos
        Features:
        - Colored +4 cards (instead of +2)
        - Skip Everyone
        - Discard All Card (discard all cards of that number/color)
        - Wild +6, +10 (mega draw)
        - Wild +4 Reverse (draw 4 + reverse direction)
        - Wild Color Roulette (random color selection)
        """
        deck = []
        colors = ['red', 'yellow', 'green', 'blue']
        
        # Numbers 0-9 (0 twice, 1-9 three times each) - increased from classic
        for color in colors:
            # 0 appears twice per color
            deck.append({'color': color, 'value': 0, 'variant': 'no_mercy'})
            deck.append({'color': color, 'value': 0, 'variant': 'no_mercy'})
            # 1-9 appear three times per color
            for num in range(1, 10):
                deck.append({'color': color, 'value': num, 'variant': 'no_mercy'})
                deck.append({'color': color, 'value': num, 'variant': 'no_mercy'})
                deck.append({'color': color, 'value': num, 'variant': 'no_mercy'})
        
        # Action cards - No Mercy special (3 per color for more chaos)
        for color in colors:
            # +4 in colors (3 per color) - replaces classic +2
            for _ in range(3):
                deck.append({'color': color, 'value': '+4', 'variant': 'no_mercy'})
            
            # Skip Everyone (2 per color) - skips ALL other players
            deck.append({'color': color, 'value': 'skip_everyone', 'variant': 'no_mercy'})
            deck.append({'color': color, 'value': 'skip_everyone', 'variant': 'no_mercy'})
            
            # Discard All Card (2 per color) - discard all cards matching this number/color
            deck.append({'color': color, 'value': 'discard_all_card', 'variant': 'no_mercy'})
            deck.append({'color': color, 'value': 'discard_all_card', 'variant': 'no_mercy'})
            
            # Reverse (3 per color) - increased frequency
            for _ in range(3):
                deck.append({'color': color, 'value': 'reverse', 'variant': 'no_mercy'})
            
            # Skip (3 per color) - increased frequency
            for _ in range(3):
                deck.append({'color': color, 'value': 'skip', 'variant': 'no_mercy'})
        
        # Wild cards - No Mercy devastation (NO basic wild cards!)
        # Wild +6 (3 cards) - increased frequency
        for _ in range(3):
            deck.append({'color': 'wild', 'value': '+6', 'variant': 'no_mercy'})
        
        # Wild +10 (2 cards) - the ultimate punishment, now twice as common
        for _ in range(2):
            deck.append({'color': 'wild', 'value': '+10', 'variant': 'no_mercy'})
        
        # Wild +4 Reverse (3 cards) - draw 4 AND reverse direction
        for _ in range(3):
            deck.append({'color': 'wild', 'value': '+4_reverse', 'variant': 'no_mercy'})
        
        # Wild Color Roulette (2 cards) - draw until you get the color
        for _ in range(2):
            deck.append({'color': 'wild', 'value': 'color_roulette', 'variant': 'no_mercy'})
        
        random.shuffle(deck)
        return deck
    
    def can_play_no_mercy_card(self, card, top_card, current_color):
        """Check if a No Mercy card can be played"""
        # Wild cards can always be played
        if card['color'] == 'wild':
            return True
        
        # Discard All Card can be played on matching color OR matching number
        if card['value'] == 'discard_all_card':
            if card['color'] == current_color:
                return True
            # Can also match if top card has same number
            if isinstance(top_card.get('value'), int) and card['color'] == top_card['color']:
                return True
        
        # Match color or value
        if card['color'] == current_color:
            return True
        if card['value'] == top_card.get('value'):
            return True
        
        return False
    
    def apply_no_mercy_effect(self, card, game):
        """
        Apply No Mercy card effects
        Returns dict with effect details:
        - draw_count: number of cards to draw
        - skip_everyone: True if all other players are skipped
        - reverse: True if direction changes
        - discard_all: True if player can discard matching cards
        - draw_color: True if next player draws until color (like Flip)
        """
        effects = {}
        value = card['value']
        
        if value == '+4' and card['color'] != 'wild':
            # Colored +4
            effects['draw_count'] = 4
            effects['skip_turn'] = True
        elif value == '+6':
            # Wild +6
            effects['draw_count'] = 6
            effects['skip_turn'] = True
        elif value == '+10':
            # Wild +10 - the nuclear option
            effects['draw_count'] = 10
            effects['skip_turn'] = True
        elif value == '+4_reverse':
            # Wild +4 Reverse
            effects['draw_count'] = 4
            effects['reverse'] = True
            effects['skip_turn'] = True
        elif value == 'skip_everyone':
            # Skip Everyone - only current player plays
            effects['skip_everyone'] = True
        elif value == 'discard_all_card':
            # Discard All Card - player discards all cards of THIS color
            effects['discard_all'] = card['color']  # Store the color to discard
        elif value == 'color_roulette':
            # Color Roulette - like Wild Draw Color from Flip
            # Next player chooses color and draws until they get that color
            effects['draw_color'] = True
        elif value == 'reverse':
            effects['reverse'] = True
        elif value == 'skip':
            effects['skip_turn'] = True
        
        return effects
    
    def get_matching_cards_for_discard_all(self, hand, played_card):
        """
        Get all cards that match the color of the Discard All Card
        ALL cards of that color (including the Discard All Card itself) are discarded
        """
        matching = []
        discard_color = played_card['color']
        
        for idx, card in enumerate(hand):
            # Match by color - discard ALL cards of this color
            if card['color'] == discard_color:
                matching.append(idx)
        
        return matching
