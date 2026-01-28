"""
UNO Game Logic
Supports 2-10 players with standard UNO rules
"""
import random
import discord
from pathlib import Path
import json

# Card colors
COLORS = ['red', 'yellow', 'green', 'blue']
COLORS_FLIP_LIGHT = ['red', 'yellow', 'green', 'blue']
COLORS_FLIP_DARK = ['teal', 'purple', 'pink', 'orange']

COLOR_EMOJIS = {
    'red': '🔴',
    'yellow': '🟡',
    'green': '🟢',
    'blue': '🔵',
    'teal': '🔵',  # Closest match
    'purple': '🟣',
    'pink': '🩷',
    'orange': '🟠',
    'wild': '⚫'
}

# Base path for card assets
ASSETS_PATH = Path(__file__).parent.parent / 'assets' / 'uno_cards' / 'uno_classic'

# Cache dla emoji mapping
_emoji_cache = None
_translations_cache = None

def load_emoji_mapping(variant='classic'):
    """Ładuje mapowanie emoji z pliku JSON dla danego wariantu (classic/flip)"""
    global _emoji_cache
    if _emoji_cache is None:
        try:
            # Path from cogs/uno/ -> go up 3 levels to root, then to data/
            mapping_path = Path(__file__).parent.parent.parent / 'data' / 'uno_emoji_mapping.json'
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    _emoji_cache = json.load(f)
            else:
                print(f"[UNO] WARNING: Emoji mapping file not found at {mapping_path}")
                _emoji_cache = {}
        except Exception as e:
            print(f"[UNO] Error loading emoji mapping: {e}")
            import traceback
            traceback.print_exc()
            _emoji_cache = {}
    
    # Zwróć odpowiedni wariant lub pusty dict
    if isinstance(_emoji_cache, dict):
        return _emoji_cache.get(variant, {})
    return {}

def load_translations():
    """Load UNO translations from JSON file"""
    global _translations_cache
    if _translations_cache is None:
        try:
            # Path from cogs/uno/ -> go up 2 levels to root, then to data/
            translations_path = Path(__file__).parent.parent.parent / 'data' / 'uno_translations.json'
            if translations_path.exists():
                with open(translations_path, 'r', encoding='utf-8') as f:
                    _translations_cache = json.load(f)
            else:
                print(f"[UNO] WARNING: Translation file not found at {translations_path}")
                _translations_cache = {}
        except Exception as e:
            print(f"[UNO] Error loading translations: {e}")
            import traceback
            traceback.print_exc()
            _translations_cache = {}
    return _translations_cache

def get_text(key_path, lang='pl'):
    """
    Get translated text by key path (e.g., 'lobby.title', 'game.now_playing')
    Args:
        key_path: dot-separated path to translation key
        lang: language code ('pl' or 'en')
    Returns:
        Translated text or key_path if not found
    """
    translations = load_translations()
    if lang not in translations:
        lang = 'en'  # Fallback to English
    
    keys = key_path.split('.')
    current = translations.get(lang, {})
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return key_path  # Return key path if translation not found
    
    return current

def get_card_emoji_id(card, variant='classic'):
    """Zwraca ID emoji dla danej karty"""
    mapping = load_emoji_mapping(variant)
    if not mapping:
        return None
    
    color = card['color']
    value = card['value']
    
    # Mapowanie wartości na nazwę pliku PNG (taka jak w JSON)
    if color == 'wild':
        if value == 'wild+4':
            filename = 'wild_+4.png'
        elif value == 'flip':
            filename = 'wild_flip.png'
        elif value == '+2':
            filename = 'wild_+2.png'
        elif value == 'draw_color':
            filename = 'wild_draw_color_flip.png'
        elif value == '+6':
            filename = 'wild_+6.png'
        elif value == '+10':
            filename = 'wild_+10.png'
        elif value == '+4_reverse':
            filename = 'wild_+4_reverse.png'
        elif value == 'color_roulette':
            filename = 'wild_color_roulette.png'
        # No Mercy+ expansion wild cards
        elif value == 'discard_all':
            filename = 'wild_discard_all_card.png'
        elif value == 'reverse_draw_8':
            filename = 'wild_+8_reverse.png'
        elif value == 'final_attack':
            filename = 'wild_final_attack.png'
        elif value == 'sudden_death':
            filename = 'wild_sudden_death.png'
        else:
            filename = 'wild.png'
    else:
        if isinstance(value, int):
            filename = f"{color}_{value}.png"
        elif value == 'skip':
            filename = f"{color}_block.png"
        elif value == 'reverse':
            filename = f"{color}_reverse.png"
        elif value == '+2':
            filename = f"{color}_+2.png"
        elif value == '+4':
            filename = f"{color}_+4.png"
        elif value == '+1':
            filename = f"{color}_+1.png"
        elif value == '+5':
            filename = f"{color}_+5.png"
        elif value == 'flip':
            filename = f"{color}_flip.png"
        elif value == 'skip_everyone':
            filename = f"{color}_skip_everyone.png"
        elif value == 'discard_all_card':
            filename = f"{color}_discard_all_card.png"
        else:
            filename = f"{color}_{value}.png"
    
    return mapping.get(filename)

def card_to_emoji(card, variant='classic'):
    """Zwraca obiekt emoji Discord dla karty (do użycia w przyciskach/select)"""
    emoji_id = get_card_emoji_id(card, variant)
    if emoji_id:
        try:
            # Validate emoji_id is a valid integer
            emoji_id_int = int(emoji_id)
            if emoji_id_int > 0:
                return discord.PartialEmoji(name='_', id=emoji_id_int)
        except (ValueError, TypeError) as e:
            print(f"Invalid emoji ID for card {card}: {emoji_id}, error: {e}")
            pass
    # Fallback do color emoji
    color_emoji = COLOR_EMOJIS.get(card['color'], '⚫')
    print(f"Using fallback emoji for card {card}: {color_emoji}")
    return color_emoji

def get_uno_back_emoji(variant='classic'):
    """Zwraca string emoji dla tyłu karty UNO (do użycia w embeds)"""
    mapping = load_emoji_mapping(variant)
    emoji_id = mapping.get('uno_back.png')
    if emoji_id:
        return f"<:uno_back:{emoji_id}>"
    return "🎴"  # Fallback

def get_uno_back_partial_emoji(variant='classic'):
    """Zwraca PartialEmoji dla tyłu karty UNO (do użycia w przyciskach)"""
    mapping = load_emoji_mapping(variant)
    emoji_id = mapping.get('uno_back.png')
    if emoji_id:
        return discord.PartialEmoji(name='uno_back', id=emoji_id)
    return None  # Fallback - przycisk użyje label bez emoji

def get_card_asset_path(card, variant='classic'):
    """Get the file path for a card's PNG asset"""
    color = card['color']
    value = card['value']
    
    if color == 'wild':
        if value == 'wild+4':
            filename = 'wild+4.png'
        elif value == 'flip':
            filename = 'wild_flip.png'
        elif value == '+2':
            filename = 'wild_+2.png'
        elif value == 'draw_color':
            filename = 'wild_draw_color_flip.png'
        elif value == '+6':
            filename = 'wild_+6.png'
        elif value == '+10':
            filename = 'wild_+10.png'
        elif value == '+4_reverse':
            filename = 'wild_+4_reverse.png'
        elif value == 'color_roulette':
            filename = 'wild_color_roulette.png'
        # No Mercy+ expansion wild cards
        elif value == 'discard_all':
            filename = 'wild_discard_all_card.png'
        elif value == 'reverse_draw_8':
            filename = 'wild_+8_reverse.png'
        elif value == 'final_attack':
            filename = 'wild_final_attack.png'
        elif value == 'sudden_death':
            filename = 'wild_sudden_death.png'
        else:
            filename = 'wild.png'
    else:
        if isinstance(value, int):
            filename = f"{color}_{value}.png"
        elif value == 'skip':
            filename = f"{color}_block.png"
        elif value == 'reverse':
            filename = f"{color}_reverse.png"
        elif value == '+2':
            filename = f"{color}_+2.png"
        elif value == '+1':
            filename = f"{color}_+1.png"
        elif value == '+5':
            filename = f"{color}_+5.png"
        elif value == '+4':
            filename = f"{color}_+4.png"
        elif value == 'flip':
            filename = f"{color}_flip.png"
        elif value == 'skip_everyone':
            filename = f"{color}_skip_everyone.png"
        elif value == 'discard_all_card':
            filename = f"{color}_discard_all_card.png"
        else:
            filename = f"{color}_{value}.png"
    
    # Wybierz folder w zależności od wariantu
    if variant == 'flip':
        folder_name = 'uno_flip'
    elif variant == 'no_mercy':
        folder_name = 'uno_no_mercy'
    elif variant == 'no_mercy_plus':
        folder_name = 'uno_no_mercy+'
    else:
        folder_name = 'uno_classic'
    
    assets_path = Path(__file__).parent.parent.parent / 'assets' / 'uno_cards' / folder_name
    card_path = assets_path / filename
    
    # Fallback: No Mercy+ uses No Mercy cards if not found
    if variant == 'no_mercy_plus' and not card_path.exists():
        fallback_path = Path(__file__).parent.parent.parent / 'assets' / 'uno_cards' / 'uno_no_mercy'
        fallback_card_path = fallback_path / filename
        if fallback_card_path.exists():
            return fallback_card_path
    
    return card_path

def card_to_image(card, variant='classic'):
    """Convert card to discord.File for sending as attachment"""
    import time
    
    # Auto-detect variant from card properties if not specified
    if variant == 'classic':
        if 'side' in card:
            # Flip cards have 'side' property
            variant = 'flip'
        elif card.get('value') in ['+1', '+5', 'draw_color']:
            # These values only exist in Flip
            variant = 'flip'
        elif card.get('color') in ['teal', 'purple', 'pink', 'orange']:
            # Dark side colors only in Flip
            variant = 'flip'
        elif card.get('value') in ['discard_all', 'reverse_draw_8', 'final_attack', 'sudden_death']:
            # Expansion pack cards only in No Mercy+
            variant = 'no_mercy_plus'
        elif card.get('value') == 10:
            # 10's Play Again only in No Mercy+
            variant = 'no_mercy_plus'
        elif card.get('value') in ['+6', '+10', '+4_reverse', 'color_roulette', 'discard_all_card']:
            # These values exist in No Mercy and No Mercy+
            if card.get('variant') == 'no_mercy_plus':
                variant = 'no_mercy_plus'
            else:
                variant = 'no_mercy'
        elif card.get('value') == '+4' and card.get('color') != 'wild':
            # Colored +4 in No Mercy and No Mercy+
            if card.get('variant') == 'no_mercy_plus':
                variant = 'no_mercy_plus'
            else:
                variant = 'no_mercy'
    
    path = get_card_asset_path(card, variant)
    if path.exists():
        # Add timestamp to filename to prevent Discord caching issues
        base_name = path.stem
        extension = path.suffix
        unique_filename = f"{base_name}_{int(time.time() * 1000)}{extension}"
        return discord.File(path, filename=unique_filename)
    return None

# Card types
NUMBERS = list(range(10))  # 0-9
SPECIAL_CARDS = ['skip', 'reverse', '+2']
WILD_CARDS = ['wild', 'wild+4']

def create_deck():
    """Create a standard UNO deck (108 cards)"""
    deck = []
    
    # Number cards: 0 (1 of each color), 1-9 (2 of each color)
    for color in COLORS:
        deck.append({'color': color, 'value': 0})
        for num in range(1, 10):
            deck.append({'color': color, 'value': num})
            deck.append({'color': color, 'value': num})
    
    # Special cards: 2 of each type per color
    for color in COLORS:
        for special in SPECIAL_CARDS:
            deck.append({'color': color, 'value': special})
            deck.append({'color': color, 'value': special})
    
    # Wild cards: 4 of each type
    for _ in range(4):
        deck.append({'color': 'wild', 'value': 'wild'})
        deck.append({'color': 'wild', 'value': 'wild+4'})
    
    return deck

def shuffle_deck(deck):
    """Shuffle the deck"""
    random.shuffle(deck)
    return deck

def reshuffle_discard_into_deck(deck, discard):
    """When deck runs out, reshuffle discard pile (except top card) into deck"""
    if len(deck) < 5 and len(discard) > 1:  # Keep top card on discard
        # Take all but the last card from discard
        top_card = discard[-1]  # Save the top card
        cards_to_reshuffle = discard[:-1].copy()  # Copy all but top card
        discard.clear()
        discard.append(top_card)  # Put top card back
        # Shuffle and add to deck
        random.shuffle(cards_to_reshuffle)
        deck.extend(cards_to_reshuffle)
        return True
    return False

def draw_cards(deck, count=1):
    """Draw cards from deck"""
    drawn = []
    for _ in range(count):
        if deck:
            drawn.append(deck.pop())
    return drawn

def card_to_string(card, compact=False, lang='en'):
    """Convert card to display string (for text descriptions)"""
    color_emoji = COLOR_EMOJIS.get(card['color'], '⚫')
    value = card['value']
    
    # Get color names from translations
    color_key = f"colors.{card['color']}"
    color_name = get_text(color_key, lang)
    
    if compact:
        # Shorter version for buttons
        if isinstance(value, int):
            return f"{color_name} {value}"
        elif value == 'skip':
            return f"{color_name} {get_text('actions.skip', lang).upper()}"
        elif value == 'skip_everyone':
            return f"{color_name} {get_text('actions.skip_everyone', lang).upper()}"
        elif value == 'reverse':
            return f"{color_name} {get_text('actions.reverse', lang).upper()}"
        elif value == '+1':
            return f"{color_name} +1"
        elif value == '+2':
            return f"{color_name} +2"
        elif value == '+5':
            return f"{color_name} +5"
        elif value == 'flip':
            return f"{color_name} {get_text('actions.flip', lang).upper()}"
        elif value == 'wild':
            return get_text('colors.wild', lang).upper()
        elif value == 'wild+4':
            return f"{get_text('colors.wild', lang).upper()} +4"
        elif value == 'draw_color':
            return f"{get_text('colors.wild', lang).upper()} DRAW COLOR"
        return f"{color_name} {value}"
    else:
        # Full version for display
        if isinstance(value, int):
            return f"{color_emoji} **{color_name} {value}**"
        elif value == 'skip':
            return f"{color_emoji} **{color_name} {get_text('actions.skip', lang).upper()}**"
        elif value == 'skip_everyone':
            return f"{color_emoji} **{color_name} {get_text('actions.skip_everyone', lang).upper()}**"
        elif value == 'reverse':
            return f"{color_emoji} **{color_name} {get_text('actions.reverse', lang).upper()}**"
        elif value == '+1':
            return f"{color_emoji} **{color_name} +1**"
        elif value == '+2':
            return f"{color_emoji} **{color_name} +2**"
        elif value == '+5':
            return f"{color_emoji} **{color_name} +5**"
        elif value == 'flip':
            return f"{color_emoji} **{color_name} {get_text('actions.flip', lang).upper()}**"
        elif value == 'wild':
            return f"🌈 **{get_text('colors.wild', lang).upper()}**"
        elif value == 'wild+4':
            return f"🌈 **{get_text('colors.wild', lang).upper()} +4**"
        elif value == 'draw_color':
            return f"🌈 **{get_text('colors.wild', lang).upper()} DRAW COLOR**"
        return f"{color_emoji} **{color_name} {value}**"

def can_play_card(card, top_card, current_color, draw_stack=0, settings=None):
    """Check if a card can be played on the current top card"""
    if settings is None:
        settings = {}
    
    # If there's a draw stack, only specific cards can be played
    if draw_stack > 0:
        variant = settings.get('variant', 'classic')
        
        # No Mercy / No Mercy+ mode: ALL draw cards can stack together
        if variant == 'no_mercy' or variant == 'no_mercy_plus':
            # List of ALL draw cards that can stack
            all_draw_cards = ['draw_2', '+2', 'wild+4', '+4', '+6', '+10', '+4_reverse', 'reverse_draw_8']
            
            # Check if both cards are draw cards
            top_is_draw = top_card['value'] in all_draw_cards
            card_is_draw = card['value'] in all_draw_cards
            
            # If either stacking setting is enabled, allow all draw cards to stack
            if (settings.get('stack_plus_two') or settings.get('stack_plus_four') or settings.get('stack_combined')):
                if top_is_draw and card_is_draw:
                    return True
            
            return False  # Must accept draw penalty
        
        # Flip mode: Can stack +1 on +1 or +5 on +5
        if variant == 'flip' and settings.get('stack_flip_draw'):
            if top_card['value'] == '+1' and card['value'] == '+1':
                return True
            if top_card['value'] == '+5' and card['value'] == '+5':
                return True
            # Can play +1 and +5 together (combined stacking in Flip)
            if settings.get('stack_combined'):
                if top_card['value'] == '+1' and card['value'] == '+5':
                    return True
                if top_card['value'] == '+5' and card['value'] == '+1':
                    return True
            return False  # Must accept draw penalty
        
        # Classic mode: Can stack +2 on +2
        if settings.get('stack_plus_two') and top_card['value'] == '+2' and card['value'] == '+2':
            return True
        # Can stack +4 on +4
        if settings.get('stack_plus_four') and top_card['value'] == 'wild+4' and card['value'] == 'wild+4':
            return True
        # Can play +2 and +4 together (combined stacking in Classic)
        if settings.get('stack_combined'):
            if top_card['value'] == '+2' and card['value'] == 'wild+4':
                return True
            if top_card['value'] == 'wild+4' and card['value'] == '+2':
                return True
        return False  # Must accept draw penalty
    
    # Wild cards can always be played
    if card['color'] == 'wild':
        return True
    
    # Match color (using current_color for wild cards)
    if card['color'] == current_color:
        return True
    
    # Match value
    if card['value'] == top_card['value']:
        return True
    
    return False

def get_playable_cards(hand, top_card, current_color, draw_stack=0, settings=None):
    """Get list of playable card indices from hand"""
    playable = []
    for i, card in enumerate(hand):
        if can_play_card(card, top_card, current_color, draw_stack, settings):
            playable.append(i)
    return playable

def apply_card_effect(card, game_state):
    """Apply card effects to game state"""
    value = card['value']
    settings = game_state.get('settings', {})
    variant = settings.get('variant', 'classic')
    
    # No Mercy effects
    if variant == 'no_mercy' or variant == 'no_mercy_plus':
        if value == '+4' and card['color'] != 'wild':
            # Colored +4 in No Mercy
            return {'draw_penalty': 4}
        elif value == '+6':
            # Wild +6
            return {'draw_penalty': 6}
        elif value == '+10':
            # Wild +10
            return {'draw_penalty': 10}
        elif value == '+4_reverse':
            # Wild +4 Reverse: draw 4 AND reverse
            return {'draw_penalty': 4, 'reverse': True}
        elif value == 'skip_everyone':
            # Skip Everyone: only current player plays
            return {'skip_everyone': True}
        elif value == 'discard_all_card':
            # Discard All Card: player discards all matching color cards
            return {'discard_all': card['color']}
        elif value == 'color_roulette':
            # Color Roulette: like Wild Draw Color
            return {'draw_color': True}
        # No Mercy+ expansion effects
        elif value == 'reverse_draw_8':
            # Wild Reverse Draw 8: reverse + draw 8
            return {'draw_penalty': 8, 'reverse': True}
        elif value == 'final_attack':
            # Wild Final Attack: handled separately
            return {'final_attack': True}
        elif value == 'sudden_death':
            # Wild Sudden Death: handled separately
            return {'sudden_death': True}
        elif value == 'discard_all':
            # Wild Discard All: handled separately
            return {'wild_discard_all': True}
        elif value == 10:
            # 10's Play Again: extra turn
            return {'play_again': True}
    
    if value == 'skip':
        # Skip next player
        return {'skip_next': True}
    
    elif value == 'skip_everyone':
        # Flip dark side: Skip everyone except current player
        return {'skip_everyone': True}
    
    elif value == 'reverse':
        # Reverse direction
        return {'reverse': True}
    
    elif value == '+2':
        # Next player draws 2
        return {'draw_penalty': 2}
    
    elif value == '+1':
        # Flip light side: Next player draws 1
        return {'draw_penalty': 1}
    
    elif value == '+5':
        # Flip dark side: Next player draws 5
        return {'draw_penalty': 5}
    
    elif value == 'wild+4':
        # Next player draws 4
        return {'draw_penalty': 4}
    
    elif value == 'flip':
        # FLIP card - handled separately in game logic
        return {'flip': True}
    
    elif value == 'draw_color':
        # Wild Draw Color: Next player chooses color and draws until they get that color
        return {'draw_color': True}
    
    elif value == 7 and settings.get('seven_zero', False):
        # 7-0 Rule: Player chooses someone to swap hands with
        return {'swap_hands': True}
    
    elif value == 0 and settings.get('seven_zero', False):
        # 7-0 Rule: All hands rotate in play direction
        return {'rotate_hands': True}
    
    return {}

def bot_choose_card(hand, top_card, current_color):
    """Simple bot AI to choose a card"""
    playable = get_playable_cards(hand, top_card, current_color)
    
    if not playable:
        return None
    
    # Priority: special cards > wild cards > matching color > matching value
    special_cards = []
    wild_cards = []
    color_match = []
    value_match = []
    
    for idx in playable:
        card = hand[idx]
        if card['value'] in SPECIAL_CARDS:
            special_cards.append(idx)
        elif card['color'] == 'wild':
            wild_cards.append(idx)
        elif card['color'] == current_color:
            color_match.append(idx)
        else:
            value_match.append(idx)
    
    # Choose in priority order
    if color_match:
        return random.choice(color_match)
    if value_match:
        return random.choice(value_match)
    if special_cards:
        return random.choice(special_cards)
    if wild_cards:
        return random.choice(wild_cards)
    
    return playable[0]

def bot_choose_color(hand):
    """Bot chooses a color for wild card"""
    # Count colors in hand
    color_counts = {color: 0 for color in COLORS}
    for card in hand:
        if card['color'] in COLORS:
            color_counts[card['color']] += 1
    
    # Choose most common color
    return max(color_counts.items(), key=lambda x: x[1])[0]

def check_uno(hand):
    """Check if player should call UNO (1 card left)"""
    return len(hand) == 1

def check_winner(hand):
    """Check if player has won (0 cards left)"""
    return len(hand) == 0
