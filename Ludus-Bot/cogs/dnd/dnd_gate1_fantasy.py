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
        
        # Quest Progress Flags (unlock system)
        self.quest_flags = {
            "kingdom_quest_started": False,
            "kingdom_quest_complete": False,
            "dragon_discovered": False,
            "dragon_pact_offered": False,
            "dragon_hostile": False,
            "rebellion_contacted": False,
            "rebellion_allied": False,
            "rebellion_destroyed": False,
            "artifact_sword_obtained": False,
            "artifact_shield_obtained": False,
            "artifact_crown_obtained": False,
            "artifact_book_obtained": False,
            "artifact_heart_obtained": False,
            "dark_pact_accepted": False,
            "ghost_army_obtained": False,
            "lightbringer_obtained": False,
            "varathul_defeated": False,
            "zariel_defeated": False,
            "villages_saved": 0,  # counter
            "moral_alignment": "neutral",  # "good", "neutral", "evil"
        }
        
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
    
    # WĄTEK B: SMOK (016-025)
    elif scene_id == "g1_main_016":
        return get_scene_016_dragon_legend(lang, world_state, player_data)
    
    elif scene_id == "g1_main_017":
        return get_scene_017_mountain_journey(lang, world_state, player_data)
    
    elif scene_id == "g1_main_018":
        return get_scene_018_dragon_negotiation(lang, world_state, player_data)
    
    elif scene_id == "g1_main_019":
        return get_scene_019_dragon_trial(lang, world_state, player_data)
    
    elif scene_id == "g1_main_020":
        return get_scene_020_dragon_pact(lang, world_state, player_data)
    
    # WĄTEK C: REBELIA (026-035)
    elif scene_id == "g1_main_026":
        return get_scene_026_forest_rebels(lang, world_state, player_data)
    
    elif scene_id == "g1_main_027":
        return get_scene_027_rebellion_truth(lang, world_state, player_data)
    
    # WĄTEK D: ARTEFAKTY (036-045)
    elif scene_id == "g1_main_036":
        return get_scene_036_artifact_map(lang, world_state, player_data)
    
    elif scene_id == "g1_main_037":
        return get_scene_037_sword_artifact(lang, world_state, player_data)
    
    elif scene_id == "g1_main_038":
        return get_scene_038_shield_artifact(lang, world_state, player_data)
    
    # WĄTEK E: MROCZNA ŚCIEŻKA (046-050)
    elif scene_id == "g1_main_046":
        return get_scene_046_dark_rebellion(lang, world_state, player_data)
    
    elif scene_id == "g1_main_047":
        return get_scene_047_assassination_spree(lang, world_state, player_data)
    
    elif scene_id == "g1_main_048":
        return get_scene_048_rift_control(lang, world_state, player_data)
    
    elif scene_id == "g1_main_049":
        return get_scene_049_demon_lord_power(lang, world_state, player_data)
    
    elif scene_id == "g1_main_050":
        return get_scene_050_ultimate_power(lang, world_state, player_data)
    
    # TODO: Implement remaining scenes and branches
    
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
    
    elif scene_id == "g1_end_stalemate":
        return get_ending_stalemate(lang, world_state, player_data)
    
    elif scene_id == "g1_end_sacrifice":
        return get_ending_sacrifice(lang, world_state, player_data)
    
    elif scene_id == "g1_end_reshape_reality":
        return get_ending_reshape_reality(lang, world_state, player_data)
    
    elif scene_id == "g1_end_eternal_throne":
        return get_ending_eternal_throne(lang, world_state, player_data)
    
    elif scene_id == "g1_end_dragon_merge":
        return get_ending_dragon_merge(lang, world_state, player_data)
    
    elif scene_id == "g1_end_exile":
        return get_ending_exile(lang, world_state, player_data)
    
    elif scene_id == "g1_end_timeloop":
        return get_ending_timeloop(lang, world_state, player_data)
    
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
    state.quest_flags["kingdom_quest_complete"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "throne_room", "ending": True}


# ==================== WĄTEK B: SMOK (016-025) ====================

def get_scene_016_dragon_legend(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 016: Legenda o śpiącym smoku - REQUIRES: heard rumors"""
    if lang == "pl":
        title = "🐉 Opowieści Strażników"
        text = """W tawernie po bitwie słyszysz rozmowę starych strażników.

**"...słyszałeś legendę o Drakonie z Gór Ognia? Mówią że śpi tam od tysiąca lat..."**

**"To głupoty! Smokiew wyginęły!"**

**"A może właśnie smok STWORZYŁ Rozłam? Pomyśl - fioletowa magia to NIE magia ludzi..."**

Podchodzisz do nich."""
        
        choices = [
            {"text": "🗣️ 'Opowiedzcie mi o smoku'", "next": "g1_main_017"},
            {"text": "🍺 'Postaw im rundy, wyciągnij info'", "next": "g1_main_017", 
             "req": {"type": "resource_check", "resource": "gold", "amount": 50}},
            {"text": "⚔️ 'Gdzie te góry?! Zabijęgo!'", "next": "g1_main_017",
             "effects": {"dragon_hostile": True}},
            {"text": "❌ Ignoruj - wróć do głównego questu", "next": "g1_main_002"}
        ]
    else:
        title = "🐉 Guardsmen Tales"
        text = """In tavern after battle you hear old guardsmen talking.

**"...heard the legend of Dragon from Fire Mountains? They say it sleeps there for thousand years..."**

**"That's nonsense! Dragons are extinct!"**

**"Or maybe dragon CREATED the Rift? Think - purple magic is NOT human magic..."**

You approach them."""
        
        choices = [
            {"text": "🗣️ 'Tell me about the dragon'", "next": "g1_main_017"},
            {"text": "🍺 'Buy them rounds, extract info'", "next": "g1_main_017",
             "req": {"type": "resource_check", "resource": "gold", "amount": 50}},
            {"text": "⚔️ 'Where are those mountains?! I'll kill it!'", "next": "g1_main_017",
             "effects": {"dragon_hostile": True}},
            {"text": "❌ Ignore - return to main quest", "next": "g1_main_002"}
        ]
    
    state.quest_flags["dragon_discovered"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "tavern"}


def get_scene_017_mountain_journey(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 017: Wyprawa do gór"""
    if lang == "pl":
        title = "⛰️ Góry Ognia"
        text = """Podróż trwa tydzień. Góry rosną przed tobą - szczyty dymiące, lawowe rzeki.

**To wulkaniczny region.**

Docierasz do ogromnej jaskini. Wejście szerokość 100 stóp. **Ślady pazurów na skale.**

Powietrze gorące. Słyszysz... **oddech.**

Głęboki. Powolny. Coś OGROMNEGO śpi w środku.

{'Światłoklinga drży w twojej ręce. Ostrzega.' if state.quest_flags.get("lightbringer_obtained") else 'Instynkt krzyczy: NIEBEZPIECZEŃSTWO.'}"""
        
        choices = [
            {"text": "👣 Wejdź CICHO - spróbuj nie obudzić", "next": "g1_main_018",
             "req": {"type": "stat_check", "stat": "agility", "dc": 14}},
            {"text": "📢 ZAWOŁAJ - 'Smoku! Chcę rozmawiać!'", "next": "g1_main_018"},
            {"text": "⚔️ Zakradnij się i ZAATAKUJ śpiącego", "next": "g1_branch_ambush_dragon",
             "effects": {"dragon_hostile": True, "alignment_shift": "evil"}},
            {"text": "🔙 Wróć - to zbyt ryzykowne", "next": "g1_main_002"}
        ]
    else:
        title = "⛰️ Fire Mountains"
        text = """Journey takes a week. Mountains grow before you - smoking peaks, lava rivers.

**This is volcanic region.**

You reach huge cavern. Entrance 100 feet wide. **Claw marks on stone.**

Air is hot. You hear... **breathing.**

Deep. Slow. Something ENORMOUS sleeps inside.

{'Lightbringer trembles in your hand. Warning.' if state.quest_flags.get("lightbringer_obtained") else 'Instinct screams: DANGER.'}"""
        
        choices = [
            {"text": "👣 Enter QUIETLY - try not to wake", "next": "g1_main_018",
             "req": {"type": "stat_check", "stat": "agility", "dc": 14}},
            {"text": "📢 CALL OUT - 'Dragon! I want to talk!'", "next": "g1_main_018"},
            {"text": "⚔️ Sneak and ATTACK sleeping dragon", "next": "g1_branch_ambush_dragon",
             "effects": {"dragon_hostile": True, "alignment_shift": "evil"}},
            {"text": "🔙 Return - too risky", "next": "g1_main_002"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "dragon_lair_entrance"}


def get_scene_018_dragon_negotiation(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 018: Negocjacje ze smokiem"""
    dragon_hostile = state.quest_flags.get("dragon_hostile", False)
    
    if lang == "pl":
        title = "🐲 Żywa Legenda" if not dragon_hostile else "🐲 Gniew Smoka"
        text = """{'SMOK BUDZI SIĘ!!' if not dragon_hostile else 'SMOK JUŻ CZEKA!!'}

**PYRAXIS PŁOMIENIOSERCE** - długość 200 stóp. Łuski czerwone jak lawa. Oczy złote. Dym wydobywa się z nozdrzy.

{'Głos rozbrzmiewa w twojej głowie - nie porusza paszczą:' if not dragon_hostile else 'Ryczy z furią:'}

{'**"Śmiertelny odważył się wejść do mojej siedziby. Ciekawe. Czuję zapach... Rozłamu na tobie. Więc TO już się zaczęło."**' if not dragon_hostile else '**"TCHÓRZU! Chciałeś mnie zabić przez sen?! PŁAĆ ŻYCIEM!"**'}

{'Smok siada, patrzy na ciebie z góry.' if not dragon_hostile else 'Smok przygotowuje ogień w gardle!'}

{'**"Mów szybko, śmiertelny. Czego chcesz? I dlaczego nie powinienem cię ZJEŚĆ?"**' if not dragon_hostile else '**DC 20 Charisma żeby go uspokoić - albo WALKA!**'}"""
        
        if not dragon_hostile:
            choices = [
                {"text": "🤝 'Potrzebuję pomocy zamknąć Rozłam'", "next": "g1_main_019"},
                {"text": "❓ 'Czy to TY otworzyłeś Rozłam?'", "next": "g1_main_019",
                 "effects": {"dragon_offended": True}},
                {"text": "💎 'Zaoferuję skarbcy za pomoc'", "next": "g1_main_019",
                 "req": {"type": "resource_check", "resource": "gold", "amount": 5000}},
                {"text": "⚔️ 'Walczę zamiast gadać!' - ATAK", "next": "g1_branch_fight_dragon",
                 "effects": {"dragon_hostile": True}}
            ]
        else:
            choices = [
                {"text": "🗣️ PRÓBA USPOKOJENIA (DC 20)", "next": "g1_main_019",
                 "req": {"type": "stat_check", "stat": "charisma", "dc": 20}},
                {"text": "⚔️ WALCZ - nie masz wyboru!", "next": "g1_branch_fight_dragon"},
                {"text": "🏃 UCIECZKA - biegnij z jaskini!", "next": "g1_main_002",
                 "effects": {"reputation": -50}}
            ]
    else:
        title = "🐲 Living Legend" if not dragon_hostile else "🐲 Dragon's Wrath"
        text = """{'DRAGON AWAKENS!!' if not dragon_hostile else 'DRAGON ALREADY WAITING!!'}

**PYRAXIS FLAMEHEART** - 200 feet long. Scales red as lava. Eyes golden. Smoke from nostrils.

{'Voice echoes in your mind - doesn't move jaws:' if not dragon_hostile else 'Roars with fury:'}

{'**"Mortal dared enter my domain. Interesting. I smell... Rift on you. So IT has begun."**' if not dragon_hostile else '**"COWARD! You wanted to kill me in sleep?! PAY WITH LIFE!"**'}

{'Dragon sits, looks down at you.' if not dragon_hostile else 'Dragon prepares fire in throat!'}

{'**"Speak quickly, mortal. What do you want? And why shouldn't I EAT you?"**' if not dragon_hostile else '**DC 20 Charisma to calm - or FIGHT!**'}"""
        
        if not dragon_hostile:
            choices = [
                {"text": "🤝 'I need help sealing the Rift'", "next": "g1_main_019"},
                {"text": "❓ 'Did YOU open the Rift?'", "next": "g1_main_019",
                 "effects": {"dragon_offended": True}},
                {"text": "💎 'I'll offer treasure for help'", "next": "g1_main_019",
                 "req": {"type": "resource_check", "resource": "gold", "amount": 5000}},
                {"text": "⚔️ 'Fight instead of talk!' - ATTACK", "next": "g1_branch_fight_dragon",
                 "effects": {"dragon_hostile": True}}
            ]
        else:
            choices = [
                {"text": "🗣️ TRY CALM (DC 20)", "next": "g1_main_019",
                 "req": {"type": "stat_check", "stat": "charisma", "dc": 20}},
                {"text": "⚔️ FIGHT - no choice!", "next": "g1_branch_fight_dragon"},
                {"text": "🏃 FLEE - run from cavern!", "next": "g1_main_002",
                 "effects": {"reputation": -50}}
            ]
    
    state.ancient_dragon_awakened = True
    
    return {"title": title, "text": text, "choices": choices, "location": "dragon_lair", "epic": True}


def get_scene_019_dragon_trial(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 019: Próba smoka - honorowy pojedynek"""
    if lang == "pl":
        title = "⚔️ Próba Ognia"
        text = """Smok słucha twojej prośby. Milczy długo.

**"Ciekawe. Śmiałość masz... ale CZY wartość?"**

**"Smokii nie pomagają słabym. Jesteśmy dumni. Musisz przejść PRÓBĘ."**

Smok się zmniejsza - teraz ma "tylko" 30 stóp.

**"Walcz ze mną. Pokroć 3 rundy. JEŚLI przeżyjesz - pomogę. Jeśli nie... zostaniesz prochem."**

**"Zaczynam TERAZ."**

**BOSS FIGHT - Pyraxis (Trial Mode)**
**HP: 300 | Atak: +10 | Obrona: 18**
**Specjalne:**
- **Przedmuch Ognia** - 50 dmg cone (DC 17 Agility half)
- **Atak Ogonem** - 40 dmg + knockdown
- **Lot** - unika fizycznych ataków 2 rundy

**WARUNEK ZWYCIĘSTWA:** Przeżyj 3 rundy LUB zadaj 150+ dmg"""
        
        choices = [
            {"text": "⚔️ ATAK BEZPOŚREDNI", "next": "g1_main_020_combat",
             "req": {"type": "combat_action"}},
            {"text": "🛡️ OBRONA - przetrwaj", "next": "g1_main_020_combat"},
            {"text": "🏹 DYSTANS - atakuj z daleka", "next": "g1_main_020_combat",
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "🗣️ 'Jest inny sposób próby?'", "next": "g1_branch_alternative_trial"}
        ]
    else:
        title = "⚔️ Trial of Fire"
        text = """Dragon listens to your request. Silent for long.

**"Interesting. You have boldness... but DO you have worth?"**

**"Dragons don't help the weak. We are proud. You must pass TRIAL."**

Dragon shrinks - now "only" 30 feet.

**"Fight me. Survive 3 rounds. IF you live - I help. If not... become ash."**

**"I begin NOW."**

**BOSS FIGHT - Pyraxis (Trial Mode)**
**HP: 300 | Attack: +10 | Defense: 18**
**Special:**
- **Fire Breath** - 50 dmg cone (DC 17 Agility half)
- **Tail Attack** - 40 dmg + knockdown
- **Flight** - avoids physical attacks 2 rounds

**WIN CONDITION:** Survive 3 rounds OR deal 150+ dmg"""
        
        choices = [
            {"text": "⚔️ DIRECT ATTACK", "next": "g1_main_020_combat",
             "req": {"type": "combat_action"}},
            {"text": "🛡️ DEFENSE - survive", "next": "g1_main_020_combat"},
            {"text": "🏹 RANGE - attack from distance", "next": "g1_main_020_combat",
             "req": {"type": "stat_check", "stat": "agility", "dc": 15}},
            {"text": "🗣️ 'Is there another way for trial?'", "next": "g1_branch_alternative_trial"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "dragon_lair", "combat": True, "boss": "pyraxis_trial"}


def get_scene_020_dragon_pact(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 020: Pakt ze smokiem lub wojna"""
    survived_trial = True  # TODO: check combat result
    
    if lang == "pl":
        title = "🔥 Smocze Słowo"
        if survived_trial:
            text = """Upadasz na kolana. Wyczerpany. Ale ŻYJESZ.

Smok ląduje, wraca do pełnego rozmiaru.

**"Imponujące. Mało śmiertelnych przeszło próbę. Masz mój RESPEKT."**

**"Zatem pakt. Pomogę ci zamknąć Rozłam. ALE pod warunkami:**

**1) Po zamknięciu - królestwo płaci mi TRYBUT. 1000 złota rocznie."**
**2) Góry Ognia pozostają MOIM terytorium. Zakaz dla ludzi."**
**3) **Jeden dzień w roku** - przysłużysz się MNE jak ZAŻĄDAM."**

**"Zgadzasz się?"**"""
            
            choices = [
                {"text": "🤝 PRZYJMIJ PAKT - zgadzam się", "next": "g1_main_022",
                 "effects": {"dragon_pact": True, "dragon_ally": True}},
                {"text": "⚖️ NEGOCJUJ - 'Zmniejszmy trybut'", "next": "g1_main_021",
                 "req": {"type": "stat_check", "stat": "charisma", "dc": 18}},
                {"text": "❌ ODMÓW - 'Zbyt wysoką cenę'", "next": "g1_main_021"},
                {"text": "⚔️ 'Pomożesz NA MOICH warunkach!' - atak", "next": "g1_branch_fight_dragon_full"}
            ]
        else:
            text = """Nie przetrwałeś próby. Smok cię pokonał.

**"Słaby. Nie wartościowy. IDŹ."**

Wyrzuca cię z jaskini. Bez pomocy smoka."""
            
            choices = [
                {"text": "😔 Wracaj - przegrałeś", "next": "g1_main_002"}
            ]
    else:
        title = "🔥 Dragon's Word"
        if survived_trial:
            text = """You fall to knees. Exhausted. But ALIVE.

Dragon lands, returns to full size.

**"Impressive. Few mortals passed trial. You have my RESPECT."**

**"So, pact. I'll help seal Rift. BUT with conditions:**

**1) After sealing - kingdom pays me TRIBUTE. 1000 gold yearly."**
**2) Fire Mountains remain MY territory. Ban for humans."**
**3) **One day per year** - you'll serve ME as I DEMAND."**

**"Do you agree?"**"""
            
            choices = [
                {"text": "🤝 ACCEPT PACT - I agree", "next": "g1_main_022",
                 "effects": {"dragon_pact": True, "dragon_ally": True}},
                {"text": "⚖️ NEGOTIATE - 'Lower the tribute'", "next": "g1_main_021",
                 "req": {"type": "stat_check", "stat": "charisma", "dc": 18}},
                {"text": "❌ REFUSE - 'Too high price'", "next": "g1_main_021"},
                {"text": "⚔️ 'You'll help on MY terms!' - attack", "next": "g1_branch_fight_dragon_full"}
            ]
        else:
            text = """You didn't survive trial. Dragon defeated you.

**"Weak. Not worthy. LEAVE."**

He throws you from cavern. Without dragon's help."""
            
            choices = [
                {"text": "😔 Return - you lost", "next": "g1_main_002"}
            ]
    
    if survived_trial:
        state.quest_flags["dragon_pact_offered"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "dragon_lair"}


# ==================== WĄTEK C: REBELIA (026-035) ====================

def get_scene_026_forest_rebels(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 026: Spotkanie z rebeliantami"""
    if lang == "pl":
        title = "🏹 Cienie Lasu"
        text = """W drodze powrotnej nagle - **STRZAŁY!**

Otaczają cię zamaskowani łucznicy. 

**Kobieta w zielonej pelerynie** wychodzi z cienia.

**"Nie ruszaj się, Wędrowiec. Słyszeliśmy o tobie. Zabijasz demony... ALE służysz TYRANOWI."**

Ściąga maskę. Jest młoda, oczy płoną determinacją.

**"Jestem LYRA WOLNA - liderka Rebelii. Król Aldric był MORDERCĄ. Zabijał niewinnych. Wprowadził niewolnictwo."**

{'**"A teraz JEGO córka siada na tronie. Kontynuuje terror."**' if state.king_alive == False else '**"Zamordowaliśmy go. Bo musiał UMRZEĆ."**'}

**"Dołącz do nas. Razem obalimy tron. Stwwórzymy RZECZPOSPOLITĄ."**"""
        
        choices = [
            {"text": "🤝 'Opowiedz mi więcej...'", "next": "g1_main_027"},
            {"text": "⚔️ 'Jesteście zdrajcami!' - ATAK", "next": "g1_branch_fight_rebels",
             "effects": {"rebellion_hostile": True}},
            {"text": "🤔 'Udowodnij że król był tyranem'", "next": "g1_main_027"},
            {"text": "🏃 'Puszczajcie mnie' - odejdź", "next": "g1_main_002"}
        ]
    else:
        title = "🏹 Forest Shadows"
        text = """On way back suddenly - **ARROWS!**

Masked archers surround you.

**Woman in green cloak** emerges from shadow.

**"Don't move, Wanderer. We heard of you. You kill demons... BUT serve TYRANT."**

She removes mask. Young, eyes burning with determination.

**"I am LYRA FREE - Rebellion leader. King Aldric was MURDERER. Killed innocents. Introduced slavery."**

{'**"And now HIS daughter sits on throne. Continues terror."**' if state.king_alive == False else '**"We murdered him. Because he HAD to DIE."**'}

**"Join us. Together we'll overthrow throne. Create REPUBLIC."**"""
        
        choices = [
            {"text": "🤝 'Tell me more...'", "next": "g1_main_027"},
            {"text": "⚔️ 'You are traitors!' - ATTACK", "next": "g1_branch_fight_rebels",
             "effects": {"rebellion_hostile": True}},
            {"text": "🤔 'Prove king was tyrant'", "next": "g1_main_027"},
            {"text": "🏃 'Let me go' - leave", "next": "g1_main_002"}
        ]
    
    state.rebellion_leader_known = True
    state.quest_flags["rebellion_contacted"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "forest_rebel_camp"}


def get_scene_027_rebellion_truth(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 027: Prawda o królu"""
    if lang == "pl":
        title = "📜 Mroczna Przeszłość"
        text = """Lyra pokazuje ci dokumenty. Świadectwa. **Listy królewskie.**

**"Patrz. Rozkaz spalenia wioski Riverdale - za odmowę podatku. 200 osób. DZIECI."**

**"Tu - lista więźniów politycznych. Tortury. Za krytykę króla."**

Jeden dokument cię uderza - **DEMON PAKT.**

**"Król WIEDZIAŁ o Rozłamie. SAM go otworzył! Chciał mocy demon dla siebie!"**

**"Ale gdy stracił kontrolę... obwinił innych. Kościół skorumpował by ukryć prawdę."**

{'Jeśli to prawda... twoja walka była kłamstwem...' if state.quest_flags.get("lightbringer_obtained") else 'To brzmi niewiarygodnie...'}"""
        
        choices = [
            {"text": "😨 'To PRAWDA?! Król był zły?!'", "next": "g1_main_028",
             "effects": {"moral_crisis": True}},
            {"text": "❌ 'To FAŁSZYWKI! Propaganda!'", "next": "g1_branch_fight_rebels"},
            {"text": "🤝 DOŁĄCZ DO REBELII", "next": "g1_main_029",
             "effects": {"rebellion_allied": True, "reputation": -50}},
            {"text": "⚖️ 'Muszę to zweryfikować...'", "next": "g1_main_028"}
        ]
    else:
        title = "📜 Dark Past"
        text = """Lyra shows you documents. Testimonies. **Royal letters.**

**"Look. Order to burn Riverdale village - for tax refusal. 200 people. CHILDREN."**

**"Here - list of political prisoners. Torture. For criticizing king."**

One document strikes you - **DEMON PACT.**

**"King KNEW about Rift. HE opened it! Wanted demon power for himself!"**

**"But when he lost control... blamed others. Corrupted church to hide truth."**

{'If this is true... your fight was a lie...' if state.quest_flags.get("lightbringer_obtained") else 'This sounds unbelievable...'}"""
        
        choices = [
            {"text": "😨 'This is TRUE?! King was evil?!'", "next": "g1_main_028",
             "effects": {"moral_crisis": True}},
            {"text": "❌ 'These are FAKES! Propaganda!'", "next": "g1_branch_fight_rebels"},
            {"text": "🤝 JOIN REBELLION", "next": "g1_main_029",
             "effects": {"rebellion_allied": True, "reputation": -50}},
            {"text": "⚖️ 'I must verify this...'", "next": "g1_main_028"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "rebel_command"}


# ==================== WĄTEK D: ARTEFAKTY (036-045) ====================

def get_scene_036_artifact_map(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 036: Odkrycie mapy do artefaktów"""
    if lang == "pl":
        title = "🗺️ Mapa Zagłady"
        text = """W ruinach starożytnej biblioteki znajdujesz **MAPOWPERGAMINU.**

Zaznaczonych 5 lokacji. Przy każdej - symbol:

🗡️ **MIECZ ŚWIATŁA** - Krypta Wampirów (Północ)
🛡️ **TARCZA WIEKÓW** - Twierdza Olbrzymów (Wschód)
👑 **KORONA UMYSŁU** - Labirynt Szaleństwa (Południe)
📚 **KSIĘGA ZAKAZANA** - Nekromanckie Katakumby (Zachód)
❤️ **SERCE FENIX** - Wulkan Wiecznego Ognia (Centrum)

Pod mapą napis:

**"Kto zbierze WSZYSTKIE PIĘĆ - może zniszczyć bogów... lub ZOSTAĆ bogiem."**

{'Światłoklinga wibruje. Ostrzega - to niebezpieczne artefakty.' if state.quest_flags.get("lightbringer_obtained") else 'Czujesz moc emanującą z mapy.'}"""
        
        choices = [
            {"text": "🗡️ IDŹ PO MIECZ - Krypta Wampirów", "next": "g1_main_037"},
            {"text": "🛡️ IDŹ PO TARCZĘ - Twierdza Olbrzymów", "next": "g1_main_038"},
            {"text": "👑 IDŹ PO KORONĘ - Labirynt", "next": "g1_main_039"},
            {"text": "❌ ZOSTAW - to zbyt groźne", "next": "g1_main_002"}
        ]
    else:
        title = "🗺️ Map of Doom"
        text = """In ruins of ancient library you find **PARCHMENT MAP.**

5 locations marked. By each - symbol:

🗡️ **SWORD OF LIGHT** - Vampire Crypt (North)
🛡️ **SHIELD OF AGES** - Giants' Fortress (East)
👑 **CROWN OF MIND** - Labyrinth of Madness (South)
📚 **FORBIDDEN BOOK** - Necromantic Catacombs (West)
❤️ **PHOENIX HEART** - Eternal Fire Volcano (Center)

Under map, inscription:

**"Who gathers ALL FIVE - can destroy gods... or BECOME god."**

{'Lightbringer vibrates. Warns - these are dangerous artifacts.' if state.quest_flags.get("lightbringer_obtained") else 'You feel power emanating from map.'}"""
        
        choices = [
            {"text": "🗡️ GET SWORD - Vampire Crypt", "next": "g1_main_037"},
            {"text": "🛡️ GET SHIELD - Giants' Fortress", "next": "g1_main_038"},
            {"text": "👑 GET CROWN - Labyrinth", "next": "g1_main_039"},
            {"text": "❌ LEAVE - too dangerous", "next": "g1_main_002"}
        ]
    
    state.quest_flags["artifact_map_found"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "ancient_library"}


def get_scene_037_sword_artifact(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 037: Miecz Światła w krypcie wampirów"""
    if lang == "pl":
        title = "🗡️ Krypta Krwiopijców"
        text = """Krypta jest CIEMNA. Zapach rozkładu.

**Trumny wszędzie.** Setki.

W centrum - **MIECZ NA PIEDESTALE.** Ostrze emituje białe światło.

Podchodzisz. Nagle - **TRUMNY OTWIERAJĄ SIĘ!**

**5 WAMPIRÓW** wyłania się z cieni. Oczy czerwone. Kły wyszczerzone.

**WAMPIR-LORD**: *"Śmiertelny odważył się tu przyjść? MIECZ jest NASZYM strażnikiem. Weź go... i UMRZYJ."*

**BOSS FIGHT - 5 Wampirów (każdy 80 HP, regeneracja 10 HP/rundę)**

LUB możesz:"""
        
        choices = [
            {"text": "⚔️ WALCZ z wampirami!", "next": "g1_main_037_combat",
             "req": {"type": "combat_check"}},
            {"text": "💡 UŻYJ ŚWIATŁA - wypędź wampiry (DC 16)", "next": "g1_main_037_success",
             "req": {"type": "stat_check", "stat": "wisdom", "dc": 16}},
            {"text": "🗣️ NEGOCJUJ - zaoferuj krew (20 HP)", "next": "g1_main_037_success",
             "effects": {"hp_cost": 20}},
            {"text": "🏃 CHWYĆ i UCIEKAJ!", "next": "g1_main_037_escape"}
        ]
    else:
        title = "🗡️ Bloodsucker Crypt"
        text = """Crypt is DARK. Smell of decay.

**Coffins everywhere.** Hundreds.

In center - **SWORD ON PEDESTAL.** Blade emits white light.

You approach. Suddenly - **COFFINS OPEN!**

**5 VAMPIRES** emerge from shadows. Red eyes. Fangs bared.

**VAMPIRE-LORD**: *"Mortal dared come? SWORD is OUR guardian. Take it... and DIE."*

**BOSS FIGHT - 5 Vampires (each 80 HP, regeneration 10 HP/round)**

OR you can:"""
        
        choices = [
            {"text": "⚔️ FIGHT vampires!", "next": "g1_main_037_combat",
             "req": {"type": "combat_check"}},
            {"text": "💡 USE LIGHT - repel vampires (DC 16)", "next": "g1_main_037_success",
             "req": {"type": "stat_check", "stat": "wisdom", "dc": 16}},
            {"text": "🗣️ NEGOTIATE - offer blood (20 HP)", "next": "g1_main_037_success",
             "effects": {"hp_cost": 20}},
            {"text": "🏃 GRAB and FLEE!", "next": "g1_main_037_escape"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "vampire_crypt", "combat": True}


def get_scene_038_shield_artifact(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 038: Tarcza Wieków w twierdzy olbrzymów"""
    if lang == "pl":
        title = "🛡️ Twierdza Tytanów"
        text = """Twierdza GIGANTYCZNA. Bramy 50 stóp wysokoś ci.

Wszystko jest OLBRZYMIE - stoły, krzesła, miecze.

W sali tronowej - **OLBRZYM** 40 stóp wysokości.

**"Maluch! Przyszedłeś po TARCZĘ? To MOJA tarcza! Dawno temu ukradzona przez magów!"**

**"Walcz ze mną o nią! LUB... rozwiąż moją zagadkę."**

Olbrzym uśmiecha się.

**ZAGADKA:**
**"Nie żyje, a rośnie. Nie je, a pożera. Nie pije, a ginie od wody. Co to?"**"""
        
        choices = [
            {"text": "💭 'OGIEŃ!' - odpowiedź", "next": "g1_main_038_success",
             "correct": True},
            {"text": "💭 'CIEŃ!' - odpowiedź", "next": "g1_main_038_fail"},
            {"text": "💭 'CZAS!' - odpowiedź", "next": "g1_main_038_fail"},
            {"text": "⚔️ WALCZ zamiast zagadek!", "next": "g1_main_038_combat",
             "req": {"type": "combat_check"}}
        ]
    else:
        title = "🛡️ Titans' Fortress"
        text = """Fortress GIGANTIC. Gates 50 feet high.

Everything is GIANT - tables, chairs, swords.

In throne room - **GIANT** 40 feet tall.

**"Tiny! You came for SHIELD? This is MY shield! Stolen long ago by mages!"**

**"Fight me for it! OR... solve my riddle."**

Giant smiles.

**RIDDLE:**
**"Not alive, yet grows. Doesn't eat, yet devours. Doesn't drink, yet killed by water. What is it?"**"""
        
        choices = [
            {"text": "💭 'FIRE!' - answer", "next": "g1_main_038_success",
             "correct": True},
            {"text": "💭 'SHADOW!' - answer", "next": "g1_main_038_fail"},
            {"text": "💭 'TIME!' - answer", "next": "g1_main_038_fail"},
            {"text": "⚔️ FIGHT instead of riddles!", "next": "g1_main_038_combat",
             "req": {"type": "combat_check"}}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "giant_fortress"}


# ==================== WĄTEK E: MROCZNA ŚCIEŻKA (046-050) ====================

def get_scene_046_dark_rebellion(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 046: Rebelia mroczna - sojusz z demonami"""
    requires_dark_alignment = state.quest_flags.get("moral_alignment") == "evil"
    
    if lang == "pl":
        title = "💀 Mroczny Pakt"
        text = """{'Twoje czyny doprowadziły cię tu...' if requires_dark_alignment else 'Podążasz mroczną ścieżką...'}

**Głos z Rozłamu** rozbrzmiewa w twojej głowie:

**"Widzę cię, Wędrowiec. Widzę twoją AMBIJĘ. Twoją SIŁĘ."**

**"Nie zamykaj mnie. UŻYJ mnie. Dołącz do nas."**

**"Możesz zostać PANEM tego świata. Nie sługą króla. WŁADCĄ."**

Fioletowa energia wyciąga się do ciebie.

**"Wystarczy jeden dotyk. Jedna decyzja. A MOC będzie twoja."**

{'Światłoklinga KRZCZY w twojej ręce - ostrzega!' if state.quest_flags.get("lightbringer_obtained") else 'Kuszące...'}"""
        
        choices = [
            {"text": "💜 DOTKNIJ - przyjmij moc demon", "next": "g1_main_047",
             "effects": {"dark_pact": True, "alignment": "evil"}},
            {"text": "⚔️ 'Nigdy!' - odrzuć i atakuj", "next": "g1_main_013"},
            {"text": "🤔 'Jaką DOKŁADNIE moc?'", "next": "g1_branch_demon_details"}
        ]
    else:
        title = "💀 Dark Pact"
        text = """{'Your deeds led you here...' if requires_dark_alignment else 'You follow dark path...'}

**Voice from Rift** echoes in your mind:

**"I see you, Wanderer. I see your AMBITION. Your STRENGTH."**

**"Don't seal me. USE me. Join us."**

**"You can become LORD of this world. Not king's servant. RULER."**

Purple energy reaches toward you.

**"Just one touch. One decision. And POWER is yours."**

{'Lightbringer SCREAMS in your hand - warning!' if state.quest_flags.get("lightbringer_obtained") else 'Tempting...'}"""
        
        choices = [
            {"text": "💜 TOUCH - accept demon power", "next": "g1_main_047",
             "effects": {"dark_pact": True, "alignment": "evil"}},
            {"text": "⚔️ 'Never!' - reject and attack", "next": "g1_main_013"},
            {"text": "🤔 'What EXACTLY power?'", "next": "g1_branch_demon_details"}
        ]
    
    state.quest_flags["dark_pact_offered"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "rift_heart", "critical": True}


def get_scene_047_assassination_spree(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 047: Zabójstwo wszystkich przywódców"""
    if lang == "pl":
        title = "🗡️ Noc Długich Noży"
        text = """Moc demon przepływa przez ciebie. **Czujesz się NIEPOKONANY.**

Twoje oczy świecą FIOLETOWO.

Otrzymujesz WIZJĘ - lokacje wszystkich przywódców:

✓ Dowódca Rycerzy - w koszarach
✓ Lider Rebelii - w lesie  
✓ {'Duch Króla - w Krainie Umarłych' if state.quest_flags.get("ghost_army_obtained") else 'Rada Królewska - w pałacu'}
✓ Smok Pyraxis - w jaskini
✓ Przywódca Kościoła - w katedrze

**"Zabij ich WSZYSTKICH. Zostaw królestwo bez przywódców. A ty PANUJ z chaosu."**

Czujesz... pragnienie mordu."""
        
        choices = [
            {"text": "💀 ROZPOCZNIJ MASAKRĘ", "next": "g1_main_048"},
            {"text": "😨 'Co ja robię?!' - OPIERAJ SIĘ!", "next": "g1_branch_resist_darkness",
             "req": {"type": "stat_check", "stat": "wisdom", "dc": 22}},
            {"text": "🔥 WZMOCNIJ moc - zabij WSZYSTKICH", "next": "g1_main_048",
             "effects": {"full_corruption": True}}
        ]
    else:
        title = "🗡️ Night of Long Knives"
        text = """Demon power flows through you. **You feel INVINCIBLE.**

Your eyes glow PURPLE.

You receive VISION - locations of all leaders:

✓ Knight Commander - in barracks
✓ Rebellion Leader - in forest
✓ {'Ghost King - in Land of Dead' if state.quest_flags.get("ghost_army_obtained") else 'Royal Council - in palace'}
✓ Dragon Pyraxis - in cavern
✓ Church Leader - in cathedral

**"Kill them ALL. Leave kingdom without leaders. And you RULE from chaos."**

You feel... lust for murder."""
        
        choices = [
            {"text": "💀 BEGIN MASSACRE", "next": "g1_main_048"},
            {"text": "😨 'What am I doing?!' - RESIST!", "next": "g1_branch_resist_darkness",
             "req": {"type": "stat_check", "stat": "wisdom", "dc": 22}},
            {"text": "🔥 AMPLIFY power - kill EVERYONE", "next": "g1_main_048",
             "effects": {"full_corruption": True}}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "various", "dark": True}


def get_scene_048_rift_control(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 048: Przejęcie kontroli nad Rozłamem"""
    if lang == "pl":
        title = "💜 Władca Otchłani"
        text = """Wszyscy przywódcy... martwi. Przez twoją rękę.

**Królestwo tonie w chaosie.**

Wracasz do Rozłamu. Teraz czujesz... POŁĄCZENIE.

**"Dobra robota, nasz nowy PANIE."**

Głos demon nie jest już zewnętrzny. Jest W TOBIE.

**"Teraz ostatni krok. Wejdź DO Rozłamu. Przejmij tron Pana Demonów."**

**"Zostań DEMON-KRÓLEM. Władcą obydwu światów."**

Widzisz portal. Prowadzi w głąb Rozłamu - do SERCA demon."""
        
        choices = [
            {"text": "👿 WEJDŹ - przejmij tron demon", "next": "g1_main_049"},
            {"text": "⚔️ 'Nie! Zniszczę Rozłam od ŚRODKA!'", "next": "g1_branch_sacrifice_ending"},
            {"text": "💀 WCHŁOŃ Rozłam w SIEBIE", "next": "g1_main_050"}
        ]
    else:
        title = "💜 Lord of Abyss"
        text = """All leaders... dead. By your hand.

**Kingdom drowns in chaos.**

You return to Rift. Now you feel... CONNECTION.

**"Good work, our new LORD."**

Demon voice is no longer external. It's IN YOU.

**"Now final step. Enter INTO Rift. Seize Demon Lord's throne."**

**"Become DEMON-KING. Ruler of both worlds."**

You see portal. Leads into Rift depths - to demon HEART."""
        
        choices = [
            {"text": "👿 ENTER - seize demon throne", "next": "g1_main_049"},
            {"text": "⚔️ 'No! I'll destroy Rift from INSIDE!'", "next": "g1_branch_sacrifice_ending"},
            {"text": "💀 ABSORB Rift into YOURSELF", "next": "g1_main_050"}
        ]
    
    state.rift_activity = "controlled"
    
    return {"title": title, "text": text, "choices": choices, "location": "rift_heart", "dark": True}


def get_scene_049_demon_lord_power(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 049: Wchłonięcie mocy Pana Demonów"""
    if lang == "pl":
        title = "👑 Tron Ognia"
        text = """Wchodzisz przez portal.

**PIEKŁO.**

Świat fioletu i ognia. Miliony demon wokół.

Na tronie z czaszek siedzi **AZATHUL - PAN DEMONÓW.**

**"ŚMIERTELNY? Tutaj?! NIEMOŻLI-"**

Nie kończy. **ATAKUJESZ.**

Twoja moc demon vs jego moc. Starcie Tytanów.

**WYGRYWASZ.**

Wchłaniasz jego esencję. **Jego MOC.**

**Zasiadasz na tronie.**

Wszystkie demony klękają.

**"NOWY PAN! NOWY PAN! NOWY PAN!"**

Jesteś teraz... BOGIEM DEMON."""
        
        choices = [
            {"text": "👿 ZAAKCEPTUJ - zostań Panem", "next": "g1_end_demon_lord"},
            {"text": "💥 ZNISZCZ TRON - zakończ to", "next": "g1_end_sacrifice"}
        ]
    else:
        title = "👑 Throne of Fire"
        text = """You enter through portal.

**HELL.**

World of violet and fire. Millions of demons around.

On throne of skulls sits **AZATHUL - DEMON LORD.**

**"MORTAL? Here?! IMPOSSI-"**

He doesn't finish. **YOU ATTACK.**

Your demon power vs his. Clash of Titans.

**YOU WIN.**

You absorb his essence. **His POWER.**

**You sit on throne.**

All demons kneel.

**"NEW LORD! NEW LORD! NEW LORD!"**

You are now... DEMON GOD."""
        
        choices = [
            {"text": "👿 ACCEPT - become Lord", "next": "g1_end_demon_lord"},
            {"text": "💥 DESTROY THRONE - end this", "next": "g1_end_sacrifice"}
        ]
    
    return {"title": title, "text": text, "choices": choices, "location": "demon_throne_room", "epic": True}


def get_scene_050_ultimate_power(lang: str, state: Gate1WorldState, player) -> Dict:
    """Scena 050: Finał - pełna fuzja z mocą"""
    if lang == "pl":
        title = "💫 Bóstwo"
        text = """Wchłaniasz WSZYSTKO.

Rozłam. Demony. Moc. Królestwo. WSZYSTKO.

**Stajesz się CZYMŚ WIĘCEJ.**

Nie jesteś już śmiertelnikiem.
Nie jesteś demonem.
Nie jesteś bogiem.

Jesteś... **TRANSCENDENCJĄ.**

**Przestrzeń-czas zgina się wokół ciebie.**

Widzisz WSZYSTKIE wymiary jednocześnie. 9 Bram. Wszystkie możliwości.

**Możesz:**
- Przerobić Gate 1 według swojej woli
- Przeskoczyć do innego wymiaru
- Zostać tu na zawsze jako bóg"""
        
        choices = [
            {"text": "🔮 PRZEBUDUJ GATE 1", "next": "g1_end_reshape_reality"},
            {"text": "🌌 PRZEJDŹ DO GATE 2", "next": "return_to_precipice"},
            {"text": "👑 ZOSTAŃ BOGIEM TU", "next": "g1_end_eternal_throne"}
        ]
    else:
        title = "💫 Godhood"
        text = """You absorb EVERYTHING.

Rift. Demons. Power. Kingdom. EVERYTHING.

**You become SOMETHING MORE.**

You're no longer mortal.
You're not demon.
You're not god.

You are... **TRANSCENDENCE.**

**Space-time bends around you.**

You see ALL dimensions simultaneously. 9 Gates. All possibilities.

**You can:**
- Reshape Gate 1 according to your will
- Jump to another dimension
- Stay here forever as god"""
        
        choices = [
            {"text": "🔮 RESHAPE GATE 1", "next": "g1_end_reshape_reality"},
            {"text": "🌌 GO TO GATE 2", "next": "return_to_precipice"},
            {"text": "👑 BECOME GOD HERE", "next": "g1_end_eternal_throne"}
        ]
    
    state.quest_flags["transcendence_achieved"] = True
    
    return {"title": title, "text": text, "choices": choices, "location": "beyond_reality", "ending": True, "ultimate": True}


# Kontynuacja w następnym replace - dodaję kolejne sceny

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
    """Zakończenie: Królestwo uratowane - heroic ending"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  🏆 KRÓLESTWO URATOWANE - KONIEC  🏆  ║
╚═══════════════════════════════════════╝

Rozłam **ZAMYKA SIĘ** w eksplozji światła.

Ostatnia fala demonicznej energii rozrywa niebo, ale **TY** stoisz mocno, {player.character.name}.
Fragment **ŚWIATŁONOŚCICELA** w twoich rękach rozbłyska **OŚLEPIAJĄCYM BLASKIEM**.

```asciidoc
ROZŁAM ▂▃▅▇█▓▒░ ZAMYKA SIĘ ░▒▓█▇▅▃▂
```

**TŁUM KRZYCZY** z ulgi i radości.

**📜 EPILOG:**

• **KRÓLESTWO** odbudowuje się z ruin - {state.villages_saved if hasattr(state, 'villages_saved') else 0} wiosek ocalonych
• **PRINCESSKA ELARA** koronowana jako nowa królowa, mądra i sprawiedliwa
• **ZAKON RYCERZY** składa ci przysięgę wierności
• **SER MARKUS** nazywa cię **"Zbawcą Królestwa"**

{f"• **PYRAXIS FLAMEHEART** powraca do lazurowych gór, pakt mocno trwa" if state.quest_flags.get("dragon_pact_offered") else ""}
{f"• **REBELIA** integruje się z królestwem, Lyra Free zostaje Wielką Marszałkini" if state.quest_flags.get("rebellion_allied") else ""}

**TWOJE IMIĘ** zapisane zostaje w legendach.

Jednak... głęboko w sercu **CZUJESZ**:

> *To dopiero początek. Pozostało jeszcze **8 BRAM**.*

**NAGRODY FINAŁOWE:**
├─ 🪙 +10,000 Gold
├─ 💎 +500 Experience
├─ 🏅 Tytuł: "Zbawca Królestwa"
├─ ✨ Unlock: Gate 2 Access
└─ 🎖️ Achievement: "Hero of Gate 1"

**STATYSTYKI ZAKOŃCZENIA:**
```
Rozłam:         ZAMKNIĘTY ✓
Straty:         {state.villages_destroyed if hasattr(state, 'villages_destroyed') else 0} wiosek zniszczonych
Uratowanych:    {state.villages_saved if hasattr(state, 'villages_saved') else 0} wiosek ocalonych
Moralność:      {state.quest_flags.get('moral_alignment', 'neutral').upper()}
Sojusznicy:     {', '.join([k.replace('_', ' ').title() for k, v in state.quest_flags.items() if 'allied' in k and v]) or 'Brak'}
```

_(Możesz teraz przejść do Gate 2 lub eksplorować Gate 1 w trybie post-game)_
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  🏆 KINGDOM SAVED - THE END  🏆   ║
╚════════════════════════════════════╝

The Rift **CLOSES** in an explosion of light.

The final wave of demonic energy tears the sky, but **YOU** stand firm, {player.character.name}.
The **LIGHTBRINGER** fragment in your hands blazes with **BLINDING BRILLIANCE**.

```asciidoc
RIFT ▂▃▅▇█▓▒░ CLOSING ░▒▓█▇▅▃▂
```

**THE CROWD ROARS** with relief and joy.

**📜 EPILOGUE:**

• **KINGDOM** rebuilds from ruins - {state.villages_saved if hasattr(state, 'villages_saved') else 0} villages saved
• **PRINCESS ELARA** crowned as new queen, wise and just
• **KNIGHT ORDER** swears fealty to you
• **SER MARKUS** names you **"Savior of the Kingdom"**

{f"• **PYRAXIS FLAMEHEART** returns to azure mountains, pact holds strong" if state.quest_flags.get("dragon_pact_offered") else ""}
{f"• **REBELLION** integrates with kingdom, Lyra Free becomes Grand Marshal" if state.quest_flags.get("rebellion_allied") else ""}

**YOUR NAME** is written in legends.

Yet... deep in your heart **YOU FEEL**:

> *This is only the beginning. **8 GATES** remain.*

**FINAL REWARDS:**
├─ 🪙 +10,000 Gold
├─ 💎 +500 Experience
├─ 🏅 Title: "Kingdom Savior"
├─ ✨ Unlock: Gate 2 Access
└─ 🎖️ Achievement: "Hero of Gate 1"

**ENDING STATISTICS:**
```
Rift:           SEALED ✓
Losses:         {state.villages_destroyed if hasattr(state, 'villages_destroyed') else 0} villages destroyed
Saved:          {state.villages_saved if hasattr(state, 'villages_saved') else 0} villages protected
Morality:       {state.quest_flags.get('moral_alignment', 'neutral').upper()}
Allies:         {', '.join([k.replace('_', ' ').title() for k, v in state.quest_flags.items() if 'allied' in k and v]) or 'None'}
```

_(You can now proceed to Gate 2 or explore Gate 1 in post-game mode)_
"""
    
    choices = [
        {"text": "🚪 Przejdź do Gate 2" if lang == "pl" else "🚪 Proceed to Gate 2",
         "next": "gate_2_transition",
         "effects": {"gate": 2}},
        {"text": "🔄 Eksploruj Gate 1" if lang == "pl" else "🔄 Explore Gate 1",
         "next": "g1_postgame_hub"}
    ]
    
    # Apply rewards
    player.currency += 10000
    player.experience += 500
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "heroic",
        "outcome": "kingdom_saved"
    }


def get_ending_demon_lord(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Zostałeś władcą demonów"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  👿 WŁADCA DEMONÓW - KONIEC  👿      ║
╚═══════════════════════════════════════╝

**ROZŁAM** nie zamyka się. **TY** go kontrolujesz.

{player.character.name}, twoje oczy płoną **FIOLETOWYM OGNIEM**.
Moc **AZATHULA** została wchłonięta. Jesteś **PANEM OTCHŁANI**.

```asciidoc
🔥 DEMONY KLĘKAJĄ PRZED TOBĄ 🔥
```

**📜 EPILOG - KRÓLOWANIE PRZEZ PRZERAŻENIE:**

• **KRÓLESTWO** upada w chaos i ruinę
• **REBELIA** zmiażdżona twoją mocą
• **SMOK PYRAXIS** {'pokonany w bitwie' if state.quest_flags.get('dragon_hostile') else 'unika konfrontacji'}
• **ELARA** {'zginęła w walce' if state.quest_flags.get('princess_dead') else 'uwięziona w wieży'}

**TWOJE PANOWANIE:**

Rządzisz z **TRONU Z CZASZEK** w centrum Rozłamu.
Królestwo przekształciło się w **DEMONICZNĄ KRAINĄ**.

Każdego dnia tysiące dusz przepływa przez portal, zasilając twoją moc.

**OSIĄGNIĘCIA WŁADCY:**
├─ 💀 Kontrola nad 10,000+ demonami
├─ 🔥 Przekształcono 50+ wiosek w warownie demoniczne
├─ 👿 Złożono 1,000,000+ ofiar
├─ 💜 Moc Rozłamu: ABSOLUTNA
└─ ⚫ Status: NIEŚMIERTELNY TYRAN

Ale...

**GŁOS AZATHULA** wciąż szepcze w twojej głowie:

> *"Jesteś **MOIM** narzędziem. Zawsze byłeś. Zawsze będziesz."*

Czy naprawdę **WYGRAŁEŚ**?
Czy tylko **ZMIENIŁEŚ PANA**?

**ZAKOŃCZENIE: ZŁE - "Król Demonów"**

_(To zakończenie uniemożliwia przejście do Gate 2. Możesz zresetować lub kontynuować panowanie w Gate 1)_
"""
    else:  # EN
        text = f"""╔═══════════════════════════════════╗
║  👿 DEMON LORD - THE END  👿     ║
╚═══════════════════════════════════╝

**THE RIFT** does not close. **YOU** control it.

{player.character.name}, your eyes burn with **VIOLET FIRE**.
**AZATHUL'S** power has been absorbed. You are **LORD OF THE ABYSS**.

```asciidoc
🔥 DEMONS KNEEL BEFORE YOU 🔥
```

**📜 EPILOGUE - REIGN THROUGH TERROR:**

• **KINGDOM** falls into chaos and ruin
• **REBELLION** crushed by your might
• **DRAGON PYRAXIS** {'defeated in battle' if state.quest_flags.get('dragon_hostile') else 'avoids confrontation'}
• **ELARA** {'died in combat' if state.quest_flags.get('princess_dead') else 'imprisoned in tower'}

**YOUR REIGN:**

You rule from the **THRONE OF SKULLS** at the center of the Rift.
The kingdom has transformed into a **DEMONIC WASTELAND**.

Every day thousands of souls flow through the portal, feeding your power.

**LORD'S ACHIEVEMENTS:**
├─ 💀 Control over 10,000+ demons
├─ 🔥 Transformed 50+ villages into demon fortresses
├─ 👿 1,000,000+ sacrifices made
├─ 💜 Rift Power: ABSOLUTE
└─ ⚫ Status: IMMORTAL TYRANT

But...

**AZATHUL'S VOICE** still whispers in your mind:

> *"You are **MY** tool. Always were. Always will be."*

Did you truly **WIN**?
Or did you just **CHANGE MASTERS**?

**ENDING: EVIL - "Demon King"**

_(This ending blocks Gate 2 access. You can reset or continue ruling Gate 1)_
"""
    
    choices = [
        {"text": "👿 Kontynuuj panowanie" if lang == "pl" else "👿 Continue reign",
         "next": "g1_demon_lord_hub"},
        {"text": "🔄 Zresetuj kampanię" if lang == "pl" else "🔄 Reset campaign",
         "next": "reset_gate1"}
    ]
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "evil",
        "outcome": "demon_lord_reign"
    }


def get_ending_dragon_pact(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Pakt ze smokiem"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  🐉 PAKT SMOKA - KONIEC  🐉          ║
╚═══════════════════════════════════════╝

**PYRAXIS FLAMEHEART** i {player.character.name} stoją razem przed Rozłamem.

Starożytny smok wybucha **SMUGĄ ŚWIATŁA DRAGONIEGO** wprost w serce portalu.
Ty zaś wznosisz **FRAGMENT ŚWIATŁONOŚCICELA** - energie łączą się.

```asciidoc
╔══════════════════════════╗
║ 🔥🐉  FUZJA MOCY  🐉🔥  ║
╚══════════════════════════╝
```

Rozłam **IMPLODUJE** w kaskadzie dźwięku i światła.

**📜 EPILOG - NOWA ERA:**

• **KRÓLESTWO** odbudowane pod przywództwem Elary i Pyraxisa
• **PAKT DRAGONÓW** - pierwsza taka umowa od 1000 lat
• **TY** zostałeś **SMOCZY RYCERZ** - jedyny w historii nieSmok z tym tytułem

**TWOJA NOWA ROLA:**

Co roku spędzasz **1 MIESIĄC** w Lazurowych Górach, ucząc się starożytnej magii od Pyraxisa.
Płacisz **TRYBUT** (1000 złota rocznie), ale w zamian:

├─ 🐉 Możesz przywołać Pyraxisa raz na rok
├─ 🔥 Otrzymałeś **DAR SMOCZEGO ODDECHU** (minor)
├─ 📚 Dostęp do Biblioteki Smoków
├─ ⚔️ Miecz wykuty w smoczym ogniu
└─ 🛡️ Immunitet na ogień

**PYRAXIS** mówi, stojąc na szczycie góry:

> *"Rzadko znajduję śmiertelnika **GODNEGO SZACUNKU**. Twoja odwaga zmieniła historię, młody przyjacielu."*

**KRÓLESTWO** świętuje **PIERWSZEGO SMOCZY RYCERZA**.

**ZAKOŃCZENIE: SOJUSZ - "Smocze Braterstwo"**

✨ **ODBLOKOWANE**: Gate 2 + Smocza Siła
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  🐉 DRAGON PACT - THE END  🐉     ║
╚════════════════════════════════════╝

**PYRAXIS FLAMEHEART** and {player.character.name} stand together before the Rift.

The ancient dragon releases a **BEAM OF DRAGONFIRE** straight into the portal's heart.
You raise the **LIGHTBRINGER FRAGMENT** - the energies merge.

```asciidoc
╔══════════════════════════╗
║ 🔥🐉  POWER FUSION  🐉🔥 ║
╚══════════════════════════╝
```

The Rift **IMPLODES** in a cascade of sound and light.

**📜 EPILOGUE - NEW ERA:**

• **KINGDOM** rebuilt under Elara and Pyraxis's leadership
• **DRAGON PACT** - first such accord in 1000 years
• **YOU** became **DRAGON KNIGHT** - only non-Dragon in history with this title

**YOUR NEW ROLE:**

Each year you spend **1 MONTH** in Azure Mountains, learning ancient magic from Pyraxis.
You pay **TRIBUTE** (1000 gold yearly), but in return:

├─ 🐉 Can summon Pyraxis once per year
├─ 🔥 Received **GIFT OF DRAGONBREATH** (minor)
├─ 📚 Access to Dragon Library
├─ ⚔️ Sword forged in dragonfire
└─ 🛡️ Fire immunity

**PYRAXIS** says, standing atop the mountain:

> *"Rarely do I find a mortal **WORTHY OF RESPECT**. Your courage changed history, young friend."*

The **KINGDOM** celebrates its **FIRST DRAGON KNIGHT**.

**ENDING: ALLIANCE - "Dragon Brotherhood"**

✨ **UNLOCKED**: Gate 2 + Dragon Power
"""
    
    choices = [
        {"text": "🚪 Przejdź do Gate 2" if lang == "pl" else "🚪 Proceed to Gate 2",
         "next": "gate_2_transition",
         "effects": {"gate": 2, "dragon_ally": True}},
        {"text": "🐉 Wizyta u Pyraxisa" if lang == "pl" else "🐉 Visit Pyraxis",
         "next": "g1_dragon_keep"}
    ]
    
    # Rewards
    player.currency += 5000
    player.experience += 400
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "alliance",
        "outcome": "dragon_pact"
    }


def get_ending_stalemate(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Pat - Rozłam pozostaje otwarty w kontrolowanym stanie"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  ⚖️ PAT - KONIEC NIEPEWNY  ⚖️        ║
╚═══════════════════════════════════════╝

Rozłam **NIE ZAMYKA SIĘ**.

Ale też **NIE ROZRASTA SIĘ** dalej.

{player.character.name}, użyłeś fragmentu Światłonościcela do **USTABILIZOWANIA** portalu, nie zamknięcia go.

```asciidoc
⚠️  ROZŁAM: STATUS ZAWIESZONY  ⚠️
```

**📜 EPILOG - RÓWNOWAGA STRACHU:**

• **KRÓLESTWO** stoi w gotowości bojowej 24/7
• **ROZŁAM** monitorowany przez straże co 6 minut
• **ELARA** rządzi z kamienną twarzą, wiedząc że niebezpieczeństwo nigdy nie minęło

**TWOJA DECYZJA MIAŁA KONSEKWENCJE:**

Uratowałeś księżniczkę (lub kogoś innego), ale **CENĄ** była niemożność pełnego zamknięcia portalu.

**ŻYCIE W CIENIU ROZŁAMU:**

├─ Demony **NIE ATAKUJĄ** (na razie)
├─ Ale ludzie **ŻYJĄ W STRACHU**
├─ Co noc pojawia się pytanie: *"Czy dziś wybuchnie?"*
├─ Królestwo nie może się rozwijać - cała energia idzie na obronę
└─ Każde pokolenie **CZEKA NA WYBUCH**

**SER MARKUS** mówi, patrząc na portal:

> *"Zrobiłeś, co musiałeś. Ale **HISTORIA CIĘ OSĄDZI** - czy uratowałeś królestwo, czy tylko *przedłużyłeś agonię*?"*

**ZAKOŃCZENIE: NIEJEDNOZNACZNE - "Wieczny Miecz Damoklesa"**

_(Możesz wrócić i spróbować inaczej, lub żyć z konsekwencjami)_
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  ⚖️ STALEMATE - UNCERTAIN END  ⚖️  ║
╚════════════════════════════════════╝

The Rift **DOES NOT CLOSE**.

But it **DOESN'T EXPAND** either.

{player.character.name}, you used the Lightbringer fragment to **STABILIZE** the portal, not seal it.

```asciidoc
⚠️  RIFT: STATUS SUSPENDED  ⚠️
```

**📜 EPILOGUE - BALANCE OF FEAR:**

• **KINGDOM** stands in combat readiness 24/7
• **RIFT** monitored by guards every 6 minutes
• **ELARA** rules with stone face, knowing danger never passed

**YOUR DECISION HAD CONSEQUENCES:**

You saved the princess (or someone else), but the **PRICE** was inability to fully close the portal.

**LIFE IN RIFT'S SHADOW:**

├─ Demons **DON'T ATTACK** (for now)
├─ But people **LIVE IN FEAR**
├─ Every night asks: *"Will it explode today?"*
├─ Kingdom cannot develop - all energy goes to defense
└─ Every generation **WAITS FOR ERUPTION**

**SER MARKUS** says, looking at the portal:

> *"You did what you had to. But **HISTORY WILL JUDGE** - did you save the kingdom, or only *prolong its agony*?"*

**ENDING: AMBIGUOUS - "Eternal Sword of Damocles"**

_(You can return and try differently, or live with consequences)_
"""
    
    choices = [
        {"text": "🔄 Spróbuj ponownie" if lang == "pl" else "🔄 Try again",
         "next": "g1_main_014",
         "effects": {"reset_to_choice": True}},
        {"text": "✅ Zaakceptuj los" if lang == "pl" else "✅ Accept fate",
         "next": "g1_postgame_stalemate"}
    ]
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "ambiguous",
        "outcome": "stalemate"
    }


def get_ending_sacrifice(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Ofiara - zniszczenie tronu demonów kosztem własnego życia"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  ⚡ OSTATECZNA OFIARA - KONIEC  ⚡   ║
╚═══════════════════════════════════════╝

{player.character.name} kładzie dłonie na **TRONIE Z CZASZEK**.

Twoja moc, dusza, wszystko co jesteś - **PRZEPŁYWA** do kamienia.

```asciidoc
💥 EKSPLOZJA ŚWIETLNA 💥
```

**AZATHUL KRZYCZY** w agonii, rozpadając się na miliony cząstek.

**TRON PĘKA** z dźwiękiem łamiącego się świata.

**ROZŁAM IMPLODUJE** - zasysając wszystkie demony z powrotem.

Ostatnią rzeczą, którą widzisz, jest **TWARZ ELARY** w portalu, krzyczącej twoje imię...

**📜 EPILOG - 100 LAT PÓŹNIEJ:**

Królestwo **ODBUDOWAŁO SIĘ** w czasach pokoju.

W centrum stolicy stoi **200-METROWY POMNIK**:

```
╔══════════════════════════════════╗
║  {player.character.name.upper()}           ║
║  ZBAWCA KRÓLESTWA               ║
║  "Oddał życie, byśmy żyli"      ║
╚══════════════════════════════════╝
```

**ELARA**, teraz stara królowa, każdego roku składa kwiaty u pomnika.

Jej pra-wnuki słuchają **LEGENDY o BOHATERZE**, który pokonał Pana Demonów ceną własnej duszy.

**PIEŚŃ BARDÓW:**

> *"W ciemności najgłębszej, gdy zło tryumfowało*
> *Jedno serce biło, co dobro wybierało*
> *{player.character.name} imieniem, {player.character.char_class} klasą*
> *Oddał życie swoje, by zamknąć Przepaść własną."*

**TWOJA DUSZA:**

Ale ty... czujesz dziwny spokój.

Twoja dusza unosi się teraz w **LIMBO MIĘDZY ŚWIATAMI**.

**GŁOS** przemawia:

> *"NIEWIELU wybiera **ABSOLUTNĄ OFIARĘ**. Zasługujesz na nagrodę."*

**OPCJE REINKARNACJI:**

**ZAKOŃCZENIE: HEROICZNE - "Wieczna Ofiara"**

✨ **SPECJALNA NAGRODA**: Postać {player.character.name} otrzymuje status LEGENDARY w bazie danych.
Przy następnej kampanii możesz ją wskrzesić jako mentora/ducha.
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  ⚡ ULTIMATE SACRIFICE - END  ⚡   ║
╚════════════════════════════════════╝

{player.character.name} places hands on the **THRONE OF SKULLS**.

Your power, soul, everything you are - **FLOWS** into the stone.

```asciidoc
💥 LIGHT EXPLOSION 💥
```

**AZATHUL SCREAMS** in agony, dissolving into millions of particles.

**THRONE CRACKS** with the sound of a breaking world.

**RIFT IMPLODES** - sucking all demons back.

The last thing you see is **ELARA'S FACE** in the portal, screaming your name...

**📜 EPILOGUE - 100 YEARS LATER:**

The kingdom **REBUILT** in times of peace.

In the capital's center stands a **200-METER MONUMENT**:

```
╔══════════════════════════════════╗
║  {player.character.name.upper()}           ║
║  KINGDOM SAVIOR                 ║
║  "Gave life, that we may live"  ║
╚══════════════════════════════════╝
```

**ELARA**, now an old queen, lays flowers at the monument every year.

Her great-grandchildren listen to the **LEGEND of the HERO** who defeated the Demon Lord at the cost of his own soul.

**BARD'S SONG:**

> *"In deepest darkness, when evil triumphed*
> *One heart beat, choosing good*
> *{player.character.name} by name, {player.character.char_class} by class*
> *Gave their life, to close the Abyss themselves."*

**YOUR SOUL:**

But you... feel a strange peace.

Your soul now floats in **LIMBO BETWEEN WORLDS**.

A **VOICE** speaks:

> *"FEW choose **ABSOLUTE SACRIFICE**. You deserve reward."*

**REINCARNATION OPTIONS:**

**ENDING: HEROIC - "Eternal Sacrifice"**

✨ **SPECIAL REWARD**: Character {player.character.name} receives LEGENDARY status in database.
In next campaign you can resurrect them as mentor/spirit.
"""
    
    choices = [
        {"text": "👻 Zostań duchem-mentorem" if lang == "pl" else "👻 Become spirit-mentor",
         "next": "reincarnation_spirit"},
        {"text": "🔄 Reinkarnacja (nowa postać)" if lang == "pl" else "🔄 Reincarnation (new character)",
         "next": "reincarnation_new"}
    ]
    
    # Special legendary status
    player.experience += 1000
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "heroic_sacrifice",
        "outcome": "ultimate_sacrifice",
        "legendary": True
    }


def get_ending_reshape_reality(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Przebudowa rzeczywistości Gate 1"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  🔮 NOWA RZECZYWISTOŚĆ - KONIEC  🔮  ║
╚═══════════════════════════════════════╝

{player.character.name}, teraz **ISTOTA TRANSCENDENTNA**, unosi dłoń.

Rzeczywistość **ZMIENIA SIĘ** na twoje skinienie.

```asciidoc
✨ GATE 1: REWRITING... █████████ 100% ✨
```

**TWOJE ZMIANY:**

**1. ROZŁAM:**
   - Przekształcony w **PORTAL HANDLOWY** między wymiarami
   - Demony? Teraz są **SPRZEDAWCAMI MAGICZNYCH TOWARÓW**
   - Azathul? Zarządza biurem celnym

**2. KRÓLESTWO:**
   - Elara nadal królową, ale teraz z **MAGICZNYMI MOCAMI**
   - Wszyscy mieszkańcy otrzymali **+50 lat życia**
   - Choroby? **WYELIMINOWANE**

**3. SMOK PYRAXIS:**
   - Teraz współrządzi jako **MINISTER MAGII**
   - Doradzajacy sposób, nie tyran

**4. REBELIA:**
   - Już nie potrzebna - sprawiedliwość **AUTOMATYCZNA**
   - Lyra Free? Teraz dyrektor ds. edukacji

**REAKCJE:**

**ELARA** (zaszokowana): *"To... to niemożliwe. Zmieniłeś **SAMĄ ISTOTĘ ŚWIATA**."*

**PYRAXIS**: *"Nawet ja, który żył 10,000 lat, nie widziałem takiej mocy. Jesteś **PONAD** bogami."*

**AZATHUL** (teraz przyjacielski sprzedawca): *"Witam! Potrzebujesz magicznego artefaktu? Mamy promocję!"* (😄)

**LUDZIE** początkowo są przerażeni, ale stopniowo **AKCEPTUJĄ** nową rzeczywistość.

```asciidoc
GATE 1: STATUS - PARADISE MODE ✓
```

**ALE OSTRZEŻENIE:**

Głos z Gate 9 (najwyższa Brama):

> *"Przekroczyłeś próg **BOSKOŚCI**. Pozostałych 8 Bram obserwuje. Niektórzy cię **PODZIWIAJĄ**. Inni cię **BOJĄ SIĘ**. Jeszcze inni... cię **NENADERWIDZĄ**."*

**ZAKOŃCZENIE: TRANSCENDENTNE - "Boski Architekt"**

✨ **EFEKTY:**
- Gate 2-9: Wiedza o tobie się rozprzestrzenia
- Status: GOD-TIER
- Możesz teraz przemieszczać się między Bramami **NATYCHMIAST**
- Osiągnięcie: "Reality Bender"
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  🔮 NEW REALITY - THE END  🔮     ║
╚════════════════════════════════════╝

{player.character.name}, now a **TRANSCENDENT BEING**, raises a hand.

Reality **CHANGES** at your command.

```asciidoc
✨ GATE 1: REWRITING... █████████ 100% ✨
```

**YOUR CHANGES:**

**1. RIFT:**
   - Transformed into **TRADE PORTAL** between dimensions
   - Demons? Now **MAGICAL GOODS MERCHANTS**
   - Azathul? Manages customs office

**2. KINGDOM:**
   - Elara still queen, but now with **MAGICAL POWERS**
   - All citizens received **+50 years lifespan**
   - Diseases? **ELIMINATED**

**3. DRAGON PYRAXIS:**
   - Now co-rules as **MINISTER OF MAGIC**
   - Advisor, not tyrant

**4. REBELLION:**
   - No longer needed - justice **AUTOMATIC**
   - Lyra Free? Now education director

**REACTIONS:**

**ELARA** (shocked): *"This... this is impossible. You changed the **VERY ESSENCE OF THE WORLD**."*

**PYRAXIS**: *"Even I, who lived 10,000 years, haven't seen such power. You are **ABOVE** gods."*

**AZATHUL** (now friendly merchant): *"Welcome! Need a magical artifact? We have a sale!"* (😄)

**PEOPLE** are initially terrified, but gradually **ACCEPT** the new reality.

```asciidoc
GATE 1: STATUS - PARADISE MODE ✓
```

**BUT WARNING:**

Voice from Gate 9 (highest Gate):

> *"You crossed the threshold of **DIVINITY**. The remaining 8 Gates watch. Some **ADMIRE** you. Others **FEAR** you. Still others... **HATE** you."*

**ENDING: TRANSCENDENT - "Divine Architect"**

✨ **EFFECTS:**
- Gates 2-9: Knowledge of you spreads
- Status: GOD-TIER
- You can now move between Gates **INSTANTLY**
- Achievement: "Reality Bender"
"""
    
    choices = [
        {"text": "🚪 Skocz do Gate 5 (środek)" if lang == "pl" else "🚪 Jump to Gate 5 (middle)",
         "next": "gate_5_transition"},
        {"text": "🕰️ Zostań w Gate 1" if lang == "pl" else "🕰️ Stay in Gate 1",
         "next": "g1_paradise_hub"}
    ]
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "transcendent_reshape",
        "outcome": "reality_rewrite"
    }


def get_ending_eternal_throne(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Wieczny tron - zostań bogiem Gate 1"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  👑 WIECZNY TRON - KONIEC  👑        ║
╚═══════════════════════════════════════╝

{player.character.name} zasiada na **TRONIE TRANSCENDENCJI**.

Nie zmieniasz świata. **STAJESZ SIĘ ŚWIATEM**.

```asciidoc
╔══════════════════════════════════╗
║  BOG GATE 1 - {player.character.name.upper()[:20]}  ║
╚══════════════════════════════════╝
```

**TWOJA TRANSFORMACJA:**

• Twoje ciało **ROZPUSZCZA SIĘ** w energię
• Stajesz się **NIEWIDZIALNYM STRAŻNIKIEM** Gate 1
• Czujesz każdą myśl, każde słowo, każdy oddech w tym wymiarze
• **JESTEŚ BOGIEM**, ale więźniem własnej domeny

**📜 WIECZNE PANOWANIE:**

**ROK 1:**
Ludzie cię czczą. Budują świątynie. Modlą się.

**ROK 100:**
Religia oparta na tobie **DOMINUJE** Gate 1.

**ROK 1,000:**
Twoje imię stało się **LEGENDĄ**. Nikt nie pamięta, że byłeś śmiertelnikiem.

**ROK 10,000:**
Jesteś **SAM**. Tak bardzo sam.
Widzisz wszystko, ale **NIE MOŻESZ DOTKNĄĆ**.
Słyszysz wszystko, ale **NIE MOŻESZ ODPOWIEDZIEĆ** (chyba że przez znaki).

**ELARA** dawno umarła. Jej pra-pra-pra wnuki teraz rządzą.

**PYRAXIS** odwiedza ci co 100 lat, jedyny który cię pamięta:

> *"Stary przyjacielu... czy to naprawdę tego chciałeś? **NIEŚMIERTELNOŚĆ** kosztem **ŻYCIA**?"*

**TWOJE MYŚLI:**

Sam na tronie energii, obserwujesz lata, dekady, wieki...

```asciidoc
CZAS: ∞
SAMOTNOŚĆ: ∞
ŻAŁOBA: ▓▓▓▓▓▓▓▓▓▓ 100%
```

**ALE:**

Masz moc. Masz wieczność. Masz... wszystko, czego chciałeś.

*Prawda?*

**ZAKOŃCZENIE: GORZKO-SŁODKIE - "Samotny Bóg"**

✨ **EFEKTY:**
- Nieśmiertelny w Gate 1
- Możesz błogosławić/przeklinać mieszkańców
- **NIE MOŻESZ** opuścić Gate 1 (uwięziony swoim wyborem)
- Osiągnięcie: "Eternal Watcher"

_(Czy to naprawdę wygrana?)_
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  👑 ETERNAL THRONE - THE END  👑  ║
╚════════════════════════════════════╝

{player.character.name} sits on the **THRONE OF TRANSCENDENCE**.

You don't change the world. **YOU BECOME THE WORLD**.

```asciidoc
╔══════════════════════════════════╗
║  GOD OF GATE 1 - {player.character.name.upper()[:20]}  ║
╚══════════════════════════════════╝
```

**YOUR TRANSFORMATION:**

• Your body **DISSOLVES** into energy
• You become the **INVISIBLE GUARDIAN** of Gate 1
• You feel every thought, every word, every breath in this dimension
• **YOU ARE GOD**, but prisoner of your own domain

**📜 ETERNAL REIGN:**

**YEAR 1:**
People worship you. Build temples. Pray.

**YEAR 100:**
Religion based on you **DOMINATES** Gate 1.

**YEAR 1,000:**
Your name became **LEGEND**. No one remembers you were mortal.

**YEAR 10,000:**
You are **ALONE**. So very alone.
You see everything, but **CANNOT TOUCH**.
You hear everything, but **CANNOT RESPOND** (except through signs).

**ELARA** died long ago. Her great-great-great grandchildren now rule.

**PYRAXIS** visits every 100 years, the only one who remembers you:

> *"Old friend... is this really what you wanted? **IMMORTALITY** at the cost of **LIFE**?"*

**YOUR THOUGHTS:**

Alone on the throne of energy, you watch years, decades, centuries...

```asciidoc
TIME: ∞
LONELINESS: ∞
REGRET: ▓▓▓▓▓▓▓▓▓▓ 100%
```

**BUT:**

You have power. You have eternity. You have... everything you wanted.

*Right?*

**ENDING: BITTERSWEET - "Lonely God"**

✨ **EFFECTS:**
- Immortal in Gate 1
- Can bless/curse inhabitants
- **CANNOT** leave Gate 1 (trapped by your choice)
- Achievement: "Eternal Watcher"

_(Was this really a victory?)_
"""
    
    choices = [
        {"text": "😢 Akceptuj los" if lang == "pl" else "😢 Accept fate",
         "next": "g1_god_eternal"},
        {"text": "🔄 Cofnij decyzję (jeśli możliwe)" if lang == "pl" else "🔄 Undo decision (if possible)",
         "next": "g1_main_050",
         "effects": {"rewind": True}}
    ]
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "bittersweet_god",
        "outcome": "eternal_throne"
    }


def get_ending_dragon_merge(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Fuzja ze smokiem - stajesz się pół-smokiem"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  🐉 FUZJA DRAGONA - KONIEC  🐉       ║
╚═══════════════════════════════════════╝

Rozłam **EKSPLODUJE** w ostatnim ataku.

{player.character.name} i **PYRAXIS FLAMEHEART** - obydwoje śmiertelnie ranni.

**PYRAXIS** (umierając): *"Jest... jeden sposób... starodawna magia... FUZJA DUSZ..."*

Twoja dłoń dotyka łuski smoka.

```asciidoc
🔥🐉 POŁĄCZENIE... AKTYWNE 🐉🔥
```

**BOL** - twoje ciało **PRZEKSZTAŁCA SIĘ**.

**📜 TRANSFORMACJA:**

• Skóra staje się **ŁUSKOWATA** (lazurowo-złota)
• Z pleców wyrastają **SKRZYDŁA** (15-metrowa rozpiętość)
• Oczy płoną **ZŁOTYM OGNIEM**
• Wzrost: **3 METRY**
• Pazury, kły, ogon

**JESTEŚ TERAZ:**

**DRAKOŃSKIM WOJOWNIKIEM** - hybryda człowieka i starożytnego smoka.

**MOCE:**
├─ 🔥 Smocze Tchnienie (120 dmg, AOE)
├─ 🪽 Lot (500 km/h)
├─ 🛡️ Łuski (Defense +15)
├─ 💎 Żywotność x5 (500 HP total)
├─ 📚 Pamięć Pyraxisa (10,000 lat wiedzy)
└─ 👁️ Darkvision 500 metrów

**PYRAXIS GŁOS** (w twojej głowie):

> *"Żyjemy... razem. Moja dusza, twoje serce. **JESTEM TY**. **TY JESTEŚ MNĄ**."*

**REAKCJE:**

**ELARA** (przerażona, ale zafascynowana): *"Ty... ty wciąż jesteś sobą?"*

**TY** (podwójny głos - twój + dragon): *"Tak. I nie. Jestem **CZYMŚ WIĘCEJ**."*

**KRÓLESTWO** początkowo się boi, ale stopniowo akceptuje.

Zostajesz **PIERWSZYM DRAKOŃSKIM RYCERZEM** - legenda żywa.

```asciidoc
RASA: HUMAN-DRAGON HYBRID
STATUS: LEGENDARY
LATA ŻYCIA: ~2000
```

**ZAKOŃCZENIE: FUZJA - "Drakoński Wojownik"**

✨ **EFEKTY:**
- Unlock: Draconic Knight class (unikalna)
- Możesz przejść do Gate 2 jako hybryd
- +1000 do wszystkich statystyk
- Osiągnięcie: "Dragon Merger"

**ALE:**

Każdej nocy **ŚNISZ SNY PYRAXISA** - 10,000 lat wspomnień.

Czasami nie wiesz, gdzie kończy się {player.character.name}, a zaczyna Pyraxis...
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  🐉 DRAGON FUSION - THE END  🐉   ║
╚════════════════════════════════════╝

The Rift **EXPLODES** in final attack.

{player.character.name} and **PYRAXIS FLAMEHEART** - both mortally wounded.

**PYRAXIS** (dying): *"There is... one way... ancient magic... SOUL FUSION..."*

Your hand touches dragon's scales.

```asciidoc
🔥🐉 MERGING... ACTIVE 🐉🔥
```

**PAIN** - your body **TRANSFORMS**.

**📜 TRANSFORMATION:**

• Skin becomes **SCALED** (azure-gold)
• **WINGS** grow from back (15-meter wingspan)
• Eyes burn with **GOLDEN FIRE**
• Height: **3 METERS**
• Claws, fangs, tail

**YOU ARE NOW:**

**DRACONIC WARRIOR** - hybrid of human and ancient dragon.

**POWERS:**
├─ 🔥 Dragon Breath (120 dmg, AOE)
├─ 🪽 Flight (500 km/h)
├─ 🛡️ Scales (Defense +15)
├─ 💎 Vitality x5 (500 HP total)
├─ 📚 Pyraxis's Memory (10,000 years knowledge)
└─ 👁️ Darkvision 500 meters

**PYRAXIS VOICE** (in your head):

> *"We live... together. My soul, your heart. **I AM YOU**. **YOU ARE ME**."*

**REACTIONS:**

**ELARA** (terrified but fascinated): *"You... are you still yourself?"*

**YOU** (dual voice - yours + dragon): *"Yes. And no. I am **SOMETHING MORE**."*

**KINGDOM** is initially afraid, but gradually accepts.

You become the **FIRST DRACONIC KNIGHT** - a living legend.

```asciidoc
RACE: HUMAN-DRAGON HYBRID
STATUS: LEGENDARY
LIFESPAN: ~2000 years
```

**ENDING: FUSION - "Draconic Warrior"**

✨ **EFFECTS:**
- Unlock: Draconic Knight class (unique)
- Can proceed to Gate 2 as hybrid
- +1000 to all stats
- Achievement: "Dragon Merger"

**BUT:**

Every night you **DREAM PYRAXIS'S DREAMS** - 10,000 years of memories.

Sometimes you don't know where {player.character.name} ends and Pyraxis begins...
"""
    
    choices = [
        {"text": "🚪 Przejdź do Gate 2 (jako hybryd)" if lang == "pl" else "🚪 Proceed to Gate 2 (as hybrid)",
         "next": "gate_2_transition",
         "effects": {"gate": 2, "race": "draconic_hybrid"}},
        {"text": "🏔️ Zamieszkaj w górach" if lang == "pl" else "🏔️ Live in mountains",
         "next": "g1_dragon_mountain_home"}
    ]
    
    # Massive stat boosts
    player.hp += 400
    player.experience += 700
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "transformation_fusion",
        "outcome": "dragon_merge"
    }


def get_ending_exile(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Wygnanie - zbyt wiele strasznych wyborów"""
    
    # Count evil actions
    evil_score = 0
    if state.quest_flags.get("villages_destroyed", 0) > 3:
        evil_score += 3
    if state.quest_flags.get("rebellion_destroyed"):
        evil_score += 2
    if state.quest_flags.get("dragon_hostile"):
        evil_score += 2
    if state.quest_flags.get("moral_alignment") == "evil":
        evil_score += 3
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  ⚖️ WYGNANIE - KONIEC GORZKI  ⚖️     ║
╚═══════════════════════════════════════╝

Rozłam **ZAMYKA SIĘ**.

Królestwo **URATOWANE**.

Ale... **CY JEST BOHATEREM**?

**SER MARKUS** podchodzi, twarz jak kamień:

> *"{player.character.name}. W imieniu Korony i Ludu... **JESTEŚ WYGNANY**."*

**TWOJE ZBRODNIE:**

{f"• Zniszczono {state.villages_destroyed} wiosek (setki cywilów martwych) 💀" if hasattr(state, 'villages_destroyed') and state.villages_destroyed > 0 else ""}
{f"• Rebelia zmasakrowana (300+ egzekucji) ⚔️" if state.quest_flags.get("rebellion_destroyed") else ""}
{f"• Smok Pyraxis zabity (gatunkobójstwo) 🐉" if state.quest_flags.get("dragon_hostile") and state.quest_flags.get("varathul_defeated") else ""}
{f"• Księża zamordowani (świętokradztwo) ⛪" if state.quest_flags.get("priests_killed") else ""}
{f"• Demon pakt inicjowany (zdrada) 👿" if state.quest_flags.get("dark_pact_offered") else ""}

**OCENA MORALNA:**
```
Dobro:  {"▓" * max(0, 10 - evil_score)}{"░" * evil_score}
Zło:    {"▓" * evil_score}{"░" * max(0, 10 - evil_score)}
Wynik:  {evil_score}/10 (ZŁE CZYNY)
```

**ELARA** odwraca wzrok, płacze:

> *"Uratowałeś królestwo... ale **JAKĄKOLWIEK CENĘ**. Zbyt wiele niewinnych umarło przez twoje wybory. Nie mogę cię nagrodzić."*

**WYROK:**

• **DOŻYWOTNIE WYGNANIE** z królestwa
• Zakaz wstępu do wszystkich miast
• Twoje imię **WYMAZANE** z kronik
• Nagroda: **0 złota**
• Tytuł: *"Morderczy Zbawca"*

**LUDZIE** rzucają kamieniami gdy opuszczasz bramę.

```asciidoc
═══════════════════════════════════
  WYPROWADZENIE - GODZINA 13:00
       (NIECH NIGDY NIE WRÓCI)
═══════════════════════════════════
```

**1 ROK PÓŹNIEJ:**

Wędrierzeszz samotnie przez dzikie ziemie.

Każdej nocy **DUCHY ZABITYCH** nawiedzają twoje sny.

Wioski zamykają drzwi na twój widok. Twoja twarz na plakatach "WANTED - NIE ZABIJAĆ, TYLKO WYGNAĆ".

**PYRAXIS GŁOS** (jeśli żyje): *"Widzisz, śmiertelniku? **CZYNY MAJĄ KONSEKWENCJE**. Moc bez mądrości = zniszczenie."*

**ZAKOŃCZENIE: TRAGICZNE - "Samotny Wygnańc"**

❌ **KONSEKWENCJE:**
- Brak dostępu do Gate 2
- Wszystkie reputacje: -100
- Tytuł: "Exiled Savior"
- Osiągnięcie: "Fall from Grace"

**MOŻLIWOŚĆ ODKUPIENIA:**
_(Dodatkowa kampania side-quest: "Droga Odkupienia" - 20 misji dobra)_
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  ⚖️ EXILE - BITTER END  ⚖️         ║
╚════════════════════════════════════╝

The Rift **CLOSES**.

Kingdom **SAVED**.

But... **ARE YOU A HERO**?

**SER MARKUS** approaches, face like stone:

> *"{player.character.name}. In the name of Crown and People... **YOU ARE EXILED**."*

**YOUR CRIMES:**

{f"• Destroyed {state.villages_destroyed} villages (hundreds of civilians dead) 💀" if hasattr(state, 'villages_destroyed') and state.villages_destroyed > 0 else ""}
{f"• Rebellion massacred (300+ executions) ⚔️" if state.quest_flags.get("rebellion_destroyed") else ""}
{f"• Dragon Pyraxis killed (genocide) 🐉" if state.quest_flags.get("dragon_hostile") and state.quest_flags.get("varathul_defeated") else ""}
{f"• Priests murdered (sacrilege) ⛪" if state.quest_flags.get("priests_killed") else ""}
{f"• Demon pact initiated (treason) 👿" if state.quest_flags.get("dark_pact_offered") else ""}

**MORAL ASSESSMENT:**
```
Good:   {"▓" * max(0, 10 - evil_score)}{"░" * evil_score}
Evil:   {"▓" * evil_score}{"░" * max(0, 10 - evil_score)}
Score:  {evil_score}/10 (EVIL DEEDS)
```

**ELARA** turns away, crying:

> *"You saved the kingdom... but **AT ANY COST**. Too many innocents died by your choices. I cannot reward you."*

**SENTENCE:**

• **LIFETIME EXILE** from kingdom
• Banned from all cities
• Your name **ERASED** from chronicles
• Reward: **0 gold**
• Title: *"Murderous Savior"*

**PEOPLE** throw stones as you leave the gate.

```asciidoc
═══════════════════════════════════
  EXPULSION - HOUR 13:00
       (MAY NEVER RETURN)
═══════════════════════════════════
```

**1 YEAR LATER:**

You wander alone through wild lands.

Every night **GHOSTS OF THE SLAIN** haunt your dreams.

Villages close doors at your sight. Your face on posters "WANTED - DON'T KILL, JUST EXILE".

**PYRAXIS VOICE** (if alive): *"See, mortal? **ACTIONS HAVE CONSEQUENCES**. Power without wisdom = destruction."*

**ENDING: TRAGIC - "Lonely Exile"**

❌ **CONSEQUENCES:**
- No Gate 2 access
- All reputations: -100
- Title: "Exiled Savior"
- Achievement: "Fall from Grace"

**REDEMPTION POSSIBILITY:**
_(Additional side-quest campaign: "Road to Redemption" - 20 good missions)_
"""
    
    choices = [
        {"text": "💔 Zaakceptuj wygnanie" if lang == "pl" else "💔 Accept exile",
         "next": "g1_exile_life"},
        {"text": "🔥 Rozpocznij Drogę Odkupienia" if lang == "pl" else "🔥 Start Redemption Path",
         "next": "g1_redemption_quest_001"}
    ]
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "tragic_exile",
        "outcome": "exiled"
    }


def get_ending_timeloop(lang: str, state: Gate1WorldState, player) -> Dict:
    """Zakończenie: Pętla czasu - utknięcie w nieskończonym cyklu"""
    
    if lang == "pl":
        text = f"""╔═══════════════════════════════════════╗
║  ⏰ PĘTLA CZASU - KONIEC...?  ⏰     ║
╚═══════════════════════════════════════╝

Rozłam **NIE ZAMYKA SIĘ**.

Ale też **NIE OTWIERA SIĘ** bardziej.

Coś poszło **STRASZNIE ŹLE**.

**CZAS ZATRZYMUJE SIĘ**.

Wszystko **ZAMRAŻA** w miejscu - ludzie, ptaki, chmury.

Tylko **TY** możesz się poruszać.

```asciidoc
⏰ ANOMALIA CZASOWA WYKRYTA ⏰
   LOADING... ERROR... RESET...
```

**GŁOS Z ROZŁAMU** (mechaniczny, nie-ludzki):

> *"BŁĄD PARADOKSU WYKRYTY. PRZYWRACANIE PUNKTU ZAPISU. 3... 2... 1..."*

**BŁYSK ŚWIATŁA.**

---

Budzisz się przed **BRAMĄ GATE 1**.

To samo intro. Ta sama data.

**DÉJÀ VU.**

Wszystko dokładnie tak samo jak **PIERWSZY RAZ**.

**PRÓBUJESZ INACZEJ:**

• Mówisz inaczej - Ser Markus odpowiada **DOKŁADNIE TAK SAMO**
• Idziesz inną drogą - **WYNIK IDENTYCZNY**
• Atakujesz wcześniej - **CZAS RESETUJE ZNOWU**

```asciidoc
═══════════════════════════════
  PĘTLA #1    ✓ UKOŃCZONA
  PĘTLA #2    ✓ UKOŃCZONA  
  PĘTLA #3    ✓ UKOŃCZONA
  PĘTLA #4    ✓ UKOŃCZONA
  ...
  PĘTLA #477  ◄ AKTYWNA
═══════════════════════════════
```

**PĘTLA #477:**

{player.character.name}, wiesz już **KAŻDE SŁOWO** każdej osoby.

Przewidujesz każdy atak. Znasz każdą pułapkę.

Ale **NIE MOŻESZ UCIEC**.

**SER MARKUS** (po raz 477.): *"Witaj wędrowcze. Kim jesteś?"*

**TY** (szalony śmiech): *"Nazywam się {player.character.name}. Jestem **UWIĘZIONY W PĘTLI CZASU**. Czy to pyta się już **477. RAZ**?"*

**SER MARKUS**: *"Witaj wędrowcze. Kim jesteś?"* [identyczna intonacja]

```asciidoc
🔄 SYSTEM STUCK IN LOOP 🔄
>> CANNOT BREAK CYCLE
>> REASON: PARADOX UNRESOLVED
>> SOLUTION: UNKNOWN
```

**PRAWDA:**

Pewnego wyboru **POPEŁNIŁEŚ PARADOKS CZASOWY**.

Może zapisałeś kogoś, kto powinien zginąć?
Może zabiłeś kogoś, kto musiał żyć?

**ROZŁAM** nie może się domknąć, bo **PRZYCZYNOWOŚĆ JEST ZŁAMANA**.

**ZAKOŃCZENIE: HORROR - "Wieczna Pętla"**

⏰ **STAN:**
- Uwięziony w pętli czasowej Gate 1
- Loop count: ∞
- Świadomość: ZACHOWANA (najgorsze)
- Możliwość ucieczki: 0.001%

**OPCJE:**

1. **ZAAKCEPTUJ PĘTLĘ** - żyj w nieskończonej repetycji
2. **SZUKAJ ROZWIĄZANIA** - eksperymentuj z każdym wyborem (może po 10,000 pętlach znajdziesz wyjście?)
3. **ZATRAC ŚWIADOMOŚĆ** - pozwól umysłowi upaść, zapomnij, zresetuj pamięć

*Najbardziej przerażające zakończenie - gorsz niż śmierć.*
"""
    else:  # EN
        text = f"""╔════════════════════════════════════╗
║  ⏰ TIME LOOP - THE END...?  ⏰   ║
╚════════════════════════════════════╝

The Rift **DOESN'T CLOSE**.

But it **DOESN'T EXPAND** further either.

Something went **TERRIBLY WRONG**.

**TIME STOPS**.

Everything **FREEZES** in place - people, birds, clouds.

Only **YOU** can move.

```asciidoc
⏰ TIME ANOMALY DETECTED ⏰
   LOADING... ERROR... RESET...
```

**VOICE FROM RIFT** (mechanical, inhuman):

> *"PARADOX ERROR DETECTED. RESTORING SAVE POINT. 3... 2... 1..."*

**FLASH OF LIGHT.**

---

You wake up at **GATE 1 ENTRANCE**.

Same intro. Same date.

**DÉJÀ VU.**

Everything exactly like the **FIRST TIME**.

**YOU TRY DIFFERENTLY:**

• Speak differently - Ser Markus responds **EXACTLY THE SAME**
• Take different path - **IDENTICAL RESULT**
• Attack earlier - **TIME RESETS AGAIN**

```asciidoc
═══════════════════════════════
  LOOP #1    ✓ COMPLETED
  LOOP #2    ✓ COMPLETED  
  LOOP #3    ✓ COMPLETED
  LOOP #4    ✓ COMPLETED
  ...
  LOOP #477  ◄ ACTIVE
═══════════════════════════════
```

**LOOP #477:**

{player.character.name}, you know **EVERY WORD** of every person.

You predict every attack. Know every trap.

But **YOU CANNOT ESCAPE**.

**SER MARKUS** (477th time): *"Greetings traveler. Who are you?"*

**YOU** (mad laughter): *"My name is {player.character.name}. I am **TRAPPED IN TIME LOOP**. Is this the **477TH TIME** you ask?"*

**SER MARKUS**: *"Greetings traveler. Who are you?"* [identical intonation]

```asciidoc
🔄 SYSTEM STUCK IN LOOP 🔄
>> CANNOT BREAK CYCLE
>> REASON: PARADOX UNRESOLVED
>> SOLUTION: UNKNOWN
```

**TRUTH:**

At some choice you **CREATED TIME PARADOX**.

Maybe saved someone who should have died?
Maybe killed someone who had to live?

**RIFT** cannot close because **CAUSALITY IS BROKEN**.

**ENDING: HORROR - "Eternal Loop"**

⏰ **STATUS:**
- Trapped in Gate 1 time loop
- Loop count: ∞
- Consciousness: PRESERVED (worst part)
- Escape chance: 0.001%

**OPTIONS:**

1. **ACCEPT LOOP** - live in infinite repetition
2. **SEARCH SOLUTION** - experiment with every choice (maybe after 10,000 loops find exit?)
3. **LOSE CONSCIOUSNESS** - let mind fall, forget, reset memory

*Most terrifying ending - worse than death.*
"""
    
    choices = [
        {"text": "😱 KONTYNUUJ SZUKANIE" if lang == "pl" else "😱 KEEP SEARCHING",
         "next": "g1_main_001",
         "effects": {"loop_count": (state.quest_flags.get("loop_count", 0) + 1)}},
        {"text": "🧠 ZATRAĆ PAMIĘĆ" if lang == "pl" else "🧠 LOSE MEMORY",
         "next": "g1_mindwipe"},
        {"text": "🔄 ZRESETUJ KAMPANIĘ" if lang == "pl" else "🔄 RESET CAMPAIGN",
         "next": "reset_gate1"}
    ]
    
    # Track loop count
    if "loop_count" not in state.quest_flags:
        state.quest_flags["loop_count"] = 1
    else:
        state.quest_flags["loop_count"] += 1
    
    return {
        "text": text,
        "choices": choices,
        "is_ending": True,
        "ending_type": "horror_timeloop",
        "outcome": "infinite_loop"
    }

