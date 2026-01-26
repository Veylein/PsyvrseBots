import compileall
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent

print('Running compileall...')
ok = compileall.compile_dir(str(BASE), force=False, quiet=1)
print('compileall ok:', ok)

print('\n--- git status (porcelain) ---')
subprocess.run(['git', 'status', '--porcelain'])

print('\n--- tracked .env files ---')
res = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
tracked_envs = [l for l in res.stdout.splitlines() if l.strip().endswith('.env')]
if tracked_envs:
    for t in tracked_envs:
        print(t)
else:
    print('none')

print('\n--- verify start wrappers ---')
for p in ('Pax-Bot/start.py', 'Ludus-Bot/start.py'):
    exists = (BASE / p).exists()
    print(f"{p}: {'exists' if exists else 'MISSING'}")

print('\n--- main.py check ---')
main = BASE / 'main.py'
if main.exists():
    text = main.read_text()
    print('find_folder_by_name' in text and 'ENTRY_CANDIDATES' in text)
else:
    print('main.py missing')

print('\n--- .gitignore present ---')
print((BASE / '.gitignore').exists())

print('\nDone.')
