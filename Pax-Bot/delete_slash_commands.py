import os
import discord
import asyncio

# Do NOT hardcode bot tokens. Use an environment variable instead.
PAX_TOKEN = os.getenv('PAX_TOKEN')
if not PAX_TOKEN:
    raise RuntimeError('PAX_TOKEN must be set in the environment')


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
client.run(PAX_TOKEN)
