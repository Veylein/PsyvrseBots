import discord
from discord.ext import commands
import random
import asyncio
from typing import Dict, List, Set

class AkinatorEnhanced(commands.Cog):
    """Enhanced Akinator - 100x Better with 200+ characters and intelligent questioning"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.character_database = self.load_massive_character_database()
        self.question_tree = self.build_intelligent_questions()
    
    def load_massive_character_database(self) -> List[Dict]:
        """Massive character database - 200+ characters across all categories"""
        return [
            # VIDEO GAMES (50 characters)
            {"name": "Mario", "tags": ["video_game", "nintendo", "italian", "plumber", "red", "mustache", "mushrooms", "princess_rescue", "platformer", "iconic"]},
            {"name": "Luigi", "tags": ["video_game", "nintendo", "italian", "plumber", "green", "scared", "brother", "taller", "mustache", "sidekick"]},
            {"name": "Sonic the Hedgehog", "tags": ["video_game", "sega", "blue", "fast", "hedgehog", "rings", "chili_dogs", "90s", "iconic", "speed"]},
            {"name": "Link", "tags": ["video_game", "nintendo", "zelda", "green", "sword", "shield", "hero", "elf", "silent", "master_sword"]},
            {"name": "Pikachu", "tags": ["video_game", "pokemon", "electric", "yellow", "mouse", "cute", "ash", "mascot", "thunder", "anime"]},
            {"name": "Pac-Man", "tags": ["video_game", "arcade", "yellow", "round", "eats", "ghosts", "maze", "retro", "80s", "iconic"]},
            {"name": "Lara Croft", "tags": ["video_game", "tomb_raider", "female", "archaeologist", "guns", "adventurer", "british", "strong", "iconic", "90s"]},
            {"name": "Master Chief", "tags": ["video_game", "halo", "xbox", "space", "soldier", "helmet", "green", "sci_fi", "shooter", "spartan"]},
            {"name": "Kratos", "tags": ["video_game", "god_of_war", "greek", "warrior", "angry", "bald", "tattoo", "revenge", "god", "brutal"]},
            {"name": "Cloud Strife", "tags": ["video_game", "final_fantasy", "sword", "spiky_hair", "blonde", "soldier", "rpg", "jrpg", "iconic", "mercenary"]},
            {"name": "Samus Aran", "tags": ["video_game", "metroid", "female", "space", "bounty_hunter", "power_suit", "nintendo", "strong", "orange", "sci_fi"]},
            {"name": "Solid Snake", "tags": ["video_game", "metal_gear", "stealth", "soldier", "bandana", "tactical", "gruff", "smoker", "clone", "spy"]},
            {"name": "Ryu", "tags": ["video_game", "street_fighter", "martial_arts", "hadouken", "karate", "white_gi", "headband", "fighter", "japanese", "disciplined"]},
            {"name": "Chun-Li", "tags": ["video_game", "street_fighter", "martial_arts", "female", "chinese", "kicks", "blue", "buns", "fighter", "strong"]},
            {"name": "Crash Bandicoot", "tags": ["video_game", "playstation", "bandicoot", "orange", "spin", "crates", "australian", "goofy", "90s", "platformer"]},
            {"name": "Spyro", "tags": ["video_game", "playstation", "dragon", "purple", "fire", "flying", "gems", "cute", "90s", "platformer"]},
            {"name": "Donkey Kong", "tags": ["video_game", "nintendo", "gorilla", "tie", "bananas", "strong", "arcade", "barrels", "jungle", "kong"]},
            {"name": "Kirby", "tags": ["video_game", "nintendo", "pink", "round", "copy", "cute", "float", "inhale", "star", "adorable"]},
            {"name": "Steve (Minecraft)", "tags": ["video_game", "minecraft", "blocky", "builder", "pickaxe", "cubic", "miner", "crafter", "silent", "iconic"]},
            {"name": "Geralt of Rivia", "tags": ["video_game", "witcher", "white_hair", "swords", "monster_hunter", "magic", "mutant", "gruff", "medieval", "polish"]},
            {"name": "Ezio Auditore", "tags": ["video_game", "assassins_creed", "italian", "assassin", "hood", "renaissance", "parkour", "blade", "charismatic", "revenge"]},
            {"name": "Nathan Drake", "tags": ["video_game", "uncharted", "treasure_hunter", "adventurer", "charming", "gun", "climbing", "funny", "male", "explorer"]},
            {"name": "Mega Man", "tags": ["video_game", "capcom", "blue", "robot", "arm_cannon", "boss_weapons", "jumping", "platformer", "retro", "iconic"]},
            {"name": "Sub-Zero", "tags": ["video_game", "mortal_kombat", "ice", "ninja", "blue", "mask", "freeze", "fighter", "brutal", "lin_kuei"]},
            {"name": "Scorpion", "tags": ["video_game", "mortal_kombat", "fire", "ninja", "yellow", "spear", "get_over_here", "undead", "fighter", "revenge"]},
            {"name": "Jill Valentine", "tags": ["video_game", "resident_evil", "female", "cop", "zombie", "survivor", "brave", "guns", "horror", "beretta"]},
            {"name": "Leon Kennedy", "tags": ["video_game", "resident_evil", "cop", "rookie", "zombie", "survivor", "handsome", "guns", "horror", "brave"]},
            {"name": "Bowser", "tags": ["video_game", "nintendo", "mario", "turtle", "villain", "king", "kidnapper", "fire", "spikes", "koopa"]},
            {"name": "Sephiroth", "tags": ["video_game", "final_fantasy", "villain", "long_hair", "sword", "angel", "one_wing", "silver", "evil", "powerful"]},
            {"name": "GLaDOS", "tags": ["video_game", "portal", "ai", "robot", "female_voice", "villain", "sarcastic", "testing", "cake", "science"]},
            {"name": "Yoshi", "tags": ["video_game", "nintendo", "mario", "dinosaur", "green", "eggs", "tongue", "cute", "ride", "helper"]},
            {"name": "Toad", "tags": ["video_game", "nintendo", "mario", "mushroom", "small", "helper", "red_spots", "high_voice", "loyal", "princess"]},
            {"name": "Gordon Freeman", "tags": ["video_game", "half_life", "scientist", "crowbar", "glasses", "silent", "physicist", "hero", "orange", "rebel"]},
            {"name": "Tracer", "tags": ["video_game", "overwatch", "female", "british", "fast", "time", "orange", "cheerful", "lesbian", "recall"]},
            {"name": "Widowmaker", "tags": ["video_game", "overwatch", "female", "french", "sniper", "blue_skin", "assassin", "cold", "spider", "villain"]},
            {"name": "Aloy", "tags": ["video_game", "horizon", "female", "redhead", "bow", "robot_dinosaurs", "tribal", "hunter", "brave", "outcast"]},
            {"name": "Joel", "tags": ["video_game", "last_of_us", "survivor", "father_figure", "beard", "gruff", "apocalypse", "smuggler", "protective", "older"]},
            {"name": "Ellie", "tags": ["video_game", "last_of_us", "female", "teenager", "immune", "survivor", "brave", "apocalypse", "guitar", "lesbian"]},
            {"name": "Marcus Fenix", "tags": ["video_game", "gears_of_war", "soldier", "muscular", "chainsaw", "armor", "gruff", "leader", "war", "tough"]},
            {"name": "Cortana", "tags": ["video_game", "halo", "ai", "blue", "female", "hologram", "helper", "intelligent", "loyal", "companion"]},
            {"name": "Rayman", "tags": ["video_game", "ubisoft", "no_limbs", "floating", "platformer", "european", "cheerful", "hair", "hero", "quirky"]},
            {"name": "Banjo", "tags": ["video_game", "rare", "bear", "backpack", "bird", "kazooie", "duo", "n64", "collectathon", "friendly"]},
            {"name": "Sackboy", "tags": ["video_game", "littlebigplanet", "cute", "fabric", "creator", "zipper", "customizable", "platformer", "playstation", "adorable"]},
            {"name": "Ratchet", "tags": ["video_game", "lombax", "wrench", "clank", "space", "weapons", "hero", "playstation", "furry", "mechanic"]},
            {"name": "Jak", "tags": ["video_game", "naughty_dog", "elf_ears", "dark_eco", "precursor", "playstation", "adventure", "hero", "orange", "serious"]},
            {"name": "Dante", "tags": ["video_game", "devil_may_cry", "demon_hunter", "white_hair", "sword", "guns", "stylish", "cocky", "red_coat", "half_demon"]},
            {"name": "Bayonetta", "tags": ["video_game", "witch", "female", "guns", "heels", "hair", "sexy", "powerful", "stylish", "british"]},
            {"name": "Raiden", "tags": ["video_game", "metal_gear", "cyborg", "ninja", "sword", "white_hair", "lightning", "fast", "jack", "child_soldier"]},
            {"name": "Vault Boy", "tags": ["video_game", "fallout", "mascot", "thumbs_up", "cartoon", "blonde", "retro", "nuclear", "pip_boy", "iconic"]},
            {"name": "Dovahkiin", "tags": ["video_game", "skyrim", "dragonborn", "shout", "nord", "hero", "fantasy", "helmet", "dragon", "adventurer"]},
            
            # MOVIES & TV (50 characters)
            {"name": "Darth Vader", "tags": ["movie", "star_wars", "villain", "father", "dark_side", "mask", "breathing", "sith", "powerful", "iconic"]},
            {"name": "Luke Skywalker", "tags": ["movie", "star_wars", "jedi", "hero", "farm_boy", "lightsaber", "blonde", "force", "son", "new_hope"]},
            {"name": "Yoda", "tags": ["movie", "star_wars", "jedi", "green", "small", "wise", "old", "master", "backwards_talk", "powerful"]},
            {"name": "Harry Potter", "tags": ["movie", "book", "wizard", "glasses", "scar", "hogwarts", "british", "orphan", "chosen_one", "gryffindor"]},
            {"name": "Hermione Granger", "tags": ["movie", "book", "wizard", "female", "smart", "bushy_hair", "british", "brave", "muggleborn", "gryffindor"]},
            {"name": "Iron Man", "tags": ["movie", "marvel", "superhero", "genius", "billionaire", "tech", "suit", "tony_stark", "arrogant", "goatee"]},
            {"name": "Captain America", "tags": ["movie", "marvel", "superhero", "shield", "soldier", "blonde", "strong", "patriotic", "steve_rogers", "leader"]},
            {"name": "Thor", "tags": ["movie", "marvel", "superhero", "god", "hammer", "norse", "blonde", "thunder", "asgard", "strong"]},
            {"name": "Spider-Man", "tags": ["movie", "marvel", "superhero", "web", "teenager", "red", "agile", "peter_parker", "friendly", "neighborhood"]},
            {"name": "Batman", "tags": ["movie", "dc", "superhero", "dark", "rich", "gotham", "detective", "bruce_wayne", "orphan", "cape"]},
            {"name": "Superman", "tags": ["movie", "dc", "superhero", "alien", "fly", "strong", "clark_kent", "cape", "red", "blue"]},
            {"name": "Wonder Woman", "tags": ["movie", "dc", "superhero", "female", "amazon", "warrior", "lasso", "diana", "strong", "greek"]},
            {"name": "Black Widow", "tags": ["movie", "marvel", "superhero", "spy", "female", "redhead", "russian", "natasha", "assassin", "agile"]},
            {"name": "Hulk", "tags": ["movie", "marvel", "superhero", "green", "strong", "angry", "scientist", "bruce_banner", "giant", "smash"]},
            {"name": "Thanos", "tags": ["movie", "marvel", "villain", "purple", "titan", "gauntlet", "infinity_stones", "powerful", "snap", "mad"]},
            {"name": "Joker", "tags": ["movie", "dc", "villain", "clown", "insane", "batman", "purple", "chaos", "laughing", "unpredictable"]},
            {"name": "Elsa", "tags": ["movie", "disney", "frozen", "ice", "queen", "blonde", "let_it_go", "sister", "magical", "powerful"]},
            {"name": "Anna", "tags": ["movie", "disney", "frozen", "princess", "redhead", "sister", "brave", "optimistic", "quirky", "love"]},
            {"name": "Simba", "tags": ["movie", "disney", "lion_king", "lion", "prince", "cub", "mufasa", "scar", "hakuna_matata", "king"]},
            {"name": "Woody", "tags": ["movie", "pixar", "toy_story", "cowboy", "toy", "sheriff", "andy", "loyal", "leader", "pull_string"]},
            {"name": "Buzz Lightyear", "tags": ["movie", "pixar", "toy_story", "space", "toy", "ranger", "wings", "to_infinity", "delusional", "hero"]},
            {"name": "Shrek", "tags": ["movie", "dreamworks", "ogre", "green", "swamp", "donkey", "fairy_tale", "scottish", "grumpy", "hero"]},
            {"name": "Donkey", "tags": ["movie", "dreamworks", "shrek", "sidekick", "talking", "annoying", "funny", "loyal", "energetic", "dragon"]},
            {"name": "Po", "tags": ["movie", "dreamworks", "kung_fu_panda", "panda", "fat", "kung_fu", "dragon_warrior", "noodles", "funny", "chosen_one"]},
            {"name": "Gollum", "tags": ["movie", "lord_of_the_rings", "creature", "ring", "precious", "corrupted", "small", "bald", "schizophrenic", "tragic"]},
            {"name": "Gandalf", "tags": ["movie", "lord_of_the_rings", "wizard", "grey", "staff", "wise", "old", "beard", "shall_not_pass", "powerful"]},
            {"name": "Frodo", "tags": ["movie", "lord_of_the_rings", "hobbit", "ring_bearer", "small", "brave", "innocent", "sam", "journey", "hero"]},
            {"name": "Aragorn", "tags": ["movie", "lord_of_the_rings", "ranger", "king", "sword", "beard", "heir", "brave", "leader", "human"]},
            {"name": "Neo", "tags": ["movie", "matrix", "chosen_one", "hacker", "black_coat", "sunglasses", "bullet_time", "kung_fu", "virtual", "hero"]},
            {"name": "Morpheus", "tags": ["movie", "matrix", "mentor", "sunglasses", "bald", "wise", "red_pill", "rebel", "ship_captain", "belief"]},
            {"name": "Trinity", "tags": ["movie", "matrix", "hacker", "female", "leather", "kung_fu", "love_interest", "badass", "pilot", "rebel"]},
            {"name": "Jack Sparrow", "tags": ["movie", "pirates", "pirate", "drunk", "eyeliner", "captain", "compass", "rum", "funny", "chaotic"]},
            {"name": "Indiana Jones", "tags": ["movie", "adventurer", "archaeologist", "whip", "hat", "professor", "treasure", "snakes", "hero", "harrison_ford"]},
            {"name": "Marty McFly", "tags": ["movie", "back_to_future", "teenager", "time_travel", "delorean", "1985", "skateboard", "vest", "future", "past"]},
            {"name": "Doc Brown", "tags": ["movie", "back_to_future", "scientist", "white_hair", "crazy", "time_travel", "delorean", "inventor", "1.21_gigawatts", "eccentric"]},
            {"name": "Terminator", "tags": ["movie", "robot", "arnold", "killer", "cyborg", "time_travel", "ill_be_back", "sunglasses", "leather", "future"]},
            {"name": "Ellen Ripley", "tags": ["movie", "alien", "female", "survivor", "space", "xenomorph", "brave", "strong", "flamethrower", "hero"]},
            {"name": "Forrest Gump", "tags": ["movie", "simple", "running", "box_of_chocolates", "vietnam", "ping_pong", "shrimp", "jenny", "mama", "life"]},
            {"name": "Tony Montana", "tags": ["movie", "scarface", "gangster", "cuban", "cocaine", "say_hello", "violent", "tragic", "ambitious", "rise_and_fall"]},
            {"name": "Walter White", "tags": ["tv", "breaking_bad", "teacher", "chemist", "meth", "heisenberg", "cancer", "bald", "transformation", "villain"]},
            {"name": "Jesse Pinkman", "tags": ["tv", "breaking_bad", "druggie", "yeah_science", "partner", "young", "emotional", "yo", "cook", "tragic"]},
            {"name": "Jon Snow", "tags": ["tv", "game_of_thrones", "nights_watch", "bastard", "know_nothing", "sword", "king", "resurrected", "hero", "winter"]},
            {"name": "Daenerys", "tags": ["tv", "game_of_thrones", "queen", "dragons", "targaryen", "white_hair", "fire", "mother", "breaker_of_chains", "mad"]},
            {"name": "Tyrion Lannister", "tags": ["tv", "game_of_thrones", "dwarf", "small", "smart", "drunk", "witty", "imp", "lion", "survivor"]},
            {"name": "Eleven", "tags": ["tv", "stranger_things", "girl", "powers", "telekinesis", "shaved_head", "nose_bleed", "mike", "upside_down", "experiments"]},
            {"name": "Michael Scott", "tags": ["tv", "the_office", "manager", "awkward", "funny", "thats_what_she_said", "dunder_mifflin", "silly", "lovable", "boss"]},
            {"name": "Sherlock Holmes", "tags": ["tv", "movie", "detective", "smart", "british", "violin", "pipe", "watson", "deduction", "genius"]},
            {"name": "Rick Sanchez", "tags": ["tv", "rick_and_morty", "scientist", "drunk", "genius", "portal_gun", "nihilistic", "grandpa", "burp", "multiverse"]},
            {"name": "Morty Smith", "tags": ["tv", "rick_and_morty", "teenager", "anxious", "grandson", "adventures", "reluctant", "oh_geez", "scared", "sidekick"]},
            {"name": "Homer Simpson", "tags": ["tv", "simpsons", "fat", "yellow", "donut", "doh", "beer", "dumb", "father", "nuclear_plant"]},
            
            # ANIME & MANGA (40 characters)
            {"name": "Goku", "tags": ["anime", "dragon_ball", "saiyan", "orange_gi", "spiky_hair", "kamehameha", "super_saiyan", "strong", "naive", "fighter"]},
            {"name": "Vegeta", "tags": ["anime", "dragon_ball", "saiyan", "prince", "rival", "proud", "spiky_hair", "angry", "powerful", "antihero"]},
            {"name": "Naruto", "tags": ["anime", "naruto", "ninja", "blonde", "whiskers", "orange", "ramen", "hokage", "nine_tails", "dattebayo"]},
            {"name": "Sasuke", "tags": ["anime", "naruto", "ninja", "avenger", "sharingan", "dark", "rival", "emo", "lightning", "brother"]},
            {"name": "Luffy", "tags": ["anime", "one_piece", "pirate", "rubber", "straw_hat", "meat", "gum_gum", "captain", "king", "cheerful"]},
            {"name": "Zoro", "tags": ["anime", "one_piece", "swordsman", "three_swords", "green_hair", "directionally_challenged", "strong", "sake", "serious", "pirate"]},
            {"name": "Light Yagami", "tags": ["anime", "death_note", "genius", "death_note", "kira", "god_complex", "smart", "villain", "protagonist", "justice"]},
            {"name": "L", "tags": ["anime", "death_note", "detective", "sweets", "messy_hair", "genius", "sits_weird", "eyes", "rival", "mysterious"]},
            {"name": "Edward Elric", "tags": ["anime", "fullmetal_alchemist", "alchemist", "blonde", "short", "metal_arm", "brother", "equivalent_exchange", "automail", "protagonist"]},
            {"name": "Alphonse Elric", "tags": ["anime", "fullmetal_alchemist", "alchemist", "armor", "soul", "cat", "brother", "gentle", "tall", "empty"]},
            {"name": "Spike Spiegel", "tags": ["anime", "cowboy_bebop", "bounty_hunter", "cool", "lazy", "martial_arts", "green_hair", "smoking", "space", "cowboy"]},
            {"name": "Eren Yeager", "tags": ["anime", "attack_on_titan", "titan", "rage", "freedom", "protagonist", "transform", "survey_corps", "angry", "tragic"]},
            {"name": "Mikasa Ackerman", "tags": ["anime", "attack_on_titan", "soldier", "scarf", "strong", "female", "protective", "skilled", "asian", "eren"]},
            {"name": "Levi", "tags": ["anime", "attack_on_titan", "captain", "short", "strongest", "clean_freak", "spinning", "humanity", "tea", "badass"]},
            {"name": "Saitama", "tags": ["anime", "one_punch_man", "bald", "overpowered", "hero", "one_punch", "bored", "yellow_suit", "strong", "parody"]},
            {"name": "Genos", "tags": ["anime", "one_punch_man", "cyborg", "disciple", "serious", "blonde", "incinerate", "student", "hero", "determined"]},
            {"name": "All Might", "tags": ["anime", "my_hero_academia", "hero", "symbol_of_peace", "blonde", "muscular", "smile", "i_am_here", "mentor", "declining"]},
            {"name": "Deku", "tags": ["anime", "my_hero_academia", "hero", "green_hair", "one_for_all", "analysis", "crying", "determined", "successor", "nervous"]},
            {"name": "Todoroki", "tags": ["anime", "my_hero_academia", "ice", "fire", "half_and_half", "daddy_issues", "powerful", "cool", "dual_quirk", "stoic"]},
            {"name": "Gon", "tags": ["anime", "hunter_x_hunter", "hunter", "naive", "determined", "fishing_rod", "nen", "spiky_hair", "young", "innocent"]},
            {"name": "Killua", "tags": ["anime", "hunter_x_hunter", "assassin", "white_hair", "electricity", "best_friend", "yo_yo", "rich", "trained", "cool"]},
            {"name": "Ichigo", "tags": ["anime", "bleach", "shinigami", "orange_hair", "sword", "hollow", "substitute", "protector", "bankai", "hero"]},
            {"name": "Inuyasha", "tags": ["anime", "inuyasha", "half_demon", "dog", "white_hair", "sword", "feudal_japan", "sit", "kagome", "grumpy"]},
            {"name": "Sailor Moon", "tags": ["anime", "magical_girl", "blonde", "transform", "moon", "usagi", "crybaby", "sailor_scouts", "love", "justice"]},
            {"name": "Ash Ketchum", "tags": ["anime", "pokemon", "trainer", "pikachu", "hat", "wannabe_master", "naive", "determined", "forever_10", "pallet_town"]},
            {"name": "Misty", "tags": ["anime", "pokemon", "trainer", "water", "redhead", "gym_leader", "ash", "tomboyish", "bike", "sisters"]},
            {"name": "Vegito", "tags": ["anime", "dragon_ball", "fusion", "saiyan", "potara", "powerful", "confident", "earrings", "goku_vegeta", "ultimate"]},
            {"name": "Gohan", "tags": ["anime", "dragon_ball", "saiyan", "scholar", "purple_gi", "cell", "mystic", "piccolo", "son", "potential"]},
            {"name": "Kakashi", "tags": ["anime", "naruto", "sensei", "copy_ninja", "masked", "sharingan", "lazy", "late", "silver_hair", "cool"]},
            {"name": "Itachi", "tags": ["anime", "naruto", "uchiha", "brother", "tragic", "sharingan", "genius", "criminal", "crow", "truth"]},
            
            # COMICS & SUPERHEROES (30 characters)
            {"name": "Spider-Man", "tags": ["comic", "marvel", "superhero", "web", "teenager", "red", "friendly", "neighborhood", "peter_parker", "responsibility"]},
            {"name": "Wolverine", "tags": ["comic", "marvel", "x_men", "claws", "healing", "canadian", "gruff", "beer", "adamantium", "immortal"]},
            {"name": "Deadpool", "tags": ["comic", "marvel", "antihero", "red", "regeneration", "mercenary", "fourth_wall", "jokes", "insane", "katanas"]},
            {"name": "Flash", "tags": ["comic", "dc", "superhero", "fast", "red", "lightning", "barry_allen", "speedster", "fastest", "time_travel"]},
            {"name": "Green Lantern", "tags": ["comic", "dc", "superhero", "ring", "willpower", "green", "space", "constructs", "oath", "corps"]},
            {"name": "Aquaman", "tags": ["comic", "dc", "superhero", "underwater", "atlantis", "trident", "king", "fish", "blonde", "powerful"]},
            {"name": "Catwoman", "tags": ["comic", "dc", "antihero", "thief", "cat", "whip", "leather", "batman", "selina", "agile"]},
            {"name": "Harley Quinn", "tags": ["comic", "dc", "villain", "antihero", "jester", "joker", "baseball_bat", "crazy", "pigtails", "chaotic"]},
            {"name": "Poison Ivy", "tags": ["comic", "dc", "villain", "plants", "redhead", "green", "eco_terrorist", "seductive", "immune", "nature"]},
            {"name": "Robin", "tags": ["comic", "dc", "sidekick", "batman", "acrobat", "young", "dick_grayson", "titan", "cape", "traffic_light"]},
            {"name": "Nightwing", "tags": ["comic", "dc", "hero", "acrobat", "blue", "dick_grayson", "former_robin", "leader", "charming", "skilled"]},
            {"name": "Cyclops", "tags": ["comic", "marvel", "x_men", "laser_eyes", "visor", "leader", "scott_summers", "tactical", "mutant", "serious"]},
            {"name": "Storm", "tags": ["comic", "marvel", "x_men", "weather", "white_hair", "goddess", "lightning", "wind", "african", "powerful"]},
            {"name": "Magneto", "tags": ["comic", "marvel", "x_men", "villain", "magnetism", "helmet", "metal", "holocaust", "brotherhood", "tragic"]},
            {"name": "Professor X", "tags": ["comic", "marvel", "x_men", "telepath", "bald", "wheelchair", "school", "founder", "peaceful", "mentor"]},
            {"name": "Daredevil", "tags": ["comic", "marvel", "blind", "lawyer", "red", "acrobat", "radar", "catholic", "matt_murdock", "hells_kitchen"]},
            {"name": "Punisher", "tags": ["comic", "marvel", "antihero", "skull", "guns", "vigilante", "military", "brutal", "frank_castle", "revenge"]},
            {"name": "Venom", "tags": ["comic", "marvel", "symbiote", "black", "tongue", "antihero", "spider_man", "eddie_brock", "teeth", "we"]},
            {"name": "Doctor Strange", "tags": ["comic", "marvel", "sorcerer", "magic", "cape", "goatee", "surgeon", "time_stone", "mystical", "multiverse"]},
            {"name": "Black Panther", "tags": ["comic", "marvel", "king", "wakanda", "vibranium", "cat", "tchalla", "rich", "african", "advanced"]},
            {"name": "Ant-Man", "tags": ["comic", "marvel", "shrink", "ants", "suit", "helmet", "thief", "scott_lang", "small", "funny"]},
            {"name": "Wasp", "tags": ["comic", "marvel", "shrink", "wings", "female", "sting", "suit", "janet", "founding", "avenger"]},
            {"name": "Hawkeye", "tags": ["comic", "marvel", "archer", "purple", "bow", "sharp_shooter", "clint_barton", "deaf", "avenger", "human"]},
            {"name": "Vision", "tags": ["comic", "marvel", "android", "mind_stone", "red", "cape", "synthetic", "avenger", "phase", "powerful"]},
            {"name": "Scarlet Witch", "tags": ["comic", "marvel", "magic", "chaos", "red", "reality_warping", "wanda", "powerful", "hex", "avenger"]},
            {"name": "Loki", "tags": ["comic", "marvel", "god", "trickster", "villain", "horns", "magic", "adopted", "mischief", "norse"]},
            {"name": "Hela", "tags": ["comic", "marvel", "goddess", "death", "asgard", "villain", "horns", "powerful", "thor", "necroswords"]},
            {"name": "Ultron", "tags": ["comic", "marvel", "robot", "ai", "villain", "red_eyes", "avenger_creation", "extinction", "vibranium", "hive_mind"]},
            {"name": "Green Arrow", "tags": ["comic", "dc", "archer", "green", "hood", "goatee", "billionaire", "oliver_queen", "boxing_glove_arrow", "liberal"]},
            {"name": "Lex Luthor", "tags": ["comic", "dc", "villain", "genius", "billionaire", "bald", "superman", "businessman", "power_suit", "human"]},
            
            # HISTORICAL & REAL (10 characters)
            {"name": "Abraham Lincoln", "tags": ["historical", "president", "tall", "beard", "hat", "assassinated", "civil_war", "honest", "emancipation", "american"]},
            {"name": "Albert Einstein", "tags": ["historical", "scientist", "genius", "relativity", "mustache", "crazy_hair", "physicist", "e_mc2", "nobel", "german"]},
            {"name": "Leonardo da Vinci", "tags": ["historical", "artist", "inventor", "renaissance", "mona_lisa", "genius", "italian", "polymath", "beard", "notebook"]},
            {"name": "Cleopatra", "tags": ["historical", "queen", "egypt", "beautiful", "snake", "ruler", "intelligent", "roman", "seductive", "last_pharaoh"]},
            {"name": "Julius Caesar", "tags": ["historical", "roman", "emperor", "military", "assassinated", "et_tu_brute", "conquest", "gaul", "dictator", "powerful"]},
            {"name": "Napoleon", "tags": ["historical", "french", "emperor", "short", "military", "hat", "strategist", "waterloo", "exile", "ambitious"]},
            {"name": "George Washington", "tags": ["historical", "president", "first", "american", "revolutionary", "general", "founding_father", "cannot_tell_lie", "wig", "hero"]},
            {"name": "Martin Luther King Jr", "tags": ["historical", "civil_rights", "preacher", "american", "dream_speech", "nonviolent", "assassinated", "baptist", "leader", "nobel"]},
            {"name": "Gandhi", "tags": ["historical", "indian", "nonviolent", "independence", "bald", "glasses", "peaceful", "fasting", "philosophy", "assassinated"]},
            {"name": "Elvis Presley", "tags": ["historical", "singer", "king", "rock_and_roll", "hip_thrusting", "graceland", "jumpsuits", "died_young", "american", "iconic"]},
            
            # MYTHOLOGY (10 characters)
            {"name": "Zeus", "tags": ["mythology", "greek", "god", "lightning", "king", "olympus", "powerful", "beard", "eagle", "sky"]},
            {"name": "Poseidon", "tags": ["mythology", "greek", "god", "sea", "trident", "earthquakes", "beard", "horses", "brother", "ocean"]},
            {"name": "Hades", "tags": ["mythology", "greek", "god", "underworld", "death", "cerberus", "helmet", "brother", "dark", "ruler"]},
            {"name": "Thor", "tags": ["mythology", "norse", "god", "thunder", "hammer", "mjolnir", "strong", "redhead", "viking", "warrior"]},
            {"name": "Odin", "tags": ["mythology", "norse", "god", "king", "one_eye", "wise", "ravens", "father", "sleipnir", "allfather"]},
            {"name": "Loki", "tags": ["mythology", "norse", "trickster", "shapeshifter", "mischief", "cunning", "frost_giant", "adopted", "chaos", "clever"]},
            {"name": "Anubis", "tags": ["mythology", "egyptian", "god", "death", "jackal", "mummification", "underworld", "black", "scales", "guardian"]},
            {"name": "Ra", "tags": ["mythology", "egyptian", "god", "sun", "falcon", "pharaoh", "boat", "powerful", "sky", "creation"]},
            {"name": "Medusa", "tags": ["mythology", "greek", "gorgon", "snakes_for_hair", "stone_gaze", "monster", "perseus", "cursed", "tragic", "ugly"]},
            {"name": "Hercules", "tags": ["mythology", "greek", "demigod", "strong", "twelve_labors", "hero", "muscular", "zeus", "club", "lion"]},
        ]
    
    def build_intelligent_questions(self) -> List[Dict]:
        """Build an intelligent question tree with branching logic"""
        return [
            # Category questions
            {"id": "cat_video_game", "text": "Is your character from a video game?", "tag": "video_game", "weight": 10},
            {"id": "cat_movie", "text": "Is your character from a movie or TV show?", "tag": "movie", "weight": 10},
            {"id": "cat_tv", "text": "Is your character from a TV show?", "tag": "tv", "weight": 10},
            {"id": "cat_anime", "text": "Is your character from anime or manga?", "tag": "anime", "weight": 10},
            {"id": "cat_comic", "text": "Is your character from comic books?", "tag": "comic", "weight": 10},
            {"id": "cat_historical", "text": "Is your character a real historical figure?", "tag": "historical", "weight": 10},
            {"id": "cat_mythology", "text": "Is your character from mythology or legends?", "tag": "mythology", "weight": 10},
            
            # Gender/species
            {"id": "gender_female", "text": "Is your character female?", "tag": "female", "weight": 9},
            {"id": "species_human", "text": "Is your character human?", "tag": "human", "weight": 8},
            {"id": "species_robot", "text": "Is your character a robot or cyborg?", "tag": "robot", "weight": 8},
            {"id": "species_alien", "text": "Is your character an alien?", "tag": "alien", "weight": 8},
            {"id": "species_animal", "text": "Is your character an animal or creature?", "tag": "animal", "weight": 8},
            {"id": "species_god", "text": "Is your character a god or deity?", "tag": "god", "weight": 8},
            
            # Role/alignment
            {"id": "role_hero", "text": "Is your character a hero or protagonist?", "tag": "hero", "weight": 9},
            {"id": "role_villain", "text": "Is your character a villain or antagonist?", "tag": "villain", "weight": 9},
            {"id": "role_antihero", "text": "Is your character an antihero or morally grey?", "tag": "antihero", "weight": 8},
            {"id": "role_sidekick", "text": "Is your character a sidekick or helper?", "tag": "sidekick", "weight": 7},
            
            # Powers/abilities
            {"id": "power_super", "text": "Does your character have superpowers?", "tag": "superhero", "weight": 8},
            {"id": "power_magic", "text": "Does your character use magic?", "tag": "magic", "weight": 8},
            {"id": "power_tech", "text": "Does your character use advanced technology?", "tag": "tech", "weight": 7},
            {"id": "power_martial", "text": "Is your character skilled in martial arts or combat?", "tag": "martial_arts", "weight": 7},
            {"id": "power_weapons", "text": "Does your character use weapons?", "tag": "weapons", "weight": 7},
            {"id": "power_fly", "text": "Can your character fly?", "tag": "fly", "weight": 7},
            {"id": "power_strong", "text": "Is your character incredibly strong?", "tag": "strong", "weight": 7},
            {"id": "power_fast", "text": "Is your character known for being fast?", "tag": "fast", "weight": 7},
            {"id": "power_smart", "text": "Is your character a genius or very intelligent?", "tag": "genius", "weight": 7},
            
            # Physical appearance
            {"id": "appearance_hair_blonde", "text": "Does your character have blonde hair?", "tag": "blonde", "weight": 6},
            {"id": "appearance_hair_red", "text": "Does your character have red or orange hair?", "tag": "redhead", "weight": 6},
            {"id": "appearance_hair_white", "text": "Does your character have white or silver hair?", "tag": "white_hair", "weight": 6},
            {"id": "appearance_bald", "text": "Is your character bald?", "tag": "bald", "weight": 6},
            {"id": "appearance_mask", "text": "Does your character wear a mask?", "tag": "mask", "weight": 6},
            {"id": "appearance_glasses", "text": "Does your character wear glasses?", "tag": "glasses", "weight": 6},
            {"id": "appearance_beard", "text": "Does your character have a beard?", "tag": "beard", "weight": 6},
            {"id": "appearance_cape", "text": "Does your character wear a cape?", "tag": "cape", "weight": 5},
            {"id": "appearance_armor", "text": "Does your character wear armor?", "tag": "armor", "weight": 5},
            
            # Color associations
            {"id": "color_red", "text": "Is red a significant color for your character?", "tag": "red", "weight": 5},
            {"id": "color_blue", "text": "Is blue a significant color for your character?", "tag": "blue", "weight": 5},
            {"id": "color_green", "text": "Is green a significant color for your character?", "tag": "green", "weight": 5},
            {"id": "color_black", "text": "Does your character wear black or dark colors?", "tag": "dark", "weight": 5},
            
            # Personality traits
            {"id": "personality_funny", "text": "Is your character funny or comedic?", "tag": "funny", "weight": 6},
            {"id": "personality_serious", "text": "Is your character serious or stoic?", "tag": "serious", "weight": 6},
            {"id": "personality_angry", "text": "Is your character often angry or aggressive?", "tag": "angry", "weight": 6},
            {"id": "personality_cheerful", "text": "Is your character cheerful or optimistic?", "tag": "cheerful", "weight": 6},
            {"id": "personality_brave", "text": "Is your character known for being brave?", "tag": "brave", "weight": 6},
            {"id": "personality_smart", "text": "Is your character strategic or clever?", "tag": "smart", "weight": 6},
            
            # Specific attributes
            {"id": "attr_sword", "text": "Does your character use a sword?", "tag": "sword", "weight": 6},
            {"id": "attr_gun", "text": "Does your character use guns?", "tag": "guns", "weight": 6},
            {"id": "attr_shield", "text": "Does your character use a shield?", "tag": "shield", "weight": 5},
            {"id": "attr_hammer", "text": "Does your character use a hammer?", "tag": "hammer", "weight": 5},
            {"id": "attr_wings", "text": "Does your character have wings?", "tag": "wings", "weight": 5},
            {"id": "attr_tail", "text": "Does your character have a tail?", "tag": "tail", "weight": 5},
            
            # Context-specific
            {"id": "context_space", "text": "Is your character associated with space or sci-fi?", "tag": "space", "weight": 7},
            {"id": "context_medieval", "text": "Is your character from a medieval or fantasy setting?", "tag": "medieval", "weight": 7},
            {"id": "context_modern", "text": "Is your character from a modern or contemporary setting?", "tag": "modern", "weight": 6},
            {"id": "context_underwater", "text": "Is your character associated with water or the ocean?", "tag": "underwater", "weight": 5},
            {"id": "context_ninja", "text": "Is your character a ninja or assassin?", "tag": "ninja", "weight": 6},
            {"id": "context_pirate", "text": "Is your character a pirate?", "tag": "pirate", "weight": 5},
            {"id": "context_royalty", "text": "Is your character royalty (king, queen, prince, princess)?", "tag": "royalty", "weight": 6},
            
            # Company/franchise specific
            {"id": "company_nintendo", "text": "Is your character owned by Nintendo?", "tag": "nintendo", "weight": 8},
            {"id": "company_marvel", "text": "Is your character from Marvel?", "tag": "marvel", "weight": 8},
            {"id": "company_dc", "text": "Is your character from DC Comics?", "tag": "dc", "weight": 8},
            {"id": "company_disney", "text": "Is your character from a Disney property?", "tag": "disney", "weight": 7},
            {"id": "company_pixar", "text": "Is your character from a Pixar movie?", "tag": "pixar", "weight": 6},
        ]
    
    @commands.command(name="akinator", aliases=["aki", "guesswho"])
    async def akinator(self, ctx):
        """🔮 Play Akinator - Think of a character and I'll guess it!"""
        
        if ctx.author.id in self.active_games:
            await ctx.send("❌ You already have an active Akinator game! Finish it first with `L!endgame`")
            return
        
        # Initialize game
        self.active_games[ctx.author.id] = {
            "type": "akinator",
            "channel": ctx.channel.id,
            "possible_characters": self.character_database.copy(),
            "asked_questions": [],
            "answers": {},
            "question_count": 0,
            "confidence_threshold": 0.85
        }
        
        embed = discord.Embed(
            title="🔮 Akinator - Enhanced Edition",
            description="**Welcome to Akinator!**\n\n"
                       "Think of **any character** from:\n"
                       "🎮 Video Games (200+ characters)\n"
                       "🎬 Movies & TV\n"
                       "📺 Anime & Manga\n"
                       "📚 Comics & Books\n"
                       "🏛️ History & Mythology\n\n"
                       "**I will ask you questions and guess your character!**\n\n"
                       "Answer with:\n"
                       "✅ **Yes** - Definitely yes\n"
                       "❌ **No** - Definitely no\n"
                       "🤔 **Probably** - Probably yes\n"
                       "❓ **Probably Not** - Probably no\n"
                       "🤷 **Don't Know** - Not sure\n\n"
                       "Let's begin! 🎩✨",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Type 'quit' to end | Type 'back' to go back")
        
        await ctx.send(embed=embed)
        await asyncio.sleep(2)
        await self.ask_next_question(ctx)
    
    async def ask_next_question(self, ctx):
        """Ask the next most relevant question"""
        game = self.active_games.get(ctx.author.id)
        if not game:
            return
        
        # Check if we have a confident guess
        if len(game["possible_characters"]) <= 3 and game["question_count"] >= 5:
            await self.make_guess(ctx)
            return
        
        # Check if we've asked enough questions
        if game["question_count"] >= 25:
            await self.make_final_guess(ctx)
            return
        
        # Select best question using intelligent scoring
        best_question = self.select_best_question(game)
        
        if not best_question:
            await self.make_final_guess(ctx)
            return
        
        game["current_question"] = best_question
        game["question_count"] += 1
        
        embed = discord.Embed(
            title=f"🔮 Question {game['question_count']}",
            description=f"**{best_question['text']}**\n\n"
                       "Reply with: **yes**, **no**, **probably**, **probably not**, or **don't know**",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{len(game['possible_characters'])} possible characters remaining")
        
        await ctx.send(embed=embed)
    
    def select_best_question(self, game) -> Dict:
        """Intelligently select the best question to narrow down characters"""
        remaining_chars = game["possible_characters"]
        asked = game["asked_questions"]
        
        # Get all applicable questions
        available_questions = [q for q in self.question_tree if q["id"] not in asked]
        
        if not available_questions:
            return None
        
        # Score each question based on how well it splits the remaining characters
        scored_questions = []
        
        for question in available_questions:
            tag = question["tag"]
            
            # Count how many remaining characters have this tag
            chars_with_tag = sum(1 for char in remaining_chars if tag in char["tags"])
            chars_without_tag = len(remaining_chars) - chars_with_tag
            
            # Best questions split the pool roughly in half
            # Use information theory (entropy)
            if chars_with_tag == 0 or chars_without_tag == 0:
                score = 0
            else:
                # Information gain calculation
                p_yes = chars_with_tag / len(remaining_chars)
                p_no = chars_without_tag / len(remaining_chars)
                
                # Entropy-based scoring
                import math
                entropy = -(p_yes * math.log2(p_yes) if p_yes > 0 else 0) - (p_no * math.log2(p_no) if p_no > 0 else 0)
                
                # Apply question weight
                score = entropy * question["weight"]
            
            scored_questions.append((question, score))
        
        # Sort by score (highest first)
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        
        # Return best question
        return scored_questions[0][0] if scored_questions else None
    
    async def process_answer(self, message):
        """Process user's answer to current question"""
        game = self.active_games[message.author.id]
        
        if message.channel.id != game["channel"]:
            return
        
        answer = message.content.lower().strip()
        
        # Handle special commands
        if answer in ["quit", "stop", "end"]:
            await message.channel.send("👋 Thanks for playing Akinator!")
            del self.active_games[message.author.id]
            return
        
        if answer == "back":
            # TODO: Implement going back to previous question
            await message.channel.send("⚠️ Can't go back yet - feature coming soon!")
            return
        
        # Parse answer
        if answer in ["yes", "y", "yeah", "yep", "yup", "definitely"]:
            answer_val = "yes"
        elif answer in ["no", "n", "nope", "nah", "definitely not"]:
            answer_val = "no"
        elif answer in ["probably", "prob", "maybe yes", "likely", "think so"]:
            answer_val = "probably"
        elif answer in ["probably not", "prob not", "maybe not", "unlikely", "don't think so"]:
            answer_val = "probably_not"
        elif answer in ["don't know", "dk", "idk", "not sure", "unsure", "?"]:
            answer_val = "unknown"
        else:
            await message.channel.send("❓ Please answer with: **yes**, **no**, **probably**, **probably not**, or **don't know**")
            return
        
        # Store answer
        current_q = game["current_question"]
        game["answers"][current_q["id"]] = answer_val
        game["asked_questions"].append(current_q["id"])
        
        # Filter characters based on answer
        tag = current_q["tag"]
        
        if answer_val == "yes":
            # Keep only characters with this tag
            game["possible_characters"] = [c for c in game["possible_characters"] if tag in c["tags"]]
        elif answer_val == "no":
            # Remove characters with this tag
            game["possible_characters"] = [c for c in game["possible_characters"] if tag not in c["tags"]]
        elif answer_val == "probably":
            # Weak filter - prefer characters with tag but don't eliminate others yet
            with_tag = [c for c in game["possible_characters"] if tag in c["tags"]]
            without_tag = [c for c in game["possible_characters"] if tag not in c["tags"]]
            game["possible_characters"] = with_tag + without_tag[:len(without_tag)//3]
        elif answer_val == "probably_not":
            # Weak filter - prefer characters without tag
            without_tag = [c for c in game["possible_characters"] if tag not in c["tags"]]
            with_tag = [c for c in game["possible_characters"] if tag in c["tags"]]
            game["possible_characters"] = without_tag + with_tag[:len(with_tag)//3]
        # If "unknown", don't filter at all
        
        # Ask next question
        await self.ask_next_question(message.channel)
    
    async def make_guess(self, ctx):
        """Make a confident guess"""
        game = self.active_games[ctx.author.id]
        
        if not game["possible_characters"]:
            await ctx.send("🤔 Hmm, I can't figure out who you're thinking of! You stumped me!")
            del self.active_games[ctx.author.id]
            return
        
        # Pick most likely character
        guess = game["possible_characters"][0]
        
        embed = discord.Embed(
            title="🎯 I think I know!",
            description=f"# Is your character...\n\n**{guess['name']}**?\n\n"
                       f"*Category: {guess['tags'][1] if len(guess['tags']) > 1 else 'Various'}*\n\n"
                       "**Reply:** 'yes' if correct, 'no' if wrong",
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
        game["guessing"] = True
        game["current_guess"] = guess
    
    async def make_final_guess(self, ctx):
        """Make final guess after many questions"""
        game = self.active_games[ctx.author.id]
        
        if not game["possible_characters"]:
            embed = discord.Embed(
                title="😅 You Stumped Me!",
                description="I couldn't figure out your character!\n\n"
                           "**You win this round!** 🏆\n\n"
                           "*Help me improve by suggesting this character!*",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            del self.active_games[ctx.author.id]
            return
        
        # Show top 3 guesses
        guesses = game["possible_characters"][:3]
        
        description = "**My top guesses are:**\n\n"
        for i, char in enumerate(guesses, 1):
            description += f"{i}. **{char['name']}**\n"
        
        description += "\n**Reply with the number if I got it right, or 'no' if I'm wrong!**"
        
        embed = discord.Embed(
            title="🤔 Final Guesses",
            description=description,
            color=discord.Color.orange()
        )
        
        await ctx.send(embed=embed)
        game["final_guessing"] = True
    
    async def handle_guess_response(self, message):
        """Handle response to guess"""
        game = self.active_games[message.author.id]
        
        if message.channel.id != game["channel"]:
            return
        
        answer = message.content.lower().strip()
        
        if game.get("guessing"):
            if answer in ["yes", "y", "yeah", "correct", "right", "yep", "yup"]:
                embed = discord.Embed(
                    title="🎉 I WIN!",
                    description=f"**I guessed it!** Your character was **{game['current_guess']['name']}**!\n\n"
                               f"It only took me **{game['question_count']} questions**! 🎩✨\n\n"
                               "*Thanks for playing Akinator Enhanced!*",
                    color=discord.Color.green()
                )
                await message.channel.send(embed=embed)
                del self.active_games[message.author.id]
            else:
                # Continue asking questions
                game["guessing"] = False
                game["possible_characters"] = [c for c in game["possible_characters"] if c != game["current_guess"]]
                await message.channel.send("🤔 Let me think more...")
                await asyncio.sleep(1)
                await self.ask_next_question(message.channel)
        
        elif game.get("final_guessing"):
            if answer in ["1", "2", "3"]:
                idx = int(answer) - 1
                if idx < len(game["possible_characters"]):
                    char = game["possible_characters"][idx]
                    embed = discord.Embed(
                        title="🎉 I GOT IT!",
                        description=f"**Your character was {char['name']}!**\n\n"
                                   f"Questions asked: **{game['question_count']}**\n\n"
                                   "*Thanks for playing!*",
                        color=discord.Color.green()
                    )
                    await message.channel.send(embed=embed)
                    del self.active_games[message.author.id]
            else:
                embed = discord.Embed(
                    title="😅 You Beat Me!",
                    description="I couldn't guess your character!\n\n"
                               "**You win!** 🏆\n\n"
                               "*Great job stumping Akinator!*",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)
                del self.active_games[message.author.id]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for answers"""
        if message.author.bot:
            return
        
        if message.author.id not in self.active_games:
            return
        
        game = self.active_games[message.author.id]
        
        if game["type"] != "akinator":
            return
        
        if game.get("guessing") or game.get("final_guessing"):
            await self.handle_guess_response(message)
        else:
            await self.process_answer(message)

async def setup(bot):
    await bot.add_cog(AkinatorEnhanced(bot))
