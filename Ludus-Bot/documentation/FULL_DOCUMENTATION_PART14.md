# Ludus Bot — Full Documentation Part 14: Integration Guide

> **Covers:** How all cogs connect — `bot.py` startup, inter-cog communication patterns, shared state, utility infrastructure, and data-flow diagrams.

---

## Table of Contents

1. [Overview](#1-overview)
2. [bot.py — The Integration Hub](#2-botpy--the-integration-hub)
   - 2.1 [Startup Sequence](#21-startup-sequence)
   - 2.2 [Shared Bot-Level State](#22-shared-bot-level-state)
   - 2.3 [Custom Command Tree](#23-custom-command-tree)
   - 2.4 [Activity Worker](#24-activity-worker)
3. [The `get_cog()` Pattern](#3-the-get_cog-pattern)
   - 3.1 [Graceful Degradation](#31-graceful-degradation)
   - 3.2 [Standard Usage Pattern](#32-standard-usage-pattern)
4. [Economy as the Central Hub](#4-economy-as-the-central-hub)
   - 4.1 [Economy API Surface](#41-economy-api-surface)
   - 4.2 [Who Calls Economy](#42-who-calls-economy)
5. [Profile as the Display Layer](#5-profile-as-the-display-layer)
6. [BotLogger as the Passive Observer](#6-botlogger-as-the-passive-observer)
   - 6.1 [Passive Error Capture](#61-passive-error-capture)
   - 6.2 [Active Logging Calls](#62-active-logging-calls)
7. [ServerConfig as the Permission Gate](#7-serverconfig-as-the-permission-gate)
8. [Blacklist as the Access Gate](#8-blacklist-as-the-access-gate)
9. [GameControl as the Cleanup Utility](#9-gamecontrol-as-the-cleanup-utility)
10. [GlobalEvents → Economy Flow](#10-globalevents--economy-flow)
11. [Achievements Integration](#11-achievements-integration)
12. [GameStats Integration](#12-gamestats-integration)
13. [GlobalLeaderboard Integration](#13-globalleaderboard-integration)
14. [Farming ↔ FarmShop Coupling](#14-farming--farmshop-coupling)
15. [Mafia Custom Roles — sys.modules Bridge](#15-mafia-custom-roles--sysmodules-bridge)
16. [Utils Infrastructure](#16-utils-infrastructure)
    - 16.1 [utils/user_storage.py](#161-utilsuser_storagepy)
    - 16.2 [utils/database.py](#162-utilsdatabasepy)
    - 16.3 [utils/stat_hooks.py](#163-utilsstat_hookspy)
    - 16.4 [utils/card_visuals.py](#164-utilscard_visualspy)
    - 16.5 [utils/embed_styles.py](#165-utilsembed_stylespy)
    - 16.6 [utils/performance.py](#166-utilsperformancepy)
17. [Data File Sharing Between Cogs](#17-data-file-sharing-between-cogs)
18. [Complete Cross-Cog Dependency Map](#18-complete-cross-cog-dependency-map)

---

## 1. Overview

Ludus Bot's architecture follows a **hub-and-spoke** model:

- **`Economy`** is the central economic hub — nearly every gameplay cog calls it to give or take PsyCoins.
- **`BotLogger`** is a passive observer — it intercepts errors from all cogs without them needing to know it exists.
- **`ServerConfig`** gates slash commands globally via the custom `BotCommandTree`.
- **`Blacklist`** gates prefix and slash commands via event listeners.
- **`bot.py`** owns shared state (active games, data directory, activity queue) that all cogs access through `self.bot`.

The communication mechanism throughout is `self.bot.get_cog("Name")` — a zero-coupling lookup that returns `None` if the cog isn't loaded, allowing every integration to degrade gracefully.

---

## 2. bot.py — The Integration Hub

**File:** `bot.py` (316 lines)

### 2.1 Startup Sequence

```
python start.py
    └── bot.run(TOKEN)
            └── setup_hook()          ← fires before connecting to Discord
                    ├── Load UNO emoji mapping (constants.UNO_BACK_EMOJI)
                    ├── load_cogs()           ← iterate ./cogs/, load every .py and package
                    ├── user_storage.init_user_storage_worker(bot.loop)
                    └── asyncio.create_task(activity_worker())
            └── on_ready()            ← fires after Discord connection established
                    ├── stat_hooks.us_set_bot(bot)
                    ├── Print connected summary
                    ├── bot.tree.sync()       ← register slash commands globally
                    └── bot.change_presence(activity=discord.Game("minigames"))
```

**`load_cogs()`** iterates `./cogs/`, loading both:
- Single-file cogs: `.py` files → `cogs.<name>`
- Package cogs: subdirectories with `__init__.py` → `cogs.<dirname>`

Each extension is loaded with `await bot.load_extension(f"cogs.{name}")`. Failures are printed but do not stop other cogs from loading.

### 2.2 Shared Bot-Level State

After initialization, `bot` carries these attributes that all cogs access via `self.bot`:

| Attribute | Type | Set In | Purpose |
|-----------|------|--------|---------|
| `bot.data_dir` | `str` | `bot.py` init | Absolute path to persistent data directory (`RENDER_DISK_PATH` or `./data/`) |
| `bot.owner_ids` | `set[int]` | `config.json` load | Set of owner user IDs; used by `Owner` cog's `cog_check` |
| `bot.active_games` | `dict` | `bot.py` init | Shared game state dict (used by some multiplayer cogs) |
| `bot.active_lobbies` | `dict` | `bot.py` init | Shared lobby state dict |
| `bot.active_minigames` | `dict` | `bot.py` init | Shared minigame state dict |
| `bot.pending_rematches` | `dict` | `bot.py` init | Pending rematch requests |
| `bot.tree` | `BotCommandTree` | `commands.Bot()` | Slash command tree with disabled-command checking |

**`bot.data_dir` resolution:**
```python
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH")
if RENDER_DISK_PATH:
    BASE_DATA_DIR = RENDER_DISK_PATH          # Production: Render.com persistent disk
else:
    BASE_DATA_DIR = os.path.join(os.getcwd(), "data")  # Development: ./data/
bot.data_dir = BASE_DATA_DIR
```

Every cog that needs to save data constructs its file path using this pattern:
```python
DATA_FILE = os.path.join(os.getenv("RENDER_DISK_PATH", "data"), "filename.json")
```

### 2.3 Custom Command Tree

`BotCommandTree(app_commands.CommandTree)` overrides `interaction_check`:

```python
async def interaction_check(self, interaction: discord.Interaction) -> bool:
    server_config_cog = interaction.client.get_cog("ServerConfig")
    if not server_config_cog:
        return True
    guild_cfg = server_config_cog.get_server_config(str(interaction.guild.id))
    disabled = guild_cfg.get("disabled_commands", [])
    if interaction.command.name in disabled:
        await interaction.response.send_message(
            f"❌ Command `{cmd_name}` is disabled on this server.", ephemeral=True
        )
        return False
    return True
```

This check runs **before every slash command handler** without requiring individual cogs to implement it. The `ServerConfig` cog provides the disabled-command list, but if that cog isn't loaded the check returns `True` (fail-open).

### 2.4 Activity Worker

The activity worker is a background task running from startup that batches-writes user interaction data to `user_activity.json`:

```python
async def activity_worker():
    batch = []
    activity_file = os.path.join(bot.data_dir, "user_activity.json")
    while True:
        # Accumulate up to BATCH_SIZE=50 entries, flush on BATCH_INTERVAL=2.0s timeout
        async with aiofiles.open(activity_file, "a") as f:
            lines = [json.dumps(entry) + "\n" for entry in batch]
            await f.writelines(lines)
```

Cogs enqueue activity records via `_record_user_activity(user_id, username, type, name, extra)`, which calls `activity_queue.put_nowait(data)`. This prevents file I/O from blocking command handlers.

---

## 3. The `get_cog()` Pattern

### 3.1 Graceful Degradation

Every inter-cog call in Ludus Bot follows the same defensive pattern:

```python
economy_cog = self.bot.get_cog("Economy")
if not economy_cog:
    await ctx.send("❌ Economy system not loaded!")
    return
```

If a cog is absent (failed to load, was unloaded, or not yet loaded), the calling cog either:
- Returns an error message to the user
- Silently skips the action (for non-critical features like logging)
- Falls through to a fallback (as in `owner.py`'s TCG resolution chain)

This means the bot can run with a subset of cogs, and a crashed/disabled cog doesn't cascade failures to every cog that depends on it.

### 3.2 Standard Usage Pattern

```python
# 1. Lookup (per-call, not cached)
cog = self.bot.get_cog("CogName")

# 2. Guard
if not cog:
    # handle absence
    return

# 3. Use cog's public API
cog.some_method(args)
result = cog.some_attribute
```

`get_cog()` is called at **every invocation**, not cached at `__init__`. This allows hot-reloading of cogs (`L!reload`) without stale references breaking dependent cogs.

---

## 4. Economy as the Central Hub

**Cog name:** `"Economy"` (registered in `economy.py`)

### 4.1 Economy API Surface

The public API used by other cogs:

| Method / Attribute | Signature | Purpose |
|--------------------|-----------|---------|
| `get_balance(user_id)` | `(int) → int` | Returns current PsyCoin balance; creates default entry if missing |
| `add_coins(user_id, amount, source)` | `(int, int, str)` | Adds coins and logs the source for tracking |
| `remove_coins(user_id, amount)` | `(int, int) → bool` | Returns `False` if balance insufficient |
| `add_item(user_id, item_id, qty)` | `(int, str, int)` | Adds item to inventory |
| `remove_item(user_id, item_id, qty)` | `(int, str, int) → bool` | Removes item; returns `False` if insufficient |
| `economy_data` | `dict[str, dict]` | Direct access to full economy dict (used by `owner.py` for `godmode`) |
| `shop_items` | `dict[str, dict]` | Item catalog — name, price, effect, description |
| `save_economy()` | `()` | Writes `economy_data` to disk (atomic write) |

### 4.2 Who Calls Economy

```
Economy.add_coins() ← called by:
    gambling.py        (wins from slots, roulette, blackjack, poker, dice, crash, mines)
    blackjack.py       (BJ win payouts)
    poker.py           (pot distribution)
    heist.py           (raid success rewards)
    daily_rewards.py   (daily claim coins)
    counting.py        (milestone coin rewards)
    chess_checkers.py  (wager games win payout)
    boardgames.py      (wager games win payout)
    boardgames_enhanced.py (same)
    globalevents.py    (WAR/WorldBoss/Hunt rewards)
    owner.py           (raincoins, chaos, spawn, lottery)
    dueling.py         (duel wager resolution)
    cardgames.py       (card game wins)
    cards_enhanced.py  (same)
    marriage.py        (divorce fee refund, ring cost)
    businesses.py      (business income)
    business.py        (business purchase)
    farming.py         (harvest sell proceeds)

Economy.remove_coins() ← called by:
    gambling.py        (bets placed)
    blackjack.py       (bet placed)
    poker.py           (blind, raise, call)
    heist.py           (entry fee)
    chess_checkers.py  (wager deduction)
    boardgames.py      (wager deduction)
    marriage.py        (ring purchase, divorce fee)
    business.py        (business purchase)
    businesses.py      (business upgrade)
    farmshop.py        (seed/tool purchase)
    dueling.py         (duel bet deduction)

Economy.add_item() ← called by:
    owner.py           (giveitem, godmode)

Economy.get_balance() ← called by:
    gambling.py        (display current balance)
    blackjack.py       (validate bet)
    poker.py           (validate bet)
    owner.py           (addcoins result display)
    any cog showing balance info
```

The Economy cog is the **only** authoritative source for PsyCoin balances. No cog maintains its own coin counter — all financial state flows through `economy.json`.

---

## 5. Profile as the Display Layer

**Cog name:** `"Profile"`

The Profile cog holds per-user metadata (bio, badges, title, color, stats) that is separate from the Economy cog's financial data.

```
Profile.data[] ← read by:
    gambling.py        (update gambling_stats in profile)
    reputation.py      (write rep received/given to profile)
    farming.py         (update farm profile stats)
    marriage.py        (write partner_id to profile)
    serverinfo.py      (direct JSON read — no cog call)
```

**Notable pattern:** `serverinfo.py`'s `_build_userinfo_embed()` reads `profiles.json` and `economy.json` directly with `open()` rather than calling the Profile or Economy cog. This avoids a cog dependency for a read-only display command and works even if those cogs are not loaded.

---

## 6. BotLogger as the Passive Observer

**Cog name:** `"BotLogger"` (registered in `bot_logger.py`)

### 6.1 Passive Error Capture

`BotLogger` receives errors from all cogs through Discord.py's event system without any cog needing to reference it:

```
discord.py           BotLogger listener
─────────── ──────────────────────────────────────────
on_command_error  → @commands.Cog.listener()
                    on_command_error(ctx, error)
                    → categorize → log() → Discord embed

on_application_command_error → on_application_command_error(interaction, error)
                    → categorize → log() → Discord embed

on_error          → on_error(event, *args, **kwargs)
                    → format_exc() → log() → Discord embed
```

The `on_command_error` listener in BotLogger doesn't interfere with other error handlers — it observes, not intercepts.

### 6.2 Active Logging Calls

Cogs that explicitly call BotLogger:

```
globalevents.py:
    logger = self.bot.get_cog("BotLogger")
    if logger:
        await logger.log_event_spawn(event_type, guild_id, spawner_id, details)
        await logger.log_event_end(event_type, details)

owner.py:
    logger = self.bot.get_cog("BotLogger")
    if logger:
        await logger.log_owner_command(ctx, "stats update", "...")
    logger_cog = self.bot.get_cog("BotLogger")
    if logger_cog:
        await logger_cog.log_owner_command(ctx.author, "L!update global", "...")
```

All active calls use the `if logger:` guard — if BotLogger is not loaded, these calls are silently skipped.

---

## 7. ServerConfig as the Permission Gate

**Cog name:** `"ServerConfig"`

The ServerConfig cog stores per-guild configuration in `server_configs.json`. Its primary integration points:

**1. BotCommandTree** (in `bot.py`):
```python
guild_cfg = server_config_cog.get_server_config(str(interaction.guild.id))
disabled = guild_cfg.get("disabled_commands", [])
if interaction.command.name in disabled:
    # Block the slash command
```

This gates **every** slash command before it reaches the handler.

**2. Mining cog**:
```python
server_config_cog = bot.get_cog("ServerConfig")
# Reads per-guild settings for mining reward multipliers and channel restrictions
```

**3. Farming cog** and others read server-specific channel IDs for event announcements.

The `get_server_config(guild_id)` method returns a default config if the guild has no saved config, ensuring new guilds work without manual setup.

---

## 8. Blacklist as the Access Gate

**Cog name:** `"Blacklist"`

Unlike ServerConfig (which gates specific commands), Blacklist gates **all** bot interaction at the user and server level. It operates through two listeners that fire before command logic:

```
User runs L!command
    └── on_command listener (Blacklist)
            ├── _load()  ← reads blacklist.json fresh from disk
            ├── check ctx.author.id in data["users"]
            ├── check ctx.guild.id in data["servers"]
            └── raise CheckFailure if blocked  ← command aborted

User uses /slash-command
    └── on_interaction listener (Blacklist)
            ├── _load()  ← fresh read
            ├── check interaction.user.id
            └── check interaction.guild_id
```

No cog needs to implement its own blacklist check — the listeners handle it centrally. The fresh disk read on every command ensures immediate effect after blacklisting without requiring a bot restart.

---

## 9. GameControl as the Cleanup Utility

**Cog name:** `"GameControl"`

GameControl provides emergency cleanup for **all** game cogs through a single unified command. It uses `get_cog()` to reach each game cog's in-memory state dict and removes the user's entry:

```
L!stop / /stop
    ├── get_cog("CardGames")         → del active_games[id]
    ├── get_cog("FishingAkinatorFun") → del active_akinator[user_id]
    │                                  del active_drawings[channel_id]
    ├── get_cog("MiniGames")         → del active_wordle[user_id]
    │                                  del active_trivia[channel_id]
    └── get_cog("BoardGames")        → del active_games[id]
```

The game cogs themselves do not need to implement a "stop" command — they only need to maintain their state in a known dict attribute that GameControl can reach.

---

## 10. GlobalEvents → Economy Flow

The GlobalEvents cog triggers Economy rewards on event completion:

```
GlobalEvents.defeat_worldboss(bot, event_data)
    ├── economy_cog = bot.get_cog("Economy")
    ├── For each participant (by damage tier):
    │   ├── Top tier (>20% dmg):    +15,000 coins
    │   ├── Mid tier (>5% dmg):     +7,500 coins
    │   └── Base tier (participated): +2,500 coins
    └── logger.log_event_end(...)

GlobalEvents.resolve_war(bot, event_data)
    ├── economy_cog = bot.get_cog("Economy")
    ├── Winning faction members: +10,000 coins
    └── All participants: +2,000 coins (participation)

GlobalEvents.end_hunt(bot, event_data)
    ├── economy_cog = bot.get_cog("Economy")
    └── Top hunters: scaled coin rewards
```

All `economy_cog` calls go through `add_coins(user_id, amount, source)` where `source` is event-specific (e.g. `"worldboss_reward"`, `"war_victory"`) for tracking.

Additionally, `globalevents.py` calls `BotLogger` directly when spawning or ending events:
```python
logger = self.bot.get_cog("BotLogger")
if logger:
    await logger.log_event_spawn(event_type, guild_id, spawner_id)
```

---

## 11. Achievements Integration

**Cog name:** `"Achievements"`

Achievements are triggered by other cogs after significant milestones. The calling cogs obtain the achievement cog and call its checking/granting method:

```python
# Pattern used in boardgames.py, social.py:
ach_cog = bot.get_cog("Achievements")
if ach_cog:
    await ach_cog.check_and_grant(user_id, trigger_type, context)
```

**Who triggers achievements:**
- `boardgames.py` — after a game win (win streak, first win, etc.)
- `social.py` — after hug/pat/etc. interactions (social milestones)
- Other gameplay cogs call in after significant events

The Achievements cog is purely **reactive** — no cog pushes directly to `user_achievements.json`. All achievement state flows through the Achievements cog's methods, which handle the grant logic, deduplication (don't award twice), and persistence.

---

## 12. GameStats Integration

**Cog name:** `"GameStats"`

The GameStats cog tracks per-user game statistics (wins, losses, draws, streak). It is called by skill-based game cogs after each game result:

```
chess_checkers.py — after every game result:
    game_stats_cog = self.bot.get_cog("GameStats")
    if game_stats_cog:
        game_stats_cog.record_result(user_id, game_type, result)  # "win"/"loss"/"draw"

boardgames.py — after game completion:
    game_stats_cog = bot.get_cog("GameStats")
    if game_stats_cog:
        game_stats_cog.record_result(user_id, game_name, outcome)
```

`chess_checkers.py` has the most intensive GameStats integration — it calls `get_cog("GameStats")` at every possible game conclusion path (checkmate, resignation, timeout, stalemate) to ensure accurate tracking regardless of how the game ends.

`game_stats.json` is the persistence layer for these stats, readable via `L!gamestats` and `/gamestats` commands in the GameStats cog.

---

## 13. GlobalLeaderboard Integration

**Cog name:** `"GlobalLeaderboard"`

The GlobalLeaderboard ranks servers against each other using an aggregated score. It is a **read-only consumer** — other cogs don't push to it during normal operation. Score is calculated on-demand:

```python
# In owner.py (L!stats):
global_lb_cog = self.bot.get_cog("GlobalLeaderboard")
if global_lb_cog and hasattr(global_lb_cog, 'data'):
    score = global_lb_cog.calculate_server_score(guild_id)
    servers_ranked = len([s for s,d in global_lb_cog.consents.items() if d.get("enabled")])

# In owner.py (L!update global):
for guild in bot.guilds:
    if global_cog.consents[guild_id].get("enabled"):
        score = global_cog.calculate_server_score(guild_id)
        global_cog.data[guild_id]["last_updated"] = ...
global_cog.save_data()
```

**Data sources for score calculation** (all accessed via `bot.get_cog()` in `calculate_server_score()`):
- `Economy` — total coins, active users
- `LeaderboardManager` — games played stat
- `GlobalEvents` — events participated in
- `MiniGames` — minigames played

The global leaderboard respects opt-in consent: servers must enable participation via `/globalleaderboard toggle` before their data is included.

---

## 14. Farming ↔ FarmShop Coupling

The FarmShop cog is tightly coupled to both `Farming` and `Economy`:

```
L!farmshop buy <item>
    ├── farming_cog = self.bot.get_cog("Farming")   ← checks farm exists
    ├── economy = self.bot.get_cog("Economy")        ← payment
    ├── economy.remove_coins(user_id, price)
    └── farming_cog.add_to_inventory(user_id, item)  ← place in farm inventory

L!farmshop sell <item>
    ├── farming_cog = self.bot.get_cog("Farming")   ← validates item ownership
    ├── economy = self.bot.get_cog("Economy")        ← payout
    ├── farming_cog.remove_from_inventory(user_id, item)
    └── economy.add_coins(user_id, sell_price, "farm_sale")
```

Neither `Farming` nor `FarmShop` maintain their own coin balances. The entire transaction chain passes through Economy. `FarmShop` is essentially a specialized Economy interface scoped to farm items.

---

## 15. Mafia Custom Roles — sys.modules Bridge

The most unusual integration in the codebase is in `owner.py`'s `apply_custom_roles_to_database()`:

```python
def apply_custom_roles_to_database(bot):
    mafia_module = sys.modules.get('cogs.mafia')
    if mafia_module and hasattr(mafia_module, 'ROLES_DATABASE'):
        roles_db = mafia_module.ROLES_DATABASE
        for role in load_custom_roles():
            faction_key = "mafia_advanced" if role["faction"] == "MAFIA" else "werewolf_advanced"
            roles_db[faction_key][role["role_id"]] = role
        return True
    return False
```

This bypasses `get_cog()` entirely and reaches the mafia module's **module-level global dict** directly via `sys.modules`. This is necessary because `ROLES_DATABASE` is a module-level constant (not a cog attribute), initialized at import time.

**Why this works:** Python module objects are singletons — `sys.modules['cogs.mafia']` returns the exact same object that is already loaded and running the Mafia game. Mutating `ROLES_DATABASE` on that object immediately affects all active Mafia game sessions.

**When it runs:**
1. On `Owner.__init__()` — loads saved custom roles at cog startup
2. After every `L!customrole` create/delete action — keeps the live DB in sync with the file

---

## 16. Utils Infrastructure

### 16.1 utils/user_storage.py

Provides persistent per-user file storage in `bot.data_dir/users/<user_id>.json`.

**Functions called from bot.py:**
```python
user_storage.init_user_storage_worker(bot.loop)  # Start background save worker
user_storage.touch_user(user_id, username)        # Create/update user file on every message
```

`on_message` in `bot.py` calls `touch_user` as a fire-and-forget task:
```python
asyncio.create_task(user_storage.touch_user(message.author.id, message.author.name))
```

This ensures every user that sends a message has a persistent record, even before they use any commands.

### 16.2 utils/database.py

A **singleton SQLite wrapper** (`DatabaseManager`) providing a structured alternative to direct JSON access.

```python
class DatabaseManager:  # Singleton via __new__
    def upsert_user(user_id, username)
    def update_stat(user_id, stat_name, value, increment=False)
    def increment_stat(user_id, stat_name, amount=1)
    def log_activity(user_id, activity_type, activity_name, timestamp=None)
    def increment_command_count(user_id)
    def save_game_state(user_id, game_name, state_json)
    def get_user_data(user_id) → dict
```

**Schema** (from `initialize_schema()`): Two tables — `users` (id, username, created_at, last_seen, command_count, json stats) and `activities` (id, user_id, type, name, timestamp).

The singleton pattern means all cogs that import `DatabaseManager` share one connection pool. Currently used opt-in by cogs that need structured querying beyond JSON files.

### 16.3 utils/stat_hooks.py

Provides lightweight cross-cog stat recording. The bot reference is set once via `us_set_bot(bot)` in `on_ready`:

```python
# bot.py on_ready:
from utils.stat_hooks import us_set_bot
us_set_bot(bot)
```

The `_task(coro)` helper wraps coroutines for fire-and-forget execution:
```python
def _task(coro):
    asyncio.ensure_future(coro)
```

Cogs use stat_hooks to record events without awaiting the result, preventing I/O latency in command handlers.

### 16.4 utils/card_visuals.py

PIL-based card rendering library used by card game cogs. Provides:

| Function | Used By |
|----------|---------|
| `create_hand_image(cards, title, deck)` | `blackjack.py`, `poker.py`, card games |
| `create_blackjack_image(player, dealer, ...)` | `blackjack.py` |
| `create_poker_table_image(community, players, ...)` | `poker.py` |
| `create_comparison_image(p_cards, o_cards)` | `blackjack.py` long-mode reveal |
| `create_war_image(p_card, o_card)` | Card war game variant |
| `create_table_image(community_cards)` | Holdem table display |

**Asset path pattern:**
```python
CARD_ASSETS_DIR = os.path.join("assets", "cards")
FONT_DIR = os.path.join("assets", "fonts")
```

Card images are loaded from `assets/cards/<deck>/`, with a fallback to drawn representations if image files are missing. This allows the bot to run without assets in minimal deployments.

### 16.5 utils/embed_styles.py

Centralized embed factory via `EmbedStyle` class with themed static methods:

```python
EmbedStyle.success(title, description)   → green embed
EmbedStyle.error(title, description)     → red embed
EmbedStyle.warning(title, description)   → orange embed
EmbedStyle.info(title, description)      → blue embed
EmbedStyle.economy(title, description)   → gold embed
EmbedStyle.game(title, description)      → purple embed
EmbedStyle.leveling(title, description)  → teal embed
EmbedStyle.music(title, description)     → blurple embed
EmbedStyle.leaderboard(title, entries)   → ranked list embed
EmbedStyle.profile(user, data)           → full profile card embed
EmbedStyle.progress_bar(pct)            → "████░░░░" string
EmbedStyle.format_number(n)             → "1,234,567" string
EmbedStyle.tier_color(tier)             → int color by tier name
```

Module-level shortcuts (`success_embed`, `error_embed`, etc.) delegate to `EmbedStyle` for backward compatibility with older cogs.

### 16.6 utils/performance.py

A `FileCache` class providing timed in-memory caching for JSON file reads:

```python
cache = FileCache()
data = cache.get(file_path, default=None)  # Returns cached data if fresh
cache.invalidate(file_path)                # Manual cache bust after writes
cache.clear()                              # Clear all cached entries
```

Cogs that read large JSON files frequently (leaderboards, profiles) can use this to avoid repeated disk reads. The cache validates against file modification time, so it automatically gets stale data after a write.

---

## 17. Data File Sharing Between Cogs

Several JSON files are accessed by **multiple cogs**. This creates implicit coupling that isn't visible through `get_cog()` calls:

| File | Primary Owner | Also Read By | Risk |
|------|--------------|--------------|------|
| `economy.json` | `economy.py` | `serverinfo.py` (direct read) | Serverinfo reads stale if Economy hasn't saved yet |
| `profiles.json` | `profile.py` | `serverinfo.py` (direct read), `reputation.py` | Serverinfo bypasses cog cache |
| `server_configs.json` | `server_config.py` | `BotCommandTree` (via get_cog), `mining.py` | Mining reads through cog, tree reads through cog |
| `fishing_data.json` | `fishing.py` | `owner.py` (via Fishing cog methods) | No direct bypass |
| `blacklist.json` | `blacklist.py` | Enforcement listeners only (via `_load()`) | All reads go through `_load()` |
| `custom_roles.json` | `owner.py` (module functions) | Loaded into `cogs.mafia.ROLES_DATABASE` at startup | Out-of-band injection via sys.modules |

**The `serverinfo.py` direct-read pattern** is intentional — a display command that only needs current-on-disk values:
```python
# In serverinfo.py _build_userinfo_embed():
with open(os.path.join(DATA_DIR, "economy.json")) as f:
    economy_data = json.load(f)
with open(os.path.join(DATA_DIR, "profiles.json")) as f:
    profiles_data = json.load(f)
```

This avoids cog dependency for `L!userinfo`, but means very recent Economy/Profile changes (within the save interval) may not appear immediately.

---

## 18. Complete Cross-Cog Dependency Map

```
bot.py
├── Provides: bot.data_dir, bot.owner_ids, bot.active_games, bot.active_lobbies
├── Uses: ServerConfig (via BotCommandTree.interaction_check)
├── Uses: LudusPersonality (via on_message forward)
└── Runs: activity_worker (background), user_storage worker (background)

INFRASTRUCTURE LAYER (no gameplay dependencies)
├── BotLogger   ← passively observes all errors via Discord.py events
│               ← actively called by: owner.py, globalevents.py
├── Blacklist   ← gates all commands via on_command + on_interaction listeners
├── ServerConfig ← gates slash commands via BotCommandTree; read by mining.py
└── GameControl ← cleans up: CardGames, FishingAkinatorFun, MiniGames, BoardGames

ECONOMY LAYER (central financial hub)
└── Economy ← called by ALL gameplay cogs (add/remove coins, add/remove items)
    ├── Callers: gambling, blackjack, poker, heist, daily_rewards, counting,
    │           chess_checkers, boardgames, boardgames_enhanced, globalevents,
    │           owner, dueling, cardgames, cards_enhanced, marriage,
    │           businesses, business, farming, farmshop
    └── Direct JSON readers: serverinfo (read-only, bypasses cog)

GAMEPLAY COGS (peer-level, call Economy + each other's data)
├── Gambling    → Economy (all games), Profile (stats display)
├── Blackjack   → Economy (bets/payouts), card_visuals (image rendering)
├── Poker       → Economy (blinds/pots), card_visuals (table/hand images)
├── Heist       → Economy (entry/reward)
├── Farming     → Economy (harvest income), Profile (farm stats)
├── FarmShop    → Farming (inventory), Economy (purchases/sales)
├── Fishing     → Economy (via owner.py grants), standalone data
├── Mining      → Economy (ore sell), ServerConfig (per-guild settings)
├── CardGames   → Economy (game wins)
├── Chess/Checkers → Economy (wagers), GameStats (results)
├── BoardGames  → Economy (wagers), GameStats (results), Achievements
├── Counting    → Economy (milestone rewards)
├── DailyRewards → Economy (daily coins)
├── Dueling     → Economy (duel wagers)
├── Marriage    → Economy (ring purchases), Profile (partner_id)
├── Reputation  → Profile (rep stored in profile)
├── Social      → Achievements (social milestones)
├── Business/Businesses → Economy (income/purchases)
├── GlobalEvents → Economy (event rewards), BotLogger (spawn/end logs)
└── Owner       → Economy, Fishing, Counting, GlobalLeaderboard, BotLogger,
                  GameStats, GlobalEvents, MultiplayerGames, TCG,
                  sys.modules["cogs.mafia"] (custom roles bridge)

DISPLAY/META LAYER (aggregate and present)
├── Profile     ← written by: gambling, reputation, farming, marriage
│               ← read by: serverinfo (direct JSON), reputation, marriage
├── GameStats   ← written by: chess_checkers, boardgames
├── Achievements ← triggered by: boardgames, social
├── GlobalLeaderboard ← calculated from: Economy, LeaderboardManager,
│                        GlobalEvents, MiniGames
├── Leaderboards ← aggregates from: Economy, Fishing, Mining, etc.
└── ServerInfo  ← direct JSON reads: economy.json, profiles.json

UTILS (shared libraries, no Discord.py coupling)
├── utils/card_visuals.py → PIL image rendering (blackjack, poker, card games)
├── utils/embed_styles.py → Themed embed factory (used by many cogs)
├── utils/database.py     → SQLite singleton wrapper (optional opt-in)
├── utils/user_storage.py → Per-user JSON files; touched by bot.py on_message
├── utils/stat_hooks.py   → Fire-and-forget stat recording helper
└── utils/performance.py  → FileCache for JSON reads
```

---

*Part 14 complete. See [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) for the full documentation map.*
