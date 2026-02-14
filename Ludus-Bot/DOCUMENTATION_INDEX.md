# 🎮 Ludus Bot - Complete Project Documentation

> **COMPLETE ENGLISH DOCUMENTATION** for the entire Ludus Discord Bot project  
> 50,000+ lines of code | 90+ Python files | 600+ commands | 450+ games  
> **Parts 1-7 Complete** ✅ | ~58,500 words documented

---

## 📋 DOCUMENTATION INDEX

This documentation is divided into comprehensive parts for easier navigation:

#### **[📘 PART 1: Core Architecture](/documentation/FULL_DOCUMENTATION_PART1.md)**
Complete analysis of bot.py (475 lines):
- Bot initialization & configuration
- Event system (on_ready, on_command, on_interaction)
- Cog loading mechanism
- Command synchronization (global + dev guild)
- Blacklist system
- Server configuration loader
- Error handling
- **Line-by-line code walkthrough**

#### **[💰 PART 2: Economy System](/documentation/FULL_DOCUMENTATION_PART2.md)** 
Complete analysis of economy.py (918 lines):
- PsyCoin currency system
- Shop & inventory management
- Daily rewards with streak bonuses
- Boost system (double_coins, xp_boost, luck_charm)
- Currency conversion (WW Gold, Farm Tokens, etc.)
- Leaderboards & rankings
- Atomic write system & data persistence
- All 15+ commands documented
- **Every function explained with code examples**

---

### Game Systems

#### **[🎣 PART 3: Simulation Games](documentation/FULL_DOCUMENTATION_PART3.md)**
Complete analysis of fishing.py, mining.py, farming.py, zoo.py (7,499 lines total):
- **Fishing System (3,472 lines - LARGEST FILE):**
  - 8 interactive UI view classes
  - 50+ fish species across 6 rarity tiers
  - 9 fishing areas with progression
  - Kraken boss fight (8 attack patterns)
  - Tournament system (auto + manual)
  - Equipment progression (rods, boats, bait)
  - Weather & time multipliers
  - Crafting system
  - 8-page in-game help system
- **Mining Adventure (3,254 lines - 2D MINECRAFT-STYLE):**
  - Procedural world generation (seed-based, 100x150 world)
  - Real-time PNG rendering (PIL, 352x320px viewport)
  - 6 biomes with depth progression (Surface → Abyss)
  - 25+ block types (ores, terrain, structures)
  - Energy system (1 per 30 seconds)
  - Shop upgrades (pickaxe, backpack, energy)
  - Item placement (ladders, torches, portals)
  - Mineshaft structures with loot chests
  - Gravity physics & darkness system
  - Singleplayer & multiplayer modes (per-server toggle)
  - Developer mode with debug tools (owner only)
- **Farming System (773 lines):**
  - 10 crop types with seasonal mechanics
  - Plot-based farming (4-20 plots)
  - 4 farm upgrades
  - Leveling system
- **~50,000 words of documentation**


#### **[🎰 PART 4A: Gambling & Arcade Games](documentation/FULL_DOCUMENTATION_PART4A.md)** 
Complete analysis of gambling.py, arcadegames.py, game_challenges.py (2,600 lines total):
- **Gambling System (1,671 lines):**
  - 8 casino games (slots, poker, roulette, higher/lower, dice, crash, mines, coinflip)
  - Comprehensive statistics tracking (per-user, per-game)
  - Win/loss ratios, biggest wins, net profit
  - Responsible gaming disclaimer system
  - House edge balancing (slots 5% RTP, roulette 50% edge)
  - Zoo encounter integration (5% chance)
  - Profile "most played games" tracking
  - Global leaderboard integration
- **Arcade Games (429 lines):**
  - PacMan (text-based with ghost AI)
  - Math Quiz (3 difficulty levels, timed)
  - Bomb Defusal (wire cutting game)
  - Interactive Discord UI with buttons
  - Skill-based, no wagering
- **Game Challenges (500 lines):**
  - Daily challenges with streak system
  - Weekly challenges with larger rewards
  - Auto-progress tracking via event hooks
  - Streak bonuses (7/14/30/60/90/180/365 days)
  - Personal bests tracking
  - Challenge rarity tiers (common → legendary)
- **~20,000 words of documentation**

#### **[🏴‍☠️ PART 4B: Lottery & Heist Systems](documentation/FULL_DOCUMENTATION_PART4B.md)** 
Complete analysis of lottery.py, heist.py (815 lines total):
- **Lottery System (313 lines):**
  - Daily automated drawings at midnight UTC
  - Sequential ticket numbering (100 coins each, 1-100 max)
  - Growing jackpot system (50% of sales + 5k if no tickets)
  - Winner announcements in all servers
  - History tracking (last 10 winners)
  - Fair probability (more tickets = higher chance)
  - Major coin sink (50% of sales removed)
- **Heist System (502 lines):**
  - Bank heists (2-6 players, 10k-50k reward)
  - Business heists (2-4 players, steal pending income)
  - Success rates scale with crew (40%-90%)
  - Equal bet requirement (1k-10k bank, 500-5k business)
  - 30-minute cooldown per player
  - Recruitment timers (60s bank, 45s business)
  - Statistics tracking (wins, losses, profit, success rate)
  - Business protection system integration
- **~12,000 words of documentation**

#### **[🃏 PART 5A: Card Games](documentation/FULL_DOCUMENTATION_PART5A.md)** 
Complete analysis of cardgames.py, cards_enhanced.py (1,014 lines total):
- **Classic Card Games (cardgames.py - 733 lines):**
  - Go Fish (vs bot or player, book completion, DM-based hands)
  - Blackjack (vs dealer, ace handling, hit/stand mechanics)
  - War (instant high-card comparison)
  - Turn-based multiplayer support with bot AI
  - State management per player
- **Enhanced Card Games (cards_enhanced.py - 283 lines):**
  - Solitaire (interactive button UI, tableau/stock/waste/foundations)
  - Spades (4-player trick-taking team game)
  - Crazy Eights (match suits/ranks, 8s are wild)
  - Bullshit (bluffing game with challenge system)
  - Ephemeral messages for privacy
  - Interactive Discord UI (buttons, dropdowns)
- **7 total card games** (4 fully implemented, 3 with lobby systems)
- **~8,000 words of documentation**

#### **[♟️ PART 5B: Board Games & UNO System](documentation/FULL_DOCUMENTATION_PART5B.md)**
Complete analysis of boardgames.py, boardgames_enhanced.py, chess_checkers.py, uno/ (11,138 lines total - **LARGEST PART**):
- **Board Games (4,141 lines):**
  - **Tic-Tac-Toe:** Minimax AI (unbeatable 3x3), 3x3/4x4/5x5 boards, Disappearing Symbols mode, lobby system, rematch
  - **Connect 4:** 6x7 grid, strategic AI (win/block/center), gravity physics
  - **Hangman:** 8 categories, hint system (penalty), 6 wrong guesses, ASCII art
  - **Scrabble:** 15x15 board, 100-tile bag, letter values, word validation, DM privacy
  - **Backgammon:** Traditional 24-point board, dice rolling, bear-off mechanics
  - **Tetris:** 7 piece types, rotation, line clearing, level progression, interactive controls
  - **Chess:** Python-chess library, PIL rendering, 6 themes, modal moves, bot AI, draw offers, resign
  - **Checkers:** 8x8 board, PIL rendering, kings, multi-jump, bot AI, move notation (3b-4c)
- **UNO System (6,997 lines - 63% of Part 5B):**
  - **Classic UNO (5,506 lines - LARGEST SINGLE FILE):** 2-10 players, bot AI with owner names, 19+ settings, multilingual (EN/PL)
  - **UNO Flip (355 lines):** Light/Dark sides, Flip mechanic, Skip Everyone, +5, Wild Draw Color
  - **UNO No Mercy (167 lines):** 168 cards, Colored +4, Skip Everyone, Discard All, Wild +6/+10, Color Roulette
  - **UNO No Mercy+ (303 lines):** Expansion pack, 10's Play Again, Wild Discard All, Reverse Draw 8, Final Attack, Sudden Death
  - **uno_logic.py (657 lines):** Shared deck/validation, custom emoji mapping (JSON), translation system (uno_translations.json), PNG asset loading
- **Technical Features:**
  - Minimax AI with alpha-beta pruning (Tic-Tac-Toe)
  - PIL board rendering (chess, checkers)
  - Interactive Discord UI (modals, buttons, dropdowns)
  - Multi-language support (EN/PL)
  - Custom emoji system with JSON mapping
  - Lobby systems with extensive settings
  - Bot opponents with strategic AI
- **8 board games + 4 UNO variants = 12 total games**
- **~30,000 words of documentation**

#### **[🎭 PART 6: Multiplayer Games](documentation/FULL_DOCUMENTATION_PART6.md)**
Complete analysis of mafia.py, multiplayer_games.py, dueling.py, monopoly.py (4,000+ lines total):
- **Mafia/Werewolf System (2,639 lines - LARGEST MULTIPLAYER FILE):**
  - 100+ roles across 4 databases (mafia/werewolf × normal/advanced)
  - 3 game modes (Normal, Advanced, Custom)
  - Smart presets for 6-16 players (20 balanced configurations)
  - 8 custom themed presets (Chaos Mode, Detective Heavy, etc.)
  - Time presets (Fast/Standard/Hardcore/Roleplay)
  - Auto-balance checker (AI-powered role composition analysis)
  - Full lobby system with interactive Discord UI
  - Role picker with preview & balance feedback
  - **Voice Mode (NEW):**
    - Theme-specific meeting spots (8 per theme)
    - Main center voice channel (town center/campfire)
    - Game center text channel (read-only updates)
    - Meeting spot locking/unlocking per phase
    - Player teleportation to center during night/vote
  - **Full Game Loop:**
    - Night phase (evil faction votes, voice conspiracy)
    - Day phase (discussion, unlocked locations)
    - Vote phase (lynch voting, locked locations)
    - Win condition checking
  - Category creation with channels (main/evil/ghost)
  - Permission system (faction-based access)
  - DM role cards with descriptions
  - Auto-cleanup after 60s
  - Bilingual support (PL/EN)
  - 26/26 features complete
- **Other Multiplayer Systems:**
  - Secret Hitler, Spyfall, Resistance
  - PvP dueling system
  - Monopoly board game (1,000 lines)
- **~15,000 words of documentation**

#### **[🎮 PART 7: Minigames System](documentation/FULL_DOCUMENTATION_PART7.md)** ⭐ **NEW**
Complete analysis of minigames.py (1,070 lines):
- **300+ Interactive Mini-Games:**
  - 50 base games (coinflip, roll, guess_number, rps, memory, reaction_time, typing_race, hangman, unscramble, quick_math, trivia, etc.)
  - 250 micro-game variants with difficulty scaling (25 levels)
  - 10 core game types: Parity, Dice Sum, Quick Math, Reverse Word, Emoji Memory, Color Pick, Fast Type, Unscramble, Trivia, Item Picking
- **Interactive Help System:**
  - Paginated embeds with working navigation buttons (Prev/Next/Close)
  - 10 games per page (~30 pages total)
  - User-specific interaction checks
  - Enhanced descriptions with button instructions
  - Integration with main help.py system (L!help mini)
- **Economy Integration:**
  - Automatic PsyCoin rewards (5 coins per win)
  - User statistics tracking (wins, games played, coins earned)
  - Non-blocking executor pattern for storage
  - Safe execution (never crashes game if economy fails)
- **Command Registration System:**
  - Programmatic registration of 300+ prefix commands
  - Anti-collision system with smart name handling
  - Alias support (micro_1, micro_2, etc.)
  - Triple-fallback command lookup
- **PaginatedHelpView Class:**
  - Reusable pagination component for other cogs
  - Interaction-based with triple-fallback send strategy
  - Customizable category names and descriptions
  - 120-second timeout with auto-cleanup
- **Recent Part 7 Updates (February 2026):**
  - Fixed button parameter order (interaction, button)
  - Fixed command wrapper argument handling (*args)
  - Removed problematic cog attribution
  - Enhanced embed descriptions and footers
  - Optimized per-page count (12 → 10)
  - help.py integration with button instructions
- **300+ games × 10-30 seconds = endless entertainment**
- **~8,500 words of documentation**

---

- **PART 8: RPG Systems** (D&D, Wizard Wars, Quests)

### Social & Utility Systems
- **PART 9: Social Features** (Pets, Marriage, Reputation, Profiles)
- **PART 10: Server Management** (Starboard, Counting, Confessions, Events)
- **PART 11: Utility Commands** (Help, Info, Utilities)

### Technical Reference
- **PART 12: Admin & Owner Commands**
- **PART 13: Data Structures** (JSON files, data schemas)
- **PART 14: Integration Guide** (How cogs interact)
- **PART 15: Deployment** (Docker, Render.com, setup)

---

## 🏗️ PROJECT ARCHITECTURE OVERVIEW

### File Structure (90 Files)

```
Ludus-Bot/ (50,000+ lines total)
│
├── 📄 Core Files (4 files, ~1,500 lines)
│   ├── bot.py (475 lines) - Main bot entry point
│   ├── start.py (50 lines) - Production launcher  
│   ├── constants.py (100 lines) - Global constants
│   └── config.json - Bot configuration
│
├── 🎯 Cogs/ (70+ files, 45,000+ lines)
│   │
│   ├── 💰 Economy & Core (8 files, ~5,000 lines)
│   │   ├── economy.py (918 lines) - Currency system
│   │   ├── achievements.py (600 lines) - Achievement tracking
│   │   ├── daily_rewards.py (400 lines) - Daily claims
│   │   ├── profile.py (600 lines) - User profiles
│   │   ├── reputation.py (300 lines) - Reputation system
│   │   ├── leaderboards.py (500 lines) - Rankings
│   │   ├── global_leaderboard.py (300 lines) - Cross-server
│   │   └── quests.py (500 lines) - Quest system
│   │
│   ├── 🎣 Simulation Games (5 files, ~10,000 lines)
│   │   ├── fishing.py (3472 lines) - **BIGGEST FILE**
│   │   ├── farming.py (1200 lines) - Farm simulator
│   │   ├── mining.py (3249 lines) - **2nd BIGGEST**
│   │   ├── zoo.py (800 lines) - Animal collection
│   │   └── farmshop.py (300 lines) - Farming marketplace
│   │
│   ├── 🎰 Gambling & Casino (3 files, ~3,000 lines)
│   │   ├── gambling.py (1200 lines) - Blackjack, Slots, Roulette
│   │   ├── lottery.py (400 lines) - Lottery system
│   │   └── heist.py (700 lines) - Bank heist co-op
│   │
│   ├── 🎮 Card & Board Games (6 files, ~5,000 lines)
│   │   ├── cardgames.py (900 lines) - Poker, Blackjack
│   │   ├── cards_enhanced.py (600 lines) - Advanced cards
│   │   ├── boardgames.py (1000 lines) - Chess, Checkers
│   │   ├── boardgames_enhanced.py (800 lines) - Advanced boards
│   │   ├── chess_checkers.py (1000 lines) - Chess/Checkers system
│   │   ├── uno_gofish.py (1200 lines) - UNO game
│   │   └── uno/ (5 files, ~2000 lines) - Modular UNO system
│   │       ├── __init__.py
│   │       ├── uno_logic.py
│   │       ├── classic.py
│   │       ├── flip.py
│   │       ├── no_mercy.py
│   │       └── no_mercy_plus.py
│   │
│   ├── 🕹️ Minigames & Arcade (5 files, ~4,000 lines)
│   │   ├── minigames.py (1070 lines) - **300+ mini-games**
│   │   ├── arcadegames.py (800 lines) - Arcade classics
│   │   ├── puzzlegames.py (600 lines) - Puzzles
│   │   ├── game_challenges.py (400 lines) - Challenges
│   │   └── simulations.py (600 lines) - Life simulations
│   │
│   ├── 🎭 Multiplayer & Social Deduction (3 files, ~2,500 lines)
│   │   ├── mafia.py - Warewolf & Mafia
│   │   ├── multiplayer_games.py (800 lines) - clue, murder mystery
│   │   ├── monopoly.py (1000 lines) - Monopoly board game
│   │   └── dueling.py (400 lines) - PvP duels
│   │
│   ├── ⚔️ RPG & Campaign Systems (3 files, ~2,500 lines)
│   │   ├── dnd.py (1500 lines) - D&D campaigns
│   │   ├── wizardwars.py (800 lines) - Wizard dueling RPG
│   │   └── guilds.py (400 lines) - Guild/clan system
│   │
│   ├── 🐾 Social & Collection (6 files, ~3,000 lines)
│   │   ├── pets.py (800 lines) - Pet ownership system
│   │   ├── marriage.py (400 lines) - Marriage feature
│   │   ├── social.py (500 lines) - Social interactions
│   │   ├── actions.py (400 lines) - Action commands
│   │   ├── trading.py (500 lines) - Player trading
│   │   └── psyvrse_tcg.py (600 lines) - Trading card game
│   │
│   ├── 🔧 Utility & Fun (8 files, ~3,000 lines)
│   │   ├── funcommands.py (600 lines) - Fun commands
│   │   ├── fun.py (500 lines) - Entertainment
│   │   ├── utilities.py (400 lines) - Utility tools
│   │   ├── meme.py (300 lines) - Meme generator
│   │   ├── quotes.py (200 lines) - Quote system
│   │   ├── akinator_enhanced.py (600 lines) - Akinator game
│   │   ├── personality.py (300 lines) - Personality quiz
│   │   └── seasonal.py (400 lines) - Seasonal events
│   │
│   ├── 🛡️ Server Management (7 files, ~2,500 lines)
│   │   ├── server_config.py (400 lines) - Server settings
│   │   ├── starboard.py (400 lines) - Message highlights
│   │   ├── counting.py (300 lines) - Counting game
│   │   ├── confessions.py (300 lines) - Anonymous posts
│   │   ├── globalevents.py (700 lines) - Server-wide events
│   │   ├── serverinfo.py (300 lines) - Server info
│   │   └── tutorial.py (400 lines) - Bot tutorial
│   │
│   ├── 📚 Help & Information (3 files, ~1,500 lines)
│   │   ├── help.py (800 lines) - Custom help system
│   │   ├── help_system.py (400 lines) - Help framework
│   │   └── about.py (200 lines) - Bot information
│   │
│   ├── 👑 Admin & Owner (4 files, ~2,000 lines)
│   │   ├── owner.py (1100 lines) - Owner-only commands
│   │   ├── blacklist.py (300 lines) - User/server blocking
│   │   ├── gamecontrol.py (400 lines) - Game management
│   │   └── bot_logger.py (300 lines) - Logging system
│   │
│   └── 🌐 Other Systems (10+ files, ~3,000 lines)
│       ├── businesses.py (500 lines) - Business simulator
│       ├── business.py (400 lines) - Business management
│       ├── command_groups.py (300 lines) - Command organization
│       ├── game_stats.py (400 lines) - Statistics tracking
│       ├── onboarding.py (300 lines) - New user onboarding
│       ├── perimeter.py (400 lines) - Moderation tools
│       ├── perimeter_explicit.py (300 lines) - Explicit content
│       └── professional_info.py (300 lines) - Professional data
│
├── 📦 Utils/ (3 files, ~500 lines)
│   ├── embed_styles.py (200 lines) - Consistent embeds
│   ├── user_storage.py (150 lines) - User data storage
│   └── performance.py (150 lines) - Performance monitoring
│
├── 💾 Data/ (20+ JSON files)
│   ├── economy.json - User balances
│   ├── fishing_data.json - Fishing progress
│   ├── inventory.json - User inventories
│   ├── pets.json - Pet ownership
│   ├── profiles.json - User profiles
│   ├── achievements_data.json - Achievements
│   ├── quests_data.json - Quest progress
│   ├── gambling_stats.json - Gambling history
│   ├── game_stats.json - Game statistics
│   ├── leaderboard_stats.json - Rankings
│   ├── server_configs.json - Server settings
│   ├── uno_emoji_mapping.json - UNO emojis
│   ├── uno_translations.json - UNO translations
│   └── tcg/ - Trading card game data
│
└── 🎨 Assets/
    ├── cards/ - Playing card images
    └── uno_cards/ - UNO card images
    └── mining/ - mining image assets
```

---

## 📊 PROJECT STATISTICS

### Code Metrics
```
Total Lines of Code:   50,000+
Total Python Files:    90
Total Cogs:            70+
Total Commands:        300+
Slash Commands:        150+
Prefix Commands:       150+
Total Games:           150+
Data Files:            20+
```

### Complexity Breakdown
```
Largest File:   fishing.py (3,472 lines)
2nd Largest:    mining.py (3,249 lines)
3rd Largest:    minigames.py (1,070 lines)
4th Largest:    dnd.py (1,500 lines)
5th Largest:    monopoly.py (1,000 lines)
```

### System Categories
```
💰 Economy & Currency:     ~5,000 lines (10%)
🎣 Simulation Games:       ~10,000 lines (20%)
🎰 Gambling & Casino:      ~3,000 lines (6%)
🎮 Card & Board Games:     ~5,000 lines (10%)
🕹️ Minigames & Arcade:    ~4,000 lines (8%)
⚔️ RPG & Campaigns:        ~2,500 lines (5%)
🐾 Social & Collection:    ~3,000 lines (6%)
🔧 Utility & Fun:          ~3,000 lines (6%)
🛡️ Server Management:      ~2,500 lines (5%)
👑 Admin & Owner:          ~2,000 lines (4%)
📚 Help & Info:            ~1,500 lines (3%)
🌐 Other Systems:          ~3,000 lines (6%)
📦 Utils:                  ~500 lines (1%)
🏗️ Core Architecture:      ~1,500 lines (3%)
🎨 Assets & Config:        ~3,000 lines (6%)
```

---

## 🎯 FEATURE OVERVIEW

#### Casino & Gambling 🎰
- [ ] **Blackjack** - Classic 21 with side bets
- [ ] **Slots** - 5-reel slots with jackpots
- [ ] **Roulette** - European & American variants
- [ ] **Coinflip** - Double or nothing
- [ ] **Dice Games** - Craps, Sic Bo
- [ ] **Lottery** - Daily and weekly draws
- [ ] **Heist** - Cooperative bank robbery

#### Board & Card Games 🎮
- [ ] **Chess** - Full chess implementation
- [ ] **Checkers** - Classic checkers
- [ ] **UNO** - 5 game modes
  - Classic UNO
  - UNO Flip
  - No Mercy
  - No Mercy Plus
  - Custom rules
- [ ] **Poker** - Texas Hold'em
- [ ] **Blackjack** - Card game variant
- [ ] **Monopoly** - Full board game

#### Minigames (100+) 🕹️
- [ ] **Trivia** - 1000+ questions, 20+ categories
- [ ] **Word Games** - Hangman, Word Chain, Anagrams
- [ ] **Math Games** - Math Quiz, Quick Math
- [ ] **Reaction Games** - Button Click, Type Race
- [ ] **Memory Games** - Simon Says, Memory Match
- [ ] **Puzzle Games** - Sudoku, 2048, Minesweeper
- [ ] **Arcade Classics** - Snake, Pong, Tetris-style
- [ ] **Quick Games** - 50+ rapid mini-games

#### Multiplayer & Social Deduction 🎭
- [ ] **Mafia** - Classic Mafia game
- [ ] **Werewolf** - Village vs Werewolves
- [ ] **Among Us Style** - Social deduction
- [ ] **Secret Hitler** - Hidden roles
- [ ] **Spyfall** - Location guessing
- [ ] **Dueling** - PvP combat system

#### RPG & Campaign Systems ⚔️
- [ ] **D&D Campaigns** (1500 lines) - Full D&D system
  - Character creation (races, classes)
  - Dice rolling (d4, d6, d8, d10, d12, d20, d100)
  - Campaign management
  - NPC system
  - Combat encounters
  - Treasure & loot
  
- [ ] **Wizard Wars** (800 lines) - Wizard dueling RPG
  - 30+ spells
  - Element system (Fire, Water, Earth, Air)
  - Wizard customization
  - PvP dueling
  - Gold economy
  
- [ ] **Quests** (500 lines) - Quest system
  - Daily quests
  - Weekly quests
  - Achievement quests
  - Reward tiers
  - Progress tracking

- [ ] **Guilds** (400 lines) - Guild/clan system
  - Guild creation
  - Member management
  - Guild bank
  - Guild wars
  - Leaderboards

#### Social & Collection Systems 🐾
- [ ] **Pets** (800 lines) - Pet ownership
  - 20+ pet species
  - Happiness & hunger systems
  - Pet training
  - Pet battles
  - Breeding system
  
- [ ] **Marriage** (400 lines) - Marriage system
  - Proposal system
  - Marriage benefits
  - Joint balance
  - Divorce mechanics
  
- [ ] **Reputation** (300 lines) - Rep system
  - Give/receive reputation
  - Reputation levels
  - Perks & rewards
  
- [ ] **Profiles** (600 lines) - User profiles
  - Customizable profiles
  - Statistics display
  - Badges & achievements
  - Activity tracking
  
- [ ] **Trading** (500 lines) - Player trading
  - Item trading
  - Pet trading
  - Currency trading
  - Trade history
  
- [ ] **TCG** (600 lines) - Trading card game
  - 100+ cards
  - Rarity system
  - Card packs
  - Trading system
  - PvP battles

#### Server Management 🛡️
- [ ] **Starboard** (400 lines) - Message highlights
  - Star threshold customization
  - Starboard channel
  - Leaderboard
  
- [ ] **Counting** (300 lines) - Counting game
  - Count incrementally
  - Track who breaks it
  - Leaderboards
  
- [ ] **Confessions** (300 lines) - Anonymous posts
  - Anonymous messaging
  - Confession channel
  - Moderation tools
  
- [ ] **Global Events** (700 lines) - Server-wide events
  - Scheduled events
  - Event rewards
  - Participation tracking
  
- [ ] **Server Config** (400 lines) - Server settings
  - Prefix customization
  - Feature toggles
  - Channel configuration

#### Utility & Fun Commands 🔧
- [ ] **Fun Commands** (600 lines) - Entertainment
  - 8ball, meme, roast, joke
  - Random generators
  - ASCII art
  
- [ ] **Utilities** (400 lines) - Utility tools
  - Reminders
  - Polls
  - Timers
  - Calculators
  
- [ ] **Help System** (1200 lines) - Custom help
  - Command categories
  - Interactive help
  - Command search
  - Examples & tutorials

#### Admin & Owner Systems 👑
- [ ] **Owner Commands** (1100 lines) - Bot admin
  - Eval command (code execution)
  - Cog reload
  - Economy management
  - User management
  - Statistics
  
- [ ] **Blacklist** (300 lines) - Blocking system
  - User blacklist
  - Server blacklist
  - Blacklist reasons
  
- [ ] **Game Control** (400 lines) - Game management
  - Force end games
  - Game timeouts
  - Game statistics

---

## 🔧 TECHNICAL ARCHITECTURE

### Technology Stack
```python
# Core Framework
discord.py==2.3.2      # Discord API wrapper
asyncio                # Async operations

# Data & Storage
json                   # Data serialization
os, shutil             # File operations

# Utilities
python-dotenv==1.0.0   # Environment variables
aiohttp==3.9.1         # Async HTTP
Pillow==10.1.0         # Image processing
random, datetime       # Standard library
```

### Design Patterns

#### 1. Cog Architecture
Every feature is a **separate cog** (module) that can be loaded/unloaded independently:
```python
class FeatureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize feature-specific data
    
    async def cog_load(self):
        # Setup when cog loads
        pass
    
    def cog_unload(self):
        # Cleanup when cog unloads
        pass
```

#### 2. Hybrid Commands
All commands support **both prefix and slash** commands:
```python
@commands.command(name="balance")
async def balance_prefix(self, ctx):
    await self._show_balance(ctx.author, ctx, None)

@app_commands.command(name="balance")
async def balance_slash(self, interaction: discord.Interaction):
    await interaction.response.defer()
    await self._show_balance(interaction.user, None, interaction)

async def _show_balance(self, user, ctx, interaction):
    # Unified logic for both command types
    pass
```

#### 3. Data Persistence
**JSON-based storage** with atomic writes:
```python
# Write to temp file first
temp_file = file_path + ".tmp"
with open(temp_file, 'w') as f:
    json.dump(data, f, indent=2)

# Atomic rename (safe)
os.replace(temp_file, file_path)
```

#### 4. Economy Integration
Every cog that rewards players uses economy:
```python
economy_cog = self.bot.get_cog("Economy")
if economy_cog:
    economy_cog.add_coins(user.id, reward, "source_name")
```

#### 5. Interactive Views
Discord Components v2 for rich interactions:
```python
class GameView(discord.ui.View):
    @discord.ui.button(label="Play", style=discord.ButtonStyle.success)
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle button click
        pass
```

### Data Flow

```
User Command
     ↓
Discord Gateway
     ↓
bot.py (Event Router)
     ↓
Appropriate Cog
     ↓
Business Logic
     ↓
Economy Integration (if rewards)
     ↓
Data Persistence (JSON)
     ↓
Response to User
```

### Scalability Features

1. **In-Memory Caching** - All data loaded into RAM
2. **Autosave System** - Background saves every 5 minutes
3. **Concurrency Locks** - Prevent race conditions
4. **Lazy Loading** - User accounts created on first use
5. **Atomic Writes** - Prevent data corruption
6. **Backup System** - Automatic backups before overwrites

---

## 🚀 GETTING STARTED

### Prerequisites
```bash
Python 3.10+
discord.py 2.3.2+
50MB disk space (for data files)
```

### Installation
```bash
# Clone repository
git clone "It's on GitHub."
cd Ludus-Bot

# Install dependencies
pip install -r requirements.txt

# Configure bot token
echo "LUDUS_TOKEN=your_bot_token_here" > .env

# Run bot
python start.py
```

### Configuration Files

**config.json:**
```json
{
  "prefix": "L!",
  "owner_ids": [1138720397567742014, 1382187068373074001, 1300838678280671264, 1311394031640776716, 1310134550566797352],
  "emojiServerId": [1445021753846796371, 1327316480983040000, 1455492650009624589, 1441089572628074700]
}
```

**.env:**
```
LUDUS_TOKEN=your_bot_token_here
DEV_GUILD_IDS=123456789  # Optional: for fast slash command testing
RENDER_DISK_PATH=/path/to/persistent/disk  # Optional: for cloud hosting
```

---

## 📖 COMMAND REFERENCE (Quick Overview)

### Economy Commands
- `L!balance` / `/balance` - Check PsyCoin balance
- `L!daily` / `/daily` - Claim daily reward
- `L!shop` / `/shop` - View shop
- `L!buy <item>` / `/buy` - Purchase item
- `L!inventory` / `/inventory` - View inventory
- `L!use <item>` / `/use` - Use an item
- `L!give <user> <amount>` / `/give` - Give coins
- `L!leaderboard` / `/leaderboard` - View rankings

### Fishing Commands
- `L!fish` / `/fish` - Go fishing
- `L!fish_stats` / `/fish_stats` - View fishing statistics
- `L!fish_shop` / `/fish_shop` - Browse fishing shop
- `L!encyclopedia` / `/encyclopedia` - Fish encyclopedia
- `L!fight_kraken` / `/fight_kraken` - Battle the Kraken boss

### Mining Commands
- `L!mine` / `/mine` - Start mining
- `L!mine_shop` / `/mine_shop` - Browse mining shop
- `L!mine_stats` / `/mine_stats` - View mining stats
- `L!structures` / `/structures` - View discovered structures

### Gambling Commands
- `L!blackjack <bet>` / `/blackjack` - Play blackjack
- `L!slots <bet>` / `/slots` - Play slots
- `L!roulette <bet> <number/color>` / `/roulette` - Play roulette
- `L!coinflip <bet>` / `/coinflip` - Flip a coin

### Game Commands
- `L!chess <opponent>` / `/chess` - Play chess
- `L!uno` / `/uno` - Start UNO game
- `L!trivia` / `/trivia` - Play trivia
- `L!tictactoe <opponent>` / `/tictactoe` - Play tic-tac-toe

### Minigames Commands (300+ quick games)
- `L!gamelist` - View all 300+ minigames (paginated)
- `L!help mini` - View minigames via help system
- `L!coinflip` - Flip a coin
- `L!roll` - Roll 1-100
- `L!guess_number` - Guess a number 1-20
- `L!rps` - Rock, Paper, Scissors
- `L!memory` - Remember emoji sequence
- `L!reaction_time` - Test your reflexes
- `L!typing_race` - Type sentence quickly
- `L!hangman` - Play hangman
- `L!quick_math` - Solve math problem
- `L!unscramble` - Unscramble a word
- `L!parity_guess_micro` (or `L!micro_1`) - Even/odd guess
- `L!dice_sum_micro` (or `L!micro_2`) - Dice sum game
- ... (290+ more micro-games with difficulty scaling)

### Social Commands
- `L!pet` / `/pet` - View your pet
- `L!marry <user>` / `/marry` - Propose marriage
- `L!profile` / `/profile` - View profile
- `L!rep <user>` / `/rep` - Give reputation

... (300+ total commands)

---

## 📈 FUTURE IMPROVEMENTS

### How to define plans for the future
- [ ] TEST
- [x] TEST 


---

## 🤝 CONTRIBUTING

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Document all functions
- Add docstrings to classes

### Testing
- Test all commands before committing
- Verify economy integration
- Check for memory leaks
- Test with multiple users

### Pull Request Process
1. Fork the repository
2. Create feature branch
3. Implement changes
4. Test thoroughly
5. Submit PR with description

---

## 📝 LICENSE

This project is proprietary. All rights reserved.

---

**This documentation is a living document and will be updated as the project evolves.**

Last Updated: 06.02.2026
Total Documentation Size: 58,500+ words across 7 completed parts (Parts 1-7)
Documentation Status: ✅ Parts 1-7 Complete | 🚧 Parts 8-15 Planned
The documentation was written by wilczek80.