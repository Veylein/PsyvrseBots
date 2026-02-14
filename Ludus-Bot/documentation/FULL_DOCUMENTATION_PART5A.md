# FULL DOCUMENTATION - PART 5A: CARD GAMES

**Project:** Ludus Bot  
**Coverage:** Card Games (Go Fish, Blackjack Fast/Long, Poker Fast/Long, War, Solitaire, Spades, Crazy Eights, Bullshit)  
**Total Lines:** 5,829 lines of code  
**Status:** ✅ COMPLETE (Updated with Fast Modes & Custom Decks)  
**Date:** May 2025

---

## Table of Contents

1. [Card Games Overview](#1-card-games-overview)
2. [Custom Card Deck System](#2-custom-card-deck-system)
3. [Go Fish System](#3-go-fish-system)
4. [Blackjack System](#4-blackjack-system)
   - [Blackjack Fast](#blackjack-fast-1v1-dealer)
   - [Blackjack Long](#blackjack-long-multiplayer-lobby)
   - [Blackjack Simple](#blackjack-simple-dm-based)
5. [Poker System](#5-poker-system)
   - [Poker Fast](#poker-fast-5-card-vs-dealer)
   - [Poker Long](#poker-long-texas-holdem)
6. [War Card Game](#6-war-card-game)
7. [Enhanced Card Games](#7-enhanced-card-games)
   - [Solitaire](#solitaire)
   - [Spades](#spades)
   - [Crazy Eights](#crazy-eights)
   - [Bullshit](#bullshit)
8. [Responsible Gambling](#8-responsible-gambling)
9. [Technical Implementation](#9-technical-implementation)
10. [Commands Reference](#10-commands-reference)
11. [Summary](#11-summary)

---

## 1. CARD GAMES OVERVIEW

**Files:**  
- `cogs/cardgames.py` (1,098 lines) - Go Fish, War, enhanced game menus
- `cogs/blackjack.py` (1,944 lines) - Blackjack Fast/Long/Simple with custom decks
- `cogs/poker.py` (2,787 lines) - Poker Fast/Long with Texas Hold'em
- `cogs/cards_enhanced.py` (283 lines) - Solitaire, Spades, Crazy Eights, Bullshit

The Card Games system provides both **classic single-player** and **multiplayer card games** with:
- **Custom visual card decks** (Classic, Dark, Platinum)
- **Fast vs Long modes** for blackjack/poker
- **Real-time rendering** with Pillow image generation
- **Lobby systems** for multiplayer coordination
- **Responsible gambling** disclaimers and educational content
- **Persistent UI** with timeout=None for always-visible buttons

### Core Features

**Standard 52-Card Deck:**
- 4 suits: ♠️ ♥️ ♦️ ♣️
- 13 ranks: A, 2-10, J, Q, K
- Joker support (optional)
- Automatic shuffling

**Visual Card Rendering:**
- **3 deck styles:** `classic`, `dark`, `platinum`
- **PNG assets:** Located in `assets/cards/{deck}/`
- **Format:** `{rank}{suit}.png` (e.g., `AS.png`, `10H.png`)
- **Player customization:** Players choose deck in Fast modes
- **Dealer default:** Always uses `classic` deck

**Game Modes:**

| Mode | Players | Description | Ephemeral | Deck Customization |
|------|---------|-------------|-----------|-------------------|
| **Fast** | 1v1 | Quick games vs dealer/bot | No | Player custom, dealer classic |
| **Long** | 2+ | Multiplayer lobby, turn-based | Varies | All players share lobby deck |
| **Simple** | 1 | DM-based classic mode | Yes | No customization |

**Game Types:**
1. **Blackjack Fast** - 1v1 vs dealer, instant gameplay, custom player deck
2. **Blackjack Long** - Multiplayer lobby (COOP/PVP), shared deck
3. **Poker Fast** - 5-card vs dealer, instant gameplay
4. **Poker Long** - Texas Hold'em multiplayer
5. **Go Fish** - Multiplayer (vs bot or player), collect sets of 4
6. **War** - Instant comparison game, highest card wins
7. **Solitaire** - Single-player classic patience game
8. **Spades** - 4-player team trick-taking game
9. **Crazy Eights** - Match suits/ranks, first to empty wins
10. **Bullshit** - Bluffing game, call out lies

**Privacy System:**
- Player hands sent via DM (Go Fish, Blackjack Simple)
- Game state visible in channel (Fast modes, Long lobbies)
- Ephemeral messages for bet selection
- Turn-based notifications

**State Management:**
- Active game tracking per player
- Prevention of multiple simultaneous games
- Automatic cleanup on game end
- Bot opponent AI for single-player

**Economy Integration:**
- Betting system for Blackjack/Poker Fast modes
- **Payouts:**
  - Blackjack Win: **2x bet** (bet 100, win 200, net +100)
  - Blackjack (natural 21): **2.5x bet** (bet 100, win 250, net +150)
  - Poker Win: **2x bet**
  - Push/Tie: **1x bet returned** (no profit/loss)
- **Same Bet button:** Instant replay with previous bet amount
- Economy file: `data/economy.json`

---

## 2. CUSTOM CARD DECK SYSTEM

**Implementation:** `cogs/blackjack.py` Lines 687-893 (`create_blackjack_image`)  
**Assets:** `assets/cards/{classic|dark|platinum}/`

The custom deck system allows players to personalize card visuals while maintaining game integrity.

### Deck Styles

**Available Decks:**
1. **Classic** (`classic`) - Traditional red/black design
2. **Dark** (`dark`) - Sleek dark theme with gold accents
3. **Platinum** (`platinum`) - Premium silver/white aesthetic

**Asset Structure:**
```
assets/cards/
├── classic/
│   ├── AS.png   # Ace of Spades
│   ├── 2H.png   # 2 of Hearts
│   ├── 10D.png  # 10 of Diamonds
│   └── ...      # All 52 cards
├── dark/
│   └── ...
└── platinum/
    └── ...
```

**Naming Convention:**
- **Ranks:** `A`, `2`-`10`, `J`, `Q`, `K`
- **Suits:** `S` (Spades), `H` (Hearts), `D` (Diamonds), `C` (Clubs)
- **Format:** `{RANK}{SUIT}.png` (e.g., `KS.png`, `10H.png`)

### Deck Selection

**Player Customization:**
- Available in **Blackjack Fast** and **Poker Fast** modes
- Selected via dropdown during bet selection
- Stored per-game (not persistent across games)

**Dealer/Bot Behavior:**
- Always uses **classic deck** for consistency
- Cannot be customized by players
- Maintains house visual identity

**Code Implementation:**
```python
# Player selects deck in BetSelectView (blackjack.py line 22-152)
class BetSelectView(discord.ui.View):
    def __init__(self, user_id, mode="fast"):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.mode = mode
        self.bet_amount = None
        self.selected_deck = "classic"  # Default
    
    @discord.ui.select(
        placeholder="Select Card Deck",
        options=[
            discord.SelectOption(label="Classic", value="classic", emoji="🃏"),
            discord.SelectOption(label="Dark", value="dark", emoji="🌑"),
            discord.SelectOption(label="Platinum", value="platinum", emoji="💎")
        ],
        row=1
    )
    async def deck_select(self, interaction, select):
        self.selected_deck = select.values[0]
        await interaction.response.defer()
```

### Image Rendering

**Function Signature:**
```python
async def create_blackjack_image(
    player_hand: List[str],
    dealer_hand: List[str],
    show_dealer: bool,
    player_deck: str = "classic",  # Player's chosen deck
    dealer_deck: str = "classic",  # Dealer always classic
    bet: int = 0
) -> io.BytesIO:
```

**Rendering Process:**
```python
# Draw player cards with custom deck
for i, card in enumerate(player_hand):
    card_path = f"assets/cards/{player_deck}/{card}.png"  # Player deck
    card_img = Image.open(card_path).resize((card_width, card_height))
    image.paste(card_img, (player_x_start + i * x_spacing, player_y))

# Draw dealer cards (always classic)
for i, card in enumerate(dealer_hand):
    if i == 0 or show_dealer:
        card_path = f"assets/cards/{dealer_deck}/{card}.png"  # Always "classic"
        card_img = Image.open(card_path).resize((card_width, card_height))
    else:
        card_img = card_back  # Hidden card
    image.paste(card_img, (dealer_x_start + i * x_spacing, dealer_y))
```

**Error Handling:**
```python
try:
    card_img = Image.open(card_path).resize((card_width, card_height))
except FileNotFoundError:
    # Fallback to classic deck if custom deck missing
    fallback_path = f"assets/cards/classic/{card}.png"
    card_img = Image.open(fallback_path).resize((card_width, card_height))
```

### Usage Examples

**Blackjack Fast with Platinum Deck:**
```
User: /blackjack fast
Bot: [Bet Selection Menu]
User: Selects "Platinum" deck, enters 500 bet
Bot: [Renders table with player cards in platinum, dealer in classic]
```

**Separate Rendering:**
- **Player hand:** Platinum deck (AS.png, KH.png from assets/cards/platinum/)
- **Dealer hand:** Classic deck (10S.png, 7D.png from assets/cards/classic/)
- **Visual contrast:** Easy to distinguish player vs dealer cards

---

## 3. GO FISH SYSTEM

**File:** `cogs/cardgames.py` Lines 1-430  
**Players:** 1-2 (vs bot or player)  
**Goal:** Collect the most "books" (sets of 4 matching ranks)

### Game Mechanics

**Setup:**
- Each player dealt 7 cards
- Remaining cards form draw deck
- Players take turns asking opponent for specific ranks

**Turn Flow:**
```python
# Player asks opponent for rank (e.g., "A")
if opponent has rank:
    # Transfer all matching cards to asker
    # Asker goes again
    # Check for completed books (4 of a kind)
else:
    # "Go Fish" - draw from deck
    # Turn passes to opponent
```

**Completing Books:**
```python
async def _check_books_gofish(self, state: Dict[str, Any], pid):
    hand = state['hands'].get(pid, [])
    ranks = {}
    for c in hand:
        r = self.rank_of(c)  # Extract rank (e.g., "A" from "A♠")
        ranks.setdefault(r, []).append(c)
    
    completed = []
    for r, cards in ranks.items():
        if len(cards) >= 4:
            # Remove 4 cards from hand
            for card in cards[:4]:
                hand.remove(card)
            # Add book to player's collection
            state['books'][pid].append(r)
            completed.append(r)
    
    # Notify player of completed books
    if completed and pid != 'BOT':
        await user.send(embed=discord.Embed(
            title="🎉 Go Fish — Book Completed!",
            description=f"Completed books: **{', '.join(completed)}**",
            color=discord.Color.gold()
        ))
    return completed
```

**Win Conditions:**
1. Both players have empty hands
2. Deck is empty and at least one player has empty hand
3. Winner has most books

**Bot AI (Lines 374-430):**
```python
async def _bot_turn_gofish(self, game_id, state, ctx, interaction):
    """Simple bot AI for Go Fish"""
    player_id = state['players'][0]
    
    while state['turn'] == 'BOT':
        await asyncio.sleep(1)  # Simulate thinking
        
        # Bot draws if no cards
        if not state['hands']['BOT']:
            if state['deck']:
                drawn = state['deck'].pop()
                state['hands']['BOT'].append(drawn)
                continue
            else:
                break  # Game over
        
        # Bot randomly asks for rank it has
        bot_rank = self.rank_of(random.choice(state['hands']['BOT']))
        player_hand = state['hands'][player_id]
        
        # Check if player has the rank
        player_cards = [c for c in player_hand if self.rank_of(c) == bot_rank]
        
        if player_cards:
            # Bot takes cards and goes again
            for c in player_cards:
                player_hand.remove(c)
                state['hands']['BOT'].append(c)
            await self._check_books_gofish(state, 'BOT')
            messages.append(f"🤖 Bot asked for **{bot_rank}** and took **{len(player_cards)} card(s)**! Bot goes again...")
        else:
            # Bot goes fishing
            if state['deck']:
                bdraw = state['deck'].pop()
                state['hands']['BOT'].append(bdraw)
            messages.append(f"🤖 Bot asked for **{bot_rank}** and went fishing.")
            
            # Check for win
            win_result = self._check_gofish_win(state)
            if win_result:
                # End game
                break
            
            # Pass turn to player
            state['turn'] = player_id
            messages.append("**Your turn!**")
            break
```

### Commands

**Start Game:**
```
L!gofish start [@opponent]  # Prefix command
/gofish start [@opponent]   # Slash command with dropdown
```
- Opponent optional (defaults to bot)
- Sends initial hands via DM

**Ask for Cards:**
```
L!gofish ask <rank>  # e.g., L!gofish ask A
/gofish-ask <rank>   # Slash command
```
- Valid ranks: A, 2-10, J, Q, K
- Only works on your turn

**View Hand:**
```
L!gofish hand
/gofish hand  # Via action dropdown
```
- Shows your cards, books, opponent's book count
- Sent via DM for privacy

**Stop Game:**
```
L!gofish stop
/gofish stop
```
- Ends game immediately
- Cleans up game state

### Example Game Flow

```
[Game Start]
Player: 7 cards (A♠, A♥, 2♣, 5♦, 5♠, 8♥, K♦)
Bot: 7 cards (hidden)
Deck: 38 cards

Player's Turn:
L!gofish ask A
→ Bot has A♦, A♣ (gives both to player)
→ Player now has 4 Aces (A♠, A♥, A♦, A♣)
→ Book completed! Player: 1 book, Bot: 0 books
→ Player's turn again

L!gofish ask 5
→ Bot doesn't have 5
→ Player draws 3♠ from deck
→ Bot's turn

[Bot's Turn]
🤖 Bot asks for K and takes 1 card!
→ Bot goes again
🤖 Bot asks for 3 and went fishing.
→ Player's turn

[Continue until win condition met]
🎉 Player wins with 5 books vs 3!
```

---

## 4. BLACKJACK SYSTEM

**File:** `cogs/blackjack.py` (1,944 lines)  
**Players:** 1-8 (varies by mode)  
**Goal:** Get closer to 21 than dealer without busting (going over 21)

The Blackjack system offers **three distinct gameplay modes**:
1. **Fast** - Instant 1v1 vs dealer with custom deck visuals
2. **Long** - Multiplayer lobby with COOP/PVP modes
3. **Simple** - Classic DM-based blackjack (legacy)

---

### Blackjack Fast (1v1 Dealer)

**Lines:** 1588-1840  
**Players:** 1 vs dealer (bot)  
**Style:** Non-ephemeral, instant gameplay, visual table rendering

**Features:**
- ✅ Custom player deck (classic/dark/platinum)
- ✅ Dealer always uses classic deck
- ✅ Real-time image rendering with Pillow
- ✅ Economy integration (betting system)
- ✅ Same Bet button for instant replay
- ✅ Gambling disclaimer (always visible)
- ✅ Persistent buttons (timeout=None)

**Flow:**

**1. Bet Selection (Ephemeral)**
```python
# User runs: /blackjack fast
# Bot responds with ephemeral BetSelectView

class BetSelectView(discord.ui.View):
    """Ephemeral bet selection with deck customization"""
    
    @discord.ui.select(
        placeholder="Select Card Deck",
        options=[
            discord.SelectOption(label="Classic", value="classic", emoji="🃏"),
            discord.SelectOption(label="Dark", value="dark", emoji="🌑"),
            discord.SelectOption(label="Platinum", value="platinum", emoji="💎")
        ]
    )
    async def deck_select(self, interaction, select):
        self.selected_deck = select.values[0]
    
    @discord.ui.button(label="Place Bet", style=discord.ButtonStyle.green)
    async def place_bet(self, interaction, button):
        # Validate bet amount
        # Start game with selected deck
        await play_fast_blackjack(interaction, self.bet_amount, self.selected_deck)
```

**2. Game Start (Public Channel)**
```python
async def play_fast_blackjack(interaction, bet_amount, player_deck="classic", preset_bet=None):
    """Main fast blackjack game logic"""
    
    # Create deck and deal cards
    deck = create_deck()
    random.shuffle(deck)
    
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    # Check for instant blackjack
    player_initial = calculate_hand(player_hand)
    dealer_initial = calculate_hand(dealer_hand)
    
    if player_initial == 21 and dealer_initial != 21:
        # Instant win, pay 2.5x
        winnings = int(bet_amount * 2.5)
        await economy.add_balance(user_id, winnings)
        
        # Create final image
        img = await create_blackjack_image(
            player_hand, dealer_hand, 
            show_dealer=True,
            player_deck=player_deck,  # Custom player deck
            dealer_deck="classic",    # Dealer always classic
            bet=bet_amount
        )
        
        embed = discord.Embed(
            title="Blackjack",
            description=f"**Blackjack!** You win **{winnings:,}** coins! (+{winnings - bet_amount:,})",
            color=discord.Color.gold()
        )
        
        # Add Same Bet button
        view = SameBetBlackjackView(user_id, bet_amount, player_deck, timeout=None)
        await interaction.followup.send(embed=embed, file=file, view=view)
        return
    
    # Normal game flow - send image with action buttons
    img = await create_blackjack_image(
        player_hand, dealer_hand,
        show_dealer=False,  # Hide dealer's second card
        player_deck=player_deck,
        dealer_deck="classic",
        bet=bet_amount
    )
    
    embed = discord.Embed(
        title="Blackjack",
        description=f"**Bet:** {bet_amount:,} coins\n**Your Total:** {player_initial}",
        color=discord.Color.blue()
    )
    
    # Action view with persistent buttons
    view = BlackjackActionView(
        user_id, player_hand, dealer_hand, deck, bet_amount, player_deck, timeout=None
    )
    await interaction.followup.send(embed=embed, file=file, view=view)
```

**3. Player Actions (Mid-Game)**
```python
class BlackjackActionView(discord.ui.View):
    """Persistent action buttons during gameplay"""
    
    def __init__(self, user_id, player_hand, dealer_hand, deck, bet, player_deck, **kwargs):
        super().__init__(**kwargs)  # timeout=None from caller
        self.user_id = user_id
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.deck = deck
        self.bet = bet
        self.player_deck = player_deck
        
        # Add disclaimer button (row 2)
        self.add_item(DisclaimerButton(row=2))
    
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def hit_button(self, interaction, button):
        """Draw another card"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        
        # Draw card
        new_card = self.deck.pop()
        self.player_hand.append(new_card)
        new_total = calculate_hand(self.player_hand)
        
        if new_total > 21:
            # Bust - player loses
            await self.end_game(interaction, "bust")
        else:
            # Update image with new card
            img = await create_blackjack_image(
                self.player_hand, self.dealer_hand,
                show_dealer=False,
                player_deck=self.player_deck,
                dealer_deck="classic",
                bet=self.bet
            )
            
            embed = discord.Embed(
                title="Blackjack",
                description=f"**Bet:** {self.bet:,} coins\n**Your Total:** {new_total}",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.success, emoji="✋", row=0)
    async def stand_button(self, interaction, button):
        """End turn, dealer plays"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        
        # Dealer draws until >= 17
        while calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        
        # Determine winner
        await self.end_game(interaction, "stand")
    
    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.secondary, emoji="💰", row=0)
    async def double_button(self, interaction, button):
        """Double bet, draw one card, auto-stand"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        
        # Check if user has enough balance
        current_balance = await economy.get_balance(self.user_id)
        if current_balance < self.bet:
            await interaction.response.send_message("Insufficient balance to double down!", ephemeral=True)
            return
        
        # Double bet
        self.bet *= 2
        
        # Draw one card and auto-stand
        new_card = self.deck.pop()
        self.player_hand.append(new_card)
        
        if calculate_hand(self.player_hand) > 21:
            await self.end_game(interaction, "bust")
        else:
            # Dealer plays
            while calculate_hand(self.dealer_hand) < 17:
                self.dealer_hand.append(self.deck.pop())
            await self.end_game(interaction, "stand")
    
    async def end_game(self, interaction, reason):
        """Handle game end with payouts"""
        player_total = calculate_hand(self.player_hand)
        dealer_total = calculate_hand(self.dealer_hand)
        
        # Calculate result
        if reason == "bust":
            result_text = "Bust! Dealer wins."
            color = discord.Color.red()
            winnings = 0  # Lose bet
        elif dealer_total > 21:
            result_text = "Dealer busts! You win!"
            color = discord.Color.green()
            winnings = self.bet * 2  # Win 2x bet
        elif player_total > dealer_total:
            result_text = "You win!"
            color = discord.Color.green()
            winnings = self.bet * 2
        elif player_total == dealer_total:
            result_text = "Push (tie)"
            color = discord.Color.gold()
            winnings = self.bet  # Return bet
        else:
            result_text = "Dealer wins"
            color = discord.Color.red()
            winnings = 0
        
        # Update economy
        net_profit = winnings - self.bet
        if winnings > 0:
            await economy.add_balance(self.user_id, winnings)
        
        # Create final image (show dealer cards)
        img = await create_blackjack_image(
            self.player_hand, self.dealer_hand,
            show_dealer=True,
            player_deck=self.player_deck,
            dealer_deck="classic",
            bet=self.bet
        )
        
        embed = discord.Embed(
            title="Blackjack",
            description=f"**{result_text}**\n\n"
                       f"**Your Total:** {player_total}\n"
                       f"**Dealer Total:** {dealer_total}\n"
                       f"**Net Profit:** {net_profit:+,} coins",
            color=color
        )
        
        # Add Same Bet + Disclaimer buttons
        view = EndGameView(self.user_id, self.bet, self.player_deck, timeout=None)
        await interaction.response.edit_message(embed=embed, attachments=[file], view=view)

class DisclaimerButton(discord.ui.Button):
    """Always-visible gambling disclaimer"""
    def __init__(self, **kwargs):
        super().__init__(
            label="⚠️ Gambling Info",
            style=discord.ButtonStyle.secondary,
            **kwargs
        )
    
    async def callback(self, interaction):
        embed = discord.Embed(
            title="⚠️ Responsible Gambling",
            description=(
                "**This is entertainment with virtual currency only.**\n\n"
                "Gambling should never be seen as a way to make money. "
                "The odds are always in favor of the house. Set limits and know when to stop.\n\n"
                "If you or someone you know has a gambling problem, help is available:\n"
                "**National Council on Problem Gambling:** 1-800-522-4700"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
```

**4. Same Bet Replay**
```python
class SameBetBlackjackView(discord.ui.View):
    """Instant replay with same bet and deck"""
    def __init__(self, user_id, bet_amount, player_deck, **kwargs):
        super().__init__(**kwargs)  # timeout=None
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.player_deck = player_deck
        self.add_item(DisclaimerButton(row=1))
    
    @discord.ui.button(label="Same Bet", style=discord.ButtonStyle.green, emoji="🔄", row=0)
    async def same_bet(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        
        # Start new game with preset bet
        await play_fast_blackjack(
            interaction, 
            preset_bet=self.bet_amount, 
            player_deck=self.player_deck
        )
```

**Payouts:**
- **Standard Win:** 2x bet (bet 100 → win 200, net +100)
- **Blackjack (21 with first 2 cards):** 2.5x bet (bet 100 → win 250, net +150)
- **Push (tie):** 1x bet returned (bet 100 → get 100 back, net ±0)
- **Loss/Bust:** 0x bet (lose full bet amount)

---

### Blackjack Long (Multiplayer Lobby)

**Lines:** 894-1587  
**Players:** 2-8 (multiplayer)  
**Modes:** COOP (all vs dealer) or PVP (players vs each other)

**Features:**
- ✅ Lobby system with join/leave buttons
- ✅ Host controls (start/kick/bot management)
- ✅ Turn-based gameplay
- ✅ Shared deck for all players
- ✅ Real-time hand updates
- ✅ Spectator mode for eliminated players

**Lobby System:**
```python
class BlackjackLobbyView(discord.ui.View):
    """Multiplayer lobby manager"""
    
    def __init__(self, host_id, mode, buy_in, **kwargs):
        super().__init__(**kwargs)  # timeout=300 (5 minutes)
        self.host_id = host_id
        self.mode = mode  # "coop" or "pvp"
        self.buy_in = buy_in
        self.players = [host_id]  # Real players only
        self.has_bot = False
        self.update_buttons()
    
    def update_buttons(self):
        """Enable/disable start button based on real player count"""
        real_player_count = len([p for p in self.players if isinstance(p, int)])
        
        # Need 2+ real players to start (bot doesn't count)
        start_button = discord.utils.get(self.children, custom_id="start_game")
        if start_button:
            start_button.disabled = (real_player_count < 2 and not self.has_bot)
    
    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.green, custom_id="join")
    async def join_button(self, interaction, button):
        if interaction.user.id in self.players:
            await interaction.response.send_message("Already in game!", ephemeral=True)
            return
        
        # Check balance for buy-in
        if not await economy.check_balance(interaction.user.id, self.buy_in):
            await interaction.response.send_message(f"Need {self.buy_in:,} coins!", ephemeral=True)
            return
        
        self.players.append(interaction.user.id)
        self.update_buttons()
        await self.refresh_lobby(interaction)
    
    @discord.ui.button(label="Add Bot", style=discord.ButtonStyle.secondary, custom_id="add_bot")
    async def add_bot(self, interaction, button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Only host can add bots!", ephemeral=True)
            return
        
        if self.has_bot:
            # Remove bot
            self.has_bot = False
            button.label = "Add Bot"
        else:
            # Add bot
            self.has_bot = True
            button.label = "Remove Bot"
        
        self.update_buttons()
        await self.refresh_lobby(interaction)
    
    @discord.ui.button(label="Start Game", style=discord.ButtonStyle.primary, custom_id="start_game")
    async def start_button(self, interaction, button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("Only host can start!", ephemeral=True)
            return
        
        # Deduct buy-ins
        for player_id in self.players:
            await economy.remove_balance(player_id, self.buy_in)
        
        # Start game
        await self.start_blackjack_long(interaction)
```

**COOP Mode:**
- All players vs dealer
- Players take turns
- Dealer plays last
- Each player wins/loses independently
- Payouts same as Fast mode (2x/2.5x)

**PVP Mode:**
- Players compete against each other
- No dealer (or dealer as neutral party)
- Highest hand wins pot
- Busted players eliminated
- Winner takes all buy-ins

---

### Blackjack Simple (DM-Based)

**File:** `cogs/cardgames.py` Lines 432-685  
**Players:** 1 vs dealer (legacy mode)  
**Style:** DM-based commands, text-only

**Features:**
- ✅ Classic blackjack rules
- ✅ Hands sent via DM
- ✅ Text-based gameplay (no images)
- ✅ Prefix commands (L!blackjack)
- ✅ Simple embed displays

**Commands:**
```
L!blackjack start  - Start game
L!blackjack hit    - Draw card
L!blackjack stand  - End turn
L!blackjack hand   - View hand
L!blackjack stop   - Forfeit game
```

**Note:** This mode is legacy and lacks modern features (no deck customization, no economy integration, no visual rendering). Use **Fast mode** for enhanced experience.

---

### Card Value Calculation

**Universal Logic (All Modes):**
```python
def calculate_hand(hand: List[str]) -> int:
    """Calculate blackjack hand value with ace optimization"""
    value = 0
    aces = 0
    
    for card in hand:
        rank = card[:-1]  # Extract rank (e.g., "A" from "AS")
        
        if rank.isdigit():
            value += int(rank)  # 2-10 = face value
        elif rank in ['J', 'Q', 'K']:
            value += 10  # Face cards = 10
        elif rank == 'A':
            aces += 1  # Count aces separately
    
    # Add aces optimally (11 if possible, else 1)
    for _ in range(aces):
        if value + 11 <= 21:
            value += 11
        else:
            value += 1
    
    return value
```

**Example Hands:**
- `['AS', 'KH']` → 21 (A=11, K=10) - **Blackjack!**
- `['AS', 'AH', '9D']` → 21 (A=11, A=1, 9=9)
- `['KS', 'QH', '5D']` → 25 (K=10, Q=10, 5=5) - **Bust!**
- `['7S', '7H', '7D']` → 21 (7+7+7)
- `['AS', '5H']` → 16 (A=11, 5=5) *soft 16*
  - If hit and draw 9: `['AS', '5H', '9D']` → 15 (A=1, 5=5, 9=9)

---

### Strategy Tips

**Basic Strategy:**
1. **Always hit on 11 or less** (impossible to bust)
2. **Always stand on 17+** (high risk of busting)
3. **Hit on 12-16 if dealer shows 7-Ace** (dealer likely has strong hand)
4. **Stand on 12-16 if dealer shows 2-6** (dealer likely to bust)
5. **Double down on 10-11** (best odds to win)
6. **Never take insurance** (mathematically unfavorable)

**Dealer Rules:**
- Dealer MUST hit until reaching 17+
- Dealer MUST stand on 17+
- Dealer has no choice (robotic behavior)
- This gives players strategic advantage if played correctly

**Expected House Edge:**
- Basic strategy: ~0.5% house edge
- Poor strategy: 2-5% house edge
- Card counting: Player advantage (not applicable in bot shuffled decks)

---

## 5. POKER SYSTEM

**File:** `cogs/poker.py` (2,787 lines)  
**Players:** 2-10 (varies by mode)  
**Goal:** Build the best 5-card poker hand

The Poker system offers **two distinct gameplay modes**:
1. **Fast** - Instant 5-card poker vs dealer
2. **Long** - Texas Hold'em multiplayer tournaments

---

### Poker Fast (5-Card vs Dealer)

**Lines:** 1304-1570  
**Players:** 1 vs dealer (bot)  
**Style:** Simple 5-card draw, instant results

**Features:**
- ✅ Custom player deck (classic/dark/platinum)
- ✅ Dealer uses classic deck
- ✅ Instant hand evaluation
- ✅ Economy integration (betting)
- ✅ Same Bet button for replay
- ✅ Gambling disclaimer
- ✅ Persistent buttons (timeout=None)

**Game Flow:**

**1. Bet Selection**
```python
# User runs: /poker fast
# Bot displays ephemeral bet selection menu

class PokerBetSelectView(discord.ui.View):
    """Ephemeral bet + deck selection"""
    
    @discord.ui.select(
        placeholder="Select Card Deck",
        options=[
            discord.SelectOption(label="Classic", value="classic", emoji="🃏"),
            discord.SelectOption(label="Dark", value="dark", emoji="🌑"),
            discord.SelectOption(label="Platinum", value="platinum", emoji="💎")
        ]
    )
    async def deck_select(self, interaction, select):
        self.selected_deck = select.values[0]
    
    @discord.ui.button(label="Place Bet", style=discord.ButtonStyle.green)
    async def place_bet(self, interaction, button):
        await play_fast_poker(interaction, self.bet_amount, self.selected_deck)
```

**2. Deal & Evaluation**
```python
async def play_fast_poker(interaction, bet_amount, player_deck="classic", preset_bet=None):
    """Fast poker main logic"""
    
    # Create deck and deal hands
    deck = create_deck()
    random.shuffle(deck)
    
    player_hand = [deck.pop() for _ in range(5)]
    dealer_hand = [deck.pop() for _ in range(5)]
    
    # Evaluate hands
    player_rank, player_desc = evaluate_poker_hand(player_hand)
    dealer_rank, dealer_desc = evaluate_poker_hand(dealer_hand)
    
    # Determine winner
    if player_rank > dealer_rank:
        result = "You win!"
        color = discord.Color.green()
        winnings = bet_amount * 2  # 2x payout
    elif player_rank < dealer_rank:
        result = "Dealer wins"
        color = discord.Color.red()
        winnings = 0
    else:
        # Tie - compare high cards
        if max(player_hand) > max(dealer_hand):
            result = "You win (high card tiebreaker)!"
            color = discord.Color.green()
            winnings = bet_amount * 2
        else:
            result = "Dealer wins (high card tiebreaker)"
            color = discord.Color.red()
            winnings = 0
    
    # Update economy
    net_profit = winnings - bet_amount
    if winnings > 0:
        await economy.add_balance(user_id, winnings)
    
    # Create result embed
    embed = discord.Embed(
        title="Poker",
        description=f"**{result}**\n\n"
                   f"**Your Hand:** {player_desc}\n"
                   f"**Dealer Hand:** {dealer_desc}\n\n"
                   f"**Bet:** {bet_amount:,} coins\n"
                   f"**Net Profit:** {net_profit:+,} coins",
        color=color
    )
    
    # Add player cards as embed field (with deck styling)
    player_cards_text = " ".join([format_card(c, player_deck) for c in player_hand])
    dealer_cards_text = " ".join([format_card(c, "classic") for c in dealer_hand])
    
    embed.add_field(name="Your Cards", value=player_cards_text, inline=False)
    embed.add_field(name="Dealer Cards", value=dealer_cards_text, inline=False)
    
    # Add Same Bet + Disclaimer buttons
    view = SameBetPokerView(user_id, bet_amount, player_deck, timeout=None)
    await interaction.followup.send(embed=embed, view=view)
```

**3. Hand Evaluation**
```python
def evaluate_poker_hand(hand: List[str]) -> Tuple[int, str]:
    """
    Evaluate 5-card poker hand
    Returns (rank, description)
    Rank: 0-9 (higher is better)
    """
    ranks = [card[:-1] for card in hand]  # Extract ranks
    suits = [card[-1] for card in hand]   # Extract suits
    
    # Convert face cards to numbers for comparison
    rank_values = {
        'A': 14, 'K': 13, 'Q': 12, 'J': 11,
        '10': 10, '9': 9, '8': 8, '7': 7,
        '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    }
    values = sorted([rank_values[r] for r in ranks], reverse=True)
    
    # Check for flush (all same suit)
    is_flush = len(set(suits)) == 1
    
    # Check for straight (consecutive values)
    is_straight = (values[0] - values[4] == 4) and len(set(values)) == 5
    # Special case: A-2-3-4-5 (wheel)
    if values == [14, 5, 4, 3, 2]:
        is_straight = True
        values = [5, 4, 3, 2, 1]  # Ace low
    
    # Count rank frequencies
    rank_counts = {}
    for v in values:
        rank_counts[v] = rank_counts.get(v, 0) + 1
    counts = sorted(rank_counts.values(), reverse=True)
    
    # Evaluate hand rank
    if is_straight and is_flush and values[0] == 14:
        return (9, "Royal Flush")
    elif is_straight and is_flush:
        return (8, f"Straight Flush ({rank_name(values[0])} high)")
    elif counts == [4, 1]:
        return (7, "Four of a Kind")
    elif counts == [3, 2]:
        return (6, "Full House")
    elif is_flush:
        return (5, "Flush")
    elif is_straight:
        return (4, f"Straight ({rank_name(values[0])} high)")
    elif counts == [3, 1, 1]:
        return (3, "Three of a Kind")
    elif counts == [2, 2, 1]:
        return (2, "Two Pair")
    elif counts == [2, 1, 1, 1]:
        return (1, "One Pair")
    else:
        return (0, f"High Card ({rank_name(values[0])})")
```

**Poker Hand Rankings (High to Low):**
1. **Royal Flush** - A♠ K♠ Q♠ J♠ 10♠
2. **Straight Flush** - 8♥ 7♥ 6♥ 5♥ 4♥
3. **Four of a Kind** - Q♠ Q♥ Q♦ Q♣ 3♠
4. **Full House** - J♠ J♥ J♦ 5♣ 5♠
5. **Flush** - K♦ 10♦ 7♦ 5♦ 2♦
6. **Straight** - 9♠ 8♥ 7♦ 6♣ 5♠
7. **Three of a Kind** - 8♠ 8♥ 8♦ K♣ 4♠
8. **Two Pair** - A♠ A♥ 7♦ 7♣ 2♠
9. **One Pair** - 10♠ 10♥ Q♦ 8♣ 3♠
10. **High Card** - A♠ J♥ 9♦ 6♣ 3♠

**Payouts:**
- **Win:** 2x bet (bet 100 → win 200, net +100)
- **Loss:** 0x bet (lose full bet)
- **No pushes** in 5-card poker (always a winner)

**Same Bet Replay:**
```python
class SameBetPokerView(discord.ui.View):
    """Instant replay with same bet and deck"""
    def __init__(self, user_id, bet_amount, player_deck, **kwargs):
        super().__init__(**kwargs)  # timeout=None
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.player_deck = player_deck
        self.add_item(DisclaimerButton(row=1))
    
    @discord.ui.button(label="Same Bet", style=discord.ButtonStyle.green, emoji="🔄", row=0)
    async def same_bet(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        
        await play_fast_poker(
            interaction,
            preset_bet=self.bet_amount,
            player_deck=self.player_deck
        )
```

---

### Poker Long (Texas Hold'em)

**Lines:** 200-1300  
**Players:** 2-10 (multiplayer)  
**Style:** Full Texas Hold'em with community cards

**Features:**
- ✅ Texas Hold'em rules (2 hole cards + 5 community)
- ✅ Betting rounds (Pre-flop, Flop, Turn, River)
- ✅ Raise/Call/Fold actions
- ✅ Side pots for all-in situations
- ✅ Tournament bracket support
- ✅ Spectator mode

**Texas Hold'em Phases:**
```
1. Pre-Flop: Each player dealt 2 hole cards
   - Betting round (call/raise/fold)

2. Flop: 3 community cards revealed
   - Betting round

3. Turn: 4th community card revealed
   - Betting round

4. River: 5th community card revealed
   - Final betting round

5. Showdown: Best 5-card hand from 7 available cards wins
```

**Betting Actions:**
- **Fold:** Exit hand, lose any bets made
- **Call:** Match current bet
- **Raise:** Increase bet (other players must match)
- **Check:** Pass action without betting (if no raise)
- **All-In:** Bet all remaining chips (creates side pot)

**Hand Evaluation:**
- Players make best 5-card hand from:
  - 2 hole cards + 5 community cards = 7 total
- Can use 0, 1, or 2 hole cards
- Standard poker rankings apply

**Pot Distribution:**
- Main pot: All players eligible
- Side pots: Created when player goes all-in
- Winner(s) split pots if tied

---

## 6. WAR CARD GAME

**File:** `cogs/cardgames.py` Lines 687-733  
**Players:** 1 (vs bot or player)  
**Type:** Instant comparison, no turns

### Rules

**Simple Comparison:**
```python
# Both players draw one card
user_card = deck.pop()  # e.g., "K♠"
opp_card = deck.pop()   # e.g., "7♥"

# Card ranking
order = {
    "A": 14, "K": 13, "Q": 12, "J": 11,
    "10": 10, "9": 9, "8": 8, "7": 7,
    "6": 6, "5": 5, "4": 4, "3": 3, "2": 2
}

# Compare values
if val(user_card) > val(opp_card):
    result = "Player wins!"
elif val(user_card) < val(opp_card):
    result = "Opponent wins!"
else:
    result = "Tie (WAR)!"
```

**Complete Implementation (Lines 700-733):**
```python
async def _play_war(self, author, opponent, ctx, interaction):
    if opponent and (opponent.bot or opponent.id == author.id):
        return  # Invalid opponent
    
    # Deal one card each
    deck = self.build_deck()
    user_card = deck.pop()
    opp_card = deck.pop()
    
    # Compare
    order = {"A":14, "K":13, "Q":12, "J":11, "10":10, "9":9, "8":8, "7":7, "6":6, "5":5, "4":4, "3":3, "2":2}
    def val(card):
        return order.get(self.rank_of(card), 0)
    
    if val(user_card) > val(opp_card):
        result = f"🎉 {author.mention} wins the round!"
        color = discord.Color.green()
    elif val(user_card) < val(opp_card):
        result = f"😔 {opponent.mention if opponent else '**Bot**'} wins the round!"
        color = discord.Color.red()
    else:
        result = "⚔️ It's a tie (WAR)!"
        color = discord.Color.gold()
    
    # Display result
    embed = discord.Embed(title="⚔️ War", color=color)
    embed.add_field(name=f"{author.display_name}'s Card", value=f"**{user_card}**", inline=True)
    embed.add_field(name=f"{opponent.display_name if opponent else 'Bot'}'s Card", value=f"**{opp_card}**", inline=True)
    embed.add_field(name="Result", value=result, inline=False)
    
    await interaction.followup.send(embed=embed)
```

### Commands

**Play Round:**
```
L!war [@opponent]  # Prefix
/war [@opponent]   # Slash
```
- Opponent optional (defaults to bot)
- Instant result, no state tracking
- Can play repeatedly

### Example Games

```
Example 1: Clear Win
Player: K♠ (13)
Bot: 7♥ (7)
Result: 🎉 Player wins!

Example 2: Ace High
Player: A♦ (14)
Opponent: Q♣ (12)
Result: 🎉 Player wins!

Example 3: Tie
Player: 8♠ (8)
Bot: 8♥ (8)
Result: ⚔️ Tie (WAR)!
```

**Note:** This is simplified War (single round comparison). Traditional War involves collecting all cards and playing multiple rounds, which is not implemented in this version.

---

## 7. ENHANCED CARD GAMES

**File:** `cogs/cards_enhanced.py` (283 lines)

Enhanced card games use ephemeral messages (private, auto-deleting) and interactive Discord UI for improved gameplay experience.

### Solitaire

**Type:** Single-player patience game  
**Goal:** Move all cards to four foundation piles (one per suit), Ace to King

**Game Structure (Lines 74-143):**
```python
async def start_solitaire(self, interaction: discord.Interaction):
    deck = self.create_deck()
    random.shuffle(deck)
    
    # Deal tableau (7 piles)
    tableau = [deck[i:i+i+1] for i in range(7)]
    # Pile 1: 1 card
    # Pile 2: 2 cards
    # ...
    # Pile 7: 7 cards
    # Total: 28 cards
    
    stock = deck[28:]  # Remaining 24 cards
    
    game_state = {
        "type": "solitaire",
        "tableau": tableau,        # 7 piles of cards
        "stock": stock,            # Draw pile
        "waste": [],               # Discard pile
        "foundations": [[], [], [], []],  # 4 suit piles
        "player": interaction.user.id
    }
```

**Display Format:**
```
🃏 Solitaire
━━━━━━━━━━━━━━━━

Stock: 24 cards
Waste: 5♦

Foundations:
♠️: Empty
♥️: A♥
♦️: Empty
♣️: Empty

Tableau:
Pile 1: 7♠
Pile 2: Q♥ 3♣
Pile 3: K♦ 8♠ 2♥
Pile 4: J♣ 9♦ 5♠ A♦
Pile 5: 10♥ 7♣ 4♦ Q♠ 6♥
Pile 6: 9♠ 6♦ 3♥ K♣ 8♦ 5♣
Pile 7: J♥ 10♦ 7♠ 4♣ A♠ 9♣ 2♦
```

**Interactive Buttons (Lines 232-283):**
- **🃏 Draw Card** - Move top card from stock to waste
- **🔄 Reset Stock** - Flip waste pile back to stock
- **🆕 New Game** - Start fresh game
- **❌ Quit** - End game

**Commands:**
```
/cardsmenu → Select "🃏 Solitaire"
```
- Game shown via ephemeral message (only you see it)
- Use buttons to interact

---

### Spades

**Type:** 4-player team trick-taking game  
**Teams:** 2 vs 2 (partners sit opposite)  
**Goal:** Bid and win tricks, spades are trump suit

**Setup (Lines 182-200):**
```python
async def start_spades(self, interaction: discord.Interaction):
    embed = discord.Embed(
        title="♠️ Spades",
        description="🎮 **Team-based card game**\n\n"
                   "Spades is a 4-player trick-taking game!\n"
                   "Looking for 3 more players...\n\n"
                   "Players use `/cardsmenu` to join!",
        color=discord.Color.dark_purple()
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    await interaction.channel.send(
        f"♠️ **{interaction.user.mention} wants to play Spades!**\n"
        f"Need 3 more players! Use `/cardsmenu` and select Spades to join!"
    )
```

**Rules Summary:**
1. **Deal:** 13 cards each (full deck)
2. **Bidding:** Each player bids number of tricks they expect to win
3. **Play:** Standard trick-taking, must follow suit
4. **Trump:** Spades are always trump (beat any other suit)
5. **Scoring:** Team must meet combined bid, penalties for overbidding

**Status:** Partially implemented (recruitment system only)

**Commands:**
```
/cardsmenu → Select "♠️ Spades"
```

---

### Crazy Eights

**Type:** 2-6 player shedding game  
**Goal:** First player to empty their hand wins  
**Special Card:** 8s are wild (can be played on anything)

**Setup (Lines 165-180):**
```python
async def start_crazy_eights(self, interaction: discord.Interaction):
    embed = discord.Embed(
        title="8️⃣ Crazy Eights",
        description="🎮 **Looking for opponent...**\n\n"
                   "Waiting for another player to join!\n"
                   "Use `/cardsmenu` and select Crazy Eights to join!",
        color=discord.Color.orange()
    )
    
    await interaction.channel.send(
        f"8️⃣ **{interaction.user.mention} wants to play Crazy Eights!**\n"
        f"Type `/cardsmenu` and select Crazy Eights to join!"
    )
```

**Rules Summary:**
1. **Deal:** 5-7 cards each, one card face-up to start discard pile
2. **Play:** Match suit or rank of top discard card
3. **Draw:** If can't play, draw until you can
4. **Eights:** Play on any card, declare new suit
5. **Win:** First to empty hand

**Status:** Partially implemented (recruitment system only)

**Commands:**
```
/cardsmenu → Select "8️⃣ Crazy Eights"
```

---

### Bullshit

**Type:** 2-6 player bluffing game  
**Goal:** Empty your hand by playing cards face-down (lying allowed!)

**Setup (Lines 202-230):**
```python
async def start_bullshit(self, interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎴 Bullshit",
        description="🃏 **The Bluffing Card Game**\n\n"
                   "Lie about your cards and don't get caught!\n\n"
                   "**How to Play:**\n"
                   "• Play cards face-down claiming they're a certain rank\n"
                   "• Other players can call 'Bullshit!'\n"
                   "• If caught lying, you take all the cards\n"
                   "• If you were honest, the challenger takes them\n"
                   "• First to empty their hand wins!\n\n"
                   "Waiting for more players...",
        color=discord.Color.red()
    )
```

**Rules Summary:**
1. **Deal:** All cards distributed evenly
2. **Play:** Take turns playing 1-4 cards face-down, declaring rank
3. **Claim:** "I play 3 Kings" (can be lying!)
4. **Challenge:** Any player can call "Bullshit!"
5. **Reveal:** If liar caught, they take pile. If honest, challenger takes pile
6. **Win:** First to empty hand

**Status:** Partially implemented (recruitment system only)

**Commands:**
```
/cardsmenu → Select "🎴 Bullshit"
```

---

## 8. RESPONSIBLE GAMBLING

**Implemented:** `cogs/blackjack.py`, `cogs/poker.py`, `cogs/gambling.py`  
**Features:** Disclaimer buttons, educational content, help resources

All card games with betting (Blackjack Fast, Poker Fast) include **always-visible gambling disclaimers** to promote responsible gaming and provide help resources.

### Disclaimer Button

**Implementation:**
```python
class DisclaimerButton(discord.ui.Button):
    """Always-visible gambling disclaimer button"""
    def __init__(self, **kwargs):
        super().__init__(
            label="⚠️ Gambling Info",
            style=discord.ButtonStyle.secondary,
            **kwargs
        )
    
    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Responsible Gambling",
            description=(
                "**This is entertainment with virtual currency only.**\n\n"
                "Gambling should never be seen as a way to make money. "
                "The odds are always in favor of the house. "
                "Set limits and know when to stop.\n\n"
                "If you or someone you know has a gambling problem, "
                "help is available:\n"
                "**National Council on Problem Gambling:** 1-800-522-4700\n"
                "**Website:** www.ncpgambling.org"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
```

**Placement:**
1. **Mid-Game:** Added to `BlackjackActionView` (Hit/Stand/Double screen) at row 2
2. **End-Game:** Added to result screens with Same Bet button at row 1
3. **Persistent:** All views use `timeout=None` for permanent button visibility

### Educational Content

**Key Messages:**
- Virtual currency only (no real money)
- House always has mathematical edge
- Entertainment value, not income source
- Set personal limits
- Know when to stop

**Help Resources:**
- **National Council on Problem Gambling (NCPG)**
  - Hotline: 1-800-522-4700
  - Website: www.ncpgambling.org
  - 24/7 confidential support

**Expected House Edge:**
- Blackjack (basic strategy): ~0.5%
- Blackjack (poor strategy): 2-5%
- 5-Card Poker vs Dealer: ~5% (varies)

### Button Persistence

**Timeout Configuration:**
```python
# All game views use timeout=None
view = BlackjackActionView(..., timeout=None)  # Never expires
view = SameBetBlackjackView(..., timeout=None)  # Always visible
view = PokerEndGameView(..., timeout=None)      # Permanent access
```

**Benefits:**
- Disclaimer accessible anytime during/after game
- No 3-minute view expiration (Discord default)
- Players can review info before next bet
- Persistent educational presence

---

## 9. TECHNICAL IMPLEMENTATION

### Deck Management

**Standard Deck Creation:**
```python
def build_deck(self, jokers: int = 0):
    """Create standard 52-card deck"""
    suits = ["♠", "♥", "♦", "♣"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    
    # Create all combinations
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    
    # Add jokers if requested
    for _ in range(jokers):
        deck.append("JOKER")
    
    # Shuffle before returning
    random.shuffle(deck)
    return deck
```

**Card Representation:**
- Format: `<rank><suit>` (e.g., "A♠", "10♥", "K♦")
- Jokers: Special string "JOKER"
- Easy parsing with `rank_of()` method

### State Management

**Go Fish State:**
```python
{
    'deck': [...],                  # Remaining cards
    'players': [player1_id, player2_id],
    'hands': {
        player1_id: ["A♠", "2♥", ...],
        player2_id: ["K♦", "5♣", ...]
    },
    'books': {
        player1_id: ["A", "K"],     # Completed sets
        player2_id: ["7"]
    },
    'turn': player1_id,             # Whose turn
    'names': {
        player1_id: "PlayerName",
        player2_id: "Bot"
    },
    'channel': channel_id           # For bot messages
}
```

**Blackjack State:**
```python
{
    'deck': [...],
    'player': ["A♠", "K♥"],         # Player's hand
    'dealer': ["7♦", "5♣"]          # Dealer's hand
}
```

**Game ID Tracking:**
```python
# Go Fish: Track by game participants
self.go_fish_games: Dict[Tuple[int, ...], Dict] = {}
self.player_to_game: Dict[int, Tuple[int, ...]] = {}

# Blackjack: Track by player ID
self.blackjack_games: Dict[int, Dict] = {}
```

### Privacy System

**DM-Based Hands:**
```python
try:
    await author.send(embed=discord.Embed(
        title="🎣 Go Fish — Your hand",
        description=self.pretty_hand(player_hand),
        color=discord.Color.blue()
    ))
except:
    await ctx.send("❌ Could not DM you. Please enable DMs from server members.")
    # Cancel game setup
```

**Ephemeral Messages (Enhanced Games):**
```python
# Solitaire - only player sees game
await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
```

### Interactive UI

**Button Views:**
```python
class SolitaireView(discord.ui.View):
    def __init__(self, cog, game_id):
        super().__init__(timeout=600)  # 10 minute timeout
        self.cog = cog
        self.game_id = game_id
    
    @discord.ui.button(label="Draw Card", style=discord.ButtonStyle.primary, emoji="🃏")
    async def draw_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.cog.active_games.get(self.game_id)
        
        if game and game['stock']:
            card = game['stock'].pop()
            game['waste'].append(card)
            
            # Update display
            embed = discord.Embed(
                title="🃏 Solitaire",
                description=self.cog.display_solitaire(self.game_id),
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ No more cards in stock!", ephemeral=True)
```

**Dropdown Menus:**
```python
class CardGameSelector(discord.ui.View):
    @discord.ui.button(label="🃏 Solitaire", style=discord.ButtonStyle.primary)
    async def solitaire_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_solitaire(interaction)
    
    @discord.ui.button(label="♠️ Spades", style=discord.ButtonStyle.secondary)
    async def spades_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.start_spades(interaction)
```

---

## 10. COMMANDS REFERENCE

### Main Commands

| Command | Description | Players | Privacy |
|---------|-------------|---------|---------|
| `/cardsmenu` | Choose card game | Varies | Ephemeral |
| **Blackjack** | | | |
| `/blackjack fast` | Instant 1v1 vs dealer with custom deck | 1 | Public |
| `/blackjack long <mode> <buy_in>` | Multiplayer lobby (COOP/PVP) | 2-8 | Public |
| `L!blackjack start` | Simple DM-based blackjack (legacy) | 1 | DM hands |
| **Poker** | | | |
| `/poker fast` | Instant 5-card vs dealer | 1 | Public |
| `/poker long <buy_in>` | Texas Hold'em tournament | 2-10 | Public |
| **Other Games** | | | |
| `L!gofish start [@user]` | Start Go Fish | 1-2 | DM hands |
| `/gofish start` | Start Go Fish (slash) | 1-2 | DM hands |
| `L!war [@user]` | Play War round | 1-2 | Public |
| `/war [@user]` | Play War round (slash) | 1-2 | Public |
| `/cardshelp` | View all card commands | - | Ephemeral |

### Blackjack Fast Commands

| Action | Type | Description |
|--------|------|-------------|
| **Bet Selection** | Ephemeral Menu | Select deck (classic/dark/platinum) + enter bet amount |
| **Hit** | Button | Draw another card (risk busting over 21) |
| **Stand** | Button | End turn, dealer plays (draws until ≥17) |
| **Double Down** | Button | Double bet, draw 1 card, auto-stand |
| **Leave** | Button | Forfeit game (lose bet) |
| **Show Hand** | Button | Display current hand value in ephemeral message |
| **Same Bet** | Button (End) | Instant replay with same bet and deck |
| **⚠️ Gambling Info** | Button | View responsible gambling disclaimer |

### Blackjack Long Commands

| Action | Type | Description |
|--------|------|-------------|
| **Join Game** | Button | Join lobby (requires buy-in balance) |
| **Leave Game** | Button | Exit lobby before start |
| **Add/Remove Bot** | Button (Host) | Toggle bot player in lobby |
| **Start Game** | Button (Host) | Begin game (requires 2+ real players) |
| **Kick Player** | Button (Host) | Remove player from lobby |
| **Game Actions** | Buttons | Same as Fast mode (Hit/Stand/Double/etc) |

### Poker Fast Commands

| Action | Type | Description |
|--------|------|-------------|
| **Bet Selection** | Ephemeral Menu | Select deck + enter bet amount |
| **Instant Deal** | Automatic | Deals 5 cards to player & dealer, evaluates winner |
| **Same Bet** | Button (End) | Replay with same bet and deck |
| **⚠️ Gambling Info** | Button | View responsible gambling disclaimer |

### Poker Long Commands

| Action | Type | Description |
|--------|------|-------------|
| **Fold** | Button | Exit hand (lose current bet) |
| **Call** | Button | Match current bet |
| **Raise** | Button | Increase bet (opens amount input) |
| **Check** | Button | Pass action without betting (if no raise) |
| **All-In** | Button | Bet all remaining chips (creates side pot) |

### Go Fish Commands

| Command | Description |
|---------|-------------|
| `L!gofish ask <rank>` | Ask opponent for rank (A, 2-10, J, Q, K) |
| `L!gofish hand` | View your hand via DM |
| `L!gofish stop` | End current game |
| `/gofish` (dropdown) | Use action menu for all Go Fish actions |

### Blackjack Simple Commands (Legacy)

| Command | Description |
|---------|-------------|
| `L!blackjack hit` | Draw another card |
| `L!blackjack stand` | End turn, dealer plays |
| `L!blackjack hand` | View your hand |
| `L!blackjack stop` | Forfeit game |
| `/blackjack` (dropdown) | Use action menu for all Blackjack actions |

**Note:** Use **Blackjack Fast** for modern experience with visual rendering and deck customization.

---

## 11. SUMMARY

**Part 5A Coverage:**
- **10 card games** across 4 files (updated May 2025)
- **Fully implemented:** Go Fish, Blackjack Fast/Long/Simple, Poker Fast/Long, War, Solitaire
- **Partially implemented:** Spades, Crazy Eights, Bullshit (recruitment only)

**Major Features:**

**🎨 Visual Card Rendering:**
- 3 custom deck styles (classic, dark, platinum)
- 156 PNG card assets (52 cards × 3 decks)
- Real-time image generation with Pillow
- Player vs dealer visual separation

**🎮 Game Modes:**
- **Fast:** Instant 1v1 games with custom decks (Blackjack, Poker)
- **Long:** Multiplayer lobbies with turn-based gameplay
- **Simple:** Legacy DM-based games (Go Fish, Blackjack Simple)

**💰 Economy Integration:**
- Betting system with balance checking
- Standard payouts: 2x win, 2.5x blackjack, 1x push
- Same Bet button for instant replay
- Economy file: `data/economy.json`

**🛡️ Responsible Gambling:**
- Always-visible ⚠️ disclaimer button
- NCPG hotline (1-800-522-4700)
- Educational content on house edge
- Persistent buttons (timeout=None)

**🎯 Lobby Systems:**
- Host controls (start/kick/bot management)
- Real player count validation
- Dynamic button state updates
- Buy-in balance verification

**Technical Highlights:**

**Code Structure:**
- Dual command system (prefix + slash)
- Type-safe state management
- Async/await game loops
- Error handling for DM failures
- View persistence with timeout=None
- Separate player/dealer deck rendering

**State Management:**
- Active game tracking per player
- Prevention of multiple simultaneous games
- Automatic cleanup on game end
- Bot opponent AI for single-player

**File Statistics:**
- `cogs/blackjack.py`: **1,944 lines** (Fast/Long/Simple modes)
- `cogs/poker.py`: **2,787 lines** (Fast/Long Texas Hold'em)
- `cogs/cardgames.py`: **1,098 lines** (Go Fish, War, game menus)
- `cogs/cards_enhanced.py`: **283 lines** (Solitaire, Spades, etc)
- **Total:** **6,112 lines** across 4 files

**Asset Files:**
- `assets/cards/classic/`: 52 PNG files
- `assets/cards/dark/`: 52 PNG files
- `assets/cards/platinum/`: 52 PNG files
- **Total:** **156 card images**

**Recent Updates (May 2025):**
- ✅ Custom deck system (3 visual styles)
- ✅ Blackjack Fast mode with image rendering
- ✅ Poker Fast mode with instant evaluation
- ✅ Same Bet button for quick replay
- ✅ Gambling disclaimer system
- ✅ Persistent buttons (never expire)
- ✅ Separate player/dealer deck rendering
- ✅ Lobby system improvements
- ✅ Non-ephemeral gameplay
- ✅ Proper casino payouts (2x/2.5x)

**Next Steps:**
- Implement card deck packs (themed sets)
- Add player statistics tracking
- Leaderboards for Fast mode wins
- Tournament brackets for Long mode
- More poker variants (Omaha, 7-Card Stud)
- Card animation effects
- Sound effects for cards/wins

---

**Documentation Complete** ✅  
For implementation details, see individual game sections above.
- **Total:** 1,014 lines of code
- **Documentation:** ~8,000 words

**Integration Points:**
- Profile system (game stats tracking)
- Economy system (future: betting on games)
- Leaderboards (game wins/losses)

