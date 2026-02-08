import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from core.config import get_guild_settings, save_guild_settings
from core import ui as core_ui


LOG_EVENTS = [
    'message_delete',
    'message_edit',
    'member_update',
]


class LogConfigGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name='logconfig', description='Configure server logging')

    @app_commands.command(name='channel', description='Set the logging channel')
    @app_commands.describe(channel='Channel to send logs to (text channel)')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        settings['log_channel'] = channel.id
        save_guild_settings(interaction.guild.id, settings)
        await core_ui.send(interaction, embed=core_ui.success_embed("Log channel set", f"Logs will be sent to {channel.mention}."), ephemeral=True)

    @app_commands.command(name='enable', description='Enable logging for an event')
    @app_commands.describe(event='Event to enable')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def enable(self, interaction: discord.Interaction, event: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        if event not in LOG_EVENTS:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Unknown event", f"Valid events: {', '.join(LOG_EVENTS)}"), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        evs = settings.get('log_events', {})
        evs[event] = True
        settings['log_events'] = evs
        save_guild_settings(interaction.guild.id, settings)
        await core_ui.send(interaction, embed=core_ui.success_embed("Logging enabled", f"Enabled logging for {event}."), ephemeral=True)

    @app_commands.command(name='disable', description='Disable logging for an event')
    @app_commands.describe(event='Event to disable')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def disable(self, interaction: discord.Interaction, event: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        if event not in LOG_EVENTS:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Unknown event", f"Valid events: {', '.join(LOG_EVENTS)}"), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        evs = settings.get('log_events', {})
        evs[event] = False
        settings['log_events'] = evs
        save_guild_settings(interaction.guild.id, settings)
        await core_ui.send(interaction, embed=core_ui.success_embed("Logging disabled", f"Disabled logging for {event}."), ephemeral=True)

    @app_commands.command(name='status', description='Show logging settings')
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        settings = get_guild_settings(interaction.guild.id)
        chan = settings.get('log_channel')
        evs = settings.get('log_events', {})
        bot = interaction.client
        chan_display = bot.get_channel(chan).mention if chan and bot.get_channel(chan) else '(not set)'
        lines = [f'Log channel: {chan_display}']
        for e in LOG_EVENTS:
            lines.append(f'{e}: {"enabled" if evs.get(e) else "disabled"}')
        await core_ui.send(interaction, embed=core_ui.info_embed("Logging status", "
".join(lines)), ephemeral=True)


class LoggingCog(commands.Cog):
    """Configurable per-guild logging of common events."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild_id: int, embed: discord.Embed):
        settings = get_guild_settings(guild_id)
        chan_id = settings.get('log_channel')
        if not chan_id:
            return
        try:
            ch = self.bot.get_channel(int(chan_id))
            if ch:
                await ch.send(embed=embed)
        except Exception:
            pass

    # --- listeners ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        settings = get_guild_settings(message.guild.id)
        if not settings.get('log_events', {}).get('message_delete'):
            return
        emb = core_ui.brand_embed('Message deleted')
        emb.add_field(name='Author', value=f'{message.author} ({message.author.id})', inline=False)
        emb.add_field(name='Channel', value=message.channel.mention, inline=False)
        emb.add_field(name='Content', value=message.content or '(embed/attachment)', inline=False)
        await self._send_log(message.guild.id, emb)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild:
            return
        settings = get_guild_settings(before.guild.id)
        if not settings.get('log_events', {}).get('message_edit'):
            return
        emb = core_ui.brand_embed('Message edited')
        emb.add_field(name='Author', value=f'{before.author} ({before.author.id})', inline=False)
        emb.add_field(name='Channel', value=before.channel.mention, inline=False)
        emb.add_field(name='Before', value=before.content or '(embed/attachment)', inline=False)
        emb.add_field(name='After', value=after.content or '(embed/attachment)', inline=False)
        await self._send_log(before.guild.id, emb)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not before.guild:
            return
        settings = get_guild_settings(before.guild.id)
        if not settings.get('log_events', {}).get('member_update'):
            return
        changes = []
        if before.display_name != after.display_name:
            changes.append(f'Nickname: {before.display_name} -> {after.display_name}')
        if before.roles != after.roles:
            before_roles = ','.join([r.name for r in before.roles if r.name != '@everyone'])
            after_roles = ','.join([r.name for r in after.roles if r.name != '@everyone'])
            changes.append(f'Roles changed: {before_roles} -> {after_roles}')
        if not changes:
            return
        emb = core_ui.brand_embed('Member updated')
        emb.add_field(name='Member', value=f'{after} ({after.id})', inline=False)
        emb.add_field(name='Changes', value='
'.join(changes), inline=False)
        await self._send_log(before.guild.id, emb)


async def setup(bot: commands.Bot):
    cog = LoggingCog(bot)
    await bot.add_cog(cog)
    try:
        bot.tree.add_command(LogConfigGroup())
    except Exception:
        pass
