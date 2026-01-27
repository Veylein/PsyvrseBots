import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from core.config import get_guild_settings, save_guild_settings


LOG_EVENTS = [
    'message_delete',
    'message_edit',
    'member_update',
]


class LoggingCog(commands.Cog):
    """Configurable per-guild logging of common events.

    Commands:
    - /logconfig channel <channel>  -> set log channel
    - /logconfig enable <event>     -> enable event logging
    - /logconfig disable <event>    -> disable event logging
    - /logconfig status             -> show current log settings
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild_id: int, embed: discord.Embed):
        settings = get_guild_settings(guild_id)
        chan_id = settings.get('log_channel')
        enabled = settings.get('log_events', {})
        if not chan_id:
            return
        # embed.author may be set by caller
        try:
            ch = self.bot.get_channel(int(chan_id))
            if ch:
                await ch.send(embed=embed)
        except Exception:
            pass

    # Implement a proper app_commands.Group for logconfig so subcommands register correctly
    class _LogConfigGroup(app_commands.Group):
        def __init__(self):
            super().__init__(name='logconfig', description='Configure server logging')

        @app_commands.command(name='channel', description='Set the logging channel')
        @app_commands.describe(channel='Channel to send logs to (text channel)')
        async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message('You need Manage Guild permission.', ephemeral=True)
            settings = get_guild_settings(interaction.guild.id)
            settings['log_channel'] = channel.id
            save_guild_settings(interaction.guild.id, settings)
            await interaction.response.send_message(f'Set log channel to {channel.mention}', ephemeral=True)

        @app_commands.command(name='enable', description='Enable logging for an event')
        @app_commands.describe(event='Event to enable')
        async def enable(self, interaction: discord.Interaction, event: str):
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message('You need Manage Guild permission.', ephemeral=True)
            if event not in LOG_EVENTS:
                return await interaction.response.send_message(f'Unknown event. Valid: {LOG_EVENTS}', ephemeral=True)
            settings = get_guild_settings(interaction.guild.id)
            evs = settings.get('log_events', {})
            evs[event] = True
            settings['log_events'] = evs
            save_guild_settings(interaction.guild.id, settings)
            await interaction.response.send_message(f'Enabled logging for {event}', ephemeral=True)

        @app_commands.command(name='disable', description='Disable logging for an event')
        @app_commands.describe(event='Event to disable')
        async def disable(self, interaction: discord.Interaction, event: str):
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message('You need Manage Guild permission.', ephemeral=True)
            if event not in LOG_EVENTS:
                return await interaction.response.send_message(f'Unknown event. Valid: {LOG_EVENTS}', ephemeral=True)
            settings = get_guild_settings(interaction.guild.id)
            evs = settings.get('log_events', {})
            evs[event] = False
            settings['log_events'] = evs
            save_guild_settings(interaction.guild.id, settings)
            await interaction.response.send_message(f'Disabled logging for {event}', ephemeral=True)

        @app_commands.command(name='status', description='Show logging settings')
        async def status(self, interaction: discord.Interaction):
            settings = get_guild_settings(interaction.guild.id)
            chan = settings.get('log_channel')
            evs = settings.get('log_events', {})
            bot = interaction.client
            lines = [f'Log channel: {bot.get_channel(chan).mention if chan and bot.get_channel(chan) else "(not set)"}']
            for e in LOG_EVENTS:
                lines.append(f'{e}: {"enabled" if evs.get(e) else "disabled"}')
            await interaction.response.send_message('\n'.join(lines), ephemeral=True)

    # --- listeners ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return
        settings = get_guild_settings(message.guild.id)
        if not settings.get('log_events', {}).get('message_delete'):
            return
        emb = discord.Embed(title='Message deleted', color=discord.Color.red())
        emb.add_field(name='Author', value=f'{message.author} ({message.author.id})', inline=False)
        emb.add_field(name='Channel', value=message.channel.mention, inline=False)
        emb.add_field(name='Content', value=message.content or '(embed/attachment)')
        await self._send_log(message.guild.id, emb)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild:
            return
        settings = get_guild_settings(before.guild.id)
        if not settings.get('log_events', {}).get('message_edit'):
            return
        emb = discord.Embed(title='Message edited', color=discord.Color.orange())
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
        emb = discord.Embed(title='Member updated', color=discord.Color.blue())
        emb.add_field(name='Member', value=f'{after} ({after.id})', inline=False)
        emb.add_field(name='Changes', value='\n'.join(changes), inline=False)
        await self._send_log(before.guild.id, emb)


async def setup(bot: commands.Bot):
    cog = LoggingCog(bot)
    await bot.add_cog(cog)
    # Register logconfig group as slash commands
    try:
        bot.tree.add_command(_LogConfigGroup())
    except Exception:
        pass
