# ========================================
# MAFIA / WEREWOLF SYSTEM v2
# Complete Rewrite with proper Settings Interface
# ========================================

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime

# ========================================
# ROLE DEFINITIONS - EXPANDABLE SYSTEM
# ========================================

ROLES_DATABASE = {
    # 🕴️ MAFIA - NORMAL MODE
    "mafia_normal": {
        "TOWN": {
            "citizen": {"name_en": "Citizen", "name_pl": "Obywatel", "emoji": "😇", "power": None},
            "detective": {"name_en": "Detective", "name_pl": "Detektyw", "emoji": "🕵", "power": "investigate"},
            "doctor": {"name_en": "Doctor", "name_pl": "Lekarz", "emoji": "🥼", "power": "protect"},
            "bodyguard": {"name_en": "Bodyguard", "name_pl": "Strażnik", "emoji": "🛡", "power": "guard"},
            "witness": {"name_en": "Witness", "name_pl": "Świadek", "emoji": "👁", "power": "track"},
            "reporter": {"name_en": "Reporter", "name_pl": "Reporter", "emoji": "📰", "power": "reveal_dead"},
        },
        "MAFIA": {
            "mafioso": {"name_en": "Mafioso", "name_pl": "Mafiozo", "emoji": "🔫", "power": "kill"},
            "don": {"name_en": "Don", "name_pl": "Don", "emoji": "🎩", "power": "kill_leader"},
            "shadow": {"name_en": "Shadow", "name_pl": "Cień", "emoji": "👤", "power": "stealth"},
        },
        "NEUTRAL": {
            "jester": {"name_en": "Jester", "name_pl": "Błazen", "emoji": "🤡", "power": "lynch_win"},
            "mercenary": {"name_en": "Mercenary", "name_pl": "Najemnik", "emoji": "💼", "power": "contract"},
        }
    },
    
    # 🕴️ MAFIA - ADVANCED MODE
    "mafia_advanced": {
        "TOWN": {
            "citizen": {"name_en": "Citizen", "name_pl": "Obywatel", "emoji": "😇", "power": None},
            "detective": {"name_en": "Detective", "name_pl": "Detektyw", "emoji": "🕵️", "power": "investigate"},
            "doctor": {"name_en": "Doctor", "name_pl": "Lekarz", "emoji": "🥼", "power": "protect"},
            "analyst": {"name_en": "Analyst", "name_pl": "Analityk", "emoji": "📊", "power": "stats"},
            "profiler": {"name_en": "Profiler", "name_pl": "Profiler", "emoji": "🧠", "power": "hints"},
            "observer": {"name_en": "Observer", "name_pl": "Obserwator", "emoji": "👀", "power": "visits"},
            "coroner": {"name_en": "Coroner", "name_pl": "Koroner", "emoji": "🔬", "power": "death_cause"},
            "prosecutor": {"name_en": "Prosecutor", "name_pl": "Prokurator", "emoji": "⚖", "power": "reveal"},
            "judge": {"name_en": "Judge", "name_pl": "Sędzia", "emoji": "⚖", "power": "cancel_vote"},
            "negotiator": {"name_en": "Negotiator", "name_pl": "Negocjator", "emoji": "🤝", "power": "delay"},
            "hacker": {"name_en": "Hacker", "name_pl": "Haker", "emoji": "💻", "power": "logs"},
            "evidence_guard": {"name_en": "Evidence Guard", "name_pl": "Strażnik Dowodów", "emoji": "📋", "power": "secure"},
            "lighthouse": {"name_en": "Lighthouse", "name_pl": "Latarnik", "emoji": "🗼", "power": "suspicious"},
            "speaker": {"name_en": "Speaker", "name_pl": "Mówca", "emoji": "📢", "power": "double_vote"},
            "silent": {"name_en": "Silent", "name_pl": "Milczący", "emoji": "🤫", "power": "no_vote_strong"},
            "mediator": {"name_en": "Mediator", "name_pl": "Mediator", "emoji": "🤝", "power": "connect"},
        },
        "MAFIA": {
            "mafioso": {"name_en": "Mafioso", "name_pl": "Mafiozo", "emoji": "🔫", "power": "kill"},
            "don": {"name_en": "Don", "name_pl": "Don", "emoji": "🎩", "power": "kill_leader"},
            "forger": {"name_en": "Forger", "name_pl": "Fałszerz", "emoji": "✍️", "power": "fake_reports"},
            "infiltrator": {"name_en": "Infiltrator", "name_pl": "Infiltrator", "emoji": "🎭", "power": "steal"},
            "saboteur": {"name_en": "Saboteur", "name_pl": "Sabotażysta", "emoji": "💣", "power": "block"},
            "recruiter": {"name_en": "Recruiter", "name_pl": "Rekruter", "emoji": "🤵", "power": "convert"},
            "briber": {"name_en": "Briber", "name_pl": "Łapówkarz", "emoji": "💰", "power": "buy_votes"},
            "executioner": {"name_en": "Executioner", "name_pl": "Egzekutor", "emoji": "⚔️", "power": "unstoppable"},
            "pr_agent": {"name_en": "PR Agent", "name_pl": "PR-owiec", "emoji": "📺", "power": "lower_sus"},
            "shadow": {"name_en": "Shadow", "name_pl": "Cień", "emoji": "👤", "power": "stealth"},
            "agent": {"name_en": "Agent", "name_pl": "Agent", "emoji": "🕴️", "power": "fake_town"},
        },
        "NEUTRAL": {
            "opportunist": {"name_en": "Opportunist", "name_pl": "Oportunista", "emoji": "🎯", "power": "top3"},
            "agitator": {"name_en": "Agitator", "name_pl": "Podżegacz", "emoji": "📣", "power": "chaos"},
            "escapee": {"name_en": "Escapee", "name_pl": "Uciekinier", "emoji": "🏃", "power": "survive_x"},
            "secret_collector": {"name_en": "Secret Collector", "name_pl": "Kolekcjoner Sekretów", "emoji": "🗂️", "power": "info"},
            "balance_keeper": {"name_en": "Balance Keeper", "name_pl": "Strażnik Równowagi", "emoji": "⚖️", "power": "buff_weak"},
            "contractor": {"name_en": "Contractor", "name_pl": "Kontraktor", "emoji": "📜", "power": "contract"},
            "blackmailer": {"name_en": "Blackmailer", "name_pl": "Szantażysta", "emoji": "🎭", "power": "force"},
            "chaos_observer": {"name_en": "Chaos Observer", "name_pl": "Obserwator Chaosu", "emoji": "🌀", "power": "chaos_win"},
        },
        "CHAOS": {
            "anarchist": {"name_en": "Anarchist", "name_pl": "Anarchista", "emoji": "⚫", "power": "reverse_vote"},
            "system_saboteur": {"name_en": "System Saboteur", "name_pl": "Sabotażysta Systemowy", "emoji": "💥", "power": "break_night"},
            "illusionist": {"name_en": "Illusionist", "name_pl": "Iluzjonista", "emoji": "🎪", "power": "fake_reports"},
            "random": {"name_en": "Random", "name_pl": "Losowy", "emoji": "🎲", "power": "random"},
            "catalyst": {"name_en": "Catalyst", "name_pl": "Katalizator", "emoji": "⚗", "power": "grow"},
            "paranoia_agent": {"name_en": "Paranoia Agent", "name_pl": "Agent Paranoi", "emoji": "👁", "power": "anonymous_dm"},
            "false_prophet": {"name_en": "False Prophet", "name_pl": "Błędny Prorok", "emoji": "🔮", "power": "50_lie"},
            "vote_manipulator": {"name_en": "Vote Manipulator", "name_pl": "Manipulator Głosów", "emoji": "🗳", "power": "swap_votes"},
        }
    },
    
    # 🐺 WEREWOLF - NORMAL MODE
    "werewolf_normal": {
        "VILLAGE": {
            "villager": {"name_en": "Villager", "name_pl": "Wieśniak", "emoji": "👨", "power": None},
            "seer": {"name_en": "Seer", "name_pl": "Jasnowidz", "emoji": "🔮", "power": "investigate"},
            "doctor": {"name_en": "Doctor", "name_pl": "Lekarz", "emoji": "💊", "power": "protect"},
            "hunter": {"name_en": "Hunter", "name_pl": "Łowca", "emoji": "🏹", "power": "revenge_kill"},
            "watcher": {"name_en": "Watcher", "name_pl": "Obserwator", "emoji": "👁", "power": "track"},
        },
        "WEREWOLVES": {
            "werewolf": {"name_en": "Werewolf", "name_pl": "Wilkołak", "emoji": "🐺", "power": "kill"},
            "alpha_wolf": {"name_en": "Alpha Wolf", "name_pl": "Alfa", "emoji": "👑", "power": "kill_leader"},
        },
        "NEUTRAL": {
            "fool": {"name_en": "Fool", "name_pl": "Głupiec", "emoji": "🤡", "power": "lynch_win"},
            "survivor": {"name_en": "Survivor", "name_pl": "Ocalały", "emoji": "🏕", "power": "survive"},
        }
    },
    
    # 🐺 WEREWOLF - ADVANCED MODE
    "werewolf_advanced": {
        "VILLAGE": {
            "villager": {"name_en": "Villager", "name_pl": "Wieśniak", "emoji": "👨", "power": None},
            "seer": {"name_en": "Seer", "name_pl": "Jasnowidz", "emoji": "🔮", "power": "investigate"},
            "doctor": {"name_en": "Doctor", "name_pl": "Lekarz", "emoji": "💊", "power": "protect"},
            "witch": {"name_en": "Witch", "name_pl": "Wiedźma", "emoji": "🧙", "power": "potions"},
            "medium": {"name_en": "Medium", "name_pl": "Medium", "emoji": "👻", "power": "dead_chat"},
            "tracker": {"name_en": "Tracker", "name_pl": "Tropiciel", "emoji": "🔍", "power": "track"},
            "priest": {"name_en": "Priest", "name_pl": "Ksiądz", "emoji": "✝", "power": "block_curse"},
            "blacksmith": {"name_en": "Blacksmith", "name_pl": "Kowal", "emoji": "🔨", "power": "armor"},
            "bard": {"name_en": "Bard", "name_pl": "Bard", "emoji": "🎵", "power": "influence"},
            "archivist": {"name_en": "Archivist", "name_pl": "Archiwista", "emoji": "📚", "power": "old_actions"},
            "prophet": {"name_en": "Prophet", "name_pl": "Prorok", "emoji": "✨", "power": "future"},
            "oracle": {"name_en": "Oracle", "name_pl": "Wyrocznia", "emoji": "🌙", "power": "riddles"},
            "guardian": {"name_en": "Guardian", "name_pl": "Strażnik", "emoji": "🛡️", "power": "sacrifice"},
            "exorcist": {"name_en": "Exorcist", "name_pl": "Egzorcysta", "emoji": "📿", "power": "remove_curse"},
            "herbalist": {"name_en": "Herbalist", "name_pl": "Zielarz", "emoji": "🌿", "power": "potions"},
            "dreamer": {"name_en": "Dreamer", "name_pl": "Śniący", "emoji": "💤", "power": "dreams"},
        },
        "WEREWOLVES": {
            "werewolf": {"name_en": "Werewolf", "name_pl": "Wilkołak", "emoji": "🐺", "power": "kill"},
            "alpha_wolf": {"name_en": "Alpha Wolf", "name_pl": "Alfa", "emoji": "👑", "power": "kill_leader"},
            "shapeshifter": {"name_en": "Shapeshifter", "name_pl": "Zmiennokształtny", "emoji": "🎭", "power": "disguise"},
            "cursed_wolf": {"name_en": "Cursed Wolf", "name_pl": "Przeklęty Wilk", "emoji": "😈", "power": "fake_villager"},
            "night_stalker": {"name_en": "Night Stalker", "name_pl": "Nocny Tropiciel", "emoji": "🌑", "power": "track"},
            "blood_hunter": {"name_en": "Blood Hunter", "name_pl": "Łowca Krwi", "emoji": "🩸", "power": "grow"},
            "howler": {"name_en": "Howler", "name_pl": "Wyjący", "emoji": "🌕", "power": "vote_influence"},
            "feral_wolf": {"name_en": "Feral Wolf", "name_pl": "Dziki Wilk", "emoji": "🐾", "power": "unpredictable"},
            "ancient_wolf": {"name_en": "Ancient Wolf", "name_pl": "Prawieczny Wilk", "emoji": "🌑", "power": "event"},
        },
        "NEUTRAL": {
            "fool": {"name_en": "Fool", "name_pl": "Głupiec", "emoji": "🤡", "power": "lynch_win"},
            "cultist": {"name_en": "Cultist", "name_pl": "Kultysta", "emoji": "🕯️", "power": "recruit"},
            "lone_wolf": {"name_en": "Lone Wolf", "name_pl": "Samotny Wilk", "emoji": "🌙", "power": "solo"},
            "doppelganger": {"name_en": "Doppelganger", "name_pl": "Sobowtór", "emoji": "👥", "power": "copy"},
            "avenger": {"name_en": "Avenger", "name_pl": "Mściciel", "emoji": "⚡", "power": "revenge"},
            "wanderer": {"name_en": "Wanderer", "name_pl": "Wędrowiec", "emoji": "🚶", "power": "survive"},
            "beast_tamer": {"name_en": "Beast Tamer", "name_pl": "Pogromca Bestii", "emoji": "🦁", "power": "control"},
            "time_drifter": {"name_en": "Time Drifter", "name_pl": "Podróżnik Czasu", "emoji": "⏳", "power": "manipulate_turns"},
        },
        "CHAOS": {
            "trickster": {"name_en": "Trickster", "name_pl": "Kuglar z", "emoji": "🃏", "power": "mix_reports"},
            "mad_prophet": {"name_en": "Mad Prophet", "name_pl": "Szalony Prorok", "emoji": "🔮", "power": "random_visions"},
            "reality_breaker": {"name_en": "Reality Breaker", "name_pl": "Łamacz Rzeczywistości", "emoji": "🌀", "power": "break_night"},
            "void_caller": {"name_en": "Void Caller", "name_pl": "Wyzywacz Pustki", "emoji": "🕳️", "power": "summon"},
            "entropy": {"name_en": "Entropy", "name_pl": "Entropia", "emoji": "💫", "power": "decay"},
            "paranoiac": {"name_en": "Paranoiac", "name_pl": "Paranoik", "emoji": "😰", "power": "conflicts"},
            "glitch": {"name_en": "Glitch", "name_pl": "Błąd", "emoji": "⚠️", "power": "random_effects"},
            "harbinger": {"name_en": "Harbinger", "name_pl": "Zwiastun", "emoji": "☠️", "power": "catastrophe"},
        }
    }
}

# ========================================
# PRESETS - BALANCED CONFIGURATIONS
# ========================================

PRESETS = {
    "mafia_normal": {
        6: ["mafioso", "don", "detective", "doctor", "citizen", "citizen"],
        8: ["mafioso", "mafioso", "don", "detective", "doctor", "bodyguard", "citizen", "citizen"],
        10: ["mafioso", "mafioso", "don", "shadow", "detective", "doctor", "witness", "citizen", "citizen", "citizen"],
        12: ["mafioso", "mafioso", "mafioso", "don", "detective", "doctor", "bodyguard", "reporter", "citizen", "citizen", "citizen", "citizen"],
        16: ["mafioso", "mafioso", "mafioso", "mafioso", "don", "shadow", "detective", "doctor", "bodyguard", "witness", "reporter", "citizen", "citizen", "citizen", "citizen", "citizen"],
    },
    "mafia_advanced": {
        8: ["mafioso", "mafioso", "forger", "detective", "doctor", "observer", "jester", "citizen"],
        10: ["mafioso", "mafioso", "don", "saboteur", "detective", "doctor", "coroner", "agitator", "citizen", "citizen"],
        12: ["mafioso", "mafioso", "mafioso", "don", "infiltrator", "forger", "detective", "doctor", "judge", "secret_collector", "citizen", "citizen"],
        16: ["mafioso", "mafioso", "mafioso", "mafioso", "don", "executioner", "briber", "detective", "hacker", "doctor", "prosecutor", "jester", "paranoia_agent", "citizen", "citizen", "citizen"],
    },
    "werewolf_normal": {
        6: ["werewolf", "seer", "doctor", "villager", "villager", "villager"],
        8: ["werewolf", "werewolf", "alpha_wolf", "seer", "doctor", "villager", "villager", "villager"],
        10: ["werewolf", "werewolf", "alpha_wolf", "seer", "doctor", "hunter", "villager", "villager", "villager", "villager"],
        12: ["werewolf", "werewolf", "werewolf", "alpha_wolf", "seer", "doctor", "hunter", "villager", "villager", "villager", "villager", "villager"],
    },
    "werewolf_advanced": {
        8: ["werewolf", "werewolf", "alpha_wolf", "witch", "seer", "tracker", "fool", "villager"],
        10: ["werewolf", "werewolf", "alpha_wolf", "shapeshifter", "witch", "medium", "doctor", "cultist", "villager", "villager"],
        12: ["werewolf", "werewolf", "werewolf", "alpha_wolf", "shapeshifter", "witch", "medium", "priest", "dreamer", "lone_wolf", "villager", "villager"],
        16: ["werewolf", "werewolf", "werewolf", "werewolf", "alpha_wolf", "ancient_wolf", "witch", "medium", "oracle", "guardian", "cultist", "doppelganger", "villager", "villager", "villager", "villager"],
    }
}

# Custom mode presets - role pools for random selection
CUSTOM_PRESETS = {
    "mafia": {
        "chaos_mode": {
            "name_pl": "🌪️ Tryb Chaos",
            "name_en": "🌪️ Chaos Mode",
            "desc_pl": "Wszystkie role chaos + neutralne",
            "desc_en": "All chaos + neutral roles",
            "roles": ["mafioso", "mafioso", "don", "anarchist", "saboteur", "arsonist", "detective", "hacker", "citizen", "citizen", "jester", "executioner", "cultist", "paranoia_agent", "doppelganger"]
        },
        "detective_heavy": {
            "name_pl": "🔍 Detektywi",
            "name_en": "🔍 Detective Heavy",
            "desc_pl": "Dużo ról śledczych",
            "desc_en": "Many investigative roles",
            "roles": ["mafioso", "mafioso", "don", "shadow", "detective", "observer", "coroner", "tracker", "hacker", "witness", "reporter", "secret_collector", "citizen", "citizen", "citizen"]
        },
        "power_roles": {
            "name_pl": "⚡ Power Roles",
            "name_en": "⚡ Power Roles",
            "desc_pl": "Same role z mocami",
            "desc_en": "All power roles",
            "roles": ["don", "infiltrator", "forger", "briber", "detective", "doctor", "bodyguard", "judge", "hacker", "vigilante", "executioner", "arsonist", "cultist", "paranoia_agent"]
        },
        "balanced_chaos": {
            "name_pl": "⚖️ Zbalansowany Chaos",
            "name_en": "⚖️ Balanced Chaos",
            "desc_pl": "Mix wszystkich frakcji",
            "desc_en": "Mix of all factions",
            "roles": ["mafioso", "mafioso", "don", "saboteur", "detective", "doctor", "bodyguard", "citizen", "citizen", "jester", "executioner", "arsonist", "anarchist", "cultist", "doppelganger", "paranoia_agent"]
        }
    },
    "werewolf": {
        "chaos_mode": {
            "name_pl": "🌪️ Tryb Chaos",
            "name_en": "🌪️ Chaos Mode",
            "desc_pl": "Wszystkie role chaos + neutralne",
            "desc_en": "All chaos + neutral roles",
            "roles": ["werewolf", "werewolf", "alpha_wolf", "ancient_wolf", "witch", "seer", "medium", "villager", "villager", "fool", "lone_wolf", "cultist", "doppelganger", "vampire", "chaos_wolf"]
        },
        "mystic_mode": {
            "name_pl": "🔮 Tryb Mistyczny",
            "name_en": "🔮 Mystic Mode",
            "desc_pl": "Role magiczne i nadprzyrodzone",
            "desc_en": "Magic and supernatural roles",
            "roles": ["werewolf", "alpha_wolf", "shapeshifter", "ancient_wolf", "witch", "medium", "oracle", "seer", "priest", "dreamer", "villager", "villager", "cultist", "vampire"]
        },
        "hunter_pack": {
            "name_pl": "🏹 Łowcy",
            "name_en": "🏹 Hunter Pack",
            "desc_pl": "Dużo aktywnych ról",
            "desc_en": "Many active roles",
            "roles": ["werewolf", "werewolf", "alpha_wolf", "witch", "guardian", "tracker", "hunter", "vigilante", "bodyguard", "villager", "villager", "fool", "lone_wolf"]
        },
        "balanced_chaos": {
            "name_pl": "⚖️ Zbalansowany Chaos",
            "name_en": "⚖️ Balanced Chaos",
            "desc_pl": "Mix wszystkich frakcji",
            "desc_en": "Mix of all factions",
            "roles": ["werewolf", "werewolf", "alpha_wolf", "shapeshifter", "witch", "seer", "medium", "guardian", "villager", "villager", "fool", "lone_wolf", "cultist", "vampire", "doppelganger", "chaos_wolf"]
        }
    }
}

# ========================================
# TIME PRESETS
# ========================================

TIME_PRESETS = {
    "fast": {
        "name_pl": "⚡ Szybki",
        "name_en": "⚡ Fast",
        "day": 60,
        "night": 30,
        "vote": 30
    },
    "standard": {
        "name_pl": "⏱️ Standardowy",
        "name_en": "⏱️ Standard",
        "day": 180,
        "night": 90,
        "vote": 60
    },
    "hardcore": {
        "name_pl": "🔥 Hardcore",
        "name_en": "🔥 Hardcore",
        "day": 300,
        "night": 120,
        "vote": 90
    },
    "roleplay": {
        "name_pl": "🎭 Roleplay",
        "name_en": "🎭 Roleplay",
        "day": 600,
        "night": 180,
        "vote": 120
    }
}

# ========================================
# AUTO-BALANCE CHECKER
# ========================================

def check_role_balance(theme: str, mode: str, custom_roles: list, player_count: int, lang: str = "en") -> dict:
    """
    Check balance of custom role selection
    Returns: {
        "status": "balanced" | "risky" | "chaotic",
        "warnings": [],
        "suggestions": []
    }
    """
    result = {
        "status": "balanced",
        "warnings": [],
        "suggestions": [],
        "emoji": "✅"
    }
    
    if not custom_roles or mode != "custom":
        return result
    
    # Get role database
    db_key = f"{theme}_advanced" if mode in ["advanced", "custom"] else f"{theme}_normal"
    role_db = ROLES_DATABASE.get(db_key, {})
    
    # Count factions
    faction_counts = {}
    power_counts = {"investigate": 0, "protect": 0, "kill": 0}
    chaos_count = 0
    
    for role_id in custom_roles:
        for faction, roles in role_db.items():
            if role_id in roles:
                faction_counts[faction] = faction_counts.get(faction, 0) + 1
                
                role_info = roles[role_id]
                power = role_info.get("power")
                
                # Count specific powers
                if power == "investigate":
                    power_counts["investigate"] += 1
                elif power in ["protect", "guard"]:
                    power_counts["protect"] += 1
                elif power in ["kill", "kill_leader"]:
                    power_counts["kill"] += 1
                
                # Count chaos
                if faction == "CHAOS":
                    chaos_count += 1
                
                break
    
    # Determine evil and good factions
    evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
    good_faction = "TOWN" if theme == "mafia" else "VILLAGE"
    
    evil_count = faction_counts.get(evil_faction, 0)
    good_count = faction_counts.get(good_faction, 0)
    neutral_count = faction_counts.get("NEUTRAL", 0)
    
    # Check evil ratio (should be 20-35% of total)
    if player_count > 0:
        evil_ratio = evil_count / player_count
        
        if evil_ratio > 0.45:
            result["status"] = "risky"
            result["warnings"].append(
                f"⚠️ {'Za dużo złych ról' if lang == 'pl' else 'Too many evil roles'} ({evil_count}/{player_count} = {evil_ratio*100:.0f}%)"
            )
        elif evil_ratio < 0.15:
            result["status"] = "risky"
            result["warnings"].append(
                f"⚠️ {'Za mało złych ról' if lang == 'pl' else 'Too few evil roles'} ({evil_count}/{player_count} = {evil_ratio*100:.0f}%)"
            )
    
    # Check chaos ratio
    if chaos_count > player_count * 0.3:
        result["status"] = "chaotic"
        result["warnings"].append(
            f"🌀 {'Dużo ról chaos' if lang == 'pl' else 'Many chaos roles'} ({chaos_count}/{player_count})"
        )
    
    # Check for investigators
    if power_counts["investigate"] == 0 and good_count > 3:
        result["suggestions"].append(
            f"💡 {'Dodaj detektywa/jasnowidza' if lang == 'pl' else 'Add detective/seer'}"
        )
    
    # Check for healers
    if power_counts["protect"] == 0 and player_count >= 8:
        result["suggestions"].append(
            f"💡 {'Dodaj lekarza/ochroniarza' if lang == 'pl' else 'Add doctor/healer'}"
        )
    
    # Too many investigators
    if power_counts["investigate"] > 3:
        result["warnings"].append(
            f"⚠️ {'Za dużo śledczych' if lang == 'pl' else 'Too many investigators'} ({power_counts['investigate']})"
        )
    
    # Determine final status emoji
    if result["status"] == "chaotic":
        result["emoji"] = "🌀"
    elif result["status"] == "risky":
        result["emoji"] = "⚠️"
    elif result["suggestions"]:
        result["emoji"] = "💡"
    
    return result

# ========================================
# SETTINGS VIEW - Interactive Interface
# ========================================

class MafiaSettingsView(discord.ui.LayoutView):
    """Settings interface - NOT a modal, proper view with buttons/selects"""
    
    def __init__(self, cog, lobby_id, lobby_message=None):
        self.cog = cog
        self.lobby_id = lobby_id
        self.lobby_message = lobby_message  # Reference to main lobby message
        super().__init__(timeout=180.0)
        self._build_ui()
    
    async def on_timeout(self):
        """Clean up lobby when view times out"""
        if self.lobby_id in self.cog.active_lobbies:
            del self.cog.active_lobbies[self.lobby_id]
    
    async def _update_lobby_display(self):
        """Update the main lobby message after settings change"""
        if self.lobby_message:
            lobby_view = MafiaLobbyView(self.cog, self.lobby_id)
            try:
                await self.lobby_message.edit(view=lobby_view)
            except:
                pass  # Message might be deleted
    
    def _get_roles_info_for_mode(self, lobby: dict, lang: str) -> str:
        """Get roles information based on current mode"""
        theme = lobby["theme"]
        mode = lobby["mode"]
        player_count = len(lobby["players"])
        
        if mode == "custom":
            # Show custom selected roles
            if "custom_roles" not in lobby or not lobby["custom_roles"]:
                return f"*{f'{player_count} ' if player_count else ''}{'Niestandardowych ról nie wybrano' if lang == 'pl' else 'No custom roles selected'}*"
            
            random_mode = lobby.get("random_roles", False)
            evil_count = lobby.get("evil_count")
            
            db_key = f"{theme}_advanced"
            role_db = ROLES_DATABASE.get(db_key, {})
            roles_display = []
            
            for role_id in lobby["custom_roles"]:
                for faction, roles in role_db.items():
                    if role_id in roles:
                        role_data = roles[role_id]
                        role_name = role_data[f"name_{lang}"]
                        role_emoji = role_data["emoji"]
                        roles_display.append(f"{role_emoji} {role_name}")
                        break
            
            header = ""
            if random_mode:
                header = f"🎲 {'LOSOWE ' if lang == 'pl' else 'RANDOM '}{player_count}/{len(roles_display)}"
                if evil_count:
                    faction_name = "Mafii" if theme == "mafia" else "Wilkołaków"
                    faction_name_en = "Mafia" if theme == "mafia" else "Werewolves"
                    header += f" | {evil_count} {faction_name if lang == 'pl' else faction_name_en}"
                header += "\n"
            
            result = header + "\n".join([f"• {r}" for r in roles_display[:10]])
            if len(roles_display) > 10:
                result += f"\n*...+{len(roles_display)-10} {'więcej' if lang == 'pl' else 'more'}*"
            return result
        
        else:
            # Show preset roles
            preset_key = f"{theme}_{mode}"
            if player_count in PRESETS.get(preset_key, {}):
                preset = PRESETS[preset_key][player_count]
                db_key = f"{theme}_{mode}"
                role_db = ROLES_DATABASE.get(db_key, {})
                
                roles_display = []
                for role_id in preset:
                    for faction, roles in role_db.items():
                        if role_id in roles:
                            role_data = roles[role_id]
                            role_name = role_data[f"name_{lang}"]
                            role_emoji = role_data["emoji"]
                            roles_display.append(f"{role_emoji} {role_name}")
                            break
                
                return "\n".join([f"• {r}" for r in roles_display])
            else:
                return f"*{'Brak presetu dla' if lang == 'pl' else 'No preset for'} {player_count} {'graczy' if lang == 'pl' else 'players'}*"
    
    def _build_ui(self):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            return
        
        lang = lobby["language"]
        
        # Get roles info
        roles_info = self._get_roles_info_for_mode(lobby, lang)
        
        # Build content
        content = (
            f"# ⚙️ GAME SETTINGS\n\n"
            f"**Current Configuration:**\n"
            f"• Theme: **{lobby['theme'].title()}** {'🕴️' if lobby['theme'] == 'mafia' else '🐺'}\n"
            f"• Mode: **{lobby['mode'].title()}**\n"
            f"• Language: **{lobby['language'].upper()}** {'🇵🇱' if lobby['language'] == 'pl' else '🇬🇧'}\n"
            f"• Day: **{lobby['day_duration']}s** | Night: **{lobby['night_duration']}s** | Vote: **{lobby['vote_duration']}s**\n"
            f"• Voice Mode: **{'ON 🎤' if lobby['voice_mode'] else 'OFF 💬'}**\n\n"
            f"**{'Role' if lang == 'pl' else 'Roles'}:**\n{roles_info}\n\n"
            f"*Use buttons below to configure*"
        )
        
        # Theme buttons
        theme_mafia_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary if lobby['theme'] == 'mafia' else discord.ButtonStyle.secondary,
            emoji="🕴️",
            label="Mafia"
        )
        theme_werewolf_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary if lobby['theme'] == 'werewolf' else discord.ButtonStyle.secondary,
            emoji="🐺",
            label="Werewolf"
        )
        theme_mafia_btn.callback = lambda i: self.set_theme(i, "mafia")
        theme_werewolf_btn.callback = lambda i: self.set_theme(i, "werewolf")
        
        # Mode buttons
        mode_normal_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby['mode'] == 'normal' else discord.ButtonStyle.secondary,
            label="Normal"
        )
        mode_advanced_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby['mode'] == 'advanced' else discord.ButtonStyle.secondary,
            label="Advanced"
        )
        mode_custom_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby['mode'] == 'custom' else discord.ButtonStyle.secondary,
            label="Custom"
        )
        mode_normal_btn.callback = lambda i: self.set_mode(i, "normal")
        mode_advanced_btn.callback = lambda i: self.set_mode(i, "advanced")
        mode_custom_btn.callback = lambda i: self.set_mode(i, "custom")
        
        # Language buttons
        lang_en_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary if lobby['language'] == 'en' else discord.ButtonStyle.secondary,
            emoji="🇬🇧",
            label="English"
        )
        lang_pl_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary if lobby['language'] == 'pl' else discord.ButtonStyle.secondary,
            emoji="🇵🇱",
            label="Polski"
        )
        lang_en_btn.callback = lambda i: self.set_language(i, "en")
        lang_pl_btn.callback = lambda i: self.set_language(i, "pl")
        
        # Voice toggle
        voice_btn = discord.ui.Button(
            style=discord.ButtonStyle.success if lobby['voice_mode'] else discord.ButtonStyle.danger,
            emoji="🎤" if lobby['voice_mode'] else "💬",
            label=f"Voice: {'ON' if lobby['voice_mode'] else 'OFF'}"
        )
        voice_btn.callback = self.toggle_voice
        
        # Time preset select
        time_preset_select = discord.ui.Select(
            placeholder="⏱️ Time Presets",
            options=[
                discord.SelectOption(label=f"⚡ Fast (60/30/30s)", value="fast", description="Quick games"),
                discord.SelectOption(label=f"⏱️ Standard (180/90/60s)", value="standard", description="Default timing"),
                discord.SelectOption(label=f"🔥 Hardcore (300/120/90s)", value="hardcore", description="Long strategic games"),
                discord.SelectOption(label=f"🎭 Roleplay (600/180/120s)", value="roleplay", description="RP-heavy games"),
            ]
        )
        time_preset_select.callback = self.apply_time_preset
        
        # Back button
        back_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="◀️", label="Back to Lobby")
        back_btn.callback = self.back_to_lobby
        
        # Container
        color = 0x5865F2  # Blurple for settings
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="**Theme:**"),
            discord.ui.ActionRow(theme_mafia_btn, theme_werewolf_btn),
            discord.ui.TextDisplay(content="**Mode:**"),
            discord.ui.ActionRow(mode_normal_btn, mode_advanced_btn, mode_custom_btn),
            discord.ui.TextDisplay(content="**Language:**"),
            discord.ui.ActionRow(lang_en_btn, lang_pl_btn),
            discord.ui.ActionRow(voice_btn),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(time_preset_select),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(back_btn),
            accent_colour=discord.Colour(color)
        )
        
        self.add_item(self.container)
    
    async def set_theme(self, interaction: discord.Interaction, theme: str):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby or interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        lobby["theme"] = theme
        await self._update_lobby_display()
        
        # Update settings view
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def set_mode(self, interaction: discord.Interaction, mode: str):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby or interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        lobby["mode"] = mode
        
        # If custom mode, open role picker by editing current message
        if mode == "custom":
            role_picker = MafiaRolePickerView(self.cog, self.lobby_id, self.lobby_message)
            await interaction.response.edit_message(view=role_picker)
            return
        
        await self._update_lobby_display()
        
        # Update settings view
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def set_language(self, interaction: discord.Interaction, lang: str):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby or interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        lobby["language"] = lang
        await self._update_lobby_display()
        
        # Update settings view
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def toggle_voice(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby or interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        lobby["voice_mode"] = not lobby["voice_mode"]
        await self._update_lobby_display()
        
        # Update settings view
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def apply_time_preset(self, interaction: discord.Interaction):
        """Apply time preset to lobby"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby or interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can change settings!", ephemeral=True)
            return
        
        preset_id = interaction.data['values'][0]
        preset = TIME_PRESETS.get(preset_id)
        
        if preset:
            lobby["day_duration"] = preset["day"]
            lobby["night_duration"] = preset["night"]
            lobby["vote_duration"] = preset["vote"]
            
            await self._update_lobby_display()
            
            # Update settings view
            self.clear_items()
            self._build_ui()
            await interaction.response.edit_message(view=self)
    
    
    async def back_to_lobby(self, interaction: discord.Interaction):
        # Return to lobby view
        lobby_view = MafiaLobbyView(self.cog, self.lobby_id)
        await interaction.response.edit_message(view=lobby_view)

class CustomDurationModal(discord.ui.Modal, title="⏱️ Custom Durations"):
    day = discord.ui.TextInput(label="Day Duration (seconds)", placeholder="180", default="180", max_length=4)
    night = discord.ui.TextInput(label="Night Duration (seconds)", placeholder="90", default="90", max_length=4)
    vote = discord.ui.TextInput(label="Vote Duration (seconds)", placeholder="60", default="60", max_length=4)
    
    def __init__(self, cog, lobby_id, settings_view):
        super().__init__()
        self.cog = cog
        self.lobby_id = lobby_id
        self.settings_view = settings_view
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            lobby = self.cog.active_lobbies[self.lobby_id]
            lobby["day_duration"] = int(self.day.value)
            lobby["night_duration"] = int(self.night.value)
            lobby["vote_duration"] = int(self.vote.value)
            
            # Refresh settings view
            self.settings_view.clear_items()
            self.settings_view._build_ui()
            await interaction.response.edit_message(view=self.settings_view)
        except ValueError:
            await interaction.response.send_message("❌ Invalid numbers!", ephemeral=True)

# ========================================
# ROLE PICKER VIEW - For Custom Mode
# ========================================

class MafiaRolePickerView(discord.ui.LayoutView):
    """Interface for selecting custom roles with pagination"""
    
    def __init__(self, cog, lobby_id, lobby_message=None):
        self.cog = cog
        self.lobby_id = lobby_id
        self.lobby_message = lobby_message  # Reference to main lobby message
        self.page = 0
        self.roles_per_page = 15  # 3 rows x 5 buttons (reduced for new options)
        super().__init__(timeout=300.0)
        self._build_ui()
    
    async def on_timeout(self):
        """Clean up lobby when view times out"""
        if self.lobby_id in self.cog.active_lobbies:
            del self.cog.active_lobbies[self.lobby_id]
    
    def _get_all_roles(self):
        """Get all available roles for current theme"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            return []
        
        theme = lobby["theme"]
        lang = lobby["language"]
        db_key = f"{theme}_advanced"  # Use advanced for all roles
        role_db = ROLES_DATABASE.get(db_key, {})
        
        all_roles = []
        # Preserve faction order: Town/Village, Evil, Neutral, CHAOS
        faction_order = []
        if theme == "mafia":
            faction_order = ["TOWN", "MAFIA", "NEUTRAL", "CHAOS"]
        else:
            faction_order = ["VILLAGE", "WEREWOLVES", "NEUTRAL", "CHAOS"]
        
        for faction in faction_order:
            if faction in role_db:
                for role_id, role_data in role_db[faction].items():
                    all_roles.append({
                        "id": role_id,
                        "name": role_data[f"name_{lang}"],
                        "emoji": role_data["emoji"],
                        "faction": faction
                    })
        
        return all_roles
    
    def _build_ui(self, preview_message: str = None, preview_role: dict = None):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            return
        
        player_count = len(lobby["players"])
        selected_roles = lobby.get("custom_roles", [])
        lang = lobby["language"]
        
        # Get all roles
        all_roles = self._get_all_roles()
        total_pages = (len(all_roles) + self.roles_per_page - 1) // self.roles_per_page
        
        # Get current page roles
        start_idx = self.page * self.roles_per_page
        end_idx = start_idx + self.roles_per_page
        page_roles = all_roles[start_idx:end_idx]
        
        # Build role database for name lookup
        theme = lobby["theme"]
        db_key = f"{theme}_advanced"
        role_db = ROLES_DATABASE.get(db_key, {})
        
        # Build selected roles display
        roles_display = []
        for role_id in selected_roles:
            for faction, roles in role_db.items():
                if role_id in roles:
                    role_data = roles[role_id]
                    role_name = role_data[f"name_{lang}"]
                    role_emoji = role_data["emoji"]
                    roles_display.append(f"{role_emoji} {role_name}")
                    break
        
        # Build content
        random_mode = lobby.get("random_roles", False)
        evil_count = lobby.get("evil_count", None)
        
        content = (
            f"# 🎯 {'NIESTANDARDOWY WYBÓR RÓL' if lang == 'pl' else 'CUSTOM ROLE SELECTION'}\n\n"
            f"**{'Graczy' if lang == 'pl' else 'Players'}:** {player_count}\n"
            f"**{'Wybrane role' if lang == 'pl' else 'Selected Roles'}:** {len(selected_roles)}"
        )
        
        if random_mode:
            content += f" {'🎲 LOSOWE' if lang == 'pl' else ' 🎲 RANDOM'}"
        else:
            content += f"/{player_count}"
        
        if evil_count is not None:
            faction_name = "Mafii" if theme == "mafia" else "Wilkołaków"
            faction_name_en = "Mafia" if theme == "mafia" else "Werewolves"
            content += f"\n**{faction_name if lang == 'pl' else faction_name_en}:** {evil_count}"
        
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
        
        if roles_display:
            roles_text = "\n".join([f"• {role}" for role in roles_display])
            content += f"\n**{'Obecny wybór' if lang == 'pl' else 'Current Selection'}:**\n{roles_text}\n"
        
        content += f"\n**{'Strona' if lang == 'pl' else 'Page'} {self.page + 1}/{total_pages}**"
        
        # Create role buttons (max 5 per row, 4 rows)
        items = []
        
        # Add preview message if provided (role description before adding)
        if preview_message:
            items.append(discord.ui.TextDisplay(content=preview_message))
            items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
            
            # Add confirmation buttons
            add_btn = discord.ui.Button(
                style=discord.ButtonStyle.success,
                emoji="✅",
                label="Dodaj" if lang == "pl" else "Add"
            )
            cancel_btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                emoji="❌",
                label="Anuluj" if lang == "pl" else "Cancel"
            )
            add_btn.callback = lambda i: self.confirm_add_role(i, preview_role)
            cancel_btn.callback = self.cancel_preview
            
            items.append(discord.ui.ActionRow(add_btn, cancel_btn))
            
            # When showing preview, skip role buttons to avoid hitting 40 element limit
            # Container
            theme = lobby["theme"]
            accent = discord.Colour(0xDC143C) if theme == "mafia" else discord.Colour(0x4169E1)
            self.container = discord.ui.Container(*items, accent_colour=accent)
            self.add_item(self.container)
            return
        
        items.extend([
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ])
        
        # Add role buttons in rows of 5
        for i in range(0, len(page_roles), 5):
            row_roles = page_roles[i:i+5]
            row_buttons = []
            
            for role in row_roles:
                # Check if already selected
                is_selected = role["id"] in selected_roles
                
                # If selected, use secondary style with checkmark
                if is_selected:
                    style = discord.ButtonStyle.secondary
                    label = f"✓ {role['name'][:75]}"  # Shorter to fit checkmark
                else:
                    # Color by faction
                    if role["faction"] in ["TOWN", "VILLAGE"]:
                        style = discord.ButtonStyle.success  # Green
                    elif role["faction"] in ["MAFIA", "WEREWOLVES"]:
                        style = discord.ButtonStyle.danger  # Red
                    elif role["faction"] == "NEUTRAL":
                        style = discord.ButtonStyle.secondary  # Gray
                    else:  # CHAOS
                        style = discord.ButtonStyle.primary  # Blue
                    label = role["name"][:80]
                
                btn = discord.ui.Button(
                    style=style,
                    emoji=role["emoji"],
                    label=label,
                    custom_id=f"role_{role['id']}"
                )
                
                # Different callback based on selected state
                if is_selected:
                    btn.callback = lambda i, r=role: self.remove_role(i, r)
                else:
                    btn.callback = lambda i, r=role: self.show_role_preview(i, r)
                
                row_buttons.append(btn)
            
            items.append(discord.ui.ActionRow(*row_buttons))
        
        # Navigation buttons
        prev_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="◀️",
            label="Poprzednia" if lang == "pl" else "Previous",
            disabled=(self.page == 0)
        )
        next_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="▶️",
            label="Następna" if lang == "pl" else "Next",
            disabled=(self.page >= total_pages - 1)
        )
        prev_btn.callback = self.prev_page
        next_btn.callback = self.next_page
        
        items.extend([
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(prev_btn, next_btn),
        ])
        
        # Options buttons - Random toggle, Evil count, Presets
        random_btn = discord.ui.Button(
            style=discord.ButtonStyle.primary if lobby.get("random_roles") else discord.ButtonStyle.secondary,
            emoji="🎲",
            label=f"{'Losowe' if lang == 'pl' else 'Random'}: {'ON' if lobby.get('random_roles') else 'OFF'}"
        )
        evil_select = discord.ui.Select(
            placeholder=f"{'🔴 Liczba Mafii/Wilkołaków' if lang == 'pl' else '🔴 Evil Count'}",
            options=[
                discord.SelectOption(label=f"Auto ({('25%' if player_count <= 8 else '30%')})", value="auto"),
                discord.SelectOption(label="1", value="1"),
                discord.SelectOption(label="2", value="2"),
                discord.SelectOption(label="3", value="3"),
                discord.SelectOption(label="4", value="4"),
                discord.SelectOption(label="5", value="5"),
            ]
        )
        preset_select = discord.ui.Select(
            placeholder=f"{'📋 Załaduj Preset' if lang == 'pl' else '📋 Load Preset'}",
            options=self._get_preset_options(theme, lang, player_count)
        )
        
        random_btn.callback = self.toggle_random
        evil_select.callback = self.set_evil_count
        preset_select.callback = self.load_preset
        
        items.extend([
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(random_btn),
            discord.ui.ActionRow(evil_select),
            discord.ui.ActionRow(preset_select),
        ])
        
        # Action buttons
        clear_btn = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            label="Wyczyść" if lang == "pl" else "Clear All"
        )
        done_btn = discord.ui.Button(
            style=discord.ButtonStyle.success,
            emoji="✅",
            label="Gotowe" if lang == "pl" else "Done"
        )
        back_btn = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji="◀️",
            label="Powrót" if lang == "pl" else "Back"
        )
        
        clear_btn.callback = self.clear_roles
        done_btn.callback = self.finish_selection
        back_btn.callback = self.back_to_settings
        
        items.append(discord.ui.ActionRow(clear_btn, done_btn, back_btn))
        
        # Container
        theme = lobby["theme"]
        accent = discord.Colour(0xDC143C) if theme == "mafia" else discord.Colour(0x4169E1)
        self.container = discord.ui.Container(*items, accent_colour=accent)
        self.add_item(self.container)
    
    async def prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        all_roles = self._get_all_roles()
        total_pages = (len(all_roles) + self.roles_per_page - 1) // self.roles_per_page
        self.page = min(total_pages - 1, self.page + 1)
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    def _get_preset_options(self, theme: str, lang: str, player_count: int):
        """Get preset options for select menu"""
        options = []
        
        # Add dynamic presets for normal/advanced modes
        normal_preset_key = f"{theme}_normal"
        advanced_preset_key = f"{theme}_advanced"
        
        if player_count in PRESETS.get(normal_preset_key, {}):
            label = f"📋 {'Klasyczny' if lang == 'pl' else 'Classic'} ({player_count})"
            desc = f"{'Wczytaj role z trybu klasycznego' if lang == 'pl' else 'Load roles from classic mode'}"
            options.append(discord.SelectOption(
                label=label[:100],
                value=f"dynamic_normal",
                description=desc[:100]
            ))
        
        if player_count in PRESETS.get(advanced_preset_key, {}):
            label = f"⚡ {'Rozbudowany' if lang == 'pl' else 'Advanced'} ({player_count})"
            desc = f"{'Wczytaj role z trybu rozbudowanego' if lang == 'pl' else 'Load roles from advanced mode'}"
            options.append(discord.SelectOption(
                label=label[:100],
                value=f"dynamic_advanced",
                description=desc[:100]
            ))
        
        # Separator
        if options:
            options.append(discord.SelectOption(
                label="─────────────",
                value="separator",
                description="Custom presets below"
            ))
        
        # Add custom presets
        presets = CUSTOM_PRESETS.get(theme, {})
        
        for preset_id, preset_data in presets.items():
            name = preset_data[f"name_{lang}"]
            desc = preset_data[f"desc_{lang}"]
            options.append(discord.SelectOption(
                label=name[:100],
                value=preset_id,
                description=desc[:100]
            ))
        
        return options if options else [discord.SelectOption(label="None", value="none")]
    
    async def toggle_random(self, interaction: discord.Interaction):
        """Toggle random role selection"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        lobby["random_roles"] = not lobby.get("random_roles", False)
        
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def set_evil_count(self, interaction: discord.Interaction):
        """Set evil faction count"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        value = interaction.data['values'][0]
        
        if value == "auto":
            lobby["evil_count"] = None  # Auto-calculate
        else:
            lobby["evil_count"] = int(value)
        
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def load_preset(self, interaction: discord.Interaction):
        """Load preset role pool"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        preset_id = interaction.data['values'][0]
        theme = lobby["theme"]
        player_count = len(lobby["players"])
        lang = lobby["language"]
        
        if preset_id == "none" or preset_id == "separator":
            await interaction.response.defer()
            return
        
        # Handle dynamic presets (normal/advanced mode)
        if preset_id.startswith("dynamic_"):
            mode = preset_id.replace("dynamic_", "")  # "normal" or "advanced"
            preset_key = f"{theme}_{mode}"
            
            if player_count in PRESETS.get(preset_key, {}):
                lobby["custom_roles"] = PRESETS[preset_key][player_count].copy()
                lobby["random_roles"] = False  # Exact mode for normal/advanced presets
                
                msg = f"✅ {'Załadowano' if lang == 'pl' else 'Loaded'}: {mode.title()} ({player_count} {'graczy' if lang == 'pl' else 'players'})"
            else:
                msg = f"❌ {'Brak presetu dla' if lang == 'pl' else 'No preset for'} {player_count} {'graczy' if lang == 'pl' else 'players'}"
                await interaction.response.send_message(msg, ephemeral=True)
                return
        else:
            # Handle custom presets
            presets = CUSTOM_PRESETS.get(theme, {})
            if preset_id in presets:
                preset = presets[preset_id]
                lobby["custom_roles"] = preset["roles"].copy()
                lobby["random_roles"] = True  # Enable random mode for custom presets
                
                msg = f"✅ {'Załadowano preset' if lang == 'pl' else 'Loaded preset'}: {preset[f'name_{lang}']}"
            else:
                await interaction.response.defer()
                return
        
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def show_role_preview(self, interaction: discord.Interaction, role_data: dict):
        """Show role description with Add/Cancel buttons"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        player_count = len(lobby["players"])
        lang = lobby["language"]
        theme = lobby["theme"]
        random_mode = lobby.get("random_roles", False)
        
        if "custom_roles" not in lobby:
            lobby["custom_roles"] = []
        
        role_id = role_data["id"]
        
        # Only check limit in exact mode (not random mode)
        if not random_mode and len(lobby["custom_roles"]) >= player_count:
            msg = f"❌ Masz już {player_count} ról!" if lang == "pl" else f"❌ Already have {player_count} roles!"
            await interaction.response.send_message(msg, ephemeral=True)
            return
        
        # Get full role info from database
        db_key = f"{theme}_advanced"
        role_db = ROLES_DATABASE.get(db_key, {})
        
        # Find the role in database to get description
        role_info = None
        for faction, roles in role_db.items():
            if role_id in roles:
                role_info = roles[role_id]
                break
        
        # Build description message
        role_name = role_data["name"]
        role_emoji = role_data["emoji"]
        faction_name = role_data["faction"]
        power = role_info.get("power") if role_info else None
        
        # Create description based on power
        description = self._get_role_description(role_id, power, lang)
        
        # Faction name translation
        faction_display = {
            "TOWN": "🟢 Miasto" if lang == "pl" else "🟢 Town",
            "VILLAGE": "🟢 Wioska" if lang == "pl" else "🟢 Village",
            "MAFIA": "🔴 Mafia" if lang == "pl" else "🔴 Mafia",
            "WEREWOLVES": "🔴 Wilkołaki" if lang == "pl" else "🔴 Werewolves",
            "NEUTRAL": "⚪ Neutralny" if lang == "pl" else "⚪ Neutral",
            "CHAOS": "🔵 Chaos" if lang == "pl" else "🔵 Chaos"
        }.get(faction_name, faction_name)
        
        # Build preview message with description
        preview_msg = (
            f"# {role_emoji} {role_name}\n\n"
            f"**{'Frakcja' if lang == 'pl' else 'Faction'}:** {faction_display}\n\n"
            f"**{'Opis' if lang == 'pl' else 'Description'}:**\n{description}\n\n"
            f"*{'Dodać tę rolę?' if lang == 'pl' else 'Add this role?'}*"
        )
        
        # Rebuild UI with preview and Add/Cancel buttons
        self.clear_items()
        self._build_ui(preview_message=preview_msg, preview_role=role_data)
        
        # Edit the current message
        await interaction.response.edit_message(view=self)
    
    async def confirm_add_role(self, interaction: discord.Interaction, role_data: dict):
        """Actually add the role after confirmation"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        lang = lobby["language"]
        
        if "custom_roles" not in lobby:
            lobby["custom_roles"] = []
        
        role_id = role_data["id"]
        lobby["custom_roles"].append(role_id)
        
        # Rebuild UI normally (without preview)
        self.clear_items()
        self._build_ui()
        
        await interaction.response.edit_message(view=self)
    
    async def cancel_preview(self, interaction: discord.Interaction):
        """Cancel role preview and return to normal view"""
        # Rebuild UI normally (without preview)
        self.clear_items()
        self._build_ui()
        
        await interaction.response.edit_message(view=self)
    
    async def remove_role(self, interaction: discord.Interaction, role_data: dict):
        """Remove a selected role"""
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        role_id = role_data["id"]
        
        if "custom_roles" in lobby and role_id in lobby["custom_roles"]:
            lobby["custom_roles"].remove(role_id)
        
        # Rebuild UI
        self.clear_items()
        self._build_ui()
        
        await interaction.response.edit_message(view=self)
    
    def _get_role_description(self, role_id: str, power: str, lang: str) -> str:
        """Generate role description based on power type"""
        descriptions = {
            "pl": {
                None: "Zwykły obywatel bez specjalnych mocy.",
                "investigate": "Co noc może zbadać gracza i dowiedzieć się czy jest zły.",
                "protect": "Co noc może ochronić gracza przed śmiercią.",
                "guard": "Może ochronić gracza, ale zginie jeśli obroni przed zabójcą.",
                "track": "Może śledzić gracza i zobaczyć kogo odwiedził.",
                "reveal_dead": "Może ujawnić jedną rolę zmarłego gracza.",
                "kill": "Co noc może zabić wybranego gracza.",
                "kill_leader": "Zabija graczy i jest odporny na wykrycie.",
                "stealth": "Niewidzialny dla detektywów.",
                "lynch_win": "Wygrywa jeśli zostanie zlinczowany.",
                "contract": "Musi zabić określony cel aby wygrać.",
                "stats": "Otrzymuje statystyki o grze.",
                "hints": "Otrzymuje wskazówki o rolach.",
                "visits": "Widzi kto kogo odwiedził.",
                "death_cause": "Dowiaduje się jak zmarł gracz.",
                "reveal": "Może ujawnić rolę żywego gracza.",
                "cancel_vote": "Może anulować jeden głos w linczowaniu.",
                "delay": "Może opóźnić głosowanie.",
                "logs": "Widzi wszystkie akcje nocne.",
                "secure": "Chroni dowody przed sabotażem.",
                "suspicious": "Może oznaczyć gracza jako podejrzanego.",
                "double_vote": "Głos liczy się podwójnie.",
                "no_vote_strong": "Nie może głosować ale jest silniejszy.",
                "connect": "Może połączyć dwóch graczy.",
                "fake_reports": "Może podrabiać raporty śledztw.",
                "steal": "Może ukraść moc innemu graczowi.",
                "block": "Blokuje moc innego gracza.",
                "convert": "Może przekonwertować gracza do mafii.",
                "buy_votes": "Może kupić dodatkowe głosy.",
                "unstoppable": "Zabójstwo nie może być zablokowane.",
                "lower_sus": "Obniża podejrzenia wobec mafii.",
                "fake_town": "Wygląda jak town dla detektywów.",
                "top3": "Wygrywa jeśli przeżyje do ostatnich 3.",
                "chaos": "Wygrywa gdy gra jest chaotyczna.",
                "survive_x": "Musi przeżyć określoną liczbę dni.",
                "info": "Zbiera informacje o graczach.",
                "buff_weak": "Wzmacnia słabszą frakcję.",
                "force": "Może zmusić gracza do akcji.",
                "chaos_win": "Wygrywa gdy jest maksimum chaosu.",
                "reverse_vote": "Odwraca wyniki głosowania.",
                "break_night": "Może zepsuć fazę nocną.",
                "random": "Losowa moc każdej nocy.",
                "grow": "Moc rośnie z czasem.",
                "anonymous_dm": "Wysyła anonimowe wiadomości.",
                "50_lie": "50% szans na kłamliwe informacje.",
                "swap_votes": "Może zamienić głosy graczy.",
                "revenge_kill": "Może zabić po śmierci.",
                "potions": "Ma miksturę życia i śmierci.",
                "dead_chat": "Może rozmawiać z zmarłymi.",
                "block_curse": "Blokuje przekleństwa.",
                "armor": "Tworzy zbroję dla graczy.",
                "influence": "Wpływa na głosowania.",
                "old_actions": "Widzi historię akcji.",
                "future": "Otrzymuje wizje przyszłości.",
                "alpha_power": "Silniejszy wilkołak, prowadzi stado.",
                "curse": "Może przekląć gracza.",
                "recruit_wolf": "Może rekrutować do stada.",
                "fake_village": "Wygląda jak wieśniak.",
                "win_lynch": "Wygrywa gdy zostanie zlinczowany.",
                "survive": "Musi tylko przeżyć.",
                "cleanse": "Oczyszcza z przekleństw.",
                "sacrifice": "Może się poświęcić za innego.",
                "summon_role": "Przywołuje dodatkową rolę.",
                "win_death": "Wygrywa gdy zginie.",
                "infect": "Zaraża graczy plagą.",
                "solo": "Samotny wilk, działa solo.",
                "copy_role": "Kopiuje rolę innego gracza.",
                "summon": "Przywołuje istoty z pustki.",
                "steal_power": "Kradnie moc zmarłym.",
                "50_powerup": "50% szans na podwójną moc.",
                "random_effects": "Losowe efekty na grę.",
                "riddles": "Wysyła zagadki graczom.",
                "remove_curse": "Usuwa przekleństwa.",
                "dreams": "Otrzymuje sny o przyszłości.",
                "disguise": "Może się przebrać za innego.",
                "fake_villager": "Wygląda jak wieśniak dla wszystkich.",
                "vote_influence": "Wpływa na głosowanie innych.",
                "unpredictable": "Nieprzewidywalne zachowanie.",
                "event": "Może wywołać losowe wydarzenie.",
                "recruit": "Może rekrutować do kultu.",
                "copy": "Kopiuje zdolność innej roli.",
                "revenge": "Mści się na zabójcy.",
                "control": "Kontroluje dzikie bestie.",
                "manipulate_turns": "Manipuluje kolejnością tur.",
                "mix_reports": "Miesza raporty śledztw.",
                "random_visions": "Losowe wizje (prawda/fałsz).",
                "decay": "Powoduje rozpad i chaos.",
                "conflicts": "Tworzy konflikty między graczami.",
                "catastrophe": "Może wywołać katastrofę.",
            },
            "en": {
                None: "Regular citizen with no special powers.",
                "investigate": "Can investigate a player each night to learn if they are evil.",
                "protect": "Can protect a player from death each night.",
                "guard": "Can protect a player but dies if defending against killer.",
                "track": "Can track a player and see who they visited.",
                "reveal_dead": "Can reveal one dead player's role.",
                "kill": "Can kill a chosen player each night.",
                "kill_leader": "Kills players and is immune to detection.",
                "stealth": "Invisible to detectives.",
                "lynch_win": "Wins if lynched.",
                "contract": "Must kill specific target to win.",
                "stats": "Receives game statistics.",
                "hints": "Receives hints about roles.",
                "visits": "Sees who visited whom.",
                "death_cause": "Learns how a player died.",
                "reveal": "Can reveal a living player's role.",
                "cancel_vote": "Can cancel one lynch vote.",
                "delay": "Can delay voting.",
                "logs": "Sees all night actions.",
                "secure": "Protects evidence from sabotage.",
                "suspicious": "Can mark a player as suspicious.",
                "double_vote": "Vote counts double.",
                "no_vote_strong": "Cannot vote but is stronger.",
                "connect": "Can connect two players.",
                "fake_reports": "Can fake investigation reports.",
                "steal": "Can steal another player's power.",
                "block": "Blocks another player's power.",
                "convert": "Can convert a player to mafia.",
                "buy_votes": "Can buy additional votes.",
                "unstoppable": "Kill cannot be blocked.",
                "lower_sus": "Lowers suspicion towards mafia.",
                "fake_town": "Appears as town to detectives.",
                "top3": "Wins if survives to final 3.",
                "chaos": "Wins when game is chaotic.",
                "survive_x": "Must survive X number of days.",
                "info": "Collects information about players.",
                "buff_weak": "Buffs the weaker faction.",
                "force": "Can force a player to take action.",
                "chaos_win": "Wins when maximum chaos.",
                "reverse_vote": "Reverses voting results.",
                "break_night": "Can break night phase.",
                "random": "Random power each night.",
                "grow": "Power grows over time.",
                "anonymous_dm": "Sends anonymous messages.",
                "50_lie": "50% chance for false information.",
                "swap_votes": "Can swap player votes.",
                "revenge_kill": "Can kill after death.",
                "potions": "Has life and death potions.",
                "dead_chat": "Can talk to the dead.",
                "block_curse": "Blocks curses.",
                "armor": "Creates armor for players.",
                "influence": "Influences votes.",
                "old_actions": "Sees action history.",
                "future": "Receives future visions.",
                "alpha_power": "Stronger werewolf, leads pack.",
                "curse": "Can curse a player.",
                "recruit_wolf": "Can recruit to pack.",
                "fake_village": "Appears as villager.",
                "win_lynch": "Wins if lynched.",
                "survive": "Must only survive.",
                "cleanse": "Cleanses curses.",
                "sacrifice": "Can sacrifice for another.",
                "summon_role": "Summons additional role.",
                "win_death": "Wins upon death.",
                "infect": "Infects players with plague.",
                "solo": "Lone wolf, acts solo.",
                "copy_role": "Copies another player's role.",
                "summon": "Summons void creatures.",
                "steal_power": "Steals power from dead.",
                "50_powerup": "50% chance for double power.",
                "random_effects": "Random effects on game.",
                "riddles": "Sends riddles to players.",
                "remove_curse": "Removes curses.",
                "dreams": "Receives dreams about future.",
                "disguise": "Can disguise as another.",
                "fake_villager": "Appears as villager to all.",
                "vote_influence": "Influences other votes.",
                "unpredictable": "Unpredictable behavior.",
                "event": "Can trigger random event.",
                "recruit": "Can recruit to cult.",
                "copy": "Copies another role's ability.",
                "revenge": "Takes revenge on killer.",
                "control": "Controls wild beasts.",
                "manipulate_turns": "Manipulates turn order.",
                "mix_reports": "Mixes investigation reports.",
                "random_visions": "Random visions (true/false).",
                "decay": "Causes decay and chaos.",
                "conflicts": "Creates conflicts between players.",
                "catastrophe": "Can trigger catastrophe.",
            }
        }
        
        return descriptions[lang].get(power, "Specjalna rola." if lang == "pl" else "Special role.")
    
    async def clear_roles(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        lobby["custom_roles"] = []
        
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def finish_selection(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        player_count = len(lobby["players"])
        role_count = len(lobby.get("custom_roles", []))
        lang = lobby["language"]
        random_mode = lobby.get("random_roles", False)
        
        print(f"[DEBUG] finish_selection: random_mode={random_mode}, role_count={role_count}, player_count={player_count}")
        
        # Validation based on mode
        if random_mode:
            # In random mode, need at least player_count roles
            if role_count < player_count:
                msg = (f"❌ Potrzebujesz co najmniej {player_count} ról dla trybu losowego! (Obecnie: {role_count})" if lang == "pl" 
                       else f"❌ Need at least {player_count} roles for random mode! (Currently: {role_count})")
                await interaction.response.send_message(msg, ephemeral=True)
                return
        else:
            # In exact mode, need exactly player_count roles
            if role_count != player_count:
                msg = (f"❌ Potrzebujesz dokładnie {player_count} ról! (Obecnie: {role_count})" if lang == "pl" 
                       else f"❌ Need exactly {player_count} roles! (Currently: {role_count})")
                await interaction.response.send_message(msg, ephemeral=True)
                return
        
        # Update main lobby display
        if self.lobby_message:
            lobby_view = MafiaLobbyView(self.cog, self.lobby_id)
            try:
                await self.lobby_message.edit(view=lobby_view)
            except:
                pass
        
        # Return to lobby view
        lobby_view = MafiaLobbyView(self.cog, self.lobby_id)
        await interaction.response.edit_message(view=lobby_view)
    
    async def back_to_settings(self, interaction: discord.Interaction):
        # Return to settings view
        settings_view = MafiaSettingsView(self.cog, self.lobby_id, self.lobby_message)
        await interaction.response.edit_message(view=settings_view)

# ========================================
# MAIN LOBBY VIEW
# ========================================

class MafiaLobbyView(discord.ui.LayoutView):
    """Main lobby interface with Container UI"""
    
    def __init__(self, cog, lobby_id):
        self.cog = cog
        self.lobby_id = lobby_id
        super().__init__(timeout=300.0)
        self._build_ui()
    
    async def on_timeout(self):
        """Clean up lobby when view times out"""
        if self.lobby_id in self.cog.active_lobbies:
            del self.cog.active_lobbies[self.lobby_id]
    
    def _get_roles_info_for_mode(self, lobby: dict, lang: str) -> str:
        """Get roles information based on current mode"""
        theme = lobby["theme"]
        mode = lobby["mode"]
        player_count = len(lobby["players"])
        
        if mode == "custom":
            # Show custom selected roles
            if "custom_roles" not in lobby or not lobby["custom_roles"]:
                return f"*{f'{player_count} ' if player_count else ''}{'Niestandardowych ról nie wybrano' if lang == 'pl' else 'No custom roles selected'}*"
            
            random_mode = lobby.get("random_roles", False)
            evil_count = lobby.get("evil_count")
            
            db_key = f"{theme}_advanced"
            role_db = ROLES_DATABASE.get(db_key, {})
            roles_display = []
            
            for role_id in lobby["custom_roles"]:
                for faction, roles in role_db.items():
                    if role_id in roles:
                        role_data = roles[role_id]
                        role_name = role_data[f"name_{lang}"]
                        role_emoji = role_data["emoji"]
                        roles_display.append(f"{role_emoji} {role_name}")
                        break
            
            header = ""
            if random_mode:
                header = f"🎲 {'LOSOWE ' if lang == 'pl' else 'RANDOM '}{player_count}/{len(roles_display)}"
                if evil_count:
                    faction_name = "Mafii" if theme == "mafia" else "Wilkołaków"
                    faction_name_en = "Mafia" if theme == "mafia" else "Werewolves"
                    header += f" | {evil_count} {faction_name if lang == 'pl' else faction_name_en}"
                header += "\n"
            
            result = header + "\n".join([f"• {r}" for r in roles_display[:10]])
            if len(roles_display) > 10:
                result += f"\n*...+{len(roles_display)-10} {'więcej' if lang == 'pl' else 'more'}*"
            return result
        
        else:
            # Show preset roles
            preset_key = f"{theme}_{mode}"
            if player_count in PRESETS.get(preset_key, {}):
                preset = PRESETS[preset_key][player_count]
                db_key = f"{theme}_{mode}"
                role_db = ROLES_DATABASE.get(db_key, {})
                
                roles_display = []
                for role_id in preset:
                    for faction, roles in role_db.items():
                        if role_id in roles:
                            role_data = roles[role_id]
                            role_name = role_data[f"name_{lang}"]
                            role_emoji = role_data["emoji"]
                            roles_display.append(f"{role_emoji} {role_name}")
                            break
                
                return "\n".join([f"• {r}" for r in roles_display])
            else:
                return f"*{'Brak presetu dla' if lang == 'pl' else 'No preset for'} {player_count} {'graczy' if lang == 'pl' else 'players'}*"
    
    def _build_ui(self):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            return
        
        lang = lobby["language"]
        theme_emoji = "🕴️" if lobby["theme"] == "mafia" else "🐺"
        theme_name = "MAFIA" if lobby["theme"] == "mafia" else "WEREWOLF"
        
        # Translate strings
        if lang == "pl":
            title = f"{theme_emoji} LOBBY {theme_name}"
            host_label = "Host"
            players_label = "Gracze"
            settings_label = "Ustawienia"
            theme_label = "Motyw"
            mode_label = "Tryb"
            language_label = "Język"
            day_label = "Dzień"
            night_label = "Noc"
            vote_label = "Głosowanie"
            voice_label = "Tryb głosowy"
            how_to_play_label = "📋 Jak grać"
        else:
            title = f"{theme_emoji} {theme_name} LOBBY"
            host_label = "Host"
            players_label = "Players"
            settings_label = "Settings"
            theme_label = "Theme"
            mode_label = "Mode"
            language_label = "Language"
            day_label = "Day"
            night_label = "Night"
            vote_label = "Vote"
            voice_label = "Voice Mode"
            how_to_play_label = "📋 How to Play"
        
        player_list = "\n".join([f"• <@{pid}>" for pid in lobby["players"]])
        
        # Build settings display
        settings_text = []
        settings_text.append(f"• {theme_label}: **{lobby['theme'].title()}** {theme_emoji}")
        settings_text.append(f"• {mode_label}: **{lobby['mode'].title()}**")
        settings_text.append(f"• {language_label}: **{lang.upper()}** {'🇵🇱' if lang == 'pl' else '🇬🇧'}")
        settings_text.append(f"• {day_label}: **{lobby['day_duration']}s** | {night_label}: **{lobby['night_duration']}s** | {vote_label}: **{lobby['vote_duration']}s**")
        settings_text.append(f"• {voice_label}: **{'ON 🎤' if lobby['voice_mode'] else 'OFF 💬'}**")
        
        # Show roles for current mode
        roles_info = self._get_roles_info_for_mode(lobby, lang)
        if roles_info:
            settings_text.append(f"\n**{'Role' if lang == 'pl' else 'Roles'}:**")
            settings_text.append(roles_info)
        
        # How to play
        if lobby["theme"] == "mafia":
            if lang == "pl":
                how_to_play = ("• Mafia zabija w nocy\n• Miasto śledzi i chroni\n• Głosuj by wyeliminować podejrzanych\n• Miasto wygrywa: Wyeliminuj całą mafię\n• Mafia wygrywa: Dorównaj/przewyższ miasto")
            else:
                how_to_play = ("• Mafia kills at night\n• Town investigates and protects\n• Vote to eliminate suspects\n• Town wins: Eliminate all mafia\n• Mafia wins: Equal/outnumber town")
        else:
            if lang == "pl":
                how_to_play = ("• Wilkołaki polują w nocy\n• Wioska używa mocy\n• Głosuj by wyeliminować podejrzanych\n• Wioska wygrywa: Wyeliminuj wszystkie wilkołaki\n• Wilkołaki wygrywają: Dorównaj/przewyższ wioskę")
            else:
                how_to_play = ("• Werewolves hunt at night\n• Village uses special powers\n• Vote to eliminate suspects\n• Village wins: Eliminate all werewolves\n• Werewolves win: Equal/outnumber village")
        
        # Build main content
        content = (
            f"# {title}\n\n"
            f"**{host_label}:** <@{lobby['host']}>\n\n"
            f"**{players_label} ({len(lobby['players'])}/16):**\n{player_list}\n\n"
            f"**{settings_label}:**\n" + "\n".join(settings_text) + f"\n\n"
            f"**{how_to_play_label}:**\n{how_to_play}"
        )
        
        # Create buttons
        if lang == "pl":
            join_btn = discord.ui.Button(style=discord.ButtonStyle.success, emoji="✅", label="Dołącz")
            leave_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="🚪", label="Wyjdź")
            settings_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⚙️", label="Ustawienia")
            start_btn = discord.ui.Button(style=discord.ButtonStyle.danger, emoji="▶️", label="Rozpocznij")
            cancel_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="❌", label="Anuluj")
        else:
            join_btn = discord.ui.Button(style=discord.ButtonStyle.success, emoji="✅", label="Join")
            leave_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="🚪", label="Leave")
            settings_btn = discord.ui.Button(style=discord.ButtonStyle.primary, emoji="⚙️", label="Settings")
            start_btn = discord.ui.Button(style=discord.ButtonStyle.danger, emoji="▶️", label="Start")
            cancel_btn = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="❌", label="Cancel")
        
        # Assign callbacks
        join_btn.callback = self.join_callback
        leave_btn.callback = self.leave_callback
        settings_btn.callback = self.settings_callback
        start_btn.callback = self.start_callback
        cancel_btn.callback = self.cancel_callback
        
        # Container
        color = 0x8B0000 if lobby["theme"] == "mafia" else 0x1E3A8A
        self.container = discord.ui.Container(
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(join_btn, leave_btn),
            discord.ui.ActionRow(settings_btn, start_btn, cancel_btn),
            accent_colour=discord.Colour(color)
        )
        
        self.add_item(self.container)
    
    async def join_callback(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id in lobby["players"]:
            await interaction.response.send_message("❌ You're already in!", ephemeral=True)
            return
        
        if len(lobby["players"]) >= 16:
            await interaction.response.send_message("❌ Lobby full! (16/16)", ephemeral=True)
            return
        
        lobby["players"].append(interaction.user.id)
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def leave_callback(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id not in lobby["players"]:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        
        if interaction.user.id == lobby["host"]:
            await interaction.response.send_message("❌ Host can't leave! Cancel the game instead.", ephemeral=True)
            return
        
        lobby["players"].remove(interaction.user.id)
        self.clear_items()
        self._build_ui()
        await interaction.response.edit_message(view=self)
    
    async def settings_callback(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != lobby["host"]:
            lang = lobby["language"]
            msg = "❌ Tylko host może zmieniać ustawienia!" if lang == "pl" else "❌ Only host can change settings!"
            await interaction.response.send_message(msg, ephemeral=True)
            return
        
        # Show settings view by editing current message
        settings_view = MafiaSettingsView(self.cog, self.lobby_id, interaction.message)
        await interaction.response.edit_message(view=settings_view)
    
    async def start_callback(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can start!", ephemeral=True)
            return
        
        # Check min players (6 for all modes)
        min_players = 6
        if len(lobby["players"]) < min_players:
            lang = lobby["language"]
            msg = (f"❌ Potrzeba co najmniej {min_players} graczy!" if lang == "pl" 
                   else f"❌ Need at least {min_players} players!")
            await interaction.response.send_message(msg, ephemeral=True)
            return
        
        # Check if preset exists or custom is valid
        if lobby["mode"] != "custom":
            player_count = len(lobby["players"])
            preset_key = f"{lobby['theme']}_{lobby['mode']}"
            if player_count not in PRESETS.get(preset_key, {}):
                await interaction.response.send_message(
                    f"❌ No preset for {player_count} players in {lobby['theme']} {lobby['mode']} mode!",
                    ephemeral=True
                )
                return
        else:
            # Custom mode validation
            if len(lobby.get("custom_roles", [])) != len(lobby["players"]):
                await interaction.response.send_message(
                    "❌ Custom roles not configured! Use Settings → Custom Mode",
                    ephemeral=True
                )
                return
        
        lobby["started"] = True
        await interaction.response.send_message("🎮 **Game Starting!** Assigning roles...", ephemeral=True)
        await self.cog.start_mafia_game(interaction, self.lobby_id)
    
    async def cancel_callback(self, interaction: discord.Interaction):
        lobby = self.cog.active_lobbies.get(self.lobby_id)
        if not lobby:
            await interaction.response.send_message("❌ Lobby no longer exists!", ephemeral=True)
            return
        
        if interaction.user.id != lobby["host"]:
            await interaction.response.send_message("❌ Only host can cancel!", ephemeral=True)
            return
        
        del self.cog.active_lobbies[self.lobby_id]
        await interaction.response.send_message("❌ **Game cancelled by host.**")
        await interaction.message.delete()

# ========================================
# MAFIA COG
# ========================================

class MafiaCog(commands.Cog):
    """Advanced Mafia/Werewolf social deduction game"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_lobbies = {}
        self.active_games = {}
    
    @app_commands.command(name="mafia", description="🕴️ Start a Mafia/Werewolf social deduction game")
    async def mafia_command(self, interaction: discord.Interaction):
        """Create a new Mafia/Werewolf lobby"""
        
        lobby_id = f"mafia_{interaction.channel.id}"
        if lobby_id in self.active_lobbies:
            await interaction.response.send_message("❌ A game is already active in this channel!", ephemeral=True)
            return
        
        # Create lobby with defaults
        self.active_lobbies[lobby_id] = {
            "host": interaction.user.id,
            "players": [interaction.user.id],
            "theme": "mafia",
            "mode": "normal",
            "language": "en",
            "day_duration": 180,
            "night_duration": 90,
            "vote_duration": 60,
            "voice_mode": False,
            "custom_roles": [],
            "started": False,
            "channel_id": interaction.channel.id,
            "created_at": datetime.utcnow()
        }
        
        view = MafiaLobbyView(self, lobby_id)
        await interaction.response.send_message(view=view)
    
    async def start_mafia_game(self, interaction: discord.Interaction, lobby_id: str):
        """Start the actual Mafia game with full loop"""
        lobby = self.active_lobbies.get(lobby_id)
        if not lobby:
            return
        
        guild = interaction.guild
        channel = interaction.channel
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
                    ("🏚️", "magazyn" if lang == "pl" else "warehouse"),
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
        
        # Set permissions - initially only main is visible to players
        player_members = [await guild.fetch_member(pid) for pid in lobby["players"]]
        
        # Main channel - all players can see
        for member in player_members:
            await main_channel.set_permissions(member, read_messages=True, send_messages=True)
        
        # Evil channel - hidden initially (or skip in voice mode)
        if not lobby.get("voice_mode", False):
            await evil_channel.set_permissions(guild.default_role, read_messages=False)
        else:
            # In voice mode, evil channel is hidden - force public meetings
            await evil_channel.set_permissions(guild.default_role, read_messages=False)
            await evil_channel.edit(name="❌-disabled-voice-mode")
        
        # Dead channel - hidden initially
        await dead_channel.set_permissions(guild.default_role, read_messages=False)
        
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
            "voice_channels": voice_channels,  # Voice mode meeting spots
            "center_voice_channel_id": center_voice_channel.id if center_voice_channel else None,
            "game_center_text_id": game_center_text.id if game_center_text else None,
            "theme": theme,
            "mode": mode,
            "language": lang,
            "day_duration": lobby["day_duration"],
            "night_duration": lobby["night_duration"],
            "vote_duration": lobby["vote_duration"],
            "voice_mode": lobby["voice_mode"],
            "players": {},  # {player_id: {"role": role_id, "alive": True, "votes": 0}}
            "alive_players": [],
            "dead_players": [],
            "day_number": 0,
            "phase": "night",  # night, day, vote
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
        
        # Grant evil faction access to their channel
        guild = self.bot.get_guild(game_state["guild_id"])
        evil_channel = guild.get_channel(game_state["evil_channel_id"])
        evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
        
        for player_id, player_data in game_state["players"].items():
            if player_data["faction"] == evil_faction:
                member = await guild.fetch_member(player_id)
                await evil_channel.set_permissions(member, read_messages=True, send_messages=True)
        
        # Send roles via DM
        await self._send_roles_dm(game_state)
        
        # Announce in original channel
        await channel.send(
            f"# 🎮 **{'GRA ROZPOCZĘTA!' if lang == 'pl' else 'GAME STARTED!'}**\n"
            f"{'Gra przeniesiona do' if lang == 'pl' else 'Game moved to'} {main_channel.mention}\n"
            f"{'Role zostały rozdane. Sprawdźcie DM!' if lang == 'pl' else 'Roles have been assigned. Check your DMs!'}"
        )
        
        # Send welcome message in main channel
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
    
    async def _send_roles_dm(self, game_state: dict):
        """Send role assignments via DM"""
        lang = game_state["language"]
        theme = game_state["theme"]
        
        for player_id, player_data in game_state["players"].items():
            try:
                user = await self.bot.fetch_user(player_id)
                role_id = player_data["role"]
                role_info = player_data["role_info"]
                faction = player_data["faction"]
                
                role_name = role_info[f"name_{lang}"]
                role_emoji = role_info["emoji"]
                power = role_info.get("power")
                
                # Faction names
                faction_names = {
                    "pl": {
                        "TOWN": "🏛️ MIASTO",
                        "MAFIA": "🔫 MAFIA",
                        "VILLAGE": "🏘️ WIOSKA",
                        "WEREWOLVES": "🐺 WILKOŁAKI",
                        "NEUTRAL": "⚖️ NEUTRALNY",
                        "CHAOS": "🌀 CHAOS"
                    },
                    "en": {
                        "TOWN": "🏛️ TOWN",
                        "MAFIA": "🔫 MAFIA",
                        "VILLAGE": "🏘️ VILLAGE",
                        "WEREWOLVES": "🐺 WEREWOLVES",
                        "NEUTRAL": "⚖️ NEUTRAL",
                        "CHAOS": "🌀 CHAOS"
                    }
                }
                
                faction_display = faction_names[lang].get(faction, faction)
                
                # Get description
                descriptions = {
                    "pl": {
                        None: "Zwykły obywatel bez specjalnych mocy.",
                        "investigate": "Co noc możesz zbadać gracza i dowiedzieć się czy jest zły.",
                        "protect": "Co noc możesz ochronić gracza przed śmiercią.",
                        "kill": "Co noc możesz zabić wybranego gracza (głosowanie z zespołem).",
                        "kill_leader": "Zabijasz graczy i jesteś odporny na wykrycie.",
                    },
                    "en": {
                        None: "Regular citizen with no special powers.",
                        "investigate": "Each night you can investigate a player to learn if they are evil.",
                        "protect": "Each night you can protect a player from death.",
                        "kill": "Each night you can kill a chosen player (vote with team).",
                        "kill_leader": "You kill players and are immune to detection.",
                    }
                }
                
                desc = descriptions[lang].get(power, "Specjalna rola." if lang == "pl" else "Special role.")
                
                msg = (
                    f"# 🎭 {'TWOJA ROLA' if lang == 'pl' else 'YOUR ROLE'}\n\n"
                    f"**{role_emoji} {role_name}**\n"
                    f"{faction_display}\n\n"
                    f"**{'Opis' if lang == 'pl' else 'Description'}:**\n{desc}\n\n"
                    f"{'Powodzenia!' if lang == 'pl' else 'Good luck!'} 🎮"
                )
                
                await user.send(msg)
            except Exception as e:
                print(f"Failed to send DM to {player_id}: {e}")
    
    async def _night_phase(self, lobby_id: str):
        """Execute night phase"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return
        
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
    
    async def _process_night(self, lobby_id: str):
        """Process night actions and move to day"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return
        
        main_channel = self.bot.get_channel(game_state["main_channel_id"])
        dead_channel = self.bot.get_channel(game_state["dead_channel_id"])
        guild = self.bot.get_guild(game_state["guild_id"])
        lang = game_state["language"]
        theme = game_state["theme"]
        
        # Determine who was killed
        evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
        target = game_state["night_actions"].get(evil_faction)
        
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
    
    async def _day_phase(self, lobby_id: str):
        """Execute day phase (discussion)"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return
        
        game_state["phase"] = "day"
        main_channel = self.bot.get_channel(game_state["main_channel_id"])
        lang = game_state["language"]
        guild = self.bot.get_guild(game_state["guild_id"])
        
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
    
    async def _vote_phase(self, lobby_id: str):
        """Execute voting phase"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return
        
        game_state["phase"] = "vote"
        game_state["votes"] = {}
        
        # Use game center text for voice mode, otherwise main channel
        if game_state.get("voice_mode", False) and game_state.get("game_center_text_id"):
            channel = self.bot.get_channel(game_state["game_center_text_id"])
        else:
            channel = self.bot.get_channel(game_state["main_channel_id"])
        
        lang = game_state["language"]
        guild = self.bot.get_guild(game_state["guild_id"])
        
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
    
    async def _process_votes(self, lobby_id: str):
        """Process voting results"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return
        
        main_channel = self.bot.get_channel(game_state["main_channel_id"])
        dead_channel = self.bot.get_channel(game_state["dead_channel_id"])
        guild = self.bot.get_guild(game_state["guild_id"])
        lang = game_state["language"]
        
        # Count votes
        vote_counts = {}
        for voter, target in game_state["votes"].items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        if not vote_counts:
            await main_channel.send(f"❌ {'Nikt nie głosował!' if lang == 'pl' else 'No one voted!'}")
        else:
            # Find player with most votes
            lynched = max(vote_counts, key=vote_counts.get)
            lynch_votes = vote_counts[lynched]
            
            # Show results
            results = "\n".join([f"<@{pid}>: **{count}** {'głos(ów)' if lang == 'pl' else 'vote(s)'}" 
                                for pid, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)])
            
            await main_channel.send(
                f"## 📊 {'WYNIKI GŁOSOWANIA' if lang == 'pl' else 'VOTE RESULTS'}\n{results}"
            )
            
            # Lynch player
            if game_state["players"][lynched]["alive"]:
                game_state["players"][lynched]["alive"] = False
                game_state["alive_players"].remove(lynched)
                game_state["dead_players"].append(lynched)
                
                role_id = game_state["players"][lynched]["role"]
                role_info = game_state["players"][lynched]["role_info"]
                role_name = role_info[f"name_{lang}"]
                role_emoji = role_info["emoji"]
                
                # Give access to ghost channel
                try:
                    member = await guild.fetch_member(lynched)
                    await dead_channel.set_permissions(member, read_messages=True, send_messages=True)
                except:
                    pass
                
                await main_channel.send(
                    f"⚰️ <@{lynched}> {'został zlinczowany!' if lang == 'pl' else 'was lynched!'}\n"
                    f"{'Był' if lang == 'pl' else 'They were'} **{role_emoji} {role_name}**"
                )
        
        # Check win conditions
        if await self._check_win_condition(lobby_id):
            return
        
        # Continue to next night
        await asyncio.sleep(3)
        await self._night_phase(lobby_id)
    
    async def _check_win_condition(self, lobby_id: str) -> bool:
        """Check if any faction has won"""
        game_state = self.active_games.get(lobby_id)
        if not game_state:
            return True
        
        main_channel = self.bot.get_channel(game_state["main_channel_id"])
        guild = self.bot.get_guild(game_state["guild_id"])
        lang = game_state["language"]
        theme = game_state["theme"]
        
        # Count alive players by faction
        alive_by_faction = {}
        for pid in game_state["alive_players"]:
            faction = game_state["players"][pid]["faction"]
            alive_by_faction[faction] = alive_by_faction.get(faction, 0) + 1
        
        evil_faction = "MAFIA" if theme == "mafia" else "WEREWOLVES"
        good_faction = "TOWN" if theme == "mafia" else "VILLAGE"
        
        evil_count = alive_by_faction.get(evil_faction, 0)
        good_count = alive_by_faction.get(good_faction, 0)
        
        winner = None
        
        # Evil wins if they equal or outnumber good
        if evil_count >= good_count and evil_count > 0:
            winner = evil_faction
        # Good wins if no evil left
        elif evil_count == 0:
            winner = good_faction
        
        if winner:
            winner_name = {
                "MAFIA": "🔫 MAFIA",
                "WEREWOLVES": "🐺 " + ("WILKOŁAKI" if lang == "pl" else "WEREWOLVES"),
                "TOWN": "🏛️ " + ("MIASTO" if lang == "pl" else "TOWN"),
                "VILLAGE": "🏘️ " + ("WIOSKA" if lang == "pl" else "VILLAGE"),
            }.get(winner, winner)
            
            # Show all roles
            role_list = []
            for pid, pdata in game_state["players"].items():
                role_info = pdata["role_info"]
                role_name = role_info[f"name_{lang}"]
                role_emoji = role_info["emoji"]
                status = "✅" if pdata["alive"] else "💀"
                role_list.append(f"{status} <@{pid}>: {role_emoji} {role_name}")
            
            await main_channel.send(
                f"# 🏆 {'KONIEC GRY!' if lang == 'pl' else 'GAME OVER!'}\n\n"
                f"## {winner_name} {'WYGRYWA!' if lang == 'pl' else 'WINS!'}\n\n"
                f"**{'Role' if lang == 'pl' else 'Roles'}:**\n" + "\n".join(role_list) +
                f"\n\n{'Kategoria zostanie usunięta za 60 sekund...' if lang == 'pl' else 'Category will be deleted in 60 seconds...'}"
            )
            
            # Wait before cleanup
            await asyncio.sleep(60)
            
            # Delete category and all channels
            try:
                category = guild.get_channel(game_state["category_id"])
                if category:
                    for channel in category.channels:
                        await channel.delete()
                    await category.delete()
            except Exception as e:
                print(f"Failed to delete category: {e}")
            
            # Cleanup
            del self.active_games[lobby_id]
            if lobby_id in self.active_lobbies:
                del self.active_lobbies[lobby_id]
            
            return True
        
        return False


# ========================================
# GAME PHASE VIEWS
# ========================================

class NightActionView(discord.ui.View):
    """View for night actions (evil faction voting)"""
    
    def __init__(self, cog, lobby_id: str, faction: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.lobby_id = lobby_id
        self.faction = faction
        self._build_ui()
    
    def _build_ui(self):
        game_state = self.cog.active_games.get(self.lobby_id)
        if not game_state:
            return
        
        # Get alive targets (not in evil faction)
        targets = [pid for pid, pdata in game_state["players"].items() 
                  if pdata["alive"] and pdata["faction"] != self.faction]
        
        if not targets:
            return
        
        # Create select menu
        options = []
        for pid in targets[:25]:  # Max 25 options
            try:
                role_info = game_state["players"][pid]["role_info"]
                options.append(discord.SelectOption(
                    label=f"Player {pid[:8]}...",
                    value=str(pid),
                    emoji="🎯"
                ))
            except:
                pass
        
        if options:
            select = discord.ui.Select(
                placeholder="Choose target...",
                options=options
            )
            select.callback = self.vote_target
            self.add_item(select)
    
    async def vote_target(self, interaction: discord.Interaction):
        game_state = self.cog.active_games.get(self.lobby_id)
        if not game_state:
            return
        
        # Check if voter is in evil faction
        if interaction.user.id not in game_state["players"]:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        
        if game_state["players"][interaction.user.id]["faction"] != self.faction:
            await interaction.response.send_message("❌ You can't do that!", ephemeral=True)
            return
        
        target = int(interaction.data['values'][0])
        game_state["night_actions"][self.faction] = target
        
        await interaction.response.send_message(f"✅ Target selected!", ephemeral=True)


class VoteView(discord.ui.View):
    """View for day voting (lynch)"""
    
    def __init__(self, cog, lobby_id: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.lobby_id = lobby_id
        self._build_ui()
    
    def _build_ui(self):
        game_state = self.cog.active_games.get(self.lobby_id)
        if not game_state:
            return
        
        # Get alive players
        alive = game_state["alive_players"]
        
        if not alive:
            return
        
        # Create select menu
        options = []
        for pid in alive[:25]:  # Max 25 options
            try:
                options.append(discord.SelectOption(
                    label=f"Player {pid[:8]}...",
                    value=str(pid),
                    emoji="🗳️"
                ))
            except:
                pass
        
        if options:
            select = discord.ui.Select(
                placeholder="Vote to lynch...",
                options=options
            )
            select.callback = self.cast_vote
            self.add_item(select)
    
    async def cast_vote(self, interaction: discord.Interaction):
        game_state = self.cog.active_games.get(self.lobby_id)
        if not game_state:
            return
        
        # Check if voter is alive
        if interaction.user.id not in game_state["alive_players"]:
            await interaction.response.send_message("❌ You can't vote!", ephemeral=True)
            return
        
        target = int(interaction.data['values'][0])
        game_state["votes"][interaction.user.id] = target
        
        await interaction.response.send_message(f"✅ Vote cast for <@{target}>!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(MafiaCog(bot))
