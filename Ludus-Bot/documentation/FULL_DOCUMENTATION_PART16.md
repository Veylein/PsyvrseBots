# 🤖 PART 16: Bot Intelligence & Personality System

> **Cogs covered:** `cogs/personality.py` (1,504 lines) · `cogs/intelligence.py.disabled` (182 lines)
> **~8,000 words of documentation**

---

## Table of Contents

1. [Overview](#overview)
2. [LudusPersonality Cog — personality.py](#luduspersonality-cog)
   - [Class Structure & Init](#class-structure--init)
   - [Content Safety System](#content-safety-system)
   - [Personality Profiles](#personality-profiles)
   - [Custom Emoji Map](#custom-emoji-map)
   - [Knowledge Base (Q&A Learning)](#knowledge-base-qa-learning)
   - [Event Listeners — on_message pipeline](#event-listeners--on_message-pipeline)
   - [Smart Detection Helpers](#smart-detection-helpers)
   - [Commands](#commands)
   - [Rare Event System](#rare-event-system)
   - [Server Configuration](#server-configuration)
3. [Intelligence Cog — intelligence.py.disabled](#intelligence-cog)
   - [Why Disabled?](#why-disabled)
   - [Features & Architecture](#features--architecture)
   - [Knowledge Structure (knowledge.json)](#knowledge-structure-knowledgejson)
   - [Multilingual Support](#multilingual-support)
   - [Self-Teaching Mechanism](#self-teaching-mechanism)
4. [Shared Data: knowledge.json](#shared-data-knowledgejson)
5. [Inter-Cog Integration](#inter-cog-integration)
6. [Missing / Undocumented Cogs Audit](#missing--undocumented-cogs-audit)

---

## Overview

The **Bot Intelligence & Personality System** provides Ludus with a living, reactive personality. It is responsible for:

- **Trigger-based chat reactions** — Ludus reads messages and reacts/responds to specific keywords with personality-appropriate text and emojis.
- **Per-server personality modes** — Admins pick from 5 distinct personalities (default, snappy, jester, fps, peaceful).
- **AI-like Q&A with learning** — Ludus answers questions from a structured `knowledge.json` file and can learn new facts from users in real time.
- **Content safety filtering** — A 3-tier moderation layer (hate/sexual/harassment) applied to every bot response.
- **Math solving** — Inline arithmetic detection and evaluation via the AST-safe evaluator.
- **Wordle answer fetching** — Live NYT Wordle answer via API.
- **Rare random events** — 1% chance trigger on any command, granting coin/XP bonuses.

---

## LudusPersonality Cog

**File:** `cogs/personality.py`  
**Class:** `LudusPersonality(commands.Cog)`  
**Lines:** 1,504  
**Registered via:** `setup(bot)` → `bot.add_cog(LudusPersonality(bot))`

---

### Class Structure & Init

```python
class LudusPersonality(commands.Cog):
    HATE_WORDS    = [...]   # ~30 entries
    SEXUAL_WORDS  = [...]   # ~25 entries
    HARASS_WORDS  = [...]   # ~30 entries
```

The cog is primarily initialized in `__init__`, which sets up:

| Attribute | Type | Purpose |
|-----------|------|---------|
| `last_reaction_time` | `dict[int, float]` | Per-user cooldown timestamps |
| `cooldown_seconds` | `int (5)` | Seconds between reactions per user |
| `ludus_emojis` | `dict[str, str]` | Name → Discord emoji string map |
| `personalities` | `dict[str, dict]` | 5 personality profiles (see below) |
| `server_personality` | `dict[int, str]` | In-memory guild_id → personality cache |
| `rare_events` | `list[dict]` | 5 possible rare event definitions |
| `user_personalities` | `dict` | Reserved for per-user tracking (not yet used) |
| `knowledge_path` | `str` | Path to `knowledge.json` |
| `knowledge_lock` | `asyncio.Lock` | Async lock for concurrent writes |
| `knowledge_mtime` | `float\|None` | mtime of loaded knowledge file for hot-reload |
| `knowledge_data` | `dict` | In-memory knowledge store |

---

### Content Safety System

All bot responses pass through `_safe_response(text, user_message=None)` before being sent. This normalizes both the generated response **and** the original user message through `normalize()`, then pattern-matches against three word lists.

#### `normalize(text)` — leet-speak decoding

Converts common character substitutions before checking forbidden words:

| Input char | Normalized to |
|-----------|---------------|
| `0` | `o` |
| `1` | `i` |
| `!` | `i` |
| `@` | `a` |
| `$` | `s` |
| `*` | *(removed)* |
| `5` | `s` |
| `3` | `e` |
| `4` | `a` |
| `7` | `t` |
| `8` | `b` |
| `9` | `g` |

#### `_is_bad_word(word, text)` — safe-context aware

Uses regex word-boundary matching (`\b`) to detect forbidden words. Before matching, it checks a whitelist of `safe_contexts` (60+ entries: `"assistant"`, `"classic"`, `"massachusetts"`, etc.) that contain the word as a fragment but are legitimate.

#### Response tiers

| Match type | Response |
|-----------|---------|
| `HATE_WORDS` | `"I can't respond to that."` |
| `SEXUAL_WORDS` | `"I'm not comfortable answering that."` |
| `HARASS_WORDS` | Random from 4 gentle deflections (e.g. `"Try being a little kinder!"`) |
| Clean | Return text unchanged |

---

### Personality Profiles

Five named profiles. Each profile defines a `triggers` dict: `keyword → {emoji, responses[]}`.

| Key | Name | Description |
|-----|------|-------------|
| `default` | Classic Ludus | Friendly, hype, supportive |
| `snappy` | Snappy | Deadpan, sarcastic, still loveable |
| `jester` | Jester | Pun-heavy, jokes, comedy first |
| `fps` | FPS Shooter | Military/shooter game slang |
| `peaceful` | Peaceful Gamer | Lofi, cozy games, Minecraft vibes |

#### Default personality trigger summary

The `default` profile has **30+ triggers**, grouped by theme:

| Theme | Triggers |
|-------|---------|
| Victory | `gg`, `win`, `victory`, `pog`, `nice`, `amazing`, `awesome` |
| Greetings | `hello`, `hey`, `sup` |
| Gratitude | `thanks`, `thank`, `love`, `cute` |
| Comfort | `coffee`, `read`, `music`, `sleep`, `fire`, `hug`, `think`, `party` |
| Failure | `oof`, `rip`, `nooo`, `lose`, `lost`, `fail` |
| Attitude | `bruh`, `wtf`, `why` |
| Tired | `tired`, `sleepy`, `sleep` |
| Calm | `chill`, `relax`, `calm` |
| Devotion | `pray`, `hope`, `luck` |
| Gaming | `grind`, `op`, `nerf`, `buff`, `ludus`, `bot` |
| Easter egg | `mushroom`, `shroom` |

All other profiles share the same top-level triggers (`gg`, `win`, `lose`, `love`, `bruh`, `chill`) but with personality-specific response text.

#### Trigger resolution logic (in `_on_message_inner`)

```
for trigger in triggers:
    if trigger in message.content.lower():
        if random.random() > 0.5:   # 50% skip for natural feel
            continue
        emoji = ludus_emojis[data.emoji]
        response = random.choice(data.responses).format(emoji=emoji)
        if random.random() > 0.7:   # 30% react, 70% send text
            await message.add_reaction(emoji)
        else:
            await message.channel.send(response)
        break
```

---

### Custom Emoji Map

24 entries mapping short names to Discord custom emoji strings or Unicode:

| Key | Emoji |
|-----|-------|
| `sob` | `<:LudusSob:1439151045862232194>` |
| `chill` | `<:LudusChill:1439150847639425034>` |
| `annoyed` | `<:LudusAnnoyed:1439150791314374708>` |
| `blush` | `<:LudusBlush:1439150829348061194>` |
| `cloud` | `<:LudusCloud:1439150889729261579>` |
| `control` | `<:LudusControl:1439150906175127582>` |
| `eepy` | `<:LudusEepy:1439150733365612666>` |
| `enemy` | `<:LudusEnemy:1439150929923408043>` |
| `happy` | `<:LudusHappy:1439150960164208660>` |
| `heart` | `<:LudusHeart:1443154289974575215>` |
| `key` | `<:LudusKey:1439151178985246720>` |
| `love` | `<:LudusLove:1439151016162365460>` |
| `pray` | `<:LudusPray:1439150751665492108>` |
| `shroom` | `<:LudusShroom:1439151033480777779>` |
| `star` | `<:LudusStar:1439151089093185576>` |
| `trophy` | `<:LudusTrophy:1439151104137891900>` |
| `unamused` | `<:LudusUnamused:1439150773283061762>` |
| `game` | `<:GameLudus:1439151118503645204>` |
| `wave` | `👋` |
| `think` | `🤔` |
| `party` | `🥳` |
| `coffee` | `☕` |
| `book` | `📚` |
| `music` | `🎵` |
| `sleep` | `😴` |
| `fire` | `🔥` |
| `question` | `❓` |
| `hug` | `🤗` |

> **Note:** These custom emojis require Ludus to be a member of the emoji-hosting server(s) defined in `config.json` under `emojiServerId`.

---

### Knowledge Base (Q&A Learning)

The knowledge base stores and retrieves answers from `knowledge.json` using a 5-tier lookup chain.

#### Data structure expected in `knowledge.json`

```json
{
  "identity": {
    "name": "...",
    "favorites": {
      "color": "...",
      "game": "..."
    }
  },
  "faq": {
    "how do i earn coins": "Play games and use daily rewards!",
    ...
  },
  "general_knowledge": {
    "capital of france": "Paris"
  },
  "user_taught": {
    "what is a creeper": {
      "question": "what is a creeper?",
      "answer": "An exploding mob from Minecraft!",
      "taught_by": null,
      "taught_at": "2026-03-01T12:00:00"
    }
  },
  "conversations": {}
}
```

#### `_get_known_answer(question_text)` — lookup chain

1. **Favorites** — regex-match `"what is your favorite <X>"` → check `identity.favorites[X]`
2. **User-taught** — exact + normalized + partial + fuzzy match against `user_taught`
3. **FAQ** — same matching against `faq`
4. **Identity** — substring match against `identity` keys
5. **General knowledge** — same matching against `general_knowledge` (also merges legacy flat `"knowledge"` key)

Fuzzy matching uses `difflib.get_close_matches` with cutoff `0.78`.

#### `_handle_learning_question(message, question_text)`

If no answer found in the knowledge base, Ludus initiates a **learning conversation**:

```
Ludus:  "I don't know that yet. Can you tell me the answer? Reply within 60 seconds!"
User:   "<answer>"
Ludus:  "Thanks! I'll remember that for next time."
```

The answer is stored in `user_taught` via `_store_learned_answer()` using `asyncio.Lock` to prevent race conditions. `taught_by` is always stored as `null` for privacy.

#### Hot-reload

`_refresh_knowledge_if_needed()` compares the current file mtime to `knowledge_mtime`; reloads from disk if changed externally.

---

### Event Listeners — on_message pipeline

The main pipeline runs inside `_on_message_inner()`, called by `on_message` (which wraps it in a `try/except discord.Forbidden`).

```
on_message(message)
│
├── Ignore bots / valid commands
├── Load server config (personality type, allowed channels)
├── Check personality_reactions toggle
├── Channel restriction check
├── Cooldown check (5s per user)
│
├── "How are you Ludus?" patterns → status-aware reply
├── Wordle question detection → fetch NYT API
├── Math question detection → AST-safe eval
│
├── _extract_question_text() → determine trigger_strength
│   ├── "high"   = @mention or "Hey Ludus"
│   ├── "medium" = "Ludus" at start, or DM
│   └── "low"    = "ludus" anywhere in message
│
├── Knowledge base lookup (if trigger_strength ≥ medium and not choice question)
│   └── _handle_learning_question() → answer or learn
│
├── Yes/No/"X or Y" question detection
│   └── _answer_yesno_or() → consistent hash-based answer
│
└── Trigger-based personality response
    └── 50% skip chance per trigger, 30% react vs 70% send
```

#### "How are you?" — status-aware responses

Ludus reads the guild's bot status and replies accordingly:

| Status | Sample replies |
|--------|---------------|
| `online` | `"I am fantastic"`, `"I could be better"` |
| `idle` | `"Tired"`, `"I am just sleepy"` |
| `dnd` / `do not disturb` | `"Annoyed"`, `"I have given up"` |

---

### Smart Detection Helpers

#### `_is_math_question(content)`

Detects phrases like `"what is 5 + 3"`, `"calculate 100 / 4"`, numeric expressions with `+`, `-`, `*`, `/`, `^`, `%`, and natural language keywords (`plus`, `minus`, `times`, `divided by`, `modulo`, `power`).

#### `_solve_math(content)` — AST-safe evaluator

Translates natural language operators to Python symbols, strips everything except `[0-9+\-*/.%()eE]`, parses with `ast.parse(mode='eval')`, and evaluates only through an allowed-operators whitelist (`Add`, `Sub`, `Mult`, `Div`, `Pow`, `Mod`, `USub`, `UAdd`). Never uses `eval()` directly.

Special output for results `42`, `69`, `0`, `abs > 1e12`, `abs < 1e-6`.

#### `_is_wordle_question(content)` + `_get_todays_wordle()`

Detects any mention of "wordle" combined with: `answer`, `solution`, `word`, `today`.  
Fetches from `https://www.nytimes.com/svc/wordle/v2/{YYYY-MM-DD}.json` via `aiohttp`.

#### `_is_yesno_or_question(content, addressed)` + `_answer_yesno_or()`

Detects yes/no questions via regex patterns (`do you...?`, `are you...?`, `will...?`, etc.) and "or" questions (only when `addressed=True` to avoid false positives).

`_answer_yesno_or()` uses `abs(hash(f"{user_id}-{personality}-{content}")) % len(options)` for **deterministic, consistent answers** — the same question from the same user always gets the same answer.

#### `_extract_question_text(message)`

Returns `(question_text, trigger_strength)` by stripping bot mentions and trigger phrases:
- Removes `@mention`, `"Hey Ludus"`, `"Ludus"` prefix
- Checks if remaining content `_looks_like_question()` (contains `?` or starts with question word ≥ 6 chars)
- Returns trigger strength: `"high"`, `"medium"`, `"low"`, or `"none"`

---

### Commands

#### Slash command: `/personality`

**Permission required:** Server administrator

| Parameter | Type | Description |
|-----------|------|-------------|
| `personality` | `str \| None` | Personality key or `"help"` for list |
| `channels` | `str \| None` | Space-separated `#channel` mentions or IDs |

If `personality` is omitted or `"help"`, shows the list of available personalities (ephemeral).  
If valid key provided, saves to `server_configs.json` and updates in-memory `server_personality` cache.  
`channels` restricts personality responses to specific channels.

---

#### Prefix command: `L!setpersonalitychannels`

**Permission required:** `administrator`  
**Usage:** `L!setpersonalitychannels #general #games`

Sets the list of channels where personality responses are allowed. Passing no channels effectively clears the restriction. Saved to `server_configs.json` under `personality_channels`.

---

#### Prefix command: `L!personality`

**No permission required**  
**Usage:** `L!personality`

Displays an embed listing all trigger word categories with examples:
- 😊 Positive Vibes (`gg`, `win`, `nice`, `love`, `amazing`, `awesome`)
- 😢 Tough Times (`oof`, `rip`, `lose`, `bruh`, `wtf`)
- 😴 Sleepy Mode (`tired`, `sleepy`, `sleep`)
- 😎 Chill Vibes (`chill`, `relax`, `calm`)
- 🎮 Gaming Talk (`grind`, `op`, `nerf`, `buff`)
- ✨ Secret Words (`mushroom`, `shroom`, `ludus`, `pray`)

---

#### Prefix command: `L!vibe` *(hidden)*

**Usage:** `L!vibe`

Sends a random current-mood message from 7 options using Ludus custom emojis:
- Feeling **hyped**, **chill**, **sleepy**, **loving**, **grumpy**, **vibing**, or **Zen mode**

---

#### Prefix command: `L!easter` (aliases: `L!secrets`, `L!hidden`)

**Usage:** `L!easter`

Reveals an embed documenting all hidden Easter eggs:
- Rare events (1% chance per command) with rewards
- Mushroom Hunt easter egg
- Ludus Love friendship mechanic
- Hidden commands (`L!vibe`, `L!personality`)
- Mystery Box in inventory
- Secret achievements

---

#### Prefix command: `L!mood`

**Usage:** `L!mood`

Shows a "Ludus's Feelings" embed with a randomized friendship level:

| Interactions (simulated) | Level | Mood text |
|--------------------------|-------|-----------|
| 0–9 | New Friend | "Just getting to know you" |
| 10–29 | Good Friend | "You're pretty cool!" |
| 30–59 | Close Friend | "I really enjoy our time together!" |
| 60+ | Best Friend | "You're one of my favorites!" |

> **Note:** The interaction count is currently `random.randint(0, 100)` — friendship tracking is not yet persisted to disk.

---

### Rare Event System

Triggered by the `on_command` listener with a **1% probability** (`random.random() > 0.99`) on any bot command.

| Event | Emoji | Reward |
|-------|-------|--------|
| Lucky Day | `star` | +250 coins *(TODO: not yet integrated with economy)* |
| Mystical Shroom | `shroom` | +500 coins *(TODO)* |
| Ludus Blessing | `love` | 1.5× coins for 10 min *(TODO)* |
| Cosmic Key | `key` | +1000 coins + secret achievement *(TODO)* |
| Cloud Nine | `cloud` | Double XP next 5 games *(TODO)* |

> All rewards display via embed but actual coin/XP application is marked `# TODO` — the economy integration is not yet implemented.

---

### Server Configuration

Read/written via `server_configs.json` (shared with other cogs).  
Relevant keys under each guild ID:

```json
{
  "GUILD_ID": {
    "personality_reactions": true,
    "personality_channels": ["CHANNEL_ID_1", "CHANNEL_ID_2"],
    "personality_type": "default"
  }
}
```

| Key | Default | Purpose |
|-----|---------|---------|
| `personality_reactions` | `true` | Master toggle for all personality responses |
| `personality_channels` | `[]` | Channel whitelist (empty = all channels) |
| `personality_type` | `"default"` | Active personality profile key |

---

## Intelligence Cog

**File:** `cogs/intelligence.py.disabled`  
**Class:** `Intelligence(commands.Cog)`  
**Lines:** 182  
**Status:** ⚠️ DISABLED — file extension `.disabled` prevents loading by `bot.py`

---

### Why Disabled?

The `Intelligence` cog was the **first version** of Ludus's conversational AI. It was replaced by the much more advanced `LudusPersonality` cog (`personality.py`). The file is retained for reference but is no longer loaded.

Key reasons it was superseded:
- Flat single-level knowledge structure vs the hierarchical 5-category structure in `personality.py`
- Synchronous `googletrans` + `fuzzywuzzy` dependencies vs the async-safe implementation in `personality.py`
- No content safety filtering
- No personality modes or custom emoji support
- No math/Wordle detection

---

### Features & Architecture

```python
class Intelligence(commands.Cog):
    def __init__(self, bot):
        self.knowledge_file = "knowledge.json"
        self.knowledge = {}
        self.load_knowledge()
        self.translator = Translator()   # googletrans
```

#### Dependencies

| Package | Use |
|---------|-----|
| `fuzzywuzzy` | Fuzzy question matching via `process.extractOne()` |
| `googletrans` | Language detection and translation |

These are still listed in `requirements.txt` because `personality.py` originally shipped alongside this cog.

---

### Knowledge Structure (knowledge.json)

The `Intelligence` cog used a flat, 3-key structure:

```json
{
  "greetings": ["hello", "hi", "hey", "yo", "sup"],
  "farewells": ["bye", "goodbye", "see you", "later"],
  "knowledge": {
    "what is your name": "My name is Ludus.",
    "who are you": "I am Ludus, a Discord bot.",
    "what are you": "I am a bot on Discord.",
    "how to use the bot": "...",
    "how to get currency": "...",
    "what are psycoins": "...",
    "what is ludus": "...",
    "who created you": "I was created by Psyvrse Development."
  }
}
```

This was replaced by the 5-key hierarchical format used by `personality.py` (`identity`, `faq`, `general_knowledge`, `user_taught`, `conversations`).

---

### Multilingual Support

`Intelligence` had full multi-language support via `googletrans`:

1. Detect source language of incoming message
2. Translate to English for knowledge base lookup
3. Respond in the user's original language by translating the answer back

`LudusPersonality` does **not** implement this — it operates in English only.

---

### Self-Teaching Mechanism

When a question was asked that scored below 80% fuzzy match, the bot replied:

```
"I don't have an answer for that. Would you like to teach me?
If so, please tell me the answer!"
```

Simple inline statement learning was also supported: `"X is Y"` → automatically stored `X → Y`.

`LudusPersonality` has a similar but more robust system (see [Handle Learning Question](#_handle_learning_questionmessage-question_text)).

---

## Shared Data: knowledge.json

**File:** `knowledge.json` (project root)  
**Used by:** Both `LudusPersonality` (active) and `Intelligence` (disabled)

The active format used by `LudusPersonality`:

```json
{
  "identity": {
    "name": "Ludus",
    "creator": "Psyvrse Development",
    "favorites": {
      "color": "purple",
      "game": "Minecraft"
    }
  },
  "faq": { },
  "general_knowledge": { },
  "user_taught": {
    "normalized question key": {
      "question": "original question text",
      "answer": "answer text",
      "taught_by": null,
      "taught_at": "ISO8601 timestamp"
    }
  },
  "conversations": { }
}
```

> `taught_by` is always `null` — user IDs are **never stored** for privacy.

---

## Inter-Cog Integration

### Called by `bot.py`

```python
# In bot.py on_message:
personality_cog = bot.get_cog("LudusPersonality")
if personality_cog:
    await personality_cog.on_message(message)
```

`bot.py` explicitly forwards every message to `LudusPersonality.on_message` after normal command processing.

### Reads from `server_configs.json`

Shared with `server_config.py`, `confessions.py`, `starboard.py`, and other server-management cogs. Personality only reads/writes its own keys (`personality_reactions`, `personality_channels`, `personality_type`).

### Economy integration (pending)

The rare event system has `# TODO` markers for calling the economy cog:
```python
# TODO: Add coins to user (integrate with economy system)
```
The `economy.py` cog API (`add_coins`, `get_balance`) exists but the personality cog does not yet call it.

---

## Missing / Undocumented Cogs Audit

After a full cross-check of all files in `cogs/` against Parts 1–15 + Utils Reference, the following cogs have **no dedicated documentation section** (only listed in file-tree outline):

| Cog file | Lines | Category | Status |
|----------|-------|----------|--------|
| `personality.py` | 1,504 | Bot AI | ✅ Documented here (Part 16) |
| `intelligence.py.disabled` | 182 | Bot AI (legacy) | ✅ Documented here (Part 16) |
| `simulations.py` | ~600 | Minigames | ⚠️ Only 2 passing references in Part 13 |
| `onboarding.py` | ~300 | Server Mgmt | ⚠️ Only mentioned as first_time_users.json source |
| `perimeter_explicit.py` | ~300 | Moderation | ❌ Not documented at all |
| `professional_info.py` | ~300 | Unknown | ❌ Not documented at all |

### Recommended follow-up

- **Part 17** (or expand Part 10): `perimeter_explicit.py`, `onboarding.py` — both are server management tools
- **Part 7 addendum**: `simulations.py` — belongs with minigames/arcade
- **Part 11 or standalone**: `professional_info.py` — needs code review to determine category

Additionally, the file-tree in `DOCUMENTATION_INDEX.md` contains several **inaccuracies** worth noting:

| Issue | Detail |
|-------|--------|
| `personality.py` described as "Personality quiz" | Incorrect — it is the full bot personality/AI system (1,504 lines, not 300) |
| `intelligence.py.disabled` not listed | Missing from the file tree overview entirely |
| `zoo.py` listed in file tree | Does not exist in the actual `cogs/` directory |
| `command_groups.py` listed | Does not exist in the actual `cogs/` directory |
| `uno_gofish.py` listed | Does not exist; UNO is handled by the `uno/` subdirectory |
| `akinator_enhanced.py` listed | Does not exist; only `akinator.py` exists |

---

*End of Part 16 — Bot Intelligence & Personality System*
