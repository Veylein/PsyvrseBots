# Ludus Bot — Full Documentation Part 12: Admin & Owner Commands

> **Covers:** `cogs/owner.py`, `cogs/blacklist.py`, `cogs/gamecontrol.py`, `cogs/bot_logger.py`
> **Scope:** Bot-owner administration, blacklist management, game session control, and the centralized logging system.

---

## Table of Contents

1. [Overview](#1-overview)
2. [owner.py — Owner Cog](#2-ownerpy--owner-cog)
   - 2.1 [Architecture & Permission Model](#21-architecture--permission-model)
   - 2.2 [Custom Role Manager Subsystem](#22-custom-role-manager-subsystem)
   - 2.3 [Economy Management Commands](#23-economy-management-commands)
   - 2.4 [Bot Status & Presence Commands](#24-bot-status--presence-commands)
   - 2.5 [Server & Guild Management](#25-server--guild-management)
   - 2.6 [Fishing Management Commands](#26-fishing-management-commands)
   - 2.7 [Fun & Chaos Commands](#27-fun--chaos-commands)
   - 2.8 [TCG Card Management](#28-tcg-card-management)
   - 2.9 [Debug & Reload Commands](#29-debug--reload-commands)
   - 2.10 [Owner Help Command](#210-owner-help-command)
3. [blacklist.py — Blacklist System](#3-blacklistpy--blacklist-system)
   - 3.1 [Data Model & Persistence](#31-data-model--persistence)
   - 3.2 [BlacklistView UI](#32-blacklistview-ui)
   - 3.3 [_InputModal](#33-_inputmodal)
   - 3.4 [Blacklist Enforcement Listeners](#34-blacklist-enforcement-listeners)
4. [gamecontrol.py — Game Control](#4-gamecontrolpy--game-control)
   - 4.1 [Universal Stop Command](#41-universal-stop-command)
5. [bot_logger.py — Centralized Logging System](#5-bot_loggerpy--centralized-logging-system)
   - 5.1 [Architecture](#51-architecture)
   - 5.2 [StreamInterceptor — Console Capture](#52-streaminterceptor--console-capture)
   - 5.3 [Core Logging Method](#53-core-logging-method)
   - 5.4 [Error Listeners](#54-error-listeners)
   - 5.5 [Structured Logging Helpers](#55-structured-logging-helpers)
   - 5.6 [Lifecycle & Connection Events](#56-lifecycle--connection-events)
   - 5.7 [Global Exception Hook](#57-global-exception-hook)
6. [Cross-Cog Integration Points](#6-cross-cog-integration-points)
7. [Security Design](#7-security-design)

---

## 1. Overview

Part 12 documents the four cogs that provide administrative, moderation, and operational infrastructure for Ludus Bot:

| File | Cog Name | Purpose |
|------|----------|---------|
| `owner.py` | `Owner` | All bot-owner commands — economy manipulation, status, chaos events, tools |
| `blacklist.py` | `Blacklist` | Block users and servers globally from using the bot |
| `gamecontrol.py` | `GameControl` | Universal emergency-stop for stuck game sessions |
| `bot_logger.py` | `BotLogger` | Centralized logging: errors, owner commands, events, console capture |

These cogs sit at the intersection of bot operations — BotLogger passively watches everything, Owner directly manipulates live state, Blacklist gates access, and GameControl cleans up orphaned sessions.

---

## 2. owner.py — Owner Cog

### 2.1 Architecture & Permission Model

**File:** `cogs/owner.py` (1784 lines)

The `Owner` cog uses a **two-layer permission system**:

1. **`cog_check(ctx)`** — Global guard applied automatically to every command in the cog. Resolves `user_id` from either `ctx.author` (prefix) or `ctx.user` (interaction), then checks membership in `self.owner_ids` (populated from `bot.owner_ids`).

2. **Inline double-check** — Many sensitive commands also perform their own `ctx.author.id not in self.owner_ids` check as a belt-and-suspenders safety measure. Failed inline checks log an `UNAUTHORIZED` print with the caller's ID.

```python
async def cog_check(self, ctx):
    user_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
    return user_id in self.owner_ids
```

The `__init__` also **auto-loads custom roles** into the live mafia database on startup:

```python
try:
    if apply_custom_roles_to_database(bot):
        print("[OWNER COG] ✅ Custom roles loaded successfully")
except Exception as e:
    print(f"[OWNER COG] ⚠️ Could not load custom roles yet: {e}")
```

Two flavor-text lists are defined at init: `self.god_mode_responses` (5 entries for `L!godmode`) and `self.chaos_responses` (5 entries for `L!chaos`).

---

### 2.2 Custom Role Manager Subsystem

This self-contained subsystem at the top of `owner.py` (before the `Owner` cog class) manages persistent custom Mafia/Werewolf roles.

#### Module-Level Data Path

```python
_OWNER_DATA_DIR = os.getenv("RENDER_DISK_PATH", "data")
CUSTOM_ROLES_FILE = os.path.join(_OWNER_DATA_DIR, "custom_roles.json")
```

The file stores `{"roles": [...]}` where each role is a dict with `role_id`, `name_en`, `name_pl`, `theme`, `faction`, `power`, `emoji`, `desc_en`, `desc_pl`.

#### `load_custom_roles()` / `save_custom_roles(roles)`

Standard load/save pair. `load_custom_roles()` returns `data.get("roles", [])`. `save_custom_roles(roles)` writes `{"roles": roles}`.

#### `apply_custom_roles_to_database(bot)`

Bridges the persistent JSON to the live in-memory game database:

```python
mafia_module = sys.modules.get('cogs.mafia')
if mafia_module and hasattr(mafia_module, 'ROLES_DATABASE'):
    roles_db = mafia_module.ROLES_DATABASE
    for role in roles:
        target_faction = "mafia_advanced" if role["faction"] in ("MAFIA",) else "werewolf_advanced"
        roles_db[target_faction][role["role_id"]] = role
```

Uses `sys.modules` to reach the already-loaded mafia cog's global `ROLES_DATABASE` dict directly, eliminating the need for a bot reference. Returns `True` if the mafia module was found and updated.

#### `create_role_with_data(interaction, manager_view, name_en, name_pl, theme, faction, power, emoji, desc_en, desc_pl)`

Async standalone helper called at the end of both modal paths:

1. Generates `role_id = name_en.lower().replace(" ", "_")`
2. Checks for duplicate `role_id` in `load_custom_roles()` result
3. Assigns default faction emoji if `emoji` is blank:
   - `TOWN → 👤`, `MAFIA → 🔫`, `WEREWOLVES → 🐺`, `VILLAGE → 🏘️`, `NEUTRAL → ⚖️`, `CHAOS → 🌀`
4. Saves the complete role list via `save_custom_roles()`
5. Calls `apply_custom_roles_to_database(manager_view.bot)` to inject into live DB
6. Edits the manager's Discord message to show the updated embed

#### `CustomRoleManagerView(bot, user)` — `discord.ui.View(timeout=300)`

Main management dashboard posted by `L!customrole`. Contains:

| Button | Label | Behavior |
|--------|-------|----------|
| ➕ | Create Role | Opens `CreateRoleModal` (Step 1) |
| 🗑️ | Delete Role | Presents a `Select` with up to 25 custom roles; deletes selected on submit |
| 🔄 | Refresh | Reloads from JSON, rebuilds embed, edits message |

`_build_embed()` lists up to 10 custom roles with name, faction, theme, and power.

`show(ctx)` sends the initial embed + view to the channel.

#### Two-Step Role Creation Flow

**Step 1 — `CreateRoleModal`** (`discord.ui.Modal`):

| Field | Required | Description |
|-------|----------|-------------|
| `name_en` | Yes | English role name (max 50 chars) |
| `name_pl` | Yes | Polish role name (max 50 chars) |
| `theme` | Yes | `MAFIA` or `WEREWOLF` |
| `faction` | Yes | `TOWN`, `MAFIA`, `WEREWOLVES`, `VILLAGE`, `NEUTRAL`, or `CHAOS` |
| `power` | No | One of 65+ valid power strings |

Validation on submit:
- `theme` must be in `valid_themes = ["MAFIA", "WEREWOLF"]`
- `faction` must be in `valid_factions = ["TOWN", "MAFIA", "WEREWOLVES", "VILLAGE", "NEUTRAL", "CHAOS"]`
- If `power` provided, must be in the 65+ entry `valid_powers` list (covers: `detective`, `doctor`, `vigilante`, `godfather`, `framer`, `forger`, `serial_killer`, `witch`, `escort`, `medium`, `transporter`, `mayor`, `veteran`, `amnesiac`, etc.)

On success: shows a Step2View with two buttons — **"Add Descriptions & Emoji"** (opens Step 2 modal) or **"Skip (Use Defaults)"** (calls `create_role_with_data` with blank optionals).

**Step 2 — `CreateRoleModalStep2`** (`discord.ui.Modal`):

| Field | Required | Description |
|-------|----------|-------------|
| `emoji` | No | Custom emoji for the role |
| `desc_en` | No | English description (paragraph style, max 500 chars) |
| `desc_pl` | No | Polish description (paragraph style, max 500 chars) |

On submit: calls `create_role_with_data()` with all data from both steps combined.

**Command:**
```
L!customrole
```
Opens the `CustomRoleManagerView` interface.

---

### 2.3 Economy Management Commands

All economy commands delegate to the `Economy` cog via `self.bot.get_cog("Economy")`.

| Command | Syntax | Effect |
|---------|--------|--------|
| `L!godmode` | `L!godmode` | Sets owner's balance to 999,999,999; streak to 999; gives all shop items × 99 |
| `L!setcoins` | `L!setcoins @user <amount>` | Directly writes `economy_data[user]["balance"] = amount` |
| `L!addcoins` | `L!addcoins @user <amount>` | Calls `economy_cog.add_coins(member.id, amount, "owner_grant")` |
| `L!removecoins` | `L!removecoins @user <amount>` | Calls `economy_cog.remove_coins()`; reports if balance insufficient |
| `L!resetcoins` | `L!resetcoins @user` | Deletes `economy_data[user_key]`; next access re-creates defaults |
| `L!giveitem` | `L!giveitem @user <item_id> [qty]` | Calls `economy_cog.add_item(member.id, item_id, quantity)` |

**`L!godmode` full effect:**
```python
economy_cog.economy_data[str(ctx.author.id)] = {
    "balance": 999999999,
    "total_earned": 999999999,
    "total_spent": 999999999,
    "last_daily": None,
    "daily_streak": 999,
    "active_boosts": {}
}
for item_id in economy_cog.shop_items.keys():
    economy_cog.add_item(ctx.author.id, item_id, 99)
```

Responds with a random `god_mode_responses` message plus a gold embed showing the maxed stats.

---

### 2.4 Bot Status & Presence Commands

| Command | Syntax | Effect |
|---------|--------|--------|
| `L!status` | `L!status <type> <text>` | Changes bot activity; `type` = `playing`, `watching`, `listening`, `competing` |
| `L!presence` | `L!presence <status>` | Changes online indicator; `status` = `online`, `idle`, `dnd`, `invisible` |
| `L!nickname` | `L!nickname [name]` | Edits bot's server nickname; omit `name` to reset; catches `discord.Forbidden` |

`L!status` constructs a `discord.Activity(type=ActivityType.<x>, name=text)` and calls `bot.change_presence(activity=...)`.

`L!presence` maps the string to `discord.Status.<x>` and calls `bot.change_presence(status=...)`.

---

### 2.5 Server & Guild Management

#### `L!serverlist`
Paginated list of every guild the bot is in. Shows 20 guilds per embed page. For each guild attempts to fetch existing invites (sorted by `max_age`/`uses`) to provide an invite URL. Fields: Name, ID, Members, Invite.

#### `L!restart [reason]`
Graceful bot restart in two steps:
1. `await self.bot.close()` — shuts down Discord connection cleanly
2. `os.execv(sys.executable, [sys.executable] + sys.argv)` — replaces the process with itself

If `execv` fails (e.g., permission error), falls back to `os._exit(0)` so the process manager can restart the bot.

#### `L!leave [guild_id]`
Leaves target guild. If no ID provided, leaves the current guild. Uses `guild.leave()`. Reports success or failure.

#### `L!purge [amount]`
Deletes `amount+1` messages (the +1 accounts for the command message). Sends a confirmation, then deletes it after 3 seconds:
```python
msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
await asyncio.sleep(3)
await msg.delete()
```

#### `L!announce <#channel> <message>`
Sends a blue embed titled "📢 Announcement" to the target channel. Footer shows the owner's display name.

#### `L!dm @user <message>`
Sends a raw string DM. Catches `discord.Forbidden` if the target has DMs disabled.

#### `L!countset <number>`
Overrides the current counting game number for the current guild, resets `last_user` to `None` (preventing anti-consecutive enforcement on the next count), and saves. Reports the configured counting channel if one exists.

#### `L!stats [update]`
Comprehensive 7-section bot statistics embed:

| Section | Data Source |
|---------|-------------|
| 🌐 Server Stats | `bot.guilds`, latency |
| ⚙️ Commands | `bot.commands`, `bot.tree.get_commands()`, `bot.cogs` |
| 💰 Economy | `Economy.economy_data` — total users, total coins, average, top-3 richest |
| 🎮 Activity | `LeaderboardManager.stats` games played; pets and levels if cogs available |
| 🌍 Global Events | `GlobalEvents.active_events` count and list |
| 🏆 Global Rankings | `GlobalLeaderboard.consents` ranked count, top scoring server |
| 🎮 Multiplayer | `MultiplayerGames.active_lobbies` count |

Running `L!stats update` also calls `logger.log_owner_command(ctx, "stats update", ...)`.

#### `L!update <system>`
- `L!update global` — Recalculates scores for all opted-in servers in `GlobalLeaderboard`, stamps `last_updated`, calls `global_cog.save_data()`, then logs via `BotLogger`
- `L!update stats` — Invokes `L!stats update` internally via `ctx.invoke`

---

### 2.6 Fishing Management Commands

These commands provide owner-level control over the Fishing cog's player data.

| Command | Syntax | Effect |
|---------|--------|--------|
| `L!fishing_tournament` | `L!fishing_tournament <mode> <duration>` | Starts a tournament in the guild's configured tournament channel |
| `L!give_fish` | `L!give_fish @user <fish_id> [qty]` | Adds fish to user's `fish_caught` dict; updates `total_catches` and `total_value` |
| `L!give_bait` | `L!give_bait @user <bait_id> [qty]` | Adds bait to user's `bait_inventory` dict |
| `L!give_rod` | `L!give_rod @user <rod_id>` | Sets `user_data["rod"] = rod_id` |
| `L!give_boat` | `L!give_boat @user <boat_id>` | Sets `user_data["boat"] = boat_id`; `none` removes boat |
| `L!unlock_area` | `L!unlock_area @user <area_id>` | Appends area to `user_data["unlocked_areas"]` if not already present |

**Tournament modes:** `biggest` (heaviest single fish), `most` (most fish caught), `rarest` (rarest species). Duration is 1–30 minutes. Requires tournament channel to be pre-configured by an admin.

**`L!give_bait` with `kraken_bait`** triggers a special message:
> ⚠️ **Warning:** This summons the Kraken in Mariana Trench!

All fishing commands validate item IDs against the fishing cog's dictionaries (`fish_types`, `baits`, `rods`, `boats`, `areas`) and return informative error messages listing valid options.

---

### 2.7 Fun & Chaos Commands

#### `L!raincoins [amount]`
Gives `amount` PsyCoins (default 1000) to every **non-bot, non-offline** member in the guild. Iterates `ctx.guild.members`, filters by `status != discord.Status.offline`.

#### `L!chaos`
Random rewards for **all** guild members (including offline):
- Each member receives 100–10,000 PsyCoins randomly
- 30% chance per member to also receive a random shop item
- Sends results in chunks of 10 to avoid message limits

#### `L!spinlottery [prize]`
Picks a random non-bot member as lottery winner. Gives them `prize` coins (default 50,000) via `economy_cog.add_coins`. Shows an embed with the winner's avatar.

#### `L!spawn`
Boss raid event:
1. Randomly selects one of 5 bosses: Ancient Dragon (10k HP/5k reward) → Celestial Being (30k HP/20k reward)
2. Posts embed with ⚔️ reaction
3. Waits 30 seconds for reactions
4. Fetches message, counts non-bot ⚔️ reactors
5. If anyone joined: splits `boss["reward"]` evenly, credits via `economy_cog.add_coins`
6. If no one joined: "escaped" message

#### `L!cursed`
Sends one of 5 **Zalgo text messages** (Unicode combining characters) followed by "Just kidding! 😈" after a 1-second pause.

#### `L!countset <number>`
*(Also listed under Server Management)* Sets the counting game's current number for the guild, with input validation `>= 0`.

#### `L!hack @user`
14-step animated fake hack sequence, editing a single message through each step with 2-second delays. Final message reveals "hacked secrets" like favorite game and lucky number (all random). Ends with a reveal that it was a joke.

#### `L!roastme`
Sends the invoker's mention plus a random entry from 7 roast strings.

#### `L!vibecheck [@user]` (alias: `vc`)
Random vibe result from 7 tiers: IMMACULATE (10/10, gold) → FAILED (0/10, dark_red). Targets the mentioned user or the invoker.

---

### 2.8 TCG Card Management

#### `L!give_tc @user <card_query>`
Gives a TCG card to a member. Resolution order:
1. Try legacy `TCG` cog's `_find_card_by_name_or_id()` + `manager.award_card()`
2. Fall back to `psyvrse_tcg` module: accepts crafted ID (`C...`), numeric seed (0 to `TOTAL_CARD_POOL-1`), or name substring search in `inventory.crafted`

#### `L!remove_tc @user <card_query>`
Same resolution order as `give_tc`, but calls `manager.remove_card()` or `inventory.remove_card()`. Reports if the member doesn't own the card.

---

### 2.9 Debug & Reload Commands

| Command | Syntax | Effect |
|---------|--------|--------|
| `L!eval <code>` | Any Python expression | Calls `eval(code)` in the bot's runtime; strips ` ```python ` / ` ``` ` fences |
| `L!reload <cog>` | `L!reload economy` | `await bot.reload_extension("cogs.<cog>")` |
| `L!reloadall` | `L!reloadall` | Iterates `bot.extensions.keys()`, reloads each; shows success/failed breakdown |
| `L!ownertest` | `L!ownertest` | Confirms owner commands are working; prints invoker and owner IDs |

**`L!eval` safety note:** This executes arbitrary Python in the live bot process. It is protected solely by the cog_check owner guard. Results and errors are both returned as embed messages.

---

### 2.10 Owner Help Command

```
L!ownerhelp   (aliases: 👑, L!owner, L!helpowner)
```

Sends a gold embed with 7 categorized sections listing all owner commands with usage syntax:
- 💰 Economy Management (6 commands)
- 🤖 Bot Status (3 commands)
- 🎭 Fun & Chaos (8 commands)
- 🎣 Fishing Management (6 commands + notes)
- 🎭 Mafia/Werewolf Custom Roles (1 command + feature bullets)
- 🔧 Server Management (9 commands)
- 🛠️ Debug (5 commands)

---

## 3. blacklist.py — Blacklist System

**File:** `cogs/blacklist.py`

### 3.1 Data Model & Persistence

**File path:**
```python
BLACKLIST_FILE = os.path.join(os.getenv("RENDER_DISK_PATH", "."), "blacklist.json")
```

**JSON structure:**
```json
{
  "users": [123456789, 987654321],
  "servers": [111222333, 444555666]
}
```

Both `_load()` and `_save(data)` use **atomic writes** (`.tmp` file + `os.replace()`) to prevent data corruption:

```python
def _save(data):
    tmp = BLACKLIST_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, BLACKLIST_FILE)
```

`_load()` returns the parsed dict or `{"users": [], "servers": []}` on error.

### 3.2 BlacklistView UI

`BlacklistView(cog)` — `discord.ui.View` with 5 buttons:

| Button | Emoji | Label | Action |
|--------|-------|-------|--------|
| 🚫 | Ban user | Opens `_InputModal("Blacklist User", "ban_user", cog)` |
| 🏰 | Ban server | Opens `_InputModal("Blacklist Server", "ban_server", cog)` |
| ✅ | Unblacklist user | Opens `_InputModal("Unblacklist User", "unban_user", cog)` |
| ✅ | Unblacklist server | Opens `_InputModal("Unblacklist Server", "unban_server", cog)` |
| 🔄 | Refresh | Rebuilds embed from file, edits message |

`_build_overview_embed()` creates an embed showing up to 15 blacklisted users and 15 blacklisted servers (by ID). Color is `discord.Color.red()`.

**Command:**
```
L!blacklist   (alias: bl)
```
Requires **bot owner OR server administrator** (`commands.has_permissions(administrator=True)` check). Sends the overview embed + `BlacklistView`.

### 3.3 _InputModal

`_InputModal(title, action, cog)` — `discord.ui.Modal` with a single `discord.ui.TextInput` for a user/server ID.

On submit, dispatches to one of 4 handlers:

| `action` | Effect |
|----------|--------|
| `ban_user` | Appends user ID (int) to `data["users"]` |
| `ban_server` | Appends server ID (int) to `data["servers"]` |
| `unban_user` | Removes ID from `data["users"]` if present |
| `unban_server` | Removes ID from `data["servers"]` if present |

After saving, the modal calls `interaction.message.edit(embed=_build_overview_embed(), view=BlacklistView(cog))` to auto-refresh the dashboard in place.

### 3.4 Blacklist Enforcement Listeners

Two listeners enforce the blacklist for all bot interactions:

**`on_command` (prefix command listener):**
```python
@commands.Cog.listener()
async def on_command(self, ctx):
    data = _load()  # Fresh read each check
    if ctx.author.id in data["users"]:
        raise commands.CheckFailure("blacklisted")
    if ctx.guild and ctx.guild.id in data["servers"]:
        raise commands.CheckFailure("blacklisted")
```

**`on_interaction` (slash command listener):**
Same logic using `interaction.user.id` and `interaction.guild_id`.

Both listeners load the blacklist fresh on every command invocation (no caching), ensuring that newly blacklisted users are blocked immediately without a restart.

---

## 4. gamecontrol.py — Game Control

**File:** `cogs/gamecontrol.py`

### 4.1 Universal Stop Command

The `GameControl` cog provides a single command with both prefix and slash implementations.

**Command:**
```
L!stop
/stop
```

**Both implementations check the same six game state dictionaries:**

| Cog | Attribute | Game Type |
|-----|-----------|-----------|
| `CardGames` | `active_games` | UNO / Card Games — checks `player in game["players"]` |
| `FishingAkinatorFun` | `active_akinator` | Akinator — keyed by `str(user.id)` |
| `FishingAkinatorFun` | `active_drawings` | Drawing Game — checks if invoker is the `artist` |
| `MiniGames` | `active_wordle` | Wordle — keyed by `str(user.id)` |
| `MiniGames` | `active_trivia` | Trivia — keyed by `channel.id` |
| `BoardGames` | `active_games` | Board Games — checks `player in game["players"]` |

**Behavior:**
- Removes entries from the relevant dict(s) to free the slot
- Collects names of stopped games into a `stopped` list
- Responds with `✅ Stopped: {', '.join(set(stopped))}` or `❌ You don't have any active games running!`
- Uses `set()` on the stopped list to deduplicate in case the same game type is stopped multiple times

**Integration pattern:** The command directly mutates the cog's in-memory dicts. Since all active game state is held in memory (not persisted), dict deletion is the complete cleanup operation — there's no secondary persistence to update.

---

## 5. bot_logger.py — Centralized Logging System

**File:** `cogs/bot_logger.py` (512 lines)

### 5.1 Architecture

`BotLogger` is the central observability layer for Ludus Bot. It serves two distinct purposes:

1. **Discord-channel logging** — Sends structured embeds to a hardcoded private log channel
2. **Console capture** — Intercepts `sys.stdout` / `sys.stderr` and mirrors all print output to a separate Discord channel in real time

**Hardcoded channel IDs:**
```python
self.log_channel_id = 1442605619835179127      # Structured event logs
self.console_channel_id = 1468974282418950177  # Raw console output
```

### 5.2 StreamInterceptor — Console Capture

`StreamInterceptor(io.TextIOBase)` — A custom stream that:
- **Wraps** the original `sys.stdout` or `sys.stderr`
- **Writes to both** the original terminal AND a `queue.Queue`
- Does not suppress console output — both outputs happen simultaneously

```python
def write(self, message: str):
    if self.original_stream:
        self.original_stream.write(message)  # Terminal still sees output
        self.original_stream.flush()
    if message.strip():
        self.buffer.put((self.stream_name, message))  # Queue for Discord
```

**`start_console_capture()`** replaces `sys.stdout` and `sys.stderr` with `StreamInterceptor` instances, then launches `console_worker` as an `asyncio.Task`.

**`stop_console_capture()`** restores original streams and cancels the task.

**`console_worker()`** — An infinite loop that:
1. Awaits `bot.wait_until_ready()`
2. Reads from the queue via `run_in_executor` (blocking queue.get runs in thread pool to avoid blocking the event loop)
3. Truncates messages over 1900 characters
4. Posts to `console_channel` as:
   ```
   **STDOUT**
   ```text
   <output>
   ```
   ```

This provides the bot owners live view of all `print()` statements from every cog.

### 5.3 Core Logging Method

```python
async def log(self, title, description, color, fields=None):
```

Fetches the log channel (tries cache first, fetches if not cached), builds a `discord.Embed` with:
- `timestamp=datetime.now(timezone.utc)` — always UTC ISO timestamp
- Optional list of `fields` dicts with `name`, `value`, `inline` keys

All other logging methods in this cog are wrappers around `log()`.

### 5.4 Error Listeners

#### `on_command_error(ctx, error)`

Catches and categorizes **prefix command errors** with 20+ type mappings:

| Error Class | Title | Color |
|-------------|-------|-------|
| `CommandNotFound` | (silently ignored) | — |
| `CommandOnCooldown` | (silently ignored) | — |
| `MissingPermissions` | 🔒 PERMISSION ERROR | orange |
| `BotMissingPermissions` | ⚠️ BOT PERMISSION ERROR | orange |
| `MissingRequiredArgument` | 📝 MISSING ARGUMENT ERROR | gold |
| `BadArgument` | ❓ BAD ARGUMENT ERROR | gold |
| `MaxConcurrencyReached` | ⏸️ CONCURRENCY ERROR | orange |
| `RateLimited` | 🚦 RATE LIMIT ERROR | red |
| `Forbidden` | 🚫 FORBIDDEN ERROR | red |
| `HTTPException` | 🌐 HTTP ERROR | red |
| `NotFound` | 🔍 NOT FOUND ERROR | orange |
| `DiscordServerError` | 🔥 DISCORD SERVER ERROR | dark_red |
| `InvalidData` | 📊 INVALID DATA ERROR | red |
| `GatewayNotFound` | 🌐 GATEWAY NOT FOUND | dark_red |
| `ConnectionClosed` | 🔌 CONNECTION CLOSED | dark_red |
| `asyncio.TimeoutError` | ⏱️ TIMEOUT ERROR | orange |
| `asyncio.CancelledError` | 🚫 TASK CANCELLED | orange |
| `aiohttp.ClientError` | 🌐 CLIENT ERROR | red |
| `aiohttp.ServerDisconnectedError` | 🔌 SERVER DISCONNECTED | red |
| `aiohttp.ClientConnectionError` | 🔌 CLIENT CONNECTION ERROR | red |
| `ConnectionError` | 🔌 CONNECTION ERROR | red |
| `OSError` | 💾 OS ERROR | red |
| `MemoryError` | 🧠 MEMORY ERROR | dark_red |
| `json.JSONDecodeError` | 📋 JSON DECODE ERROR | orange |
| *(other)* | ❌ COMMAND ERROR | red |

All non-silenced errors log: error type, message text, command name, user, server, channel, and full truncated traceback.

#### `on_application_command_error(interaction, error)`

Similar handling for **slash command errors** with 5 specific type mappings. Logs command name (with `/` prefix), user, server, and traceback.

### 5.5 Structured Logging Helpers

| Method | Trigger | Color |
|--------|---------|-------|
| `log_owner_command(ctx, command_name, details)` | Called by owner commands for audit trail | purple |
| `log_admin_command(ctx, command_name, details)` | Called by admin cogs for audit trail | blue |
| `log_event_spawn(event_type, guild_id, spawner_id, details)` | Called by GlobalEvents on spawn | gold |
| `log_event_end(event_type, details)` | Called by GlobalEvents on completion | orange |
| `log_moderation(action, guild_id, moderator_id, target_id, reason)` | Called by moderation cogs | red |
| `log_economy(transaction_type, user_id, amount, reason)` | Called for large transactions | green |
| `log_bot_event(event_type, description)` | Internal lifecycle events | blurple |

**`log_economy` threshold:** Only logs transactions where `amount >= 1000`, preventing log spam from small routine transactions.

### 5.6 Lifecycle & Connection Events

| Event | Title | Trigger |
|-------|-------|---------|
| `on_ready` | BOT EVENT: STARTUP | Starts console capture; logs server count, user count, latency |
| `on_guild_join` | 📥 JOINED SERVER | Logs name, ID, members, owner, created date, invite URL |
| `on_guild_remove` | 📤 LEFT SERVER | Logs name, ID, members |
| `on_disconnect` | BOT EVENT: DISCONNECT | Connection lost |
| `on_resumed` | BOT EVENT: RESUMED | Reconnected |
| `on_error` | ⚠️ EVENT ERROR | Catch-all for listener errors; logs full `format_exc()` |
| `on_close` | — | Stops console capture cleanly |

**Sharding events** (for future multi-shard deployments):
- `on_shard_connect`, `on_shard_disconnect`, `on_shard_ready`, `on_shard_resumed` — all log via `log_bot_event`

**`on_socket_event_type`:** Watches raw websocket events; logs specifically when `event_type in ['RESUMED', 'READY', 'GUILD_UNAVAILABLE']`.

**`on_guild_join` invite logic:**
```python
if guild.system_channel:
    inv = await guild.system_channel.create_invite(max_age=0, max_uses=1)
    invite = inv.url
```
Creates a single-use permanent invite via the system channel to give owners a direct link into new guilds.

### 5.7 Global Exception Hook

BotLogger installs a custom `sys.excepthook` on `cog_load` and restores it on `cog_unload`:

```python
async def cog_load(self):
    self.original_excepthook = sys.excepthook
    sys.excepthook = self.handle_exception
```

`handle_exception(exc_type, exc_value, exc_traceback)`:
1. Passes `KeyboardInterrupt` through to `sys.__excepthook__` (allows Ctrl+C to work normally)
2. For all other exceptions: formats the full traceback, truncates to 1800 chars, creates an async task to log `💥 UNCAUGHT EXCEPTION` to Discord
3. Also calls `sys.__excepthook__` so the exception is still printed to the (now-intercepted) console

This catches crashes that occur **outside** the Discord.py event loop — for example, in synchronous startup code or threads.

---

## 6. Cross-Cog Integration Points

```
owner.py ──────────────────────────────────────────────────────────────
    │  get_cog("Economy")      →  godmode, setcoins, addcoins, removecoins
    │                             resetcoins, giveitem, raincoins, chaos
    │                             spinlottery, spawn
    │  get_cog("Fishing")      →  give_fish, give_bait, give_rod, give_boat
    │                             unlock_area, fishing_tournament
    │  get_cog("Counting")     →  countset
    │  get_cog("BotLogger")    →  stats update, update global (audit log)
    │  get_cog("GlobalLeaderboard") → stats (display), update global
    │  get_cog("GlobalEvents") →  stats (display)
    │  get_cog("MultiplayerGames") → stats (display)
    │  sys.modules["cogs.mafia"] → apply_custom_roles_to_database
    │  psyvrse_tcg module       →  give_tc, remove_tc
    └──────────────────────────────────────────────────────────────────

gamecontrol.py ─────────────────────────────────────────────────────────
    │  get_cog("CardGames")     →  active_games dict mutation
    │  get_cog("FishingAkinatorFun") → active_akinator, active_drawings
    │  get_cog("MiniGames")     →  active_wordle, active_trivia
    │  get_cog("BoardGames")    →  active_games dict mutation
    └──────────────────────────────────────────────────────────────────

bot_logger.py ──────────────────────────────────────────────────────────
    │  Called by: owner.py      →  log_owner_command
    │  Called by: globalevents.py → log_event_spawn, log_event_end
    │  Called by: moderation cogs → log_moderation, log_admin_command
    │  Called by: economy.py    →  log_economy (large transactions)
    │  Intercepts: all cogs     →  on_command_error, on_application_command_error
    └──────────────────────────────────────────────────────────────────
```

---

## 7. Security Design

### Owner Authentication

The `Owner` cog relies on `bot.owner_ids` set at bot initialization (from `config.json`). The `cog_check` method enforces this globally. Critical commands also perform inline checks with `UNAUTHORIZED` logging, creating an audit trail of failed access attempts in the console (which BotLogger forwards to Discord).

### Blacklist Freshness

The blacklist system intentionally reads from disk on **every command invocation** rather than caching. This ensures:
- A newly blacklisted user is blocked starting from their next command, without restart
- Multiple bot processes (if ever deployed) would share the same blacklist state via shared disk

### Eval Safety

`L!eval` executes arbitrary Python in the bot's runtime with access to `self.bot`, all cog states, the database, and OS-level calls. It is protected only by the owner-only guard. There is intentionally no sandboxing — this is a developer tool, not a user-facing feature.

### Atomic Writes

Both `owner.py`'s `save_custom_roles()` and `blacklist.py`'s `_save()` use the atomic write pattern (`tmp` → `os.replace()`), preventing partial writes that could corrupt the JSON files under concurrent access or process interruption.

---

*Part 12 complete. See [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) for the full documentation map.*
