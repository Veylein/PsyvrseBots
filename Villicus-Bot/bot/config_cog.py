import asyncio
import os
import re
from typing import List, Optional

import discord
from discord.ext import commands
from discord import app_commands

from core.config import get_guild_settings, save_guild_settings, set_prefix


PUNISHMENT_ROLES = {
    'shadow_ban': 'Shadow Ban',
    'shadow_mute': 'Shadow Mute',
    'deafen': 'Deafen',
    'brick': 'Brick',
    'demoji': 'Demoji'
}


class ConfigCog(commands.Cog):
    """Core config: prefix, config wizard and status; punishment role creation
    and lightweight enforcement (shadowmute/brick/demoji listeners).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='prefix')
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx: commands.Context, new_prefix: str):
        """Change the bot prefix for this guild (Administrator)."""
        ok = set_prefix(ctx.guild.id, new_prefix)
        if ok:
            await ctx.send(f'Prefix updated to: {new_prefix}')
        else:
            await ctx.send('Failed to update prefix.')

    @commands.command(name='status')
    @commands.has_permissions(manage_guild=True)
    async def status(self, ctx: commands.Context):
        """Show basic bot health and enabled modules."""
        settings = get_guild_settings(ctx.guild.id)
        enabled = settings.get('punishments', [])
        lines = [f'Guild: {ctx.guild.name} ({ctx.guild.id})', f'Prefix: {settings.get("prefix", "V!")}', '', 'Enabled punishments:']
        if not enabled:
            lines.append(' (none)')
        else:
            for p in enabled:
                lines.append(f' - {p}')
        # quick API ping
        try:
            p = round(self.bot.latency * 1000)
            lines.append(f'Bot latency: {p}ms')
        except Exception:
            pass
        await ctx.send('\n'.join(lines))

    @commands.command(name='config')
    @commands.has_permissions(administrator=True)
    async def config(self, ctx: commands.Context, section: Optional[str] = None):
        """Interactive config helper. `V!config punishments` to enable punishment roles."""
        if section == 'punishments':
            await self._config_punishments(ctx)
            return
        await ctx.send('Config sections: `punishments` — try `V!config punishments`')

    async def _config_punishments(self, ctx: commands.Context):
        # Prompt the admin for which punishments to enable (simple text-based flow)
        choices = [f'{i+1}. {name.replace("_", " ").title()}' for i, name in enumerate(PUNISHMENT_ROLES.keys())]
        msg = await ctx.send('Which punishments do you want to enable? Reply with numbers separated by spaces (e.g. `1 3 5`) or `all` or `none`:\n' + '\n'.join(choices))

        def check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            reply = await self.bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            return await ctx.send('Config timed out.')

        text = reply.content.strip().lower()
        selected = []
        if text == 'all':
            selected = list(PUNISHMENT_ROLES.keys())
        elif text == 'none' or text == '0':
            selected = []
        else:
            nums = re.findall(r'\d+', text)
            for n in nums:
                try:
                    idx = int(n) - 1
                    key = list(PUNISHMENT_ROLES.keys())[idx]
                    selected.append(key)
                except Exception:
                    continue

        # create roles for selected punishments
        created = []
        for key in selected:
            role_name = PUNISHMENT_ROLES.get(key)
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            try:
                if role is None:
                    role = await ctx.guild.create_role(name=role_name, reason='Configured by Villicus punishments setup')
                created.append(role_name)
                # special-case: Shadow Ban should deny View Channel everywhere — we'll try to apply overwrites
                if key == 'shadow_ban':
                    await self._apply_shadow_ban_overwrites(ctx.guild, role)
            except Exception:
                pass

        # persist
        settings = get_guild_settings(ctx.guild.id)
        settings['punishments'] = selected
        save_guild_settings(ctx.guild.id, settings)

        await ctx.send(f'Configured punishments: {created or "(none)"}')

    async def _apply_shadow_ban_overwrites(self, guild: discord.Guild, role: discord.Role):
        # Deny view_channel for the role across text/voice channels if possible
        if not guild.me or not guild.me.guild_permissions.manage_roles or not guild.me.guild_permissions.manage_channels:
            return
        for ch in guild.channels:
            try:
                await ch.set_permissions(role, view_channel=False, read_message_history=False)
            except Exception:
                pass

    # PUNISHMENT COMMANDS (basic implementations that assign created roles)
    @commands.command(name='shadowban')
    @commands.has_permissions(administrator=True)
    async def shadowban(self, ctx: commands.Context, member: discord.Member, duration_minutes: Optional[int] = None):
        role = discord.utils.get(ctx.guild.roles, name=PUNISHMENT_ROLES['shadow_ban'])
        if role is None:
            return await ctx.send('Shadow Ban role not configured. Run `V!config punishments` first.')
        try:
            await member.add_roles(role, reason=f'Shadow banned by {ctx.author}')
        except Exception as e:
            return await ctx.send(f'Failed to add role: {e}')
        await ctx.send(f'{member.mention} shadow banned.')
        if duration_minutes:
            await asyncio.sleep(int(duration_minutes) * 60)
            try:
                await member.remove_roles(role, reason='Shadow ban expired')
            except Exception:
                pass

    @commands.command(name='shadowunban')
    @commands.has_permissions(administrator=True)
    async def shadowunban(self, ctx: commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name=PUNISHMENT_ROLES['shadow_ban'])
        if role is None:
            return await ctx.send('Shadow Ban role not configured.')
        try:
            await member.remove_roles(role, reason=f'Shadow unbanned by {ctx.author}')
        except Exception as e:
            return await ctx.send(f'Failed to remove role: {e}')
        await ctx.send(f'{member.mention} shadow unbanned.')

    @commands.command(name='shadowmute')
    @commands.has_permissions(manage_messages=True, moderate_members=True)
    async def shadowmute(self, ctx: commands.Context, member: discord.Member, duration_minutes: Optional[int] = None):
        role = discord.utils.get(ctx.guild.roles, name=PUNISHMENT_ROLES['shadow_mute'])
        if role is None:
            return await ctx.send('Shadow Mute role not configured. Run `V!config punishments` first.')
        try:
            await member.add_roles(role, reason=f'Shadow muted by {ctx.author}')
        except Exception as e:
            return await ctx.send(f'Failed to add role: {e}')
        await ctx.send(f'{member.mention} shadow muted.')
        if duration_minutes:
            await asyncio.sleep(int(duration_minutes) * 60)
            try:
                await member.remove_roles(role, reason='Shadow mute expired')
            except Exception:
                pass

    @commands.command(name='shadowunmute')
    @commands.has_permissions(manage_messages=True, moderate_members=True)
    async def shadowunmute(self, ctx: commands.Context, member: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name=PUNISHMENT_ROLES['shadow_mute'])
        if role is None:
            return await ctx.send('Shadow Mute role not configured.')
        try:
            await member.remove_roles(role, reason=f'Shadow unmuted by {ctx.author}')
        except Exception as e:
            return await ctx.send(f'Failed to remove role: {e}')
        await ctx.send(f'{member.mention} shadow unmuted.')

    # EVENT LISTENERS: enforce shadowmute/brick/demoji
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        member = message.author
        # Shadow Mute: delete messages so others don't see them, but DM the author a copy
        sm_role = discord.utils.get(guild.roles, name=PUNISHMENT_ROLES['shadow_mute'])
        if sm_role and sm_role in member.roles:
            try:
                # delete publicly
                await message.delete()
            except Exception:
                pass
            try:
                await member.send(f'Your message in {guild.name} was hidden by shadow mute. Copy:\n{message.content}')
            except Exception:
                pass
            return

        # Brick: replace user messages with 'Brick 🧱'
        brick_role = discord.utils.get(guild.roles, name=PUNISHMENT_ROLES['brick'])
        if brick_role and brick_role in member.roles:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await message.channel.send(f'{member.mention} Brick 🧱')
            except Exception:
                pass
            return

        # Demoji: delete messages containing custom emoji patterns if role present
        demoji_role = discord.utils.get(guild.roles, name=PUNISHMENT_ROLES['demoji'])
        if demoji_role and demoji_role in member.roles:
            if re.search(r'<a?:[A-Za-z0-9_]+:\d+>', message.content):
                try:
                    await message.delete()
                except Exception:
                    pass
                return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # remove reaction if user has Demoji role
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        demoji_role = discord.utils.get(guild.roles, name=PUNISHMENT_ROLES['demoji'])
        if demoji_role and demoji_role in member.roles:
            try:
                channel = self.bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                for r in message.reactions:
                    if getattr(r.emoji, 'id', None) == payload.emoji.id if hasattr(payload.emoji, 'id') else False:
                        try:
                            await message.remove_reaction(payload.emoji, member)
                        except Exception:
                            pass
            except Exception:
                pass


async def setup(bot: commands.Bot):
    cog = ConfigCog(bot)
    await bot.add_cog(cog)
