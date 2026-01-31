import re
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent

pattern = re.compile(r"@bot\.command\((.*?)\)\s*\n\s*async def\s+(\w+)|@bot\.command\((.*?)\)", re.S)
name_re = re.compile(r"name\s*=\s*['\"]([\w\-_/]+)['\"]")

commands = {}

for p in ROOT.rglob('*.py'):
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    for m in re.finditer(r"@bot\.command\(([^)]*)\)\s*\n\s*(?:async\s+def|def)\s+(\w+)", text):
        args = m.group(1)
        func = m.group(2)
        nm = None
        # try name= in args
        mm = name_re.search(args)
        if mm:
            nm = mm.group(1)
        else:
            # check for decorators without name: then command name is func or aliases? We'll record func
            nm = func
        entry = commands.setdefault(nm, [])
        entry.append(str(p))

# find duplicates
dups = {k: v for k, v in commands.items() if len(v) > 1}

print('Found', len(commands), 'commands,', len(dups), 'duplicates')
if dups:
    for name, files in sorted(dups.items()):
        print('\nCommand duplicate:', name)
        for f in files:
            print(' -', f)
else:
    print('No duplicate bot.command registrations found')
