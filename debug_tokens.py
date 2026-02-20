
import os
from pathlib import Path

def check_env_file(path):
    print(f"Checking {path}...")
    if not path.exists():
        print(f"  - File does not exist.")
        return

    try:
        content = path.read_text(encoding='utf-8')
        lines = content.splitlines()
        found = False
        for line in lines:
            line = line.strip()
            if line.startswith("PSYVRSE_TOKEN=") or line.startswith("DISCORD_TOKEN="):
                key, val = line.split("=", 1)
                val = val.strip()
                if val == "your_psyverse_bot_token_here":
                    print(f"  - Found {key} with PLACEHOLDER value.")
                elif val:
                    masked = val[:5] + "..." + val[-5:] if len(val) > 10 else "SHORT_VAL"
                    print(f"  - Found {key} with value: {masked}")
                else:
                    print(f"  - Found {key} with EMPTY value.")
                found = True
        if not found:
            print("  - No token found in file.")
            
    except Exception as e:
        print(f"  - Error reading file: {e}")

root = Path.cwd()
print(f"Scanning for .env files in {root}...")

possible_locs = [
    root / ".env",
    root / "PsySource" / ".env",
    root / "PsySource" / ".env.example",
    root / "Pax-Bot" / ".env",
    root / "Ludus-Bot" / ".env",
    root / "Ludus-Bot" / "config.env", # sometimes config.env
]

for p in possible_locs:
    check_env_file(p)

# Also explicit walk
print("\nWalking directory for any .env file...")
for path in root.rglob(".env"):
    if path not in possible_locs:
        check_env_file(path)
