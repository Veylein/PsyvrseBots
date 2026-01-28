import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import datetime
import io

from core.config import get_guild_settings, save_guild_settings


class TicketCog(commands.Cog):
    """Clean Ticketing cog — create private ticket channels, close them and post transcripts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _create_ticket_channel(self, guild: discord.Guild, author: discord.Member, reason: Optional[str] = None):
        settings = get_guild_settings(guild.id)
        category_id = settings.get('ticket_category')
        staff_role_id = settings.get('ticket_staff_role')
        category = guild.get_channel(category_id) if category_id else None
        ts = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M')
        name = f'ticket-{author.name}-{ts}'
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if staff_role_id:
            role = guild.get_role(staff_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if guild.me and guild.me.guild_permissions.manage_roles:
            overwrites[guild.me] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(name=name, category=category, overwrites=overwrites, reason='Ticket created')
        tickets = settings.get('open_tickets', {})
        tickets[str(channel.id)] = {'owner': author.id, 'created_at': int(datetime.datetime.utcnow().timestamp()), 'reason': reason}
        settings['open_tickets'] = tickets
        save_guild_settings(guild.id, settings)
        return channel

    @app_commands.group(name='ticket', description='Ticketing commands')
    async def ticket_group(self, interaction: discord.Interaction):
        if interaction.subcommand_passed is None:
            await interaction.response.send_message('Use /ticket create, /ticket close, or /ticket settings', ephemeral=True)

    @ticket_group.command(name='create', description='Create a private ticket channel')
    @app_commands.describe(reason='Optional reason for the ticket')
    async def ticket_create(self, interaction: discord.Interaction, reason: Optional[str] = None):
        await interaction.response.defer(ephemeral=True)
        channel = await self._create_ticket_channel(interaction.guild, interaction.user, reason)
        try:
            await channel.send(f'{interaction.user.mention} created this ticket. Reason: {reason or "(none)"}')
        except Exception:
            pass
        await interaction.followup.send(f'Ticket created: {channel.mention}', ephemeral=True)

    @ticket_group.command(name='close', description='Close the current ticket (must be inside ticket channel)')
    @app_commands.describe(transcript_channel='Optional channel to post a transcript')
    async def ticket_close(self, interaction: discord.Interaction, transcript_channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True)
        ch = interaction.channel
        settings = get_guild_settings(interaction.guild.id)
        tickets = settings.get('open_tickets', {})
        if str(ch.id) not in tickets:
            return await interaction.followup.send('This channel is not a ticket managed by Villicus.', ephemeral=True)

        msgs = []
        try:
            async for m in ch.history(limit=None, oldest_first=True):
                time = m.created_at.isoformat() if m.created_at else 'unknown'
                author = f'{m.author} ({m.author.id})'
                content = m.content or ''
                msgs.append(f'[{time}] {author}: {content}')
        except Exception:
            pass

        transcript = '\n'.join(msgs) or '(no messages)'

        if transcript_channel:
            try:
                header = f'Transcript for {ch.name} (closed by {interaction.user}):'
                await transcript_channel.send(header)
                if len(transcript) > 1900:
                    bio = io.BytesIO(transcript.encode('utf-8'))
                    bio.seek(0)
                    await transcript_channel.send(file=discord.File(fp=bio, filename=f'transcript-{ch.id}.txt'))
                else:
                    await transcript_channel.send('```' + transcript + '```')
            except Exception:
                pass

        try:
            tickets.pop(str(ch.id), None)
            settings['open_tickets'] = tickets
            save_guild_settings(interaction.guild.id, settings)
        except Exception:
            pass

        try:
            await ch.delete(reason=f'Ticket closed by {interaction.user}')
        except Exception:
            pass
        await interaction.followup.send('Ticket closed.', ephemeral=True)

    @ticket_group.command(name='settings', description='Configure ticketing for this server')
    @app_commands.describe(category='Category for created tickets', staff_role='Role to give ticket access')
    async def ticket_settings(self, interaction: discord.Interaction, category: Optional[discord.CategoryChannel] = None, staff_role: Optional[discord.Role] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message('Manage Guild required.', ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        if category:
            settings['ticket_category'] = category.id
        if staff_role:
            settings['ticket_staff_role'] = staff_role.id
        save_guild_settings(interaction.guild.id, settings)
        await interaction.response.send_message('Ticket settings updated.', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
