import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from core.config import get_guild_settings, save_guild_settings


RANKS = ['Helper', 'Moderator', 'Senior Moderator', 'Supervisor', 'Administrator']


class AdminCog(commands.Cog):
    """Full moderation and admin commands: kick/ban/softban/unban/massban, channel tools,
    staff management, emoji locking and utility commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _moderation_cog(self):
        return self.bot.get_cog('ModerationCog')

    # --- Moderation actions ---
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = 'No reason provided'):
        try:
            await member.kick(reason=reason)
            mod = self._moderation_cog()
            if mod:
                mod._record_infraction(member.id, ctx.author.id, 'kick', reason)
            await ctx.send(f'Kicked {member}.')
        except Exception as e:
            await ctx.send(f'Failed to kick: {e}')

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, days: int = 0, *, reason: str = 'No reason provided'):
        try:
            await member.ban(reason=reason, delete_message_days=days)
            mod = self._moderation_cog()
            if mod:
                mod._record_infraction(member.id, ctx.author.id, 'ban', reason)
            await ctx.send(f'Banned {member}.')
        except Exception as e:
            await ctx.send(f'Failed to ban: {e}')

    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: str, *, reason: str = 'Unbanned by staff'):
        # user can be ID or name#discrim
        try:
            bans = await ctx.guild.bans()
            target = None
            if user.isdigit():
                uid = int(user)
                for entry in bans:
                    if entry.user.id == uid:
                        target = entry.user
                        break
            else:
                for entry in bans:
                    if f"{entry.user.name}#{entry.user.discriminator}" == user:
                        target = entry.user
                        break
            if not target:
                return await ctx.send('User not found in ban list.')
            await ctx.guild.unban(target, reason=reason)
            mod = self._moderation_cog()
            if mod:
                mod._record_infraction(target.id, ctx.author.id, 'unban', reason)
            await ctx.send(f'Unbanned {target}.')
        except Exception as e:
            await ctx.send(f'Failed to unban: {e}')

    @commands.command(name='softban')
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = 'Softban by staff'):
        try:
            await member.ban(reason=reason, delete_message_days=1)
            await ctx.guild.unban(member, reason='Softban unban')
            mod = self._moderation_cog()
            if mod:
                mod._record_infraction(member.id, ctx.author.id, 'softban', reason)
            await ctx.send(f'Softbanned {member}.')
        except Exception as e:
            await ctx.send(f'Failed to softban: {e}')

    @commands.command(name='massban')
    @commands.has_permissions(administrator=True)
    async def massban(self, ctx: commands.Context, criteria: str):
        """Simple massban: 'role:rolename' or 'account_age<days'."""
        try:
            parts = criteria.split(':', 1)
            members = []
            if parts[0] == 'role' and len(parts) > 1:
                role_name = parts[1].strip()
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if not role:
                    return await ctx.send('Role not found.')
                members = [m for m in ctx.guild.members if role in m.roles and not m.bot]
            elif parts[0].startswith('account_age'):
                # format account_age<days
                m = re.search(r'account_age<(?P<days>\d+)', criteria)
                if not m:
                    return await ctx.send('Invalid account_age filter, use account_age<days')
                days = int(m.group('days'))
                cutoff = datetime.utcnow() - timedelta(days=days)
                members = [m for m in ctx.guild.members if hasattr(m, 'joined_at') and m.joined_at and m.joined_at < cutoff and not m.bot]
            else:
                return await ctx.send('Unsupported criteria. Use role:rolename or account_age<days')
            count = 0
            for m in members:
                try:
                    await ctx.guild.ban(m, reason=f'Massban: {criteria}')
                    count += 1
                except Exception:
                    continue
            await ctx.send(f'Attempted massban for {len(members)} members; banned {count}.')
        except Exception as e:
            await ctx.send(f'Massban failed: {e}')

    # --- Channel & message controls ---
    @commands.command(name='clear')
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int = 50):
        try:
            deleted = await ctx.channel.purge(limit=amount)
            await ctx.send(f'Deleted {len(deleted)} messages.', delete_after=5)
        except Exception as e:
            await ctx.send(f'Failed to clear messages: {e}')

    @commands.command(name='slowmode')
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 0):
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            await ctx.send(f'Set slowmode to {seconds} seconds.')
        except Exception as e:
            await ctx.send(f'Failed to set slowmode: {e}')

    @commands.command(name='lock')
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        ch = channel or ctx.channel
        try:
            await ch.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(f'Locked {ch.mention}')
        except Exception as e:
            await ctx.send(f'Failed to lock: {e}')

    @commands.command(name='unlock')
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        ch = channel or ctx.channel
        try:
            await ch.set_permissions(ctx.guild.default_role, send_messages=True)
            await ctx.send(f'Unlocked {ch.mention}')
        except Exception as e:
            await ctx.send(f'Failed to unlock: {e}')

    @commands.command(name='clone')
    @commands.has_permissions(administrator=True)
    async def clone(self, ctx: commands.Context, channel: Optional[discord.abc.GuildChannel] = None):
        ch = channel or ctx.channel
        try:
            new = await ch.clone(reason=f'Cloned by {ctx.author}')
            await ctx.send(f'Cloned {ch.mention} to {new.mention}')
        except Exception as e:
            await ctx.send(f'Failed to clone: {e}')

    # --- Deafen ---
    @commands.command(name='deafen')
    @commands.has_permissions(moderate_members=True)
    async def deafen(self, ctx: commands.Context, member: discord.Member, duration_minutes: Optional[int] = None):
        try:
            await member.edit(deafen=True, reason=f'Deafened by {ctx.author}')
            await ctx.send(f'{member.mention} deafened.')
            if duration_minutes:
                await asyncio.sleep(int(duration_minutes) * 60)
                try:
                    await member.edit(deafen=False, reason='Deafen expired')
                except Exception:
                    pass
        except Exception as e:
            await ctx.send(f'Failed to deafen: {e}')

    @commands.command(name='undeafen')
    @commands.has_permissions(moderate_members=True)
    async def undeafen(self, ctx: commands.Context, member: discord.Member):
        try:
            await member.edit(deafen=False, reason=f'Undeafen by {ctx.author}')
            await ctx.send(f'{member.mention} undeafened.')
        except Exception as e:
            await ctx.send(f'Failed to undeafen: {e}')

    # --- Brick & Demoji assignments (roles already created by config) ---
    @commands.command(name='brick')
    @commands.has_permissions(manage_roles=True)
    async def brick(self, ctx: commands.Context, member: discord.Member, *, reason: str = ''):
        role = discord.utils.get(ctx.guild.roles, name='Brick')
        if role is None:
            return await ctx.send('Brick role not configured. Run `V!config punishments` first.')
        try:
            await member.add_roles(role, reason=reason or f'Bricked by {ctx.author}')
            await ctx.send(f'{member.mention} bricked.')
        except Exception as e:
            await ctx.send(f'Failed to brick: {e}')

    @commands.command(name='unbrick')
    @commands.has_permissions(manage_roles=True)
    async def unbrick(self, ctx: commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name='Brick')
        if role is None:
            return await ctx.send('Brick role not configured.')
        try:
            await member.remove_roles(role, reason=f'Unbricked by {ctx.author}')
            await ctx.send(f'{member.mention} unbricked.')
        except Exception as e:
            await ctx.send(f'Failed to unbrick: {e}')

    @commands.command(name='demoji')
    @commands.has_permissions(manage_roles=True)
    async def demoji(self, ctx: commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name='Demoji')
        if role is None:
            return await ctx.send('Demoji role not configured. Run `V!config punishments` first.')
        try:
            await member.add_roles(role, reason=f'Demoji by {ctx.author}')
            await ctx.send(f'{member.mention} demoji applied.')
        except Exception as e:
            await ctx.send(f'Failed to apply demoji: {e}')

    @commands.command(name='undemoji')
    @commands.has_permissions(manage_roles=True)
    async def undemoji(self, ctx: commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name='Demoji')
        if role is None:
            return await ctx.send('Demoji role not configured.')
        try:
            await member.remove_roles(role, reason=f'Undemoji by {ctx.author}')
            await ctx.send(f'{member.mention} demoji removed.')
        except Exception as e:
            await ctx.send(f'Failed to remove demoji: {e}')

    # --- Emoji lock/unlock ---
    @commands.command(name='emoji_lock')
    @commands.has_permissions(manage_guild=True)
    async def emoji_lock(self, ctx: commands.Context, emoji: str, role: discord.Role):
        settings = get_guild_settings(ctx.guild.id)
        locks = settings.get('emoji_locks', {})
        locks[emoji] = role.id
        settings['emoji_locks'] = locks
        save_guild_settings(ctx.guild.id, settings)
        await ctx.send(f'Locked emoji {emoji} to role {role.name}.')

    @commands.command(name='emoji_unlock')
    @commands.has_permissions(manage_guild=True)
    async def emoji_unlock(self, ctx: commands.Context, emoji: str):
        settings = get_guild_settings(ctx.guild.id)
        locks = settings.get('emoji_locks', {})
        if emoji in locks:
            locks.pop(emoji, None)
            settings['emoji_locks'] = locks
            save_guild_settings(ctx.guild.id, settings)
            await ctx.send(f'Unlocked emoji {emoji}.')
        else:
            await ctx.send('Emoji not locked.')

    # --- Staff system ---
    @commands.command(name='staff_setup')
    @commands.has_permissions(administrator=True)
    async def staff_setup(self, ctx: commands.Context):
        created = {}
        for r in RANKS:
            role = discord.utils.get(ctx.guild.roles, name=r)
            if role is None:
                try:
                    role = await ctx.guild.create_role(name=r, reason='Staff setup by Villicus')
                except Exception:
                    role = discord.utils.get(ctx.guild.roles, name=r)
            if role:
                created[r] = role.id
        settings = get_guild_settings(ctx.guild.id)
        settings['staff_roles'] = created
        save_guild_settings(ctx.guild.id, settings)
        await ctx.send(f'Staff roles ensured: {list(created.keys())}')

    @commands.command(name='staff_promote')
    @commands.has_permissions(administrator=True)
    async def staff_promote(self, ctx: commands.Context, member: discord.Member, rank: str):
        settings = get_guild_settings(ctx.guild.id)
        staff = settings.get('staff_roles', {})
        if rank not in staff:
            return await ctx.send('Unknown rank. Run `V!staff_setup` first or check `V!staff perms`')
        role_id = staff[rank]
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send('Role not found on server.')
        try:
            await member.add_roles(role, reason=f'Promoted to {rank} by {ctx.author}')
            await ctx.send(f'{member.mention} promoted to {rank}.')
        except Exception as e:
            await ctx.send(f'Failed to promote: {e}')

    @commands.command(name='staff_demote')
    @commands.has_permissions(administrator=True)
    async def staff_demote(self, ctx: commands.Context, member: discord.Member, rank: str):
        settings = get_guild_settings(ctx.guild.id)
        staff = settings.get('staff_roles', {})
        if rank not in staff:
            return await ctx.send('Unknown rank.')
        role = ctx.guild.get_role(staff[rank])
        if not role:
            return await ctx.send('Role not found on server.')
        try:
            await member.remove_roles(role, reason=f'Demoted from {rank} by {ctx.author}')
            await ctx.send(f'{member.mention} demoted from {rank}.')
        except Exception as e:
            await ctx.send(f'Failed to demote: {e}')

    @commands.command(name='staff_perms')
    @commands.has_permissions(administrator=True)
    async def staff_perms(self, ctx: commands.Context, rank: Optional[str] = None):
        settings = get_guild_settings(ctx.guild.id)
        staff = settings.get('staff_roles', {})
        if rank:
            if rank not in staff:
                return await ctx.send('Unknown rank.')
            role = ctx.guild.get_role(staff[rank])
            return await ctx.send(f'Role {rank}: {role.mention if role else "(missing)"}')
        if not staff:
            return await ctx.send('No staff roles configured. Run `V!staff_setup`')
        lines = [f'{k}: <@&{v}>' for k, v in staff.items()]
        await ctx.send('Staff roles:\n' + '\n'.join(lines))

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
        # check content for custom emoji patterns
        matches = re.findall(r'<a?:[A-Za-z0-9_]+:(\d+)>', message.content)
        if not matches:
            return
        for eid in matches:
            for emoji, role_id in locks.items():
                if eid == emoji or emoji == f'<:{eid}>' or emoji == f'<a:{eid}>':
                    role = guild.get_role(role_id)
                    member = message.author
                    if role and role not in member.roles:
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        settings = get_guild_settings(guild.id)
        locks = settings.get('emoji_locks', {})
        if not locks:
            return
        # payload.emoji may have id
        eid = getattr(payload.emoji, 'id', None)
        if not eid:
            return
        for emoji, role_id in locks.items():
            if str(eid) == emoji or emoji == f'<:{eid}>' or emoji == f'<a:{eid}>':
                member = guild.get_member(payload.user_id)
                role = guild.get_role(role_id)
                if member and role and role not in member.roles:
                    try:
                        channel = self.bot.get_channel(payload.channel_id)
                        message = await channel.fetch_message(payload.message_id)
                        await message.remove_reaction(payload.emoji, member)
                    except Exception:
                        pass

    # ---------------- SLASH COMMAND WRAPPERS ----------------
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = 'No reason provided'):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.followup.send('You do not have permission to kick members.', ephemeral=True)
        try:
            await member.kick(reason=reason)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'kick', reason)
            await interaction.followup.send(f'Kicked {member}.')
        except Exception as e:
            await interaction.followup.send(f'Failed to kick: {e}', ephemeral=True)

    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, days: int = 0, reason: str = 'No reason provided'):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.followup.send('You do not have permission to ban members.', ephemeral=True)
        try:
            await member.ban(reason=reason, delete_message_days=days)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(member.id, interaction.user.id, 'ban', reason)
            await interaction.followup.send(f'Banned {member}.')
        except Exception as e:
            await interaction.followup.send(f'Failed to ban: {e}', ephemeral=True)

    async def unban_slash(self, interaction: discord.Interaction, user: discord.User, reason: str = 'Unbanned by staff'):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.followup.send('You do not have permission to unban members.', ephemeral=True)
        try:
            bans = await interaction.guild.bans()
            target = None
            for entry in bans:
                if entry.user.id == user.id:
                    target = entry.user
                    break
            if not target:
                return await interaction.followup.send('User not found in ban list.', ephemeral=True)
            await interaction.guild.unban(target, reason=reason)
            mod = self.bot.get_cog('ModerationCog')
            if mod:
                mod._record_infraction(target.id, interaction.user.id, 'unban', reason)
            await interaction.followup.send(f'Unbanned {target}.')
        except Exception as e:
            await interaction.followup.send(f'Failed to unban: {e}', ephemeral=True)

    async def clear_slash(self, interaction: discord.Interaction, amount: int = 50):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.followup.send('You do not have permission to manage messages.', ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f'Deleted {len(deleted)} messages.', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'Failed to clear messages: {e}', ephemeral=True)

    async def lock_slash(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer()
        ch = channel or interaction.channel
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.followup.send('You do not have permission to manage channels.', ephemeral=True)
        try:
            await ch.set_permissions(interaction.guild.default_role, send_messages=False)
            await interaction.followup.send(f'Locked {ch.mention}')
        except Exception as e:
            await interaction.followup.send(f'Failed to lock: {e}', ephemeral=True)

    async def unlock_slash(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer()
        ch = channel or interaction.channel
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.followup.send('You do not have permission to manage channels.', ephemeral=True)
        try:
            await ch.set_permissions(interaction.guild.default_role, send_messages=True)
            await interaction.followup.send(f'Unlocked {ch.mention}')
        except Exception as e:
            await interaction.followup.send(f'Failed to unlock: {e}', ephemeral=True)

    async def brick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = ''):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.followup.send('You do not have permission to manage roles.', ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name='Brick')
        if role is None:
            return await interaction.followup.send('Brick role not configured. Run `V!config punishments` first.', ephemeral=True)
        try:
            await member.add_roles(role, reason=reason or f'Bricked by {interaction.user}')
            await interaction.followup.send(f'{member.mention} bricked.')
        except Exception as e:
            await interaction.followup.send(f'Failed to brick: {e}', ephemeral=True)

    async def demoji_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.followup.send('You do not have permission to manage roles.', ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name='Demoji')
        if role is None:
            return await interaction.followup.send('Demoji role not configured. Run `V!config punishments` first.', ephemeral=True)
        try:
            await member.add_roles(role, reason=f'Demoji by {interaction.user}')
            await interaction.followup.send(f'{member.mention} demoji applied.')
        except Exception as e:
            await interaction.followup.send(f'Failed to apply demoji: {e}', ephemeral=True)

    async def emoji_lock_slash(self, interaction: discord.Interaction, emoji: str, role: discord.Role):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.followup.send('You do not have permission to manage the guild.', ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        locks = settings.get('emoji_locks', {})
        locks[emoji] = role.id
        settings['emoji_locks'] = locks
        save_guild_settings(interaction.guild.id, settings)
        await interaction.followup.send(f'Locked emoji {emoji} to role {role.name}.')

    async def emoji_unlock_slash(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.followup.send('You do not have permission to manage the guild.', ephemeral=True)
        settings = get_guild_settings(interaction.guild.id)
        locks = settings.get('emoji_locks', {})
        if emoji in locks:
            locks.pop(emoji, None)
            settings['emoji_locks'] = locks
            save_guild_settings(interaction.guild.id, settings)
            await interaction.followup.send(f'Unlocked emoji {emoji}.')
        else:
            await interaction.followup.send('Emoji not locked.', ephemeral=True)


async def setup(bot: commands.Bot):
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    # Best-effort: register important admin slash commands onto the tree — actual sync happens in on_ready()
    try:
        try:
            bot.tree.add_command(app_commands.Command(name='kick', description='Kick a member', callback=cog.kick_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='ban', description='Ban a member', callback=cog.ban_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='unban', description='Unban a member', callback=cog.unban_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='clear', description='Purge messages', callback=cog.clear_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='lock', description='Lock a channel', callback=cog.lock_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='unlock', description='Unlock a channel', callback=cog.unlock_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='brick', description='Apply Brick role', callback=cog.brick_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='demoji', description='Apply Demoji role', callback=cog.demoji_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='emoji_lock', description='Lock an emoji to a role', callback=cog.emoji_lock_slash))
        except Exception:
            pass
        try:
            bot.tree.add_command(app_commands.Command(name='emoji_unlock', description='Unlock an emoji', callback=cog.emoji_unlock_slash))
        except Exception:
            pass
    except Exception:
        pass
