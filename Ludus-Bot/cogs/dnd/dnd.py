"""
INFINITY ADVENTURE - Interdimensional Narrative System
A massive narrative RPG where players traverse 9 dimensions as eternal beings.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import random
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

# Import Gate 1 Fantasy system
try:
    from .dnd_gate1_fantasy import (
        Gate1WorldState, 
        get_random_entry_point, 
        get_gate1_scene,
        GATE1_ENTRY_POINTS
    )
    GATE1_AVAILABLE = True
except ImportError:
    GATE1_AVAILABLE = False
    print("[WARNING] Gate 1 Fantasy system not found")


# ==================== TRANSLATIONS ====================

TRANSLATIONS = {
    "en": {
        # Language Selection
        "lang_title": "🌌 INFINITY ADVENTURE",
        "lang_desc": "Choose your language / Wybierz język",
        "lang_english": "English",
        "lang_polish": "Polski",
        
        # Tutorial
        "tutorial_title": "📜 Welcome to Infinity Adventure",
        "tutorial_text": """**You are not a hero. Not yet.**

You are a **BODILESS ENTITY** - consciousness without form, standing at the **Cape of All Existence** (Przylądek Wszechrzeczy).

Before you stand **NINE GATES**, each leading to a different dimension with different rules, dangers, and destinies.

**HOW IT WORKS:**
• Choose a Gate to enter a dimension
• Adopt a physical form and new identity
• Make choices that shape entire worlds
• **Death is not the end** - you return to the Cape
• Your actions create **permanent consequences**
• Worlds remember what you've done

**KEY MECHANICS:**
🎲 **Dice Rolls** - Your fate is tested by D20 rolls
💀 **Death & Rebirth** - Return to Cape, choose new life
🌍 **World States** - Dimensions evolve based on your actions
👁️ **Influence** - Your cosmic weight grows with impact
💾 **Auto-Save** - Progress saved after major choices

The **Four Guardians** watch from the shadows.
Reality itself will bend to your will... or break under it.

**Are you ready to begin your infinite journey?**""",
        "tutorial_ready": "✨ I'm Ready",
        "tutorial_explain": "📖 Explain More",
        
        # Cape of All Existence
        "cape_title": "🌌 CAPE OF ALL EXISTENCE",
        "cape_desc": """You stand at the center of all reality.

**CAPE OF ALL EXISTENCE** - the first place beyond dimensions. Here, time does not flow, death cannot reach, and every possibility exists simultaneously.

Before you, nine towering gates pulse with cosmic energy.
Each leads to a different universe, a different fate.

The air hums with ancient power.
You feel the gaze of the **Four Guardians** upon you, though they remain unseen.

**Which gate calls to you?**""",
        "cape_influence": "Cosmic Influence",
        "cape_deaths": "Past Lives",
        "cape_worlds_changed": "Worlds Altered",
        "gate_select_placeholder": "🚪 Choose a Gate to Enter",
        "load_save_btn": "📂 Load Save",
        
        # Gate Names
        "gate_1": "Sword & Blood",
        "gate_2": "Steam & Gears", 
        "gate_3": "Ash & War",
        "gate_4": "Neon & Steel",
        "gate_5": "Silence & Ruin",
        "gate_6": "Stardust & Void",
        "gate_7": "Empire & Throne",
        "gate_8": "Dream & Myth",
        "gate_9": "Abyss & Truth",
        
        # Gate Descriptions (short)
        "gate_1_short": "Fantasy realm of heroes, dragons, and destiny",
        "gate_2_short": "Steampunk world of invention and progress",
        "gate_3_short": "Dieselpunk war-torn nightmare",
        "gate_4_short": "Cyberpunk dystopia of control",
        "gate_5_short": "Post-apocalyptic wasteland",
        "gate_6_short": "Sci-fi exploration of cosmos",
        "gate_7_short": "Space opera of galactic empires",
        "gate_8_short": "Surreal realm where logic fails",
        "gate_9_short": "Cosmic horror beyond comprehension",
        
        # Common UI
        "btn_back": "◀️ Back",
        "btn_confirm": "✅ Confirm",
        "btn_cancel": "❌ Cancel",
        "btn_continue": "▶️ Continue",
        "btn_stats": "📊 Stats",
        "btn_save": "💾 Save Game",
        "btn_exit": "🚪 Save & Exit",
        "btn_quit": "🚪 Quit to Cape",
        
        # Character Creation
        "char_title": "👤 Manifest Your Form",
        "char_desc": "You must take physical form to exist in this dimension.\n\nWho will you become?",
        "char_name": "Enter Name",
        "char_class": "Choose Path",
        "char_created": "You feel your consciousness crystallize into flesh and bone.\n\n**{name} the {char_class}** opens their eyes for the first time.",
        
        # Stats
        "stat_health": "❤️ Health",
        "stat_mana": "💙 Mana",
        "stat_stamina": "💚 Stamina",
        "stat_strength": "💪 Strength",
        "stat_intelligence": "🧠 Intelligence",
        "stat_charisma": "✨ Charisma",
        "stat_luck": "🍀 Luck",
        
        # Save/Load
        "save_success": "💾 **Game Saved**\nYour journey has been recorded.",
        "save_failed": "❌ Failed to save game.",
        "exit_success": "💾 **Game Saved & Closed**\nYour journey has been recorded. Use /dnd to continue.",
        "load_success": "✅ **Game Loaded**\nWelcome back, wanderer.",
        "no_save": "❌ No saved game found.",
        
        # Anti-cheat messages (trying to load after death)
        "cheat_death_1": "💀 **Did you think you could cheat Death itself?**\n\nFoolish mortal. The void remembers.",
        "cheat_death_2": "💀 **Trying again?**\n\nDeath does not forget. Your {deaths} past lives are gone forever.",
        "cheat_death_3": "💀 **Really? After {deaths} deaths?**\n\nYou never learn. The Guardians mock your futile attempts.",
        
        # Party Mode
        "party_gathering": "🎭 Gathering Party",
        "party_desc": "**{leader}** is gathering a party for an adventure!\n\n**Current Members:** {count}\n{members}\n\nClick 'Join Party' to join the adventure!\n\n**Note:** Each member will create their own character. You'll travel together as a group.",
        "party_join": "✅ Join Party",
        "party_start": "🚀 Start Adventure",
        "party_cancel": "❌ Cancel",
        "party_joined": "✅ You joined the party!",
        "party_already_joined": "⚠️ You're already in this party!",
        "party_started": "🌌 **The party steps through the veil...**",
        "party_turn": "🎯 {name}'s Turn",
        "party_waiting": "⏳ Waiting for {name}...",
        "party_members_short": "Party Members",
        
        # Death
        "death_title": "💀 YOU HAVE DIED",
        "death_text": """The world fades to black.

But you do not end.

You feel your consciousness **torn from your body**, pulled through the fabric of reality itself.

Memories of {name} linger like smoke...

You return to the **Cape of All Existence**.

The Guardians whisper: *"Death is but a doorway."*

**What will you do now?**""",
        "death_return": "Return to Same Body",
        "death_new_life": "✨ Begin New Life",
        "death_change_gate": "🚪 Choose Different Gate",
    },
    
    "pl": {
        # Language Selection
        "lang_title": "🌌 NIESKOŃCZONA PRZYGODA",
        "lang_desc": "Wybierz język / Choose your language",
        "lang_english": "English",
        "lang_polish": "Polski",
        
        # Tutorial
        "tutorial_title": "📜 Witaj w Nieskończonej Przygodzie",
        "tutorial_text": """**Nie jesteś bohaterem. Jeszcze nie.**

Jesteś **BEZCIELESNĄ ISTOTĄ** - świadomością bez formy, stojącą na **Przylądku Wszechrzeczy** (Cape of All Existence).

Przed tobą **DZIEWIĘĆ BRAM**, każda prowadząca do innego wymiaru z innymi zasadami, niebezpieczeństwami i przeznaczeniami.

**JAK TO DZIAŁA:**
• Wybierz Bramę aby wejść do wymiaru
• Przyjmij fizyczną formę i nową tożsamość
• Podejmuj decyzje kształtujące całe światy
• **Śmierć to nie koniec** - wracasz na Przylądek
• Twoje czyny tworzą **trwałe konsekwencje**
• Światy pamiętają co zrobiłeś

**KLUCZOWE MECHANIKI:**
🎲 **Rzuty Kostką** - Twój los testowany jest rzutami K20
💀 **Śmierć i Odrodzenie** - Powrót na Przylądek, wybór nowego życia
🌍 **Stany Światów** - Wymiary ewoluują na podstawie twoich działań
👁️ **Wpływ** - Twoja kosmiczna waga rośnie z wpływem
💾 **Auto-Zapis** - Postęp zapisany po ważnych wyborach

**Czterej Strażnicy** obserwują z cieni.
Sama rzeczywistość ugnie się pod twoją wolą... lub załamie.

**Czy jesteś gotowy rozpocząć nieskończoną podróż?**""",
        "tutorial_ready": "✨ Jestem Gotowy",
        "tutorial_explain": "📖 Wyjaśnij Więcej",
        
        # Cape of All Existence
        "cape_title": "🌌 PRZYLĄDEK WSZECHRZECZY",
        "cape_desc": """Stoisz w centrum całej rzeczywistości.

**PRZYLĄDEK WSZECHRZECZY** - pierwsze miejsce poza wymiarami. Tutaj czas nie płynie, śmierć nie sięga, a każda możliwość istnieje jednocześnie.

Przed tobą dziewięć monumentalnych bram pulsuje kosmiczną energią.
Każda prowadzi do innego wszechświata, innego przeznaczenia.

Powietrze wibruje starożytną mocą.
Czujesz spojrzenie **Czterech Strażników**, choć pozostają niewidzialni.

**Która brama cię wzywa?**""",
        "cape_influence": "Wpływ Kosmiczny",
        "cape_deaths": "Przeszłe Życia",
        "cape_worlds_changed": "Zmienione Światy",
        "gate_select_placeholder": "🚪 Wybierz Bramę do Wejścia",
        "load_save_btn": "📂 Wczytaj Zapis",
        
        # Gate Names
        "gate_1": "Miecz i Krew",
        "gate_2": "Para i Zębatki",
        "gate_3": "Popiół i Wojna",
        "gate_4": "Neon i Stal",
        "gate_5": "Cisza i Ruina",
        "gate_6": "Gwiezdny Pył",
        "gate_7": "Imperium i Tron",
        "gate_8": "Sen i Mit",
        "gate_9": "Otchłań i Prawda",
        
        # Gate Descriptions
        "gate_1_short": "Fantasy królestwo bohaterów, smoków i przeznaczenia",
        "gate_2_short": "Steampunkowy świat wynalazków i postępu",
        "gate_3_short": "Dieselpunkowy koszmar wojny",
        "gate_4_short": "Cyberpunkowa dysrepia kontroli",
        "gate_5_short": "Postapokaliptyczna pustka",
        "gate_6_short": "Sci-fi eksploracja kosmosu",
        "gate_7_short": "Space opera galaktycznych imperiów",
        "gate_8_short": "Surrealistyczny wymiar gdzie logika zawodzi",
        "gate_9_short": "Kosmiczny horror poza zrozumieniem",
        
        # Common UI
        "btn_back": "◀️ Wstecz",
        "btn_confirm": "✅ Potwierdź",
        "btn_cancel": "❌ Anuluj",
        "btn_continue": "▶️ Dalej",
        "btn_stats": "📊 Statystyki",
        "btn_save": "💾 Zapisz Grę",
        "btn_exit": "🚪 Zapisz i Wyjdź",
        "btn_quit": "🚪 Wyjdź na Przylądek",
        
        # Character Creation
        "char_title": "👤 Przyjmij Formę",
        "char_desc": "Musisz przyjąć fizyczną formę aby istnieć w tym wymiarze.\n\nKim się staniesz?",
        "char_name": "Wpisz Imię",
        "char_class": "Wybierz Ścieżkę",
        "char_created": "Czujesz jak twoja świadomość krystalizuje się w ciało i kości.\n\n**{name} - {char_class}** otwiera oczy po raz pierwszy.",
        
        # Stats
        "stat_health": "❤️ Zdrowie",
        "stat_mana": "💙 Mana",
        "stat_stamina": "💚 Wytrzymałość",
        "stat_strength": "💪 Siła",
        "stat_intelligence": "🧠 Inteligencja",
        "stat_charisma": "✨ Charyzma",
        "stat_luck": "🍀 Szczęście",
        
        # Save/Load
        "save_success": "💾 **Gra Zapisana**\nTwoja podróż została zanotowana.",
        "save_failed": "❌ Nie udało się zapisać gry.",
        "exit_success": "💾 **Gra Zapisana i Zamknięta**\nTwoja podróż została zanotowana. Użyj /dnd aby kontynuować.",
        "load_success": "✅ **Gra Wczytana**\nWitaj z powrotem, wędrowcze.",
        "no_save": "❌ Nie znaleziono zapisanej gry.",
        
        # Anti-cheat messages (trying to load after death)
        "cheat_death_1": "💀 **Myślałeś że oszukasz samą Śmierć?**\n\nGłupiec. Otchłań pamięta.",
        "cheat_death_2": "💀 **Znowu próbujesz?**\n\nŚmierć nie zapomina. Twoje {deaths} przeszłe życia przepadły na zawsze.",
        "cheat_death_3": "💀 **Naprawdę? Po {deaths} śmierciach?**\n\nNigdy się nie nauczysz. Strażnicy szydzą z twoich daremnych prób.",
        
        # Party Mode
        "party_gathering": "🎭 Zbieranie Drużyny",
        "party_desc": "**{leader}** zbiera drużynę na przygodę!\n\n**Obecni Członkowie:** {count}\n{members}\n\nKliknij 'Dołącz do Drużyny' aby przyłączyć się do przygody!\n\n**Uwaga:** Każdy członek stworzy swoją postać. Będziecie podróżować razem jako grupa.",
        "party_join": "✅ Dołącz do Drużyny",
        "party_start": "🚀 Rozpocznij Przygodę",
        "party_cancel": "❌ Anuluj",
        "party_joined": "✅ Dołączyłeś do drużyny!",
        "party_already_joined": "⚠️ Jesteś już w tej drużynie!",
        "party_started": "🌌 **Drużyna przekracza zasłonę...**",
        "party_turn": "🎯 Tura: {name}",
        "party_waiting": "⏳ Czekamy na {name}...",
        "party_members_short": "Członkowie Drużyny",
        
        # Death
        "death_title": "💀 ZGINĄŁEŚ",
        "death_text": """Świat gaśnie w ciemności.

Ale ty się nie kończysz.

Czujesz jak twoja świadomość **zostaje wyrwana z ciała**, przeciągnięta przez tkankę samej rzeczywistości.

Wspomnienia {name} pozostają jak dym...

Wracasz na **Przylądek Wszechrzeczy**.

Strażnicy szepczą: *"Śmierć to tylko drzwi."*

**Co teraz zrobisz?**""",
        "death_return": "Wróć do Tego Samego Ciała",
        "death_new_life": "✨ Rozpocznij Nowe Życie",
        "death_change_gate": "🚪 Wybierz Inną Bramę",
    }
}

def t(lang: str, key: str, **kwargs) -> str:
    """Get translation with optional formatting"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


# ==================== DATA STRUCTURES ====================

class PlayerData:
    """Stores all player progression data"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.language = "en"
        
        # Tutorial
        self.tutorial_completed = False
        
        # Cosmic Stats
        self.cosmic_influence = 0  # Hidden stat - grows with world impact
        self.total_deaths = 0
        self.worlds_changed = 0
        self.dimensions_visited = set()
        
        # Current Life
        self.current_gate = None  # 1-9 or None if at Cape
        self.current_dimension_state = {}
        self.character = None  # CurrentCharacter object
        
        # Party tracking (for stats)
        self.party_adventures = 0  # How many party adventures completed
        
        # World States - persistent across deaths
        # Each dimension has its own state object
        self.dimension_states = {i: {} for i in range(1, 10)}
        
        # Entry point tracking - gdzie ostatnio wylądowałeś
        self.last_entry_points = {}  # {gate_id: entry_point_id}
        
        # Story Progress
        self.current_scene = None
        self.story_history = []  # List of scene IDs visited
        self.choices_made = []  # List of major choices
        
        # Relationships - NPCs remember you
        self.npc_relationships = {}  # {npc_id: relationship_value}
        self.npc_memories = {}  # {npc_id: [memory_ids]}
        
        # Artefacts & Items
        self.artefacts = []  # Special items that transcend death
        self.inventory = {}
        
        # Save metadata
        self.last_save = None
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to saveable dictionary"""
        return {
            "user_id": self.user_id,
            "language": self.language,
            "tutorial_completed": self.tutorial_completed,
            "cosmic_influence": self.cosmic_influence,
            "total_deaths": self.total_deaths,
            "worlds_changed": self.worlds_changed,
            "dimensions_visited": list(self.dimensions_visited),
            "party_adventures": self.party_adventures,
            "current_gate": self.current_gate,
            "current_dimension_state": self.current_dimension_state,
            "character": self.character.to_dict() if self.character else None,
            "dimension_states": self.dimension_states,
            "last_entry_points": self.last_entry_points,
            "current_scene": self.current_scene,
            "story_history": self.story_history,
            "choices_made": self.choices_made,
            "npc_relationships": self.npc_relationships,
            "npc_memories": self.npc_memories,
            "artefacts": self.artefacts,
            "inventory": self.inventory,
            "last_save": self.last_save,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Load from dictionary"""
        player = cls(data["user_id"])
        player.language = data.get("language", "en")
        player.tutorial_completed = data.get("tutorial_completed", False)
        player.cosmic_influence = data.get("cosmic_influence", 0)
        player.total_deaths = data.get("total_deaths", 0)
        player.worlds_changed = data.get("worlds_changed", 0)
        player.dimensions_visited = set(data.get("dimensions_visited", []))
        player.party_adventures = data.get("party_adventures", 0)
        player.current_gate = data.get("current_gate")
        player.current_dimension_state = data.get("current_dimension_state", {})
        
        char_data = data.get("character")
        if char_data:
            player.character = CurrentCharacter.from_dict(char_data)
        
        player.dimension_states = data.get("dimension_states", {i: {} for i in range(1, 10)})
        player.last_entry_points = data.get("last_entry_points", {})
        player.current_scene = data.get("current_scene")
        player.story_history = data.get("story_history", [])
        player.choices_made = data.get("choices_made", [])
        player.npc_relationships = data.get("npc_relationships", {})
        player.npc_memories = data.get("npc_memories", {})
        player.artefacts = data.get("artefacts", [])
        player.inventory = data.get("inventory", {})
        player.last_save = data.get("last_save")
        player.created_at = data.get("created_at", datetime.now().isoformat())
        
        return player


class CurrentCharacter:
    """Current incarnation/body"""
    
    def __init__(self, name: str, char_class: str, gate: int):
        self.name = name
        self.char_class = char_class
        self.gate = gate
        
        # Combat Stats
        self.max_health = 100
        self.health = 100
        self.max_mana = 50
        self.mana = 50
        self.max_stamina = 100
        self.stamina = 100
        
        # Base Attributes (affect rolls)
        self.strength = 10
        self.intelligence = 10
        self.charisma = 10
        self.luck = 10
        
        # Experience
        self.level = 1
        self.experience = 0
        
        # Conditions
        self.conditions = []  # ["bleeding", "blessed", etc]
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "char_class": self.char_class,
            "gate": self.gate,
            "max_health": self.max_health,
            "health": self.health,
            "max_mana": self.max_mana,
            "mana": self.mana,
            "max_stamina": self.max_stamina,
            "stamina": self.stamina,
            "strength": self.strength,
            "intelligence": self.intelligence,
            "charisma": self.charisma,
            "luck": self.luck,
            "level": self.level,
            "experience": self.experience,
            "conditions": self.conditions,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        char = cls(data["name"], data["char_class"], data["gate"])
        char.max_health = data.get("max_health", 100)
        char.health = data.get("health", 100)
        char.max_mana = data.get("max_mana", 50)
        char.mana = data.get("mana", 50)
        char.max_stamina = data.get("max_stamina", 100)
        char.stamina = data.get("stamina", 100)
        char.strength = data.get("strength", 10)
        char.intelligence = data.get("intelligence", 10)
        char.charisma = data.get("charisma", 10)
        char.luck = data.get("luck", 10)
        char.level = data.get("level", 1)
        char.experience = data.get("experience", 0)
        char.conditions = data.get("conditions", [])
        return char
    
    def get_stats_display(self, lang: str) -> str:
        """Get formatted stats string"""
        health_bar = self._make_bar(self.health, self.max_health, 10)
        mana_bar = self._make_bar(self.mana, self.max_mana, 10)
        stamina_bar = self._make_bar(self.stamina, self.max_stamina, 10)
        
        return f"""**{self.name}** - {self.char_class} (Lvl {self.level})

{t(lang, 'stat_health')}: {health_bar} {self.health}/{self.max_health}
{t(lang, 'stat_mana')}: {mana_bar} {self.mana}/{self.max_mana}
{t(lang, 'stat_stamina')}: {stamina_bar} {self.stamina}/{self.max_stamina}

{t(lang, 'stat_strength')}: {self.strength} | {t(lang, 'stat_intelligence')}: {self.intelligence}
{t(lang, 'stat_charisma')}: {self.charisma} | {t(lang, 'stat_luck')}: {self.luck}"""
    
    def _make_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """Create a progress bar"""
        filled = int((current / maximum) * length) if maximum > 0 else 0
        return "█" * filled + "░" * (length - filled)


# ==================== SAVE/LOAD SYSTEM ====================

SAVE_DIR = "./data/saves"
SAVE_FILE = os.path.join(SAVE_DIR, "infinity_adventure.json")

def ensure_save_dir():
    """Create saves directory if it doesn't exist"""
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

def save_player(player: PlayerData) -> bool:
    """Save player data to disk"""
    try:
        ensure_save_dir()
        
        # Load existing data
        all_data = {}
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        
        # Update player's data
        player.last_save = datetime.now().isoformat()
        all_data[str(player.user_id)] = player.to_dict()
        
        # Save back
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[Infinity] Save error: {e}")
        return False

def load_player(user_id: int) -> Optional[PlayerData]:
    """Load player data from disk"""
    try:
        if not os.path.exists(SAVE_FILE):
            return None
        
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        user_data = all_data.get(str(user_id))
        if not user_data:
            return None
        
        return PlayerData.from_dict(user_data)
    except Exception as e:
        print(f"[Infinity] Load error: {e}")
        return None


# ==================== GATE CONFIGURATIONS ====================

GATE_CONFIGS = {
    1: {
        "name_key": "gate_1",
        "desc_key": "gate_1_short",
        "emoji": "⚔️",
        "ruler": "IGNAR",
        "theme": "fantasy",
        "color": 0xC41E3A,
        "classes": {
            "en": ["Warrior", "Mage", "Rogue", "Cleric", "Ranger", "Paladin"],
            "pl": ["Wojownik", "Mag", "Łotrzyk", "Kleryk", "Łowca", "Paladyn"]
        },
    },
    2: {
        "name_key": "gate_2",
        "desc_key": "gate_2_short",
        "emoji": "⚙️",
        "ruler": "AETRION",
        "theme": "steampunk",
        "color": 0x8B4513,
        "classes": {
            "en": ["Inventor", "Engineer", "Airship Captain", "Alchemist", "Mechanist"],
            "pl": ["Wynalazca", "Inżynier", "Kapitan Sterowca", "Alchemik", "Mechanik"]
        },
    },
    3: {
        "name_key": "gate_3",
        "desc_key": "gate_3_short",
        "emoji": "☠️",
        "ruler": "NIHARA",
        "theme": "dieselpunk_war",
        "color": 0x2F4F4F,
        "classes": {
            "en": ["Soldier", "Medic", "Sniper", "Saboteur", "Commander"],
            "pl": ["Żołnierz", "Medyk", "Snajper", "Sabotażysta", "Dowódca"]
        },
    },
    4: {
        "name_key": "gate_4",
        "desc_key": "gate_4_short",
        "emoji": "🌃",
        "ruler": "PSYCHON",
        "theme": "cyberpunk",
        "color": 0xFF006E,
        "classes": {
            "en": ["Netrunner", "Street Samurai", "Corpo", "Fixer", "Techie"],
            "pl": ["Netrunner", "Uliczny Samuraj", "Korporacjonista", "Pośrednik", "Technik"]
        },
    },
    5: {
        "name_key": "gate_5",
        "desc_key": "gate_5_short",
        "emoji": "🏚️",
        "ruler": "MORTIS",
        "theme": "post_apocalypse",
        "color": 0x556B2F,
        "classes": {
            "en": ["Scavenger", "Survivor", "Raider", "Medic", "Trader"],
            "pl": ["Zbieracz", "Ocalały", "Najeźdźca", "Medyk", "Handlarz"]
        },
    },
    6: {
        "name_key": "gate_6",
        "desc_key": "gate_6_short",
        "emoji": "✨",
        "ruler": "ORIGEN",
        "theme": "sci_fi",
        "color": 0x4169E1,
        "classes": {
            "en": ["Explorer", "Scientist", "Pilot", "Xenobiologist", "AI Specialist"],
            "pl": ["Odkrywca", "Naukowiec", "Pilot", "Ksenobiolog", "Specjalista AI"]
        },
    },
    7: {
        "name_key": "gate_7",
        "desc_key": "gate_7_short",
        "emoji": "👑",
        "ruler": "FINIS",
        "theme": "space_opera",
        "color": 0xFFD700,
        "classes": {
            "en": ["Imperial Officer", "Rebel Leader", "Diplomat", "Admiral", "Spy"],
            "pl": ["Oficer Imperialny", "Przywódca Rebelii", "Dyplomata", "Admirał", "Szpieg"]
        },
    },
    8: {
        "name_key": "gate_8",
        "desc_key": "gate_8_short",
        "emoji": "🎭",
        "ruler": "VITA",
        "theme": "surreal",
        "color": 0x9370DB,
        "classes": {
            "en": ["Dreamer", "Reality Bender", "Artist", "Shapeshifter", "Oracle"],
            "pl": ["Marzyciel", "Zginacz Rzeczywistości", "Artysta", "Zmiennokształtny", "Wyrocznia"]
        },
    },
    9: {
        "name_key": "gate_9",
        "desc_key": "gate_9_short",
        "emoji": "🌀",
        "ruler": "VOIDREX",
        "theme": "cosmic_horror",
        "color": 0x000000,
        "classes": {
            "en": ["Cultist", "Investigator", "Touched One", "Witness", "Void Walker"],
            "pl": ["Kultista", "Śledczy", "Dotknięty", "Świadek", "Wędrowiec Otchłani"]
        },
        "unstable": True,  # Can be closed by Guardians
    },
}


# ==================== MAIN VIEW CLASS ====================

class InfinityView(discord.ui.LayoutView):
    """Main interface for Infinity Adventure"""
    
    def __init__(self, player: PlayerData, cog, timeout: float = 5400, is_new_session: bool = False):
        super().__init__(timeout=timeout)  # 90 minutes
        self.player = player
        self.cog = cog
        self.message: Optional[discord.Message] = None
        self.is_new_session = is_new_session  # True when /dnd is called
        
        # State management
        self.current_state = self._determine_state()
        
        # Party mode
        self.party_mode = False
        self.party_members = []  # [user_ids]
        self.party_leader = None
        self.party_characters = {}  # {user_id: CurrentCharacter}
        self.party_players = {}  # {user_id: PlayerData}
        
        # Turn-based action system
        self.current_actor = None  # user_id of player whose turn it is
        self.turn_order = []  # List of user_ids in turn order
        self.waiting_for_action = False
        
        # Anti-cheat tracking
        self.just_died = False  # Set to True when player dies
    
    def _determine_state(self) -> str:
        """Determine what screen to show based on player data"""
        # For new sessions:
        # 1. ALWAYS show language selection first
        # 2. Mode selection (Solo/Party)
        # 3. Tutorial/Cape
        
        if self.is_new_session:
            return "language_select"
        
        if not self.player.language:
            return "language_select"
        if not self.player.tutorial_completed:
            return "tutorial"
        if self.player.current_gate is None:
            return "cape"
        if self.player.character is None:
            return "character_creation"
        if self.player.current_scene:
            return "story"
        return "cape"
    
    async def build_ui(self):
        """Build UI based on current state"""
        if self.current_state == "mode_select":
            await self._build_mode_select()
        elif self.current_state == "party_gathering":
            await self._build_party_gathering()
        elif self.current_state == "language_select":
            await self._build_language_select()
        elif self.current_state == "tutorial":
            await self._build_tutorial()
        elif self.current_state == "cape":
            await self._build_cape()
        elif self.current_state == "character_creation":
            await self._build_character_creation()
        elif self.current_state == "story":
            await self._build_story()
    
    # ==================== MODE SELECTION (Solo/Party) ====================
    
    async def _build_mode_select(self):
        """Build Solo/Party mode selection screen"""
        lang = self.player.language
        
        # Build description
        if lang == "en":
            title = "🌌 INFINITY ADVENTURE"
            description = """**Will you venture alone or gather a party?**

**Solo** - Play alone, forge your own path through dimensions
• Your choices alone shape reality
• Deep personal narrative
• Full control over your destiny

**Party** - Play with friends, adventure together
• Each player creates their own character
• Travel together as a group
• NPCs see you as a company of travelers
• Turn-based action system
"""
        else:  # pl
            title = "🌌 NIESKOŃCZONA PRZYGODA"
            description = """**Wyruszysz sam czy zbierzesz drużynę?**

**Solo** - Graj sam, wykuj własną ścieżkę przez wymiary
• Twoje wybory kształtują rzeczywistość
• Głęboka osobista narracja
• Pełna kontrola nad swoim przeznaczeniem

**Party** - Graj z przyjaciółmi, wyruszcie razem
• Każdy gracz tworzy swoją postać
• Podróżujecie razem jako grupa
• NPC widzą was jako kompanię podróżników
• System akcji oparty na turach
"""
        
        container_items = [
            discord.ui.TextDisplay(content=f"""# {title}

{description}"""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Mode selection buttons
        solo_label = "👤 Solo" if lang == "en" else "👤 Solo"
        party_label = "👥 Party" if lang == "en" else "👥 Drużyna"
        
        solo_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=solo_label,
            custom_id="mode_solo"
        )
        party_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label=party_label,
            custom_id="mode_party"
        )
        
        solo_btn.callback = lambda i: self._select_mode(i, False)
        party_btn.callback = lambda i: self._select_mode(i, True)
        
        container_items.append(discord.ui.ActionRow(solo_btn, party_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.add_item(self.container)
    
    async def _select_mode(self, interaction: discord.Interaction, is_party: bool):
        """Handle mode selection"""
        self.party_mode = is_party
        self.is_new_session = False  # No longer new session
        
        if is_party:
            # Go to party gathering screen
            self.party_leader = interaction.user.id
            self.party_members = [interaction.user.id]
            self.current_state = "party_gathering"
        else:
            # Solo mode - continue to tutorial or cape
            self.party_members = [interaction.user.id]
            self.current_state = "tutorial" if not self.player.tutorial_completed else "cape"
        
        await self._refresh_ui(interaction)
    
    # ==================== PARTY GATHERING ====================
    
    async def _build_party_gathering(self):
        """Build party gathering screen where players can join"""
        lang = self.player.language
        
        # Build member list
        member_mentions = [f"<@{uid}>" for uid in self.party_members]
        members_text = "\n".join([f"{i+1}. {mention}" for i, mention in enumerate(member_mentions)])
        
        leader_mention = f"<@{self.party_leader}>"
        
        desc = t(lang, "party_desc", leader=leader_mention, count=len(self.party_members), members=members_text)
        
        container_items = [
            discord.ui.TextDisplay(content=f"""# {t(lang, 'party_gathering')}

{desc}"""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Join button (for other players)
        join_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label=t(lang, "party_join"),
            custom_id="party_join"
        )
        join_btn.callback = self._join_party
        
        # Start button (only for leader, requires at least 2 players)
        can_start = len(self.party_members) >= 1  # Can start solo too
        start_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=t(lang, "party_start"),
            custom_id="party_start",
            disabled=False  # Leader can always start
        )
        start_btn.callback = self._start_party_adventure
        
        # Cancel button (only for leader)
        cancel_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label=t(lang, "party_cancel"),
            custom_id="party_cancel"
        )
        cancel_btn.callback = self._cancel_party
        
        container_items.extend([
            discord.ui.ActionRow(join_btn),
            discord.ui.ActionRow(start_btn, cancel_btn),
        ])
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.clear_items()
        self.add_item(self.container)
    
    async def _join_party(self, interaction: discord.Interaction):
        """Handle player joining party"""
        user_id = interaction.user.id
        lang = self.player.language
        
        # Check if already in party
        if user_id in self.party_members:
            await interaction.response.send_message(
                t(lang, "party_already_joined"),
                ephemeral=True,
                delete_after=3
            )
            return
        
        # Add to party
        self.party_members.append(user_id)
        
        # Load or create PlayerData for this member
        member_data = load_player(user_id)
        if not member_data:
            member_data = PlayerData(user_id)
            member_data.language = self.player.language  # Use party language
        self.party_players[user_id] = member_data
        
        # Register this user in active sessions too
        self.cog.active_sessions[user_id] = self
        
        # Show confirmation
        await interaction.response.send_message(
            t(lang, "party_joined"),
            ephemeral=True,
            delete_after=3
        )
        
        # Refresh view to show updated member list
        await self._refresh_ui_for_party(interaction)
    
    async def _start_party_adventure(self, interaction: discord.Interaction):
        """Start the adventure with the gathered party"""
        lang = self.player.language
        
        # Only leader can start
        if interaction.user.id != self.party_leader:
            await interaction.response.send_message(
                "❌ Only the party leader can start the adventure!",
                ephemeral=True,
                delete_after=3
            )
            return
        
        # Initialize party players dict
        for member_id in self.party_members:
            if member_id not in self.party_players:
                member_data = load_player(member_id)
                if not member_data:
                    member_data = PlayerData(member_id)
                    member_data.language = self.player.language
                self.party_players[member_id] = member_data
        
        # Show starting message
        await interaction.response.send_message(
            t(lang, "party_started"),
            ephemeral=True,
            delete_after=3
        )
        
        # Move to language selection or tutorial
        if not self.player.tutorial_completed:
            self.current_state = "tutorial"
        else:
            self.current_state = "cape"
        
        await self._refresh_ui_for_party(interaction)
    
    async def _cancel_party(self, interaction: discord.Interaction):
        """Cancel party gathering"""
        # Only leader can cancel
        if interaction.user.id != self.party_leader:
            await interaction.response.send_message(
                "❌ Only the party leader can cancel!",
                ephemeral=True,
                delete_after=3
            )
            return
        
        # Remove all members from active sessions except leader
        for member_id in self.party_members:
            if member_id != self.party_leader and member_id in self.cog.active_sessions:
                del self.cog.active_sessions[member_id]
        
        # Reset to solo mode
        self.party_mode = False
        self.party_members = [self.party_leader]
        
        # Go back to mode select
        self.is_new_session = True
        self.current_state = "mode_select"
        
        await self._refresh_ui(interaction)
    
    async def _refresh_ui_for_party(self, interaction: discord.Interaction):
        """Refresh UI for all party members after party changes"""
        self.clear_items()
        await self.build_ui()
        
        if self.message:
            await self.message.edit(view=self)
    
    # ==================== LANGUAGE SELECTION ====================
    
    async def _build_language_select(self):
        """Build language selection screen"""
        container_items = [
            discord.ui.TextDisplay(content=f"""# 🌌 INFINITY ADVENTURE

**Choose your language / Wybierz język**

This choice will determine the language for your entire adventure.
Ten wybór określi język całej twojej przygody."""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Language buttons
        en_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="🇬🇧 English",
            custom_id="lang_en"
        )
        pl_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="🇵🇱 Polski",
            custom_id="lang_pl"
        )
        
        en_btn.callback = lambda i: self._select_language(i, "en")
        pl_btn.callback = lambda i: self._select_language(i, "pl")
        
        container_items.append(discord.ui.ActionRow(en_btn, pl_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.add_item(self.container)
    
    async def _select_language(self, interaction: discord.Interaction, lang: str):
        """Handle language selection"""
        self.player.language = lang
        save_player(self.player)
        
        # After language selection, go to mode selection if new session
        if self.is_new_session:
            self.current_state = "mode_select"
        else:
            # Existing player choosing language - go to tutorial or cape
            self.current_state = "tutorial" if not self.player.tutorial_completed else "cape"
        
        await self._refresh_ui(interaction)
    
    # ==================== TUTORIAL ====================
    
    async def _build_tutorial(self):
        """Build tutorial screen"""
        lang = self.player.language
        
        container_items = [
            discord.ui.TextDisplay(content=f"""# {t(lang, 'tutorial_title')}

{t(lang, 'tutorial_text')}"""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Ready button
        ready_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            label=t(lang, 'tutorial_ready'),
            custom_id="tutorial_ready"
        )
        ready_btn.callback = self._tutorial_complete
        
        container_items.append(discord.ui.ActionRow(ready_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.clear_items()
        self.add_item(self.container)
    
    async def _tutorial_complete(self, interaction: discord.Interaction):
        """Mark tutorial as complete and move to Cape"""
        self.player.tutorial_completed = True
        self.current_state = "cape"
        save_player(self.player)
        
        await self._refresh_ui(interaction)
    
    # ==================== CAPE OF ALL EXISTENCE ====================
    
    async def _build_cape(self):
        """Build Cape/Gate selection screen"""
        lang = self.player.language
        
        # Build stats line
        stats_line = f"{t(lang, 'cape_influence')}: **{self.player.cosmic_influence}** | "
        stats_line += f"{t(lang, 'cape_deaths')}: **{self.player.total_deaths}** | "
        stats_line += f"{t(lang, 'cape_worlds_changed')}: **{self.player.worlds_changed}**"
        
        container_items = [
            discord.ui.TextDisplay(content=f"""# {t(lang, 'cape_title')}

{t(lang, 'cape_desc')}

{stats_line}"""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Gate selection dropdown
        gate_options = []
        for gate_id in range(1, 10):
            config = GATE_CONFIGS[gate_id]
            
            # Check if Gate 9 is locked
            if gate_id == 9 and config.get("unstable"):
                # Gate 9 can be unavailable based on multiverse stability
                if self.player.cosmic_influence < 1000:  # Placeholder condition
                    continue
            
            gate_options.append(
                discord.SelectOption(
                    label=f"{config['emoji']} {t(lang, config['name_key'])}",
                    value=f"gate_{gate_id}",
                    description=t(lang, config['desc_key'])[:100],
                )
            )
        
        gate_select = discord.ui.Select(
            placeholder=t(lang, 'gate_select_placeholder'),
            options=gate_options,
            custom_id="gate_select"
        )
        gate_select.callback = self._select_gate
        
        container_items.extend([
            discord.ui.ActionRow(gate_select),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ])
        
        # Additional buttons
        stats_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=t(lang, 'btn_stats'),
            custom_id="view_stats"
        )
        stats_btn.callback = self._view_full_stats
        
        # Load button - only way to continue existing adventure
        load_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=t(lang, 'load_save_btn'),
            custom_id="load_save_cape"
        )
        load_btn.callback = self._load_save_at_cape
        
        container_items.append(discord.ui.ActionRow(stats_btn, load_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x5865F2),
        )
        
        self.clear_items()
        self.add_item(self.container)
    
    async def _select_gate(self, interaction: discord.Interaction, values: List[str] = None):
        """Handle gate selection"""
        if values is None:
            values = interaction.data.get("values", [])
        
        if not values:
            return
        
        # Reset anti-cheat flag - player is starting new adventure legitimately
        self.just_died = False
        
        gate_id = int(values[0].replace("gate_", ""))
        self.player.current_gate = gate_id
        self.player.dimensions_visited.add(gate_id)
        self.player.character = None  # Clear old character
        self.player.current_scene = None
        self.current_state = "character_creation"
        save_player(self.player)
        
        await self._refresh_ui(interaction)
    
    async def _view_full_stats(self, interaction: discord.Interaction):
        """Show detailed stats in ephemeral message"""
        lang = self.player.language
        
        stats_text = f"""# 📊 **Your Cosmic Profile**

**{t(lang, 'cape_influence')}:** {self.player.cosmic_influence}
**{t(lang, 'cape_deaths')}:** {self.player.total_deaths}
**{t(lang, 'cape_worlds_changed')}:** {self.player.worlds_changed}

**Dimensions Visited:** {len(self.player.dimensions_visited)}/9

**Known NPCs:** {len(self.player.npc_relationships)}
**Artefacts:** {len(self.player.artefacts)}

**Current Character:** {self.player.character.name if self.player.character else "None"}
"""
        
        await interaction.response.send_message(stats_text, ephemeral=True, delete_after=60)
    
    async def _load_save_at_cape(self, interaction: discord.Interaction):
        """Load saved game from Cape screen - transports to world if character exists"""
        user_id = interaction.user.id
        lang = self.player.language
        
        # ANTI-CHEAT: Check if player just died and is trying to load old save
        if self.just_died:
            # Reset flag
            self.just_died = False
            
            # Show sarcastic message based on death count
            deaths = self.player.total_deaths
            
            if deaths <= 2:
                msg = t(lang, 'cheat_death_1')
            elif deaths <= 5:
                msg = t(lang, 'cheat_death_2', deaths=deaths)
            else:
                msg = t(lang, 'cheat_death_3', deaths=deaths)
            
            await interaction.response.send_message(msg, ephemeral=True, delete_after=10)
            return
        
        # Load player data
        loaded_player = load_player(user_id)
        if not loaded_player:
            msg = t(lang, 'no_save')
            await interaction.response.send_message(msg, ephemeral=True, delete_after=5)
            return
        
        # Replace current player data
        self.player = loaded_player
        
        # Reset anti-cheat flag - successful legitimate load
        self.just_died = False
        
        msg = t(lang, 'load_success')
        await interaction.response.send_message(msg, ephemeral=True, delete_after=3)
        
        # Determine where to go based on loaded data
        if self.player.character and self.player.current_gate and self.player.current_scene:
            # Has active adventure - transport to story
            self.current_state = "story"
        elif self.player.current_gate:
            # Has gate but no character - go to character creation
            self.current_state = "character_creation"
        else:
            # No active adventure - stay at Cape
            self.current_state = "cape"
        
        await self._refresh_ui_after_response(interaction)
    
    # ==================== CHARACTER CREATION ====================
    
    async def _build_character_creation(self):
        """Build character creation screen"""
        lang = self.player.language
        gate_id = self.player.current_gate
        config = GATE_CONFIGS[gate_id]
        
        # Check how many party members still need to create characters
        if self.party_mode:
            pending_members = []
            ready_members = []
            for member_id in self.party_members:
                if member_id in self.party_characters:
                    char = self.party_characters[member_id]
                    ready_members.append(f"✅ <@{member_id}> - {char.name} ({char.char_class})")
                else:
                    pending_members.append(f"⏳ <@{member_id}>")
            
            party_status = "\n".join(ready_members + pending_members)
            party_info = f"\n\n**{t(lang, 'party_members_short')}:**\n{party_status}\n"
        else:
            party_info = ""
        
        container_items = [
            discord.ui.TextDisplay(content=f"""# {config['emoji']} {t(lang, config['name_key'])}

{t(lang, 'char_title')}

{t(lang, 'char_desc')}{party_info}

**Available Paths:**"""),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Class selection
        class_options = []
        classes_list = config["classes"].get(lang, config["classes"]["en"])
        for char_class in classes_list:
            class_options.append(
                discord.SelectOption(
                    label=char_class,
                    value=char_class,
                )
            )
        
        class_select = discord.ui.Select(
            placeholder=t(lang, 'char_class'),
            options=class_options,
            custom_id="class_select"
        )
        class_select.callback = self._select_class
        
        container_items.extend([
            discord.ui.ActionRow(class_select),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ])
        
        # Back button only
        back_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=t(lang, 'btn_back'),
            custom_id="back_to_cape"
        )
        back_btn.callback = self._back_to_cape
        
        container_items.append(discord.ui.ActionRow(back_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(config["color"]),
        )
        
        self.clear_items()
        self.add_item(self.container)
    
    async def _select_class(self, interaction: discord.Interaction, values: List[str] = None):
        """Handle class selection - show name input modal"""
        if values is None:
            values = interaction.data.get("values", [])
        
        if not values:
            return
        
        char_class = values[0]
        lang = self.player.language
        
        # Show modal for name input
        modal = CharacterNameModal(self, char_class, lang)
        await interaction.response.send_modal(modal)
    
    async def _create_character(self, interaction: discord.Interaction, name: str, char_class: str):
        """Finalize character creation"""
        user_id = interaction.user.id
        lang = self.player.language
        gate_id = self.player.current_gate
        
        # Create character for this user
        new_char = CurrentCharacter(name, char_class, gate_id)
        
        if self.party_mode:
            # Store in party characters
            self.party_characters[user_id] = new_char
            
            # Also store in player data for this member
            if user_id in self.party_players:
                self.party_players[user_id].character = new_char
                self.party_players[user_id].current_gate = gate_id
                save_player(self.party_players[user_id])
            
            # Check if all members have created characters
            if len(self.party_characters) >= len(self.party_members):
                # Everyone ready - start adventure
                # Use dynamic entry point system
                self.player.current_scene = self._get_entry_scene_id(gate_id, is_party=True)
                self.current_state = "story"
                
                # Set up turn order
                self.turn_order = list(self.party_members)
                self.current_actor = self.turn_order[0]
            else:
                # Still waiting for others
                creation_msg = t(lang, 'char_created', name=name, char_class=char_class)
                await interaction.response.send_message(creation_msg, ephemeral=True, delete_after=5)
                await self._refresh_ui_after_modal(interaction)
                return
        else:
            # Solo mode
            self.player.character = new_char
            # Use dynamic entry point system - różne miejsca spawnu!
            self.player.current_scene = self._get_entry_scene_id(gate_id, is_party=False)
            self.current_state = "story"
            save_player(self.player)
        
        # Show creation message
        creation_msg = t(lang, 'char_created', name=name, char_class=char_class)
        await interaction.response.send_message(creation_msg, ephemeral=True, delete_after=5)
        
        # Refresh to story view
        await self._refresh_ui_after_modal(interaction)
    
    async def _back_to_cape(self, interaction: discord.Interaction):
        """Return to Cape"""
        self.player.current_gate = None
        self.current_state = "cape"
        await self._refresh_ui(interaction)
    
    # ==================== STORY SYSTEM ====================
    
    async def _build_story(self):
        """Build main story interface"""
        lang = self.player.language
        gate_id = self.player.current_gate
        config = GATE_CONFIGS[gate_id]
        
        # Get current scene
        scene = self._get_current_scene()
        
        if not scene:
            # No scene found - return to cape
            self.player.current_scene = None
            self.current_state = "cape"
            await self.build_ui()
            return
        
        # Build main story display
        if self.party_mode:
            # Show all party members' stats in condensed format
            party_stats = []
            for member_id in self.party_members:
                if member_id in self.party_characters:
                    char = self.party_characters[member_id]
                    is_current = (member_id == self.current_actor)
                    marker = "🎯" if is_current else "⚪"
                    party_stats.append(f"{marker} **{char.name}** ({char.char_class}) - HP: {char.health}/{char.max_health}")
            
            party_display = "\n".join(party_stats)
            
            container_items = [
                discord.ui.TextDisplay(content=f"""# {config['emoji']} {scene['title']}

{scene['text']}

---

**{t(lang, 'party_members_short')}:**
{party_display}"""),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ]
        else:
            # Solo mode - show full stats
            container_items = [
                discord.ui.TextDisplay(content=f"""# {config['emoji']} {scene['title']}

{scene['text']}

---

{self.player.character.get_stats_display(lang)}"""),
                discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ]
        
        # Add choice buttons
        if scene.get("choices"):
            for i, choice in enumerate(scene["choices"]):
                label = choice["text"][:80]
                
                # In party mode, only enable for current actor
                if self.party_mode:
                    # Show who can act
                    if self.current_actor:
                        actor_char = self.party_characters.get(self.current_actor)
                        if actor_char:
                            label = f"[{actor_char.name[:10]}] {choice['text'][:60]}"
                
                btn = discord.ui.Button(
                    style=discord.ButtonStyle.primary if i == 0 else discord.ButtonStyle.secondary,
                    label=label,
                    custom_id=f"choice_{i}"
                )
                btn.callback = lambda inter, idx=i: self._make_choice(inter, idx)
                container_items.append(discord.ui.ActionRow(btn))
        
        container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Control buttons
        stats_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=t(lang, 'btn_stats'),
            custom_id="view_char_stats"
        )
        stats_btn.callback = self._view_character_stats
        
        save_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=t(lang, 'btn_save'),
            custom_id="manual_save"
        )
        save_btn.callback = self._manual_save
        
        # Exit button - saves and closes session
        exit_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label=t(lang, 'btn_exit'),
            custom_id="exit_game"
        )
        exit_btn.callback = self._exit_game
        
        container_items.append(discord.ui.ActionRow(stats_btn, save_btn, exit_btn))
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(config["color"]),
        )
        
        self.clear_items()
        self.add_item(self.container)
    
    def _get_entry_scene_id(self, gate_id: int, is_party: bool = False) -> str:
        """
        Losuj punkt wejścia do wymiaru
        Różne miejsca i czasy dla replay value!
        """
        if gate_id == 1 and GATE1_AVAILABLE:
            # Gate 1 - use dynamic entry system
            entry_point = get_random_entry_point()
            
            # Save entry point for tracking
            self.player.last_entry_points[gate_id] = entry_point["scene_id"]
            
            save_msg = f"Wchodzisz przez: {entry_point.get('name_pl' if self.player.language == 'pl' else 'name_en')}"
            print(f"[Gate 1 Entry] {save_msg}")
            
            return entry_point["scene_id"]
        
        # Fallback dla innych bram (na razie)
        suffix = "_party" if is_party else ""
        return f"gate_{gate_id}_intro{suffix}"
    
    def _get_current_scene(self) -> Optional[Dict]:
        """Get current scene data - routing to dimension systems"""
        scene_id = self.player.current_scene
        gate_id = self.player.current_gate
        lang = self.player.language
        
        # === GATE 1: FANTASY - Dynamic System ===
        if gate_id == 1 and GATE1_AVAILABLE:
            # Load world state for Gate 1
            world_state_data = self.player.dimension_states.get(1, {})
            if world_state_data:
                world_state = Gate1WorldState.from_dict(world_state_data)
            else:
                world_state = Gate1WorldState()
                # Save initial state
                self.player.dimension_states[1] = world_state.to_dict()
            
            # Get scene from Gate 1 system
            scene = get_gate1_scene(scene_id, lang, world_state, self.player)
            
            if scene:
                # Save updated world state
                self.player.dimension_states[1] = world_state.to_dict()
                return scene
        
        # === FALLBACK: Old intro system dla niezaimplementowanych bram ===
        if scene_id == f"gate_{gate_id}_intro":
            return self._get_intro_scene(gate_id, lang, is_party=False)
        elif scene_id == f"gate_{gate_id}_intro_party":
            return self._get_intro_scene(gate_id, lang, is_party=True)
        
        # No scene found
        return None
    
    def _get_intro_scene(self, gate_id: int, lang: str, is_party: bool = False) -> Dict:
        """Get intro scene for a dimension"""
        config = GATE_CONFIGS[gate_id]
        
        if is_party:
            # Build party description
            party_names = []
            for member_id in self.party_members:
                if member_id in self.party_characters:
                    char = self.party_characters[member_id]
                    party_names.append(f"**{char.name}** ({char.char_class})")
            
            party_list = ", ".join(party_names[:-1]) + (" and " if lang == "en" else " oraz ") + party_names[-1] if len(party_names) > 1 else party_names[0]
            
            # Party intro - NPC sees the whole group
            intros = {
                1: {  # Fantasy
                    "en": f"""You all step through the gate together, and reality **crystallizes** around your group.

Stone towers pierce storm-gray skies. The smell of iron and rain fills your lungs.

{party_list} now stand together in the courtyard of **Stormhold Keep**.

A knight in dented armor approaches, his eyes widening as he sees your party.

"By the gods... {len(self.party_members)} travelers at once? The prophecy spoke of warriors arriving, but I didn't expect... a whole company."

He looks over your group, hand on sword hilt.

"The realm is in chaos. The king is dead. Demons pour from the Rift. We need all the help we can get."

He addresses the group: "Will you help us? Or are you just more fools chasing glory?"

**What will your party do?**""",
                    "pl": f"""Wszyscy razem przekraczacie bramę, a rzeczywistość **krystalizuje się** wokół waszej grupy.

Kamienne wieże przebijają burzowe niebo. Zapach żelaza i deszczu wypełnia wasze płuca.

{party_list} stoją teraz razem na dziedzińcu **Fortecy Burzy**.

Rycerz w porysowanej zbroi podchodzi, szeroko otwierając oczy na widok waszej drużyny.

"Na bogów... {len(self.party_members)} podróżników naraz? Przepowiednia mówiła o wojownikach, ale nie spodziewałem się... całej kompanii."

Przygląda się waszej grupie z ręką na rękojeści miecza.

"Królestwo w chaosie. Król nie żyje. Demony wylewają się z Rozłamu. Potrzebujemy wszelkiej pomocy."

Zwraca się do grupy: "Pomożecie nam? Czy jesteście kolejnymi głupcami goniącymi za chwałą?"

**Co zrobi wasza drużyna?**""",
                    "choices": {
                        "en": [
                            {"text": "✅ We'll help you", "next_scene": "gate_1_accept"},
                            {"text": "❓ Tell us more about the situation", "next_scene": "gate_1_info"},
                            {"text": "⚔️ Draw weapons and attack", "next_scene": "gate_1_attack"},
                            {"text": "🚶 Walk away", "next_scene": "gate_1_leave"},
                        ],
                        "pl": [
                            {"text": "✅ Pomożemy wam", "next_scene": "gate_1_accept"},
                            {"text": "❓ Opowiedz więcej o sytuacji", "next_scene": "gate_1_info"},
                            {"text": "⚔️ Dobądź broń i atakuj", "next_scene": "gate_1_attack"},
                            {"text": "🚶 Odejdź", "next_scene": "gate_1_leave"},
                        ],
                    }
                },
            }
            
            text = intros.get(gate_id, {}).get(lang, f"Your party of {len(self.party_members)} enters a new world together...")
        else:
            # Solo intro
            char = self.player.character
            intros = {
                1: {  # Fantasy
                    "en": f"""You step through the gate, and reality itself **crystallizes** around you.

Stone towers pierce storm-gray skies. The smell of iron and rain fills your lungs.

**{char.name}**, {char.char_class}, now stands in the courtyard of **Stormhold Keep**.

A knight in dented armor approaches, hand on sword hilt.

"You... the prophecy spoke of you. The realm is in chaos. The king is dead. Demons pour from the Rift."

He looks you up and down, uncertain.

"Will you help us? Or are you just another fool chasing glory?"

**What do you do?**""",
                    "pl": f"""Przekraczasz bramę, a rzeczywistość **krystalizuje się** wokół ciebie.

Kamienne wieże przebijają burzowe niebo. Zapach żelaza i deszczu wypełnia twoje płuca.

**{char.name}**, {char.char_class}, stoi teraz na dziedzińcu **Fortecy Burzy**.

Rycerz w porysowanej zbroi podchodzi z ręką na rękojeści miecza.

"Ty... przepowiednia mówiła o tobie. Królestwo w chaosie. Król nie żyje. Demony wylewają się z Rozłamu."

Przygląda ci się niepewnie.

"Pomożesz nam? Czy jesteś kolejnym głupcem goniącym za chwałą?"

**Co robisz?**""",
                    "choices": {
                        "en": [
                            {"text": "✅ I'll help you", "next_scene": "gate_1_accept"},
                            {"text": "❓ Tell me more about the situation", "next_scene": "gate_1_info"},
                            {"text": "⚔️ Draw weapon and attack", "next_scene": "gate_1_attack"},
                            {"text": "🚶 Walk away", "next_scene": "gate_1_leave"},
                        ],
                        "pl": [
                            {"text": "✅ Pomogę wam", "next_scene": "gate_1_accept"},
                            {"text": "❓ Opowiedz mi więcej o sytuacji", "next_scene": "gate_1_info"},
                            {"text": "⚔️ Dobądź broni i atakuj", "next_scene": "gate_1_attack"},
                            {"text": "🚶 Odejdź", "next_scene": "gate_1_leave"},
                        ],
                    }
                },
            }
            
            text = intros.get(gate_id, {}).get(lang, "You enter a new world...")
        
        # Get choices in correct language
        intro_data = intros.get(gate_id, {})
        choices_data = intro_data.get("choices", {})
        choices = choices_data.get(lang, choices_data.get("en", [
            {"text": "✅ Continue", "next_scene": f"gate_{gate_id}_accept"},
        ]))
        
        return {
            "title": "The Beginning" if lang == "en" else "Początek",
            "text": text,
            "choices": choices
        }
    
    async def _make_choice(self, interaction: discord.Interaction, choice_idx: int):
        """Handle player choice"""
        user_id = interaction.user.id
        scene = self._get_current_scene()
        
        if not scene or choice_idx >= len(scene.get("choices", [])):
            await interaction.response.send_message("❌ Invalid choice", ephemeral=True)
            return
        
        # In party mode, check if it's this player's turn
        if self.party_mode:
            # Check if user is in party
            if user_id not in self.party_members:
                await interaction.response.send_message(
                    "❌ You're not in this party!",
                    ephemeral=True,
                    delete_after=3
                )
                return
            
            # Check if it's their turn
            if user_id != self.current_actor:
                actor_char = self.party_characters.get(self.current_actor)
                actor_name = actor_char.name if actor_char else "another player"
                await interaction.response.send_message(
                    f"⏳ It's {actor_name}'s turn! Wait for your turn.",
                    ephemeral=True,
                    delete_after=3
                )
                return
            
            # Execute the choice for this party member
            await interaction.response.send_message(
                f"✅ **{self.party_characters[user_id].name}** takes action!",
                ephemeral=True,
                delete_after=2
            )
            
            # Move to next turn
            current_idx = self.turn_order.index(user_id)
            next_idx = (current_idx + 1) % len(self.turn_order)
            self.current_actor = self.turn_order[next_idx]
            
            # Execute the choice
            await self._execute_choice(choice_idx, scene)
            return
        
        # Solo mode - execute immediately
        choice = scene["choices"][choice_idx]
        
        # Record choice
        self.player.choices_made.append({
            "scene": self.player.current_scene,
            "choice": choice["text"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Move to next scene
        next_scene = choice.get("next_scene")
        if next_scene:
            self.player.current_scene = next_scene
            self.player.story_history.append(next_scene)
        
        # Auto-save
        save_player(self.player)
        
        # Check for dice roll requirement
        if choice.get("requires_roll"):
            await self._perform_dice_roll(interaction, choice)
        else:
            await self._refresh_ui(interaction)
    
    async def _execute_choice(self, choice_idx: int, scene: Dict):
        """Execute a choice (used after voting in party mode)"""
        choice = scene["choices"][choice_idx]
        
        # Record choice
        self.player.choices_made.append({
            "scene": self.player.current_scene,
            "choice": choice["text"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Move to next scene
        next_scene = choice.get("next_scene")
        if next_scene:
            self.player.current_scene = next_scene
            self.player.story_history.append(next_scene)
        
        # Auto-save
        save_player(self.player)
        
        # Refresh UI for party
        if self.message:
            self.clear_items()
            await self.build_ui()
            await self.message.edit(view=self)
    
    async def _perform_dice_roll(self, interaction: discord.Interaction, choice: Dict):
        """Perform a D20 roll with modifiers"""
        lang = self.player.language
        char = self.player.character
        
        # Determine stat modifier
        stat_type = choice.get("stat", "luck")
        stat_value = getattr(char, stat_type.lower(), 10)
        modifier = (stat_value - 10) // 2  # D&D style modifier
        
        # Roll
        roll = random.randint(1, 20)
        total = roll + modifier
        dc = choice.get("dc", 10)
        
        success = total >= dc
        
        # Show result
        result_emoji = "✅" if success else "❌"
        crit_text = ""
        if roll == 20:
            crit_text = "\n**🎯 CRITICAL SUCCESS!**"
            success = True
        elif roll == 1:
            crit_text = "\n**💀 CRITICAL FAILURE!**"
            success = False
        
        result_text = f"""**🎲 Dice Roll: {stat_type.title()} Check**

Roll: **{roll}** + Modifier: **{modifier}** = **{total}**
DC: **{dc}**

{result_emoji} **{"SUCCESS" if success else "FAILURE"}**{crit_text}"""
        
        await interaction.response.send_message(result_text, ephemeral=True, delete_after=10)
        
        # Apply consequence
        if success:
            next_scene = choice.get("success_scene")
        else:
            next_scene = choice.get("failure_scene")
        
        if next_scene:
            self.player.current_scene = next_scene
            self.player.story_history.append(next_scene)
            save_player(self.player)
        
        # Refresh UI after delay
        await asyncio.sleep(1)
        await self._refresh_ui_after_ephemeral(interaction)
    
    async def _view_character_stats(self, interaction: discord.Interaction):
        """Show detailed character stats"""
        user_id = interaction.user.id
        lang = self.player.language
        
        # In party mode, show the stats of the requesting user's character
        if self.party_mode:
            if user_id in self.party_characters:
                char = self.party_characters[user_id]
            else:
                await interaction.response.send_message(
                    "❌ You don't have a character yet!",
                    ephemeral=True,
                    delete_after=3
                )
                return
        else:
            char = self.player.character
        
        if not char:
            return
        
        stats_text = f"""# 📊 {char.name} - {char.char_class}

**Level:** {char.level} | **XP:** {char.experience}

**Resources:**
{t(lang, 'stat_health')}: {char.health}/{char.max_health}
{t(lang, 'stat_mana')}: {char.mana}/{char.max_mana}
{t(lang, 'stat_stamina')}: {char.stamina}/{char.max_stamina}

**Attributes:**
{t(lang, 'stat_strength')}: {char.strength}
{t(lang, 'stat_intelligence')}: {char.intelligence}
{t(lang, 'stat_charisma')}: {char.charisma}
{t(lang, 'stat_luck')}: {char.luck}

**Conditions:** {', '.join(char.conditions) if char.conditions else 'None'}

**Cosmic Stats:**
Total Deaths: {self.player.total_deaths}
Worlds Changed: {self.player.worlds_changed}
Influence: {self.player.cosmic_influence}"""
        
        await interaction.response.send_message(stats_text, ephemeral=True, delete_after=60)
    
    async def _manual_save(self, interaction: discord.Interaction):
        """Manual save via button - keeps session active"""
        lang = self.player.language
        
        # Save all party members if in party mode
        if self.party_mode:
            success = True
            for member_id, player_data in self.party_players.items():
                if not save_player(player_data):
                    success = False
            
            if success:
                await interaction.response.send_message(t(lang, 'save_success'), ephemeral=True, delete_after=5)
            else:
                await interaction.response.send_message(t(lang, 'save_failed'), ephemeral=True, delete_after=5)
        else:
            if save_player(self.player):
                await interaction.response.send_message(t(lang, 'save_success'), ephemeral=True, delete_after=5)
            else:
                await interaction.response.send_message(t(lang, 'save_failed'), ephemeral=True, delete_after=5)
    
    async def _exit_game(self, interaction: discord.Interaction):
        """Save and exit - closes session completely"""
        lang = self.player.language
        
        # Save all party members if in party mode
        if self.party_mode:
            for member_id, player_data in self.party_players.items():
                save_player(player_data)
                
                # Remove from active sessions
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            save_player(self.player)
            
            # Remove from active sessions
            if self.player.user_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.player.user_id]
        
        # Disable all components
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
        
        # Show exit message
        await interaction.response.send_message(t(lang, 'exit_success'), ephemeral=True, delete_after=10)
        
        # Update message to show session ended
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    async def _quit_to_cape(self, interaction: discord.Interaction):
        """Return to Cape without dying"""
        # Save and reset for all party members
        if self.party_mode:
            for member_id, player_data in self.party_players.items():
                player_data.current_gate = None
                save_player(player_data)
                
                # Remove from active sessions
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            self.player.current_gate = None
            save_player(self.player)
        
        self.current_state = "cape"
        
        await self._refresh_ui(interaction)
    
    # ==================== UI REFRESH HELPERS ====================
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        user_id = interaction.user.id
        
        # In party mode, any party member can interact
        if self.party_mode:
            if user_id not in self.party_members:
                await interaction.response.send_message(
                    "❌ You're not part of this adventure!",
                    ephemeral=True,
                    delete_after=3
                )
                return False
            return True
        
        # In solo mode, only the player can interact
        if user_id != self.player.user_id:
            await interaction.response.send_message(
                "❌ This isn't your adventure!",
                ephemeral=True,
                delete_after=3
            )
            return False
        
        return True
    
    # ==================== UI REFRESH METHODS ====================
    
    async def _refresh_ui(self, interaction: discord.Interaction):
        """Rebuild and refresh the entire UI"""
        # Clear existing items
        self.clear_items()
        
        # Rebuild based on current state
        await self.build_ui()
        
        # Update the message
        try:
            await interaction.response.edit_message(view=self)
        except discord.errors.InteractionResponded:
            # Interaction already responded (e.g., from modal)
            if self.message:
                await self.message.edit(view=self)
    
    async def _refresh_ui_after_modal(self, interaction: discord.Interaction):
        """Refresh UI after a modal was shown"""
        self.clear_items()
        await self.build_ui()
        
        if self.message:
            await self.message.edit(view=self)
    
    async def _refresh_ui_after_ephemeral(self, interaction: discord.Interaction):
        """Refresh UI after ephemeral message was sent"""
        self.clear_items()
        await self.build_ui()
        
        if self.message:
            await self.message.edit(view=self)
    
    async def _refresh_ui_after_response(self, interaction: discord.Interaction):
        """Refresh UI after interaction.response was already used"""
        self.clear_items()
        await self.build_ui()
        
        if self.message:
            await self.message.edit(view=self)
    
    def handle_death(self):
        """Handle character death - clear dimension save, return to Cape"""
        user_id = self.player.user_id
        
        # Mark that player just died (for anti-cheat)
        self.just_died = True
        
        # Death detected - clear all dimension progress
        if self.player.current_gate:
            # Clear dimension state
            self.player.dimension_states[self.player.current_gate] = {}
        
        # Death stats
        self.player.total_deaths += 1
        self.player.worlds_changed += 1  # Death changes things
        
        # Remove character and return to Cape
        self.player.character = None
        self.player.current_gate = None
        self.player.current_scene = None
        self.player.story_history = []
        self.player.choices_made = []
        
        # Auto-save at Cape - no cheating with old world saves
        save_player(self.player)
        
        # Update state
        self.current_state = "cape"
    
    def check_character_death(self) -> bool:
        """Check if character is dead, handle death if so"""
        if self.player.character and self.player.character.health <= 0:
            self.handle_death()
            return True
        return False
    
    async def apply_damage(self, damage: int, damage_type: str = "physical"):
        """Apply damage to character and check for death"""
        if not self.player.character:
            return
        
        self.player.character.health -= damage
        
        # Check for death
        if self.check_character_death():
            # Character died - show death screen
            lang = self.player.language
            death_title = t(lang, 'death_title')
            death_text = t(lang, 'death_text', name=self.player.character.name if self.player.character else "Unknown")
            
            # Save at Cape
            save_player(self.player)
            
            return True  # Character died
        
        return False  # Character survived
    
    async def on_timeout(self):
        """Handle view timeout"""
        # Remove session for all party members
        if self.party_mode:
            for member_id in self.party_members:
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            if self.player.user_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.player.user_id]
        
        # Disable all components
        for item in self.children:
            if hasattr(item, 'disabled'):
                item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==================== MODALS ====================

class CharacterNameModal(discord.ui.Modal):
    """Modal for entering character name"""
    
    def __init__(self, view: InfinityView, char_class: str, lang: str):
        super().__init__(title=t(lang, 'char_name'))
        self.view = view
        self.char_class = char_class
        self.lang = lang
        
        self.name_input = discord.ui.TextInput(
            label=t(lang, 'char_name'),
            placeholder="Enter your character's name",
            min_length=2,
            max_length=30,
            required=True
        )
        self.add_item(self.name_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle name submission"""
        name = self.name_input.value.strip()
        await self.view._create_character(interaction, name, self.char_class)


# ==================== COG DEFINITION ====================

class InfinityAdventure(commands.Cog):
    """Infinity Adventure - Interdimensional Narrative System"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}  # {user_id: InfinityView}
    
    @app_commands.command(name="dnd", description="Begin your infinite journey across dimensions")
    async def dnd(self, interaction: discord.Interaction):
        """Start or resume Infinity Adventure"""
        user_id = interaction.user.id
        
        # Check for active session
        if user_id in self.active_sessions:
            await interaction.response.send_message(
                "❌ **You're already in an adventure!** Use the Save/Quit buttons to exit first.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Load or create player data
        player = load_player(user_id)
        if not player:
            player = PlayerData(user_id)
        
        # Create view (mark as new session)
        view = InfinityView(player, self, is_new_session=True)
        await view.build_ui()
        
        # Send message (no content parameter for Components V2)
        message = await interaction.followup.send(view=view)
        
        view.message = message
        self.active_sessions[user_id] = view


async def setup(bot):
    await bot.add_cog(InfinityAdventure(bot))
