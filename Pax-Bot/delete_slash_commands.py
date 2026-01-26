import os
import discord
import asyncio

# Do NOT hardcode bot tokens. Use an environment variable instead.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN') or os.getenv('PAX_TOKEN')
if not DISCORD_TOKEN:
    raise RuntimeError('DISCORD_TOKEN or PAX_TOKEN must be set in the environment')


class CleanupBot(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        app_id = (await self.application_info()).id
        commands = await self.http.get_global_commands(app_id)
        for cmd in commands:
            await self.http.delete_global_command(app_id, cmd['id'])
            print(f"Deleted global command: {cmd['name']}")
        await self.close()


intents = discord.Intents.default()
client = CleanupBot(intents=intents)
client.run(DISCORD_TOKEN)
