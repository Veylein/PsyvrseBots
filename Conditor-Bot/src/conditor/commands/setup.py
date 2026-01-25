from discord import app_commands
from discord.ext import commands
from ..modals import SetupModalStep1


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Start a Conditor server setup modal")
    async def setup(self, interaction: commands.Context):
        await interaction.response.send_modal(SetupModalStep1(self.bot))


async def setup_sync(bot: commands.Bot):
    # Add the cog instance and ensure commands are registered
    bot.add_cog(SetupCog(bot))
