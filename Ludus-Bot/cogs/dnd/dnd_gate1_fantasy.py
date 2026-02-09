"""
GATE 1: SWORD & BLOOD - Fantasy Dimension
50+ scenes with multiple entry points and branching narratives
"""

import random
from typing import Dict, Optional, List

# ==================== WORLD STATE SYSTEM ====================

class Gate1WorldState:
    """Track the state of the Fantasy dimension"""
    
    def __init__(self):
        # Kingdom Status
        self.king_alive = None  # None = random, True/False = fixed
        self.capital_status = "under_siege"  # "safe", "under_siege", "fallen", "liberated"
        self.rift_activity = "active"  # "dormant", "active", "unstable", "sealed"
        
        # Factions
        self.royal_guard_strength = 50  # 0-100
        self.resistance_power = 30  # 0-100
        self.demon_forces = 70  # 0-100
        self.church_influence = 40  # 0-100
        
        # Key NPCs Status
        self.knight_commander_alive = True
        self.high_priestess_corrupted = False
        self.rebellion_leader_known = False
        self.ancient_dragon_awakened = False
        
        # World Events
        self.cities_saved = []
        self.cities_fallen = []
        self.alliances_formed = []
        self.artifacts_found = []
        
        # Timeline markers (which events already happened)
        self.king_assassination_happened = False
        self.demon_invasion_started = False
        self.dragon_awakening_triggered = False
        
    def to_dict(self):
        return {
            "king_alive": self.king_alive,
            "capital_status": self.capital_status,
            "rift_activity": self.rift_activity,
            "royal_guard_strength": self.royal_guard_strength,
            "resistance_power": self.resistance_power,
            "demon_forces": self.demon_forces,
            "church_influence": self.church_influence,
            "knight_commander_alive": self.knight_commander_alive,
            "high_priestess_corrupted": self.high_priestess_corrupted,
            "rebellion_leader_known": self.rebellion_leader_known,
            "ancient_dragon_awakened": self.ancient_dragon_awakened,
            "cities_saved": self.cities_saved,
            "cities_fallen": self.cities_fallen,
            "alliances_formed": self.alliances_formed,
            "artifacts_found": self.artifacts_found,
            "king_assassination_happened": self.king_assassination_happened,
            "demon_invasion_started": self.demon_invasion_started,
            "dragon_awakening_triggered": self.dragon_awakening_triggered,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state


# ==================== ENTRY POINTS ====================

GATE1_ENTRY_POINTS = {
    # Różne miejsca i czasy wejścia
    "stormhold_siege": {
        "weight": 30,  # Szansa na wylosowanie
        "name_en": "Stormhold Keep - Under Siege",
        "name_pl": "Forteca Burzy - Pod Oblężeniem",
        "time": "present",
        "scene_id": "g1_intro_stormhold"
    },
    "forest_ambush": {
        "weight": 25,
        "name_en": "Forest Road - Ambush",
        "name_pl": "Droga Leśna - Zasadzka",
        "time": "present",
        "scene_id": "g1_intro_forest"
    },
    "capital_ruins": {
        "weight": 20,
        "name_en": "Capital City - In Ruins",
        "name_pl": "Stolica - W Ruinach",
        "time": "future",  # Przyszłość - królestwo już upadło
        "scene_id": "g1_intro_ruins"
    },
    "temple_ritual": {
        "weight": 15,
        "name_en": "Ancient Temple - During Ritual",
        "name_pl": "Starożytna Świątynia - Podczas Rytuału",
        "time": "present",
        "scene_id": "g1_intro_temple"
    },
    "dragon_lair": {
        "weight": 10,
        "name_en": "Dragon's Lair - Awakening",
        "name_pl": "Legowisko Smoka - Przebudzenie",
        "time": "past",  # Przeszłość - przed inwazją
        "scene_id": "g1_intro_dragon"
    }
}


def get_random_entry_point() -> Dict:
    """Losuj punkt wejścia z wagami"""
    points = []
    weights = []
    
    for key, data in GATE1_ENTRY_POINTS.items():
        points.append(data)
        weights.append(data["weight"])
    
    return random.choices(points, weights=weights)[0]


# ==================== SCENE DATABASE ====================

def get_gate1_scene(scene_id: str, lang: str, world_state: Gate1WorldState, player_data) -> Optional[Dict]:
    """
    Pobierz scenę dla Gate 1
    
    Sceny są numerowane:
    g1_intro_X - punkty wejścia (5)
    g1_main_001 - g1_main_050 - główne sceny (50+)
    g1_branch_X_Y - rozgałęzienia
    g1_end_X - zakończenia
    """
    
    # ==================== INTRO SCENES ====================
    
    if scene_id == "g1_intro_stormhold":
        return get_intro_stormhold(lang, world_state, player_data)
    
    elif scene_id == "g1_intro_forest":
        return get_intro_forest(lang, world_state, player_data)
    
    elif scene_id == "g1_intro_ruins":
        return get_intro_ruins(lang, world_state, player_data)
    
    elif scene_id == "g1_intro_temple":
        return get_intro_temple(lang, world_state, player_data)
    
    elif scene_id == "g1_intro_dragon":
        return get_intro_dragon(lang, world_state, player_data)
    
    # ==================== MAIN QUEST SCENES ====================
    
    elif scene_id == "g1_main_001":
        return get_scene_001_knight_decision(lang, world_state, player_data)
    
    elif scene_id == "g1_main_002":
        return get_scene_002_throne_room(lang, world_state, player_data)
    
    elif scene_id == "g1_main_003":
        return get_scene_003_rift_discovery(lang, world_state, player_data)
    
    elif scene_id == "g1_main_004":
        return get_scene_004_first_demon_boss(lang, world_state, player_data)
    
    elif scene_id == "g1_main_005":
        return get_scene_005_village_attack(lang, world_state, player_data)
    
    elif scene_id == "g1_main_006":
        return get_scene_006_aftermath(lang, world_state, player_data)
    
    elif scene_id == "g1_main_007":
        return get_scene_007_betrayal_discovery(lang, world_state, player_data)
    
    elif scene_id == "g1_main_008":
        return get_scene_008_church_infiltration(lang, world_state, player_data)
    
    elif scene_id == "g1_main_009":
        return get_scene_009_cathedral_battle(lang, world_state, player_data)
    
    elif scene_id == "g1_main_010":
        return get_scene_010_ancient_weapon(lang, world_state, player_data)
    
    elif scene_id == "g1_main_011":
        return get_scene_011_underworld_journey(lang, world_state, player_data)
    
    elif scene_id == "g1_main_012":
        return get_scene_012_ghost_king(lang, world_state, player_data)
    
    elif scene_id == "g1_main_013":
        return get_scene_013_final_siege(lang, world_state, player_data)
    
    elif scene_id == "g1_main_014":
        return get_scene_014_seal_rift(lang, world_state, player_data)
    
    elif scene_id == "g1_main_015":
        return get_scene_015_coronation(lang, world_state, player_data)
    
    # TODO: Implement 35+ main scenes (dragon, rebellion, artifacts, dark path)
    
    # ==================== BRANCH SCENES ====================
    
    elif scene_id == "g1_branch_attack_knight":
        return get_branch_attack_knight(lang, world_state, player_data)
    
    elif scene_id == "g1_branch_help_villagers":
        return get_branch_help_villagers(lang, world_state, player_data)
    
    # ==================== ENDINGS ====================
    
    elif scene_id == "g1_end_kingdom_saved":
        return get_ending_kingdom_saved(lang, world_state, player_data)
    
    elif scene_id == "g1_end_demon_lord":
        return get_ending_demon_lord(lang, world_state, player_data)
    
    elif scene_id == "g1_end_dragon_pact":
        return get_ending_dragon_pact(lang, world_state, player_data)
    
    return None


# ==================== INTRO SCENES (5) ====================

def get_intro_stormhold(lang: str, state: Gate1WorldState, player) -> Dict:
    """Intro: Forteca Burzy - klasyczne intro"""
    
    if lang == "pl":
        text = f"""Przekraczasz bramę, a rzeczywistość **krystalizuje się** wokół ciebie.

**FORTECA BURZY** - kamienne wieże przebijają burzowe szare niebo. Zapach żelaza i deszczu wypełnia twoje płuca.

**{player.character.name}** ({player.character.char_class}) stoi na dziedzińcu oblężonej fortecy.

Wokół ciebie panuje chaos:
• Żołnierze krzyczą rozkazy
• Strzały gwiżdżą nad murami
• Zapach siarki i spalenizny unosi się w powietrzu

Rycerz w porysowanej zbroi podchodzi, ręka na mieczu:

**"TY! Podróżniku! Jesteś ze straży miejskiej? Nie? To kim do diabła jesteś?"**

Patrzy na ciebie z mieszanką nadziei i desperacji.

**"Królestwo upada. Król właśnie zginął. DEMONY wylewają się z Rozłamu."**

Wskazuje na purpurową szcze linę na niebie, pulsującą złowieszczą energią.

**"Potrzebujemy KAŻDEJ ręki do walki. Pomożesz nam? Czy jesteś kolejnym tchórzem?"**

Co robisz?"""
        
        choices = [
            {"text": "⚔️ 'Pomogą. Gdzie jest ten Rozłam?'", "next_scene": "g1_main_001", "effect": {"royal_guard": +10}},
            {"text": "🤔 'Opowiedz mi więcej o sytuacji'", "next_scene": "g1_main_002", "effect": {"intelligence_check": 12}},
            {"text": "🗡️ 'Atakuj rycerza - zabierz jego zbroję'", "next_scene": "g1_branch_attack_knight", "effect": {"alignment": "dark"}},
            {"text": "🚶 'To nie moja wojna. Odchodzę.'", "next_scene": "g1_main_003", "effect": {"royal_guard": -20}},
        ]
    
    else:  # EN
        text = f"""You step through the gate, and reality **crystallizes** around you.

**STORMHOLD KEEP** - stone towers pierce storm-gray skies. The smell of iron and rain fills your lungs.

**{player.character.name}** ({player.character.char_class}) stands in the courtyard of a besieged fortress.

Chaos surrounds you:
• Soldiers shouting orders
• Arrows whistling over walls
• The stench of sulfur and burning fills the air

A knight in battered armor approaches, hand on sword:

**"YOU! Traveler! Are you with the city guard? No? Then who the hell are you?"**

He looks at you with a mix of hope and desperation.

**"The kingdom is falling. The king just died. DEMONS pour from the Rift."**

He points to a purple scar in the sky, pulsing with ominous energy.

**"We need EVERY hand to fight. Will you help us? Or are you another coward?"**

What do you do?"""
        
        choices = [
            {"text": "⚔️ 'I'll help. Where is this Rift?'", "next_scene": "g1_main_001", "effect": {"royal_guard": +10}},
            {"text": "🤔 'Tell me more about the situation'", "next_scene": "g1_main_002", "effect": {"intelligence_check": 12}},
            {"text": "🗡️ 'Attack the knight - take his armor'", "next_scene": "g1_branch_attack_knight", "effect": {"alignment": "dark"}},
            {"text": "🚶 'Not my war. I'm leaving.'", "next_scene": "g1_main_003", "effect": {"royal_guard": -20}},
        ]
    
    return {
        "title": "Forteca Burzy" if lang == "pl" else "Stormhold Keep",
        "text": text,
        "choices": choices,
        "location": "stormhold_keep",
        "npc_present": ["knight_commander"]
    }


def get_intro_forest(lang: str, state: Gate1WorldState, player) -> Dict:
    """Intro: Droga leśna - zasadzka"""
    
    if lang == "pl":
        text = f"""Materializujesz się pośród **starożytnego lasu**.

Wysokie drzewa blokują większość światła. Powietrze jest gęste od wilgoci.

**{player.character.name}**, {player.character.char_class}, stoisz na wąskiej drodze pokrytej mchem.

**KRZYK rozbrzmiewa w odali!**

Wybiegasz na polanę i widzisz:

🛡️ **Wóz kupiecki** - przewrócony, płonący
⚔️ **Trzech bandytów** - rabujący towar
😱 **Rodzina** - ukrywa się za skałą, przerażona

Jeden z bandytów dostrzega cię:

**"Patrz, patrz! Jeszcze jeden ślepiec wpada nam w ręce! Zostaw broń, podróżniku, albo skończysz jak ci głupcy!"**

Wskazuje na ciała dwóch strażników leżących w kałuży krwi.

**"Albo... dołącz do nas? Mamy dobry interes tu w lesie!"**

Pozostałe dwa osoby zbliżają się powoli, broń wyciągnięta.

Co robisz?"""
        
        choices = [
            {"text": "⚔️ Zaatakuj bandytów (wymagany rzut Siły DC 14)", "next_scene": "g1_main_004", "requires_roll": True, "stat": "strength", "dc": 14},
            {"text": "💬 'Wszyscy tu umrzemy. To nie zwykły las.'", "next_scene": "g1_main_005", "effect": {"charisma_check": 13}},
            {"text": "🏃 Ucieknij w głąb lasu", "next_scene": "g1_branch_forest_escape", "effect": {}},
            {"text": "🤝 'Dołączę. Co rabujemy?'", "next_scene": "g1_branch_join_bandits", "effect": {"alignment": "dark"}},
        ]
    
    else:  # EN
        text = f"""You materialize in an **ancient forest**.

Tall trees block most of the light. The air is thick with moisture.

**{player.character.name}**, {player.character.char_class}, you stand on a narrow moss-covered road.

**A SCREAM echoes in the distance!**

You run to a clearing and see:

🛡️ **Merchant wagon** - overturned, burning
⚔️ **Three bandits** - looting goods
😱 **Family** - hiding behind rocks, terrified

One bandit spots you:

**"Look, look! Another fool walks into our hands! Drop your weapon, traveler, or you'll end up like these fools!"**

He points to two guard corpses in a pool of blood.

**"Or... join us? We have good business here in the woods!"**

The other two advance slowly, weapons drawn.

What do you do?"""
        
        choices = [
            {"text": "⚔️ Attack bandits (Strength check DC 14)", "next_scene": "g1_main_004", "requires_roll": True, "stat": "strength", "dc": 14},
            {"text": "💬 'We'll all die here. This is no ordinary forest.'", "next_scene": "g1_main_005", "effect": {"charisma_check": 13}},
            {"text": "🏃 Flee deeper into the forest", "next_scene": "g1_branch_forest_escape", "effect": {}},
            {"text": "🤝 'I'll join. What are we looting?'", "next_scene": "g1_branch_join_bandits", "effect": {"alignment": "dark"}},
        ]
    
    return {
        "title": "Droga Leśna" if lang == "pl" else "Forest Road",
        "text": text,
        "choices": choices,
        "location": "ancient_forest",
        "npc_present": ["bandits"]
    }


def get_intro_ruins(lang: str, state: Gate1WorldState, player) -> Dict:
    """Intro: Ruiny stolicy - przyszłość, królestwo już upadło"""
    
    if lang == "pl":
        text = f"""Przekraczasz bramę... i **czas pęka**.

Pojwiasz się w **PRZYSZŁOŚCI**.

**{player.character.name}** stoi pośród ruin tego, co kiedyś było wspaniałą stolicą.

**To co widzisz przyprawia cię o mdłości:**

🏚️ Wielki pałac - rozsadzony od środka, płonie wiecznym fioletowym ogniem
💀 Ulice - pokryte kośćmi i popiołem
🌫️ Niebo - purpurowe, rozerwane, pulsujące demoniczną energią
👁️ **OCZY** - obserwują cię z ciemności

**Głos rozbrzmiewa w twojej głowie:**

*"Witaj, wędrowcze. Spóźniłeś się o dekadę. TU NIE MA KRÓLESTWA DO RATOWANIA."*

*"Ale może... może możesz COFNĄĆ TO, co się stało?"*

Dostrzegasz **rozbłysk światła** w ruinach świątyni. Coś... lub ktoś tam jest.

**"POMÓŻ MI!"** - krzyczy kobiecy głos.

Ale słyszysz też **szelest** za sobą. Coś się zbliża.

Co robisz?"""
        
        choices = [
            {"text": "🏃 Biegnij do świątyni - ratuj głos", "next_scene": "g1_main_006", "effect": {}},
            {"text": "⚔️ Obróć się - staw czoła temu co nadchodzi", "next_scene": "g1_main_007", "effect": {"courage": +1}},
            {"text": "🔮 Zbadaj Rozłam - może jest sposób cofnąć czas?", "next_scene": "g1_main_008", "effect": {"intelligence_check": 15}},
            {"text": "😱 To za dużo. UCIEKAJ przez bramę!", "next_scene": "g1_branch_flee_future", "effect": {"fear": +1}},
        ]
    
    else:  # EN
        text = f"""You step through the gate... and **time shatters**.

You appear in the **FUTURE**.

**{player.character.name}** stands amid ruins of what was once a grand capital.

**What you see makes you nauseous:**

🏚️ Grand palace - burst from within, burning with eternal purple fire
💀 Streets - covered in bones and ash
🌫️ Sky - purple, torn, pulsing with demonic energy
👁️ **EYES** - watching you from the darkness

**A voice echoes in your head:**

*"Welcome, wanderer. You're a decade too late. THERE IS NO KINGDOM TO SAVE."*

*"But perhaps... perhaps you can UNDO what happened?"*

You spot a **glimmer of light** in temple ruins. Something... or someone is there.

**"HELP ME!"** - a woman's voice screams.

But you also hear **rustling** behind you. Something approaches.

What do you do?"""
        
        choices = [
            {"text": "🏃 Run to temple - save the voice", "next_scene": "g1_main_006", "effect": {}},
            {"text": "⚔️ Turn around - face what's coming", "next_scene": "g1_main_007", "effect": {"courage": +1}},
            {"text": "🔮 Examine the Rift - can time be reversed?", "next_scene": "g1_main_008", "effect": {"intelligence_check": 15}},
            {"text": "😱 This is too much. FLEE through the gate!", "next_scene": "g1_branch_flee_future", "effect": {"fear": +1}},
        ]
    
    return {
        "title": "Ruiny Stolicy" if lang == "pl" else "Capital Ruins",
        "text": text,
        "choices": choices,
        "location": "capital_ruins_future",
        "npc_present": ["mysterious_voice"],
        "timeline": "future"
    }


def get_intro_temple(lang: str, state: Gate1WorldState, player) -> Dict:
    """Intro: Starożytna świątynia - podczas rytuału"""
    if lang == "pl":
        title = "🕯️ Zakłócony Rytuał"
        text = """Pojawiasz się w ogromnej katedrze tonącej w półmroku. Setki świec płoną wokół centralnego ołtarza, a powietrze drży od mocy.
        
**Arcykapłanka w srebrnej szacie stoi nad ołtarzem**, wznosi ręce do góry. Wokół niej wiruje krąg złotej energii. Jej głos rozbrzmiewa echem:

*"Bogowie dali nam klątwę demonów jako próbę! Musimy udowodnić naszą wiarę! Ofiarujmy naszą krew dla oczyszczenia!"*

**Widzisz związanych ludzi przy ołtarzu** - trzech młodych nowicjuszy. Mają przerażenie w oczach. Rytuał wygląda na... ofiarę.

**Nagle arcykapłanka cię dostrzega.** Rytualna moc zamiera. Wszyscy patrzą na ciebie.

*"Przybysz! To znak! Bogowie przysłali kolejną ofiarę!"* - woła i wskazuje na ciebie.

Strażnicy kościelni sięgają po miecze."""
        
        choices = [
            {"text": "PRZERWIJ RYTUAŁ - Rzuć się do uwięzionych", "next": "g1_branch_save_sacrifices", 
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "ZAATAKUJ ARCYKAPŁANKĘ - Zabij ją przed dokończeniem", "next": "g1_branch_kill_priestess",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "PRZEKONAJ - 'To nie jest wola bogów!'", "next": "g1_branch_persuade_church",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 17}},
            {"text": "UCIEKAJ - To szaleństwo, wyjdź z katedry", "next": "g1_branch_temple_escape"}
        ]
    else:  # EN
        title = "🕯️ Interrupted Ritual"
        text = """You materialize in a vast cathedral shrouded in twilight. Hundreds of candles burn around the central altar, and the air trembles with power.
        
**A High Priestess in silver robes stands over the altar**, raising her hands skyward. A circle of golden energy swirls around her. Her voice echoes:

*"The gods gave us the demon curse as a test! We must prove our faith! Let us offer our blood for purification!"*

**You see bound people at the altar** - three young acolytes. Terror fills their eyes. The ritual looks like... a sacrifice.

**Suddenly the High Priestess notices you.** The ritual power halts. All eyes turn to you.

*"Stranger! A sign! The gods sent another offering!"* - she calls out, pointing at you.

Church guards reach for their swords."""
        
        choices = [
            {"text": "INTERRUPT RITUAL - Rush to the captives", "next": "g1_branch_save_sacrifices",
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "ATTACK PRIESTESS - Kill her before completion", "next": "g1_branch_kill_priestess",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "PERSUADE - 'This is not the gods' will!'", "next": "g1_branch_persuade_church",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 17}},
            {"text": "FLEE - This is madness, leave the cathedral", "next": "g1_branch_temple_escape"}
        ]
    
    # World state effects
    state.high_priestess_corrupted = True
    state.church_influence = 60
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None
    }


def get_intro_dragon(lang: str, state: Gate1WorldState, player) -> Dict:
    """Intro: Legowisko smoka - przeszłość"""
    if lang == "pl":
        title = "🐉 Przed Inwazją"
        text = """*Tykanie. Czujesz tykanie. Czas płynie inaczej.*

Pojawiasz się w gigantycznej jaskini wypełnionej **górami złota i klejnotów**. Powietrze jest gorące, pachnie siarką. To legowisko.

**OGROMNY SMOK** spoczywa na szczycie góry skarbów. Jego łuski lśnią jak rubiny w świetle lawy. Oczy są zamknięte - śpi.

Ale czujesz to. **To nie jest "teraz"**. To wcześniej. Znacznie wcześniej.

Nagle **głos rozbrzmiewa w twojej głowie**:

*"Śmiertelny trafiłeś do mojej jaskini... w przeszłości. Ciekawa interwencja czasu-przestrzeni. Widzę twoją przyszłość - widzę demony. Widzę zniszczenie. Widzę Rozłam."*

Smok otwiera jedno oko. Patrzy na ciebie.

*"Może powinieneś zapobiec inwazji... Zanim się zacznie. Zabijając odpowiedzialne królestwo. TERAZ, gdy są słabi. Czy... może smoki same spowodowały Rozłam? Chcesz o tym porozmawiać?"*

Widzisz obok portale czasowe - prowadzące do różnych punktów historii."""
        
        choices = [
            {"text": "PAKT - Pomóż smokowi zniszczyć królestwo TERAZ", "next": "g1_branch_dragon_dark_pact",
             "effects": {"reputation": -20, "alignment_shift": "evil"}},
            {"text": "OSTRZEŻ - Powiedz smokowi o przyszłości, błagaj o pomoc", "next": "g1_branch_dragon_warning",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 18}},
            {"text": "ZAATAKUJ - Zabij smoka gdy jest bezbronny!", "next": "g1_branch_kill_sleeping_dragon",
             "req": {"type": "stat_check", "stat": "strength", "dc": 20}},
            {"text": "PRZEKROCZENIE - Skocz w portal do innego czasu", "next": "g1_branch_time_travel"}
        ]
    else:  # EN
        title = "🐉 Before the Invasion"
        text = """*Ticking. You feel ticking. Time flows differently.*

You materialize in a gigantic cavern filled with **mountains of gold and gems**. The air is hot, reeks of sulfur. This is a lair.

**A MASSIVE DRAGON** rests atop the treasure hoard. Its scales shimmer like rubies in the lava's glow. Eyes closed - sleeping.

But you feel it. **This is not "now"**. This is earlier. Much earlier.

Suddenly **a voice echoes in your mind**:

*"Mortal, you've arrived in my lair... in the past. Curious space-time intervention. I see your future - I see demons. I see destruction. I see the Rift."*

The dragon opens one eye. Stares at you.

*"Perhaps you should prevent the invasion... Before it begins. By destroying the responsible kingdom. NOW, while they're weak. Or... did dragons themselves cause the Rift? Want to discuss this?"*

You see time portals nearby - leading to different points in history."""
        
        choices = [
            {"text": "PACT - Help dragon destroy kingdom NOW", "next": "g1_branch_dragon_dark_pact",
             "effects": {"reputation": -20, "alignment_shift": "evil"}},
            {"text": "WARN - Tell dragon about future, beg for help", "next": "g1_branch_dragon_warning",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 18}},
            {"text": "ATTACK - Kill the dragon while defenseless!", "next": "g1_branch_kill_sleeping_dragon",
             "req": {"type": "stat_check", "stat": "strength", "dc": 20}},
            {"text": "TIME JUMP - Leap into portal to another time", "next": "g1_branch_time_travel"}
        ]
    
    # World state effects - PAST timeline
    state.timeline_marker = "past"
    state.ancient_dragon_awakened = True
    state.demon_invasion_started = False  # Hasn't happened yet
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None
    }


# ==================== MAIN QUEST SCENES (50+) ====================

def get_scene_001_knight_decision(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 001: Decyzja rycerza - po przyjęciu pomocy w Stormhold"""
    if lang == "pl":
        title = "🏰 Misja Honorowa"
        text = f"""**Komandor Rycerzy** prowadzi cię przez zniszczone korytarze fortecy. Wszędzie ranni, płonące bale, krzyki.

Docieracie do sali dowodzenia. Nad stołem rozłożona mapa królestwa.

**\"Widzisz te znaki?\"** - pokazuje czerwone krzyże. **\"To miasta które już upadły. Demony wychodzą z ROZŁAMU.\"**

Wskazuje fioletowy symbol w centrum mapy.

**\"Znajduje się 50 mil stąd, w Dolinie Cieni. Kiedyś było tam święte miejsce. Teraz... otchłań.\"**

Pochyla się nad tobą:

**\"Król oferuje nagrodę: 5000 złotych monet za **ZAMKNIĘCIE ROZŁAMU**. Ale musisz wiedzieć... Nikt dotąd nie wrócił stamtąd żywy.\"**

**\"Rycerze są potrzebni tu, w obronie. Ale ty... ty jesteś Wędrowcem. Masz szansę.\"**

**\"Akceptujesz misję?\"**"""
        
        choices = [
            {"text": "✅ AKCEPTUJ - 'Pójdę do Rozłamu'", "next": "g1_main_002", 
             "effects": {"reputation": 25, "gold": 100}},
            {"text": "🤔 ZAPYTAJ - 'Co dokładnie jest w Rozłamie?'", "next": "g1_main_002_info"},
            {"text": "💰 NEGOCJUJ - 'Chcę 10000, nie 5000'", "next": "g1_main_002_bargain",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16}},
            {"text": "❌ ODMÓW - 'To misja samobójcza, odmawiam'", "next": "g1_branch_refuse_quest"}
        ]
    else:
        title = "🏰 Honor Mission"
        text = f"""**Knight Commander** leads you through the fortress' ruined corridors. Wounded everywhere, burning bales, screams.

You reach the command hall. A kingdom map sprawls across the table.

**\"See these marks?\"** - he points at red crosses. **\"These cities already fell. Demons emerge from THE RIFT.\"**

He indicates a purple symbol at the map's center.

**\"It's 50 miles from here, in Shadow Valley. Once a holy place. Now... an abyss.\"**

He leans toward you:

**\"The King offers a reward: 5000 gold coins for **SEALING THE RIFT**. But you must know... No one returned alive.\"**

**\"Knights are needed here, in defense. But you... you're a Wanderer. You have a chance.\"**

**\"Do you accept the mission?\"**"""
        
        choices = [
            {"text": "✅ ACCEPT - 'I'll go to the Rift'", "next": "g1_main_002",
             "effects": {"reputation": 25, "gold": 100}},
            {"text": "🤔 ASK - 'What exactly is in the Rift?'", "next": "g1_main_002_info"},
            {"text": "💰 BARGAIN - 'I want 10000, not 5000'", "next": "g1_main_002_bargain",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16}},
            {"text": "❌ REFUSE - 'This is suicide, I refuse'", "next": "g1_branch_refuse_quest"}
        ]
    
    # State changes
    state.quest_started = True
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None,
        "location": "stormhold_command"
    }


def get_scene_002_throne_room(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 002: Sala tronowa - audiencja u króla"""
    if lang == "pl":
        title = "👑 Przed Tronem"
        text = """Prowadzą cię do **Sali Tronowej**. 

Ogromna komnata, wysoka na 30 stóp. Witraże przedstaw human dawnych bohaterów. Ale teraz... połowa okien wybitych. Gruz na podłodze.

**Na tronie siedzi KRÓL ALDRIC III.**

Stary człowiek, ale z ogniem w oczach. Korona lekko przekrzywiona. Wygląda na zmęczonego.

**\"Wędrowiec.\"** - mówi głębokim głosem. **\"Słyszałem o twojej pomocy w Stormhold. Masz moje podziękowanie.\"**

Wstaje z tronu i podchodzi bliżej.

**\"Ale teraz... teraz potrzebuję więcej. Rozłam pożera moje królestwo. Moje DZIECI.\"**

Widzisz łzę w jego oku.

**\"Moja córka, Księżniczka Elara, zaginęła podczas ekspedycji zwiadowczej blisko Rozłamu. To było miesiąc temu.\"**

**\"Jeśli ją znajdziesz... jeśli ją URATUSZESZ... dam ci połowę królestwa.\"**

Jego głos drży.

**\"Proszę.\"**"""
        
        choices = [
            {"text": "🛡️ PRZYRZEKAM - 'Znajdę twoją córkę, mój panie'", "next": "g1_main_003",
             "effects": {"reputation": 50, "quest": "save_princess"}},
            {"text": "🤝 'Zrobię co mogę, ale bez obietnic'", "next": "g1_main_003",
             "effects": {"reputation": 25}},
            {"text": "💎 'Połowa królestwa... to intratna oferta'", "next": "g1_main_003_greedy",
             "effects": {"alignment_shift": "neutral"}},
            {"text": "❌ 'Nie jestem ratownikiem, mam zamknąć Rozłam'", "next": "g1_main_003_refuse_princess",
             "effects": {"reputation": -30}}
        ]
    else:
        title = "👑 Before the Throne"
        text = """They escort you to the **Throne Room**.

A massive chamber, 30 feet high. Stained glass depicts ancient heroes. But now... half the windows shattered. Rubble on floor.

**KING ALDRIC III sits on the throne.**

An old man, but with fire in his eyes. Crown slightly askew. Looks exhausted.

**\"Wanderer.\"** - he speaks in a deep voice. **\"I heard of your help at Stormhold. You have my thanks.\"**

He rises from the throne and approaches.

**\"But now... now I need more. The Rift devours my kingdom. My CHILDREN.\"**

You see a tear in his eye.

**\"My daughter, Princess Elara, vanished during a scouting expedition near the Rift. That was a month ago.\"**

**\"If you find her... if you SAVE her... I'll give you half the kingdom.\"**

His voice trembles.

**\"Please.\"**"""
        
        choices = [
            {"text": "🛡️ I SWEAR - 'I'll find your daughter, my lord'", "next": "g1_main_003",
             "effects": {"reputation": 50, "quest": "save_princess"}},
            {"text": "🤝 'I'll do what I can, but no promises'", "next": "g1_main_003",
             "effects": {"reputation": 25}},
            {"text": "💎 'Half a kingdom... that's lucrative'", "next": "g1_main_003_greedy",
             "effects": {"alignment_shift": "neutral"}},
            {"text": "❌ 'I'm not a rescuer, I seal Rifts'", "next": "g1_main_003_refuse_princess",
             "effects": {"reputation": -30}}
        ]
    
    # State tracking
    state.king_alive = True
    state.princess_quest_active = True
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None,
        "location": "royal_palace"
    }


def get_scene_003_rift_discovery(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 003: Odkrycie Rozłamu - pierwsza wizja"""
    if lang == "pl":
        title = "💜 Otchłań"
        text = """Po trzech dniach podróży docierasz do **Doliny Cieni**.

I wtedy to widzisz.

**ROZŁAM.**

PękniĘcie w rzeczywistości.

Fioletowe światło bije z ziemi jak fontanna. **Szczelina szeroka na 100 stóp**, sięgająca w niebo. Powietrze wokół niej drży.

Słyszysz **szepty**.

*\"...dołącz do nas...\"*
*\"...potęga czeka...\"*
*\"...zostań naszym...\"*

Ziemia wokół Rozłamu jest **MARTWA**. Czarna, spękana, dymiąca. Drzewa zamienione w kamień.

Widzisz **obozy demon** - setki namiotów. Ognie. Wrzaski.

**I wtedy... widzisz JĄ.**

**Klatka.** Wisi nad samym Rozłamem, na łańcuchach. W środku - dziewczyna w srebrnej zbroi.

**KSIĘŻNICZKA ELARA.**

Jest żywa. Ale otoczona przez demon-strażników.

**Głos rozbrzmiewa z Rozłamu:**

*\"WĘDROWIEC. Przyszedłeś zamknąć mnie? Głupi. Ja jestem PRZEPUSTKĄ do PRAWDZIWEJ MOCY. Dołącz do nas. Otrzymasz wszystko.\"*"""
        
        choices = [
            {"text": "⚔️ ATAK FRONTALNY - Szarża na obóz demonów!", "next": "g1_main_004_fight",
             "req": {"type": "stat_check", "stat": "strength", "dc": 15}},
            {"text": "🕵️ INFILTRACJA - Poczekaj do nocy, wkradnij się", "next": "g1_main_004_stealth",
             "req": {"type": "stat_check", "stat": "agility", "dc": 14}},
            {"text": "🗣️ NEGOCJACJE - 'Chcę porozmawiać z waszym przywódcą'", "next": "g1_main_004_talk",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16}},
            {"text": "💀 PRZYJMIJ MOC - Sięgnij do Rozłamu...", "next": "g1_branch_dark_pact",
             "effects": {"alignment_shift": "evil"}}
        ]
    else:
        title = "💜 The Abyss"
        text = """After three days' travel you reach **Shadow Valley**.

And then you see it.

**THE RIFT.**

A crack in reality.

Purple light erupts from the ground like a fountain. **A crevice 100 feet wide**, reaching to the sky. Air around it trembles.

You hear **whispers**.

*\"...join us...\"*
*\"...power awaits...\"*
*\"...be our...\"*

The ground around the Rift is **DEAD**. Black, cracked, smoking. Trees turned to stone.

You see **demon camps** - hundreds of tents. Fires. Shrieks.

**And then... you see HER.**

**A cage.** Hanging over the Rift itself, on chains. Inside - a girl in silver armor.

**PRINCESS ELARA.**

She's alive. But surrounded by demon-guards.

**A voice echoes from the Rift:**

*\"WANDERER. You came to seal me? Foolish. I am the GATEWAY to TRUE POWER. Join us. You'll receive everything.\"*"""
        
        choices = [
            {"text": "⚔️ FRONTAL ASSAULT - Charge the demon camp!", "next": "g1_main_004_fight",
             "req": {"type": "stat_check", "stat": "strength", "dc": 15}},
            {"text": "🕵️ INFILTRATION - Wait for night, sneak in", "next": "g1_main_004_stealth",
             "req": {"type": "stat_check", "stat": "agility", "dc": 14}},
            {"text": "🗣️ NEGOTIATE - 'I want to speak with your leader'", "next": "g1_main_004_talk",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16}},
            {"text": "💀 ACCEPT POWER - Reach into the Rift...", "next": "g1_branch_dark_pact",
             "effects": {"alignment_shift": "evil"}}
        ]
    
    # Major state change
    state.rift_discovered = True
    state.princess_found = True
    state.demon_forces = 80
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None,
        "location": "rift_valley"
    }


def get_scene_004_first_demon_boss(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 004: Pierwsze starcie z demonem - BOSS FIGHT"""
    if lang == "pl":
        title = "⚔️ Demon Strażnik"
        text = """Bez względu na twój wybór - demony cię zauważyły.

**ALARM!** Rogi demon zagrały. 

Z głównego namiotu wychodzi COLOSALNY DEMON.

**VARATHUL KRWIOPIJCA.**

10 stóp wysokości. Skóra czarna jak węgiel. Rogi zakrzywione. Oczy płoną czerwienią. W ręku - topór wielkości człowieka.

**"ŚMIERTELNY ODWAŻYŁ SIĘ ZAKŁÓCIĆ OFIARĘ?!"**

Uderza toporem o ziemię - **wybuch ognia**.

**"WALCZ ALBO UMIERAJ!"**

Inne demony tworzą ARENĘ wokół was. Wykrzykują. Chcą widowiska.

**BOSS FIGHT - Varathul Blooddrinker**
**HP: 150 | Atak: +8 | Obrona: 16**
**Specjalne: Co 3 rundy - Ogniowy Wybuch (30 dmg, DC 15 Agility żeby zmniejszyć do 15)**

Co robisz?"""
        
        choices = [
            {"text": "⚔️ ATAK BEZPOŚREDNI - Uderz w korpus (DC 14)", "next": "g1_main_004_combat_1",
             "req": {"type": "combat_action", "target": "varathul", "action": "attack"}},
            {"text": "🛡️ OBRONA + KONTRATAK - Czekaj na otwarcie (DC 12)", "next": "g1_main_004_combat_2",
             "req": {"type": "combat_action", "action": "defend_counter"}},
            {"text": "🏃 UNIK + ATAK NÓŻEM - Szybki ruch (DC 15 Agility)", "next": "g1_main_004_combat_3",
             "req": {"type": "combat_action", "action": "dodge_strike"}},
            {"text": "🔥 UŻYJ MAGII - Jeśli masz (wymaga Mana)", "next": "g1_main_004_combat_magic",
             "req": {"type": "resource_check", "resource": "mana", "amount": 20}}
        ]
    else:
        title = "⚔️ Demon Guardian"
        text = """Regardless of your choice - the demons noticed you.

**ALARM!** Demon horns blared.

A COLOSSAL DEMON emerges from the main tent.

**VARATHUL BLOODDRINKER.**

10 feet tall. Skin black as coal. Horns curved. Eyes burning red. In hand - an axe the size of a man.

**"A MORTAL DARED DISTURB THE SACRIFICE?!"**

He slams the axe into the ground - **fire explosion**.

**"FIGHT OR DIE!"**

Other demons form an ARENA around you. They shout. They want a show.

**BOSS FIGHT - Varathul Blooddrinker**
**HP: 150 | Attack: +8 | Defense: 16**
**Special: Every 3 rounds - Fire Burst (30 dmg, DC 15 Agility to reduce to 15)**

What do you do?"""
        
        choices = [
            {"text": "⚔️ DIRECT ATTACK - Strike the torso (DC 14)", "next": "g1_main_004_combat_1",
             "req": {"type": "combat_action", "target": "varathul", "action": "attack"}},
            {"text": "🛡️ DEFENSE + COUNTER - Wait for opening (DC 12)", "next": "g1_main_004_combat_2",
             "req": {"type": "combat_action", "action": "defend_counter"}},
            {"text": "🏃 DODGE + DAGGER - Quick move (DC 15 Agility)", "next": "g1_main_004_combat_3",
             "req": {"type": "combat_action", "action": "dodge_strike"}},
            {"text": "🔥 USE MAGIC - If you have (requires Mana)", "next": "g1_main_004_combat_magic",
             "req": {"type": "resource_check", "resource": "mana", "amount": 20}}
        ]
    
    # Combat initiated
    state.boss_varathul_encountered = True
    state.combat_active = True
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None,
        "location": "rift_valley",
        "combat": True,
        "boss": "varathul"
    }


def get_scene_005_village_attack(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 005: Napad na wioskę - wybór moralny"""
    if lang == "pl":
        title = "🏘️ Płonąca Wioska"
        text = """Po pokonaniu Varathula (lub ucieczce) słyszysz **KRZYKI** dochodzące z pobliskiej wioski.

Biegniesz tam.

**HORROR.**

Wiostka **PŁONIE**. Demony rwą domy. Ludzie uciekają. Dzieci płaczą.

**Widzisz dwie ścieżki:**

**1)** Po lewej - **Główna grupa demon** (około 20) pali ratusz. W środku uwięzionych jest **50 mieszkańców**.

**2)** Po prawej - **Mniejsze demony** (5-6) goniążane **małą grupę** uciekinierów w stronę lasu. W grupie widzisz **dziecko** - może ma 7 lat.

**NIE MOŻESZ URATOWAĆ OBOICH.**

Jeśli pójdziesz na lewo - dziecko zginie.
Jeśli na prawo - 50 osób w ratuszu spłonie żywcem.

**Na podjęcie decyzji masz 10 sekund zanim ogień pochłonie budynek.**

W oddali słyszysz **głos księżniczki Elary krzyczącej** - nadal jest w klatce nad Rozłamem.

Co robisz?"""
        
        choices = [
            {"text": "⬅️ RATUJ 50 OSÓB - Atak na ratusz (ciężka walka)", "next": "g1_main_006_save_many",
             "effects": {"reputation": 40, "alignment_shift": "good", "deaths": 1}},
            {"text": "➡️ RATUJ DZIECKO - Goń małe demony (łatwiejsza walka)", "next": "g1_main_006_save_child",
             "effects": {"reputation": -20, "alignment_shift": "neutral", "deaths": 50}},
            {"text": "💜 IGNORUJ WSZYSTKO - Biegnij ratować księżniczkę", "next": "g1_main_007_princess_priority",
             "effects": {"reputation": -60, "alignment_shift": "selfish", "deaths": 51}},
            {"text": "🔥 PRÓBUJ OBOICH - Rozdziel się magicznie? (DC 20 Mana)", "next": "g1_main_006_miracle",
             "req": {"type": "resource_check", "resource": "mana", "amount": 50}}
        ]
    else:
        title = "🏘️ Burning Village"
        text = """After defeating Varathul (or fleeing) you hear **SCREAMS** from a nearby village.

You run there.

**HORROR.**

The village is **BURNING**. Demons tear through homes. People flee. Children cry.

**You see two paths:**

**1)** On the left - **Main demon group** (about 20) burning town hall. Inside trapped **50 villagers**.

**2)** On the right - **Smaller demons** (5-6) chasing a **small group** toward the forest. In the group you see a **child** - maybe 7 years old.

**YOU CANNOT SAVE BOTH.**

If you go left - the child dies.
If you go right - 50 people in the hall burn alive.

**You have 10 seconds to decide before fire consumes the building.**

In the distance you hear **Princess Elara screaming** - still in her cage above the Rift.

What do you do?"""
        
        choices = [
            {"text": "⬅️ SAVE 50 PEOPLE - Attack town hall (hard fight)", "next": "g1_main_006_save_many",
             "effects": {"reputation": 40, "alignment_shift": "good", "deaths": 1}},
            {"text": "➡️ SAVE CHILD - Chase small demons (easier fight)", "next": "g1_main_006_save_child",
             "effects": {"reputation": -20, "alignment_shift": "neutral", "deaths": 50}},
            {"text": "💜 IGNORE EVERYTHING - Run to save princess", "next": "g1_main_007_princess_priority",
             "effects": {"reputation": -60, "alignment_shift": "selfish", "deaths": 51}},
            {"text": "🔥 TRY BOTH - Split yourself magically? (DC 20 Mana)", "next": "g1_main_006_miracle",
             "req": {"type": "resource_check", "resource": "mana", "amount": 50}}
        ]
    
    # Critical moral choice
    state.moral_choice_village = "pending"
    
    return {
        "title": title,
        "text": text,
        "choices": choices,
        "image_url": None,
        "location": "burning_village",
        "timed": True,
        "timer_seconds": 10
    }


def get_scene_006_aftermath(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 006: Konsekwencje wyboru w wiosce"""
    if lang == "pl":
        title = "💔 Cena Decyzji"
        text = f"""Dymy unoszą się nad spaloną wioską. Cisza.

{'Uratowałeś 50 mieszkańców z ratusza. Ale dziecko... znaleźli je w lesie. Martwe.' if state.moral_choice_village == 'saved_many' else 'Uratowałeś dziecko. Ale ratusz... znalazłeś tylko zwęglone szczątki 50 osób.' if state.moral_choice_village == 'saved_child' else 'Zignorowałeś wioskę. Wszyscy zginęli. 51 osób.'}

**Stary człowiek siedzący przy studni** patrzy na ciebie pustym wzrokiem.

**"Kto jesteś? Zbawca czy tchórz? Widzę w twoich oczach... ciężar wyboru."**

Wstaje i podchodzi.

**"Dowódca demon... Varathul... przed śmiercią krzyczał coś. Że 'Rozłam ma strażników WEWNĄTRZ królestwa'. Że 'zdrajca siedzi przy królewskim stole'."**

**"Jeśli to prawda... twoja misja może być pułapką."**

Pokazuje ci medalion - symbol Kościoła Świateł.

**"Znaleźliśmy to przy demonach. Oni współpracują z KIMŚ z kościoła."**"""
        
        choices = [
            {"text": "🕵️ WRÓĆ DO STOLICY - Ostrzeż króla!", "next": "g1_main_007",
             "effects": {"reputation": 30}},
            {"text": "⛪ IDŹ DO KOŚCIOŁA - Konfrontuj arcykapłankę", "next": "g1_main_008",
             "effects": {"reputation": 10}},
            {"text": "💜 WRÓĆ DO ROZŁAMU - Księżniczka czeka!", "next": "g1_main_013",
             "effects": {"reputation": -20}},
            {"text": "❓ 'Kim jesteś, staruszku?' - Dowiedz się więcej", "next": "g1_branch_mysterious_elder"}
        ]
    else:
        title = "💔 Price of Choice"
        text = f"""Smoke rises from the burned village. Silence.

{'You saved 50 townsfolk from the hall. But the child... they found it in the forest. Dead.' if state.moral_choice_village == 'saved_many' else 'You saved the child. But the hall... only charred remains of 50 people.' if state.moral_choice_village == 'saved_child' else 'You ignored the village. Everyone died. 51 people.'}

**An old man sitting by the well** looks at you with empty eyes.

**"Who are you? Savior or coward? I see in your eyes... the weight of choice."**

He stands and approaches.

**"Demon commander... Varathul... before death he screamed something. That 'The Rift has guardians INSIDE the kingdom'. That 'a traitor sits at the royal table'."**

**"If true... your mission may be a trap."**

He shows you a medallion - symbol of the Church of Lights.

**"We found this on demons. They collaborate with SOMEONE from the church."**"""
        
        choices = [
            {"text": "🕵️ RETURN TO CAPITAL - Warn the king!", "next": "g1_main_007",
             "effects": {"reputation": 30}},
            {"text": "⛪ GO TO CHURCH - Confront high priestess", "next": "g1_main_008",
             "effects": {"reputation": 10}},
            {"text": "💜 RETURN TO RIFT - Princess waits!", "next": "g1_main_013",
             "effects": {"reputation": -20}},
            {"text": "❓ 'Who are you, old man?' - Learn more", "next": "g1_branch_mysterious_elder"}
        ]
    
    state.betrayal_discovered = True
    
    return {"title": title, "text": text, "choices": choices, "location": "village_ruins"}


def get_scene_007_betrayal_discovery(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 007: Odkrycie zdrady w stolicy"""
    if lang == "pl":
        title = "👑 Zdrada w Stolicy"
        text = """Wracasz do stolicy w pośpiechu. Ulice są... dziwnie puste.

Docierasz do pałacu. Strażnicy wpuszczają cię natychmiast.

**Sala tronowa. Król Aldric leży na tronie... MARTWY. Nóż w sercu.**

**Arcykapłanka stoi obok** w krwawej szacie. Uśmiecha się.

**"Ah, Wędrowiec. Idealny timing. Widzisz tragiczną scenę - król został zamordowany przez... ciebie, oczywiście."**

Wskazuje na strażników otaczających cię.

**"Przyznaj się. Wszyscy wiedzą że byłeś ostatnią osobą która z nim rozmawiała. A teraz wróciłeś dokończyć dzieła."**

**Dowódca Rycerzy** patrzy na ciebie z niedowierzaniem.

**"To prawda? TY to zrobiłeś?"**"""
        
        choices = [
            {"text": "⚖️ 'TO ONA! Ma medalion demon!'", "next": "g1_main_008",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 17}},
            {"text": "⚔️ ZAATAKUJ ARCYKAPŁANKĘ!", "next": "g1_branch_fight_priestess",
             "effects": {"reputation": -40}},
            {"text": "🏃 UCIEKAJ Z PAŁACU!", "next": "g1_branch_escape_palace"},
            {"text": "🛐 'Demony kontrolują kościół...'", "next": "g1_main_008"}
        ]
    else:
        title = "👑 Betrayal in Capital"
        text = """You return to the capital in haste. Streets are... strangely empty.

You reach the palace. Guards let you in immediately.

**Throne room. King Aldric lies on throne... DEAD. Knife in heart.**

**High Priestess stands beside** in bloody robes. She smiles.

**"Ah, Wanderer. Perfect timing. See the tragic scene - king murdered by... you, of course."**

She points at guards surrounding you.

**"Confess. Everyone knows you were last person who spoke with him. Now you returned to finish the job."**

**Knight Commander** looks at you with disbelief.

**"Is it true? YOU did this?"**"""
        
        choices = [
            {"text": "⚖️ 'IT'S HER! She has demon medallion!'", "next": "g1_main_008",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 17}},
            {"text": "⚔️ ATTACK HIGH PRIESTESS!", "next": "g1_branch_fight_priestess",
             "effects": {"reputation": -40}},
            {"text": "🏃 FLEE THE PALACE!", "next": "g1_branch_escape_palace"},
            {"text": "🛐 'Demons control the church...'", "next": "g1_main_008"}
        ]
    
    state.king_alive = False
    state.high_priestess_corrupted = True
    
    return {"title": title, "text": text, "choices": choices, "location": "throne_room", "combat_possible": True}


def get_scene_008_church_infiltration(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 008: Infiltracja kościoła"""
    if lang == "pl":
        title = "⛪ Święte Kłamstwo"
        text = """{'Strażnicy ci nie uwierzyli. Arcykapłanka ucieka w stronę katedry!' if not state.king_alive else 'Idziesz prosto do katedry.'}

**Katedra Świateł** - największa budowla w królestwie. Wysokie wieże. Złote kopuły.

Wchodzisz do środka. **Pustka.**

Nagle słyszysz **śpiew**. W podziemiach.

Schodzisz po schodach. **Sekretna komnata.**

**Widzisz JĄ.**

**Arcykapłanka klęczy przed FIOLETOWYM KRYSZTAŁEM** - kawałkiem Rozłamu, pulsującym mocą demon.

**"Bogowie nas opuścili"** - mówi. **"Ale demony... demony dają PRAWDZIWĄ moc. Król był słaby. Odmówił paktowi."**

Obraca się do ciebie.

**"Dołącz do nas. Razem możemy KONTROLOWAĆ Rozłam. Władać obydwoma światami."**

**Jej oczy płoną FIOLETOWO.**"""
        
        choices = [
            {"text": "⚔️ 'Nigdy!' - Zaatakuj ją!", "next": "g1_main_009",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "🔥 ZNISZCZ KRYSZTAŁ!", "next": "g1_main_009",
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "💀 'Zgadzam się...' - Zdradź królestwo", "next": "g1_branch_join_demons",
             "effects": {"alignment_shift": "evil"}},
            {"text": "🗣️ 'Dokąd prowadzi Rozłam?'", "next": "g1_branch_priestess_talk"}
        ]
    else:
        title = "⛪ Holy Lie"
        text = """{'Guards didn't believe you. High Priestess flees toward cathedral!' if not state.king_alive else 'You go straight to the cathedral.'}

**Cathedral of Lights** - largest structure in kingdom. Tall towers. Golden domes.

You enter inside. **Empty.**

Suddenly you hear **singing**. In the basement.

You descend stairs. **Secret chamber.**

**You see HER.**

**High Priestess kneels before PURPLE CRYSTAL** - a piece of Rift, pulsing with demon power.

**"Gods abandoned us"** - she says. **"But demons... demons give TRUE power. King was weak. Refused the pact."**

She turns to you.

**"Join us. Together we can CONTROL the Rift. Rule both worlds."**

**Her eyes burn PURPLE.**"""
        
        choices = [
            {"text": "⚔️ 'Never!' - Attack her!", "next": "g1_main_009",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "🔥 DESTROY THE CRYSTAL!", "next": "g1_main_009",
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "💀 'I agree...' - Betray kingdom", "next": "g1_branch_join_demons",
             "effects": {"alignment_shift": "evil"}},
            {"text": "🗣️ 'Where does Rift lead?'", "next": "g1_branch_priestess_talk"}
        ]
    
    state.church_influence = 90
    
    return {"title": title, "text": text, "choices": choices, "location": "cathedral_crypt"}


def get_scene_009_cathedral_battle(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 009: Bitwa w katedrze - boss fight"""
    if lang == "pl":
        title = "⚡ Skorumpowana Święta"
        text = """Arcykapłanka **WYBUCHA** fioletową mocą!

**Jej ciało MUTUJE.** Skrzydła demon wyrastają z pleców. Skóra staje się obsydianowa. Oczy - czyste fiolety.

**"GŁUPCZE! Jestem już CZĘŚCIĄ ROZŁAMU!"**

Unosi rękę - **kryształ eksploduje energią**.

**BOSS FIGHT - Arcykapłanka Zariel (Skorumpowana)**
**HP: 200 | Atak: +9 | Obrona: 17**
**Specjalne:**
- **Fioletowy Promień** - 40 dmg (DC 16 Agility)
- **Przywołanie Demon** - spawns 3 imp (25 HP each)
- **Władza Umysłu** - mind control attempt (DC 18 Wisdom)

Katedra trzęsie się. Posągi spadają. To walka na śmierć i życie!

Co robisz?"""
        
        choices = [
            {"text": "⚔️ ATAK BEZPOŚREDNI na skrzydła!", "next": "g1_main_009_combat_1",
             "req": {"type": "combat_action", "action": "attack_wings"}},
            {"text": "🔨 ZNISZCZ KRYSZTAŁ - źródło mocy!", "next": "g1_main_009_combat_2",
             "req": {"type": "combat_action", "action": "destroy_crystal"}},
            {"text": "🛡️ OBRONA + czekaj na otwarcie", "next": "g1_main_009_combat_3"},
            {"text": "📿 PRÓBA EGZORCYZMU (jeśli masz święta moc)", "next": "g1_main_009_exorcism",
             "req": {"type": "resource_check", "resource": "holy_power", "amount": 30}}
        ]
    else:
        title = "⚡ Corrupted Saint"
        text = """High Priestess **EXPLODES** with purple power!

**Her body MUTATES.** Demon wings sprout from back. Skin becomes obsidian. Eyes - pure violet.

**"FOOL! I am already PART OF THE RIFT!"**

She raises hand - **crystal explodes with energy**.

**BOSS FIGHT - High Priestess Zariel (Corrupted)**
**HP: 200 | Attack: +9 | Defense: 17**
**Special:**
- **Violet Ray** - 40 dmg (DC 16 Agility)
- **Summon Demons** - spawns 3 imps (25 HP each)
- **Mind Control** - control attempt (DC 18 Wisdom)

Cathedral shakes. Statues fall. This is fight to death!

What do you do?"""
        
        choices = [
            {"text": "⚔️ DIRECT ATTACK on wings!", "next": "g1_main_009_combat_1",
             "req": {"type": "combat_action", "action": "attack_wings"}},
            {"text": "🔨 DESTROY CRYSTAL - power source!", "next": "g1_main_009_combat_2",
             "req": {"type": "combat_action", "action": "destroy_crystal"}},
            {"text": "🛡️ DEFEND + wait for opening", "next": "g1_main_009_combat_3"},
            {"text": "📿 TRY EXORCISM (if you have holy power)", "next": "g1_main_009_exorcism",
             "req": {"type": "resource_check", "resource": "holy_power", "amount": 30}}
        ]
    
    state.boss_zariel_encountered = True
    state.combat_active = True
    
    return {"title": title, "text": text, "choices": choices, "location": "cathedral_crypt", "combat": True, "boss": "zariel"}


def get_scene_010_ancient_weapon(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 010: Odkrycie starożytnej broni"""
    if lang == "pl":
        title = "⚔️ Broń Przodków"
        text = """Po pokonaniu Arcykapłanki kryształ **pęka**.

Fioletowa moc wycieka, tworząc portal. **Widzisz w nim coś.**

**Starożytna krypta. Za portalem.**

Wchodzisz. Powietrze jest stare, musisz od tysięcy lat.

**Na piedestele leży MIECZ.**

Nie zwykły miecz. **Ostrze świeci BIAŁYM światłem.** Runy pokrywają klingę.

Podchodzisz. **Głos rozbrzmiewa w twojej głowie:**

*"Jestem ŚWIATŁOKLINGA. Wykuty przez pierwszych mędrców by walczyć z Rozłamem. Dotknij mnie, śmiertelny. Sprawdź czy jesteś godny."*

**PRÓBA:** Musisz zdać Strength DC 18 LUB Charisma DC 16 żeby podnieść miecz.

Jeśli fai lujesz - miecz odrzuca cię (30 dmg elektryczne).
Jeśli sukces - otrzymujesz **Lightbringer Sword** (+50 dmg vs demons, heal 10 HP per kill)."""
        
        choices = [
            {"text": "💪 SIŁĄ - Chwyć miecz mocno! (DC 18)", "next": "g1_main_011",
             "req": {"type": "stat_check", "stat": "strength", "dc": 18},
             "reward": {"weapon": "lightbringer", "damage_bonus": 50}},
            {"text": "🗣️ PERSWAZJĄ - 'Jestem godny, widziałem cierpienie' (DC 16)", "next": "g1_main_011",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16},
             "reward": {"weapon": "lightbringer", "damage_bonus": 50}},
            {"text": "🏃 ZOSTAW MIECZ - To pułapka", "next": "g1_main_011"},
            {"text": "🔮 BADAJ RUNY - Dowiedz się więcej", "next": "g1_branch_sword_lore"}
        ]
    else:
        title = "⚔️ Ancestral Weapon"
        text = """After defeating High Priestess, crystal **shatters**.

Purple power leaks, forming a portal. **You see something within.**

**Ancient crypt. Behind portal.**

You enter. Air is old, untouched for millennia.

**On pedestal lies a SWORD.**

Not ordinary sword. **Blade shines WHITE light.** Runes cover blade.

You approach. **Voice echoes in your mind:**

*"I am LIGHTBRINGER. Forged by first sages to fight the Rift. Touch me, mortal. Prove if you are worthy."*

**TEST:** Must pass Strength DC 18 OR Charisma DC 16 to lift sword.

If fail - sword rejects you (30 electric dmg).
If success - receive **Lightbringer Sword** (+50 dmg vs demons, heal 10 HP per kill)."""
        
        choices = [
            {"text": "💪 BY FORCE - Grip sword hard! (DC 18)", "next": "g1_main_011",
             "req": {"type": "stat_check", "stat": "strength", "dc": 18},
             "reward": {"weapon": "lightbringer", "damage_bonus": 50}},
            {"text": "🗣️ BY PERSUASION - 'I am worthy, I've seen suffering' (DC 16)", "next": "g1_main_011",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 16},
             "reward": {"weapon": "lightbringer", "damage_bonus": 50}},
            {"text": "🏃 LEAVE SWORD - It's a trap", "next": "g1_main_011"},
            {"text": "🔮 STUDY RUNES - Learn more", "next": "g1_branch_sword_lore"}
        ]
    
    state.ancient_weapon_found = True
    
    return {"title": title, "text": text, "choices": choices, "location": "ancient_crypt"}


def get_scene_011_underworld_journey(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 011: Podróż do Krainy Umarłych"""
    if lang == "pl":
        title = "💀 Kraina Cieni"
        text = """Z krypty wracasz do powierzchni. **Dowódca Rycerzy czeka.**

**"Słyszałem grzmoty z katedry. Arcykapłanka nie żyje?"**

Kiwasz głową.

**"Dobrze. Ale mamy problem. Księżniczka nadal w klatce. A demons mnożą się. Bez pomocy... przegramy."**

Pochyla głowę.

**"Jest jedno rozwiązanie. Stare legendy mówią o... Krainie Umarłych. Że duchy wielkich królów wciąż tam są. Może pomogą?"**

**"Ale żeby tam dotrzeć... musisz UMRZEĆ."**

Pokazuje ci **czarny puchar** z trucizną.

**"Wypij. Twoje ciało umrze. Dusza zejdzie. Porozmawiaj z duchami. Wróć z pomocą... lub nie wróć wcale."**

**"To ryzyko. Ale może jedyna szansa."**"""
        
        choices = [
            {"text": "☠️ WYPIJ TRUCIZNĘ - Zejdź do Krainy Umarłych", "next": "g1_main_012",
             "effects": {"temp_death": True}},
            {"text": "❌ ODMÓW - 'Znajdę inny sposób'", "next": "g1_main_013"},
            {"text": "🤔 'Czy jest inny sposób dotarcia tam?'", "next": "g1_branch_alternative_underworld"},
            {"text": "🗡️ 'Nie potrzebuję duchów. Mam miecz.'", "next": "g1_main_013"}
        ]
    else:
        title = "💀 Land of Shadows"
        text = """From crypt you return to surface. **Knight Commander waits.**

**"I heard thunder from cathedral. High Priestess dead?"**

You nod.

**"Good. But we have problem. Princess still in cage. Demons multiply. Without help... we lose."**

He bows head.

**"There's one solution. Old legends speak of... Land of Dead. That spirits of great kings still there. Maybe they help?"**

**"But to reach there... you must DIE."**

He shows you **black chalice** with poison.

**"Drink. Your body dies. Soul descends. Talk with spirits. Return with help... or don't return at all."**

**"It's risk. But maybe only chance."**"""
        
        choices = [
            {"text": "☠️ DRINK POISON - Descend to Land of Dead", "next": "g1_main_012",
             "effects": {"temp_death": True}},
            {"text": "❌ REFUSE - 'I'll find another way'", "next": "g1_main_013"},
            {"text": "🤔 'Is there another way to reach there?'", "next": "g1_branch_alternative_underworld"},
            {"text": "🗡️ 'I don't need ghosts. I have sword.'", "next": "g1_main_013"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "palace_ruins"}


def get_scene_012_ghost_king(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 012: Spotkanie z Duchem Króla"""
    if lang == "pl":
        title = "👻 Duchy Przodków"
        text = """Ciemność. Zimno. **Umarłeś.**

Ale świadomość pozostaje.

Otwierasz oczy. **Kraina Umarłych.**

Wszystko jest SZARE. Mgła. Duchy unoszą się wokół. Szepty.

**Przed tobą stoi DUCH** w królewskiej koronie. Przejrzysty. Stary.

**"Śmiertelny odważył się tu przyjść za życia... ciekawe."**

To **Król Aldric II** - ojciec obecnego króla (teraz martwego).

**"Widzę co się stało. Mój syn nie żyje. Królestwo pada. Rozłam rośnie."**

**"Mogę ci pomóc. Armia duchów może walczyć przy tobie. ALE..."**

Jego oczy stają się zimne.

**"...musisz mi coś obiecać. Zabij WSZYSTKICH odpowiedzialnych za otwarcie Rozłamu. Demony. Zdrajców. WSZYSTKICH."**

**"Bez litości. Bez wahania. To moja cena."**"""
        
        choices = [
            {"text": "⚔️ 'Przysięgam. Wszyscy zginą.'", "next": "g1_main_013",
             "effects": {"reputation": -30, "alignment_shift": "ruthless", "ghost_army": True}},
            {"text": "⚖️ 'Zabiję winnych. Ale oszczędzę niewinnych.'", "next": "g1_main_013",
             "effects": {"reputation": 20, "ghost_army_limited": True}},
            {"text": "❌ 'Nie mogę tego obiecać.'", "next": "g1_main_013",
             "effects": {"ghost_army": False}},
            {"text": "❓ 'Kto NAPRAWDĘ otworzył Rozłam?'", "next": "g1_branch_rift_origin"}
        ]
    else:
        title = "👻 Ghosts of Ancestors"
        text = """Darkness. Cold. **You died.**

But consciousness remains.

You open eyes. **Land of Dead.**

Everything is GREY. Fog. Ghosts float around. Whispers.

**Before you stands GHOST** in royal crown. Translucent. Old.

**"Mortal dared come here while alive... interesting."**

This is **King Aldric II** - father of current king (now dead).

**"I see what happened. My son dead. Kingdom falls. Rift grows."**

**"I can help you. Army of ghosts can fight with you. BUT..."**

His eyes turn cold.

**"...you must promise something. Kill ALL responsible for opening Rift. Demons. Traitors. ALL."**

**"No mercy. No hesitation. That's my price."**"""
        
        choices = [
            {"text": "⚔️ 'I swear. All will die.'", "next": "g1_main_013",
             "effects": {"reputation": -30, "alignment_shift": "ruthless", "ghost_army": True}},
            {"text": "⚖️ 'I'll kill guilty. But spare innocent.'", "next": "g1_main_013",
             "effects": {"reputation": 20, "ghost_army_limited": True}},
            {"text": "❌ 'I can't promise that.'", "next": "g1_main_013",
             "effects": {"ghost_army": False}},
            {"text": "❓ 'Who REALLY opened Rift?'", "next": "g1_branch_rift_origin"}
        ]
    
    state.ghost_king_pact = True
    
    return {"title": title, "text": text, "choices": choices, "location": "underworld"}


def get_scene_013_final_siege(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 013: Ostatnie oblężenie stolicy"""
    if lang == "pl":
        title = "🔥 Ostatnia Bitwa"
        text = """{'Budzisz się. Trucizna przestała działać. Armia duchów za tobą.' if state.ghost_king_pact else 'Wracasz z odmową duchów. Sam musisz walczyć.'}

**Stolica POD ATAKIEM.**

Demons szturmują mury. Tysiące. **Niebo jest FIOLETOWE.**

Rozłam **ROZRÓSŁ SIĘ** - teraz zajmuje pół horyzontu. Portal wielkości miasta.

Z Rozłamu wychodzi **KOLOSALNY DEMON** - 50 stóp wysokości.

**PAN DEMONÓW - AZATHUL NISZCZYCIEL.**

**"ŚMIERTELNI! Wasza era się kończy! To świat należy TERAZ do nas!"**

Dowódca Rycerzy krzyczy:

**"TO JEST TO! OSTATNIA SZANSA! Jeśli nie zamkniemy Rozłamu TERAZ - wszystko przepadnie!"**

{'Duchy atakują demony! Chaos!' if state.ghost_king_pact else ''}

**"Wędrowiec! Musisz dotrzeć do SERCA ROZŁAMU! Tam jest pieczęć! Użyj {'Światłoklingi!' if state.ancient_weapon_found else 'jakiejkolwiek mocy jaką masz!'}**

Co robisz?"""
        
        choices = [
            {"text": "⚔️ SZARŻA przez pole bitwy DO ROZŁAMU!", "next": "g1_main_014",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "🕊️ PRÓBUJ NEGOCJOWAĆ z Panem Demonów", "next": "g1_branch_negotiate_demon_lord",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 20}},
            {"text": "🔥 WALCZ z Azathulem - zabij Pana Demonów!", "next": "g1_branch_fight_demon_lord",
             "req": {"type": "combat_check"}},
            {"text": "💜 PRZYJMIJ MOC ROZŁAMU - zostań władcą", "next": "g1_end_demon_lord",
             "effects": {"alignment_shift": "evil"}}
        ]
    else:
        title = "🔥 Final Battle"
        text = """{'You wake. Poison stopped. Ghost army behind you.' if state.ghost_king_pact else 'You return without ghosts. Must fight alone.'}

**Capital UNDER ATTACK.**

Demons storm walls. Thousands. **Sky is PURPLE.**

Rift has **GROWN** - now takes half the horizon. Portal size of city.

From Rift emerges **COLOSSAL DEMON** - 50 feet tall.

**DEMON LORD - AZATHUL DESTROYER.**

**"MORTALS! Your era ends! This world belongs NOW to us!"**

Knight Commander shouts:

**"THIS IS IT! LAST CHANCE! If we don't seal Rift NOW - everything lost!"**

{'Ghosts attack demons! Chaos!' if state.ghost_king_pact else ''}

**"Wanderer! Must reach RIFT HEART! Seal is there! Use {'Lightbringer!' if state.ancient_weapon_found else 'whatever power you have!'}**

What do you do?"""
        
        choices = [
            {"text": "⚔️ CHARGE through battlefield TO RIFT!", "next": "g1_main_014",
             "req": {"type": "stat_check", "stat": "strength", "dc": 16}},
            {"text": "🕊️ TRY NEGOTIATE with Demon Lord", "next": "g1_branch_negotiate_demon_lord",
             "req": {"type": "stat_check", "stat": "charisma", "dc": 20}},
            {"text": "🔥 FIGHT Azathul - kill Demon Lord!", "next": "g1_branch_fight_demon_lord",
             "req": {"type": "combat_check"}},
            {"text": "💜 ACCEPT RIFT POWER - become ruler", "next": "g1_end_demon_lord",
             "effects": {"alignment_shift": "evil"}}
        ]
    
    state.final_battle_started = True
    state.demon_forces = 100
    
    return {"title": title, "text": text, "choices": choices, "location": "capital_battlefield", "epic": True}


def get_scene_014_seal_rift(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 014: Zamknięcie Rozłamu"""
    if lang == "pl":
        title = "💜 Pieczęć Rozłamu"
        text = """Biegniesz przez pole bitwy. Demons atakują. {'Duchy chronią cię.' if state.ghost_king_pact else 'Ledwo przeżywasz.'}

Docierasz do **BRZEGU ROZŁAMU.**

Fioletowa otchłań. Energia wybucha. Słyszysz **miliony głosów** demon.

**W centrum - PIECZĘĆ.** Starożytny symbol. **Pęknięty.**

{'Świątłoklinga wibruje w twojej ręce. Wie co robić.' if state.ancient_weapon_found else 'Musisz użyć własnej mocy.'}

**NAGLE - KSIĘŻNICZKA ELARA!**

Klatka spada obok ciebie! Jest żywa ale słaba.

**"Wędrowiec... zamknij Rozłam... ale... jeśli to zrobisz... ja zginę. Jestem... połączona z Rozłamem. To... pułapka demon..."**

**WYBÓR:**

1) Zamknij Rozłam - Księżniczka zginie, ale królestwo uratowane
2) Zostaw Rozłam otwarty - Księżniczka żyje, ale świat pada
3) Spróbuj znaleźć inne rozwiązanie (wymaga magii DC 20)"""
        
        choices = [
            {"text": "⚔️ ZAMKNIJ ROZŁAM - ratuj królestwo", "next": "g1_main_015",
             "effects": {"princess_dead": True, "reputation": 100}},
            {"text": "💔 ZOSTAW OTWARTY - ratuj ksieżniczkę", "next": "g1_end_stalemate",
             "effects": {"princess_alive": True, "reputation": -80}},
            {"text": "🔮 ZNAJDŹ INNE ROZWIĄZANIE (DC 20 Mana)", "next": "g1_main_015_miracle",
             "req": {"type": "resource_check", "resource": "mana", "amount": 100}},
            {"text": "💜 WCHŁOŃ MOC ROZŁAMU - zostań bogiem", "next": "g1_end_demon_lord",
             "effects": {"alignment_shift": "evil"}}
        ]
    else:
        title = "💜 Rift Seal"
        text = """You run through battlefield. Demons attack. {'Ghosts protect you.' if state.ghost_king_pact else 'Barely survive.'}

You reach **RIFT EDGE.**

Purple abyss. Energy explodes. You hear **millions of voices** of demons.

**In center - SEAL.** Ancient symbol. **Cracked.**

{'Lightbringer vibrates in your hand. Knows what to do.' if state.ancient_weapon_found else 'Must use own power.'}

**SUDDENLY - PRINCESS ELARA!**

Cage falls beside you! She's alive but weak.

**"Wanderer... seal Rift... but... if you do... I die. I'm... connected to Rift. It's... demon trap..."**

**CHOICE:**

1) Seal Rift - Princess dies, kingdom saved
2) Leave Rift open - Princess lives, world falls
3) Try find other solution (requires magic DC 20)"""
        
        choices = [
            {"text": "⚔️ SEAL RIFT - save kingdom", "next": "g1_main_015",
             "effects": {"princess_dead": True, "reputation": 100}},
            {"text": "💔 LEAVE OPEN - save princess", "next": "g1_end_stalemate",
             "effects": {"princess_alive": True, "reputation": -80}},
            {"text": "🔮 FIND OTHER SOLUTION (DC 20 Mana)", "next": "g1_main_015_miracle",
             "req": {"type": "resource_check", "resource": "mana", "amount": 100}},
            {"text": "💜 ABSORB RIFT POWER - become god", "next": "g1_end_demon_lord",
             "effects": {"alignment_shift": "evil"}}
        ]
    
    state.rift_activity = "unstable"
    
    return {"title": title, "text": text, "choices": choices, "location": "rift_heart", "critical": True}


def get_scene_015_coronation(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 015: Koronacja - heroic ending"""
    if lang == "pl":
        title = "👑 Nowy Świt"
        text = """{'Wbijasz Światłoklingę w pieczęć.' if state.ancient_weapon_found else 'Używasz całej swojej mocy.'}

**WYBUCH ŚWIATŁA!**

Rozłam **ZAMYKA SIĘ.** Fioletowa energia imploduje. Demons krzyczą i są wciągani z powrotem.

**Ciemność ustępuje. Niebo staje się NIEBIESKIE po raz pierwszy od miesięcy.**

Księżniczka {'umiera w twoich ramionach. Jej ostatnie słowa: "Dziękuję... bohaterze..."' if state.princess_dead else 'ŻYJE! Okazało się że była inna metoda!'}

**Tydzień później.**

**Koronacja.**

{'Nowy król (brat księżniczki)' if state.princess_dead else 'Księżniczka Elara'} wstępuje na tron.

**"Dzisiaj honorujemy BOHATERA który uratował królestwo. Wędrowiec - klęknij."**

Kłękasz.

**"Mianujuję cię OBROŃCĄ KRÓLESTWA. Twoją statua będzie stała w centrum stolicy. Nigdy nie zapomnimy."**

Tłum wiwatuje. Wojna się skończyła.

Ale ty wiesz... **to tylko PIERWSZA BRAMĘ.**

**Zostało jeszcze 8 wymiarów.**

**GATE 1 - UKOŃCZONA**
**Cosmic Influence:** +150
**Reputation:** Legendary Hero
**Tytuł:** Pieczętowicz Rozłamu"""
        
        choices = [
            {"text": "✅ WRÓĆ DO PRZYLĄDKA", "next": "return_to_precipice"},
            {"text": "🌟 SPRAWDŹ STATYSTYKI", "next": "show_stats"},
            {"text": "🔮 CO DALEJ?", "next": "next_gate_preview"}
        ]
    else:
        title = "👑 New Dawn"
        text = """{'You thrust Lightbringer into seal.' if state.ancient_weapon_found else 'Use all your power.'}

**EXPLOSION OF LIGHT!**

Rift **CLOSES.** Purple energy implodes. Demons scream and are sucked back.

**Darkness recedes. Sky becomes BLUE for first time in months.**

Princess {'dies in your arms. Her last words: "Thank you... hero..."' if state.princess_dead else 'LIVES! Turns out there was another method!'}

**Week later.**

**Coronation.**

{'New king (princess' brother)' if state.princess_dead else 'Princess Elara'} ascends throne.

**"Today we honor HERO who saved kingdom. Wanderer - kneel."**

You kneel.

**"I name you DEFENDER OF KINGDOM. Your statue will stand in capital center. We'll never forget."**

Crowd cheers. War ended.

But you know... **this was only FIRST GATE.**

**8 dimensions remain.**

**GATE 1 - COMPLETED**
**Cosmic Influence:** +150
**Reputation:** Legendary Hero
**Title:** Rift Sealer"""
        
        choices = [
            {"text": "✅ RETURN TO PRECIPICE", "next": "return_to_precipice"},
            {"text": "🌟 CHECK STATISTICS", "next": "show_stats"},
            {"text": "🔮 WHAT'S NEXT?", "next": "next_gate_preview"}
        ]
    
    state.capital_status = "safe"
    state.rift_activity = "sealed"
    state.quest_completed = True
    
    return {"title": title, "text": text, "choices": choices, "location": "throne_room", "ending": True}


# ==================== BRANCH SCENES ====================

def get_branch_attack_knight(lang: str, state: Gate1WorldState, player) -> Dict:
    """Branch: Atak na rycerza - dark path"""
    
    if lang == "pl":
        text = f"""Wyciągasz broń i **atakujesz rycerza**!

Ale to weteran setek bitew. Widzi twój ruch milę dalej.

**CLASH!** Wasze ostrza zderzają się!

**"Ty CHORze!"** - krzyczy, parując twój cios.

Inni strażnicy natychmiast cię otaczają. Jesteś w okrążeniu.

**"ZŁÓDZIEJ! OSZUST! ZABIĆ GO!"**

Co robisz TERAZ?"""
        
        choices = [
            {"text": "⚔️ Walcz do końca! (DC 18)", "next_scene": "g1_branch_fight_guards", "requires_roll": True, "stat": "strength", "dc": 18},
            {"text": "🏃 Uciekaj! Skocz z muru!", "next_scene": "g1_branch_escape_fortress", "damage": 20},
            {"text": "🙏 'Przepraszam! To był impuls!'", "next_scene": "g1_branch_grovel", "effect": {"reputation": -50}},
        ]
    else:
        text = f"""You draw your weapon and **attack the knight**!

But he's a veteran of hundreds of battles. He sees your move a mile away.

**CLASH!** Your blades meet!

**"You BASTARD!"** - he shouts, parrying your strike.

Other guards immediately surround you. You're outnumbered.

**"THIEF! TRAITOR! KILL HIM!"**

What do you do NOW?"""
        
        choices = [
            {"text": "⚔️ Fight to the end! (DC 18)", "next_scene": "g1_branch_fight_guards", "requires_roll": True, "stat": "strength", "dc": 18},
            {"text": "🏃 Flee! Jump from the wall!", "next_scene": "g1_branch_escape_fortress", "damage": 20},
            {"text": "🙏 'I'm sorry! It was impulse!'", "next_scene": "g1_branch_grovel", "effect": {"reputation": -50}},
        ]
    
    return {
        "title": "Zdrada" if lang == "pl" else "Betrayal",
        "text": text,
        "choices": choices,
        "location": "stormhold_keep",
        "combat": True
    }


def get_branch_help_villagers(lang: str, state: Gate1WorldState, player) -> Dict:
    """Branch: Pomoc wiośnianom"""
    # TODO: Implement branch scenes
    return {
        "title": "TODO",
        "text": "Scene not implemented yet.",
        "choices": [],
        "image_url": None
    }


# ==================== ENDINGS ====================

def get_ending_kingdom_saved(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Królestwo uratowane"""
    # TODO: Implement endings
    pass


def get_ending_demon_lord(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Zostałeś władcą demonów"""
    pass


def get_ending_dragon_pact(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Pakt ze smokiem"""
    pass
