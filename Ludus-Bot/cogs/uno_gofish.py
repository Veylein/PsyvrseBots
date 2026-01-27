import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import List, Optional, Dict
import json
import os


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
