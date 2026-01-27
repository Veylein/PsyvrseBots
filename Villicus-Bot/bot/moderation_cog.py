import asyncio
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands


DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_PATH = os.path.join(DB_DIR, 'moderation.db')


def _ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS infractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            timestamp INTEGER NOT NULL,
            duration_seconds INTEGER,
            active INTEGER NOT NULL DEFAULT 1
        )
        '''
    )
    conn.commit()
    conn.close()


class ModerationCog(commands.Cog):
    """Moderation utilities: warn, mute, unmute, kick, ban, infractions and audit logging."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _ensure_db()
        self._tasks = {}

    def _record_infraction(self, user_id: int, moderator_id: int, action: str, reason: Optional[str] = None, duration_seconds: Optional[int] = None, active: bool = True):
        ts = int(time.time())
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO infractions (user_id, moderator_id, action, reason, timestamp, duration_seconds, active) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, moderator_id, action, reason, ts, duration_seconds, 1 if active else 0)
        )
        conn.commit()
        rowid = cur.lastrowid
        conn.close()
        return rowid

    def _set_infraction_inactive(self, infraction_id: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('UPDATE infractions SET active = 0 WHERE id = ?', (infraction_id,))
        conn.commit()
        conn.close()

    def _list_infractions_for(self, user_id: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT id, moderator_id, action, reason, timestamp, duration_seconds, active FROM infractions WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
        rows = cur.fetchall()
        conn.close()
        return rows

    async def _ensure_muted_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        # find existing role
        role = discord.utils.get(guild.roles, name='Muted')
        try:
            if role is None:
                perms = discord.Permissions(send_messages=False, speak=False)
                role = await guild.create_role(name='Muted', permissions=perms, reason='Created by Villicus moderation')
            # try to apply channel overrides if we have permission
            if guild.me and guild.me.guild_permissions.manage_roles and guild.me.guild_permissions.manage_channels:
                for ch in guild.text_channels:
                    try:
                        await ch.set_permissions(role, send_messages=False, add_reactions=False)
                    except Exception:
                        pass
            return role
        except Exception:
            return None

    async def _apply_timed_unmute(self, guild: discord.Guild, member: discord.Member, role: discord.Role, infraction_id: int, duration_seconds: int):
        try:
            await asyncio.sleep(duration_seconds)
            try:
                await member.remove_roles(role, reason='Timed mute expired')
            except Exception:
                pass
            self._set_infraction_inactive(infraction_id)
        except asyncio.CancelledError:
            pass

    def _check_mod_perms(self, ctx: commands.Context) -> bool:
        if getattr(ctx.author, 'guild_permissions', None) and ctx.author.guild_permissions.moderate_members:
            return True
        if getattr(ctx.author, 'guild_permissions', None) and (ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members or ctx.author.guild_permissions.manage_messages):
            return True
        return False

    @commands.command(name='warn')
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = 'No reason provided'):
        """Warn a member and record the infraction."""
        if not self._check_mod_perms(ctx):
            await ctx.send('You do not have permission to warn members.')
            return
        inf_id = self._record_infraction(member.id, ctx.author.id, 'warn', reason)
        await ctx.send(f'{member.mention} has been warned. (id: {inf_id})')

    @app_commands.command(name='warn')
    @app_commands.describe(member='Member to warn', reason='Reason for the warning')
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = 'No reason provided'):
        ctx = await commands.Context.from_interaction(interaction)
        if not self._check_mod_perms(ctx):
            await interaction.response.send_message('You do not have permission to warn members.', ephemeral=True)
            return
        inf_id = self._record_infraction(member.id, interaction.user.id, 'warn', reason)
        await interaction.response.send_message(f'{member.mention} warned (id: {inf_id}).')

    @commands.command(name='mute')
    async def mute(self, ctx: commands.Context, member: discord.Member, duration_minutes: Optional[int] = None, *, reason: str = 'No reason provided'):
        """Mute a member, optionally for a specified duration in minutes."""
        if not self._check_mod_perms(ctx):
            await ctx.send('You do not have permission to mute members.')
            return
        role = await self._ensure_muted_role(ctx.guild)
        if role is None:
            await ctx.send('Failed to create or find Muted role.')
            return
        try:
            await member.add_roles(role, reason=reason)
        except Exception as e:
            await ctx.send(f'Failed to add Muted role: {e}')
            return
        duration_seconds = None
        inf_id = None
        if duration_minutes:
            duration_seconds = int(duration_minutes) * 60
            inf_id = self._record_infraction(member.id, ctx.author.id, 'mute', reason, duration_seconds=duration_seconds)
            task = asyncio.create_task(self._apply_timed_unmute(ctx.guild, member, role, inf_id, duration_seconds))
            self._tasks[inf_id] = task
            await ctx.send(f'{member.mention} muted for {duration_minutes} minute(s). (id: {inf_id})')
        else:
            inf_id = self._record_infraction(member.id, ctx.author.id, 'mute', reason)
            await ctx.send(f'{member.mention} muted indefinitely. (id: {inf_id})')

    @app_commands.command(name='mute')
    @app_commands.describe(member='Member to mute', minutes='Duration in minutes', reason='Reason for mute')
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, minutes: Optional[int] = None, reason: str = 'No reason provided'):
        ctx = await commands.Context.from_interaction(interaction)
        await interaction.response.defer(ephemeral=True)
        if not self._check_mod_perms(ctx):
            await interaction.followup.send('You do not have permission to mute members.', ephemeral=True)
            return
        role = await self._ensure_muted_role(interaction.guild)
        if role is None:
            await interaction.followup.send('Failed to create or find Muted role.', ephemeral=True)
            return
        try:
            await member.add_roles(role, reason=reason)
        except Exception as e:
            await interaction.followup.send(f'Failed to add Muted role: {e}', ephemeral=True)
            return
        duration_seconds = None
        if minutes:
            duration_seconds = int(minutes) * 60
            inf_id = self._record_infraction(member.id, interaction.user.id, 'mute', reason, duration_seconds=duration_seconds)
            task = asyncio.create_task(self._apply_timed_unmute(interaction.guild, member, role, inf_id, duration_seconds))
            self._tasks[inf_id] = task
            await interaction.followup.send(f'{member.mention} muted for {minutes} minute(s). (id: {inf_id})', ephemeral=True)
        else:
            inf_id = self._record_infraction(member.id, interaction.user.id, 'mute', reason)
            await interaction.followup.send(f'{member.mention} muted indefinitely. (id: {inf_id})', ephemeral=True)

    @commands.command(name='unmute')
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = 'Unmuted by staff'):
        if not self._check_mod_perms(ctx):
            await ctx.send('You do not have permission to unmute members.')
            return
        role = discord.utils.get(ctx.guild.roles, name='Muted')
        if role is None:
            await ctx.send('Muted role not found.')
            return
        try:
            await member.remove_roles(role, reason=reason)
        except Exception as e:
            await ctx.send(f'Failed to remove role: {e}')
            return
        # mark any active mute infractions inactive
        rows = self._list_infractions_for(member.id)
        for r in rows:
            if r[2] == 'mute' and r[6] == 1:
                self._set_infraction_inactive(r[0])
        await ctx.send(f'{member.mention} has been unmuted.')

    @app_commands.command(name='unmute')
    @app_commands.describe(member='Member to unmute', reason='Reason for unmute')
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = 'Unmuted by staff'):
        ctx = await commands.Context.from_interaction(interaction)
        await interaction.response.defer(ephemeral=True)
        if not self._check_mod_perms(ctx):
            await interaction.followup.send('You do not have permission to unmute members.', ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name='Muted')
        if role is None:
            await interaction.followup.send('Muted role not found.', ephemeral=True)
            return
        try:
            await member.remove_roles(role, reason=reason)
        except Exception as e:
            await interaction.followup.send(f'Failed to remove role: {e}', ephemeral=True)
            return
        rows = self._list_infractions_for(member.id)
        for r in rows:
            if r[2] == 'mute' and r[6] == 1:
                self._set_infraction_inactive(r[0])
        await interaction.followup.send(f'{member.mention} has been unmuted.', ephemeral=True)

    @commands.command(name='infractions')
    async def infractions(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        rows = self._list_infractions_for(target.id)
        if not rows:
            await ctx.send(f'No infractions found for {target}.')
            return
        lines = []
        for r in rows[:20]:
            ts = datetime.fromtimestamp(r[4]).isoformat()
            active = 'active' if r[6] == 1 else 'inactive'
            lines.append(f"#{r[0]} {r[2]} by <@{r[1]}> at {ts} — {r[3] or ''} ({active})")
        msg = '\n'.join(lines)
        await ctx.send(f'Infractions for {target} (most recent {min(20, len(rows))}):\n{msg}')


async def setup(bot: commands.Bot):
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
