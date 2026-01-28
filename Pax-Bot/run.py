import asyncio
import os
import signal
import discord
from discord.ext import commands
from contextlib import asynccontextmanager
from api import app, set_bot_instance
import uvicorn
import logging

logging.getLogger('discord').setLevel(logging.WARNING)

IS_DEPLOYED = os.getenv("REPLIT_DEPLOYMENT") == "1"

@asynccontextmanager
async def lifespan(app):
    from main import bot
    
    print("✅ API server started")
    
    if IS_DEPLOYED:
        print("🚀 Running in PRODUCTION mode")
        print("🤖 Starting Discord bot...")
    else:
        print("🔧 Running in DEVELOPMENT mode")
        print("🤖 Starting Discord bot...")
        print("⚠️  Note: Stop this workflow before publishing to avoid duplicate bot instances!")
    
    set_bot_instance(bot)
    
    discord_token = os.getenv("PAX_TOKEN")
    if not discord_token:
        raise ValueError("PAX_TOKEN environment variable is required")
    
    bot_task = asyncio.create_task(bot.start(discord_token))
    
    yield
    
    print("🔄 Shutting down gracefully...")
    
    bot_task.cancel()
    try:
        await asyncio.wait_for(bot_task, timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    
    if not bot.is_closed():
        await bot.close()

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    print("🐼 Starting Panda Bot Control Panel...")
    print("📡 Starting API server on port 5000...")
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
