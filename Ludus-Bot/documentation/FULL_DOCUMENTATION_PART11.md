# 📚 LUDUS BOT — FULL DOCUMENTATION PART 11
## Utility & Help Systems

**Files Covered:** `help.py` (466 lines) · `help_system.py` (~115 lines) · `about.py` (258 lines) · `utilities.py` (~220 lines) · `serverinfo.py` (267 lines)  
**Total Lines:** ~1,325 lines  
**Category:** Help, Information & Utilities

---

## Table of Contents

1. [Help System (help.py)](#1-help-system)
2. [Help Framework (help_system.py)](#2-help-framework)
3. [About Guide (about.py)](#3-about-guide)
4. [Utilities (utilities.py)](#4-utilities)
5. [Server & User Info (serverinfo.py)](#5-server--user-info)
6. [Cross-System Integration](#6-cross-system-integration)
7. [Command Reference](#7-command-reference)

---

## 1. Help System

**File:** `cogs/help.py` — 466 lines  
**Purpose:** Provides an interactive, category-based help menu for all bot commands. Supports both `L!help` prefix and `/help` slash. Includes a dropdown selector for quick navigation between 17 categories.

### 1.1 Overview

The `Help` cog overrides Discord.py's default help command with a fully custom paginated system. Rather than generating docs from command metadata, it maintains a manually curated `categories` dict mapping category names to `(command, description)` pairs. This allows non-technical copy in the descriptions and fine-grained control over which commands are shown without exposing internal details.

Key design choices:
- **Dropdown menu** — `CategorySelect` using `discord.ui.Select`, shown on the main help page
- **Dual access** — `/help`, `/help <category>`, `L!help`, `L!help <category>` all work
- **Owner-only category** — `👑 Owner` is conditionally added to the dropdown and visible only to bot owners
- **Fuzzy matching** — category lookup uses substring and normalized text matching so `L!help eco` finds `💰 Economy`
- **Section headers** — command entries starting with `—` render as bold section dividers inside category embeds

### 1.2 `categories` Dictionary

Defined in `__init__`, the dict maps a visible name (with emoji) to a sub-dict:

```python
{
    "💰 Economy": {
        "key": "economy",       # short key used in L!help economy
        "desc": "Currency system and trading",
        "commands": [
            ("balance", "Check your PsyCoin balance"),
            ("buy <item>", "Purchase an item"),
            ...
        ]
    },
    ...
}
```

The following categories are defined:

| Category | Key | Commands |
|---|---|---|
| 💰 Economy | `economy` | balance, daily, shop, buy, inventory, use, give, leaderboard, trade |
| 🎰 Gambling | `gambling` | /slots, /coinflip, /higerlower, dicegamble, /blackjack, /poker, /crash, /mines, /dice, /roulette, /gambling_stats, /odds, /strategy |
| 🎲 Board Games | `board` | ttt, connect4, hangman, chess, checkers, /monopoly start |
| 🃏 Card Games | `cards` | /uno, /gofish, war |
| 🎮 Minigames | `mini` | /minigames |
| 🧩 Puzzle Games | `puzzle` | /game minesweeper, /game memory, /game codebreaker, /game clue |
| 👾 Arcade | `arcade` | /arcade pacman, /arcade mathgame, /arcade bombdefuse |
| 🚜🎣⛏️ Simulators | `sims` | /farm view, /farm plant, /farm harvest, /farm sell, fish, /fish cast, /mine, and more |
| 🧡 Social | `social` | /ship, /hug, /kiss, /slap, /petpet, roast, compliment, pray, curse, marry, spouse, bank, couplequests, divorce, rep commands |
| 🌍 Global Events | `events` | event war, joinfaction, warleaderboard, event worldboss, attack, bossstats, event hunt, event list, event end + reward info |
| 📜 Quests | `quests` | quests, achievements, questclaim |
| 💼 Business | `business` | business buy, business collect, business upgrade, business list |
| 💎 Premium | `premium` | lottery, heist, marry, divorce |
| 🎨 Fun | `fun` | joke, meme, quote, dog, cat, panda, gif, poll, 8ball, tarot |
| ⚙️ Utility | `utility` | about, setup, ping, invite, serverinfo, userinfo, avatar |
| ⚡ Admin | `admin` | /counting, /starboard, serverconfig, purge, confession |

Owner-only (hidden from regular users):

| Category | Key | Commands |
|---|---|---|
| 👑 Owner | `owner` | godmode, /setcoins, /addcoins, giveitem, raincoins, chaos, spawn, stats, reload, announce, /botstatus |

### 1.3 `CategorySelect` Inner Class

Extends `discord.ui.Select`. Built dynamically in `__init__`:
```python
for cat_name, cat_data in cog.categories.items():
    options.append(discord.SelectOption(
        label=cat_name,
        value=cat_data.get('key') or cat_name,
        description=cat_data.get('desc', '')[:100]
    ))
```
If the user is a bot owner, the owner category entries are appended to the options list (max 25 total — well under Discord's limit).

**Callback:** When a selection is made, `_send_category_help()` is called with `is_slash=True`, meaning it uses `interaction.response.send_message`.

### 1.4 `CategoryView` Inner Class

A `discord.ui.View` that simply holds a `CategorySelect`. Timeout defaults to 60 seconds.

### 1.5 `_send_main_help(ctx, is_owner, is_slash=False)`

Builds the landing embed:
- Title: `🎮 Ludus Bot - Command Categories`
- Description: Quick Start tips (`L!tutorial`, `L!daily`, `L!balance`, `L!slots 100`)
- Fields: each category as an inline field showing `L!help <key>` + short description
- Footer: bot version, category count, prefix
- Sends embeds with `CategoryView` dropdown attached

The `is_slash` flag controls whether to use `ctx.response.send_message` (slash) or `ctx.send` (prefix).

### 1.6 `_send_category_help(ctx, category_key, is_owner, is_slash=False)`

The main lookup method. Has two special paths before the general search:

**Owner redirect path:**
```python
if norm_key == 'owner' or raw_key == '👑':
    if is_owner:
        owner_cog = self.bot.get_cog('Owner')
        ownerhelp_cmd = owner_cog.owner_help
        # for slash: creates FakeCtx to bridge interaction → ctx.send API
        await ownerhelp_cmd(fake_ctx)
```
A `FakeCtx` inner class (defined inline) wraps an `Interaction` so the owner help command — which expects a `ctx` — can call `ctx.send()` and have it route to `interaction.followup.send()`.

**Category lookup:**
```python
if (
    cat_data.get('key') == raw_key          # exact key match
    or cat_data.get('key') == norm_key       # normalized match
    or raw_key in cat_name_lower             # substring in visible name
    or norm_key and norm_key in norm_cat     # normalized substring
):
```

`_normalize(text)` strips non-alphanumeric characters, collapses whitespace, and lowercases.

**Embed construction for found category:**
- Loops `category_data["commands"]`
- Entries starting with `—` render as `▸ SECTION HEADER` using `inline=False` (divider rows)
- Regular entries: slash commands keep `/` prefix; prefix commands get `L!` prepended

Example of a section-header row in `Global Events`:
```python
("— WAR EVENT —", "Faction-based server competition")
# → renders as field name: ▸ WAR EVENT, value: Faction-based server competition
```

### 1.7 Commands

| Command | Description |
|---|---|
| `L!help` | Main help menu with category dropdown |
| `L!help <category>` | Jump directly to a category (fuzzy matching) |
| `/help` | Slash main help menu |
| `/help [category]` | Slash jump to category |

---

## 2. Help Framework

**File:** `cogs/help_system.py` — ~115 lines  
**Purpose:** A lightweight support scaffold for the help system. Provides a `HelpView` paginator component used by other cogs (notably `minigames.py`), a category list with autocomplete, and a delegation bridge to the richer `Help` cog.

### 2.1 `CAT_LIST`

A module-level list of `(name, emoji)` tuples defining the 14 canonical categories:
```python
CAT_LIST = [
    ("Economy", "💰"), ("Gambling", "🎰"), ("Board Games", "🎲"),
    ("Card Games", "🃏"), ("Minigames", "🎮"), ("Puzzle Games", "🧩"),
    ("Arcade", "👾"), ("Fishing+", "🎣"), ("Farming", "🚜"),
    ("Social", "👥"), ("Pets", "🐾"), ("Profile", "👤"), ("Admin", "⚡"), ("Owner", "👑")
]
```
This list drives both the `/help_cat main` autocomplete and the `_category_list_embed()` overview.

### 2.2 `HelpView`

A reusable paginator `discord.ui.View` intended for import by other cogs:

```python
class HelpView(discord.ui.View):
    def __init__(self, pages: List[discord.Embed], timeout: int = 120):
        self.pages = pages
        self.index = 0

    @discord.ui.button(label="⬅️ Prev", ...)
    async def prev(self, b, i):
        self.index = (self.index - 1) % len(self.pages)
        await i.response.edit_message(embed=self.current(), view=self)

    @discord.ui.button(label="Next ➡️", ...)
    async def next(self, b, i):
        self.index = (self.index + 1) % len(self.pages)
        await i.response.edit_message(embed=self.current(), view=self)
```

Circular navigation (modulo wrapping). No `✕ Close` button — designed for lightweight use.

**Used by:** `minigames.py` (`PaginatedHelpView` adapts this pattern for its 300+ game list); `help_system.py` internal commands.

### 2.3 `HelpSystem` Cog

**Group:** `/help_cat` — distinct name avoids collision with `Help` cog's `/help` command.

#### `/help_cat main [category]`
- No category: sends `_category_list_embed()` (ephemeral)
- With category: sends `_category_detail_embed_dynamic(category, bot)` which introspects loaded cogs to build a command list from `cog.get_commands()`

**Autocomplete for `category` param:**
```python
async def _help_category_autocomplete(self, interaction, current):
    choices = [app_commands.Choice(name=name, value=name)
               for name, _ in CAT_LIST if current.lower() in name.lower()]
    return choices[:25]
```

#### `help_prefix(ctx, category=None)` — internal delegation bridge
Not registered as a bot command directly. Called by bot.py if needed. Delegates to `Help` cog's `_send_category_help()` method if available, falling back to `_category_detail_embed()`.

**Debug logging:** Prints `[HELP_SYSTEM debug]` lines to console for troubleshooting category delegation failures:
```python
print(f"[HELP_SYSTEM debug] Delegating prefix help for '{category}' to Help cog")
```

### 2.4 Setup Guard

```python
async def setup(bot):
    if bot.get_cog('HelpSystem') is not None:
        return   # prevent double-registration on cog reload
    await bot.add_cog(HelpSystem(bot))
    # No prefix 'help' command registered here — defers to Help cog
```

The comment explicitly documents the decision not to register a prefix `help` command here, leaving it to `help.py`.

---

## 3. About Guide

**File:** `cogs/about.py` — 258 lines  
**Purpose:** A 9-page interactive bot guide delivered directly to a user's DMs. The guide covers every major system and serves as the first-time user onboarding reference.

### 3.1 `PAGES` List

Module-level list of 9 dicts, each with `title`, `description`, and `color`:

| Page | Title | Color |
|---|---|---|
| 1 | 🎮 Welcome to Ludus — The Ultimate Discord MMO | Gold |
| 2 | 💰 Economy & Shop | Green |
| 3 | 🎰 Gambling & Casino | Orange `#FFA500` |
| 4 | 🎣⛏️🚜 Fishing · Mining · Farming | Light green `#8BC34A` |
| 5 | 🎲 Board & Card Games | Blue |
| 6 | ⚔️ RPG — Infinity Adventure & Wizard Wars | Dark Purple |
| 7 | 🌍 Global Events | Red |
| 8 | 🐾 Pets & Social | Pink `#FF6496` |
| 9 | 💡 Tips & Quick Start | Gold |

All emoji in the strings use Python Unicode escapes (`\U0001f3ae`, `\u2022`, etc.) for encoding safety — the file is written with explicit UTF-8 BOM-free encoding.

### 3.2 `AboutView`

A `discord.ui.View` with `timeout=120`. Stores `author_id` for requester-only interaction checks.

**State:** `self.page` integer (0-indexed).

**`build_embed() → discord.Embed`:**
1. Reads `PAGES[self.page]`
2. Creates embed with title, description, color from the page dict
3. Footer: `Page X / 9  ·  Ludus Bot`
4. Calls `_update_buttons()` to disable Prev on page 0 and Next on page 8

**`_update_buttons()`:**
```python
self.prev_btn.disabled = (self.page == 0)
self.next_btn.disabled = (self.page == len(PAGES) - 1)
```

**`_check(interaction) → bool`:**
```python
if interaction.user.id != self.author_id:
    await interaction.response.send_message("This isn't your guide!", ephemeral=True)
    return False
return True
```
All three button handlers call `_check()` first — only the user who invoked the command can navigate their guide.

**Buttons:**
| Button | Label | Style |
|---|---|---|
| `prev_btn` | `◄ Prev` | Secondary |
| `next_btn` | `Next ►` | Primary |
| `close_btn` | `✕ Close` | Danger → deletes message + `self.stop()` |

### 3.3 `About` Cog

#### `_send_dm(user, ctx_or_interaction)`

The unified DM delivery method:
```python
async def _send_dm(self, user, ctx_or_interaction):
    view = AboutView(user.id)
    embed = view.build_embed()            # builds page 1 embed
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    try:
        dm = await user.create_dm()       # opens DM channel
        await dm.send(embed=embed, view=view)
        # Reply in server with ephemeral confirmation
        msg = "📬 Check your DMs for the interactive Ludus guide!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
    except discord.Forbidden:
        # User has DMs closed
        msg = "❌ I couldn't DM you! Please enable DMs from server members, then try again."
        ...
```

**Why DMs?** The 9-page guide with navigation buttons would clutter a server channel. Sending to DMs keeps it persistent, private, and accessible without channel spam. The ephemeral in-server reply confirms the DM was sent without leaving a visible message.

#### Commands

| Command | Description |
|---|---|
| `L!about` | Send 9-page interactive guide to user's DMs |
| `/about` | Slash version — same behavior |

Both delegate to `_send_dm(user, ctx_or_interaction)`.

---

## 4. Utilities

**File:** `cogs/utilities.py` — ~220 lines  
**Purpose:** Miscellaneous utility commands: ping, invite, setup guide, say (owner), feedback, reminders. Also contains shared helper classes (`Paginator`, `Colors`, `Emojis`) used throughout the cog.

### 4.1 Module-Level Definitions

#### `Colors` class
Simple namespace for `discord.Color` constants:
```python
class Colors:
    PRIMARY   = discord.Color.blue()
    SECONDARY = discord.Color.green()
    ERROR     = discord.Color.red()
```

#### `Emojis` class
Emoji constants as string attributes (`SPARKLES`, `COIN`, `TROPHY`, etc.).

#### `ALLOWED_SAY_USER_ID` tuple
Hardcoded tuple of 3 user IDs authorized to use the `L!say` command:
```python
ALLOWED_SAY_USER_ID = (1382187068373074001, 1311394031640776716, 1138720397567742014)
```

#### `_parse_ts(s)` helper
Shared with other cogs — parses ISO timestamp strings with or without timezone info, attaching UTC if naive:
```python
d = _dt.fromisoformat(str(s))
return d if d.tzinfo else d.replace(tzinfo=_tz.utc)
```

### 4.2 `Paginator` View

A reusable paginated embed viewer distinct from `HelpView`. Features:
- `◀️ Previous` / `▶️ Next` prefix-style buttons
- `❌ Close` button deletes the message and calls `self.stop()`
- Requester-only check via `interaction.user != self.ctx.author`
- Constructor: `__init__(ctx, pages)` — stores the `ctx` for author matching

Used when a prefix command needs to show multiple pages of content.

### 4.3 `Utilities` Cog

#### Data Files

| File | Purpose |
|---|---|
| `reminders.json` | Persistent reminder storage |
| `server_prefixes.json` | Per-server custom prefix overrides |

Both are stored at `RENDER_DISK_PATH` (or `.` as fallback). Loaded via `load_json()` on startup.

`save_json()` uses a simple direct write (not atomic) — reminders are low-stakes enough that partial writes on crash are acceptable, though an upgrade to atomic writes would be consistent with the rest of the codebase.

#### `check_reminders` Task

```python
@tasks.loop(seconds=60)
async def check_reminders(self):
    now = discord.utils.utcnow()
    for user_id, reminders in list(self.reminders.items()):
        for reminder in reminders[:]:
            remind_time = _parse_ts(reminder['time'])
            if now >= remind_time:
                user = await self.bot.fetch_user(int(user_id))
                # sends DM embed with title "⏰ Reminder!" + message content
                reminders.remove(reminder)
                updated = True
    if updated:
        self.save_json(...)
```

Runs every 60 seconds. Uses `_parse_ts()` for timezone-safe comparison. On delivery failure (user blocked DMs, left server) exceptions are silently caught. The task starts in `cog_load()`.

**Reminder data structure (per user entry):**
```json
{
  "<user_id>": [
    {
      "time": "2026-01-01T12:00:00+00:00",
      "message": "Buy milk",
      "set_ago": "10 minutes ago"
    }
  ]
}
```

#### Core Commands

**`L!ping`**
```python
await ctx.send(f"Pong! {round(self.bot.latency*1000)}ms")
```
Simple latency display using `bot.latency` (WebSocket heartbeat RTT in seconds).

**`L!invite`**
Returns a bot invite link. Currently shows a placeholder string `"Invite me: <your_bot_invite_link_here>"` — intended to be replaced with the actual OAuth2 URL.

**`L!setup`**
Builds and sends the setup guide embed via `create_setup_embed()`. No admin restriction — any user can view the setup guide.

**`L!say <text>`**
Echo command requiring the user's ID to be in `ALLOWED_SAY_USER_ID`. Used by specific bot operators to post messages through the bot. The permission check is a simple tuple membership test rather than a decorator.

**`L!feedback <text>`**
Posts an embed to a hardcoded feedback channel ID (`1467981316028108918`). The embed shows the author's display name and avatar but explicitly **omits** any user ID or snowflake for privacy. Sends a confirmation `✅ Thank you!` to the user.

### 4.4 `create_setup_embed() → discord.Embed`

The most detailed method in the cog. Produces a multi-section gold embed titled `🎮 Welcome to Ludus — Quick Setup Guide`.

**Field breakdown:**

| Field | Contents |
|---|---|
| 🚀 Quick Start | `L!daily`, `L!balance`, `L!shop`, `L!quests`, `/fish cast` |
| 💰 Economy | balance, leaderboard, inventory, shop, buy, sell, sub-currencies |
| 🎲 Games & Casino | ttt, connect4, chess, /blackjack, /poker, /slots, /roulette, /uno, /monopoly |
| 🎣⛏️🚜 Simulators | /fish cast, /mine, /farm view, /farm plant |
| 🌍 Global Events | event war, event worldboss, event hunt, L!joinfaction syntax |
| ⚙️ Server Admin Setup | /starboard set, /server_config counting, /server_config welcome |

Footer: `L!help [category] or /help for full command list  ·  Ludus Bot`

---

## 5. Server & User Info

**File:** `cogs/serverinfo.py` — 267 lines  
**Purpose:** Two informational commands: `L!serverinfo` (comprehensive guild stats) and `L!userinfo` (detailed member profile pulling from Discord API + Ludus data files).

### 5.1 Module-Level Constants

#### `BADGE_MAP`

```python
BADGE_MAP = {
    "staff":                  ("🛠️", "Discord Staff"),
    "partner":                ("🤝", "Partnered"),
    "hypesquad":              ("🏠", "HypeSquad Events"),
    "bug_hunter":             ("🐛", "Bug Hunter"),
    "hypesquad_bravery":      ("🔥", "HypeSquad Bravery"),
    "hypesquad_brilliance":   ("💡", "HypeSquad Brilliance"),
    "hypesquad_balance":      ("⚖️", "HypeSquad Balance"),
    "early_supporter":        ("👴", "Early Supporter"),
    "bug_hunter_level_2":     ("🐞", "Bug Hunter Lv.2"),
    "verified_bot_developer": ("🤖", "Verified Bot Dev"),
    "active_developer":       ("🔧", "Active Developer"),
}
```

Keyed by `public_flags` attribute names. Used in `_build_userinfo_embed()` to render a `🏅 Badges` field.

#### `VERIFICATION_LABELS`

Maps `discord.VerificationLevel` enum values to human-readable strings:
```
None → "None"
Low  → "Low (email)"
Medium → "Medium (5 min)"
High → "High (10 min)"
Highest → "Highest (phone)"
```

#### `STATUS_ICONS`

Maps `discord.Status` enums to colored circle emojis:
```
online   → 🟢
idle     → 🟡
dnd      → 🔴
offline  → ⚫
invisible → ⚫
```

### 5.2 `_load_json(path) → dict`

A simple helper that reads a JSON file or returns `{}` on any exception. Used for reading `economy.json` and `profiles.json` without crashing if files are missing.

### 5.3 `_build_serverinfo_embed(guild) → discord.Embed`

Standalone function (not a method) that constructs a `discord.Embed` from guild data.

**Computed values:**
```python
total  = guild.member_count or len(guild.members)
bots   = sum(1 for m in guild.members if m.bot)
humans = total - bots
online = sum(1 for m in guild.members if m.status != discord.Status.offline)
```

**Boost tier icons:**
```python
boost_icons = {0: "📊", 1: "🥉", 2: "🥈", 3: "🥇"}
```

**Fields built:**

| Field | Contents |
|---|---|
| 🆔 ID | Guild ID in backticks |
| 👑 Owner | Owner mention |
| 📅 Created | Discord relative + absolute timestamp |
| 🔗 Vanity URL | `discord.gg/<code>` (only if set) |
| 👥 Members | Humans, bots, online, total (each with icon) |
| 📺 Channels | Text, voice, stage, categories counts |
| 🎨 Other | Roles count, emoji count / limit, file upload limit |
| 💎 Boosts | Tier (with icon), boost count, booster count |
| 🛡️ Security | Verification level, 2FA moderation, NSFW level |
| ⭐ Features | Up to 8 features with emoji prefixes (VERIFIED ✅, PARTNERED 🤝, etc.), `+N more` if capped |

**Thumbnail:** Guild icon  
**Image:** Guild banner (full-width, below fields)  
**Color:** `discord.Color.blurple()`  
**Timestamp:** Current UTC `discord.utils.utcnow()`

### 5.4 `_build_userinfo_embed(member) → discord.Embed`

Builds a rich `discord.Embed` combining Discord member data with Ludus game stats.

**Color:** Uses `member.color` (top role color) unless it's `discord.Color.default()`, in which case falls back to blurple. This makes the embed border match the user's highest role color.

**Base fields:**

| Field | Source |
|---|---|
| 🪪 Username | `str(member)` (e.g. `username`) |
| 🆔 User ID | `member.id` in backticks |
| 🤖 Bot | Yes / No |
| 📅 Account Created | Discord timestamp — date + relative |
| 📥 Joined Server | `member.joined_at` — date + relative |

**Status + Activity field:**

The activity string is built by type inspection:
```python
if isinstance(act, discord.Spotify):
    activity_str = f"🎵 {act.title} — {act.artist}"
elif isinstance(act, discord.Game):
    activity_str = f"🎮 {act.name}"
elif isinstance(act, discord.Streaming):
    activity_str = f"📺 {act.name}"
elif isinstance(act, discord.CustomActivity) and act.name:
    activity_str = act.name
```
Combined with the `STATUS_ICONS` circle emoji to produce e.g. `🟡 Idle\n🎮 Minecraft`.

**Badges field:**
Iterates `BADGE_MAP`, checking `member.public_flags.<key>`. Server Booster is prepended separately:
```python
if member.premium_since:
    badges.insert(0, f"💎 Server Booster (since <t:{...}:D>)")
```

**Roles field:**
Roles sorted by position (highest first), `@everyone` excluded. Capped at 20:
```python
role_str = " ".join(r.mention for r in roles[:20])
if len(roles) > 20:
    role_str += f" … +{len(roles) - 20} more"
```
Field title includes total count: `🎭 Roles [12]`.

**Ludus Stats field:**
Reads `economy.json` and `profiles.json` from `DATA_PATH`. The field is only added if at least one file contains data for the user:

From `economy.json`:
- 💰 Balance (PsyCoins)
- 🔥 Daily Streak
- 📈 Total Earned
- 🐟 FishCoins (if non-zero)
- ⛏️ MineCoins (if non-zero)
- 🌾 FarmCoins (if non-zero)

From `profiles.json`:
- ⭐ Level + XP
- 🎮 Games Won / Played (minigames)

**Footer:** `ID: <member.id>`  
**Thumbnail:** `member.display_avatar.url`

### 5.5 `ServerInfo` Cog

#### Commands

| Command | Aliases | Permission | Description |
|---|---|---|---|
| `L!serverinfo` | `server`, `si` | Guild only | Show server statistics embed |
| `/serverinfo` | — | Guild only | Slash version |
| `L!userinfo [@member]` | `ui`, `whois`, `memberinfo` | Guild only | Show user info (defaults to self) |
| `/userinfo [member]` | — | Guild only | Slash version with optional member parameter |

All commands are decorated with `@commands.guild_only()` / `@app_commands.guild_only()` — they cannot be used in DMs.

The prefix `userinfo` command accepts a `discord.Member` via Discord.py's converter. If no member is provided, `ctx.author` is used. The slash version uses `interaction.guild.get_member(interaction.user.id)` as the fallback.

---

## 6. Cross-System Integration

### help.py ↔ owner.py

When `/help owner` or `L!help owner` is requested by a bot owner:
```python
owner_cog = self.bot.get_cog('Owner')
ownerhelp_cmd = owner_cog.owner_help
await ownerhelp_cmd(ctx_or_fake_ctx)
```
The `FakeCtx` bridge class wraps a slash `Interaction` so the prefix-based `owner_help` command can be called during a slash interaction context.

### help_system.py ↔ help.py

`HelpSystem.help_prefix()` delegates to `Help._send_category_help()` when the `Help` cog is loaded:
```python
help_cog = self.bot.get_cog('Help')
if help_cog is not None:
    await help_cog._send_category_help(ctx, category.lower(), is_owner, is_slash=False)
```
This makes `HelpSystem` a fallback scaffold that gracefully hands off to the richer cog.

### help_system.py → minigames.py

`HelpView` is imported/adapted by `minigames.py` as `PaginatedHelpView` for its 300+ game list. The pattern — `pages: List[discord.Embed]`, `Prev/Next` buttons, modulo wrapping — is identical.

### utilities.py ↔ Economy cog

No direct coupling. The setup guide describes economy commands but does not call `get_cog("Economy")`.

### serverinfo.py ↔ economy.json / profiles.json

Direct file reads (no cog dependency):
```python
eco  = _load_json(os.path.join(DATA_PATH, "economy.json")).get(uid_str)
prof = _load_json(os.path.join(DATA_PATH, "profiles.json")).get(uid_str)
```
This allows `userinfo` to show Ludus stats without requiring the Economy or Profile cogs to be loaded at the time of the command.

---

## 7. Command Reference

### Help Commands

| Command | Permission | Description |
|---|---|---|
| `L!help` | Any | Main help menu with category dropdown |
| `L!help <category>` | Any | Jump to category (fuzzy key match) |
| `/help` | Any | Slash main help menu |
| `/help [category]` | Any | Slash category help |
| `/help_cat main [category]` | Any | HelpSystem framework with autocomplete |

**Valid category keys:** `economy`, `gambling`, `board`, `cards`, `mini`, `puzzle`, `arcade`, `sims`, `social`, `events`, `quests`, `business`, `premium`, `fun`, `utility`, `admin`, `owner` (owner only)

### About Commands

| Command | Permission | Description |
|---|---|---|
| `L!about` | Any | Send 9-page interactive guide to DMs |
| `/about` | Any | Slash version |

### Utility Commands

| Command | Permission | Description |
|---|---|---|
| `L!ping` | Any | Bot latency in ms |
| `L!invite` | Any | Bot invite link |
| `L!setup` | Any | Show quick setup guide embed |
| `L!say <text>` | Allowed users only | Echo text through bot |
| `L!feedback <text>` | Any | Submit anonymous feedback |

### Server & User Info Commands

| Command | Aliases | Permission | Description |
|---|---|---|---|
| `L!serverinfo` | `server`, `si` | Guild only | Comprehensive server stats |
| `/serverinfo` | — | Guild only | Slash version |
| `L!userinfo [@member]` | `ui`, `whois`, `memberinfo` | Guild only | Detailed member info + Ludus stats |
| `/userinfo [member]` | — | Guild only | Slash version |

---

## 8. Architecture Notes

### Why `help.py` Uses a Manual Category Dict

Discord.py's default `HelpCommand` auto-generates help from command docstrings. While convenient, this produces verbose technical descriptions unsuitable for an end-user guide. The manual dict approach allows:
- Non-technical, user-friendly descriptions
- Selective command exposure (hiding internal commands)
- Section dividers within categories (the `—` header pattern)
- Full control over command ordering and grouping

### Why `about.py` Sends to DMs

The 9-page paginated guide would take up channel scroll space and confuse other server members. DM delivery means:
- The guide persists (visible in DMs history)
- It's private and personalised
- No channel clutter
- The server gets a clean ephemeral "📬 Check your DMs" confirmation

The `discord.Forbidden` handler gracefully tells users to enable DMs rather than silently failing.

### Why `serverinfo.py` Reads JSON Directly

`_build_userinfo_embed()` reads `economy.json` and `profiles.json` via `_load_json()` rather than calling `self.bot.get_cog("Economy")`. This:
- Avoids a hard dependency on the Economy cog being loaded
- Works even if the Economy cog crashed or was unloaded
- Is safe for read-only display (no modification needed)
- The `_load_json()` helper returns `{}` silently if files don't exist, making the Ludus Stats field optional

The trade-off is that if the Economy cog has in-memory unsaved changes, `userinfo` might show slightly stale data. Acceptable for an informational command.

### Reminder System Design

The `check_reminders` task polls every 60 seconds rather than scheduling exact-time callbacks. This means reminders fire within a 60-second window of their set time (not precisely). The trade-off:
- Simpler implementation — no `asyncio.sleep` arithmetic required
- Works correctly across bot restarts (reads from file)
- ≤60 second imprecision acceptable for Discord reminders

---

*Last updated: 2026*  
*Part of the Ludus Bot Documentation Series — Part 11 of 15*  
*Previous: [Part 10 — Server Management](FULL_DOCUMENTATION_PART10.md)*  
*Next: Part 12 — Admin & Owner Commands (planned)*
