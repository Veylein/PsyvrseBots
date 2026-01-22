
# Villicus main entry point
import asyncio
import sys
from bot import start_bot

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
