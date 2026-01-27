"""
UNO Flip - Dark side implementation with reversed view
Players see OTHER players' cards, but not their own!
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
import time
import uuid

class UnoFlipHandler:
    """Handles UNO Flip specific game logic with reversed view mechanic"""
    
    def __init__(self, bot, uno_cog):
        self.bot = bot
        self.uno_cog = uno_cog
        self.games = {}
    
    
    def create_double_sided_flip_deck(self):
        """
        Create UNO Flip deck with random light-dark pairings.
        Each card has a unique ID and two sides (light and dark) randomly paired.
        Returns: (deck, card_mapping)
        """
        # Create all light side cards
        light_cards = []
        colors_light = ['red', 'yellow', 'green', 'blue']
        
        for color in colors_light:
            # Numbers 1-9 (twice each)
            for num in range(1, 10):
                light_cards.append({'color': color, 'value': num, 'side': 'light'})
                light_cards.append({'color': color, 'value': num, 'side': 'light'})
            # Draw 1 (2 per color)
            light_cards.append({'color': color, 'value': '+1', 'side': 'light'})
            light_cards.append({'color': color, 'value': '+1', 'side': 'light'})
            # Flip (2 per color)
            light_cards.append({'color': color, 'value': 'flip', 'side': 'light'})
            light_cards.append({'color': color, 'value': 'flip', 'side': 'light'})
        
        # Wild cards (4 Wild, 2 Wild Draw 2)
        for _ in range(4):
            light_cards.append({'color': 'wild', 'value': 'wild', 'side': 'light'})
        for _ in range(2):
            light_cards.append({'color': 'wild', 'value': '+2', 'side': 'light'})
        
        # Total light cards: 4 * 22 + 6 = 94 cards
        
        # Create all dark side cards (MUST BE SAME COUNT AS LIGHT!)
        dark_cards = []
        colors_dark = ['teal', 'purple', 'pink', 'orange']
        
        for color in colors_dark:
            # Numbers 1-9 (twice each)
            for num in range(1, 10):
                dark_cards.append({'color': color, 'value': num, 'side': 'dark'})
                dark_cards.append({'color': color, 'value': num, 'side': 'dark'})
            # Draw 5 (2 per color)
            dark_cards.append({'color': color, 'value': '+5', 'side': 'dark'})
            dark_cards.append({'color': color, 'value': '+5', 'side': 'dark'})
            # Skip Everyone (2 per color)
            dark_cards.append({'color': color, 'value': 'skip_everyone', 'side': 'dark'})
            dark_cards.append({'color': color, 'value': 'skip_everyone', 'side': 'dark'})
            # Flip (2 per color)
            dark_cards.append({'color': color, 'value': 'flip', 'side': 'dark'})
            dark_cards.append({'color': color, 'value': 'flip', 'side': 'dark'})
        
        # Wild cards (4 Wild Flip, 2 Draw Color)
        for _ in range(4):
            dark_cards.append({'color': 'wild', 'value': 'flip', 'side': 'dark'})
        for _ in range(2):
            dark_cards.append({'color': 'wild', 'value': 'draw_color', 'side': 'dark'})
        
        # Total dark cards: 4 * 22 + 6 = 94 cards (MATCHES LIGHT!)
        
        # Shuffle dark cards to randomize pairing
        random.shuffle(dark_cards)
        
        # Create paired cards with unique IDs
        card_mapping = {}  # card_id -> {'light': light_card, 'dark': dark_card}
        deck = []
        
        # Pair each light card with a random dark card
        for light_card, dark_card in zip(light_cards, dark_cards):
            card_id = str(uuid.uuid4())
            
            # Add card_id to both sides
            light_card_with_id = light_card.copy()
            light_card_with_id['card_id'] = card_id
            
            dark_card_with_id = dark_card.copy()
            dark_card_with_id['card_id'] = card_id
            
            # Store mapping
            card_mapping[card_id] = {
                'light': light_card_with_id,
                'dark': dark_card_with_id
            }
            
            # Start with light side up
            deck.append(light_card_with_id)
        
        # Shuffle the deck
        random.shuffle(deck)
        
        return deck, card_mapping
    
    def create_flip_deck(self, side='light'):
        """
        Create UNO Flip deck for given side
        Light side: red, yellow, green, blue + Draw 1, Flip
        Dark side: teal, purple, pink, orange + Draw 5, Skip Everyone, Flip
        """
        deck = []
        
        if side == 'light':
            colors = ['red', 'yellow', 'green', 'blue']
            # Numbers 0-9 (0 once, 1-9 twice each)
            for color in colors:
                for num in range(1, 10):
                    deck.append({'color': color, 'value': num, 'side': 'light'})
                    deck.append({'color': color, 'value': num, 'side': 'light'})
                # Draw 1 (2 per color)
                deck.append({'color': color, 'value': '+1', 'side': 'light'})
                deck.append({'color': color, 'value': '+1', 'side': 'light'})
                # Flip (2 per color)
                deck.append({'color': color, 'value': 'flip', 'side': 'light'})
                deck.append({'color': color, 'value': 'flip', 'side': 'light'})
            
            # Wild cards (4 Wild, 2 Wild Draw 2)
            for _ in range(4):
                deck.append({'color': 'wild', 'value': 'wild', 'side': 'light'})
            for _ in range(2):
                deck.append({'color': 'wild', 'value': '+2', 'side': 'light'})
        
        else:  # dark side
            colors = ['teal', 'purple', 'pink', 'orange']
            # Numbers 1-9 (twice each, no 0 on dark side)
            for color in colors:
                for num in range(1, 10):
                    deck.append({'color': color, 'value': num, 'side': 'dark'})
                    deck.append({'color': color, 'value': num, 'side': 'dark'})
                # Draw 5 (2 per color)
                deck.append({'color': color, 'value': '+5', 'side': 'dark'})
                deck.append({'color': color, 'value': '+5', 'side': 'dark'})
                # Skip Everyone (2 per color)
                deck.append({'color': color, 'value': 'skip_everyone', 'side': 'dark'})
                deck.append({'color': color, 'value': 'skip_everyone', 'side': 'dark'})
                # Reverse (2 per color)
                deck.append({'color': color, 'value': 'reverse', 'side': 'dark'})
                deck.append({'color': color, 'value': 'reverse', 'side': 'dark'})
                # Flip (2 per color)
                deck.append({'color': color, 'value': 'flip', 'side': 'dark'})
                deck.append({'color': color, 'value': 'flip', 'side': 'dark'})
            
            # Wild cards (4 Flip, 2 Draw Color)
            for _ in range(4):
                deck.append({'color': 'wild', 'value': 'flip', 'side': 'dark'})
            for _ in range(2):
                deck.append({'color': 'wild', 'value': 'draw_color', 'side': 'dark'})
        
        random.shuffle(deck)
        return deck
    
    def flip_card(self, card, card_mapping=None):
        """
        Flip a card to its opposite side using the card mapping.
        If card_mapping is provided, uses that for accurate flipping.
        Otherwise falls back to old static rules (for backward compatibility).
        """
        # If we have card mapping, use it for precise flipping
        if card_mapping and 'card_id' in card:
            card_id = card['card_id']
            if card_id in card_mapping:
                current_side = card['side']
                opposite_side = 'dark' if current_side == 'light' else 'light'
                return card_mapping[card_id][opposite_side].copy()
        
        # Fallback to old static rules if no mapping available
        if card['side'] == 'light':
            # Map light cards to dark equivalents
            new_card = card.copy()
            new_card['side'] = 'dark'
            
            # Color mapping (official UNO Flip rules)
            color_map = {'red': 'pink', 'blue': 'teal', 'green': 'orange', 'yellow': 'purple'}
            if card['color'] in color_map:
                new_card['color'] = color_map[card['color']]
            
            # Value mapping
            if card['value'] == '+1':
                new_card['value'] = '+5'
            elif card['value'] == 'skip':
                new_card['value'] = 'skip_everyone'
            elif card['value'] == 'reverse':
                new_card['value'] = 'reverse'  # Reverse stays Reverse
            elif card['value'] == 'flip':
                new_card['value'] = 'flip'
            elif card['value'] == 'wild' and card['color'] == 'wild':
                new_card['value'] = 'flip'  # Wild becomes Wild Flip on dark side
            elif card['value'] == '+2' and card['color'] == 'wild':
                new_card['value'] = 'draw_color'
            
            return new_card
        else:
            # Map dark cards to light equivalents
            new_card = card.copy()
            new_card['side'] = 'light'
            
            # Color mapping (official UNO Flip rules)
            color_map = {'pink': 'red', 'teal': 'blue', 'orange': 'green', 'purple': 'yellow'}
            if card['color'] in color_map:
                new_card['color'] = color_map[card['color']]
            
            # Value mapping
            if card['value'] == '+5':
                new_card['value'] = '+1'
            elif card['value'] == 'skip_everyone':
                new_card['value'] = 'skip'
            elif card['value'] == 'reverse':
                new_card['value'] = 'reverse'  # Reverse stays Reverse
            elif card['value'] == 'flip' and card['color'] == 'wild':
                new_card['value'] = 'wild'  # Wild Flip becomes Wild on light side
            elif card['value'] == 'flip':
                new_card['value'] = 'flip'
            elif card['value'] == 'draw_color' and card['color'] == 'wild':
                new_card['value'] = '+2'
            
            return new_card
    
    async def handle_flip_card_played(self, game_state):
        """Handle FLIP card - switches all cards to other side"""
        current_side = game_state.get('current_side', 'light')
        new_side = 'dark' if current_side == 'light' else 'light'
        
        # Get card mapping for accurate flipping
        card_mapping = game_state.get('card_mapping', None)
        
        # Flip all cards in all hands
        for player_id in game_state['hands']:
            game_state['hands'][player_id] = [self.flip_card(card, card_mapping) for card in game_state['hands'][player_id]]
        
        # Flip deck
        game_state['deck'] = [self.flip_card(card, card_mapping) for card in game_state['deck']]
        
        # Flip discard pile
        game_state['discard'] = [self.flip_card(card, card_mapping) for card in game_state['discard']]
        
        # DON'T update current_color here - it will be set by the calling code
        # after getting the flipped card reference
        
        # Update current side
        game_state['current_side'] = new_side
        
        lang = game_state.get('lang', 'en')
        side_name = self.uno_cog.t('messages.dark', lang=lang) if new_side == 'dark' else self.uno_cog.t('messages.light', lang=lang)
        return f"🔄 {self.uno_cog.t('messages.cards_flipped', lang=lang)}: **{'🌙' if new_side == 'dark' else '🌅'} {side_name.upper()}**"
    
    async def show_opponents_cards(self, interaction, game_id):
        """Show ALL opponents' cards to the player (reversed view mechanic - pokazuje ODWROTNĄ stronę kart)"""
        game = self.bot.active_games.get(game_id)
        if not game:
            return await interaction.response.send_message(self.uno_cog.t('messages.game_inactive', lang='en'), ephemeral=True)
        
        # Ensure uid is string to match game['hands'] keys
        uid = str(interaction.user.id)
        
        if uid not in game['hands']:
            return await interaction.response.send_message(self.uno_cog.t('messages.not_player', lang='en'), ephemeral=True)
        
        from . import uno_logic
        
        # Get current side of the game
        lang = game.get('lang', 'en')
        current_side = game.get('current_side', 'light')
        opposite_side = 'dark' if current_side == 'light' else 'light'
        card_mapping = game.get('card_mapping', None)
        
        side_current = self.uno_cog.t('messages.light', lang=lang) if current_side == 'light' else self.uno_cog.t('messages.dark', lang=lang)
        side_opposite = self.uno_cog.t('messages.dark', lang=lang) if opposite_side == 'dark' else self.uno_cog.t('messages.light', lang=lang)
        
        embed = discord.Embed(
            title=f"👥 {self.uno_cog.t('messages.opponent_cards_title', lang=lang)}",
            description=f"{self.uno_cog.t('messages.flip_see_opposite', lang=lang)}\n\n🎴 {self.uno_cog.t('messages.flip_game_side', lang=lang)}: **🌅 {side_current.upper()}**\n👁️ {self.uno_cog.t('messages.flip_you_see', lang=lang)}: **🌙 {side_opposite.upper()}**",
            color=0x9B59B6
        )
        
        has_opponents = False
        
        # Show each opponent's cards (including BOT) - but FLIPPED to opposite side
        for player_id in game['players']:
            if player_id == uid:
                continue
            
            has_opponents = True
            hand = game['hands'][player_id]
            
            # Display name
            bot_names = game.get('bot_names', {})
            if player_id.startswith('BOT_'):
                bot_name = bot_names.get(player_id, f"BOT {player_id.split('_')[1]}")
                player_name = f"🤖 {bot_name}"
            else:
                player_name = f"<@{player_id}>"
            
            # Create card display with emojis - pokazuj ODWRÓCONĄ stronę
            card_display = ""
            for i, card in enumerate(hand, 1):
                # Flip card to opposite side before displaying
                flipped_card = self.flip_card(card, card_mapping)
                emoji = uno_logic.card_to_emoji(flipped_card, variant='flip')
                card_display += str(emoji) + " "
                if i % 8 == 0:  # Line break every 8 cards
                    card_display += "\n"
            
            if not card_display:
                card_display = self.uno_cog.t('messages.no_cards', lang=lang)
            
            embed.add_field(
                name=f"{player_name} - {len(hand)} {self.uno_cog.t('messages.cards', lang=lang)}",
                value=card_display,
                inline=False
            )
        
        if not has_opponents:
            embed.description = self.uno_cog.t('messages.no_other_players', lang=lang)
        
        # Check if this is clicked from game lobby or from existing opponent view
        # If clicked from main game lobby, always send NEW ephemeral message
        is_from_game_lobby = hasattr(interaction, 'message') and interaction.message and interaction.message.id == game.get('messageId')
        is_existing_opponent_view = uid in game.get('opponent_views', {}) and not is_from_game_lobby
        
        if is_existing_opponent_view:
            # Update existing ephemeral opponent view message
            try:
                await interaction.response.edit_message(embed=embed)
                msg = interaction.message
            except:
                # If edit fails, send new message
                await interaction.response.send_message(embed=embed, ephemeral=True)
                msg = await interaction.original_response()
        else:
            # Always send NEW ephemeral message (don't edit game lobby!)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            msg = await interaction.original_response()
        
        # Store reference for auto-refresh
        if 'opponent_views' not in game:
            game['opponent_views'] = {}
        game['opponent_views'][uid] = {
            'message': msg,
            'interaction': interaction
        }
