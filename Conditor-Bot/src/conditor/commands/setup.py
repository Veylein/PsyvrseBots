from discord import app_commands, Interaction
from discord.ext import commands
from ..modals import SetupModalStep1


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup_sync(bot: commands.Bot):
    """Register the setup slash command and add the cog to the bot.

    This registers a simple `/setup` command that opens the first modal.
    """
    # register cog for potential non-app helpers
    bot.add_cog(SetupCog(bot))

    async def _setup(interaction: Interaction):
        await interaction.response.send_modal(SetupModalStep1(bot))

    cmd = app_commands.Command(name="setup", description="Start a Conditor server setup modal", callback=_setup)
    # avoid duplicate registration
    try:
        bot.tree.add_command(cmd)
    except Exception:
        # command might already be added; ignore
        pass
