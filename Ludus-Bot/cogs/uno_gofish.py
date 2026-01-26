import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import List, Optional, Dict
import json
import os

# UNO Card representation
class UNOCard:
    COLORS = ["🔴", "🟡", "🟢", "🔵"]
    SPECIAL_CARDS = ["Skip", "Reverse", "Draw2"]
    WILD_CARDS = ["Wild", "Wild Draw4"]
    
    def __init__(self, color=None, value=None):
        self.color = color
        self.value = value
    
    def __str__(self):
        if self.value in self.WILD_CARDS:
            return f"🌈 {self.value}"
        return f"{self.color} {self.value}"
    
    def __repr__(self):
        return self.__str__()
    
    @staticmethod
    def create_deck():
        """Create a full UNO deck"""
        deck = []
        
        # Number cards (0-9, two of each except 0)
        for color in UNOCard.COLORS:
            deck.append(UNOCard(color, "0"))
            for num in range(1, 10):
                deck.append(UNOCard(color, str(num)))
                deck.append(UNOCard(color, str(num)))
            
            # Special cards (2 of each)
            for special in UNOCard.SPECIAL_CARDS:
                deck.append(UNOCard(color, special))
                deck.append(UNOCard(color, special))
        
        # Wild cards (4 of each)
        for _ in range(4):
            deck.append(UNOCard(None, "Wild"))
            deck.append(UNOCard(None, "Wild Draw4"))
        
        random.shuffle(deck)
        return deck
    
    def can_play_on(self, other_card, declared_color=None):
        """Check if this card can be played on another"""
        # Wild cards can always be played
        if self.value in self.WILD_CARDS:
            return True
        
        # Match color or value
        target_color = declared_color if declared_color else other_card.color
        return self.color == target_color or self.value == other_card.value

class UNOGame:
    def __init__(self, players: List[discord.Member]):
        self.players = players
        self.hands = {player.id: [] for player in players}
        self.deck = UNOCard.create_deck()
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        self.current_color = None
        self.game_over = False
        self.winner = None
        
        # Deal initial hands
        for player in players:
            for _ in range(7):
                self.hands[player.id].append(self.deck.pop())
        
        # Start discard pile with a non-special card
        while True:
            card = self.deck.pop()
            if card.value not in UNOCard.SPECIAL_CARDS and card.value not in UNOCard.WILD_CARDS:
                self.discard_pile.append(card)
                self.current_color = card.color
                break
    
    @property
    def current_player(self):
        return self.players[self.current_player_index]
    
    @property
    def top_card(self):
        return self.discard_pile[-1] if self.discard_pile else None
    
    def draw_card(self, player_id, count=1):
        """Draw cards from deck"""
        cards = []
        for _ in range(count):
            if not self.deck:
                # Reshuffle discard pile (except top card)
                if len(self.discard_pile) > 1:
                    self.deck = self.discard_pile[:-1]
                    random.shuffle(self.deck)
                    self.discard_pile = [self.discard_pile[-1]]
                else:
                    break
            
            card = self.deck.pop()
            self.hands[player_id].append(card)
            cards.append(card)
        return cards
    
    def play_card(self, player_id, card_index, declared_color=None):
        """Play a card from hand"""
        if card_index < 0 or card_index >= len(self.hands[player_id]):
            return False, "Invalid card index!"
        
        card = self.hands[player_id][card_index]
        
        # Check if card can be played
        if not card.can_play_on(self.top_card, self.current_color):
            return False, "Card cannot be played on current card!"
        
        # Remove card from hand
        self.hands[player_id].pop(card_index)
        self.discard_pile.append(card)
        
        # Update current color
        if card.value in UNOCard.WILD_CARDS:
            self.current_color = declared_color
        else:
            self.current_color = card.color
        
        # Handle special cards
        if card.value == "Skip":
            self.next_turn()
        elif card.value == "Reverse":
            self.direction *= -1
            if len(self.players) == 2:
                self.next_turn()
        elif card.value == "Draw2":
            self.next_turn()
            self.draw_card(self.current_player.id, 2)
            return True, "Next player draws 2 cards!"
        elif card.value == "Wild Draw4":
            self.next_turn()
            self.draw_card(self.current_player.id, 4)
            return True, "Next player draws 4 cards!"
        
        # Check for win
        if len(self.hands[player_id]) == 0:
            self.game_over = True
            self.winner = next(p for p in self.players if p.id == player_id)
            return True, "WIN!"
        
        return True, "Card played successfully!"
    
    def next_turn(self):
        """Move to next player"""
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
    
    def get_hand_display(self, player_id):
        """Display a player's hand"""
        hand = self.hands[player_id]
        return "\n".join([f"`{i}` {card}" for i, card in enumerate(hand)])

# Go-Fish implementation
class GoFishGame:
    def __init__(self, players: List[discord.Member]):
        self.players = players
        self.hands = {player.id: [] for player in players}
        self.books = {player.id: [] for player in players}  # Sets of 4
        self.deck = self.create_deck()
        self.current_player_index = 0
        self.game_over = False
        self.winner = None
        
        # Deal initial hands (7 cards for 2 players, 5 for 3+)
        cards_to_deal = 7 if len(players) == 2 else 5
        for player in players:
            for _ in range(cards_to_deal):
                self.hands[player.id].append(self.deck.pop())
            self.check_for_books(player.id)
    
    @staticmethod
    def create_deck():
        """Create a standard 52-card deck"""
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♣', '♥', '♦']
        deck = [f"{rank}{suit}" for rank in ranks for suit in suits]
        random.shuffle(deck)
        return deck
    
    @property
    def current_player(self):
        return self.players[self.current_player_index]
    
    def get_rank(self, card):
        """Get rank from card string"""
        return card[:-1]
    
    def check_for_books(self, player_id):
        """Check if player has any sets of 4"""
        hand = self.hands[player_id]
        rank_counts = {}
        
        for card in hand:
            rank = self.get_rank(card)
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        # Remove sets of 4
        for rank, count in rank_counts.items():
            if count == 4:
                # Remove all cards of this rank
                self.hands[player_id] = [c for c in hand if self.get_rank(c) != rank]
                self.books[player_id].append(rank)
    
    def ask_for_rank(self, asker_id, target_id, rank):
        """Ask another player for cards of a rank"""
        target_hand = self.hands[target_id]
        matching_cards = [c for c in target_hand if self.get_rank(c) == rank]
        
        if matching_cards:
            # Transfer cards
            for card in matching_cards:
                target_hand.remove(card)
                self.hands[asker_id].append(card)
            
            self.check_for_books(asker_id)
            return True, len(matching_cards)
        
        return False, 0
    
    def go_fish(self, player_id):
        """Draw a card from deck"""
        if self.deck:
            card = self.deck.pop()
            self.hands[player_id].append(card)
            self.check_for_books(player_id)
            return card
        return None
    
    def next_turn(self):
        """Move to next player"""
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
    
    def check_game_over(self):
        """Check if game is over"""
        if not self.deck and all(len(hand) == 0 for hand in self.hands.values()):
            self.game_over = True
            # Winner is player with most books
            max_books = max(len(books) for books in self.books.values())
            for player in self.players:
                if len(self.books[player.id]) == max_books:
                    self.winner = player
                    break

class MoreCardGames(commands.Cog):
    """Legacy file - commands moved to other cogs"""
    
    def __init__(self, bot):
        self.bot = bot
        # No active game tracking needed - legacy commands removed
    
    # ==================== LEGACY COMMANDS REMOVED ====================
    # All legacy UNO and Go-Fish commands have been removed to save command slots.
    # Working implementations exist in cardgames.py (UNO) and other cogs.

async def setup(bot):
    await bot.add_cog(MoreCardGames(bot))
