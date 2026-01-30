import asyncio
import os
import sqlite3
import time
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands
import csv
import io

DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_PATH = os.path.join(DB_DIR, 'moderation.db')


def ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
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
    ''')
    conn.commit()
    conn.close()


class ModerationCog(commands.Cog):
    """Moderation utilities: warn, mute, unmute, and infractions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        ensure_db()
        self._tasks = {}

    # ---------------- Database Utilities ----------------
    def _record_infraction(
        self, user_id: int, moderator_id: int, action: str,
        reason: Optional[str] = None, duration_seconds: Optional[int] = None,
        active: bool = True, guild_id: Optional[int] = None
    ) -> int:
        ts = int(time.time())
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO infractions (user_id, moderator_id, action, reason, timestamp, duration_seconds, active) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, moderator_id, action, reason, ts, duration_seconds, 1 if active else 0)
        )
        inf_id = cur.lastrowid
        conn.commit()
        conn.close()
        # Send a moderation log embed to configured log channel (best-effort)
        try:
            if guild_id:
                log = self.bot.get_cog('LoggingCog')
                if log:
                    emb = discord.Embed(title='Infraction recorded', color=discord.Color.dark_red())
                    emb.add_field(name='Action', value=action, inline=False)
                    emb.add_field(name='User ID', value=str(user_id), inline=True)
                    emb.add_field(name='Moderator ID', value=str(moderator_id), inline=True)
                    if reason:
                        emb.add_field(name='Reason', value=reason, inline=False)
                    if duration_seconds:
                        emb.add_field(name='Duration (s)', value=str(duration_seconds), inline=True)
                    emb.set_footer(text=f'Infraction ID: {inf_id} | Timestamp: {ts}')
                    try:
                        # schedule async send
                        self.bot.loop.create_task(log._send_log(guild_id, emb))
                    except Exception:
                        pass
        except Exception:
            pass
        return inf_id

    def _set_infraction_inactive(self, inf_id: int):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('UPDATE infractions SET active = 0 WHERE id = ?', (inf_id,))
        conn.commit()
        conn.close()

    def _list_infractions_for(self, user_id: int):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            'SELECT id, moderator_id, action, reason, timestamp, duration_seconds, active '
            'FROM infractions WHERE user_id = ? ORDER BY timestamp DESC', (user_id,)
        ).fetchall()
        conn.close()
        return rows

    def _export_infractions_csv(self, user_id: int) -> bytes:
        """Return CSV bytes for infractions of a user."""
        rows = self._list_infractions_for(user_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'moderator_id', 'action', 'reason', 'timestamp', 'duration_seconds', 'active'])
        for r in rows:
            writer.writerow(list(r))
        return output.getvalue().encode('utf-8')

    # ---------------- Role & Mute Handling ----------------
    async def _ensure_muted_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        role = discord.utils.get(guild.roles, name="Muted")
        if role:
            return role
        try:
            perms = discord.Permissions(send_messages=False, speak=False)
            role = await guild.create_role(name="Muted", permissions=perms, reason="Moderation Cog")
            if guild.me.guild_permissions.manage_channels:
                for ch in guild.channels:
                    try:
                        await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                    except Exception:
                        pass
            return role
        except Exception:
            return None

    async def _apply_timed_unmute(self, guild: discord.Guild, member: discord.Member, role: discord.Role, inf_id: int, duration: int):
        try:
            await asyncio.sleep(duration)
            try:
                await member.remove_roles(role, reason="Timed mute expired")
            except Exception:
                pass
            self._set_infraction_inactive(inf_id)
        except asyncio.CancelledError:
            pass

    # ---------------- Permission Check ----------------
    def _is_mod(self, member: discord.Member) -> bool:
        perms = member.guild_permissions
        return perms.moderate_members or perms.kick_members or perms.ban_members or perms.manage_messages

    # Prefix commands removed — slash equivalents are used instead.

    # ---------------- SLASH COMMANDS ----------------
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
            return
        inf_id = self._record_infraction(member.id, interaction.user.id, "warn", reason, guild_id=interaction.guild.id)
        await interaction.response.send_message(f"{member.mention} warned (id: {inf_id}).", ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.describe(member="Member to mute", minutes="Duration in minutes", reason="Reason for mute")
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, minutes: Optional[int] = None, reason: str = "No reason provided"):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message("You do not have permission to mute members.", ephemeral=True)
            return

        role = await self._ensure_muted_role(interaction.guild)
        if not role:
            await interaction.response.send_message("Failed to find or create Muted role.", ephemeral=True)
            return

        await member.add_roles(role, reason=reason)

        if minutes:
            duration = minutes * 60
            inf_id = self._record_infraction(member.id, interaction.user.id, "mute", reason, duration_seconds=duration, guild_id=interaction.guild.id)
            asyncio.create_task(self._apply_timed_unmute(interaction.guild, member, role, inf_id, duration))
            await interaction.response.send_message(f"{member.mention} muted for {minutes} minute(s). (id: {inf_id})", ephemeral=True)
        else:
            inf_id = self._record_infraction(member.id, interaction.user.id, "mute", reason, guild_id=interaction.guild.id)
            await interaction.response.send_message(f"{member.mention} muted indefinitely. (id: {inf_id})", ephemeral=True)

    @app_commands.command(name="timeout", description="Apply communication timeout to a member")
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason for timeout")
    async def timeout_slash(self, interaction: discord.Interaction, member: discord.Member, minutes: Optional[int] = None, reason: str = "Timed out by staff"):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message("You do not have permission to timeout members.", ephemeral=True)
            return
        if minutes is None or minutes <= 0:
            await interaction.response.send_message("Please specify a timeout duration in minutes.", ephemeral=True)
            return
        try:
            from datetime import datetime, timedelta
            until = datetime.utcnow() + timedelta(minutes=int(minutes))
            await member.edit(communication_disabled_until=until, reason=reason)
            inf_id = self._record_infraction(member.id, interaction.user.id, 'timeout', reason, duration_seconds=int(minutes) * 60, guild_id=interaction.guild.id)
            await interaction.response.send_message(f"{member.mention} timed out for {minutes} minute(s). (id: {inf_id})", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to apply timeout: {e}", ephemeral=True)

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="Member to unmute", reason="Reason for unmute")
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Unmuted by staff"):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message("You do not have permission to unmute members.", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not role:
            await interaction.response.send_message("Muted role not found.", ephemeral=True)
            return

        await member.remove_roles(role, reason=reason)
        for r in self._list_infractions_for(member.id):
            if r[2] == "mute" and r[6] == 1:
                self._set_infraction_inactive(r[0])
        await interaction.response.send_message(f"{member.mention} has been unmuted.", ephemeral=True)

    @app_commands.command(name="infractions", description="List infractions for a user")
    @app_commands.describe(member="Member to view infractions for (defaults to you)")
    async def infractions_slash(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=True)
        target = member or interaction.user
        rows = self._list_infractions_for(target.id)
        if not rows:
            return await interaction.followup.send(f"No infractions found for {target}.", ephemeral=True)
        lines = []
        for r in rows[:20]:
            ts = datetime.fromtimestamp(r[4]).isoformat()
            active = "active" if r[6] == 1 else "inactive"
            lines.append(f"#{r[0]} {r[2]} by <@{r[1]}> at {ts} — {r[3] or ''} ({active})")
        await interaction.followup.send(f"Infractions for {target} (most recent {min(20, len(rows))}):\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name='export_infractions', description='Export infractions for a user as CSV')
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(member='Member to export infractions for (defaults to you)')
    async def export_infractions_slash(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message('You do not have permission to export infractions.', ephemeral=True)
            return
        target = member or interaction.user
        csv_bytes = self._export_infractions_csv(target.id)
        if not csv_bytes:
            return await interaction.response.send_message('No infractions found.', ephemeral=True)
        bio = io.BytesIO(csv_bytes)
        bio.seek(0)
        await interaction.response.send_message(file=discord.File(fp=bio, filename=f'infractions-{target.id}.csv'), ephemeral=True)


# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
    # Register app (slash) commands onto the tree but do NOT call `bot.tree.sync()` here;
    # the main bot (`start_bot`) performs a sync in `on_ready()` when the application_id is available.
    try:
        try:
            bot.tree.add_command(app_commands.Command(name='warn', description='Warn a member', callback=cog.warn_slash, default_member_permissions=discord.Permissions(moderate_members=True)))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='mute', description='Mute a member', callback=cog.mute_slash, default_member_permissions=discord.Permissions(manage_messages=True)))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='unmute', description='Unmute a member', callback=cog.unmute_slash, default_member_permissions=discord.Permissions(manage_messages=True)))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='timeout', description='Timeout a member', callback=cog.timeout_slash, default_member_permissions=discord.Permissions(moderate_members=True)))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='infractions', description='List infractions for a user', callback=cog.infractions_slash))
        except Exception:
            pass
    except Exception:
        # best-effort registration; continue even if it fails
        pass
