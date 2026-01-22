import asyncpg
from src.logger import setup_logger

logger = setup_logger(__name__)

class Database:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or "postgresql://user:pass@localhost/sonus"
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)
        logger.info("Database pool created")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
