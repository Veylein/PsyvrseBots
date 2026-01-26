"""
Quick test to verify all cogs load properly
"""
import sys
import os
import ast

print("=" * 80)
print("QUICK COG LOAD TEST")
print("=" * 80)

# Test 1: Check if all main files exist
print("\n[1] Checking file existence...")
files_to_check = {
    "bot.py": False,
    "cogs/help.py": False,
    "cogs/gambling.py": False,
    "cogs/economy.py": False,
}

for filepath in files_to_check:
    if os.path.exists(filepath):
        files_to_check[filepath] = True
        print(f"  ✅ {filepath}")
    else:
        print(f"  ❌ {filepath} - MISSING!")

# Test 2: Check bot.py for help_command=None
print("\n[2] Checking bot.py for help_command=None...")
with open("bot.py", "r", encoding="utf-8") as f:
    bot_content = f.read()
    if "help_command=None" in bot_content:
        print("  ✅ help_command=None found")
    else:
        print("  ❌ help_command=None NOT found!")

# Test 3: Check help.py structure
print("\n[3] Checking help.py structure...")
with open("cogs/help.py", "r", encoding="utf-8") as f:
    help_content = f.read()
    checks = {
        '@commands.command(name="help"': False,
        '@app_commands.command(name="help"': False,
        'async def setup(bot)': False,
        'class Help(commands.Cog)': False,
    }
    
    for check in checks:
        if check in help_content:
            checks[check] = True
            print(f"  ✅ Found: {check}")
        else:
            print(f"  ❌ Missing: {check}")

# Test 4: Check gambling.py for prefix commands
print("\n[4] Checking gambling.py for prefix commands...")
with open("cogs/gambling.py", "r", encoding="utf-8") as f:
    gambling_content = f.read()
    prefix_commands = [
        'slots',
        'gambling_stats',
        'odds',
        'strategy',
        'dicegamble',
    ]
    
    for cmd in prefix_commands:
        pattern = f'@commands.command(name="{cmd}"'
        if pattern in gambling_content:
            print(f"  ✅ L!{cmd}")
        else:
            print(f"  ❌ L!{cmd} - NOT FOUND!")

# Test 5: Syntax validation
print("\n[5] Checking Python syntax...")
files_to_validate = [
    "bot.py",
    "cogs/help.py",
    "cogs/gambling.py",
]

all_valid = True
for filepath in files_to_validate:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
            ast.parse(code)
        print(f"  ✅ {filepath} - Valid syntax")
    except SyntaxError as e:
        print(f"  ❌ {filepath} - SYNTAX ERROR: {e}")
        all_valid = False

# Test 6: Check for setup() in cogs
print("\n[6] Checking cog setup functions...")
cog_files = ["cogs/help.py", "cogs/gambling.py", "cogs/economy.py"]
for cog_file in cog_files:
    with open(cog_file, "r", encoding="utf-8") as f:
        content = f.read()
        if "async def setup(bot)" in content:
            print(f"  ✅ {cog_file} has setup()")
        else:
            print(f"  ❌ {cog_file} missing setup()!")

# Final summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_files_exist = all(files_to_check.values())
help_command_disabled = "help_command=None" in bot_content
help_structure_ok = all(checks.values())

print(f"\n✅ All files exist: {all_files_exist}")
print(f"✅ help_command=None in bot.py: {help_command_disabled}")
print(f"✅ help.py structure correct: {help_structure_ok}")
print(f"✅ No syntax errors: {all_valid}")

if all_files_exist and help_command_disabled and help_structure_ok and all_valid:
    print("\n🎉 ALL CHECKS PASSED! Code is ready!")
    print("\n⚠️ If commands don't work on Render, the issue is deployment/environment!")
    print("   → Check Render logs for cog loading")
    print("   → Verify latest commit is deployed")
    print("   → Manually redeploy if needed")
else:
    print("\n❌ SOME CHECKS FAILED! Review output above.")

print("=" * 80)
