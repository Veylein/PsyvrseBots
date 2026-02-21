"""
Akinator – Components V2 rewrite.
Think of any character and the bot will guess it through binary questions.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

# ──────────────────────────────────────────────────────────────────────────────
# Static data (character database + questions)
# ──────────────────────────────────────────────────────────────────────────────

def _build_characters() -> List[Dict]:
    return [
        # VIDEO GAMES
        {"name": "Mario",             "tags": ["video_game","nintendo","italian","plumber","red","mustache","mushrooms","princess_rescue","platformer","iconic"]},
        {"name": "Luigi",             "tags": ["video_game","nintendo","italian","plumber","green","scared","brother","taller","mustache","sidekick"]},
        {"name": "Sonic the Hedgehog","tags": ["video_game","sega","blue","fast","hedgehog","rings","chili_dogs","90s","iconic","speed"]},
        {"name": "Link",              "tags": ["video_game","nintendo","zelda","green","sword","shield","hero","elf","silent","master_sword"]},
        {"name": "Pikachu",           "tags": ["video_game","pokemon","electric","yellow","mouse","cute","ash","mascot","thunder","anime"]},
        {"name": "Pac-Man",           "tags": ["video_game","arcade","yellow","round","eats","ghosts","maze","retro","80s","iconic"]},
        {"name": "Lara Croft",        "tags": ["video_game","tomb_raider","female","archaeologist","guns","adventurer","british","strong","iconic","90s"]},
        {"name": "Master Chief",      "tags": ["video_game","halo","xbox","space","soldier","helmet","green","sci_fi","shooter","spartan"]},
        {"name": "Kratos",            "tags": ["video_game","god_of_war","greek","warrior","angry","bald","tattoo","revenge","god","brutal"]},
        {"name": "Cloud Strife",      "tags": ["video_game","final_fantasy","sword","spiky_hair","blonde","soldier","rpg","jrpg","iconic","mercenary"]},
        {"name": "Samus Aran",        "tags": ["video_game","metroid","female","space","bounty_hunter","power_suit","nintendo","strong","orange","sci_fi"]},
        {"name": "Solid Snake",       "tags": ["video_game","metal_gear","stealth","soldier","bandana","tactical","gruff","smoker","clone","spy"]},
        {"name": "Ryu",               "tags": ["video_game","street_fighter","martial_arts","hadouken","karate","white_gi","headband","fighter","japanese","disciplined"]},
        {"name": "Chun-Li",           "tags": ["video_game","street_fighter","martial_arts","female","chinese","kicks","blue","buns","fighter","strong"]},
        {"name": "Crash Bandicoot",   "tags": ["video_game","playstation","bandicoot","orange","spin","crates","australian","goofy","90s","platformer"]},
        {"name": "Spyro",             "tags": ["video_game","playstation","dragon","purple","fire","flying","gems","cute","90s","platformer"]},
        {"name": "Donkey Kong",       "tags": ["video_game","nintendo","gorilla","tie","bananas","strong","arcade","barrels","jungle","kong"]},
        {"name": "Kirby",             "tags": ["video_game","nintendo","pink","round","copy","cute","float","inhale","star","adorable"]},
        {"name": "Steve (Minecraft)", "tags": ["video_game","minecraft","blocky","builder","pickaxe","cubic","miner","crafter","silent","iconic"]},
        {"name": "Geralt of Rivia",   "tags": ["video_game","witcher","white_hair","swords","monster_hunter","magic","mutant","gruff","medieval","polish"]},
        {"name": "Ezio Auditore",     "tags": ["video_game","assassins_creed","italian","assassin","hood","renaissance","parkour","blade","charismatic","revenge"]},
        {"name": "Nathan Drake",      "tags": ["video_game","uncharted","treasure_hunter","adventurer","charming","gun","climbing","funny","male","explorer"]},
        {"name": "Mega Man",          "tags": ["video_game","capcom","blue","robot","arm_cannon","boss_weapons","jumping","platformer","retro","iconic"]},
        {"name": "Sub-Zero",          "tags": ["video_game","mortal_kombat","ice","ninja","blue","mask","freeze","fighter","brutal","lin_kuei"]},
        {"name": "Scorpion",          "tags": ["video_game","mortal_kombat","fire","ninja","yellow","spear","get_over_here","undead","fighter","revenge"]},
        {"name": "Jill Valentine",    "tags": ["video_game","resident_evil","female","cop","zombie","survivor","brave","guns","horror","beretta"]},
        {"name": "Leon Kennedy",      "tags": ["video_game","resident_evil","cop","rookie","zombie","survivor","handsome","guns","horror","brave"]},
        {"name": "Bowser",            "tags": ["video_game","nintendo","mario","turtle","villain","king","kidnapper","fire","spikes","koopa"]},
        {"name": "Sephiroth",         "tags": ["video_game","final_fantasy","villain","long_hair","sword","angel","one_wing","silver","evil","powerful"]},
        {"name": "GLaDOS",            "tags": ["video_game","portal","ai","robot","female_voice","villain","sarcastic","testing","cake","science"]},
        {"name": "Yoshi",             "tags": ["video_game","nintendo","mario","dinosaur","green","eggs","tongue","cute","ride","helper"]},
        {"name": "Gordon Freeman",    "tags": ["video_game","half_life","scientist","crowbar","glasses","silent","physicist","hero","orange","rebel"]},
        {"name": "Tracer",            "tags": ["video_game","overwatch","female","british","fast","time","orange","cheerful","lesbian","recall"]},
        {"name": "Widowmaker",        "tags": ["video_game","overwatch","female","french","sniper","blue","assassin","cold","spider","villain"]},
        {"name": "Aloy",              "tags": ["video_game","horizon","female","redhead","bow","robot_dinosaurs","tribal","hunter","brave","outcast"]},
        {"name": "Joel",              "tags": ["video_game","last_of_us","survivor","father_figure","beard","gruff","apocalypse","smuggler","protective","older"]},
        {"name": "Ellie",             "tags": ["video_game","last_of_us","female","teenager","immune","survivor","brave","apocalypse","guitar","lesbian"]},
        {"name": "Cortana",           "tags": ["video_game","halo","ai","blue","female","hologram","helper","intelligent","loyal","companion"]},
        {"name": "Dante",             "tags": ["video_game","devil_may_cry","demon_hunter","white_hair","sword","guns","stylish","cocky","red_coat","half_demon"]},
        {"name": "Bayonetta",         "tags": ["video_game","witch","female","guns","heels","hair","sexy","powerful","stylish","british"]},
        {"name": "Dovahkiin",         "tags": ["video_game","skyrim","dragonborn","shout","nord","hero","fantasy","helmet","dragon","adventurer"]},
        {"name": "Vault Boy",         "tags": ["video_game","fallout","mascot","thumbs_up","cartoon","blonde","retro","nuclear","pip_boy","iconic"]},

        # MOVIES & TV
        {"name": "Darth Vader",       "tags": ["movie","star_wars","villain","father","dark_side","mask","breathing","sith","powerful","iconic"]},
        {"name": "Luke Skywalker",    "tags": ["movie","star_wars","jedi","hero","farm_boy","lightsaber","blonde","force","son","new_hope"]},
        {"name": "Yoda",              "tags": ["movie","star_wars","jedi","green","small","wise","old","master","backwards_talk","powerful"]},
        {"name": "Harry Potter",      "tags": ["movie","book","wizard","glasses","scar","hogwarts","british","orphan","chosen_one","gryffindor"]},
        {"name": "Hermione Granger",  "tags": ["movie","book","wizard","female","smart","bushy_hair","british","brave","muggleborn","gryffindor"]},
        {"name": "Iron Man",          "tags": ["movie","marvel","superhero","genius","billionaire","tech","suit","tony_stark","arrogant","goatee"]},
        {"name": "Captain America",   "tags": ["movie","marvel","superhero","shield","soldier","blonde","strong","patriotic","steve_rogers","leader"]},
        {"name": "Thor",              "tags": ["movie","marvel","superhero","god","hammer","norse","blonde","thunder","asgard","strong"]},
        {"name": "Spider-Man",        "tags": ["movie","marvel","superhero","web","teenager","red","agile","peter_parker","friendly","neighborhood"]},
        {"name": "Batman",            "tags": ["movie","dc","superhero","dark","rich","gotham","detective","bruce_wayne","orphan","cape"]},
        {"name": "Superman",          "tags": ["movie","dc","superhero","alien","fly","strong","clark_kent","cape","red","blue"]},
        {"name": "Wonder Woman",      "tags": ["movie","dc","superhero","female","amazon","warrior","lasso","diana","strong","greek"]},
        {"name": "Black Widow",       "tags": ["movie","marvel","superhero","spy","female","redhead","russian","natasha","assassin","agile"]},
        {"name": "Hulk",              "tags": ["movie","marvel","superhero","green","strong","angry","scientist","bruce_banner","giant","smash"]},
        {"name": "Thanos",            "tags": ["movie","marvel","villain","purple","titan","gauntlet","infinity_stones","powerful","snap","mad"]},
        {"name": "Joker",             "tags": ["movie","dc","villain","clown","insane","batman","purple","chaos","laughing","unpredictable"]},
        {"name": "Elsa",              "tags": ["movie","disney","frozen","ice","queen","blonde","let_it_go","sister","magical","powerful"]},
        {"name": "Anna",              "tags": ["movie","disney","frozen","princess","redhead","sister","brave","optimistic","quirky","love"]},
        {"name": "Simba",             "tags": ["movie","disney","lion_king","lion","prince","cub","mufasa","scar","hakuna_matata","king"]},
        {"name": "Woody",             "tags": ["movie","pixar","toy_story","cowboy","toy","sheriff","andy","loyal","leader","pull_string"]},
        {"name": "Buzz Lightyear",    "tags": ["movie","pixar","toy_story","space","toy","ranger","wings","to_infinity","delusional","hero"]},
        {"name": "Shrek",             "tags": ["movie","dreamworks","ogre","green","swamp","donkey","fairy_tale","scottish","grumpy","hero"]},
        {"name": "Po",                "tags": ["movie","dreamworks","kung_fu_panda","panda","fat","kung_fu","dragon_warrior","noodles","funny","chosen_one"]},
        {"name": "Gollum",            "tags": ["movie","lord_of_the_rings","creature","ring","precious","corrupted","small","bald","schizophrenic","tragic"]},
        {"name": "Gandalf",           "tags": ["movie","lord_of_the_rings","wizard","grey","staff","wise","old","beard","shall_not_pass","powerful"]},
        {"name": "Frodo",             "tags": ["movie","lord_of_the_rings","hobbit","ring_bearer","small","brave","innocent","sam","journey","hero"]},
        {"name": "Aragorn",           "tags": ["movie","lord_of_the_rings","ranger","king","sword","beard","heir","brave","leader","human"]},
        {"name": "Neo",               "tags": ["movie","matrix","chosen_one","hacker","black_coat","sunglasses","bullet_time","kung_fu","virtual","hero"]},
        {"name": "Morpheus",          "tags": ["movie","matrix","mentor","sunglasses","bald","wise","red_pill","rebel","ship_captain","belief"]},
        {"name": "Jack Sparrow",      "tags": ["movie","pirates","pirate","drunk","eyeliner","captain","compass","rum","funny","chaotic"]},
        {"name": "Indiana Jones",     "tags": ["movie","adventurer","archaeologist","whip","hat","professor","treasure","snakes","hero","harrison_ford"]},
        {"name": "Marty McFly",       "tags": ["movie","back_to_future","teenager","time_travel","delorean","1985","skateboard","vest","future","past"]},
        {"name": "Terminator",        "tags": ["movie","robot","arnold","killer","cyborg","time_travel","ill_be_back","sunglasses","leather","future"]},
        {"name": "Forrest Gump",      "tags": ["movie","simple","running","box_of_chocolates","vietnam","ping_pong","shrimp","jenny","mama","life"]},
        {"name": "Walter White",      "tags": ["tv","breaking_bad","teacher","chemist","meth","heisenberg","cancer","bald","transformation","villain"]},
        {"name": "Jesse Pinkman",     "tags": ["tv","breaking_bad","druggie","yeah_science","partner","young","emotional","yo","cook","tragic"]},
        {"name": "Jon Snow",          "tags": ["tv","game_of_thrones","nights_watch","bastard","know_nothing","sword","king","resurrected","hero","winter"]},
        {"name": "Daenerys",          "tags": ["tv","game_of_thrones","queen","dragons","targaryen","white_hair","fire","mother","breaker_of_chains","mad"]},
        {"name": "Tyrion Lannister",  "tags": ["tv","game_of_thrones","dwarf","small","smart","drunk","witty","imp","lion","survivor"]},
        {"name": "Eleven",            "tags": ["tv","stranger_things","girl","powers","telekinesis","shaved_head","nose_bleed","mike","upside_down","experiments"]},
        {"name": "Michael Scott",     "tags": ["tv","the_office","manager","awkward","funny","thats_what_she_said","dunder_mifflin","silly","lovable","boss"]},
        {"name": "Sherlock Holmes",   "tags": ["tv","movie","detective","smart","british","violin","pipe","watson","deduction","genius"]},
        {"name": "Rick Sanchez",      "tags": ["tv","rick_and_morty","scientist","drunk","genius","portal_gun","nihilistic","grandpa","burp","multiverse"]},
        {"name": "Morty Smith",       "tags": ["tv","rick_and_morty","teenager","anxious","grandson","adventures","reluctant","oh_geez","scared","sidekick"]},
        {"name": "Homer Simpson",     "tags": ["tv","simpsons","fat","yellow","donut","doh","beer","dumb","father","nuclear_plant"]},

        # ANIME & MANGA
        {"name": "Goku",              "tags": ["anime","dragon_ball","saiyan","orange_gi","spiky_hair","kamehameha","super_saiyan","strong","naive","fighter"]},
        {"name": "Vegeta",            "tags": ["anime","dragon_ball","saiyan","prince","rival","proud","spiky_hair","angry","powerful","antihero"]},
        {"name": "Naruto",            "tags": ["anime","naruto","ninja","blonde","whiskers","orange","ramen","hokage","nine_tails","dattebayo"]},
        {"name": "Sasuke",            "tags": ["anime","naruto","ninja","avenger","sharingan","dark","rival","emo","lightning","brother"]},
        {"name": "Luffy",             "tags": ["anime","one_piece","pirate","rubber","straw_hat","meat","gum_gum","captain","king","cheerful"]},
        {"name": "Zoro",              "tags": ["anime","one_piece","swordsman","three_swords","green_hair","strong","sake","serious","pirate","directionally_challenged"]},
        {"name": "Light Yagami",      "tags": ["anime","death_note","genius","death_note","kira","god_complex","smart","villain","protagonist","justice"]},
        {"name": "L",                 "tags": ["anime","death_note","detective","sweets","messy_hair","genius","sits_weird","eyes","rival","mysterious"]},
        {"name": "Edward Elric",      "tags": ["anime","fullmetal_alchemist","alchemist","blonde","short","metal_arm","brother","equivalent_exchange","automail","protagonist"]},
        {"name": "Spike Spiegel",     "tags": ["anime","cowboy_bebop","bounty_hunter","cool","lazy","martial_arts","green_hair","smoking","space","cowboy"]},
        {"name": "Eren Yeager",       "tags": ["anime","attack_on_titan","titan","rage","freedom","protagonist","transform","survey_corps","angry","tragic"]},
        {"name": "Mikasa Ackerman",   "tags": ["anime","attack_on_titan","soldier","scarf","strong","female","protective","skilled","asian","eren"]},
        {"name": "Levi",              "tags": ["anime","attack_on_titan","captain","short","strongest","clean_freak","spinning","humanity","tea","badass"]},
        {"name": "Saitama",           "tags": ["anime","one_punch_man","bald","overpowered","hero","one_punch","bored","yellow_suit","strong","parody"]},
        {"name": "All Might",         "tags": ["anime","my_hero_academia","hero","symbol_of_peace","blonde","muscular","smile","i_am_here","mentor","declining"]},
        {"name": "Deku",              "tags": ["anime","my_hero_academia","hero","green_hair","one_for_all","analysis","crying","determined","successor","nervous"]},
        {"name": "Todoroki",          "tags": ["anime","my_hero_academia","ice","fire","half_and_half","daddy_issues","powerful","cool","dual_quirk","stoic"]},
        {"name": "Gon",               "tags": ["anime","hunter_x_hunter","hunter","naive","determined","fishing_rod","nen","spiky_hair","young","innocent"]},
        {"name": "Killua",            "tags": ["anime","hunter_x_hunter","assassin","white_hair","electricity","best_friend","yo_yo","rich","trained","cool"]},
        {"name": "Ichigo",            "tags": ["anime","bleach","shinigami","orange_hair","sword","hollow","substitute","protector","bankai","hero"]},
        {"name": "Sailor Moon",       "tags": ["anime","magical_girl","blonde","transform","moon","usagi","crybaby","sailor_scouts","love","justice"]},
        {"name": "Ash Ketchum",       "tags": ["anime","pokemon","trainer","pikachu","hat","wannabe_master","naive","determined","forever_10","pallet_town"]},
        {"name": "Kakashi",           "tags": ["anime","naruto","sensei","copy_ninja","masked","sharingan","lazy","late","silver_hair","cool"]},
        {"name": "Itachi",            "tags": ["anime","naruto","uchiha","brother","tragic","sharingan","genius","criminal","crow","truth"]},

        # COMICS & SUPERHEROES
        {"name": "Wolverine",         "tags": ["comic","marvel","x_men","claws","healing","canadian","gruff","beer","adamantium","immortal"]},
        {"name": "Deadpool",          "tags": ["comic","marvel","antihero","red","regeneration","mercenary","fourth_wall","jokes","insane","katanas"]},
        {"name": "Flash",             "tags": ["comic","dc","superhero","fast","red","lightning","barry_allen","speedster","fastest","time_travel"]},
        {"name": "Catwoman",          "tags": ["comic","dc","antihero","thief","cat","whip","leather","batman","selina","agile"]},
        {"name": "Harley Quinn",      "tags": ["comic","dc","villain","antihero","jester","joker","baseball_bat","crazy","pigtails","chaotic"]},
        {"name": "Nightwing",         "tags": ["comic","dc","hero","acrobat","blue","dick_grayson","former_robin","leader","charming","skilled"]},
        {"name": "Cyclops",           "tags": ["comic","marvel","x_men","laser_eyes","visor","leader","scott_summers","tactical","mutant","serious"]},
        {"name": "Storm",             "tags": ["comic","marvel","x_men","weather","white_hair","goddess","lightning","wind","african","powerful"]},
        {"name": "Magneto",           "tags": ["comic","marvel","x_men","villain","magnetism","helmet","metal","holocaust","brotherhood","tragic"]},
        {"name": "Professor X",       "tags": ["comic","marvel","x_men","telepath","bald","wheelchair","school","founder","peaceful","mentor"]},
        {"name": "Daredevil",         "tags": ["comic","marvel","blind","lawyer","red","acrobat","radar","catholic","matt_murdock","hells_kitchen"]},
        {"name": "Deadpool",          "tags": ["comic","marvel","antihero","red","fourth_wall","mercenary","guns","jokes","insane","regeneration"]},
        {"name": "Venom",             "tags": ["comic","marvel","symbiote","black","tongue","antihero","spider_man","eddie_brock","teeth","we"]},
        {"name": "Doctor Strange",    "tags": ["comic","marvel","sorcerer","magic","cape","goatee","surgeon","time_stone","mystical","multiverse"]},
        {"name": "Black Panther",     "tags": ["comic","marvel","king","wakanda","vibranium","cat","tchalla","rich","african","advanced"]},
        {"name": "Loki",              "tags": ["comic","marvel","god","trickster","villain","horns","magic","adopted","mischief","norse"]},
        {"name": "Scarlet Witch",     "tags": ["comic","marvel","magic","chaos","red","reality_warping","wanda","powerful","hex","avenger"]},
        {"name": "Green Arrow",       "tags": ["comic","dc","archer","green","hood","goatee","billionaire","oliver_queen","boxing_glove_arrow","liberal"]},
        {"name": "Lex Luthor",        "tags": ["comic","dc","villain","genius","billionaire","bald","superman","businessman","power_suit","human"]},

        # HISTORICAL
        {"name": "Abraham Lincoln",      "tags": ["historical","president","tall","beard","hat","assassinated","civil_war","honest","emancipation","american"]},
        {"name": "Albert Einstein",      "tags": ["historical","scientist","genius","relativity","mustache","crazy_hair","physicist","e_mc2","nobel","german"]},
        {"name": "Leonardo da Vinci",    "tags": ["historical","artist","inventor","renaissance","mona_lisa","genius","italian","polymath","beard","notebook"]},
        {"name": "Cleopatra",            "tags": ["historical","queen","egypt","beautiful","snake","ruler","intelligent","roman","seductive","last_pharaoh"]},
        {"name": "Napoleon",             "tags": ["historical","french","emperor","short","military","hat","strategist","waterloo","exile","ambitious"]},
        {"name": "George Washington",    "tags": ["historical","president","first","american","revolutionary","general","founding_father","cannot_tell_lie","wig","hero"]},
        {"name": "Gandhi",               "tags": ["historical","indian","nonviolent","independence","bald","glasses","peaceful","fasting","philosophy","assassinated"]},

        # MYTHOLOGY
        {"name": "Zeus",      "tags": ["mythology","greek","god","lightning","king","olympus","powerful","beard","eagle","sky"]},
        {"name": "Poseidon",  "tags": ["mythology","greek","god","sea","trident","earthquakes","beard","horses","brother","ocean"]},
        {"name": "Hades",     "tags": ["mythology","greek","god","underworld","death","cerberus","helmet","brother","dark","ruler"]},
        {"name": "Odin",      "tags": ["mythology","norse","god","king","one_eye","wise","ravens","father","sleipnir","allfather"]},
        {"name": "Loki",      "tags": ["mythology","norse","trickster","shapeshifter","mischief","cunning","frost_giant","adopted","chaos","clever"]},
        {"name": "Anubis",    "tags": ["mythology","egyptian","god","death","jackal","mummification","underworld","black","scales","guardian"]},
        {"name": "Medusa",    "tags": ["mythology","greek","gorgon","snakes_for_hair","stone_gaze","monster","perseus","cursed","tragic","ugly"]},
        {"name": "Hercules",  "tags": ["mythology","greek","demigod","strong","twelve_labors","hero","muscular","zeus","club","lion"]},
    ]


def _build_questions() -> List[Dict]:
    return [
        # Category
        {"id": "cat_video_game",  "text": "Is your character from a video game?",           "tag": "video_game",  "weight": 10},
        {"id": "cat_movie",       "text": "Is your character from a movie?",                 "tag": "movie",       "weight": 10},
        {"id": "cat_tv",          "text": "Is your character from a TV show?",               "tag": "tv",          "weight": 10},
        {"id": "cat_anime",       "text": "Is your character from anime or manga?",          "tag": "anime",       "weight": 10},
        {"id": "cat_comic",       "text": "Is your character from comic books?",             "tag": "comic",       "weight": 10},
        {"id": "cat_historical",  "text": "Is your character a real historical figure?",    "tag": "historical",  "weight": 10},
        {"id": "cat_mythology",   "text": "Is your character from mythology or legends?",   "tag": "mythology",   "weight": 10},
        # Gender / Species
        {"id": "gender_female",   "text": "Is your character female?",                       "tag": "female",      "weight": 9},
        {"id": "species_robot",   "text": "Is your character a robot or AI?",                "tag": "robot",       "weight": 8},
        {"id": "species_alien",   "text": "Is your character an alien?",                     "tag": "alien",       "weight": 8},
        {"id": "species_god",     "text": "Is your character a god or deity?",               "tag": "god",         "weight": 8},
        # Role
        {"id": "role_hero",       "text": "Is your character a hero or protagonist?",        "tag": "hero",        "weight": 9},
        {"id": "role_villain",    "text": "Is your character a villain or antagonist?",      "tag": "villain",     "weight": 9},
        {"id": "role_antihero",   "text": "Is your character an antihero?",                  "tag": "antihero",    "weight": 8},
        {"id": "role_sidekick",   "text": "Is your character a sidekick or helper?",         "tag": "sidekick",    "weight": 7},
        # Powers
        {"id": "power_magic",     "text": "Does your character use magic?",                  "tag": "magic",       "weight": 8},
        {"id": "power_tech",      "text": "Does your character use advanced technology?",    "tag": "tech",        "weight": 7},
        {"id": "power_strong",    "text": "Is your character known for incredible strength?","tag": "strong",      "weight": 7},
        {"id": "power_fast",      "text": "Is your character known for being fast?",         "tag": "fast",        "weight": 7},
        {"id": "power_smart",     "text": "Is your character a genius or very intelligent?", "tag": "genius",      "weight": 7},
        # Appearance
        {"id": "app_blonde",      "text": "Does your character have blonde hair?",           "tag": "blonde",      "weight": 6},
        {"id": "app_redhead",     "text": "Does your character have red or orange hair?",    "tag": "redhead",     "weight": 6},
        {"id": "app_white_hair",  "text": "Does your character have white or silver hair?",  "tag": "white_hair",  "weight": 6},
        {"id": "app_bald",        "text": "Is your character bald?",                         "tag": "bald",        "weight": 6},
        {"id": "app_mask",        "text": "Does your character wear a mask or helmet?",      "tag": "mask",        "weight": 6},
        {"id": "app_glasses",     "text": "Does your character wear glasses?",               "tag": "glasses",     "weight": 6},
        {"id": "app_beard",       "text": "Does your character have a beard?",               "tag": "beard",       "weight": 6},
        {"id": "app_cape",        "text": "Does your character wear a cape?",                "tag": "cape",        "weight": 5},
        # Weapons / Tools
        {"id": "attr_sword",      "text": "Does your character use a sword?",                "tag": "sword",       "weight": 6},
        {"id": "attr_gun",        "text": "Does your character use a gun?",                  "tag": "guns",        "weight": 6},
        {"id": "attr_shield",     "text": "Does your character use a shield?",               "tag": "shield",      "weight": 5},
        {"id": "attr_hammer",     "text": "Does your character wield a hammer?",             "tag": "hammer",      "weight": 5},
        # Franchise
        {"id": "fr_nintendo",     "text": "Is your character from Nintendo?",                "tag": "nintendo",    "weight": 8},
        {"id": "fr_marvel",       "text": "Is your character from Marvel?",                  "tag": "marvel",      "weight": 8},
        {"id": "fr_dc",           "text": "Is your character from DC?",                      "tag": "dc",          "weight": 8},
        {"id": "fr_disney",       "text": "Is your character from a Disney property?",       "tag": "disney",      "weight": 7},
        {"id": "fr_star_wars",    "text": "Is your character from Star Wars?",               "tag": "star_wars",   "weight": 8},
        {"id": "fr_pokemon",      "text": "Is your character from Pokémon?",                 "tag": "pokemon",     "weight": 7},
        # Setting
        {"id": "set_space",       "text": "Is your character associated with space or sci-fi?", "tag": "space",   "weight": 7},
        {"id": "set_medieval",    "text": "Is your character from a medieval/fantasy world?",   "tag": "medieval","weight": 7},
        {"id": "set_ninja",       "text": "Is your character a ninja or assassin?",          "tag": "ninja",       "weight": 6},
        {"id": "set_pirate",      "text": "Is your character a pirate?",                     "tag": "pirate",      "weight": 5},
        # Personality
        {"id": "per_funny",       "text": "Is your character funny or comedic?",             "tag": "funny",       "weight": 6},
        {"id": "per_angry",       "text": "Is your character often angry or aggressive?",    "tag": "angry",       "weight": 6},
        {"id": "per_brave",       "text": "Is your character known for being brave?",        "tag": "brave",       "weight": 6},
        {"id": "per_tragic",      "text": "Does your character have a tragic backstory?",    "tag": "tragic",      "weight": 6},
    ]


_CHARACTERS: List[Dict] = _build_characters()
_QUESTIONS:  List[Dict] = _build_questions()

# ──────────────────────────────────────────────────────────────────────────────
# Game logic helpers
# ──────────────────────────────────────────────────────────────────────────────

# Multipliers applied to character score for each answer
_SCORE_MULT: Dict[str, tuple] = {
    # answer_val: (multiplier_if_tag_present, multiplier_if_tag_absent)
    "yes":          (4.0,  0.05),
    "probably":     (2.5,  0.35),
    "idk":          (1.0,  1.0),
    "probably_not": (0.35, 2.5),
    "no":           (0.05, 4.0),
}


def _apply_answer(game: dict, tag: str, answer_val: str) -> None:
    """Multiply each character's score based on whether it has the tag."""
    has_m, no_m = _SCORE_MULT.get(answer_val, (1.0, 1.0))
    scores = game["scores"]
    for c in game["possible_characters"]:
        name = c["name"]
        if tag in c["tags"]:
            scores[name] = scores[name] * has_m
        else:
            scores[name] = scores[name] * no_m
    # Re-sort by score descending so index-0 is always the best guess
    game["possible_characters"].sort(
        key=lambda c: game["scores"][c["name"]], reverse=True
    )


def _best_question(game: dict) -> Optional[Dict]:
    """Return the question that maximises score-weighted information gain."""
    chars  = game["possible_characters"]
    scores = game["scores"]
    asked  = set(game["asked_questions"])
    available = [q for q in _QUESTIONS if q["id"] not in asked]
    if not available or not chars:
        return None

    total = sum(scores[c["name"]] for c in chars)
    if total == 0:
        return None

    best, best_score = None, -1.0
    for q in available:
        tag = q["tag"]
        sw = sum(scores[c["name"]] for c in chars if tag in c["tags"])
        sn = total - sw
        if sw <= 0 or sn <= 0:
            score = 0.0
        else:
            p, r  = sw / total, sn / total
            score = (-(p * math.log2(p)) - (r * math.log2(r))) * q["weight"]
        if score > best_score:
            best_score = score
            best = q
    return best


def _confidence(game: dict) -> float:
    """Return top character's share of total score (0–1)."""
    chars  = game["possible_characters"]
    scores = game["scores"]
    total  = sum(scores[c["name"]] for c in chars)
    if total <= 0 or not chars:
        return 0.0
    return scores[chars[0]["name"]] / total


def _next_phase(game: dict) -> str:
    """Decide next phase after an answer has been applied."""
    q_count = game["question_count"]
    chars   = game["possible_characters"]

    if not chars:
        return "stumped"

    if q_count >= 25:
        return "final"

    conf = _confidence(game)
    # Guess when we're very confident (and asked at least 4 questions)
    if q_count >= 4 and conf >= 0.70:
        game["current_guess"] = chars[0]
        return "guess"

    q = _best_question(game)
    if q is None:
        return "final"
    game["current_question"] = q
    game["question_count"] += 1
    return "question"


# ──────────────────────────────────────────────────────────────────────────────
# Components V2 View
# ──────────────────────────────────────────────────────────────────────────────

_COL_PURPLE = discord.Colour.from_str("#9b59b6")
_COL_GOLD   = discord.Colour.from_str("#f39c12")
_COL_GREEN  = discord.Colour.from_str("#2ecc71")
_COL_RED    = discord.Colour.from_str("#e74c3c")
_COL_ORANGE = discord.Colour.from_str("#e67e22")

_ANSWER_DEFS = [
    # (key, label, emoji, style)
    ("yes",          "Yes",          "✅", discord.ButtonStyle.success),
    ("probably",     "Probably",     "🤔", discord.ButtonStyle.primary),
    ("idk",          "Don't Know",   "🤷", discord.ButtonStyle.secondary),
    ("probably_not", "Prob. Not",    "🙁", discord.ButtonStyle.primary),
    ("no",           "No",           "❌", discord.ButtonStyle.danger),
]

_ASCII_AKI = (
    "```\n"
    "                                    .:..            \n"
    "                     ........... ...:x+. .          \n"
    "                .::.;+;:........:::xxx;..            \n"
    "                ;.:...x;.  .   ..:x:...             \n"
    "               .;...;;::x+........::+:.             \n"
    "               :...:+++..:+:.        .::            \n"
    "               :;......:::;;+..        :.           \n"
    "                :xx;;;;;;;;;;;++..     ::           \n"
    "                .XXx;;;+xXXXx;;x&+... .x.           \n"
    "                 .+++;;;;+xx;;;;&X+++;++.           \n"
    "                 .;;+;;;;;++;;;;+x++;:;.            \n"
    "                .:;;+;;;;;;;;;;;XXx$x.              \n"
    "                .:;xXX+xXxx+;;;;Xx:..               \n"
    "                .:;;;+;;;;;;;;;;;+..                \n"
    "                 .+;;X;;;;;;;;;x+...                \n"
    "                   .x&&Xxx+;+;;x+:..                \n"
    "                 ..;$&Xx;;;;xxxxx...                \n"
    "              .:xxxxxxX+;;;xxxxxxxxx+;....          \n"
    "             .;xxxxxxx+;;xxxxxxxxxxxxxx+;....       \n"
    "           ..;x+xxxxxx+;;;xxxxxxxxxxxxxxxx:.        \n"
    "         ..:x+++;+xxxxx+xxxxxxxxxxxxxxxxxxx.        \n"
    "        .;xxXxXXxxxxxxxxxxXxxxxxxxxxxxxxxxX.        \n"
    "   ..:+xxxxxxx;;;;;;;;;;;;xxxxxxxxxxxxxxxx+.        \n"
    "   .:+xxxxxxx;;;;;xxxxxxxxxxxXxxxxxxxxxxx:..        \n"
    "    .+xxxxxx+;;x;+xxxxxxxxxxxxxxxxxxxxx+:.  .       \n"
    "     .+xxxxx+XX++xxxxxxxxxxxxxxxxxxxxx;.  ..        \n"
    "      .;xxxxXXxxxxxxxxx+xxxxxxxxxxxX:..  .          \n"
    "      ..+xxXXx;xxxxxxxxxxxxxxxxxxX;..               \n"
    "        .xxXX:;xxxxxxxxxxXxxxxxxx+..                \n"
    "        .:xX+..xxxxxxxxxxxxxxxxxx...                \n"
    "          ..  .;xxxxxxxxxxxxxxx;.                   \n"
    "              ..x+x++xxxxxxx+x:...                  \n"
    "                :xxxxxxxxxxx;. ..                   \n"
    "              ...+xxxxxxxx+:..                      \n"
    "               ..:xxxxxxxx..                        \n"
    "                 .:xxxxxx..                         \n"
    "                 ..:xxxxx:.                         \n"
    "                   .:xxxxxx+;xxxxxxxx+::......::..  \n"
    "                 .....+xxxxxxxxxxxxx+;;:::..;;+:.   \n"
    "                    ....;xxxxxxxxXxxXxx++++++:...   \n"
    "                         ........+xxxxxxxx+:..      \n"
    "                                 ..:xxx;:.. .       \n"
    "                                 .:+++;+:.          \n"
    "```"
)


class AkinatorView(discord.ui.LayoutView):
    """Components V2 view that drives the entire Akinator session."""

    def __init__(self, uid: int, state: dict) -> None:
        super().__init__(timeout=300)
        self.uid   = uid
        self.state = state
        self._build()

    # ── user guard ────────────────────────────────────────────────────────────

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.uid:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return False
        return True

    # ── rendering ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.clear_items()
        phase = self.state.get("phase", "question")
        dispatch = {
            "question": self._render_question,
            "guess":    self._render_guess,
            "final":    self._render_final,
            "stumped":  self._render_stumped,
        }
        fn = dispatch.get(phase)
        if fn:
            fn()

    def _render_question(self) -> None:
        q         = self.state["current_question"]
        n         = self.state["question_count"]
        # "remaining" = chars with meaningful score (top-30 approximation)
        scores    = self.state["scores"]
        chars     = self.state["possible_characters"]
        total_s   = sum(scores[c["name"]] for c in chars) or 1
        remaining = sum(1 for c in chars if scores[c["name"]] / total_s >= 0.005)
        filled    = "█" * n + "░" * (25 - n)

        art_block = f"{_ASCII_AKI}\n" if n == 1 else ""
        header = (
            f"{art_block}"
            f"## 🔮 Akinator\n"
            f"`{filled}` **{n} / 25**\n"
            f"-# {remaining} characters still possible\n\n"
            f"**{q['text']}**"
        )

        yes_b = discord.ui.Button(emoji="✅", label="Yes",        style=discord.ButtonStyle.success,   custom_id="aki_ans_yes")
        prb_b = discord.ui.Button(emoji="🤔", label="Probably",   style=discord.ButtonStyle.primary,   custom_id="aki_ans_probably")
        idk_b = discord.ui.Button(emoji="🤷", label="Don't Know", style=discord.ButtonStyle.secondary, custom_id="aki_ans_idk")
        prn_b = discord.ui.Button(emoji="🙁", label="Prob. Not",  style=discord.ButtonStyle.primary,   custom_id="aki_ans_probably_not")
        no_b  = discord.ui.Button(emoji="❌", label="No",         style=discord.ButtonStyle.danger,    custom_id="aki_ans_no")

        yes_b.callback = self._make_answer_cb("yes")
        prb_b.callback = self._make_answer_cb("probably")
        idk_b.callback = self._make_answer_cb("idk")
        prn_b.callback = self._make_answer_cb("probably_not")
        no_b.callback  = self._make_answer_cb("no")

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(header),
            discord.ui.Separator(),
            discord.ui.ActionRow(yes_b, prb_b, idk_b),
            discord.ui.ActionRow(prn_b, no_b),
            accent_colour=_COL_PURPLE,
        ))

    def _render_guess(self) -> None:
        char = self.state["current_guess"]
        cat  = char["tags"][0].replace("_", " ").title()
        n    = self.state["question_count"]

        text = (
            f"## 🎯 I think I know!\n\n"
            f"After **{n}** questions…\n\n"
            f"# {char['name']}\n"
            f"-# {cat}\n\n"
            f"Is that your character?"
        )

        yes_b = discord.ui.Button(emoji="✅", label="Yes! You got it!", style=discord.ButtonStyle.success, custom_id="aki_g_yes")
        no_b  = discord.ui.Button(emoji="❌", label="Nope, wrong!",    style=discord.ButtonStyle.danger,  custom_id="aki_g_no")
        yes_b.callback = self._guess_yes_cb
        no_b.callback  = self._guess_no_cb

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(yes_b, no_b),
            accent_colour=_COL_GOLD,
        ))

    def _render_final(self) -> None:
        guesses = self.state["possible_characters"][:3]
        n       = self.state["question_count"]
        lines   = "\n".join(f"**{i + 1}.** {c['name']}" for i, c in enumerate(guesses))

        text = (
            f"## 🤔 Final Round\n\n"
            f"After **{n}** questions, my best guesses:\n\n"
            f"{lines}\n\n"
            f"Which one is yours?"
        )

        guess_btns = []
        for i, char in enumerate(guesses):
            b = discord.ui.Button(label=str(i + 1), emoji="🎯",
                                  style=discord.ButtonStyle.primary,
                                  custom_id=f"aki_f_{i}")
            b.callback = self._make_final_cb(i, char["name"])
            guess_btns.append(b)

        none_b = discord.ui.Button(label="None of these — I win!",
                                   emoji="🏆", style=discord.ButtonStyle.danger,
                                   custom_id="aki_f_none")
        none_b.callback = self._final_none_cb

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(*guess_btns, none_b),
            accent_colour=_COL_ORANGE,
        ))

    def _render_stumped(self) -> None:
        text = (
            "## 😅 You Stumped Me!\n\n"
            "I couldn't figure out your character!\n\n"
            "**You win this round!** 🏆\n"
            "-# Thanks for playing — consider suggesting your character!"
        )
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            accent_colour=_COL_RED,
        ))

    # ── answer callbacks ──────────────────────────────────────────────────────

    def _make_answer_cb(self, answer_val: str):
        async def _cb(interaction: discord.Interaction) -> None:
            tag = self.state["current_question"]["tag"]
            qid = self.state["current_question"]["id"]
            self.state["answers"][qid] = answer_val
            self.state["asked_questions"].append(qid)
            # Score-based update — never eliminates characters completely
            _apply_answer(self.state, tag, answer_val)
            self.state["phase"] = _next_phase(self.state)
            self._build()
            await interaction.response.edit_message(view=self)
        return _cb

    # ── guess callbacks ────────────────────────────────────────────────────────

    async def _guess_yes_cb(self, interaction: discord.Interaction) -> None:
        char = self.state["current_guess"]
        n    = self.state["question_count"]
        text = (
            f"## 🎉 I Win!\n\n"
            f"Your character was **{char['name']}**!\n\n"
            f"I guessed it in only **{n}** questions 🎩✨\n\n"
            f"-# Thanks for playing Akinator!"
        )
        self.clear_items()
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            accent_colour=_COL_GREEN,
        ))
        self.state["phase"] = "done_win"
        await interaction.response.edit_message(view=self)
        self.stop()

    async def _guess_no_cb(self, interaction: discord.Interaction) -> None:
        wrong = self.state["current_guess"]["name"]
        # Crush the score of the wrong guess so it won't come back
        self.state["scores"][wrong] = 0.0
        self.state["possible_characters"].sort(
            key=lambda c: self.state["scores"][c["name"]], reverse=True
        )
        # Force back into question phase (don't let _next_phase re-guess same char)
        self.state["current_guess"] = None
        # Continue asking questions
        q = _best_question(self.state)
        if q is None:
            self.state["phase"] = "final"
        else:
            self.state["current_question"] = q
            self.state["question_count"] += 1
            self.state["phase"] = "question"
        self._build()
        await interaction.response.edit_message(view=self)
        if self.state["phase"] == "stumped":
            self.stop()

    # ── final callbacks ────────────────────────────────────────────────────────

    def _make_final_cb(self, idx: int, name: str):
        async def _cb(interaction: discord.Interaction) -> None:
            n    = self.state["question_count"]
            text = (
                f"## 🎉 I Got It!\n\n"
                f"Your character was **{name}**!\n\n"
                f"Questions asked: **{n}**\n\n"
                f"-# Thanks for playing!"
            )
            self.clear_items()
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(text),
                accent_colour=_COL_GREEN,
            ))
            self.state["phase"] = "done_win"
            await interaction.response.edit_message(view=self)
            self.stop()
        return _cb

    async def _final_none_cb(self, interaction: discord.Interaction) -> None:
        self.state["phase"] = "stumped"
        self._build()
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self) -> None:
        self.state["phase"] = "timed_out"
        self.stop()


# ──────────────────────────────────────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────────────────────────────────────

class AkinatorCog(commands.Cog, name="Akinator"):
    """🔮 Akinator — think of a character and I'll guess it!"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.active_games: dict[int, dict] = {}

    @app_commands.command(name="akinator",
                          description="🔮 Think of any character — I'll guess who it is!")
    async def akinator_cmd(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id

        if uid in self.active_games:
            await interaction.response.send_message(
                "❌ You already have an Akinator game running! Finish it first.",
                ephemeral=True,
            )
            return

        # Initialise state
        chars_copy = list(_CHARACTERS)   # shallow copy
        state: dict = {
            "phase":               "question",
            "possible_characters": chars_copy,
            "scores":              {c["name"]: 1.0 for c in chars_copy},
            "asked_questions":     [],
            "answers":             {},
            "question_count":      0,
            "current_question":    None,
            "current_guess":       None,
        }

        # Pick first question
        first_q = _best_question(state)
        if first_q is None:
            await interaction.response.send_message("❌ Failed to start game.", ephemeral=True)
            return

        state["current_question"] = first_q
        state["question_count"]   = 1

        self.active_games[uid] = state
        view = AkinatorView(uid, state)

        await interaction.response.send_message(view=view)

        # Wait for the view to finish (win / stump / timeout) then clean up
        await view.wait()
        self.active_games.pop(uid, None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AkinatorCog(bot))
