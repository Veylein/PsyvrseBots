# ⚔️ PART 8: RPG Systems

> **Documentation for:** `cogs/dnd/dnd.py`, `cogs/dnd/dnd_gate1_fantasy.py`, `cogs/wizardwars.py`, `cogs/quests.py`  
> **Total Lines:** ~13,400 | **Files:** 4 | **Date:** March 2026

---

## 📋 TABLE OF CONTENTS

1. [Overview & File Summary](#1-overview--file-summary)
2. [Infinity Adventure — dnd.py (2,229 lines)](#2-infinity-adventure--cogsdnddndpy-2229-lines)
3. [Gate 1: Fantasy Dimension — dnd_gate1_fantasy.py (9,902 lines)](#3-gate-1-fantasy-dimension--cogsdnddnd_gate1_fantasypy-9902-lines)
4. [Wizard Wars — wizardwars.py (855 lines)](#4-wizard-wars--cogswizardwarspy-855-lines)
5. [Quests & Achievements — quests.py (~400 lines)](#5-quests--achievements--cogsquestspy-400-lines)
6. [Cross-Cog Integration Map](#6-cross-cog-integration-map)
7. [Commands Reference](#7-commands-reference)
8. [Part 8 Summary](#8-part-8-summary)

---

## 1. Overview & File Summary

Part 8 covers the three RPG pillars of Ludus Bot: a massive interdimensional narrative adventure, a spell-based wizard dueling system, and a quest/achievement tracker.

| File | Lines | Role |
|------|-------|------|
| `cogs/dnd/dnd.py` | 2,229 | Core Infinity Adventure engine: state machine, translations, data classes, 9 gates, party system |
| `cogs/dnd/dnd_gate1_fantasy.py` | **9,902** | Gate 1 scene database: 50+ branching fantasy scenes, world state flags, faction system |
| `cogs/wizardwars.py` | 855 | Wizard Wars RPG: 32 spells, 4 schools, duels, territories, guild system skeleton, interactive shop |
| `cogs/quests.py` | ~400 | Daily quests + 10 achievements, 24h reset loop, TCG card rewards, progress bars |
| **TOTAL** | **~13,386** | |

**Data files used:**

| File | Purpose |
|------|---------|
| `data/saves/infinity_adventure.json` | All Infinity Adventure player saves |
| `wizard_wars_data.json` | Wizard profiles, guilds, territory control |
| `data/quests_data.json` | Active quests, progress, completion history |
| `data/achievements_data.json` | Unlocked achievements per user |

---

## 2. Infinity Adventure — `cogs/dnd/dnd.py` (2,229 lines)

### 2.1 Concept

**Infinity Adventure** (branded in-game as *"INFINITY ADVENTURE"* / *"NIESKOŃCZONA PRZYGODA"*) is the most ambitious system in Ludus Bot. The player is not a typical RPG hero — they are a **Bodiless Entity** standing at the **Cape of All Existence** (`Przylądek Wszechrzeczy`), a metaphysical hub between 9 parallel dimensions.

Core design principles:
- **Death is not the end** — the player always returns to the Cape. Past lives accumulate as a cosmic stat.
- **Permanent consequences** — world states persist across deaths. Killing the king stays done.
- **Identity fluidity** — each visit to a gate creates a new character (name, class). The entity is immortal; mortals are temporary vessels.
- **Bilingual** — full EN/PL translation via the `t()` helper, covering 80+ UI strings.
- **Party mode** — multiple Discord users can join a session, each creating their own character, with a turn-based action system.

---

### 2.2 Translation System

The entire UI is bilingual. All user-facing strings live in the `TRANSLATIONS` dict at the top of the file:

```python
TRANSLATIONS = {
    "en": {
        "cape_title": "🌌 CAPE OF ALL EXISTENCE",
        "gate_1": "Sword & Blood",
        "gate_1_short": "Fantasy realm of heroes, dragons, and destiny",
        "stat_health": "❤️ Health",
        # ... 80+ keys
    },
    "pl": {
        "cape_title": "🌌 PRZYLĄDEK WSZECHRZECZY",
        "gate_1": "Miecz i Krew",
        # ... same keys in Polish
    }
}

def t(lang: str, key: str, **kwargs) -> str:
    """Get translation with optional .format() substitution"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
```

Usage example: `t(lang, "death_text", name=character.name)` — inserts the character's name into the death message.

---

### 2.3 Data Classes

#### `PlayerData` (line 342)

Stores all persistent player information. Survives across game sessions.

```python
class PlayerData:
    user_id: int
    language: str               # "en" or "pl"
    tutorial_completed: bool

    # Cosmic stats (persist across ALL deaths)
    cosmic_influence: int       # Grows with world impact
    total_deaths: int
    worlds_changed: int
    dimensions_visited: set     # Which gates were visited

    # Current life
    current_gate: Optional[int]           # 1-9 or None (= at Cape)
    character: Optional[CurrentCharacter]  # Active body
    current_scene: Optional[str]          # Scene ID currently at

    # Persistent world memory
    dimension_states: dict      # {1: {}, 2: {}, ..., 9: {}} — Gate1WorldState etc.
    last_entry_points: dict     # {gate_id: entry_point_id}

    # Narrative tracking
    story_history: list         # Scene IDs visited
    choices_made: list          # Major choices
    npc_relationships: dict     # {npc_id: relationship_value}
    npc_memories: dict          # {npc_id: [memory_ids]}

    # Transcendental items (survive death)
    artefacts: list
    inventory: dict

    # Party
    party_adventures: int       # How many party adventures completed
```

Serialised to `data/saves/infinity_adventure.json` via `to_dict()` / `from_dict()`.

#### `CurrentCharacter` (line 450)

Represents the player's current physical incarnation within a specific gate.

```python
class CurrentCharacter:
    name: str         # Entered via modal
    char_class: str   # Selected from gate-specific class list
    gate: int         # Which dimension this body exists in

    # Combat
    max_health: int = 100
    health: int = 100
    max_mana: int = 50
    mana: int = 50
    max_stamina: int = 100
    stamina: int = 100

    # D&D-style attributes
    strength: int = 10
    intelligence: int = 10
    charisma: int = 10
    luck: int = 10

    level: int = 1
    experience: int = 0
    conditions: list  # ["bleeding", "blessed", "cursed", ...]
```

`get_stats_display(lang)` renders a progress-bar stat block using `_make_bar()` (blocks: `█` / `░`).

---

### 2.4 Save / Load System

```python
SAVE_FILE = "./data/saves/infinity_adventure.json"

def save_player(player: PlayerData) -> bool:
    # Loads existing dict → updates player's key → writes back
    # Uses ensure_save_dir() to create directory on first run

def load_player(user_id: int) -> Optional[PlayerData]:
    # Reads file → returns PlayerData.from_dict()
    # Returns None if no save exists
```

All saves are in one file keyed by `str(user_id)`.

---

### 2.5 Gate Configurations

9 dimensions are defined in `GATE_CONFIGS` (line ~580). Each entry:

```python
{
    "name_key": "gate_1",          # Translation key
    "desc_key": "gate_1_short",
    "emoji": "⚔️",
    "ruler": "IGNAR",              # Lore name of the dimension's ruler
    "theme": "fantasy",
    "color": 0xC41E3A,             # Discord embed color
    "classes": {
        "en": ["Warrior", "Mage", "Rogue", "Cleric", "Ranger", "Paladin"],
        "pl": ["Wojownik", "Mag", "Łotrzyk", "Kleryk", "Łowca", "Paladyn"]
    }
}
```

Full gate list:

| Gate | Theme | Ruler | Emoji | EN Classes |
|------|-------|-------|-------|-----------|
| 1 — Sword & Blood | Fantasy | IGNAR | ⚔️ | Warrior, Mage, Rogue, Cleric, Ranger, Paladin |
| 2 — Steam & Gears | Steampunk | AETRION | ⚙️ | Inventor, Engineer, Airship Captain, Alchemist, Mechanist |
| 3 — Ash & War | Dieselpunk War | NIHARA | ☠️ | Soldier, Medic, Sniper, Saboteur, Commander |
| 4 — Neon & Steel | Cyberpunk | PSYCHON | 🌃 | Netrunner, Street Samurai, Corpo, Fixer, Techie |
| 5 — Silence & Ruin | Post-Apocalypse | MORTIS | 🏚️ | Scavenger, Survivor, Raider, Medic, Trader |
| 6 — Stardust & Void | Sci-Fi | ORIGEN | ✨ | Explorer, Scientist, Pilot, Xenobiologist, AI Specialist |
| 7 — Empire & Throne | Space Opera | FINIS | 👑 | Imperial Officer, Rebel Leader, Diplomat, Admiral, Spy |
| 8 — Dream & Myth | Surreal | VITA | 🎭 | Dreamer, Reality Bender, Artist, Shapeshifter, Oracle |
| 9 — Abyss & Truth | Cosmic Horror | VOIDREX | 🌀 | Cultist, Investigator, Touched One, Witness, Void Walker |

Gate 9 has `"unstable": True` — can be closed by the Four Guardians.

---

### 2.6 InfinityView State Machine (line 708)

`InfinityView` extends `discord.ui.LayoutView` (Components V2). It is the entire UI controller for an active game session.

**States:**

```
language_select → mode_select → tutorial → cape → character_creation → story
                                                ↑                           |
                                                └─────────── (death) ───────┘
```

| State | Description |
|-------|-------------|
| `language_select` | EN / PL button choice. Always first on `/dnd` call. |
| `mode_select` | Solo vs Party selection screen |
| `party_gathering` | Join-party lobby. Leader + other players can join, then leader starts |
| `tutorial` | Lore intro with "I'm Ready" / "Explain More" buttons |
| `cape` | Cape of All Existence — gate selector dropdown, load save button |
| `character_creation` | Gate-specific class dropdown + `CharacterNameModal` |
| `story` | Active scene from `get_gate1_scene()` (or equivalent for other gates) |

`_determine_state()` (line 748) resolves which state to show based on `player.language`, `tutorial_completed`, `current_gate`, `character`, and `current_scene`.

`build_ui()` dispatches to `_build_<state>()` methods. `_refresh_ui(interaction)` calls `build_ui()` then edits the Discord message.

---

### 2.7 Party Mode

The party system allows multiple Discord users to share one `InfinityView` instance:

```python
self.party_mode = False
self.party_members = []        # [user_ids]
self.party_leader = None
self.party_characters = {}     # {user_id: CurrentCharacter}
self.party_players = {}        # {user_id: PlayerData}
self.party_adventures = 0

# Turn-based
self.current_actor = None      # user_id whose turn it is
self.turn_order = []
self.waiting_for_action = False
```

Flow:
1. Leader calls `/dnd` → selects Party mode → party gathering screen appears
2. Other users click **Join Party** in the Discord message
3. Leader clicks **Start Adventure**
4. Each player gets `character_creation` in sequence (turn-based: `t(lang, "party_turn", name=...)`)
5. In story scenes, a different player acts each turn

---

### 2.8 Character Name Modal (line 2163)

```python
class CharacterNameModal(discord.ui.Modal):
    # Text input: "Enter Name" / "Wpisz Imię"
    # On submit → sets character.name → proceeds to story
```

Used during `character_creation` state to enter a custom character name before entering the story.

---

### 2.9 InfinityAdventure Cog + `/dnd` Command (line 2189)

```python
class InfinityAdventure(commands.Cog):
    @app_commands.command(name="dnd", description="Begin your infinite journey across dimensions")
    async def dnd(self, interaction: discord.Interaction):
        player = load_player(interaction.user.id) or PlayerData(interaction.user.id)
        view = InfinityView(player, cog=self, is_new_session=True)
        await view.build_ui()
        await interaction.response.send_message(view=view, ephemeral=True)
```

Single command, all interaction from there is button/dropdown/modal driven.

---

## 3. Gate 1: Fantasy Dimension — `cogs/dnd/dnd_gate1_fantasy.py` (9,902 lines)

### 3.1 Overview

Gate 1 is **the only fully implemented gate** at this time. Its scene database at 9,902 lines is the single **largest file in the entire project**, nearly doubling the second-largest (`fishing.py` at 3,472 lines). It contains:

- 50+ individual story scenes
- Multiple entry points into the world
- A full faction/world-state simulation
- Branching decisions with permanent consequences
- Combat, diplomacy, and exploration scenes
- 20+ quest flags that permanently alter scene output

---

### 3.2 Gate1WorldState (line 11)

`Gate1WorldState` is the persistent memory of the fantasy dimension. Every decision the player makes is stored here and survives death.

**Kingdom factions (0–100 power each):**

```python
self.royal_guard_strength = 50
self.resistance_power = 30
self.demon_forces = 70
self.church_influence = 40
```

**Key NPC flags:**

```python
self.king_alive = None                  # None = decide randomly on first visit
self.knight_commander_alive = True
self.high_priestess_corrupted = False
self.rebellion_leader_known = False
self.ancient_dragon_awakened = False
```

**Capital status:** `"under_siege"` | `"safe"` | `"fallen"` | `"liberated"`  
**Rift activity:** `"dormant"` | `"active"` | `"unstable"` | `"sealed"`

**Quest flags (25 total):**

| Flag | Type | Purpose |
|------|------|---------|
| `kingdom_quest_started / _complete` | bool | Main story arc |
| `dragon_discovered / _pact_offered / _hostile` | bool | Dragon path |
| `rebellion_contacted / _allied / _destroyed` | bool | Rebel faction |
| `artifact_sword / _shield / _crown / _book / _heart _obtained` | bool | 5 legendary items |
| `dark_pact_accepted` | bool | Evil route unlock |
| `ghost_army_obtained` | bool | Undead army |
| `lightbringer_obtained` | bool | Holy sword |
| `varathul_defeated / zariel_defeated` | bool | Boss kills |
| `villages_saved / villages_destroyed` | int | Moral counter |
| `princess_dead / priests_killed` | bool | Morality trackers |
| `moral_alignment` | str | `"good"` / `"neutral"` / `"evil"` |

---

### 3.3 Entry Points

```python
GATE1_ENTRY_POINTS = [
    {"id": "ruins_outside_capital", "name": "Ruins Outside the Capital", ...},
    {"id": "village_tavern",        "name": "Village Tavern",            ...},
    {"id": "forest_trail",          "name": "Deep Forest Trail",         ...},
    # ... more entry points
]

def get_random_entry_point() -> dict:
    """Returns a random entry point dict"""
    return random.choice(GATE1_ENTRY_POINTS)
```

Entry points set the *where* of a new incarnation. The last used entry point is stored in `player.last_entry_points[1]`.

---

### 3.4 Scene Engine

```python
def get_gate1_scene(
    scene_id: str,
    lang: str,
    world_state: Gate1WorldState,
    player_data
) -> Optional[Dict]:
```

Returns a scene dict for the given `scene_id`, taking into account the current `world_state` and `player_data` to dynamically alter text and available choices.

**Scene dict structure:**

```python
{
    "id": "g1_main_001",
    "title": "The Ruined Gates",
    "description": "The capital city of Erandor lies before you...",
    "image": None,          # Optional image URL
    "choices": [
        {
            "id": "enter_city",
            "text": "Enter the city through the broken gate",
            "condition": None,        # Optional world_state condition
            "roll": None,             # Optional D20 roll requirement
            "consequences": {         # World state changes on choice
                "faction": "royal_guard",
                "delta": +5
            }
        },
        {
            "id": "observe_from_distance",
            "text": "Observe from the ridge",
            "condition": None,
            "roll": None
        }
    ],
    "roll_required": None,   # If set, D20 roll before choices
    "death_possible": False,
    "xp_reward": 10,
    "influence_reward": 1    # Adds to cosmic_influence
}
```

World-state-conditional text: Scene descriptions include if-blocks checking flags like `world_state.quest_flags["dark_pact_accepted"]` to show different paragraphs.

---

### 3.5 Scene Navigation Flow

```
Cape (gate select) 
    → character_creation (name + class modal)
        → get_random_entry_point()
            → get_gate1_scene("entry_scene_id", ...)
                → Player picks choice
                    → Consequences applied to Gate1WorldState
                        → get_gate1_scene(next_scene_id, ...)
                            → ... (branching tree)
                                → death scene → Cape
                                  (world_state persists)
```

---

### 3.6 File Scale

At **9,902 lines**, `dnd_gate1_fantasy.py` is a testament to the ambition of the project. For reference:

| File | Lines |
|------|-------|
| `cogs/dnd/dnd_gate1_fantasy.py` | **9,902** |
| `cogs/fishing.py` | 3,472 |
| `cogs/dnd/dnd.py` | 2,229 |
| `cogs/mining.py` | 4,053 |

Gates 2–9 are planned but not yet implemented in the codebase. Only Gate 1 has its full `dnd_gate1_fantasy.py` companion file.

---

## 4. Wizard Wars — `cogs/wizardwars.py` (855 lines)

### 4.1 Concept

Wizard Wars is a standalone spell-based strategy RPG. Players create a wizard, learn spells from a Gold-based economy (separate from PsyCoins), duel AI opponents, and eventually compete for territory control. The system is fully functional for solo AI duels; guild wars and territory capture are designed but marked "coming soon."

---

### 4.2 Module-Level Constants

```python
SCHOOL_EMOJIS = {
    "Elemental": "🌊",
    "Cosmic": "🌌",
    "Forbidden": "☠️",
    "Divine": "✨",
}

TYPE_EMOJIS = {
    "fire": "🔥", "water": "💧", "thunder": "⚡", "ice": "❄️",
    "wind": "🌀", "earth": "🌍", "gravity": "⚫", "space": "🌌",
    "time": "⏳", "blood": "🩸", "shadow": "🌑", "curse": "👁️",
    "light": "🌟", "holy": "✨",
}
```

---

### 4.3 Spell Database (32 spells)

Spells are grouped into 4 Schools. Each spell has:

```python
{
    "type":    str,   # element type (fire, water, thunder, ...)
    "power":   int,   # 3–10; drives both damage and Gold price (power × 100)
    "mana":    int,   # 30–100 mana cost per cast
    "effect":  str,   # gameplay tag (damage, shield, heal, debuff, ...)
    "school":  str    # Elemental / Cosmic / Forbidden / Divine
}
```

**Elemental School (14 spells):**

| Spell | Type | Power | Effect |
|-------|------|-------|--------|
| Flame Burst | fire | 3 | damage |
| Inferno Wave | fire | 7 | aoe_damage |
| Pyroblast | fire | 10 | massive_damage |
| Water Shield | water | 4 | shield |
| Tidal Surge | water | 6 | heal_damage |
| Aqua Fortress | water | 9 | massive_shield |
| Lightning Strike | thunder | 5 | chain_damage |
| Thunderstorm | thunder | 8 | multi_chain |
| Frost Nova | ice | 4 | freeze |
| Blizzard | ice | 8 | freeze_aoe |
| Gale Twist | wind | 3 | evasion |
| Hurricane | wind | 7 | knockback_aoe |
| Earth Wall | earth | 5 | barrier |
| Earthquake | earth | 9 | stun_aoe |

**Cosmic School (6 spells):**

| Spell | Type | Power | Effect |
|-------|------|-------|--------|
| Gravity Well | gravity | 6 | pull |
| Black Hole | gravity | 10 | crush_all |
| Spatial Rift | space | 5 | teleport |
| Dimension Shift | space | 8 | phase |
| Time Slow | time | 4 | slow |
| Temporal Rewind | time | 9 | undo_damage |

**Forbidden School (6 spells):**

| Spell | Type | Power | Effect |
|-------|------|-------|--------|
| Blood Drain | blood | 5 | lifesteal |
| Hemorrhage | blood | 8 | massive_lifesteal |
| Shadow Veil | shadow | 4 | stealth |
| Void Embrace | shadow | 9 | immune |
| Curse of Weakness | curse | 3 | debuff |
| Doom | curse | 10 | execute |

**Divine School (6 spells):**

| Spell | Type | Power | Effect |
|-------|------|-------|--------|
| Holy Light | light | 4 | heal |
| Radiance | light | 7 | aoe_heal |
| Divine Smite | holy | 6 | pure_damage |
| Judgement | holy | 10 | ultimate |
| Blessing | holy | 3 | buff |
| Resurrection | holy | 9 | revive |

---

### 4.4 Spell Combos (6 combinations)

Casting two specific spells together creates a Combo — a more powerful combined effect:

```python
self.combos = {
    ("Flame Burst", "Gale Twist"):        {"name": "Inferno Cyclone",   "power": 12, "effect": "Massive fire tornado"},
    ("Frost Nova", "Lightning Strike"):   {"name": "Glacial Shock",     "power": 11, "effect": "Frozen lightning damage"},
    ("Shadow Veil", "Blood Drain"):       {"name": "Vampiric Shadow",   "power": 10, "effect": "Stealth lifesteal"},
    ("Water Shield", "Earth Wall"):       {"name": "Fortress Barrier",  "power": 13, "effect": "Impenetrable defense"},
    ("Gravity Well", "Black Hole"):       {"name": "Singularity",       "power": 15, "effect": "Ultimate void damage"},
    ("Holy Light", "Divine Smite"):       {"name": "Celestial Wrath",   "power": 12, "effect": "Holy devastation"},
}
```

`check_combo(spell1, spell2)` checks both orderings, so order doesn't matter.

---

### 4.5 Territory Map (12 territories)

```python
self.territories = [
    "Crystal Peaks", "Shadow Vale", "Ember Wastes", "Frost Tundra",
    "Storm Heights", "Verdant Grove", "Void Nexus", "Golden Shores",
    "Mystic Marshes", "Titan's Rest", "Eclipse Valley", "Arcane Citadel"
]
```

Territory control (`self.territory_control`) is a dict mapping territory name → controlling guild name (or `"Unclaimed"`).

---

### 4.6 Wizard Profile Schema

```python
wizard = {
    'name': str,            # Discord username at creation
    'level': int,           # Starts at 1
    'xp': int,              # 0 to (level × 100) then level up
    'mana': int,            # Current mana (max_mana)
    'max_mana': int,        # Starts 100, +20 per level
    'hp': int,
    'max_hp': int,          # Starts 100, +20 per level
    'gold': int,            # Starts 1000; SEPARATE from PsyCoins
    'spells': list,         # All learned spell names
    'guild': Optional[str],
    'wins': int,
    'losses': int,
    'territories': int,
    'rank': str,            # "Apprentice" at start
    'title': Optional[str],
    'equipped_spells': list, # Active spell loadout
    'spell_slots': int       # Starts at 3
}
```

Starting spells: `["Flame Burst", "Water Shield", "Lightning Strike"]`.

---

### 4.7 Core Methods

#### `create_wizard(user_id, username)` (line ~247)

Creates a fresh wizard with the default profile above, saves to `wizard_wars_data.json`, and returns the dict.

#### `calculate_damage(spell_name, attacker)` (line ~264)

```python
damage = spell['power'] * 10 + attacker['level'] * 2
```

Simple formula: Power scales linearly, level adds a bonus of 2 per level.

#### `check_combo(spell1, spell2)` (line ~269)

Checks `(spell1, spell2)` and `(spell2, spell1)` against `self.combos`. Returns the combo dict or `None`.

---

### 4.8 ShopView (line 32) — Interactive Spell Shop

```python
class ShopView(discord.ui.View):
    timeout = 120
```

The SpellShop uses a two-component design:

**Component 1 — Dropdown Select (row 0):**
- Shows up to 25 unowned spells
- Each option: `label=spell_name`, `description="Price Gold | School | Power: N"`, `emoji=TYPE_EMOJIS[type]`
- `spell_selected` callback edits the message embed with a full spell preview
- Footer shows: already owned / can afford / can't afford status

**Component 2 — Buy Button (row 1):**
- `label="💰 Buy Spell"`, `style=ButtonStyle.success`
- Custom ID: `ww_buy_btn`
- `buy_button` callback:
  1. Validates `selected_spell` is set
  2. Checks ownership
  3. Checks `wizard['gold'] >= price`
  4. Deducts gold, appends spell to `wizard['spells']`
  5. Calls `self.cog.save_data()`
  6. Creates a **new `ShopView`** with updated available spells
  7. Edits message with confirmation + refreshed shop embed

After a purchase, the shop refreshes itself showing remaining purchasable spells. If the user owns all 32 spells, a "🎉 Collection Complete!" field replaces the dropdown.

---

### 4.9 AI Duel System (line ~497)

`start_ai_duel(interaction, wizard, user_id)`:

**AI creation:**
```python
ai_level = max(1, wizard['level'] - 1 + random.randint(-1, 2))
ai_wizard = {
    'name': random.choice(['Malakar', 'Zephyra', 'Ignatius', 'Frostbane', 'Shadowmere', 'Lumina']),
    'hp': 100 + (ai_level * 10),
    'spells': random.sample(list(self.spells.keys()), min(5, len(self.spells)))
}
```

AI is approximately the same level as the player (±1 level variance).

**Combat loop (up to 20 turns):**

```
while wizard['hp'] > 0 and ai_wizard['hp'] > 0 and turn < 20:
    Player turn:
        → pick random spell from equipped_spells
        → if mana >= cost: cast (damage = calculate_damage()), else: +20 mana regen
    AI turn:
        → pick random spell from ai['spells']
        → same logic
```

**Victory rewards:**
```python
xp_reward  = 50 + (ai_level * 10)
gold_reward = 100 + (ai_level * 50)
wizard['xp'] += xp_reward
wizard['gold'] += gold_reward
wizard['wins'] += 1
```

**Level-up on win:**
```python
while wizard['xp'] >= wizard['level'] * 100:
    wizard['xp'] -= wizard['level'] * 100
    wizard['level'] += 1
    wizard['max_hp'] += 20
    wizard['max_mana'] += 20
```

**TCG Integration:** After a win, `tcg_manager.award_for_game_event(user_id, 'mythic')` awards a chance at a rare TCG card.

---

### 4.10 Commands

| Command | Shorthand | Action Parameter | Description |
|---------|-----------|-----------------|-------------|
| `/wizardwars action:create` | `/ww create` | create | Create a new wizard |
| `/wizardwars action:spellbook` | `/ww spellbook` | spellbook | View learned spells grouped by school |
| `/wizardwars action:upgrade` | `/ww upgrade` | upgrade | Upgrade spell power (UI skeleton) |
| `/wizardwars action:duel` | `/ww duel` | duel | Launch AI duel or PvP invite |
| `/wizardwars action:guild` | `/ww guild` | guild | Guild management panel |
| `/wizardwars action:territories` | `/ww territories` | territories | View 12-territory conquest map |
| `/wizardwars action:events` | `/ww events` | events | World events panel |
| `/wizardwars action:leaderboard` | `/ww leaderboard` | leaderboard | Top 10 wizards sorted by level+wins |
| `/wizardwars action:shop` | `/ww shop` | shop | Interactive spell shop (ShopView) |
| `/wizardwars action:profile` | `/ww profile` | profile | Wizard stats + combat record |

Both `/wizardwars` and `/ww` have identical `@app_commands.choices` definitions. `/ww` calls `.callback` directly on the `/wizardwars` handler.

---

### 4.11 Feature Status

| Feature | Status |
|---------|--------|
| Wizard creation | ✅ Fully working |
| Spellbook display | ✅ Fully working |
| AI Duel combat | ✅ Fully working |
| Spell Shop (interactive) | ✅ Fully working (ShopView) |
| Leaderboard | ✅ Fully working |
| Profile display | ✅ Fully working |
| Territory map | ✅ Display only (no capture mechanic) |
| World events | ✅ Display only (no active events) |
| Guild system | 🔧 UI skeleton — wars/raids coming |
| Spell upgrade | 🔧 UI stub only |
| PvP duels | 🔧 Button shown, logic coming |
| Spell combos | 🔧 Logic in `check_combo()`, not yet used in duel |

---

## 5. Quests & Achievements — `cogs/quests.py` (~400 lines)

### 5.1 Overview

`quests.py` provides two parallel systems:
1. **Daily Quests** — one random quest assigned per user per day, auto-reset at midnight
2. **Achievements** — 10 permanent milestones that unlock via gameplay across the entire bot

---

### 5.2 Daily Quest Database (5 quests)

```python
self.daily_quests = [
    {"id": "play_5_games",    "name": "Game Master",       "desc": "Play 5 different minigames",     "reward": 100, "target": 5},
    {"id": "social_butterfly","name": "Social Butterfly",  "desc": "Use 3 social commands",           "reward": 75,  "target": 3},
    {"id": "coin_collector",  "name": "Coin Collector",    "desc": "Earn 200 PsyCoins",              "reward": 150, "target": 200},
    {"id": "pet_caretaker",   "name": "Pet Caretaker",     "desc": "Interact with your pet 5 times", "reward": 80,  "target": 5},
    {"id": "win_streak",      "name": "Winning Streak",    "desc": "Win 3 games in a row",           "reward": 200, "target": 3},
]
```

A random quest from this list is assigned on first access and on each daily reset.

---

### 5.3 Achievement Database (10 achievements)

```python
self.all_achievements = {
    "first_win":      {"name": "🏆 First Victory",    "desc": "Win your first game",                  "reward": 50},
    "money_maker":    {"name": "💰 Money Maker",       "desc": "Earn 1000 total PsyCoins",             "reward": 100},
    "social_expert":  {"name": "🎭 Social Expert",     "desc": "Use 50 social commands",               "reward": 150},
    "game_master":    {"name": "🎮 Game Master",        "desc": "Play 100 total games",                 "reward": 200},
    "pet_lover":      {"name": "🐾 Pet Lover",          "desc": "Adopt and care for a pet for 7 days", "reward": 100},
    "quest_hunter":   {"name": "📜 Quest Hunter",       "desc": "Complete 10 quests",                   "reward": 250},
    "millionaire":    {"name": "💎 Millionaire",        "desc": "Accumulate 10,000 PsyCoins",           "reward": 500},
    "daily_devotee":  {"name": "🔥 Daily Devotee",      "desc": "Maintain a 7-day login streak",        "reward": 200},
    "board_game_pro": {"name": "♟️ Board Game Pro",     "desc": "Win 10 board games",                  "reward": 150},
    "card_shark":     {"name": "🃏 Card Shark",         "desc": "Win 10 card games",                    "reward": 150},
}
```

---

### 5.4 User Data Schemas

**Quest data** (`data/quests_data.json`):
```json
{
  "USER_ID": {
    "active_quests": [{"id": "coin_collector", "name": "Coin Collector", "desc": "...", "reward": 150, "target": 200}],
    "completed_today": 0,
    "total_completed": 7,
    "last_reset": "2026-03-04T00:00:00+00:00",
    "progress": {"coin_collector": 47}
  }
}
```

**Achievement data** (`data/achievements_data.json`):
```json
{
  "USER_ID": {
    "unlocked": ["first_win", "money_maker", "quest_hunter"],
    "progress": {}
  }
}
```

---

### 5.5 Core Methods

#### `get_user_quests(user_id)` (line ~158)

Auto-initialises a new user record if first visit. Assigns a random daily quest and initialises track structure. Returns the user's quest dict.

#### `update_quest_progress(user_id, quest_type, amount=1)` (line ~172)

Called by other cogs to report game events. Increments progress for any matching active quest. If the target is reached, calls `_complete_quest()`.

```python
# Example call from economy.py:
quests_cog = bot.get_cog("Quests")
if quests_cog:
    quests_cog.update_quest_progress(user.id, "coin_collector", amount_earned)
```

#### `_complete_quest(user_id, quest)` (line ~188)

1. Removes quest from `active_quests`
2. Increments `completed_today` and `total_completed`
3. Calls `economy_cog.add_coins(user_id, quest["reward"], "quest_completion")`
4. Optionally awards TCG card: `tcg_manager.award_for_game_event(user_id, 'mythic')`
5. Sends TCG award notification via DM
6. Checks for `quest_hunter` achievement (10 total completed)

#### `get_user_achievements(user_id)` / `unlock_achievement(user_id, achievement_id)` (line ~215)

`unlock_achievement`:
1. Checks user doesn't already have it
2. Appends to `user_data["unlocked"]`
3. Awards coins via economy cog
4. Optionally awards TCG card (same `award_for_game_event('mythic')` call)
5. Sends DM embed: `"🏆 Achievement Unlocked!"`

#### `_create_progress_bar(current, target, length=10)` (line ~289)

```python
bar = "█" * filled + "░" * (length - filled)
return f"[{bar}]"
```

Used in `L!quests` display to show visual progress for each active quest.

---

### 5.6 Daily Reset Loop

```python
@tasks.loop(hours=24)
async def check_daily_reset(self):
```

Iterates all users in `quests_data`. For each user whose `last_reset` date is before today:
1. Picks a random new quest
2. Resets `active_quests`, `completed_today`, `progress`
3. Updates `last_reset`

Starts with `@check_daily_reset.before_loop` → `await self.bot.wait_until_ready()`.

---

### 5.7 TCG Integration

Both quest completion and achievement unlock have TCG award hooks:

```python
if tcg_manager:
    awarded = tcg_manager.award_for_game_event(str(user_id), 'mythic')
    if awarded:
        names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
        await user.send(f"🎴 You received TCG card(s): {', '.join(names)}")
```

`award_for_game_event` uses a probability check internally — not every quest/achievement triggers a card drop.

---

### 5.8 Commands

| Command | Description |
|---------|-------------|
| `L!quests` | View active quests with visual progress bars + rewards |
| `L!achievements [member]` | View achievements for self or another user |
| `/questshelp` | Paginated help for all quest commands (uses `PaginatedHelpView` from `minigames.py`) |

> **Note:** There are no slash equivalents for `L!quests` and `L!achievements` — they are prefix-only. Only `/questshelp` is a slash command.

---

## 6. Cross-Cog Integration Map

```
Quests (quests.py)
    ↑ update_quest_progress(user_id, "play_5_games")
    │       Called by: minigames.py, arcadegames.py, cardgames.py, boardgames.py
    ↑ update_quest_progress(user_id, "coin_collector", amount)
    │       Called by: economy.py (on add_coins)
    ↑ update_quest_progress(user_id, "social_butterfly")
    │       Called by: social.py
    ↑ update_quest_progress(user_id, "pet_caretaker")
            Called by: pets.py (on feed/play/walk)

    ↓ unlock_achievement(user_id, "first_win")   → Called internally on win
    ↓ add_coins(reward)                           → economy.py
    ↓ award_for_game_event('mythic')              → psyvrse_tcg.py (quest/ach reward)

WizardWars (wizardwars.py)
    ↓ award_for_game_event('mythic')              → psyvrse_tcg.py (duel win reward)
    [Economy: uses Gold (wizard['gold']), NOT PsyCoins]

Infinity Adventure (dnd.py + dnd_gate1_fantasy.py)
    [Standalone — no inter-cog economy hooks at this time]
    [Save file: data/saves/infinity_adventure.json]
```

---

## 7. Commands Reference

### Infinity Adventure

| Command | Type | Description |
|---------|------|-------------|
| `/dnd` | Slash | Start or continue your Infinity Adventure |

All interaction from there is via buttons, dropdowns, and modals within the `InfinityView`.

### Wizard Wars

| Command | Type | Action | Status |
|---------|------|--------|--------|
| `/wizardwars` | Slash | All actions (10 choices) | ✅ |
| `/ww` | Slash | Shorthand alias | ✅ |

### Quests & Achievements

| Command | Type | Description |
|---------|------|-------------|
| `L!quests` | Prefix | View daily quest + progress bar |
| `L!achievements [member]` | Prefix | View achievements grid |
| `/questshelp` | Slash | Paginated help (PaginatedHelpView) |

---

## 8. Part 8 Summary

### What makes Part 8 unique in the codebase

1. **Scale** — `dnd_gate1_fantasy.py` at 9,902 lines is the single largest file in the project, nearly 5× the size of a typical large cog.
2. **Narrative depth** — Infinity Adventure is the only feature in the bot that has persistent, cross-death world state consequences. A player can permanently change a dimension.
3. **Bilingual RPG** — Full EN/PL translation system for an interactive story game, not just UI labels.
4. **Party support** — Multiple Discord users can share one `InfinityView` and take turns making story decisions.
5. **Gold economy** — Wizard Wars intentionally uses a separate `Gold` currency to keep its progression isolated from PsyCoins.
6. **TCG hooks** — Both Wizard Wars wins and Quest/Achievement completions feed into the TCG card reward pipeline.
7. **Architect pattern** — `InfinityView` is a state machine — one Discord message that morphs through 7+ screens without ever sending a new message.

---

### Stats

| Metric | Value |
|--------|-------|
| Total lines | ~13,386 |
| Commands (slash) | 3 (`/dnd`, `/wizardwars`, `/ww`) |
| Commands (prefix) | 2 (`L!quests`, `L!achievements`) |
| Spells | 32 across 4 schools |
| Spell combos | 6 |
| Territories | 12 |
| Daily quest types | 5 |
| Achievement types | 10 |
| RPG gates designed | 9 |
| Gates fully implemented | 1 (Gate 1 — 9,902 lines) |
| Gate 1 scenes | 50+ |
| Quest flags (Gate 1) | 25 |
| Factions (Gate 1) | 4 (Royal Guard, Resistance, Demons, Church) |
| Languages | 2 (EN/PL) |

---

*Part 8 documented by: wilczek80 | March 2026*
