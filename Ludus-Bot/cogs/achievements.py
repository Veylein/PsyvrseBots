import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import json
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis
try:
    from utils.stat_hooks import us_inc as _us_inc
except Exception:
    _us_inc = None

# ── Category metadata ────────────────────────────────────────────────────────
CATEGORIES = {
    "Economy":     {"emoji": "💰", "color": Colors.ECONOMY},
    "Gambling":    {"emoji": "🎰", "color": Colors.GAMBLING},
    "Gaming":      {"emoji": "🎮", "color": Colors.MINIGAMES},
    "TCG":         {"emoji": "⚔️", "color": Colors.TCG},
    "Social":      {"emoji": "💖", "color": Colors.SOCIAL},
    "Fishing":     {"emoji": "🎣", "color": Colors.FISHING},
    "Mining":      {"emoji": "⛏️", "color": 0x8B6914},
    "Farming":     {"emoji": "🌾", "color": 0x4CAF50},
    "Pets":        {"emoji": "🐾", "color": Colors.PETS},
    "Board Games": {"emoji": "♟️", "color": Colors.BOARD_GAMES},
    "Quests":      {"emoji": "📜", "color": Colors.QUESTS},
    "Events":      {"emoji": "🎉", "color": Colors.PRIMARY},
    "Milestones":  {"emoji": "⚡", "color": Colors.INFO},
}

def _bar(pct: float, length: int = 10) -> str:
    filled = min(int(pct / 100 * length), length)
    return "█" * filled + "░" * (length - filled)


class AchievementManager:
    """Manages 250+ achievements across all bot activities"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.achievements_file = os.path.join(data_dir, "user_achievements.json")
        self.user_achievements = self.load_achievements()
        
        # Define all 250+ achievements
        self.achievements = {
            # ── ECONOMY (15) ──────────────────────────────────────────────────
            "first_coins":          {"name": "First Steps",        "description": "Earn your first PsyCoin",                 "reward": 10,    "points": 5,   "emoji": "💰", "category": "Economy"},
            "hundred_coins":        {"name": "Getting Started",    "description": "Accumulate 100 PsyCoins",                 "reward": 50,    "points": 10,  "emoji": "💵", "category": "Economy"},
            "thousand_coins":       {"name": "Entrepreneur",       "description": "Accumulate 1,000 PsyCoins",               "reward": 100,   "points": 15,  "emoji": "💸", "category": "Economy"},
            "ten_thousand_coins":   {"name": "Business Mogul",     "description": "Accumulate 10,000 PsyCoins",              "reward": 500,   "points": 25,  "emoji": "💎", "category": "Economy"},
            "hundred_thousand_coins": {"name": "Wealthy",          "description": "Accumulate 100,000 PsyCoins",             "reward": 2000,  "points": 50,  "emoji": "👑", "category": "Economy"},
            "millionaire":          {"name": "Millionaire",        "description": "Accumulate 1,000,000 PsyCoins",           "reward": 10000, "points": 100, "emoji": "🏆", "category": "Economy"},
            "daily_starter":        {"name": "Daily Habit",        "description": "Claim daily reward 7 days in a row",      "reward": 100,   "points": 15,  "emoji": "📅", "category": "Economy"},
            "daily_dedication":     {"name": "Dedicated",          "description": "Claim daily reward 30 days in a row",     "reward": 500,   "points": 30,  "emoji": "📆", "category": "Economy"},
            "daily_legend":         {"name": "Daily Legend",       "description": "Claim daily reward 100 days in a row",    "reward": 2000,  "points": 75,  "emoji": "⭐", "category": "Economy"},
            "big_spender":          {"name": "Big Spender",        "description": "Spend 10,000 PsyCoins total",             "reward": 250,   "points": 20,  "emoji": "💳", "category": "Economy"},
            "shopaholic":           {"name": "Shopaholic",         "description": "Spend 100,000 PsyCoins total",            "reward": 1000,  "points": 40,  "emoji": "🛍️", "category": "Economy"},
            "business_owner":       {"name": "Business Owner",     "description": "Create your first business",              "reward": 200,   "points": 25,  "emoji": "🏪", "category": "Economy"},
            "first_sale":           {"name": "First Sale",         "description": "Make your first business sale",           "reward": 100,   "points": 15,  "emoji": "🤝", "category": "Economy"},
            "merchant":             {"name": "Merchant",           "description": "Make 50 business sales",                  "reward": 500,   "points": 35,  "emoji": "🏬", "category": "Economy"},
            "tycoon":               {"name": "Business Tycoon",    "description": "Make 500 business sales",                 "reward": 2000,  "points": 75,  "emoji": "🏭", "category": "Economy"},

            # ── GAMBLING (11) ─────────────────────────────────────────────────
            "lucky_start":          {"name": "Lucky Start",        "description": "Win your first gambling game",            "reward": 50,    "points": 10,  "emoji": "🎰", "category": "Gambling"},
            "gambler":              {"name": "Gambler",            "description": "Play 100 gambling games",                 "reward": 200,   "points": 20,  "emoji": "🎲", "category": "Gambling"},
            "high_roller":          {"name": "High Roller",        "description": "Play 1,000 gambling games",               "reward": 1000,  "points": 50,  "emoji": "💎", "category": "Gambling"},
            "slots_novice":         {"name": "Slots Novice",       "description": "Play slots 50 times",                     "reward": 100,   "points": 15,  "emoji": "🎰", "category": "Gambling"},
            "slots_master":         {"name": "Slots Master",       "description": "Play slots 500 times",                    "reward": 500,   "points": 35,  "emoji": "🎰", "category": "Gambling"},
            "blackjack_player":     {"name": "Blackjack Player",   "description": "Play blackjack 50 times",                 "reward": 100,   "points": 15,  "emoji": "🃏", "category": "Gambling"},
            "blackjack_ace":        {"name": "Blackjack Ace",      "description": "Win 100 blackjack games",                 "reward": 500,   "points": 40,  "emoji": "🃏", "category": "Gambling"},
            "big_win":              {"name": "Big Win!",           "description": "Win 1,000+ coins in one game",            "reward": 200,   "points": 25,  "emoji": "💰", "category": "Gambling"},
            "huge_win":             {"name": "Huge Win!",          "description": "Win 10,000+ coins in one game",           "reward": 1000,  "points": 50,  "emoji": "💸", "category": "Gambling"},
            "jackpot":              {"name": "JACKPOT!",           "description": "Win 100,000+ coins in one game",          "reward": 5000,  "points": 100, "emoji": "🏆", "category": "Gambling"},
            "winning_streak":       {"name": "On Fire!",           "description": "Win 5 gambling games in a row",           "reward": 300,   "points": 30,  "emoji": "🔥", "category": "Gambling"},
            "unstoppable":          {"name": "Unstoppable",        "description": "Win 10 gambling games in a row",          "reward": 1000,  "points": 60,  "emoji": "⚡", "category": "Gambling"},

            # ── GAMING / MINIGAMES (14) ───────────────────────────────────────
            "gamer":                {"name": "Gamer",              "description": "Play 50 minigames",                       "reward": 100,   "points": 15,  "emoji": "🎮", "category": "Gaming"},
            "game_master":          {"name": "Game Master",        "description": "Play 500 minigames",                      "reward": 500,   "points": 40,  "emoji": "🎮", "category": "Gaming"},
            "ultimate_gamer":       {"name": "Ultimate Gamer",     "description": "Play 2,000 minigames",                    "reward": 2000,  "points": 80,  "emoji": "🎮", "category": "Gaming"},
            "wordle_beginner":      {"name": "Word Seeker",        "description": "Win 10 Wordle games",                     "reward": 100,   "points": 15,  "emoji": "📝", "category": "Gaming"},
            "wordle_expert":        {"name": "Word Master",        "description": "Win 100 Wordle games",                    "reward": 500,   "points": 40,  "emoji": "📝", "category": "Gaming"},
            "riddle_solver":        {"name": "Riddle Solver",      "description": "Solve 25 riddles",                        "reward": 100,   "points": 20,  "emoji": "🧩", "category": "Gaming"},
            "riddle_master":        {"name": "Riddle Master",      "description": "Solve 100 riddles",                       "reward": 500,   "points": 45,  "emoji": "🧩", "category": "Gaming"},
            "trivia_novice":        {"name": "Trivia Novice",      "description": "Answer 50 trivia correctly",              "reward": 100,   "points": 20,  "emoji": "❓", "category": "Gaming"},
            "trivia_genius":        {"name": "Trivia Genius",      "description": "Answer 500 trivia correctly",             "reward": 1000,  "points": 50,  "emoji": "❓", "category": "Gaming"},
            "speed_demon":          {"name": "Speed Demon",        "description": "Get 100+ WPM in typerace",                "reward": 200,   "points": 30,  "emoji": "⚡", "category": "Gaming"},
            "typing_god":           {"name": "Typing God",         "description": "Get 150+ WPM in typerace",                "reward": 500,   "points": 50,  "emoji": "⚡", "category": "Gaming"},
            "monopoly_tycoon":      {"name": "Monopoly Tycoon",    "description": "Win a full Monopoly game",                "reward": 500,   "points": 40,  "emoji": "🎩", "category": "Gaming"},
            "uno_champion":         {"name": "UNO Champion",       "description": "Win 25 UNO games",                        "reward": 300,   "points": 30,  "emoji": "🃏", "category": "Gaming"},
            "chess_knight":         {"name": "Chess Knight",       "description": "Win 10 chess matches",                    "reward": 300,   "points": 35,  "emoji": "♟️", "category": "Gaming"},
            "chess_grand":          {"name": "Grandmaster",        "description": "Win 50 chess matches",                    "reward": 1500,  "points": 75,  "emoji": "♟️", "category": "Gaming"},

            # ── TCG (13) ──────────────────────────────────────────────────────
            "tcg_beginner":         {"name": "TCG Beginner",       "description": "Play your first TCG battle",              "reward": 50,    "points": 10,  "emoji": "⚔️", "category": "TCG"},
            "tcg_fighter":          {"name": "TCG Fighter",        "description": "Win 25 TCG battles",                      "reward": 200,   "points": 25,  "emoji": "⚔️", "category": "TCG"},
            "tcg_warrior":          {"name": "TCG Warrior",        "description": "Win 100 TCG battles",                     "reward": 500,   "points": 40,  "emoji": "⚔️", "category": "TCG"},
            "tcg_champion":         {"name": "TCG Champion",       "description": "Win 500 TCG battles",                     "reward": 2000,  "points": 75,  "emoji": "⚔️", "category": "TCG"},
            "ranked_debut":         {"name": "Ranked Debut",       "description": "Play your first ranked match",            "reward": 100,   "points": 15,  "emoji": "🏅", "category": "TCG"},
            "silver_rank":          {"name": "Silver Rank",        "description": "Reach Silver tier in ranked",             "reward": 200,   "points": 25,  "emoji": "🥈", "category": "TCG"},
            "gold_rank":            {"name": "Gold Rank",          "description": "Reach Gold tier in ranked",               "reward": 500,   "points": 40,  "emoji": "🥇", "category": "TCG"},
            "diamond_rank":         {"name": "Diamond Rank",       "description": "Reach Diamond tier in ranked",            "reward": 1000,  "points": 60,  "emoji": "💎", "category": "TCG"},
            "master_rank":          {"name": "Master Rank",        "description": "Reach Master tier in ranked",             "reward": 2000,  "points": 80,  "emoji": "👑", "category": "TCG"},
            "card_collector":       {"name": "Card Collector",     "description": "Own 50 TCG cards",                        "reward": 200,   "points": 20,  "emoji": "🎴", "category": "TCG"},
            "card_hoarder":         {"name": "Card Hoarder",       "description": "Own 200 TCG cards",                       "reward": 1000,  "points": 50,  "emoji": "🎴", "category": "TCG"},
            "tournament_entry":     {"name": "Tournament Entry",   "description": "Enter your first tournament",             "reward": 100,   "points": 15,  "emoji": "🏆", "category": "TCG"},
            "tournament_winner":    {"name": "Tournament Winner",  "description": "Win a tournament",                        "reward": 1000,  "points": 75,  "emoji": "🏆", "category": "TCG"},

            # ── SOCIAL (11) ───────────────────────────────────────────────────
            "friendly":             {"name": "Friendly",           "description": "Give 10 compliments",                     "reward": 50,    "points": 10,  "emoji": "💖", "category": "Social"},
            "kind_soul":            {"name": "Kind Soul",          "description": "Give 100 compliments",                    "reward": 300,   "points": 30,  "emoji": "💖", "category": "Social"},
            "angel":                {"name": "Angel",              "description": "Give 500 compliments",                    "reward": 1000,  "points": 60,  "emoji": "😇", "category": "Social"},
            "popular":              {"name": "Popular",            "description": "Receive 50 compliments",                  "reward": 200,   "points": 25,  "emoji": "⭐", "category": "Social"},
            "celebrity":            {"name": "Celebrity",          "description": "Receive 200 compliments",                 "reward": 1000,  "points": 50,  "emoji": "🌟", "category": "Social"},
            "roaster":              {"name": "Roast Master",       "description": "Give 50 roasts",                          "reward": 100,   "points": 15,  "emoji": "🔥", "category": "Social"},
            "savage":               {"name": "Savage",             "description": "Give 200 roasts",                         "reward": 500,   "points": 35,  "emoji": "🔥", "category": "Social"},
            "storyteller":          {"name": "Storyteller",        "description": "Contribute to 25 stories",                "reward": 200,   "points": 20,  "emoji": "📖", "category": "Social"},
            "author":               {"name": "Author",             "description": "Contribute to 100 stories",               "reward": 500,   "points": 40,  "emoji": "📖", "category": "Social"},
            "married":              {"name": "Taken",              "description": "Get married in Ludus",                    "reward": 300,   "points": 25,  "emoji": "💍", "category": "Social"},
            "heist_crew":           {"name": "Heist Crew",         "description": "Complete 10 heists",                      "reward": 400,   "points": 30,  "emoji": "🦹", "category": "Social"},

            # ── FISHING (10) ──────────────────────────────────────────────────
            "first_catch":          {"name": "First Catch",        "description": "Catch your first fish",                   "reward": 50,    "points": 10,  "emoji": "🎣", "category": "Fishing"},
            "angler":               {"name": "Angler",             "description": "Catch 100 fish",                          "reward": 200,   "points": 20,  "emoji": "🎣", "category": "Fishing"},
            "fishing_expert":       {"name": "Fishing Expert",     "description": "Catch 500 fish",                          "reward": 500,   "points": 40,  "emoji": "🎣", "category": "Fishing"},
            "master_angler":        {"name": "Master Angler",      "description": "Catch 2,000 fish",                        "reward": 2000,  "points": 80,  "emoji": "🎣", "category": "Fishing"},
            "rare_fisher":          {"name": "Rare Fisher",        "description": "Catch 10 rare fish",                      "reward": 200,   "points": 25,  "emoji": "🐟", "category": "Fishing"},
            "rare_hunter":          {"name": "Rare Hunter",        "description": "Catch 50 rare fish",                      "reward": 1000,  "points": 50,  "emoji": "🐟", "category": "Fishing"},
            "legendary_fisher":     {"name": "Legendary Fisher",   "description": "Catch your first legendary fish",         "reward": 500,   "points": 50,  "emoji": "🐋", "category": "Fishing"},
            "legend_hunter":        {"name": "Legend Hunter",      "description": "Catch 10 legendary fish",                 "reward": 2000,  "points": 80,  "emoji": "🐋", "category": "Fishing"},
            "big_catch":            {"name": "Big Catch",          "description": "Catch a fish weighing 50+ kg",            "reward": 300,   "points": 30,  "emoji": "🐟", "category": "Fishing"},
            "monster_catch":        {"name": "Monster Catch",      "description": "Catch a fish weighing 100+ kg",           "reward": 1000,  "points": 60,  "emoji": "🐋", "category": "Fishing"},

            # ── MINING (17) ───────────────────────────────────────────────────
            "first_mine":           {"name": "First Pickaxe",      "description": "Mine your first block",                   "reward": 50,    "points": 10,  "emoji": "⛏️", "category": "Mining"},
            "miner_novice":         {"name": "Miner Novice",       "description": "Mine 100 blocks",                         "reward": 100,   "points": 15,  "emoji": "⛏️", "category": "Mining"},
            "miner_veteran":        {"name": "Miner Veteran",      "description": "Mine 1,000 blocks",                       "reward": 400,   "points": 35,  "emoji": "⛏️", "category": "Mining"},
            "tunnel_rat":           {"name": "Tunnel Rat",         "description": "Mine 10,000 blocks total",                "reward": 2000,  "points": 80,  "emoji": "🐀", "category": "Mining"},
            "depth_10":             {"name": "Going Deeper",       "description": "Reach depth 10 in the mine",             "reward": 100,   "points": 15,  "emoji": "🕳️", "category": "Mining"},
            "depth_50":             {"name": "Deep Diver",         "description": "Reach depth 50 in the mine",             "reward": 500,   "points": 40,  "emoji": "🌊", "category": "Mining"},
            "depth_100":            {"name": "Abyss Walker",       "description": "Reach depth 100 (the Abyss!)",           "reward": 2000,  "points": 100, "emoji": "🌑", "category": "Mining"},
            "diamond_find":         {"name": "Diamonds!",          "description": "Find your first diamond ore",             "reward": 300,   "points": 30,  "emoji": "💎", "category": "Mining"},
            "emerald_find":         {"name": "Emerald Hunter",     "description": "Find your first emerald ore",             "reward": 400,   "points": 35,  "emoji": "💚", "category": "Mining"},
            "netherite_find":       {"name": "Netherite",          "description": "Find netherite deep underground",         "reward": 2000,  "points": 90,  "emoji": "⬛", "category": "Mining"},
            "chest_finder":         {"name": "Treasure Hunter",    "description": "Find 5 chests in the mine",               "reward": 500,   "points": 35,  "emoji": "📦", "category": "Mining"},
            "creature_hunter":      {"name": "Monster Hunter",     "description": "Defeat 10 underground creatures",         "reward": 400,   "points": 30,  "emoji": "🗡️", "category": "Mining"},
            "creature_slayer":      {"name": "Creature Slayer",    "description": "Defeat 100 underground creatures",        "reward": 2000,  "points": 70,  "emoji": "⚔️", "category": "Mining"},
            "dynamite_fan":         {"name": "Demolitionist",      "description": "Use 10 dynamites in the mine",            "reward": 300,   "points": 25,  "emoji": "💣", "category": "Mining"},
            "mine_millionaire":     {"name": "Rich Miner",         "description": "Earn 10,000 coins from mining",           "reward": 800,   "points": 50,  "emoji": "💰", "category": "Mining"},
            "pickaxe_upgrade":      {"name": "Upgraded",           "description": "Upgrade your pickaxe to level 3",         "reward": 300,   "points": 25,  "emoji": "🔨", "category": "Mining"},
            "pickaxe_master":       {"name": "Pickaxe Master",     "description": "Reach max pickaxe level 5",               "reward": 1500,  "points": 75,  "emoji": "⛏️", "category": "Mining"},

            # ── FARMING (6) ───────────────────────────────────────────────────
            "first_crop":           {"name": "Green Thumb",        "description": "Plant your first crop",                   "reward": 50,    "points": 10,  "emoji": "🌱", "category": "Farming"},
            "first_harvest":        {"name": "First Harvest",      "description": "Harvest your first crop",                 "reward": 75,    "points": 12,  "emoji": "🌾", "category": "Farming"},
            "farmer":               {"name": "Farmer",             "description": "Harvest 100 crops",                       "reward": 200,   "points": 20,  "emoji": "🚜", "category": "Farming"},
            "master_farmer":        {"name": "Master Farmer",      "description": "Harvest 1,000 crops",                     "reward": 1000,  "points": 55,  "emoji": "🏡", "category": "Farming"},
            "farm_tycoon":          {"name": "Farm Tycoon",        "description": "Reach farm level 10",                     "reward": 2000,  "points": 80,  "emoji": "🌻", "category": "Farming"},
            "crop_seller":          {"name": "Crop Seller",        "description": "Sell 500 crops at market",                "reward": 500,   "points": 35,  "emoji": "💹", "category": "Farming"},

            # ── PETS (7) ──────────────────────────────────────────────────────
            "pet_owner":            {"name": "Pet Owner",          "description": "Adopt your first pet",                    "reward": 100,   "points": 15,  "emoji": "🐾", "category": "Pets"},
            "pet_feeder":           {"name": "Loving Owner",       "description": "Feed your pet 100 times",                 "reward": 300,   "points": 25,  "emoji": "🍖", "category": "Pets"},
            "pet_lover":            {"name": "Pet Lover",          "description": "Reach max pet happiness",                  "reward": 400,   "points": 30,  "emoji": "❤️", "category": "Pets"},
            "pet_adventurer":       {"name": "Pet Adventurer",     "description": "Send pet on 20 adventures",               "reward": 500,   "points": 35,  "emoji": "🗺️", "category": "Pets"},
            "pet_lvl5":             {"name": "Bonded",             "description": "Raise pet to level 5",                    "reward": 300,   "points": 25,  "emoji": "⭐", "category": "Pets"},
            "pet_lvl10":            {"name": "True Companion",     "description": "Raise pet to level 10",                   "reward": 1000,  "points": 60,  "emoji": "🌟", "category": "Pets"},
            "pet_rare":             {"name": "Rare Companion",     "description": "Adopt a rare pet",                        "reward": 500,   "points": 40,  "emoji": "✨", "category": "Pets"},

            # ── BOARD GAMES (8) ───────────────────────────────────────────────
            "ttt_player":           {"name": "TTT Player",         "description": "Play 25 Tic-Tac-Toe games",              "reward": 100,   "points": 15,  "emoji": "❌", "category": "Board Games"},
            "ttt_master":           {"name": "TTT Master",         "description": "Win 50 Tic-Tac-Toe games",               "reward": 300,   "points": 30,  "emoji": "❌", "category": "Board Games"},
            "connect4_player":      {"name": "Connect4 Player",    "description": "Play 25 Connect4 games",                  "reward": 100,   "points": 15,  "emoji": "🔴", "category": "Board Games"},
            "connect4_master":      {"name": "Connect4 Master",    "description": "Win 50 Connect4 games",                   "reward": 300,   "points": 30,  "emoji": "🔴", "category": "Board Games"},
            "hangman_player":       {"name": "Hangman Player",     "description": "Play 25 Hangman games",                   "reward": 100,   "points": 15,  "emoji": "🎯", "category": "Board Games"},
            "hangman_master":       {"name": "Hangman Master",     "description": "Win 50 Hangman games",                    "reward": 300,   "points": 30,  "emoji": "🎯", "category": "Board Games"},
            "checkers_player":      {"name": "Checkers Player",    "description": "Play 20 Checkers games",                  "reward": 100,   "points": 15,  "emoji": "🔵", "category": "Board Games"},
            "checkers_master":      {"name": "Checkers King",      "description": "Win 30 Checkers games",                   "reward": 300,   "points": 30,  "emoji": "🔵", "category": "Board Games"},

            # ── QUESTS (7) ────────────────────────────────────────────────────
            "quest_starter":        {"name": "Quest Starter",      "description": "Complete your first quest",               "reward": 50,    "points": 10,  "emoji": "📜", "category": "Quests"},
            "quest_hunter":         {"name": "Quest Hunter",       "description": "Complete 25 quests",                      "reward": 200,   "points": 25,  "emoji": "📜", "category": "Quests"},
            "quest_master":         {"name": "Quest Master",       "description": "Complete 100 quests",                     "reward": 1000,  "points": 50,  "emoji": "📜", "category": "Quests"},
            "quest_legend":         {"name": "Quest Legend",       "description": "Complete 500 quests",                     "reward": 5000,  "points": 100, "emoji": "📜", "category": "Quests"},
            "daily_quester":        {"name": "Daily Quester",      "description": "Complete 10 daily quests",                "reward": 100,   "points": 15,  "emoji": "📅", "category": "Quests"},
            "daily_champion":       {"name": "Daily Champion",     "description": "Complete 100 daily quests",               "reward": 1000,  "points": 50,  "emoji": "📅", "category": "Quests"},
            "weekly_completer":     {"name": "Weekly Warrior",     "description": "Complete all weekly quests 5 times",      "reward": 2000,  "points": 70,  "emoji": "📆", "category": "Quests"},

            # ── EVENTS (5) ────────────────────────────────────────────────────
            "event_participant":    {"name": "Event Participant",  "description": "Join your first event",                   "reward": 100,   "points": 15,  "emoji": "🎉", "category": "Events"},
            "event_enthusiast":     {"name": "Event Enthusiast",   "description": "Join 10 events",                          "reward": 300,   "points": 25,  "emoji": "🎉", "category": "Events"},
            "event_legend":         {"name": "Event Legend",       "description": "Join 50 events",                          "reward": 1000,  "points": 50,  "emoji": "🎉", "category": "Events"},
            "event_winner":         {"name": "Event Winner",       "description": "Win your first event",                    "reward": 500,   "points": 40,  "emoji": "🏆", "category": "Events"},
            "event_champion":       {"name": "Event Champion",     "description": "Win 10 events",                           "reward": 2000,  "points": 75,  "emoji": "🏆", "category": "Events"},

            # ── MILESTONES (7) ────────────────────────────────────────────────
            "active_user":          {"name": "Active User",        "description": "Use 1,000 commands",                      "reward": 500,   "points": 40,  "emoji": "⚡", "category": "Milestones"},
            "power_user":           {"name": "Power User",         "description": "Use 10,000 commands",                     "reward": 2000,  "points": 75,  "emoji": "⚡", "category": "Milestones"},
            "legendary_user":       {"name": "Legendary User",     "description": "Use 50,000 commands",                     "reward": 10000, "points": 150, "emoji": "⚡", "category": "Milestones"},
            "chatty":               {"name": "Chatty",             "description": "Send 1,000 messages",                     "reward": 200,   "points": 20,  "emoji": "💬", "category": "Milestones"},
            "conversationalist":    {"name": "Conversationalist",  "description": "Send 10,000 messages",                    "reward": 1000,  "points": 50,  "emoji": "💬", "category": "Milestones"},
            "veteran":              {"name": "Veteran",            "description": "Be active for 30 days",                   "reward": 500,   "points": 40,  "emoji": "🎖️", "category": "Milestones"},
            "ancient":              {"name": "Ancient One",        "description": "Be active for 365 days",                  "reward": 5000,  "points": 100, "emoji": "👴", "category": "Milestones"},
        }

    def load_achievements(self):
        """Load user achievements from JSON"""
        if os.path.exists(self.achievements_file):
            try:
                with open(self.achievements_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_achievements(self):
        """Save achievements to JSON (atomic write)"""
        tmp = self.achievements_file + ".tmp"
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.user_achievements, f, indent=4)
            os.replace(tmp, self.achievements_file)
        except Exception as e:
            print(f"[Achievements] Save error: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
    
    def get_user_achievements(self, user_id):
        """Get or create user achievement data"""
        user_id = str(user_id)
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = {
                "unlocked": [],
                "progress": {},
                "points": 0,
                "unlocked_at": {}
            }
            self.save_achievements()
        return self.user_achievements[user_id]
    
    def check_achievement(self, user_id, achievement_id):
        """Check if user has unlocked an achievement"""
        user_data = self.get_user_achievements(user_id)
        return achievement_id in user_data["unlocked"]
    
    def unlock_achievement(self, user_id, achievement_id):
        """Unlock an achievement for a user"""
        if achievement_id not in self.achievements:
            return None
        
        user_data = self.get_user_achievements(user_id)
        
        if achievement_id in user_data["unlocked"]:
            return None  # Already unlocked
        
        achievement = self.achievements[achievement_id]
        user_data["unlocked"].append(achievement_id)
        user_data["points"] += achievement["points"]
        user_data["unlocked_at"][achievement_id] = discord.utils.utcnow().isoformat()
        
        self.save_achievements()
        # Track in data/users/{id}.json
        if _us_inc is not None:
            try:
                _us_inc(int(user_id), 'achievements_unlocked')
            except Exception:
                pass
        return achievement
    
    def get_achievements_by_category(self, category):
        """Get all achievements in a category"""
        return {k: v for k, v in self.achievements.items() if v["category"] == category}
    
    def get_user_progress(self, user_id):
        """Get user's achievement progress"""
        user_data = self.get_user_achievements(user_id)
        total = len(self.achievements)
        unlocked = len(user_data["unlocked"])
        percentage = (unlocked / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "unlocked": unlocked,
            "percentage": percentage,
            "points": user_data["points"]
        }
    
    def get_category_progress(self, user_id, category):
        """Get progress in a specific category"""
        user_data = self.get_user_achievements(user_id)
        category_achievements = self.get_achievements_by_category(category)
        
        total = len(category_achievements)
        unlocked = sum(1 for ach_id in category_achievements.keys() if ach_id in user_data["unlocked"])
        percentage = (unlocked / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "unlocked": unlocked,
            "percentage": percentage
        }

class AchievementView(discord.ui.View):
    """Embed-based achievement browser — uses inline fields for proper 3-column grid."""
    PER_PAGE = 5 # For category pages (overview shows all categories in one)

    def __init__(self, manager: "AchievementManager", user: discord.User, viewer_id: int):
        super().__init__(timeout=180)
        self.manager   = manager
        self.user      = user
        self.viewer_id = viewer_id
        self.category  = "overview"
        self.page      = 0
        self._build_select()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _cat_color(self) -> discord.Colour:
        if self.category == "overview":
            return discord.Colour(Colors.WARNING)
        return discord.Colour(CATEGORIES.get(self.category, {}).get("color", Colors.PRIMARY))

    def _cat_emoji(self, cat: str = None) -> str:
        c = cat or self.category
        if c == "overview":
            return "🏆"
        return CATEGORIES.get(c, {}).get("emoji", "🏆")

    # ── embed builders ────────────────────────────────────────────────────────

    def build_embed(self) -> discord.Embed:
        if self.category == "overview":
            return self._embed_overview()
        return self._embed_category()

    def _embed_overview(self) -> discord.Embed:
        progress  = self.manager.get_user_progress(self.user.id)
        user_data = self.manager.get_user_achievements(self.user.id)
        pct       = progress["percentage"]
        bar       = _bar(pct, 20)

        embed = discord.Embed(
            title=f"🏆 {self.user.display_name}'s Achievements",
            description=(
                f"**Progress:** {bar} `{pct:.1f}%`\n"
                f"**{progress['unlocked']}/{progress['total']}** unlocked  •  "
                f"**{progress['points']}** Achievement Points\n"
                f"-# Achievement Points = total points for unlocked achievements (visible in /leaderboard)\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=self._cat_color(),
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)

        # 3-column grid via inline fields — Discord handles alignment natively
        for cat in CATEGORIES.keys():
            cp  = self.manager.get_category_progress(self.user.id, cat)
            bar = _bar(cp["percentage"], 10)
            embed.add_field(
                name=f"{self._cat_emoji(cat)} {cat}",
                value=f"{bar}\n`{cp['unlocked']}/{cp['total']}` `{cp['percentage']:.0f}%`",
                inline=True,
            )

        # Recent unlocks
        recent = sorted(
            user_data.get("unlocked_at", {}).items(),
            key=lambda x: x[1], reverse=True
        )[:5]
        if recent:
            lines = []
            for ach_id, _ in recent:
                if ach_id in self.manager.achievements:
                    a = self.manager.achievements[ach_id]
                    lines.append(f"{a['emoji']} **{a['name']}** — *{a['description']}*")
            embed.add_field(name="✨ Recently Unlocked", value="\n".join(lines), inline=False)

        embed.set_footer(text="Use the dropdown to switch categories!")
        return embed

    def _embed_category(self) -> discord.Embed:
        all_ach   = list(self.manager.get_achievements_by_category(self.category).items())
        user_data = self.manager.get_user_achievements(self.user.id)
        cp        = self.manager.get_category_progress(self.user.id, self.category)
        bar       = _bar(cp["percentage"], 20)
        total_pg  = max(1, (len(all_ach) + self.PER_PAGE - 1) // self.PER_PAGE)
        page_ach  = all_ach[self.page * self.PER_PAGE : (self.page + 1) * self.PER_PAGE]

        embed = discord.Embed(
            title=f"{self._cat_emoji()} {self.category} Achievements",
            description=(
                f"{bar} `{cp['percentage']:.1f}%`  •  "
                f"**{cp['unlocked']}**/**{cp['total']}** unlocked\n"
                f"-# Page {self.page + 1}/{total_pg}"
            ),
            color=self._cat_color(),
        )
        embed.set_thumbnail(url=self.user.display_avatar.url)

        for ach_id, ach in page_ach:
            unlocked = ach_id in user_data["unlocked"]
            status   = "✅" if unlocked else "🔒"
            embed.add_field(
                name=f"{status} {ach['emoji']} {ach['name']}",
                value=f"{ach['description']}\n-# 💰 {ach['reward']:,} coins  •  ⭐ {ach['points']} pts",
                inline=False,
            )

        embed.set_footer(text="Use the dropdown to switch categories!")
        return embed

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_select(self):
        # Remove old select/buttons, re-add fresh
        self.clear_items()

        # Pagination buttons (only for category pages)
        if self.category != "overview":
            all_ach  = list(self.manager.get_achievements_by_category(self.category).items())
            total_pg = max(1, (len(all_ach) + self.PER_PAGE - 1) // self.PER_PAGE)
            if total_pg > 1:
                prev_btn = discord.ui.Button(
                    label="◀ Prev", style=discord.ButtonStyle.secondary,
                    disabled=(self.page == 0), row=0
                )
                prev_btn.callback = self._prev_page
                next_btn = discord.ui.Button(
                    label="Next ▶", style=discord.ButtonStyle.secondary,
                    disabled=(self.page >= total_pg - 1), row=0
                )
                next_btn.callback = self._next_page
                self.add_item(prev_btn)
                self.add_item(next_btn)

        main_select = discord.ui.Select(
            placeholder="🏆 Choose a category  ▾",
            row=1,
            options=[
                discord.SelectOption(label="Overview",      value="overview",    emoji="📊", default=self.category == "overview"),
                discord.SelectOption(label="Economy",          value="Economy",     emoji="💰", default=self.category == "Economy"),
                discord.SelectOption(label="Gambling",         value="Gambling",    emoji="🎰", default=self.category == "Gambling"),
                discord.SelectOption(label="Gaming",           value="Gaming",      emoji="🎮", default=self.category == "Gaming"),
                discord.SelectOption(label="TCG",              value="TCG",         emoji="⚔️", default=self.category == "TCG"),
                discord.SelectOption(label="Social",           value="Social",      emoji="💖", default=self.category == "Social"),
                discord.SelectOption(label="Fishing",          value="Fishing",     emoji="🎣", default=self.category == "Fishing"),
                discord.SelectOption(label="Mining",           value="Mining",      emoji="⛏️", default=self.category == "Mining"),
                discord.SelectOption(label="Farming",          value="Farming",     emoji="🌾", default=self.category == "Farming"),
                discord.SelectOption(label="Pets",             value="Pets",        emoji="🐾", default=self.category == "Pets"),
                discord.SelectOption(label="Board Games",      value="Board Games", emoji="♟️", default=self.category == "Board Games"),
                discord.SelectOption(label="Quests",           value="Quests",      emoji="📜", default=self.category == "Quests"),
                discord.SelectOption(label="Events",           value="Events",      emoji="🎉", default=self.category == "Events"),
                discord.SelectOption(label="Milestones",       value="Milestones",  emoji="⚡", default=self.category == "Milestones"),
            ],
        )
        main_select.callback = self._category_select
        self.add_item(main_select)

    # ── interaction handlers ──────────────────────────────────────────────────

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.viewer_id:
            await interaction.response.send_message("❌ This menu isn't for you!", ephemeral=True)
            return False
        return True

    async def _category_select(self, interaction: discord.Interaction):
        values = interaction.data.get("values", [])
        if not values:
            await interaction.response.defer()
            return
        self.category = values[0]
        self.page     = 0
        self._build_select()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        self._build_select()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _next_page(self, interaction: discord.Interaction):
        all_ach  = list(self.manager.get_achievements_by_category(self.category).items())
        total_pg = max(1, (len(all_ach) + self.PER_PAGE - 1) // self.PER_PAGE)
        self.page = min(total_pg - 1, self.page + 1)
        self._build_select()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class Achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = AchievementManager(data_dir)
        
    
    async def _send_achievement_notification(self, ctx, achievement):
        """Send a V2 achievement unlock notification."""
        cat   = achievement.get("category", "Milestones")
        color = discord.Colour(CATEGORIES.get(cat, {}).get("color", Colors.WARNING))
        text  = (
            f"# 🏆 Achievement Unlocked!\n\n"
            f"{achievement['emoji']} **{achievement['name']}**\n"
            f"-# {achievement['description']}\n\n"
            f"💰 **{achievement['reward']:,}** PsyCoins  •  ⭐ **+{achievement['points']}** pts"
        )
        notif_view = discord.ui.LayoutView(timeout=None)
        notif_view.add_item(discord.ui.Container(
            discord.ui.TextDisplay(content=text),
            accent_colour=color,
        ))
        await ctx.send(view=notif_view)
    
    @commands.command(name="myachievements", aliases=["ach", "achieve", "mych"])
    async def achievements_command(self, ctx, user: discord.User = None):
        """View your achievements — Components V2 browser"""
        target = user or ctx.author
        view   = AchievementView(self.manager, target, ctx.author.id)
        await ctx.send(embed=view.build_embed(), view=view)
    
    @app_commands.command(name="achievements", description="View your achievements")
    async def achievements_slash(self, interaction: discord.Interaction, user: discord.User = None):
        """Slash command for achievements — Components V2 browser"""
        await interaction.response.defer()
        target = user or interaction.user
        view   = AchievementView(self.manager, target, interaction.user.id)
        await interaction.followup.send(embed=view.build_embed(), view=view)
    
    @commands.command(name="achleaderboard", aliases=["achlb", "achtop"])
    async def leaderboard_command(self, ctx, category: str = "points"):
        """View achievement leaderboards"""
        all_users = self.manager.user_achievements
        
        if category.lower() in ["points", "pts", "achievement"]:
            # Sort by achievement points
            sorted_users = sorted(
                all_users.items(),
                key=lambda x: x[1].get("points", 0),
                reverse=True
            )[:10]
            
            embed = EmbedBuilder.create(
                title=f"{Emojis.TROPHY} Top Achievement Hunters",
                description="Users with the most achievement points!",
                color=Colors.WARNING
            )
            
            leaderboard_text = ""
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    points = data.get("points", 0)
                    unlocked = len(data.get("unlocked", []))
                    
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    leaderboard_text += f"{medal} {user.mention} - **{points} pts** ({unlocked} unlocked)\n"
                except:
                    continue
            
            embed.description += f"\n\n{leaderboard_text}"
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Achievements(bot))
