import asyncio
import re
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from core.config import get_guild_settings, save_guild_settings
from core import ui as core_ui

RANKS = ['Helper', 'Moderator', 'Senior Moderator', 'Supervisor', 'Administrator']


class AdminCog(commands.Cog):
    """Full moderation and admin commands: kick/ban/softban/unban/massban, channel tools,
    staff management, emoji locking and utility commands.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild_id: int, embed: discord.Embed):
        log = self.bot.get_cog('LoggingCog')
        if log:
            try:
                await log._send_log(guild_id, embed)
            except Exception:
                pass

    # --- Listeners for emoji locks ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        settings = get_guild_settings(guild.id)
        locks = settings.get('emoji_locks', {})
        if not locks:
            return
        custom_matches = re.findall(r'<a?:[A-Za-z0-9_]+:(\d+)>', message.content)
        member = message.author
        for emoji_key, role_id in locks.items():
            try:
                role = guild.get_role(role_id)
                if not role:
                    continue
                if emoji_key.isdigit():
                    if emoji_key in custom_matches and role not in member.roles:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return
                else:
                    if emoji_key in message.content and role not in member.roles:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return
            except Exception:
                continue

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        settings = get_guild_settings(guild.id)
        locks = settings.get('emoji_locks', {})
        if not locks:
            return
        eid = getattr(payload.emoji, 'id', None)
        name = getattr(payload.emoji, 'name', None)
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        for emoji_key, role_id in locks.items():
            try:
                role = guild.get_role(role_id)
                if not role:
                    continue
                if emoji_key.isdigit():
                    if eid and str(eid) == emoji_key and role not in member.roles:
                        try:
                            channel = self.bot.get_channel(payload.channel_id)
                            message = await channel.fetch_message(payload.message_id)
                            await message.remove_reaction(payload.emoji, member)
                        except Exception:
                            pass
                else:
                    if name and emoji_key == name and role not in member.roles:
                        try:
                            channel = self.bot.get_channel(payload.channel_id)
                            message = await channel.fetch_message(payload.message_id)
                            await message.remove_reaction(payload.emoji, member)
                        except Exception:
                            pass
            except Exception:
                pass

    # ---------------- SLASH COMMANDS ----------------
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = 'No reason provided'):
        if not interaction.user.guild_permissions.kick_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Kick Members permission required."), ephemeral=True)
        try:
            await member.kick(reason=reason)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'kick', reason, guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Kick",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason=reason,
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Member kicked", f"{member.mention} was kicked."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Kick failed", str(e)), ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="Member to ban", days="Delete messages from the last N days (0-7)", reason="Reason for the ban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, days: int = 0, reason: str = 'No reason provided'):
        if not interaction.user.guild_permissions.ban_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Ban Members permission required."), ephemeral=True)
        try:
            await member.ban(reason=reason, delete_message_days=days)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'ban', reason, guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Ban",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason=reason,
                extra_fields=[("Message Delete", f"{days} day(s)")],
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Member banned", f"{member.mention} was banned."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Ban failed", str(e)), ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user.")
    @app_commands.describe(user="User to unban", reason="Reason for the unban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban_slash(self, interaction: discord.Interaction, user: discord.User, reason: str = 'Unbanned by staff'):
        if not interaction.user.guild_permissions.ban_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Ban Members permission required."), ephemeral=True)
        try:
            bans = await interaction.guild.bans()
            target = None
            for entry in bans:
                if entry.user.id == user.id:
                    target = entry.user
                    break
            if not target:
                return await core_ui.send(interaction, embed=core_ui.warn_embed("Not found", "That user is not in the ban list."), ephemeral=True)
            await interaction.guild.unban(target, reason=reason)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(target.id, interaction.user.id, 'unban', reason, guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Unban",
                f"{target} ({target.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason=reason,
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("User unbanned", f"{target} was unbanned."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Unban failed", str(e)), ephemeral=True)

    @app_commands.command(name="clear", description="Purge messages from the current channel.")
    @app_commands.describe(amount="Number of messages to delete (1-200)")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def clear_slash(self, interaction: discord.Interaction, amount: int = 50):
        if not interaction.user.guild_permissions.manage_messages:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Messages permission required."), ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await core_ui.send(interaction, embed=core_ui.success_embed("Messages deleted", f"Deleted {len(deleted)} message(s)."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Purge failed", str(e)), ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel for @everyone.")
    @app_commands.describe(channel="Channel to lock (defaults to current)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def lock_slash(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        ch = channel or interaction.channel
        if not interaction.user.guild_permissions.manage_channels:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Channels permission required."), ephemeral=True)
        try:
            await ch.set_permissions(interaction.guild.default_role, send_messages=False)
            await core_ui.send(interaction, embed=core_ui.success_embed("Channel locked", f"{ch.mention} locked for @everyone."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Lock failed", str(e)), ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock a channel for @everyone.")
    @app_commands.describe(channel="Channel to unlock (defaults to current)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def unlock_slash(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        ch = channel or interaction.channel
        if not interaction.user.guild_permissions.manage_channels:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Channels permission required."), ephemeral=True)
        try:
            await ch.set_permissions(interaction.guild.default_role, send_messages=True)
            await core_ui.send(interaction, embed=core_ui.success_embed("Channel unlocked", f"{ch.mention} unlocked for @everyone."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Unlock failed", str(e)), ephemeral=True)

    @app_commands.command(name="brick", description="Apply the Brick role to a member.")
    @app_commands.describe(member="Member to brick", reason="Reason for the punishment")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def brick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = ''):
        if not interaction.user.guild_permissions.manage_roles:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Roles permission required."), ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name='Brick')
        if role is None:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Brick not configured", "Run /config punishments to create the Brick role."), ephemeral=True)
        try:
            await member.add_roles(role, reason=reason or f'Bricked by {interaction.user}')
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'brick', reason or f'Bricked by {interaction.user}', guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Brick",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason=reason or "Bricked by staff",
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Brick applied", f"{member.mention} has been bricked."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Brick failed", str(e)), ephemeral=True)

    @app_commands.command(name="demoji", description="Apply the Demoji role to a member.")
    @app_commands.describe(member="Member to apply Demoji to")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def demoji_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_roles:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Roles permission required."), ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name='Demoji')
        if role is None:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Demoji not configured", "Run /config punishments to create the Demoji role."), ephemeral=True)
        try:
            await member.add_roles(role, reason=f'Demoji by {interaction.user}')
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'demoji', f'Demoji by {interaction.user}', guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Demoji",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason="Demoji by staff",
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Demoji applied", f"{member.mention} now has Demoji."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Demoji failed", str(e)), ephemeral=True)

    @app_commands.command(name="emoji_lock", description="Lock an emoji to a specific role.")
    @app_commands.describe(emoji="Emoji or emoji ID", role="Role allowed to use the emoji")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def emoji_lock_slash(self, interaction: discord.Interaction, emoji: str, role: discord.Role):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        key = emoji
        m = re.match(r'<a?:[A-Za-z0-9_]+:(\d+)>', emoji)
        if m:
            key = m.group(1)
        elif emoji.isdigit():
            key = emoji
        else:
            key = emoji
        settings = get_guild_settings(interaction.guild.id)
        locks = settings.get('emoji_locks', {})
        locks[str(key)] = role.id
        settings['emoji_locks'] = locks
        save_guild_settings(interaction.guild.id, settings)
        await core_ui.send(interaction, embed=core_ui.success_embed("Emoji locked", f"{emoji} is now locked to {role.mention}."), ephemeral=True)

    @app_commands.command(name="emoji_unlock", description="Unlock a locked emoji.")
    @app_commands.describe(emoji="Emoji or emoji ID")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def emoji_unlock_slash(self, interaction: discord.Interaction, emoji: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        m = re.match(r'<a?:[A-Za-z0-9_]+:(\d+)>', emoji)
        if m:
            key = m.group(1)
        elif emoji.isdigit():
            key = emoji
        else:
            key = emoji
        settings = get_guild_settings(interaction.guild.id)
        locks = settings.get('emoji_locks', {})
        if str(key) in locks:
            locks.pop(str(key), None)
            settings['emoji_locks'] = locks
            save_guild_settings(interaction.guild.id, settings)
            await core_ui.send(interaction, embed=core_ui.success_embed("Emoji unlocked", f"{emoji} is now unlocked."), ephemeral=True)
            return
        found = None
        for k in list(locks.keys()):
            if k == emoji:
                found = k
                break
        if found:
            locks.pop(found, None)
            settings['emoji_locks'] = locks
            save_guild_settings(interaction.guild.id, settings)
            await core_ui.send(interaction, embed=core_ui.success_embed("Emoji unlocked", f"{emoji} is now unlocked."), ephemeral=True)
            return
        await core_ui.send(interaction, embed=core_ui.warn_embed("Not locked", "That emoji is not locked."), ephemeral=True)

    @app_commands.command(name="emoji_list", description="List all locked emojis.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def emoji_list_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Guild permission required."), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        locks = settings.get('emoji_locks', {})
        if not locks:
            return await core_ui.send(interaction, embed=core_ui.info_embed("Emoji locks", "No emoji locks configured."), ephemeral=True)
        lines = []
        for k, rid in locks.items():
            role = interaction.guild.get_role(rid)
            lines.append(f'{k} -> {role.name if role else rid}')
        await core_ui.send(interaction, embed=core_ui.info_embed("Emoji locks", "\n".join(lines)), ephemeral=True)

    @app_commands.command(name="softban", description="Softban a member (ban and immediate unban).")
    @app_commands.describe(member="Member to softban", reason="Reason for the softban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def softban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = 'Softban by staff'):
        if not interaction.user.guild_permissions.ban_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Ban Members permission required."), ephemeral=True)
        try:
            await member.ban(reason=reason, delete_message_days=1)
            await interaction.guild.unban(member, reason='Softban unban')
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'softban', reason, guild_id=interaction.guild.id)
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Softban",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                reason=reason,
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Member softbanned", f"{member.mention} was softbanned."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Softban failed", str(e)), ephemeral=True)

    @app_commands.command(name="massban", description="Massban members by criteria.")
    @app_commands.describe(criteria="Use role:<name> or account_age<days>")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def massban_slash(self, interaction: discord.Interaction, criteria: str):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        try:
            parts = criteria.split(':', 1)
            members = []
            if parts[0] == 'role' and len(parts) > 1:
                role_name = parts[1].strip()
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if not role:
                    return await core_ui.send(interaction, embed=core_ui.warn_embed("Role not found", "That role name does not exist."), ephemeral=True)
                members = [m for m in interaction.guild.members if role in m.roles and not m.bot]
            elif parts[0].startswith('account_age'):
                m = re.search(r'account_age<(?P<days>\d+)', criteria)
                if not m:
                    return await core_ui.send(interaction, embed=core_ui.warn_embed("Invalid filter", "Use account_age<days>."), ephemeral=True)
                days = int(m.group('days'))
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() - timedelta(days=days)
                members = [m for m in interaction.guild.members if m.joined_at and m.joined_at < cutoff and not m.bot]
            else:
                return await core_ui.send(interaction, embed=core_ui.warn_embed("Unsupported criteria", "Use role:<name> or account_age<days>."), ephemeral=True)
            count = 0
            for m in members:
                try:
                    await interaction.guild.ban(m, reason=f'Massban: {criteria}')
                    count += 1
                except Exception:
                    continue
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Massban",
                f"{count} members",
                f"{interaction.user} ({interaction.user.id})",
                reason=f"Criteria: {criteria}",
                extra_fields=[("Matched", str(len(members)))],
            ))
            await core_ui.send(interaction, embed=core_ui.warn_embed("Massban complete", f"Matched {len(members)} members, banned {count}."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Massban failed", str(e)), ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode for the current channel.")
    @app_commands.describe(seconds="Delay between messages (0-21600)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def slowmode_slash(self, interaction: discord.Interaction, seconds: int = 0):
        if not interaction.user.guild_permissions.manage_channels:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Manage Channels permission required."), ephemeral=True)
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            await core_ui.send(interaction, embed=core_ui.success_embed("Slowmode updated", f"Slowmode set to {seconds} seconds."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Slowmode failed", str(e)), ephemeral=True)

    @app_commands.command(name="clone", description="Clone a channel.")
    @app_commands.describe(channel="Channel to clone (defaults to current)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def clone_slash(self, interaction: discord.Interaction, channel: Optional[discord.abc.GuildChannel] = None):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        ch = channel or interaction.channel
        try:
            new = await ch.clone(reason=f'Cloned by {interaction.user}')
            await core_ui.send(interaction, embed=core_ui.success_embed("Channel cloned", f"{ch.mention} cloned to {new.mention}."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Clone failed", str(e)), ephemeral=True)

    @app_commands.command(name="deafen", description="Server deafen a member.")
    @app_commands.describe(member="Member to deafen", duration_minutes="Optional duration in minutes")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def deafen_slash(self, interaction: discord.Interaction, member: discord.Member, duration_minutes: Optional[int] = None):
        if not interaction.user.guild_permissions.moderate_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Moderate Members permission required."), ephemeral=True)
        try:
            await member.edit(deafen=True, reason=f'Deafened by {interaction.user}')
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Deafen",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
                duration=f"{duration_minutes} minutes" if duration_minutes else None,
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Member deafened", f"{member.mention} is now deafened."), ephemeral=True)
            if duration_minutes:
                await asyncio.sleep(int(duration_minutes) * 60)
                try:
                    await member.edit(deafen=False, reason='Deafen expired')
                except Exception:
                    pass
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Deafen failed", str(e)), ephemeral=True)

    @app_commands.command(name="undeafen", description="Remove server deafen from a member.")
    @app_commands.describe(member="Member to undeafen")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def undeafen_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Moderate Members permission required."), ephemeral=True)
        try:
            await member.edit(deafen=False, reason=f'Undeafen by {interaction.user}')
            await self._log(interaction.guild.id, core_ui.mod_action_embed(
                "Undeafen",
                f"{member} ({member.id})",
                f"{interaction.user} ({interaction.user.id})",
            ))
            await core_ui.send(interaction, embed=core_ui.success_embed("Member undeafened", f"{member.mention} is now undeafened."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Undeafen failed", str(e)), ephemeral=True)

    @app_commands.command(name="staff_setup", description="Create or restore core staff roles.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def staff_setup_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        created = {}
        for r in RANKS:
            role = discord.utils.get(interaction.guild.roles, name=r)
            if role is None:
                try:
                    role = await interaction.guild.create_role(name=r, reason='Staff setup by Villicus')
                except Exception:
                    role = discord.utils.get(interaction.guild.roles, name=r)
            if role:
                created[r] = role.id
        settings = get_guild_settings(interaction.guild.id)
        settings['staff_roles'] = created
        save_guild_settings(interaction.guild.id, settings)
        await core_ui.send(interaction, embed=core_ui.success_embed("Staff roles ready", f"Ensured: {', '.join(created.keys())}"), ephemeral=True)

    @app_commands.command(name="staff_promote", description="Promote a member to a staff rank.")
    @app_commands.describe(member="Member to promote", rank="Staff rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.choices(rank=[app_commands.Choice(name=r, value=r) for r in RANKS])
    async def staff_promote_slash(self, interaction: discord.Interaction, member: discord.Member, rank: str):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        staff = settings.get('staff_roles', {})
        if rank not in staff:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Unknown rank", "Run /staff_setup first."), ephemeral=True)
        role = interaction.guild.get_role(staff[rank])
        if not role:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Role missing", "That role no longer exists on the server."), ephemeral=True)
        try:
            await member.add_roles(role, reason=f'Promoted to {rank} by {interaction.user}')
            await core_ui.send(interaction, embed=core_ui.success_embed("Promotion complete", f"{member.mention} promoted to {rank}."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Promotion failed", str(e)), ephemeral=True)

    @app_commands.command(name="staff_demote", description="Demote a member from a staff rank.")
    @app_commands.describe(member="Member to demote", rank="Staff rank")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.choices(rank=[app_commands.Choice(name=r, value=r) for r in RANKS])
    async def staff_demote_slash(self, interaction: discord.Interaction, member: discord.Member, rank: str):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        staff = settings.get('staff_roles', {})
        if rank not in staff:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Unknown rank", "Run /staff_setup first."), ephemeral=True)
        role = interaction.guild.get_role(staff[rank])
        if not role:
            return await core_ui.send(interaction, embed=core_ui.warn_embed("Role missing", "That role no longer exists on the server."), ephemeral=True)
        try:
            await member.remove_roles(role, reason=f'Demoted from {rank} by {interaction.user}')
            await core_ui.send(interaction, embed=core_ui.success_embed("Demotion complete", f"{member.mention} demoted from {rank}."), ephemeral=True)
        except Exception as e:
            await core_ui.send(interaction, embed=core_ui.error_embed("Demotion failed", str(e)), ephemeral=True)

    @app_commands.command(name="staff_perms", description="Show staff rank role mappings.")
    @app_commands.describe(rank="Optional rank to inspect")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.choices(rank=[app_commands.Choice(name=r, value=r) for r in RANKS])
    async def staff_perms_slash(self, interaction: discord.Interaction, rank: Optional[str] = None):
        if not interaction.user.guild_permissions.administrator:
            return await core_ui.send(interaction, embed=core_ui.error_embed("Permission denied", "Administrator permission required."), ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        staff = settings.get('staff_roles', {})
        if rank:
            if rank not in staff:
                return await core_ui.send(interaction, embed=core_ui.warn_embed("Unknown rank", "Run /staff_setup first."), ephemeral=True)
            role = interaction.guild.get_role(staff[rank])
            return await core_ui.send(interaction, embed=core_ui.info_embed("Staff role", f"{rank}: {role.mention if role else '(missing)'}"), ephemeral=True)
        if not staff:
            return await core_ui.send(interaction, embed=core_ui.info_embed("Staff roles", "No staff roles configured. Run /staff_setup."), ephemeral=True)
        lines = [f'{k}: <@&{v}>' for k, v in staff.items()]
        await core_ui.send(interaction, embed=core_ui.info_embed("Staff roles", "\n".join(lines)), ephemeral=True)


async def setup(bot: commands.Bot):
    cog = AdminCog(bot)
    await bot.add_cog(cog)
