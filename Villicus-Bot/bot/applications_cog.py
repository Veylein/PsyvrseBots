import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from typing import Optional

from core.config import get_guild_settings, save_guild_settings


class ApplicationModal(ui.Modal, title="Server Application"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.reason = ui.TextInput(label="Why do you want to join?", style=discord.TextStyle.long, required=True, max_length=1500)
        self.experience = ui.TextInput(label="Relevant experience / skills", style=discord.TextStyle.long, required=False, max_length=1000)
        self.other = ui.TextInput(label="Anything else?", style=discord.TextStyle.long, required=False, max_length=1000)
        self.add_item(self.reason)
        self.add_item(self.experience)
        self.add_item(self.other)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        settings = get_guild_settings(guild.id)
        target_id = settings.get('application_channel')
        embed = discord.Embed(title="New Application", color=0x3498db)
        embed.set_author(name=str(interaction.user), icon_url=getattr(interaction.user, 'display_avatar', None) or None)
        embed.add_field(name="Applicant", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        embed.add_field(name="Why", value=self.reason.value or '(none)', inline=False)
        embed.add_field(name="Experience", value=self.experience.value or '(none)', inline=False)
        embed.add_field(name="Other", value=self.other.value or '(none)', inline=False)
        embed.set_footer(text=f"Server: {guild.name} ({guild.id})")
        embed.timestamp = discord.utils.utcnow()

        if not target_id:
            return await interaction.followup.send('Application channel is not configured. Ask an admin to set it with /set-application-channel.', ephemeral=True)

        target = None
        if hasattr(interaction.client, 'fetch_channel'):
            try:
                target = await interaction.client.fetch_channel(int(target_id))
            except Exception:
                target = None
        else:
            try:
                target = await interaction.client.channels.fetch(int(target_id))
            except Exception:
                target = None

        if not target:
            return await interaction.followup.send('Configured application channel not available. Ask an admin to reconfigure.', ephemeral=True)

        # Post to channel
        try:
            await target.send({ 'embeds': [embed] })
        except Exception:
            await interaction.followup.send('Failed to post application to the configured channel.', ephemeral=True)
            return

        # DM applicant a copy; handle closed DMs
        try:
            dm = await interaction.user.create_dm()
            await dm.send('Thanks — your application has been submitted. Here is a copy:')
            await dm.send({ 'embeds': [embed] })
            await interaction.followup.send("Application submitted and a copy was DM'd to you.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send('Application submitted, but I could not DM you — your DMs appear to be closed.', ephemeral=True)
        except Exception:
            await interaction.followup.send('Application submitted. Failed to DM a copy.', ephemeral=True)


class ApplicationsCog(commands.Cog):
    """Manage server applications: collect via modal and post to configured channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='apply', description='Submit an application to join the server')
    async def apply(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ApplicationModal(self.bot))

    @app_commands.command(name='set-application-channel', description='Set channel to receive applications')
    @app_commands.describe(channel='Target text channel')
    async def set_application_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # permission: manage_guild or owner
        if not (interaction.user.guild_permissions.manage_guild or str(interaction.user.id) in (self.bot.owner_id and [str(self.bot.owner_id)] or [])):
            return await interaction.response.send_message('Require Manage Guild or owner.', ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        settings['application_channel'] = str(channel.id)
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message(f'Application channel set to {channel.mention}', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationsCog(bot))
