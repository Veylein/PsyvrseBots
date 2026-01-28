import logging
from discord import app_commands, Interaction
from discord.ext import commands
from ..modals import SetupModalStep1


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Start a Conditor server setup modal")
    async def setup(self, interaction: Interaction):
        await interaction.response.send_modal(SetupModalStep1(self.bot))


async def setup_sync(bot: commands.Bot):
    # Add the cog instance; also register cog app-commands with the CommandTree
    cog = SetupCog(bot)
    await bot.add_cog(cog)
    try:
        # Register any app commands defined on the cog immediately
        bot.tree.add_cog(cog)
    except Exception:
        # some versions or states may raise if commands already registered
        pass
    try:
        # Diagnostic log for command registration
        slash_count = sum(1 for _ in bot.tree.walk_commands())
        logging.getLogger(__name__).info(f"Conditor: registered setup cog. Slash commands now: {slash_count}")
    except Exception:
        logging.getLogger(__name__).exception("Conditor: failed to enumerate slash commands after setup_sync")
