import asyncio
import os
import sys

async def main():
    os.environ["PYTHONIOENCODING"] = "utf-8"

    try:
        import main
    except Exception as e:
        print("❌ Failed to import main.py:", e)
        sys.exit(1)

    # Start the bot object inside eventus_render_mega.py
    try:
        await main.bot.start(os.getenv("EVENTUS_TOKEN"))
    except Exception as e:
        print("❌ Bot crashed:", e)
    finally:
        await main.bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot manually stopped")
      
