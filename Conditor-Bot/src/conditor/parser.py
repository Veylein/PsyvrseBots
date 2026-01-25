import hashlib
from typing import Any, Dict, List


PERMISSION_MAP = {
    "administrator": "administrator",
    "manage_guild": "manage_guild",
    "manage_roles": "manage_roles",
    "manage_channels": "manage_channels",
    "manage_messages": "manage_messages",
    "kick_members": "kick_members",
    "ban_members": "ban_members",
    "mute_members": "mute_members",
    "send_messages": "send_messages",
    "read_messages": "view_channel",
    "view_channel": "view_channel",
    "read_message_history": "read_message_history",
}


class TemplateParser:
    """Deterministically generates a concrete creation plan from template + inputs.

    Determinism: SHA256(actor_id + template_name + inputs) -> seed string. All
    name mutation and inclusion rules use slices of seed. No RNG.
    """

    def __init__(self, template: Dict[str, Any]):
        self.template = template

    def _seed(self, actor_id: str, extras: str = "") -> str:
        s = f"{actor_id}|{self.template.get('template_name','')}:" + extras
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def _mutate_name(self, base: str, seed: str, index: int = 0) -> str:
        pos = (index * 5) % max(1, len(seed))
        suffix = seed[pos:pos + 6]
        safe = base.lower().strip().replace(' ', '-').replace('/', '-')
        return f"{safe}-{suffix}"

    def _map_permissions(self, perms: List[str]) -> List[str]:
        return [PERMISSION_MAP[p] for p in perms if p in PERMISSION_MAP]

    def generate(self, inputs: Dict[str, str], actor_id: str) -> Dict[str, Any]:
        seed = self._seed(actor_id, inputs.get('theme', ''))
        plan = {'roles': [], 'categories': [], 'summary': ''}

        # Roles
        for ridx, (rname, meta) in enumerate(self.template.get('roles', {}).items()):
            display = self._mutate_name(rname, seed, index=ridx)
            perms = self._map_permissions(meta.get('permissions', []))
            plan['roles'].append({'template_name': rname, 'name': display, 'permissions': perms, 'color': meta.get('color'), 'hoist': meta.get('hoist', False), 'mentionable': meta.get('mentionable', False)})

        # Categories (optionally reordered deterministically)
        categories = list(self.template.get('categories', []))
        if self.template.get('unique_variation_rules', {}).get('reorder_categories'):
            categories = sorted(categories, key=lambda c: hashlib.sha256((c.get('name','') + seed).encode()).hexdigest())

        for cidx, cat in enumerate(categories):
            cat_name = self._mutate_name(cat.get('name', 'category'), seed, index=cidx)
            cat_plan = {'name': cat_name, 'channels': []}
            for chidx, ch in enumerate(cat.get('channels', [])):
                ch_name = self._mutate_name(ch.get('name', 'channel'), seed, index=chidx + cidx)
                ch_plan = {'type': ch.get('type', 'text'), 'name': ch_name, 'topic': ch.get('topic', ''), 'permissions': ch.get('permissions', {}), 'bitrate': ch.get('bitrate'), 'user_limit': ch.get('user_limit')}

                if self.template.get('unique_variation_rules', {}).get('conditional_channels'):
                    nibble = seed[(chidx + cidx) % len(seed)]
                    include = int(nibble, 16) % 2 == 0
                    if include:
                        cat_plan['channels'].append(ch_plan)
                else:
                    cat_plan['channels'].append(ch_plan)

            # apply density scaling
            density = inputs.get('channel_density', 'standard').lower()
            if density == 'minimal':
                cat_plan['channels'] = cat_plan['channels'][:1]
            elif density == 'massive' and self.template.get('unique_variation_rules', {}).get('scaling_rules'):
                extra = []
                for i, ch in enumerate(cat_plan['channels']):
                    copy_name = self._mutate_name(ch['name'] + '-x', seed, index=i + len(cat_plan['channels']))
                    extra.append({**ch, 'name': copy_name})
                cat_plan['channels'].extend(extra)

            plan['categories'].append(cat_plan)

        plan['summary'] = f"{len(plan['roles'])} roles, {sum(len(c['channels']) for c in plan['categories'])} channels"
        return plan
