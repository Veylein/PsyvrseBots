"""
Card Visualization System - PIL-based rendering for all card games
Supports multiple card decks (classic, dark, platinum) and custom backgrounds
"""
from PIL import Image, ImageDraw, ImageFont
import io
import discord
import os
import random

# ==================== CONSTANTS ====================

# Colors
FELT_GREEN = (53, 101, 77)
FELT_DARK = (35, 70, 55)
CARD_WHITE = (255, 255, 255)
CARD_BORDER = (200, 200, 200)
TEXT_WHITE = (255, 255, 255)
TEXT_GOLD = (255, 215, 0)
TEXT_BLACK = (30, 30, 30)
BUTTON_BG = (70, 120, 90)

# Card sizes
CARD_WIDTH = 80
CARD_HEIGHT = 112
CARD_SPACING = 10

# Suit mappings
SUIT_DISPLAY = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
SUIT_COLORS = {'h': (220, 20, 60), 'd': (220, 20, 60), 'c': (0, 0, 0), 's': (0, 0, 0)}
SUIT_NAMES_PL = {'h': 'kier', 'd': 'karo', 'c': 'trefl', 's': 'pik'}

# Card image cache
CARD_IMAGE_CACHE = {}

# ==================== FONT MANAGEMENT ====================

def get_font(size, bold=False):
    """Get font with fallback"""
    try:
        if bold:
            return ImageFont.truetype("arialbd.ttf", size)
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

# ==================== CARD IMAGE LOADING ====================

def get_card_image_path(rank, suit, deck='classic'):
    """Get path to card PNG file"""
    rank_names = {
        'j': 'walet', 'q': 'dama', 'k': 'krol', 'a': 'as',
        '2': '2', '3': '3', '4': '4', '5': '5', '6': '6',
        '7': '7', '8': '8', '9': '9', '10': '10'
    }
    
    suit_name = SUIT_NAMES_PL.get(suit.lower(), 'pik')
    rank_name = rank_names.get(rank.lower(), rank)
    filename = f"{rank_name}_{suit_name}.png"
    
    # Try deck-specific path
    card_path = os.path.join('assets', 'cards', deck, filename)
    if not os.path.exists(card_path):
        # Fallback to classic
        card_path = os.path.join('assets', 'cards', 'classic', filename)
    
    return card_path if os.path.exists(card_path) else None

def load_card_image(rank, suit, deck='classic', size=None):
    """Load card image from PNG with caching"""
    cache_key = f"{deck}_{rank}_{suit}_{size}"
    
    if cache_key in CARD_IMAGE_CACHE:
        return CARD_IMAGE_CACHE[cache_key]
    
    card_path = get_card_image_path(rank, suit, deck)
    if not card_path:
        return None
    
    try:
        img = Image.open(card_path)
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        CARD_IMAGE_CACHE[cache_key] = img
        return img
    except Exception as e:
        print(f"❌ Error loading card {rank}{suit}: {e}")
        return None

def load_card_back(deck='classic', size=None):
    """Load card back image"""
    cache_key = f"{deck}_back_{size}"
    
    if cache_key in CARD_IMAGE_CACHE:
        return CARD_IMAGE_CACHE[cache_key]
    
    back_path = os.path.join('assets', 'cards', deck, 'back.png')
    if not os.path.exists(back_path):
        back_path = os.path.join('assets', 'cards', 'classic', 'back.png')
    
    if not os.path.exists(back_path):
        return None
    
    try:
        img = Image.open(back_path)
        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        CARD_IMAGE_CACHE[cache_key] = img
        return img
    except Exception as e:
        print(f"❌ Error loading card back: {e}")
        return None

# ==================== CARD DRAWING ====================

def parse_card(card_str):
    """Parse card string 'Ah' -> ('a', 'h')"""
    if not card_str or len(card_str) < 2:
        return None, None
    return card_str[:-1].lower(), card_str[-1].lower()

def draw_card(draw, x, y, rank, suit, width=CARD_WIDTH, height=CARD_HEIGHT, 
              img_base=None, deck='classic', show_face=True):
    """Draw a single card (face or back)"""
    # Draw card background
    draw.rounded_rectangle(
        [(x, y), (x + width, y + height)],
        radius=8,
        fill=CARD_WHITE,
        outline=CARD_BORDER,
        width=2
    )
    
    if not show_face:
        # Draw card back
        card_size = (int(width * 0.95), int(height * 0.95))
        back_img = load_card_back(deck, card_size)
        
        if back_img and img_base:
            offset_x = x + (width - card_size[0]) // 2
            offset_y = y + (height - card_size[1]) // 2
            try:
                img_base.paste(back_img, (offset_x, offset_y), back_img)
                return
            except:
                pass
        
        # Fallback pattern for back
        spacing = max(10, int(width / 8))
        dot_size = max(5, int(width / 12))
        pattern_color = (50, 100, 200)
        for i in range(5, height - 5, spacing):
            for j in range(5, width - 5, spacing):
                draw.ellipse([(x + j, y + i), (x + j + dot_size, y + i + dot_size)], fill=pattern_color)
        return
    
    # Draw card face
    if img_base:
        card_size = (int(width * 0.95), int(height * 0.95))
        card_img = load_card_image(rank, suit, deck, card_size)
        
        if card_img:
            offset_x = x + (width - card_size[0]) // 2
            offset_y = y + (height - card_size[1]) // 2
            try:
                img_base.paste(card_img, (offset_x, offset_y), card_img)
                return
            except:
                pass
    
    # Fallback: draw simple card with symbols
    suit_symbol = SUIT_DISPLAY.get(suit, '♠')
    color = SUIT_COLORS.get(suit, (0, 0, 0))
    
    rank_font = get_font(32, bold=True)
    suit_font = get_font(36, bold=True)
    
    # Rank (top left)
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

def draw_card_string(draw, x, y, card_str, width=CARD_WIDTH, height=CARD_HEIGHT,
                     img_base=None, deck='classic', show_face=True):
    """Draw card from string like 'Ah'"""
    rank, suit = parse_card(card_str)
    if rank and suit:
        draw_card(draw, x, y, rank, suit, width, height, img_base, deck, show_face)
    else:
        # Empty card slot
        draw.rounded_rectangle(
            [(x, y), (x + width, y + height)],
            radius=8,
            fill=(100, 100, 100),
            outline=CARD_BORDER,
            width=2
        )

# ==================== GAME-SPECIFIC VISUALIZATIONS ====================

def create_hand_image(cards, title="Your Hand", deck='classic', width=None, height=None):
    """Create image showing a hand of cards"""
    num_cards = len(cards)
    if num_cards == 0:
        num_cards = 1
    
    if not width:
        width = num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING + 40
    if not height:
        height = CARD_HEIGHT + 80
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=3)
    
    # Title
    title_font = get_font(24, bold=True)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 15), title, fill=TEXT_GOLD, font=title_font)
    
    # Cards
    if cards:
        start_x = (width - (num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING)) // 2
        cards_y = 50
        
        for i, card in enumerate(cards):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            draw_card_string(draw, x, cards_y, card, img_base=img, deck=deck)
    else:
        # No cards message
        no_cards_font = get_font(18)
        msg = "No cards"
        msg_bbox = draw.textbbox((0, 0), msg, font=no_cards_font)
        msg_width = msg_bbox[2] - msg_bbox[0]
        draw.text(((width - msg_width) // 2, 80), msg, fill=TEXT_WHITE, font=no_cards_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='hand.png')

def create_table_image(community_cards, title="Table", deck='classic', info_text=None,
                       width=600, height=300, show_backs=False):
    """Create image showing cards on table"""
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=4)
    
    # Title
    title_font = get_font(28, bold=True)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 15), title, fill=TEXT_GOLD, font=title_font)
    
    # Info text
    if info_text:
        info_font = get_font(16)
        info_bbox = draw.textbbox((0, 0), info_text, font=info_font)
        info_width = info_bbox[2] - info_bbox[0]
        draw.text(((width - info_width) // 2, 50), info_text, fill=TEXT_WHITE, font=info_font)
    
    # Cards
    if community_cards:
        num_cards = len(community_cards)
        total_width = num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING
        start_x = (width - total_width) // 2
        cards_y = 100
        
        for i, card in enumerate(community_cards):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            if show_backs:
                draw_card_string(draw, x, cards_y, card, img_base=img, deck=deck, show_face=False)
            else:
                draw_card_string(draw, x, cards_y, card, img_base=img, deck=deck)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='table.png')

def create_comparison_image(player_cards, opponent_cards, player_name="You", 
                           opponent_name="Opponent", deck='classic', result_text=None):
    """Create side-by-side comparison of two hands"""
    width = 500
    height = 400
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=4)
    
    # Player 1 section
    name_font = get_font(20, bold=True)
    draw.text((50, 30), player_name, fill=TEXT_WHITE, font=name_font)
    
    if player_cards:
        start_x = 50
        for i, card in enumerate(player_cards[:5]):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            draw_card_string(draw, x, 60, card, img_base=img, deck=deck)
    
    # VS divider
    vs_font = get_font(32, bold=True)
    draw.text((width // 2 - 20, height // 2 - 20), "VS", fill=TEXT_GOLD, font=vs_font)
    
    # Player 2 section
    draw.text((50, 220), opponent_name, fill=TEXT_WHITE, font=name_font)
    
    if opponent_cards:
        start_x = 50
        for i, card in enumerate(opponent_cards[:5]):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            draw_card_string(draw, x, 250, card, img_base=img, deck=deck)
    
    # Result text at bottom
    if result_text:
        result_font = get_font(22, bold=True)
        result_bbox = draw.textbbox((0, 0), result_text, font=result_font)
        result_width = result_bbox[2] - result_bbox[0]
        
        # Color based on result
        color = TEXT_GOLD
        if "win" in result_text.lower():
            color = (0, 255, 100)
        elif "lose" in result_text.lower() or "lost" in result_text.lower():
            color = (255, 50, 50)
        
        draw.text(((width - result_width) // 2, height - 40), result_text, fill=color, font=result_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='comparison.png')

# ==================== BLACKJACK SPECIFIC ====================

def create_blackjack_image(player_hand, dealer_hand, player_total, dealer_total, 
                          player_name="You", deck='classic', show_dealer_card=True):
    """Create blackjack game visualization"""
    width = 600
    height = 450
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=4)
    
    # Title
    title_font = get_font(32, bold=True)
    draw.text((width // 2 - 100, 20), "♠ BLACKJACK ♥", fill=TEXT_GOLD, font=title_font)
    
    # Dealer section
    dealer_font = get_font(20, bold=True)
    draw.text((50, 80), f"Dealer: {dealer_total if show_dealer_card else '?'}", 
              fill=TEXT_WHITE, font=dealer_font)
    
    if dealer_hand:
        start_x = 50
        for i, card in enumerate(dealer_hand):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            if i == 0 or show_dealer_card:
                draw_card_string(draw, x, 110, card, img_base=img, deck=deck)
            else:
                draw_card_string(draw, x, 110, card, img_base=img, deck=deck, show_face=False)
    
    # Player section
    player_font = get_font(20, bold=True)
    draw.text((50, 260), f"{player_name}: {player_total}", fill=TEXT_WHITE, font=player_font)
    
    if player_hand:
        start_x = 50
        for i, card in enumerate(player_hand):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            draw_card_string(draw, x, 290, card, img_base=img, deck=deck)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='blackjack.png')

# ==================== WAR SPECIFIC ====================

def create_war_image(player_card, opponent_card, player_name="You", 
                    opponent_name="Opponent", deck='classic', result_text=None, opponent_deck='classic'):
    """Create War game visualization"""
    width = 500
    height = 350
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=4)
    
    # Title
    title_font = get_font(36, bold=True)
    draw.text((width // 2 - 60, 20), "WAR", fill=TEXT_GOLD, font=title_font)
    
    # Cards side by side
    card_y = 100
    
    # Player card (left) - uses player's deck
    name_font = get_font(18, bold=True)
    draw.text((80, 70), player_name, fill=TEXT_WHITE, font=name_font)
    draw_card_string(draw, 70, card_y, player_card, img_base=img, deck=deck)
    
    # VS
    vs_font = get_font(32, bold=True)
    draw.text((width // 2 - 25, card_y + 40), "VS", fill=TEXT_GOLD, font=vs_font)
    
    # Opponent card (right) - uses opponent's deck (classic for bot)
    draw.text((width - 180, 70), opponent_name, fill=TEXT_WHITE, font=name_font)
    draw_card_string(draw, width - 160, card_y, opponent_card, img_base=img, deck=opponent_deck)
    
    # Result
    if result_text:
        result_font = get_font(24, bold=True)
        result_bbox = draw.textbbox((0, 0), result_text, font=result_font)
        result_width = result_bbox[2] - result_bbox[0]
        
        color = TEXT_GOLD
        if "win" in result_text.lower():
            color = (0, 255, 100)
        elif "lose" in result_text.lower():
            color = (255, 50, 50)
        
        draw.text(((width - result_width) // 2, height - 60), result_text, fill=color, font=result_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='war.png')

def create_poker_table_image(community_cards, players_data, pot, current_phase, 
                             deck='classic', width=800, height=600):
    """
    Create Texas Hold'em table image with player cards
    
    players_data: list of dicts with keys:
        - name: player name
        - cards: list of 2 cards ['Ah', 'Kd'] or [] for face-down
        - chips: chip count
        - bet: current bet
        - status: 'active', 'folded', 'all_in', 'dealer', 'turn'
        - is_bot: True if bot
    """
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width, height)], outline=FELT_DARK, width=4)
    
    # ===== POT AND PHASE =====
    pot_font = get_font(32, bold=True)
    phase_font = get_font(20, bold=True)
    
    pot_text = f"Pula: {pot} 💎"
    pot_bbox = draw.textbbox((0, 0), pot_text, font=pot_font)
    pot_width = pot_bbox[2] - pot_bbox[0]
    draw.text(((width - pot_width) // 2, 20), pot_text, fill=TEXT_GOLD, font=pot_font)
    
    phase_text = current_phase
    phase_bbox = draw.textbbox((0, 0), phase_text, font=phase_font)
    phase_width = phase_bbox[2] - phase_bbox[0]
    draw.text(((width - phase_width) // 2, 60), phase_text, fill=TEXT_WHITE, font=phase_font)
    
    # ===== COMMUNITY CARDS =====
    num_community = len(community_cards) if community_cards else 5
    cards_width = num_community * CARD_WIDTH + (num_community - 1) * 10
    cards_start_x = (width - cards_width) // 2
    cards_y = 100
    
    if community_cards:
        for i, card in enumerate(community_cards):
            x = cards_start_x + i * (CARD_WIDTH + 10)
            draw_card_string(draw, x, cards_y, card, img_base=img, deck=deck)
    else:
        # Show card backs
        for i in range(5):
            x = cards_start_x + i * (CARD_WIDTH + 10)
            draw_card_string(draw, x, cards_y, "🎴", img_base=img, deck=deck, show_face=False)
    
    # ===== PLAYER BOXES =====
    if not players_data:
        return discord.File(fp=io.BytesIO(img.tobytes()), filename='poker_table.png')
    
    # Position players at bottom
    num_players = len(players_data)
    player_box_width = 140
    player_box_height = 180
    player_spacing = 20
    
    total_width = num_players * player_box_width + (num_players - 1) * player_spacing
    start_x = (width - total_width) // 2
    player_y = height - player_box_height - 20
    
    name_font = get_font(14, bold=True)
    info_font = get_font(12)
    small_font = get_font(10)
    
    for i, player in enumerate(players_data):
        x = start_x + i * (player_box_width + player_spacing)
        
        # Determine box color based on status
        box_color = (40, 40, 40)  # default dark
        border_color = FELT_DARK
        border_width = 2
        
        if player.get('status') == 'turn':
            box_color = (60, 100, 60)  # green for current turn
            border_color = (100, 255, 100)
            border_width = 4
        elif player.get('status') == 'folded':
            box_color = (30, 30, 30)  # darker for folded
            border_color = (100, 100, 100)
        elif player.get('status') == 'all_in':
            box_color = (100, 40, 40)  # red for all-in
            border_color = (255, 100, 100)
            border_width = 3
        elif player.get('status') == 'dealer':
            border_color = TEXT_GOLD
            border_width = 3
        
        # Draw player box
        draw.rounded_rectangle(
            [(x, player_y), (x + player_box_width, player_y + player_box_height)],
            radius=10,
            fill=box_color,
            outline=border_color,
            width=border_width
        )
        
        # Player icon and name
        icon = "🤖" if player.get('is_bot') else "👤"
        name = player['name'][:12]  # truncate long names
        name_text = f"{icon} {name}"
        
        name_bbox = draw.textbbox((0, 0), name_text, font=name_font)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text((x + (player_box_width - name_width) // 2, player_y + 5), 
                 name_text, fill=TEXT_WHITE, font=name_font)
        
        # Cards (2 small cards)
        cards = player.get('cards', [])
        card_width = 50
        card_height = 70
        cards_x = x + (player_box_width - (2 * card_width + 5)) // 2
        cards_y = player_y + 30
        
        if cards and len(cards) >= 2:
            # Show player's cards
            for j, card in enumerate(cards[:2]):
                card_x = cards_x + j * (card_width + 5)
                draw_card_string(draw, card_x, cards_y, card, 
                               width=card_width, height=card_height,
                               img_base=img, deck=deck)
        else:
            # Show card backs
            for j in range(2):
                card_x = cards_x + j * (card_width + 5)
                draw_card_string(draw, card_x, cards_y, "🎴",
                               width=card_width, height=card_height,
                               img_base=img, deck=deck, show_face=False)
        
        # Chips and bet info
        chips_y = player_y + 110
        chips_text = f"💎 {player.get('chips', 0)}"
        chips_bbox = draw.textbbox((0, 0), chips_text, font=info_font)
        chips_width = chips_bbox[2] - chips_bbox[0]
        draw.text((x + (player_box_width - chips_width) // 2, chips_y),
                 chips_text, fill=TEXT_GOLD, font=info_font)
        
        # Current bet
        bet = player.get('bet', 0)
        if bet > 0:
            bet_text = f"Stawka: {bet}"
            bet_bbox = draw.textbbox((0, 0), bet_text, font=small_font)
            bet_width = bet_bbox[2] - bet_bbox[0]
            draw.text((x + (player_box_width - bet_width) // 2, chips_y + 20),
                     bet_text, fill=TEXT_WHITE, font=small_font)
        
        # Status indicator
        status = player.get('status', '')
        if status in ['folded', 'all_in', 'dealer']:
            status_texts = {
                'folded': '[FOLD]',
                'all_in': '[ALL-IN]',
                'dealer': '[D]'
            }
            status_text = status_texts.get(status, '')
            status_bbox = draw.textbbox((0, 0), status_text, font=small_font)
            status_width = status_bbox[2] - status_bbox[0]
            draw.text((x + (player_box_width - status_width) // 2, player_y + player_box_height - 25),
                     status_text, fill=TEXT_GOLD, font=small_font)
    
    # ===== WAITING INDICATOR (if applicable) =====
    waiting_text = "Czekamy na graczy..."
    if any(p.get('status') == 'turn' for p in players_data):
        current_player = next((p for p in players_data if p.get('status') == 'turn'), None)
        if current_player:
            waiting_text = f"⏰ Ruch: {current_player['name']}"
    
    waiting_font = get_font(16)
    waiting_bbox = draw.textbbox((0, 0), waiting_text, font=waiting_font)
    waiting_width = waiting_bbox[2] - waiting_bbox[0]
    draw.text(((width - waiting_width) // 2, 270), waiting_text, fill=TEXT_WHITE, font=waiting_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='poker_table.png')
