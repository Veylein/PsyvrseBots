import asyncio
import random
import time
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from core.config import get_guild_settings, save_guild_settings


class GiveawayCog(commands.Cog):
    """Persistent giveaways: create, end, reroll. Stores active giveaways in
    `guild_settings` under key `giveaways` as message_id -> {channel_id, prize, host_id, ends_at, winners}
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks = {}  # (guild_id, message_id) -> asyncio.Task
        # Loader is scheduled from the async setup hook to avoid accessing
        # `bot.loop` in synchronous contexts (see setup below).
        pass

    async def _load_giveaways(self):
        await self.bot.wait_until_ready()
        # Iterate guild settings and schedule pending giveaways
        for guild in self.bot.guilds:
            try:
                settings = get_guild_settings(guild.id)
                giveaways = settings.get('giveaways', {}) or {}
                for msg_id_str, g in list(giveaways.items()):
                    try:
                        msg_id = int(msg_id_str)
                    except Exception:
                        continue
                    if g.get('ended'):
                        continue
                    ends_at = g.get('ends_at')
                    if not ends_at:
                        continue
                    delay = ends_at - int(time.time())
                    if delay <= 0:
                        # end immediately
                        asyncio.create_task(self._end_giveaway(guild.id, msg_id))
                    else:
                        task = asyncio.create_task(self._wait_and_end(guild.id, msg_id, delay))
                        self._tasks[(guild.id, msg_id)] = task
            except Exception:
                continue

    async def _wait_and_end(self, guild_id: int, message_id: int, delay: int):
        try:
            await asyncio.sleep(max(0, int(delay)))
            await self._end_giveaway(guild_id, message_id)
        except asyncio.CancelledError:
            return
        except Exception:
            return

    def _persist(self, guild_id: int, giveaways: dict):
        settings = get_guild_settings(guild_id)
        settings['giveaways'] = giveaways
        save_guild_settings(guild_id, settings)

    @app_commands.command(name='giveaway', description='Create a giveaway in this channel')
    @app_commands.describe(duration_minutes='Duration in minutes', prize='Prize to give', winners='Number of winners')
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_create(self, interaction: discord.Interaction, duration_minutes: int, prize: str, winners: int = 1):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send('Manage Guild or Administrator required to create giveaways.', ephemeral=True)
        if duration_minutes <= 0:
            return await interaction.followup.send('Duration must be a positive integer.', ephemeral=True)
        if winners <= 0:
            return await interaction.followup.send('Winners must be a positive integer.', ephemeral=True)

        ends_at = int(time.time()) + int(duration_minutes) * 60
        embed = discord.Embed(title='🎉 Giveaway!', description=prize, color=discord.Color.blurple())
        embed.add_field(name='Hosted by', value=interaction.user.mention)
        embed.add_field(name='Winners', value=str(winners))
        embed.set_footer(text=f'Ends in {duration_minutes} minute(s)')

        channel = interaction.channel
        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction('🎉')
        except Exception as e:
            return await interaction.followup.send(f'Failed to create giveaway message: {e}', ephemeral=True)

        settings = get_guild_settings(interaction.guild.id)
        giveaways = settings.get('giveaways', {}) or {}
        giveaways[str(msg.id)] = {
            'channel_id': channel.id,
            'prize': prize,
            'host_id': interaction.user.id,
            'ends_at': ends_at,
            'winners': winners,
            'ended': False,
        }
        self._persist(interaction.guild.id, giveaways)

        delay = ends_at - int(time.time())
        task = asyncio.create_task(self._wait_and_end(interaction.guild.id, msg.id, delay))
        self._tasks[(interaction.guild.id, msg.id)] = task

        await interaction.followup.send(f'Giveaway created: {msg.jump_url}', ephemeral=True)

    async def _end_giveaway(self, guild_id: int, message_id: int):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        settings = get_guild_settings(guild_id)
        giveaways = settings.get('giveaways', {}) or {}
        g = giveaways.get(str(message_id))
        if not g or g.get('ended'):
            return
        channel = guild.get_channel(g.get('channel_id'))
        if not channel:
            # mark ended anyway
            g['ended'] = True
            giveaways[str(message_id)] = g
            self._persist(guild_id, giveaways)
            return
        try:
            msg = await channel.fetch_message(message_id)
        except Exception:
            g['ended'] = True
            giveaways[str(message_id)] = g
            self._persist(guild_id, giveaways)
            return

        entrants = []
        for reaction in msg.reactions:
            try:
                if str(reaction.emoji) == '🎉':
                    users = [u async for u in reaction.users()]
                    entrants = [u for u in users if not u.bot]
                    break
            except Exception:
                continue

        winners = []
        if entrants:
            count = min(int(g.get('winners', 1)), len(entrants))
            try:
                winners = random.sample(entrants, count)
            except Exception:
                # fallback deterministic selection
                winners = entrants[:count]

        if not winners:
            await channel.send(f'Giveaway for **{g.get("prize")}** ended — no valid entrants.')
        else:
            await channel.send(f'🎉 Giveaway for **{g.get("prize")}** ended! Winners: {", ".join(w.mention for w in winners)}')

        g['ended'] = True
        giveaways[str(message_id)] = g
        self._persist(guild_id, giveaways)

        taskkey = (guild_id, message_id)
        t = self._tasks.pop(taskkey, None)
        if t:
            t.cancel()

    @app_commands.command(name='giveaway_end', description='End a running giveaway by message id')
    @app_commands.describe(message_id='Message ID of the giveaway to end')
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_end(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send('Manage Guild or Administrator required.', ephemeral=True)
        await self._end_giveaway(interaction.guild.id, message_id)
        await interaction.followup.send('Giveaway ended (if it existed).', ephemeral=True)

    @app_commands.command(name='giveaway_reroll', description='Reroll winners for a past giveaway')
    @app_commands.describe(message_id='Message ID of the ended giveaway')
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send('Manage Guild or Administrator required.', ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        giveaways = settings.get('giveaways', {}) or {}
        g = giveaways.get(str(message_id))
        if not g:
            return await interaction.followup.send('Giveaway not found.', ephemeral=True)
        channel = interaction.guild.get_channel(g.get('channel_id'))
        if not channel:
            return await interaction.followup.send('Giveaway channel not found.', ephemeral=True)
        try:
            msg = await channel.fetch_message(message_id)
        except Exception:
            return await interaction.followup.send('Giveaway message not available.', ephemeral=True)

        entrants = []
        for reaction in msg.reactions:
            try:
                if str(reaction.emoji) == '🎉':
                    users = [u async for u in reaction.users()]
                    entrants = [u for u in users if not u.bot]
                    break
            except Exception:
                continue

        if not entrants:
            return await interaction.followup.send('No entrants to choose from.', ephemeral=True)

        count = min(int(g.get('winners', 1)), len(entrants))
        try:
            winners = random.sample(entrants, count)
        except Exception:
            winners = entrants[:count]

        await interaction.followup.send(f'Reroll winners: {", ".join(w.mention for w in winners)}', ephemeral=True)


async def setup(bot: commands.Bot):
    cog = GiveawayCog(bot)
    await bot.add_cog(cog)
    # Schedule the giveaway loader from this async setup context so it uses
    # the active event loop instead of accessing `bot.loop` from __init__.
    try:
        asyncio.create_task(cog._load_giveaways())
    except Exception:
        pass
    # Register slash commands (best-effort)
    try:
        bot.tree.add_command(app_commands.Command(name='giveaway', description='Create a giveaway', callback=cog.giveaway_create, default_member_permissions=discord.Permissions(manage_guild=True)))
    except Exception:
        pass
    try:
        bot.tree.add_command(app_commands.Command(name='giveaway_end', description='End a giveaway', callback=cog.giveaway_end, default_member_permissions=discord.Permissions(manage_guild=True)))
    except Exception:
        pass
    try:
        bot.tree.add_command(app_commands.Command(name='giveaway_reroll', description='Reroll giveaway winners', callback=cog.giveaway_reroll, default_member_permissions=discord.Permissions(manage_guild=True)))
    except Exception:
        pass
