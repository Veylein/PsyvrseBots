import logging
from typing import Dict, Any
import discord

logger = logging.getLogger("conditor.creator")


PERMISSION_STR_TO_ATTR = {
    'create_instant_invite': 'create_instant_invite',
    'kick_members': 'kick_members',
    'ban_members': 'ban_members',
    'administrator': 'administrator',
    'manage_channels': 'manage_channels',
    'manage_guild': 'manage_guild',
    'add_reactions': 'add_reactions',
    'view_audit_log': 'view_audit_log',
    'priority_speaker': 'priority_speaker',
    'stream': 'stream',
    'view_channel': 'view_channel',
    'read_messages': 'view_channel',
    'send_messages': 'send_messages',
    'send_tts_messages': 'send_tts_messages',
    'manage_messages': 'manage_messages',
    'embed_links': 'embed_links',
    'attach_files': 'attach_files',
    'read_message_history': 'read_message_history',
    'mention_everyone': 'mention_everyone',
    'use_external_emojis': 'use_external_emojis',
    'view_guild_insights': 'view_guild_insights',
    'connect': 'connect',
    'speak': 'speak',
    'mute_members': 'mute_members',
    'deafen_members': 'deafen_members',
    'move_members': 'move_members',
    'use_vad': 'use_vad',
    'change_nickname': 'change_nickname',
    'manage_nicknames': 'manage_nicknames',
    'manage_roles': 'manage_roles',
    'manage_webhooks': 'manage_webhooks',
    'manage_emojis_and_stickers': 'manage_emojis_and_stickers',
    'use_application_commands': 'use_application_commands',
    'request_to_speak': 'request_to_speak',
    'manage_threads': 'manage_threads',
    'create_public_threads': 'create_public_threads',
    'create_private_threads': 'create_private_threads',
    'use_external_stickers': 'use_external_stickers',
}


def permissions_from_list(strings):
    perms = discord.Permissions.none()
    for s in strings:
        attr = PERMISSION_STR_TO_ATTR.get(s)
        if attr and hasattr(perms, attr):
            setattr(perms, attr, True)
    return perms


class CreationPipeline:
    """Executes a creation plan against a Guild and supports rollback."""

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.created = {"roles": [], "categories": [], "channels": []}

    async def _create_role(self, spec: Dict[str, Any]):
        perms = permissions_from_list(spec.get('permissions', [])) if spec.get('permissions') else discord.Permissions.none()
        role = await self.guild.create_role(name=spec['name'], hoist=spec.get('hoist', False), mentionable=spec.get('mentionable', False), permissions=perms)
        self.created['roles'].append(role)
        logger.info(f"Created role {role.name} ({role.id})")
        return role

    async def _create_category(self, spec: Dict[str, Any]):
        cat = await self.guild.create_category(spec['name'])
        self.created['categories'].append(cat)
        logger.info(f"Created category {cat.name} ({cat.id})")
        return cat

    async def _create_channel(self, parent, ch_spec: Dict[str, Any], role_map: Dict[str, discord.Role]):
        ch_type = ch_spec.get('type', 'text')
        kwargs = {}
        if ch_spec.get('topic'):
            kwargs['topic'] = ch_spec.get('topic')

        overwrites = {}
        for role_key, perms in ch_spec.get('permissions', {}).items():
            role_obj = role_map.get(role_key)
            if not role_obj:
                continue
            allow = discord.Permissions.none()
            deny = discord.Permissions.none()
            for pname, val in perms.items():
                attr = PERMISSION_STR_TO_ATTR.get(pname, pname)
                if val:
                    if hasattr(allow, attr):
                        setattr(allow, attr, True)
                else:
                    if hasattr(deny, attr):
                        setattr(deny, attr, True)
            overwrites[role_obj] = discord.PermissionOverwrite.from_pair(allow, deny)

        if ch_type in ('text', 'announcement'):
            if ch_type == 'announcement' and hasattr(self.guild, 'create_news_channel'):
                ch = await self.guild.create_news_channel(ch_spec['name'], category=parent, overwrites=overwrites, **kwargs)
            else:
                ch = await self.guild.create_text_channel(ch_spec['name'], category=parent, overwrites=overwrites, **kwargs)
        elif ch_type == 'voice':
            ch = await self.guild.create_voice_channel(ch_spec['name'], category=parent, overwrites=overwrites, bitrate=ch_spec.get('bitrate'), user_limit=ch_spec.get('user_limit'))
        elif ch_type == 'stage':
            ch = await self.guild.create_stage_channel(ch_spec['name'], category=parent, overwrites=overwrites)
        elif ch_type == 'forum':
            if hasattr(self.guild, 'create_forum_channel'):
                ch = await self.guild.create_forum_channel(ch_spec['name'], category=parent, overwrites=overwrites, topic=ch_spec.get('topic'))
            else:
                ch = await self.guild.create_text_channel(ch_spec['name'], category=parent, overwrites=overwrites, **kwargs)
        else:
            ch = await self.guild.create_text_channel(ch_spec['name'], category=parent, overwrites=overwrites, **kwargs)

        self.created['channels'].append(ch)
        logger.info(f"Created channel {ch.name} ({ch.id})")
        return ch

    async def execute(self, plan: Dict[str, Any], actor=None) -> Dict[str, Any]:
        try:
            role_map = {}
            for r in plan.get('roles', []):
                role = await self._create_role(r)
                role_map[r.get('template_name')] = role
                role_map[r.get('name')] = role

            for cat in plan.get('categories', []):
                new_cat = await self._create_category({'name': cat['name']})
                for ch in cat.get('channels', []):
                    await self._create_channel(new_cat, ch, role_map)

            return {"summary": plan.get('summary', '')}
        except Exception:
            logger.exception("Creation failed, rolling back")
            await self.rollback()
            raise

    async def rollback(self):
        for ch in list(self.created.get('channels', [])):
            try:
                await ch.delete()
            except Exception:
                logger.exception(f"Failed to delete channel {getattr(ch, 'id', None)}")
        for cat in list(self.created.get('categories', [])):
            try:
                await cat.delete()
            except Exception:
                logger.exception(f"Failed to delete category {getattr(cat, 'id', None)}")
        for r in list(self.created.get('roles', [])):
            try:
                await r.delete()
            except Exception:
                logger.exception(f"Failed to delete role {getattr(r, 'id', None)}")
