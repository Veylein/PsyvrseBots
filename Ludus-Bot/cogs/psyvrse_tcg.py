from __future__ import annotations
import os, json, random, time, tempfile, threading
from typing import List, Dict, Optional
import math
from dataclasses import dataclass, asdict
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import Callable

# Compatibility helper: some discord.py versions don't expose
# app_commands.checks.is_owner; provide a small wrapper that
# returns an app_commands.check enforcing owner-only access.
def app_owner_check() -> Callable:
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            return await interaction.client.is_owner(interaction.user)
        except Exception:
            return False
    return app_commands.check(predicate)

# =====================
# CONFIG / PATHS
# =====================
DATA_DIR = os.path.join(os.getcwd(), "Ludus", "data", "tcg")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CRAFTED_FILE = os.path.join(DATA_DIR, "crafted.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.json")

os.makedirs(DATA_DIR, exist_ok=True)

TOTAL_CARD_POOL = 2_038_400
RARITY_ORDER = ['C','B','A','S','X','Z']
RARITY_WEIGHTS = [('C',0.45), ('B',0.25), ('A',0.15), ('S',0.10), ('X',0.04), ('Z',0.01)]
RARITY_SCALE = {"C":1.0,"B":1.5,"A":2.2,"S":3.0,"X":4.0,"Z":5.5}

PREFIXES = ["Ancient","Cyber","Crimson","Gilded","Storm","Solar","Lunar","Iron","Velvet","Glass",
            "Obsidian","Phantom","Ethereal","Infernal","Celestial","Shadow","Titan","Mystic","Arcane",
            "Volcanic","Frost","Thunder","Vortex","Aurora","Spectral"]
CORES = ["Drake","Unicorn","Ogre","Warden","Archer","Golem","Raven","Seraph","Marauder",
         "Phoenix","Hydra","Griffin","Knight","Paladin","Assassin","Rogue","Samurai","Berserker",
         "Necromancer","Valkyrie","Sphinx","Elemental","Dragon","Behemoth","Sentinel"]
SUFFIXES = ["of Ruin","of Dawn","of Echoes","of the Wild","of the Void","of Ages","the Eternal",
            "of Flames","of Frost","of Shadows","of Storms","of Light","the Forsaken","of Chaos",
            "of Time","of Eternity","the Blessed","the Cursed","of Nightfall","of the Ancients",
            "of Secrets","the Arcane","of Destiny","of Infinity","of Valor"]
TYPES = ["Warrior","Mage","Beast","Dragon","Undead","Elemental","Rogue","Paladin","Assassin","Guardian"]
TRAITS = ["Swift","Brave","Cunning","Mighty","Wise","Resilient","Ferocious","Ethereal","Ancient","Mystic"]

# Optional: list of guild IDs for faster guild-scoped app command registration
# Set to [] for global registration (may take up to an hour to fully propagate)
GUILD_IDS: List[int] = []

# =====================
# UTILITIES
# =====================
_FILE_IO_LOCK = threading.Lock()

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: str, data: dict):
    # Atomic write: write to temp file in same dir then replace
    dirn = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=dirn)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

# =====================
# CARD CLASS
# =====================
@dataclass
class Card:
    id: str
    name: str
    rarity: str
    type: str = ''
    attack: int = 0
    defense: int = 0
    traits: List[str] = None
    description: str = ''

    def to_dict(self) -> dict: return asdict(self)
    @staticmethod
    def from_dict(d:dict) -> Optional[Card]:
        if not d: return None
        return Card(
            id=d.get('id',''),
            name=d.get('name',''),
            rarity=d.get('rarity','C'),
            type=d.get('type',''),
            attack=int(d.get('attack',0)),
            defense=int(d.get('defense',0)),
            traits=list(d.get('traits') or []),
            description=d.get('description','')
        )

# =====================
# INVENTORY MANAGER
# =====================
class PsyInventory:
    def __init__(self):
        self.users = load_json(USERS_FILE)
        self.crafted = load_json(CRAFTED_FILE)
        self.trades = load_json(TRADES_FILE)

    def save(self):
        # Lock in-process saves to avoid concurrent write corruption
        with _FILE_IO_LOCK:
            save_json(USERS_FILE, self.users)
            save_json(CRAFTED_FILE, self.crafted)
            save_json(TRADES_FILE, self.trades)

    def get_user(self,user_id:int) -> dict:
        uid = str(user_id)
        if uid not in self.users:
            self.users[uid] = {"coins":100,"dust":0,"cards":[],"packs_opened":0}
        return self.users[uid]

    def add_card(self,user_id:int,card_id:str):
        user = self.get_user(user_id)
        user['cards'].append(str(card_id))
        self.save()

    def remove_card(self,user_id:int,card_id:str) -> bool:
        user = self.get_user(user_id)
        try: user['cards'].remove(str(card_id))
        except ValueError: return False
        self.save()
        return True

    def create_crafted(self,card:Card) -> str:
        cid = f"C{int(time.time()*1000)}{random.randint(1000,9999)}"
        card.id = cid
        self.crafted[cid] = card.to_dict()
        self.save()
        return cid

    def get_crafted(self,cid:str) -> Optional[Card]:
        return Card.from_dict(self.crafted.get(str(cid)))

inventory = PsyInventory()

# =====================
# CARD GENERATOR
# =====================
def generate_card_from_seed(seed:int) -> Card:
    rng = random.Random(seed)
    rarities, weights = zip(*RARITY_WEIGHTS)
    rarity = rng.choices(rarities,weights=weights,k=1)[0]
    atk = max(1,int(rng.randint(1,10)*RARITY_SCALE[rarity]))
    df = max(0,int(rng.randint(0,10)*RARITY_SCALE[rarity]))
    name = f"{rng.choice(PREFIXES)} {rng.choice(CORES)} {rng.choice(SUFFIXES)}"
    card_type = rng.choice(TYPES)
    card_traits = rng.sample(TRAITS, k=3)
    description = f"A {card_type} card with traits: {', '.join(card_traits)}."
    return Card(id=str(seed),name=name,rarity=rarity,type=card_type,attack=atk,defense=df,traits=card_traits,description=description)

def get_card_for_id(cid:int) -> Card:
    if 0 <= cid < TOTAL_CARD_POOL: return generate_card_from_seed(cid)
    raise ValueError("Invalid numeric card id")

# =====================
# PAGINATION VIEW
# =====================
class PagedView(discord.ui.View):
    def __init__(self,pages:List[discord.Embed],timeout:int=120):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    def current(self): return self.pages[self.index]

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, b, i): 
        self.index=(self.index-1)%len(self.pages)
        e = self.current()
        # update footer with page info when available
        try:
            e.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")
        except Exception:
            pass
        await i.response.edit_message(embed=e, view=self)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def next(self, b, i):
        self.index=(self.index+1)%len(self.pages)
        e = self.current()
        try:
            e.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")
        except Exception:
            pass
        await i.response.edit_message(embed=e, view=self)

# =====================
# TCG COG
# =====================
class PsyvrseTCG(commands.Cog):
    """VIP Slash-command TCG: collect, craft, trade, inspect cards."""

    def __init__(self,bot:commands.Bot):
        self.bot = bot

    # --------- /tcg commands ---------
    tcg_group = app_commands.Group(name="tcg", description="Trading Card Game commands")

    @tcg_group.command(name="profile", description="Show your card collection")
    async def profile(self, interaction:discord.Interaction):
        uid = interaction.user.id
        user = inventory.get_user(uid)
        cards_ids = user['cards']
        total_cards = len(cards_ids)
        if not cards_ids:
            await interaction.response.send_message("You have no cards yet.", ephemeral=True)
            return
        cards:List[Card] = []
        summary:Dict[str,int] = {}
        for cid in cards_ids:
            if str(cid).upper().startswith('C'):
                c = inventory.get_crafted(cid)
            else:
                try:
                    c = get_card_for_id(int(cid))
                except Exception:
                    c = None
            if not c:
                continue
            cards.append(c)
            summary[c.rarity] = summary.get(c.rarity,0)+1

        # Summary embed
        summ = discord.Embed(title=f"{interaction.user.display_name}'s Collection",
                             description=f"Total Cards: {total_cards}/{TOTAL_CARD_POOL}\n" +
                                         '\n'.join(f"**{k}**: {v}" for k,v in sorted(summary.items())),
                             color=discord.Color.gold())
        summ.set_thumbnail(url=interaction.user.display_avatar.url)
        pages = [summ]

        # Create per-page collection embeds (12 per page)
        per_page = 12
        for page_idx in range(0, len(cards), per_page):
            chunk = cards[page_idx:page_idx+per_page]
            e = discord.Embed(title=f"Collection — Page {page_idx//per_page+1}", color=discord.Color.blue())
            for c in chunk:
                traits = ', '.join(c.traits) if c.traits else '—'
                # compact field for each card
                e.add_field(name=f"{c.name} [{c.id}]", value=f"{c.rarity} • {c.type} • {c.attack}/{c.defense}\n{traits}", inline=False)
            e.set_footer(text=f"Page {len(pages)} / {((len(cards)-1)//per_page)+1}")
            pages.append(e)

        # Ensure footer for first content page too
        if len(pages) > 1:
            pages[1].set_footer(text=f"Page 1/{len(pages)-1}")

        await interaction.response.send_message(embed=pages[0], view=PagedView(pages))

    @tcg_group.command(name="openpack", description="Open a pack to receive a random card")
    async def openpack(self, interaction: discord.Interaction):
        user = inventory.get_user(interaction.user.id)
        seed = random.randrange(TOTAL_CARD_POOL)
        sid = str(seed)
        if sid not in map(str, user['cards']):
            user['cards'].append(sid)
        user['packs_opened'] = user.get('packs_opened', 0) + 1
        try:
            inventory.save()
        except Exception:
            pass
        card = generate_card_from_seed(seed)
        e = discord.Embed(title="Pack Opened", color=discord.Color.blurple())
        e.add_field(name="Name", value=card.name, inline=False)
        e.add_field(name="Seed", value=str(seed))
        e.add_field(name="Rarity", value=card.rarity)
        e.add_field(name="Attack / Defense", value=f"{card.attack} / {card.defense}")
        await interaction.response.send_message(embed=e, ephemeral=False)

    @tcg_group.command(name="inspect", description="Inspect a card by numeric id or crafted id")
    async def inspect(self, interaction: discord.Interaction, card_id: str):
        try:
            if str(card_id).upper().startswith('C'):
                c = inventory.get_crafted(card_id)
                if not c:
                    return await interaction.response.send_message("Crafted card not found.", ephemeral=True)
            else:
                cid = int(card_id)
                c = get_card_for_id(cid)
        except Exception:
            return await interaction.response.send_message("Invalid card id.", ephemeral=True)
        e = discord.Embed(title=c.name, description=c.description, color=discord.Color.green())
        e.add_field(name='ID', value=c.id)
        e.add_field(name='Rarity', value=c.rarity)
        e.add_field(name='Type', value=c.type)
        e.add_field(name='Attack / Defense', value=f"{c.attack} / {c.defense}")
        if c.traits:
            e.add_field(name='Traits', value=', '.join(c.traits), inline=False)
        await interaction.response.send_message(embed=e, ephemeral=False)

    @inspect.autocomplete('card_id')
    async def _inspect_card_autocomplete(self, interaction: discord.Interaction, current: str):
        user = inventory.get_user(interaction.user.id)
        cards = list(map(str, user.get('cards', [])))
        choices = [app_commands.Choice(name=c, value=c) for c in cards if current.lower() in c.lower()][:25]
        return choices

    @tcg_group.command(name="combine", description="Combine two owned cards into a crafted card (50/50 blend)")
    async def combine(self, interaction: discord.Interaction, a_id: str, b_id: str):
        uid = interaction.user.id
        user = inventory.get_user(uid)
        owned = set(map(str, user.get('cards', [])))
        if a_id not in owned or b_id not in owned:
            return await interaction.response.send_message("You must own both cards to combine them.", ephemeral=True)

        def load_card(cid: str):
            if str(cid).upper().startswith('C'):
                return inventory.get_crafted(cid)
            else:
                return get_card_for_id(int(cid))

        ca = load_card(a_id)
        cb = load_card(b_id)
        if not ca or not cb:
            return await interaction.response.send_message("Failed to load one of the cards.", ephemeral=True)

        na = int(round((ca.attack + cb.attack) / 2))
        nd = int(round((ca.defense + cb.defense) / 2))

        a_parts = ca.name.split()
        b_parts = cb.name.split()
        if len(a_parts) >= 2 and len(b_parts) >= 1:
            new_name = ' '.join(a_parts[:2] + b_parts[-1:])
        else:
            new_name = f"{ca.name} + {cb.name}"

        av = RARITY_ORDER.index(ca.rarity) if ca.rarity in RARITY_ORDER else 0
        bv = RARITY_ORDER.index(cb.rarity) if cb.rarity in RARITY_ORDER else 0
        avg = (av + bv) / 2.0
        frac = avg - math.floor(avg)
        if abs(frac - 0.5) < 1e-9:
            chosen_idx = math.floor(avg) + (1 if random.choice([True, False]) else 0)
        else:
            chosen_idx = int(round(avg))
        chosen_idx = max(0, min(chosen_idx, len(RARITY_ORDER)-1))
        new_rarity = RARITY_ORDER[chosen_idx]

        crafted_card = Card(id='0', name=new_name, rarity=new_rarity, type=cb.type, attack=na, defense=nd,
                            traits=list(dict.fromkeys((ca.traits or []) + (cb.traits or []))), description=f"Fusion of {ca.name} and {cb.name}")

        cid = inventory.create_crafted(crafted_card)
        inventory.remove_card(uid, a_id)
        inventory.remove_card(uid, b_id)
        inventory.add_card(uid, cid)

        e = discord.Embed(title=f"Crafted: {crafted_card.name}", color=discord.Color.blurple())
        e.add_field(name='Crafted ID', value=cid)
        e.add_field(name='Rarity', value=crafted_card.rarity)
        e.add_field(name='Attack / Defense', value=f"{crafted_card.attack} / {crafted_card.defense}")
        await interaction.response.send_message(embed=e, ephemeral=False)

    @combine.autocomplete('a_id')
    async def _combine_a_autocomplete(self, interaction: discord.Interaction, current: str):
        user = inventory.get_user(interaction.user.id)
        cards = list(map(str, user.get('cards', [])))
        choices = [app_commands.Choice(name=c, value=c) for c in cards if current.lower() in c.lower()][:25]
        return choices

    @combine.autocomplete('b_id')
    async def _combine_b_autocomplete(self, interaction: discord.Interaction, current: str):
        user = inventory.get_user(interaction.user.id)
        cards = list(map(str, user.get('cards', [])))
        choices = [app_commands.Choice(name=c, value=c) for c in cards if current.lower() in c.lower()][:25]
        return choices

    @tcg_group.command(name="collection", description="Show your collection (first page)")
    async def collection_cmd(self, interaction: discord.Interaction):
        user = inventory.get_user(interaction.user.id)
        if not user['cards']:
            return await interaction.response.send_message("You have no cards.", ephemeral=True)
        shown = user['cards'][:15]
        lines = []
        for s in shown:
            c = generate_card_from_seed(int(s)) if not str(s).upper().startswith('C') else inventory.get_crafted(s)
            lines.append(f"• {c.name} ({c.rarity}) [{c.id}]")
        e = discord.Embed(title="Your Collection", description='\n'.join(lines), color=discord.Color.teal())
        await interaction.response.send_message(embed=e, ephemeral=False)

    @tcg_group.command(name="dust", description="Dust a numeric card to gain dust")
    async def dust_cmd(self, interaction: discord.Interaction, seed: str):
        uid = interaction.user.id
        user = inventory.get_user(uid)
        if seed not in map(str, user.get('cards', [])):
            return await interaction.response.send_message("You don't own that card.", ephemeral=True)
        if str(seed).upper().startswith('C'):
            return await interaction.response.send_message("Cannot dust crafted cards.", ephemeral=True)
        card = generate_card_from_seed(int(seed))
        gain = {"C":5,"B":10,"A":25,"S":60,"X":150,"Z":400}.get(card.rarity, 0)
        inventory.remove_card(uid, seed)
        user['dust'] = user.get('dust',0) + gain
        try:
            inventory.save()
        except Exception:
            pass
        e = discord.Embed(title='Card Dusted', color=discord.Color.orange())
        e.add_field(name='Card', value=card.name, inline=False)
        e.add_field(name='Dust Gained', value=str(gain))
        await interaction.response.send_message(embed=e, ephemeral=False)

    @dust_cmd.autocomplete('seed')
    async def _dust_autocomplete(self, interaction: discord.Interaction, current: str):
        user = inventory.get_user(interaction.user.id)
        cards = [c for c in map(str, user.get('cards', [])) if not str(c).upper().startswith('C')]
        choices = [app_commands.Choice(name=c, value=c) for c in cards if current.lower() in c.lower()][:25]
        return choices

    # --------------------
    # Trades (slash)
    # --------------------
    @tcg_group.command(name='offer', description='Offer a trade to another user')
    async def offer(self, interaction: discord.Interaction, member: discord.Member, give: str, want: Optional[str] = None):
        giver = str(interaction.user.id)
        receiver = str(member.id)
        give_list = [x.strip() for x in give.split(',') if x.strip()]
        want_list = [x.strip() for x in (want or '').split(',') if x.strip()]
        user = inventory.get_user(interaction.user.id)
        owned = set(map(str, user.get('cards', [])))
        for cid in give_list:
            if cid not in owned:
                return await interaction.response.send_message(f"You don't own {cid}.", ephemeral=True)
        tid = f"T{int(time.time()*1000)}{random.randint(100,999)}"
        trade = {'id': tid, 'from': giver, 'to': receiver, 'give': give_list, 'want': want_list, 'status': 'pending', 'created_at': datetime.utcnow().isoformat()}
        inventory.trades[tid] = trade
        try:
            inventory.save()
        except Exception:
            pass
        e = discord.Embed(title=f"Trade Offer {tid}", description=f"From: {interaction.user.mention}\nTo: {member.mention}", color=discord.Color.gold())
        e.add_field(name='Give', value=', '.join(give_list) or '—')
        e.add_field(name='Want', value=', '.join(want_list) or '—')
        await interaction.response.send_message(embed=e, ephemeral=True)
        try:
            await member.send(embed=e)
        except Exception:
            pass

    @tcg_group.command(name='offers', description='List incoming offers to you')
    async def offers(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        out = []
        for t in inventory.trades.values():
            if t.get('to') == uid and t.get('status') == 'pending':
                out.append(f"{t['id']}: from <@{t['from']}> give: {','.join(t['give'])} want: {','.join(t['want'])}")
        if not out:
            return await interaction.response.send_message('No pending offers.', ephemeral=True)
        e = discord.Embed(title='Pending Offers', description='\n'.join(out), color=discord.Color.blurple())
        await interaction.response.send_message(embed=e, ephemeral=True)

    @tcg_group.command(name='accept', description='Accept a trade offered to you')
    async def accept(self, interaction: discord.Interaction, trade_id: str):
        t = inventory.trades.get(trade_id)
        if not t:
            return await interaction.response.send_message('Trade not found.', ephemeral=True)
        if t.get('to') != str(interaction.user.id):
            return await interaction.response.send_message('You are not the recipient of this trade.', ephemeral=True)
        if t.get('status') != 'pending':
            return await interaction.response.send_message('Trade is not pending.', ephemeral=True)
        giver_id = t['from']
        receiver_id = t['to']
        give_list = t['give']
        want_list = t['want']
        giver = inventory.get_user(int(giver_id))
        receiver = inventory.get_user(int(receiver_id))
        for cid in want_list:
            if cid not in map(str, receiver.get('cards', [])):
                return await interaction.response.send_message(f"You don't own requested card {cid} to fulfill the trade.", ephemeral=True)
        for cid in give_list:
            if cid not in map(str, giver.get('cards', [])):
                return await interaction.response.send_message(f"Offerer no longer owns {cid}; trade cancelled.", ephemeral=True)
        for cid in give_list:
            try: giver['cards'].remove(cid)
            except ValueError: pass
            receiver['cards'].append(cid)
        for cid in want_list:
            try: receiver['cards'].remove(cid)
            except ValueError: pass
            giver['cards'].append(cid)
        t['status'] = 'completed'
        t['completed_at'] = datetime.utcnow().isoformat()
        try:
            inventory.save()
        except Exception:
            pass
        e = discord.Embed(title=f"Trade {trade_id} Completed", color=discord.Color.green())
        e.add_field(name='From', value=f"<@{giver_id}>")
        e.add_field(name='To', value=f"<@{receiver_id}>")
        await interaction.response.send_message(embed=e, ephemeral=False)

    @tcg_group.command(name='decline', description='Decline a trade offered to you')
    async def decline(self, interaction: discord.Interaction, trade_id: str):
        t = inventory.trades.get(trade_id)
        if not t:
            return await interaction.response.send_message('Trade not found.', ephemeral=True)
        if t.get('to') != str(interaction.user.id):
            return await interaction.response.send_message('You are not the recipient of this trade.', ephemeral=True)
        if t.get('status') != 'pending':
            return await interaction.response.send_message('Trade is not pending.', ephemeral=True)
        t['status'] = 'declined'
        t['declined_at'] = datetime.utcnow().isoformat()
        try:
            inventory.save()
        except Exception:
            pass
        e = discord.Embed(title=f"Trade {trade_id} Declined", color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=e, ephemeral=False)

    @tcg_group.command(name='cancel', description='Cancel a trade you offered')
    async def cancel(self, interaction: discord.Interaction, trade_id: str):
        t = inventory.trades.get(trade_id)
        if not t:
            return await interaction.response.send_message('Trade not found.', ephemeral=True)
        if t.get('from') != str(interaction.user.id):
            return await interaction.response.send_message('Only the offerer can cancel this trade.', ephemeral=True)
        if t.get('status') != 'pending':
            return await interaction.response.send_message('Trade is not pending.', ephemeral=True)
        t['status'] = 'cancelled'
        t['cancelled_at'] = datetime.utcnow().isoformat()
        try:
            inventory.save()
        except Exception:
            pass
        e = discord.Embed(title=f"Trade {trade_id} Cancelled", color=discord.Color.dark_grey())
        await interaction.response.send_message(embed=e, ephemeral=False)

    # Admin give/remove as slash commands
    @tcg_group.command(name='give', description='(Owner) Give a card to a user')
    @app_owner_check()
    async def give(self, interaction: discord.Interaction, member: discord.Member, card_id: str):
        inventory.add_card(member.id, card_id)
        e = discord.Embed(title="Admin: Gave Card", color=discord.Color.dark_blue())
        e.add_field(name='Card', value=str(card_id))
        e.add_field(name='Recipient', value=member.mention)
        e.set_footer(text="Players normally obtain cards via openpack and combine; this is owner-only.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @tcg_group.command(name='remove', description='(Owner) Remove a specific card from a user')
    @app_owner_check()
    async def remove(self, interaction: discord.Interaction, member: discord.Member, card_id: str):
        ok = inventory.remove_card(member.id, card_id)
        if ok:
            e = discord.Embed(title='Admin: Removed Card', color=discord.Color.dark_red())
            e.add_field(name='Card', value=str(card_id))
            e.add_field(name='From', value=member.mention)
            await interaction.response.send_message(embed=e, ephemeral=True)
        else:
            await interaction.response.send_message("Card not found in user's collection.", ephemeral=True)

async def setup(bot:commands.Bot):
    # Avoid adding the cog twice (some deploy systems reload modules)
    if bot.get_cog('PsyvrseTCG') is not None:
        return
    try:
        await bot.add_cog(PsyvrseTCG(bot))
    except Exception:
        # If adding the cog fails, avoid crashing the loader.
        return

    # Register the app-command group if not already present so /tcg subcommands work
    try:
        if bot.tree.get_command('tcg') is None:
            bot.tree.add_command(PsyvrseTCG.tcg_group)
    except Exception:
        pass
