import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List

try:
    from .tcg import manager as tcg_manager
    from .psyvrse_tcg import CARD_DATABASE
except Exception:
    tcg_manager = None
    CARD_DATABASE = {}

SCHOOL_EMOJIS = {
    "Elemental": "🌊",
    "Cosmic": "🌌",
    "Forbidden": "☠️",
    "Divine": "✨",
}

TYPE_EMOJIS = {
    "fire": "🔥", "water": "💧", "thunder": "⚡", "ice": "❄️",
    "wind": "🌀", "earth": "🌍", "gravity": "⚫", "space": "🌌",
    "time": "⏳", "blood": "🩸", "shadow": "🌑", "curse": "👁️",
    "light": "🌟", "holy": "✨",
}


class ShopView(discord.ui.View):
    """Interactive spell shop with dropdown select + buy button."""

    def __init__(self, cog, user_id: str, available_spells: list):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.selected_spell: str | None = None

        options = []
        for spell_name in available_spells[:25]:
            spell = cog.spells[spell_name]
            price = spell['power'] * 100
            te = TYPE_EMOJIS.get(spell['type'], "✨")
            options.append(discord.SelectOption(
                label=spell_name,
                value=spell_name,
                description=f"{price} Gold | {spell['school']} | Power: {spell['power']}",
                emoji=te,
            ))

        self.spell_select = discord.ui.Select(
            placeholder="Choose a spell to preview...",
            options=options,
            custom_id="spell_select",
        )
        self.spell_select.callback = self.spell_selected
        self.add_item(self.spell_select)

    async def spell_selected(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This shop isn't yours!", ephemeral=True)

        self.selected_spell = self.spell_select.values[0]
        spell = self.cog.spells[self.selected_spell]
        price = spell['power'] * 100
        wizard = self.cog.wizards[self.user_id]
        te = TYPE_EMOJIS.get(spell['type'], "✨")
        se = SCHOOL_EMOJIS.get(spell['school'], "🔮")

        embed = discord.Embed(
            title=f"{te} {self.selected_spell}",
            description=f"**School:** {se} {spell['school']} | **Type:** {spell['type'].title()}",
            color=discord.Color.gold(),
        )
        embed.add_field(name="⚡ Power", value=str(spell['power']), inline=True)
        embed.add_field(name="🔮 Mana Cost", value=str(spell['mana']), inline=True)
        embed.add_field(name="💰 Price", value=f"{price} Gold", inline=True)
        embed.add_field(name="✨ Effect", value=spell['effect'].replace('_', ' ').title(), inline=True)

        if self.selected_spell in wizard['spells']:
            embed.set_footer(text="✅ You already own this spell!")
        elif wizard['gold'] >= price:
            embed.set_footer(text=f"Your Gold: {wizard['gold']} | Click 💰 Buy Spell to purchase!")
        else:
            embed.set_footer(text=f"❌ Not enough gold! You have {wizard['gold']}, need {price}")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💰 Buy Spell", style=discord.ButtonStyle.success, custom_id="ww_buy_btn", row=1)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This shop isn't yours!", ephemeral=True)

        if not self.selected_spell:
            return await interaction.response.send_message("⚠️ Select a spell from the dropdown first!", ephemeral=True)

        wizard = self.cog.wizards[self.user_id]
        spell = self.cog.spells[self.selected_spell]
        price = spell['power'] * 100

        if self.selected_spell in wizard['spells']:
            return await interaction.response.send_message("✅ You already own this spell!", ephemeral=True)

        if wizard['gold'] < price:
            return await interaction.response.send_message(
                f"❌ Not enough gold! Need **{price}**, you have **{wizard['gold']}**.", ephemeral=True
            )

        # Process purchase
        wizard['gold'] -= price
        wizard['spells'].append(self.selected_spell)
        self.cog.save_data()

        te = TYPE_EMOJIS.get(spell['type'], "✨")
        available_spells = [s for s in self.cog.spells.keys() if s not in wizard['spells']]

        new_embed = discord.Embed(
            title="💰 Spell Shop",
            description=f"Your Gold: **{wizard['gold']}**\nSelect a spell from the dropdown to preview it, then click **💰 Buy Spell** to purchase.",
            color=discord.Color.gold(),
        )
        by_school: dict = {}
        for s in available_spells:
            sp = self.cog.spells[s]
            by_school.setdefault(sp['school'], []).append((s, sp))
        for school, spells in by_school.items():
            se = SCHOOL_EMOJIS.get(school, "🔮")
            lines = [f"{TYPE_EMOJIS.get(sp['type'], '✨')} **{sn}** — {sp['power'] * 100} Gold" for sn, sp in spells]
            new_embed.add_field(name=f"{se} {school}", value="\n".join(lines), inline=True)
        if not available_spells:
            new_embed.add_field(name="🎉 Collection Complete!", value="You own all available spells!", inline=False)

        new_view = ShopView(self.cog, self.user_id, available_spells) if available_spells else None
        await interaction.response.edit_message(
            content=f"✅ Purchased **{te} {self.selected_spell}** for **{price} Gold**!",
            embed=new_embed,
            view=new_view,
        )


class WizardWars(commands.Cog):
    """Wizard Wars - Spell-Based MMO Strategy System"""
    
    def __init__(self, bot):
        self.bot = bot
        _data_dir = os.getenv("RENDER_DISK_PATH", "data")
        os.makedirs(_data_dir, exist_ok=True)
        self.data_file = os.path.join(_data_dir, "wizard_wars_data.json")
        self.load_data()
        
        # Spell Database
        self.spells = {
            # ELEMENTAL SPELLS
            "Flame Burst": {"type": "fire", "power": 3, "mana": 30, "effect": "damage", "school": "Elemental"},
            "Inferno Wave": {"type": "fire", "power": 7, "mana": 70, "effect": "aoe_damage", "school": "Elemental"},
            "Pyroblast": {"type": "fire", "power": 10, "mana": 100, "effect": "massive_damage", "school": "Elemental"},
            "Water Shield": {"type": "water", "power": 4, "mana": 40, "effect": "shield", "school": "Elemental"},
            "Tidal Surge": {"type": "water", "power": 6, "mana": 60, "effect": "heal_damage", "school": "Elemental"},
            "Aqua Fortress": {"type": "water", "power": 9, "mana": 90, "effect": "massive_shield", "school": "Elemental"},
            "Lightning Strike": {"type": "thunder", "power": 5, "mana": 50, "effect": "chain_damage", "school": "Elemental"},
            "Thunderstorm": {"type": "thunder", "power": 8, "mana": 80, "effect": "multi_chain", "school": "Elemental"},
            "Frost Nova": {"type": "ice", "power": 4, "mana": 40, "effect": "freeze", "school": "Elemental"},
            "Blizzard": {"type": "ice", "power": 8, "mana": 80, "effect": "freeze_aoe", "school": "Elemental"},
            "Gale Twist": {"type": "wind", "power": 3, "mana": 30, "effect": "evasion", "school": "Elemental"},
            "Hurricane": {"type": "wind", "power": 7, "mana": 70, "effect": "knockback_aoe", "school": "Elemental"},
            "Earth Wall": {"type": "earth", "power": 5, "mana": 50, "effect": "barrier", "school": "Elemental"},
            "Earthquake": {"type": "earth", "power": 9, "mana": 90, "effect": "stun_aoe", "school": "Elemental"},
            
            # COSMIC SPELLS
            "Gravity Well": {"type": "gravity", "power": 6, "mana": 60, "effect": "pull", "school": "Cosmic"},
            "Black Hole": {"type": "gravity", "power": 10, "mana": 100, "effect": "crush_all", "school": "Cosmic"},
            "Spatial Rift": {"type": "space", "power": 5, "mana": 50, "effect": "teleport", "school": "Cosmic"},
            "Dimension Shift": {"type": "space", "power": 8, "mana": 80, "effect": "phase", "school": "Cosmic"},
            "Time Slow": {"type": "time", "power": 4, "mana": 40, "effect": "slow", "school": "Cosmic"},
            "Temporal Rewind": {"type": "time", "power": 9, "mana": 90, "effect": "undo_damage", "school": "Cosmic"},
            
            # FORBIDDEN SPELLS
            "Blood Drain": {"type": "blood", "power": 5, "mana": 50, "effect": "lifesteal", "school": "Forbidden"},
            "Hemorrhage": {"type": "blood", "power": 8, "mana": 80, "effect": "massive_lifesteal", "school": "Forbidden"},
            "Shadow Veil": {"type": "shadow", "power": 4, "mana": 40, "effect": "stealth", "school": "Forbidden"},
            "Void Embrace": {"type": "shadow", "power": 9, "mana": 90, "effect": "immune", "school": "Forbidden"},
            "Curse of Weakness": {"type": "curse", "power": 3, "mana": 30, "effect": "debuff", "school": "Forbidden"},
            "Doom": {"type": "curse", "power": 10, "mana": 100, "effect": "execute", "school": "Forbidden"},
            
            # DIVINE SPELLS
            "Holy Light": {"type": "light", "power": 4, "mana": 40, "effect": "heal", "school": "Divine"},
            "Radiance": {"type": "light", "power": 7, "mana": 70, "effect": "aoe_heal", "school": "Divine"},
            "Divine Smite": {"type": "holy", "power": 6, "mana": 60, "effect": "pure_damage", "school": "Divine"},
            "Judgement": {"type": "holy", "power": 10, "mana": 100, "effect": "ultimate", "school": "Divine"},
            "Blessing": {"type": "holy", "power": 3, "mana": 30, "effect": "buff", "school": "Divine"},
            "Resurrection": {"type": "holy", "power": 9, "mana": 90, "effect": "revive", "school": "Divine"},
        }
        
        # Spell Combos
        self.combos = {
            ("Flame Burst", "Gale Twist"): {"name": "Inferno Cyclone", "power": 12, "effect": "Massive fire tornado"},
            ("Frost Nova", "Lightning Strike"): {"name": "Glacial Shock", "power": 11, "effect": "Frozen lightning damage"},
            ("Shadow Veil", "Blood Drain"): {"name": "Vampiric Shadow", "power": 10, "effect": "Stealth lifesteal"},
            ("Water Shield", "Earth Wall"): {"name": "Fortress Barrier", "power": 13, "effect": "Impenetrable defense"},
            ("Gravity Well", "Black Hole"): {"name": "Singularity", "power": 15, "effect": "Ultimate void damage"},
            ("Holy Light", "Divine Smite"): {"name": "Celestial Wrath", "power": 12, "effect": "Holy devastation"},
        }
        
        # Territories
        self.territories = [
            "Crystal Peaks", "Shadow Vale", "Ember Wastes", "Frost Tundra",
            "Storm Heights", "Verdant Grove", "Void Nexus", "Golden Shores",
            "Mystic Marshes", "Titan's Rest", "Eclipse Valley", "Arcane Citadel"
        ]
    
    def load_data(self):
        """Load wizard wars data from JSON"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.wizards = data.get('wizards', {})
                self.guilds = data.get('guilds', {})
                self.territory_control = data.get('territories', {})
                self.active_events = data.get('events', {})
                self.leaderboards = data.get('leaderboards', {})
        except FileNotFoundError:
            self.wizards = {}
            self.guilds = {}
            self.territory_control = {}
            self.active_events = {}
            self.leaderboards = {}
    
    def save_data(self):
        """Save wizard wars data to JSON (atomic write)"""
        data = {
            'wizards': self.wizards,
            'guilds': self.guilds,
            'territories': self.territory_control,
            'events': self.active_events,
            'leaderboards': self.leaderboards
        }
        tmp = self.data_file + ".tmp"
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp, self.data_file)
        except Exception as e:
            print(f"[WizardWars] Save error: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
    
    def create_wizard(self, user_id: str, username: str) -> dict:
        """Create a new wizard profile"""
        wizard = {
            'name': username,
            'level': 1,
            'xp': 0,
            'mana': 100,
            'max_mana': 100,
            'hp': 100,
            'max_hp': 100,
            'gold': 1000,
            'spells': ["Flame Burst", "Water Shield", "Lightning Strike"],  # Starting spells
            'guild': None,
            'wins': 0,
            'losses': 0,
            'territories': 0,
            'rank': "Apprentice",
            'title': None,
            'equipped_spells': ["Flame Burst", "Water Shield", "Lightning Strike"],
            'spell_slots': 3
        }
        self.wizards[user_id] = wizard
        self.save_data()
        return wizard
    
    def calculate_damage(self, spell_name: str, attacker: dict) -> int:
        """Calculate spell damage based on wizard stats"""
        spell = self.spells.get(spell_name, {})
        base_power = spell.get('power', 0)
        level_bonus = attacker['level'] * 2
        return base_power * 10 + level_bonus
    
    def check_combo(self, spell1: str, spell2: str) -> Optional[dict]:
        """Check if two spells form a combo"""
        combo_key = (spell1, spell2)
        reverse_key = (spell2, spell1)
        
        if combo_key in self.combos:
            return self.combos[combo_key]
        elif reverse_key in self.combos:
            return self.combos[reverse_key]
        return None
    
    @app_commands.command(name="wizardwars", description="Play Wizard Wars - Spell-Based MMO Strategy")
    @app_commands.choices(action=[
        app_commands.Choice(name="🧙 Create Wizard", value="create"),
        app_commands.Choice(name="📚 View Spellbook", value="spellbook"),
        app_commands.Choice(name="⬆️ Upgrade Spell", value="upgrade"),
        app_commands.Choice(name="⚔️ Duel Wizard", value="duel"),
        app_commands.Choice(name="🏰 Guild Menu", value="guild"),
        app_commands.Choice(name="🗺️ Territory Map", value="territories"),
        app_commands.Choice(name="🌍 World Events", value="events"),
        app_commands.Choice(name="🏆 Leaderboards", value="leaderboard"),
        app_commands.Choice(name="💰 Spell Shop", value="shop"),
        app_commands.Choice(name="📊 My Profile", value="profile")
    ])
    async def wizardwars(self, interaction: discord.Interaction, action: str):
        """Main Wizard Wars command"""
        
        if action == "create":
            await self.create_wizard_action(interaction)
        elif action == "spellbook":
            await self.spellbook_action(interaction)
        elif action == "upgrade":
            await self.upgrade_action(interaction)
        elif action == "duel":
            await self.duel_action(interaction)
        elif action == "guild":
            await self.guild_action(interaction)
        elif action == "territories":
            await self.territories_action(interaction)
        elif action == "events":
            await self.events_action(interaction)
        elif action == "leaderboard":
            await self.leaderboard_action(interaction)
        elif action == "shop":
            await self.shop_action(interaction)
        elif action == "profile":
            await self.profile_action(interaction)
    
    @app_commands.command(name="ww", description="Wizard Wars shorthand")
    @app_commands.choices(action=[
        app_commands.Choice(name="🧙 Create Wizard", value="create"),
        app_commands.Choice(name="📚 View Spellbook", value="spellbook"),
        app_commands.Choice(name="⬆️ Upgrade Spell", value="upgrade"),
        app_commands.Choice(name="⚔️ Duel Wizard", value="duel"),
        app_commands.Choice(name="🏰 Guild Menu", value="guild"),
        app_commands.Choice(name="🗺️ Territory Map", value="territories"),
        app_commands.Choice(name="🌍 World Events", value="events"),
        app_commands.Choice(name="🏆 Leaderboards", value="leaderboard"),
        app_commands.Choice(name="💰 Spell Shop", value="shop"),
        app_commands.Choice(name="📊 My Profile", value="profile")
    ])
    async def ww(self, interaction: discord.Interaction, action: str):
        """Shorthand for Wizard Wars command"""
        await self.wizardwars.callback(self, interaction, action)
    
    async def create_wizard_action(self, interaction: discord.Interaction):
        """Create a new wizard"""
        user_id = str(interaction.user.id)
        
        if user_id in self.wizards:
            await interaction.response.send_message(
                "🧙 You already have a wizard! Use `/ww profile` to view your stats.",
                ephemeral=True
            )
            return
        
        wizard = self.create_wizard(user_id, interaction.user.name)
        
        embed = discord.Embed(
            title="🧙‍♂️ Wizard Created!",
            description=f"Welcome to the Wizard Wars, **{interaction.user.name}**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="⭐ Rank", value=wizard['rank'], inline=True)
        embed.add_field(name="📊 Level", value=f"{wizard['level']}", inline=True)
        embed.add_field(name="💰 Gold", value=f"{wizard['gold']}", inline=True)
        embed.add_field(
            name="📚 Starting Spells",
            value="🔥 Flame Burst\n💧 Water Shield\n⚡ Lightning Strike",
            inline=False
        )
        embed.add_field(
            name="🎯 Next Steps",
            value="• `/ww duel` - Challenge others\n• `/ww shop` - Buy new spells\n• `/ww guild` - Join a guild\n• `/ww territories` - Conquer land",
            inline=False
        )
        embed.set_footer(text="Your journey as a wizard begins now!")
        
        await interaction.response.send_message(embed=embed)
    
    async def spellbook_action(self, interaction: discord.Interaction):
        """View wizard's spellbook"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return
        
        wizard = self.wizards[user_id]
        
        embed = discord.Embed(
            title=f"📚 {wizard['name']}'s Spellbook",
            description=f"**Level {wizard['level']} {wizard['rank']}**",
            color=discord.Color.blue()
        )
        
        # Group spells by school
        schools = {}
        for spell_name in wizard['spells']:
            spell = self.spells.get(spell_name, {})
            school = spell.get('school', 'Unknown')
            if school not in schools:
                schools[school] = []
            
            equipped = "✅" if spell_name in wizard['equipped_spells'] else "⬜"
            power = spell.get('power', 0)
            mana = spell.get('mana', 0)
            schools[school].append(f"{equipped} **{spell_name}** - Power: {power} | Mana: {mana}")
        
        for school, spells in schools.items():
            embed.add_field(
                name=f"🌟 {school} Magic",
                value="\n".join(spells[:5]),  # Limit to 5 per field
                inline=False
            )
        
        embed.add_field(
            name="📊 Capacity",
            value=f"{len(wizard['spells'])}/50 Spells Learned\n{len(wizard['equipped_spells'])}/{wizard['spell_slots']} Equipped",
            inline=True
        )
        embed.add_field(
            name="💰 Resources",
            value=f"{wizard['gold']} Gold\n{wizard['mana']}/{wizard['max_mana']} Mana",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def upgrade_action(self, interaction: discord.Interaction):
        """Upgrade spell power"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return
        
        wizard = self.wizards[user_id]
        
        embed = discord.Embed(
            title="⬆️ Spell Upgrade System",
            description="Upgrade your spells to increase their power!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💡 How It Works",
            value="• Each upgrade costs Gold\n• Power increases by +1\n• Mana cost increases by +5\n• Max level: 10",
            inline=False
        )
        embed.add_field(
            name="🔧 Coming Soon",
            value="Full upgrade system with interactive selection!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def duel_action(self, interaction: discord.Interaction):
        """Challenge another wizard to a duel"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return
        
        wizard = self.wizards[user_id]
        
        # Create duel selection view
        embed = discord.Embed(
            title="⚔️ Select Duel Mode",
            description=f"**{wizard['name']}** is ready for combat!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📊 Your Stats",
            value=f"❤️ HP: {wizard['hp']}/{wizard['max_hp']}\n🔮 Mana: {wizard['mana']}/{wizard['max_mana']}\n⭐ Level: {wizard['level']}",
            inline=True
        )
        embed.add_field(
            name="🏆 Record",
            value=f"✅ Wins: {wizard['wins']}\n❌ Losses: {wizard['losses']}",
            inline=True
        )
        embed.add_field(
            name="⚔️ Duel Modes",
            value="🤖 **AI Duel** - Fight a computer opponent\n👤 **PvP Duel** - Challenge another wizard (coming soon)",
            inline=False
        )
        
        # Create button
        view = discord.ui.View(timeout=60)
        
        async def ai_duel_callback(button_interaction: discord.Interaction):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ This isn't your duel!", ephemeral=True)
                return
            
            await button_interaction.response.defer()
            await self.start_ai_duel(button_interaction, wizard, user_id)
        
        ai_button = discord.ui.Button(label="🤖 Fight AI", style=discord.ButtonStyle.primary)
        ai_button.callback = ai_duel_callback
        view.add_item(ai_button)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def start_ai_duel(self, interaction: discord.Interaction, wizard: dict, user_id: str):
        """Start an AI duel"""
        # Create AI opponent
        ai_level = max(1, wizard['level'] - 1 + random.randint(-1, 2))
        ai_wizard = {
            'name': random.choice(['Malakar', 'Zephyra', 'Ignatius', 'Frostbane', 'Shadowmere', 'Lumina']),
            'level': ai_level,
            'hp': 100 + (ai_level * 10),
            'max_hp': 100 + (ai_level * 10),
            'mana': 100 + (ai_level * 10),
            'max_mana': 100 + (ai_level * 10),
            'spells': random.sample(list(self.spells.keys()), min(5, len(self.spells)))
        }
        
        # Reset player mana/hp
        wizard['hp'] = wizard['max_hp']
        wizard['mana'] = wizard['max_mana']
        
        # Combat loop
        turn = 0
        combat_log = []
        
        while wizard['hp'] > 0 and ai_wizard['hp'] > 0 and turn < 20:
            turn += 1
            
            # Player turn
            if wizard['equipped_spells']:
                spell_name = random.choice(wizard['equipped_spells'])
                spell = self.spells.get(spell_name, {})
                mana_cost = spell.get('mana', 0)
                
                if wizard['mana'] >= mana_cost:
                    wizard['mana'] -= mana_cost
                    damage = self.calculate_damage(spell_name, wizard)
                    ai_wizard['hp'] -= damage
                    combat_log.append(f"⚔️ **Turn {turn}** - You cast **{spell_name}**! Dealt {damage} damage.")
                else:
                    # Regenerate mana
                    wizard['mana'] = min(wizard['max_mana'], wizard['mana'] + 20)
                    combat_log.append(f"🔮 **Turn {turn}** - You meditate and restore 20 mana.")
            
            if ai_wizard['hp'] <= 0:
                break
            
            # AI turn
            if ai_wizard['spells']:
                ai_spell_name = random.choice(ai_wizard['spells'])
                ai_spell = self.spells.get(ai_spell_name, {})
                ai_mana_cost = ai_spell.get('mana', 0)
                
                if ai_wizard['mana'] >= ai_mana_cost:
                    ai_wizard['mana'] -= ai_mana_cost
                    ai_damage = self.calculate_damage(ai_spell_name, ai_wizard)
                    wizard['hp'] -= ai_damage
                    combat_log.append(f"🔴 **{ai_wizard['name']}** casts **{ai_spell_name}**! You take {ai_damage} damage.")
                else:
                    ai_wizard['mana'] = min(ai_wizard['max_mana'], ai_wizard['mana'] + 20)
                    combat_log.append(f"🔮 **{ai_wizard['name']}** meditates and restores 20 mana.")
        
        # Determine winner
        if wizard['hp'] > 0:
            # Player wins
            xp_reward = 50 + (ai_level * 10)
            gold_reward = 100 + (ai_level * 50)
            wizard['xp'] += xp_reward
            wizard['gold'] += gold_reward
            wizard['wins'] += 1
            
            # Level up check
            level_up = False
            while wizard['xp'] >= wizard['level'] * 100:
                wizard['xp'] -= wizard['level'] * 100
                wizard['level'] += 1
                wizard['max_hp'] += 20
                wizard['max_mana'] += 20
                wizard['hp'] = wizard['max_hp']
                wizard['mana'] = wizard['max_mana']
                level_up = True
            
            self.save_data()
            
            embed = discord.Embed(
                title="🎉 VICTORY!",
                description=f"You defeated **{ai_wizard['name']}** (Level {ai_level})!",
                color=discord.Color.green()
            )
            embed.add_field(name="🏆 Rewards", value=f"⭐ {xp_reward} XP\n💰 {gold_reward} Gold", inline=True)
            embed.add_field(name="❤️ Remaining HP", value=f"{wizard['hp']}/{wizard['max_hp']}", inline=True)
            
            if level_up:
                embed.add_field(
                    name="⬆️ LEVEL UP!",
                    value=f"You are now **Level {wizard['level']}**!\n+20 Max HP, +20 Max Mana",
                    inline=False
                )
            
            # Show combat log (last 5 turns)
            embed.add_field(
                name="📜 Combat Log",
                value="\n".join(combat_log[-5:]),
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            # Chance to award a mythic TCG card for high-tier game (WizardWars)
            if tcg_manager:
                try:
                    awarded = tcg_manager.award_for_game_event(str(interaction.user.id), 'mythic')
                    if awarded:
                        names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
                        await interaction.followup.send(f"🎴 Bonus TCG reward: {', '.join(names)}")
                except Exception:
                    pass
        else:
            # Player loses
            wizard['losses'] += 1
            self.save_data()
            
            embed = discord.Embed(
                title="💀 DEFEAT",
                description=f"You were defeated by **{ai_wizard['name']}** (Level {ai_level}).",
                color=discord.Color.red()
            )
            embed.add_field(name="💔 HP", value="0", inline=True)
            embed.add_field(name="🏆 Record", value=f"{wizard['wins']}W - {wizard['losses']}L", inline=True)
            embed.add_field(
                name="📜 Combat Log",
                value="\n".join(combat_log[-5:]),
                inline=False
            )
            embed.set_footer(text="Train harder and try again!")
            
            await interaction.followup.send(embed=embed)
    
    async def guild_action(self, interaction: discord.Interaction):
        """Guild management"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return
        
        wizard = self.wizards[user_id]
        
        embed = discord.Embed(
            title="🏰 Wizard Guilds",
            description="Form powerful alliances and conquer territories!",
            color=discord.Color.purple()
        )
        
        if wizard['guild']:
            embed.add_field(name="Your Guild", value=wizard['guild'], inline=False)
        else:
            embed.add_field(name="Status", value="Not in a guild", inline=False)
        
        embed.add_field(
            name="🛡️ Guild Features",
            value="• Create or join guilds\n• Declare wars\n• Capture territories\n• Raid enemy vaults\n• Share resources\n• Guild-exclusive spells",
            inline=False
        )
        embed.add_field(
            name="🔧 Coming Soon",
            value="Full guild system with wars, raids, and territory control!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def territories_action(self, interaction: discord.Interaction):
        """View territory control map"""
        embed = discord.Embed(
            title="🗺️ Wizard World - Territory Map",
            description="12 territories await conquest!",
            color=discord.Color.green()
        )
        
        for i, territory in enumerate(self.territories, 1):
            controller = self.territory_control.get(territory, "Unclaimed")
            embed.add_field(
                name=f"{i}. {territory}",
                value=f"Controlled by: **{controller}**",
                inline=True
            )
        
        embed.add_field(
            name="⚔️ Territory Wars",
            value="Guilds can capture territories for bonuses and resources!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def events_action(self, interaction: discord.Interaction):
        """View active world events"""
        embed = discord.Embed(
            title="🌍 World Events",
            description="Global challenges with legendary rewards!",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="⚫ Void Storms",
            value="Random portal invasions\nReward: Forbidden Spells",
            inline=True
        )
        embed.add_field(
            name="👹 Titan Invasions",
            value="Massive boss battles\nReward: Legendary Spells",
            inline=True
        )
        embed.add_field(
            name="🌑 Eclipse Rifts",
            value="Time-limited dungeons\nReward: Cosmic Spells",
            inline=True
        )
        embed.add_field(
            name="🎭 Lore Bosses",
            value="Story encounters\nReward: Spell Evolution",
            inline=True
        )
        embed.add_field(
            name="📅 Event Schedule",
            value="No active events right now.\nCheck back soon!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def leaderboard_action(self, interaction: discord.Interaction):
        """View global leaderboards"""
        embed = discord.Embed(
            title="🏆 Wizard Wars Leaderboards",
            description="The most powerful wizards in the realm!",
            color=discord.Color.gold()
        )
        
        # Sort wizards by level
        sorted_wizards = sorted(
            [(uid, w) for uid, w in self.wizards.items()],
            key=lambda x: (x[1]['level'], x[1]['wins']),
            reverse=True
        )[:10]
        
        if sorted_wizards:
            leaderboard_text = ""
            for i, (uid, wizard) in enumerate(sorted_wizards, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{wizard['name']}** - Lvl {wizard['level']} ({wizard['wins']} wins)\n"
            
            embed.add_field(name="⚔️ Top Wizards", value=leaderboard_text, inline=False)
        else:
            embed.add_field(name="⚔️ Top Wizards", value="No wizards yet!", inline=False)
        
        embed.add_field(
            name="📊 Categories",
            value="⚔️ Duelists | 🔮 Spell Power | 🏰 Guilds | 🗺️ Territories | 👑 Champions",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def shop_action(self, interaction: discord.Interaction):
        """Spell shop"""
        user_id = str(interaction.user.id)

        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return

        wizard = self.wizards[user_id]
        available_spells = [s for s in self.spells.keys() if s not in wizard['spells']]

        embed = discord.Embed(
            title="💰 Spell Shop",
            description=f"Your Gold: **{wizard['gold']}**\nSelect a spell from the dropdown to preview it, then click **💰 Buy Spell** to purchase.",
            color=discord.Color.gold(),
        )

        # Group by school
        by_school: dict = {}
        for spell_name in available_spells:
            spell = self.spells[spell_name]
            by_school.setdefault(spell['school'], []).append((spell_name, spell))

        for school, spells in by_school.items():
            se = SCHOOL_EMOJIS.get(school, "🔮")
            lines = [f"{TYPE_EMOJIS.get(sp['type'], '✨')} **{sn}** — {sp['power'] * 100} Gold" for sn, sp in spells]
            embed.add_field(name=f"{se} {school}", value="\n".join(lines), inline=True)

        if not available_spells:
            embed.add_field(name="🎉 Collection Complete!", value="You own all available spells!", inline=False)

        view = ShopView(self, user_id, available_spells) if available_spells else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def profile_action(self, interaction: discord.Interaction):
        """View wizard profile"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.wizards:
            await interaction.response.send_message(
                "🧙 You need to create a wizard first! Use `/ww create`",
                ephemeral=True
            )
            return
        
        wizard = self.wizards[user_id]
        
        embed = discord.Embed(
            title=f"🧙 {wizard['name']}'s Profile",
            description=f"**{wizard['rank']}** | Level {wizard['level']}",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📊 Stats",
            value=f"❤️ HP: {wizard['hp']}/{wizard['max_hp']}\n🔮 Mana: {wizard['mana']}/{wizard['max_mana']}\n⭐ XP: {wizard['xp']}/{wizard['level'] * 100}",
            inline=True
        )
        embed.add_field(
            name="💰 Resources",
            value=f"💰 Gold: {wizard['gold']}\n📚 Spells: {len(wizard['spells'])}/50\n🗡️ Equipped: {len(wizard['equipped_spells'])}/{wizard['spell_slots']}",
            inline=True
        )
        embed.add_field(
            name="🏆 Combat Record",
            value=f"✅ Wins: {wizard['wins']}\n❌ Losses: {wizard['losses']}\n🎯 Win Rate: {wizard['wins']/(wizard['wins']+wizard['losses'])*100:.1f}%" if wizard['wins']+wizard['losses'] > 0 else "No battles yet",
            inline=True
        )
        
        if wizard['guild']:
            embed.add_field(name="🏰 Guild", value=wizard['guild'], inline=True)
        
        if wizard['title']:
            embed.add_field(name="🎭 Title", value=wizard['title'], inline=True)
        
        embed.set_footer(text="Use /ww to explore more features!")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(WizardWars(bot))
