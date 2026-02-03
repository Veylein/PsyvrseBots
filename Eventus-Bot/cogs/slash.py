from discord import app_commands
import discord

class Slash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # E!help as a Slash Command
    @app_commands.command(name="help", description="Shows help for a specific command or cog")
    async def help(self, interaction: discord.Interaction, command_name: str = None):
        if command_name:
            command = self.bot.get_command(command_name)
            if command:
                await interaction.response.send_message(f"Help for {command_name}: {command.help}")
            else:
                await interaction.response.send_message(f"Command `{command_name}` not found.")
        else:
            await interaction.response.send_message("Showing general help...")  # You can expand this as needed

    # E!test as a Slash Command
    @app_commands.command(name="test", description="Test if the bot is working.")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message("Test command works!")

    # E!attend_event as a Slash Command
    @app_commands.command(name="attend_event", description="RSVP to an event.")
    @app_commands.describe(event_id="The ID of the event you want to attend.")
    async def attend_event(self, interaction: discord.Interaction, event_id: int):
        await interaction.response.send_message(f"You've RSVPed to event {event_id}!")

    # E!create_event as a Slash Command
    @app_commands.command(name="create_event", description="Create an event with RSVP, recurrence, and reminders.")
    @app_commands.describe(title="The title of the event", description="The description of the event")
    async def create_event(self, interaction: discord.Interaction, title: str, description: str):
        # Here you would add the logic for creating the event in your database
        await interaction.response.send_message(f"Event '{title}' created with description: {description}")


async def setup(bot):
    await bot.add_cog(Slash(bot))