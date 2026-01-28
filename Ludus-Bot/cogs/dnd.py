import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from datetime import datetime
from typing import Optional, Dict, List
# Best-effort imports for TCG compatibility. Prefer the new psyvrse_tcg
# but gracefully fall back to the legacy manager if present.
tcg_manager = None
CARD_DATABASE = {}
try:
    from .psyvrse_tcg import CARD_DATABASE, inventory as _psy_inventory
    try:
        # Provide a tiny adapter exposing the legacy `award_for_game_event` API
        # backed by the new `PsyInventory` so other cogs can call it safely.
        class _PsyManagerAdapter:
            def award_for_game_event(self, user_id: str, category: str, amount: int = 1, chance: Optional[float] = None):
                awarded = []
                try:
                    uid = int(user_id)
                except Exception:
                    try:
                        uid = int(str(user_id))
                    except Exception:
                        uid = None
                for _ in range(max(0, int(amount))):
                    # pick a deterministic-ish numeric card id from pool
                    seed = random.randint(0, 2038399)
                    cid = str(seed)
                    try:
                        if uid is not None:
                            _psy_inventory.add_card(uid, cid)
                        awarded.append(cid)
                    except Exception:
                        # if saving fails, still include cid in the returned list
                        awarded.append(cid)
                return awarded

        tcg_manager = _PsyManagerAdapter()
    except Exception:
        tcg_manager = None
except Exception:
    CARD_DATABASE = {}

# If a legacy tcg manager exists, prefer it (maintain backward compatibility)
try:
    from .tcg import manager as _legacy_tcg_manager
    if _legacy_tcg_manager:
        tcg_manager = _legacy_tcg_manager
except Exception:
    pass

class DNDSystem(commands.Cog):
    """Fully Automated D&D System - No prep required!"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.campaigns_file = os.path.join(data_dir, "dnd_campaigns.json")
        self.campaigns = self.load_campaigns()
        
        # Character creation data
        self.races = {
            "human": {"hp_bonus": 5, "str": 0, "dex": 0, "int": 0, "wis": 0, "cha": 1},
            "elf": {"hp_bonus": 0, "str": 0, "dex": 2, "int": 1, "wis": 0, "cha": 0},
            "dwarf": {"hp_bonus": 10, "str": 2, "dex": 0, "int": 0, "wis": 1, "cha": 0},
            "halfling": {"hp_bonus": 0, "str": 0, "dex": 2, "int": 0, "wis": 0, "cha": 1},
            "orc": {"hp_bonus": 15, "str": 3, "dex": 0, "int": -1, "wis": 0, "cha": -1},
            "tiefling": {"hp_bonus": 5, "str": 0, "dex": 0, "int": 1, "wis": 0, "cha": 2},
            "dragonborn": {"hp_bonus": 10, "str": 2, "dex": 0, "int": 0, "wis": 0, "cha": 1}
        }
        
        self.classes = {
            "warrior": {"hp": 50, "str": 3, "dex": 1, "abilities": ["Slash", "Shield Bash", "Battle Cry"]},
            "mage": {"hp": 30, "str": 0, "dex": 1, "int": 4, "abilities": ["Fireball", "Ice Shard", "Lightning Bolt", "Mana Shield"]},
            "rogue": {"hp": 35, "str": 1, "dex": 4, "abilities": ["Backstab", "Poison Dart", "Stealth", "Evade"]},
            "cleric": {"hp": 40, "str": 1, "dex": 0, "wis": 3, "abilities": ["Heal", "Smite", "Bless", "Divine Shield"]},
            "ranger": {"hp": 40, "str": 2, "dex": 3, "abilities": ["Arrow Shot", "Animal Companion", "Track", "Multishot"]},
            "paladin": {"hp": 45, "str": 2, "dex": 0, "cha": 2, "abilities": ["Holy Strike", "Lay on Hands", "Divine Protection", "Aura of Courage"]}
        }
        
        self.settings = [
            {"name": "Frozen Wasteland", "description": "A desolate arctic realm where ancient evils slumber beneath eternal ice.", "difficulty": "Hard"},
            {"name": "Cursed Town", "description": "A once-prosperous village now plagued by dark magic and restless undead.", "difficulty": "Medium"},
            {"name": "Volcanic Citadel", "description": "A fortress built into an active volcano, home to fire elementals and dragons.", "difficulty": "Hard"},
            {"name": "Enchanted Forest", "description": "A mystical woodland where reality bends and fey creatures roam.", "difficulty": "Medium"},
            {"name": "Underground Catacombs", "description": "Ancient burial chambers filled with traps, treasures, and horrors.", "difficulty": "Medium"},
            {"name": "Sky Castle", "description": "A floating fortress high above the clouds, ruled by storm giants.", "difficulty": "Hard"},
            {"name": "Haunted Mansion", "description": "An abandoned estate where the dead refuse to rest.", "difficulty": "Easy"},
            {"name": "Desert Ruins", "description": "Crumbling temples half-buried in sand, guarding ancient secrets.", "difficulty": "Medium"}
        ]
        
        self.bosses = [
            {"name": "Warden of Shadows", "hp": 200, "weakness": "Holy damage", "type": "Undead Lord"},
            {"name": "Frost Tyrant", "hp": 250, "weakness": "Fire spells", "type": "Ice Dragon"},
            {"name": "Flame Sovereign", "hp": 220, "weakness": "Water/Ice", "type": "Fire Elemental"},
            {"name": "Mind Flayer", "hp": 180, "weakness": "Physical damage", "type": "Aberration"},
            {"name": "Ancient Lich", "hp": 240, "weakness": "Radiant damage", "type": "Undead Mage"},
            {"name": "Chimera", "hp": 210, "weakness": "Piercing damage", "type": "Beast"},
            {"name": "Vampire Lord", "hp": 200, "weakness": "Sunlight/Stakes", "type": "Undead Noble"}
        ]
        
        self.magic_items = [
            "Sword of Flames (+15 fire damage)",
            "Ring of Protection (+2 AC)",
            "Amulet of Health (+20 max HP)",
            "Boots of Speed (+3 initiative)",
            "Cloak of Invisibility (stealth advantage)",
            "Staff of Power (+2 spell damage)",
            "Healing Potion (restore 30 HP)",
            "Mana Potion (restore spell slot)",
            "Dagger of Venom (+poison damage)",
            "Shield of Reflection (reflect spells)"
        ]

    def load_campaigns(self):
        if os.path.exists(self.campaigns_file):
            with open(self.campaigns_file, 'r') as f:
                return json.load(f)
        return {}

    def save_campaigns(self):
        with open(self.campaigns_file, 'w') as f:
            json.dump(self.campaigns, f, indent=2)

    def generate_campaign(self, server_id: str):
        """Generate a complete campaign"""
        setting = random.choice(self.settings)
        boss = random.choice(self.bosses)
        
        # Generate side quests
        side_quests = random.sample([
            "Rescue a captured villager",
            "Find the ancient artifact",
            "Defeat the mini-boss guarding the passage",
            "Solve the riddle of the sphinx",
            "Gather magical components",
            "Clear the monster nest"
        ], 3)
        
        # Generate loot
        loot = random.sample(self.magic_items, 4)
        
        campaign = {
            "setting": setting,
            "boss": boss,
            "side_quests": side_quests,
            "loot": loot,
            "party": {},
            "dm": None,
            "dm_mode": None,  # "auto", "human", or None
            "current_scene": "intro",
            "party_xp": 0,
            "party_level": 1,
            "completed_quests": [],
            "discovered_items": [],
            "boss_defeated": False,
            "created_at": datetime.now().isoformat()
        }
        
        return campaign

    def generate_character(self, player_id: str, player_name: str):
        """Generate a random character"""
        race = random.choice(list(self.races.keys()))
        char_class = random.choice(list(self.classes.keys()))
        
        race_stats = self.races[race]
        class_stats = self.classes[char_class]
        
        # Base stats (roll 3d6)
        base_str = sum(random.randint(1, 6) for _ in range(3))
        base_dex = sum(random.randint(1, 6) for _ in range(3))
        base_int = sum(random.randint(1, 6) for _ in range(3))
        base_wis = sum(random.randint(1, 6) for _ in range(3))
        base_cha = sum(random.randint(1, 6) for _ in range(3))
        
        character = {
            "player_id": player_id,
            "player_name": player_name,
            "race": race,
            "class": char_class,
            "level": 1,
            "xp": 0,
            "hp": class_stats["hp"] + race_stats["hp_bonus"],
            "max_hp": class_stats["hp"] + race_stats["hp_bonus"],
            "str": base_str + race_stats.get("str", 0) + class_stats.get("str", 0),
            "dex": base_dex + race_stats.get("dex", 0) + class_stats.get("dex", 0),
            "int": base_int + race_stats.get("int", 0) + class_stats.get("int", 0),
            "wis": base_wis + race_stats.get("wis", 0) + class_stats.get("wis", 0),
            "cha": base_cha + race_stats.get("cha", 0) + class_stats.get("cha", 0),
            "abilities": class_stats["abilities"].copy(),
            "inventory": ["Basic Healing Potion"],
            "gold": 100
        }
        
        return character

    @app_commands.command(name="dnd", description="D&D Campaign Management")
    @app_commands.choices(action=[
        app_commands.Choice(name="🎲 Start Campaign", value="start"),
        app_commands.Choice(name="🚪 Join Party", value="join"),
        app_commands.Choice(name="⚔️ Take Action", value="action"),
        app_commands.Choice(name="📊 View Status", value="status"),
        app_commands.Choice(name="🎒 Check Inventory", value="inventory"),
        app_commands.Choice(name="🎭 Volunteer as DM", value="dm"),
        app_commands.Choice(name="💾 Save Campaign", value="save"),
        app_commands.Choice(name="📂 Load Campaign", value="load")
    ])
    async def dnd_command(
        self, 
        interaction: discord.Interaction, 
        action: app_commands.Choice[str],
        target: Optional[str] = None
    ):
        """Unified D&D command"""
        await interaction.response.defer()
        
        action_value = action.value if isinstance(action, app_commands.Choice) else action
        
        if action_value == "start":
            await self.start_campaign(interaction)
        elif action_value == "join":
            await self.join_party(interaction)
        elif action_value == "action":
            await self.take_action(interaction, target)
        elif action_value == "status":
            await self.view_status(interaction)
        elif action_value == "inventory":
            await self.check_inventory(interaction)
        elif action_value == "dm":
            await self.volunteer_dm(interaction)
        elif action_value == "save":
            await self.save_campaign_cmd(interaction)
        elif action_value == "load":
            await self.load_campaign_cmd(interaction)

    async def start_campaign(self, interaction: discord.Interaction):
        """Start a new D&D campaign"""
        server_id = str(interaction.guild.id)
        
        if server_id in self.campaigns and not self.campaigns[server_id].get("boss_defeated"):
            await interaction.followup.send("❌ A campaign is already active! Use `/dnd join` to join or complete the current campaign first.")
            return
        
        # Generate new campaign
        campaign = self.generate_campaign(server_id)
        self.campaigns[server_id] = campaign
        self.save_campaigns()
        
        # Create embed
        embed = discord.Embed(
            title="🎲 D&D Campaign Started!",
            description=f"**{campaign['setting']['name']}**\n{campaign['setting']['description']}",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📜 Main Objective",
            value=f"Defeat the **{campaign['boss']['name']}** ({campaign['boss']['type']})\n"
                  f"🎯 Weakness: {campaign['boss']['weakness']}",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Side Quests",
            value="\n".join([f"• {q}" for q in campaign['side_quests']]),
            inline=False
        )
        
        embed.add_field(
            name="🎭 DM Needed!",
            value="React with 🎭 to volunteer as DM, or wait 30s for auto-DM mode!",
            inline=False
        )
        
        embed.add_field(
            name="🚪 Join Now!",
            value="Use `/dnd join` to create your character and join the party!",
            inline=False
        )
        
        embed.set_footer(text=f"Difficulty: {campaign['setting']['difficulty']} | Party Level: 1")
        
        await interaction.followup.send(embed=embed)

    async def join_party(self, interaction: discord.Interaction):
        """Join the active campaign"""
        server_id = str(interaction.guild.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign! Use `/dnd start` to begin one.")
            return
        
        campaign = self.campaigns[server_id]
        player_id = str(interaction.user.id)
        
        if player_id in campaign["party"]:
            await interaction.followup.send("❌ You're already in the party!")
            return
        
        # Generate character
        character = self.generate_character(player_id, interaction.user.display_name)
        campaign["party"][player_id] = character
        self.save_campaigns()
        
        # Create character sheet embed
        embed = discord.Embed(
            title=f"⚔️ {character['player_name']} Joins the Party!",
            description=f"**{character['race'].title()} {character['class'].title()}** (Level {character['level']})",
            color=discord.Color.green()
        )
        
        embed.add_field(name="❤️ HP", value=f"{character['hp']}/{character['max_hp']}", inline=True)
        embed.add_field(name="💪 STR", value=character['str'], inline=True)
        embed.add_field(name="🏃 DEX", value=character['dex'], inline=True)
        embed.add_field(name="🧠 INT", value=character['int'], inline=True)
        embed.add_field(name="🦉 WIS", value=character['wis'], inline=True)
        embed.add_field(name="💬 CHA", value=character['cha'], inline=True)
        
        embed.add_field(
            name="✨ Abilities",
            value=", ".join(character['abilities']),
            inline=False
        )
        
        embed.add_field(
            name="🎒 Starting Gear",
            value="Basic Healing Potion, 100 gold",
            inline=False
        )
        
        party_count = len(campaign["party"])
        embed.set_footer(text=f"Party Members: {party_count} | Ready for adventure!")
        
        await interaction.followup.send(embed=embed)

    async def take_action(self, interaction: discord.Interaction, target: Optional[str]):
        """Take an action in combat/exploration"""
        server_id = str(interaction.guild.id)
        player_id = str(interaction.user.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign!")
            return
        
        campaign = self.campaigns[server_id]
        
        if player_id not in campaign["party"]:
            await interaction.followup.send("❌ You're not in the party! Use `/dnd join` first.")
            return
        
        character = campaign["party"][player_id]
        
        # Roll d20 for action
        roll = random.randint(1, 20)
        
        # Determine success
        if roll == 20:
            result = "🎯 **CRITICAL SUCCESS!**"
            damage = random.randint(20, 40)
            xp_gain = 50
        elif roll >= 15:
            result = "✅ **Success!**"
            damage = random.randint(10, 20)
            xp_gain = 25
        elif roll >= 10:
            result = "⚠️ **Partial Success**"
            damage = random.randint(5, 10)
            xp_gain = 15
        elif roll == 1:
            result = "💥 **CRITICAL FAILURE!**"
            damage = 0
            character['hp'] = max(0, character['hp'] - random.randint(5, 15))
            xp_gain = 5
        else:
            result = "❌ **Failure**"
            damage = 0
            xp_gain = 10
        
        # Add XP
        character['xp'] += xp_gain
        campaign['party_xp'] += xp_gain
        
        # Check for level up
        level_up = False
        if character['xp'] >= character['level'] * 100:
            character['level'] += 1
            character['max_hp'] += 10
            character['hp'] = character['max_hp']
            level_up = True
        
        self.save_campaigns()
        
        embed = discord.Embed(
            title=f"🎲 {character['player_name']}'s Action",
            description=f"**Roll:** d20 = {roll}\n{result}",
            color=discord.Color.gold() if roll >= 15 else discord.Color.orange()
        )
        
        if damage > 0:
            embed.add_field(name="⚔️ Damage Dealt", value=f"{damage} damage!", inline=True)
        
        embed.add_field(name="✨ XP Gained", value=f"+{xp_gain} XP", inline=True)
        embed.add_field(name="❤️ Current HP", value=f"{character['hp']}/{character['max_hp']}", inline=True)
        
        if level_up:
            embed.add_field(
                name="🎉 LEVEL UP!",
                value=f"You reached level {character['level']}!\n+10 max HP, HP fully restored!",
                inline=False
            )

        # Chance to award TCG card(s) for high-tier DnD actions
        if tcg_manager and roll >= 15:
            try:
                awarded = tcg_manager.award_for_game_event(player_id, 'mythic')
                if awarded:
                    names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                    embed.add_field(name='🎴 Bonus Card', value=', '.join(names), inline=False)
            except Exception:
                pass

        await interaction.followup.send(embed=embed)

    async def view_status(self, interaction: discord.Interaction):
        """View campaign and party status"""
        server_id = str(interaction.guild.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign!")
            return
        
        campaign = self.campaigns[server_id]
        
        embed = discord.Embed(
            title=f"📊 {campaign['setting']['name']} - Status",
            description=campaign['setting']['description'],
            color=discord.Color.blue()
        )
        
        # Party status
        party_list = []
        for player_id, char in campaign["party"].items():
            party_list.append(
                f"• **{char['player_name']}** - {char['race'].title()} {char['class'].title()} (Lv{char['level']})\n"
                f"  HP: {char['hp']}/{char['max_hp']} | XP: {char['xp']}"
            )
        
        if party_list:
            embed.add_field(
                name=f"⚔️ Party ({len(party_list)} members)",
                value="\n".join(party_list),
                inline=False
            )
        
        # Objectives
        embed.add_field(
            name="🎯 Main Objective",
            value=f"Defeat **{campaign['boss']['name']}**",
            inline=False
        )
        
        # Side quests
        remaining_quests = [q for q in campaign['side_quests'] if q not in campaign['completed_quests']]
        if remaining_quests:
            embed.add_field(
                name="📜 Active Quests",
                value="\n".join([f"• {q}" for q in remaining_quests]),
                inline=False
            )
        
        # DM info
        dm_text = "🤖 Auto-DM" if campaign['dm_mode'] == "auto" else f"<@{campaign['dm']}>" if campaign['dm'] else "❓ No DM"
        embed.add_field(name="🎭 Dungeon Master", value=dm_text, inline=True)
        embed.add_field(name="📈 Party Level", value=campaign['party_level'], inline=True)
        embed.add_field(name="✨ Party XP", value=campaign['party_xp'], inline=True)
        
        await interaction.followup.send(embed=embed)

    async def check_inventory(self, interaction: discord.Interaction):
        """Check player inventory"""
        server_id = str(interaction.guild.id)
        player_id = str(interaction.user.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign!")
            return
        
        campaign = self.campaigns[server_id]
        
        if player_id not in campaign["party"]:
            await interaction.followup.send("❌ You're not in the party!")
            return
        
        character = campaign["party"][player_id]
        
        embed = discord.Embed(
            title=f"🎒 {character['player_name']}'s Inventory",
            color=discord.Color.gold()
        )
        
        if character['inventory']:
            embed.add_field(
                name="Items",
                value="\n".join([f"• {item}" for item in character['inventory']]),
                inline=False
            )
        else:
            embed.add_field(name="Items", value="*Empty*", inline=False)
        
        embed.add_field(name="💰 Gold", value=character['gold'], inline=True)
        embed.add_field(name="❤️ HP", value=f"{character['hp']}/{character['max_hp']}", inline=True)
        embed.add_field(name="📊 Level", value=character['level'], inline=True)
        
        await interaction.followup.send(embed=embed)

    async def volunteer_dm(self, interaction: discord.Interaction):
        """Volunteer to be the DM"""
        server_id = str(interaction.guild.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign!")
            return
        
        campaign = self.campaigns[server_id]
        
        if campaign['dm']:
            await interaction.followup.send(f"❌ <@{campaign['dm']}> is already the DM!")
            return
        
        campaign['dm'] = str(interaction.user.id)
        campaign['dm_mode'] = "human"
        self.save_campaigns()
        
        await interaction.followup.send(f"🎭 **{interaction.user.display_name}** is now the Dungeon Master! The fate of the party is in your hands...")

    async def save_campaign_cmd(self, interaction: discord.Interaction):
        """Save the current campaign"""
        server_id = str(interaction.guild.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No active campaign to save!")
            return
        
        self.save_campaigns()
        await interaction.followup.send("💾 Campaign saved successfully!")

    async def load_campaign_cmd(self, interaction: discord.Interaction):
        """Load a saved campaign"""
        server_id = str(interaction.guild.id)
        
        if server_id not in self.campaigns:
            await interaction.followup.send("❌ No saved campaign found!")
            return
        
        campaign = self.campaigns[server_id]
        
        embed = discord.Embed(
            title="📂 Campaign Loaded!",
            description=f"**{campaign['setting']['name']}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="⚔️ Party Members", value=len(campaign['party']), inline=True)
        embed.add_field(name="📈 Party Level", value=campaign['party_level'], inline=True)
        embed.add_field(name="✨ Party XP", value=campaign['party_xp'], inline=True)
        
        await interaction.followup.send("📂 Campaign loaded!", embed=embed)

async def setup(bot):
    # Idempotent setup: avoid adding the cog or app command twice
    if bot.get_cog('DNDSystem') is not None:
        return
    try:
        await bot.add_cog(DNDSystem(bot))
    except Exception:
        return
    # App commands declared on the Cog are registered automatically when the
    # cog is added. Avoid explicitly calling `bot.tree.add_command` here to
    # prevent duplicate registrations during extension reloads.
