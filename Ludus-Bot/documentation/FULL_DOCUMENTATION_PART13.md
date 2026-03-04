# 📦 Ludus-Bot — Part 13: Data Structures (JSON Schemas)
> Full reference of every persistent JSON file — location, owner cog, key names, types and relationships.

---

## Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [data/economy.json](#2-dataeconomyjson)
3. [data/inventory.json](#3-datainventoryjson)
4. [data/profiles.json + data/users/{id}.json](#4-dataprofilesjson--datausersidJSON)
5. [data/pets.json](#5-datapetsjson)
6. [data/fishing_data.json](#6-datafishing_datajson)
7. [data/mining_data.json](#7-datamining_datajson)
8. [data/farms.json](#8-datafarmsjson)
9. [data/gambling_stats.json](#9-dagambling_statsjson)
10. [data/game_stats.json](#10-datagame_statsjson)
11. [data/reputation.json](#11-dataReputationjson)
12. [data/lottery.json](#12-datalotteryjson)
13. [data/quests_data.json](#13-dataquests_datajson)
14. [data/user_achievements.json](#14-datauser_achievementsjson)
15. [data/server_configs.json](#15-dataserver_configsjson)
16. [data/starboard.json](#16-datastarboardjson)
17. [data/counting.json](#17-datacountingjson)
18. [data/leaderboard_stats.json](#18-dataleaderboard_statsjson)
19. [data/global_consent.json](#19-dataglobal_consentjson)
20. [data/tcg/users.json + data/tcg/crafted.json](#20-datatcgusersjson--datatcgcraftedjson)
21. [data/saves/ — DnD Adventure Saves](#21-datasaves--dnd-adventure-saves)
22. [Miscellaneous Files](#22-miscellaneous-files)
23. [Cross-File Relationships](#23-cross-file-relationships)
24. [Render Disk Deployment](#24-render-disk-deployment)

---

## 1. Overview & Architecture

All persistent data is stored as flat JSON files under the `data/` directory (or `$RENDER_DISK_PATH/` when deployed on Render).

### Directory Layout

```
data/
├── economy.json              # Balances, streaks, sub-currency
├── inventory.json            # Deck/item ownership per user
├── profiles.json             # Stat defaults + seed data
├── users/                    # Per-user stat snapshots
│   ├── {user_id}.json
│   └── ...
├── pets.json                 # Pet states
├── fishing_data.json         # Rod, area, catch log
├── mining_data.json          # World map + player state (LARGE)
├── farms.json                # Farm plots, animals, decorations
├── gambling_stats.json       # Win/loss per mini-game
├── game_stats.json           # Board/minigame stats
├── reputation.json           # Rep history per user
├── lottery.json              # Global jackpot + tickets
├── quests_data.json          # Active quests per user
├── user_achievements.json    # Unlocked achievements per user
├── server_configs.json       # Per-guild settings
├── starboard.json            # Starred messages per guild
├── counting.json             # Counting channel state
├── leaderboard_stats.json    # Cross-server stat snapshots
├── global_consent.json       # Data-sharing consent per guild
├── stories.json              # User-generated stories (empty)
├── tcg/
│   ├── users.json            # TCG card collections
│   └── crafted.json          # Crafted card registry
├── saves/
│   └── infinity_adventure.json  # DnD adventure session saves
├── confession_config.json    # Confessions channel config
├── custom_roles.json         # Custom assignable roles
├── cards_emoji_mapping.json  # Playing-card -> emoji table
├── minesweeper_emoji_mapping.json
├── uno_emoji_mapping.json
├── gambling_stats.json
├── tarot_daily.json          # Daily tarot draw tracking
├── first_time_users.json     # Onboarding tracking list
└── global_leaderboard.json   # Aggregate cross-server LB
```

### Keying Convention

| Key type | Format | Example |
|---|---|---|
| User ID | Discord snowflake (string) | `"1138720397567742014"` |
| Guild ID | Discord snowflake (string) | `"1445021753846796371"` |
| Timestamp | ISO 8601 (UTC) | `"2026-03-05T08:32:36+00:00"` |
| Currency | Integer (Ludus Coins) | `2126` |

---

## 2. `data/economy.json`

**Owner cog:** `cogs/economy.py`  
**Purpose:** Core currency ledger — every user's coin balance, lifetime totals, streak, and active boosts.

### Schema

```json
{
  "<user_id>": {
    "balance":       integer,   // current spendable coins
    "total_earned":  integer,   // lifetime coins earned
    "total_spent":   integer,   // lifetime coins spent
    "last_daily":    string|null, // ISO8601 timestamp of last /daily claim
    "daily_streak":  integer,   // consecutive daily streak
    "active_boosts": object,    // { boost_name: expiry_timestamp }
    "username":      string,    // cached display name
    "mine_coins":    integer,   // optional — mining sub-currency
    "farm_coins":    integer,   // optional — farm sub-currency
    "fish_coins":    integer    // optional — fishing sub-currency
  }
}
```

### Field Details

| Field | Default | Notes |
|---|---|---|
| `balance` | `0` | Main spendable currency |
| `total_earned` | `0` | Never decrements |
| `total_spent` | `0` | Never decrements |
| `last_daily` | `null` | `null` = never claimed |
| `daily_streak` | `0` | Reset when gap > 48 h |
| `active_boosts` | `{}` | Keyed by boost slug, value = ISO expiry |
| `mine_coins` | absent | Added on first mining session |
| `farm_coins` | absent | Added on first farm session |
| `fish_coins` | absent | Added on first fishing session |

### Relationships
- `balance` is the source of truth for all transactions in `economy.py`, `gambling.py`, `blackjack.py`, `poker.py`
- `daily_streak` is mirrored in `data/users/{id}.json#stats.daily_streak`

---

## 3. `data/inventory.json`

**Owner cog:** `cogs/economy.py`, `cogs/business.py`  
**Purpose:** Tracks which card decks and special items each user owns.

### Schema

```json
{
  "<user_id>": {
    "deck_classic":  boolean,   // owns classic card deck
    "deck_platinum": boolean,   // owns platinum deck
    "deck_dark":     boolean,   // owns dark deck
    "equipped_deck": string,    // slug of currently active deck
    "<item_slug>":   boolean    // dynamic — any purchasable item
  }
}
```

### Known Item Keys

| Key | Description |
|---|---|
| `deck_classic` | Classic playing card skin |
| `deck_platinum` | Platinum (premium) skin |
| `deck_dark` | Dark theme skin |
| `equipped_deck` | Active deck slug used in card games |

### Notes
- Users with no purchases have an empty object `{}`
- New items are added dynamically when purchased — no migrations needed

---

## 4. `data/profiles.json` + `data/users/{id}.json`

**Owner cog:** `cogs/profile.py`, `cogs/economy.py`  
**Purpose:** `profiles.json` stores a seeded record for the bot-owner user with defaults; `data/users/{id}.json` is the authoritative per-user stat file written at runtime.

### `data/users/{id}.json` — Full Schema

```json
{
  "user_id":  integer,        // Discord user snowflake
  "username": string,         // Cached display name

  "stats": {
    // === Energy ===
    "energy":         integer,   // current energy (0–100)
    "max_energy":     integer,   // capacity (default 100)
    "level":          integer,   // XP level
    "xp":             integer,   // experience points

    // === Activity ===
    "messages_sent":  integer,
    "commands_used":  integer,

    // === Mini-games ===
    "minigames_played": integer,
    "minigames_won":    integer,

    // TicTacToe
    "tictactoe_wins": integer, "tictactoe_losses": integer, "tictactoe_draws": integer,
    // Connect4
    "connect4_wins":  integer, "connect4_losses": integer, "connect4_played": integer,
    // Wordle
    "wordle_wins":    integer, "wordle_losses": integer, "wordle_played": integer,
    // Hangman
    "hangman_wins":   integer, "hangman_losses": integer, "hangman_played": integer,
    // Trivia
    "trivia_wins":    integer, "trivia_losses": integer, "trivia_played": integer,

    // === Gambling ===
    "blackjack_wins": integer, "blackjack_losses": integer,
    "blackjack_draws": integer, "blackjack_played": integer, "blackjack_coins_won": integer,
    "poker_wins":     integer, "poker_losses": integer, "poker_played": integer, "poker_coins_won": integer,
    "slots_wins":     integer, "slots_losses": integer, "slots_coins_won": integer,

    // UNO
    "uno_wins":       integer, "uno_losses": integer, "uno_played": integer,
    // Chess / Checkers
    "chess_wins":     integer, "chess_losses": integer, "chess_draws": integer,
    "checkers_wins":  integer, "checkers_losses": integer,

    // === Resource Games ===
    "fishing_total_caught":    integer,
    "fishing_rare_caught":     integer,
    "fishing_coins_earned":    integer,
    "mining_total_mined":      integer,
    "mining_rare_found":       integer,
    "mining_coins_earned":     integer,
    "farming_total_harvested": integer,
    "farming_coins_earned":    integer,

    // === Economy Activities ===
    "heist_participated":  integer,
    "heist_successful":    integer,
    "heist_coins_earned":  integer,
    "daily_streak":        integer,
    "daily_longest_streak":integer,
    "daily_total_claimed": integer,

    // === Social ===
    "reputation_given":    integer,
    "reputation_received": integer,
    "marriages":           integer,
    "divorces":            integer,

    // === Pets ===
    "pets_owned":          integer,
    "pets_fed":            integer,
    "pets_played_with":    integer,

    // === Meta ===
    "achievements_unlocked": integer,
    "quests_completed":      integer,
    "total_coins_earned":    integer,
    "total_coins_spent":     integer,

    // === Combat / War ===
    "duels_won":       integer, "duels_lost": integer, "duels_coins_won": integer,
    "war_wins":        integer, "war_losses": integer,
    "war_played":      integer, "war_coins_won": integer,

    // === Mini-game Extras ===
    "snake_high_score": integer,
    "snake_played":     integer
    // ... (additional keys added by newer cogs)
  }
}
```

### Relationship to `profiles.json`
- `profiles.json` contains the bot-owner's seeded record + a `_comment` key that documents which keys are copied into new user files
- When a new user first interacts, all `stats` keys from this template are copied into `data/users/{id}.json`

---

## 5. `data/pets.json`

**Owner cog:** `cogs/pets.py`  
**Purpose:** Stores the currently owned pet for each user, plus a global `__adoptions__` counter.

### Schema

```json
{
  "<user_id>": {
    "emoji":      string,    // Unicode emoji for the pet type
    "type":       string,    // Pet type name, e.g. "Cat", "Tiger", "Horse"
    "name":       string,    // User-assigned nickname
    "hunger":     integer,   // 0–100 (100 = full)
    "happiness":  integer,   // 0–100
    "energy":     integer,   // 0–100
    "adopted":    string,    // Datetime string (local TZ, not UTC)
    "behavior":   string     // optional — e.g. "aggressive", "playful"
  },
  "__adoptions__": {
    "<user_id>": integer     // Total times this user has adopted a pet
  }
}
```

### Pet Types & Emojis

| Type | Emoji |
|---|---|
| Cat | 🐱 |
| Dog | 🐶 |
| Horse | 🐴 |
| Tiger | 🐯 |
| Dragon | 🐉 |
| Fox | 🦊 |
| Wolf | 🐺 |
| Rabbit | 🐰 |

### Notes
- One pet per user at a time — re-adopting with `/pet adopt` replaces the old pet
- `hunger`, `happiness`, `energy` all decay over time if not maintained
- `behavior` is assigned based on interaction history (optional field)
- `__adoptions__` is a special non-user key in the same dict

---

## 6. `data/fishing_data.json`

**Owner cog:** `cogs/fishing.py`  
**Purpose:** Tracks equipment, unlocked areas, and catch history for each fisher.

### Schema

```json
{
  "<user_id>": {
    "rod":            string,      // active rod slug
    "boat":           string,      // active boat slug
    "current_area":   string,      // active fishing area slug
    "bait_inventory": {
      "<bait_slug>":  integer      // quantity owned
    },
    "fish_caught": {
      "<fish_slug>": {
        "count":   integer,        // total caught
        "biggest": float           // record weight in kg
      }
    },
    "total_catches":   integer,
    "total_value":     integer,    // cumulative coins earned from sales
    "unlocked_areas":  [string],   // list of unlocked area slugs
    "achievements":    [string],   // earned fishing achievement slugs
    "stats": {
      "biggest_catch": null|string, // slug of biggest fish ever
      "rarest_catch":  null|string,
      "favorite_area": string
    },
    "owned_rods":      [string],   // all rods purchased
    "owned_boats":     [string]    // all boats purchased
  }
}
```

### Known Rod Tiers

| Slug | Description |
|---|---|
| `starter_rod` | Default rod |
| `carbon_rod` | Mid-tier |
| `legendary_rod` | Highest tier |

### Fishing Areas

| Slug | Description |
|---|---|
| `pond` | Starter area |
| `river` | Mid area |
| `lake` | Large fish |
| `trench` | Deep sea |
| `ocean` | Rarest fish |

---

## 7. `data/mining_data.json`

**Owner cog:** `cogs/mining.py`  
**Purpose:** Persistent 2D world map + per-player mining state. ⚠️ Can be very large (30,000+ lines for active worlds).

### Top-Level Structure

```json
{
  "games": {
    "<user_id_or_guild_id>": { /* PlayerState */ }
  }
}
```

### PlayerState Schema

```json
{
  "user_id":           integer,
  "guild_id":          integer|null,  // null = personal world
  "is_shared":         boolean,       // true = guild-shared world
  "seed":              integer,       // world generation seed
  "x":                 integer,       // current X position
  "y":                 integer,       // current Y position (depth)
  "depth":             integer,       // deepest depth reached
  "energy":            integer,       // current energy
  "max_energy":        integer,       // capacity (default 60)
  "last_energy_regen": string,        // ISO8601 timestamp
  "pickaxe_level":     integer,       // 1–5
  "backpack_capacity": integer,       // max items before needing to sell
  "inventory": {
    "<block_type>":    integer        // count
  },
  "coins":             integer,       // mining sub-currency
  "last_map_regen":    string,        // ISO8601
  "map_data": {
    "<x,y>":           string         // block type at coordinate
  }
}
```

### Block Types

| Type | Rarity | Value |
|---|---|---|
| `air` | N/A | 0 |
| `dirt` | Common | 1 |
| `stone` | Common | 2 |
| `coal` | Common | 5 |
| `iron` | Uncommon | 20 |
| `gold` | Rare | 50 |
| `diamond` | Very Rare | 200 |
| `emerald` | Legendary | 500 |

### Notes
- Map coordinates use `"x,y"` string keys
- `y` increases downward (depth)
- Shared worlds: `guild_id` is set, `is_shared=true`, key in `games` is guild_id

---

## 8. `data/farms.json`

**Owner cog:** `cogs/simulations.py` (Farming module)  
**Purpose:** Complete farm state per user — plots, animals, decorations, seasonal weather.

### Schema

```json
{
  "<user_id>": {
    "plots": {
      "<plot_id>": {
        "crop":       string,       // crop slug, e.g. "wheat"
        "planted_at": string,       // ISO8601
        "watered":    boolean,
        "fertilized": boolean,
        "growth_stage": integer,    // 0 = seed, max = ready
        "hybrid":     string|null   // null = normal crop
      }
    },
    "inventory": {
      "<item_slug>": integer        // seeds, harvested crops
    },
    "season":        string,        // "spring"|"summer"|"autumn"|"winter"
    "season_change": string,        // ISO8601 — next season flip
    "tools": [string],              // owned tool slugs, e.g. ["basic_hoe", "sprinkler"]
    "animals": {
      "<animal_id>": {
        "type":       string,       // e.g. "chicken", "cow"
        "name":       string,
        "feed":       integer,      // 0–100
        "happiness":  integer,
        "last_fed":   string
      }
    },
    "animal_products": {
      "<product_slug>": integer     // collected products ready for sale
    },
    "water_level":         integer, // irrigation reservoir 0–100
    "xp":                  integer,
    "level":               integer,
    "max_plots":           integer, // unlocked plot capacity
    "auto_watered_plots":  [integer],
    "fertilized_plots":    { "<plot_id>": boolean },
    "weather":             string,  // "sunny"|"rainy"|"stormy"
    "decorations": {
      "<slot>": string              // decoration slug placed in slot
    },
    "beauty_points":       integer,
    "daily_quest":         string,  // quest slug
    "quest_progress":      integer,
    "quest_reset":         string,  // ISO8601
    "achievements":        [string],
    "genetics_lab":        boolean, // unlocked genetic engineering
    "market_status":       {},      // active market listings
    "harvests_today":      integer,
    "last_reset":          string,  // ISO8601
    "breeding_pairs": {
      "<pair_id>": {
        "parent_a": string,
        "parent_b": string,
        "started_at": string
      }
    }
  }
}
```

### Crops

| Slug | Season | Days to Grow |
|---|---|---|
| `wheat` | any | 1 |
| `carrot` | spring | 2 |
| `potato` | spring | 3 |
| `tomato` | summer | 2 |
| `sunflower` | summer | 3 |
| `pumpkin` | autumn | 4 |
| `strawberry` | spring | 2 |
| `corn` | summer | 3 |

---

## 9. `data/gambling_stats.json`

**Owner cog:** `cogs/gambling.py`  
**Purpose:** Win/loss tracking per mini-game for each user.

### Schema

```json
{
  "<user_id>": {
    "total_games":   integer,
    "total_wagered": integer,
    "total_won":     integer,
    "total_lost":    integer,
    "games": {
      "<game_slug>": {
        "played": integer,
        "won":    integer,
        "lost":   integer
      }
    },
    "biggest_win":   integer,  // largest single payout
    "biggest_loss":  integer   // largest single loss
  }
}
```

### Tracked Game Slugs

| Slug | Game |
|---|---|
| `slots` | Slot machine |
| `crash` | Crash multiplier |
| `dice` | Dice roll |
| `mines` | Mine sweeper bet |
| `poker` | Poker (vs bot) |
| `roulette` | Roulette |
| `blackjack` | Blackjack |

---

## 10. `data/game_stats.json`

**Owner cog:** `cogs/game_stats.py`  
**Purpose:** Cross-game stats tracking — totals, categories, guild-specific breakdowns.

### Schema

```json
{
  "<user_id>": {
    "total_games":            integer,
    "games_won":              integer,
    "games_lost":             integer,
    "total_coins_earned":     integer,
    "favorite_game":          string,     // slug of most-played game
    "game_counts": {
      "<game_slug>":          integer
    },
    "total_playtime_minutes": float,
    "achievements_unlocked":  integer,
    "perfect_games":          integer,
    "comeback_wins":          integer,
    "speedrun_wins":          integer,
    "first_game_date":        string,     // "YYYY-MM-DD"
    "last_game_date":         string,
    "daily_streak":           integer,
    "best_daily_streak":      integer,
    "categories": {
      "word_games":     integer,
      "math_games":     integer,
      "board_games":    integer,
      "puzzle_games":   integer,
      "trivia_games":   integer,
      "speed_games":    integer,
      "memory_games":   integer,
      "strategy_games": integer
    },
    "guild_stats": {
      "<guild_id>": {
        "total_games": integer,
        "games_won":   integer,
        "game_counts": { "<slug>": integer }
      }
    }
  }
}
```

---

## 11. `data/reputation.json`

**Owner cog:** `cogs/reputation.py`  
**Purpose:** Tracks positive/negative reputation given between users with full history.

### Schema

```json
{
  "<user_id>": {
    "total_rep":    integer,
    "positive_rep": integer,
    "negative_rep": integer,
    "given_rep": {
      "<target_user_id>": integer     // last rep given to this person
    },
    "rep_history": [
      {
        "type":       "positive"|"negative",
        "giver_id":   integer,
        "giver_name": string,
        "reason":     string,
        "timestamp":  string          // ISO8601
      }
    ]
  }
}
```

### Notes
- `given_rep` tracks who **this user** gave rep to (cooldown enforcement)
- `rep_history` is the list of rep **received** by this user
- Each user can give rep once every 24 h (enforced via timestamp check)

---

## 12. `data/lottery.json`

**Owner cog:** `cogs/lottery.py`  
**Purpose:** Global lottery state — jackpot, ticket pool, draw history.

### Schema

```json
{
  "current_jackpot": integer,          // accumulated prize pool
  "tickets": {
    "<user_id>": [integer]             // list of ticket IDs owned
  },
  "ticket_counter":  integer,          // auto-increment ticket ID
  "last_drawing":    string|null,      // ISO8601 of last draw
  "next_drawing":    string,           // ISO8601 of next scheduled draw
  "winners_history": [
    {
      "winner_id":   integer,
      "prize":       integer,
      "date":        string,
      "ticket_id":   integer
    }
  ]
}
```

### Notes
- Drawing is automatic (checked at bot startup / daily reset)
- Jackpot seeds from `/daily` and direct ticket sales
- Unclaimed jackpot rolls over to next drawing

---

## 13. `data/quests_data.json`

**Owner cog:** `cogs/quests.py`  
**Purpose:** Tracks active daily quests, progress, and completion counts per user.

### Schema

```json
{
  "<user_id>": {
    "active_quests": [
      {
        "id":     string,     // quest slug, e.g. "pet_caretaker"
        "name":   string,     // display name
        "desc":   string,     // description
        "reward": integer,    // coin reward on completion
        "target": integer     // required completions
      }
    ],
    "completed_today": integer,
    "total_completed": integer,
    "last_reset":      string,   // ISO8601 — when quests were last refreshed
    "progress": {
      "<quest_id>":    integer   // current progress toward target
    }
  }
}
```

### Quest Slugs (examples)

| Slug | Task | Target |
|---|---|---|
| `pet_caretaker` | Interact with pet | 5 |
| `fisherman` | Catch fish | 3 |
| `miner` | Mine blocks | 10 |
| `farmer` | Harvest crops | 5 |
| `gambler` | Play gambling game | 3 |
| `socialite` | Send messages | 20 |
| `daily_claimer` | Claim daily reward | 1 |

---

## 14. `data/user_achievements.json`

**Owner cog:** `cogs/achievements.py`  
**Purpose:** Tracks which achievements each user has unlocked.

### Schema

```json
{
  "<user_id>": {
    "unlocked":    [string],        // list of unlocked achievement slugs
    "progress": {
      "<achievement_slug>": integer // progress toward next tier
    },
    "points":      integer,         // total achievement points
    "unlocked_at": {
      "<achievement_slug>": string  // ISO8601 timestamp of unlock
    }
  }
}
```

### Achievement Category Slugs (examples)

| Slug | Category | Unlock Condition |
|---|---|---|
| `first_catch` | Fishing | Catch 1 fish |
| `master_angler` | Fishing | Catch 100 fish |
| `beautiful_farm` | Farming | Place 5 decorations |
| `hybrid_creator` | Farming | Create 1 hybrid crop |
| `big_spender` | Economy | Spend 10,000 coins |
| `daily_devotion` | Social | 7-day daily streak |
| `duelist` | Combat | Win 10 duels |

---

## 15. `data/server_configs.json`

**Owner cog:** `cogs/server_config.py`  
**Purpose:** Per-guild feature toggles and configuration.

### Schema

```json
{
  "<guild_id>": {
    "welcome_dm":            boolean,  // send DM on new member join
    "personality_reactions": boolean,  // bot reacts with personality emojis
    "disabled_commands":     [string], // list of disabled command names
    "mod_roles":             [integer],// list of role IDs with mod perms
    "log_channel":           integer|null, // channel ID for audit log
    "rate_limit_enabled":    boolean,
    "nsfw_filter":           boolean,
    "shared_mining_world":   boolean,  // all guild members share one mine map
    "mining_map_reset":      boolean   // reset mine on next use
  }
}
```

### Default Values

| Field | Default |
|---|---|
| `welcome_dm` | `false` |
| `personality_reactions` | `true` |
| `disabled_commands` | `[]` |
| `rate_limit_enabled` | `true` |
| `nsfw_filter` | `true` |
| `shared_mining_world` | `false` |

---

## 16. `data/starboard.json`

**Owner cog:** `cogs/starboard.py`  
**Purpose:** Tracks starred messages and starboard channel per guild.

### Schema

```json
{
  "boards": {
    "<guild_id>": {
      "channel_id":   integer,      // starboard output channel
      "threshold":    integer,      // stars needed to post
      "emoji":        string        // star emoji used
    }
  },
  "limit": integer,                 // global default threshold
  "posted_messages": {
    "<original_message_id>": integer  // starboard message ID
  }
}
```

---

## 17. `data/counting.json`

**Owner cog:** `cogs/counting.py`  
**Purpose:** State of the counting channel game per guild.

### Schema

```json
{
  "<guild_id>": {
    "current_count": integer,     // last valid number
    "last_user":     integer,     // user_id who sent last valid count
    "channel":       integer      // channel_id of counting channel
  }
}
```

### Rules enforced
- Users cannot count twice in a row
- Wrong number resets count to 0

---

## 18. `data/leaderboard_stats.json`

**Owner cog:** `cogs/leaderboards.py`  
**Purpose:** Cross-server aggregate stat snapshots used for global leaderboards.

### Schema

```json
{
  "<guild_id>": {
    "counting_peak":  integer,     // highest count reached in guild
    "music_plays":    integer,     // total music plays in guild
    "pet_adoptions":  integer,     // total pet adoptions
    "gtn_wins":       integer,     // guess-the-number wins
    "tod_uses":       integer,     // truth-or-dare uses
    "server_name":    string       // cached guild name
  }
}
```

---

## 19. `data/global_consent.json`

**Owner cog:** `cogs/global_leaderboard.py`  
**Purpose:** Tracks whether each guild has opted-in to global leaderboard data sharing.

### Schema

```json
{
  "<guild_id>": {
    "enabled":  boolean,         // true = opted-in to global LB
    "set_by":   integer,         // admin user_id who toggled it
    "set_at":   string           // ISO8601 timestamp
  }
}
```

---

## 20. `data/tcg/users.json` + `data/tcg/crafted.json`

**Owner cog:** `cogs/psyvrse_tcg.py`  
**Purpose:** Trading Card Game — user collections and crafted card registry.

### `users.json` Schema

```json
{
  "users": {
    "<user_id>": {
      "cards":     [string],      // list of owned card slugs
      "packs_opened": integer,
      "coins":     integer,       // TCG-specific currency
      "deck": {
        "name":    string,
        "cards":   [string]       // selected deck list
      }
    }
  }
}
```

### `crafted.json` Schema

```json
{
  "<card_slug>": {
    "crafted_by":  integer,       // user_id
    "crafted_at":  string,        // ISO8601
    "recipe":      [string]       // input card slugs used
  }
}
```

### Notes
- Both files currently have minimal data (users = `{}`, crafted = `{}`)
- TCG system is actively developed — schemas may expand

---

## 21. `data/saves/` — DnD Adventure Saves

**Owner cog:** `cogs/dnd/dnd.py`  
**Purpose:** Persistent session saves for the Infinity Adventure DnD system.

### Save File: `saves/infinity_adventure.json`

Each save is keyed by user ID and stores the full DnD session state:

```json
{
  "<user_id>": {
    "session_id":    string,       // UUID
    "gate":          string,       // current gate slug, e.g. "gate1_fantasy"
    "player": {
      "name":        string,
      "class":       string,       // warrior|mage|rogue|healer
      "level":       integer,
      "hp":          integer,
      "max_hp":      integer,
      "mana":        integer,
      "max_mana":    integer,
      "attack":      integer,
      "defense":     integer,
      "gold":        integer,
      "inventory":   [string],
      "abilities":   [string],
      "status_effects": [string]
    },
    "state": {
      "room":        integer,       // current room index
      "floor":       integer,
      "explored":    [integer],     // visited room IDs
      "flags": {
        "<flag_name>": boolean|any  // story flags
      }
    },
    "combat": null | {
      "enemy":       object,        // current enemy state
      "turn":        integer,
      "log":         [string]
    },
    "created_at":    string,        // ISO8601
    "last_saved":    string         // ISO8601
  }
}
```

### Path Configuration

Configured in `cogs/dnd/dnd.py`:
```python
SAVE_DIR = os.path.join(os.getenv("RENDER_DISK_PATH", "data"), "saves")
```

This ensures saves land on the persistent Render disk when deployed.

---

## 22. Miscellaneous Files

### `data/confession_config.json`

```json
{
  "<guild_id>": {
    "channel_id":  integer,      // confession output channel
    "enabled":     boolean,
    "anonymous":   boolean       // hide sender identity
  }
}
```

### `data/counting.json` (already documented in §17)

### `data/custom_roles.json`

```json
{
  "<guild_id>": {
    "roles": [
      {
        "role_id":   integer,
        "label":     string,
        "emoji":     string
      }
    ]
  }
}
```

### `data/first_time_users.json`

```json
[integer, integer, ...]  // flat array of user_ids who completed onboarding
```

### `data/stories.json`

Currently empty `{}`. Reserved for user-generated story content from `/story` or social cogs.

### `data/tarot_daily.json`

```json
{
  "<user_id>": {
    "last_drawn":  string,       // ISO8601 date
    "card":        string        // last drawn card name
  }
}
```

### Emoji Mapping Files

Three files map internal slugs to Discord emoji strings:

| File | Used by |
|---|---|
| `data/cards_emoji_mapping.json` | `cogs/cardgames.py`, `cogs/blackjack.py`, `cogs/poker.py` |
| `data/minesweeper_emoji_mapping.json` | `cogs/minigames.py` |
| `data/uno_emoji_mapping.json` | `cogs/uno/` |

Format:

```json
{
  "<slug>": "<discord_emoji_string>"
}
```

---

## 23. Cross-File Relationships

```
economy.json ──────── balance ──────────────────► all transaction cogs
                       ↑
                  daily_streak mirror
                       ↓
users/{id}.json ─── stats.daily_streak

profiles.json ──────── template ───────────────► users/{id}.json (on first join)

user_achievements.json ─ achievement unlocks ──► users/{id}.json#stats.achievements_unlocked
quests_data.json ────── quest completions ─────► users/{id}.json#stats.quests_completed

pets.json ──────────── pet events ─────────────► users/{id}.json#stats.pets_fed/pets_played_with
fishing_data.json ───── catch events ───────────► users/{id}.json#stats.fishing_total_caught
mining_data.json ───── mine events ─────────────► users/{id}.json#stats.mining_total_mined
farms.json ─────────── harvest events ──────────► users/{id}.json#stats.farming_total_harvested

reputation.json ────── rep history ─────────────► users/{id}.json#stats.reputation_received
gambling_stats.json ─── game results ───────────► game_stats.json (aggregated)

server_configs.json ─── shared_mining_world ───► mining_data.json (shared world key)
global_consent.json ──── opted-in guilds ───────► leaderboard_stats.json (visible to LB)
```

---

## 24. Render Disk Deployment

When deployed to Render, the environment variable `RENDER_DISK_PATH` points to the persistent disk mount (e.g. `/opt/render/project/disk`).

All cogs that write persistent data use this pattern:

```python
import os

DATA_DIR = os.getenv("RENDER_DISK_PATH", "data")
DATA_FILE = os.path.join(DATA_DIR, "filename.json")
```

### Cogs that use `RENDER_DISK_PATH`

| Cog | File |
|---|---|
| `economy.py` | `economy.json` |
| `pets.py` | `pets.json` |
| `fishing.py` | `fishing_data.json` |
| `mining.py` | `mining_data.json` |
| `simulations.py` | `farms.json` |
| `reputation.py` | `reputation.json` |
| `achievements.py` | `user_achievements.json` |
| `quests.py` | `quests_data.json` |
| `dnd/dnd.py` | `saves/infinity_adventure.json` |
| `server_config.py` | `server_configs.json` |

### ⚠️ Local vs Render Path

| Environment | `DATA_DIR` resolves to |
|---|---|
| Local dev (no env var) | `./data/` |
| Render production | `/opt/render/project/disk/` |

The `data/` directory in the repo contains **initial seed files** that are used only before the persistent disk is populated.

---

*Part 13 of 13 — Complete Documentation Series*  
*Generated: 2026-03-05*  
*Covers: 25+ JSON data files, 3 subdirectories, all schemas with field types*
