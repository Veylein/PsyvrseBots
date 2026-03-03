# 🐾 PART 9: Social Features

> **Documentation for:** pets.py, marriage.py, reputation.py, profile.py, social.py, trading.py  
> **Total Lines:** ~5,021 | **Files:** 6 | **Date:** March 2026

---

## 📋 TABLE OF CONTENTS

1. [Overview & File Summary](#1-overview--file-summary)
2. [Pets System (pets.py — 741 lines)](#2-pets-system-cogspetspy--741-lines)
3. [Marriage System (marriage.py — 456 lines)](#3-marriage-system-cogsmarriagepy--456-lines)
4. [Reputation System (reputation.py — 396 lines)](#4-reputation-system-cogsreputationpy--396-lines)
5. [Profile System (profile.py — 911 lines)](#5-profile-system-cogsprofilepy--911-lines)
6. [Social System (social.py — 998 lines)](#6-social-system-cogssocialpy--998-lines)
7. [Action Commands (actions.py — 311 lines)](#7-action-commands-cogsactionspy--311-lines)
8. [Trading System (trading.py — 1,289 lines)](#8-trading-system-cogstradingpy--1289-lines)
9. [Cross-Cog Integration Map](#9-cross-cog-integration-map)
10. [Commands Reference](#10-commands-reference)
11. [Part 9 Summary](#11-part-9-summary)

---

## 1. Overview & File Summary

Part 9 covers all player-to-player social and relationship systems. These cogs blur together — pets feed into profiles, profiles pull from pets, marriage integrates with economy, reputation adjusts rewards. The entire Part 9 is a web of cross-cog hooks.

| File | Lines | Role |
|------|-------|------|
| `cogs/pets.py` | 740 | Virtual pet companions with gameplay perks across all activity systems |
| `cogs/marriage.py` | 783 | Marriage proposals (buttons), shared bank (modal buttons), 15 couple quests, divorce |
| `cogs/reputation.py` | 303 | Community rep system: price/reward modifiers, tier ladder |
| `cogs/profile.py` | 910 | Comprehensive 4-page user profile (Components V2), stat aggregation |
| `cogs/social.py` | 997 | Roasts, compliments, WYR, story maker, GIF reactions + action commands (slap/punch/etc.) |
| `cogs/trading.py` | 1,288 | Full P2P trading, anonymous gifts, sell system, block lists |
| **TOTAL** | **~5,021** | |

**Data files used:**
- `data/pets.json` — all pet ownership records + `__adoptions__` counter
- `data/profiles.json` — user profiles (60+ stats per user)
- `data/marriages.json` — marriage records (migrated from cogs/ on first run)
- `data/reputation.json` — reputation records (migrated from cogs/ on first run)
- `data/trade_history.json`, `data/blocks.json`, `data/gift_settings.json`

---

## 2. Pets System (`cogs/pets.py` — 741 lines)

### Overview

A companion pet system with **16 unique pets** across 5 rarity tiers. Each pet provides passive perks that boost performance in fishing, mining, farming, gambling, daily rewards, and economy. The first pet is free; all subsequent adoptions cost 10,000 PsyCoins.

### Pet Database

16 pets with weighted rarity:

| Rarity | Weight | Chance | Pets |
|--------|--------|--------|------|
| Common | 55 | 55% | Tiger, Dog, Cat, Hamster, Snake, Horse |
| Uncommon | 28 | 28% | Panda, Dragon, Pig, Turtle |
| Rare | 12 | 12% | Fox, Axolotl, Wolf |
| Epic | 4 | 4% | Owl, Elder Dragon |
| Legendary | 1 | 1% | Unicorn |

**Full pet catalogue with perks:**

| Pet | Rarity | Perk Label | Key Perks |
|-----|--------|------------|-----------|
| 🐯 Tiger | Common | Gambler's Fury | +15% gambling winnings · +10% mining speed |
| 🐶 Dog | Common | Miner's Companion | +20% mining XP · +15% rare ore · +10% farm yield |
| 🐱 Cat | Common | Fisher's Luck | +20% fishing catch · +15% rare fish chance |
| 🐹 Hamster | Common | Coin Hoarder | +12% all coins · +5% fishing · +8% farm yield |
| 🐍 Snake | Common | Risk Reducer | -20% gambling losses · +15% daily bonus |
| 🐴 Horse | Common | Harvest Champion | +30% farm yield · +40% auto-tend · +15% mining speed |
| 🐼 Panda | Uncommon | Nature's Bounty | +25% farm yield · +20% XP · +10% coins |
| 🐉 Dragon | Uncommon | Economy Overlord | +20% all coins · +5% jackpot · +10% rare ore |
| 🐷 Pig | Uncommon | Lucky Snout | +15% gambling winnings · -15% losses · +10% daily |
| 🐢 Turtle | Uncommon | Steady Grinder | +25% XP · +15% daily bonus · +10% all coins |
| 🦊 Fox | Rare | Trickster's Edge | +20% gambling · +15% fishing · +12% coins |
| 🦎 Axolotl | Rare | Aquatic Master | +30% fishing · +25% rare fish · +20% sell price |
| 🐺 Wolf | Rare | Pack Hunter | +25% gambling · +10% jackpot · +15% mining speed |
| 🦉 Owl | Epic | Scholar's Blessing | +35% XP · +25% daily bonus · +15% coins |
| 🐲 Elder Dragon | Epic | Ancient Power | +30% coins · +15% jackpot · +20% rare ore |
| 🦄 Unicorn | Legendary | Fortune's Chosen | +25% ALL gains (coins, XP, gambling, fishing, mining, farm, daily) |

### Perk System (14 Perk Keys)

```python
_AVAILABLE_PETS perk keys:
  gambling_mult       # multiplier on winnings        (1.15 = +15%)
  gambling_loss_red   # fraction of losses reduced    (0.20 = lose 20% less)
  gambling_jackpot    # extra jackpot/bonus chance     (0.05 = +5%)
  fishing_mult        # fishing catch-rate multiplier
  fishing_rare        # extra rare-fish probability (additive)
  fishing_value       # fish sell-price multiplier
  mining_speed        # mining tick-speed multiplier
  mining_rare         # extra rare-ore drop chance
  mining_xp           # mining XP multiplier
  farm_yield          # harvest yield multiplier
  farm_auto_tend      # chance to auto-tend on harvest
  coins_mult          # flat coin-gain multiplier on ALL activities
  daily_bonus         # extra % on daily reward
  xp_mult             # global XP multiplier
```

### UI — PetDashboardView (Components V2)

```python
class PetDashboardView(discord.ui.LayoutView):
    """180-second timeout; interaction_check only allows the owner"""
    
    def _build(self):
        """Calls _render_dashboard(pet) if pet exists, else _render_no_pet()"""
    
    def _render_dashboard(self, pet):
        """Container with TextDisplay(status text) + Separator + ActionRow(feed/play/walk/release)"""
        # Buttons auto-disabled when stats at limits:
        # feed_b.disabled if hunger >= 90
        # play_b.disabled / walk_b.disabled if energy < 20
    
    def _render_no_pet(self):
        """Shows adopt UI:
           - FREE on first adoption (adopt_count == 0)
           - 10,000 coins for all subsequent adoptions
        """
```

**Status text components:**
```
## 🐯 [name]
-# ⬜ Common · Aggressive · Adopted 2026-01-15

🍖 Hunger    ████████░░  80/100
😊 Happiness ██████░░░░  60/100
⚡ Energy    ████░░░░░░  40/100

🎭 Mood: 😊 Happy
🌾 Farm: Can trample and destroy crops

✨ Gambler's Fury
-# +15% gambling winnings · +10% mining speed
```

**Mood ladder:**
- 80+ → 😄 Ecstatic
- 60–79 → 😊 Happy
- 40–59 → 😐 Okay
- 20–39 → 😟 Unhappy
- 0–19 → 😢 Miserable

**Farm impact behaviors:**

| Behavior | Description |
|----------|-------------|
| trample | Can trample and destroy crops |
| burn | Might accidentally burn crops |
| eat | Will eat crops when hungry |
| dig | Might dig up planted seeds |
| hoard | Steals harvested crops |
| none | Doesn't interact with farms |

Farm damage only triggers **when pet is hungry (hunger < 40)**. Probability scales: `(40 - hunger) * 2`%.

### Action Callbacks

| Button | Hunger Δ | Happiness Δ | Energy Δ | Coin Reward |
|--------|-----------|-------------|----------|-------------|
| 🍖 Feed | +30 (max 100) | +10 | — | +5 |
| 🎾 Play | -10 | +25 | -20 (min 0) | +15 |
| 🚶 Walk | -15 | +15 | -15 (min 0) | +10 |
| 💔 Release | — | — | — | — (confirmation required) |

### Inter-Cog API Methods

The `Pets` cog exposes a full accessor API used by other cogs:

```python
# Called by fishing.py
pets.get_fishing_multiplier(user_id)     # → float
pets.get_fishing_rare_bonus(user_id)     # → float (additive)
pets.get_fishing_value_multiplier(user_id)  # → float

# Called by farming.py
pets.get_farm_yield_multiplier(user_id)  # → float
pets.get_auto_tend_chance(user_id)       # → float
pets.check_pet_farm_interaction(user_id) # → {"interaction": bool, "type": str, ...}

# Called by mining.py
pets.get_mining_speed_multiplier(user_id)  # → float
pets.get_mining_xp_multiplier(user_id)    # → float
pets.get_mining_rare_bonus(user_id)       # → float

# Called by gambling.py / economy.py
pets.get_gambling_multiplier(user_id)      # → float
pets.get_gambling_loss_reduction(user_id)  # → float
pets.get_gambling_jackpot_bonus(user_id)   # → float
pets.get_coins_multiplier(user_id)         # → float
pets.get_xp_multiplier(user_id)            # → float
pets.get_daily_bonus(user_id)              # → float
```

### Adoption Tracking

```python
# pets.json structure
{
  "__adoptions__": {"123456789": 2},  # how many total each user has adopted
  "123456789": {                      # current active pet
    "emoji": "🐯",
    "type": "Tiger",
    "name": "dwilc's Tiger",
    "hunger": 80,
    "happiness": 60,
    "energy": 50,
    "adopted": "2026-01-15T12:00:00+00:00",
    "behavior": "aggressive",
    "farm_impact": "trample"
  }
}
```

Legacy fallback: if users had a pet before `__adoptions__` tracking was added, `get_adopt_count()` returns 1 (so their next adoption costs 10k).

### Leaderboard Integration

On successful adoption, the cog increments `leaderboard_manager.increment_stat(guild_id, "pet_adoptions", 1)` and calls `profile_manager.increment_stat(user_id, "pets_owned")`.

### Command

| Command | Type | Description |
|---------|------|-------------|
| `/pet` | Slash | Open pet dashboard — adopt, feed, play, walk |

---

## 3. Marriage System (`cogs/marriage.py` — 783 lines)

### Overview

A relationship system allowing two users to get married, share a bank account, and complete couple quests together. Proposals and the shared bank use interactive **Discord UI buttons and modals** — no typing commands to accept/decline.

### Marriage Flow

```
1. L!marry @user
   └── Author pays 10,000 coins
   └── Bot pings partner + sends embed with Accept 💍 / Decline 💔 buttons
   └── Only the target partner can click (5-minute timeout)
   └── On accept: marriage processed immediately via button callback
   └── On timeout: proposal auto-expires, embed updated

2. L!divorce
   └── Cost: 5,000 PsyCoins
   └── Shared bank balance is LOST
   └── Both users' marriage data reset
   └── divorce counter incremented on both (synced to profiles.json)
```

### Data Structure

```python
# data/marriages.json
{
  "123456789": {
    "spouse": 987654321,
    "married_since": "2026-01-15T12:00:00+00:00",
    "shared_bank": 5000,
    "completed_quests": ["date_night"],
    "love_points": 10,
    "divorces": 0
  }
}
```

### Shared Bank

Both spouses share a single `shared_bank` value. `L!bank` sends an embed with **Deposit 💰** and **Withdraw 💸** buttons — clicking either opens a Discord modal asking for the amount. Both partners can use the buttons (guarded by `interaction_check`). Depositing/withdrawing updates both records simultaneously.

```python
# Modal submit → remove_coins / add_coins
economy_cog.remove_coins(user_id, amount)      # deposit
economy_cog.add_coins(user_id, amount, ...)    # withdraw
marriage["shared_bank"] += amount              # mirrors on both sides
spouse_marriage["shared_bank"] += amount
```

### Couple Quests

15 quests across 3 tiers with weekly reset:

| Tier | Quests | Rewards |
|------|--------|---------|
| ⭐ Easy (5) | Date Night, Sweet Words, Heads or Tails, Daily Duo, Fishing Date | 1,000–3,000 coins · 3–6 ❤️ |
| ⭐⭐ Medium (5) | Gift Exchange, Fortune Hunters, Mining Duo, Harvest Season, Trivia Night | 4,000–7,500 coins · 8–12 ❤️ |
| ⭐⭐⭐ Hard (5) | Adventure Together, Heist Partners, Card Champions, Wealthy Couple, One Month Strong | 10,000–25,000 coins · 20–50 ❤️ |

`L!couplequests` sends 3 separate embeds (one per tier) with completed/total counter.

### Reputation Tier Effects

The `_parse_ts()` helper handles both naive (old data) and timezone-aware ISO timestamps for `married_since` — this prevents errors when computing `days_married` for users married before the tz-aware migration.

### Commands

| Command | Description |
|---------|-------------|
| `L!marry @user` | Propose marriage — pings partner, sends Accept 💍/Decline 💔 buttons (costs 10,000 coins) |
| `L!marry accept/decline` | Fallback prefix commands (buttons preferred) |
| `L!divorce` | Divorce your spouse (costs 5,000 coins) |
| `L!spouse [@user]` | View marriage info (spouse, days married, love points, shared bank) |
| `L!bank` | View shared bank + Deposit 💰 / Withdraw 💸 modal buttons |
| `L!couplequests` | View 15 couple quests in 3 tier embeds |

---

## 4. Reputation System (`cogs/reputation.py` — 303 lines)

### Overview

A community-driven reputation ladder. Users give ±1 rep to each other (24hr cooldown per pair). Reputation affects shop prices and reward amounts across the bot.

### Reputation Tiers

| Total Rep | Tier | Color |
|-----------|------|-------|
| 100+ | 🌟 Legendary | Gold |
| 50–99 | ⭐ Excellent | Purple |
| 25–49 | 💎 Great | Blue |
| 10–24 | ✨ Good | Green |
| 0–9 | 👤 Neutral | Light Grey |
| -10 to -1 | ⚠️ Questionable | Orange |
| -25 to -11 | ❌ Bad | Red |
| -100 to -26 | ☠️ Notorious | Dark Red |

### Gameplay Effects

```python
def get_price_modifier(self, total_rep):
    """Shop price multiplier. -20% at 100 rep, +20% at -100 rep."""
    modifier = 1.0 - (total_rep / 500.0)
    return max(0.8, min(1.2, modifier))  # Capped to 80%–120%

def get_reward_modifier(self, total_rep):
    """Reward multiplier. +10% at 100 rep, -10% at -100 rep."""
    modifier = 1.0 + (total_rep / 1000.0)
    return max(0.9, min(1.1, modifier))  # Capped to 90%–110%
```

| Rep Score | Shop Prices | Rewards |
|-----------|-------------|---------|
| 100 | -20% (pay 80%) | +10% |
| 50 | -10% | +5% |
| 0 | Normal | Normal |
| -50 | +10% | -5% |
| -100 | +20% (pay 120%) | -10% |

### Cooldown Logic

```python
def can_give_rep(self, giver_id, receiver_id):
    """24-hour cooldown per unique giver→receiver pair."""
    cooldown_key = f"{giver_id}_{receiver_id}"
    # Returns: (True, None) if allowed, or (False, "Xh Ym") if on cooldown
```

Cooldowns are stored in `self.rep_cooldowns` (in-memory dict), **not in the JSON file**. This means cooldowns reset on bot restart.

`rep_give` and `rep_remove` both call `profile_cog.increment_stat()` to sync `reputation_given` / `reputation_received` into `profiles.json` — this powers the server leaderboard and the profile Social page.

### Data Structure

```python
# data/reputation.json
{
  "123456789": {
    "total_rep": 15,
    "positive_rep": 18,
    "negative_rep": 3,
    "given_rep": {},           # unused (legacy field)
    "rep_history": [           # last N events
      {
        "type": "positive",    # or "negative"
        "giver_id": 987654321,
        "giver_name": "alice",
        "reason": "Very helpful!",
        "timestamp": "2026-01-15T12:00:00+00:00"
      }
    ]
  }
}
```

### Commands

| Command | Description |
|---------|-------------|
| `L!rep [@user]` | View reputation (tier, score, +/- breakdown, recent history, effects) |
| `L!rep give @user [reason]` | Give +1 rep (aliases: `add`, `+`) |
| `L!rep remove @user [reason]` | Give -1 rep (aliases: `take`, `-`) |
| `L!rep history [@user]` | View recent rep events (last 5 shown) |
| `/leaderboard` | Server & global reputation rankings (via leaderboard cog) |

---

## 5. Profile System (`cogs/profile.py` — 910 lines)

### Overview

A comprehensive profile system tracking **60+ statistics** per user. The profile is rendered using **Components V2 LayoutView** with 4 browsable pages. Stats are aggregated live from multiple JSON files using `ProfileManager.get_user_stats()`.

### ProfileManager (Lines 19–400)

The `ProfileManager` class handles all data operations:

```python
class ProfileManager:
    def __init__(self, data_dir):
        self.profiles_file      = os.path.join(data_dir, "profiles.json")
        self.fishing_data_file  = os.path.join(data_dir, "fishing_data.json")
        self.gambling_stats_file= os.path.join(data_dir, "gambling_stats.json")
        # Also loads economy.json and data/users/{id}.json at runtime
```

**Key methods:**

| Method | Purpose |
|--------|---------|
| `get_profile(user_id)` | Get or create profile, backfill missing keys from default |
| `get_user_stats(user_id)` | **Aggregate stats** from profiles.json + users/{id}.json + economy.json + fishing_data.json + gambling_stats.json |
| `increment_stat(user_id, stat, amount=1)` | Increment any stat (creates key if missing) |
| `record_game_played(user_id, game, with_users)` | Track most-played games and most-played-with users |
| `add_badge(user_id, badge_id)` | Add badge if not already owned |
| `use_energy(user_id, amount)` | Deduct energy, return False if insufficient |
| `restore_energy(user_id, amount)` | Restore up to max_energy |

**Stat aggregation priority in `get_user_stats()`:**
1. `data/users/{id}.json` stats (wins, per-game granular data — highest priority for numeric stats)
2. `data/economy.json` (balance, total_earned, total_spent, fish_coins, mine_coins, farm_coins, daily streak)
3. `data/fishing_data.json` (fish_caught, rare/legendary counts, biggest weight)
4. `data/gambling_stats.json` (total_games, wins, losses, wagered, biggest win/loss)
5. `data/profiles.json` base data (farming stats, badges, most_played_games, etc.)

### ProfileView — 4 Pages (Components V2)

```python
class ProfileView(discord.ui.LayoutView):
    """60-second timeout. interaction_check only allows viewer (not profile target)."""
    pages = ["overview", "gaming", "economy", "social"]
```

**Page selector:** `discord.ui.Select` with 4 options (Overview/Gaming/Economy/Social) — rebuilds entire Container on change.

**Card deck selector:** if viewer is viewing their own profile and owns cosmetic decks, a secondary `Select` appears above the page selector for equipping decks directly from the profile.

#### Page: Overview

```
# 👑 [username]'s Profile

**Level X** • Y XP
⚡ **Energy:** ██████████ 100/100
🐾 **Pet:** 🐯 username's Tiger — ⬜ Common    ← if pet owned

## 🏆 Top Activities
🎲 Gambling: **52** games • 48.1% winrate
🎮 Minigames: **300** played • **210** won
💬 Social: **20** compliments • **5** events

*Use dropdown to see detailed stats*
```

#### Page: Gaming

Shows W/L/D and winrate % for:
- Minigames (Wordle correct/total, Trivia, Riddles)
- Board Games (Tic-Tac-Toe, Connect4, Hangman, Checkers, Chess)
- Card Games (UNO, Blackjack with draws, War)
- Psyvrse TCG (battles W/L, ranked, tournaments, collection size)
- Fishing & Combat (fish caught by rarity, biggest weight, PvP, bosses, dungeons)

#### Page: Economy

Shows:
- Current PsyCoin balance
- Secondary currencies (FishCoins, MineCoins, FarmCoins)
- Total earned / spent / net profit
- Biggest win / biggest loss
- Gambling section (games, win rate, wagered, won, ROI %)
- Business ownership status, sales, revenue
- Quest streak, quests completed, achievements unlocked

#### Page: Social

Shows:
- Compliments given/received, roasts given, highfives, stories
- Current pet (detailed block with hunger/happiness/perk)
- Pet care stats (fed/played/walked counts)
- Events participated/won, seasonal points
- Commands used, messages sent, last_active timestamp
- Music stats (songs played, listen time, favorite genre)

### Commands

| Command | Type | Description |
|---------|------|-------------|
| `L!profile [@user]` | Prefix | View profile (aliases: `L!p`, `L!me`) |
| `/profile [user]` | Slash | View profile (Components V2 panel) |
| `L!energy` | Prefix | Quick energy status check with progress bar |

### Profile JSON Template

Profiles are built from `data/profile_template.json`. If the template file fails to load, `_create_default_profile_legacy()` is used as a hardcoded fallback (60+ fields covering all stat categories). Fields are backfilled on-demand: `get_profile()` always merges missing keys from the default template.

---

## 6. Social System (`cogs/social.py` — 997 lines)

### Overview

Social interaction commands: random roasts & compliments with coin rewards, Would You Rather game, collaborative story maker, GIF reaction slash commands, prefix action GIF commands (slap/punch/kick/etc.), and various fun utility commands.

### Roasts & Compliments

```python
self.roasts     = [...]  # 59 internet/tech-themed roasts
self.compliments = [...] # 54 positive messages
```

**Economy integration:**
- `L!roast @user` → +10 coins to author; +stat `roasts_given` / `roasts_received`
- `L!compliment @user` → +15 coins to author, +10 coins to target; +stat `compliments_given` / `compliments_received`
- Achievement hooks: `roaster` (50 roasts), `savage` (200), `friendly` (10 compliments), `kind_soul` (100), `angel` (500)

### Would You Rather (WYR)

```python
# Stored in wyr_questions.json
# Default: 10 built-in questions
# Community-sourced: users add with L!wouldyourather add

@wyr.command("play")    # Random question + 10 coins reward
@wyr.command("add")     # Add question (auto-prepends "Would you rather" if missing) + 25 coins
@wyr.command("list")    # Shows first 10 questions
```

### Story Maker

Collaborative channel storytelling via `on_message`:

```
1. L!story start   → registers channel in story_data
2. Members send 1-3 word messages (non-command)
   → bot appends to story["words"]
   → tracks per-user word count in story["contributors"]
   → reacts 📖 to each contribution
3. L!story read    → shows current story (up to 4,000 characters)
4. L!story end     → awards 5 coins per contributed word to each contributor
                   → saves final story
                   → removes channel from active stories
```

Limitation: only one active story per channel. Non-command messages from all users are captured — commands (starting with `L!`, `/`, `!`) are ignored.

### GIF Reaction Slash Commands

All use **nokos.best API v2** (`https://nekos.best/api/v2/{action}`):

| Command | Action | Description |
|---------|--------|-------------|
| `/hug @user` | `hug` | Animated hug GIF |
| `/kiss @user` | `kiss` | Animated kiss (self blocked) |
| `/slap @user` | `slap` | Animated slap (self blocked) |
| `/petpet @user` | — | Petpet GIF via some-random-api.com/premium/petpet |
| `/ship user1 user2` | `kiss`/`cuddle` | Ship calculator + GIF |

**Petpet** fetches user avatar → passes to `some-random-api.com` endpoint → returns animated GIF bytes → uploaded as `discord.File`. Falls back to static thumbnail if API unavailable.

**`/ship` algorithm:**
```python
score = (user1.id + user2.id) % 101   # Deterministic — same pair always same score
ship_name = name1[:mid] + name2[-(len(name2) - max(1, len(name2)//2)):]
```

Ship tiers:
| Score | Tier | Color |
|-------|------|-------|
| 90–100 | 💖 SOULMATES | Pink |
| 75–89 | ❤️ Perfect Match | Red |
| 60–74 | 💛 Great Together | Gold |
| 45–59 | 💙 Could Work Out | Blurple |
| 25–44 | 🤍 Just Friends | Grey |
| 0–24 | 💔 Total Disaster | Dark Grey |

**HTTP session management:** `aiohttp.ClientSession` is lazily created in `_get_session()`, reused across all GIF requests, and closed in `cog_unload()` to avoid unclosed connector warnings.

### Other Social Commands

| Command | Description |
|---------|-------------|
| `L!pray [@user]` | Send prayers (+10–50 random coins to target) |
| `L!curse @user` | Playful curse (10% backfire chance: author loses 5–20 coins) |
| `L!avatar [@user]` | Display avatar with download links (PNG/JPG/WebP/GIF) |
| `L!socialprofile [@user]` | Cross-cog profile: coins, fishing, pets, zoo, gambling, farming (aliases: `sprof`, `sp`) |
| `L!shipold user1 user2` | Legacy prefix ship command |

### Commands

| Command | Type | Description |
|---------|------|-------------|
| `L!roast [@user]` | Prefix | Random roast + 10 coins |
| `L!compliment [@user]` | Prefix | Random compliment + coins for both |
| `L!wouldyourather play` | Prefix | Random WYR question |
| `L!wouldyourather add <question>` | Prefix | Add question + 25 coins |
| `L!story start/read/end` | Prefix | Collaborative story |
| `/hug @user` | Slash | Hug with GIF |
| `/kiss @user` | Slash | Kiss with GIF |
| `/slap @user` | Slash | Slap with GIF |
| `/petpet @user` | Slash | Petpet animated GIF |
| `/ship user1 [user2]` | Slash | Ship compatibility calculator |
| `L!pray [@user]` | Prefix | Prayer with coin blessing |
| `L!curse @user` | Prefix | Playful curse (backfire chance) |
| `L!avatar [@user]` | Prefix | Display avatar + download links |

---

## 7. Action Commands (in `cogs/social.py`)

### Overview

Prefix GIF action commands are part of `social.py` (not a separate file). 7 action types, each with multiple GIF URLs and message templates.

### Action Types

| Command | Emoji | Self-Action Response |
|---------|-------|---------------------|
| `L!slap @user` | 🤚 | "Here, have a hug instead! 🤗" |
| `L!punch @user` | 👊 | "Maybe try a workout instead? 💪" |
| `L!kick @user` | 🦵 | "That's some impressive flexibility! 🤸" |
| `L!kiss @user` | 💋 | "Self-love is important! 💖" |
| `L!dance @user` | 💃 | "Dancing solo! You've got the moves!" |
| `L!stab @user` | 🔪 | "Someone get this person some help!" |
| `L!shoot @user` | 🔫 | "That's not very wise..." |

**Message template system:**
```python
message = random.choice(self.messages["slap"]).format(
    author=ctx.author.mention,
    target=target.mention
)
gif = random.choice(self.gifs["slap"])
await ctx.send(f"{message}\n{gif}")
# Discord auto-embeds the GIF link — no explicit embed object needed
```

**Slap GIFs** use Tenor share links wrapped in `[⠀](url)` — zero-width space creates invisible hyperlink that Discord previews as the GIF. Kiss/dance/stab/shoot use standard Imgur `.gif` URLs.

**Validation:** Target is required (`None` check) and self-targeting is caught. No economy integration — pure entertainment commands.

---

## 8. Trading System (`cogs/trading.py` — 1,288 lines)

### Overview

A full P2P trading system with interactive trade sessions, item selling at 85–90% value, anonymous gift system, and block lists. The largest file in Part 9.

### TradeSession Class

```python
class TradeSession:
    """5-minute timeout. Stored in cog.active_trades dict."""
    user1, user2      # discord.Member
    channel           # discord.TextChannel
    user1_coins       # int
    user1_items       # dict: {item_id: qty}
    user2_coins       # int
    user2_items       # dict: {item_id: qty}
    user1_confirmed   # bool
    user2_confirmed   # bool
    active            # bool (set False on complete/cancel)
```

**Confirmation reset:** Any `add_offer()` or `remove_offer()` call resets both `confirmed` flags — preventing bait-and-switch.

### Trade Flow

```
1. L!trade @user
   └── Checks: no active trade, not blocked by each other
   └── Bot posts embed with ✅/❌ reactions
   └── 60s wait_for reaction from target
   └── If accepted: TradeSession created, embed posted with instructions

2. L!trade add coins 1000   /   L!trade add item luck_charm 2
   └── Validates balance / inventory ownership
   └── Adds to offer, resets confirmations, reposts embed

3. L!trade remove coins 500  /  L!trade remove item item_id
   └── Decrements offer, resets confirmations

4. L!tradeconfirm
   └── Sets user's confirmed flag
   └── If both confirmed → execute_trade()

5. L!tradecancel
   └── Marks active=False, removes from active_trades
```

### Trade Execution (`execute_trade()`)

Pre-flight validation before any transfer:
1. Check user1 still has `user1_coins`
2. Check user2 still has `user2_coins`
3. Check user1 has all `user1_items` in inventory
4. Check user2 has all `user2_items` in inventory

If any check fails: cancel trade, return error.

Execution order:
```python
# Coins
economy_cog.remove_coins(user1.id, trade.user1_coins)
economy_cog.add_coins(user2.id, trade.user1_coins)
# (and vice versa for user2's coins)

# Items
economy_cog.remove_item(user1.id, item_id, qty)
economy_cog.add_item(user2.id, item_id, qty)
# (and vice versa for user2's items)

# Log to trade_history.json
# Record state in data/users/{id}.json via _record_trade_state()
```

### Sell System (`L!sell`)

Sell price: **85–90% of base value** (random per transaction).

| Item Category | Source | Base Value |
|---------------|--------|------------|
| Shop items | `item_sell_values` dict or `economy_cog.shop_items[item]['price']` | Varies |
| Farm crops | `sim_cog.crops[item]['sell_price']` | Per-crop |
| Wizard spells | `ww_cog.spells[spell]['power'] * 100` | power×100 |
| Pets | Hardcoded: Tiger 500, Dragon 1000, Horse 700, etc. | Fixed |

Pets require a **reaction confirmation** (✅/❌, 30s timeout) before selling.

Sellable items dict (hardcoded):
```python
self.item_sell_values = {
    "luck_charm": 450, "xp_boost": 270, "pet_food": 135,
    "energy_drink": 180, "double_coins": 765, "mystery_box": 225,
    "rare_fish_bait": 180, "farm_expansion": 900,
}
```

### Gift System (`L!gift`)

Anonymous gifts delivered via DM:

```
L!gift @user luck_charm Hope this helps!
L!gift @user 1000 coins Here you go!
```

**Gift flow:**
1. Check `self.gifts_enabled(target_id)` (default True)
2. Check not blocked
3. Detect gift type (coins / shop item / farm crop / wizard spell)
4. Transfer item/coins via appropriate cog
5. Send DM embed with `"The sender's identity is secret! 🤫"` footer
6. If DM fails (Forbidden/HTTPException): announces in channel that DM closed but transfer still happened

### Block System

```python
# data/blocks.json
{"123456789": [987654321, 444444444]}  # user 123 has blocked users 987 and 444
```

Blocking prevents: trading, gifting, and direct game challenges. Group games are unaffected.

### Data Persistence

```python
# _record_trade_state() — async, asyncio.to_thread
# Saves to data/users/{id}.json under:
user["games"]["trading"]["total_trades"] += 1
user["games"]["trading"]["last_trade"] = trade_summary
user["games"]["trading"]["recent_trades"]  # last 50 trades
```

Uses `user_storage.enqueue_user_storage` for non-blocking async writes.

### Commands

| Command | Description |
|---------|-------------|
| `L!trade @user` | Initiate trade request |
| `L!trade add coins <amount>` | Add coins to your offer |
| `L!trade add item <item_id> [qty]` | Add item to your offer |
| `L!trade remove coins <amount>` | Remove coins from offer |
| `L!trade remove item <item_id> [qty]` | Remove item from offer |
| `L!tradeconfirm` | Confirm your side |
| `L!tradecancel` | Cancel the trade |
| `L!tradehistory [limit]` | View your recent trades (default 5) |
| `L!sell [item_name]` | Sell item for 85–90% value |
| `L!block @user` | Block user from trading/gifting with you |
| `L!unblock @user` | Unblock user |
| `L!blocklist` | View your blocklist |
| `L!gift @user <item> [message]` | Send anonymous gift via DM |
| `L!gifts` | View gift settings |
| `L!gifts enable` | Enable receiving gifts |
| `L!gifts disable` | Disable receiving gifts |
| `L!admire @user` | Anonymous admiration DM |
| `L!encourage @user` | Anonymous encouragement DM |

---

## 9. Cross-Cog Integration Map

Part 9 cogs are heavily interconnected with each other and with the rest of the bot:

```
pets.py ──────────────────────────────────────────────────────────
  │  gets_fishing_multiplier()     → fishing.py
  │  get_farm_yield_multiplier()   → farming.py
  │  check_pet_farm_interaction()  → farming.py
  │  get_mining_*_multiplier()     → mining.py
  │  get_gambling_multiplier()     → gambling.py
  │  get_daily_bonus()             → economy.py
  │  get_coins_multiplier()        → economy.py
  └  leaderboard_manager.increment_stat("pet_adoptions")
  └  profile_manager.increment_stat("pets_owned")

profile.py ────────────────────────────────────────────────────────
  │  economy.json → coins_balance, total_earned, specialty_coins
  │  fishing_data.json → fish_caught, rare/legendary, biggest
  │  gambling_stats.json → total_games, wins, wagered
  │  data/users/{id}.json → per-game stats (highest priority)
  └  pets_cog.pets_data → pet block in overview/social pages

social.py ─────────────────────────────────────────────────────────
  │  economy_cog.add_coins() for all social rewards
  │  profile_cog.profile_manager.increment_stat() for all social stats
  └  ach_cog.manager.unlock_achievement() for social milestones

trading.py ────────────────────────────────────────────────────────
  │  economy_cog (get_balance, remove_coins, add_coins, get_inventory,
  │               remove_item, add_item)
  │  sim_cog (farm crops)
  │  ww_cog (wizard spells)
  └  pets_cog (pet selling)

marriage.py ──────────────────────────────────────────────────────
  └  economy_cog (10k marriage cost, 5k divorce cost, shared bank)

reputation.py ────────────────────────────────────────────────────
  └  (effects consumed by other cogs via get_price_modifier / get_reward_modifier)
```

---

## 10. Commands Reference

### Pets
| Command | Type | Cost |
|---------|------|------|
| `/pet` | Slash | Free (first), 10,000 coins (subsequent) |

### Marriage
| Command | Type | Cost |
|---------|------|------|
| `L!marry @user` | Prefix | 10,000 coins — sends Accept/Decline buttons |
| `L!marry accept/decline` | Prefix | Fallback (buttons preferred) |
| `L!divorce` | Prefix | 5,000 coins |
| `L!spouse [@user]` | Prefix | Free |
| `L!bank` | Prefix | Free — Deposit 💰 / Withdraw 💸 modals |
| `L!couplequests` | Prefix | Free — 3-tier embed (15 quests) |

### Reputation
| Command | Type | Notes |
|---------|------|-------|
| `L!rep [@user]` | Prefix | View |
| `L!rep give/remove @user [reason]` | Prefix | 24hr cooldown |
| `L!rep history [@user]` | Prefix | Last 5 events |
| `/leaderboard` | Slash | ❤️ Server Reputation + 🌍 Global Reputation |

### Profile
| Command | Type | Notes |
|---------|------|-------|
| `L!profile [@user]` (alias `L!p`, `L!me`) | Prefix | 4-page LayoutView |
| `/profile [user]` | Slash | Same |
| `L!energy` | Prefix | Energy status |

### Social / Actions / Trading
*(See individual sections above for full tables)*

---

**11. Part 9 Summary**

**6 files · ~5,021 total lines · March 2026**

### System Coverage

| System | File | Lines | Complexity |
|--------|------|-------|------------|
| Pets | pets.py | 740 | High — 16 pets, 14 perk types, cross-cog API |
| Profile | profile.py | 910 | High — Components V2, 5-file stat aggregation |
| Trading | trading.py | 1,288 | High — P2P sessions, gifts, sell, blocks |
| Social + Actions | social.py | 997 | Medium — GIF API, story listener, ship, action commands |
| Marriage | marriage.py | 783 | Medium — button proposals, modal bank, 15 quests |
| Reputation | reputation.py | 303 | Low-Medium — tier ladder, cooldowns, profile sync |

### Key Technical Features

- **Components V2:** Both `PetDashboardView` and `ProfileView` use `discord.ui.LayoutView` with `Container` / `TextDisplay` / `Separator` / `ActionRow` — no `discord.Embed` in these panels
- **Cross-cog perk injection:** `pets.py` is a passive multiplier provider — other cogs call its methods to scale their outputs without pets.py needing to know about them
- **Stat aggregation:** `ProfileManager.get_user_stats()` merges 5 separate JSON files with priority ordering; the `data/users/{id}.json` store (per-user file written by `user_storage`) takes precedence over profile.json for numeric stats
- **Deterministic ship score:** `/ship` uses `(id1 + id2) % 101` — same two users always get the same percentage, making it repeatable without storing anything
- **Anonymous gifts:** `trading.py` transfers the item/coins immediately regardless of DM success — the anonymity is only in the DM message, not in the transfer
- **Trade safety:** `execute_trade()` re-validates ownership before any transfer — prevents TOCTOU race where user spends coins between confirming and execution
- **Story listener:** `social.py` `on_message` captures all non-command channel messages when a story is active — hooks into the bot event loop passively
- **_parse_ts() pattern:** Appears in marriage.py, reputation.py, and profile.py — handles both naive (legacy) and timezone-aware ISO timestamps gracefully across all three cogs

### Stat Categories Tracked in profiles.json

The `_create_default_profile_legacy()` method documents all 60+ tracked stats, grouped into:
- Economy (earned, spent, biggest win/loss)
- Gambling (7 game types, wagered, ROI)
- Minigames (Wordle, trivia, riddles, typing)
- Board games (TTT, C4, Hangman, Checkers, Chess)
- Card games (UNO, Blackjack, War, Go Fish)
- TCG (battles, ranked, tournaments, cards owned/crafted)
- Social (compliments, roasts, highfives, stories)
- Pets (adopted count, fed/played/walked)
- Fishing (caught, rare, legendary, biggest weight, trips)
- Farming (crops planted/harvested, level)
- Quests (completed, daily streak, longest streak)
- Events (participated, won, seasonal points)
- Business (owned, sales, revenue, items bought/sold)
- Battle (PvP, bosses, dungeons)
- Music (songs played, listen time, genre)
- Misc (commands_used, messages_sent, voice_time)
