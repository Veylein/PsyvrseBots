"""
Blackjack - Fast & Long modes
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import json
import os
from PIL import Image, ImageDraw, ImageFont
import io

# Reuse poker visual functions
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from poker.py
from poker import (
    create_deck, get_card_image, draw_card, draw_card_back, 
    get_font, parse_card, FELT_GREEN, FELT_DARK, TEXT_WHITE, 
    TEXT_GOLD, CARD_BORDER, POT_BG, CARD_WIDTH, CARD_HEIGHT, 
    CARD_SPACING, TABLE_WIDTH, TABLE_HEIGHT, CARD_WHITE, draw_card_back
)

# Active games
active_blackjack_games = {}

def create_blackjack_settings_view(lobby_id, settings):
    """Creates view with blackjack settings"""
    settings_view = discord.ui.View(timeout=60)
    
    # Row 0: Game mode (COOP vs PVP)
    mode_btn = discord.ui.Button(
        label=f"🎮 Mode: {'COOP' if settings['game_mode'] == 'coop' else 'PVP'}",
        style=discord.ButtonStyle.success if settings['game_mode'] == 'coop' else discord.ButtonStyle.danger,
        custom_id=f"blackjack_setting_mode_{lobby_id}",
        row=0
    )
    settings_view.add_item(mode_btn)
    
    # Row 1: Bet amount
    bet_btn = discord.ui.Button(
        label=f"💰 Bet: {settings['bet_amount']}",
        style=discord.ButtonStyle.secondary,
        custom_id=f"blackjack_setting_bet_{lobby_id}",
        row=1
    )
    settings_view.add_item(bet_btn)
    
    # Row 2: Max players
    max_btn = discord.ui.Button(
        label=f"👤 Max: {settings['max_players']}",
        style=discord.ButtonStyle.secondary,
        custom_id=f"blackjack_setting_max_{lobby_id}",
        row=2
    )
    settings_view.add_item(max_btn)
    
    return settings_view


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


class BlackjackActionView(discord.ui.View):
    """Action buttons for blackjack"""
    
    def __init__(self, player_id, can_double=True, player_cards=None, player_value=0, player_name="", is_pvp=False, economy_cog=None):
        super().__init__(timeout=120)
        self.player_id = player_id
        self.action = None
        self.player_cards = player_cards or []
        self.player_value = player_value
        self.player_name = player_name
        self.is_pvp = is_pvp
        self.economy_cog = economy_cog
        
        if not can_double:
            self.double_btn.disabled = True
    
    @discord.ui.button(label="👊 Hit", style=discord.ButtonStyle.primary, row=0)
    async def hit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        self.action = "hit"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="✋ Stand", style=discord.ButtonStyle.success, row=0)
    async def stand_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        self.action = "stand"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="💰 Double", style=discord.ButtonStyle.danger, row=0)
    async def double_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        self.action = "double"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="🚪 Leave", style=discord.ButtonStyle.secondary, row=1)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        self.action = "leave"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label="🃏 Hand", style=discord.ButtonStyle.secondary, row=1)
    async def hand_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        # Calculate visible value for PVP (1st + 3rd+ cards)
        if self.is_pvp and len(self.player_cards) >= 2:
            visible_cards = [self.player_cards[0]]
            if len(self.player_cards) > 2:
                visible_cards.extend(self.player_cards[2:])
            visible_value = calculate_hand_value(visible_cards)
            display_value = f"?+{visible_value}"
        else:
            display_value = str(self.player_value)
        
        # Get user's card deck
        deck = 'classic'
        if self.economy_cog:
            deck = self.economy_cog.get_user_card_deck(interaction.user.id)
        
        # Create hand image with hidden 2nd card in PVP
        hand_image = await asyncio.to_thread(
            create_blackjack_hand_image,
            self.player_cards,
            self.player_value,
            self.player_name,
            is_pvp=self.is_pvp,
            deck=deck
        )
        hand_embed = discord.Embed(
            title="🃏 Your Cards 🃏",
            description=f"Value: **{display_value}**",
            color=discord.Color.blue()
        )
        hand_embed.set_image(url="attachment://blackjack_hand.png")
        
        # Send as ephemeral
        await interaction.response.send_message(embed=hand_embed, file=hand_image, ephemeral=True)
        # Don't stop the view - just showing cards
    
    @discord.ui.button(label="⚠️", style=discord.ButtonStyle.secondary, row=2)
    async def disclaimer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show gambling disclaimer"""
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
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # Don't stop the view - just showing disclaimer


def calculate_hand_value(cards):
    """Calculate blackjack hand value"""
    value = 0
    aces = 0
    
    for card in cards:
        if isinstance(card, tuple):
            rank, suit = card
        else:
            rank, suit = parse_card(card)
        
        rank = rank.lower()  # Normalize to lowercase
        if rank in ['j', 'q', 'k']:
            value += 10
        elif rank == 'a':
            aces += 1
            value += 11
        else:
            value += int(rank)
    
    # Adjust for aces
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    
    return value


def create_blackjack_hand_image(cards, value, player_name, is_pvp=False, deck='classic'):
    """Create image showing player's current hand in blackjack"""
    from poker import CARD_WIDTH, CARD_HEIGHT, CARD_SPACING, FELT_GREEN, FELT_DARK, TEXT_GOLD, draw_card, draw_card_back, parse_card, get_font
    
    num_cards = len(cards)
    width = num_cards * CARD_WIDTH + (num_cards - 1) * CARD_SPACING + 40
    height = CARD_HEIGHT + 100
    
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
    
    # Value
    value_font = get_font(18, bold=True)
    if is_pvp and len(cards) >= 2:
        # Show partial value (1st + 3rd+ cards)
        visible_cards = [cards[0]]
        if len(cards) > 2:
            visible_cards.extend(cards[2:])
        visible_value = calculate_hand_value(visible_cards)
        value_text = f"Value: ?+{visible_value}"
    else:
        value_text = f"Value: {value}"
    value_bbox = draw.textbbox((0, 0), value_text, font=value_font)
    value_width = value_bbox[2] - value_bbox[0]
    draw.text(((width - value_width) // 2, 35), value_text, fill=TEXT_GOLD, font=value_font)
    
    # Cards
    if cards:
        start_x = 20
        cards_y = 65
        
        for i, card in enumerate(cards):
            x = start_x + i * (CARD_WIDTH + CARD_SPACING)
            # Hide 2nd card (index 1) in PVP
            if is_pvp and i == 1:
                draw_card_back(draw, x, cards_y, width=CARD_WIDTH, height=CARD_HEIGHT, img_base=img, deck=deck)
            else:
                rank, suit = parse_card(card)
                if rank and suit:
                    draw_card(draw, x, cards_y, rank, suit, img_base=img, deck=deck)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='blackjack_hand.png')


def create_blackjack_table_image(dealer_cards, dealer_value, players, show_dealer=False, pot=0, is_pvp=False, current_player_index=None, deck='classic'):
    """Create blackjack table image with all players - uses assets/fonts
    
    Args:
        dealer_cards: List of dealer's cards e.g. ['Ah', 'Kd']
        dealer_value: Dealer's hand value
        players: List of player dicts with {user, cards, value, bet, status, result}
        show_dealer: Whether to reveal dealer's hidden card (or all cards in final)
        pot: Total pot (sum of all bets)
        is_pvp: Whether it's PVP mode (no dealer)
        current_player_index: Index of current player (for hiding other players' cards in PVP)
        deck: Card deck theme ('classic', 'dark', 'platinum')
    
    Returns:
        discord.File with PNG image
    """
    # Calculate dynamic table height based on number of rows and max cards
    num_players = len(players) if players else 0
    players_per_row = 3
    num_rows = (num_players + players_per_row - 1) // players_per_row if num_players > 0 else 1
    
    # Calculate height for each row
    max_cards = max(len(p.get('cards', [])) for p in players) if players else 2
    base_row_height = 220  # Increased from 180
    extra_height_per_card = 40 if max_cards > 4 else 0  # Increased from 30
    row_height = base_row_height + (max_cards - 4) * extra_height_per_card if max_cards > 4 else base_row_height
    
    # Total height = base + (rows * row_height) + gaps between rows
    gap_between_rows = 80  # Increased from 60
    total_rows_height = num_rows * row_height + (num_rows - 1) * gap_between_rows if num_rows > 0 else 0
    
    # Calculate required table width based on player count and cards
    small_card_width = 70
    base_table_width = 1000
    
    if players:
        # Pre-calculate max box width needed
        max_cards_any_player = max(len(p.get('cards', [])) for p in players)
        cards_width = max_cards_any_player * small_card_width + (max_cards_any_player - 1) * 5
        max_box_width = max(200, cards_width + 30)
        
        # Calculate required width for 3 players per row
        players_per_row = 3
        min_gap = 30
        required_row_width = (max_box_width + min_gap) * min(players_per_row, len(players))
        
        # Add padding and check if we need wider table
        required_table_width = required_row_width + 120  # Extra padding for margins
        table_width = max(base_table_width, required_table_width)
    else:
        table_width = base_table_width
    
    table_height = TABLE_HEIGHT + 300 + total_rows_height  # Increased from 200
    img = Image.new('RGB', (table_width, table_height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (table_width-1, table_height-1)], outline=FELT_DARK, width=5)
    
    # Title
    title_font = get_font(48, bold=True)  # Increased from 38
    title = "Blackjack"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((table_width - title_width) // 2, 20), title, fill=TEXT_GOLD, font=title_font)
    
    # Pot display
    if pot > 0:
        pot_font = get_font(38, bold=True)  # Increased from 32
        pot_text = f"Pot: {pot}"
        pot_bbox = draw.textbbox((0, 0), pot_text, font=pot_font)
        pot_width = pot_bbox[2] - pot_bbox[0]
        pot_height = pot_bbox[3] - pot_bbox[1]
        
        # Background for pot
        padding = 20
        box_width = pot_width + 2 * padding
        pot_x = (table_width - box_width) // 2
        pot_y = 75
        draw.rounded_rectangle(
            [(pot_x, pot_y), (pot_x + box_width, pot_y + pot_height + 20)],
            radius=12,
            fill=POT_BG,
            outline=TEXT_GOLD,
            width=3
        )
        text_x = pot_x + (box_width - pot_width) // 2
        draw.text((text_x, pot_y + 10), pot_text, fill=TEXT_WHITE, font=pot_font)
    
    # Dealer section (only in COOP mode)
    if not is_pvp and dealer_cards:
        dealer_y = 140
        name_font = get_font(32, bold=True)  # Increased from 28
        dealer_name_text = "Dealer"
        dealer_name_bbox = draw.textbbox((0, 0), dealer_name_text, font=name_font)
        dealer_name_width = dealer_name_bbox[2] - dealer_name_bbox[0]
        draw.text(((table_width - dealer_name_width) // 2, dealer_y), dealer_name_text, fill=TEXT_WHITE, font=name_font)
        
        # Dealer value
        value_font = get_font(28, bold=True)  # Increased from 24
        if show_dealer:
            dealer_value_text = f"Value: {dealer_value}"
            if dealer_value == 21 and len(dealer_cards) == 2:
                dealer_value_text = "BLACKJACK! 🎰"
            elif dealer_value > 21:
                dealer_value_text = f"BUST! {dealer_value}"
        else:
            dealer_value_text = "Value: ?"
        
        dealer_val_bbox = draw.textbbox((0, 0), dealer_value_text, font=value_font)
        dealer_val_width = dealer_val_bbox[2] - dealer_val_bbox[0]
        draw.text(((table_width - dealer_val_width) // 2, dealer_y + 35), dealer_value_text, fill=TEXT_GOLD, font=value_font)
        
        # Dealer cards
        dealer_cards_y = dealer_y + 75
        card_w = 100  # Increased from 90
        card_h = 140  # Increased from 126
        spacing = 12
        
        num_dealer_cards = len(dealer_cards)
        total_dealer_width = num_dealer_cards * (card_w + spacing) - spacing
        dealer_start_x = (table_width - total_dealer_width) // 2
        
        for i, card in enumerate(dealer_cards):
            x = dealer_start_x + i * (card_w + spacing)
            if i == 0 or show_dealer:
                # Show card
                rank, suit = parse_card(card)
                if rank and suit:
                    draw_card(draw, x, dealer_cards_y, rank, suit, width=card_w, height=card_h, img_base=img, deck=deck)
            else:
                # Hide card (card back)
                draw_card_back(draw, x, dealer_cards_y, width=card_w, height=card_h, img_base=img)
        
        # VS divider
        vs_y = dealer_cards_y + card_h + 25
    else:
        # PVP mode - no dealer, start players higher
        vs_y = 130
    
    vs_font = get_font(42, bold=True)  # Increased from 36
    vs_text = "VS" if not is_pvp else "PVP"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
    vs_width = vs_bbox[2] - vs_bbox[0]
    draw.text(((table_width - vs_width) // 2, vs_y), vs_text, fill=(255, 215, 0), font=vs_font)
    
    # Players section
    if players:
        small_card_width = 84  # Reduced to fit more cards
        small_card_height = 114  # Proportionally reduced
        
        num_players = len(players)
        max_spacing = 200  # Increased from 140
        available_width = table_width - 100  # More padding for safety
        
        # Layout: 3 players per row
        rows = []
        players_per_row = 3
        for i in range(0, num_players, players_per_row):
            row_players = players[i:i+players_per_row]
            if rows:
                # Calculate previous row height
                prev_row_max_cards = rows[-1]['max_cards']
                prev_row_height = 220  # Base height (increased from 180)
                if prev_row_max_cards > 4:
                    prev_row_height += (prev_row_max_cards - 4) * 40  # Increased from 30
                row_y = rows[-1]['y'] + prev_row_height + 80  # 80px gap between rows (increased from 60)
            else:
                row_y = vs_y + 80
            
            # Calculate max cards in this row
            row_max_cards = max(len(p.get('cards', [])) for p in row_players) if row_players else 2
            rows.append({
                'players': row_players,
                'y': row_y,
                'max_cards': row_max_cards
            })
        
        for row in rows:
            row_players = row['players']
            player_y = row['y']
            num_in_row = len(row_players)
            
            # Calculate max box width in this row
            max_box_width = 200  # Increased from 165
            max_card_count = 2  # Track max cards for height adjustment
            for player in row_players:
                cards = player.get('cards', [])
                num_cards = len(cards)
                max_card_count = max(max_card_count, num_cards)
                if num_cards > 0:
                    cards_width = num_cards * small_card_width + (num_cards - 1) * 5
                    box_width = max(200, cards_width + 30)  # More padding
                    max_box_width = max(max_box_width, box_width)
            
            # Increase box height if more than 4 cards
            box_height = 220  # Increased from 180
            if max_card_count > 4:
                # Add 40px for each card beyond 4 (increased from 30)
                box_height += (max_card_count - 4) * 40
            
            # Calculate spacing based on max box width
            min_gap = 30  # Increased from 10
            spacing = max_box_width + min_gap
            
            # Check if fits, if not reduce spacing
            if num_in_row * spacing > available_width:
                spacing = available_width // num_in_row
            
            total_width = num_in_row * spacing
            start_x = (table_width - total_width) // 2 + spacing // 2 - 90  # Shifted left
            
            for i, player in enumerate(row_players):
                # Get global player index for card hiding logic
                global_player_index = players.index(player)
                x = start_x + i * spacing
                
                # Player cards count for dynamic sizing
                cards = player.get('cards', [])
                num_cards = len(cards)
                
                # Calculate dynamic box width based on number of cards
                # Base width for name/text: 90px (increased), Each card: 60px, spacing between cards: 5px
                if num_cards > 0:
                    cards_width = num_cards * small_card_width + (num_cards - 1) * 5
                    # Add padding
                    box_width = max(200, cards_width + 30)
                else:
                    box_width = 200
                
                box_left = x - 12
                box_right = x - 12 + box_width
                
                # Player background color based on status
                status = player.get('status', 'waiting')
                result = player.get('result')
                
                if status == 'playing' or status == 'stand':
                    player_bg_color = (70, 120, 90)  # Active green
                elif status == 'bust':
                    player_bg_color = (120, 40, 40)  # Red for bust
                elif result == 'win' or result == 'blackjack':
                    player_bg_color = (40, 120, 40)  # Bright green for win
                elif result == 'lose':
                    player_bg_color = (80, 40, 40)  # Dark red for lose
                elif result == 'push':
                    player_bg_color = (80, 80, 40)  # Yellow-ish for push
                else:
                    player_bg_color = (40, 80, 60)  # Default
                
                # Player box (dynamic width and height)
                # Enhanced outline for current player
                is_current = current_player_index is not None and global_player_index == current_player_index and not show_dealer
                
                # Draw double outline for current player (like poker.py)
                if is_current:
                    # Outer gold outline
                    draw.rounded_rectangle(
                        [(box_left - 2, player_y - 12), (box_right + 2, player_y + box_height + 2)],
                        radius=10,
                        outline=TEXT_GOLD,
                        width=4
                    )
                
                draw.rounded_rectangle(
                    [(box_left, player_y - 10), (box_right, player_y + box_height)],
                    radius=8,
                    fill=player_bg_color,
                    outline=TEXT_GOLD if is_current else CARD_BORDER,
                    width=2
                )
                
                # Player name (centered in box)
                name_font_small = get_font(28, bold=True)  # Increased for better visibility
                name = player['user'].display_name[:12]
                name_bbox = draw.textbbox((0, 0), name, font=name_font_small)
                name_width = name_bbox[2] - name_bbox[0]
                name_x = box_left + (box_width - name_width) // 2
                draw.text((name_x, player_y), name, fill=TEXT_WHITE, font=name_font_small)
                
                # Player value and bet (centered)
                value_font_small = get_font(26, bold=True)  # Larger gold text for better visibility
                # In PVP, calculate visible cards value (1st + 3rd+ cards only)
                if is_pvp and current_player_index is not None and current_player_index != global_player_index and not show_dealer:
                    # Calculate visible value: 1st card + cards from index 2 onwards
                    visible_cards = [cards[0]] if cards else []
                    if len(cards) > 2:
                        visible_cards.extend(cards[2:])  # Add 3rd, 4th, etc.
                    visible_value = calculate_hand_value(visible_cards) if visible_cards else 0
                    value_text = f"V:?+{visible_value} B:{player.get('bet', 0)}"
                else:
                    value_text = f"V:{player.get('value', 0)} B:{player.get('bet', 0)}"
                value_bbox = draw.textbbox((0, 0), value_text, font=value_font_small)
                value_width = value_bbox[2] - value_bbox[0]
                value_x = box_left + (box_width - value_width) // 2
                draw.text((value_x, player_y + 32), value_text, fill=TEXT_GOLD, font=value_font_small)  # Increased from +20
                
                # Player cards (centered in box)
                if cards:
                    cards_width = num_cards * small_card_width + (num_cards - 1) * 5  # Increased spacing
                    cards_start_x = box_left + (box_width - cards_width) // 2
                    
                    # PVP card hiding pattern: Show 1st card + 3rd+ cards, hide ONLY 2nd card
                    # This creates pattern: [shown][hidden][shown][shown]...
                    should_hide_second = (is_pvp and not show_dealer and 
                                         current_player_index is not None and 
                                         global_player_index != current_player_index)
                    
                    for j, card in enumerate(cards):
                        card_x = cards_start_x + j * (small_card_width + 5)  # Increased spacing
                        card_y = player_y + 60  # Increased from 48
                        
                        # Hide ONLY 2nd card (index 1) in PVP for other players
                        if should_hide_second and j == 1:
                            draw_card_back(draw, card_x, card_y, width=small_card_width, height=small_card_height, img_base=img)
                        else:
                            rank, suit = parse_card(card)
                            if rank and suit:
                                draw_card(draw, card_x, card_y, rank, suit, 
                                        width=small_card_width, height=small_card_height, img_base=img, deck=deck)
                
                # Status text (centered)
                if status == 'bust':
                    status_font = get_font(24, bold=True)  # Increased from 18
                    status_bbox = draw.textbbox((0, 0), "BUST", font=status_font)
                    status_width = status_bbox[2] - status_bbox[0]
                    status_x = box_left + (box_width - status_width) // 2
                    # Position at bottom of box
                    draw.text((status_x, player_y + box_height - 25), "BUST", fill=(255, 100, 100), font=status_font)
                elif status == 'blackjack':
                    status_font = get_font(22, bold=True)  # Increased from 18
                    bj_bbox = draw.textbbox((0, 0), "BJ!", font=status_font)
                    bj_width = bj_bbox[2] - bj_bbox[0]
                    bj_x = box_left + (box_width - bj_width) // 2
                    draw.text((bj_x, player_y + box_height - 25), "BJ!", fill=(255, 215, 0), font=status_font)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='blackjack_table.png')


def create_blackjack_image(player_cards, dealer_cards, player_value, dealer_value, 
                           player_name, bet, result=None, show_dealer=False, player_deck='classic', dealer_deck='classic'):
    """Create blackjack game image with separate decks for player and dealer"""
    width = 900
    height = 750
    
    img = Image.new('RGB', (width, height), FELT_GREEN)
    draw = ImageDraw.Draw(img)
    
    # Border
    draw.rectangle([(0, 0), (width-1, height-1)], outline=FELT_DARK, width=4)
    
    # Title
    title_font = get_font(38, bold=True)
    title = "Blackjack"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) // 2, 20), title, fill=TEXT_GOLD, font=title_font)
    
    # Bet display
    bet_font = get_font(28, bold=True)
    bet_text = f"Bet: {bet}"
    bet_bbox = draw.textbbox((0, 0), bet_text, font=bet_font)
    bet_width = bet_bbox[2] - bet_bbox[0]
    draw.text(((width - bet_width) // 2, 75), bet_text, fill=TEXT_WHITE, font=bet_font)
    
    # Card dimensions
    card_w = 100
    card_h = 140
    spacing = 15
    
    # Dealer section
    dealer_y = 130
    name_font = get_font(26, bold=True)
    dealer_name_bbox = draw.textbbox((0, 0), "Dealer", font=name_font)
    dealer_name_width = dealer_name_bbox[2] - dealer_name_bbox[0]
    draw.text(((width - dealer_name_width) // 2, dealer_y), "Dealer", fill=TEXT_WHITE, font=name_font)
    
    value_font = get_font(24, bold=True)
    if show_dealer:
        dealer_text = f"Value: {dealer_value}"
        if dealer_value == 21 and len(dealer_cards) == 2:
            dealer_text = "BLACKJACK! 🎰"
    else:
        dealer_text = "Value: ?"
    dealer_val_bbox = draw.textbbox((0, 0), dealer_text, font=value_font)
    dealer_val_width = dealer_val_bbox[2] - dealer_val_bbox[0]
    draw.text(((width - dealer_val_width) // 2, dealer_y + 35), dealer_text, fill=TEXT_GOLD, font=value_font)
    
    # Dealer cards
    dealer_cards_y = dealer_y + 80
    total_dealer_width = len(dealer_cards) * (card_w + spacing) - spacing
    dealer_start_x = (width - total_dealer_width) // 2
    
    for i, card in enumerate(dealer_cards):
        x = dealer_start_x + i * (card_w + spacing)
        if i == 0 or show_dealer:
            rank, suit = parse_card(card)
            if rank and suit:
                draw_card(draw, x, dealer_cards_y, rank, suit, width=card_w, height=card_h, img_base=img, deck=dealer_deck)
        else:
            draw_card_back(draw, x, dealer_cards_y, width=card_w, height=card_h, img_base=img)
    
    # Result text (between dealer and player)
    if result:
        result_y = dealer_cards_y + card_h + 15
        result_font = get_font(36, bold=True)
        if result == "win":
            result_text = "YOU WIN! 🎉"
            result_color = (100, 255, 100)
        elif result == "lose":
            result_text = "DEALER WINS 💔"
            result_color = (255, 100, 100)
        elif result == "push":
            result_text = "PUSH - Bet Returned"
            result_color = (255, 255, 100)
        elif result == "blackjack":
            result_text = "BLACKJACK! 2.5x WIN! 🎰"
            result_color = (255, 215, 0)
        else:
            result_text = result
            result_color = TEXT_WHITE
        
        result_bbox = draw.textbbox((0, 0), result_text, font=result_font)
        result_width = result_bbox[2] - result_bbox[0]
        draw.text(((width - result_width) // 2, result_y), result_text, fill=result_color, font=result_font)
    
    # VS divider
    vs_y = dealer_cards_y + card_h + (70 if result else 30)
    vs_font = get_font(36, bold=True)
    vs_text = "VS"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
    vs_width = vs_bbox[2] - vs_bbox[0]
    draw.text(((width - vs_width) // 2, vs_y), vs_text, fill=(255, 215, 0), font=vs_font)
    
    # Player section
    player_y = vs_y + 50
    player_name_bbox = draw.textbbox((0, 0), player_name, font=name_font)
    player_name_width = player_name_bbox[2] - player_name_bbox[0]
    draw.text(((width - player_name_width) // 2, player_y), player_name, fill=TEXT_WHITE, font=name_font)
    
    player_text = f"Value: {player_value}"
    if player_value == 21 and len(player_cards) == 2:
        player_text = "BLACKJACK! 🎰"
    elif player_value > 21:
        player_text = f"BUST! {player_value}"
    
    color = TEXT_GOLD if player_value <= 21 else (255, 100, 100)
    player_val_bbox = draw.textbbox((0, 0), player_text, font=value_font)
    player_val_width = player_val_bbox[2] - player_val_bbox[0]
    draw.text(((width - player_val_width) // 2, player_y + 35), player_text, fill=color, font=value_font)
    
    # Player cards
    player_cards_y = player_y + 80
    total_player_width = len(player_cards) * (card_w + spacing) - spacing
    player_start_x = (width - total_player_width) // 2
    
    for i, card in enumerate(player_cards):
        x = player_start_x + i * (card_w + spacing)
        rank, suit = parse_card(card)
        if rank and suit:
            draw_card(draw, x, player_cards_y, rank, suit, width=card_w, height=card_h, img_base=img, deck=player_deck)
    
    # Save to buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return discord.File(fp=buffer, filename='blackjack.png')


class BlackjackLobbyView(discord.ui.View):
    """Blackjack lobby view - same structure as poker"""
    
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
            if isinstance(child, discord.ui.Button) and child.custom_id == "blackjack_lobby_start":
                # Need at least 1 real player (can add bots)
                child.disabled = len(real_players) < 1
    
    @discord.ui.button(label="🤖➕", style=discord.ButtonStyle.secondary, custom_id="blackjack_lobby_bot_add", row=0)
    async def bot_add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        if len(self.lobby['players']) >= self.lobby['settings']['max_players']:
            await interaction.response.send_message("❌ Lobby is full!", ephemeral=True)
            return
        
        # Add bot - fetch name from owner_ids
        bot_num = sum(1 for p in self.lobby['players'] if p.get('is_bot')) + 1
        
        # Get bot instance from interaction
        bot_instance = interaction.client
        owner_ids = getattr(bot_instance.get_cog('BlackjackCog'), 'owner_ids', [])
        
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
            'user': type('obj', (object,), {'id': f'bot_{bot_num}', 'display_name': bot_name, 'mention': f'🤖 {bot_name}'}),
            'is_bot': True
        })
        self.lobby['last_activity'] = time.time()
        
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="🤖➖", style=discord.ButtonStyle.secondary, custom_id="blackjack_lobby_bot_remove", row=0)
    async def bot_remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        # Find last bot
        bot_players = [p for p in self.lobby['players'] if p.get('is_bot')]
        if not bot_players:
            await interaction.response.send_message("❌ No bots!", ephemeral=True)
            return
        
        # Remove last bot
        last_bot = bot_players[-1]
        self.lobby['players'].remove(last_bot)
        self.lobby['last_activity'] = time.time()
        
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, custom_id="blackjack_lobby_join", row=1)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        
        # Check if full
        if len(self.lobby['players']) >= self.lobby['settings']['max_players']:
            await interaction.response.send_message("❌ Lobby is full!", ephemeral=True)
            return
        
        # Check if already in
        if any(p['user'].id == interaction.user.id for p in self.lobby['players'] if not p.get('is_bot')):
            await interaction.response.send_message("❌ You're already in the lobby!", ephemeral=True)
            return
        
        # Check balance
        bet_amount = self.lobby['settings']['bet_amount']
        balance = self.economy_cog.get_balance(interaction.user.id)
        if balance < bet_amount:
            await interaction.response.send_message(f"❌ You need at least **{bet_amount}** 💠", ephemeral=True)
            return
        
        # Add player
        self.lobby['players'].append({
            'user': interaction.user,
            'is_bot': False
        })
        self.lobby['last_activity'] = time.time()
        
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, custom_id="blackjack_lobby_leave", row=1)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Find player
        player = None
        for i, p in enumerate(self.lobby['players']):
            if not p.get('is_bot') and p['user'].id == interaction.user.id:
                player = p
                self.lobby['players'].pop(i)
                break
        
        if not player:
            await interaction.response.send_message("❌ You are not in the lobby!", ephemeral=True)
            return
        
        await interaction.response.defer()
        self.update_buttons()
        await interaction.message.edit(embed=self.create_lobby_embed(), view=self)
    
    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, custom_id="blackjack_lobby_settings", row=2)
    async def settings_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host!", ephemeral=True)
            return
        
        # Create ephemeral view with settings
        settings_view = create_blackjack_settings_view(self.lobby_id, self.lobby['settings'])
        
        embed = discord.Embed(
            title="⚙️ Blackjack Settings",
            description="Click a button to change value\n\n**COOP**: All players vs dealer\n**PVP**: Players compete (highest score wins)",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, view=settings_view, ephemeral=True)
    
    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, custom_id="blackjack_lobby_start", row=2)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.lobby['hostId']:
            await interaction.response.send_message("❌ Only host can start!", ephemeral=True)
            return
        
        # Count only real players (not bots)
        real_players = [p for p in self.lobby['players'] if not p.get('is_bot')]
        if len(real_players) < 1:
            await interaction.response.send_message("❌ Need at least 1 real player!", ephemeral=True)
            return
        
        await interaction.response.send_message("🎲 Starting game...", ephemeral=True)
        self.lobby['started'] = True
        self.stop()
    
    def create_lobby_embed(self):
        """Create lobby embed"""
        settings = self.lobby['settings']
        
        # Player list
        player_list = []
        for p in self.lobby['players']:
            if p.get('is_bot'):
                player_list.append(f"🤖 {p['user'].display_name}")
            else:
                player_list.append(p['user'].mention)
        
        players_text = "\n".join(player_list) if player_list else "*No players*"
        
        embed = discord.Embed(
            title="♠️ Blackjack Lobby ♠️",
            description=f"Host: <@{self.lobby['hostId']}>\nPlayers: {len(self.lobby['players'])}/{settings['max_players']}\n\nWaiting for players...",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="👥 Players", value=players_text, inline=False)
        mode_text = "🤝 COOP (all vs dealer)" if settings.get('game_mode', 'coop') == 'coop' else "⚔️ PVP (competitive)"
        embed.add_field(
            name="⚙️ Settings",
            value=f"🎮 Mode: {mode_text}\n💰 Bet amount: **{settings['bet_amount']}** 💠\n👤 Max players: **{settings['max_players']}**",
            inline=False
        )
        
        return embed


class BlackjackGame:
    """Blackjack game instance"""
    
    def __init__(self, channel, lobby_data, economy_cog):
        self.channel = channel
        self.host_id = lobby_data['hostId']
        self.settings = lobby_data['settings']
        self.economy_cog = economy_cog
        self.players = []
        self.message = None
        
        # Convert lobby players to game players
        for player_data in lobby_data['players']:
            self.players.append({
                'user': player_data['user'],
                'cards': [],
                'value': 0,
                'bet': self.settings['bet_amount'],
                'status': 'waiting',
                'result': None,
                'is_bot': player_data.get('is_bot', False)
            })
    
    def get_user_deck(self, user_id):
        """Get user's equipped card deck (classic/dark/platinum)"""
        return self.economy_cog.get_user_card_deck(user_id)
    
    async def start_game(self):
        """Start the blackjack game"""
        if len(self.players) < 1:
            return
        
        # Check minimum players (at least 2 for multiplayer)
        real_players = [p for p in self.players if not p.get('is_bot')]
        if len(real_players) < 1 or (len(self.players) < 2 and len(real_players) < 2):
            await self.channel.send("❌ Need at least 2 players (or 1 player + bot) to start!")
            return
        
        is_pvp = self.settings.get('game_mode', 'coop') == 'pvp'
        
        # Deduct bets
        for player in self.players:
            if not player.get('is_bot'):
                self.economy_cog.remove_coins(player['user'].id, player['bet'])
        
        # Create deck
        deck = create_deck()
        random.shuffle(deck)
        
        # Deal initial cards
        dealer_cards = [] if is_pvp else [deck.pop(), deck.pop()]
        dealer_value = 0 if is_pvp else calculate_hand_value(dealer_cards)
        
        for player in self.players:
            player['cards'] = [deck.pop(), deck.pop()]
            player['value'] = calculate_hand_value(player['cards'])
            player['status'] = 'playing'
            
            # Check for blackjack
            if player['value'] == 21:
                player['status'] = 'blackjack'
        
        # COOP mode: check dealer blackjack
        if not is_pvp:
            dealer_blackjack = dealer_value == 21
            if dealer_blackjack:
                for player in self.players:
                    if player['status'] == 'blackjack':
                        player['result'] = 'push'
                        if not player.get('is_bot'):
                            self.economy_cog.add_coins(player['user'].id, player['bet'], "blackjack_push")
                    else:
                        player['result'] = 'lose'
                
                await self.show_final_results(dealer_cards, dealer_value, True, is_pvp)
                return
        
        # Play each player's turn
        for i, player in enumerate(self.players):
            if player['status'] == 'blackjack':
                continue
            player['is_current'] = True
            await self.play_player_turn(player, deck, dealer_cards, dealer_value, is_pvp, i)
            player['is_current'] = False
        
        if not is_pvp:
            # COOP: Dealer's turn
            while dealer_value < 17:
                dealer_cards.append(deck.pop())
                dealer_value = calculate_hand_value(dealer_cards)
            
            dealer_blackjack = dealer_value == 21 and len(dealer_cards) == 2
            
            # Determine winners vs dealer
            for player in self.players:
                if player['status'] == 'bust':
                    player['result'] = 'lose'
                elif player['status'] == 'blackjack':
                    player['result'] = 'blackjack'
                    winnings = int(player['bet'] * 2.5)
                    if not player.get('is_bot'):
                        self.economy_cog.add_coins(player['user'].id, winnings, "blackjack_win")
                elif dealer_value > 21:
                    player['result'] = 'win'
                    winnings = player['bet'] * 2
                    if not player.get('is_bot'):
                        self.economy_cog.add_coins(player['user'].id, winnings, "blackjack_win")
                elif dealer_value > player['value']:
                    player['result'] = 'lose'
                elif dealer_value < player['value']:
                    player['result'] = 'win'
                    winnings = player['bet'] * 2
                    if not player.get('is_bot'):
                        self.economy_cog.add_coins(player['user'].id, winnings, "blackjack_win")
                else:
                    player['result'] = 'push'
                    if not player.get('is_bot'):
                        self.economy_cog.add_coins(player['user'].id, player['bet'], "blackjack_push")
        else:
            # PVP: Find winner(s)
            # Filter valid players (not bust)
            valid_players = [p for p in self.players if p['status'] != 'bust' and p['value'] <= 21]
            
            if not valid_players:
                # All busted - everyone loses
                for player in self.players:
                    player['result'] = 'lose'
            else:
                # Find highest value
                max_value = max(p['value'] for p in valid_players)
                winners = [p for p in valid_players if p['value'] == max_value]
                
                if len(winners) == 1:
                    # Single winner takes all
                    winner = winners[0]
                    total_pot = sum(p['bet'] for p in self.players)
                    winner['result'] = 'win'
                    if not winner.get('is_bot'):
                        self.economy_cog.add_coins(winner['user'].id, total_pot, "blackjack_pvp_win")
                    
                    # Others lose
                    for player in self.players:
                        if player != winner and player['result'] is None:
                            player['result'] = 'lose'
                else:
                    # Tie - split pot
                    pot_share = sum(p['bet'] for p in self.players) // len(winners)
                    for player in self.players:
                        if player in winners:
                            player['result'] = 'push'
                            if not player.get('is_bot'):
                                self.economy_cog.add_coins(player['user'].id, pot_share, "blackjack_pvp_push")
                        elif player['result'] is None:
                            player['result'] = 'lose'
            
            dealer_blackjack = False
        
        await self.show_final_results(dealer_cards, dealer_value, dealer_blackjack if not is_pvp else False, is_pvp)
    
    async def play_player_turn(self, player, deck, dealer_cards, dealer_value, is_pvp, current_index):
        """Play one player's turn"""
        # Get card deck for current player
        card_deck = 'classic'
        if not player.get('is_bot'):
            card_deck = self.get_user_deck(player['user'].id)
        
        while player['value'] < 21 and player['status'] == 'playing':
            # Create visual table
            table_image = await asyncio.to_thread(
                create_blackjack_table_image,
                dealer_cards,
                dealer_value,
                self.players,
                show_dealer=False,
                pot=sum(p['bet'] for p in self.players),
                is_pvp=is_pvp,
                current_player_index=current_index,
                deck=card_deck
            )
            
            if is_pvp:
                desc = f"**Your value:** {player['value']}"
            else:
                desc = f"**Your value:** {player['value']}\n**Dealer shows:** {dealer_cards[0]}"
            
            embed = discord.Embed(
                title=f"♠️ {player['user'].display_name}'s Turn ♠️",
                description=desc,
                color=discord.Color.blue()
            )
            embed.set_image(url="attachment://blackjack_table.png")
            
            # Bot AI logic
            if player.get('is_bot'):
                await asyncio.sleep(2)  # Simulate thinking
                
                # Simple bot strategy
                if player['value'] < 17:
                    action = 'hit'
                elif player['value'] == 17 and len(player['cards']) == 2:
                    # Soft 17 - hit if has ace
                    has_ace = any(parse_card(c)[0].lower() == 'a' for c in player['cards'])
                    action = 'hit' if has_ace else 'stand'
                else:
                    action = 'stand'
                
                # Show bot decision
                embed.add_field(name="🤖 Bot Decision", value=f"**{action.upper()}**", inline=False)
                
                if not self.message:
                    self.message = await self.channel.send(embed=embed, file=table_image)
                else:
                    await self.message.edit(embed=embed, attachments=[table_image])
                
                await asyncio.sleep(1.5)  # Show decision
                
                if action == 'stand':
                    player['status'] = 'stand'
                    break
                else:  # hit
                    player['cards'].append(deck.pop())
                    player['value'] = calculate_hand_value(player['cards'])
                    if player['value'] >= 21:
                        player['status'] = 'bust' if player['value'] > 21 else 'stand'
                        break
                    # Continue loop for bot's next decision
            else:
                # Human player
                view = BlackjackActionView(
                    player['user'].id, 
                    can_double=len(player['cards']) == 2,
                    player_cards=player['cards'],
                    player_value=player['value'],
                    player_name=player['user'].display_name,
                    is_pvp=is_pvp,
                    economy_cog=self.economy_cog
                )
                
                # Send main table to channel
                if not self.message:
                    self.message = await self.channel.send(embed=embed, file=table_image, view=view)
                else:
                    await self.message.edit(embed=embed, attachments=[table_image], view=view)
                
                await view.wait()
                
                if not view.action or view.action == "stand":
                    player['status'] = 'stand'
                    break
                
                if view.action == "leave":
                    player['status'] = 'bust'
                    player['result'] = 'lose'
                    await self.channel.send(f"🚪 **{player['user'].display_name}** left the game!")
                    break
                
                if view.action == "double":
                    self.economy_cog.remove_coins(player['user'].id, player['bet'])
                    player['bet'] *= 2
                    player['cards'].append(deck.pop())
                    player['value'] = calculate_hand_value(player['cards'])
                    player['status'] = 'bust' if player['value'] > 21 else 'stand'
                    break  # Auto-end turn after double
                
                if view.action == "hit":
                    player['cards'].append(deck.pop())
                    player['value'] = calculate_hand_value(player['cards'])
                    
                    # Update view with new cards for Hand button
                    view.player_cards = player['cards']
                    view.player_value = player['value']
                    
                    if player['value'] >= 21:
                        player['status'] = 'bust' if player['value'] > 21 else 'stand'
                        break  # Auto-end turn if 21 or bust
    
    async def show_final_results(self, dealer_cards, dealer_value, dealer_blackjack, is_pvp):
        """Show final results"""
        # Get card deck from first human player (host by default)
        card_deck = 'classic'
        for player in self.players:
            if not player.get('is_bot'):
                card_deck = self.get_user_deck(player['user'].id)
                break
        
        table_image = await asyncio.to_thread(
            create_blackjack_table_image,
            dealer_cards,
            dealer_value,
            self.players,
            show_dealer=True,
            pot=sum(p['bet'] for p in self.players),
            is_pvp=is_pvp,
            current_player_index=-1,  # Show all cards
            deck=card_deck
        )
        
        summary_lines = []
        
        if not is_pvp:
            summary_lines.append(f"**Dealer:** {dealer_value} {'BLACKJACK! 🎰' if dealer_blackjack else 'BUST!' if dealer_value > 21 else ''}")
            summary_lines.append("")
        
        for player in self.players:
            if player['result'] == 'blackjack':
                result_text = f"🎰 BLACKJACK! +{int(player['bet'] * 1.5)} 💠"
            elif player['result'] == 'win':
                if is_pvp:
                    total_pot = sum(p['bet'] for p in self.players)
                    result_text = f"🏆 WINNER! +{total_pot - player['bet']} 💠"
                else:
                    result_text = f"🎉 WIN! +{player['bet']} 💠"
            elif player['result'] == 'lose':
                result_text = f"💔 LOSE -{player['bet']} 💠"
            elif player['result'] == 'push':
                if is_pvp:
                    result_text = "🤝 TIE - Pot split"
                else:
                    result_text = "🤝 PUSH - Bet returned"
            else:
                result_text = "⏳ Playing..."
            
            summary_lines.append(f"**{player['user'].display_name}:** {player['value']} - {result_text}")
        
        title = "⚔️ PVP Results ⚔️" if is_pvp else "♠️ Blackjack Results ♠️"
        embed = discord.Embed(
            title=title,
            description="\n".join(summary_lines),
            color=discord.Color.gold()
        )
        embed.set_image(url="attachment://blackjack_table.png")
        
        # Add Play Again/Leave buttons (only if there are human players)
        player_ids = [p['user'].id for p in self.players if not p.get('is_bot')]
        if player_ids:  # Only add view if there are human players
            play_again_view = BlackjackPlayAgainView(
                player_ids=player_ids,
                players=self.players,
                settings=self.settings,
                channel=self.channel,
                economy_cog=self.economy_cog
            )
            if self.message:
                await self.message.edit(embed=embed, attachments=[table_image], view=play_again_view)
            else:
                await self.channel.send(embed=embed, file=table_image, view=play_again_view)
        else:  # No human players, just show results
            if self.message:
                await self.message.edit(embed=embed, attachments=[table_image], view=None)
            else:
                await self.channel.send(embed=embed, file=table_image)


class BlackjackPlayAgainView(discord.ui.View):
    """View for Play Again/Leave buttons after game ends"""
    
    def __init__(self, player_ids, players=None, settings=None, channel=None, economy_cog=None, lobby_id=None):
        super().__init__(timeout=60)
        self.player_ids = set(player_ids)
        self.players = players or []
        self.settings = settings or {'bet_amount': 100, 'max_players': 6, 'game_mode': 'coop'}
        self.channel = channel
        self.economy_cog = economy_cog
        self.lobby_id = lobby_id
        self.responses = {}
    
    @discord.ui.button(label="🎲 Play Again", style=discord.ButtonStyle.success, row=0)
    async def play_again_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.player_ids:
            await interaction.response.send_message("❌ You weren't in this game!", ephemeral=True)
            return
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Get blackjack cog
        blackjack_cog = interaction.client.get_cog('BlackjackCog')
        
        if not blackjack_cog or not self.economy_cog or not self.channel:
            await interaction.followup.send("❌ Error starting new game. Use /blackjack to play again!", ephemeral=True)
            return
        
        # Create lobby structure with same players and settings
        lobby_data = {
            'game': 'blackjack',
            'hostId': str(self.players[0]['user'].id),
            'players': [{
                'user': p['user'],
                'is_bot': p.get('is_bot', False)
            } for p in self.players],
            'settings': self.settings.copy(),
            'messageId': None,
            'last_activity': time.time(),
            'started': True  # Already "started" since we skip lobby
        }
        
        # Send confirmation message
        await interaction.followup.send("🎲 Starting new game with same players...", ephemeral=True)
        
        # Start game directly
        await blackjack_cog.start_blackjack_game(lobby_data, self.channel, self.economy_cog)
    
    @discord.ui.button(label="🚪 Leave", style=discord.ButtonStyle.secondary, row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.player_ids:
            await interaction.response.send_message("❌ You weren't in this game!", ephemeral=True)
            return
        
        self.responses[interaction.user.id] = 'leave'
        await interaction.response.send_message("👋 Thanks for playing!", ephemeral=True)


class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Load owner_ids from config.json
        self.owner_ids = []
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.owner_ids = config.get('owner_ids', [])
        except Exception as e:
            print(f"❌ Error loading owner_ids from config.json: {e}")
    
    def get_economy_cog(self):
        """Get economy cog"""
        return self.bot.get_cog('Economy')
    
    def get_user_deck(self, user_id: int) -> str:
        """Get user's preferred card deck from economy system"""
        economy = self.get_economy_cog()
        if economy:
            return economy.get_user_card_deck(user_id)
        return 'classic'  # Default if economy not available
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle settings button interactions"""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get('custom_id', '')
        
        # Check if it's a blackjack settings button
        if custom_id.startswith('blackjack_setting_'):
            await self.handle_blackjack_settings(interaction, custom_id)
    
    async def handle_blackjack_settings(self, interaction: discord.Interaction, cid: str):
        """Handles blackjack settings buttons"""
        # Extract lobby_id from custom_id (e.g. "blackjack_setting_mode_blackjack_123_456" -> "blackjack_123_456")
        parts = cid.split('_')
        if len(parts) >= 5:
            lobby_id = f"{parts[-3]}_{parts[-2]}_{parts[-1]}"
        else:
            await interaction.response.send_message("❌ Invalid ID!", ephemeral=True)
            return
        
        if not hasattr(self.bot, 'active_blackjack_lobbies'):
            self.bot.active_blackjack_lobbies = {}
        
        lobby = self.bot.active_blackjack_lobbies.get(lobby_id)
        
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
        
        # Game mode (COOP/PVP toggle)
        if 'blackjack_setting_mode_' in cid:
            # Toggle between coop/pvp
            current_mode = lobby['settings']['game_mode']
            new_mode = 'pvp' if current_mode == 'coop' else 'coop'
            lobby['settings']['game_mode'] = new_mode
            
            # Edit lobby
            view = lobby.get('view')
            if view:
                await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
            
            # Edit ephemeral settings
            settings_view = create_blackjack_settings_view(lobby_id, lobby['settings'])
            await interaction.response.edit_message(view=settings_view)
        
        # Bet amount
        elif 'blackjack_setting_bet_' in cid:
            modal = discord.ui.Modal(title="Bet Amount")
            bet_input = discord.ui.TextInput(
                label="Bet amount (coins)",
                placeholder="100",
                default=str(lobby['settings']['bet_amount']),
                max_length=10,
                required=True
            )
            modal.add_item(bet_input)
            
            async def on_submit_bet(modal_interaction: discord.Interaction):
                try:
                    value = int(bet_input.value)
                    if value < 50:
                        await modal_interaction.response.send_message("❌ Min: 50", ephemeral=True)
                        return
                    lobby['settings']['bet_amount'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_blackjack_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Bet: **{value}** 💠", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_bet
            await interaction.response.send_modal(modal)
            return
        
        # Max players
        elif 'blackjack_setting_max_' in cid:
            modal = discord.ui.Modal(title="Max Players")
            max_input = discord.ui.TextInput(
                label="Max players (1-10)",
                placeholder="6",
                default=str(lobby['settings']['max_players']),
                max_length=2,
                required=True
            )
            modal.add_item(max_input)
            
            async def on_submit_max(modal_interaction: discord.Interaction):
                try:
                    value = int(max_input.value)
                    if not 1 <= value <= 10:
                        await modal_interaction.response.send_message("❌ Range: 1-10", ephemeral=True)
                        return
                    lobby['settings']['max_players'] = value
                    view = lobby.get('view')
                    if view:
                        await lobby_msg.edit(embed=view.create_lobby_embed(), view=view)
                    
                    # Edit ephemeral settings
                    settings_view = create_blackjack_settings_view(lobby_id, lobby['settings'])
                    await interaction.edit_original_response(view=settings_view)
                    await modal_interaction.response.send_message(f"✅ Max: **{value}**", ephemeral=True)
                except ValueError:
                    await modal_interaction.response.send_message("❌ Please enter a number!", ephemeral=True)
            
            modal.on_submit = on_submit_max
            await interaction.response.send_modal(modal)
            return
    
    @app_commands.command(name="blackjack", description="Play Blackjack")
    @app_commands.describe(mode="Game mode: fast (vs dealer) or long (multiplayer lobby)")
    @app_commands.choices(mode=[
        app_commands.Choice(name="🎯 Fast Blackjack", value="fast"),
        app_commands.Choice(name="🎲 Long Blackjack Lobby", value="long")
    ])
    async def blackjack(self, interaction: discord.Interaction, mode: str = "fast"):
        """Play blackjack"""
        if mode == "fast":
            await self.play_fast_blackjack(interaction)
        else:
            await self.play_long_blackjack(interaction)
    
    async def play_fast_blackjack(self, interaction: discord.Interaction, preset_bet: int = None):
        """Fast blackjack vs dealer - dealer always uses classic deck, player uses custom deck"""
        economy_cog = self.get_economy_cog()
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
            return
        
        # Get user's card deck (player only)
        card_deck = self.get_user_deck(interaction.user.id)
        
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
            bet_view = BetSelectView(interaction.user.id, balance, "blackjack")
            embed = discord.Embed(
                title="Blackjack - Select Bet",
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
        
        # Create deck and deal
        deck = create_deck()
        random.shuffle(deck)
        
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        player_value = calculate_hand_value(player_cards)
        dealer_value = calculate_hand_value(dealer_cards)
        
        # Variable to track the game message
        game_message = None
        
        # Check for blackjacks
        player_bj = player_value == 21
        dealer_bj = dealer_value == 21
        
        if player_bj or dealer_bj:
            # Instant result
            if player_bj and dealer_bj:
                result = "push"
                economy_cog.add_coins(interaction.user.id, bet_amount, "blackjack_push")
                winnings_text = "Bet returned"
            elif player_bj:
                result = "blackjack"
                winnings = int(bet_amount * 2.5)
                economy_cog.add_coins(interaction.user.id, winnings, "blackjack_win")
                winnings_text = f"+{winnings - bet_amount} 💠"
            else:
                result = "lose"
                winnings_text = f"-{bet_amount} 💠"
            
            game_image = await asyncio.to_thread(
                create_blackjack_image,
                player_cards, dealer_cards, player_value, dealer_value,
                interaction.user.display_name, bet_amount, result, True, 
                player_deck=card_deck, dealer_deck='classic'
            )
            
            embed = discord.Embed(
                title="Blackjack",
                description=winnings_text,
                color=discord.Color.gold() if result != "lose" else discord.Color.red()
            )
            embed.set_image(url=f"attachment://blackjack.png")
            
            # Play again buttons
            play_again_view = discord.ui.View(timeout=None)
            
            play_again_btn = discord.ui.Button(label="Play Again", style=discord.ButtonStyle.primary)
            same_bet_btn = discord.ui.Button(label=f"Same Bet ({bet_amount})", style=discord.ButtonStyle.success)
            disclaimer_btn = discord.ui.Button(label="⚠️", style=discord.ButtonStyle.secondary, row=1)
            
            async def play_again_callback(btn_interaction: discord.Interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("❌ Not your game!", ephemeral=True)
                    return
                await self.play_fast_blackjack(btn_interaction)
            
            async def same_bet_callback(btn_interaction: discord.Interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("❌ Not your game!", ephemeral=True)
                    return
                await self.play_fast_blackjack(btn_interaction, preset_bet=bet_amount)
            
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
            play_again_view.add_item(play_again_btn)
            play_again_view.add_item(same_bet_btn)
            play_again_view.add_item(disclaimer_btn)
            
            # Send to channel (non-ephemeral)
            await interaction.followup.send(embed=embed, file=game_image, view=play_again_view)
            return
        
        # Player's turn
        while player_value < 21:
            game_image = await asyncio.to_thread(
                create_blackjack_image,
                player_cards, dealer_cards, player_value, dealer_value,
                interaction.user.display_name, bet_amount, None, False, 
                player_deck=card_deck, dealer_deck='classic'
            )
            
            embed = discord.Embed(
                title="Your Turn",
                description=f"Your value: **{player_value}**\nChoose your action:",
                color=discord.Color.blue()
            )
            embed.set_image(url=f"attachment://blackjack.png")
            
            can_double = len(player_cards) == 2 and balance >= bet_amount
            action_view = BlackjackActionView(interaction.user.id, can_double, economy_cog=economy_cog)
            
            # Send first message or edit existing
            if game_message is None:
                game_message = await interaction.followup.send(embed=embed, file=game_image, view=action_view, wait=True)
            else:
                await game_message.edit(embed=embed, attachments=[game_image], view=action_view)
            
            await action_view.wait()
            
            if not action_view.action or action_view.action == "stand":
                break
            
            if action_view.action == "double":
                economy_cog.remove_coins(interaction.user.id, bet_amount)
                bet_amount *= 2
                player_cards.append(deck.pop())
                player_value = calculate_hand_value(player_cards)
                break
            
            if action_view.action == "hit":
                player_cards.append(deck.pop())
                player_value = calculate_hand_value(player_cards)
        
        # Dealer's turn
        show_dealer = True
        if player_value > 21:
            result = "lose"
            winnings_text = f"-{bet_amount} 💠"
        else:
            while dealer_value < 17:
                dealer_cards.append(deck.pop())
                dealer_value = calculate_hand_value(dealer_cards)
            
            if dealer_value > 21:
                result = "win"
                winnings = bet_amount * 2
                economy_cog.add_coins(interaction.user.id, winnings, "blackjack_win")
                winnings_text = f"+{winnings - bet_amount} 💠"
            elif dealer_value > player_value:
                result = "lose"
                winnings_text = f"-{bet_amount} 💠"
            elif dealer_value < player_value:
                result = "win"
                winnings = bet_amount * 2
                economy_cog.add_coins(interaction.user.id, winnings, "blackjack_win")
                winnings_text = f"+{winnings - bet_amount} 💠"
            else:
                result = "push"
                economy_cog.add_coins(interaction.user.id, bet_amount, "blackjack_push")
                winnings_text = "Bet returned"
        
        # Final result
        game_image = await asyncio.to_thread(
            create_blackjack_image,
            player_cards, dealer_cards, player_value, dealer_value,
            interaction.user.display_name, bet_amount, result, show_dealer, 
            player_deck=card_deck, dealer_deck='classic'
        )
        
        embed = discord.Embed(
            title="Blackjack Result",
            description=winnings_text,
            color=discord.Color.gold() if result == "win" else (discord.Color.red() if result == "lose" else discord.Color.blue())
        )
        embed.set_image(url=f"attachment://blackjack.png")
        
        # Play again buttons
        play_again_view = discord.ui.View(timeout=None)
        
        play_again_btn = discord.ui.Button(label="Play Again", style=discord.ButtonStyle.primary)
        same_bet_btn = discord.ui.Button(label=f"Same Bet ({bet_amount})", style=discord.ButtonStyle.success)
        disclaimer_btn = discord.ui.Button(label="⚠️", style=discord.ButtonStyle.secondary, row=1)
        
        async def play_again_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id != interaction.user.id:
                await btn_interaction.response.send_message("❌ Not your game!", ephemeral=True)
                return
            await self.play_fast_blackjack(btn_interaction)
        
        async def same_bet_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id != interaction.user.id:
                await btn_interaction.response.send_message("❌ Not your game!", ephemeral=True)
                return
            await self.play_fast_blackjack(btn_interaction, preset_bet=bet_amount)
        
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
        play_again_view.add_item(play_again_btn)
        play_again_view.add_item(same_bet_btn)
        play_again_view.add_item(disclaimer_btn)
        
        # Edit the game message with final result
        if game_message:
            await game_message.edit(embed=embed, attachments=[game_image], view=play_again_view)
        else:
            await interaction.followup.send(embed=embed, file=game_image, view=play_again_view)


    async def play_long_blackjack(self, interaction: discord.Interaction):
        """Long blackjack with multiplayer lobby - same structure as poker"""
        # Defer immediately to prevent timeout
        await interaction.response.defer()
        
        uid = str(interaction.user.id)
        economy_cog = self.get_economy_cog()
        if not economy_cog:
            await interaction.followup.send("❌ Economy system not available!", ephemeral=True)
            return
        
        # Create lobby structure like poker
        lobby_id = f"blackjack_{interaction.channel.id}_{int(time.time())}"
        lobby = {
            'game': 'blackjack',
            'hostId': uid,
            'players': [
                {
                    'user': interaction.user,
                    'is_bot': False
                }
            ],
            'settings': {
                'bet_amount': 100,  # Default bet
                'max_players': 6,
                'game_mode': 'coop'  # coop = all vs dealer, pvp = competitive
            },
            'messageId': None,
            'last_activity': time.time(),
            'started': False
        }
        
        # Store lobby
        if not hasattr(self.bot, 'active_blackjack_lobbies'):
            self.bot.active_blackjack_lobbies = {}
        
        self.bot.active_blackjack_lobbies[lobby_id] = lobby
        
        # Create view and embed
        view = BlackjackLobbyView(lobby_id, lobby, economy_cog)
        lobby['view'] = view
        embed = view.create_lobby_embed()
        
        await interaction.followup.send(embed=embed, view=view)
        msg = await interaction.original_response()
        lobby['messageId'] = msg.id
        
        # Wait for start
        await view.wait()
        
        if lobby.get('started'):
            await self.start_blackjack_game(lobby, interaction.channel, economy_cog)
        else:
            # Cancelled
            if lobby_id in self.bot.active_blackjack_lobbies:
                del self.bot.active_blackjack_lobbies[lobby_id]
    
    async def start_blackjack_game(self, lobby, channel, economy_cog):
        """Start blackjack game"""
        lobby_id = f"blackjack_{channel.id}_{int(lobby['last_activity'])}"
        
        if lobby_id in self.bot.active_blackjack_lobbies:
            del self.bot.active_blackjack_lobbies[lobby_id]
        
        # Create game instance
        game = BlackjackGame(channel, lobby, economy_cog)
        active_blackjack_games[channel.id] = game
        
        # Start game
        await game.start_game()


async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))