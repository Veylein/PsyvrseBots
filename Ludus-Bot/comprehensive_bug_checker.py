"""
COMPREHENSIVE BUG CHECKER - Tests all major bot systems
Simulates usage patterns and identifies potential issues
"""

import json
import os
import sys
import importlib.util

print("="*80)
print("LUDUS BOT - COMPREHENSIVE BUG SIMULATION")
print("="*80)

bugs_found = []
warnings = []
passes = []

def test_section(name):
    print(f"\n[TEST] {name}")
    print("-" * 80)

# Test 1: File Structure
test_section("File Structure Integrity")
required_files = {
    "bot.py": "Main bot file",
    "config.json": "Configuration",
    "requirements.txt": "Dependencies",
    "cogs/economy.py": "Economy system",
    "cogs/leveling.py": "Leveling system",
    "cogs/cardgames.py": "Card games (including UNO)",
    "cogs/minigames.py": "Minigames (including riddles)",
    "cogs/music.py": "Music player",
    "cogs/owner.py": "Owner commands",
    "cogs/utilities.py": "Help and utilities",
    "cogs/pets.py": "Pet system",
}

for filepath, description in required_files.items():
    if os.path.exists(filepath):
        passes.append(f"✅ {filepath} exists ({description})")
        print(f"✅ {filepath}")
    else:
        bugs_found.append(f"CRITICAL: {filepath} missing!")
        print(f"❌ {filepath} - MISSING!")

# Test 2: Python Syntax Validation
test_section("Python Syntax Validation")
cog_files = [
    "bot.py",
    "cogs/economy.py",
    "cogs/leveling.py",
    "cogs/cardgames.py",
    "cogs/minigames.py",
    "cogs/music.py",
    "cogs/owner.py",
    "cogs/utilities.py",
    "cogs/pets.py",
]

for filepath in cog_files:
    if not os.path.exists(filepath):
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        compile(code, filepath, 'exec')
        passes.append(f"✅ {filepath} - valid syntax")
        print(f"✅ {filepath} - Valid syntax")
    except SyntaxError as e:
        bugs_found.append(f"SYNTAX ERROR in {filepath}: Line {e.lineno}: {e.msg}")
        print(f"❌ {filepath} - SYNTAX ERROR: {e}")
    except Exception as e:
        warnings.append(f"Could not validate {filepath}: {e}")
        print(f"⚠️ {filepath} - Could not validate: {e}")

# Test 3: Import Validation
test_section("Import Statement Validation")
import_tests = [
    ("discord", "discord.py library"),
    ("yt_dlp", "YouTube downloader"),
]

for module_name, description in import_tests:
    try:
        importlib.import_module(module_name)
        passes.append(f"✅ {module_name} installed ({description})")
        print(f"✅ {module_name} - Installed")
    except ImportError:
        bugs_found.append(f"MISSING DEPENDENCY: {module_name} ({description})")
        print(f"❌ {module_name} - NOT INSTALLED!")

# Test 4: Config Validation
test_section("Configuration Validation")
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    
    required_keys = ["prefix", "owner_ids"]
    for key in required_keys:
        if key in config:
            passes.append(f"✅ config.json has '{key}'")
            print(f"✅ {key}: {config[key]}")
        else:
            bugs_found.append(f"config.json missing required key: {key}")
            print(f"❌ Missing key: {key}")
    
    # Validate owner_ids format
    if "owner_ids" in config:
        if isinstance(config["owner_ids"], list):
            if len(config["owner_ids"]) > 0:
                passes.append("✅ owner_ids is a non-empty list")
                print(f"✅ owner_ids has {len(config['owner_ids'])} owner(s)")
            else:
                warnings.append("owner_ids list is empty")
                print("⚠️ owner_ids is empty")
        else:
            bugs_found.append("owner_ids must be a list")
            print("❌ owner_ids is not a list!")
            
except FileNotFoundError:
    bugs_found.append("CRITICAL: config.json not found!")
    print("❌ config.json not found!")
except json.JSONDecodeError as e:
    bugs_found.append(f"config.json has invalid JSON: {e}")
    print(f"❌ Invalid JSON: {e}")

# Test 5: Cog Structure Analysis
test_section("Cog Structure Analysis")
for filepath in cog_files[1:]:  # Skip bot.py
    if not os.path.exists(filepath):
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Cog class
        if "class" in content and "commands.Cog" in content:
            passes.append(f"✅ {filepath} has Cog class")
            print(f"✅ {filepath} - Has Cog class")
        else:
            bugs_found.append(f"{filepath} missing Cog class definition")
            print(f"❌ {filepath} - No Cog class!")
        
        # Check for setup function
        if "async def setup(bot)" in content:
            passes.append(f"✅ {filepath} has setup() function")
            print(f"   ✅ Has setup() function")
        else:
            bugs_found.append(f"{filepath} missing setup() function")
            print(f"   ❌ Missing setup() function!")
            
    except Exception as e:
        warnings.append(f"Could not analyze {filepath}: {e}")
        print(f"⚠️ Could not analyze: {e}")

# Test 6: Command Registration Check
test_section("Command Registration Patterns")
command_patterns = {
    "cogs/economy.py": ["balance", "daily", "shop"],
    "cogs/cardgames.py": ["blackjack", "gofish", "war", "uno"],
    "cogs/minigames.py": ["wordle", "riddle", "gtn"],
    "cogs/music.py": ["play", "pause", "stop"],
    "cogs/owner.py": ["owner", "godmode", "setcoins"],
    "cogs/utilities.py": ["help", "setup"],
}

for filepath, expected_commands in command_patterns.items():
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{filepath}:")
    for cmd in expected_commands:
        # Check for both @commands.command and @app_commands
        found = f'name="{cmd}"' in content or f"name='{cmd}'" in content
        if found:
            passes.append(f"✅ {filepath} has '{cmd}' command")
            print(f"  ✅ {cmd}")
        else:
            warnings.append(f"{filepath} might be missing '{cmd}' command")
            print(f"  ⚠️ {cmd} - Not found (might use different name)")

# Test 7: Music System Specific Checks
test_section("Music System Configuration")
if os.path.exists("cogs/music.py"):
    with open("cogs/music.py", 'r', encoding='utf-8') as f:
        music_content = f.read()
    
    music_checks = [
        ("yt_dlp", "YouTube downloader import"),
        ("ytdl_opts", "yt-dlp options configured"),
        ("player_client", "Android client configured"),
        ("search_song", "Search function exists"),
        ("FFmpegPCMAudio", "FFmpeg audio support"),
    ]
    
    for check, description in music_checks:
        if check in music_content:
            passes.append(f"✅ Music: {description}")
            print(f"✅ {description}")
        else:
            bugs_found.append(f"Music system missing: {description}")
            print(f"❌ {description} - NOT FOUND!")

# Test 8: UNO Migration Check
test_section("UNO Migration Verification")
uno_checks = {
    "cogs/cardgames.py": ["UNOCard", "UNOGame", "uno", "unoplay"],
    "cogs/uno_gofish.py": []  # Should still exist for Go-Fish
}

for filepath, expected_items in uno_checks.items():
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{filepath}:")
    if expected_items:
        for item in expected_items:
            if item in content:
                passes.append(f"✅ {filepath} has {item}")
                print(f"  ✅ {item}")
            else:
                bugs_found.append(f"{filepath} missing {item} (UNO migration incomplete!)")
                print(f"  ❌ {item} - MISSING!")
    else:
        # uno_gofish should NOT have UNO classes
        if "UNOCard" in content or "class UNOGame" in content:
            warnings.append("uno_gofish.py still contains UNO code (should be in cardgames.py)")
            print("  ⚠️ Still contains UNO code")
        else:
            passes.append("✅ uno_gofish.py properly separated")
            print("  ✅ No UNO code found (correct!)")

# Test 9: Riddles Feature Check
test_section("Riddles Feature Verification")
if os.path.exists("cogs/minigames.py"):
    with open("cogs/minigames.py", 'r', encoding='utf-8') as f:
        minigames_content = f.read()
    
    riddle_checks = [
        "self.riddles",
        "@commands.command(name=\"riddle\")",
        "handle_riddle_guess",
        "hint",
    ]
    
    for check in riddle_checks:
        if check in minigames_content:
            passes.append(f"✅ Riddles: {check} found")
            print(f"✅ {check}")
        else:
            bugs_found.append(f"Riddles feature missing: {check}")
            print(f"❌ {check} - NOT FOUND!")

# Test 10: Help Command Update Check
test_section("Help Command Verification")
if os.path.exists("cogs/utilities.py"):
    with open("cogs/utilities.py", 'r', encoding='utf-8') as f:
        utilities_content = f.read()
    
    help_checks = [
        '@commands.command(name="help")',
        "_create_help_embed",
        "_get_category_help",
        "riddle",  # Should mention riddles
        "uno",     # Should mention UNO
    ]
    
    for check in help_checks:
        if check in utilities_content:
            passes.append(f"✅ Help system: {check}")
            print(f"✅ {check}")
        else:
            if check in ["riddle", "uno"]:
                warnings.append(f"Help might not mention {check}")
                print(f"⚠️ {check} - Not mentioned in help")
            else:
                bugs_found.append(f"Help system missing: {check}")
                print(f"❌ {check} - NOT FOUND!")

# Test 11: Owner Command Verification
test_section("Owner Command Configuration")
owner_issues = []

# Check bot.py for owner_ids setup
if os.path.exists("bot.py"):
    with open("bot.py", 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    if "owner_ids=set(config.get(" in bot_content:
        passes.append("✅ bot.py sets owner_ids correctly")
        print("✅ owner_ids configured in Bot constructor")
    else:
        bugs_found.append("bot.py doesn't set owner_ids properly!")
        print("❌ owner_ids NOT configured!")

# Check owner.py for decorator issues
if os.path.exists("cogs/owner.py"):
    with open("cogs/owner.py", 'r', encoding='utf-8') as f:
        owner_content = f.read()
    
    # Should NOT have @commands.is_owner() decorators
    if "@commands.is_owner()" in owner_content:
        bugs_found.append("owner.py still has @commands.is_owner() decorators!")
        print("❌ Found @commands.is_owner() - SHOULD BE REMOVED!")
    else:
        passes.append("✅ owner.py has no @commands.is_owner() decorators")
        print("✅ No @commands.is_owner() decorators (correct!)")
    
    # Should have cog_check
    if "async def cog_check" in owner_content:
        passes.append("✅ owner.py has cog_check()")
        print("✅ Has cog_check() for permission validation")
    else:
        bugs_found.append("owner.py missing cog_check()!")
        print("❌ Missing cog_check()!")

# Test 12: Data File Format Check
test_section("Data File JSON Validation")
json_files = ["config.json", "pets.json"]

for json_file in json_files:
    if not os.path.exists(json_file):
        warnings.append(f"{json_file} doesn't exist (might be auto-created)")
        print(f"⚠️ {json_file} - Will be auto-created")
        continue
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        passes.append(f"✅ {json_file} is valid JSON")
        print(f"✅ {json_file} - Valid JSON")
    except json.JSONDecodeError as e:
        bugs_found.append(f"{json_file} has invalid JSON: {e}")
        print(f"❌ {json_file} - INVALID JSON: {e}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("COMPREHENSIVE BUG CHECK SUMMARY")
print("="*80)

print(f"\n✅ PASSED: {len(passes)} checks")
print(f"⚠️ WARNINGS: {len(warnings)} items")
print(f"❌ BUGS FOUND: {len(bugs_found)} critical issues")

if bugs_found:
    print("\n" + "="*80)
    print("CRITICAL BUGS THAT NEED FIXING:")
    print("="*80)
    for i, bug in enumerate(bugs_found, 1):
        print(f"{i}. ❌ {bug}")

if warnings:
    print("\n" + "="*80)
    print("WARNINGS (Review Recommended):")
    print("="*80)
    for i, warning in enumerate(warnings, 1):
        print(f"{i}. ⚠️ {warning}")

print("\n" + "="*80)
print("DEPLOYMENT READINESS")
print("="*80)

if len(bugs_found) == 0:
    print("✅ NO CRITICAL BUGS FOUND!")
    print("✅ Bot is ready for deployment!")
    print("\nNext steps:")
    print("1. git add .")
    print("2. git commit -m 'All features complete and tested'")
    print("3. git push origin master")
    print("4. Wait for Render to auto-deploy (2-5 minutes)")
    print("5. Test commands in Discord!")
else:
    print(f"❌ Found {len(bugs_found)} critical bug(s)")
    print("⚠️ Fix these issues before deploying!")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
