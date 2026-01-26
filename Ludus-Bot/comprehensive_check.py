"""
COMPREHENSIVE BUG CHECK AND FIX
Tests all major systems and identifies issues
"""

import json
import os
import sys

print("="*80)
print("LUDUS BOT - COMPREHENSIVE BUG CHECK")
print("="*80)

issues_found = []
fixes_applied = []

# Test 1: Config validation
print("\n[TEST 1] Config File Validation")
print("-" * 80)
try:
    with open("config.json", "r") as f:
        config = json.load(f)
    
    required_fields = ["prefix", "owner_ids"]
    for field in required_fields:
        if field not in config:
            issues_found.append(f"config.json missing required field: {field}")
            print(f"❌ Missing: {field}")
        else:
            print(f"✅ Found: {field} = {config[field]}")
    
    # Validate owner_ids is a list
    if not isinstance(config.get("owner_ids"), list):
        issues_found.append("owner_ids must be a list")
        print("❌ owner_ids is not a list")
    elif len(config["owner_ids"]) == 0:
        issues_found.append("owner_ids list is empty")
        print("⚠️ owner_ids is empty")
    else:
        print(f"✅ owner_ids has {len(config['owner_ids'])} owner(s)")
        
except FileNotFoundError:
    issues_found.append("config.json not found")
    print("❌ config.json not found!")
except json.JSONDecodeError as e:
    issues_found.append(f"config.json has invalid JSON: {e}")
    print(f"❌ Invalid JSON: {e}")

# Test 2: Bot.py validation
print("\n[TEST 2] Bot.py Setup Check")
print("-" * 80)
try:
    with open("bot.py", "r", encoding="utf-8") as f:
        bot_content = f.read()
    
    checks = [
        ("owner_ids configuration", "owner_ids=set(config.get(\"owner_ids\""),
        ("cog loading", "async def load_cogs"),
        ("bot initialization", "commands.Bot("),
    ]
    
    for check_name, search_str in checks:
        if search_str in bot_content:
            print(f"✅ {check_name}: Found")
        else:
            issues_found.append(f"bot.py missing: {check_name}")
            print(f"❌ {check_name}: Missing")
            
except FileNotFoundError:
    issues_found.append("bot.py not found")
    print("❌ bot.py not found!")

# Test 3: Cog file checks
print("\n[TEST 3] Cog Files Check")
print("-" * 80)
required_cogs = [
    "economy.py",
    "leveling.py", 
    "cardgames.py",
    "music.py",
    "owner.py",
    "utilities.py"
]

for cog in required_cogs:
    path = f"cogs/{cog}"
    if os.path.exists(path):
        print(f"✅ {cog}")
        
        # Check for setup function
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if "async def setup(bot)" not in content:
                issues_found.append(f"{cog} missing setup(bot) function")
                print(f"   ❌ Missing setup() function")
    else:
        issues_found.append(f"{cog} not found")
        print(f"❌ {cog}: NOT FOUND")

# Test 4: Owner command check
print("\n[TEST 4] Owner Commands Check")
print("-" * 80)
try:
    with open("cogs/owner.py", "r", encoding="utf-8") as f:
        owner_content = f.read()
    
    # Check for owner command
    if '@commands.command(name="owner")' in owner_content:
        print("✅ L!owner command registered")
    else:
        issues_found.append("L!owner command not found in owner.py")
        print("❌ L!owner command not registered")
    
    # Check cog_check
    if "async def cog_check(self, ctx):" in owner_content:
        print("✅ cog_check (permission validation) found")
    else:
        issues_found.append("owner.py missing cog_check")
        print("❌ cog_check missing")
    
    # Count commands
    command_count = owner_content.count("@commands.command(")
    print(f"✅ Found {command_count} owner commands")
    
except FileNotFoundError:
    issues_found.append("owner.py not found")
    print("❌ owner.py not found!")

# Test 5: Music system check
print("\n[TEST 5] Music System Check")
print("-" * 80)
try:
    with open("cogs/music.py", "r", encoding="utf-8") as f:
        music_content = f.read()
    
    checks = [
        ("yt_dlp import", "import yt_dlp"),
        ("search_song method", "async def search_song"),
        ("play command", '@commands.command(name="play")' in music_content or '@music.command(name="play")' in music_content),
        ("android client", "player_client"),
    ]
    
    for check_name, search_item in checks:
        if isinstance(search_item, str):
            found = search_item in music_content
        else:
            found = search_item
            
        if found:
            print(f"✅ {check_name}")
        else:
            issues_found.append(f"Music system missing: {check_name}")
            print(f"❌ {check_name}")
    
except FileNotFoundError:
    issues_found.append("music.py not found")
    print("❌ music.py not found!")

# Test 6: Data file checks
print("\n[TEST 6] Data Files Check")
print("-" * 80)
data_files = [
    "economy.json",
    "levels.json",
    "pets.json",
]

for data_file in data_files:
    if os.path.exists(data_file):
        print(f"✅ {data_file} exists")
        try:
            with open(data_file, "r") as f:
                json.load(f)
            print(f"   ✅ Valid JSON")
        except json.JSONDecodeError:
            issues_found.append(f"{data_file} has invalid JSON")
            print(f"   ❌ Invalid JSON")
    else:
        print(f"⚠️ {data_file} missing (will be auto-created)")

# Test 7: Requirements check
print("\n[TEST 7] Requirements File Check")
print("-" * 80)
try:
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    required_packages = [
        "discord.py",
        "yt-dlp",
        "PyNaCl",
    ]
    
    for package in required_packages:
        if package.lower() in requirements.lower():
            print(f"✅ {package}")
        else:
            issues_found.append(f"requirements.txt missing: {package}")
            print(f"❌ {package} not in requirements.txt")
            
except FileNotFoundError:
    issues_found.append("requirements.txt not found")
    print("❌ requirements.txt not found!")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

if issues_found:
    print(f"\n❌ Found {len(issues_found)} issue(s):\n")
    for i, issue in enumerate(issues_found, 1):
        print(f"{i}. {issue}")
else:
    print("\n✅ No issues found! All checks passed.")

if fixes_applied:
    print(f"\n🔧 Applied {len(fixes_applied)} fix(es):\n")
    for i, fix in enumerate(fixes_applied, 1):
        print(f"{i}. {fix}")

print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)
print("""
1. If on Render:
   - Push to GitHub: git add . && git commit -m "Bug fixes" && git push
   - Render will auto-redeploy
   - Check Render logs after deployment

2. Test commands in Discord:
   - L!owner (should show owner commands)
   - L!music play never gonna give you up (test music)
   - L!help (check help command)

3. Common Issues:
   - Bot not restarted: Stop and restart with: python bot.py
   - Render not redeployed: Force redeploy from dashboard
   - Wrong Discord ID: Verify your ID matches config.json
   
4. Debug commands:
   - L!music test <query> - Test music search
   - Check bot logs for [Music] messages
""")
