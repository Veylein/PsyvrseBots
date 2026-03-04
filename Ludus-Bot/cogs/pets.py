import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from datetime import datetime
from leaderboard_manager import leaderboard_manager

try:
    from utils.stat_hooks import us_inc as _pet_inc
except Exception:
    _pet_inc = None

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_COL_PET      = discord.Colour.from_str("#f0a500")
_COL_GREEN    = discord.Colour.from_str("#2ecc71")
_COL_RED      = discord.Colour.from_str("#e74c3c")
_COL_BLUE     = discord.Colour.from_str("#3498db")
_COL_PURPLE   = discord.Colour.from_str("#9b59b6")
_COL_GOLD     = discord.Colour.from_str("#f1c40f")

# Rarity colours
_RARITY_COLOUR = {
    "Common":    discord.Colour.from_str("#95a5a6"),
    "Uncommon":  discord.Colour.from_str("#2ecc71"),
    "Rare":      discord.Colour.from_str("#3498db"),
    "Epic":      discord.Colour.from_str("#9b59b6"),
    "Legendary": discord.Colour.from_str("#f1c40f"),
}
_RARITY_WEIGHT = {
    "Common": 55, "Uncommon": 28, "Rare": 12, "Epic": 4, "Legendary": 1
}

# ─── Pet database ─────────────────────────────────────────────────────────────
# perks keys:
#   gambling_mult     – multiplier on winnings  (1.15 = +15%)
#   gambling_loss_red – fraction of losses reduced  (0.20 = lose 20% less)
#   gambling_jackpot  – extra jackpot/bonus-round chance added (0.05 = +5%)
#   fishing_mult      – fishing catch-rate multiplier
#   fishing_rare      – extra rare-fish probability (additive)
#   fishing_value     – fish sell-price multiplier
#   mining_speed      – mining tick-speed multiplier
#   mining_rare       – extra rare-ore drop chance
#   mining_xp         – mining XP multiplier
#   farm_yield        – harvest yield multiplier
#   farm_auto_tend    – chance to auto-tend on harvest
#   coins_mult        – flat coin-gain multiplier on ALL activities
#   daily_bonus       – extra % on daily reward
#   xp_mult           – global XP multiplier
_AVAILABLE_PETS = [
    # ── COMMON ──────────────────────────────────────────────────────────────
    {
        "emoji": "🐯", "name": "Tiger", "rarity": "Common",
        "behavior": "aggressive", "farm_impact": "trample",
        "perk_label": "Gambler's Fury",
        "perk_desc":  "+15% gambling winnings · +10% mining speed",
        "perks": {"gambling_mult": 1.15, "mining_speed": 1.10},
    },
    {
        "emoji": "🐶", "name": "Dog", "rarity": "Common",
        "behavior": "loyal", "farm_impact": "dig",
        "perk_label": "Miner's Companion",
        "perk_desc":  "+20% mining XP · +15% rare ore chance · +10% farm yield",
        "perks": {"mining_xp": 1.20, "mining_rare": 0.15, "farm_yield": 1.10},
    },
    {
        "emoji": "🐱", "name": "Cat", "rarity": "Common",
        "behavior": "lazy", "farm_impact": "none",
        "perk_label": "Fisher's Luck",
        "perk_desc":  "+20% fishing catch · +15% rare fish chance",
        "perks": {"fishing_mult": 1.20, "fishing_rare": 0.15},
    },
    {
        "emoji": "🐹", "name": "Hamster", "rarity": "Common",
        "behavior": "playful", "farm_impact": "hoard",
        "perk_label": "Coin Hoarder",
        "perk_desc":  "+12% all coin gains · +5% fishing · +8% farm yield",
        "perks": {"coins_mult": 1.12, "fishing_mult": 1.05, "farm_yield": 1.08},
    },
    {
        "emoji": "🐍", "name": "Snake", "rarity": "Common",
        "behavior": "sneaky", "farm_impact": "none",
        "perk_label": "Risk Reducer",
        "perk_desc":  "-20% gambling losses · +15% daily bonus",
        "perks": {"gambling_loss_red": 0.20, "daily_bonus": 0.15},
    },
    {
        "emoji": "🐴", "name": "Horse", "rarity": "Common",
        "behavior": "strong", "farm_impact": "trample",
        "perk_label": "Harvest Champion",
        "perk_desc":  "+30% farm yield · +40% auto-tend chance · +15% mining speed",
        "perks": {"farm_yield": 1.30, "farm_auto_tend": 0.40, "mining_speed": 1.15},
    },
    # ── UNCOMMON ─────────────────────────────────────────────────────────────
    {
        "emoji": "🐼", "name": "Panda", "rarity": "Uncommon",
        "behavior": "peaceful", "farm_impact": "eat",
        "perk_label": "Nature's Bounty",
        "perk_desc":  "+25% farm yield · +20% XP gain · +10% coins",
        "perks": {"farm_yield": 1.25, "xp_mult": 1.20, "coins_mult": 1.10},
    },
    {
        "emoji": "🐉", "name": "Dragon", "rarity": "Uncommon",
        "behavior": "chaotic", "farm_impact": "burn",
        "perk_label": "Economy Overlord",
        "perk_desc":  "+20% all coin gains · +5% jackpot chance · +10% rare ore",
        "perks": {"coins_mult": 1.20, "gambling_jackpot": 0.05, "mining_rare": 0.10},
    },
    {
        "emoji": "🐷", "name": "Pig", "rarity": "Uncommon",
        "behavior": "greedy", "farm_impact": "eat",
        "perk_label": "Lucky Snout",
        "perk_desc":  "+15% gambling winnings · -15% gambling losses · +10% daily",
        "perks": {"gambling_mult": 1.15, "gambling_loss_red": 0.15, "daily_bonus": 0.10},
    },
    {
        "emoji": "🐢", "name": "Turtle", "rarity": "Uncommon",
        "behavior": "patient", "farm_impact": "none",
        "perk_label": "Steady Grinder",
        "perk_desc":  "+25% XP gain · +15% daily bonus · +10% all coins",
        "perks": {"xp_mult": 1.25, "daily_bonus": 0.15, "coins_mult": 1.10},
    },
    # ── RARE ─────────────────────────────────────────────────────────────────
    {
        "emoji": "🦊", "name": "Fox", "rarity": "Rare",
        "behavior": "cunning", "farm_impact": "hoard",
        "perk_label": "Trickster's Edge",
        "perk_desc":  "+20% gambling winnings · +15% fishing · +12% all coins",
        "perks": {"gambling_mult": 1.20, "fishing_mult": 1.15, "coins_mult": 1.12},
    },
    {
        "emoji": "🦎", "name": "Axolotl", "rarity": "Rare",
        "behavior": "calm", "farm_impact": "none",
        "perk_label": "Aquatic Master",
        "perk_desc":  "+30% fishing catch · +25% rare fish · +20% fish sell price",
        "perks": {"fishing_mult": 1.30, "fishing_rare": 0.25, "fishing_value": 1.20},
    },
    {
        "emoji": "🐺", "name": "Wolf", "rarity": "Rare",
        "behavior": "fierce", "farm_impact": "trample",
        "perk_label": "Pack Hunter",
        "perk_desc":  "+25% gambling winnings · +10% jackpot chance · +15% mining speed",
        "perks": {"gambling_mult": 1.25, "gambling_jackpot": 0.10, "mining_speed": 1.15},
    },
    # ── EPIC ─────────────────────────────────────────────────────────────────
    {
        "emoji": "🦉", "name": "Owl", "rarity": "Epic",
        "behavior": "wise", "farm_impact": "none",
        "perk_label": "Scholar's Blessing",
        "perk_desc":  "+35% XP gain · +25% daily bonus · +15% all coins",
        "perks": {"xp_mult": 1.35, "daily_bonus": 0.25, "coins_mult": 1.15},
    },
    {
        "emoji": "🐲", "name": "Elder Dragon", "rarity": "Epic",
        "behavior": "ancient", "farm_impact": "burn",
        "perk_label": "Ancient Power",
        "perk_desc":  "+30% all coins · +15% jackpot · +20% mining rare ore",
        "perks": {"coins_mult": 1.30, "gambling_jackpot": 0.15, "mining_rare": 0.20},
    },
    # ── LEGENDARY ────────────────────────────────────────────────────────────
    {
        "emoji": "🦄", "name": "Unicorn", "rarity": "Legendary",
        "behavior": "magical", "farm_impact": "none",
        "perk_label": "Fortune's Chosen",
        "perk_desc":  "+25% ALL gains · +20% gambling · +20% fishing · +20% mining",
        "perks": {
            "coins_mult": 1.25, "xp_mult": 1.25, "gambling_mult": 1.20,
            "fishing_mult": 1.20, "mining_xp": 1.20, "farm_yield": 1.20,
            "daily_bonus": 0.20,
        },
    },
]

# Build lookup: name → template
_PET_BY_NAME = {p["name"]: p for p in _AVAILABLE_PETS}

_FARM_BEHAVIORS = {
    "trample": "Can trample and destroy crops",
    "burn":    "Might accidentally burn crops",
    "eat":     "Will eat crops when hungry",
    "dig":     "Might dig up planted seeds",
    "hoard":   "Steals harvested crops",
    "none":    "Doesn't interact with farms",
}


def _roll_pet() -> dict:
    """Weighted random roll across all pets by rarity."""
    pool  = []
    weights = []
    for p in _AVAILABLE_PETS:
        pool.append(p)
        weights.append(_RARITY_WEIGHT[p["rarity"]])
    return random.choices(pool, weights=weights, k=1)[0]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _bar(value: int, total: int = 100, length: int = 10) -> str:
    filled = round(value / total * length)
    return "█" * filled + "░" * (length - filled)


def _mood(happiness: int) -> str:
    if happiness >= 80: return "😄 Ecstatic"
    if happiness >= 60: return "😊 Happy"
    if happiness >= 40: return "😐 Okay"
    if happiness >= 20: return "😟 Unhappy"
    return "😢 Miserable"


def _rarity_stars(rarity: str) -> str:
    return {"Common": "⬜", "Uncommon": "🟢", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟡"}.get(rarity, "")


def _pet_template(pet_data: dict) -> dict:
    """Return the static template dict for a saved pet (matched by 'type')."""
    return _PET_BY_NAME.get(pet_data.get("type", ""), {})


def _pet_perk(pet_data: dict, perk_key: str, default=1.0):
    """Read a perk value from the pet's template (or return default)."""
    tmpl = _pet_template(pet_data)
    return tmpl.get("perks", {}).get(perk_key, default)


def _pet_status_text(pet: dict) -> str:
    hunger    = pet["hunger"]
    happiness = pet["happiness"]
    energy    = pet["energy"]
    adopted   = pet["adopted"][:10]
    tmpl      = _pet_template(pet)
    rarity    = tmpl.get("rarity", "Common")
    farm_desc = _FARM_BEHAVIORS.get(pet.get("farm_impact", "none"), "—")
    perk_label= tmpl.get("perk_label", "No perks")
    perk_desc = tmpl.get("perk_desc", "")
    star      = _rarity_stars(rarity)

    warnings = []
    if hunger    < 30: warnings.append("⚠️ **Hungry** — feed me soon!")
    if happiness < 30: warnings.append("⚠️ **Sad** — play with me!")
    if energy    < 20: warnings.append("⚠️ **Exhausted** — needs rest!")
    warning_block = ("\n" + "\n".join(warnings)) if warnings else ""

    return (
        f"## {pet['emoji']} {pet['name']}\n"
        f"-# {star} {rarity} · {pet['behavior'].title()} · Adopted {adopted}\n\n"
        f"🍖 **Hunger**    `{_bar(hunger)}`  {hunger}/100\n"
        f"😊 **Happiness** `{_bar(happiness)}`  {happiness}/100\n"
        f"⚡ **Energy**    `{_bar(energy)}`  {energy}/100\n\n"
        f"🎭 Mood: {_mood(happiness)}\n"
        f"🌾 Farm: {farm_desc}\n\n"
        f"✨ **{perk_label}**\n"
        f"-# {perk_desc}"
        f"{warning_block}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard View (Components V2)
# ─────────────────────────────────────────────────────────────────────────────

class PetDashboardView(discord.ui.LayoutView):
    def __init__(self, cog: "Pets", user: discord.User | discord.Member) -> None:
        super().__init__(timeout=180)
        self.cog  = cog
        self.user = user
        self._build()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your pet panel!", ephemeral=True)
            return False
        return True

    # ── build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.clear_items()
        uid = str(self.user.id)
        pet = self.cog.pets_data.get(uid)
        if pet:
            self._render_dashboard(pet)
        else:
            self._render_no_pet()

    def _render_dashboard(self, pet: dict) -> None:
        text = _pet_status_text(pet)

        feed_b  = discord.ui.Button(emoji="🍖", label="Feed",  style=discord.ButtonStyle.success,   custom_id="pet_feed")
        play_b  = discord.ui.Button(emoji="🎾", label="Play",  style=discord.ButtonStyle.primary,   custom_id="pet_play")
        walk_b  = discord.ui.Button(emoji="🚶", label="Walk",  style=discord.ButtonStyle.primary,   custom_id="pet_walk")
        rel_b   = discord.ui.Button(emoji="💔", label="Release", style=discord.ButtonStyle.danger,  custom_id="pet_release")

        feed_b.callback  = self._feed_cb
        play_b.callback  = self._play_cb
        walk_b.callback  = self._walk_cb
        rel_b.callback   = self._release_cb

        # Disable buttons when not possible
        if pet["hunger"]    >= 90: feed_b.disabled = True
        if pet["energy"]    <  20: play_b.disabled = True; walk_b.disabled = True

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(feed_b, play_b, walk_b, rel_b),
            accent_colour=_COL_PET,
        ))

    def _render_no_pet(self) -> None:
        adopt_count = self.cog.get_adopt_count(self.user.id)
        is_free     = adopt_count == 0

        if is_free:
            text = (
                "## 🎰 Adopt a Pet!\n\n"
                "Roll for a **random** pet companion!\n"
                "Your **first pet is FREE!** 🎉\n\n"
                "Rarer pets have stronger perks:\n\n"
                "⬜ Common · 🟢 Uncommon · 🔵 Rare · 🟣 Epic · 🟡 **Legendary**\n\n"
                "-# Rates: 55% / 28% / 12% / 4% / 1%"
            )
            col   = _COL_GREEN
            label = "🎰 Roll for Pet! (FREE)"
        else:
            text = (
                "## 🎰 Adopt a Pet!\n\n"
                "Roll for a **random** pet companion!\n"
                "Cost: **10,000 coins** 💰\n\n"
                "Rarer pets have stronger perks:\n\n"
                "⬜ Common · 🟢 Uncommon · 🔵 Rare · 🟣 Epic · 🟡 **Legendary**\n\n"
                "-# Rates: 55% / 28% / 12% / 4% / 1%"
            )
            col   = _COL_BLUE
            label = "🎰 Roll for Pet! (10,000 coins)"

        roll_b          = discord.ui.Button(label=label, style=discord.ButtonStyle.success, custom_id="pet_roll")
        roll_b.callback = self._roll_cb

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(roll_b),
            accent_colour=col,
        ))

    # ── action callbacks ────────────────────────────────────────────────────

    _ADOPT_COST = 10_000

    async def _roll_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        if uid in self.cog.pets_data:
            await interaction.response.send_message("You already have a pet!", ephemeral=True)
            return

        adopt_count = self.cog.get_adopt_count(self.user.id)
        if adopt_count > 0:
            econ = self.cog.bot.get_cog("Economy")
            if not econ:
                await interaction.response.send_message("❌ Economy system unavailable!", ephemeral=True)
                return
            balance = econ.get_balance(self.user.id)
            if balance < self._ADOPT_COST:
                await interaction.response.send_message(
                    f"❌ Adopting a pet costs **{self._ADOPT_COST:,} coins**!\n"
                    f"You only have **{balance:,} coins** 😿",
                    ephemeral=True,
                )
                return
            econ.remove_coins(self.user.id, self._ADOPT_COST)

        tmpl = _roll_pet()
        pet = {
            "emoji":       tmpl["emoji"],
            "type":        tmpl["name"],
            "name":        f"{self.user.name}'s {tmpl['name']}",
            "hunger":      50,
            "happiness":   50,
            "energy":      50,
            "adopted":     str(discord.utils.utcnow()),
            "behavior":    tmpl["behavior"],
            "farm_impact": tmpl["farm_impact"],
        }
        self.cog.pets_data[uid] = pet
        self.cog._increment_adopt_count(self.user.id)
        self.cog.save_pets()
        try:
            leaderboard_manager.increment_stat(interaction.guild_id, "pet_adoptions", 1,
                                               getattr(interaction.guild, "name", ""))
        except Exception:
            pass
        try:
            econ = self.cog.bot.get_cog("Economy")
            if econ and adopt_count == 0: econ.add_coins(self.user.id, 50, "pet_adopt")  # welcome bonus only on first pet
        except Exception:
            pass
        try:
            pcog = self.cog.bot.get_cog("Profile")
            if pcog and hasattr(pcog, "profile_manager"):
                pcog.profile_manager.increment_stat(self.user.id, "pets_owned")
        except Exception:
            pass
        self._build()
        await interaction.response.edit_message(view=self)

    async def _feed_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        pet = self.cog.pets_data.get(uid)
        if not pet:
            await interaction.response.send_message("You don't have a pet!", ephemeral=True)
            return
        if pet["hunger"] >= 90:
            await interaction.response.send_message(f"{pet['emoji']} is already full!", ephemeral=True)
            return
        pet["hunger"]    = min(100, pet["hunger"]    + 30)
        pet["happiness"] = min(100, pet["happiness"] + 10)
        self.cog.save_pets()
        try:
            econ = self.cog.bot.get_cog("Economy")
            if econ: econ.add_coins(self.user.id, 5, "pet_feed")
        except Exception:
            pass
        try:
            pcog = self.cog.bot.get_cog("Profile")
            if pcog and hasattr(pcog, "profile_manager"):
                pcog.profile_manager.increment_stat(self.user.id, "pet_fed_count")
        except Exception:
            pass
        if _pet_inc:
            try: _pet_inc(self.user.id, "pets_fed")
            except Exception: pass
        self._build()
        await interaction.response.edit_message(view=self)

    async def _play_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        pet = self.cog.pets_data.get(uid)
        if not pet:
            await interaction.response.send_message("You don't have a pet!", ephemeral=True)
            return
        if pet["energy"] < 20:
            await interaction.response.send_message(f"{pet['emoji']} is too tired to play!", ephemeral=True)
            return
        pet["happiness"] = min(100, pet["happiness"] + 25)
        pet["energy"]    = max(0,   pet["energy"]    - 20)
        pet["hunger"]    = max(0,   pet["hunger"]    - 10)
        self.cog.save_pets()
        try:
            econ = self.cog.bot.get_cog("Economy")
            if econ: econ.add_coins(self.user.id, 15, "pet_play")
        except Exception:
            pass
        try:
            pcog = self.cog.bot.get_cog("Profile")
            if pcog and hasattr(pcog, "profile_manager"):
                pcog.profile_manager.increment_stat(self.user.id, "pet_played_count")
        except Exception:
            pass
        if _pet_inc:
            try: _pet_inc(self.user.id, "pets_played_with")
            except Exception: pass
        self._build()
        await interaction.response.edit_message(view=self)

    async def _walk_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        pet = self.cog.pets_data.get(uid)
        if not pet:
            await interaction.response.send_message("You don't have a pet!", ephemeral=True)
            return
        if pet["energy"] < 15:
            await interaction.response.send_message(f"{pet['emoji']} is too tired for a walk!", ephemeral=True)
            return
        pet["happiness"] = min(100, pet["happiness"] + 15)
        pet["energy"]    = max(0,   pet["energy"]    - 15)
        pet["hunger"]    = max(0,   pet["hunger"]    - 15)
        self.cog.save_pets()
        try:
            econ = self.cog.bot.get_cog("Economy")
            if econ: econ.add_coins(self.user.id, 10, "pet_walk")
        except Exception:
            pass
        try:
            pcog = self.cog.bot.get_cog("Profile")
            if pcog and hasattr(pcog, "profile_manager"):
                pcog.profile_manager.increment_stat(self.user.id, "pet_walked_count")
        except Exception:
            pass
        self._build()
        await interaction.response.edit_message(view=self)

    async def _release_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        if uid not in self.cog.pets_data:
            await interaction.response.send_message("You don't have a pet!", ephemeral=True)
            return
        # Confirmation step
        self.clear_items()
        pet = self.cog.pets_data[uid]
        text = (
            f"## 💔 Release {pet['emoji']} {pet['type']}?\n\n"
            f"Are you sure you want to release **{pet['name']}**?\n\n"
            f"⚠️ Your **next pet will cost 10,000 coins** to adopt!\n"
            f"-# This cannot be undone."
        )
        yes_b = discord.ui.Button(label="Yes, release", emoji="💔", style=discord.ButtonStyle.danger,   custom_id="pet_rel_yes")
        no_b  = discord.ui.Button(label="Cancel",       emoji="↩️",  style=discord.ButtonStyle.secondary, custom_id="pet_rel_no")
        yes_b.callback = self._release_confirm_cb
        no_b.callback  = self._release_cancel_cb
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(yes_b, no_b),
            accent_colour=_COL_RED,
        ))
        await interaction.response.edit_message(view=self)

    async def _release_confirm_cb(self, interaction: discord.Interaction) -> None:
        uid = str(self.user.id)
        self.cog.pets_data.pop(uid, None)
        self.cog.save_pets()
        self._build()
        await interaction.response.edit_message(view=self)

    async def _release_cancel_cb(self, interaction: discord.Interaction) -> None:
        self._build()
        await interaction.response.edit_message(view=self)


# ─────────────────────────────────────────────────────────────────────────────
# Cog
# ─────────────────────────────────────────────────────────────────────────────

class Pets(commands.Cog, name="Pets"):
    """🐾 Adopt and care for a virtual pet companion!"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        self.pets_file = os.path.join(data_dir, "pets.json")
        self.pets_data = self.load_pets()

    def load_pets(self) -> dict:
        if os.path.exists(self.pets_file):
            with open(self.pets_file, "r") as f:
                return json.load(f)
        return {}

    def save_pets(self) -> None:
        with open(self.pets_file, "w") as f:
            json.dump(self.pets_data, f, indent=2)

    # ── slash command ────────────────────────────────────────────────────────

    @app_commands.command(name="pet", description="🐾 Open your pet dashboard — adopt, feed, play and walk!")
    async def pet_slash(self, interaction: discord.Interaction) -> None:
        view = PetDashboardView(self, interaction.user)
        await interaction.response.send_message(view=view)

    # ── adoption counter ─────────────────────────────────────────────────────

    def get_adopt_count(self, user_id: int) -> int:
        """How many pets this user has adopted in total."""
        uid   = str(user_id)
        count = self.pets_data.get("__adoptions__", {}).get(uid, 0)
        # Legacy fallback: users who had a pet before adoption tracking was added
        # treat them as already having adopted 1 (so the next costs 10k)
        if count == 0 and uid in self.pets_data and uid != "__adoptions__":
            return 1
        return count

    def _increment_adopt_count(self, user_id: int) -> None:
        adoptions = self.pets_data.setdefault("__adoptions__", {})
        adoptions[str(user_id)] = adoptions.get(str(user_id), 0) + 1

    # ── helper methods used by other cogs ────────────────────────────────────

    def check_pet_farm_interaction(self, user_id: str) -> dict:
        user_id = str(user_id)
        if user_id not in self.pets_data:
            return {"interaction": False}
        
        pet = self.pets_data[user_id]
        farm_impact = pet.get('farm_impact', 'none')
        hunger = pet.get('hunger', 50)
        
        # Pet only causes trouble if hungry (below 40) and has farm impact
        if hunger < 40 and farm_impact != 'none':
            chance = (40 - hunger) * 2  # 0-80% chance based on hunger
            if random.randint(1, 100) <= chance:
                return {
                    "interaction": True,
                    "type": farm_impact,
                    "pet_name": pet['name'],
                    "pet_emoji": pet['emoji'],
                    "pet_type": pet['type']
                }
        
        return {"interaction": False}

    # ─── generic perk accessor ────────────────────────────────────────────

    def _get_pet_perk(self, user_id: int, perk_key: str, default=None):
        """Return a perk value for user_id's pet, or `default` if no pet / perk missing."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None:
            return default
        return _pet_perk(pet, perk_key, default if default is not None else (0.0 if perk_key not in ("coins_mult", "xp_mult", "fishing_mult", "farm_yield", "mining_speed", "mining_xp", "fishing_value") else 1.0))

    # ─── fishing ─────────────────────────────────────────────────────────────

    def get_fishing_multiplier(self, user_id: int) -> float:
        """Catch-rate multiplier from pet perk (fishing_mult)."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "fishing_mult", 1.0)

    def get_fishing_rare_bonus(self, user_id: int) -> float:
        """Extra rare-fish probability additive bonus from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "fishing_rare", 0.0)

    def get_fishing_value_multiplier(self, user_id: int) -> float:
        """Fish sell-price multiplier from pet perk (fishing_value)."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "fishing_value", 1.0)

    def get_rarity_multiplier(self, user_id: int, rarity: str) -> float:
        """Legacy shim — returns fishing_rare as additive bonus on rare catches."""
        bonus = self.get_fishing_rare_bonus(user_id)
        return 1.0 + bonus  # convert additive → multiplicative for callers expecting a multiplier

    # ─── farming ─────────────────────────────────────────────────────────────

    def get_farm_yield_multiplier(self, user_id: int) -> float:
        """Farm harvest yield multiplier from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "farm_yield", 1.0)

    def get_auto_tend_chance(self, user_id: int) -> float:
        """Auto-tend probability from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "farm_auto_tend", 0.0)

    # ─── mining ─────────────────────────────────────────────────────────────

    def get_mining_speed_multiplier(self, user_id: int) -> float:
        """Mining tick-speed multiplier from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "mining_speed", 1.0)

    def get_mining_xp_multiplier(self, user_id: int) -> float:
        """Mining XP multiplier from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "mining_xp", 1.0)

    def get_mining_rare_bonus(self, user_id: int) -> float:
        """Extra rare-ore drop chance additive bonus from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "mining_rare", 0.0)

    # ─── gambling ────────────────────────────────────────────────────────────

    def get_gambling_multiplier(self, user_id: int) -> float:
        """Winnings multiplier from pet perk (gambling_mult)."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "gambling_mult", 1.0)

    def get_gambling_loss_reduction(self, user_id: int) -> float:
        """Fraction of losses reduced [0-1] from pet perk (gambling_loss_red)."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "gambling_loss_red", 0.0)

    def get_gambling_jackpot_bonus(self, user_id: int) -> float:
        """Extra jackpot / bonus-round chance additive from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "gambling_jackpot", 0.0)

    # ─── economy / global ────────────────────────────────────────────────────

    def get_coin_bonus(self, user_id: int) -> int:
        """Flat coin bonus from pet perk (coins_mult applied as +X coins on 100 base)."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0
        mult = _pet_perk(pet, "coins_mult", 1.0)
        return round((mult - 1.0) * 100)  # convert to int bonus (e.g. 1.20 → 20)

    def get_coins_multiplier(self, user_id: int) -> float:
        """Global coin-gain multiplier from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "coins_mult", 1.0)

    def get_xp_multiplier(self, user_id: int) -> float:
        """Global XP multiplier from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 1.0
        return _pet_perk(pet, "xp_mult", 1.0)

    def get_daily_bonus(self, user_id: int) -> float:
        """Extra fraction added to daily reward [0-1] from pet perk."""
        uid = str(user_id)
        pet = self.pets_data.get(uid)
        if pet is None: return 0.0
        return _pet_perk(pet, "daily_bonus", 0.0)

async def setup(bot):
    await bot.add_cog(Pets(bot))
