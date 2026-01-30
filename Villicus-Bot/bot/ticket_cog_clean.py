import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import datetime
import io

from core.config import get_guild_settings, save_guild_settings


class TicketCog(commands.Cog):
    """Clean Ticketing cog — create private ticket channels, close them and post transcripts."""

    ticket_group = app_commands.Group(name='ticket', description='Ticketing commands')

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

    # Note: `ticket_group` is defined as a class-level `app_commands.Group` above.
    # We don't define a bare group callback here; the group exists to namespace subcommands.

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

    @app_commands.default_permissions(manage_guild=True)
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

    @app_commands.default_permissions(manage_guild=True)
    @ticket_group.command(name='panel', description='Post a ticket creation panel (click to open ticket)')
    @app_commands.describe(channel='Channel to post the panel in (defaults to current)')
    async def ticket_panel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message('Manage Guild required to post a ticket panel.', ephemeral=True)
        ch = channel or interaction.channel

        class _PanelView(discord.ui.View):
            def __init__(self, outer: 'TicketCog'):
                super().__init__(timeout=None)
                self.outer = outer

            @discord.ui.button(label='Create Ticket', style=discord.ButtonStyle.primary, emoji='🎫')
            async def create_button(self, button: discord.ui.Button, button_interaction: discord.Interaction):
                await button_interaction.response.defer(ephemeral=True)
                # prevent duplicate open tickets per user
                settings = get_guild_settings(button_interaction.guild.id)
                tickets = settings.get('open_tickets', {})
                for tid, meta in tickets.items():
                    try:
                        if meta.get('owner') == button_interaction.user.id:
                            # user already has ticket
                            chobj = button_interaction.guild.get_channel(int(tid))
                            if chobj:
                                return await button_interaction.followup.send(f'You already have a ticket: {chobj.mention}', ephemeral=True)
                    except Exception:
                        continue
                try:
                    new = await self.outer._create_ticket_channel(button_interaction.guild, button_interaction.user)
                    try:
                        await new.send(f'{button_interaction.user.mention} created this ticket via panel.')
                    except Exception:
                        pass
                    await button_interaction.followup.send(f'Ticket created: {new.mention}', ephemeral=True)
                except Exception as e:
                    await button_interaction.followup.send(f'Failed to create ticket: {e}', ephemeral=True)

        embed = discord.Embed(title='Open a Support Ticket', description='Click the button below to create a private ticket channel.', color=discord.Color.green())
        try:
            await ch.send(embed=embed, view=_PanelView(self))
            await interaction.response.send_message(f'Ticket panel posted in {ch.mention}', ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f'Failed to post panel: {e}', ephemeral=True)


async def setup(bot: commands.Bot):
    # Avoid adding the cog if another module already loaded it
    if bot.get_cog('TicketCog') is None:
        await bot.add_cog(TicketCog(bot))
