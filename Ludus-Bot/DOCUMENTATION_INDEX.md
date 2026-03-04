# 🎮 Ludus Bot - Complete Project Documentation

> **COMPLETE ENGLISH DOCUMENTATION** for the entire Ludus Discord Bot project  
> 50,000+ lines of code | 90+ Python files | 600+ commands | 450+ games  
> **Parts 1-16 + Utils Reference Complete** ✅ | ~153,000+ words documented

---

## 📋 DOCUMENTATION INDEX

This documentation is divided into comprehensive parts for easier navigation:

#### **[📘 PART 1: Core Architecture](/documentation/FULL_DOCUMENTATION_PART1.md)**
Complete analysis of bot.py (315 lines):
- Bot initialization & configuration (`BotCommandTree` subclass)
- `activity_worker` — async batch-saves to user_activity.json
- `setup_hook` — loads UNO emojis, all cogs, starts storage worker
- Simplified `on_ready` (global command sync only)
- Blacklist system
- Server configuration loader
- Error handling
- **Line-by-line code walkthrough**

#### **[💰 PART 2: Economy System](/documentation/FULL_DOCUMENTATION_PART2.md)** 
Complete analysis of economy.py (1,206 lines):
- PsyCoin currency system
- Shop & inventory management (incl. `card_box`, `card_decks`)
- Daily rewards with streak bonuses
- Boost system (double_coins, xp_boost, luck_charm)
- Currency conversion: `/convert` — FishCoins, MineCoins, FarmCoins ↔ PsyCoins
- `/currencies` display command;
- Leaderboards & rankings
- Atomic write system & data persistence
- All 15+ commands documented
- **Every function explained with code examples**

---

### Game Systems

#### **[🎣 PART 3: Simulation Games](documentation/FULL_DOCUMENTATION_PART3.md)**
Complete analysis of fishing.py, mining.py, farming.py, zoo.py (8,298 lines total):
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
- **Mining Adventure (4,053 lines - 2D MINECRAFT-STYLE):**
  - Procedural world generation (seed-based, 100x150 world)
  - Real-time PNG rendering (PIL, 352x320px viewport)
  - 6 biomes with depth progression (Surface → Abyss)
  - 25+ block types; `BLOCK_REQUIREMENTS` (min pickaxe level per block)
  - `ORE_STATES` system: cracked (50% yield) / irradiated (energy penalty)
  - `CREATURE_TYPES` — 7 underground creatures (zombie, skeleton, spider, creeper, enderman, mole, worm) each with stats, drops, and behavior
  - 12 mining achievements (`MINING_ACHIEVEMENTS`) with coin/XP rewards
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
Complete analysis of gambling.py (1,404 lines) + blackjack.py (2,001 lines) + poker.py (2,824 lines) + arcadegames.py + game_challenges.py:
- **Gambling System (1,404 lines):**
  - 7 casino games in gambling.py (slots, roulette, higher/lower, dice, crash, mines, coinflip)
  - **Blackjack — dedicated `blackjack.py` cog (2,001 lines):** two modes — **Fast** (instant solo vs dealer, hit/stand/double, 2.5× blackjack payout, custom card deck) and **Long** (multiplayer lobby, 1-10 players, COOP or PVP mode); imports visual helpers from `poker.py`
  - **Poker — dedicated `poker.py` cog (2,824 lines):** full Texas Hold'em, 2-8 players, `PokerGame`/`PokerGameView`/`PokerActionView`, settings lobby, custom card deck support
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
Complete analysis of lottery.py, heist.py (945 lines total):
- **Lottery System (324 lines):**
  - Daily automated drawings at midnight UTC
  - Sequential ticket numbering (100 coins each, 1-100 max)
  - Growing jackpot system (50% of sales + 5k if no tickets)
  - Winner announcements in all servers
  - History tracking (last 10 winners)
  - Fair probability (more tickets = higher chance)
  - Major coin sink (50% of sales removed)
- **Heist System (621 lines):**
  - Bank heists (2-6 players, 10k-50k reward)
  - Business heists (2-4 players, steal pending income)
  - `HeistJoinView` interactive lobby — join / launch / cancel buttons
  - Auto-launch when crew full; leader can launch early; timeout fires heist
  - Success rates scale with crew (40%-90%)
  - Equal bet requirement (1k-10k bank, 500-5k business)
  - 30-minute cooldown per player
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
  - clue, murder mystery
  - PvP dueling system
  - Monopoly board game (1,000 lines)
- **~15,000 words of documentation**

#### **[🎮 PART 7: Minigames System](documentation/FULL_DOCUMENTATION_PART7.md)**
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

#### **[⚔️ PART 8: RPG Systems](documentation/FULL_DOCUMENTATION_PART8.md)**
Complete analysis of dnd.py, dnd_gate1_fantasy.py, wizardwars.py, quests.py (~13,386 lines total — **LARGEST PART BY FAR**):
- **Infinity Adventure (dnd.py — 2,229 lines + dnd_gate1_fantasy.py — 9,902 lines):**
  - Bilingual RPG (EN/PL) — 80+ UI strings in `TRANSLATIONS` dict, `t(lang, key, **kwargs)` helper
  - `PlayerData` class — cosmic stats (influence, deaths, worlds_changed), dimension states, NPC relationships, artefacts (survive death)
  - `CurrentCharacter` class — name + class + combat stats (HP/mana/stamina) + D&D attributes (STR/INT/CHR/LCK)
  - `InfinityView` — `discord.ui.LayoutView` state machine (7 states: language → mode → tutorial → cape → char_creation → story → death)
  - 9 gate dimensions with unique themes, rulers, and class lists (Fantasy, Steampunk, Dieselpunk, Cyberpunk, Post-Apocalypse, Sci-Fi, Space Opera, Surreal, Cosmic Horror)
  - Party mode: multi-user sessions, turn-based action system, join-lobby UI
  - Save/Load: `data/saves/infinity_adventure.json` (keyed by user_id)
  - **Gate 1 Fantasy (9,902 lines — LARGEST FILE IN PROJECT):** `Gate1WorldState` (4 faction HP bars, 25+ quest flags, NPC alive/dead), 50+ branching scenes, `get_gate1_scene()` engine, 5 entry points, full consequence system
  - Anti-cheat death tracking
- **Wizard Wars (wizardwars.py — 855 lines):**
  - 32 spells across 4 schools (Elemental 14 / Cosmic 6 / Forbidden 6 / Divine 6)
  - 14 spell types with distinct effects (damage, shield, heal, freeze, lifesteal, execute, revive…)
  - 6 spell combos (e.g. Gravity Well + Black Hole = Singularity, power 15)
  - 12 territories for guild conquest
  - `ShopView` — dropdown preview + buy button; auto-refreshes after purchase; shows remaining unowned spells
  - AI duel: random AI wizard ±1 level, 20-turn combat loop, XP + Gold rewards, TCG card drop on win
  - Gold economy separate from PsyCoins (spells cost `power × 100` Gold)
  - `/wizardwars` + `/ww` (alias) slash commands, 10 action choices each
- **Quests & Achievements (quests.py — ~400 lines):**
  - 5 daily quest types (random assigned, 24h reset via `@tasks.loop(hours=24)`)
  - 10 permanent achievements (first_win → millionaire, 50–500 coin rewards)
  - `update_quest_progress(user_id, quest_type, amount)` — API for other cogs to report events
  - TCG card reward on quest completion AND achievement unlock (via DM)
  - Progress bar renderer (`_create_progress_bar` — `█░` blocks)
  - `L!quests` / `L!achievements [member]` / `/questshelp` (PaginatedHelpView)
- **~15,000 words of documentation**

### Social & Utility Systems

#### **[🐾 PART 9: Social Features](documentation/FULL_DOCUMENTATION_PART9.md)**
Complete analysis of pets.py, marriage.py, reputation.py, profile.py, social.py, trading.py (5,102 lines total):
- **Pets System (pets.py — 741 lines):**
  - 16 pets across 5 rarities (Common 55% / Uncommon 28% / Rare 12% / Epic 4% / Legendary 1%)
  - Weighted random adoption — first pet FREE, subsequent 10,000 PsyCoins
  - **14 perk types:** `gambling_mult`, `gambling_loss_red`, `gambling_jackpot`, `fishing_mult`, `fishing_rare`, `fishing_value`, `mining_speed`, `mining_rare`, `mining_xp`, `farm_yield`, `farm_auto_tend`, `coins_mult`, `daily_bonus`, `xp_mult`
  - `PetDashboardView` — Components V2 LayoutView with feed/play/walk/release buttons
  - Auto-disables buttons when stats at limits (hunger ≥ 90, energy < 20)
  - Farm damage system: hungry pets (<40 hunger) may trample/burn/eat/dig crops
  - Full inter-cog API: provides multipliers to fishing, mining, farming, gambling, economy, daily
  - `/pet` slash command
- **Marriage System (marriage.py — 456 lines):**
  - Proposal system with 5-minute timeout and 10,000-coin cost
  - Shared bank (deposit/withdraw, mirrored on both spouses)
  - Couple quests: 4 quests (5k–10k rewards + love points)
  - Divorce: 5,000 coins, shared bank lost
  - Commands: `L!marry`, `L!divorce`, `L!spouse`, `L!bank`, `L!couplequests`
- **Reputation System (reputation.py — 396 lines):**
  - 8 tiers: 👤 Neutral → 🌟 Legendary /// ⚠️ Questionable → ☠️ Notorious
  - 24h cooldown per user pair (in-memory, resets on restart)
  - Shop price modifier ±20%, reward modifier ±10%
  - History tracking, leaderboard, tier explanations
- **Profile System (profile.py — 911 lines):**
  - `ProfileManager` — aggregates stats from 5 files: profiles.json + users/{id}.json + economy.json + fishing_data.json + gambling_stats.json
  - `ProfileView` — Components V2 LayoutView, 4 pages: **Overview** (level, energy, pet, top activities) / **Gaming** (W/L/D for 10+ games) / **Economy** (balances, gambling ROI, business) / **Social** (pet care, events, last active)
  - Card deck selector embedded in profile (equip cosmetic decks)
  - 60+ tracked stats across gambling, minigames, board games, cards, TCG, fishing, farming, pets, social, quests, events, business, combat, music
  - `L!profile` / `/profile` / `L!energy`
- **Social System (social.py — 998 lines):**
  - 59 roasts + 54 compliments with coin rewards and achievement hooks
  - Would You Rather: community-sourced questions, 10-coin play reward, 25-coin contribute reward
  - Story Maker: `on_message` listener, per-word 5-coin reward on story end
  - GIF reaction commands via nekos.best API: `/hug`, `/kiss`, `/slap`, `/petpet` (some-random-api), `/ship`
  - `/ship` — deterministic `(id1+id2) % 101` score, 6 tiers, animated GIF
  - `L!pray` (+10–50 coins blessing), `L!curse` (10% backfire), `L!avatar`
- **Trading System (trading.py — 1,289 lines):**
  - P2P `TradeSession` with add/remove/confirm/cancel flow
  - Confirmation resets on any offer change (bait-and-switch prevention)
  - Pre-flight validation before execution
  - `L!sell` — 85–90% value for shop items, crops, wizard spells, pets (pets require confirmation)
  - Anonymous gift system via DM: coins, items, crops, spells
  - Block/unblock system; gift enable/disable settings
  - `L!admire` and `L!encourage` — anonymous DM messages
  - Trade history logged to `data/trade_history.json` + `data/users/{id}.json`
- **~11,500 words of documentation**

#### **[🛡️ PART 10: Server Management](documentation/FULL_DOCUMENTATION_PART10.md)**
Complete analysis of starboard.py, counting.py, confessions.py, globalevents.py (~1,700 lines total):
- **Starboard System (starboard.py — 449 lines):**
  - Up to 5 independent starboards per server (each tracks a different emoji)
  - Configurable reaction threshold, self-star prevention, per-emoji channel
  - Visual scaling: color `gold → orange → red` and icon `✨ → ⭐ → 🌟` based on popularity ratio
  - Rich embeds: image relay, attachment links, reply context, jump-to-message
  - `/starboard create/edit/remove/list` slash group + `L!starboard` prefix group
  - Uses raw reaction events so old (uncached) messages are handled correctly
  - In-place editing of existing posts; posts removed when reactions drop below threshold
- **Counting Game (counting.py — ~350 lines):**
  - Designated counting channel per guild; non-numeric messages deleted silently
  - Anti-consecutive rule: same user can't count twice in a row
  - PsyCoins: 2 coins per 4 counts + milestone bonuses (25→1000 counts: 10–500 coins)
  - Milestone roles auto-created: `Counter 25`, `Counter 50`, …, `Counter 25000`
  - Delete detection: bot announces when a user deletes their counted number
  - Leaderboard integration: `counting_peak` tracked via `leaderboard_manager`
- **Confessions System (confessions.py — ~230 lines):**
  - Users type in confession channel; bot deletes original and reposts anonymously
  - Sequential numbering: `🔒 CONFESSION #X`
  - Admin log channel records username, user ID, avatar, and full message content
  - Commands pass-through guard (L!, /, ! prefixes skip the confession flow)
  - Atomic `save_config()` with `.tmp` + `os.replace()` pattern
- **Global Events (globalevents.py — 675 lines):**
  - Owner-only event launcher; broadcasts to all guilds simultaneously
  - **WAR Event:** 4 factions (Iron Legion, Ashborn, Voidwalkers, Skybound); users join with `L!joinfaction`; winning faction earns 10,000 coins each; `add_war_points()` API for other cogs
  - **World Boss:** 4 bosses (50M–100M HP); button + prefix attack; 30s per-user cooldown; enrage at 75% HP lost (×1.5 dmg); top 10 + last-hit bonuses; `L!bossstats` for live HP
  - **Target Hunt:** Background task fires challenges every 1–3 minutes across all servers
  - **Chaos Festival:** Stub (planned for future update)
  - Economy integration: `add_coins()` for all reward payouts; BotLogger integration for spawn/end events
- **~8,500 words of documentation**

#### **[📚 PART 11: Utility & Help Systems](documentation/FULL_DOCUMENTATION_PART11.md)**
Complete analysis of help.py, help_system.py, about.py, utilities.py, serverinfo.py (~1,325 lines total):
- **Help System (help.py — 466 lines):**
  - 16 manually curated categories + 1 owner-only category (17 total)
  - `CategorySelect` dropdown — `discord.ui.Select` with key-based values, shown on main help page
  - Fuzzy category matching: exact key, substring, normalized text
  - `FakeCtx` bridge: wraps slash `Interaction` so prefix-based `owner_help` can be called from `/help owner`
  - Section-header rows: entries starting with `—` render as `▸ SECTION HEADER` dividers
  - Both `L!help [category]` and `/help [category]` fully supported
  - `CategoryView` timeout: 60 seconds
- **Help Framework (help_system.py — ~115 lines):**
  - `HelpView` — reusable paginator (Prev/Next, modulo wrap, 120s timeout) used by `minigames.py`
  - `CAT_LIST` — 14-entry `(name, emoji)` list drives `/help_cat main` autocomplete
  - `/help_cat main [category]` with `@autocomplete` for the category parameter
  - Delegation bridge: `help_prefix()` hands off to `Help._send_category_help()` when richer cog is loaded
  - Setup guard prevents double-registration on cog reload
- **About Guide (about.py — 258 lines):**
  - 9 curated pages covering every major system (Economy, Gambling, Simulators, Board/Card Games, RPG, Global Events, Pets/Social, Tips)
  - `AboutView` — requester-only checks, Prev/Next/Close buttons, auto-disables at start/end
  - DM delivery: `_send_dm()` opens DM channel, sends paginator, replies ephemeral in server
  - `discord.Forbidden` handler tells user to enable DMs
  - `L!about` + `/about`; both slash and prefix supported
- **Utilities (utilities.py — ~220 lines):**
  - `Paginator` view — requester-only ◀️/▶️/❌ pagination with author check
  - `check_reminders` background task (60s loop) — delivers DM reminder embeds, `_parse_ts()` for tz-safe comparison
  - `L!ping` — WebSocket heartbeat latency in ms
  - `L!setup` — multi-section quick-start guide embed (6 fields: Quick Start / Economy / Games / Simulators / Events / Admin)
  - `L!say` — echo command restricted to 3 hardcoded user IDs (`ALLOWED_SAY_USER_ID`)
  - `L!feedback` — posts to hardcoded channel, omits user ID for privacy
- **Server & User Info (serverinfo.py — 267 lines):**
  - `BADGE_MAP` — 11 Discord badges mapped from `public_flags` attribute names to `(emoji, label)` pairs
  - `VERIFICATION_LABELS` / `STATUS_ICONS` — display maps for guild security levels and presence status
  - `_build_serverinfo_embed()` — members (humans/bots/online/total), channels, boosts, security, guild features (up to 8 with emoji, `+N more`)
  - `_build_userinfo_embed()` — account created/joined dates, status+activity type detection (Spotify/Game/Streaming/Custom), badges, roles (sorted by position, cap 20), **Ludus Stats** from direct JSON reads (`economy.json` + `profiles.json` — no cog dependency)
  - Commands: `L!serverinfo` (aliases: server, si), `L!userinfo` (aliases: ui, whois, memberinfo), `/serverinfo`, `/userinfo [member]`; all `@guild_only()`
- **~7,500 words of documentation**

### Technical Reference
#### **[🔐 PART 12: Admin & Owner Commands](documentation/FULL_DOCUMENTATION_PART12.md)** — 4 cogs: `owner.py`, `blacklist.py`, `gamecontrol.py`, `bot_logger.py`
  - `owner.py` (1784 lines): Custom Role Manager subsystem (CUSTOM_ROLES_FILE, `load/save_custom_roles`, `apply_custom_roles_to_database` via `sys.modules`, `CustomRoleManagerView` 3-button UI, 2-step creation modal with 65+ valid powers, default faction emojis)
  - Economy management: `L!godmode` (max 999M coins + all items × 99), `L!setcoins`, `L!addcoins`, `L!removecoins`, `L!resetcoins`, `L!giveitem`
  - Bot status: `L!status` (playing/watching/listening/competing), `L!presence`, `L!nickname`
  - Server management: `L!serverlist` (paginated, with invite URLs), `L!restart` (os.execv graceful), `L!leave`, `L!purge`, `L!announce`, `L!dm`, `L!countset`, `L!stats` (7-section analytics), `L!update`
  - Fishing management: `L!fishing_tournament`, `L!give_fish/bait/rod/boat`, `L!unlock_area`
  - Fun/chaos: `L!raincoins`, `L!chaos` (100–10k random + 30% item), `L!spinlottery`, `L!spawn` (30s raid boss), `L!cursed` (Zalgo text), `L!hack` (animated), `L!roastme`, `L!vibecheck`
  - TCG: `L!give_tc`, `L!remove_tc` (legacy TCG cog → psyvrse_tcg fallback)
  - Debug: `L!eval`, `L!reload`, `L!reloadall`, `L!ownertest`; help: `L!ownerhelp` (`👑` / `owner` / `helpowner`)
  - `blacklist.py`: BLACKLIST_FILE via RENDER_DISK_PATH, atomic `_load()`/`_save()`, `_build_overview_embed()`, `BlacklistView` (5 buttons), `_InputModal` (4 actions: ban/unban user/server), enforcement via `on_command` + `on_interaction` listeners (fresh read per check)
  - `gamecontrol.py`: `L!stop` / `/stop` — checks 6 in-memory dicts across 4 cogs (CardGames, FishingAkinatorFun, MiniGames, BoardGames); dict deletion as complete cleanup
  - `bot_logger.py` (512 lines): `StreamInterceptor(io.TextIOBase)` mirrors stdout/stderr to Discord console channel; `BotLogger` with `log(title, desc, color, fields)` base method; 20+ error type mappings in `on_command_error`; helpers: `log_owner_command`, `log_admin_command`, `log_event_spawn/end`, `log_moderation`, `log_economy` (threshold 1000 coins); lifecycle: `on_ready`, `on_guild_join` (creates invite), `on_guild_remove`, shard events; global `sys.excepthook` patch via `cog_load/unload`
  - **~12,000 words of documentation**
#### **[📦 PART 13: Data Structures](documentation/FULL_DOCUMENTATION_PART13.md)** — 25+ JSON files fully documented with field-level schemas, types, defaults, and cross-file relationships

#### **[🛠️ UTILS REFERENCE: Shared Library](documentation/FULL_DOCUMENTATION_UTILS.md)** — Complete reference for all 6 files in `utils/` (~1,922 lines)
  - **`user_storage.py`** (421 lines): Per-user JSON files at `data/users/{user_id}.json`; full async API (`get_user`, `touch_user`, `record_activity`, `record_minigame_result`, `increment_stat`, `set_stat`, `record_game_state`); per-user `threading.Lock`; `_atomic_write` (.tmp → `os.replace`); backwards-compat stubs (`load_user`, `save_user`, etc.); auto back-fills new template keys
  - **`stat_hooks.py`** (145 lines): Fire-and-forget stat wrappers safe to call from sync code — `us_touch`, `us_inc`, `us_mg`, `us_set`; `us_set_bot` registers bot instance; `us_challenge` notifies `GameChallenges` cog with 10 event type strings (`game_win`, `coin_earn`, `trivia_correct`, `board_game_win`, etc.); silently drops calls if no running event loop
  - **`database.py`** (270 lines): Opt-in SQLite singleton (`DatabaseManager`) — `RENDER_DISK_PATH`-aware path; 4 tables (`users`, `stats`, `activity`, `game_states`); methods: `initialize_schema`, `upsert_user`, `update_stat`, `increment_stat`, `log_activity`, `save_game_state`, `get_user_data`; errors logged not re-raised; `get_user_data` returns dict mirroring `user_storage` format
  - **`embed_styles.py`** (380 lines): `Colors` (25+ hex constants + tier colours), `Emojis` (40+ named emoji), `EmbedBuilder` static factory — typed shortcuts: `success`, `error`, `warning`, `info`, `economy`, `game`, `leveling`, `music`; `leaderboard` (medals + top-10), `profile`, `progress_bar`, `format_number`, `tier_color`; module-level quick-access functions
  - **`performance.py`** (~60 lines): `ConfigCache` with 5-minute TTL; methods `get`, `invalidate`, `clear`; global `config_cache` singleton; caches parsed dict (not mtime-based)
  - **`card_visuals.py`** (646 lines): PIL card renderer; assets at `assets/cards/{deck}/{rank}_{suit}.png` (Polish filenames); `CARD_IMAGE_CACHE` dict; low-level: `get_font`, `parse_card`, `draw_card`, `draw_card_string`; high-level renderers returning `discord.File`: `create_hand_image`, `create_table_image`, `create_comparison_image`, `create_blackjack_image`, `create_war_image`, `create_poker_table_image` (full Hold'em table with player boxes, status colours, pot display)
  - **~12,000 words of documentation**
#### **[🔗 PART 14: Integration Guide](documentation/FULL_DOCUMENTATION_PART14.md)** — How all cogs connect: bot.py startup, inter-cog communication, shared state, and data-flow
  - `bot.py` (316 lines): startup sequence (`setup_hook` → `load_cogs` → slash sync), shared bot-level state (`bot.data_dir`, `bot.owner_ids`, `bot.active_games/lobbies/minigames/pending_rematches`), `BotCommandTree.interaction_check` (ServerConfig gate for all slash commands), `activity_worker` (BATCH_SIZE=50, BATCH_INTERVAL=2s batch-saves to `user_activity.json`)
  - `get_cog()` pattern: per-call lookup (never cached at `__init__`), graceful degradation on `None`, fallback chains (e.g. TCG cog → psyvrse_tcg module)
  - **Economy as central hub**: `add_coins`, `remove_coins`, `add_item`, `remove_item`, `get_balance`, `economy_data`, `shop_items`, `save_economy()` — called by 20+ cogs; sole authoritative source for PsyCoin balances
  - **Profile as display layer**: per-user metadata written by gambling/reputation/farming/marriage; read by serverinfo via direct JSON bypass (no cog dependency)
  - **BotLogger as passive observer**: `on_command_error` + `on_application_command_error` + `on_error` listeners catch all cog errors; active calls from globalevents + owner only
  - **ServerConfig as permission gate**: `BotCommandTree` checks `disabled_commands[]` per-guild before every slash command; mining/farming read per-guild channel config
  - **Blacklist as access gate**: fresh `_load()` on every `on_command` + `on_interaction`; gates all prefix and slash commands centrally
  - **GameControl as cleanup**: reaches 6 in-memory dicts across 4 cogs via `get_cog()`; dict deletion = complete cleanup
  - **GlobalEvents → Economy flow**: defeat_worldboss (tiers: 15k/7.5k/2.5k coins), war victory (10k/2k), hunt rewards; all via `add_coins(user_id, amount, source)`
  - **Achievements**: triggered by boardgames + social; purely reactive (Achievements cog owns grant logic + deduplication)
  - **GameStats**: recorded by chess_checkers + boardgames at every game conclusion path
  - **GlobalLeaderboard**: calculated on-demand from Economy + LeaderboardManager + GlobalEvents + MiniGames; opt-in consent required
  - **Farming ↔ FarmShop**: FarmShop bridges Farming inventory + Economy payments; neither maintains own coin state
  - **Mafia custom roles bridge**: `apply_custom_roles_to_database()` uses `sys.modules['cogs.mafia']` to inject into module-level `ROLES_DATABASE` directly
  - **utils/**: `user_storage` (per-user JSON, touched on every message), `database.py` (SQLite singleton, opt-in), `stat_hooks` (fire-and-forget recording), `card_visuals` (PIL card rendering for blackjack/poker), `embed_styles` (themed embed factory), `performance` (FileCache with mtime validation)
  - Data file sharing risks: `serverinfo.py` direct reads of `economy.json` + `profiles.json` may lag behind cog in-memory state; `custom_roles.json` injected out-of-band via `sys.modules`
  - Complete 18-section cross-cog dependency map
  - **~14,000 words of documentation**
#### **[🚀 PART 15: Deployment](documentation/FULL_DOCUMENTATION_PART15.md)** — All deployment methods, configuration, persistence, and operational procedures
  - Prerequisites: Python 3.11, FFmpeg (system), 12 Python packages (`discord.py ≥2.6.4`, `yt-dlp`, `PyNaCl`, `aiohttp`, `python-dotenv`, `Pillow`, `aiofiles`, `chess`, `googletrans`, `fuzzywuzzy`, `python-Levenshtein`, `psycopg2-binary`)
  - `config.json`: `prefix`, `owner_ids[]`, `emojiServerId[]`; `.env`: `LUDUS_TOKEN` (required), `RENDER_DISK_PATH` (optional)
  - Local dev: `python start.py` or `python bot.py`; `start.py` validates token then subprocess-launches `bot.py`; data → `./data/`
  - Docker: `python:3.11-slim` + FFmpeg install + `pip install --no-cache-dir`; `CMD ["python", "bot.py"]`; volume mount + `RENDER_DISK_PATH=/data` for persistence; docker-compose example
  - Render.com: `render.yaml` (`type: web`, `region: oregon`, `plan: free`, `buildCommand` installs pip + ffmpeg, `startCommand: python bot.py`); set `LUDUS_TOKEN` manually in dashboard; attach persistent disk at `/var/data` → `RENDER_DISK_PATH` auto-set
  - `start.sh`: pre-initializes 10 critical JSON files as `{}` before launching `bot.py`; use as `startCommand: bash start.sh` alternative
  - Data persistence: 20 files must persist (economy, inventory, profiles, fishing, mining, pets, farms, gambling_stats, leaderboard_stats, quests, achievements, blacklist, confession_config, server_configs, custom_roles, stories, lottery, counting, starboard, global_consent); atomic write pattern via `.tmp` + `os.replace()`
  - Discord setup: Message Content Intent (privileged, required), Server Members Intent (privileged, required), Presence Intent (optional); OAuth2 scope: `bot applications.commands`; 4 emoji server IDs for UNO/TCG asset hosting
  - Full startup sequence diagram (process launch → `setup_hook` → cog loading → `on_ready` → slash sync)
  - Operations: `L!reload <cog>` / `L!reloadall` for hot-reload; `L!restart` uses `os.execv` → `os._exit(0)` fallback; `migrate_users.py` for schema migrations; backup procedures for Render disk / Docker volumes
  - Troubleshooting: offline bot, slash commands not appearing, cog load failures, data not persisting, Opus missing, fuzzywuzzy warnings
  - **~12,000 words of documentation**

#### **[🤖 PART 16: Bot Intelligence & Personality System](documentation/FULL_DOCUMENTATION_PART16.md)** — Full analysis of `personality.py` (1,504 lines) and `intelligence.py.disabled` (182 lines — legacy/disabled)
  - `LudusPersonality` cog: 5 personality profiles (default, snappy, jester, fps, peaceful), 30+ keyword triggers, custom emoji map (28 entries)
  - 3-tier content safety system: HATE_WORDS / SEXUAL_WORDS / HARASS_WORDS with leet-speak normalization and safe-context whitelist
  - Knowledge base Q&A engine: 5-tier lookup chain (favorites → user_taught → faq → identity → general_knowledge), fuzzy matching via `difflib.get_close_matches` (cutoff 0.78)
  - Self-teaching: when unanswered question detected, starts 60-second learning conversation; stores answers in `user_taught` with `asyncio.Lock`
  - on_message pipeline: Wordle answer fetching (NYT API), AST-safe math evaluator, yes/no/or question handler (deterministic hash-based answers), "How are you Ludus?" status-aware replies
  - Rare event system: 1% per-command chance, 5 event types (Lucky Day, Mystical Shroom, Ludus Blessing, Cosmic Key, Cloud Nine) — economy integration pending
  - Slash `/personality` + prefix `L!setpersonalitychannels`, `L!personality`, `L!vibe`, `L!easter`, `L!mood`
  - `Intelligence` cog (disabled): flat knowledge base, `googletrans` multilingual support, `fuzzywuzzy` matching — superseded by `LudusPersonality`
  - **`knowledge.json` deep-dive** (1,263 lines): 5 sections — `identity` (~90 favorites, full persona), `faq` (~150+ Q&A pairs: elements, world capitals, literature, Discord usage, capabilities), `general_knowledge` (formulas, lists, physics/chemistry/biology), `user_taught` (runtime-learned, starts empty, async-locked writes), `conversations` (greeting pools); hot-reload via mtime check; JSON syntax bug identified on line ~128
  - **Undocumented cogs audit**: `simulations.py`, `onboarding.py`, `perimeter_explicit.py`, `professional_info.py` identified as missing from Parts 1–15
  - **~8,000 words of documentation**

---

## 🏗️ PROJECT ARCHITECTURE OVERVIEW

### File Structure (90 Files)

```
Ludus-Bot/ (50,000+ lines total)
│
├── 📄 Core Files (4 files, ~1,500 lines)
│   ├── bot.py (315 lines) - Main bot entry point
│   ├── start.py (50 lines) - Production launcher  
│   ├── constants.py (100 lines) - Global constants
│   └── config.json - Bot configuration
│
├── 🎯 Cogs/ (70+ files, 45,000+ lines)
│   │
│   ├── 💰 Economy & Core (8 files, ~5,000 lines)
│   │   ├── economy.py (1,206 lines) - Currency system
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
│   │   ├── mining.py (4,053 lines) - **2nd BIGGEST**
│   │   ├── zoo.py (800 lines) - Animal collection
│   │   └── farmshop.py (300 lines) - Farming marketplace
│   │
│   ├── 🎰 Gambling & Casino (5 files, ~7,200 lines)
│   │   ├── gambling.py (1,404 lines) - Slots, Roulette, Higher/Lower, Dice, Crash, Mines, Coinflip
│   │   ├── blackjack.py (2,001 lines) - Blackjack: Fast mode (solo) + Long mode (multiplayer lobby)
│   │   ├── poker.py (2,824 lines) - Texas Hold'em full implementation
│   │   ├── lottery.py (324 lines) - Lottery system
│   │   └── heist.py (621 lines) - Bank heist co-op
│   │
│   ├── 🎮 Card & Board Games (6 files, ~5,000 lines)
│   │   ├── cardgames.py (900 lines) - Go Fish, War, Blackjack (classic prefix commands)
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
│   ├── 🐾 Social & Collection (7 files, ~5,100 lines)
│   │   ├── pets.py (741 lines) - 16 pets, 14 perk types, inter-cog multiplier API
│   │   ├── profile.py (911 lines) - 4-page Components V2 profile, 60+ stats
│   │   ├── trading.py (1,289 lines) - P2P trades, gifts, sell, block system
│   │   ├── social.py (998 lines) - Roasts, WYR, story maker, GIF reactions
│   │   ├── marriage.py (456 lines) - Proposals, shared bank, couple quests
│   │   ├── reputation.py (396 lines) - Rep tiers, price/reward modifiers
│   │   └── psyvrse_tcg.py (~600 lines) - Trading card game
│   │
│   ├── 🔧 Utility & Fun (8 files, ~3,000 lines)
│   │   ├── funcommands.py (600 lines) - Fun commands
│   │   ├── fun.py (500 lines) - Entertainment
│   │   ├── utilities.py (400 lines) - Utility tools
│   │   ├── meme.py (300 lines) - Meme generator
│   │   ├── quotes.py (200 lines) - Quote system
│   │   ├── akinator_enhanced.py (600 lines) - Akinator game
│   │   ├── personality.py (1,504 lines) - Bot personality & AI chat system (LudusPersonality)
│   │   ├── intelligence.py.disabled (182 lines) - Legacy AI cog (disabled, superseded by personality.py)
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
├── 📦 Utils/ (6 files, ~1,922 lines)
│   ├── user_storage.py (421 lines) - Per-user JSON storage (async + thread-safe)
│   ├── database.py     (270 lines) - SQLite singleton (opt-in alternative backend)
│   ├── embed_styles.py (380 lines) - Colors / Emojis / EmbedBuilder factory
│   ├── card_visuals.py (646 lines) - PIL card game image renderer
│   ├── stat_hooks.py   (145 lines) - Fire-and-forget stat recording helpers
│   └── performance.py  ( ~60 lines) - 5-minute JSON config cache
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

Last Updated: 05.03.2026
Total Documentation Size: 153,000+ words across 16 parts + Utils Reference
Documentation Status: ✅ All 16 Parts + Utils Reference Complete
The documentation was written by wilczek80.