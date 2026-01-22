import os

class Config:
    TOKEN = os.getenv("SONUS_TOKEN")
    APP_ID = os.getenv("SONUS_ID")
    GUILD_ID = os.getenv("GUILD_ID")

    if not TOKEN:
        raise RuntimeError("SONUS_TOKEN is not set")
