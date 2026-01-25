import logging
from typing import Dict, Any
import discord

logger = logging.getLogger("conditor.creator")


PERMISSION_STR_TO_ATTR = {
    'administrator': 'administrator',
    'manage_guild': 'manage_guild',
    'manage_roles': 'manage_roles',
    'manage_channels': 'manage_channels',
    'manage_messages': 'manage_messages',
    'kick_members': 'kick_members',
    'ban_members': 'ban_members',
    'mute_members': 'mute_members',
    'send_messages': 'send_messages',
    'view_channel': 'view_channel',
    'read_message_history': 'read_message_history',
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
