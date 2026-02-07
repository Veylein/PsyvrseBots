import discord
from discord.ext import commands
import json
import os
import sys
from typing import Optional, Literal
import random
import asyncio
from datetime import datetime

# ==================== CUSTOM ROLE MANAGER ====================

CUSTOM_ROLES_FILE = "data/custom_roles.json"

def load_custom_roles():
    """Load custom roles from JSON file"""
    if os.path.exists(CUSTOM_ROLES_FILE):
        with open(CUSTOM_ROLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("roles", [])
    return []

def save_custom_roles(roles):
    """Save custom roles to JSON file"""
    os.makedirs("data", exist_ok=True)
    with open(CUSTOM_ROLES_FILE, 'w', encoding='utf-8') as f:
        json.dump({"roles": roles}, f, indent=2, ensure_ascii=False)

def apply_custom_roles_to_database(bot):
    """Apply all custom roles to ROLES_DATABASE"""
    import sys
    mafia_module = sys.modules.get('cogs.mafia')
    if not mafia_module:
        return False
    
    ROLES_DATABASE = mafia_module.ROLES_DATABASE
    custom_roles = load_custom_roles()
    
    for role in custom_roles:
        role_id = role["role_id"]
        faction = role["faction"]
        theme = role.get("theme", "MAFIA")  # Default to MAFIA theme if not specified
        
        role_data = {
            "name_en": role["name_en"],
            "name_pl": role["name_pl"],
            "emoji": role["emoji"],
            "power": role.get("power"),
            "desc_en": role.get("desc_en", "Custom role"),
            "desc_pl": role.get("desc_pl", "Niestandardowa rola"),
            "custom": True,
            "creator": role.get("creator", 0)
        }
        
        # Add to appropriate database based on theme
        if theme == "MAFIA":
            # Add to mafia_advanced
            if faction in ["TOWN"]:
                ROLES_DATABASE["mafia_advanced"]["TOWN"][role_id] = role_data.copy()
            elif faction == "MAFIA":
                ROLES_DATABASE["mafia_advanced"]["MAFIA"][role_id] = role_data.copy()
            elif faction == "NEUTRAL":
                ROLES_DATABASE["mafia_advanced"]["NEUTRAL"][role_id] = role_data.copy()
            elif faction == "CHAOS":
                ROLES_DATABASE["mafia_advanced"]["CHAOS"][role_id] = role_data.copy()
        elif theme == "WEREWOLF":
            # Add to werewolf_advanced
            if faction in ["VILLAGE", "TOWN"]:
                ROLES_DATABASE["werewolf_advanced"]["VILLAGE"][role_id] = role_data.copy()
            elif faction == "WEREWOLVES":
                ROLES_DATABASE["werewolf_advanced"]["WEREWOLVES"][role_id] = role_data.copy()
            elif faction == "NEUTRAL":
                ROLES_DATABASE["werewolf_advanced"]["NEUTRAL"][role_id] = role_data.copy()
            elif faction == "CHAOS":
                ROLES_DATABASE["werewolf_advanced"]["CHAOS"][role_id] = role_data.copy()
    
    return True


# ==================== HELPER FUNCTION ====================
async def create_role_with_data(interaction, manager_view, name_en, name_pl, theme, faction, power, emoji=None, desc_en=None, desc_pl=None):
    """Helper function to create a custom role with given data"""
    role_id = name_en.lower().replace(" ", "_").strip()
    
    # Check if exists
    for role in manager_view.custom_roles:
        if role['role_id'] == role_id:
            await interaction.response.send_message(
                f"❌ Role `{role_id}` already exists!",
                ephemeral=True
            )
            return False
    
    # Default emoji based on faction
    faction_emojis = {
        "TOWN": "👤",
        "MAFIA": "🔫",
        "WEREWOLVES": "🐺",
        "VILLAGE": "🏘️",
        "NEUTRAL": "⚖️",
        "CHAOS": "🌀"
    }
    if not emoji:
        emoji = faction_emojis.get(faction, "❓")
    
    if not desc_en:
        desc_en = f"Custom {faction.lower()} role"
    if not desc_pl:
        desc_pl = f"Niestandardowa rola {faction.lower()}"
    
    # Create role
    new_role = {
        "role_id": role_id,
        "name_en": name_en,
        "name_pl": name_pl,
        "theme": theme,
        "faction": faction,
        "power": power,
        "emoji": emoji,
        "desc_en": desc_en,
        "desc_pl": desc_pl,
        "creator": interaction.user.id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Save
    manager_view.custom_roles.append(new_role)
    save_custom_roles(manager_view.custom_roles)
    apply_custom_roles_to_database(manager_view.bot)
    
    # Update main view
    embed = manager_view._build_embed()
    await manager_view.message.edit(embed=embed, view=manager_view)
    
    await interaction.response.send_message(
        f"✅ Created custom role: {emoji} **{name_en}** ({faction}, {theme} theme)",
        ephemeral=True
    )
    return True


# ==================== CUSTOM ROLE MANAGER VIEW ====================
class CustomRoleManagerView(discord.ui.View):
    """Manager for custom roles with create/delete UI"""
    
    def __init__(self, bot, user):
        super().__init__(timeout=300.0)
        self.bot = bot
        self.user = user
        self.message = None
        self.custom_roles = load_custom_roles()
    
    async def show(self, ctx):
        """Show the manager interface"""
        embed = self._build_embed()
        self.message = await ctx.send(embed=embed, view=self)
    
    def _build_embed(self):
        """Build the main embed"""
        embed = discord.Embed(
            title="🎭 Custom Role Manager",
            description="Create and manage custom Mafia/Werewolf roles",
            color=discord.Color.blue()
        )
        
        if self.custom_roles:
            roles_text = ""
            for i, role in enumerate(self.custom_roles[:10], 1):
                theme = role.get('theme', 'MAFIA')
                power_text = f" | {role.get('power', 'None')}" if role.get('power') else ""
                roles_text += f"{i}. {role['emoji']} **{role['name_en']}** ({role['faction']}, {theme}){power_text}\n"
            
            if len(self.custom_roles) > 10:
                roles_text += f"\n*...and {len(self.custom_roles) - 10} more*"
            
            embed.add_field(name=f"Custom Roles ({len(self.custom_roles)})", value=roles_text, inline=False)
        else:
            embed.add_field(name="Custom Roles", value="*No custom roles created yet*", inline=False)
        
        embed.set_footer(text="Use buttons below to create or delete roles")
        return embed
    
    @discord.ui.button(label="Create Role", style=discord.ButtonStyle.success, emoji="➕")
    async def create_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        modal = CreateRoleModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Delete Role", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        if not self.custom_roles:
            await interaction.response.send_message("❌ No custom roles to delete!", ephemeral=True)
            return
        
        # Create select menu with roles
        options = []
        for role in self.custom_roles[:25]:  # Discord limit
            options.append(discord.SelectOption(
                label=f"{role['name_en']} ({role['faction']})",
                value=role['role_id'],
                emoji=role['emoji'],
                description=f"Power: {role.get('power', 'None')}"
            ))
        
        select = discord.ui.Select(placeholder="Select role to delete", options=options)
        
        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != self.user.id:
                await select_interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
                return
            
            role_id = select_interaction.data['values'][0]
            self.custom_roles = [r for r in self.custom_roles if r['role_id'] != role_id]
            save_custom_roles(self.custom_roles)
            apply_custom_roles_to_database(self.bot)
            
            embed = self._build_embed()
            await select_interaction.response.edit_message(embed=embed, view=self)
            await select_interaction.followup.send(f"✅ Role `{role_id}` deleted!", ephemeral=True)
        
        select.callback = select_callback
        
        delete_view = discord.ui.View()
        delete_view.add_item(select)
        await interaction.response.send_message("Select a role to delete:", view=delete_view, ephemeral=True)
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the command user can use this!", ephemeral=True)
            return
        
        self.custom_roles = load_custom_roles()
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class CreateRoleModal(discord.ui.Modal, title="Create Custom Role - Step 1/2"):
    """Modal for creating a new custom role - Step 1: Basic Info"""
    
    name_en = discord.ui.TextInput(label="English Name", placeholder="e.g., Ninja", max_length=50, required=True)
    name_pl = discord.ui.TextInput(label="Polish Name", placeholder="e.g., Ninja", max_length=50, required=True)
    theme = discord.ui.TextInput(label="Theme", placeholder="MAFIA or WEREWOLF", max_length=20, required=True)
    faction = discord.ui.TextInput(label="Faction", placeholder="TOWN/MAFIA/WEREWOLVES/VILLAGE/NEUTRAL/CHAOS", max_length=20, required=True)
    power = discord.ui.TextInput(label="Power (optional)", placeholder="e.g., investigate, protect, stealth", max_length=50, required=False)
    
    def __init__(self, manager_view):
        super().__init__()
        self.manager_view = manager_view
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate theme
        valid_themes = ["MAFIA", "WEREWOLF"]
        theme = self.theme.value.upper().strip()
        if theme not in valid_themes:
            await interaction.response.send_message(
                f"❌ Invalid theme! Use: {', '.join(valid_themes)}",
                ephemeral=True
            )
            return
        
        # Validate faction
        valid_factions = ["TOWN", "MAFIA", "WEREWOLVES", "VILLAGE", "NEUTRAL", "CHAOS"]
        faction = self.faction.value.upper().strip()
        if faction not in valid_factions:
            await interaction.response.send_message(
                f"❌ Invalid faction! Use: {', '.join(valid_factions)}",
                ephemeral=True
            )
            return
        
        # Validate power
        valid_powers = [
            "investigate", "protect", "guard", "kill", "kill_leader", "track", "stealth",
            "reveal_dead", "lynch_win", "contract", "stats", "hints", "visits", "death_cause",
            "logs", "suspicious", "old_actions", "future", "riddles", "dreams", "random_visions",
            "info", "armor", "sacrifice", "block_curse", "remove_curse", "secure", "revenge_kill",
            "potions", "block", "control", "force", "convert", "recruit", "steal", "disguise",
            "copy", "fake_reports", "lower_sus", "fake_town", "fake_villager", "reveal",
            "cancel_vote", "delay", "connect", "double_vote", "buy_votes", "reverse_vote",
            "swap_votes", "vote_influence", "anonymous_dm", "dead_chat", "influence", "chaos",
            "random", "break_night", "grow", "50_lie", "mix_reports", "random_effects",
            "catastrophe", "unpredictable", "event", "summon", "decay", "conflicts",
            "manipulate_turns", "buff_weak", "unstoppable", "no_vote_strong", "survive",
            "survive_x", "top3", "chaos_win", "solo", "revenge"
        ]
        
        power_value = self.power.value.strip() if self.power.value else None
        if power_value and power_value not in valid_powers:
            await interaction.response.send_message(
                f"❌ Invalid power! Check L!ownerhelp for valid powers.",
                ephemeral=True
            )
            return
        
        # Create a view with button to add descriptions
        step2_view = discord.ui.View(timeout=180)
        
        # Store data temporarily
        step2_view.role_data = {
            "name_en": self.name_en.value.strip(),
            "name_pl": self.name_pl.value.strip(),
            "theme": theme,
            "faction": faction,
            "power": power_value
        }
        step2_view.manager_view = self.manager_view
        
        # Button to open second modal
        async def add_descriptions_callback(button_interaction: discord.Interaction):
            second_modal = CreateRoleModalStep2(
                step2_view.manager_view,
                step2_view.role_data["name_en"],
                step2_view.role_data["name_pl"],
                step2_view.role_data["theme"],
                step2_view.role_data["faction"],
                step2_view.role_data["power"]
            )
            await button_interaction.response.send_modal(second_modal)
        
        add_desc_button = discord.ui.Button(label="Add Descriptions & Emoji", style=discord.ButtonStyle.primary, emoji="📝")
        add_desc_button.callback = add_descriptions_callback
        step2_view.add_item(add_desc_button)
        
        # Button to skip and use defaults
        async def skip_callback(button_interaction: discord.Interaction):
            # Create role with defaults
            await create_role_with_data(
                button_interaction,
                step2_view.manager_view,
                step2_view.role_data["name_en"],
                step2_view.role_data["name_pl"],
                step2_view.role_data["theme"],
                step2_view.role_data["faction"],
                step2_view.role_data["power"]
            )
        
        skip_button = discord.ui.Button(label="Skip (Use Defaults)", style=discord.ButtonStyle.secondary, emoji="⏭️")
        skip_button.callback = skip_callback
        step2_view.add_item(skip_button)
        
        await interaction.response.send_message(
            "✅ Basic info saved! Choose an option:",
            view=step2_view,
            ephemeral=True
        )


class CreateRoleModalStep2(discord.ui.Modal, title="Create Custom Role - Step 2/2"):
    
    emoji = discord.ui.TextInput(label="Emoji (optional)", placeholder="e.g., 🥷", max_length=10, required=False)
    desc_en = discord.ui.TextInput(
        label="English Description", 
        placeholder="Describe the role in English", 
        style=discord.TextStyle.paragraph,
        max_length=200, 
        required=False
    )
    desc_pl = discord.ui.TextInput(
        label="Polish Description", 
        placeholder="Opisz rolę po polsku", 
        style=discord.TextStyle.paragraph,
        max_length=200, 
        required=False
    )
    
    def __init__(self, manager_view, name_en, name_pl, theme, faction, power):
        super().__init__()
        self.manager_view = manager_view
        self.name_en = name_en
        self.name_pl = name_pl
        self.theme = theme
        self.faction = faction
        self.power = power
    
    async def on_submit(self, interaction: discord.Interaction):
        # Get custom values
        emoji = self.emoji.value.strip() if self.emoji.value else None
        desc_en = self.desc_en.value.strip() if self.desc_en.value else None
        desc_pl = self.desc_pl.value.strip() if self.desc_pl.value else None
        
        # Create role with custom descriptions
        await create_role_with_data(
            interaction,
            self.manager_view,
            self.name_en,
            self.name_pl,
            self.theme,
            self.faction,
            self.power,
            emoji,
            desc_en,
            desc_pl
        )


class Owner(commands.Cog):
    """Secret owner-only commands for bot management and fun"""
    
    def __init__(self, bot):
        self.bot = bot
        self.owner_ids = bot.owner_ids
        
        print(f"[OWNER COG] Initialized with owner_ids: {self.owner_ids}")
        
        # Load custom roles to mafia database
        try:
            if apply_custom_roles_to_database(bot):
                print("[OWNER COG] ✅ Custom roles loaded successfully")
        except Exception as e:
            print(f"[OWNER COG] ⚠️ Could not load custom roles yet: {e}")
        
        # Funny responses for secret commands
        self.god_mode_responses = [
            "🌟 You feel the power of the gods flowing through you...",
            "⚡ Reality bends to your will...",
            "👑 All shall bow before your might!",
            "🔮 The cosmos aligns in your favor...",
            "💫 Transcendence achieved!"
        ]
        
        self.chaos_responses = [
            "🌪️ CHAOS UNLEASHED!",
            "💥 The universe trembles!",
            "🎭 Reality is what you make it!",
            "🎪 Let the games begin!",
            "🎲 Rolling the cosmic dice..."
        ]

    async def cog_check(self, ctx):
        """Global check - only allow owners"""
        user_id = None
        if hasattr(ctx, 'author'):
            user_id = ctx.author.id
        elif hasattr(ctx, 'user'):
            user_id = ctx.user.id
        
        is_owner = user_id in self.owner_ids
        print(f"[OWNER COG] cog_check: user_id={user_id}, owner_ids={self.owner_ids}, is_owner={is_owner}")
        
        return is_owner
    
    # ==================== TEST COMMAND ====================
    
    @commands.command(name="ownertest")
    async def ownertest(self, ctx):
        """Test if owner commands are working"""
        print(f"[OWNER COG] ownertest called by {ctx.author.id}")
        await ctx.send(f"✅ Owner commands are working!\n**Your ID:** {ctx.author.id}\n**Owner IDs:** {self.owner_ids}")
    
    @commands.command(name="fishing_tournament")
    async def fishing_tournament_owner(self, ctx, mode: str = "biggest", duration: int = 5):
        """Owner-only: Start a fishing tournament
        
        Usage: L!fishing_tournament <mode> <duration>
        Modes: biggest, most, rarest
        Duration: 1-30 minutes
        """
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        mode = mode.lower()
        if mode not in ["biggest", "most", "rarest"]:
            return await ctx.send("❌ Invalid mode! Use: biggest, most, or rarest")
        
        if duration < 1 or duration > 30:
            return await ctx.send("❌ Duration must be between 1-30 minutes!")
        
        # Check if tournament already running
        guild_id = str(ctx.guild.id)
        if guild_id in getattr(fishing_cog, 'active_tournaments', {}):
            return await ctx.send("❌ A tournament is already running in this server!")
        
        # Get configured tournament channel
        guild_config = fishing_cog.get_guild_config(ctx.guild.id)
        tournament_channel_id = guild_config.get("tournament_channel")
        
        if not tournament_channel_id:
            return await ctx.send("❌ No tournament channel configured! Admin must set it first using `L!fishtournament_channel #channel`")
        
        tournament_channel = self.bot.get_channel(tournament_channel_id)
        if not tournament_channel:
            return await ctx.send("❌ Tournament channel not found! Ask admin to reconfigure it.")
        
        # Start tournament via fishing cog
        await fishing_cog.start_random_tournament(ctx.guild.id, tournament_channel_id, mode=mode, duration=duration)
        
        mode_names = {
            "biggest": "🏆 Biggest Fish",
            "most": "📊 Most Fish",
            "rarest": "✨ Rarest Fish"
        }
        await ctx.send(f"✅ Tournament started in {tournament_channel.mention}!\n"
                      f"**Mode:** {mode_names.get(mode, mode)}\n"
                      f"**Duration:** {duration} minutes")

    @commands.command(name="give_fish")
    async def give_fish(self, ctx, member: discord.Member, fish_id: str, quantity: int = 1):
        """Owner-only: Give a fish to someone
        
        Usage: L!give_fish @user <fish_id> [quantity]
        Example: L!give_fish @user salmon 5
        """
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED give_fish attempt by {ctx.author.id}")
            return
        
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        # Check if fish exists
        if fish_id not in fishing_cog.fish_types:
            available_fish = list(fishing_cog.fish_types.keys())[:20]  # Show first 20
            return await ctx.send(f"❌ Invalid fish ID! Examples: {', '.join(available_fish[:10])}...\nUse `/fish encyclopedia` to see all fish!")
        
        # Get user data
        user_data = fishing_cog.get_user_data(member.id)
        
        # Add fish to user's catches (new dict format)
        if fish_id not in user_data["fish_caught"]:
            user_data["fish_caught"][fish_id] = {"count": 0, "biggest": 0}
        
        # Ensure dict format (fix old data)
        if not isinstance(user_data["fish_caught"][fish_id], dict):
            user_data["fish_caught"][fish_id] = {"count": int(user_data["fish_caught"][fish_id]), "biggest": 0}
        
        user_data["fish_caught"][fish_id]["count"] += quantity
        user_data["total_catches"] += quantity
        
        # Update total value
        fish_info = fishing_cog.fish_types[fish_id]
        user_data["total_value"] += fish_info["value"] * quantity
        
        fishing_cog.save_fishing_data()
        
        fish_name = fish_info["name"]
        await ctx.send(f"🎣 Gave **{quantity}x {fish_name}** to {member.mention}!")

    @commands.command(name="give_bait")
    async def give_bait(self, ctx, member: discord.Member, bait_id: str, quantity: int = 1):
        """Owner-only: Give fishing bait to someone
        
        Usage: L!give_bait @user <bait_id> [quantity]
        Bait types: worm, cricket, minnow, shrimp, squid, special, kraken_bait
        Example: L!give_bait @user kraken_bait 1
        """
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED give_bait attempt by {ctx.author.id}")
            return
        
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        # Check if bait exists
        if bait_id not in fishing_cog.baits:
            available_baits = ', '.join(fishing_cog.baits.keys())
            return await ctx.send(f"❌ Invalid bait ID! Available: {available_baits}")
        
        # Get user data
        user_data = fishing_cog.get_user_data(member.id)
        
        # Add bait to inventory
        if bait_id not in user_data["bait_inventory"]:
            user_data["bait_inventory"][bait_id] = 0
        user_data["bait_inventory"][bait_id] += quantity
        
        fishing_cog.save_fishing_data()
        
        bait_name = fishing_cog.baits[bait_id]["name"]
        
        # Special message for kraken bait
        if bait_id == "kraken_bait":
            await ctx.send(f"🦑 Gave **{quantity}x {bait_name}** to {member.mention}!\n"
                          f"⚠️ **Warning:** This summons the Kraken in Mariana Trench!")
        else:
            await ctx.send(f"🪱 Gave **{quantity}x {bait_name}** to {member.mention}!")

    @commands.command(name="give_rod")
    async def give_rod(self, ctx, member: discord.Member, rod_id: str):
        """Owner-only: Give a fishing rod to someone
        
        Usage: L!give_rod @user <rod_id>
        Rod types: basic_rod, carbon_rod, pro_rod, master_rod, legendary_rod
        Example: L!give_rod @user legendary_rod
        """
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED give_rod attempt by {ctx.author.id}")
            return
        
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        # Check if rod exists
        if rod_id not in fishing_cog.rods:
            available_rods = ', '.join(fishing_cog.rods.keys())
            return await ctx.send(f"❌ Invalid rod ID! Available: {available_rods}")
        
        # Get user data
        user_data = fishing_cog.get_user_data(member.id)
        
        # Set user's rod
        user_data["rod"] = rod_id
        
        fishing_cog.save_fishing_data()
        
        rod_name = fishing_cog.rods[rod_id]["name"]
        await ctx.send(f"🎣 Gave {rod_name} to {member.mention}!")

    @commands.command(name="give_boat")
    async def give_boat(self, ctx, member: discord.Member, boat_id: str):
        """Owner-only: Give a fishing boat to someone
        
        Usage: L!give_boat @user <boat_id>
        Boat types: none, kayak, motorboat, yacht, submarine
        Example: L!give_boat @user submarine
        """
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED give_boat attempt by {ctx.author.id}")
            return
        
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        # Check if boat exists
        if boat_id not in fishing_cog.boats:
            available_boats = ', '.join(fishing_cog.boats.keys())
            return await ctx.send(f"❌ Invalid boat ID! Available: {available_boats}")
        
        # Get user data
        user_data = fishing_cog.get_user_data(member.id)
        
        # Set user's boat
        user_data["boat"] = boat_id
        
        fishing_cog.save_fishing_data()
        
        if boat_id == "none":
            await ctx.send(f"🚫 Removed boat from {member.mention}")
        else:
            boat_name = fishing_cog.boats[boat_id]["name"]
            await ctx.send(f"⛵ Gave {boat_name} to {member.mention}!")

    @commands.command(name="unlock_area")
    async def unlock_fishing_area(self, ctx, member: discord.Member, area_id: str):
        """Owner-only: Unlock a fishing area for someone
        
        Usage: L!unlock_area @user <area_id>
        Areas: pond, river, lake, ocean, reef, abyss, trench
        Example: L!unlock_area @user trench
        """
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED unlock_area attempt by {ctx.author.id}")
            return
        
        fishing_cog = self.bot.get_cog("Fishing")
        if not fishing_cog:
            return await ctx.send("❌ Fishing cog not loaded!")
        
        # Check if area exists
        if area_id not in fishing_cog.areas:
            available_areas = ', '.join(fishing_cog.areas.keys())
            return await ctx.send(f"❌ Invalid area ID! Available: {available_areas}")
        
        # Get user data
        user_data = fishing_cog.get_user_data(member.id)
        
        # Unlock area
        if area_id not in user_data["unlocked_areas"]:
            user_data["unlocked_areas"].append(area_id)
            fishing_cog.save_fishing_data()
            
            area_name = fishing_cog.areas[area_id]["name"]
            await ctx.send(f"🗺️ Unlocked {area_name} for {member.mention}!")
        else:
            area_name = fishing_cog.areas[area_id]["name"]
            await ctx.send(f"ℹ️ {member.mention} already has {area_name} unlocked!")
    
    @commands.command(name="serverlist")
    async def serverlist(self, ctx):
        """Owner-only: List Discord servers the bot is in"""
        if getattr(ctx, 'author', None) and ctx.author.id not in self.owner_ids:
            return await ctx.send("❌ You must be a bot owner to use this command!")
        guilds_info = []
        for g in self.bot.guilds:
            try:
                member_count = g.member_count
            except Exception:
                member_count = "?"

            invite_url = None
            try:
                invites = await g.invites()
                if invites:
                    invites_sorted = sorted(invites, key=lambda i: (i.max_age or 0, i.uses or 0))
                    invite_url = getattr(invites_sorted[0], 'url', str(invites_sorted[0]))
            except Exception:
                invite_url = None

            guilds_info.append({
                "name": g.name,
                "id": g.id,
                "members": member_count,
                "invite": invite_url,
            })

        if not guilds_info:
            return await ctx.send("No guilds found.")

        per_page = 20
        pages = [guilds_info[i:i+per_page] for i in range(0, len(guilds_info), per_page)]
        total = len(pages)
        for idx, page in enumerate(pages, start=1):
            embed = discord.Embed(title=f"Server list — page {idx}/{total}", color=discord.Color.blurple())
            for gi in page:
                name = gi.get("name") or "(unknown)"
                if len(name) > 250:
                    name = name[:247] + "..."
                invite = gi.get("invite") or "N/A"
                embed.add_field(
                    name=name,
                    value=f"ID: {gi.get('id')}\nMembers: {gi.get('members')}\nInvite: {invite}",
                    inline=False,
                )
            await ctx.send(embed=embed)

    @commands.command(name="restart")
    async def restart(self, ctx, *, reason: Optional[str] = None):
        """Owner-only: Restart the bot process.

        Usage: L!restart [reason]
        """
        if getattr(ctx, 'author', None) and ctx.author.id not in self.owner_ids:
            return await ctx.send("❌ You must be a bot owner to use this command!")

        try:
            await ctx.send("🔁 Restarting bot now...")
        except Exception:
            pass

        # Attempt graceful shutdown then re-exec the process
        try:
            await self.bot.close()
        except Exception:
            pass

        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            # If execv fails, force exit and rely on process manager
            try:
                print(f"[OWNER COG] Restart exec failed: {e}")
            except Exception:
                pass
            os._exit(0)

    @commands.command(name="leave")
    async def leave(self, ctx, guild_id: Optional[int] = None):
        """Owner-only: Make the bot leave a guild.

        Usage: L!leave [guild_id]
        If no guild_id is provided, leaves the current guild.
        """
        if getattr(ctx, 'author', None) and ctx.author.id not in self.owner_ids:
            return await ctx.send("❌ You must be a bot owner to use this command!")

        target_guild = None
        if guild_id:
            target_guild = self.bot.get_guild(int(guild_id))
        else:
            target_guild = ctx.guild

        if not target_guild:
            return await ctx.send("❌ Guild not found.")

        try:
            await target_guild.leave()
            await ctx.send(f"✅ Left guild: {target_guild.name} ({target_guild.id})")
        except Exception as e:
            await ctx.send(f"❌ Failed to leave guild: {e}")
    
    # ==================== ECONOMY MANAGEMENT ====================

    @commands.command(name="godmode")
    async def godmode(self, ctx):
        """Secret god mode - max out your stats"""
        print(f"[OWNER COG] godmode command called by {ctx.author.id}")
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED godmode attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Max out owner's economy
        economy_cog.economy_data[str(ctx.author.id)] = {
            "balance": 999999999,
            "total_earned": 999999999,
            "total_spent": 999999999,
            "last_daily": None,
            "daily_streak": 999,
            "active_boosts": {}
        }
        economy_cog.save_economy()
        
        # Give all items
        for item_id in economy_cog.shop_items.keys():
            economy_cog.add_item(ctx.author.id, item_id, 99)
        
        await ctx.send(random.choice(self.god_mode_responses))
        embed = discord.Embed(
            title="👑 GOD MODE ACTIVATED",
            description=f"**Balance:** 999,999,999 PsyCoins\n**Streak:** 999 days\n**Items:** ALL (x99)",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @commands.command(name="setcoins")
    async def setcoins(self, ctx, member: discord.Member, amount: int):
        """Set someone's PsyCoin balance"""
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED setcoins attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        user_key = str(member.id)
        economy_cog.get_balance(member.id)  # Ensure user exists
        economy_cog.economy_data[user_key]["balance"] = amount
        economy_cog.save_economy()
        
        await ctx.send(f"💰 Set {member.mention}'s balance to **{amount:,} PsyCoins**")

    @commands.command(name="addcoins")
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        """Add PsyCoins to someone's balance"""
        
        # CRITICAL: Check if user is bot owner (cog_check handles this, but double-check)
        if ctx.author.id not in self.owner_ids:
            await ctx.send("❌ You must be a bot owner to use this command!")
            print(f"[OWNER COG] UNAUTHORIZED addcoins attempt by {ctx.author.id}")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        economy_cog.add_coins(member.id, amount, "owner_grant")
        new_balance = economy_cog.get_balance(member.id)
        
        await ctx.send(f"💸 Added **{amount:,} PsyCoins** to {member.mention}\nNew balance: **{new_balance:,}**")

    @commands.command(name="removecoins")
    async def removecoins(self, ctx, member: discord.Member, amount: int):
        """Remove PsyCoins from someone's balance"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        success = economy_cog.remove_coins(member.id, amount)
        new_balance = economy_cog.get_balance(member.id)
        
        if success:
            await ctx.send(f"💸 Removed **{amount:,} PsyCoins** from {member.mention}\nNew balance: **{new_balance:,}**")
        else:
            await ctx.send(f"❌ {member.mention} doesn't have enough coins! Current balance: **{new_balance:,}**")

    @commands.command(name="resetcoins")
    async def resetcoins(self, ctx, member: discord.Member):
        """Reset someone's economy data"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        user_key = str(member.id)
        if user_key in economy_cog.economy_data:
            del economy_cog.economy_data[user_key]
            economy_cog.save_economy()
        
        await ctx.send(f"🔄 Reset {member.mention}'s economy data to defaults")

    @commands.command(name="giveitem")
    async def giveitem(self, ctx, member: discord.Member, item_id: str, quantity: int = 1):
        """Give an item to someone"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        if item_id not in economy_cog.shop_items:
            await ctx.send(f"❌ Invalid item ID! Available items: {', '.join(economy_cog.shop_items.keys())}")
            return
        
        economy_cog.add_item(member.id, item_id, quantity)
        item_name = economy_cog.shop_items[item_id]["name"]
        
        await ctx.send(f"🎁 Gave **{quantity}x {item_name}** to {member.mention}")

    @commands.command(name="give_tc")
    async def give_tc(self, ctx, member: discord.Member, *, card_query: str):
        """Owner-only: give a TCG card by name or id to a member."""
        # Try legacy TCG cog first, then fallback to psyvrse_tcg inventory
        tcg = self.bot.get_cog('TCG')
        if tcg:
            try:
                cid = tcg._find_card_by_name_or_id(card_query)
                if not cid:
                    return await ctx.send('Card not found.')
                tcg.manager.award_card(str(member.id), cid, 1)
                return await ctx.send(f'Gave 1x {cid} to {member.mention}')
            except Exception:
                pass

        # Fallback: psyvrse_tcg
        try:
            from cogs import psyvrse_tcg
            # simple resolver: exact crafted id, numeric seed, or search crafted by name
            q = card_query.strip()
            # crafted id
            if q.upper().startswith('C') and psyvrse_tcg.inventory.get_crafted(q):
                cid = q
            else:
                # numeric id
                try:
                    n = int(q)
                    if 0 <= n < psyvrse_tcg.TOTAL_CARD_POOL:
                        cid = str(n)
                    else:
                        cid = None
                except Exception:
                    cid = None
                # search crafted names if not numeric
                if not cid:
                    for k,v in psyvrse_tcg.inventory.crafted.items():
                        if q.lower() in (v.get('name','').lower()):
                            cid = k
                            break
            if not cid:
                return await ctx.send('Card not found.')
            psyvrse_tcg.inventory.add_card(member.id, cid)
            return await ctx.send(f'Gave 1x {cid} to {member.mention}')
        except Exception:
            return await ctx.send('TCG cog not loaded.')

    @commands.command(name="remove_tc")
    async def remove_tc(self, ctx, member: discord.Member, *, card_query: str):
        """Owner-only: remove a TCG card by name or id from a member."""
        # Try legacy TCG cog first, then fallback to psyvrse_tcg inventory
        tcg = self.bot.get_cog('TCG')
        if tcg:
            try:
                cid = tcg._find_card_by_name_or_id(card_query)
                if not cid:
                    return await ctx.send('Card not found.')
                ok = tcg.manager.remove_card(str(member.id), cid, 1)
                if not ok:
                    return await ctx.send('Member does not have that card.')
                return await ctx.send(f'Removed 1x {cid} from {member.mention}')
            except Exception:
                pass

        # Fallback: psyvrse_tcg
        try:
            from cogs import psyvrse_tcg
            q = card_query.strip()
            if q.upper().startswith('C') and psyvrse_tcg.inventory.get_crafted(q):
                cid = q
            else:
                try:
                    n = int(q)
                    if 0 <= n < psyvrse_tcg.TOTAL_CARD_POOL:
                        cid = str(n)
                    else:
                        cid = None
                except Exception:
                    cid = None
                if not cid:
                    for k,v in psyvrse_tcg.inventory.crafted.items():
                        if q.lower() in (v.get('name','').lower()):
                            cid = k
                            break
            if not cid:
                return await ctx.send('Card not found.')
            ok = psyvrse_tcg.inventory.remove_card(member.id, cid)
            if not ok:
                return await ctx.send('Member does not have that card.')
            return await ctx.send(f'Removed 1x {cid} from {member.mention}')
        except Exception:
            return await ctx.send('TCG cog not loaded.')

    # ==================== BOT STATUS & PRESENCE ====================

    @commands.command(name="status")
    async def change_status(self, ctx, status_type: str, *, text: str):
        """Change bot status (playing/watching/listening/competing)"""
        status_types = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "competing": discord.ActivityType.competing
        }
        
        if status_type.lower() not in status_types:
            await ctx.send(f"❌ Invalid status type! Use: {', '.join(status_types.keys())}")
            return
        
        activity = discord.Activity(type=status_types[status_type.lower()], name=text)
        await self.bot.change_presence(activity=activity)
        
        await ctx.send(f"✅ Status changed to: **{status_type.title()}** {text}")

    @commands.command(name="presence")
    async def change_presence(self, ctx, status: str):
        """Change bot online status (online/idle/dnd/invisible)"""
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        
        if status.lower() not in status_map:
            await ctx.send(f"❌ Invalid status! Use: {', '.join(status_map.keys())}")
            return
        
        await self.bot.change_presence(status=status_map[status.lower()])
        await ctx.send(f"✅ Presence changed to: **{status}**")

    @commands.command(name="nickname")
    async def change_nickname(self, ctx, *, nickname: str = None):
        """Change bot's nickname in this server"""
        try:
            await ctx.guild.me.edit(nick=nickname)
            if nickname:
                await ctx.send(f"✅ Nickname changed to: **{nickname}**")
            else:
                await ctx.send("✅ Nickname reset to default")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change my nickname!")

    # ==================== FUN CHAOS COMMANDS ====================

    @commands.command(name="raincoins")
    async def raincoins(self, ctx, amount: int = 1000):
        """Make it rain coins for everyone online"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        online_members = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        
        for member in online_members:
            economy_cog.add_coins(member.id, amount, "coin_rain")
        
        await ctx.send(f"💸💸💸 **IT'S RAINING COINS!** 💸💸💸\n**{amount:,} PsyCoins** given to {len(online_members)} online members!")

    @commands.command(name="chaos")
    async def chaos_mode(self, ctx):
        """Activate CHAOS MODE - random rewards for everyone"""
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        await ctx.send(random.choice(self.chaos_responses))
        
        members = [m for m in ctx.guild.members if not m.bot]
        rewards = []
        
        for member in members:
            # Random reward between 100-10000
            reward = random.randint(100, 10000)
            economy_cog.add_coins(member.id, reward, "chaos_mode")
            
            # Random chance for items
            if random.random() < 0.3:  # 30% chance
                item_id = random.choice(list(economy_cog.shop_items.keys()))
                economy_cog.add_item(member.id, item_id, 1)
                rewards.append(f"{member.mention}: {reward:,} coins + item!")
            else:
                rewards.append(f"{member.mention}: {reward:,} coins")
        
        # Send in chunks to avoid message limit
        chunk_size = 10
        for i in range(0, len(rewards), chunk_size):
            chunk = rewards[i:i+chunk_size]
            await ctx.send("\n".join(chunk))
        
        await ctx.send("🎭 **CHAOS MODE COMPLETE!**")

    @commands.command(name="spinlottery")
    async def run_lottery(self, ctx, prize: int = 50000):
        """Run a lottery - pick a random winner (owner command to avoid conflict with lottery.py)"""
        members = [m for m in ctx.guild.members if not m.bot]
        winner = random.choice(members)
        
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            economy_cog.add_coins(winner.id, prize, "lottery_win")
        
        embed = discord.Embed(
            title="🎰 LOTTERY WINNER! 🎰",
            description=f"🎉 Congratulations {winner.mention}!\n\nYou won **{prize:,} PsyCoins**!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="cursed")
    async def cursed_message(self, ctx):
        """Send a cursed/haunted message"""
        cursed_messages = [
            "H̴̡̢̳̠̻̰̲̼̦̱̻̥̮͎̳̠̱̙͌̓̂̌̏ͅE̷̡͚̭͔͎̮̞̩͕̮̙͆̎͒̾̈́̎̾̏ͅ ̸̨̧̛̹̲̳̰̰̜̼̗̟̻̈́͑̓̆̄C̴̡̧̛͚̲̭̞̳̫̝̦̦̔̍̾̋̈́͐͛̿́̍̕͜͝O̴̧̨̫̩̺͓̫̙̦̜̹̊̑͛̐̀̾̅̿̅̆̚͝M̸̧̢̠̘̜̤̫̮͉̫̞̟̎̾̈́̌̍̏̂̿Ę̷̧̛̜̦̯̗̝̦̜̠̈́̍̀̍͋̐̈́̕͝S̶̡̛̻͈̥͎̱͎̯̫͐̽̊͊͆͜",
            "T̶̢̛̤͖͔̳̟͖̹̜̀̔͌̆̇̚͜h̷̢̹͉͖̞̻̦̪̪̰͌̓̍̃̿͂̌͘͝ę̷̣̭̝̫̜̱̱͚̀́͂̃̈̃̈́̚͝ ̵̧͕͙̼̲̳̗̣͚̈́̈́̄̿͘͠v̴̢̧̱̺̬̞̜͈̄͂̂̓̂́̕͠͝ͅo̵̧̢̗͍͎̰͉̠̹̔̏̿̃̑̓̎͘͜ḯ̵̧̢̛̻̮͕̤̲͙̞̋̏̎̚͝d̴̢̗̬͚̰̱̥̗̏̀̀̐̈́̍͘͝ ̴̦̹̟͈̺̙̝͍͐̔̈́͑̃̽̚͝w̶̢̛̗̪̟̝̜̮͚̤̓̋͗͊̑̌̒͘a̸̢̟͕̠̭̪̳͑̎̏̀̊͊̈́͘t̶̢̹̱͎̼̝̫̱̐̏̌̐̓̈́̑̈́c̷̡̨̬̰̪̖͎̼̦͋̀̈́̍̇̊̌̚h̶̨̨̲̜̘͈̪̮̺̔͑̄͑̿̆͝ė̶̡̛̛͔͎̺̪̻̰͖̀̊̈́̓̕͘s̶̨̖͕̥̮̟̣͖̈́̈́͒̍͒́̚͝",
            "Y̷̢̨̱̹͕̱̹̦̌̊̀͜o̶̧̦̪̤͇̺̥͂̈̈́͗̚͜u̴͓̝̬̦̪̱̞͐̈́̍̈́̂̚͝ ̴̢̛̗̺̘̜̺̞̟͆̋̐̓̐͑c̸͕̻̥͓͌̈́̀́̅͝ą̶̯̰̫͇̦̐̌͘n̸̢̢̛̰̟̪̖̯̏̾̎̒̿̕'̴̡̛̱̣̲͉̫̘̈́͋͐̓̽͝ť̶̨̮̹͈̱͎̱̍̾͋͌̚ ̵̧̨̭̻̰͉͍̅̌̋͐̽͜͠ę̷̺͔̹͎̹̱̈s̶̨̛̲̱͔̼̱̦̎̀̊̈́̚c̴̥̪̫̈́̅̄̀̌̚ǎ̸̧̡̻̯̦̘̇͗͒̈́̕͠p̷̧̪͚̬̳̞̓̅̎͗̂͠ę̸̮͕̳̝͙̜̈́̐͌̓̉̀͝",
            "🕷️ T̵̢̢̛̝͍͇͕̪̳͎̯̠͓̤͙̝̮̍͑̐̋͗̔̑͋͐̕͝h̸̨̧̢̛̯͈̖̥͈̞̣̩͌̏̿̐̿̾͗̇̑̒̚͘͝͝e̵̡̝̞̤̰͙̣̦̠̰͉̿̈́̀̐̊̄͝ ̸̨̛̼̫̼̳̦̲̠͈̻̖͙͕̬̐̅͆̊̍̇̅̚̕s̴̛̩̝̗̩͔̼̣̺̫̦̉͐̓̇̈̀̎̄͊̿̚̕͜͝p̴̧̛̘̤͕̣̱̰̺̝͙̟̐̋̈̀̈́̍̾̀̓̆͌̕i̵̪̇̀̌̓̍̋́̓̎̂͝͝d̷̨̛̩̫̙̞̬̠͔͍̖̖̱̙̻̊̓͌̍̑̑̌̍̒͐͆͆͘͘͜ę̷̢̡̖͙̝̻̼̘͔̀̾͐̎̿͗̕͜͝r̸̨̲̘̬͙̦̠͊̊͋͜͝s̴̨̧̧̡̱̹̮̘̼͈͌̈́̓̾̾̕͝ ̴̣̙̪̭̝̱͉̀̾̌̈́͒͂̄͐̄̚͜a̵̧̡̛̘̱̣͚̻̩͕͌̑̀̽̊̈́̕͠r̴̳̳͙̫̺͕͓̻̙̈́̒̈̿̎̉̈́̓̓̈ę̴̡̢̧̢̙͈̥̹̺̥̺͓̉̒͘͜͝ ̴̡̤̖̙̞̻̪̬̫̪̦͚̐͂́c̵̡̧̨͇̭̙̘̗̊̍̉̀̒͑̕͜o̷̡̭͇̮̺͕̫̗̹̊̓͛͒̇̽̓̕̚m̴̧̛̛̖̙̪͊̇̈́̈́̐͌̕͘͝͝ͅi̴̢̺͇̹̜͈̳̗͕̊̿͋̂̒̓̈́͛͌̃́̚͝ň̴̨̡̮̗̪̞͎̰͈̺̗̑͆̈́̀͒͂́̍̌̚͝g̴̲̼̼̦͉̞̹̤͋̋̔̃̇̓̇̕ 🕷️",
            "Ỉ̷̡̦̫͚̼̰͍̗̐̋̓͌͌̓͋̊̂͘͝'̶̡̧̯̙͕̗̹̳̯̻̩̃͆͑̈͛͑̂̽̓̂̕͝m̶̛̻͕̞̗̭̪̣̰͉̂̆́͆̓̈́̋̀̈́̓̕͠ ̸̢̡͎̺̬̤̩̙̰̰̝̗̎͐̌̍̈́̕͝ẁ̷̨̛̛͔̻̪̳͎̳̘̬̻̈́̽̄͑́̊̈́̒̚͜͝a̴̡͇̻̹̞̱̠̤̞̱͇̦̐̅͋͑̒͗̕͜͠t̶̨̛̠̰̖͚̫̩̙̠̀̍̌͂͗̂̀̾c̶̡̘̝̩̖̈́̾͆̍̂̑̒͊̀̾̾̚͜͝h̷̝̼͙̺̮̩̮̪̓̆͋͛̚̚͝i̴̧̞̙̩̟̣̘̋n̵̜̜̗̥̔͑̅́̚͜g̵̨̛̯̱̦̺̫̫͈͕̜̼̦̈̑̓̿͗̈́̕͠͝"
        ]
        
        await ctx.send(random.choice(cursed_messages))
        await asyncio.sleep(1)
        await ctx.send("Just kidding! 😈")

    @commands.command(name="countset")
    async def count_set(self, ctx, number: int):
        """Set the current counting number (owner only)"""
        if number < 0:
            await ctx.send("❌ Number must be 0 or greater!")
            return
        
        counting_cog = self.bot.get_cog("Counting")
        if not counting_cog:
            await ctx.send("❌ Counting system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        
        # Check if counting is set up
        if guild_id not in counting_cog.count_data:
            await ctx.send("❌ Counting game is not set up in this server! Use `L!counting` first.")
            return
        
        # Set the count
        counting_cog.count_data[guild_id]["current_count"] = number
        counting_cog.count_data[guild_id]["last_user"] = None  # Reset last user
        counting_cog.save_data()
        
        embed = discord.Embed(
            title="🔢 Count Updated!",
            description=f"The counting game has been set to **{number:,}**\n\nNext number expected: **{number + 1:,}**",
            color=discord.Color.green()
        )
        
        counting_channel_id = counting_cog.count_data[guild_id].get("channel")
        if counting_channel_id:
            counting_channel = ctx.guild.get_channel(counting_channel_id)
            if counting_channel:
                embed.add_field(name="Channel", value=counting_channel.mention, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="spawn")
    async def spawn_boss(self, ctx):
        """Spawn a 'raid boss' event"""
        bosses = [
            {"name": "🐉 Ancient Dragon", "hp": 10000, "reward": 5000},
            {"name": "👾 Cyber Demon", "hp": 15000, "reward": 7500},
            {"name": "🦑 Kraken", "hp": 20000, "reward": 10000},
            {"name": "👹 Demon Lord", "hp": 25000, "reward": 15000},
            {"name": "🌟 Celestial Being", "hp": 30000, "reward": 20000}
        ]
        
        boss = random.choice(bosses)
        
        embed = discord.Embed(
            title="⚔️ RAID BOSS SPAWNED! ⚔️",
            description=f"**{boss['name']}** has appeared!\n\n"
                       f"**HP:** {boss['hp']:,}\n"
                       f"**Reward:** {boss['reward']:,} PsyCoins\n\n"
                       f"React with ⚔️ to join the battle!",
            color=discord.Color.red()
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
        
        await asyncio.sleep(30)  # Wait 30 seconds for reactions
        
        message = await ctx.channel.fetch_message(message.id)
        reaction = discord.utils.get(message.reactions, emoji="⚔️")
        
        if reaction and reaction.count > 1:  # Minus the bot's reaction
            users = [user async for user in reaction.users() if not user.bot]
            
            # Calculate reward split
            reward_per_user = boss['reward'] // len(users)
            
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                for user in users:
                    economy_cog.add_coins(user.id, reward_per_user, "raid_boss")
            
            embed = discord.Embed(
                title="🎉 BOSS DEFEATED! 🎉",
                description=f"**{len(users)} heroes** defeated {boss['name']}!\n\n"
                           f"Each warrior received **{reward_per_user:,} PsyCoins**!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"💀 {boss['name']} escaped! No one joined the battle...")

    # ==================== SERVER MANAGEMENT ====================

    @commands.command(name="purge")
    async def purge_messages(self, ctx, amount: int = 10):
        """Delete messages in current channel"""
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for command message
        
        msg = await ctx.send(f"🗑️ Deleted {len(deleted)-1} messages")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name="announce")
    async def announce(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send an announcement to a channel"""
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"From: {ctx.author.display_name}")
        
        await channel.send(embed=embed)
        await ctx.send(f"✅ Announcement sent to {channel.mention}")

    @commands.command(name="dm")
    async def dm_user(self, ctx, member: discord.Member, *, message: str):
        """DM a specific user"""
        try:
            await member.send(message)
            await ctx.send(f"✅ DM sent to {member.mention}")
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot DM {member.mention} - they have DMs disabled")

    @commands.command(name="stats")
    async def ludus_stats(self, ctx, action: str = "view"):
        """Show detailed bot statistics with live updates
        
        Usage:
        L!stats - View current stats
        L!stats update - Force update and recalculate all stats
        """
        
        if action.lower() == "update":
            # Force recalculation
            msg = await ctx.send("🔄 Updating all statistics...")
            
            # Log the update
            logger = self.bot.get_cog("BotLogger")
            if logger:
                await logger.log_owner_command(ctx, "stats update", "Recalculating all bot statistics")
            
            await msg.edit(content="✅ Statistics updated!")
        
        # Calculate comprehensive stats
        embed = discord.Embed(
            title="📊 LUDUS BOT STATISTICS",
            description="**Real-time bot analytics and metrics**",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        
        # ===== SERVER STATS =====
        total_members = sum(g.member_count for g in self.bot.guilds)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        
        server_stats = (f"**Servers:** {len(self.bot.guilds):,}\n"
                       f"**Total Users:** {total_members:,}\n"
                       f"**Channels:** {total_channels:,}\n"
                       f"**Latency:** {round(self.bot.latency * 1000)}ms")
        
        embed.add_field(name="🌐 Server Stats", value=server_stats, inline=True)
        
        # ===== COMMAND STATS =====
        total_commands = len(self.bot.commands) + len(self.bot.tree.get_commands())
        
        command_stats = (f"**Prefix Commands:** {len(self.bot.commands)}\n"
                        f"**Slash Commands:** {len(self.bot.tree.get_commands())}\n"
                        f"**Total:** {total_commands}\n"
                        f"**Cogs Loaded:** {len(self.bot.cogs)}")
        
        embed.add_field(name="⚙️ Commands", value=command_stats, inline=True)
        
        # ===== ECONOMY STATS =====
        economy_cog = self.bot.get_cog("Economy")
        if economy_cog:
            total_users = len(economy_cog.economy_data)
            total_coins = sum(data.get("balance", 0) for data in economy_cog.economy_data.values())
            avg_coins = total_coins // total_users if total_users > 0 else 0
            
            # Get top 3 richest users
            top_users = sorted(
                economy_cog.economy_data.items(),
                key=lambda x: x[1].get("balance", 0),
                reverse=True
            )[:3]
            
            economy_stats = (f"**Total Users:** {total_users:,}\n"
                           f"**Total Coins:** {total_coins:,} 💰\n"
                           f"**Average Balance:** {avg_coins:,}\n"
                           f"**Richest Users:**")
            
            for idx, (user_id, data) in enumerate(top_users, 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    economy_stats += f"\n{idx}. {user.name}: {data.get('balance', 0):,}"
                except:
                    economy_stats += f"\n{idx}. User {user_id}: {data.get('balance', 0):,}"
            
            embed.add_field(name="💰 Economy", value=economy_stats, inline=False)
        
        # ===== ACTIVITY STATS =====
        # Games played
        total_games = 0
        minigames_cog = self.bot.get_cog("Minigames")
        leaderboard_cog = self.bot.get_cog("LeaderboardManager")
        
        if leaderboard_cog and hasattr(leaderboard_cog, 'stats'):
            for category_stats in leaderboard_cog.stats.values():
                for server_stats_data in category_stats.values():
                    total_games += server_stats_data.get("plays", 0)
        
        # Leveling stats
        leveling_cog = self.bot.get_cog("Leveling")
        total_levels = 0
        if leveling_cog and hasattr(leveling_cog, 'levels'):
            total_levels = sum(data.get("level", 0) for data in leveling_cog.levels.values())
        
        # Pets stats
        pets_cog = self.bot.get_cog("Pets")
        total_pets = 0
        if pets_cog and hasattr(pets_cog, 'pets_data'):
            total_pets = len([p for p in pets_cog.pets_data.values() if p.get("pet")])
        
        activity_stats = (f"**Games Played:** {total_games:,}\n"
                         f"**Total Levels:** {total_levels:,}\n"
                         f"**Pets Adopted:** {total_pets:,}")
        
        embed.add_field(name="🎮 Activity", value=activity_stats, inline=True)
        
        # ===== GLOBAL EVENTS =====
        global_events_cog = self.bot.get_cog("GlobalEvents")
        if global_events_cog and hasattr(global_events_cog, 'active_events'):
            active_events = len(global_events_cog.active_events)
            events_list = ", ".join(global_events_cog.active_events.keys()) if active_events > 0 else "None"
            
            events_stats = (f"**Active Events:** {active_events}\n"
                          f"**Types:** {events_list}")
            
            embed.add_field(name="🌍 Global Events", value=events_stats, inline=True)
        
        # ===== GLOBAL LEADERBOARD =====
        global_lb_cog = self.bot.get_cog("GlobalLeaderboard")
        if global_lb_cog and hasattr(global_lb_cog, 'data'):
            servers_ranked = len([s for s, d in global_lb_cog.consents.items() if d.get("enabled", False)])
            
            # Calculate top server
            if global_lb_cog.data:
                top_server_id = max(
                    global_lb_cog.data.keys(),
                    key=lambda x: global_lb_cog.calculate_server_score(x)
                )
                top_score = global_lb_cog.calculate_server_score(top_server_id)
                try:
                    top_guild = self.bot.get_guild(int(top_server_id))
                    top_name = top_guild.name if top_guild else f"Server {top_server_id}"
                except:
                    top_name = f"Server {top_server_id}"
            else:
                top_name = "None"
                top_score = 0
            
            global_stats = (f"**Servers Ranked:** {servers_ranked}\n"
                          f"**Top Server:** {top_name}\n"
                          f"**Top Score:** {top_score:,}")
            
            embed.add_field(name="🏆 Global Rankings", value=global_stats, inline=True)
        
        # ===== MULTIPLAYER GAMES =====
        multiplayer_cog = self.bot.get_cog("MultiplayerGames")
        if multiplayer_cog and hasattr(multiplayer_cog, 'active_lobbies'):
            active_lobbies = len(multiplayer_cog.active_lobbies)
            
            mp_stats = f"**Active Games:** {active_lobbies}"
            
            embed.add_field(name="🎮 Multiplayer", value=mp_stats, inline=True)
        
        # ===== FISHING & FARMING =====
        fishing_cog = self.bot.get_cog("FishingAkinatorFun")
        if fishing_cog and hasattr(fishing_cog, 'fishing_data'):
            total_fish = sum(len(data.get("fish", {})) for data in fishing_cog.fishing_data.values())
            total_fishers = len(fishing_cog.fishing_data)
            
            fishing_stats = (f"**Total Fishers:** {total_fishers:,}\n"
                           f"**Fish Caught:** {total_fish:,}")
            
            embed.add_field(name="🎣 Fishing", value=fishing_stats, inline=True)
        
        simulations_cog = self.bot.get_cog("Simulations")
        if simulations_cog and hasattr(simulations_cog, 'farms'):
            total_farmers = len(simulations_cog.farms)
            total_crops = sum(
                len([p for p in farm.get("plots", {}).values() if p.get("crop")])
                for farm in simulations_cog.farms.values()
            )
            
            farming_stats = (f"**Total Farmers:** {total_farmers:,}\n"
                           f"**Crops Planted:** {total_crops:,}")
            
            embed.add_field(name="🌾 Farming", value=farming_stats, inline=True)
        
        embed.set_footer(text=f"Updated by {ctx.author.name}" if action.lower() == "update" else "Use L!stats update to refresh")
        
        await ctx.send(embed=embed)

    @commands.command(name="update")
    async def update_command(self, ctx, system: str = None):
        """Update various systems (Owner only)"""
        if not system:
            await ctx.send("❌ Please specify what to update: `L!update global` or `L!update stats`")
            return
        
        if system.lower() == "global":
            # Update global leaderboard
            global_cog = self.bot.get_cog("GlobalLeaderboard")
            if not global_cog:
                await ctx.send("❌ Global Leaderboard cog not found!")
                return
            
            # Log the update
            logger_cog = self.bot.get_cog("BotLogger")
            if logger_cog:
                await logger_cog.log_owner_command(
                    ctx.author,
                    "L!update global",
                    f"Manual global leaderboard recalculation"
                )
            
            # Recalculate all server scores
            updated_count = 0
            for guild in self.bot.guilds:
                guild_id = str(guild.id)
                
                # Check consent
                if guild_id not in global_cog.consents or not global_cog.consents[guild_id].get("enabled", False):
                    continue
                
                # Calculate score
                score = global_cog.calculate_server_score(guild_id)
                
                # Ensure server data exists
                if guild_id not in global_cog.data:
                    global_cog.data[guild_id] = {
                        "games_played": 0,
                        "tasks_completed": 0,
                        "events_participated": 0,
                        "coins_earned": 0,
                        "messages_sent": 0,
                        "members_active": 0
                    }
                
                # Update timestamp
                global_cog.data[guild_id]["last_updated"] = datetime.utcnow().isoformat()
                updated_count += 1
            
            global_cog.save_data()
            
            embed = discord.Embed(
                title="✅ Global Leaderboard Updated",
                description=f"Recalculated scores for **{updated_count} servers**\n\n"
                           f"Updated by: {ctx.author.mention}\n"
                           f"Timestamp: <t:{int(datetime.utcnow().timestamp())}:F>",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        
        elif system.lower() == "stats":
            # Redirect to L!stats update
            await ctx.invoke(self.bot.get_command('stats'), action="update")
        
        else:
            await ctx.send(f"❌ Unknown system: `{system}`\nAvailable: `global`, `stats`")

    # ==================== DEBUG COMMANDS ====================

    @commands.command(name="eval")
    async def eval_code(self, ctx, *, code: str):
        """Evaluate Python code (DANGEROUS - Owner only)"""
        try:
            # Remove code block formatting if present
            if code.startswith("```python"):
                code = code[9:-3]
            elif code.startswith("```"):
                code = code[3:-3]
            
            result = eval(code)
            
            embed = discord.Embed(
                title="✅ Evaluation Result",
                description=f"```python\n{result}\n```",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Evaluation Error",
                description=f"```python\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="reload")
    async def reload_cog(self, ctx, cog_name: str):
        """Reload a specific cog"""
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Reloaded cog: **{cog_name}**")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload **{cog_name}**: {str(e)}")

    @commands.command(name="reloadall")
    async def reload_all(self, ctx):
        """Reload all cogs"""
        success = []
        failed = []
        
        for cog_name in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(cog_name)
                success.append(cog_name.split('.')[-1])
            except Exception as e:
                failed.append(f"{cog_name.split('.')[-1]}: {str(e)}")
        
        embed = discord.Embed(title="🔄 Reload Results", color=discord.Color.blue())
        
        if success:
            embed.add_field(name="✅ Success", value="\n".join(success), inline=False)
        if failed:
            embed.add_field(name="❌ Failed", value="\n".join(failed), inline=False)
        
        await ctx.send(embed=embed)

    # ==================== FUN TROLL COMMANDS ====================

    @commands.command(name="hack")
    async def fake_hack(self, ctx, member: discord.Member):
        """Fake 'hack' a user (just for fun)"""
        messages = [
            f"🔓 Accessing {member.mention}'s account...",
            "📡 Connecting to mainframe...",
            "💾 Downloading data...",
            "🔐 Bypassing security...",
            "⚠️ FIREWALL DETECTED!",
            "🛡️ Deploying countermeasures...",
            "✅ Access granted!",
            f"📊 {member.display_name}'s secrets:\n"
            f"```\n"
            f"Favorite Game: {random.choice(['Tic-Tac-Toe', 'Connect 4', 'Wordle', 'Typing Race'])}\n"
            f"Lucky Number: {random.randint(1, 100)}\n"
            f"Secret Wish: More PsyCoins\n"
            f"Hidden Talent: Being awesome\n"
            f"```"
        ]
        
        msg = await ctx.send("Initiating hack sequence...")
        
        for message in messages:
            await asyncio.sleep(2)
            await msg.edit(content=message)
        
        await asyncio.sleep(3)
        await ctx.send(f"{member.mention} You've been hacked! 😈\n(Just kidding, all your data is safe! 😄)")

    @commands.command(name="roastme")
    async def ultimate_roast(self, ctx):
        """Get the ultimate roast"""
        roasts = [
            "You're so powerful, even the bot fears you... just kidding, you're still a potato. 🥔",
            "I'd call you a tool, but even tools have uses.",
            "You're proof that even gods can make mistakes.",
            "Your code is like your personality - full of bugs.",
            "You're the human equivalent of a participation trophy.",
            "If you were a spice, you'd be flour.",
            "You're the reason the gene pool needs a lifeguard."
        ]
        
        await ctx.send(f"{ctx.author.mention}\n{random.choice(roasts)}")

    @commands.command(name="vibecheck", aliases=["vc"])
    async def vibe_check(self, ctx, member: Optional[discord.Member] = None):
        """Check someone's vibe"""
        target = member or ctx.author
        
        vibes = [
            ("✨ IMMACULATE", "10/10", discord.Color.gold()),
            ("🔥 FIRE", "9/10", discord.Color.orange()),
            ("😎 COOL", "8/10", discord.Color.blue()),
            ("👍 GOOD", "7/10", discord.Color.green()),
            ("😐 MID", "5/10", discord.Color.greyple()),
            ("😬 SUS", "3/10", discord.Color.red()),
            ("💀 FAILED", "0/10", discord.Color.dark_red())
        ]
        
        vibe, score, color = random.choice(vibes)
        
        embed = discord.Embed(
            title="🌊 VIBE CHECK 🌊",
            description=f"{target.mention}\n\n**Status:** {vibe}\n**Score:** {score}",
            color=color
        )
        
        await ctx.send(embed=embed)

    # ==================== CUSTOM ROLE CREATOR ====================
    
    @commands.command(name="customrole")
    async def customrole_command(self, ctx):
        """Open custom role manager interface"""
        view = CustomRoleManagerView(self.bot, ctx.author)
        await view.show(ctx)
    
    # ==================== OWNER HELP ====================
    
    @commands.command(name="ownerhelp", aliases=["👑", "owner", "helpowner"])
    async def owner_help(self, ctx):
        """Show all secret owner commands"""
        embed = discord.Embed(
            title="👑 Owner Commands",
            description="Commands only you can use!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Economy Management",
            value="```\n"
                  "L!godmode - Max out your stats\n"
                  "L!setcoins @user <amount> - Set balance\n"
                  "L!addcoins @user <amount> - Add coins\n"
                  "L!removecoins @user <amount> - Remove coins\n"
                  "L!resetcoins @user - Reset economy data\n"
                  "L!giveitem @user <item_id> [qty] - Give items\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🤖 Bot Status",
            value="```\n"
                  "L!status <type> <text> - Change activity\n"
                  "L!presence <status> - Change online status\n"
                  "L!nickname <name> - Change bot nickname\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Fun & Chaos",
            value="```\n"
                  "L!raincoins [amount] - Give everyone coins\n"
                  "L!chaos - Random rewards for all\n"
                  "L!lottery [prize] - Random winner\n"
                  "L!cursed - Send cursed message\n"
                  "L!spawn - Spawn raid boss\n"
                  "L!hack @user - Fake hack (fun)\n"
                  "L!roastme - Ultimate roast\n"
                  "L!vibe [@user] - Vibe check\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🎣 Fishing Management",
            value="```\n"
                  "L!fishing_tournament <mode> <mins> - Start tournament\n"
                  "  Modes: biggest, most, rarest\n"
                  "  Duration: 1-30 minutes\n"
                  "L!give_fish @user <fish_id> [qty] - Give fish\n"
                  "L!give_bait @user <bait_id> [qty] - Give bait\n"
                  "  Special: kraken_bait (summons Kraken boss!)\n"
                  "L!give_rod @user <rod_id> - Give fishing rod\n"
                  "L!give_boat @user <boat_id> - Give boat\n"
                  "L!unlock_area @user <area_id> - Unlock area\n"
                  "Note: Random tournaments spawn automatically every 2-4h\n"
                  "Use /fish craft to craft kraken_bait from 8 tentacles\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Mafia/Werewolf Custom Roles",
            value="```\n"
                  "L!customrole - Open custom role manager (UI)\n"
                  "  • Create new roles with modal form\n"
                  "  • Choose custom emoji for each role\n"
                  "  • Delete existing custom roles\n"
                  "  • All 65+ powers supported\n"
                  "  • Persistent (saved to JSON file)\n"
                  "  • Auto-loads on bot restart\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Server Management",
            value="```\n"
                  "L!purge [amount] - Delete messages\n"
                  "L!announce <#channel> <msg> - Send announcement\n"
                  "L!dm @user <message> - DM a user\n"
                  "L!stats - Bot statistics\n"
                  "L!stats update - Refresh bot stats\n"
                  "L!update global - Update global leaderboard\n"
                  "L!update stats - Update bot stats\n"
                  "L!countset <number> - Set counting number\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Debug",
            value="```\n"
                  "L!eval <code> - Evaluate Python code\n"
                  "L!reload <cog> - Reload specific cog\n"
                  "L!reloadall - Reload all cogs\n"
                  "L!ownermine - Developer mining mode with testing features\n"
                  "```",
            inline=False
        )
        
        embed.set_footer(text="These commands are secret! Use them wisely 😈")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Owner(bot))
