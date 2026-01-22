from src.logger import setup_logger

logger = setup_logger(__name__)


def register(bot):
    @bot.event
    async def on_interaction(interaction):
        # Generic interaction entrypoint; UI-driven flows should hook here.
        logger.debug("Interaction received: %s", type(interaction))
