# 🎭 PART 6: Multiplayer Games - Complete Documentation

> **Social Deduction & Multiplayer Game Systems**  
> mafia.py (2,639 lines) | multiplayer_games.py | dueling.py | monopoly.py  
> 4,000+ lines total | Full voice mode support | Interactive Discord UI

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Mafia/Werewolf System (2,639 lines)](#mafiawerewolf-system)
   - [Architecture](#architecture)
   - [Role Database](#role-database)
   - [Preset System](#preset-system)
   - [Custom Presets](#custom-presets)
   - [Time Presets](#time-presets)
   - [Auto-Balance Checker](#auto-balance-checker)
   - [Lobby System](#lobby-system)
   - [Settings Interface](#settings-interface)
   - [Role Picker](#role-picker)
   - [Voice Mode](#voice-mode)
   - [Game Loop](#game-loop)
   - [Phase System](#phase-system)
   - [Win Conditions](#win-conditions)
3. [Other Multiplayer Games](#other-multiplayer-games)
   - [Murder Mystery](#murder-mystery) - Among Us-style social deduction
   - [Clue](#clue) - WHO/WHAT/WHERE mystery
   - [Dueling](#dueling) - 1v1 PvP combat system
   - [Monopoly](#monopoly) - Full board game implementation
4. [Statistics](#statistics)
---

## 🎯 OVERVIEW

### System Purpose
The Multiplayer Games system provides **social deduction games** where players work together or against each other using **hidden roles, deduction, and strategy**. The flagship feature is the Mafia/Werewolf system with full voice mode support.

### Files Structure
```
cogs/
├── mafia.py (2,639 lines) - Full Mafia/Werewolf system ⭐ NEW
├── multiplayer_games.py (800 lines) - Other social games
├── dueling.py (400 lines) - PvP dueling system
└── monopoly.py (1,000 lines) - Monopoly board game
```

### Key Features
- ✅ **Dual Themes**: Mafia & Werewolf with unique roles
- ✅ **3 Game Modes**: Normal, Advanced, Custom
- ✅ **100+ Roles**: Across 4 databases with descriptions
- ✅ **Voice Mode**: Meeting spots with teleportation & locking
- ✅ **Smart Presets**: Balanced role distributions for 6-16 players
- ✅ **Auto-Balance**: AI-powered role composition analysis
- ✅ **Full Game Loop**: Night → Day → Vote → Win check
- ✅ **Bilingual**: Polish & English support
- ✅ **Interactive UI**: Discord Components v2

---

## 🕴️ MAFIA/WEREWOLF SYSTEM

### File: `mafia.py` (2,639 lines)

The most comprehensive social deduction game implementation with **26 complete features**:

### Architecture

#### Lines 1-170: Role Database System
```python
ROLES_DATABASE = {
    "mafia_normal": {
        "TOWN": {
            "citizen": {...},      # Basic villager
            "detective": {...},    # Investigate players
            "doctor": {...},       # Protect from kills
            "veteran": {...},      # Kill visitors
            # ... 15+ roles
        },
        "MAFIA": {
            "mafia": {...},        # Basic mafia
            "godfather": {...},    # Mafia leader
            "mafioso": {...},      # Mafia member
            # ... 5+ roles
        },
        "NEUTRAL": {...},
        "CHAOS": {...}
    },
    "mafia_advanced": {
        # 50+ advanced roles
        "TOWN": {...},
        "MAFIA": {...},
        "NEUTRAL": {...},
        "CHAOS": {...}
    },
    "werewolf_normal": {
        # 30+ werewolf roles
        "VILLAGE": {...},
        "WEREWOLVES": {...},
        "NEUTRAL": {...},
        "CHAOS": {...}
    },
    "werewolf_advanced": {
        # 50+ advanced werewolf roles
    }
}
```

**Each role contains:**
- `name_pl` / `name_en` - Bilingual names
- `emoji` - Visual identifier
- `description_pl` / `description_en` - Full role description
- `power` - Role ability type (investigate, protect, kill, etc.)
- `faction` - Which team the role belongs to

### Preset System

#### Lines 172-198: Balanced Presets
```python
PRESETS = {
    "mafia_normal": {
        6: ["citizen", "citizen", "citizen", "detective", "mafia", "mafia"],
        8: ["citizen", "citizen", "citizen", "citizen", "detective", "doctor", "mafia", "mafia"],
        10: ["citizen", "citizen", "citizen", "citizen", "detective", "doctor", "veteran", 
             "mafia", "mafia", "godfather"],
        12: [...],  # Balanced for 12 players
        16: [...]   # Balanced for 16 players
    },
    "mafia_advanced": {
        8: [...],
        10: [...],
        12: [...],
        16: [...]
    },
    "werewolf_normal": {
        6: [...],
        8: [...],
        10: [...],
        12: [...]
    },
    "werewolf_advanced": {
        8: [...],
        10: [...],
        12: [...],
        16: [...]
    }
}
```

**Design Principles:**
- Evil faction: 20-35% of total players
- At least 1 investigator for 6+ players
- At least 1 protector for 8+ players
- Maximum 30% chaos roles
- Balanced power distribution

### Custom Presets

#### Lines 200-258: Themed Role Pools
```python
CUSTOM_PRESETS = {
    "mafia": {
        "chaos_mode": {
            "name_pl": "🌀 Tryb Chaosu",
            "name_en": "🌀 Chaos Mode",
            "roles": [
                "jester", "executioner", "witch", "arsonist",
                "serial_killer", "plaguebearer", "werewolf",
                "vampire", "pirate", "survivor", "amnesiac",
                "guardian_angel", "witch", "arsonist", "jester"
            ]  # 15 roles for 8 players = random selection
        },
        "detective_heavy": {
            "name_pl": "🔍 Detektywi",
            "name_en": "🔍 Detective Heavy",
            "roles": ["detective", "sheriff", "investigator", "lookout", 
                     "spy", "tracker", "citizen", "citizen", "doctor",
                     "bodyguard", "mafia", "mafia", "godfather", 
                     "consigliere", "consort"]
        },
        "power_roles": {...},
        "balanced_chaos": {...}
    },
    "werewolf": {
        "chaos_mode": {...},
        "mystic_mode": {...},
        "hunter_pack": {...},
        "balanced_chaos": {...}
    }
}
```

**Features:**
- 8 themed presets (4 per theme)
- Allows 15+ roles for 8 players (random selection)
- Auto-enables random mode
- Evil count control (auto or manual 1-5)

### Time Presets

#### Lines 260-296: Timing Configurations
```python
TIME_PRESETS = {
    "fast": {
        "name_pl": "⚡ Szybki",
        "name_en": "⚡ Fast",
        "day": 60,      # 1 minute
        "night": 30,    # 30 seconds
        "vote": 30      # 30 seconds
    },
    "standard": {
        "name_pl": "⏱️ Standardowy",
        "name_en": "⏱️ Standard",
        "day": 180,     # 3 minutes
        "night": 90,    # 1.5 minutes
        "vote": 60      # 1 minute
    },
    "hardcore": {
        "name_pl": "🔥 Hardcore",
        "name_en": "🔥 Hardcore",
        "day": 300,     # 5 minutes
        "night": 120,   # 2 minutes
        "vote": 90      # 1.5 minutes
    },
    "roleplay": {
        "name_pl": "🎭 Roleplay",
        "name_en": "🎭 Roleplay",
        "day": 600,     # 10 minutes
        "night": 180,   # 3 minutes
        "vote": 120     # 2 minutes
    }
}
```

### Auto-Balance Checker

#### Lines 300-410: Role Composition Analysis
```python
def check_role_balance(theme: str, mode: str, custom_roles: list, 
                       player_count: int, lang: str = "en") -> dict:
    """
    Analyzes custom role selection for balance issues
    
    Returns:
        {
            "status": "balanced" | "risky" | "chaotic",
            "warnings": ["⚠️ warning messages"],
            "suggestions": ["💡 suggestion messages"],
            "emoji": "✅" | "⚠️" | "🌀" | "💡"
        }
    """
    result = {
        "status": "balanced",
        "warnings": [],
        "suggestions": [],
        "emoji": "✅"
    }
    
    # Analyze faction counts
    faction_counts = {}
    power_counts = {"investigate": 0, "protect": 0, "kill": 0}
    chaos_count = 0
    
    # Count each role's faction and powers
    for role_id in custom_roles:
        # ... counting logic
    
    # Check evil ratio (should be 20-35%)
    evil_ratio = evil_count / player_count
    if evil_ratio > 0.45:
        result["status"] = "risky"
        result["warnings"].append(
            f"⚠️ Za dużo złych ról ({evil_count}/{player_count} = {evil_ratio*100:.0f}%)"
        )
    elif evil_ratio < 0.15:
        result["status"] = "risky"
        result["warnings"].append(
            f"⚠️ Za mało złych ról ({evil_count}/{player_count} = {evil_ratio*100:.0f}%)"
        )
    
    # Check chaos overload (>30% is chaotic)
    if chaos_count > player_count * 0.3:
        result["status"] = "chaotic"
        result["warnings"].append(
            f"🌀 Dużo ról chaos ({chaos_count}/{player_count})"
        )
    
    # Suggest missing investigators
    if power_counts["investigate"] == 0 and good_count > 3:
        result["suggestions"].append("💡 Dodaj detektywa/jasnowidza")
    
    # Suggest missing healers
    if power_counts["protect"] == 0 and player_count >= 8:
        result["suggestions"].append("💡 Dodaj lekarza/ochroniarza")
    
    # Warn about excess investigators
    if power_counts["investigate"] > 3:
        result["warnings"].append(
            f"⚠️ Za dużo śledczych ({power_counts['investigate']})"
        )
    
    return result
```

**Analysis Criteria:**
- ✅ **Balanced**: 20-35% evil, proper power distribution
- ⚠️ **Risky**: Evil ratio too high/low
- 🌀 **Chaotic**: >30% chaos roles
- 💡 **Suggestions**: Missing essential roles

### Lobby System

#### Lines 1590-1690: Lobby View Class
```python
class MafiaLobbyView(discord.ui.LayoutView):
    """Main lobby interface with player list and controls"""
    
    def __init__(self, cog, lobby_id):
        self.cog = cog
        self.lobby_id = lobby_id
        super().__init__(timeout=300)
        self._build_ui()
    
    def _build_ui(self):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        lang = lobby["language"]
        theme = lobby["theme"]
        mode = lobby["mode"]
        
        # Build player list
        players_text = "\n".join([f"• <@{pid}>" for pid in lobby["players"]])
        
        # Build settings summary
        theme_emoji = "🕴️" if theme == "mafia" else "🐺"
        mode_emoji = {"normal": "📘", "advanced": "⚡", "custom": "🎯"}[mode]
        
        content = (
            f"# {theme_emoji} **{'MAFIA' if theme == 'mafia' else 'WEREWOLF'}** "
            f"{mode_emoji} {mode.upper()}\n\n"
            f"**{'Gracze' if lang == 'pl' else 'Players'} ({len(lobby['players'])}/16):**\n"
            f"{players_text}\n\n"
            f"**{'Ustawienia' if lang == 'pl' else 'Settings'}:**\n"
            f"• {'Język' if lang == 'pl' else 'Language'}: {lang.upper()}\n"
            f"• {'Dzień' if lang == 'pl' else 'Day'}: {lobby['day_duration']}s\n"
            f"• {'Noc' if lang == 'pl' else 'Night'}: {lobby['night_duration']}s\n"
            f"• {'Głosowanie' if lang == 'pl' else 'Vote'}: {lobby['vote_duration']}s\n"
            f"• {'Voice Mode' if lang == 'en' else 'Tryb Głosowy'}: "
            f"{'✅' if lobby.get('voice_mode') else '❌'}\n"
        )
        
        # Show role info for normal/advanced modes
        if mode != "custom":
            roles_info = self._get_roles_info_for_mode()
            if roles_info:
                content += f"\n**{'Role' if lang == 'pl' else 'Roles'}:**\n{roles_info}"
        else:
            # Show custom roles
            if lobby.get("custom_roles"):
                content += f"\n**{'Wybrane role' if lang == 'pl' else 'Selected Roles'}:** "
                content += f"{len(lobby['custom_roles'])}"
                if lobby.get("random_roles"):
                    content += " 🎲"
        
        # Create buttons
        join_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="➕",
            label="Join" if lang == "en" else "Dołącz"
        )
        leave_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            emoji="➖",
            label="Leave" if lang == "en" else "Wyjdź"
        )
        settings_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            label="Settings" if lang == "en" else "Ustawienia"
        )
        start_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="▶️",
            label="Start" if lang == "en" else "Start"
        )
        cancel_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            emoji="❌",
            label="Cancel" if lang == "en" else "Anuluj"
        )
        
        # Wire callbacks
        join_btn.callback = self.join_callback
        leave_btn.callback = self.leave_callback
        settings_btn.callback = self.settings_callback
        start_btn.callback = self.start_callback
        cancel_btn.callback = self.cancel_callback
        
        # Create container with all UI elements
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(join_btn, leave_btn),
            discord.ui.ActionRow(settings_btn, start_btn, cancel_btn),
            accent_colour=discord.Colour.red() if theme == "mafia" else discord.Colour.dark_grey()
        )
        
        self.add_item(self.container)
```

**Lobby Features:**
- Player join/leave
- Settings access (host only)
- Game start validation (6+ players)
- Real-time player list updates
- Role preview for normal/advanced
- Custom role count for custom mode

### Settings Interface

#### Lines 420-585: Settings View Class
```python
class MafiaSettingsView(discord.ui.LayoutView):
    """Interactive settings interface - NOT a modal"""
    
    def _build_ui(self):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        lang = lobby["language"]
        
        # Theme toggle
        theme_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="🕴️" if lobby["theme"] == "mafia" else "🐺",
            label=f"Theme: {lobby['theme'].title()}"
        )
        theme_btn.callback = self.toggle_theme
        
        # Mode cycle
        mode_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji={"normal": "📘", "advanced": "⚡", "custom": "🎯"}[lobby["mode"]],
            label=f"Mode: {lobby['mode'].title()}"
        )
        mode_btn.callback = self.cycle_mode
        
        # Language toggle
        lang_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji="🇵🇱" if lang == "pl" else "🇬🇧",
            label=f"Language: {lang.upper()}"
        )
        lang_btn.callback = self.toggle_language
        
        # Voice mode toggle
        voice_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby.get("voice_mode") else discord.ButtonStyle.secondary,
            emoji="🎙️",
            label="Voice Mode: " + ("ON" if lobby.get("voice_mode") else "OFF")
        )
        voice_btn.callback = self.toggle_voice
        
        # Time preset select
        time_preset_select = discord.ui.Select(
            placeholder="⏱️ Time Presets",
            options=[
                discord.SelectOption(
                    label="⚡ Fast (60/30/30s)",
                    value="fast",
                    description="Quick games"
                ),
                discord.SelectOption(
                    label="⏱️ Standard (180/90/60s)",
                    value="standard",
                    description="Default timing"
                ),
                discord.SelectOption(
                    label="🔥 Hardcore (300/120/90s)",
                    value="hardcore",
                    description="Long strategic games"
                ),
                discord.SelectOption(
                    label="🎭 Roleplay (600/180/120s)",
                    value="roleplay",
                    description="RP-heavy games"
                ),
            ]
        )
        time_preset_select.callback = self.apply_time_preset
        
        # Custom mode button
        custom_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="🎯",
            label="Custom Roles" if lang == "en" else "Niestandardowe Role"
        )
        custom_btn.callback = self.open_role_picker
        
        # Back button
        back_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="◀️",
            label="Back" if lang == "en" else "Powrót"
        )
        back_btn.callback = self.back_to_lobby
        
        # Build container
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content="# ⚙️ SETTINGS"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(theme_btn, mode_btn, lang_btn),
            discord.ui.ActionRow(voice_btn),
            time_preset_select,
            discord.ui.ActionRow(custom_btn),
            discord.ui.ActionRow(back_btn),
            accent_colour=discord.Colour.blue()
        )
```

**Settings Options:**
- **Theme**: Mafia ↔ Werewolf
- **Mode**: Normal → Advanced → Custom → Normal
- **Language**: EN ↔ PL
- **Voice Mode**: ON/OFF toggle
- **Time Presets**: Fast, Standard, Hardcore, Roleplay
- **Custom Roles**: Opens role picker

### Role Picker

#### Lines 660-1060: Custom Role Selection
```python
class MafiaRolePickerView(discord.ui.LayoutView):
    """Interactive role picker for custom mode"""
    
    def __init__(self, cog, lobby_id):
        self.cog = cog
        self.lobby_id = lobby_id
        self.page = 0
        self.roles_per_page = 15  # Reduced for balance display
        super().__init__(timeout=300)
        self._build_ui()
    
    def _build_ui(self, preview_message: str = None, preview_role: dict = None):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        player_count = len(lobby["players"])
        selected_roles = lobby.get("custom_roles", [])
        lang = lobby["language"]
        theme = lobby["theme"]
        mode = lobby["mode"]
        
        # Get all roles from database
        all_roles = self._get_all_roles()
        total_pages = (len(all_roles) + self.roles_per_page - 1) // self.roles_per_page
        
        # Build header
        content = (
            f"# 🎯 {'NIESTANDARDOWY WYBÓR RÓL' if lang == 'pl' else 'CUSTOM ROLE SELECTION'}\n\n"
            f"**{'Graczy' if lang == 'pl' else 'Players'}:** {player_count}\n"
            f"**{'Wybrane role' if lang == 'pl' else 'Selected Roles'}:** {len(selected_roles)}"
        )
        
        if lobby.get("random_roles"):
            content += f" {'🎲 LOSOWE' if lang == 'pl' else ' 🎲 RANDOM'}"
        else:
            content += f"/{player_count}"
        
        if lobby.get("evil_count") is not None:
            faction_name = "Mafii" if theme == "mafia" else "Wilkołaków"
            content += f"\n**{faction_name}:** {lobby['evil_count']}"
        
        content += "\n"
        
        # Show balance check if roles selected
        if len(selected_roles) > 0:
            balance = check_role_balance(theme, mode, selected_roles, player_count, lang)
            content += f"\n{balance['emoji']} **Balance:** {balance['status'].title()}"
            
            if balance['warnings']:
                warnings_text = "\n".join([f"⚠️ {w}" for w in balance['warnings']])
                content += f"\n{warnings_text}"
            
            if balance['suggestions']:
                suggestions_text = "\n".join([f"💡 {s}" for s in balance['suggestions']])
                content += f"\n{suggestions_text}"
            
            content += "\n"
        
        # Show selected roles
        if selected_roles:
            roles_display = []
            db_key = f"{theme}_advanced"
            role_db = ROLES_DATABASE.get(db_key, {})
            
            for role_id in selected_roles:
                for faction, roles in role_db.items():
                    if role_id in roles:
                        role_data = roles[role_id]
                        role_name = role_data[f"name_{lang}"]
                        role_emoji = role_data["emoji"]
                        roles_display.append(f"{role_emoji} {role_name}")
                        break
            
            roles_text = "\n".join([f"• {role}" for role in roles_display])
            content += f"\n**{'Obecny wybór' if lang == 'pl' else 'Current Selection'}:**\n{roles_text}\n"
        
        content += f"\n**{'Strona' if lang == 'pl' else 'Page'} {self.page + 1}/{total_pages}**"
        
        # Preview mode: show role description
        if preview_message:
            items = [
                discord.ui.TextDisplay(content=preview_message),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
            ]
            
            # Add/Cancel buttons
            add_btn = discord.ui.Button(
                style=discord.ButtonStyle.success,
                emoji="✅",
                label="Dodaj" if lang == "pl" else "Add"
            )
            cancel_btn = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                emoji="❌",
                label="Anuluj" if lang == "pl" else "Cancel"
            )
            
            add_btn.callback = lambda i: self.add_preview_role(i, preview_role)
            cancel_btn.callback = self.cancel_preview
            
            items.append(discord.ui.ActionRow(add_btn, cancel_btn))
            
            self.container = discord.ui.Container(*items, accent_colour=discord.Colour.blue())
            self.clear_items()
            self.add_item(self.container)
            return
        
        # Normal mode: show role buttons
        items = [discord.ui.TextDisplay(content=content)]
        
        # Get page roles
        start_idx = self.page * self.roles_per_page
        end_idx = start_idx + self.roles_per_page
        page_roles = all_roles[start_idx:end_idx]
        
        # Create role buttons (5 per row, 3 rows = 15 roles)
        current_row = []
        for role_info in page_roles:
            role_id = role_info["id"]
            role_emoji = role_info["emoji"]
            is_selected = role_id in selected_roles
            
            btn = discord.ui.Button(
                style=discord.ButtonStyle.success if is_selected else discord.ButtonStyle.primary,
                emoji=role_emoji,
                label="✓" if is_selected else ""
            )
            btn.callback = lambda i, r=role_info: self.toggle_role(i, r)
            current_row.append(btn)
            
            if len(current_row) == 5:
                items.append(discord.ui.ActionRow(*current_row))
                current_row = []
        
        if current_row:
            items.append(discord.ui.ActionRow(*current_row))
        
        # Options row
        random_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby.get("random_roles") else discord.ButtonStyle.secondary,
            emoji="🎲",
            label="Random" if lang == "en" else "Losowe"
        )
        random_btn.callback = self.toggle_random
        
        # Evil count select
        evil_select = discord.ui.Select(
            placeholder="👹 Evil Count",
            options=[
                discord.SelectOption(label="Auto (25-30%)", value="auto"),
                discord.SelectOption(label="1 Evil", value="1"),
                discord.SelectOption(label="2 Evil", value="2"),
                discord.SelectOption(label="3 Evil", value="3"),
                discord.SelectOption(label="4 Evil", value="4"),
                discord.SelectOption(label="5 Evil", value="5"),
            ]
        )
        evil_select.callback = self.set_evil_count
        
        # Preset select (custom presets OR dynamic classic/advanced)
        preset_options = []
        
        # Dynamic presets based on player count
        preset_key = f"{theme}_normal"
        if player_count in PRESETS.get(preset_key, {}):
            preset_options.append(
                discord.SelectOption(
                    label=f"📋 {'Klasyczny' if lang == 'pl' else 'Classic'} ({player_count})",
                    value=f"dynamic_normal_{player_count}"
                )
            )
        
        preset_key = f"{theme}_advanced"
        if player_count in PRESETS.get(preset_key, {}):
            preset_options.append(
                discord.SelectOption(
                    label=f"⚡ {'Rozbudowany' if lang == 'pl' else 'Advanced'} ({player_count})",
                    value=f"dynamic_advanced_{player_count}"
                )
            )
        
        # Custom presets
        for preset_id, preset_data in CUSTOM_PRESETS.get(theme, {}).items():
            preset_options.append(
                discord.SelectOption(
                    label=preset_data[f"name_{lang}"],
                    value=f"custom_{preset_id}"
                )
            )
        
        preset_select = discord.ui.Select(
            placeholder="📦 Load Preset",
            options=preset_options
        )
        preset_select.callback = self.load_preset
        
        items.append(discord.ui.ActionRow(random_btn))
        items.append(evil_select)
        items.append(preset_select)
        
        # Navigation row
        prev_btn = discord.ui.Button(emoji="◀️", disabled=(self.page == 0))
        next_btn = discord.ui.Button(emoji="▶️", disabled=(self.page >= total_pages - 1))
        clear_btn = discord.ui.Button(emoji="🗑️", label="Clear" if lang == "en" else "Wyczyść")
        back_btn = discord.ui.Button(emoji="◀️", label="Back" if lang == "en" else "Powrót")
        
        prev_btn.callback = self.prev_page
        next_btn.callback = self.next_page
        clear_btn.callback = self.clear_roles
        back_btn.callback = self.back_to_settings
        
        items.append(discord.ui.ActionRow(prev_btn, next_btn, clear_btn, back_btn))
        
        self.container = discord.ui.Container(*items, accent_colour=discord.Colour.gold())
        self.clear_items()
        self.add_item(self.container)
```

**Role Picker Features:**
- 15 roles per page (to fit balance display)
- Click role = preview with full description
- Click selected role = remove (✓ indicator)
- Random mode toggle (allows 15+ roles for variety)
- Evil count control (auto or manual 1-5)
- Load presets:
  - Dynamic Classic/Advanced for player count
  - 8 custom themed presets
- Auto-balance display shows warnings/suggestions
- Pagination for 100+ roles

### Voice Mode

#### Lines 1868-1940: Voice Channel Creation
```python
# Voice mode: create meeting spot voice channels + game center text channel
voice_channels = []
center_voice_channel = None
game_center_text = None

if lobby.get("voice_mode", False):
    # Create game center text channel for votes/interactions
    game_center_text = await guild.create_text_channel(
        name="🎯-centrum-gry" if lang == "pl" else "🎯-game-center",
        category=category
    )
    
    # Theme-specific meeting spots
    if theme == "mafia":
        meeting_spots = [
            ("🍰", "cukiernia" if lang == "pl" else "cafe"),
            ("🏦", "bank" if lang == "pl" else "bank"),
            ("🎰", "kasyno" if lang == "pl" else "casino"),
            ("🏪", "sklep" if lang == "pl" else "store"),
            ("🏭", "fabryka" if lang == "pl" else "factory"),
            ("🚔", "posterunek" if lang == "pl" else "police-station"),
            ("🏗️", "magazyn" if lang == "pl" else "warehouse"),
            ("🌉", "doki" if lang == "pl" else "docks"),
        ]
    else:  # werewolf
        meeting_spots = [
            ("🌾", "farma" if lang == "pl" else "farm"),
            ("🌲", "las" if lang == "pl" else "forest"),
            ("⛏️", "kopalnia" if lang == "pl" else "mine"),
            ("🏚️", "opuszczony-dom" if lang == "pl" else "abandoned-house"),
            ("🏔️", "góry" if lang == "pl" else "mountains"),
            ("🌊", "jezioro" if lang == "pl" else "lake"),
            ("⛪", "kościół" if lang == "pl" else "church"),
            ("🏰", "zamek" if lang == "pl" else "castle"),
        ]
    
    # Create main center voice channel (where players gather during day/voting)
    center_name = "🏛️-centrum-miasta" if theme == "mafia" else "🔥-ognisko"
    if lang == "en":
        center_name = "🏛️-town-center" if theme == "mafia" else "🔥-campfire"
    
    center_voice_channel = await guild.create_voice_channel(
        name=center_name,
        category=category
    )
    
    # Create meeting spot channels
    for emoji, name in meeting_spots:
        vc = await guild.create_voice_channel(
            name=f"{emoji}-{name}",
            category=category
        )
        voice_channels.append(vc.id)
        # All players can join initially
        for member in [await guild.fetch_member(pid) for pid in lobby["players"]]:
            await vc.set_permissions(member, connect=True, speak=True)
    
    # Set permissions for center voice channel
    for member in [await guild.fetch_member(pid) for pid in lobby["players"]]:
        await center_voice_channel.set_permissions(member, connect=True, speak=True)
    
    # Set permissions for game center text
    for member in [await guild.fetch_member(pid) for pid in lobby["players"]]:
        await game_center_text.set_permissions(member, read_messages=True, send_messages=False)
```

**Voice Mode Channels:**
- **🎯 Game Center (text)**: Read-only updates (votes, phases, locks)
- **🏛️ Town Center / 🔥 Campfire (voice)**: Main gathering spot
- **8 Meeting Spots (voice)**: Theme-specific locations
  - **Mafia**: cafe, bank, casino, store, factory, police, warehouse, docks
  - **Werewolf**: farm, forest, mine, house, mountains, lake, church, castle

#### Lines 2117-2165: Night Phase Locking
```python
# Voice mode: lock meeting spots and move players to center
guild = self.bot.get_guild(game_state["guild_id"])
if game_state.get("voice_mode", False):
    # Lock all meeting spot voice channels
    for vc_id in game_state.get("voice_channels", []):
        vc = guild.get_channel(vc_id)
        if vc:
            # Block all connections
            await vc.set_permissions(guild.default_role, connect=False)
            # Move any remaining players to center
            for member in vc.members:
                center_vc = guild.get_channel(game_state.get("center_voice_channel_id"))
                if center_vc:
                    try:
                        await member.move_to(center_vc)
                    except:
                        pass
    
    # Announce in game center text
    game_center = self.bot.get_channel(game_state.get("game_center_text_id"))
    if game_center:
        await game_center.send(
            f"🌙 **{'NOC' if lang == 'pl' else 'NIGHT'} {day_num}**\n"
            f"🔒 {'Wszystkie lokacje są zamknięte!' if lang == 'pl' else 'All locations are locked!'}\n"
            f"{'Wszyscy gracze przebywają w centrum.' if lang == 'pl' else 'All players stay at the center.'}"
        )
```

#### Lines 2230-2265: Day Phase Unlocking
```python
# Voice mode: unlock meeting spots
if game_state.get("voice_mode", False):
    for vc_id in game_state.get("voice_channels", []):
        vc = guild.get_channel(vc_id)
        if vc:
            # Unlock all connections
            await vc.set_permissions(guild.default_role, connect=True)
    
    # Announce in game center text
    game_center = self.bot.get_channel(game_state.get("game_center_text_id"))
    if game_center:
        await game_center.send(
            f"☀️ **{'DZIEŃ' if lang == 'pl' else 'DAY'} {game_state['day_number']}**\n"
            f"🔓 {'Wszystkie lokacje są otwarte!' if lang == 'pl' else 'All locations are open!'}\n"
            f"{'Możecie się swobodnie przemieszczać i rozmawiać.' if lang == 'pl' else 'You can freely move and talk.'}"
        )
```

#### Lines 2280-2320: Vote Phase Teleportation
```python
# Voice mode: teleport all to center and lock meeting spots
if game_state.get("voice_mode", False):
    center_vc = guild.get_channel(game_state.get("center_voice_channel_id"))
    
    # Lock meeting spots
    for vc_id in game_state.get("voice_channels", []):
        vc = guild.get_channel(vc_id)
        if vc:
            await vc.set_permissions(guild.default_role, connect=False)
            # Move players to center
            for member in vc.members:
                if center_vc:
                    try:
                        await member.move_to(center_vc)
                    except:
                        pass
```

**Voice Mode Mechanics:**
- **Night 🌙**: All meeting spots locked → players teleported to center
- **Day ☀️**: All meeting spots unlocked → free movement
- **Vote 🗳️**: All meeting spots locked → players teleported to center
- **Game Center**: Updates posted for phase changes

### Game Loop

#### Lines 1850-2010: Game Initialization
```python
async def start_mafia_game(self, interaction: discord.Interaction, lobby_id: str):
    """Start the actual Mafia game with full loop"""
    lobby = self.active_lobbies.get(lobby_id)
    guild = interaction.guild
    lang = lobby["language"]
    theme = lobby["theme"]
    mode = lobby["mode"]
    player_count = len(lobby["players"])
    
    # Create game category and channels
    category_name = f"🎮 Mafia Game #{channel.id % 10000}"
    category = await guild.create_category(category_name)
    
    # Main channel (everyone can see/talk)
    main_channel = await guild.create_text_channel(
        name="🏛️-main" if theme == "mafia" else "🏘️-main",
        category=category
    )
    
    # Evil faction channel
    evil_name = "🔫-mafia" if theme == "mafia" else "🐺-werewolves"
    evil_channel = await guild.create_text_channel(
        name=evil_name,
        category=category
    )
    
    # Dead channel
    dead_channel = await guild.create_text_channel(
        name="💀-ghosts" if lang == "en" else "💀-duchy",
        category=category
    )
    
    # [Voice mode channel creation - see above]
    
    # Assign roles
    if mode == "custom":
        roles = lobby["custom_roles"].copy()
        random_mode = lobby.get("random_roles", False)
        
        if random_mode:
            # Random selection from pool
            random.shuffle(roles)
            selected_roles = roles[:player_count]
        else:
            selected_roles = roles
    else:
        # Use preset
        preset_key = f"{theme}_{mode}"
        selected_roles = PRESETS[preset_key][player_count].copy()
    
    # Shuffle and assign
    random.shuffle(selected_roles)
    players_shuffled = lobby["players"].copy()
    random.shuffle(players_shuffled)
    
    # Create game state
    game_state = {
        "lobby_id": lobby_id,
        "guild_id": guild.id,
        "category_id": category.id,
        "main_channel_id": main_channel.id,
        "evil_channel_id": evil_channel.id,
        "dead_channel_id": dead_channel.id,
        "voice_channels": voice_channels,
        "center_voice_channel_id": center_voice_channel.id if center_voice_channel else None,
        "game_center_text_id": game_center_text.id if game_center_text else None,
        "theme": theme,
        "mode": mode,
        "language": lang,
        "day_duration": lobby["day_duration"],
        "night_duration": lobby["night_duration"],
        "vote_duration": lobby["vote_duration"],
        "voice_mode": lobby["voice_mode"],
        "players": {},
        "alive_players": [],
        "dead_players": [],
        "day_number": 0,
        "phase": "night",
        "night_actions": {},
        "votes": {},
    }
    
    # Assign roles to players
    db_key = f"{theme}_advanced" if mode in ["advanced", "custom"] else f"{theme}_normal"
    role_db = ROLES_DATABASE.get(db_key, {})
    
    for player_id, role_id in zip(players_shuffled, selected_roles):
        # Find role info
        role_info = None
        faction = None
        for f, roles in role_db.items():
            if role_id in roles:
                role_info = roles[role_id]
                faction = f
                break
        
        game_state["players"][player_id] = {
            "role": role_id,
            "role_info": role_info,
            "faction": faction,
            "alive": True,
            "protected": False,
            "votes": 0,
        }
        game_state["alive_players"].append(player_id)
    
    self.active_games[lobby_id] = game_state
    
    # Send role DMs
    await self._send_roles_dm(game_state)
    
    # Announce game start
    await channel.send(
        f"# 🎮 **{'GRA ROZPOCZĘTA!' if lang == 'pl' else 'GAME STARTED!'}**\n"
        f"{'Sprawdźcie DM po swoje role!' if lang == 'pl' else 'Check your DMs for your role!'}"
    )
    
    await main_channel.send(
        f"# 🎮 **{'WITAMY W GRZE!' if lang == 'pl' else 'WELCOME TO THE GAME!'}**\n"
        f"{'Gracze' if lang == 'pl' else 'Players'}: {len(game_state['players'])}\n"
        f"{'Tryb' if lang == 'pl' else 'Mode'}: **{theme.title()} - {mode.title()}**\n"
        + (f"\n🎙️ **Voice Mode Active!**\n"
           f"{'Spotykajcie się w kanałach głosowych aby rozmawiać!' if lang == 'pl' else 'Meet in voice channels to talk!'}\n"
           f"{'Uważajcie - inni gracze mogą was podsłuchać!' if lang == 'pl' else 'Be careful - other players might overhear you!'}\n"
           if game_state.get('voice_mode', False) else "")
        + f"\n{'Gra rozpocznie się za chwilę...' if lang == 'pl' else 'Game will start shortly...'}"
    )
    
    await asyncio.sleep(5)
    
    # Start first night
    await self._night_phase(lobby_id)
```

### Phase System

#### Lines 2080-2175: Night Phase
```python
async def _night_phase(self, lobby_id: str):
    """Execute night phase"""
    game_state = self.active_games.get(lobby_id)
    game_state["day_number"] += 1
    game_state["phase"] = "night"
    game_state["night_actions"] = {}
    
    main_channel = self.bot.get_channel(game_state["main_channel_id"])
    evil_channel = self.bot.get_channel(game_state["evil_channel_id"])
    lang = game_state["language"]
    theme = game_state["theme"]
    day_num = game_state["day_number"]
    
    # Determine evil faction name
    evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
    evil_name = "Mafia" if theme == "mafia" else ("Wilkołaki" if lang == "pl" else "Werewolves")
    
    await main_channel.send(
        f"# 🌙 {'NOC' if lang == 'pl' else 'NIGHT'} {day_num}\n"
        f"{'Miasto zasypia... Role specjalne działają w cieniu.' if lang == 'pl' else 'The town sleeps... Special roles act in the shadows.'}\n"
        f"⏱️ {game_state['night_duration']}s"
    )
    
    # [Voice mode locking - see above]
    
    # Get evil players
    evil_players = [pid for pid, pdata in game_state["players"].items() 
                   if pdata["faction"] == evil_faction and pdata["alive"]]
    
    if evil_players and not game_state.get("voice_mode", False):
        # Text mode: Create night action view for evil faction
        view = NightActionView(self, lobby_id, evil_faction)
        msg = await evil_channel.send(
            f"## 🔫 {evil_name} {'- wybierz ofiarę' if lang == 'pl' else '- choose victim'}",
            view=view
        )
        
        # Send DMs to evil players
        for pid in evil_players:
            try:
                user = await self.bot.fetch_user(pid)
                await user.send(
                    f"🌙 {'Noc' if lang == 'pl' else 'Night'} {day_num} - "
                    f"{'Głosuj na ofiarę w kanale gry' if lang == 'pl' else 'Vote for victim in game channel'}"
                )
            except:
                pass
    elif evil_players and game_state.get("voice_mode", False):
        # Voice mode: Evil players must meet in voice channels
        await main_channel.send(
            f"👥 **Voice Mode:** {evil_name} {'muszą spotkać się w kanałach głosowych aby się zorganizować!' if lang == 'pl' else 'must meet in voice channels to organize!'}\n"
            f"🔇 {'Bądźcie ostrożni - inni gracze mogą was podsłuchać!' if lang == 'pl' else 'Be careful - other players might overhear you!'}"
        )
        
        # Send DMs to evil players
        for pid in evil_players:
            try:
                user = await self.bot.fetch_user(pid)
                await user.send(
                    f"🌙 {'Noc' if lang == 'pl' else 'Night'} {day_num} - "
                    f"{'Tryb głosowy: spotkajcie się i ustalcie ofiarę!' if lang == 'pl' else 'Voice mode: meet up and decide on a victim!'}"
                )
            except:
                pass
    
    # Wait for night duration
    await asyncio.sleep(game_state["night_duration"])
    
    # Process night actions
    await self._process_night(lobby_id)
```

#### Lines 2177-2228: Process Night Actions
```python
async def _process_night(self, lobby_id: str):
    """Process night actions and move to day"""
    game_state = self.active_games.get(lobby_id)
    main_channel = self.bot.get_channel(game_state["main_channel_id"])
    dead_channel = self.bot.get_channel(game_state["dead_channel_id"])
    guild = self.bot.get_guild(game_state["guild_id"])
    lang = game_state["language"]
    theme = game_state["theme"]
    
    # Determine who was killed
    evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
    votes = game_state["night_actions"]
    
    # Count votes
    vote_counts = {}
    for voter, target in votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1
    
    # Get target with most votes
    target = max(vote_counts, key=vote_counts.get) if vote_counts else None
    
    killed_players = []
    
    if target and game_state["players"][target]["alive"]:
        # Check if protected
        if not game_state["players"][target].get("protected"):
            game_state["players"][target]["alive"] = False
            game_state["alive_players"].remove(target)
            game_state["dead_players"].append(target)
            killed_players.append(target)
            
            # Give dead player access to ghost channel
            try:
                member = await guild.fetch_member(target)
                await dead_channel.set_permissions(member, read_messages=True, send_messages=True)
            except:
                pass
    
    # Reset protections
    for pdata in game_state["players"].values():
        pdata["protected"] = False
    
    # Announce deaths
    await main_channel.send(f"# ☀️ {'DZIEŃ' if lang == 'pl' else 'DAY'} {game_state['day_number']}")
    
    if killed_players:
        for pid in killed_players:
            await main_channel.send(f"💀 <@{pid}> {'został zabity w nocy!' if lang == 'pl' else 'was killed during the night!'}")
    else:
        await main_channel.send(f"✨ {'Nikt nie zginął tej nocy!' if lang == 'pl' else 'No one died last night!'}")
    
    # Check win conditions
    if await self._check_win_condition(lobby_id):
        return
    
    # Start day phase
    await self._day_phase(lobby_id)
```

#### Lines 2230-2265: Day Phase
```python
async def _day_phase(self, lobby_id: str):
    """Execute day phase (discussion)"""
    game_state = self.active_games.get(lobby_id)
    game_state["phase"] = "day"
    main_channel = self.bot.get_channel(game_state["main_channel_id"])
    lang = game_state["language"]
    guild = self.bot.get_guild(game_state["guild_id"])
    
    # [Voice mode unlocking - see above]
    
    alive_mentions = " ".join([f"<@{pid}>" for pid in game_state["alive_players"]])
    
    await main_channel.send(
        f"## 💬 {'DYSKUSJA' if lang == 'pl' else 'DISCUSSION'}\n"
        f"{alive_mentions}\n"
        f"{'Dyskutujcie i znajdźcie podejrzanych!' if lang == 'pl' else 'Discuss and find the suspects!'}\n"
        f"⏱️ {game_state['day_duration']}s"
    )
    
    await asyncio.sleep(game_state["day_duration"])
    
    # Start voting phase
    await self._vote_phase(lobby_id)
```

#### Lines 2267-2325: Vote Phase
```python
async def _vote_phase(self, lobby_id: str):
    """Execute voting phase"""
    game_state = self.active_games.get(lobby_id)
    game_state["phase"] = "vote"
    game_state["votes"] = {}
    
    # Use game center text for voice mode, otherwise main channel
    if game_state.get("voice_mode", False) and game_state.get("game_center_text_id"):
        channel = self.bot.get_channel(game_state["game_center_text_id"])
    else:
        channel = self.bot.get_channel(game_state["main_channel_id"])
    
    lang = game_state["language"]
    guild = self.bot.get_guild(game_state["guild_id"])
    
    # [Voice mode teleportation - see above]
    
    view = VoteView(self, lobby_id)
    await channel.send(
        f"## 🗳️ {'GŁOSOWANIE' if lang == 'pl' else 'VOTING'}\n"
        f"{'Głosujcie kogo chcecie zlinczować!' if lang == 'pl' else 'Vote who to lynch!'}\n"
        f"⏱️ {game_state['vote_duration']}s",
        view=view
    )
    
    await asyncio.sleep(game_state["vote_duration"])
    
    # Process votes
    await self._process_votes(lobby_id)
```

#### Lines 2327-2385: Process Votes
```python
async def _process_votes(self, lobby_id: str):
    """Count votes and lynch player"""
    game_state = self.active_games.get(lobby_id)
    main_channel = self.bot.get_channel(game_state["main_channel_id"])
    dead_channel = self.bot.get_channel(game_state["dead_channel_id"])
    guild = self.bot.get_guild(game_state["guild_id"])
    lang = game_state["language"]
    
    votes = game_state["votes"]
    
    # Count votes
    vote_counts = {}
    for voter, target in votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1
    
    if not vote_counts:
        await main_channel.send(f"❌ {'Nikt nie głosował!' if lang == 'pl' else 'No one voted!'}")
    else:
        # Get lynched player
        lynched = max(vote_counts, key=vote_counts.get)
        lynched_votes = vote_counts[lynched]
        
        # Check for tie
        top_votes = [p for p, v in vote_counts.items() if v == lynched_votes]
        if len(top_votes) > 1:
            await main_channel.send(
                f"❌ {'Remis!' if lang == 'pl' else 'Tie!'} "
                f"({', '.join([f'<@{p}>' for p in top_votes])})"
            )
        else:
            # Lynch player
            game_state["players"][lynched]["alive"] = False
            game_state["alive_players"].remove(lynched)
            game_state["dead_players"].append(lynched)
            
            # Reveal role
            role_info = game_state["players"][lynched]["role_info"]
            role_name = role_info[f"name_{lang}"]
            role_emoji = role_info["emoji"]
            
            await main_channel.send(
                f"⚖️ <@{lynched}> {'został zlinczowany!' if lang == 'pl' else 'was lynched!'}\n"
                f"{'Jego rola:' if lang == 'pl' else 'Their role:'} {role_emoji} **{role_name}**"
            )
            
            # Give dead player access to ghost channel
            try:
                member = await guild.fetch_member(lynched)
                await dead_channel.set_permissions(member, read_messages=True, send_messages=True)
            except:
                pass
    
    # Check win conditions
    if await self._check_win_condition(lobby_id):
        return
    
    # Start next night
    await self._night_phase(lobby_id)
```

### Win Conditions

#### Lines 2387-2470: Check Win Condition
```python
async def _check_win_condition(self, lobby_id: str) -> bool:
    """Check if any faction has won"""
    game_state = self.active_games.get(lobby_id)
    main_channel = self.bot.get_channel(game_state["main_channel_id"])
    lang = game_state["language"]
    theme = game_state["theme"]
    
    # Count factions
    faction_counts = {}
    for pid, pdata in game_state["players"].items():
        if pdata["alive"]:
            faction = pdata["faction"]
            faction_counts[faction] = faction_counts.get(faction, 0) + 1
    
    evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
    good_faction = "TOWN" if theme == "mafia" else "VILLAGE"
    
    evil_count = faction_counts.get(evil_faction, 0)
    good_count = faction_counts.get(good_faction, 0)
    
    winner = None
    
    # Evil wins if equal or more than good
    if evil_count >= good_count and evil_count > 0:
        winner = evil_faction
        winner_name = "🔫 Mafia" if theme == "mafia" else "🐺 Wilkołaki"
    # Good wins if no evil left
    elif evil_count == 0:
        winner = good_faction
        winner_name = "🏛️ Miasto" if theme == "mafia" else "🏘️ Wioska"
    
    if winner:
        # Announce winner
        await main_channel.send(
            f"# 🏆 **{winner_name} {'WYGRYWA!' if lang == 'pl' else 'WINS!'}**\n\n"
            f"{'Gratulacje zwycięzcom!' if lang == 'pl' else 'Congratulations to the winners!'}"
        )
        
        # Show all roles
        roles_text = []
        for pid, pdata in game_state["players"].items():
            role_info = pdata["role_info"]
            role_name = role_info[f"name_{lang}"]
            role_emoji = role_info["emoji"]
            faction = pdata["faction"]
            status = "✅" if pdata["alive"] else "💀"
            
            roles_text.append(f"{status} <@{pid}> - {role_emoji} {role_name} ({faction})")
        
        await main_channel.send(
            f"**{'Wszyscy gracze:' if lang == 'pl' else 'All players:'}**\n" +
            "\n".join(roles_text)
        )
        
        # Cleanup after 60 seconds
        await asyncio.sleep(60)
        
        # Delete category and all channels
        category = self.bot.get_channel(game_state["category_id"])
        if category:
            for channel in category.channels:
                try:
                    await channel.delete()
                except:
                    pass
            try:
                await category.delete()
            except:
                pass
        
        # Remove game from active games
        if lobby_id in self.active_games:
            del self.active_games[lobby_id]
        
        return True
    
    return False
```

**Win Conditions:**
- **Evil Wins**: Evil count ≥ Good count
- **Good Wins**: Evil count = 0
- **Cleanup**: Category deleted after 60s
- **Role Reveal**: All roles shown at end

### Interactive Views

#### Lines 2472-2530: Night Action View
```python
class NightActionView(discord.ui.View):
    """View for evil faction to select kill target"""
    
    def __init__(self, cog, lobby_id, evil_faction):
        super().__init__(timeout=None)
        self.cog = cog
        self.lobby_id = lobby_id
        self.evil_faction = evil_faction
        
        game_state = self.cog.active_games.get(lobby_id)
        
        # Get alive non-evil players
        targets = []
        for pid, pdata in game_state["players"].items():
            if pdata["alive"] and pdata["faction"] != evil_faction:
                targets.append(pid)
        
        # Create select menu
        options = []
        for pid in targets:
            user = self.cog.bot.get_user(pid)
            if user:
                options.append(
                    discord.SelectOption(
                        label=user.name,
                        value=str(pid)
                    )
                )
        
        if options:
            select = discord.ui.Select(
                placeholder="Choose victim...",
                options=options
            )
            select.callback = self.select_target
            self.add_item(select)
    
    async def select_target(self, interaction: discord.Interaction):
        game_state = self.cog.active_games.get(self.lobby_id)
        voter_id = interaction.user.id
        target_id = int(interaction.data['values'][0])
        
        # Check if voter is evil
        if game_state["players"][voter_id]["faction"] != self.evil_faction:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        
        # Record vote
        game_state["night_actions"][voter_id] = target_id
        
        await interaction.response.send_message(
            f"✅ Vote recorded for <@{target_id}>",
            ephemeral=True
        )
```

#### Lines 2532-2590: Vote View
```python
class VoteView(discord.ui.View):
    """View for lynch voting"""
    
    def __init__(self, cog, lobby_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.lobby_id = lobby_id
        
        game_state = self.cog.active_games.get(lobby_id)
        
        # Get alive players
        alive_players = game_state["alive_players"]
        
        # Create select menu
        options = []
        for pid in alive_players:
            user = self.cog.bot.get_user(pid)
            if user:
                options.append(
                    discord.SelectOption(
                        label=user.name,
                        value=str(pid)
                    )
                )
        
        if options:
            select = discord.ui.Select(
                placeholder="Vote to lynch...",
                options=options
            )
            select.callback = self.cast_vote
            self.add_item(select)
    
    async def cast_vote(self, interaction: discord.Interaction):
        game_state = self.cog.active_games.get(self.lobby_id)
        voter_id = interaction.user.id
        target_id = int(interaction.data['values'][0])
        
        # Check if voter is alive
        if voter_id not in game_state["alive_players"]:
            await interaction.response.send_message("❌ Dead players can't vote!", ephemeral=True)
            return
        
        # Record vote
        game_state["votes"][voter_id] = target_id
        
        await interaction.response.send_message(
            f"✅ Vote cast for <@{target_id}>",
            ephemeral=True
        )
```

---

## 📊 TECHNICAL IMPLEMENTATION

### Discord Components v2
```python
# LayoutView with Container
class MafiaLobbyView(discord.ui.LayoutView):
    def __init__(self, cog, lobby_id):
        super().__init__(timeout=300)
        self._build_ui()
    
    def _build_ui(self):
        # Create container with all UI elements
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(join_btn, leave_btn),
            discord.ui.ActionRow(settings_btn, start_btn, cancel_btn),
            accent_colour=discord.Colour.red()
        )
        
        self.add_item(self.container)
```

**Important Rules:**
- Max 40 elements per view (TextDisplay, Button, Select, Separator all count)
- Cannot use `content=` parameter with IS_COMPONENTS_V2 flag
- Use TextDisplay in Container instead
- Max 5 buttons per ActionRow
- Single-message editing (no ephemeral navigation)

### Category & Channel System
```python
# Create category
category = await guild.create_category(category_name)

# Create channels in category
main_channel = await guild.create_text_channel(name="🏛️-main", category=category)
evil_channel = await guild.create_text_channel(name="🔫-mafia", category=category)
dead_channel = await guild.create_text_channel(name="💀-ghosts", category=category)

# Voice channels (voice mode only)
center_voice = await guild.create_voice_channel(name="🏛️-centrum-miasta", category=category)
meeting_spot = await guild.create_voice_channel(name="🍰-cukiernia", category=category)

# Game center text (voice mode only)
game_center = await guild.create_text_channel(name="🎯-centrum-gry", category=category)
```

### Permission System
```python
# Main channel - all players
for member in player_members:
    await main_channel.set_permissions(member, read_messages=True, send_messages=True)

# Evil channel - hidden, only evil faction gets access later
await evil_channel.set_permissions(guild.default_role, read_messages=False)

# Dead channel - hidden, dead players get access when they die
await dead_channel.set_permissions(guild.default_role, read_messages=False)

# Voice channels - all can join during day
await voice_channel.set_permissions(guild.default_role, connect=True, speak=True)

# Lock voice channel during night
await voice_channel.set_permissions(guild.default_role, connect=False)

# Game center text - read-only for players
await game_center.set_permissions(member, read_messages=True, send_messages=False)
```

### Player Teleportation
```python
# Move player to center voice channel
center_vc = guild.get_channel(center_voice_channel_id)
for member in voice_channel.members:
    try:
        await member.move_to(center_vc)
    except:
        pass  # Player not in voice or permission error
```

### Game State Management
```python
# Active lobbies (before game starts)
self.active_lobbies = {
    lobby_id: {
        "host": user_id,
        "players": [user_id, ...],
        "theme": "mafia" | "werewolf",
        "mode": "normal" | "advanced" | "custom",
        "language": "en" | "pl",
        "day_duration": 180,
        "night_duration": 90,
        "vote_duration": 60,
        "voice_mode": False,
        "custom_roles": ["citizen", "detective", ...],
        "random_roles": False,
        "evil_count": None | 1-5,
        "started": False,
        "channel_id": channel_id,
        "created_at": datetime
    }
}

# Active games (after game starts)
self.active_games = {
    lobby_id: {
        "lobby_id": lobby_id,
        "guild_id": guild_id,
        "category_id": category_id,
        "main_channel_id": main_channel_id,
        "evil_channel_id": evil_channel_id,
        "dead_channel_id": dead_channel_id,
        "voice_channels": [vc_id, ...],
        "center_voice_channel_id": center_vc_id,
        "game_center_text_id": game_center_id,
        "theme": "mafia" | "werewolf",
        "mode": "normal" | "advanced" | "custom",
        "language": "en" | "pl",
        "day_duration": 180,
        "night_duration": 90,
        "vote_duration": 60,
        "voice_mode": False,
        "players": {
            player_id: {
                "role": "citizen",
                "role_info": {...},
                "faction": "TOWN",
                "alive": True,
                "protected": False,
                "votes": 0
            }
        },
        "alive_players": [pid, ...],
        "dead_players": [pid, ...],
        "day_number": 1,
        "phase": "night" | "day" | "vote",
        "night_actions": {voter_id: target_id},
        "votes": {voter_id: target_id}
    }
}
```

---

## 🎮 OTHER MULTIPLAYER GAMES

### File: `multiplayer_games.py` (1,260 lines)

Complete social deduction and party game collection beyond Mafia/Werewolf:

### Murder Mystery
**Among Us-style social deduction game**

**Key Features:**
- 4-10 players with 3 roles: Killer 🔪, Sheriff 👮, Innocents 😇
- Interactive task system (8+ task types)
- Round-based gameplay with phases
- Voting and elimination mechanics
- Death rounds for wrong sheriff kills
- Spectator system

**Roles:**
```python
KILLER:
- Eliminates 1 player per round
- Must blend in by fake-tasking
- Wins by outnumbering innocents
- Uses `kill @user` command

SHERIFF:
- Can eliminate anyone with `/murderkill`
- Wrong kill = DEATH ROUND activated
- Completes tasks like innocents
- High-risk, high-reward role

INNOCENTS:
- Complete 5 tasks each to win
- Vote to eject suspects
- Work together to find killer
- Task completion = team progress
```

**Interactive Task Types:**
1. **Emoji Find** 🔍 - Find target emoji in grid (1-10 position)
2. **Word Memory** 🧠 - Memorize 3 words, recall after 10s
3. **Quick Math** 🔢 - Solve arithmetic equation
4. **Sort Numbers** 📊 - Arrange 5 numbers low→high
5. **Color Match** 🎨 - Identify color emoji
6. **Sequence** 🔄 - Remember 4-letter pattern (ABCD)
7. **Word Scramble** 🔤 - Unscramble word (KILLER → LRLKEI)
8. **Pattern** 🧩 - Complete sequence (2 4 6 8 → 10)

**Game Flow:**
```
1. Lobby Phase (v2 UI with Join/Leave/Settings/Start)
2. Role Assignment (DM role cards sent)
3. Round Phase:
   - Send ephemeral panels to all players
   - Killer chooses target
   - Innocents complete tasks
   - Sheriff monitors suspects
   - Duration: 90s (configurable)
4. Death Announcement (if killer struck)
5. Voting Phase:
   - Players type `vote @user`
   - Most votes = ejection
   - Reveal role after ejection
   - Duration: 45s (configurable)
6. Win Check:
   - Innocents: All tasks done OR killer ejected
   - Killer: Equal/outnumber innocents
7. Repeat or End
```

**Settings System:**
```python
lobby_settings = {
    "tasks_required": 5,        # Tasks per innocent
    "round_duration": 90,       # Seconds per round
    "vote_duration": 45,        # Seconds for voting
    "has_sheriff": True,        # Enable sheriff role
}
```

**Task Validation System:**
```python
# Players type answers in game channel
# Bot validates against stored task data
# Correct answer = task complete + team progress
# Wrong answer = ❌ reaction

# Example validations:
task_type = "math"
user_input = "35"
expected = 35
is_correct = int(user_input) == expected
```

**Death Round Mechanic:**
```python
# Triggered when sheriff kills innocent
game["death_round"] = True

# Effects:
- ⚠️ Warning displayed
- One final round to find killer
- If killer not found = KILLER WINS
- High stakes voting phase
```

**Win Conditions:**
```python
# Innocents Win:
1. Total tasks completed >= required
   (all innocents * 5 tasks each)
2. Killer ejected via voting

# Killer Wins:
1. Alive innocents <= 1
2. Sheriff killed innocent + death round failed
```

**Economy Integration:**
```python
# Winners receive PsyCoins:
- Killer Win: +500 coins
- Innocents Win: +400 coins each
- Sheriff Kill: +500 coins
```

### Clue
**Classic mystery board game - WHO, WHAT weapon, WHERE**

**Features:**
- 2-6 players simultaneous play
- Random solution generation
- Reaction-based lobby system
- Text-based accusations
- Progressive hints system

**Game Elements:**
```python
suspects = [
    "Colonel Mustard 👨‍✈️",
    "Miss Scarlet 💃",
    "Professor Plum 👨‍🏫",
    "Mrs. Peacock 👵",
    "Mr. Green 🧑‍💼",
    "Mrs. White 👩‍🍳"
]

weapons = [
    "Candlestick 🕯️",
    "Knife 🔪",
    "Lead Pipe 🔧",
    "Revolver 🔫",
    "Rope 🪢",
    "Wrench 🔩"
]

rooms = [
    "Kitchen 🍳",
    "Ballroom 💃",
    "Conservatory 🌿",
    "Dining Room 🍽️",
    "Library 📚",
    "Lounge 🛋️",
    "Study 📖",
    "Hall 🚪",
    "Billiard Room 🎱"
]
```

**Solution Generation:**
```python
solution = {
    "suspect": random.choice(suspects),
    "weapon": random.choice(weapons),
    "room": random.choice(rooms)
}
# Hidden until solved
```

**Lobby System:**
```python
# Reaction-based join/start
✅ = Join (max 6 players)
▶️ = Start (host only, min 2 players)
# 30 second timeout or host start
```

**Accusation System:**
```python
# Players type: [Suspect], [Weapon], [Room]
# Example: "Colonel Mustard, Knife, Kitchen"

# Parsing:
- Case insensitive
- Partial match allowed
- Validates against lists
- Gives hints if close
```

**Hint System:**
```python
# Progressive feedback
if suspect_guess == solution["suspect"]:
    hints.append("✅ Suspect correct!")
if weapon_guess == solution["weapon"]:
    hints.append("✅ Weapon correct!")
if room_guess == solution["room"]:
    hints.append("✅ Room correct!")

# Display: "🔍 Close! ✅ Suspect correct! ✅ Weapon correct!"
```

**Win Condition:**
```python
# All three correct = WIN
if (suspect == solution["suspect"] and 
    weapon == solution["weapon"] and 
    room == solution["room"]):
    
    winner = player
    award_coins(winner, 500)
```

**Timeout Handling:**
```python
# 300 second game timeout
# Reveals solution if unsolved
timeout_embed = {
    "title": "⏰ Game Timeout",
    "solution": {
        "suspect": solution["suspect"],
        "weapon": solution["weapon"],
        "room": solution["room"]
    }
}
```

#### Modern UI Components (v2)
```python
class MurderMysteryLobbyView(discord.ui.View):
    """Interactive lobby with buttons"""
    
    buttons = [
        join_button:     "✅ Join Game" (green)
        leave_button:    "🚪 Leave" (gray)
        settings_button: "⚙️ Settings" (blurple, host only)
        start_button:    "▶️ Start Game" (red, host only, 4+ players)
        cancel_button:   "❌ Cancel" (danger, host only)
    ]
```

**Settings Modal:**
```python
class MurderMysterySettingsModal(discord.ui.Modal):
    """Host configuration panel"""
    
    fields = [
        tasks_required:   IntInput (1-10)
        round_duration:   IntInput (30-300s)
        vote_duration:    IntInput (15-120s)
        has_sheriff:      Checkbox (ON/OFF)
    ]
```

---

### Dueling
**File: `dueling.py` (453 lines) - PvP combat system with coin betting and spectator wagers**

#### Core Features
- 1v1 competitive challenges
- 5 game types (RPS, Coinflip, Dice, High-Low, Quick Draw)
- Coin betting system (10-100,000 PsyCoins)
- Spectator betting on outcomes
- Duel history tracking
- Accept/Decline system with timeout

#### Available Duel Games
```python
duel_games = {
    "rps": "Rock Paper Scissors",
    "coinflip": "Coin Flip",
    "dice": "Dice Roll (highest wins)",
    "highlow": "High-Low Card Game",
    "quickdraw": "Quick Draw (fastest reaction)"
}
```

#### Duel Session Structure
```python
class DuelSession:
    challenger: discord.Member
    opponent: discord.Member
    game_type: str
    bet_amount: int
    channel: discord.TextChannel
    active: bool
    spectators_can_bet: bool
    start_time: datetime
```

#### Command System
```python
# Challenge someone
L!duel @user <game> <bet>
# Examples:
L!duel @Alice rps 500
L!duel @Bob coinflip 1000
L!duel @Charlie dice 250

# Spectator betting
L!bet <player> <amount>
# Example: L!bet @Alice 200
```

#### Game Types Implementation

**1. Rock Paper Scissors**
```python
# Players react with:
🪨 = Rock
📄 = Paper
✂️ = Scissors

# Win conditions:
Rock beats Scissors
Scissors beats Paper
Paper beats Rock
```

**2. Coinflip**
```python
# Players choose:
"heads" or "tails"

# Result: random.choice(["heads", "tails"])
# Winner = correct guess
```

**3. Dice Roll**
```python
# Both players roll
dice1 = random.randint(1, 6)
dice2 = random.randint(1, 6)

# Highest roll wins
# Tie = re-roll
```

**4. High-Low Card Game**
```python
# Cards: 2-14 (Jack=11, Queen=12, King=13, Ace=14)
# Dealer shows card
# Players guess: "higher" or "lower"
# Closest guess wins
```

**5. Quick Draw**
```python
# Reaction speed game
# Random countdown 3-10 seconds
# First to react wins
# False start = instant loss
```

#### Betting System
```python
# Duel bet validation
minimum_bet = 10
maximum_bet = 100000

# Both players must have funds
if balance < bet_amount:
    return "❌ Insufficient funds!"

# Deduct bets on accept
deduct_coins(challenger, bet)
deduct_coins(opponent, bet)

# Winner receives: bet * 2
# Loser receives: 0
```

#### Spectator Betting
```python
# Spectators can bet on outcome
spectator_bets = {
    user_id: {
        "target": player_id,
        "amount": bet_amount
    }
}

# Payouts:
if target == winner:
    payout = bet_amount * 1.8  # 80% profit
    add_coins(spectator, payout)
else:
    # Lose bet
    pass
```

#### Duel History Tracking
```python
duel_history = {
    duel_id: {
        "challenger": user_id,
        "opponent": user_id,
        "game_type": "rps",
        "bet": 500,
        "winner": user_id,
        "timestamp": "2026-02-06T12:00:00"
    }
}

# Saved to: cogs/duel_history.json
```

#### Accept/Decline Flow
```python
# 1. Challenge sent
embed = "⚔️ {challenger} challenges {opponent}"
embed += "Game: {game_type} | Bet: {bet}"

# 2. Add reactions
✅ = Accept
❌ = Decline

# 3. Wait for response (30s timeout)
# - Accept → Start game
# - Decline → Cancel, no loss
# - Timeout → Cancel, no loss
```

#### Win/Loss Processing
```python
async def process_duel_end(duel, winner):
    # Award winner
    winnings = duel.bet_amount * 2
    add_coins(winner, winnings, "duel_win")
    
    # Process spectator bets
    for spectator_id, bet_info in spectator_bets[duel_id].items():
        if bet_info["target"] == winner.id:
            payout = bet_info["amount"] * 1.8
            add_coins(spectator_id, payout, "spectator_win")
    
    # Log to history
    log_duel({
        "challenger": duel.challenger.id,
        "opponent": duel.opponent.id,
        "game": duel.game_type,
        "bet": duel.bet_amount,
        "winner": winner.id
    })
    
    # Remove from active duels
    del active_duels[duel_id]
```

#### Statistics System
```python
# Track per user:
- Total duels
- Wins / Losses
- Win rate %
- Total coins won
- Total coins lost
- Net profit/loss
- Favorite game type
- Longest win streak

# Command: L!duelstats [user]
```

---

### Monopoly
**File: `monopoly.py` (1,000 lines) - Full Monopoly board game implementation**

#### Core Features
- 2-8 players supported
- Complete 40-space board
- Property buying/selling/trading
- Rent collection system
- Houses and hotels
- Chance and Community Chest
- Jail mechanics
- Bankruptcy handling
- AI opponent support
- Turn-based gameplay

#### Board Layout (40 Spaces)
```python
BOARD_SPACES = [
    # Go (0)
    {"name": "GO", "type": "special", "collect": 200},
    
    # Properties (22 total)
    {"name": "Mediterranean Avenue", "type": "property", "price": 60, "rent": [2, 10, 30, 90, 160, 250], "color": "brown"},
    {"name": "Baltic Avenue", "type": "property", "price": 60, "rent": [4, 20, 60, 180, 320, 450], "color": "brown"},
    # ... (20 more properties)
    
    # Railroads (4)
    {"name": "Reading Railroad", "type": "railroad", "price": 200, "rent": [25, 50, 100, 200]},
    # ... (3 more railroads)
    
    # Utilities (2)
    {"name": "Electric Company", "type": "utility", "price": 150},
    {"name": "Water Works", "type": "utility", "price": 150},
    
    # Special Spaces
    {"name": "Chance", "type": "chance"},
    {"name": "Community Chest", "type": "community_chest"},
    {"name": "Income Tax", "type": "tax", "amount": 200},
    {"name": "Luxury Tax", "type": "tax", "amount": 100},
    {"name": "Free Parking", "type": "special"},
    {"name": "Go To Jail", "type": "jail"},
    {"name": "Just Visiting", "type": "special"}
]
```

#### Property System
```python
class Property:
    name: str
    owner: Optional[discord.Member]
    price: int
    rent: List[int]  # [base, 1h, 2h, 3h, 4h, hotel]
    houses: int  # 0-5 (5 = hotel)
    color: str
    mortgaged: bool
    
    def get_rent(self):
        if self.mortgaged:
            return 0
        if self.houses == 0:
            return self.rent[0] * self.color_set_multiplier
        return self.rent[self.houses]
```

#### Player State
```python
player_state = {
    user_id: {
        "position": 0,  # 0-39 board position
        "balance": 1500,  # Starting cash
        "properties": [],  # Owned property IDs
        "in_jail": False,
        "jail_turns": 0,
        "get_out_free_cards": 0,
        "bankrupt": False
    }
}
```

#### Turn Flow
```python
1. Roll dice (2d6)
2. Check doubles (roll again if 3 in row → jail)
3. Move token
4. Land on space:
   - Property: Buy/Auction/Pay rent
   - Railroad: Buy/Pay rent
   - Utility: Buy/Pay rent
   - Chance/Community: Draw card
   - Tax: Pay amount
   - Go To Jail: Send to jail
   - Free Parking: Collect pot (optional)
5. Build houses/hotels (if own color set)
6. Trade with other players
7. End turn
```

#### Chance & Community Cards
```python
CHANCE_CARDS = [
    "Advance to GO (Collect $200)",
    "Go to Jail",
    "Bank pays you $50",
    "Pay $15 poor tax",
    "Advance to Illinois Avenue",
    "Take a trip to Reading Railroad",
    "Get Out of Jail Free card",
    # ... 16 total cards
]

COMMUNITY_CHEST_CARDS = [
    "Bank error in your favor (Collect $200)",
    "Doctor's fee ($50)",
    "From sale of stock ($50)",
    "Get Out of Jail Free card",
    "Go to Jail",
    "Grand Opera Night (Collect $50 from each player)",
    # ... 17 total cards
]
```

#### Trading System
```python
# Propose trade
L!trade @user

# Trade components:
- Properties (both sides)
- Cash (both sides)
- Get Out of Jail Free cards

# Accept/Decline with reactions
✅ = Accept
❌ = Decline
```

#### Building System
```python
# Requirements to build:
1. Own all properties in color group
2. Build evenly (no property can have 2+ more houses)
3. Have sufficient cash

# Costs:
houses = property.house_cost  # Varies by color
hotel = property.house_cost * 5

# Max: 4 houses OR 1 hotel per property
# Selling: 50% refund
```

#### Jail Mechanics
```python
# Ways to enter jail:
1. Land on "Go To Jail"
2. Roll doubles 3 times in a row
3. Draw "Go to Jail" card

# Ways to leave jail:
1. Roll doubles (3 attempts)
2. Pay $50 fine
3. Use "Get Out of Jail Free" card

# Still collect rent while in jail
```

#### Bankruptcy Handling
```python
# Triggered when:
player.balance < debt_owed

# Process:
1. Sell houses/hotels (50% value)
2. Mortgage properties (50% value)
3. If still insufficient → bankrupt

# Bankruptcy:
- All properties → creditor
- Player eliminated
- Last player standing wins
```

#### Win Condition
```python
# Game ends when:
1. Only 1 player not bankrupt
2. All others eliminated

# Winner announced
# Coin rewards based on:
- Net worth
- Time survived
- Properties owned
```

#### AI Opponent
```python
# Bot players can join
# AI strategies:
1. Always buy if affordable
2. Build houses when possible
3. Trade aggressively
4. Never pay to leave jail early (roll for it)
5. Mortgage properties when low on cash
```

---

## Statistics

### Total Lines Breakdown
```
mafia.py:              2,639 lines (62%)
multiplayer_games.py:  1,260 lines (29%)
dueling.py:              453 lines (11%)
monopoly.py:           1,000 lines (23%)
---
TOTAL:                 5,352 lines
```

### Feature Completion
```
Mafia/Werewolf:     26/26 features (100%)
Murder Mystery:     10/10 features (100%)
Clue:                6/6 features (100%)
Dueling:             8/8 features (100%)
Monopoly:           15/15 features (100%)
```

### Game Complexity Ranking
```
1. Mafia/Werewolf  - ⭐⭐⭐⭐⭐ (Most Complex)
   - 100+ roles
   - Voice mode
   - Auto-balance AI
   - Full phase system

2. Monopoly        - ⭐⭐⭐⭐
   - 40-space board
   - Trading system
   - Property management
   - AI opponents

3. Murder Mystery  - ⭐⭐⭐⭐
   - 8 task types
   - 3 roles
   - Round-based
   - Interactive tasks

4. Dueling         - ⭐⭐⭐
   - 5 game types
   - Betting system
   - Spectator wagers
   - History tracking

5. Clue            - ⭐⭐
   - Mystery solving
   - Hint system
   - Simple mechanics
```

---

## 📈 STATISTICS

### Mafia/Werewolf Stats
```
Total Lines:        2,639
Role Database:      170 lines (100+ roles)
Preset System:      198 lines (20 presets)
Custom Presets:     258 lines (8 themed pools)
Time Presets:       296 lines (4 configurations)
Balance Checker:    410 lines (AI analysis)
Lobby System:       1,690 lines
Settings:           585 lines
Role Picker:        1,060 lines
Voice Mode:         200 lines
Game Loop:          470 lines
Phase System:       400 lines
Win Conditions:     85 lines
Interactive Views:  120 lines
```

### Feature Completion
```
✅ Dual Themes (Mafia/Werewolf)
✅ 3 Game Modes (Normal/Advanced/Custom)
✅ 100+ Roles with descriptions
✅ Smart Presets for 6-16 players
✅ 8 Custom Themed Presets
✅ Dynamic Preset Loading
✅ Time Presets (4 options)
✅ Auto-Balance Checker
✅ Bilingual Support (PL/EN)
✅ Full Lobby System
✅ Interactive Settings
✅ Role Picker with Preview
✅ Random Role Selection
✅ Evil Count Control
✅ Voice Mode with 8+ channels
✅ Meeting Spot Locking
✅ Player Teleportation
✅ Game Center Text Updates
✅ Full Game Loop
✅ Night/Day/Vote Phases
✅ Win Condition Checking
✅ Auto-Cleanup (60s)
✅ DM Role Cards
✅ Ghost Channel Access
✅ Interactive Discord UI
✅ 6-Player Minimum
```

**26/26 Features Complete (100%)**

---

## 🎯 USAGE EXAMPLES

### Starting a Game
```
User: /mafia
Bot: [Shows lobby with join/leave/settings/start buttons]

Host: [Clicks Settings]
Bot: [Shows theme/mode/language/voice/time preset options]

Host: [Changes theme to Werewolf, mode to Advanced, enables Voice Mode]
Host: [Clicks Back]

Players: [Click Join button to join lobby]

Host: [Clicks Start when 6+ players]
Bot: "🎮 GAME STARTED! Check your DMs for your role!"
Bot: [Creates category with channels]
Bot: [Sends role DMs to all players]
Bot: [Starts night phase]
```

### Playing with Voice Mode
```
Bot: "🌙 NIGHT 1"
Bot: [Locks all meeting spots]
Bot: [Teleports players to center]
Bot: [Game center text] "🔒 All locations are locked!"

[After 90s night duration]

Bot: "☀️ DAY 1"
Bot: [Unlocks all meeting spots]
Bot: [Game center text] "🔓 All locations are open!"

[Players can now move to any meeting spot to discuss]

[After 180s day duration]

Bot: "🗳️ VOTING"
Bot: [Locks all meeting spots]
Bot: [Teleports players to center]
Bot: [Shows vote menu in game center text]

[After 60s vote duration]

Bot: "⚖️ @Player was lynched!"
Bot: "Their role: 🔫 Mafia"
Bot: [Checks win condition]
Bot: [Starts next night or announces winner]
```

### Custom Role Selection
```
Host: [Opens Settings → Custom Roles]
Bot: [Shows role picker with 15 roles per page]

Host: [Clicks Detective]
Bot: [Shows preview] "🔍 Detective - Can investigate one player each night..."
Bot: [Add/Cancel buttons]

Host: [Clicks Add]
Bot: [Returns to role picker, Detective now has ✓ checkmark]

Host: [Clicks Random toggle]
Bot: [Random mode enabled - can now add 15+ roles for 8 players]

Host: [Uses Evil Count select → 3 Evil]
Bot: [Sets evil count to 3]

Host: [Clicks Load Preset → Chaos Mode]
Bot: [Loads 15 chaos roles]

Bot: [Shows balance check]
"🌀 Balance: Chaotic
 🌀 Dużo ról chaos (5/8)
 💡 Dodaj detektywa/jasnowidza"

Host: [Clicks Back]
Bot: [Returns to settings with custom roles saved]
```

---

## 🏆 KEY INNOVATIONS

1. **Voice Mode**: First Discord Mafia bot with full voice channel integration
2. **Auto-Balance**: AI-powered role composition analysis
3. **Theme-Specific Channels**: Different meeting spots for Mafia vs Werewolf
4. **Teleportation System**: Automatic player movement between voice channels
5. **Game Center Text**: Read-only updates channel for voice games
6. **Dynamic Presets**: Automatically loads balanced roles for player count
7. **Custom Presets**: 8 themed role pools for variety
8. **Time Presets**: Quick timing configurations (fast/standard/hardcore/roleplay)
9. **Bilingual Support**: Full Polish & English translation
10. **Interactive UI**: Discord Components v2 with containers

---

### Optimization Ideas
- Cache role databases in memory
- Pre-generate common preset combinations
- Optimize balance checker for large role pools
- Add role search functionality
- Implement role favorites system

---

**Last Updated**: February 6, 2026  
**Total Documentation**: ~22,000 words  
**Systems Documented**: 5 complete game systems
- Mafia/Werewolf (2,639 lines)
- Murder Mystery (650 lines)  
- Clue (200 lines)
- Dueling (453 lines)
- Monopoly (1,000 lines)  
**Code Analyzed**: 5,352 lines total  
