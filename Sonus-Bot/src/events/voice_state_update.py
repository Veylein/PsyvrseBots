from src.logger import setup_logger

logger = setup_logger(__name__)


def register(bot):
    @bot.event
    async def on_voice_state_update(member, before, after):
        # Track joins/leaves, auto-disconnect logic, etc.
        logger.debug("Voice state update for %s", getattr(member, "id", None))
