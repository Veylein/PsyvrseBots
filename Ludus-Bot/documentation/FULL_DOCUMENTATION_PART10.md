# 🛡️ LUDUS BOT — FULL DOCUMENTATION PART 10
## Server Management Systems

**Files Covered:** `starboard.py` (449 lines) · `counting.py` (~350 lines) · `confessions.py` (~230 lines) · `globalevents.py` (675 lines)  
**Total Lines:** ~1,700 lines  
**Category:** Server Management

---

## Table of Contents

1. [Starboard System (starboard.py)](#1-starboard-system)
2. [Counting Game (counting.py)](#2-counting-game)
3. [Confessions System (confessions.py)](#3-confessions-system)
4. [Global Events (globalevents.py)](#4-global-events)
5. [Cross-System Integration](#5-cross-system-integration)
6. [Data Structures Reference](#6-data-structures-reference)
7. [Command Reference](#7-command-reference)

---

## 1. Starboard System

**File:** `cogs/starboard.py` — 449 lines  
**Purpose:** Automatically highlights popular messages by tracking emoji reactions across one or more configurable "starboards" per server.

### 1.1 Overview

The Starboard system monitors reaction events on all messages in a guild. When a message accumulates enough reactions of a tracked emoji (custom or Unicode), it is automatically posted (or updated) in a designated channel — the **starboard channel**. As reaction counts change the post is edited in-place to stay current; if reactions fall below the threshold the post is removed entirely.

Key traits:
- Up to **5 independent starboards** per server (each monitoring a different emoji)
- Reaction threshold configurable per board (minimum 1)
- Optional **self-star prevention** — stops authors from starring their own messages
- Color-coded embeds that scale visually with popularity (`gold → orange → red`)
- Full image/attachment relay including first-image preview and reply context
- Uses **raw reaction events** (`on_raw_reaction_add` / `on_raw_reaction_remove`) so old cached-out messages are handled correctly

### 1.2 Module-Level Helpers

#### `load_starboards() → dict`
Reads `starboard.json` from `RENDER_DISK_PATH`. If the file does not yet exist it is created with empty `boards` and `posted_messages` sub-keys. Both keys are `setdefault`-protected so partial files from older versions don't crash the cog.

```python
data.setdefault("boards", {})
data.setdefault("posted_messages", {})
```

#### `save_starboards(data)`
Atomic write: data is written to a `.tmp` file then `os.replace()` is called. This prevents JSON corruption if the process is killed mid-write.

#### `_star_color(count, needed) → discord.Color`
Returns a `discord.Color` that visually communicates popularity:
| Ratio (count / needed) | Color |
|---|---|
| < 1.5 | 🟡 Gold `#FFCC00` |
| 1.5 – 2.5 | 🟠 Orange `#FF8C00` |
| ≥ 2.5 | 🔴 Red-Orange `#FF3C00` |

#### `_star_icon(count, needed) → str`
Emoji shown in the footer / header:
| Ratio | Icon |
|---|---|
| < 2 | `✨` |
| 2 – 3 | `⭐` |
| ≥ 3 | `🌟` |

---

### 1.3 `StarboardGroup` (Slash Command Group)

An `app_commands.Group` named `/starboard` with 4 sub-commands. All management commands require **Manage Guild** permission.

#### `/starboard create`
| Parameter | Type | Required | Description |
|---|---|---|---|
| `emoji` | str | ✅ | Reaction emoji to track |
| `channel` | TextChannel | ✅ | Where starred messages are posted |
| `amount` | int | ✅ | Reaction threshold (≥ 1) |
| `allow_self_star` | bool | ❌ | Allow authors to star their own posts (default: `False`) |

**Guards:**
- Duplicate emoji check — rejects if the same emoji is already tracked
- Server cap — maximum **5** starboards per server
- Amount must be ≥ 1

**Storage structure created:**
```json
"boards": {
  "1234567890": {
    "⭐": {
      "channel": 9876543210,
      "amount": 3,
      "self_star": false
    }
  }
}
```

#### `/starboard edit`
Edits any combination of threshold, channel, or self-star setting on an existing board.  
All three update parameters (`amount`, `channel`, `allow_self_star`) are optional — only the ones provided are changed.

#### `/starboard remove`
Deletes the starboard config for a given emoji. **Does not** remove already-posted starboard messages from the channel.

#### `/starboard list`
Lists all active starboards for the server in an ephemeral embed showing emoji, target channel, threshold, and self-star status.

---

### 1.4 `Starboard` Cog

#### Constructor
```python
def __init__(self, bot):
    self.data = load_starboards()      # in-memory data
    self._group = StarboardGroup(self)
    bot.tree.add_command(self._group)  # register slash group manually
```

The group is also manually removed in `cog_unload()` to avoid duplicate registration on reload.

#### Prefix Command Group (`L!starboard`)

Backwards-compatible prefix commands mirror every slash sub-command:

| Command | Description |
|---|---|
| `L!starboard create <emoji> <#channel> <amount>` | Create new starboard |
| `L!starboard edit <emoji> <amount>` | Change reaction threshold only |
| `L!starboard remove <emoji>` | Remove a starboard |
| `L!starboard list` | List all starboards |

The prefix `edit` command only allows changing the threshold (not channel or self-star), making it slightly less powerful than the slash version.

---

### 1.5 `_build_embed(message, emoji, count, needed) → discord.Embed`

The richest method in the file. Constructs the embed posted in the starboard channel for a qualifying message.

**Author row:** author's display name + avatar set via `embed.set_author()`.

**Content relay:**
1. `message.content` → `embed.description`
2. Attachments: first image attachment is set as `embed.set_image()`; additional attachments appear as link fields titled `📎 Attachment`
3. Embed previews: if no attachment image was found, the original embed's `image` or `thumbnail` is used; if there's no text content the original embed's description is shown

**Reply context:** If the starred message was a reply, a field is added:
```
↩️ Replying to <author> : <first 100 chars of replied content>…
```

**Navigation row:** Two inline fields are appended — a "Jump to message" hyperlink and the source channel mention.

**Footer:** Combines the dynamic star icon, reaction count, and channel name.
```
🌟 12  ·  #general
```

---

### 1.6 Reaction Event Processing

Both `on_raw_reaction_add` and `on_raw_reaction_remove` delegate to `_process_reaction(payload)`, which:

1. Checks the guild has a starboard for the reacted emoji
2. Fetches the message (works on uncached messages via `fetch_message`)
3. Ignores reactions on the starboard channel itself (prevents starboard-of-starboard loops)
4. Applies self-star guard on `REACTION_ADD` events only
5. Counts the current total reactions for that emoji
6. Determines the unique `message_key`: `{guild_id}_{message_id}_{emoji}`

**Below threshold flow:**
- If a stored post exists → fetches it from the starboard channel → deletes it → removes the key from `posted_messages` → saves

**At/above threshold flow — existing post:**
```
fetch existing starboard message → edit(content=header, embed=embed)
```
If the message was deleted externally (`NotFound`) the key is cleared and flow falls through to "create new post".

**At/above threshold flow — no existing post:**
```
send(content=header, embed=embed) → store new message ID → save
```

The `header` line format:
```
🌟 **12** — #general
```

---

### 1.7 Data File: `starboard.json`

```json
{
  "boards": {
    "<guild_id>": {
      "<emoji>": {
        "channel": 1234567890,
        "amount": 5,
        "self_star": false
      }
    }
  },
  "posted_messages": {
    "<guild_id>_<message_id>_<emoji>": 9876543210
  }
}
```

`posted_messages` maps a composite key to the ID of the message posted in the starboard channel. This enables in-place editing and threshold-based removal.

---

## 2. Counting Game

**File:** `cogs/counting.py` — ~350 lines  
**Purpose:** Turns any text channel into a collaborative counting channel where members count up sequentially, earn PsyCoins, and receive milestone roles.

### 2.1 Overview

Once a counting channel is configured for a guild, every non-bot, non-command message in that channel is inspected:
- Non-numeric messages are silently deleted
- Numbers that don't match the expected next count are rejected
- The same user cannot count twice in a row (anti-cheat)
- Correct counts increment a persistent counter, award incremental coins, and trigger milestone rewards

### 2.2 Constructor

```python
def __init__(self, bot):
    self.file_path = os.path.join(_data_dir, "counting.json")
    self.load_data()
    
    self.milestone_rewards = {
        25: 10, 50: 20, 100: 50,
        250: 100, 500: 350, 1000: 500
    }
    
    self.milestones = [
        25, 50, 100, 125, 250,
        500, 1000, 1250, 1500, 5000, 10000, 25000
    ]
    
    self.message_numbers = {}       # message_id → {number, user_id, guild_id}
    self.user_counts = self.load_user_counts()
```

Two separate files are used:
| File | Contents |
|---|---|
| `counting.json` | Per-guild counting state (current count, channel, last user) |
| `counting_user_counts.json` | Per-user, per-guild count totals for reward tracking |

### 2.3 Persistent Data

#### `counting.json` structure:
```json
{
  "<guild_id>": {
    "channel": 1234567890,
    "current_count": 42,
    "last_user": 987654321
  }
}
```

#### `counting_user_counts.json` structure:
```json
{
  "<user_id>": {
    "<guild_id>": 17
  }
}
```

### 2.4 `on_message` Listener

**Full decision tree:**

```
message received
  └─ is bot → ignore
  └─ is DM → ignore
  └─ guild has counting config? → no → ignore
  └─ is counting channel? → no → ignore
  └─ try int(content)
      └─ ValueError → delete message, return
  └─ author == last_user? → delete + warn "can't count twice in a row", auto-delete warning after 5s
  └─ number != expected → delete + warn "expected X got Y", auto-delete warning after 5s
  └─ correct number:
      ├─ update current_count + last_user, save
      ├─ update leaderboard peak via leaderboard_manager
      ├─ cache in message_numbers for delete detection
      ├─ update user_counts, save
      ├─ check coins (2 coins per 4 correct counts)
      ├─ check milestone_rewards (bonus coins + embed announcement)
      ├─ award coins via Economy cog
      ├─ add ✅ reaction to message
      └─ check milestones list → give_milestone_role()
```

**PsyCoin earning rate:** 2 coins every 4 correct counts = **0.5 coins per count on average**

**Milestone coin bonuses:**
| Count | Bonus |
|---|---|
| 25 | 10 PsyCoins |
| 50 | 20 PsyCoins |
| 100 | 50 PsyCoins |
| 250 | 100 PsyCoins |
| 500 | 350 PsyCoins |
| 1000 | 500 PsyCoins |

Milestone bonuses appear in a gold embed that auto-deletes after 15 seconds.

### 2.5 `on_message_delete` Listener

Watches `message_numbers` for cached counting messages. If a counted number's message is deleted, the bot posts:

> **🚫 Hey that's no fair!**  
> @user deleted their number but don't worry I saw it was the number **42**

This prevents users from deleting their numbers to bypass the consecutive counting rule.

### 2.6 `give_milestone_role(message, number)`

When a milestone number from the `milestones` list is reached:
1. Looks for a role named `Counter {number}` in the guild
2. If the role doesn't exist, creates it (mentionable, no special color)
3. Grants the role to the counting member

Role names: `Counter 25`, `Counter 50`, `Counter 100`, …, `Counter 25000`

### 2.7 Commands

#### Prefix Commands

| Command | Permission | Description |
|---|---|---|
| `L!counting [#channel]` | Administrator | Enable counting in the specified channel (or current) |
| `L!countingremove` | Administrator | Disable counting for the server |

#### Slash Commands (Group: `/counting`)

| Command | Permission | Description |
|---|---|---|
| `/counting setup [channel]` | Administrator | Enable counting game |
| `/counting remove` | Administrator | Disable counting game |

### 2.8 Leaderboard Integration

On every valid count, the bot reports the current count to `leaderboard_manager`:
```python
leaderboard_manager.update_peak(message.guild.id, "counting_peak", number, server_name=message.guild.name)
```
This tracks the all-time server counting record and feeds the global leaderboard system.

---

## 3. Confessions System

**File:** `cogs/confessions.py` — ~230 lines  
**Purpose:** Allows users to submit anonymous messages to a designated channel. The bot intercepts messages, deletes the originals, and reposts them under a numbered `CONFESSION #X` format. A separate admin-only log channel records who submitted each confession.

### 3.1 Overview

The confession flow is entirely event-driven. No slash commands are used for submission — users simply type in the configured channel. Admin management is handled through a `L!confession` command group.

**Privacy model:**
- Public channel: sees only `🔒 CONFESSION #X` embed with no identifying information
- Log channel: admins see full username, user ID, avatar, and message content
- The original message is deleted before either embed is sent

### 3.2 Constructor

```python
def __init__(self, bot):
    self.config_file = os.path.join(_data_dir, "confession_config.json")
    self.load_config()
```

Config is a flat dict keyed by `guild_id`:
```json
{
  "<guild_id>": {
    "confession_channel": 1234567890,
    "log_channel": 9876543210,
    "confession_count": 47
  }
}
```

### 3.3 `get_server_config(guild_id) → dict`

Lazy-initializes a config entry for a guild if it doesn't exist yet. Default state has both channels as `None` and count at `0`. The config is saved immediately after creation.

### 3.4 `save_config()` — Atomic Write

```python
def save_config(self):
    tmp = self.config_file + ".tmp"
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
        os.replace(tmp, self.config_file)
    except Exception as e:
        print(f"[Confessions] Save error: {e}")
        try:
            os.remove(tmp)    # clean up .tmp if os.replace fails
        except OSError:
            pass
```

The `except` block explicitly removes the `.tmp` file if the atomic replace fails, preventing stale partially-written files.

### 3.5 Admin Command Group: `L!confession`

All sub-commands require **Administrator** permission.

| Sub-command | Description |
|---|---|
| `L!confession set #channel` | Set the public confession channel |
| `L!confession setlog #channel` | Set the private admin log channel |
| `L!confession status` | Show current configuration and total count |
| `L!confession disable` | Remove all config for this server |

`L!confession setlog` has an alias: `L!confession logchannel`

Running `L!confession` with no sub-command shows a help embed listing all sub-commands.

#### `L!confession status` output fields:
- **Confession Channel** — mention or `❌ Not set`
- **Log Channel** — mention or `❌ Not set`
- **Total Confessions** — running integer count
- **Status** — `✅ System Active` (both channels set) or `⚠️ Incomplete Setup`

### 3.6 `on_message` Listener — Submission Flow

```
message received
  └─ is bot → ignore
  └─ is DM → ignore
  └─ not in confession channel → ignore
  └─ starts with 'L!', '/', '!' → ignore (commands pass through)
  └─ empty content → ignore
  
  → try: delete original message
  → increment confession_count, save config
  
  → post confession embed to confession channel:
       title: "🔒 CONFESSION #X"
       description: message content
       footer: "Anonymous Confession"
  
  → if log_channel configured:
       post log embed with:
         title: "📋 Confession Log #X"
         User field: mention + name#discriminator
         User ID field: backtick-formatted ID
         Confession Content field: up to 1024 chars
         thumbnail: author's avatar
```

**Order of operations matters:** The original message is deleted *before* the embeds are sent, so there is no window where both the original and the anon version coexist.

**Command passthrough:** Messages starting with `L!`, `/`, or `!` are explicitly skipped. This allows admins to run setup commands in the confession channel without accidentally triggering the confession flow.

---

## 4. Global Events

**File:** `cogs/globalevents.py` — 675 lines  
**Purpose:** Owner-only system for launching cross-server global events that engage all guilds the bot serves simultaneously. Supports four event types: **WAR**, **World Boss**, **Target Hunt**, and **Chaos Festival**.

### 4.1 Overview

Global events broadcast to every guild in `bot.guilds` using the `system_channel` or the first available text channel. Events are stored in `active_events` (in-memory dict) and persisted to `global_events.json`. The bot owner controls all events via `L!event` with sub-type arguments.

### 4.2 `AttackView`

A persistent Discord UI view (`timeout=None`) that shows during an active World Boss event. It adds an `⚔️ Attack!` button (`ButtonStyle.danger`, `custom_id="worldboss_attack"`) to the broadcast embed.

**Per-user cooldown:** 30 seconds enforced with a per-user timestamp dict inside `boss_data["cooldowns"]`. The cooldown is implemented manually (not via `commands.cooldown`) so it works identically whether the user clicks the button or uses `L!attack`.

**Enrage phase toggle:** When ≥ 75% of the boss's max HP has been depleted, the damage range is multiplied by 1.5 and the embed gains a `🔥 ENRAGED!` tag.

**Auto-stop on kill:** When `boss_data["hp"]` reaches 0 the button handler calls `cog.defeat_worldboss(interaction.channel)` then `self.stop()` to disable further button clicks.

### 4.3 Constructor

```python
self.factions = {
    "iron": {"name": "⚔️ Iron Legion",  "color": 0x808080},
    "ash":  {"name": "🔥 Ashborn",       "color": 0xFF4500},
    "void": {"name": "🌑 Voidwalkers",   "color": 0x4B0082},
    "sky":  {"name": "🌬️ Skybound",      "color": 0x87CEEB}
}

self.bosses = {
    "void_titan":  {"name": "Void Titan",  "hp": 50_000_000, "damage_range": (1000, 5000)},
    "storm_king":  {"name": "Storm King",  "hp": 75_000_000, "damage_range": (1500, 6000)},
    "shadow_lord": {"name": "Shadow Lord", "hp": 100_000_000,"damage_range": (2000, 8000)},
    "chaos_beast": {"name": "Chaos Beast", "hp": 60_000_000, "damage_range": (1200, 5500)}
}
```

All bosses and factions are defined as in-memory class-level dicts (not JSON) so they are always available without file I/O.

---

### 4.4 Event Type: WAR

**Command:** `L!event war [hours]` (default: 24 hours)

#### Startup
- Creates `active_events["war"]` with one entry per faction: `{servers: [], points: 0, members: []}`
- Broadcasts a war announcement embed to every guild's system channel
- Schedules `_auto_end_war()` as a background `asyncio.Task`

#### Joining Factions: `L!joinfaction <iron|ash|void|sky>`
- Checks that a WAR event is running
- Verifies the user is not already in a faction (cross-faction dupe check loops all factions)
- Appends the user to `faction_data["members"]` and the server ID to `faction_data["servers"]`

#### War Points
The `add_war_points(user_id, guild_id, points)` method is a **public API** for other cogs to call when users win games during the war. It finds the user's faction and adds the points to that faction's total.

#### Leaderboard: `L!warleaderboard`
Sorts factions by `points` descending, shows medal emojis (🥇🥈🥉4️⃣), member counts, server counts, and point totals.

#### End Conditions
- Automatic: `_auto_end_war()` background task fires after `hours * 3600` seconds
- Manual: `L!event end war`

On end: sorts factions, announces the winning faction, rewards all winning faction members with **10,000 PsyCoins** each.

**War event data structure:**
```json
{
  "war": {
    "end_time": "2026-01-01T12:00:00+00:00",
    "started_by": 1234567890,
    "factions": {
      "iron": {"servers": ["111"], "points": 4200, "members": ["123", "456"]},
      "ash":  {"servers": [],      "points": 0,    "members": []},
      "void": {"servers": [],      "points": 0,    "members": []},
      "sky":  {"servers": [],      "points": 0,    "members": []}
    }
  }
}
```

---

### 4.5 Event Type: World Boss

**Command:** `L!event worldboss [boss_name]` (default: `void_titan`)

Valid boss names: `void_titan`, `storm_king`, `shadow_lord`, `chaos_beast`

#### Boss Stats

| Boss | Max HP | Damage Range (normal) | Damage Range (enraged) |
|---|---|---|---|
| Void Titan | 50,000,000 | 1,000 – 5,000 | 1,500 – 7,500 |
| Storm King | 75,000,000 | 1,500 – 6,000 | 2,250 – 9,000 |
| Shadow Lord | 100,000,000 | 2,000 – 8,000 | 3,000 – 12,000 |
| Chaos Beast | 60,000,000 | 1,200 – 5,500 | 1,800 – 8,250 |

#### Data Structure During Event
```json
{
  "worldboss": {
    "boss": "void_titan",
    "hp": 49123456,
    "max_hp": 50000000,
    "participants": {"<user_id>": 876543},
    "server_damage": {"<guild_id>": 1234567},
    "cooldowns": {"<user_id>": "2026-01-01T12:00:30+00:00"},
    "last_hit": "<user_id>",
    "started": "2026-01-01T12:00:00+00:00"
  }
}
```

#### Attacking: `L!attack`
- Checks active worldboss event exists
- `commands.cooldown(1, 30, BucketType.user)` enforced at prefix level
- Calculates enrage multiplier based on HP percentage lost
- Random damage in range, subtracted from boss HP
- Tracks `participants[user_id]` (total damage), `server_damage[guild_id]`, and `last_hit`
- Shows HP progress bar (20 blocks of `🟩`/`⬜` or `🟥` when enraged)

#### Defeat: `defeat_worldboss(channel)`
Reward distribution:
| Recipient | Reward |
|---|---|
| **All** participants | 5,000 base + `damage / 100` coins |
| Top 10 damage dealers | 10,000 → 1,000 (decreasing by 1,000 per rank) |
| Last hit | 15,000 flat bonus |

After rewards the event is removed from `active_events` and the file is saved.

#### Boss Stats: `L!bossstats`
Shows live HP bar, total attackers, server count, and **Top 5 Servers** with their total damage. Server names are resolved from the bot's guild cache (shows truncated ID if guild not cached).

---

### 4.6 Event Type: Target Hunt

**Command:** `L!event hunt [minutes]` (default: 30 minutes)

Launches a global scavenger hunt with automated challenges that fire every 1–3 minutes.

**Challenge types registered:**
```python
self.hunt_challenges = [
    {"type": "message",  "desc": "Send a message containing the word '{word}'"},
    {"type": "reaction", "desc": "React to this message with {emoji}"},
    {"type": "riddle",   "desc": "Solve this riddle: {riddle}"},
    {"type": "speed",    "desc": "Type this phrase exactly: '{phrase}'"},
]
```

The `run_hunt_challenges()` coroutine runs as a background `asyncio.Task`, sleeping between 60–180 seconds and broadcasting a new challenge embed to all guilds until the event's `end_time` or until the event is manually ended.

**Note:** Only the `message` challenge type is fully implemented in the current codebase. The `reaction`, `riddle`, and `speed` types have data structures defined but their detection logic is flagged for a future update.

---

### 4.7 Event Type: Chaos Festival

**Command:** `L!event chaos [minutes]` (default: 30 minutes)

Currently a stub:
```python
async def start_chaos_event(self, ctx, minutes):
    await ctx.send("🎭 CHAOS FESTIVAL - Coming in next update!")
```

The type is registered in the command dispatcher and documented in the help text, but the implementation is pending.

---

### 4.8 `L!event` Master Command

**Permission:** `@commands.is_owner()` — only bot owners can trigger global events.

```
L!event list               — Show all active events with end times
L!event end <type>         — Manually end a specific event
L!event war [hours]        — Start WAR faction event
L!event worldboss [boss]   — Start World Boss raid
L!event hunt [minutes]     — Start Target Hunt
L!event chaos [minutes]    — Start Chaos Festival (stub)
```

The `list` sub-command uses Discord relative timestamps `<t:UNIX:R>` for all end times.

The `end` sub-command: the second argument is consumed as the `duration` int parameter but cast to `str` and used as the event type name to end. This is a quirk of the command signature design.

---

### 4.9 `_parse_ts(s)` Helper

Used when reading `end_time` or `cooldowns` timestamps from JSON:
```python
def _parse_ts(s):
    d = _dt.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=_tz.utc)
```

Handles both old naive timestamps (no timezone info) and modern tz-aware ISO strings. Without this guard, comparing a naive datetime against `discord.utils.utcnow()` (which is tz-aware) would raise a `TypeError`.

---

## 5. Cross-System Integration

### Starboard ↔ No other cog
Starboard is self-contained. It does not call the Economy cog and only reads from its own `starboard.json`.

### Counting ↔ Economy + Leaderboard
```python
# Coins
economy_cog = self.bot.get_cog("Economy")
if economy_cog:
    economy_cog.add_coins(message.author.id, total_coins, "counting")

# Leaderboard peak
leaderboard_manager.update_peak(guild.id, "counting_peak", number, server_name=guild.name)
```
The counting cog uses `get_cog()` safely — if the Economy cog is not loaded, coins are simply not awarded (no crash).

### Confessions ↔ No other cog
Confessions is self-contained — it only reads its own config and posts to Discord channels.

### GlobalEvents ↔ Economy + BotLogger
```python
# Reward distribution
economy_cog = self.bot.get_cog("Economy")
economy_cog.add_coins(int(user_id), reward, "worldboss_participation")

# Event logging
logger = self.bot.get_cog("BotLogger")
await logger.log_event_spawn("WAR", guild_id, user_id, details)
await logger.log_event_end("WAR", summary)
```

### GlobalEvents ↔ Other game cogs (intended)
The `add_war_points(user_id, guild_id, points)` method is the public API that fishing, gambling, mining, and other cogs should call when their events fire during an active WAR. Game cogs call:
```python
global_events = self.bot.get_cog("GlobalEvents")
if global_events:
    global_events.add_war_points(ctx.author.id, ctx.guild.id, 10)
```

---

## 6. Data Structures Reference

### `starboard.json`
```
{
  "boards": {
    "<guild_id>": {
      "<emoji_str>": {
        "channel": <int>,        // Channel ID to post starred messages
        "amount": <int>,         // Reaction threshold
        "self_star": <bool>      // Whether authors can star own messages
      }
    }
  },
  "posted_messages": {
    "<guild_id>_<message_id>_<emoji>": <int>  // ID of the starboard post
  }
}
```

### `counting.json`
```
{
  "<guild_id>": {
    "channel": <int>,           // Channel ID for counting
    "current_count": <int>,     // Current count value
    "last_user": <int|null>     // User ID who posted last count
  }
}
```

### `counting_user_counts.json`
```
{
  "<user_id>": {
    "<guild_id>": <int>         // How many times this user has counted
  }
}
```

### `confession_config.json`
```
{
  "<guild_id>": {
    "confession_channel": <int|null>,  // Public anon channel
    "log_channel": <int|null>,         // Admin log channel
    "confession_count": <int>          // Total confessions posted
  }
}
```

### `global_events.json`
```
{
  // Persisted event state (in-memory active_events dict is authoritative during runtime)
}
```
**Note:** The globalevents cog persists `events_data` (historical data) to this file. The currently running `active_events` dict is in-memory only — if the bot restarts during an event, the event is lost.

---

## 7. Command Reference

### Starboard Commands

| Command | Permission | Description |
|---|---|---|
| `/starboard create <emoji> <#ch> <amount> [self_star]` | Manage Guild | Create a starboard |
| `/starboard edit <emoji> [amount] [#ch] [self_star]` | Manage Guild | Edit starboard settings |
| `/starboard remove <emoji>` | Manage Guild | Delete a starboard |
| `/starboard list` | Any | List all starboards |
| `L!starboard create <emoji> <#ch> <amount>` | Manage Guild | Prefix: create |
| `L!starboard edit <emoji> <amount>` | Manage Guild | Prefix: change threshold |
| `L!starboard remove <emoji>` | Manage Guild | Prefix: remove |
| `L!starboard list` | Any | Prefix: list |

### Counting Commands

| Command | Permission | Description |
|---|---|---|
| `L!counting [#channel]` | Administrator | Enable counting |
| `L!countingremove` | Administrator | Disable counting |
| `/counting setup [channel]` | Administrator | Enable counting |
| `/counting remove` | Administrator | Disable counting |

### Confession Commands

| Command | Permission | Description |
|---|---|---|
| `L!confession` | Administrator | Show help for confession system |
| `L!confession set #channel` | Administrator | Set confession channel |
| `L!confession setlog #channel` | Administrator | Set admin log channel |
| `L!confession status` | Administrator | View setup and stats |
| `L!confession disable` | Administrator | Remove server config |

### Global Events Commands

| Command | Permission | Description |
|---|---|---|
| `L!event list` | Owner | Show active events |
| `L!event war [hours]` | Owner | Start faction war (default 24h) |
| `L!event worldboss [boss]` | Owner | Start world boss raid |
| `L!event hunt [minutes]` | Owner | Start target hunt (default 30m) |
| `L!event chaos [minutes]` | Owner | Start chaos festival (stub) |
| `L!event end <type>` | Owner | Manually end an event |
| `L!joinfaction <iron\|ash\|void\|sky>` | Any | Join WAR faction |
| `L!warleaderboard` | Any | View faction standings |
| `L!attack` | Any | Attack world boss (30s cooldown) |
| `L!bossstats` | Any | View boss HP and top servers |

---

## 8. Architecture Notes

### Starboard: Why Raw Reaction Events?

`on_reaction_add` / `on_reaction_remove` only fire for messages in the bot's **message cache** (approximately the last 1,000 messages per channel). For starboards to work on older messages that may have fallen out of cache, `on_raw_reaction_add` / `on_raw_reaction_remove` must be used — these fire for *every* reaction event regardless of cache state.

### Counting: Why `message_numbers` Cache?

`on_message_delete` does not provide message content — it only gives the message ID. The `message_numbers` dict caches `{message_id: {number, user_id}}` in memory so the delete listener can identify what number was deleted and announce it.

**Caveat:** This cache is in-memory only. If the bot restarts, `message_numbers` is cleared. Old counting messages deleted after a restart will not trigger the anti-deletion message. This is an accepted trade-off (restart is rare; the feature is cosmetic).

### GlobalEvents: In-Memory vs Persisted State

The `active_events` dict is the single source of truth during runtime. Only `events_data` (historical) is flushed to `global_events.json`. This means:
- Events survive normal operation correctly
- Bot restart during an event loses the event state
- A future improvement would be to load `active_events` from JSON on startup

### Confessions: Privacy Architecture

The "delete then post" order is by design:
1. Delete original → removes visible author attribution
2. Post anon embed → visible to everyone
3. Post log embed → visible only to admins

This ordering ensures there is no race window where both the attributed original and the anonymous version exist simultaneously.

---

*Last updated: 2026*  
*Part of the Ludus Bot Documentation Series — Part 10 of 15*  
*Previous: [Part 9 — Social Features](FULL_DOCUMENTATION_PART9.md)*  
*Next: Part 11 — Utility Commands (planned)*
