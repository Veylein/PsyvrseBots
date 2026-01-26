
# Villicus main entry point
import asyncio
import sys
from pathlib import Path

# Ensure the Villicus-Bot folder is on sys.path so `import bot` resolves
BASE = Path(__file__).parent.resolve()
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from bot.bot import start_bot

def main():
    print("[Villicus] Starting main...")
    try:
        asyncio.run(start_bot())
    except Exception as e:
        print(f"[Villicus] Fatal error: {e}", file=sys.stderr)
        # Optionally, log to Discord if possible
        raise

if __name__ == "__main__":
    main()
