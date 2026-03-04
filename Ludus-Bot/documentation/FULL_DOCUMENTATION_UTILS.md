# 🛠️ Ludus-Bot — Utils: Shared Library Reference
> Complete reference for all files in `utils/` — the shared code infrastructure used across all cogs.

---

## Table of Contents

1. [Overview — What Is utils/?](#1-overview--what-is-utils)
2. [utils/user_storage.py](#2-utilsuser_storagepy)
3. [utils/stat_hooks.py](#3-utilsstat_hookspy)
4. [utils/database.py](#4-utilsdatabasepy)
5. [utils/embed_styles.py](#5-utilsembed_stylespy)
6. [utils/performance.py](#6-utilsperformancepy)
7. [utils/card_visuals.py](#7-utilscard_visualspy)
8. [Dependency Map](#8-dependency-map)
9. [Usage Patterns & Best Practices](#9-usage-patterns--best-practices)

---

## 1. Overview — What Is utils/?

The `utils/` directory is the **shared infrastructure layer** of Ludus-Bot. It provides re-usable, cog-agnostic code that multiple cogs rely on without creating tight dependencies between those cogs.

### Directory Layout

```
utils/
├── user_storage.py   (421 lines) — Per-user JSON file storage + async API
├── database.py       (270 lines) — SQLite singleton alternative backend
├── embed_styles.py   (380 lines) — Themed Discord embed factory
├── performance.py    ( ~60 lines) — File-level JSON cache
├── stat_hooks.py     (145 lines) — Fire-and-forget stat recording
└── card_visuals.py   (646 lines) — PIL-based card game image renderer
```

**Total: ~1,922 lines** spread across 6 modules.

### Design Principles

| Principle | Explanation |
|-----------|-------------|
| **No circular imports** | Utils never import from `cogs/`. Cogs import from `utils/`. |
| **No Discord.py cog state** | Utils are plain Python modules, not `discord.Cog` subclasses. |
| **Safe on import** | Every util handles its own import failures gracefully so a missing package never prevents the bot from starting. |
| **Global singleton instances** | `database.py`, `performance.py` each expose exactly one global instance (`db`, `config_cache`) — importers share the same object. |
| **Async-safe** | I/O-bound operations in `user_storage.py` run inside `asyncio.to_thread()` so they never block the Discord event loop. |

### Who Uses What

| Util | Primary consumers |
|------|------------------|
| `user_storage` | `bot.py` (touch on every message), any cog recording stats |
| `stat_hooks` | All game cogs (thin wrapper over `user_storage`) |
| `embed_styles` | Any cog wanting colour-consistent embeds |
| `database` | Optional SQL backend — currently opt-in |
| `performance` | Any cog wanting a 5-minute read-through JSON cache |
| `card_visuals` | `blackjack.py`, `poker.py`, `cardgames.py`, `cards_enhanced.py` |

---

## 2. utils/user_storage.py

**File size:** 421 lines  
**Purpose:** Manages per-user JSON files at `data/users/{user_id}.json`. Every Discord user gets their own file, created on first interaction. All disk I/O runs in a thread pool via `asyncio.to_thread()`.

### File structure written to disk

Each user file (`data/users/123456789.json`) has this shape:

```json
{
  "user_id": 123456789,
  "username": "playerName",
  "stats": {
    "messages_sent": 0,
    "commands_used": 0,
    "minigames_played": 0,
    "minigames_won": 0,
    "blackjack_wins": 0,
    "trivia_wins": 0,
    "...": "all numeric fields from data/profile_template.json"
  },
  "minigames": {
    "by_game": {
      "wordle": { "played": 0, "wins": 0, "losses": 0, "draws": 0, "coins": 0 }
    },
    "recent_plays": []
  },
  "activity": {
    "counts": {},
    "by_name": {},
    "recent": []
  },
  "games": {},
  "meta": {
    "created_at": "2025-01-01T00:00:00+00:00",
    "updated_at": "2025-01-01T00:00:00+00:00",
    "last_active": "2025-01-01T00:00:00+00:00"
  }
}
```

> **New stat keys** added to `profile_template.json` are automatically back-filled into existing user files the next time `_sync_load()` is called.

### Internal helpers (private, never import these)

```
_get_lock(user_id)      → threading.Lock  — per-user write lock (prevents concurrent writes to same file)
_now()                  → str             — current UTC ISO timestamp
_user_path(user_id)     → Path            — returns data/users/{user_id}.json
_load_template()        → dict            — reads profile_template.json, strips non-stat fields
_make_default(user_id)  → dict            — builds a brand-new user document from template
_sync_load(user_id)     → dict            — BLOCKING: reads file or creates it; always acquires per-user lock
_atomic_write(path, d)  → None            — writes to .tmp then os.replace() for crash safety
_sync_save(data)        → None            — BLOCKING: atomically saves dict to its user file
```

#### Atomic write safety

```
write data → user_id.tmp  (temp file, same directory)
         ↓
os.replace(tmp, target)  ← OS-level atomic rename; old file never partially overwritten
```

If the process dies mid-write, the `.tmp` file is left behind but the original `.json` is untouched. On next load, if the `.json` is corrupt, `_sync_load` recreates it from the template.

### Public async API

All public functions are `async` and safe to `await` from any cog.

---

#### `get_user(user_id, username=None) → dict`

Returns the full user document. If the file does not exist yet, it is created from the template.

```python
from utils import user_storage
data = await user_storage.get_user(ctx.author.id, ctx.author.name)
print(data["stats"]["messages_sent"])
```

---

#### `touch_user(user_id, username=None) → None`

Ensures the user file exists, increments `stats.messages_sent` by 1, and updates `meta.last_active` and `meta.updated_at`.

Call this on **every message** from real users (already done in `bot.py`'s `on_message`):

```python
# In bot.py on_message:
await user_storage.touch_user(message.author.id, str(message.author))
```

---

#### `record_activity(user_id, username, activity_type, name, extra=None) → None`

Records a command/interaction in the user's `activity` sub-dict.
- Increments `activity.counts[activity_type]`
- Increments `activity.by_name[name]`
- Prepends to `activity.recent` (max 100 entries kept)
- Increments `stats.commands_used`

```python
await user_storage.record_activity(user_id, username, "command", "profile")
```

---

#### `record_minigame_result(user_id, game_name, result, coins=0, username=None) → None`

Records a minigame play. `result` must be `'win'`, `'loss'`, or `'draw'`.

Internally:
- Updates `stats.minigames_played` (always)
- Updates `stats.minigames_won` (on win)
- Updates game-specific stat fields (e.g. `stats.trivia_wins`, `stats.wordle_losses`) via `_GAME_STAT_MAP`
- Updates `minigames.by_game.{game_name}` counters
- Prepends to `minigames.recent_plays` (max 100 entries)

**`_GAME_STAT_MAP`** — internal mapping for 15 named games:

```
trivia, wordle, hangman, memory, rps, coinflip, dice, minesweeper,
riddle, quick_math, typing_race, uno_gofish, flood, lights_out, sliding_puzzle
```

All other `game_name` values still update `minigames_played` / `minigames_won` and the `by_game` dict, but have no dedicated `stats.*` field.

```python
await user_storage.record_minigame_result(user_id, "wordle", "win", coins=50, username=username)
```

---

#### `increment_stat(user_id, stat_name, amount=1, username=None) → None`

Increments any numeric key under `stats` by `amount`. Creates the key at 0 if it does not exist.

```python
await user_storage.increment_stat(user_id, "tictactoe_wins", 1, username)
await user_storage.increment_stat(user_id, "total_coins_earned", reward, username)
```

---

#### `set_stat(user_id, stat_name, value, username=None) → None`

Sets any key under `stats` to an explicit value (replace, not increment).

```python
await user_storage.set_stat(user_id, "daily_streak", new_streak, username)
```

---

#### `record_game_state(user_id, username, game_name, state) → None`

Saves an arbitrary dict as a game-state snapshot under `games.{game_name}`:

```json
{
  "games": {
    "chess": {
      "updated_at": "...",
      "state": { "...arbitrary game state..." }
    }
  }
}
```

---

### Backwards-compatibility stubs

Several old cog signatures are still present to prevent crashes:

| Name | Behaviour |
|------|-----------|
| `init_user_storage_worker(loop=None)` | No-op. Prints a ready message. |
| `flush_user_storage_queue()` | No-op async stub. |
| `enqueue_user_storage(func, *args)` | Runs `func` directly in a thread. |
| `load_user` | Alias for `_sync_load` |
| `save_user` | Alias for `_sync_save` |
| `user_file` | Alias for `_user_path` |
| `get_user_file_simple` | Returns `str(path)` |
| `save_user_simple` | Injects `user_id` and calls `_sync_save` |

---

### Threading model

```
Discord event loop thread
      │
      │  await user_storage.increment_stat(...)
      │
      ▼
asyncio.to_thread( _do_blocking_fn )
      │
      ▼
Thread pool worker thread
      │  acquires per-user threading.Lock
      │  reads / mutates dict
      │  _atomic_write → .tmp → os.replace
      │  releases lock
      │
Done — event loop continues unblocked
```

There is **no batch queue**. Every write is immediate and direct for reliability. The `asyncio.to_thread` wrapper ensures the event loop is never blocked.

---

## 3. utils/stat_hooks.py

**File size:** 145 lines  
**Purpose:** A thin, zero-overhead wrapper around `user_storage` that can be called from **synchronous code** anywhere in a cog without needing to `await` and without risking a crash if `user_storage` is unavailable.

### The problem it solves

Many cogs are synchronous at the point where they need to record a stat (e.g. inside a `discord.ui.Button.callback` that already has other logic). Rather than scattering `asyncio.to_thread` or `ensure_future` calls everywhere, `stat_hooks` provides three simple one-liners that schedule the task and return immediately.

### Import

```python
from utils.stat_hooks import us_inc, us_mg, us_touch
```

Or for challenge tracking:

```python
from utils.stat_hooks import us_challenge
```

### Public functions

---

#### `us_touch(user_id, username=None) → None`

Ensures user file exists + refreshes `last_active`. Safe to call anywhere, returns immediately.

```python
us_touch(ctx.author.id, str(ctx.author))
```

---

#### `us_inc(user_id, stat_name, amount=1, username=None) → None`

Schedules `user_storage.increment_stat(...)` as a fire-and-forget `asyncio.Task`.

```python
us_inc(user_id, "blackjack_wins", 1, username)
us_inc(user_id, "total_coins_earned", reward, username)
```

---

#### `us_mg(user_id, game_name, result, coins=0, username=None) → None`

Schedules `user_storage.record_minigame_result(...)` as a fire-and-forget task.
`result` must be `'win'`, `'loss'`, or `'draw'`.

```python
us_mg(ctx.author.id, "trivia", "win", coins=20, username=str(ctx.author))
```

---

#### `us_set(user_id, stat_name, value, username=None) → None`

Schedules `user_storage.set_stat(...)`. Use for absolute-value updates (e.g. current streak).

```python
us_set(user_id, "daily_streak", new_streak, username)
```

---

#### `us_set_bot(bot) → None`

Registers the bot instance so `us_challenge` can reach the `GameChallenges` cog. Called once in `bot.py` after `bot` is created:

```python
# bot.py
from utils.stat_hooks import us_set_bot
us_set_bot(bot)
```

---

#### `us_challenge(user_id, event_type, amount=1, game_name=None) → None`

Synchronously notifies `GameChallenges.record_game_event(...)`. Fires challenge progress updates without any async overhead.

**Valid `event_type` values:**

| event_type | Trigger when |
|------------|-------------|
| `game_win` | Any game victory |
| `coin_earn` | Player earns coins |
| `game_played` | Any game played (requires `game_name`) |
| `word_game_win` | Win in a word game (wordle, hangman, etc.) |
| `math_game_win` | Win in a math game |
| `social_game` | Played a social activity |
| `board_game_win` | Win a board game |
| `puzzle_win` | Solve a puzzle |
| `trivia_correct` | Correct trivia answer |
| `speed_win` | Win a speed/reaction game |

```python
from utils.stat_hooks import us_challenge

# After a trivia win:
us_challenge(user_id, "trivia_correct")
us_challenge(user_id, "game_win")
us_challenge(user_id, "game_played", game_name="trivia")
```

### Internal `_task(coro)` helper

Stat hooks schedule coroutines using:
```python
def _task(coro):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        pass  # no running loop — skip silently
```

If there is no running event loop (e.g. in a test script), the call is silently dropped — it never raises.

---

## 4. utils/database.py

**File size:** 270 lines  
**Purpose:** An **opt-in SQLite backend** (`DatabaseManager`) as an alternative to the flat JSON files. Currently not used by any cog by default — it's available for future migration or hybrid use.

### Architecture

`DatabaseManager` is a **singleton** — only one instance is ever created:

```python
class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_connection()
        return cls._instance
```

Importing the module gives you the global instance:

```python
from utils.database import db
db.upsert_user(user_id, username)
```

### Database path resolution

```python
render_path = os.getenv("RENDER_DISK_PATH")
if render_path:
    self.db_path = os.path.join(render_path, "data", "database.db")
else:
    self.db_path = os.path.join(...root..., "data", "database.db")
```

Respects the same `RENDER_DISK_PATH` pattern as all other data files for Render.com deployment.

### Schema — 4 tables

#### `users`
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY,
    username      TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active   TIMESTAMP,
    total_commands          INTEGER DEFAULT 0,
    daily_streak            INTEGER DEFAULT 0,
    daily_longest_streak    INTEGER DEFAULT 0,
    total_coins_earned      INTEGER DEFAULT 0,
    total_coins_spent       INTEGER DEFAULT 0
);
```

#### `stats`
```sql
CREATE TABLE IF NOT EXISTS stats (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(user_id),
    stat_name  TEXT NOT NULL,
    stat_value NUMERIC DEFAULT 0,
    UNIQUE(user_id, stat_name)
);
```

#### `activity`
```sql
CREATE TABLE IF NOT EXISTS activity (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(user_id),
    time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type    TEXT NOT NULL,
    name    TEXT NOT NULL
);
```

#### `game_states`
```sql
CREATE TABLE IF NOT EXISTS game_states (
    user_id     INTEGER,
    game_name   TEXT,
    state_json  TEXT,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, game_name)
);
```

### Public API methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `initialize_schema()` | `→ None` | Creates all 4 tables if they don't exist (`CREATE TABLE IF NOT EXISTS`) |
| `upsert_user(user_id, username)` | `→ None` | INSERT or UPDATE user row, refreshes `last_active` |
| `update_stat(user_id, stat_name, value, increment=False)` | `→ None` | Set or increment a stat value |
| `increment_stat(user_id, stat_name, amount=1)` | `→ None` | Calls `update_stat(..., increment=True)` |
| `log_activity(user_id, activity_type, activity_name, timestamp=None)` | `→ None` | Inserts a row into `activity` |
| `increment_command_count(user_id)` | `→ None` | Updates `users.total_commands + 1` |
| `save_game_state(user_id, game_name, state_json)` | `→ None` | Upsert into `game_states` (JSON as string) |
| `get_user_data(user_id)` | `→ dict` | Returns full user data dict mirroring `user_storage` format |

### Context managers

All queries use `get_cursor(commit=False)` or `get_connection()`:

```python
@contextmanager
def get_cursor(self, commit: bool = False):
    with self.get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database query error: {e}")
        finally:
            cursor.close()
```

Errors are **logged but not re-raised** — the bot keeps running even if a DB query fails. Every connection is opened and closed per-query (no connection pooling) which is fine for SQLite.

### datetime adapters

Registered globally at module import time so `datetime.datetime` objects serialize to ISO strings and deserialize cleanly:

```python
sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)
```

### `get_user_data()` return format

Returns a dict that mirrors the `user_storage` structure for drop-in compatibility:

```python
{
  "user_id": ...,
  "username": ...,
  "stats": { "stat_name": float_value, ... },
  "games": { "game_name": parsed_dict, ... },
  "minigames": {"by_game": {}, "recent_plays": []},   # always empty (mock)
  "activity": {"counts": {}, "by_name": {}, "recent": []},  # always empty (mock)
  "meta": {
    "created_at": str,
    "updated_at": str,
    "last_active": str
  }
}
```

---

## 5. utils/embed_styles.py

**File size:** 380 lines  
**Purpose:** A centralized embed/colour/emoji factory that gives the bot a consistent visual identity across all cogs.

### Three exports

1. **`Colors`** — Named hex constants
2. **`Emojis`** — Named emoji string constants
3. **`EmbedBuilder`** — Static factory methods for typed embeds

---

### `Colors` class

A flat namespace of `int` hex colour values. Using these instead of raw hex values ensures consistent branding.

**Primary colours:**

| Name | Hex | Description |
|------|-----|-------------|
| `PRIMARY` | `0x5865F2` | Discord Blurple |
| `SUCCESS` | `0x57F287` | Vibrant Green |
| `WARNING` | `0xFEE75C` | Bright Yellow |
| `ERROR` | `0xED4245` | Vibrant Red |
| `INFO` | `0x00D9FF` | Cyan Blue |

**Category colours:**

| Name | Hex | Used for |
|------|-----|---------|
| `ECONOMY` | `0xF1C40F` | Economy commands |
| `MINIGAMES` | `0xE91E63` | Game commands |
| `LEVELING` | `0x9B59B6` | XP / leveling |
| `MUSIC` | `0x1DB954` | Music features |
| `SOCIAL` | `0x3498DB` | Social commands |
| `GAMBLING` | `0xE74C3C` | Casino / gambling |
| `TCG` | `0xFF6B6B` | Trading card game |
| `BOARD_GAMES` | `0x95A5A6` | Board games |
| `FISHING` | `0x3498DB` | Fishing system |
| `PETS` | `0xFF69B4` | Pet commands |
| `QUESTS` | `0xFFD700` | Quest system |

**Item tier colours:**

| Name | Hex | Shorthand |
|------|-----|-----------|
| `COMMON` | `0x95A5A6` | `c` |
| `UNCOMMON` | `0x2ECC71` | `b` (bronze) |
| `RARE` | `0x3498DB` | `s` (silver) |
| `EPIC` | `0x9B59B6` | `g` (gold) |
| `LEGENDARY` | `0xF39C12` | `a` (amber) |
| `MYTHIC` | `0xE91E63` | `p` (platinum) |
| `DIVINE` | `0xFFD700` | `x` |

---

### `Emojis` class

Named string constants. Organised into groups:

- **Status:** `SUCCESS`, `ERROR`, `WARNING`, `INFO`, `LOADING`, `SHIELD`, `TOOLS`, `LEVEL_UP`
- **Economy:** `COIN`, `BANK`, `SHOP`, `GIFT`, `TREASURE`, `DIAMOND`
- **Games:** `GAME`, `DICE`, `CARDS`, `TROPHY`, `MEDAL`, `STAR`, `FIRE`
- **Social:** `CROWN`, `HEART`, `PARTY`, `SPARKLES`, `ROCKET`
- **Music:** `MUSIC`, `NOTE`, `HEADPHONES`, `RADIO`, `MIC`
- **Leveling:** `LEVEL_UP`, `XP`, `RANK`
- **Ranking helpers:** `NUMBERS` (1️⃣–🔟 list), `MEDALS_RANK` (🥇🥈🥉 list)

---

### `EmbedBuilder` class

All methods are `@staticmethod` — import and call directly:

```python
from utils.embed_styles import EmbedBuilder, Colors
embed = EmbedBuilder.success("Title", "Description")
```

#### `create(...)` — base method

```python
EmbedBuilder.create(
    title=None,
    description=None,
    color=Colors.PRIMARY,
    author_name=None,
    author_icon=None,
    thumbnail=None,
    image=None,
    footer_text=None,
    footer_icon=None,
    timestamp=False,       # adds datetime.utcnow() if True
    fields=None            # list of {"name": str, "value": str, "inline": bool}
) → discord.Embed
```

#### Typed shortcuts

| Method | Colour | Title prefix |
|--------|--------|-------------|
| `success(title, desc)` | `SUCCESS` (green) | `✅ {title}` |
| `error(title, desc)` | `ERROR` (red) | `❌ {title}` |
| `warning(title, desc)` | `WARNING` (yellow) | `⚠️ {title}` |
| `info(title, desc)` | `INFO` (cyan) | `ℹ️ {title}` |
| `economy(title, desc)` | `ECONOMY` (gold) | `🪙 {title}` |
| `game(title, desc)` | `MINIGAMES` (pink) | `🎲 {title}` |
| `leveling(title, desc)` | `LEVELING` (purple) | `📈 {title}` |
| `music(title, desc)` | `MUSIC` (green) | `🎵 {title}` |

All typed shortcuts accept `**kwargs` and forward them to `create(...)`.

#### `leaderboard(title, entries, user_field, value_field)` → `discord.Embed`

Formats up to 10 entries with medal emojis (🥇🥈🥉) for top 3 and `#N` for the rest. Adds `TROPHY` emoji to title and includes a UTC timestamp.

```python
entries = [{"user": "Alice", "value": 5000}, {"user": "Bob", "value": 3200}]
embed = EmbedBuilder.leaderboard("Top Players", entries)
```

#### `profile(user, stats)` → `discord.Embed`

Creates a profile embed for a Discord member: uses their display colour (falls back to `PRIMARY`), sets their avatar as thumbnail, and adds `stats` dict entries as inline fields.

#### `progress_bar(percentage, length=10)` → `str`

Returns a text progress bar: `████████░░ 80%`

```python
bar = EmbedBuilder.progress_bar(75)  # → "███████░░░ 75%"
```

#### `format_number(number)` → `str`

Formats large integers with K/M/B suffixes:
- `< 1,000` → `1,234`
- `≥ 1,000` → `1.2K`
- `≥ 1,000,000` → `1.5M`
- `≥ 1,000,000,000` → `2.1B`

#### `tier_color(tier)` → `int`

Maps tier name/shorthand to the corresponding colour constant. Accepts both long names (`"legendary"`) and single-char shorthands (`"a"`).

### Quick-access module-level functions

For compatibility with code that doesn't use the class syntax:

```python
from utils.embed_styles import create_embed, success_embed, error_embed, warning_embed, info_embed
```

All are thin wrappers: `create_embed(*args, **kwargs)` → `EmbedBuilder.create(*args, **kwargs)`

---

## 6. utils/performance.py

**File size:** ~60 lines  
**Purpose:** A simple in-memory cache for JSON config files, reducing redundant disk reads.

### `ConfigCache` class

```python
class ConfigCache:
    _cache_duration = timedelta(minutes=5)   # TTL: 5 minutes

    def get(self, file_path, default=None) → dict
    def invalidate(self, file_path) → None
    def clear() → None
```

#### `get(file_path, default=None)`

Returns cached data if younger than 5 minutes. Otherwise reads and parses the JSON file from disk, caches it, and returns it. On `FileNotFoundError` or `JSONDecodeError`, returns `default or {}`.

```python
from utils.performance import config_cache
data = config_cache.get("data/server_configs.json", default={})
```

#### `invalidate(file_path)`

Removes a specific path from the cache, forcing a fresh read on the next `get()`. Call this after writing to a config file:

```python
config_cache.invalidate("data/server_configs.json")
```

#### `clear()`

Wipes the entire cache. Called when a bulk reload is needed.

### Global instance

```python
# module-level
config_cache = ConfigCache()
```

All importers share the same `config_cache` instance, so cache hits are shared across cogs.

### Important limitation

`ConfigCache` caches the **parsed dict** — it does **not** use file `mtime` to detect external changes. If another process or cog writes to a file, the cache will serve stale data for up to 5 minutes unless `invalidate()` is called explicitly.

> ⚠️ **Note:** This cache is intentionally simple. For the primary data files (economy.json, etc.) cogs keep the data in memory and do not use `ConfigCache`. `ConfigCache` is most useful for infrequently-changing config files like `server_configs.json` when accessed from non-cog utility code.

---

## 7. utils/card_visuals.py

**File size:** 646 lines  
**Purpose:** PIL-based card game image renderer. Creates PNG images of card hands, tables, and game states as `discord.File` objects ready to send directly to Discord channels.

### Dependencies

```python
from PIL import Image, ImageDraw, ImageFont
import io
import discord
```

Requires `Pillow` to be installed (`pip install Pillow`).

### Constants

```python
CARD_WIDTH  = 80
CARD_HEIGHT = 112
CARD_SPACING = 10

FELT_GREEN  = (53, 101, 77)     # Table background
FELT_DARK   = (35, 70, 55)      # Table border
CARD_WHITE  = (255, 255, 255)
TEXT_GOLD   = (255, 215, 0)
BUTTON_BG   = (70, 120, 90)

SUIT_DISPLAY = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
SUIT_COLORS  = {'h': (220,20,60), 'd': (220,20,60), 'c': (0,0,0), 's': (0,0,0)}
SUIT_NAMES_PL = {'h': 'kier', 'd': 'karo', 'c': 'trefl', 's': 'pik'}
```

Note: `SUIT_NAMES_PL` uses Polish names because the `assets/cards/` image files are named in Polish (e.g. `as_kier.png` for Ace of Hearts).

### Card string format

Cards are represented as 2-character strings:
- Rank: `2`–`9`, `10`, `j` (Jack), `q` (Queen), `k` (King), `a` (Ace)
- Suit: `h` (hearts), `d` (diamonds), `c` (clubs), `s` (spades)

Examples: `"Ah"` = Ace of Hearts, `"10s"` = 10 of Spades, `"Kd"` = King of Diamonds

### Image asset loading

```
assets/cards/{deck}/{rank_name}_{suit_name}.png
```

Supported decks: `classic`, `dark`, `platinum` (falls back to `classic` if not found).

All loaded images are cached in `CARD_IMAGE_CACHE` (dict keyed by `"{deck}_{rank}_{suit}_{size}"`):

```python
def load_card_image(rank, suit, deck='classic', size=None) → Image | None
def load_card_back(deck='classic', size=None) → Image | None
```

### Low-level drawing functions

These are internal building blocks used by the high-level renderers:

```python
get_font(size, bold=False) → ImageFont
    # Returns arial.ttf / arialbd.ttf with fallback to default PIL font

parse_card(card_str) → (rank, suit)
    # "Ah" → ("a", "h")

draw_card(draw, x, y, rank, suit, ...)
    # Draws one card at (x,y) on the provided ImageDraw context
    # If show_face=False, draws card back pattern
    # Falls back to drawn symbols if PNG asset not found

draw_card_string(draw, x, y, card_str, ...)
    # Parses card_str and calls draw_card
```

### High-level renderer functions

All return `discord.File` objects ready to pass directly to `ctx.send()` or `interaction.followup.send()`.

---

#### `create_hand_image(cards, title, deck, width, height) → discord.File`

Creates a hand-of-cards image on a green felt background.

```python
file = create_hand_image(["Ah", "Kd", "10s"], title="Your Hand", deck='classic')
await ctx.send(file=file)
```

- Auto-sizes width to fit the number of cards
- Renders PNG at `CARD_WIDTH × CARD_HEIGHT` per card
- Returns `discord.File(filename='hand.png')`

---

#### `create_table_image(community_cards, title, deck, info_text, width, height, show_backs) → discord.File`

Renders cards on a poker table (green felt). Used for community cards in Hold'em.

- `show_backs=True` renders card backs (used during pre-flop)
- Accepts optional `info_text` shown below the title
- Returns `discord.File(filename='table.png')`

---

#### `create_comparison_image(player_cards, opponent_cards, ..., result_text) → discord.File`

Side-by-side hand comparison with "VS" divider. Used in War card game.  
`result_text` changes colour: green for wins, red for losses, gold otherwise.

Returns `discord.File(filename='comparison.png')`

---

#### `create_blackjack_image(player_hand, dealer_hand, player_total, dealer_total, ...) → discord.File`

Full blackjack game state visualization:
- Title: `♠ BLACKJACK ♥` in gold
- Dealer section at top with total (shows `?` if `show_dealer_card=False`)
- Player section at bottom with their total
- Dealer's hole card rendered face-down until reveal

```python
file = create_blackjack_image(
    player_hand=["Ah", "7c"],
    dealer_hand=["Kh", "5d"],
    player_total=18,
    dealer_total=15,
    show_dealer_card=False    # hide hole card
)
```

Returns `discord.File(filename='blackjack.png')`

---

#### `create_war_image(player_card, opponent_card, ..., result_text) → discord.File`

Single-turn War visualization. Each card uses its respective player's deck:
```python
file = create_war_image("As", "Kh", player_name="Alice", opponent_name="Bot",
                        deck='platinum', opponent_deck='classic',
                        result_text="Alice wins!")
```

Returns `discord.File(filename='war.png')`

---

#### `create_poker_table_image(community_cards, players_data, pot, current_phase, ...) → discord.File`

Full Texas Hold'em table visualization. The most complex renderer.

`players_data` is a list of dicts:

```python
players_data = [
    {
        "name": "Alice",
        "cards": ["Ah", "Kd"],     # or [] for face-down
        "chips": 1500,
        "bet": 100,
        "status": "turn",           # 'active' | 'folded' | 'all_in' | 'dealer' | 'turn'
        "is_bot": False
    },
    ...
]
```

Features:
- Community cards rendered in center
- Player boxes along the bottom row
- Current-turn player highlighted in green
- Folded players dimmed
- All-in players highlighted in red
- Dealer marker highlighted in gold
- Pot + current phase shown at top

Returns `discord.File(filename='poker_table.png')`

---

## 8. Dependency Map

```
utils/ internal dependencies:

stat_hooks.py
    └── imports → user_storage.py  (optional, fails gracefully)

database.py
    └── No utils imports (standalone)

embed_styles.py
    └── imports discord (external only)

performance.py
    └── No utils imports (standalone)

card_visuals.py
    └── imports discord, PIL (external only)

user_storage.py
    └── No utils imports (standalone)
```

```
Cog → Utils dependencies:

bot.py              → user_storage (touch_user on every message)
                    → stat_hooks (us_set_bot registration)

blackjack.py        → card_visuals (create_blackjack_image, create_hand_image)
poker.py            → card_visuals (create_poker_table_image, create_table_image)
cardgames.py        → card_visuals (create_war_image, create_hand_image)
cards_enhanced.py   → card_visuals

Any game cog        → stat_hooks (us_inc, us_mg, us_touch, us_challenge)
Any cog             → embed_styles (EmbedBuilder, Colors, Emojis)
Server config cogs  → performance (config_cache.get)
```

---

## 9. Usage Patterns & Best Practices

### Pattern 1: Record a game result (most common)

```python
# Inside any cog, after a game concludes:
from utils.stat_hooks import us_mg, us_inc, us_challenge

# 1. Record the minigame result (updates minigames.by_game + global counters)
us_mg(ctx.author.id, "trivia", "win", coins=50, username=str(ctx.author))

# 2. Increment any additional stats
us_inc(ctx.author.id, "trivia_wins", 1, str(ctx.author))

# 3. Notify challenge system
us_challenge(ctx.author.id, "trivia_correct")
us_challenge(ctx.author.id, "game_win")
us_challenge(ctx.author.id, "game_played", game_name="trivia")
```

### Pattern 2: Send a styled embed

```python
from utils.embed_styles import EmbedBuilder, Colors

# Typed shortcut:
embed = EmbedBuilder.success("Won!", f"You earned 500 coins.")
await ctx.send(embed=embed)

# Or economy-styled:
embed = EmbedBuilder.economy("Balance", f"You have **1,234** 🪙")
await ctx.send(embed=embed)

# With fields:
embed = EmbedBuilder.create(
    title="📊 Stats",
    color=Colors.INFO,
    fields=[
        {"name": "Wins", "value": "42", "inline": True},
        {"name": "Losses", "value": "13", "inline": True},
    ]
)
await ctx.send(embed=embed)
```

### Pattern 3: Send a card image (card games)

```python
from utils.card_visuals import create_hand_image, create_blackjack_image

async def show_hand(ctx, cards):
    file = create_hand_image(cards, title=f"{ctx.author.display_name}'s Hand")
    await ctx.send(file=file)
```

### Pattern 4: Cached config read

```python
from utils.performance import config_cache

def get_server_config(guild_id: str) -> dict:
    all_configs = config_cache.get("data/server_configs.json", default={})
    return all_configs.get(guild_id, {})
```

### Pattern 5: Direct user data read

```python
from utils import user_storage

# Read full user document:
data = await user_storage.get_user(ctx.author.id)
stats = data.get("stats", {})
trivia_wins = stats.get("trivia_wins", 0)

# Set a specific stat:
await user_storage.set_stat(ctx.author.id, "daily_streak", 7, str(ctx.author))
```

### What NOT to do

```python
# ❌ Never cache a cog reference at __init__ time:
self.storage = self.bot.get_cog("UserStorage")   # UserStorage is not a cog

# ❌ Never call _sync_load directly from async code:
data = user_storage._sync_load(user_id)           # blocks the event loop

# ❌ Never await stat_hooks functions — they are sync fire-and-forget:
await us_inc(user_id, "wins")                     # TypeError: not a coroutine

# ✅ Correct:
us_inc(user_id, "wins")                           # sync, schedules a Task
data = await user_storage.get_user(user_id)       # async, non-blocking
```

---

*This document covers all 6 files in `utils/` — ~1,922 lines total.*  
*Last Updated: 04.03.2026*
