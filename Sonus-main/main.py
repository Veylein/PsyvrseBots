import asyncio
from src.bot import create_bot
from src.logger import setup_logger

logger = setup_logger()

async def main():
    bot = create_bot()
    async with bot:
        await bot.start(bot.config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sonus shutting down gracefully.")
