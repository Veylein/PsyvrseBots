import asyncio
import os
import sqlite3
import time
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

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
        active: bool = True
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

    # ---------------- PREFIX COMMANDS ----------------
    @commands.command(name="warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if not self._is_mod(ctx.author):
            await ctx.send("You do not have permission to warn members.")
            return
        inf_id = self._record_infraction(member.id, ctx.author.id, "warn", reason)
        await ctx.send(f"{member.mention} has been warned. (id: {inf_id})")

    @commands.command(name="mute")
    async def mute(self, ctx: commands.Context, member: discord.Member, duration_minutes: Optional[int] = None, *, reason: str = "No reason provided"):
        if not self._is_mod(ctx.author):
            await ctx.send("You do not have permission to mute members.")
            return

        role = await self._ensure_muted_role(ctx.guild)
        if not role:
            await ctx.send("Failed to find or create Muted role.")
            return

        await member.add_roles(role, reason=reason)
        if duration_minutes:
            duration = duration_minutes * 60
            inf_id = self._record_infraction(member.id, ctx.author.id, "mute", reason, duration_seconds=duration)
            task = asyncio.create_task(self._apply_timed_unmute(ctx.guild, member, role, inf_id, duration))
            self._tasks[inf_id] = task
            await ctx.send(f"{member.mention} muted for {duration_minutes} minute(s). (id: {inf_id})")
        else:
            inf_id = self._record_infraction(member.id, ctx.author.id, "mute", reason)
            await ctx.send(f"{member.mention} muted indefinitely. (id: {inf_id})")

    @commands.command(name="unmute")
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Unmuted by staff"):
        if not self._is_mod(ctx.author):
            await ctx.send("You do not have permission to unmute members.")
            return

        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            await ctx.send("Muted role not found.")
            return

        await member.remove_roles(role, reason=reason)
        for r in self._list_infractions_for(member.id):
            if r[2] == "mute" and r[6] == 1:
                self._set_infraction_inactive(r[0])
        await ctx.send(f"{member.mention} has been unmuted.")

    @commands.command(name="infractions")
    async def infractions(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        rows = self._list_infractions_for(target.id)
        if not rows:
            await ctx.send(f"No infractions found for {target}.")
            return
        lines = []
        for r in rows[:20]:
            ts = datetime.fromtimestamp(r[4]).isoformat()
            active = "active" if r[6] == 1 else "inactive"
            lines.append(f"#{r[0]} {r[2]} by <@{r[1]}> at {ts} — {r[3] or ''} ({active})")
        await ctx.send(f"Infractions for {target} (most recent {min(20, len(rows))}):\n" + "\n".join(lines))

    # ---------------- SLASH COMMANDS ----------------
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not self._is_mod(interaction.user):
            await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
            return
        inf_id = self._record_infraction(member.id, interaction.user.id, "warn", reason)
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
            inf_id = self._record_infraction(member.id, interaction.user.id, "mute", reason, duration_seconds=duration)
            asyncio.create_task(self._apply_timed_unmute(interaction.guild, member, role, inf_id, duration))
            await interaction.response.send_message(f"{member.mention} muted for {minutes} minute(s). (id: {inf_id})", ephemeral=True)
        else:
            inf_id = self._record_infraction(member.id, interaction.user.id, "mute", reason)
            await interaction.response.send_message(f"{member.mention} muted indefinitely. (id: {inf_id})", ephemeral=True)

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


# ---------------- SETUP ----------------
async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
    await bot.tree.sync()  # ensures slash commands appear
