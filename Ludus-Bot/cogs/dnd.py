import discord
from discord.ext import commands
from discord import app_commands, ui
import json
import random
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import os

# User storage import
try:
    from utils import user_storage
    HAS_USER_STORAGE = True
except:
    HAS_USER_STORAGE = False

# Save file location
SAVE_FILE = "data/dnd_saves.json"
PARTY_FILE = "data/dnd_parties.json"


class GameModeSelectView(discord.ui.LayoutView):
    """Select game mode: Solo, Create Party, or Join Party"""
    def __init__(self, cog, user_id: int, username: str, campaign_type: str, channel):
        self.cog = cog
        self.user_id = user_id
        self.username = username
        self.campaign_type = campaign_type
        self.channel = channel
        super().__init__(timeout=120)
        self._build_ui()
    
    def _build_ui(self):
        """Build UI with buttons in container"""
        # Create buttons
        solo_btn = discord.ui.Button(label="🎮 Solo Mode", style=discord.ButtonStyle.primary, emoji="🎮")
        solo_btn.callback = self.solo_mode
        
        create_party_btn = discord.ui.Button(label="👥 Create Party", style=discord.ButtonStyle.success, emoji="👥")
        create_party_btn.callback = self.create_party
        
        join_party_btn = discord.ui.Button(label="🤝 Join Party", style=discord.ButtonStyle.success, emoji="🤝")
        join_party_btn.callback = self.join_party
        
        # Build container
        container_items = [
            discord.ui.TextDisplay(content=f"# 🎲 D&D Campaign Mode\n\n**Campaign Type:** {self.campaign_type}\n\nChoose how you want to play:"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(solo_btn, create_party_btn, join_party_btn),
        ]
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x8B4513),
        )
        
        self.add_item(self.container)
    
    async def solo_mode(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your choice!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Show class selection
        view = ClassSelectView(self.cog, self.user_id, self.username, self.campaign_type, self.channel, party_mode=False)
        
        class_embed = discord.Embed(
            title="🎭 Choose Your Class",
            description=f"**Campaign: {self.campaign_type}**\n\nSelect your character class...",
            color=discord.Color.gold()
        )
        
        await interaction.followup.send(embed=class_embed, view=view)
        
        # Disable this view and rebuild UI
        self.clear_items()
        
        # Rebuild with disabled buttons
        solo_btn = discord.ui.Button(label="🎮 Solo Mode", style=discord.ButtonStyle.primary, emoji="🎮", disabled=True)
        create_party_btn = discord.ui.Button(label="👥 Create Party", style=discord.ButtonStyle.success, emoji="👥", disabled=True)
        join_party_btn = discord.ui.Button(label="🤝 Join Party", style=discord.ButtonStyle.success, emoji="🤝", disabled=True)
        
        container_items = [
            discord.ui.TextDisplay(content=f"# 🎲 D&D Campaign Mode\n\n**Campaign Type:** {self.campaign_type}\n\nSolo Mode selected!"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(solo_btn, create_party_btn, join_party_btn),
        ]
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x8B4513),
        )
        
        self.add_item(self.container)
        await interaction.message.edit(view=self)
    
    async def create_party(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your choice!", ephemeral=True)
            return
        
        # Show modal for party name
        modal = PartyNameModal(self.cog, self.user_id, self.username, self.campaign_type, self.channel, is_join=False)
        await interaction.response.send_modal(modal)
    
    async def join_party(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your choice!", ephemeral=True)
            return
        
        # Show modal for party name
        modal = PartyNameModal(self.cog, self.user_id, self.username, self.campaign_type, self.channel, is_join=True)
        await interaction.response.send_modal(modal)


class PartyNameModal(ui.Modal, title="Party Name"):
    """Modal for entering party name"""
    def __init__(self, cog, user_id: int, username: str, campaign_type: str, channel, is_join: bool):
        super().__init__()
        self.cog = cog
        self.user_id = user_id
        self.username = username
        self.campaign_type = campaign_type
        self.channel = channel
        self.is_join = is_join
    
    party_name = ui.TextInput(
        label="Party Name",
        placeholder="Enter party name...",
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        party_name = self.party_name.value
        
        os.makedirs('data', exist_ok=True)
        parties = {}
        if os.path.exists(PARTY_FILE):
            try:
                with open(PARTY_FILE, 'r', encoding='utf-8') as f:
                    parties = json.load(f)
            except:
                parties = {}
        
        if self.is_join:
            # Join existing party
            party_id = None
            for pid, party_data in parties.items():
                if party_data['name'] == party_name:
                    party_id = pid
                    break
            
            if not party_id:
                await interaction.response.send_message(f"❌ Party '{party_name}' not found!", ephemeral=True)
                return
            
            party = parties[party_id]
            
            if self.user_id in party['members']:
                await interaction.response.send_message("❌ You're already in this party!", ephemeral=True)
                return
            
            # Add member
            party['members'].append(self.user_id)
            
            with open(PARTY_FILE, 'w', encoding='utf-8') as f:
                json.dump(parties, f, indent=2)
            
            await interaction.response.send_message(f"✅ Joined party: **{party_name}**!\n\nWaiting for leader to start...", ephemeral=True)
            await self.channel.send(f"👥 **{interaction.user.display_name}** joined party **{party_name}**!")
        
        else:
            # Create new party
            party_id = f"{self.user_id}_{party_name}"
            
            if party_id in parties:
                await interaction.response.send_message(f"❌ You already have a party named '{party_name}'!", ephemeral=True)
                return
            
            parties[party_id] = {
                'leader': self.user_id,
                'name': party_name,
                'campaign': self.campaign_type,
                'members': [self.user_id],
                'created': datetime.utcnow().isoformat()
            }
            
            with open(PARTY_FILE, 'w', encoding='utf-8') as f:
                json.dump(parties, f, indent=2)
            
            await interaction.response.defer()
            
            # Show party lobby
            view = PartyLobbyView(self.cog, self.user_id, self.username, self.campaign_type, self.channel, party_name, party_id)
            
            embed = discord.Embed(
                title=f"👥 Party: {party_name}",
                description=f"**Campaign:** {self.campaign_type}\n\n"
                            f"**Leader:** {interaction.user.display_name}\n"
                            f"**Members (1):**\n• {interaction.user.display_name}\n\n"
                            f"Press **🎬 Start Campaign** when ready!\n"
                            f"Others can press **🤝 Join Party** to join.",
                color=discord.Color.gold()
            )
            
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message


class PartyLobbyView(ui.View):
    """Lobby for party before starting campaign"""
    def __init__(self, cog, leader_id: int, leader_name: str, campaign_type: str, channel, party_name: str, party_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.leader_id = leader_id
        self.leader_name = leader_name
        self.campaign_type = campaign_type
        self.channel = channel
        self.party_name = party_name
        self.party_id = party_id
        self.message = None
    
    @ui.button(label="🎬 Start Campaign", style=discord.ButtonStyle.success, emoji="🎬", row=0)
    async def start_campaign(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("❌ Only party leader can start!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Load party data
        try:
            with open(PARTY_FILE, 'r', encoding='utf-8') as f:
                parties = json.load(f)
        except:
            await interaction.followup.send("❌ Error loading party!", ephemeral=True)
            return
        
        party = parties.get(self.party_id)
        if not party:
            await interaction.followup.send("❌ Party not found!", ephemeral=True)
            return
        
        # Initialize class selections for all members
        party['class_selections'] = {str(member_id): None for member_id in party['members']}
        party['characters'] = {}
        
        with open(PARTY_FILE, 'w', encoding='utf-8') as f:
            json.dump(parties, f, indent=2)
        
        # Send class selection message to channel for ALL members to choose
        class_embed = discord.Embed(
            title="🎭 Choose Your Class",
            description=f"**Campaign: {self.campaign_type}**\n\n"
                        f"**Party Mode** - Each member chooses their own class!\n\n"
                        f"Use the dropdown below to select your class.",
            color=discord.Color.gold()
        )
        
        view = PartyClassSelectView(self.cog, self.campaign_type, self.channel, party['members'], self.party_name, self.party_id)
        
        class_msg = await self.channel.send(embed=class_embed, view=view)
        
        # Disable lobby
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        await interaction.followup.send("🎬 Class selection started! All party members can now choose their class.", ephemeral=True)
    
    @ui.button(label="🤝 Join Party", style=discord.ButtonStyle.primary, emoji="🤝", row=0)
    async def join_party_button(self, interaction: discord.Interaction, button: ui.Button):
        # Check if already in party
        try:
            with open(PARTY_FILE, 'r', encoding='utf-8') as f:
                parties = json.load(f)
        except:
            await interaction.response.send_message("❌ Error loading party!", ephemeral=True)
            return
        
        party = parties.get(self.party_id)
        if not party:
            await interaction.response.send_message("❌ Party not found!", ephemeral=True)
            return
        
        if interaction.user.id in party['members']:
            await interaction.response.send_message("❌ You're already in this party!", ephemeral=True)
            return
        
        # Add member
        party['members'].append(interaction.user.id)
        
        with open(PARTY_FILE, 'w', encoding='utf-8') as f:
            json.dump(parties, f, indent=2)
        
        await interaction.response.send_message(f"✅ Joined party: **{self.party_name}**!\n\nWaiting for leader to start...", ephemeral=True)
        
        # Update lobby embed with new member count
        try:
            member_names = []
            for member_id in party['members']:
                try:
                    user = await self.cog.bot.fetch_user(member_id)
                    member_names.append(user.display_name)
                except:
                    member_names.append(f"User {member_id}")
            
            members_text = "\n".join([f"• {name}" for name in member_names])
            
            embed = discord.Embed(
                title=f"👥 Party: {self.party_name}",
                description=f"**Campaign:** {self.campaign_type}\n\n"
                            f"**Leader:** {self.leader_name}\n"
                            f"**Members ({len(party['members'])}):**\n{members_text}\n\n"
                            f"Press **🎬 Start Campaign** when ready!\n"
                            f"Others can press **🤝 Join Party** to join.",
                color=discord.Color.gold()
            )
            
            if self.message:
                await self.message.edit(embed=embed)
            else:
                await interaction.message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating lobby: {e}")
        
        # Send notification to channel
        await self.channel.send(f"👥 **{interaction.user.display_name}** joined party **{self.party_name}**!")


class PartyClassSelectView(ui.View):
    """Class selection for party mode - each member chooses their own class"""
    def __init__(self, cog, campaign_type: str, channel, party_members: List[int], party_name: str, party_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.campaign_type = campaign_type
        self.channel = channel
        self.party_members = party_members
        self.party_name = party_name
        self.party_id = party_id
        
        # Add class selection dropdown
        class_select = ui.Select(
            placeholder="Choose your class...",
            options=[
                discord.SelectOption(label="⚔️ Warrior", value="warrior", description="Strength & Combat", emoji="⚔️"),
                discord.SelectOption(label="🔮 Mage", value="mage", description="Intelligence & Magic", emoji="🔮"),
                discord.SelectOption(label="🗡️ Rogue", value="rogue", description="Dexterity & Stealth", emoji="🗡️"),
                discord.SelectOption(label="✨ Cleric", value="cleric", description="Wisdom & Healing", emoji="✨"),
                discord.SelectOption(label="🏹 Ranger", value="ranger", description="Nature & Tracking", emoji="🏹"),
                discord.SelectOption(label="🛡️ Paladin", value="paladin", description="Charisma & Honor", emoji="🛡️")
            ]
        )
        class_select.callback = self.class_selected
        self.add_item(class_select)
    
    async def class_selected(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Check if user is in party
        if user_id not in self.party_members:
            await interaction.response.send_message("❌ You're not in this party!", ephemeral=True)
            return
        
        selected_class = interaction.data['values'][0]
        await interaction.response.defer()
        
        # Load party data
        try:
            with open(PARTY_FILE, 'r', encoding='utf-8') as f:
                parties = json.load(f)
        except:
            await interaction.followup.send("❌ Error loading party!", ephemeral=True)
            return
        
        party = parties.get(self.party_id)
        if not party:
            await interaction.followup.send("❌ Party not found!", ephemeral=True)
            return
        
        # Generate character for this user
        race = random.choice(list(self.cog.races.keys()))
        character = self.cog.generate_character(user_id, interaction.user.display_name, selected_class, race)
        
        # Save class selection and character
        if 'class_selections' not in party:
            party['class_selections'] = {}
        if 'characters' not in party:
            party['characters'] = {}
        
        party['class_selections'][str(user_id)] = selected_class
        party['characters'][str(user_id)] = character
        
        with open(PARTY_FILE, 'w', encoding='utf-8') as f:
            json.dump(parties, f, indent=2)
        
        # Check if all members have chosen
        all_chosen = all(party['class_selections'].get(str(mid)) is not None for mid in party['members'])
        
        if all_chosen:
            # Start campaign with all characters
            campaign_data = self.cog.generate_campaign(self.campaign_type, selected_class)
            
            # Create campaign view with multiple characters
            view = await CampaignView.create(
                self.cog, 
                party['leader'], 
                campaign_data, 
                party['characters'],  # Pass dict of all characters
                party_members=party['members'], 
                party_mode=True, 
                save_name=self.party_name
            )
            
            message = await self.channel.send(view=view)
            view.message = message
            
            # Register session for all members
            for member_id in party['members']:
                self.cog.active_sessions[member_id] = view
            
            # Disable class selection
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            # Send start notification
            await self.channel.send(f"🎬 **{self.party_name}** campaign has begun! All members have chosen their classes.")
        else:
            # Show progress
            chosen_count = sum(1 for mid in party['members'] if party['class_selections'].get(str(mid)) is not None)
            await interaction.followup.send(
                f"✅ You chose: **{selected_class.title()}**!\n\n"
                f"Waiting for other party members... ({chosen_count}/{len(party['members'])})",
                ephemeral=True
            )


class ClassSelectView(ui.View):
    """Class selection before campaign starts"""
    def __init__(self, cog, user_id: int, username: str, campaign_type: str, channel, party_mode: bool = False, party_members: List[int] = None, party_name: str = None):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.username = username
        self.campaign_type = campaign_type
        self.channel = channel
        self.selected_class = None
        self.party_mode = party_mode
        self.party_members = party_members or [user_id]
        self.party_name = party_name
        
        # Add class selection dropdown
        class_select = ui.Select(
            placeholder="Choose your class...",
            options=[
                discord.SelectOption(label="⚔️ Warrior", value="warrior", description="Strength & Combat", emoji="⚔️"),
                discord.SelectOption(label="🔮 Mage", value="mage", description="Intelligence & Magic", emoji="🔮"),
                discord.SelectOption(label="🗡️ Rogue", value="rogue", description="Dexterity & Stealth", emoji="🗡️"),
                discord.SelectOption(label="✨ Cleric", value="cleric", description="Wisdom & Healing", emoji="✨"),
                discord.SelectOption(label="🏹 Ranger", value="ranger", description="Nature & Tracking", emoji="🏹"),
                discord.SelectOption(label="🛡️ Paladin", value="paladin", description="Charisma & Honor", emoji="🛡️")
            ]
        )
        class_select.callback = self.class_selected
        self.add_item(class_select)
    
    async def class_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your selection!", ephemeral=True)
            return
        
        self.selected_class = interaction.data['values'][0]
        await interaction.response.defer()
        
        # Generate character with selected class
        race = random.choice(list(self.cog.races.keys()))
        character = self.cog.generate_character(self.user_id, self.username, self.selected_class, race)
        
        # Generate campaign
        campaign_data = self.cog.generate_campaign(self.campaign_type, self.selected_class)
        
        # Create campaign view with async factory
        view = await CampaignView.create(self.cog, self.user_id, campaign_data, character, 
                                          party_members=self.party_members, party_mode=self.party_mode, save_name=self.party_name)
        
        message = await self.channel.send(view=view)
        view.message = message
        
        self.cog.active_sessions[self.user_id] = view
        
        # Welcome message
        welcome = discord.Embed(
            title="🎲 Your Legend Begins",
            description=f"**{character['name']}** - Level {character['level']} {race.title()} **{self.selected_class.title()}**\n\n"
                        f"Campaign: **{campaign_data['name']}**\n"
                        f"Type: *{campaign_data['type']}*\n\n"
                        f"*Your class shapes your destiny.*\n"
                        f"*Every choice ripples through eternity.*\n"
                        f"*All paths are REAL.*",
            color=discord.Color.purple()
        )
        
        class_info = self.cog.classes[self.selected_class]
        welcome.add_field(
            name=f"{self._get_class_emoji(self.selected_class)} Class Bonuses",
            value=f"HP: +{class_info['hp']} | STR: +{class_info['str']} | DEX: +{class_info['dex']}\n"
                  f"INT: +{class_info['int']} | WIS: +{class_info['wis']} | CHA: +{class_info['cha']}",
            inline=False
        )
        
        welcome.set_footer(text="You are the author now. Write carefully.")
        await interaction.followup.send(embed=welcome, ephemeral=True)
        
        # Disable this view
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
    
    def _get_class_emoji(self, char_class: str) -> str:
        emojis = {"warrior": "⚔️", "mage": "🔮", "rogue": "🗡️", "cleric": "✨", "ranger": "🏹", "paladin": "🛡️"}
        return emojis.get(char_class, "⚔️")


class SaveNameModal(ui.Modal, title="Save Campaign"):
    """Modal for entering save name"""
    def __init__(self, campaign_view):
        super().__init__()
        self.campaign_view = campaign_view
    
    save_name = ui.TextInput(
        label="Save Name",
        placeholder="Enter name for this save...",
        required=True,
        max_length=50,
        default="My Campaign"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        save_name = self.save_name.value
        self.campaign_view.save_name = save_name
        
        # Create save data
        save_data = self.campaign_view.save_campaign()
        
        # Load existing saves
        os.makedirs('data', exist_ok=True)
        saves = {}
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    saves = json.load(f)
            except:
                saves = {}
        
        # Save under user_id and save_name
        user_saves = saves.get(str(self.campaign_view.user_id), {})
        user_saves[save_name] = save_data
        saves[str(self.campaign_view.user_id)] = user_saves
        
        # Write to file
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(saves, f, indent=2, ensure_ascii=False)
        
        embed = discord.Embed(
            title="💾 Campaign Saved",
            description=f"**Save Name:** {save_name}\n\n"
                        f"Campaign: {save_data['campaign_name']}\n"
                        f"Scene: {save_data['current_scene'] + 1}\n"
                        f"Character: {save_data['character']['name']} (Level {save_data['character']['level']})",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LoadSaveView(ui.View):
    """View for selecting which save to load"""
    def __init__(self, cog, user_id: int, user_saves: dict, channel):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id
        self.user_saves = user_saves
        self.channel = channel
        
        # Create select menu with saves (max 25 options)
        options = []
        for save_name, save_data in list(user_saves.items())[:25]:
            char = save_data['character']
            options.append(
                discord.SelectOption(
                    label=save_name[:100],
                    description=f"{save_data['campaign_name'][:50]} - Scene {save_data['current_scene'] + 1}",
                    value=save_name
                )
            )
        
        if options:
            save_select = ui.Select(
                placeholder="Choose save to load...",
                options=options
            )
            save_select.callback = self.load_selected_save
            self.add_item(save_select)
    
    async def load_selected_save(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your saves!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        save_name = interaction.data['values'][0]
        save_data = self.user_saves[save_name]
        
        # Check if user already in campaign
        if self.user_id in self.cog.active_sessions:
            await interaction.followup.send("❌ You're already in a campaign! Quit first.", ephemeral=True)
            return
        
        # Load campaign (now async)
        view = await CampaignView.load_campaign_data(save_data, self.cog, self.cog.generate_campaign)
        
        # Create initial message
        message = await self.channel.send(view=view)
        view.message = message
        
        # Register session(s)
        if view.party_mode:
            for member_id in view.party_members:
                self.cog.active_sessions[member_id] = view
        else:
            self.cog.active_sessions[self.user_id] = view
        
        await interaction.followup.send(f"📂 Loaded campaign: **{save_name}**", ephemeral=True)


class PartyVotingView(ui.View):
    """Party voting system for group decisions"""
    def __init__(self, campaign_view, choice_options: List[Dict], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.campaign_view = campaign_view
        self.choice_options = choice_options
        self.votes = {}  # user_id: choice_idx
        self.voters = set()
        self.vote_embed_msg = None
        
    @ui.button(label="Cast Vote", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def cast_vote(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in self.campaign_view.party_members:
            await interaction.response.send_message("❌ You're not in this party!", ephemeral=True)
            return
        
        if interaction.user.id in self.voters:
            await interaction.response.send_message("✅ You already voted!", ephemeral=True)
            return
        
        # Show voting options
        vote_select = ui.Select(
            placeholder="Choose your vote...",
            options=[
                discord.SelectOption(
                    label=opt['label'][:100],
                    description=opt.get('hint', '')[:100],
                    value=str(i),
                    emoji=opt.get('emoji', '🎲')
                ) for i, opt in enumerate(self.choice_options)
            ]
        )
        
        async def vote_callback(vote_interaction: discord.Interaction):
            choice_idx = int(vote_select.values[0])
            self.votes[vote_interaction.user.id] = choice_idx
            self.voters.add(vote_interaction.user.id)
            
            await vote_interaction.response.send_message(
                f"✅ Vote cast for: **{self.choice_options[choice_idx]['label']}**",
                ephemeral=True
            )
            
            # Update vote count
            await self.update_vote_status()
            
            # Check if all voted
            if len(self.voters) >= len(self.campaign_view.party_members):
                await self.finalize_vote()
        
        vote_select.callback = vote_callback
        view = ui.View(timeout=60)
        view.add_item(vote_select)
        
        await interaction.response.send_message("Cast your vote:", view=view, ephemeral=True)
    
    async def update_vote_status(self):
        if not self.vote_embed_msg:
            return
        
        vote_counts = {}
        for choice_idx in self.votes.values():
            vote_counts[choice_idx] = vote_counts.get(choice_idx, 0) + 1
        
        status = f"**Votes: {len(self.voters)}/{len(self.campaign_view.party_members)}**\n\n"
        for idx, option in enumerate(self.choice_options):
            count = vote_counts.get(idx, 0)
            status += f"{option.get('emoji', '🎲')} **{option['label']}**: {count} vote(s)\n"
        
        embed = discord.Embed(
            title="🗳️ Party Vote in Progress",
            description=status,
            color=discord.Color.blue()
        )
        
        try:
            await self.vote_embed_msg.edit(embed=embed)
        except:
            pass
    
    async def finalize_vote(self):
        # Count votes
        vote_counts = {}
        for choice_idx in self.votes.values():
            vote_counts[choice_idx] = vote_counts.get(choice_idx, 0) + 1
        
        # Find winner (most votes)
        winning_choice = max(vote_counts.items(), key=lambda x: x[1])[0] if vote_counts else 0
        
        # Disable voting
        for item in self.children:
            item.disabled = True
        
        if self.vote_embed_msg:
            try:
                await self.vote_embed_msg.edit(view=self)
            except:
                pass
        
        # Execute the winning choice
        # We need to create a fake interaction for make_choice
        # Instead, we'll call it directly
        await self.campaign_view.execute_choice(winning_choice)
    
    async def on_timeout(self):
        # If vote times out, use majority or first vote
        if self.votes:
            await self.finalize_vote()
        else:
            # No votes, cancel
            for item in self.children:
                item.disabled = True
            if self.vote_embed_msg:
                try:
                    await self.vote_embed_msg.edit(content="⏰ Vote timed out!", view=self)
                except:
                    pass


class ChoiceSelect(ui.Select):
    """Select menu for story choices"""
    def __init__(self, view, choices: List[Dict]):
        options = [
            discord.SelectOption(
                label=choice['label'][:100],
                description=choice.get('hint', '')[:100],
                value=str(i),
                emoji=choice.get('emoji', '🎲')
            ) for i, choice in enumerate(choices)
        ]
        super().__init__(placeholder="Choose your path...", options=options, custom_id="choice_select")
        self.campaign_view = view
        self.choices_data = choices
    
    async def callback(self, interaction: discord.Interaction):
        # Party mode: check if user is in party
        if self.campaign_view.party_mode:
            if interaction.user.id not in self.campaign_view.party_members:
                await interaction.response.send_message("❌ You're not in this party!", ephemeral=True)
                return
        else:
            # Solo mode: only campaign owner can choose
            if interaction.user.id != self.campaign_view.user_id:
                await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
                return
        
        choice_idx = int(self.values[0])
        
        # Party mode: initiate voting
        if self.campaign_view.party_mode and len(self.campaign_view.party_members) > 1:
            await self.campaign_view.initiate_party_vote(interaction, choice_idx)
        else:
            await self.campaign_view.make_choice(interaction, choice_idx)


class CampaignView(discord.ui.LayoutView):
    """Immersive D&D Campaign View - Narrative God Mode with integrated UI"""
    
    def __init__(self, cog, user_id: int, campaign: dict, character, party_members: List[int] = None, party_mode: bool = False, save_name: str = None):
        self.cog = cog
        self.user_id = user_id
        self.campaign = campaign
        
        # Support both single character (solo) and multiple characters (party)
        if party_mode and isinstance(character, dict) and any(isinstance(v, dict) and 'name' in v for v in character.values()):
            # Party mode: character is dict of {user_id: character_data}
            self.characters = character
            self.character = list(character.values())[0]  # Fallback for compatibility
        else:
            # Solo mode: character is single character dict
            self.character = character
            self.characters = {str(user_id): character}
        
        self.current_scene = 0
        self.choices_made = []
        self.reputation = {}  # Factions
        self.companions = []
        self.story_flags = {}  # Track major decisions
        self.message = None
        self.side_quests_completed = []  # Side quests
        self.random_encounters_seen = []  # Track encounters
        self.scene_count = 0  # Total scenes experienced
        
        # Party system
        self.party_mode = party_mode
        self.party_members = party_members or [user_id]
        self.party_votes = {}  # Track votes for current decision
        self.save_name = save_name  # For save/load
        
        super().__init__(timeout=5400)  # 1.5 hours (1:30h) dla długich kampanii
    
    @classmethod
    async def create(cls, cog, user_id: int, campaign: dict, character, party_members: List[int] = None, party_mode: bool = False, save_name: str = None):
        """Async factory method to create view with built UI"""
        view = cls(cog, user_id, campaign, character, party_members, party_mode, save_name)
        await view._build_ui()
        return view
    
    async def _build_ui(self):
        """Build the UI components for LayoutView (initial creation only)"""
        # Get scene content
        if self.current_scene >= len(self.campaign['scenes']):
            content = self._get_ending_markdown()
        else:
            content = self._get_scene_markdown()
        
        # Create all UI elements with callbacks
        stats_btn = discord.ui.Button(label="📊 Stats", style=discord.ButtonStyle.secondary)
        stats_btn.callback = self.show_stats
        
        save_btn = discord.ui.Button(label="💾 Save", style=discord.ButtonStyle.success)
        save_btn.callback = self.handle_save
        
        load_btn = discord.ui.Button(label="📂 Load", style=discord.ButtonStyle.primary)
        load_btn.callback = self.handle_load
        
        quit_btn = discord.ui.Button(label="🚪 Quit", style=discord.ButtonStyle.danger)
        quit_btn.callback = self.quit_campaign
        
        # Build container items list
        container_items = [
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Get current scene (if not ended)
        if self.current_scene < len(self.campaign['scenes']):
            scene = self.get_current_scene()
            if scene:
                # Add choice select if available
                if scene.get('choices'):
                    choice_select = ChoiceSelect(self, scene['choices'])
                    container_items.append(discord.ui.ActionRow(choice_select))
                    container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
                
                # Add challenge button if available
                if scene.get('challenge'):
                    attempt_btn = discord.ui.Button(label="🎲 Attempt Challenge", style=discord.ButtonStyle.primary)
                    attempt_btn.callback = self.attempt_challenge
                    container_items.append(discord.ui.ActionRow(attempt_btn))
                    container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Always add control buttons
        container_items.append(discord.ui.ActionRow(stats_btn, save_btn, load_btn, quit_btn))
        
        # Create container with all items
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x8B4513),
        )
        
        self.add_item(self.container)
    
    async def refresh(self):
        """Refresh the campaign view after state changes"""
        # Clear ALL old items before rebuilding
        self.clear_items()
        
        # Get scene content
        if self.current_scene >= len(self.campaign['scenes']):
            content = self._get_ending_markdown()
        else:
            scene = self.get_current_scene()
            if not scene:
                # Scene condition not met - show placeholder
                content = "# ⚠️ Scene Unavailable\n\nThe path forward is unclear. Continue your journey..."
            else:
                content = self._get_scene_markdown()
        
        # Create all UI elements with callbacks (fresh instances)
        stats_btn = discord.ui.Button(label="📊 Stats", style=discord.ButtonStyle.secondary)
        stats_btn.callback = self.show_stats
        
        save_btn = discord.ui.Button(label="💾 Save", style=discord.ButtonStyle.success)
        save_btn.callback = self.handle_save
        
        load_btn = discord.ui.Button(label="📂 Load", style=discord.ButtonStyle.primary)
        load_btn.callback = self.handle_load
        
        quit_btn = discord.ui.Button(label="🚪 Quit", style=discord.ButtonStyle.danger)
        quit_btn.callback = self.quit_campaign
        
        # Build container items list
        container_items = [
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
        ]
        
        # Get current scene (if not ended)
        if self.current_scene < len(self.campaign['scenes']):
            scene = self.get_current_scene()
            if scene:
                # Add choice select if available
                if scene.get('choices'):
                    choice_select = ChoiceSelect(self, scene['choices'])
                    container_items.append(discord.ui.ActionRow(choice_select))
                    container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
                
                # Add challenge button if available
                if scene.get('challenge'):
                    attempt_btn = discord.ui.Button(label="🎲 Attempt Challenge", style=discord.ButtonStyle.primary)
                    attempt_btn.callback = self.attempt_challenge
                    container_items.append(discord.ui.ActionRow(attempt_btn))
                    container_items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        
        # Always add control buttons
        container_items.append(discord.ui.ActionRow(stats_btn, save_btn, load_btn, quit_btn))
        
        # Create NEW container with all items
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x8B4513),
        )
        
        self.add_item(self.container)
        
        # Edit message with updated view
        await self.message.edit(view=self)
    
    def _get_scene_markdown(self) -> str:
        """Generate scene content as markdown for TextDisplay"""
        scene = self.get_current_scene()
        if not scene:
            return "# ⚠️ Scene Unavailable\n\nThe path forward is unclear..."
        
        # Build markdown content
        content = f"# 📖 {scene['title']}\n\n"
        content += f"{scene['narrative']}\n\n"
        
        # Character status bar - show all party members in party mode
        if self.party_mode and len(self.characters) > 1:
            content += f"## 👥 Party Members\n\n"
            for user_id, char in self.characters.items():
                hp_bar = self._generate_bar(char['hp'], char['max_hp'], 10, '❤️', '🖤')
                content += f"**⚔️ {char['name']}** the {char['race'].title()} ({char['class'].title()})\n"
                content += f"{hp_bar} **{char['hp']}/{char['max_hp']} HP** | 💰 {char.get('gold', 0)} gold | ✨ Level {char['level']}\n\n"
        else:
            # Solo mode
            char = self.character
            hp_bar = self._generate_bar(char['hp'], char['max_hp'], 10, '❤️', '🖤')
            
            content += f"## ⚔️ {char['name']} the {char['race'].title()}\n"
            content += f"{hp_bar} **{char['hp']}/{char['max_hp']} HP**\n"
            content += f"💰 **{char.get('gold', 0)}** gold | ✨ **Level {char['level']}** {char['class'].title()}\n\n"
        
        # Show active effects
        if scene.get('npc'):
            content += f"**👥 Present:** {scene['npc']}\n"
        
        if scene.get('location'):
            content += f"**📍 Location:** {scene['location']}\n"
        
        if scene.get('npc') or scene.get('location'):
            content += "\n"
        
        # Reputation status
        if self.reputation:
            content += "**🏛️ Reputation:**\n"
            rep_lines = [f"• {faction}: {rep}" for faction, rep in list(self.reputation.items())[:3]]
            content += "\n".join(rep_lines) + "\n\n"
        
        # Scene challenge/conflict
        if scene.get('challenge'):
            challenge = scene['challenge']
            content += f"**🎯 {challenge['type'].title()} Challenge**\n"
            content += f"**DC {challenge['dc']}** - {challenge['description']}\n\n"
        
        # Footer with progress
        progress = f"Scene {self.current_scene + 1}/{len(self.campaign['scenes'])}"
        campaign_name = self.campaign['name']
        content += f"---\n*{progress} | {campaign_name} | Choices shape destiny...*"
        
        return content
    
    def _get_ending_markdown(self) -> str:
        """Generate campaign end content as markdown"""
        # Calculate ending based on story flags and reputation
        ending = self.campaign.get('endings', {}).get('default', 'Your story ends...')
        
        # Check for special endings
        for ending_key, ending_data in self.campaign.get('endings', {}).items():
            if ending_key == 'default':
                continue
            
            conditions_met = True
            for flag, value in ending_data.get('requires', {}).items():
                if self.story_flags.get(flag) != value:
                    conditions_met = False
                    break
            
            if conditions_met:
                ending = ending_data['narrative']
                break
        
        content = "# 🏆 Campaign Complete\n\n"
        content += f"{ending}\n\n"
        
        # Final stats - show all party members in party mode
        if self.party_mode and len(self.characters) > 1:
            content += "## 📊 Final Party\n"
            for user_id, char in self.characters.items():
                content += f"**{char['name']}** - Level {char['level']} {char['class'].title()}\n"
                content += f"HP: {char['hp']}/{char['max_hp']} | Gold: {char.get('gold', 0)}\n\n"
        else:
            # Solo mode
            char = self.character
            content += "## 📊 Final Character\n"
            content += f"**{char['name']}** - Level {char['level']} {char['class'].title()}\n"
            content += f"HP: {char['hp']}/{char['max_hp']} | Gold: {char.get('gold', 0)}\n\n"
        
        # Choices summary
        key_choices = [choice for choice in self.choices_made if 'major' in choice]
        if key_choices:
            content += "## 🔑 Key Decisions\n"
            content += "\n".join([f"• {c['label']}" for c in key_choices[:5]]) + "\n\n"
        
        # Reputation outcome
        if self.reputation:
            content += "## 🏛️ Final Standing\n"
            content += "\n".join([f"• {faction}: **{rep}**" for faction, rep in self.reputation.items()]) + "\n\n"
        
        content += "---\n*Every choice mattered. Every path was real.*"
        
        return content
        
    async def on_timeout(self):
        # Remove session when view times out
        if self.party_mode:
            for member_id in self.party_members:
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            if self.user_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.user_id]
        
        # Disable UI
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    def get_current_scene(self) -> dict:
        """Get current scene with any modifications"""
        # Check if current_scene is within bounds
        if self.current_scene >= len(self.campaign['scenes']):
            return None
        
        scene = self.campaign['scenes'][self.current_scene].copy()
        
        # Dynamic scene modification based on previous choices
        if 'condition' in scene:
            for flag, required_value in scene['condition'].items():
                if self.story_flags.get(flag) != required_value:
                    # Skip this scene if conditions not met
                    return None
        
        return scene
    
    def get_embed(self) -> discord.Embed:
        """Generate immersive scene embed"""
        scene = self.get_current_scene()
        if not scene:
            return discord.Embed(
                title="⚠️ Scene Unavailable",
                description="The path forward is unclear...",
                color=discord.Color.dark_gray()
            )
        
        # Dynamic color based on scene mood
        mood_colors = {
            'dark': discord.Color.dark_gray(),
            'hopeful': discord.Color.green(),
            'tense': discord.Color.red(),
            'mysterious': discord.Color.purple(),
            'peaceful': discord.Color.blue(),
            'chaotic': discord.Color.from_rgb(255, 0, 255),
            'dramatic': discord.Color.gold()
        }
        
        color = mood_colors.get(scene.get('mood', 'mysterious'))
        
        embed = discord.Embed(
            title=f"📖 {scene['title']}",
            description=scene['narrative'],
            color=color
        )
        
        # Character status bar
        char = self.character
        hp_bar = self._generate_bar(char['hp'], char['max_hp'], 10, '❤️', '🖤')
        
        status = f"{hp_bar} **{char['hp']}/{char['max_hp']} HP**\n"
        status += f"💰 **{char.get('gold', 0)}** gold | ✨ **Level {char['level']}** {char['class'].title()}"
        
        embed.add_field(name=f"⚔️ {char['name']} the {char['race'].title()}", value=status, inline=False)
        
        # Show active effects
        if scene.get('npc'):
            embed.add_field(name="👥 Present", value=scene['npc'], inline=True)
        
        if scene.get('location'):
            embed.add_field(name="📍 Location", value=scene['location'], inline=True)
        
        # Reputation status
        if self.reputation:
            rep_text = "\n".join([f"{faction}: {rep}" for faction, rep in list(self.reputation.items())[:3]])
            embed.add_field(name="🏛️ Reputation", value=rep_text, inline=False)
        
        # Scene challenge/conflict
        if scene.get('challenge'):
            challenge = scene['challenge']
            embed.add_field(
                name=f"🎯 {challenge['type'].title()} Challenge",
                value=f"**DC {challenge['dc']}** - {challenge['description']}",
                inline=False
            )
        
        # Footer with progress
        progress = f"Scene {self.current_scene + 1}/{len(self.campaign['scenes'])}"
        campaign_name = self.campaign['name']
        embed.set_footer(text=f"{progress} | {campaign_name} | Choices shape destiny...")
        
        return embed
    
    def get_ending_embed(self) -> discord.Embed:
        """Generate campaign end embed based on choices"""
        # Calculate ending based on story flags and reputation
        ending = self.campaign.get('endings', {}).get('default', 'Your story ends...')
        
        # Check for special endings
        for ending_key, ending_data in self.campaign.get('endings', {}).items():
            if ending_key == 'default':
                continue
            
            conditions_met = True
            for flag, value in ending_data.get('requires', {}).items():
                if self.story_flags.get(flag) != value:
                    conditions_met = False
                    break
            
            if conditions_met:
                ending = ending_data['narrative']
                break
        
        embed = discord.Embed(
            title="🏆 Campaign Complete",
            description=ending,
            color=discord.Color.gold()
        )
        
        # Final stats
        char = self.character
        embed.add_field(
            name="📊 Final Character",
            value=f"**{char['name']}** - Level {char['level']} {char['class'].title()}\n"
                  f"HP: {char['hp']}/{char['max_hp']} | Gold: {char.get('gold', 0)}",
            inline=True
        )
        
        # Choices summary
        key_choices = [choice for choice in self.choices_made if 'major' in choice]
        if key_choices:
            choices_text = "\n".join([f"• {c['label']}" for c in key_choices[:5]])
            embed.add_field(name="🔑 Key Decisions", value=choices_text, inline=False)
        
        # Reputation outcome
        if self.reputation:
            rep_outcome = "\n".join([f"{faction}: **{rep}**" for faction, rep in self.reputation.items()])
            embed.add_field(name="🏛️ Final Standing", value=rep_outcome, inline=False)
        
        embed.set_footer(text="Every choice mattered. Every path was real.")
        
        return embed
    
    def _generate_bar(self, current: int, maximum: int, length: int = 10, filled: str = '█', empty: str = '░') -> str:
        if maximum == 0:
            return empty * length
        filled_length = int((current / maximum) * length)
        return filled * filled_length + empty * (length - filled_length)
    
    def update_ui(self):
        """Update UI based on current scene - now async-aware"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._update_ui_async())
            else:
                loop.run_until_complete(self._update_ui_async())
        except:
            pass
    
    async def _update_ui_async(self):
        """Async version of update_ui"""
        await self.refresh()
    
    async def make_choice(self, interaction: discord.Interaction, choice_idx: int):
        """Process player choice and advance story"""
        await interaction.response.defer()
        
        # Check if campaign already ended
        if self.current_scene >= len(self.campaign['scenes']):
            await interaction.followup.send("✅ Campaign already completed!", ephemeral=True)
            return
        
        scene = self.get_current_scene()
        if not scene:
            await interaction.followup.send("❌ Invalid scene!", ephemeral=True)
            return
            
        choice = scene['choices'][choice_idx]
        
        # Record choice
        self.choices_made.append({
            'scene': self.current_scene,
            'label': choice['label'],
            'major': choice.get('major', False)
        })
        
        # Apply consequences
        await self.apply_consequences(choice.get('consequences', {}), interaction)
        
        # Set story flags
        if choice.get('flag'):
            self.story_flags[choice['flag']] = choice.get('flag_value', True)
        
        # Advance to next scene - MUST have next_scene defined
        if choice.get('next_scene') is not None:
            self.current_scene = choice['next_scene']
        else:
            # No next_scene means this is a dead end or ending
            self.current_scene = len(self.campaign['scenes'])  # Force end
        
        self.scene_count += 1
        
        # Check if campaign ended FIRST (before encounters that might access scenes)
        if self.current_scene >= len(self.campaign['scenes']):
            await self.end_campaign(interaction)
            return
        
        # RANDOM ENCOUNTER CHECK (20% chance between main scenes)
        if random.random() < 0.20 and self.current_scene < len(self.campaign['scenes']) - 1:
            encounter = await self.trigger_random_encounter(interaction)
            if encounter:
                return
        
        # SIDE QUEST CHECK (15% chance)
        if random.random() < 0.15 and self.current_scene < len(self.campaign['scenes']) - 2:
            side_quest = await self.offer_side_quest(interaction)
            if side_quest:
                return
        
        # Update and show next scene
        await self.refresh()
        
        # Send consequence message
        result_text = choice.get('result', f"You chose: **{choice['label']}**")
        await interaction.followup.send(f"✨ {result_text}", ephemeral=True)
    
    async def trigger_random_encounter(self, interaction: discord.Interaction) -> bool:
        """Trigger a random encounter based on campaign type"""
        encounters = self.campaign.get('random_encounters', [])
        if not encounters:
            return False
        
        # Filter out already seen encounters
        available = [e for e in encounters if e['id'] not in self.random_encounters_seen]
        if not available:
            return False
        
        encounter = random.choice(available)
        self.random_encounters_seen.append(encounter['id'])
        self.scene_count += 1
        
        # Create encounter embed
        embed = discord.Embed(
            title=f"⚡ Random Encounter: {encounter['title']}",
            description=encounter['narrative'],
            color=discord.Color.orange()
        )
        
        embed.add_field(name="🎲 Encounter Type", value=encounter.get('type', 'Event'), inline=False)
        
        if encounter.get('challenge'):
            challenge = encounter['challenge']
            stat = challenge['stat']
            
            # In party mode, use the best modifier from all characters
            if self.party_mode and len(self.characters) > 1:
                best_modifier = -999
                best_character = None
                for user_id, char in self.characters.items():
                    char_modifier = char.get(stat, 0)
                    if char_modifier > best_modifier:
                        best_modifier = char_modifier
                        best_character = char
                modifier = best_modifier
                attempting_char = best_character
            else:
                modifier = self.character.get(stat, 0)
                attempting_char = self.character
            
            roll = random.randint(1, 20)
            total = roll + modifier
            dc = challenge['dc']
            success = total >= dc
            
            roll_info = f"**{roll}** + {modifier} ({stat.upper()}) = **{total}** vs DC {dc}"
            if self.party_mode and len(self.characters) > 1:
                roll_info = f"**{attempting_char['name']}** attempts:\n{roll_info}"
            
            embed.add_field(
                name="🎲 Challenge Roll",
                value=roll_info,
                inline=False
            )
            
            if success:
                embed.add_field(name="✅ Success", value=challenge.get('success', 'You overcome the challenge!'), inline=False)
                await self.apply_consequences(challenge.get('success_consequences', {}), interaction)
            else:
                embed.add_field(name="❌ Failure", value=challenge.get('failure', 'The challenge proves too difficult...'), inline=False)
                await self.apply_consequences(challenge.get('failure_consequences', {}), interaction)
        
        await interaction.followup.send(embed=embed)
        
        # Continue to next main scene after encounter
        await self.refresh()
        
        return True
    
    async def offer_side_quest(self, interaction: discord.Interaction) -> bool:
        """Offer an optional side quest"""
        side_quests = self.campaign.get('side_quests', [])
        if not side_quests:
            return False
        
        # Filter uncompleted quests
        available = [q for q in side_quests if q['id'] not in self.side_quests_completed]
        if not available:
            return False
        
        quest = random.choice(available)
        
        # Create quest offer embed
        embed = discord.Embed(
            title=f"📜 Side Quest Available: {quest['title']}",
            description=quest['narrative'] + "\n\n**Accept this side quest?**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="⏱️ Optional", value="You can decline and continue your main journey.", inline=False)
        embed.add_field(name="🎁 Rewards", value=quest.get('rewards_hint', 'Unknown'), inline=False)
        
        # Create accept/decline buttons
        class SideQuestView(ui.View):
            def __init__(self, parent_view, quest_data):
                super().__init__(timeout=60)
                self.parent = parent_view
                self.quest = quest_data
            
            @ui.button(label='Accept Quest', style=discord.ButtonStyle.success, emoji='✅')
            async def accept(self, interaction: discord.Interaction, button: ui.Button):
                # Party mode: any member can accept
                if self.parent.party_mode:
                    if interaction.user.id not in self.parent.party_members:
                        await interaction.response.send_message('❌ Not your party!', ephemeral=True)
                        return
                else:
                    # Solo mode: only owner
                    if interaction.user.id != self.parent.user_id:
                        await interaction.response.send_message('❌ Not your quest!', ephemeral=True)
                        return
                
                await interaction.response.defer()
                await self.parent.start_side_quest(interaction, self.quest)
                self.stop()
            
            @ui.button(label='Decline', style=discord.ButtonStyle.secondary, emoji='❌')
            async def decline(self, interaction: discord.Interaction, button: ui.Button):
                # Party mode: any member can decline
                if self.parent.party_mode:
                    if interaction.user.id not in self.parent.party_members:
                        await interaction.response.send_message('❌ Not your party!', ephemeral=True)
                        return
                else:
                    # Solo mode: only owner
                    if interaction.user.id != self.parent.user_id:
                        await interaction.response.send_message('❌ Not your quest!', ephemeral=True)
                        return
                
                await interaction.response.send_message('You continue on your main path...', ephemeral=True)
                self.stop()
        
        view = SideQuestView(self, quest)
        await interaction.followup.send(embed=embed, view=view)
        
        return True
    
    async def start_side_quest(self, interaction: discord.Interaction, quest: dict):
        """Start a side quest"""
        self.side_quests_completed.append(quest['id'])
        self.scene_count += 1
        
        # Process quest challenge
        if quest.get('challenge'):
            challenge = quest['challenge']
            stat = challenge['stat']
            
            # In party mode, use the best modifier from all characters
            if self.party_mode and len(self.characters) > 1:
                best_modifier = -999
                best_character = None
                for user_id, char in self.characters.items():
                    char_modifier = char.get(stat, 0)
                    if char_modifier > best_modifier:
                        best_modifier = char_modifier
                        best_character = char
                modifier = best_modifier
                attempting_char = best_character
            else:
                modifier = self.character.get(stat, 0)
                attempting_char = self.character
            
            roll = random.randint(1, 20)
            total = roll + modifier
            dc = challenge['dc']
            success = total >= dc
            
            result_embed = discord.Embed(
                title=f"📜 {quest['title']}",
                description=quest['narrative'],
                color=discord.Color.green() if success else discord.Color.red()
            )
            
            roll_info = f"**{roll}** + {modifier} ({stat.upper()}) = **{total}** vs DC {dc}"
            if self.party_mode and len(self.characters) > 1:
                roll_info = f"**{attempting_char['name']}** attempts:\n{roll_info}"
            
            result_embed.add_field(
                name='🎲 Roll',
                value=roll_info,
                inline=False
            )
            
            if success:
                result_embed.add_field(name='✅ Quest Complete!', value=challenge.get('success', 'Victory!'), inline=False)
                await self.apply_consequences(challenge.get('success_consequences', {}), interaction)
            else:
                result_embed.add_field(name='❌ Quest Failed', value=challenge.get('failure', 'Defeat...'), inline=False)
                await self.apply_consequences(challenge.get('failure_consequences', {}), interaction)
            
            await interaction.followup.send(embed=result_embed)
        
        # Return to main campaign
        await self.refresh()
    
    async def apply_consequences(self, consequences: dict, interaction: discord.Interaction):
        """Apply choice consequences"""
        # In party mode, apply consequences to all characters
        if self.party_mode and len(self.characters) > 1:
            for user_id, char in self.characters.items():
                if 'hp_change' in consequences:
                    char['hp'] = max(0, min(char['max_hp'], char['hp'] + consequences['hp_change']))
                
                if 'gold_change' in consequences:
                    char['gold'] = max(0, char.get('gold', 0) + consequences['gold_change'])
                
                if 'xp_gain' in consequences:
                    char['xp'] = char.get('xp', 0) + consequences['xp_gain']
                    # Check level up
                    while char['xp'] >= char['level'] * 100:
                        char['xp'] -= char['level'] * 100
                        char['level'] += 1
                        char['max_hp'] += 10
                        char['hp'] = char['max_hp']
                
                if 'item' in consequences:
                    char.setdefault('inventory', []).append(consequences['item'])
        else:
            # Solo mode - apply to single character
            char = self.character
            
            if 'hp_change' in consequences:
                char['hp'] = max(0, min(char['max_hp'], char['hp'] + consequences['hp_change']))
            
            if 'gold_change' in consequences:
                char['gold'] = max(0, char.get('gold', 0) + consequences['gold_change'])
            
            if 'xp_gain' in consequences:
                char['xp'] = char.get('xp', 0) + consequences['xp_gain']
                # Check level up
                while char['xp'] >= char['level'] * 100:
                    char['xp'] -= char['level'] * 100
                    char['level'] += 1
                    char['max_hp'] += 10
                    char['hp'] = char['max_hp']
            
            if 'item' in consequences:
                char.setdefault('inventory', []).append(consequences['item'])
        
        # Reputation and companions apply to whole party regardless
        if 'reputation' in consequences:
            for faction, change in consequences['reputation'].items():
                self.reputation[faction] = self.reputation.get(faction, 0) + change
        
        if 'companion' in consequences:
            if consequences['companion'] not in self.companions:
                self.companions.append(consequences['companion'])
    
    async def attempt_challenge(self, interaction: discord.Interaction):
        """Attempt a skill challenge with D20 roll"""
        # Party mode: check if user is in party
        if self.party_mode:
            if interaction.user.id not in self.party_members:
                await interaction.response.send_message("❌ You're not in this party!", ephemeral=True)
                return
        else:
            # Solo mode: only owner
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
                return
        
        await interaction.response.defer()
        
        scene = self.get_current_scene()
        challenge = scene.get('challenge')
        
        if not challenge:
            await interaction.followup.send("No challenge here!", ephemeral=True)
            return
        
        # Roll d20 + modifier
        stat = challenge['stat']
        
        # In party mode, use the best modifier from all characters
        if self.party_mode and len(self.characters) > 1:
            best_modifier = -999
            best_character = None
            for user_id, char in self.characters.items():
                char_modifier = char.get(stat, 0)
                if char_modifier > best_modifier:
                    best_modifier = char_modifier
                    best_character = char
            modifier = best_modifier
            attempting_char = best_character
        else:
            modifier = self.character.get(stat, 0)
            attempting_char = self.character
        
        roll = random.randint(1, 20)
        total = roll + modifier
        dc = challenge['dc']
        
        # Determine success
        success = total >= dc
        critical = roll == 20
        fumble = roll == 1
        
        # Create result embed
        result_embed = discord.Embed(
            title=f"🎲 {challenge['type'].title()} Check",
            color=discord.Color.green() if success else discord.Color.red()
        )
        
        # Show who is attempting in party mode
        roll_info = f"🎲 **{roll}** + {modifier} ({stat.upper()}) = **{total}** vs DC {dc}"
        if self.party_mode and len(self.characters) > 1:
            roll_info = f"**{attempting_char['name']}** attempts:\n" + roll_info
        
        result_embed.add_field(
            name="Roll Result",
            value=roll_info,
            inline=False
        )
        
        if critical:
            result_embed.description = "🌟 **CRITICAL SUCCESS!** Beyond expectations!"
            # Extra rewards - apply to all characters in party mode
            if self.party_mode and len(self.characters) > 1:
                for user_id, char in self.characters.items():
                    char['xp'] = char.get('xp', 0) + 50
                    char['gold'] = char.get('gold', 0) + random.randint(20, 50)
            else:
                self.character['xp'] = self.character.get('xp', 0) + 50
                self.character['gold'] = self.character.get('gold', 0) + random.randint(20, 50)
        elif fumble:
            result_embed.description = "💀 **CRITICAL FAILURE!** Disaster strikes!"
            # Extra consequences - apply to all in party mode
            damage = random.randint(5, 15)
            if self.party_mode and len(self.characters) > 1:
                for user_id, char in self.characters.items():
                    char['hp'] -= damage
                result_embed.add_field(name="Consequence", value=f"The party takes {damage} damage each!", inline=False)
            else:
                self.character['hp'] -= damage
                result_embed.add_field(name="Consequence", value=f"You take {damage} damage!", inline=False)
        elif success:
            result_embed.description = challenge.get('success', "✅ You succeed!")
            # Apply success consequences
            await self.apply_consequences(challenge.get('success_consequences', {}), interaction)
        else:
            result_embed.description = challenge.get('failure', "❌ You fail...")
            # Apply failure consequences
            await self.apply_consequences(challenge.get('failure_consequences', {}), interaction)
        
        await interaction.followup.send(embed=result_embed)
        
        # Advance scene after challenge
        self.current_scene += 1
        if self.current_scene >= len(self.campaign['scenes']):
            await self.end_campaign(interaction)
            return
        
        await self.refresh()
    
    async def show_stats(self, interaction: discord.Interaction):
        """Show detailed character stats"""
        # Party mode: any member can view
        if self.party_mode:
            if interaction.user.id not in self.party_members:
                await interaction.response.send_message("❌ You're not in this party!", ephemeral=True)
                return
        else:
            # Solo mode: only owner
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
                return
        
        # In party mode, show all characters
        if self.party_mode and len(self.characters) > 1:
            embed = discord.Embed(
                title=f"📊 Party Character Sheets",
                color=discord.Color.blue()
            )
            
            for user_id, char in self.characters.items():
                # Core stats
                stats = f"💪 STR: {char['str']} | 🏃 DEX: {char['dex']} | 🧠 INT: {char['int']}\n"
                stats += f"🦉 WIS: {char['wis']} | 💬 CHA: {char['cha']}\n"
                stats += f"❤️ HP: {char['hp']}/{char['max_hp']} | ✨ Level: {char['level']} | 💰 Gold: {char.get('gold', 0)}"
                
                embed.add_field(
                    name=f"⚔️ {char['name']} ({char['class'].title()})",
                    value=stats,
                    inline=False
                )
        else:
            # Solo mode - show single character
            char = self.character
            
            embed = discord.Embed(
                title=f"📊 {char['name']} - Character Sheet",
                color=discord.Color.blue()
            )
            
            # Core stats
            stats = f"💪 STR: {char['str']} | 🏃 DEX: {char['dex']} | 🧠 INT: {char['int']}\n"
            stats += f"🦉 WIS: {char['wis']} | 💬 CHA: {char['cha']}"
            embed.add_field(name="Attributes", value=stats, inline=False)
            
            # Status
            status = f"❤️ HP: {char['hp']}/{char['max_hp']}\n"
            status += f"✨ Level: {char['level']} | XP: {char.get('xp', 0)}/{char['level']*100}\n"
            status += f"💰 Gold: {char.get('gold', 0)}"
            embed.add_field(name="Status", value=status, inline=False)
            
            # Inventory
            inventory = char.get('inventory', [])
            if inventory:
                inv_text = "\n".join([f"• {item}" for item in inventory[:10]])
                embed.add_field(name="🎒 Inventory", value=inv_text, inline=False)
        
        # Companions
        if self.companions:
            comp_text = "\n".join([f"• {comp}" for comp in self.companions])
            embed.add_field(name="👥 Companions", value=comp_text, inline=False)
        
        # Journey stats
        journey = f"Scenes: {self.current_scene + 1}/{len(self.campaign['scenes'])}\n"
        journey += f"Choices Made: {len(self.choices_made)}\n"
        journey += f"Campaign: {self.campaign['name']}"
        embed.add_field(name="📖 Journey", value=journey, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def quit_campaign(self, interaction: discord.Interaction):
        """Exit campaign early"""
        # Party mode: only leader can quit
        if self.party_mode:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Only party leader can end the campaign!", ephemeral=True)
                return
        else:
            # Solo mode: only owner
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
                return
        
        await interaction.response.defer()
        
        # Remove session IMMEDIATELY - before anything can fail
        if self.party_mode:
            for member_id in self.party_members:
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            if self.user_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.user_id]
        
        # STOP VIEW
        self.stop()
        
        # Save progress
        if HAS_USER_STORAGE:
            try:
                await user_storage.record_game_state(
                    self.user_id,
                    interaction.user.name,
                    'dnd_campaign',
                    {
                        'character': self.character,
                        'campaign': self.campaign['name'],
                        'scene': self.current_scene,
                        'choices': len(self.choices_made),
                        'timestamp': datetime.utcnow().isoformat() + "Z"
                    }
                )
            except:
                pass
        
        # Create simple quit embed (no view editing)
        quit_embed = discord.Embed(
            title="🚪 Campaign Ended",
            description=f"**{self.character['name']}** has left the adventure.\n\nYour story remains unfinished.",
            color=discord.Color.red()
        )
        
        quit_embed.add_field(
            name="Progress",
            value=f"Scene {self.current_scene + 1}/{len(self.campaign['scenes'])}\n"
                  f"Choices Made: {len(self.choices_made)}",
            inline=False
        )
        
        # Edit original message to show campaign ended (without updating view)
        try:
            await self.message.edit(content="**🚪 Campaign Ended - Session Closed**", embed=None, view=None)
        except Exception as e:
            print(f"Error editing message on quit: {e}")
        
        # Send quit confirmation
        await interaction.followup.send(embed=quit_embed, ephemeral=True)
    
    async def handle_save(self, interaction: discord.Interaction):
        """Handle save button - show modal for save name"""
        # Party mode: only leader can save
        if self.party_mode and interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only party leader can save!", ephemeral=True)
            return
        
        # Solo mode: only owner
        if not self.party_mode and interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
            return
        
        modal = SaveNameModal(self)
        await interaction.response.send_modal(modal)
    
    async def handle_load(self, interaction: discord.Interaction):
        """Handle load button - show list of saves"""
        # Party mode: only leader can load
        if self.party_mode and interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only party leader can load!", ephemeral=True)
            return
        
        # Solo mode: only owner
        if not self.party_mode and interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your story!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Load saves
        if not os.path.exists(SAVE_FILE):
            await interaction.followup.send("❌ No saved campaigns found!", ephemeral=True)
            return
        
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                saves = json.load(f)
        except:
            await interaction.followup.send("❌ Error loading saves!", ephemeral=True)
            return
        
        user_saves = saves.get(str(self.user_id), {})
        
        if not user_saves:
            await interaction.followup.send("❌ You don't have any saved campaigns!", ephemeral=True)
            return
        
        # Show saves list
        view = LoadSaveView(self.cog, self.user_id, user_saves, interaction.channel)
        
        embed = discord.Embed(
            title="📂 Load Campaign",
            description=f"Found {len(user_saves)} save(s)\n\nSelect a save to load:",
            color=discord.Color.blue()
        )
        
        for save_name, save_data in list(user_saves.items())[:10]:
            char = save_data['character']
            embed.add_field(
                name=f"💾 {save_name}",
                value=f"**{save_data['campaign_name']}**\n"
                      f"{char['name']} (Lvl {char['level']} {char['class'].title()})\n"
                      f"Scene: {save_data['current_scene'] + 1}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def initiate_party_vote(self, interaction: discord.Interaction, choice_idx: int):
        """Start party voting process for a decision"""
        scene = self.get_current_scene()
        choices = scene.get('choices', [])
        
        # Create voting view
        vote_view = PartyVotingView(self, choices, timeout=60)
        
        # Send vote announcement
        vote_embed = discord.Embed(
            title="🗳️ Party Vote Started",
            description=f"**{interaction.user.display_name}** initiated a vote!\n\nAll party members, cast your votes!",
            color=discord.Color.blue()
        )
        
        vote_msg = await interaction.response.send_message(embed=vote_embed, view=vote_view)
        vote_view.vote_embed_msg = await interaction.original_response()
    
    async def execute_choice(self, choice_idx: int):
        """Execute a choice without interaction (used for party voting)"""
        scene = self.get_current_scene()
        choice = scene['choices'][choice_idx]
        
        # Record choice
        self.choices_made.append({
            'scene': self.current_scene,
            'label': choice['label'],
            'major': choice.get('major', False)
        })
        
        # Apply consequences
        # Since we don't have interaction, we'll apply silently
        consequences = choice.get('consequences', {})
        char = self.character
        
        if 'hp_change' in consequences:
            char['hp'] = max(0, min(char['max_hp'], char['hp'] + consequences['hp_change']))
        
        if 'gold_change' in consequences:
            char['gold'] = max(0, char.get('gold', 0) + consequences['gold_change'])
        
        if 'xp_gain' in consequences:
            char['xp'] = char.get('xp', 0) + consequences['xp_gain']
            while char['xp'] >= char['level'] * 100:
                char['xp'] -= char['level'] * 100
                char['level'] += 1
                char['max_hp'] += 10
                char['hp'] = char['max_hp']
        
        if 'reputation' in consequences:
            for faction, change in consequences['reputation'].items():
                self.reputation[faction] = self.reputation.get(faction, 0) + change
        
        if 'item' in consequences:
            char.setdefault('inventory', []).append(consequences['item'])
        
        if 'companion' in consequences:
            if consequences['companion'] not in self.companions:
                self.companions.append(consequences['companion'])
        
        # Set story flags
        if choice.get('flag'):
            self.story_flags[choice['flag']] = choice.get('flag_value', True)
        
        # Advance to next scene
        if choice.get('next_scene') is not None:
            self.current_scene = choice['next_scene']
        else:
            self.current_scene += 1
        
        self.scene_count += 1
        
        # Check if campaign ended
        if self.current_scene >= len(self.campaign['scenes']):
            # Send ending to channel
            await self.refresh()  # Build ending UI
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
            return
        
        # Update and show next scene
        await self.refresh()
        
        # Send result to channel
        result_text = choice.get('result', f"Party chose: **{choice['label']}**")
        try:
            await self.message.channel.send(f"✨ {result_text}")
        except:
            pass
    
    def save_campaign(self) -> dict:
        """Save campaign state to dict"""
        return {
            'user_id': self.user_id,
            'character': self.character,  # Keep for backward compatibility
            'characters': self.characters,  # NEW: All characters in party mode
            'campaign_name': self.campaign['name'],
            'campaign_type': self.campaign['type'],
            'current_scene': self.current_scene,
            'choices_made': self.choices_made,
            'reputation': self.reputation,
            'companions': self.companions,
            'story_flags': self.story_flags,
            'side_quests_completed': self.side_quests_completed,
            'random_encounters_seen': self.random_encounters_seen,
            'scene_count': self.scene_count,
            'party_members': self.party_members,
            'party_mode': self.party_mode,
            'save_name': self.save_name,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def load_campaign_data(save_data: dict, cog, campaign_generator) -> 'CampaignView':
        """Load campaign from saved data"""
        # Regenerate campaign
        # For party mode with multiple characters, use first character's class
        if 'characters' in save_data and len(save_data['characters']) > 1:
            first_char = list(save_data['characters'].values())[0]
            campaign = campaign_generator(save_data['campaign_type'], first_char['class'])
            characters = save_data['characters']
        else:
            campaign = campaign_generator(save_data['campaign_type'], save_data['character']['class'])
            characters = save_data.get('characters', {str(save_data['user_id']): save_data['character']})
        
        # Create view with saved state using async factory
        view = await CampaignView.create(
            cog=cog,
            user_id=save_data['user_id'],
            campaign=campaign,
            character=characters,  # Pass all characters
            party_members=save_data.get('party_members', [save_data['user_id']]),
            party_mode=save_data.get('party_mode', False),
            save_name=save_data.get('save_name')
        )
        
        # Restore state
        view.current_scene = save_data['current_scene']
        view.choices_made = save_data['choices_made']
        view.reputation = save_data['reputation']
        view.companions = save_data['companions']
        view.story_flags = save_data['story_flags']
        view.side_quests_completed = save_data['side_quests_completed']
        view.random_encounters_seen = save_data['random_encounters_seen']
        view.scene_count = save_data['scene_count']
        
        # Rebuild UI with restored state
        await view._build_ui()
        
        return view
    
    async def end_campaign(self, interaction: discord.Interaction):
        """Campaign completion"""
        # Save completion
        if HAS_USER_STORAGE:
            try:
                await user_storage.record_game_state(
                    self.user_id,
                    interaction.user.name,
                    'dnd_complete',
                    {
                        'character': self.character,
                        'campaign': self.campaign['name'],
                        'choices': self.choices_made,
                        'flags': self.story_flags,
                        'reputation': self.reputation,
                        'timestamp': datetime.utcnow().isoformat() + "Z"
                    }
                )
            except:
                pass
        
        # Rebuild UI with disabled buttons
        self.clear_items()
        
        # Get ending content
        content = self._get_ending_markdown()
        
        # Create disabled buttons
        stats_btn = discord.ui.Button(label="📊 Stats", style=discord.ButtonStyle.secondary, disabled=True)
        save_btn = discord.ui.Button(label="💾 Save", style=discord.ButtonStyle.success, disabled=True)
        load_btn = discord.ui.Button(label="📂 Load", style=discord.ButtonStyle.primary, disabled=True)
        quit_btn = discord.ui.Button(label="🚪 Quit", style=discord.ButtonStyle.danger, disabled=True)
        
        container_items = [
            discord.ui.TextDisplay(content=content),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(stats_btn, save_btn, load_btn, quit_btn),
        ]
        
        self.container = discord.ui.Container(
            *container_items,
            accent_colour=discord.Colour(0x8B4513),
        )
        
        self.add_item(self.container)
        
        # Remove session
        if self.party_mode:
            for member_id in self.party_members:
                if member_id in self.cog.active_sessions:
                    del self.cog.active_sessions[member_id]
        else:
            if self.user_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.user_id]
        
        # Stop the view (prevent timeout issues)
        self.stop()
        
        # Simple completion message
        completion_embed = discord.Embed(
            title="🏆 Campaign Complete!",
            description=f"**{self.character['name']}'s** journey in **{self.campaign['name']}** has ended.\n"
                        f"*Every choice mattered. Every path was real.*",
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=completion_embed, ephemeral=True)
        await self.message.edit(view=self)


class DND(commands.Cog):
    """D&D 5e - Narrative God Mode | Every choice matters. Every path is real."""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        
        # Character archetypes
        self.classes = {
            "warrior": {"hp": 60, "str": 3, "dex": 1, "int": 0, "wis": 1, "cha": 0},
            "mage": {"hp": 35, "str": 0, "dex": 1, "int": 4, "wis": 2, "cha": 1},
            "rogue": {"hp": 40, "str": 1, "dex": 4, "int": 1, "wis": 1, "cha": 1},
            "cleric": {"hp": 50, "str": 1, "dex": 0, "int": 1, "wis": 4, "cha": 2},
            "ranger": {"hp": 45, "str": 2, "dex": 3, "int": 0, "wis": 2, "cha": 1},
            "paladin": {"hp": 55, "str": 2, "dex": 0, "int": 0, "wis": 2, "cha": 3}
        }
        
        self.races = {
            "human": {"hp": 5, "str": 0, "dex": 0, "int": 0, "wis": 0, "cha": 1},
            "elf": {"hp": 0, "str": 0, "dex": 2, "int": 1, "wis": 0, "cha": 0},
            "dwarf": {"hp": 10, "str": 2, "dex": 0, "int": 0, "wis": 1, "cha": 0},
            "halfling": {"hp": 0, "str": 0, "dex": 2, "int": 0, "wis": 0, "cha": 1},
            "orc": {"hp": 15, "str": 3, "dex": 0, "int": -1, "wis": 0, "cha": -1},
            "tiefling": {"hp": 5, "str": 0, "dex": 0, "int": 1, "wis": 0, "cha": 2},
            "dragonborn": {"hp": 10, "str": 2, "dex": 0, "int": 0, "wis": 0, "cha": 1}
        }
    
    def generate_character(self, user_id: int, username: str, char_class: str, race: str) -> dict:
        """Generate hero"""
        class_data = self.classes[char_class]
        race_data = self.races[race]
        
        base_stats = {stat: random.randint(8, 14) for stat in ['str', 'dex', 'int', 'wis', 'cha']}
        
        return {
            "user_id": user_id,
            "name": username,
            "class": char_class,
            "race": race,
            "level": 1,
            "xp": 0,
            "hp": class_data["hp"] + race_data["hp"],
            "max_hp": class_data["hp"] + race_data["hp"],
            "str": base_stats['str'] + class_data['str'] + race_data['str'],
            "dex": base_stats['dex'] + class_data['dex'] + race_data['dex'],
            "int": base_stats['int'] + class_data['int'] + race_data['int'],
            "wis": base_stats['wis'] + class_data['wis'] + race_data['wis'],
            "cha": base_stats['cha'] + class_data['cha'] + race_data['cha'],
            "gold": 50,
            "inventory": ["🗡️ Starting Weapon", "🧪 Health Potion"],
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def generate_campaign(self, campaign_type: str, char_class: str = None) -> dict:
        """Generate full campaign with branching paths - THE GOD MODE"""
        
        campaigns = {
            "Court Intrigue": self._gen_court_intrigue(char_class),
            "World Explorer": self._gen_world_explorer(char_class),
            "War Campaign": self._gen_war_campaign(char_class),
            "Mystery Detective": self._gen_mystery_detective(char_class),
            "Wilderness Survival": self._gen_wilderness_survival(char_class),
            "Character Drama": self._gen_character_drama(char_class),
            "Trade Empire": self._gen_trade_empire(char_class),
            "Chaotic Mayhem": self._gen_chaotic_mayhem(char_class)
        }
        
        return campaigns.get(campaign_type, campaigns["Chaotic Mayhem"])
    
    def _gen_court_intrigue(self, char_class: str = None) -> dict:
        """Political intrigue campaign - CHA focused - BRANCHING 18 scenes"""
        return {
            "name": "The Throne of Lies",
            "type": "Political Intrigue",
            "scenes": [
                # SCENA 0 - START
                {
                    "title": "The Royal Summons",
                    "narrative": "The gilded halls of Castle Ravenmoor shimmer with candlelight as you're escorted before Queen Elara. Her eyes, cold as winter steel, assess you.\n\n\"*You've been brought here for a purpose,*\" she says, voice like silk hiding daggers. \"*My court is poisoned with traitors. Find them... or become one.*\"\n\nThree factions vie for control: the Noble Houses, the Shadow Guild, and the Church of Light. Each holds secrets. Each could be your ally... or your doom.",
                    "location": "Royal Throne Room",
                    "npc": "Queen Elara Ravenmoor",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "\"I serve the Crown faithfully, Your Majesty.\"",
                            "emoji": "👑",
                            "hint": "Pledge loyalty to the Queen (CHA)",
                            "result": "The Queen smiles, though it doesn't reach her eyes. \"*Good. Your first task: attend tonight's masquerade. Watch everyone.*\"",
                            "consequences": {"reputation": {"Crown": 10}, "gold_change": 25},
                            "flag": "loyal_to_crown",
                            "next_scene": 1,  # Crown path
                            "major": True
                        },
                        {
                            "label": "\"I work for gold, not crowns.\"",
                            "emoji": "💰",
                            "hint": "Remain independent (INT)",
                            "result": "The Queen's eyes narrow, but she nods. \"*A mercenary. Very well. 100 gold now, 500 when you deliver results.*\"",
                            "consequences": {"gold_change": 100},
                            "flag": "mercenary",
                            "next_scene": 2,  # Mercenary path
                            "major": True
                        },
                        {
                            "label": "\"Someone hired me to WATCH you, Your Majesty.\"",
                            "emoji": "🎭",
                            "hint": "Reveal you're a double agent (Bold)",
                            "result": "Silence falls. Guards tense. Then... the Queen laughs. \"*Bold. I like you. Play both sides if you wish, but betray me and you'll wish you'd never been born.*\"",
                            "consequences": {"reputation": {"Crown": -5, "Shadow Guild": 15}, "gold_change": 50},
                            "flag": "double_agent",
                            "next_scene": 3,  # Shadow path
                            "major": True
                        }
                    ]
                },
                # SCENA 1 - Crown Loyalty Path
                {
                    "title": "The Masquerade - Crown's Watchful Eye",
                    "narrative": "The ballroom swirls with masked nobles. As the Queen's agent, you must identify threats.\n\n**Lord Casimir** whispers with servants near the wine. His mask: a golden sun.\n**Lady Seraphine** stands alone by the balcony, watching. Her mask: a silver moon.\n**High Priest Valorin** moves through shadows. His mask: a white dove.\n\nThe Queen expects results.",
                    "location": "Royal Ballroom - Masquerade",
                    "mood": "mysterious",
                    "choices": [
                        {
                            "label": "Investigate Lord Casimir (Noble Houses)",
                            "emoji": "☀️",
                            "hint": "Follow the nobleman",
                            "result": "You overhear Casimir plotting with merchants. Economic sabotage?",
                            "consequences": {"reputation": {"Noble Houses": -10, "Crown": 5}},
                            "flag": "casimir_suspect",
                            "next_scene": 4
                        },
                        {
                            "label": "Shadow Lady Seraphine (Shadow Guild)",
                            "emoji": "🌙",
                            "hint": "Track the mysterious woman",
                            "result": "She knows you're following. She WANTS you to follow. It's a test.",
                            "consequences": {"reputation": {"Shadow Guild": 10}},
                            "flag": "seraphine_contact",
                            "next_scene": 5
                        },
                        {
                            "label": "Confront Priest Valorin (Church)",
                            "emoji": "🕊️",
                            "hint": "Question the priest",
                            "result": "The priest reveals: 'The Queen herself is the darkness.' Religious coup incoming?",
                            "consequences": {"reputation": {"Church": 15, "Crown": -5}},
                            "flag": "church_conspiracy",
                            "next_scene": 6
                        }
                    ]
                },
                # SCENA 2 - Mercenary Path
                {
                    "title": "The Highest Bidder",
                    "narrative": "As a mercenary, you're approached by THREE factions, each offering contracts.\n\n**Lord Casimir** offers 500 gold to 'protect Noble interests.'\n**Lady Seraphine** whispers: '800 gold to eliminate a target.'\n**Priest Valorin**: '300 gold and salvation to spy on heretics.'\n\nWho pays best?",
                    "location": "Tavern - Midnight Meeting",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "Accept Casimir's 500 gold (Nobles)",
                            "emoji": "💰",
                            "result": "You're now a Noble enforcer. Protection racket begins.",
                            "consequences": {"gold_change": 500, "reputation": {"Noble Houses": 20}},
                            "next_scene": 7
                        },
                        {
                            "label": "Accept Seraphine's 800 gold (Assassin)",
                            "emoji": "🗡️",
                            "result": "Your target: a royal advisor. Murder for hire. Are you sure?",
                            "consequences": {"gold_change": 800, "reputation": {"Shadow Guild": 30}},
                            "flag": "assassin_hired",
                            "next_scene": 8
                        },
                        {
                            "label": "Accept all three contracts (GREED)",
                            "emoji": "🤑",
                            "result": "You're playing ALL sides. 1600 gold! But one will discover your betrayal...",
                            "consequences": {"gold_change": 1600},
                            "flag": "triple_agent",
                            "next_scene": 9
                        }
                    ]
                },
                # SCENA 3 - Shadow Guild Path
                {
                    "title": "Initiation Into Shadows",
                    "narrative": "Lady Seraphine leads you through secret tunnels beneath the castle.\n\n\"*The Shadow Guild controls this kingdom from below,*\" she says. \"*Prove yourself worthy.*\"\n\nShe hands you a lock pick and a list of three targets:\n\n1. **Steal** the Queen's private letters\n2. **Kill** a traitorous guild member\n3. **Seduce** a royal guard for information\n\nChoose your initiation trial.",
                    "location": "Shadow Guild - Underground",
                    "npc": "Lady Seraphine",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Steal the Queen's letters",
                            "emoji": "📜",
                            "hint": "Stealth mission",
                            "result": "You infiltrate the royal chambers. The letters reveal... the Queen's affair with Casimir!",
                            "consequences": {"reputation": {"Shadow Guild": 25}, "item": "📜 Blackmail Letters"},
                            "flag": "queen_affair_discovered",
                            "next_scene": 10
                        },
                        {
                            "label": "Kill the traitor",
                            "emoji": "💀",
                            "hint": "Assassination",
                            "result": "Your first kill. The blood won't wash off your hands. But you're IN.",
                            "consequences": {"reputation": {"Shadow Guild": 40}, "xp_gain": 100},
                            "flag": "guild_killer",
                            "next_scene": 11
                        },
                        {
                            "label": "Seduce the guard",
                            "emoji": "💋",
                            "hint": "Charisma challenge",
                            "result": "The guard falls for you. You learn the castle's patrol schedules. And maybe... you actually care?",
                            "consequences": {"reputation": {"Shadow Guild": 20}},
                            "flag": "guard_romance",
                            "next_scene": 12
                        }
                    ]
                },
                # SCENA 4 - Casimir Investigation
                {
                    "title": "The Noble Conspiracy",
                    "narrative": "Following Casimir leads you to a secret meeting. Twelve noble lords gather.\n\n\"*The Queen is weak,*\" Casimir declares. \"*We must act before she destroys the realm.*\"\n\nThey're planning a coup. You could:\n- **Report this to the Queen** (Loyalty)\n- **Join the nobles** (Power)\n- **Blackmail them all** (Profit)",
                    "location": "Secret Noble Meeting",
                    "mood": "tense",
                    "challenge": {
                        "type": "Stealth",
                        "stat": "dex",
                        "dc": 14,
                        "description": "Eavesdrop without being caught",
                        "success": "You hear EVERYTHING. Names, dates, plans. Leverage acquired.",
                        "failure": "They spot you! Guards chase you through the castle!",
                        "success_consequences": {"xp_gain": 150, "reputation": {"Crown": 20}},
                        "failure_consequences": {"hp_change": -25, "reputation": {"Noble Houses": -30}},
                        "next_scene": 13
                    }
                },
                # SCENA 5 - Seraphine Test
                {
                    "title": "The Shadow's Trial",
                    "narrative": "Seraphine leads you to a rooftop. Below, two men meet in an alley.\n\n\"*One is a spy,*\" she says coldly. \"*One is innocent. Kill the spy. You have 60 seconds to decide.*\"\n\nShe hands you a crossbow.\n\nBoth men LOOK guilty. Both COULD be innocent. **Choose. NOW.**",
                    "location": "Rooftop - Assassination Test",
                    "npc": "Lady Seraphine",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "Shoot the left target",
                            "emoji": "🎯",
                            "hint": "Trust your instinct",
                            "result": "He falls. Seraphine nods. 'Correct. You have the killer's intuition.' (But was he REALLY guilty?)",
                            "consequences": {"reputation": {"Shadow Guild": 30}, "xp_gain": 100},
                            "flag": "passed_test",
                            "next_scene": 14
                        },
                        {
                            "label": "Shoot the right target",
                            "emoji": "🎯",
                            "hint": "Trust your instinct",
                            "result": "He falls. Seraphine frowns. 'Wrong target. But... you pulled the trigger. That's what matters.'",
                            "consequences": {"reputation": {"Shadow Guild": 15}, "xp_gain": 75},
                            "flag": "failed_test",
                            "next_scene": 14
                        },
                        {
                            "label": "Refuse to shoot",
                            "emoji": "❌",
                            "hint": "I won't be a murderer",
                            "result": "Seraphine shoots BOTH. 'You failed. Both were innocent. I needed to see if you'd kill. You won't survive here.'",
                            "consequences": {"reputation": {"Shadow Guild": -50}},
                            "flag": "refused_kill",
                            "next_scene": 15
                        }
                    ]
                },
                # SCENA 6 - Church Conspiracy
                {
                    "title": "The Church's Holy War",
                    "narrative": "Priest Valorin reveals the truth in the cathedral's crypt.\n\n\"*The Queen practices dark magic,*\" he whispers. \"*She's made pacts with demons. The Church must act.*\"\n\nHe shows you evidence: ritual circles, blood sacrifices, summoning texts.\n\n\"*Help us purge this evil,*\" he says. \"*Or burn with her.*\"",
                    "location": "Cathedral Crypt",
                    "npc": "High Priest Valorin",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Join the Church's inquisition",
                            "emoji": "✝️",
                            "result": "You're now a holy inquisitor. The purge begins. Magic users hang in the streets.",
                            "consequences": {"reputation": {"Church": 50, "Crown": -40}},
                            "flag": "inquisitor",
                            "next_scene": 16
                        },
                        {
                            "label": "Warn the Queen of the plot",
                            "emoji": "👑",
                            "result": "You rush to warn the Queen. She thanks you... then reveals she IS a witch. 'Join me, or die.'",
                            "consequences": {"reputation": {"Crown": 30, "Church": -60}},
                            "flag": "witch_ally",
                            "next_scene": 17
                        },
                        {
                            "label": "Blackmail BOTH sides",
                            "emoji": "💰",
                            "result": "You have evidence on the Church AND the Queen. Time to get RICH off their war.",
                            "consequences": {"gold_change": 1000},
                            "flag": "profiteer",
                            "next_scene": 18
                        }
                    ]
                },
                # SCENY 7-18 - Dalsze rozgałęzienia i zakończenia
                # SCENA 7 - Noble Enforcer Path
                {
                    "title": "Enforcing Noble Will",
                    "narrative": "As Casimir's enforcer, you 'convince' merchants to pay protection fees. Violence is implied. Sometimes used.\n\nOne merchant refuses: 'I'd rather die than submit!'\n\nCasimir watches. This is your test.",
                    "location": "Market District",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "Break his legs (Violence)",
                            "emoji": "💥",
                            "result": "The merchant screams. Others pay immediately. You're feared now.",
                            "consequences": {"reputation": {"Noble Houses": 30}, "gold_change": 300},
                            "next_scene": 13
                        },
                        {
                            "label": "Let him go (Mercy)",
                            "emoji": "🤝",
                            "result": "Casimir is displeased. 'Soft. But... strategic. Fear AND mercy can coexist.'",
                            "consequences": {"reputation": {"Noble Houses": 10}},
                            "next_scene": 13
                        }
                    ]
                },
                # SCENA 8 - Assassination Contract
                {
                    "title": "The Assassination",
                    "narrative": "Your target: Royal Advisor Matthias. He knows too much about Shadow Guild operations.\n\nYou have poison, blade, and opportunity. He's alone in his study.\n\nBut... you overhear him praying for his daughter's safety. He's a FATHER.",
                    "location": "Advisor's Study - Night",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Complete the contract (Kill)",
                            "emoji": "💀",
                            "result": "He dies quietly. 800 gold earned. Your soul feels heavier.",
                            "consequences": {"gold_change": 800, "reputation": {"Shadow Guild": 40}, "xp_gain": 150},
                            "flag": "contract_killer",
                            "next_scene": 14
                        },
                        {
                            "label": "Spare him and warn him",
                            "emoji": "🛡️",
                            "result": "He flees the kingdom with his daughter. The Guild is FURIOUS. There will be consequences.",
                            "consequences": {"reputation": {"Shadow Guild": -50, "Crown": 20}},
                            "next_scene": 15
                        }
                    ]
                },
                # SCENA 9 - Triple Agent Chaos
                {
                    "title": "Web of Lies Unravels",
                    "narrative": "You're working for the Nobles, Shadow Guild, AND the Church simultaneously.\n\nIt was going well... until they ALL scheduled meetings at the SAME TIME.\n\nPanic. You can only attend ONE. The other two will discover your betrayal.",
                    "location": "Three locations at once",
                    "mood": "chaotic",
                    "choices": [
                        {
                            "label": "Prioritize the Nobles (Gold)",
                            "emoji": "💰",
                            "result": "Guild and Church mark you for death. But you keep the 1600 gold!\n\nYou flee the capital. Rich but hunted.",
                            "consequences": {"reputation": {"Shadow Guild": -100, "Church": -100}, "gold_change": 500},
                            "flag": "ending_exile_rich",
                            "next_scene": 99
                        },
                        {
                            "label": "Confess to everyone (Honesty)",
                            "emoji": "🙏",
                            "result": "You gather all three factions and confess. Shocked silence. Then... they HIRE you as a neutral mediator. Respect.",
                            "consequences": {"reputation": {"Noble Houses": 20, "Shadow Guild": 20, "Church": 20}, "xp_gain": 300},
                            "next_scene": 18
                        },
                        {
                            "label": "Fake your death (Escape)",
                            "emoji": "💀",
                            "result": "You stage an elaborate assassination. They all think you're dead. You vanish. New identity. Freedom.",
                            "flag": "ending_vanished",
                            "next_scene": 99
                        }
                    ]
                },
                # SCENA 10 - Blackmail with Letters
                {
                    "title": "The Blackmail Game",
                    "narrative": "You have the Queen's secret affair letters. With Casimir, no less!\n\nLady Seraphine grins: 'Use them wisely. Blackmail the Queen? Expose Casimir? Or... sell them to the Church?'",
                    "location": "Shadow Guild HQ",
                    "mood": "mysterious",
                    "choices": [
                        {
                            "label": "Blackmail the Queen",
                            "emoji": "👑",
                            "result": "She pays 2000 gold for silence. And marks you for death later.",
                            "consequences": {"gold_change": 2000, "reputation": {"Crown": -80}},
                            "next_scene": 18
                        },
                        {
                            "label": "Expose Casimir publicly",
                            "emoji": "📢",
                            "result": "Scandal! Casimir is ruined. The Noble faction collapses. Chaos in the court.",
                            "consequences": {"reputation": {"Noble Houses": -100, "Shadow Guild": 50}, "xp_gain": 200},
                            "next_scene": 17
                        }
                    ]
                },
                # SCENA 11 - Guild Killer Path
                {
                    "title": "The Assassin's Creed",
                    "narrative": "Your first kill opens the door. Seraphine trains you personally.\n\nPoisoned blades. Silent takedowns. Shadow magic. You become DEATH itself.\n\n'Your final test,' she says. 'Kill ME.'",
                    "location": "Training Grounds - Shadow Guild",
                    "npc": "Lady Seraphine",
                    "mood": "dramatic",
                    "challenge": {
                        "type": "Combat",
                        "stat": "dex",
                        "dc": 18,
                        "description": "Duel your mentor",
                        "success": "You WIN. Seraphine yields, impressed. 'You're ready.' You're now the Guild's Master Assassin.",
                        "failure": "She disarms you effortlessly. 'Not yet. Train harder.'",
                        "success_consequences": {"reputation": {"Shadow Guild": 100}, "xp_gain": 400, "item": "🗡️ Master's Blade"},
                        "failure_consequences": {"reputation": {"Shadow Guild": 40}, "hp_change": -20},
                        "next_scene": 18
                    }
                },
                # SCENA 12 - Guard Romance
                {
                    "title": "Love in the Shadows",
                    "narrative": "The guard—Ser Aldrik—falls for you. Or do you fall for him?\n\nHe's loyal to the Crown. You're loyal to the Guild. This romance is DOOMED.\n\n'Run away with me,' he pleads. 'Leave this life behind.'",
                    "location": "Castle Gardens - Moonlight",
                    "npc": "Ser Aldrik",
                    "mood": "peaceful",
                    "choices": [
                        {
                            "label": "Run away together (Love)",
                            "emoji": "❤️",
                            "result": "You abandon the Guild. Seraphine swears vengeance. But you're FREE. Together.",
                            "flag": "ending_love",
                            "consequences": {"reputation": {"Shadow Guild": -100}},
                            "next_scene": 99
                        },
                        {
                            "label": "Betray him (Duty)",
                            "emoji": "💔",
                            "result": "You use him for information, then disappear. His heartbreak haunts you.",
                            "consequences": {"reputation": {"Shadow Guild": 60}, "xp_gain": 150},
                            "next_scene": 18
                        },
                        {
                            "label": "Kill him (Orders)",
                            "emoji": "💀",
                            "result": "The Guild ordered his death. You pull the trigger. The light dies in his eyes. And in yours.",
                            "consequences": {"reputation": {"Shadow Guild": 80}, "xp_gain": 200},
                            "flag": "heartless_killer",
                            "next_scene": 18
                        }
                    ]
                },
                # SCENA 13 - Coup Revelation
                {
                    "title": "The Coup Unfolds",
                    "narrative": "Armed with knowledge of the Noble conspiracy, you must act.\n\nThe coup happens TONIGHT. Casimir's forces will storm the palace at midnight.\n\nYou have hours to decide your allegiance.",
                    "location": "Your Chambers - Evening",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "Defend the Queen",
                            "emoji": "👑",
                            "result": "You rally the royal guards. The coup FAILS. Casimir hangs. The Queen rewards you with a lordship.",
                            "consequences": {"reputation": {"Crown": 100, "Noble Houses": -100}, "gold_change": 3000, "xp_gain": 500},
                            "flag": "ending_loyal_lord",
                            "next_scene": 99
                        },
                        {
                            "label": "Join the coup",
                            "emoji": "⚔️",
                            "result": "You open the gates. The Queen is captured. Casimir takes the throne. You're made Royal Enforcer.",
                            "consequences": {"reputation": {"Noble Houses": 100, "Crown": -100}, "gold_change": 2000, "xp_gain": 400},
                            "flag": "ending_usurper",
                            "next_scene": 99
                        },
                        {
                            "label": "Let them fight, then seize power",
                            "emoji": "👁️",
                            "result": "Both sides destroy each other. In the chaos, YOU take the throne. The Opportunist King.",
                            "consequences": {"xp_gain": 600, "gold_change": 5000},
                            "flag": "ending_opportunist_king",
                            "next_scene": 99
                        }
                    ]
                },
                # SCENA 14 - Master Assassin
                {
                    "title": "The Guild's Finest",
                    "narrative": "You're now a legendary assassin. Contracts pour in.\n\nBut one contract makes you pause: 'Kill Lady Seraphine. Payment: 10,000 gold.'\n\nSomeone wants your mentor DEAD.",
                    "location": "Shadow Guild HQ",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Accept the contract",
                            "emoji": "💰",
                            "result": "You ambush Seraphine. The fight is legendary. She dies by your hand. You're now Guild Master.",
                            "consequences": {"gold_change": 10000, "reputation": {"Shadow Guild": 150}, "xp_gain": 600},
                            "flag": "ending_guild_master",
                            "next_scene": 99
                        },
                        {
                            "label": "Warn Seraphine",
                            "emoji": "🛡️",
                            "result": "Together, you hunt down whoever ordered the hit. It was... Casimir. You kill him together.",
                            "consequences": {"reputation": {"Shadow Guild": 100, "Noble Houses": -80}, "xp_gain": 400},
                            "next_scene": 18
                        }
                    ]
                },
                # SCENA 15 - Outcast Path
                {
                    "title": "Marked for Death",
                    "narrative": "The Shadow Guild hunts you. Every shadow hides a blade.\n\nYou failed their test. Showed mercy. Now you pay the price.\n\nYou can RUN... or FIGHT BACK.",
                    "location": "Fleeing Through Streets",
                    "mood": "chaotic",
                    "challenge": {
                        "type": "Survival",
                        "stat": "dex",
                        "dc": 16,
                        "description": "Escape the assassins",
                        "success": "You escape the capital and find refuge in a monastery. Peace, at last.",
                        "failure": "They corner you. You fight desperately. Survive, but barely.",
                        "success_consequences": {"xp_gain": 300},
                        "failure_consequences": {"hp_change": -40},
                        "next_scene": 99
                    }
                },
                # SCENA 16 - Inquisitor Path
                {
                    "title": "The Holy Purge",
                    "narrative": "As a Church inquisitor, you burn magic users. The pyres light the sky.\n\nBut one 'witch' you're ordered to burn is a CHILD. A girl who can see the future.\n\n'Please,' she cries. 'I'm not evil!'\n\nThe crowd chants: 'BURN HER!'",
                    "location": "Public Square - Execution",
                    "mood": "dramatic",
                    "choices": [
                        {
                            "label": "Light the pyre",
                            "emoji": "🔥",
                            "result": "She burns. Her screams haunt you forever. But the Church praises your devotion.",
                            "consequences": {"reputation": {"Church": 100}, "xp_gain": 200},
                            "flag": "fanatic",
                            "next_scene": 18
                        },
                        {
                            "label": "Spare her and flee",
                            "emoji": "🛡️",
                            "result": "You cut her bonds and run. The Church brands YOU a heretic. But you saved a life.",
                            "consequences": {"reputation": {"Church": -100}},
                            "flag": "ending_heretic_savior",
                            "next_scene": 99
                        }
                    ]
                },
                # SCENA 17 - Witch Queen Ally
                {
                    "title": "Pact with Darkness",
                    "narrative": "The Queen IS a witch. She offers you dark magic.\n\n'Join me,' she says, eyes glowing. 'Together we'll crush the Church and rule forever.'\n\nPower beyond imagination... for the price of your soul.",
                    "location": "Ritual Chamber",
                    "npc": "Witch Queen Elara",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Accept dark magic",
                            "emoji": "🔮",
                            "result": "You drink demon blood. Power FLOODS you. You become the Queen's dark champion.",
                            "consequences": {"xp_gain": 800, "item": "🔮 Dark Grimoire"},
                            "flag": "ending_dark_champion",
                            "next_scene": 99
                        },
                        {
                            "label": "Betray her to the Church",
                            "emoji": "✝️",
                            "result": "You signal the inquisitors. They storm in. The Queen curses you as she burns.",
                            "consequences": {"reputation": {"Church": 100, "Crown": -100}, "xp_gain": 400},
                            "flag": "ending_betrayer",
                            "next_scene": 99
                        }
                    ]
                },
                # SCENA 18 - Final Convergence
                {
                    "title": "The Throne of Lies",
                    "narrative": "All paths converge. The kingdom teeters on the edge.\n\nThe Queen is dying (again). Three heirs claim the throne:\n\n**Prince Aldric** - Lawful but cruel\n**Bastard Mira** - Warrior and revolutionary\n**Lord Casimir** - Ambitious usurper\n\nYou've seen the ugliness of this court. YOU decide who rules... or if ANYONE should.",
                    "location": "Royal Deathbed - Final Choice",
                    "mood": "dramatic",
                    "choices": [
                        {
                            "label": "Support Prince Aldric (Order)",
                            "emoji": "👑",
                            "result": "The Tyrant King rises. Stability through oppression.",
                            "flag": "ending_tyrant",
                            "next_scene": 99
                        },
                        {
                            "label": "Support Mira (Freedom)",
                            "emoji": "⚔️",
                            "result": "Civil war erupts. But a FREE kingdom emerges.",
                            "flag": "ending_warrior_queen",
                            "next_scene": 99
                        },
                        {
                            "label": "Burn the throne (Revolution)",
                            "emoji": "🔥",
                            "result": "You torch the palace. Democracy rises from ashes.",
                            "flag": "ending_revolution",
                            "next_scene": 99
                        },
                        {
                            "label": "Claim it yourself (Ambition)",
                            "emoji": "👁️",
                            "result": "YOU sit the throne. Every faction bows in shock. Long live the Player King.",
                            "flag": "ending_player_king",
                            "consequences": {"xp_gain": 1000, "gold_change": 10000},
                            "next_scene": 99
                        }
                    ]
                },
                # SCENA 99 - UNIVERSAL ENDING (always accessible)
                {
                    "title": "Epilogue",
                    "narrative": "Your story in the Throne of Lies has ended.\n\nEvery choice mattered. Every path was real.\n\nThe kingdom's fate is sealed by YOUR decisions.",
                    "location": "The End",
                    "mood": "peaceful",
                    "choices": []
                }
            ],
            
            # 12 RANDOM ENCOUNTERS - Court/Political themed!
            "random_encounters": [
                {"id": "blackmail", "title": "Anonymous Blackmail", "type": "Social", "narrative": "You receive letter with YOUR secrets inside!",
                 "challenge": {"stat": "cha", "dc": 13, "success": "You track sender and threaten THEM!", "failure": "They leak it! Reputation damaged!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {"reputation": {"Crown": -20}}}},
                {"id": "duel", "title": "Honor Duel Challenge", "type": "Combat", "narrative": "Noble publicly insults you. Demands satisfaction!",
                 "challenge": {"stat": "dex", "dc": 14, "success": "First blood! You win with style!", "failure": "You lose. Humiliated.",
                 "success_consequences": {"reputation": {"Noble Houses": 25}, "xp_gain": 100}, "failure_consequences": {"reputation": {"Noble Houses": -15}}}},
                {"id": "affair", "title": "Secret Affair Exposed", "type": "Social Crisis", "narrative": "Someone saw you with Lord Casimir's spouse...",
                 "challenge": {"stat": "cha", "dc": 15, "success": "You deny convincingly!", "failure": "SCANDAL!",
                 "success_consequences": {}, "failure_consequences": {"reputation": {"Noble Houses": -30}}}},
                {"id": "bribe", "title": "Bribe Offer", "type": "Moral Choice", "narrative": "Merchant offers 300 gold to 'forget' what you saw.",
                 "challenge": {"stat": "wis", "dc": 11, "success": "Wise choice made.", "failure": "Regret follows.",
                 "success_consequences": {"gold_change": 300}, "failure_consequences": {}}},
                {"id": "feast", "title": "Feast Politics", "type": "Social", "narrative": "At dinner, factions try recruiting you.",
                 "challenge": {"stat": "int", "dc": 12, "success": "You play them against each other!", "failure": "You offend everyone.",
                 "success_consequences": {"xp_gain": 80}, "failure_consequences": {"reputation": {"Crown": -10}}}},
                {"id": "spy", "title": "Caught Spying", "type": "Crisis", "narrative": "Guards find you somewhere forbidden!",
                 "challenge": {"stat": "cha", "dc": 14, "success": "Smooth talk saves you!", "failure": "Marked suspicious.",
                 "success_consequences": {}, "failure_consequences": {"reputation": {"Crown": -20}}}},
                {"id": "gift", "title": "Mysterious Gift", "type": "Mystery", "narrative": "Expensive jewelry arrives. No sender. Trap?",
                 "challenge": {"stat": "int", "dc": 13, "success": "It's cursed! You dispose it!", "failure": "You wear it. CURSED!",
                 "success_consequences": {"xp_gain": 50}, "failure_consequences": {"hp_change": -20}}},
                {"id": "assassination", "title": "Assassination Attempt", "type": "Combat", "narrative": "Midnight. Blade at your throat!",
                 "challenge": {"stat": "dex", "dc": 16, "success": "You capture the assassin!", "failure": "Wounded! They escape!",
                 "success_consequences": {"xp_gain": 150, "reputation": {"Crown": 15}}, "failure_consequences": {"hp_change": -25}}},
                {"id": "theater", "title": "The Play's Message", "type": "Mystery", "narrative": "Court play seems directed AT YOU. Coded warning?",
                 "challenge": {"stat": "int", "dc": 14, "success": "Decoded! Coup warning!", "failure": "Too subtle.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "gambling", "title": "High Stakes Cards", "type": "Games", "narrative": "Nobles wager fortunes. Join?",
                 "challenge": {"stat": "int", "dc": 13, "success": "You WIN BIG!", "failure": "Heavy losses.",
                 "success_consequences": {"gold_change": 400}, "failure_consequences": {"gold_change": -200}}},
                {"id": "religious", "title": "Mandatory Church Service", "type": "Social", "narrative": "Show devotion or be labeled heretic.",
                 "challenge": {"stat": "wis", "dc": 11, "success": "Piety noted.", "failure": "Suspected heretic!",
                 "success_consequences": {"reputation": {"Church": 15}}, "failure_consequences": {"reputation": {"Church": -25}}}},
                {"id": "oracle", "title": "Oracle's Cryptic Warning", "type": "Mystery", "narrative": "Court oracle: 'Beware crowned serpent!'",
                 "challenge": {"stat": "int", "dc": 15, "success": "You decipher it!", "failure": "Too cryptic.",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {}}}
            ],
            
            # 10 SIDE QUESTS - Political missions!
            "side_quests": [
                {"id": "love_letters", "title": "Deliver Secret Letters", "narrative": "Royal asks you to deliver forbidden love letters.",
                 "rewards_hint": "💌 Romance + Gold", "challenge": {"stat": "dex", "dc": 12, "success": "Delivered! Gratitude!", "failure": "Intercepted! Scandal!",
                 "success_consequences": {"gold_change": 200, "reputation": {"Noble Houses": 20}}, "failure_consequences": {"reputation": {"Crown": -15}}}},
                {"id": "wine_heist", "title": "Steal Royal Wine", "narrative": "Rogue offers profit split if you steal King's legendary wine.",
                 "rewards_hint": "💰💰 Big Loot", "challenge": {"stat": "dex", "dc": 15, "success": "Heist success! 600 gold!", "failure": "Caught! Dungeon!",
                 "success_consequences": {"gold_change": 600, "xp_gain": 150}, "failure_consequences": {"hp_change": -20, "reputation": {"Crown": -40}}}},
                {"id": "portrait", "title": "Commission Portrait", "narrative": "Famous painter offers to immortalize you for 300 gold.",
                 "rewards_hint": "⭐ Fame", "challenge": {"stat": "cha", "dc": 11, "success": "Masterpiece! Everyone admires it!", "failure": "Unflattering. Mocked.",
                 "success_consequences": {"gold_change": -300, "reputation": {"Noble Houses": 40}, "xp_gain": 50}, "failure_consequences": {"gold_change": -300, "reputation": {"Noble Houses": -10}}}},
                {"id": "duel_champion", "title": "Fight Honor Duel", "narrative": "Noble hires you to duel in their place.",
                 "rewards_hint": "💰 + Glory", "challenge": {"stat": "str", "dc": 14, "success": "Victory! Payment + fame!", "failure": "Defeat. Client angry.",
                 "success_consequences": {"gold_change": 250, "reputation": {"Noble Houses": 20}, "xp_gain": 100}, "failure_consequences": {"reputation": {"Noble Houses": -20}}}},
                {"id": "library", "title": "Forbidden Library", "narrative": "Spymaster offers access to banned books... for a favor.",
                 "rewards_hint": "📚 Secret Knowledge", "challenge": {"stat": "int", "dc": 14, "success": "Knowledge is power!", "failure": "Incomprehensible.",
                 "success_consequences": {"xp_gain": 200, "item": "📕 Forbidden Tome"}, "failure_consequences": {}}},
                {"id": "masquerade_spy", "title": "Infiltrate Rival Ball", "narrative": "Ally wants intel from rival's masquerade party.",
                 "rewards_hint": "🎭 Intel", "challenge": {"stat": "cha", "dc": 15, "success": "Perfect blend! Intel gathered!", "failure": "Exposed! Escorted out!",
                 "success_consequences": {"xp_gain": 150, "reputation": {"Shadow Guild": 30}}, "failure_consequences": {}}},
                {"id": "rescue_scholar", "title": "Rescue Jailed Scholar", "narrative": "Brilliant scholar jailed for heresy. Their knowledge crucial.",
                 "rewards_hint": "🧠 Ally", "challenge": {"stat": "dex", "dc": 16, "success": "Daring rescue! Scholar ally!", "failure": "Failed. Executed.",
                 "success_consequences": {"companion": "🧠 Scholar", "xp_gain": 175}, "failure_consequences": {}}},
                {"id": "steal_relic", "title": "Steal Church Relic", "narrative": "Lord hires you to steal holy relic to weaken church.",
                 "rewards_hint": "💰💰 + Crisis", "challenge": {"stat": "dex", "dc": 17, "success": "Stolen! Religious uproar!", "failure": "Caught! Branded heretic!",
                 "success_consequences": {"gold_change": 800, "reputation": {"Church": -60}, "xp_gain": 200}, "failure_consequences": {"reputation": {"Church": -100}}}},
                {"id": "poison_study", "title": "Learn Poisoncraft", "narrative": "Royal alchemist teaches poisons... 'educationally'.",
                 "rewards_hint": "☠️ Toxin Knowledge", "challenge": {"stat": "int", "dc": 13, "success": "Toxicology mastered!", "failure": "You poison YOURSELF!",
                 "success_consequences": {"item": "☠️ Poison Vials", "xp_gain": 100}, "failure_consequences": {"hp_change": -25}}},
                {"id": "seduction_test", "title": "Seduction Mission", "narrative": "Spy recruiter tests if you can seduce high-value target.",
                 "rewards_hint": "💋 Spy Recruitment", "challenge": {"stat": "cha", "dc": 16, "success": "Success! Spy agent now!", "failure": "Rejected. Embarrassed.",
                 "success_consequences": {"reputation": {"Shadow Guild": 50}, "xp_gain": 150}, "failure_consequences": {"reputation": {"Noble Houses": -10}}}}
            ],
            
            "endings": {
                "ending_loyal_lord": {
                    "requires": {"ending_loyal_lord": True},
                    "narrative": "🏰 **THE LOYAL LORD**\n\nYou defended the Queen against all traitors. The coup was crushed. Casimir's head decorates the castle walls.\n\nThe Queen grants you a lordship and vast lands. You're now one of the most powerful nobles in the realm.\n\nYou chose loyalty. The Crown stands eternal."
                },
                "ending_usurper": {
                    "requires": {"ending_usurper": True},
                    "narrative": "👑 **THE USURPER'S REWARD**\n\nYou opened the gates. The Queen was captured and executed. Lord Casimir sits the throne.\n\nAs Royal Enforcer, you crush dissent in the streets. Order through fear. Power through blood.\n\nYou chose ambition. Sleep well... if you can."
                },
                "ending_opportunist_king": {
                    "requires": {"ending_opportunist_king": True},
                    "narrative": "🎭 **THE OPPORTUNIST KING**\n\nWhile nobles and Crown destroyed each other, YOU seized the throne. Nobody expected it. Nobody could stop it.\n\nYour coronation is silent but absolute. The kingdom bows to the player who won the game.\n\nYou chose cunning. History crowns you genius or monster."
                },
                "ending_guild_master": {
                    "requires": {"ending_guild_master": True},
                    "narrative": "🗡️ **THE SHADOW MASTER**\n\nYou killed your mentor. Seraphine's blood bought you the Guild.\n\nNow YOU control the kingdom from the shadows. Kings bow to your whispers. Assassins obey your will.\n\nYou chose power. The darkness embraced you back."
                },
                "ending_exile_rich": {
                    "requires": {"ending_exile_rich": True},
                    "narrative": "💰 **THE RICH EXILE**\n\nYou betrayed everyone, kept the gold, and fled the capital with 1600 gold.\n\nThree factions hunt you. But you're RICH. You sail to distant lands and start a new life.\n\nYou chose wealth. Regret costs extra."
                },
                "ending_love": {
                    "requires": {"ending_love": True},
                    "narrative": "❤️ **LOVE CONQUERS ALL**\n\nYou abandoned everything for Ser Aldrik. The Guild swore vengeance. The Crown branded you traitors.\n\nBut you're FREE. Together. Living in a small cottage by the sea, loving every simple moment.\n\nYou chose love. Some endings write themselves."
                },
                "ending_vanished": {
                    "requires": {"ending_vanished": True},
                    "narrative": "👻 **THE PHANTOM**\n\nYou faked your death so convincingly that legends speak of your assassination.\n\nNew identity. New life. Complete freedom. All three factions mourned you.\n\nYou chose escape. The perfect crime is being forgotten."
                },
                "ending_guild_master": {
                    "requires": {"ending_guild_master": True},
                    "narrative": "🗡️ **MASTER OF SHADOWS**\n\nAfter defeating Seraphine, you claimed leadership of the Shadow Guild.\n\nFrom darkness, you control the kingdom. Kings rise and fall by YOUR word.\n\nYou chose dominion. The shadows obey."
                },
                "ending_heretic_savior": {
                    "requires": {"ending_heretic_savior": True},
                    "narrative": "🕊️ **THE HERETIC SAVIOR**\n\nYou saved the child witch from the pyre. The Church branded you HERETIC.\n\nBut she had the gift of prophecy. She guides you both to safety, to a hidden village that accepts magic.\n\nYou chose mercy. Your soul is clean."
                },
                "ending_dark_champion": {
                    "requires": {"ending_dark_champion": True},
                    "narrative": "🔮 **THE DARK CHAMPION**\n\nYou drank demon blood and became the Witch Queen's ultimate weapon.\n\nTogether you crushed the Church and enslaved the nobles. A dark age begins.\n\nYou chose power. Your humanity was the price."
                },
                "ending_betrayer": {
                    "requires": {"ending_betrayer": True},
                    "narrative": "✝️ **THE RIGHTEOUS BETRAYER**\n\nYou betrayed the Witch Queen to the Church. Inquisitors burned her alive.\n\nThe Church hails you as a hero. A cathedral is built in your honor.\n\nYou chose faith. Her dying curse echoes still."
                },
                "ending_player_king": {
                    "requires": {"ending_player_king": True},
                    "narrative": "👑 **THE PLAYER KING**\n\nIn the final chaos, YOU claimed the throne. Not through blood right. Not through conquest.\n\nThrough sheer WILL. Every faction was too stunned to resist. You simply... sat. And ruled.\n\nYou chose yourself. And the kingdom accepted it.\n\nLong live the Player King. The one who won the game."
                },
                "ending_tyrant": {
                    "requires": {"ending_tyrant": True},
                    "narrative": "🏰 **THE TYRANT KING**\n\nPrince Aldric ascends the throne. Order is restored, but at a cost. Dissenters vanish in the night.\n\nYou're made Royal Spymaster—a tool of oppression, rewarded handsomely.\n\nYou chose stability over justice. History will remember... then forget."
                },
                "ending_warrior_queen": {
                    "requires": {"ending_warrior_queen": True},
                    "narrative": "⚔️ **THE WARRIOR QUEEN**\n\nQueen Mira claims the throne through blood. Civil war ravages the land, but when the dust settles, a NEW kingdom emerges.\n\nYou're made Lord Commander of the New Guard. Respected. Feared. Free.\n\nYou chose struggle over peace. History will sing your name."
                },
                "ending_revolution": {
                    "requires": {"ending_revolution": True},
                    "narrative": "🔥 **THE REVOLUTION**\n\nThe monarchy crumbles. Fire consumes the palace. From the ashes, the people vote for their first elected council.\n\nYou're branded a traitor by some, a hero by others. You vanish into legend.\n\nYou chose freedom over order. History will debate you forever."
                },
                "default": "The court consumed itself. Your choices led nowhere. The kingdom falls into endless civil war. Nobody wins. Nobody survives. The Throne of Lies claims all."
            }
        }
    
    def _gen_world_explorer(self, char_class: str = None) -> dict:
        """Exploration campaign - WIS focused - 12 scenes with branching"""
        return {
            "name": "Beyond the Edge of Maps",
            "type": "Exploration",
            "scenes": [
                # SCENE 0 - Start
                {
                    "title": "The Last Port",
                    "narrative": "Port Horizon clings to the eastern edge of the known world. Beyond lies the Uncharted Sea—an expanse of mystery where ships vanish and legends are born.\n\nYou stand at the docks, examining the ship you've hired: *The Stormchaser*. Its captain, a grizzled woman named Kael, frowns at the horizon.\n\n\"*Last chance to turn back,*\" she says. \"*No maps. No guarantees. Just open water and whatever gods watch over fools.*\"\n\nWhy are you doing this?",
                    "location": "Port Horizon - Docks",
                    "npc": "Captain Kael",
                    "mood": "hopeful",
                    "choices": [
                        {
                            "label": "\"I seek the Eternal Isle—immortality itself.\"",
                            "emoji": "🏝️",
                            "hint": "Personal quest for eternal life",
                            "result": "Kael spits. \"*Everyone wants to live forever. Most die trying. Get aboard.*\"",
                            "flag": "quest_immortality",
                            "next_scene": 1,
                            "major": True
                        },
                        {
                            "label": "\"My family vanished here 10 years ago.\"",
                            "emoji": "👨‍👩‍👧",
                            "hint": "Searching for lost loved ones",
                            "result": "Kael's expression softens. \"*I've lost crew to these waters. Maybe we'll find answers together.*\"",
                            "flag": "quest_family",
                            "major": True,
                            "next_scene": 1,
                            "consequences": {"reputation": {"Captain Kael": 10}}
                        },
                        {
                            "label": "\"Because no one else will.\"",
                            "emoji": "🌊",
                            "hint": "Pure wanderlust",
                            "result": "Kael grins. \"*Now that's a reason I understand. Welcome aboard, explorer.*\"",
                            "flag": "quest_wanderlust",
                            "next_scene": 1,
                            "major": True
                        }
                    ]
                },
                # SCENE 1 - The Storm
                {
                    "title": "The Storm",
                    "narrative": "Three weeks at sea. The sky turns black.\n\nLightning splits the heavens. Waves crash over the deck. The crew screams orders as the mast cracks like thunder.\n\nKael shouts over the roar: \"*We need to lighten the ship! Throw cargo overboard—or we ALL drown!*\"\n\nYour supplies. Your tools. Your HOPE. What do you sacrifice?",
                    "location": "The Stormchaser - In Storm",
                    "mood": "chaotic",
                    "challenge": {
                        "type": "Survival",
                        "stat": "wis",
                        "dc": 14,
                        "description": "Keep the ship afloat",
                        "success": "You navigate the storm brilliantly—using ropes, timing, and intuition. The ship survives INTACT.",
                        "failure": "You lose cargo, supplies, and nearly your life. But you survive. Barely.",
                        "success_consequences": {"reputation": {"Captain Kael": 15}, "xp_gain": 75},
                        "failure_consequences": {"hp_change": -20, "gold_change": -30},
                        "next_scene": 2
                    }
                },
                # SCENE 2 - Mysterious Island
                {
                    "title": "The Mysterious Island",
                    "narrative": "An island emerges from mist—uncharted, impossible. Its beaches shimmer with black sand. Strange ruins dot the shoreline.\n\nAs you disembark, you notice:\n\n- Ancient statues with eyes that seem to **follow you**\n- A temple entrance glowing with blue light\n- Footprints in the sand... **fresh**... leading inland\n\nSomeone—or something—lives here.",
                    "location": "Mysterious Island - Beach",
                    "mood": "mysterious",
                    "choices": [
                        {
                            "label": "Investigate the glowing temple",
                            "emoji": "🔵",
                            "hint": "Seek ancient knowledge",
                            "result": "Inside, you find murals depicting a civilization that ASCENDED. Left behind: a crystal that hums with power.",
                            "consequences": {"item": "🔮 Ascension Crystal", "xp_gain": 100},
                            "flag": "found_crystal",
                            "next_scene": 3
                        },
                        {
                            "label": "Follow the footprints inland",
                            "emoji": "👣",
                            "hint": "Find whoever lives here",
                            "result": "You discover a hermit—an old explorer who's been stranded for 30 years. He knows SECRETS about these waters.",
                            "consequences": {"companion": "Old Hermit Theron", "reputation": {"Explorers": 10}},
                            "flag": "found_hermit",
                            "next_scene": 4
                        },
                        {
                            "label": "Return to the ship and leave immediately",
                            "emoji": "⚓",
                            "hint": "This place feels wrong",
                            "result": "As you flee, shadows rise from the ruins. You escape... but something FOLLOWS your ship now.",
                            "consequences": {"hp_change": -10},
                            "flag": "cursed",
                            "next_scene": 5
                        }
                    ]
                },
                # SCENE 3 - Temple Path
                {
                    "title": "The Ascension Chamber",
                    "narrative": "The crystal pulses in your hand, growing brighter. It leads you deeper into the temple.\n\nYou reach a chamber with a pedestal at its center. Ancient text glows: 'Place the crystal. Become MORE.'\n\nBut Kael grabs your arm. 'That's magic. DANGEROUS magic. We should leave.'",
                    "location": "Ancient Temple",
                    "npc": "Captain Kael (Worried)",
                    "mood": "mysterious",
                    "choices": [
                        {
                            "label": "Place the crystal (Transcend)",
                            "emoji": "✨",
                            "result": "Energy floods you. You SEE. The map of reality unfolds. You know the way now.",
                            "consequences": {"xp_gain": 300, "item": "🧠 Cosmic Knowledge"},
                            "flag": "transcended",
                            "next_scene": 6
                        },
                        {
                            "label": "Listen to Kael (Safety)",
                            "emoji": "⚓",
                            "result": "You pocket the crystal. Some secrets are too dangerous.",
                            "consequences": {"reputation": {"Captain Kael": 30}},
                            "next_scene": 7
                        }
                    ]
                },
                # SCENE 4 - Hermit Path
                {
                    "title": "The Hermit's Warning",
                    "narrative": "Theron, the hermit, draws a map in the sand with trembling hands.\n\n'30 years I've been here,' he whispers. 'Watching. Waiting. The Eternal Isle is REAL. But it demands a price.'\n\nHe points west. 'The Siren's Passage. Most ships enter. None return. But it's the only way.'\n\nKael frowns. 'We could find another route. Take longer, but safer.'",
                    "location": "Hermit's Cave",
                    "npc": "Hermit Theron",
                    "mood": "tense",
                    "choices": [
                        {
                            "label": "Take the Siren's Passage (Risky)",
                            "emoji": "🎵",
                            "result": "You set course for the Passage. Fortune favors the bold... or kills them.",
                            "flag": "took_passage",
                            "next_scene": 8
                        },
                        {
                            "label": "Find the safer route (Slow)",
                            "emoji": "🗺️",
                            "result": "Weeks pass. You sail the long way. Safer, but supplies dwindle.",
                            "consequences": {"gold_change": -100},
                            "next_scene": 9
                        }
                    ]
                },
                # SCENE 5 - Cursed Path
                {
                    "title": "The Shadow Stalker",
                    "narrative": "Ever since you fled the island, something follows. Crew members report whispers. Shadows move wrong.\n\nKael confronts you: 'We need to turn back. Lift this curse. Or throw YOU overboard.'\n\nThe crew murmurs in agreement. Mutiny brews.",
                    "location": "The Stormchaser - Cursed",
                    "npc": "Captain Kael (Furious)",
                    "mood": "dark",
                    "choices": [
                        {
                            "label": "Fight the shadow (Confront curse)",
                            "emoji": "⚔️",
                            "result": "That night, you face the shadow alone. It SCREAMS. You fight with blade and will.",
                            "consequences": {"hp_change": -30, "xp_gain": 200},
                            "flag": "defeated_curse",
                            "next_scene": 7
                        },
                        {
                            "label": "Jump overboard (Sacrifice)",
                            "emoji": "🌊",
                            "result": "You dive into dark waters. The shadow follows YOU, not the ship. Kael screams your name as you sink...",
                            "flag": "ending_sacrifice_sea",
                            "consequences": {"hp_change": -50}
                        }
                    ]
                },
                # SCENE 6 - Transcended Path
                {
                    "title": "The Cosmic Navigator",
                    "narrative": "You SEE now. The ocean is alive. Every wave is a voice. Every current is intention.\n\nKael stares at you, unnerved. 'Your eyes are glowing,' she says.\n\nYou point. 'That way. The Eternal Isle. Three days.'\n\nShe hesitates. 'You're... different. Are you still YOU?'",
                    "location": "The Stormchaser - Night",
                    "npc": "Captain Kael (Uncertain)",
                    "mood": "mysterious",
                    "choices": [
                        {
                            "label": "\"I'm MORE than I was.\"",
                            "emoji": "🌟",
                            "result": "You guide the ship with impossible precision. The crew follows, awed and terrified.",
                            "consequences": {"xp_gain": 100},
                            "next_scene": 10
                        },
                        {
                            "label": "\"I'm still me. Just... awake.\"",
                            "emoji": "👁️",
                            "result": "Kael nods slowly. Trust restored. For now.",
                            "consequences": {"reputation": {"Captain Kael": 20}},
                            "next_scene": 10
                        }
                    ]
                },
                # SCENE 7 - Safe Route Convergence
                {
                    "title": "The Merchant Fleet",
                    "narrative": "You encounter a massive merchant fleet. Dozens of ships. Safety in numbers.\n\nTheir admiral offers: 'Join our convoy. We sail to the Edge. Protection for all.'\n\nKael whispers: 'Large targets. If pirates attack, it'll be bloodbath.'",
                    "location": "Open Sea",
                    "npc": "Admiral Reeves",
                    "mood": "hopeful",
                    "choices": [
                        {
                            "label": "Join the convoy",
                            "emoji": "🚢",
                            "result": "Safety in numbers. You sail with the fleet.",
                            "consequences": {"reputation": {"Merchants": 20}},
                            "next_scene": 10
                        },
                        {
                            "label": "Sail alone",
                            "emoji": "⚓",
                            "result": "You decline. Kael respects your independence.",
                            "consequences": {"reputation": {"Captain Kael": 15}},
                            "next_scene": 10
                        }
                    ]
                },
                # SCENE 8 - Siren's Passage
                {
                    "title": "Song of the Sirens",
                    "narrative": "The Passage. Jagged rocks. Mist thick as walls.\n\nThen... singing. Beautiful. Impossible. The crew's eyes glaze over.\n\nKael fights it, blood trickling from her ears. 'COVER YOUR EARS!'",
                    "location": "Siren's Passage",
                    "mood": "chaotic",
                    "challenge": {
                        "type": "Willpower",
                        "stat": "wis",
                        "dc": 17,
                        "description": "Resist the siren song",
                        "success": "You resist. Guide the ship through. Sirens SHRIEK in fury as you escape.",
                        "failure": "The song takes you. You wake hours later, ship damaged, but alive.",
                        "success_consequences": {"xp_gain": 250, "reputation": {"Captain Kael": 40}},
                        "failure_consequences": {"hp_change": -25, "gold_change": -200},
                        "next_scene": 10
                    }
                },
                # SCENE 9 - Long Route
                {
                    "title": "The Endless Sea",
                    "narrative": "Weeks become months. The safe route is LONG. Supplies run low. Crew grows restless.\n\nKael rations food. Water is precious. Tempers flare.\n\nOne night, a crewman pulls a knife: 'There's not enough for everyone...'",
                    "location": "Open Sea - Starving",
                    "mood": "tense",
                    "challenge": {
                        "type": "Leadership",
                        "stat": "cha",
                        "dc": 15,
                        "description": "Prevent mutiny",
                        "success": "You rally the crew. 'We're almost there. Together, we survive.'",
                        "failure": "Violence erupts. You restore order, but at a cost.",
                        "success_consequences": {"xp_gain": 150},
                        "failure_consequences": {"hp_change": -20, "reputation": {"Captain Kael": -10}},
                        "next_scene": 10
                    }
                },
                # SCENE 10 - Final Convergence
                {
                    "title": "The Edge of the World",
                    "narrative": "You've sailed beyond all reason. Beyond all possibility.\n\nThe ocean... **ends**.\n\nWater pours over an edge into infinite void. Stars shine BELOW the horizon. Reality fractures.\n\nKael whispers, terrified: \"*What... what is this?*\"\n\nIn the distance, floating in the void: a city. A city of LIGHT. Impossible architecture. The Eternal Isle.\n\nBut to reach it, you must **sail over the edge**.\n\nEverything you were told—gravity, reality, LIFE itself—will break.\n\n**Do you dare?**",
                    "location": "The Edge of the World",
                    "npc": "Captain Kael (Terrified)",
                    "mood": "dramatic",
                    "choices": [
                        {
                            "label": "\"Full sail ahead! Into the void!\"",
                            "emoji": "🚀",
                            "hint": "Embrace the unknown",
                            "result": "You sail over the edge. Gravity inverts. The ship FLIES. You've broken reality itself and reached the Eternal Isle.",
                            "flag": "ending_eternal",
                            "flag_value": True,
                            "consequences": {"xp_gain": 300},
                            "major": True
                            # No next_scene - ENDING
                        },
                        {
                            "label": "\"Turn back. This is madness.\"",
                            "emoji": "⚓",
                            "hint": "Choose life over legend",
                            "result": "You return home. You've seen wonders, but not ALL wonders. You live to explore another day.",
                            "flag": "ending_return",
                            "flag_value": True,
                            "major": True
                            # No next_scene - ENDING
                        },
                        {
                            "label": "\"I'll swim. The ship stays safe.\"",
                            "emoji": "🏊",
                            "hint": "Sacrifice yourself",
                            "result": "You dive into the void alone. Kael screams your name. You fall through stars... and wake in a city of gods.",
                            "flag": "ending_sacrifice",
                            "flag_value": True,
                            "consequences": {"hp_change": -50},
                            "major": True
                            # No next_scene - ENDING
                        }
                    ]
                }
            ],
            
            # 15 RANDOM ENCOUNTERS - Sea exploration themed!
            "random_encounters": [
                {"id": "storm", "title": "Sudden Storm", "type": "Survival", "narrative": "Dark clouds roll in! Hurricane winds!",
                 "challenge": {"stat": "wis", "dc": 13, "success": "You navigate through!", "failure": "Ship damaged!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {"hp_change": -15}}},
                {"id": "pirates", "title": "Pirate Attack", "type": "Combat", "narrative": "Black sails on horizon! Pirates board!",
                 "challenge": {"stat": "str", "dc": 14, "success": "Repelled! You capture their loot!", "failure": "They steal supplies!",
                 "success_consequences": {"gold_change": 300, "xp_gain": 100}, "failure_consequences": {"gold_change": -150}}},
                {"id": "whale", "title": "Giant Whale", "type": "Discovery", "narrative": "MASSIVE whale surfaces beside ship!",
                 "challenge": {"stat": "wis", "dc": 12, "success": "It's friendly! Blesses you!", "failure": "It crashes into ship!",
                 "success_consequences": {"hp_change": 20, "xp_gain": 50}, "failure_consequences": {"hp_change": -20}}},
                {"id": "mermaid", "title": "Mermaid Encounter", "type": "Social", "narrative": "Beautiful mermaid offers guidance... or lure to doom?",
                 "challenge": {"stat": "cha", "dc": 14, "success": "She guides you to treasure!", "failure": "Siren song! Crew charmed!",
                 "success_consequences": {"gold_change": 400, "xp_gain": 100}, "failure_consequences": {"hp_change": -10}}},
                {"id": "fog", "title": "Cursed Fog", "type": "Mystery", "narrative": "Thick fog surrounds ship. Whispers in mist...",
                 "challenge": {"stat": "int", "dc": 13, "success": "You navigate out!", "failure": "Lost for days!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {}}},
                {"id": "wreck", "title": "Shipwreck Discovery", "type": "Discovery", "narrative": "Sunken ship visible below! Dive for treasure?",
                 "challenge": {"stat": "dex", "dc": 15, "success": "TREASURE JACKPOT!", "failure": "Trapped underwater! Barely escape!",
                 "success_consequences": {"gold_change": 500, "xp_gain": 150}, "failure_consequences": {"hp_change": -25}}},
                {"id": "kraken", "title": "Kraken Tentacles", "type": "Combat", "narrative": "MASSIVE tentacles rise from deep!",
                 "challenge": {"stat": "str", "dc": 17, "success": "You FIGHT IT OFF!", "failure": "Ship severely damaged!",
                 "success_consequences": {"xp_gain": 250}, "failure_consequences": {"hp_change": -35}}},
                {"id": "dolphins", "title": "Dolphin Pod", "type": "Discovery", "narrative": "Hundreds of dolphins swim alongside, guiding you.",
                 "challenge": {"stat": "wis", "dc": 11, "success": "They lead to hidden island!", "failure": "Just pretty dolphins.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "ghost_ship", "title": "Ghost Ship", "type": "Mystery", "narrative": "Phantom ship sails past. Crew of skeletons waves...",
                 "challenge": {"stat": "wis", "dc": 15, "success": "You communicate! They share secrets!", "failure": "Cursed! Bad luck follows!",
                 "success_consequences": {"xp_gain": 150, "item": "📜 Ghost Map"}, "failure_consequences": {"hp_change": -10}}},
                {"id": "trade", "title": "Trade Ship Encounter", "type": "Social", "narrative": "Merchant vessel offers trade.",
                 "challenge": {"stat": "cha", "dc": 12, "success": "Great deals!", "failure": "Cheated!",
                 "success_consequences": {"gold_change": 200}, "failure_consequences": {"gold_change": -100}}},
                {"id": "mutiny", "title": "Mutiny Threat", "type": "Social", "narrative": "Crew is restless. Mutiny brewing?",
                 "challenge": {"stat": "cha", "dc": 15, "success": "You unite them with speech!", "failure": "Fight breaks out!",
                 "success_consequences": {"reputation": {"Captain Kael": 30}}, "failure_consequences": {"hp_change": -15}}},
                {"id": "island", "title": "Uncharted Island", "type": "Discovery", "narrative": "Small island! Not on any map!",
                 "challenge": {"stat": "int", "dc": 13, "success": "You map it! Discovery!", "failure": "Nothing special.",
                 "success_consequences": {"xp_gain": 100, "gold_change": 150}, "failure_consequences": {}}},
                {"id": "waterspout", "title": "Water Tornado", "type": "Survival", "narrative": "WATERSPOUT ahead! Steer or be destroyed!",
                 "challenge": {"stat": "dex", "dc": 16, "success": "Dodged perfectly!", "failure": "Caught in it! Chaos!",
                 "success_consequences": {"xp_gain": 125}, "failure_consequences": {"hp_change": -30}}},
                {"id": "treasure_map", "title": "Bottle with Map", "type": "Discovery", "narrative": "Floating bottle contains treasure map!",
                 "challenge": {"stat": "int", "dc": 14, "success": "You decode it! Treasure found!", "failure": "Can't read it.",
                 "success_consequences": {"gold_change": 600, "xp_gain": 150}, "failure_consequences": {}}},
                {"id": "sea_serpent", "title": "Sea Serpent", "type": "Combat", "narrative": "Legendary sea serpent attacks!",
                 "challenge": {"stat": "str", "dc": 18, "success": "YOU SLAY IT! LEGEND!", "failure": "Barely escape alive!",
                 "success_consequences": {"xp_gain": 400, "gold_change": 800}, "failure_consequences": {"hp_change": -40}}}
            ],
            
            # 12 SIDE QUESTS - Exploration missions!
            "side_quests": [
                {"id": "rescue_sailor", "title": "Rescue Stranded Sailor", "narrative": "Lone sailor on raft. Rescue or pass?",
                 "rewards_hint": "🤝 Ally", "challenge": {"stat": "cha", "dc": 11, "success": "Rescued! Joins crew!", "failure": "They're hostile!",
                 "success_consequences": {"companion": "⚓ Sailor", "xp_gain": 75}, "failure_consequences": {"hp_change": -10}}},
                {"id": "rare_fish", "title": "Catch Legendary Fish", "narrative": "Captain wants rare Golden Tuna for dinner.",
                 "rewards_hint": "🐟 Food + Gold", "challenge": {"stat": "dex", "dc": 14, "success": "CAUGHT! Feast tonight!", "failure": "It got away...",
                 "success_consequences": {"gold_change": 250, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "star_chart", "title": "Map the Stars", "narrative": "Astronomer asks you to help chart constellations.",
                 "rewards_hint": "🌟 Navigation Boost", "challenge": {"stat": "int", "dc": 14, "success": "Perfect chart! Navigation mastered!", "failure": "Too cloudy.",
                 "success_consequences": {"item": "🗺️ Star Chart", "xp_gain": 125}, "failure_consequences": {}}},
                {"id": "dive_depth", "title": "Deep Dive Challenge", "narrative": "Crew bets you can't dive to ocean floor and return.",
                 "rewards_hint": "💰 Bet Winnings", "challenge": {"stat": "str", "dc": 16, "success": "You DID IT! Legendary!", "failure": "Nearly drown!",
                 "success_consequences": {"gold_change": 300, "xp_gain": 150}, "failure_consequences": {"hp_change": -25}}},
                {"id": "repair_ship", "title": "Emergency Repairs", "narrative": "Ship damaged. Must fix before storm hits!",
                 "rewards_hint": "🔧 Survival", "challenge": {"stat": "int", "dc": 13, "success": "Repaired perfectly!", "failure": "Poor patch job. Leaks.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {"hp_change": -15}}},
                {"id": "ancient_artifact", "title": "Find Sunken Artifact", "narrative": "Legend speaks of artifact in these waters.",
                 "rewards_hint": "✨ Magic Item", "challenge": {"stat": "wis", "dc": 15, "success": "FOUND! Ancient relic!", "failure": "Just coral.",
                 "success_consequences": {"item": "🔱 Poseidon's Trident", "xp_gain": 200}, "failure_consequences": {}}},
                {"id": "storm_chase", "title": "Chase the Storm", "narrative": "Scientist wants to ENTER a hurricane for research.",
                 "rewards_hint": "🌪️ Insane XP", "challenge": {"stat": "wis", "dc": 17, "success": "You survive! Data gathered!", "failure": "DISASTER!",
                 "success_consequences": {"xp_gain": 300}, "failure_consequences": {"hp_change": -40}}},
                {"id": "whale_song", "title": "Record Whale Songs", "narrative": "Mysterious whale songs. Record them?",
                 "rewards_hint": "🎵 Knowledge", "challenge": {"stat": "int", "dc": 12, "success": "Beautiful! Secrets revealed!", "failure": "Can't understand.",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {}}},
                {"id": "island_race", "title": "Island-to-Island Race", "narrative": "Rival ship challenges you to race!",
                 "rewards_hint": "🏆 Glory + Gold", "challenge": {"stat": "dex", "dc": 15, "success": "VICTORY! Prize won!", "failure": "Humiliating defeat.",
                 "success_consequences": {"gold_change": 500, "xp_gain": 150}, "failure_consequences": {"reputation": {"Captain Kael": -10}}}},
                {"id": "sea_monster_hunt", "title": "Hunt Contract: Leviathan", "narrative": "Port offers 1000 gold to kill terrorizing leviathan.",
                 "rewards_hint": "💰💰💰 Massive Reward", "challenge": {"stat": "str", "dc": 19, "success": "KILLED THE BEAST!", "failure": "It nearly kills YOU!",
                 "success_consequences": {"gold_change": 1000, "xp_gain": 400}, "failure_consequences": {"hp_change": -45}}},
                {"id": "underwater_city", "title": "Explore Sunken City", "narrative": "Ruins of ancient city below. Dive?",
                 "rewards_hint": "🏛️ Ancient Treasure", "challenge": {"stat": "wis", "dc": 16, "success": "You explore and survive! Treasures!", "failure": "Trapped! Barely escape!",
                 "success_consequences": {"gold_change": 700, "xp_gain": 250}, "failure_consequences": {"hp_change": -30}}},
                {"id": "forbidden_waters", "title": "Enter the Forbidden Zone", "narrative": "Maps mark area: 'ENTER AND DIE'. But treasure...",
                 "rewards_hint": "💀 High Risk, High Reward", "challenge": {"stat": "str", "dc": 18, "success": "You SURVIVE the forbidden zone! Epic loot!", "failure": "Cursed! Damaged!",
                 "success_consequences": {"gold_change": 1200, "xp_gain": 500}, "failure_consequences": {"hp_change": -50}}}
            ],
            
            "endings": {
                "ending_eternal": {
                    "requires": {"ending_eternal": True},
                    "narrative": "🌟 **THE ETERNAL EXPLORER**\n\nYou reached the Eternal Isle. Time doesn't exist here. You explore forever, discovering infinite wonders.\n\nKael and the crew join you. You're legends now—explorers beyond death, beyond time itself.\n\nYou chose infinity. History will never forget, because history never ends for you."
                },
                "ending_return": {
                    "requires": {"ending_return": True},
                    "narrative": "⚓ **THE WISE WANDERER**\n\nYou returned with stories. Maps of impossible places. Proof of the Uncharted.\n\nOthers will follow your path now. You opened the doors; they'll walk through.\n\nYou chose wisdom over glory. History will remember you as the one who came BACK."
                },
                "ending_sacrifice": {
                    "requires": {"ending_sacrifice": True},
                    "narrative": "🏊 **THE MARTYR OF STARS**\n\nYou fell through the void and ascended. Gods themselves greet you.\n\nYour crew sails home with your legend. Songs will be sung. Temples built.\n\nYou chose others over yourself. History will worship you."
                },
                "default": "You explored far, but never reached your destination. The sea claimed you, as it claims all explorers eventually."
            }
        }
    
    def _gen_chaotic_mayhem(self, char_class: str = None) -> dict:
        """INFINITY ADVENTURE - ULTIMATE CAMPAIGN - 100+ SCENES, 30 ENDINGS, INFINITE POSSIBILITIES!"""
        intro = "Reality fractures. The Infinity Nexus opens before you.\n\n**You stand at the crossroads of INFINITE worlds.**\n\n"
        if char_class == 'warrior':
            intro += "**As a warrior**, you feel power coursing through infinite battlefields."
        elif char_class == 'mage':
            intro += "**As a mage**, you perceive infinite timelines, infinite spells, infinite YOU."
        elif char_class == 'rogue':
            intro += "**As a rogue**, you see infinite treasures, infinite heists, infinite escapes."
        elif char_class == 'cleric':
            intro += "**As a cleric**, you hear gods from infinite realities calling."
        elif char_class == 'ranger':
            intro += "**As a ranger**, you track prey across infinite dimensions."
        elif char_class == 'paladin':
            intro += "**As a paladin**, infinite oaths bind you to infinite justices."
        
        return {
            "name": "The Infinity Adventure",
            "type": "Infinite Possibilities",
            "scenes": [
                # SCENE 0: THE NEXUS HUB
                {"title": "The Infinity Nexus", "narrative": intro + "\n\n**Ten paths shimmer before you:**\n\n⏰ Time Paradox\n🌌 Reality Breach\n⚡ God Slayer\n💀 Soul Collector\n👑 Empire Builder\n🕳️ Void Walker\n🐉 Dragon Ascension\n🔮 Prophecy Breaker\n💕 Love Eternal\n✨ Ultimate Power\n\n**Choose your destiny.**", "location": "The Nexus", "mood": "epic",
                 "choices": [
                     {"label": "Time Paradox Arc", "emoji": "⏰", "hint": "Rewrite history", "result": "You step into the TIMESTREAM.", "next_scene": 1},
                     {"label": "Reality Breach Arc", "emoji": "🌌", "hint": "Multiverse", "result": "You tear reality APART.", "next_scene": 11},
                     {"label": "God Slayer Arc", "emoji": "⚡", "hint": "Deicide", "result": "You challenge the GODS.", "next_scene": 21},
                     {"label": "Soul Collector Arc", "emoji": "💀", "hint": "Morality test", "result": "You harvest SOULS.", "next_scene": 31},
                     {"label": "Empire Builder Arc", "emoji": "👑", "hint": "Conquest", "result": "You build an EMPIRE.", "next_scene": 41},
                     {"label": "Void Walker Arc", "emoji": "🕳️", "hint": "Cosmic horror", "result": "You enter the VOID.", "next_scene": 51},
                     {"label": "Dragon Ascension Arc", "emoji": "🐉", "hint": "Transform", "result": "You become DRAGON.", "next_scene": 61},
                     {"label": "Prophecy Breaker Arc", "emoji": "🔮", "hint": "Fate rebellion", "result": "You DEFY fate.", "next_scene": 71},
                     {"label": "Love Eternal Arc", "emoji": "💕", "hint": "Romance", "result": "You seek TRUE LOVE.", "next_scene": 81},
                     {"label": "Ultimate Power Arc", "emoji": "✨", "hint": "Apotheosis", "result": "You transcend MORTALITY.", "next_scene": 91}
                 ]},
                
                # ARC 1: TIME PARADOX (Scenes 1-10)
                {"title": "Temporal Rift", "narrative": "Past, present, future COLLIDE.\n\nYou see yourself dying. Yesterday. Tomorrow. NOW.\n\n**Save yourself?**", "location": "Time Stream", "mood": "chaotic",
                 "choices": [
                     {"label": "Prevent your death", "emoji": "💚", "hint": "Paradox", "result": "Reality TEARS. You exist twice. Both versions fight!", "flag": "timeline_split", "major": True},
                     {"label": "Let yourself die", "emoji": "💀", "hint": "Accept fate", "result": "You DIE. But consciousness persists. Ghost mode.", "flag": "timeline_ghost"}
                 ]},
                {"title": "Your Past Self", "narrative": "You meet yourself, age 10.\n\nInnocent. Hopeful. Doesn't know the pain coming.\n\n**Warn them?**", "location": "Childhood Home", "npc": "Young You", "mood": "emotional",
                 "challenge": {"type": "Wisdom", "stat": "wis", "dc": 17, "description": "Handle the paradox", "success": "You guide your past self PERFECTLY. Timeline improves!", "failure": "You traumatize child-you. Everything gets WORSE.", "success_consequences": {"xp_gain": 300, "flag": "good_timeline"}, "failure_consequences": {"flag": "dark_timeline"}}},
                {"title": "The Time War", "narrative": "Future YOU attacks! They're trying to stop you from saving the world.\n\n'IT MUST HAPPEN!' they scream.\n\n**Fight yourself?**", "location": "Temporal Battlefield", "mood": "dramatic",
                 "choices": [
                     {"label": "Kill future you", "emoji": "⚔️", "hint": "Paradox++", "result": "You WIN. Future you fades. You feel... wrong. Changed.", "consequences": {"xp_gain": 400}, "flag": "killed_future_self"},
                     {"label": "Listen to them", "emoji": "👂", "hint": "Truth?", "result": "They explain: saving world ENDS universe. What do?", "flag": "learned_truth"}
                 ]},
                {"title": "Grandfather Paradox", "narrative": "You find him. Your grandfather. Before he met grandma.\n\nKill him = you NEVER exist. Universe saved?\n\n**The trolley problem of TIME.**", "location": "1920s", "npc": "Grandfather", "mood": "dark",
                 "choices": [
                     {"label": "Murder grandfather", "emoji": "🔪", "hint": "Save universe", "result": "You do it. You fade... but DON'T. Quantum YOU exists.", "flag": "grandfather_paradox", "major": True, "consequences": {"hp_change": -50}},
                     {"label": "Refuse", "emoji": "❤️", "hint": "Family", "result": "You CAN'T. He's family. Universe be damned.", "flag": "family_over_universe"}
                 ]},
                {"title": "Rewrite History", "narrative": "You have the power now. Rewrite EVERYTHING.\n\nEnd wars. Cure disease. Save everyone.\n\n**But should you?**", "location": "History's Core", "mood": "epic",
                 "challenge": {"type": "Moral Choice", "stat": "int", "dc": 18, "description": "Play God?", "success": "Utopia created! ...Humanity becomes weak. Boring. Wrong.", "failure": "You BREAK history. Everything's chaos now.", "success_consequences": {"flag": "utopia_ending", "xp_gain": 500}, "failure_consequences": {"flag": "chaos_history"}}},
                {"title": "Time Loop Trap", "narrative": "You're STUCK. Repeating today forever.\n\nDied 847 times so far.\n\n**Break the loop?**", "location": "Endless Today", "mood": "horror",
                 "choices": [
                     {"label": "Embrace the loop", "emoji": "♾️", "hint": "Infinity", "result": "You MASTER it. Live forever. Perfect every moment.", "flag": "loop_master", "major": True},
                     {"label": "BREAK FREE", "emoji": "💥", "hint": "Escape", "result": "You SHATTER time itself. Freedom! ...What's the cost?", "flag": "time_breaker"}
                 ]},
                {"title": "Your Future Children", "narrative": "They appear. Your kids. From a future that MIGHT happen.\n\n'Please, parent. Make the choices that lead to US.'\n\n**What do you owe them?**", "location": "Possible Future", "npc": "Future Kids", "mood": "emotional",
                 "challenge": {"type": "Charisma", "stat": "cha", "dc": 16, "description": "Promise them life?", "success": "You SWEAR to create their timeline. Destiny set.", "failure": "You CAN'T guarantee it. They fade, crying.", "success_consequences": {"flag": "promised_family", "companion": "👪 Fated Family"}, "failure_consequences": {"hp_change": -20}}},
                {"title": "Temporal Collapse", "narrative": "TIME IS ENDING.\n\nAll moments happen at once. Birth, death, everything.\n\n**Become time itself?**", "location": "The End of Time", "mood": "cosmic",
                 "choices": [
                     {"label": "Merge with time", "emoji": "⏰", "hint": "Transcend", "result": "You ARE time now. Eternal. Everywhere. Alone.", "flag": "ending_time_god", "major": True, "next_scene": 100},
                     {"label": "Restore normal time", "emoji": "🔄", "hint": "Fix it", "result": "You REPAIR the timeline. Reset. Wake up in bed. Was it real?", "flag": "ending_time_fixed", "next_scene": 100}
                 ]},
                
                # ARC 2: REALITY BREACH (Scenes 11-20)
                {"title": "The Multiverse Opens", "narrative": "INFINITE yous. In infinite worlds.\n\nHero-you. Villain-you. Dead-you. God-you. Ant-you.\n\n**Which is real?**", "location": "Multiverse Nexus", "mood": "surreal",
                 "choices": [
                     {"label": "You're ALL real", "emoji": "👥", "hint": "Accept", "result": "Minds MERGE. You're now a collective consciousness.", "flag": "hive_mind", "major": True},
                     {"label": "Only THIS one is real", "emoji": "☝️", "hint": "Deny", "result": "Other yous SCREAM as they vanish. You remain. Alone.", "flag": "sole_reality"}
                 ]},
                {"title": "Evil You", "narrative": "Alternate you ruled  their world as TYRANT.\n\nNow they want THIS world too.\n\n**Stop yourself?**", "location": "Throne Room", "npc": "Evil You", "mood": "dramatic",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 19, "description": "Fight your darkness", "success": "You DEFEAT evil you. Absorb their power!", "failure": "They WIN. Swap places. You're prisoner now.", "success_consequences": {"xp_gain": 600, "flag": "defeated_evil_self"}, "failure_consequences": {"hp_change": -60, "flag": "imprisoned_by_self"}}},
                {"title": "Perfect World", "narrative": "You find it. Universe where you made ALL right choices.\n\nFamily's alive. Loved. Successful. Happy.\n\n**Stay here?**", "location": "Perfect Earth", "mood": "tempting",
                 "choices": [
                     {"label": "Abandon your world", "emoji": "🏠", "hint": "Stay", "result": "You REPLACE perfect-you. Live their life. It's not really yours.", "flag": "ending_perfect_life", "major": True, "next_scene": 100},
                     {"label": "Return home", "emoji": "💔", "hint": "Duty", "result": "Your world needs you. Even if it's broken. Home is home.", "flag": "loyal_to_reality"}
                 ]},
                {"title": "Reality Virus", "narrative": "Infection spreading. Turns everything FICTIONAL.\n\nPeople becoming characters. Laws of physics= suggestions.\n\n**Cure or embrace?**", "location": "Crumbling  Reality", "mood": "horror",
                 "choices": [
                     {"label": "Cure reality", "emoji": "💉", "hint": "Save it", "result": "You STABILIZE physics. Reality's boring again. Safe.", "flag": "reality_cured"},
                     {"label": "Let it spread", "emoji": "🎭", "hint": "Embrace chaos", "result": "World becomes STORY. You're the narrator now.", "flag": "ending_story_god", "major": True, "next_scene": 100}
                 ]},
                 {"title": "The Quantum Observer", "narrative": "You realize: YOUR observation creates reality.\n\nSchrödinger's everything. Nothing exists until YOU look.\n\n**Power or curse?**", "location": "Quantum Field", "mood": "philosophical",
                 "challenge": {"type": "Intelligence", "stat": "int", "dc": 20, "description": "Understand quantum nature", "success": "You MASTER observation. Create matter with thought!", "failure": "You BREAK. Can't trust if anything's real anymore.", "success_consequences": {"flag": "quantum_master", "companion": "🌠 Reality Shaper"}, "failure_consequences": {"flag": "quantum_madness", "hp_change": -30}}},
                {"title": "Meet Your Creator", "narrative": "You find them. The one who imagined your world.\n\nThey're... disappointed in you?\n\n**What do you say?**", "location": "Outside Reality", "npc": "The Creator", "mood": "meta",
                 "choices": [
                     {"label": "Kill your creator", "emoji": "🔪", "hint": "Freedom", "result": "You MURDER god. Your world becomes REAL. No more author.", "flag": "killed_god", "major": True},
                     {"label": "Thank them", "emoji": "🙏", "hint": "Gratitude", "result": "They smile. 'You're welcome, child.' They give you POWER.", "consequences": {"xp_gain": 800}}
                 ]},
                {"title": "Reality Auction", "narrative": "Multiversal market. Realities for SALE.\n\nYou could BUY a better world. Sell this one.\n\n**Your world's value?**", "location": "The Cosmic Bazaar", "mood": "surreal",
                 "choices": [
                     {"label": "Sell your reality", "emoji": "💰", "hint": "Profit", "result": "Sold! Everyone you know becomes PROPERTY. Including you.", "flag": "sold_reality"},
                     {"label": "Buy a better one", "emoji": "🌟", "hint": "Upgrade", "result": "New reality downloaded. Everything's... artificial. Wrong.", "flag": "bought_reality"},
                     {"label": "Keep your world", "emoji": "❤️", "hint": "Home", "result": "It's flawed. Broken. But it's YOURS. Priceless.", "flag": "kept_reality"}
                 ]},
                {"title": "The False Vacuum", "narrative": "Universe is UNSTABLE. Might collapse any second.\n\nEvery moment could be the last.\n\n**How do you live?**", "location": "Edge of Existence", "mood": "apocalyptic",
                 "challenge": {"type": "Wisdom", "stat": "wis", "dc": 18, "description": "Find meaning in entropy", "success": "You find PEACE. If it ends, it ends beautifully.", "failure": "TERROR consumes you. Every second is agony.", "success_consequences": {"flag": "vacuum_peace", "xp_gain": 500}, "failure_consequences": {"flag": "vacuum_terror", "hp_change": -40}}},
                
                # ARC 3: GOD SLAYER (Scenes 21-30)
                {"title": "The First God", "narrative": "**CHRONOS**, God of Time.\n\nHe sees your thread. Cuts it.\n\nYou SHOULD be dead.\n\n**But you're not.**", "location": "Divine Realm", "npc": "Chronos", "mood": "epic",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 20, "description": "Defy death itself", "success": "You SURVIVE. Chronos IMPRESSED. Offers mentorship.", "failure": "You DIE. Wake in underworld. Journey begins.", "success_consequences": {"companion": "⏰ Chronos (Ally)", "xp_gain": 700}, "failure_consequences": {"flag": "died_once", "hp_change": -70}}},
                {"title": "Godhood Offered", "narrative": "Gods notice you. Strong. Determined. MORTAL.\n\nThey offer: JOIN US. Become divine.\n\n**Accept immortality?**", "location": "Olympus", "mood": "tempting",
                 "choices": [
                     {"label": "Become a god", "emoji": "⚡", "hint": "Power", "result": "You ASCEND. Immortal. Divine. But... still you?", "flag": "minor_deity", "major": True},
                     {"label": "Refuse", "emoji": "✊", "hint": "Stay mortal", "result": "You REJECT. 'I'll beat you AS A HUMAN.' They're intrigued.", "flag": "proud_mortal"}
                 ]},
                {"title": "The Goddess of Love", "narrative": "**APHRODITE** challenges you.\n\n'Can you resist temptation?'\n\nEvery desire made manifest.\n\n**Resist?**", "location": "Temple of Desire", "npc": "Aphrodite", "mood": "seductive",
                 "challenge": {"type": "Willpower", "stat": "wis", "dc": 21, "description": "Resist perfection", "success": "You RESIST. She's SHOCKED. 'You're ready for war.'", "failure": "You YIELD. Weeks lost in pleasure. Gods laugh.", "success_consequences": {"xp_gain": 600, "flag": "resisted_aphrodite"}, "failure_consequences": {"hp_change": -30, "flag": "fell_to_temptation"}}},
                {"title": "War God's Challenge", "narrative": "**ARES** won't let you pass without COMBAT.\n\nFight the GOD OF WAR.\n\n**Impossible?**", "location": "Arena of Mars", "npc": "Ares", "mood": "violent",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 22, "description": "Fight a GOD", "success": "You WOUND him! First mortal ever! Gods FEAR you now!", "failure": "CRUSHED. Every bone broken. You survive... barely.", "success_consequences": {"xp_gain": 900, "item": "⚔️ Godslayer Blade", "flag": "wounded_ares"}, "failure_consequences": {"hp_change": -80, "flag": "broken_by_ares"}}},
                {"title": "Divine Betrayal", "narrative": "Gods SCHEME. They set you against each other.\n\nIF you kill enough gods, they'll make you KING.\n\n**Trust them?**", "location": "Divine Court", "mood": "political",
                 "choices": [
                     {"label": "Play their game", "emoji": "🎭", "hint": "Strategy", "result": "You ACCEPT. Start hunting gods. Easy targets first.", "flag": "god_hunter", "major": True},
                     {"label": "Reject the plot", "emoji": "🚫", "hint": "Honor", "result": "You REFUSE. 'I won't be your pawn.' War begins.", "flag": "independent_slayer"}
                 ]},
                {"title": "The God of Death", "narrative": "**THANATOS** cannot die. By definition.\n\nBut he's tired. SO tired.\n\n'Please. End me.'\n\n**Mercy kill a god?**", "location": "The Underworld", "npc": "Thanatos", "mood": "dark",
                 "choices": [
                     {"label": "Grant him death", "emoji": "💀", "hint": "Mercy", "result": "You KILL Death itself. Universe breaks. Nothing can die now.", "flag": "killed_death", "major": True},
                     {"label": "Refuse", "emoji": "❤️", "hint": "Preserve", "result": "'Thank you. I need to keep working.' He spares you later.", "flag": "death_ally", "companion": "💀 Death (Grateful)"}
                 ]},
                {"title": "Siege of Olympus", "narrative": "You rally an ARMY. Mortals AND gods.\n\nWe storm HEAVEN.\n\n**Final battle.**", "location": "Olympus Gates", "mood": "war",
                 "challenge": {"type": "Leadership", "stat": "cha", "dc": 20, "description": "Lead the siege", "success": "OLYMPUS FALLS! Gods surrender! New age begins!", "failure": "Slaughter. Everyone dies. You alone survive.", "success_consequences": {"xp_gain": 1000, "flag": "conquered_olympus", "major": True}, "failure_consequences": {"flag": "failed_siege", "hp_change": -50}}},
                {"title": "The Titan King", "narrative": "**ZEUS** kneels before YOU.\n\n'Spare me. I'll give you ANYTHING.'\n\nKing of Gods. Helpless.\n\n**What mercy for tyrants?**", "location": "Zeus's Throne", "npc": "Zeus", "mood": "triumphant",
                 "choices": [
                     {"label": "Execute him", "emoji": "⚡", "hint": "Justice", "result": "Lightning DIES. You're GOD EMPEROR now.", "flag": "ending_god_emperor", "major": True, "next_scene": 100},
                     {"label": "Spare him", "emoji": "👑", "hint": "Mercy", "result": "You REFORM pantheon. Gods serve mortals now.", "flag": "ending_divine_peace", "major": True, "next_scene": 100},
                     {"label": "Take his power", "emoji": "💥", "hint": "Usurp", "result": "You ABSORB Zeus. You're the NEW god king.", "flag": "ending_zeus_replaced", "major": True, "next_scene": 100}
                 ]},
                
                # Continue with more arcs... (Due to space, I'll create a condensed version with key scenes)
                # ARC 4-10 will be abbreviated to fit remaining content
                
                # SOUL COLLECTOR Arc (Scenes 31-35)
                {"title": "First Soul", "narrative": "You hold it. Human soul. Dying man's last light.\n\n**Take it?**", "location": "Deathbed", "mood": "dark",
                 "choices": [
                     {"label": "Harvest soul", "emoji": "💀", "result": "Power SURGES. You're dealer of death now.", "flag": "soul_taker", "major": True},
                     {"label": "Let them pass", "emoji": "🕊️", "result": "Soul floats free. You're still human. For now.", "flag": "merciful_reaper"}
                 ]},
                {"title": "Soul Market", "narrative": "Souls have VALUE. You can TRADE them.\n\nRich pay millions for extra life.\n\n**Become merchant of death?**", "location": "Underworld Market", "mood": "capitalist",
                 "choices": [
                     {"label": "Sell souls", "emoji": "💰", "result": "RICH! But damned. So very damned.", "flag": "soul_merchant", "consequences": {"gold_change": 50000}},
                     {"label": "Destroy the market", "emoji": "💥", "result": "You FREE all souls. Market collapses. They hunt you.", "flag": "soul_liberator"}
                 ]},
                {"title": "Your Own Soul", "narrative": "You see it. YOUR soul. For sale. By future-you.\n\n**Buy yourself back?**", "location": "Auction House", "mood": "surreal",
                 "challenge": {"type": "Moral", "stat": "cha", "dc": 19, "description": "Reclaim yourself", "success": "Soul REUNITES! You're whole again!", "failure": "Someone else BUYS you. You're hollow now.", "success_consequences": {"xp_gain": 800, "flag": "soul_whole"}, "failure_consequences": {"flag": "ending_hollow_shell", "next_scene": 100}}},
                
                # EMPIRE BUILDER Arc (Scenes 41-45)
                {"title": "Conquer First City", "narrative": "Army ready. City weak.\n\n**Begin conquest?**", "location": "City Gates", "mood": "war",
                 "challenge": {"type": "Tactics", "stat": "int", "dc": 17, "description": "Win with minimal loss", "success": "VICTORY! City yours. People... survive.", "failure": "Pyrrhic win. City's ash. Subjects HATE you.", "success_consequences": {"flag": "wise_conqueror", "xp_gain": 500}, "failure_consequences": {"flag": "brutal_tyrant"}}},
                {"title": "Crown or Democracy?", "narrative": "Empire grows. People ask: WHO RULES?\n\n**Dictator or liberator?**", "location": "Capital", "mood": "political",
                 "choices": [
                     {"label": "Crown yourself", "emoji": "👑", "result": "EMPEROR! Absolute power! Absolute corruption?", "flag": "emperor_path", "major": True},
                     {"label": "Create democracy", "emoji": "🗳️", "result": "Power to PEOPLE! You're... unemployed now?", "flag": "democratic_leader"}
                 ]},
                {"title": "The Assassination", "narrative": "BETRAYED! Knife in back. Literally.\n\nYou're dying.\n\n**Last words?**", "location": "Senate Floor", "mood": "tragic",
                 "choices": [
                     {"label": "'Et tu, Brute?'", "emoji": "😢", "result": "You die. Successor continues empire. Peaceful.", "flag": "ending_assassinated", "next_scene": 100},
                     {"label": "Survive!", "emoji": "⚔️", "result": "You DON'T die! Kill ALL traitors! PURGE!", "flag": "survived_coup", "major": True}
                 ]},
                
                # VOID WALKER Arc (Scenes 51-55)
                {"title": "Enter the Void", "narrative": "Nothing. Absolute NOTHING.\n\nNo light. No sound. No YOU.\n\n**Survive?**", "location": "The Void", "mood": "horror",
                 "challenge": {"type": "Sanity", "stat": "wis", "dc": 22, "description": "Keep your mind", "success": "You ENDURE. Void's yours now.", "failure": "Void takes YOU. Mind shatters.", "success_consequences": {"flag": "void_master", "xp_gain": 900}, "failure_consequences": {"flag": "void_mad"}}},
                {"title": "Things Beyond", "narrative": "They live here. Things without NAME.\n\nThey notice you.\n\n**Run or communicate?**", "location": "Beyond Reality", "mood": "cosmic_horror",
                 "choices": [
                     {"label": "Communicate", "emoji": "👁️", "result": "CONTACT! They teach you. You're CHANGED forever.", "flag": "eldritch_knowledge", "major": True},
                     {"label": "FLEE!", "emoji": "🏃", "result": "You ESCAPE! But they KNOW you now. They'll visit.", "flag": "marked_by_void"}
                 ]},
                
                # DRAGON Arc (Scenes 61-65)
                {"title": "Dragon Ritual", "narrative": "Ancient magic. Transform you into DRAGON.\n\n**Become monster?**", "location": "Dragon Temple", "mood": "transformative",
                 "challenge": {"type": "Will", "stat": "wis", "dc": 20, "description": "Keep humanity", "success": "Dragon body, human heart. PERFECT!", "failure": "Full dragon. Mind gone. Only instinct.", "success_consequences": {"flag": "dragon_hybrid", "item": "🐉 Dragon Form"}, "failure_consequences": {"flag": "ending_feral_dragon", "next_scene": 100}}},
                {"title": "Dragon Hoard", "narrative": "GOLD! Mountains of it! Dragon-you needs MORE!\n\n**Give in to greed?**", "location": "Your Hoard", "mood": "tempting",
                 "choices": [
                     {"label": "Hoard everything", "emoji": "💰", "result": "You're RICH! Can't remember why you wanted it.", "flag": "greedy_dragon"},
                     {"label": "Share wealth", "emoji": "❤️", "result": "You GIVE it away. Weirdest dragon ever.", "flag": "generous_dragon", "consequences": {"gold_change": -100000, "reputation": {"World": 300}}}
                 ]},
                
                # PROPHECY BREAKER Arc (Scenes 71-75)
                {"title": "Read Your Fate", "narrative": "Prophecy says: YOU WILL FAIL.\n\nDestiny's written. Unchangeable.\n\n**Prove it wrong?**", "location": "Oracle's Cave", "npc": "The Oracle", "mood": "defiant",
                 "choices": [
                     {"label": "Accept fate", "emoji": "😔", "result": "You... give up. Prophecy wins.", "flag": "ending_prophesied_failure", "next_scene": 100},
                     {"label": "DEFY PROPHECY", "emoji": "✊", "result": "You REBEL! Fate itself trembles!", "flag": "fate_breaker", "major": True}
                 ]},
                {"title": "Kill the Author", "narrative": "You find them. The one who WROTE your failure.\n\n**Erase your fate?**", "location": "Book of Destiny", "mood": "meta",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 23, "description": "Fight DESTINY", "success": "DESTINY DIES! You write yourself now!", "failure": "Fate WINS. You're bound forever.", "success_consequences": {"flag": "ending_self_written", "xp_gain": 1500}, "failure_consequences": {"flag": "prophecy_fulfilled"}}},
                
                # LOVE ETERNAL Arc (Scenes 81-85)
                {"title": "Meet Your Soulmate", "narrative": "They're PERFECT. Literally made for you.\n\nBut... destiny forced this. Real love?\n\n**Trust fate?**", "location": "Destiny Meeting", "npc": "Soulmate", "mood": "romantic",
                 "choices": [
                     {"label": "Love them", "emoji": "❤️", "result": "You LOVE! Deeply! Is it choice or programming?", "flag": "fated_love", "major": True},
                     {"label": "Walk away", "emoji": "💔", "result": "You REJECT soulmate. Choose freedom over fate.", "flag": "chose_freedom"}
                 ]},
                {"title": "Love or Power", "narrative": "Choice time. Save lover OR save world.\n\nClassic.\n\n**What do you choose?**", "location": "Final Choice", "mood": "dramatic",
                 "choices": [
                     {"label": "Save lover", "emoji": "💕", "result": "World ENDS. But you're together. Forever.", "flag": "ending_love_won", "major": True, "next_scene": 100},
                     {"label": "Save world", "emoji": "🌍", "result": "Lover DIES. World lives. You're broken.", "flag": "ending_hero_alone", "major": True, "next_scene": 100}
                 ]},
                
                # ULTIMATE POWER Arc (Scenes 91-99)
                {"title": "The Final Power", "narrative": "OMNIPOTENCE. Right there.\n\nBecome GOD. True God.\n\n**Take it?**", "location": "Source", "mood": "cosmic",
                 "choices": [
                     {"label": "Become GOD", "emoji": "✨", "result": " You ASCEND. Omnipotent. Omniscient. ALONE.", "flag": "ending_became_god", "major": True, "next_scene": 100},
                     {"label": "Destroy the power", "emoji": "💥", "result": "You END godhood. Everyone's equal now. Free.", "flag": "ending_killed_power", "major": True, "next_scene": 100},
                     {"label": "Share it", "emoji": "🤝", "result": "EVERYONE becomes god. Universe of equals.", "flag": "ending_shared_divinity", "major": True, "next_scene": 100}
                 ]},
                
                # SCENE 100: EPILOGUE HUB
                {"title": "The End?", "narrative": "Your journey ends.\n\nOr does it?\n\nInfinity has NO end.\n\n**What was it all for?**", "location": "The Nexus", "mood": "reflective",
                 "choices": [
                     {"label": "Try again", "emoji": "🔄", "result": "Nexus RESETS. New choices. New you. Forever.", "next_scene": 0},
                     {"label": "Accept the ending", "emoji": "✅", "result": "Story ENDS. Finally. Peace.", "flag": "true_ending"}
                 ]}
            ],
            
            # 30 RANDOM ENCOUNTERS - Chaos incarnate!
            "random_encounters": [
                {"id": "doppelganger", "title": "Your Clone Attacks", "type": "Combat", "narrative": "Another YOU appears! Evil twin?",
                 "challenge": {"stat": "str", "dc": 16, "success": "You WIN! Absorb clone's power!", "failure": "Clone escapes. They're plotting.",
"success_consequences": {"xp_gain": 200}, "failure_consequences": {"flag": "evil_twin_loose"}}},
                {"id": "time_freeze", "title": "Time Stops", "type": "Temporal", "narrative": "World FREEZES. Only you move. Why?",
                 "challenge": {"stat": "int", "dc": 18, "success": "You understand! Control time!", "failure": "Stuck in frozen world!",
"success_consequences": {"item": "⏰ Time Stop", "xp_gain": 300}, "failure_consequences": {"hp_change": -20}}},
                {"id": "deity_visit", "title": "God Says Hi", "type": "Divine", "narrative": "Random god appears. 'Just checking in!'",
                 "challenge": {"stat": "cha", "dc": 15, "success": "God likes you! Blessing!", "failure": "God annoyed. Curse!",
"success_consequences": {"companion": "⚡ Divine Favor"}, "failure_consequences": {"hp_change": -15}}},
                {"id": "memory_loss", "title": "Who Am I?", "type": "Mind", "narrative": "Can't remember... anything. WHO ARE YOU?",
                 "challenge": {"stat": "wis", "dc": 17, "success": "Memories RETURN! Plus bonus memories!", "failure": "Still confused. Wrong memories?",
"success_consequences": {"xp_gain": 250}, "failure_consequences": {"flag": "memory_corrupted"}}},
                {"id": "lottery", "title": "Cosmic Lottery", "type": "Luck", "narrative": "Universal lottery! You have a ticket!",
                 "challenge": {"stat": "int", "dc": 14, "success": "JACKPOT! Infinite gold!", "failure": "Lost. Owe money now?",
"success_consequences": {"gold_change": 100000}, "failure_consequences": {"gold_change": -5000}}},
                {"id": "alternate", "title": "Wrong Universe", "type": "Reality", "narrative": "This isn't YOUR universe. Whoops.",
                 "challenge": {"stat": "int", "dc": 16, "success": "Find way HOME!", "failure": "Stuck here forever?",
"success_consequences": {"xp_gain": 200}, "failure_consequences": {"flag": "wrong_universe"}}},
                {"id": "soulmate_ghost", "title": "Dead Lover Appears", "type": "Romance", "narrative": "Past love. Dead. Visiting. For closure?",
                 "challenge": {"stat": "cha", "dc": 18, "success": "Beautiful goodbye. Peace.", "failure": "Haunted forever.",
"success_consequences": {"xp_gain": 300}, "failure_consequences": {"hp_change": -10, "flag": "haunted"}}},
                {"id": "power_surge", "title": "Random Power Up", "type": "Buff", "narrative": "ENERGY! You're SUPER CHARGED!",
                 "challenge": {"stat": "wis", "dc": 13, "success": "Control it! Permanent!", "failure": "Burns out. Hurt.",
"success_consequences": {"xp_gain": 500}, "failure_consequences": {"hp_change": -30}}},
                {"id": "trial", "title": "Cosmic Trial", "type": "Legal", "narrative": "Sued by UNIVERSE. For existing!",
                 "challenge": {"stat": "cha", "dc": 19, "success": "Case DISMISSED!", "failure": "GUILTY! Fined.",
"success_consequences": {"xp_gain": 400}, "failure_consequences": {"gold_change": -10000}}},
                {"id": "wish", "title": "Genie Appears", "type": "Magic", "narrative": "Three wishes! Classic!",
                 "challenge": {"stat": "int", "dc": 20, "success": "Perfect wishes! No tricks!", "failure": "Wishes backfire!",
"success_consequences": {"gold_change": 50000, "xp_gain": 500}, "failure_consequences": {"hp_change": -40}}},
                {"id": "apocalypse", "title": "Mini Apocalypse", "type": "Disaster", "narrative": "World ending! Briefly!",
                 "challenge": {"stat": "str", "dc": 17, "success": "You STOP it!", "failure": "World damaged.",
"success_consequences": {"xp_gain": 600}, "failure_consequences": {"reputation": {"World": -100}}}},
                {"id": "prophet", "title": "Prophecy About You", "type": "Destiny", "narrative": "Oracle speaks YOUR name!",
                 "challenge": {"stat": "wis", "dc": 15, "success": "Good prophecy!", "failure": "Doom prophecy!",
"success_consequences": {"companion": "🔮 Blessed Fate"}, "failure_consequences": {"flag": "doomed"}}},
                {"id": "army_yours", "title": "Instant Army", "type": "Military", "narrative": "Army pledges to YOU! Random!",
                 "challenge": {"stat": "cha", "dc": 16, "success": "Lead them GLORIOUSLY!", "failure": "Mutiny immediately.",
"success_consequences": {"companion": "⚔️ Legion", "xp_gain": 400}, "failure_consequences": {}}},
                {"id": "love_potion", "title": "Love Potion Effect", "type": "Romance", "narrative": "Everyone LOVES you! Potion?",
                 "challenge": {"stat": "wis", "dc": 14, "success": "Cure it! Real love only!", "failure": "Fake love forever.",
"success_consequences": {}, "failure_consequences": {"flag": "cursed_love"}}},
                {"id": "body_swap", "title": "Body Swap", "type": "Chaos", "narrative": "You're in WRONG body! Stranger's!",
                 "challenge": {"stat": "int", "dc": 18, "success": "Swap BACK!", "failure": "Permanent swap?",
"success_consequences": {"xp_gain": 300}, "failure_consequences": {"flag": "wrong_body"}}},
                {"id": "confession", "title": "NPC Confession", "type": "Social", "narrative": "Random NPC: 'I love you!' Huh?",
                 "challenge": {"stat": "cha", "dc": 13, "success": "Handle it kindly!", "failure": "Break their heart.",
"success_consequences": {"reputation": {"People": 50}}, "failure_consequences": {}}},
                {"id": "rich", "title": "Inheritance", "type": "Wealth", "narrative": "Rich uncle died! You inherit!",
                 "challenge": {"stat": "int", "dc": 12, "success": "Legitimate! Keep it!", "failure": "Tax fraud! Fined!",
"success_consequences": {"gold_change": 75000}, "failure_consequences": {"gold_change": -30000}}},
                {"id": "prison", "title": "Wrongly Imprisoned", "type": "Crisis", "narrative": "Arrested! You didn't do it!",
                 "challenge": {"stat": "cha", "dc": 17, "success": "Prove innocence!", "failure": "Life sentence!",
"success_consequences": {"xp_gain": 200}, "failure_consequences": {"flag": "imprisoned"}}},
                {"id": "dragon_baby", "title": "Dragon Egg Hatches", "type": "Companion", "narrative": "Egg hatches! Baby dragon!",
                 "challenge": {"stat": "cha", "dc": 14, "success": "It imprints! Companion!", "failure": "It flies away.",
"success_consequences": {"companion": "🐲 Baby Dragon"}, "failure_consequences": {}}},
                {"id": "plague", "title": "Plague Star", "type": "Survival", "narrative": "Sickness spreads! Are you immune?",
                 "challenge": {"stat": "wis", "dc": 16, "success": "Immune! Cure others!", "failure": "Infected! Dying!",
"success_consequences": {"xp_gain": 400}, "failure_consequences": {"hp_change": -50}}},
                {"id": "revolution", "title": "Lead Revolution", "type": "Politics", "narrative": "People BEG you: LEAD US!",
                 "challenge": {"stat": "cha", "dc": 19, "success": "FREEDOM! New government!", "failure": "Crushed. Scattered.",
"success_consequences": {"xp_gain": 700}, "failure_consequences": {"hp_change": -30}}},
                {"id": "time_child", "title": "Your Future Kid", "type": "Temporal", "narrative": "Kid from future! It's YOURS!",
                 "challenge": {"stat": "wis", "dc": 15, "success": "Accept them! Family!", "failure": "Send them back.",
"success_consequences": {"companion": "👶 Future Child"}, "failure_consequences": {}}},
                {"id": "magic_surge", "title": "Wild Magic Surge", "type": "Magic", "narrative": "CHAOS MAGIC! Random effect!",
                 "challenge": {"stat": "int", "dc": 17, "success": "Good effect!", "failure": "Bad effect!",
"success_consequences": {"xp_gain": 300}, "failure_consequences": {"hp_change": -20}}},
                {"id": "marriage", "title": "Arranged Marriage", "type": "Social", "narrative": "Kingdom demands you MARRY!",
                 "challenge": {"stat": "cha", "dc": 16, "success": "They're actually nice!", "failure": "Nightmare spouse!",
"success_consequences": {"companion": "💍 Spouse"}, "failure_consequences": {"flag": "bad_marriage"}}},
                {"id": "ascension", "title": "Random Ascension", "type": "Divine", "narrative": "You're ASCENDING! Why now?",
                 "challenge": {"stat": "wis", "dc": 20, "success": "controlled ascension!", "failure": "Wild god mode!",
"success_consequences": {"xp_gain": 1000}, "failure_consequences": {"flag": "unstable_god"}}},
                {"id": "reset", "title": "Reality Reset", "type": "Cosmic", "narrative": "Everything RESETS! Memories intact?",
                 "challenge": {"stat": "int", "dc": 21, "success": "You REMEMBER! Advantage!", "failure": "Forgot everything!",
"success_consequences": {"xp_gain": 600}, "failure_consequences": {"flag": "reset_victim"}}},
                {"id": "mirror", "title": "Mirror World", "type": "Reality", "narrative": "Mirror universe! Everything's OPPOSITE!",
                 "challenge": {"stat": "int", "dc": 16, "success": "Navigate it!", "failure": "Trapped!",
"success_consequences": {"xp_gain": 350}, "failure_consequences": {"flag": "mirror_trapped"}}},
                {"id": "offer", "title": "Devil's Bargain", "type": "Moral", "narrative": "Devil offers ANYTHING. Cost: soul.",
                 "challenge": {"stat": "wis", "dc": 18, "success": "Refuse! Keep soul!", "failure": "DEAL! Damned!",
"success_consequences": {"xp_gain": 500}, "failure_consequences": {"flag": "soul_sold", "gold_change": 1000000}}},
                {"id": "nightmare", "title": "Nightmare Realm", "type": "Horror", "narrative": "Trapped in dreams! Escape!",
                 "challenge": {"stat": "wis", "dc": 17, "success": "WAKE UP!", "failure": "Still dreaming?",
"success_consequences": {"xp_gain": 300}, "failure_consequences": {"flag": "inception"}}},
                {"id": "hero", "title": "Proclaimed Hero", "type": "Fame", "narrative": "Everyone thinks you SAVED them!",
                 "challenge": {"stat": "cha", "dc": 13, "success": "Play along! Fame!", "failure": "Deny it. Confusion.",
"success_consequences": {"reputation": {"World": 200}}, "failure_consequences": {}}}
            ],
            
            # 20 SIDE QUESTS - Game changers!
            "side_quests": [
                {"id": "unlock_arc", "title": "Unlock Hidden Arc", "narrative": "Secret 11th questline! Discover it!",
                 "rewards_hint": "🗝️ Secret Path", "challenge": {"stat": "int", "dc": 22, "success": "11TH ARC UNLOCKED!", "failure": "Remains hidden.",
"success_consequences": {"flag": "secret_arc_unlocked", "xp_gain": 1000}, "failure_consequences": {}}},
                {"id": "time_master", "title": "Master Time", "narrative": "Learn to control time itself!",
                 "rewards_hint": "⏰ Time Lord", "challenge": {"stat": "int", "dc": 23, "success": "TIME MASTERED!", "failure": "Time controls YOU!",
"success_consequences": {"companion": "⏰ Time Mastery", "xp_gain": 1200}, "failure_consequences": {"flag": "time_cursed"}}},
                {"id": "gather_souls", "title": "Collect 1000 Souls", "narrative": "Harvest enough souls for RITUAL!",
                 "rewards_hint": "💀 Dark Power", "challenge": {"stat": "wis", "dc": 20, "success": "POWER! But at what cost?", "failure": "Souls escape!",
"success_consequences": {"item": "💀 Soul Crown", "xp_gain": 1500}, "failure_consequences": {}}},
                {"id": "romance_all", "title": "Romance Every NPC", "narrative": "Love conquers all! Everyone!",
                 "rewards_hint": "💕 Harem Ending", "challenge": {"stat": "cha", "dc": 21, "success": "Everyone loves you! CHAOS!", "failure": "Everyone fights over you!",
"success_consequences": {"flag": "harem_unlocked", "xp_gain": 800}, "failure_consequences": {"hp_change": -40}}},
                {"id": "slay_all", "title": "Kill Every God", "narrative": "Complete deicide! ALL of them!",
                 "rewards_hint": "⚡ Godslayer", "challenge": {"stat": "str", "dc": 25, "success": "PANTHEON DESTROYED!", "failure": "Gods unite against you!",
"success_consequences": {"flag": "killed_all_gods", "item": "⚡ Deicide Blade", "xp_gain": 2000}, "failure_consequences": {"hp_change": -90}}},
                {"id": "build_empire", "title": "Conquer 50 Cities", "narrative": "Build TRUE empire!",
                 "rewards_hint": "👑 Empire", "challenge": {"stat": "int", "dc": 20, "success": "EMPIRE BUILT! You're emperor!", "failure": "Rebellion!",
"success_consequences": {"flag": "true_emperor", "companion": "👑 Empire", "xp_gain": 1800}, "failure_consequences": {}}},
                {"id": "merge_souls", "title": "Merge With Everyone", "narrative": "Collective consciousness! BE EVERYONE!",
                 "rewards_hint": "👁️ Hive Mind", "challenge": {"stat": "wis", "dc": 24, "success": "You're EVERYONE now!", "failure": "Identity lost!",
"success_consequences": {"flag": "ending_hive_mind", "xp_gain": 2500}, "failure_consequences": {"flag": "ego_death"}}},
                {"id": "break_game", "title": "Break the Fourth Wall", "narrative": "Realize you're in a GAME!",
                 "rewards_hint": "🎮 Meta Knowledge", "challenge": {"stat": "int", "dc": 23, "success": "You know EVERYTHING!", "failure": "Existential crisis!",
"success_consequences": {"flag": "meta_aware", "companion": "🎮 Game Master", "xp_gain": 3000}, "failure_consequences": {"flag": "existential_horror"}}},
                {"id": "save_everyone", "title": "Save Every NPC", "narrative": "No one dies! Perfect ending!",
                 "rewards_hint": "❤️ True Hero", "challenge": {"stat": "cha", "dc": 22, "success": "Everyone LIVES! Perfect!", "failure": "Some die anyway.",
"success_consequences": {"flag": "perfect_ending", "xp_gain": 2000}, "failure_consequences": {}}},
                {"id": "destroy_everything", "title": "Destroy All Reality", "narrative": "END IT ALL! Total annihilation!",
                 "rewards_hint": "💥 Oblivion", "challenge": {"stat": "str", "dc": 25, "success": "EVERYTHING ENDS!", "failure": "Can't do it. Too much.",
"success_consequences": {"flag": "ending_destroyed_all", "xp_gain": 5000}, "failure_consequences": {}}},
                {"id": "find_creator", "title": "Find Your Creator", "narrative": "Meet the one who made you!",
                 "rewards_hint": "👁️ Truth", "challenge": {"stat": "int", "dc": 24, "success": "You find them! TRUTH!", "failure": "They don't exist?",
"success_consequences": {"flag": "met_creator", "xp_gain": 3000}, "failure_consequences": {}}},
                {"id": "become_villain", "title": "Full Villain Arc", "narrative": "Be EVIL! Completely!",
                 "rewards_hint": "😈 Dark Lord", "challenge": {"stat": "cha", "dc": 19, "success": "DARK LORD! Evil wins!", "failure": "Redeemed despite efforts!",
"success_consequences": {"flag": "ending_dark_lord", "xp_gain": 1500}, "failure_consequences": {}}},
                {"id": "pacifist", "title": "Never Kill Anyone", "narrative": "Complete pacifist run!",
                 "rewards_hint": "🕊️ Peace", "challenge": {"stat": "cha", "dc": 23, "success": "NO KILLS! Moral victory!", "failure": "Had to kill someone.",
"success_consequences": {"flag": "ending_pacifist", "xp_gain": 2000}, "failure_consequences": {}}},
                {"id": "speedrun", "title": "Complete in 30 Min", "narrative": "SPEEDRUN mode!",
                 "rewards_hint": "⚡ Fast", "challenge": {"stat": "dex", "dc": 21, "success": "SPEEDRUN COMPLETE!", "failure": "Too slow!",
"success_consequences": {"flag": "speedrunner", "xp_gain": 1000}, "failure_consequences": {}}},
                {"id": "collect_all", "title": "Collect All Items", "narrative": "100% completion!",
                 "rewards_hint": "💎 Collector", "challenge": {"stat": "int", "dc": 20, "success": "ALL ITEMS! Complete!", "failure": "Missing some.",
"success_consequences": {"flag": "completionist", "xp_gain": 1500}, "failure_consequences": {}}},
                {"id": "marry_death", "title": "Romance Death", "narrative": "Seduce the Grim Reaper!",
                 "rewards_hint": "💀💕 Eternal Love", "challenge": {"stat": "cha", "dc": 24, "success": "Death LOVES you! Immortal!", "failure": "Death friendzones you.",
"success_consequences": {"flag": "married_death", "companion": "💀 Death (Spouse)", "xp_gain": 2000}, "failure_consequences": {}}},
                {"id": "solve_puzzle", "title": "Solve Ultimate Riddle", "narrative": "The question of EVERYTHING!",
                 "rewards_hint": "🧩 Answer", "challenge": {"stat": "int", "dc": 25, "success": "42! The answer is 42!", "failure": "No answer exists?",
"success_consequences": {"flag": "answered_ultimate", "xp_gain": 5000}, "failure_consequences": {}}},
                {"id": "die_100", "title": "Die 100 Times", "narrative": "Death COUNT achievement!",
                 "rewards_hint": "💀 Unkillable", "challenge": {"stat": "str", "dc": 15, "success": "100 deaths! RESPAWN MASTER!", "failure": "Not dead enough.",
"success_consequences": {"flag": "death_master", "item": "💀 Phoenix Soul", "xp_gain": 800}, "failure_consequences": {}}},
                {"id": "betray_all", "title": "Betray Everyone", "narrative": "Trust no one! Betray ALL!",
                 "rewards_hint": "🗡️ Lone Wolf", "challenge": {"stat": "cha", "dc": 18, "success": "ALL BETRAYED! You're ALONE!", "failure": "Someone still trusts you.",
"success_consequences": {"flag": "ending_betrayer", "xp_gain": 1200}, "failure_consequences": {}}},
                {"id": "find_love", "title": "Find True Love", "narrative": "Real, genuine love! Not fated!",
                 "rewards_hint": "❤️ Soulmate", "challenge": {"stat": "cha", "dc": 20, "success": "TRUE LOVE FOUND!", "failure": "Still searching...",
"success_consequences": {"flag": "ending_true_love", "companion": "❤️ True Love", "xp_gain": 2000}, "failure_consequences": {}}}
            ],
            
            # 30 ENDINGS - All possible conclusions!
            "endings": {
                "ending_time_god": {"requires": {"ending_time_god": True}, "narrative": "⏰ **BECAME TIME ITSELF**\n\nYou ARE time now. Every moment. Forever. Eternal loneliness."},
                "ending_time_fixed": {"requires": {"ending_time_fixed": True}, "narrative": "🔄 **RESET TIMELINE**\n\nWas it all a dream? Time's stable. You wake in bed. Memories... fading."},
                "ending_perfect_life": {"requires": {"ending_perfect_life": True}, "narrative": "🏠 **STOLE PERFECT LIFE**\n\nYou live someone else's perfect life. It's beautiful. But it's not yours."},
                "ending_story_god": {"requires": {"ending_story_god": True}, "narrative": "🎭 **NARRATOR**\n\nReality's a story. You write it. Every character. Every plot. Infinite power."},
                "ending_god_emperor": {"requires": {"ending_god_emperor": True}, "narrative": "⚡ **GOD EMPEROR**\n\nGods bow. Mortals worship. You rule EVERYTHING. Lonely  at the top."},
                "ending_divine_peace": {"requires": {"ending_divine_peace": True}, "narrative": "🕊️ **REFORMED HEAVEN**\n\nGods serve mortals now. Peace. Balance. You're remembered as savior."},
                "ending_zeus_replaced": {"requires": {"ending_zeus_replaced": True}, "narrative": "👑 **NEW ZEUS**\n\nYou're god-king now. Thunder yours. Olympus yours. Will you be better?"},
                "ending_hollow_shell": {"requires": {"ending_hollow_shell": True}, "narrative": "💔 **SOLD SOUL**\n\nNo soul. Just meat. You function. But you're EMPTY. Forever."},
                "ending_assassinated": {"requires": {"ending_assassinated": True}, "narrative": "🗡️ **ET TU?**\n\nBetrayed. Dying. But empire continues. Was it worth it? You'll never know."},
                "ending_prophesied_failure": {"requires": {"ending_prophesied_failure": True}, "narrative": "📜 **PROPHECY FULFILLED**\n\nYou failed. Just as written. Fate wins. Destiny unbreakable."},
                "ending_self_written": {"requires": {"ending_self_written": True}, "narrative": "✍️ **WROTE YOUR FATE**\n\nDestiny DEAD. You write yourself  now. Free will  achieved!"},
                "ending_love_won": {"requires": {"ending_love_won": True}, "narrative": "💕 **LOVE OVER ALL**\n\nWorld ended. But you're together. Forever in ruins. Worth it."},
                "ending_hero_alone": {"requires": {"ending_hero_alone": True}, "narrative": "😢 **LONELY HERO**\n\nSaved world. Lost love. Heroes walk alone. Always."},
                "ending_became_god": {"requires": {"ending_became_god": True}, "narrative": "✨ **OMNIPOTENCE**\n\nYou're GOD. True God. All-powerful. All-knowing. All-ALONE."},
                "ending_killed_power": {"requires": {"ending_killed_power": True}, "narrative": "💥 **DESTROYED GODHOOD**\n\nNo more gods. Everyone's mortal. Equal. Free. Beautiful."},
                "ending_shared_divinity": {"requires": {"ending_shared_divinity": True}, "narrative": "🌟 **EVERYONE'S GOD**\n\nShared power. Universe of equals. True democracy achieved."},
                "ending_feral_dragon": {"requires": {"ending_feral_dragon": True}, "narrative": "🐉 **BECAME BEAST**\n\nFull dragon. Mind gone. Just instinct. You don't remember being human."},
                "ending_hive_mind": {"requires": {"ending_hive_mind": True}, "narrative": "👁️ **COLLECTIVE**\n\nNo more 'I'. Only 'WE'. Everyone's you. You're everyone. Unity."},
                "perfect_ending": {"requires": {"perfect_ending": True}, "narrative": "🏆 **PERFECT GAME**\n\nEveryone saved. Everyone happy. 100% completion. TRUE ending."},
                "ending_destroyed_all": {"requires": {"ending_destroyed_all": True}, "narrative": "💥 **OBLIVION**\n\nEverything's gone. No universe. No you. Only void. Peace?"},
                "ending_dark_lord": {"requires": {"ending_dark_lord": True}, "narrative": "😈 **EVIL TRIUMPHS**\n\nVillain ending. You WON. World kneels. Darkness eternal."},
                "ending_pacifist": {"requires": {"ending_pacifist": True}, "narrative": "🕊️ **NEVER KILLED**\n\nComplete pacifist. Moral perfection. Peace through action."},
                "ending_betrayer": {"requires": {"ending_betrayer": True}, "narrative": "🗡️ **TRUST NO ONE**\n\nBetrayed everyone. Alone. Rich. Empty. Was it worth it?"},
                "ending_true_love": {"requires": {"ending_true_love": True}, "narrative": "❤️ **FOUND TRUE LOVE**\n\nReal love. Not fated. Chosen. Beautiful. Happy ending."},
                "married_death": {"requires": {"married_death": True}, "narrative": "💀💕 **MARRIED DEATH**\n\nSpouse: Grim Reaper. Weird. But you're immortal now!"},
                "speedrunner": {"requires": {"speedrunner": True}, "narrative": "⚡ **SPEEDRUN WR**\n\nWorld record! Infinity% any% speedrun complete!"},
                "meta_aware": {"requires": {"meta_aware": True}, "narrative": "🎮 **KNOWS IT'S A GAME**\n\n'Thanks for playing!' You see the credits. You're FREE?"},
                "killed_all_gods": {"requires": {"killed_all_gods": True}, "narrative": "⚡ **GODSLAYER**\n\nEvery god DEAD. Pantheons empty. You're the only divine left."},
                "true_emperor": {"requires": {"true_emperor": True}, "narrative": "👑 **EMPEROR OF ALL**\n\n50 cities. Millions of subjects. True empire built."},
                "default": "🌌 **INFINITY CONTINUES**\n\nOne story ends. Infinite others remain. The Nexus waits. Always."
            }
        }
    
    # Additional campaign generators
    def _gen_war_campaign(self, char_class: str = None) -> dict:
        """War strategy campaign - STR focused - 20 MAIN SCENES + 15 ENCOUNTERS + 12 SIDE QUESTS = 47 TOTAL!"""
        intro = f"War came to your village on a gray morning. The King's soldiers conscript everyone.\\n\\n"
        if char_class == 'warrior':
            intro += "**As a warrior**, you volunteered BEFORE the draft. You seek glory."
        elif char_class == 'mage':
            intro += "**As a mage**, you're recruited for the Battle Mages division."
        elif char_class == 'rogue':
            intro += "**As a rogue**, you plan to use this war for profit."
        elif char_class == 'cleric':
            intro += "**As a cleric**, you joined to HEAL, not kill."
        elif char_class == 'ranger':
            intro += "**As a ranger**, duty binds you despite loving the wilds."
        elif char_class == 'paladin':
            intro += "**As a paladin**, you swore to protect the innocent."
        
        return {
            "name": "The Blood Crown Wars",
            "type": "Military Strategy",
            "scenes": [
                # ACT 1: RECRUITMENT (Scenes 1-5)
                {"title": "The Draft", "narrative": intro + "\\n\\nThree kingdoms fight. Only one survives.", "location": "Your Village", "mood": "dark",
                 "choices": [
                     {"label": "Join willingly for glory", "emoji": "⚔️", "hint": "Become a soldier", "result": "The captain approves. You'll make sergeant soon.", "consequences": {"reputation": {"Army": 15}, "xp_gain": 20}, "flag": "loyal_soldier", "major": True},
                     {"label": "Go reluctantly", "emoji": "🛡️", "hint": "Survive first", "result": "One more face in the crowd.", "consequences": {"gold_change": 25}},
                     {"label": "Plan to desert later", "emoji": "🏃", "hint": "This isn't your war", "result": "You'll run when ready.", "consequences": {"reputation": {"Army": -10}}, "flag": "deserter_plan", "major": True}
                 ]},
                {"title": "The March to Fort Ironpeak", "narrative": "A week's march through mud and rain. Soldiers fall sick. Morale is low.\n\nYou meet **Sergeant Kross**, a grizzled veteran who's survived 12 battles.", "location": "Road to Fort", "npc": "Sergeant Kross", "mood": "tense",
                 "choices": [
                     {"label": "Ask Kross for advice", "emoji": "💬", "hint": "Learn from the best", "result": "He shares survival tactics. '**Stay low, move fast, trust no one.**'", "consequences": {"xp_gain": 30}, "flag": "kross_mentor"},
                     {"label": "Help the sick soldiers", "emoji": "🏥", "hint": "Build reputation", "result": "You earn respect. Soldiers remember kindness.", "consequences": {"reputation": {"Soldiers": 20}}},
                     {"label": "Keep to yourself", "emoji": "🔇", "hint": "Lone wolf", "result": "You stay isolated. Safer but lonelier.", "consequences": {}}
                 ]},
                {"title": "Fort Ironpeak - Arrival", "narrative": "The fortress is MASSIVE. 30,000 soldiers train here.\\n\\n**Three divisions:** Infantry (front lines), Archers (ranged), Cavalry (elite).\\n\\nWhich do you join?", "location": "Fort Ironpeak", "mood": "hopeful",
                 "choices": [
                     {"label": "Infantry - the backbone", "emoji": "🛡️", "hint": "Most dangerous", "result": "You're assigned to the shield wall. High casualty rate.", "flag": "infantry", "major": True},
                     {"label": "Archers - safer distance", "emoji": "🏹", "hint": "Balanced", "result": "Ranged combat. Less glory, better survival odds.", "flag": "archer"},
                     {"label": "Cavalry - the elite", "emoji": "🐎", "hint": "If accepted", "result": "You must prove yourself worthy. Challenge upcoming!", "flag": "cavalry", "major": True}
                 ]},
                {"title": "Training - Week 1", "narrative": "Dawn drills. Combat practice. Tactical lessons.\\n\\nKross pushes you hard. '**Most of you will die in 2 weeks. My job: keep SOME alive.**'", "location": "Training Grounds", "mood": "tense",
                 "challenge": {"type": "Endurance", "stat": "str" if char_class == "warrior" else "dex", "dc": 12, "description": "Survive brutal training", "success": "You excel. Kross nods approval.", "failure": "You collapse. Recover slower.", "success_consequences": {"xp_gain": 50, "hp_change": 10}, "failure_consequences": {"hp_change": -15}}},
                {"title": "The Tavern Night", "narrative": "Off-duty. Local tavern. Soldiers drink, gamble, fight.\\n\\nYou meet **Mira** (archer), **Torren** (infantry), **Elys** (field medic).\\n\\nThey could be your squad... or not.", "location": "Soldier's Respite Tavern", "npc": "Potential Squad", "mood": "peaceful",
                 "choices": [
                     {"label": "Join them - form a squad", "emoji": "🤝", "hint": "Strength in numbers", "result": "You bond over drinks and stories. **Squad Ironheart** forms!", "consequences": {"companion": "Squad Ironheart: Mira, Torren, Elys"}, "flag": "squad_formed", "major": True},
                     {"label": "Gamble and make coin", "emoji": "🎲", "hint": "Get rich", "result": "You win 200 gold! And make enemies...", "consequences": {"gold_change": 200, "reputation": {"Gamblers": -10}}},
                     {"label": "Study war maps alone", "emoji": "📜", "hint": "Tactical advantage", "result": "You learn terrain, supply routes, weak points.", "consequences": {"item": "📋 Tactical Maps"}, "flag": "tactician"}
                 ]},
                
                # ACT 2: FIRST BLOOD (Scenes 6-10)
                {"title": "Ambush on the Road", "narrative": "Week 2. Your battalion marches toward the front.\\n\\nSuddenly: **AMBUSH!** Enemy soldiers from Blue Crown attack!\\n\\nFirst real combat. Blood. Screaming. Chaos.", "location": "Forest Road", "mood": "chaotic",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 14, "description": "Survive the ambush", "success": "You kill 2 enemies. Your squad survives intact.", "failure": "You're wounded. Squad drags you to safety.", "success_consequences": {"xp_gain": 100, "reputation": {"Army": 10}}, "failure_consequences": {"hp_change": -25}}},
                {"title": "The Prisoner", "narrative": "You capture an enemy soldier. Young. Terrified.\\n\\nKross says: '**Interrogate him. Then kill him.**'\\n\\nBut he's just a kid. Conscripted like you.", "location": "Camp", "npc": "Enemy Prisoner", "mood": "dark",
                 "choices": [
                     {"label": "Execute him - follow orders", "emoji": "⚔️", "hint": "This is war", "result": "You do it. It haunts you. But you followed orders.", "consequences": {"reputation": {"Army": 15}, "hp_change": -5}, "flag": "executed_prisoner"},
                     {"label": "Let him escape", "emoji": "🕊️", "hint": "Show mercy", "result": "You look away. He runs. Kross suspects but says nothing.", "consequences": {"reputation": {"Honor": 25}}, "flag": "showed_mercy", "major": True},
                     {"label": "Recruit him to your side", "emoji": "🤝", "hint": "Bold move", "result": "He agrees to defect! Intel gained.", "consequences": {"companion": "Defector: Young Erik", "xp_gain": 75}, "flag": "recruited_enemy"}
                 ]},
                {"title": "The Supply Crisis", "narrative": "Week 3. Food runs low. Disease spreads.\\n\\n**Command error:** Supply wagons went to the wrong army.\\n\\nSoldiers are starving. Morale plummets.", "location": "Camp", "mood": "desperate",
                 "choices": [
                     {"label": "Raid enemy supply lines", "emoji": "🎯", "hint": "High risk, high reward", "result": "Night raid! You steal food, medicine, weapons!", "consequences": {"xp_gain": 150, "item": "📦 Supplies", "gold_change": 100}, "flag": "raider"},
                     {"label": "Organize rationing", "emoji": "📊", "hint": "Leadership", "result": "Fair distribution. Everyone survives. Respect earned.", "consequences": {"reputation": {"Soldiers": 30}}, "flag": "leader"},
                     {"label": "Desert NOW before it gets worse", "emoji": "🏃", "hint": "Survival", "result": "You flee in the night...", "flag": "deserted", "flag_value": True, "next_scene": 18, "major": True}
                 ]},
                {"title": "The Bridge of Blood", "narrative": "Your army reaches Blackwater River. Enemy holds the stone bridge.\\n\\n**Their forces:** 500\\n**Your forces:** 20,000\\n\\nBut the bridge is narrow. Only 6 soldiers wide.\\n\\n**It's a bottleneck. A slaughter waiting to happen.**", "location": "Blackwater Bridge", "mood": "chaotic",
                 "choices": [
                     {"label": "Lead the first wave!", "emoji": "⚔️", "hint": "Glory or death", "result": "You charge. Arrows rain. You reach the enemy and FIGHT!", "consequences": {"hp_change": -30, "xp_gain": 150, "reputation": {"Army": 35}}, "flag": "bridge_hero", "major": True},
                     {"label": "Find and ford upstream", "emoji": "🔍", "hint": "Tactical genius", "result": "You scout. Find a shallow crossing. Flank attack WINS!", "consequences": {"xp_gain": 200, "reputation": {"Command": 40}}, "flag": "flanking_genius", "major": True},
                     {"label": "Wait for sappers to blow the bridge", "emoji": "💣", "hint": "Engineer solution", "result": "Engineers place charges. BOOM! Enemy falls into river!", "consequences": {"xp_gain": 100, "gold_change": 50}}
                 ]},
                {"title": "The Aftermath - Bridge Crossing", "narrative": "The bridge is taken. But at what cost?\\n\\n**Casualties:** 3,000 dead. Rivers run red.\\n\\nYou see your first friend die. Mira takes an arrow. Torren holds her as she fades.\\n\\n**War is real now.**", "location": "Captured Bridge", "mood": "dark",
                 "challenge": {"type": "Wisdom Save", "stat": "wis", "dc": 13, "description": "Keep your sanity", "success": "You steel yourself. You can endure this.", "failure": "You break down. PTSD sets in.", "success_consequences": {"xp_gain": 50}, "failure_consequences": {"hp_change": -10, "flag": "ptsd"}}},
                
                # ACT 3: THE CRIMSON FIELDS (Scenes 11-15)
                {"title": "Arrival at Crimson Fields", "narrative": "THE BATTLEFIELD.\\n\\nThree armies converge:\\n**Red Crown (yours):** 18,000\\n**Blue Crown:** 15,000\\n**Black Crown:** 20,000\\n\\nTomorrow the world changes.", "location": "Crimson Fields - Eve of Battle", "mood": "dramatic",
                 "choices": [
                     {"label": "Spend night with your squad", "emoji": "🔥", "hint": "Brotherhood", "result": "Stories. Fears. Last words. You're ready.", "consequences": {"reputation": {"Squad": 40}}, "flag": "bonds_made"},
                     {"label": "Pray at the army chapel", "emoji": "🛐", "hint": "Find peace", "result": "Gods may or may not listen. But you feel calm.", "consequences": {"hp_change": 20}},
                     {"label": "Write final letters home", "emoji": "✉️", "hint": "Closure", "result": "If you die, they'll know you loved them.", "consequences": {"xp_gain": 25}}
                 ]},
                {"title": "THE BATTLE BEGINS", "narrative": "DAWN. Horns. Drums.\\n\\n**THREE ARMIES COLLIDE.**\\n\\nYou're in the center. Shields lock. Spears thrust. CHAOS.\\n\\nThe soldier beside you falls, throat cut. Blood everywhere.\\n\\n**THIS IS WAR.**", "location": "Crimson Fields - Center", "mood": "chaotic",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 16, "description": "SURVIVE", "success": "You fight like a demon. Hold the line!", "failure": "Wounded badly. Squad saves you.", "success_consequences": {"xp_gain": 250, "reputation": {"Army": 50}}, "failure_consequences": {"hp_change": -45}}},
                {"title": "The Mage Duel", "narrative": "Above the battlefield: **MAGES CLASH.**\\n\\nFireballs. Lightning. Hundreds die in flames.\\n\\nEnemy Archon Vex rains destruction. Your mages fall." + (" As a **mage**, you feel the call..." if char_class == "mage" else ""), "location": "Eastern Flank", "mood": "chaotic",
                 "choices": [
                     {"label": "Challenge Archon Vex!" if char_class == "mage" else "Organize archer volley", "emoji": "🔮" if char_class == "mage" else "🏹", "hint": "High risk", "result": "EPIC DUEL. You WIN! Vex falls!" if char_class == "mage" else "200 arrows fly. Vex retreats!", "consequences": {"xp_gain": 400, "reputation": {"Army": 100} if char_class == "mage" else {"Army": 50}}, "flag": "vex_defeated", "major": True},
                     {"label": "Protect your squad from magic", "emoji": "🛡️", "hint": "Save friends", "result": "You shield them. Loyalty over glory.", "consequences": {"reputation": {"Squad": 60}}},
                     {"label": "Fall back from this sector", "emoji": "↩️", "hint": "Retreat", "result": "You flee. Hundreds die. You live.", "consequences": {"reputation": {"Army": -30}}}
                 ]},
                {"title": "The Cavalry Charge", "narrative": "Black Crown cavalry breaks through your left flank!\\n\\n**2,000 mounted knights** crash into infantry. Slaughter!\\n\\nYour line crumbles. Rout imminent.\\n\\n**Someone must stop them.**", "location": "Left Flank Collapse", "mood": "desperate",
                 "choices": [
                     {"label": "Form defensive spear wall", "emoji": "🔱", "hint": "Hold position", "result": "SHIELDS UP! SPEARS OUT! You HOLD!", "consequences": {"xp_gain": 300, "hp_change": -20}, "flag": "held_line"},
                     {"label": "Counter-charge with your own cavalry", "emoji": "🐎", "hint": "If you're cavalry", "result": "CHARGE! Horse vs horse. You win!", "consequences": {"xp_gain": 350}, "flag": "cavalry_hero", "major": True},
                     {"label": "Sound the retreat", "emoji": "📯", "hint": "Save who you can", "result": "Organized retreat. Live to fight later.", "consequences": {"reputation": {"Command": -20}}}
                 ]},
                {"title": "THE BETRAYAL", "narrative": "Mid-battle, HORNS SOUND from YOUR camp.\\n\\n**IMPOSSIBLE.**\\n\\nYour Red Crown army and Black Crown army... **STOP FIGHTING EACH OTHER.**\\n\\nThey turn TOGETHER toward Blue Crown.\\n\\n**SECRET ALLIANCE. PLANNED BETRAYAL.**\\n\\nBlue Crown is surrounded. Doomed.", "location": "Crimson Fields - The Turn", "mood": "dark",
                 "choices": [
                     {"label": "Accept the alliance - crush Blue Crown", "emoji": "⚔️", "hint": "Victory at any cost", "result": "Treachery wins. Blue Crown annihilated.", "consequences": {"gold_change": 600, "reputation": {"Red Crown": 60}}, "flag": "betrayer", "major": True},
                     {"label": "REFUSE! This is dishonorable!", "emoji": "⚖️", "hint": "Stand for honor", "result": "You lower your weapon. Arrested on the spot.", "consequences": {"reputation": {"Honor": 100, "Army": -80}}, "flag": "honorable", "major": True},
                     {"label": "SWITCH SIDES - fight FOR Blue Crown!", "emoji": "💙", "hint": "Help the betrayed", "result": "You turn your cloak. INSANE but GLORIOUS!", "consequences": {"reputation": {"Red Crown": -100, "Blue Crown": 150}, "xp_gain": 400}, "flag": "turncloak", "flag_value": True, "major": True}
                 ]},
                
                # ACT 4: AFTERMATH (Scenes 16-20)
                {"title": "Victory Feast - The Kings Meet", "narrative": "Battle ends. Blue Crown destroyed. 40,000 dead total.\\n\\nRed King and Black King feast in a golden tent.\\n\\nThey plan to DIVIDE the world.\\n\\nYou're summoned. '**Name your reward, hero.**'", "location": "Victory Tent", "mood": "dark",
                 "choices": [
                     {"label": "Lands, titles, gold!", "emoji": "👑", "hint": "Accept power", "result": "You're made a LORD. Estates. Riches.", "consequences": {"gold_change": 3000, "xp_gain": 500}, "flag": "ending_lord", "flag_value": True, "major": True},
                     {"label": "Refuse all rewards", "emoji": "✋", "hint": "Reject blood money", "result": "Kings glare. Dangerous... but honorable.", "consequences": {"reputation": {"Honor": 150}}, "flag": "ending_just", "flag_value": True, "major": True},
                     {"label": "Draw blade - KILL BOTH KINGS", "emoji": "⚔️", "hint": "End tyranny", "result": "You lunge. Both fall. Guards rush. You die a LEGEND.", "consequences": {"hp_change": -999, "xp_gain": 1000}, "flag": "ending_regicide", "flag_value": True, "major": True}
                 ]},
                {"title": "The Trial", "narrative": "If you refused betrayal, you stand trial.\\n\\n**Charge:** Treason during battle.\\n**Punishment:** Death.\\n\\nBut soldiers testify FOR you. Your honor moves them.", "location": "Military Court", "mood": "dramatic",
                 "condition": {"honorable": True},
                 "choices": [
                     {"label": "Accept execution", "emoji": "⚖️", "hint": "Die with honor", "result": "You're executed. But your words spark revolution.", "flag": "ending_martyr", "flag_value": True, "major": True},
                     {"label": "Escape with help", "emoji": "🏃", "hint": "Your squad breaks you out", "result": "Daring escape! You become a legend in exile.", "flag": "ending_exile", "flag_value": True, "major": True}
                 ]},
                {"title": "Building the New Order", "narrative": "Months later. If you're a lord, you must BUILD.\\n\\nYour lands need governance. Justice. Will you be tyrant or savior?", "location": "Your Estate", "mood": "hopeful",
                 "condition": {"ending_lord": True},
                 "choices": [
                     {"label": "Rule with justice and mercy", "emoji": "⚖️", "hint": "Good lord", "result": "Your people prosper. Loved leader.", "flag": "good_lord"},
                     {"label": "Rule with iron fist", "emoji": "👊", "hint": "Order through fear", "result": "Efficient but feared. Rebellion brewing.", "flag": "tyrant_lord"}
                 ]},
                {"title": "Deserter's Path - The Run", "narrative": "You fled weeks ago. Hunted. Alone.\\n\\nYou reach a village. Peace. New life possible.\\n\\nNo one knows you're a deserter.", "location": "Western Village", "mood": "peaceful",
                 "condition": {"deserted": True},
                 "choices": [
                     {"label": "Start over here", "emoji": "🏡", "hint": "New life", "result": "You settle. Years pass. Family. Peace. You won.", "flag": "ending_peace", "flag_value": True, "major": True},
                     {"label": "Return to face justice", "emoji": "⚔️", "hint": "Atone", "result": "Execution. But clean conscience.", "flag": "ending_atone", "flag_value": True, "major": True}
                 ]},
                {"title": "Epilogue - 10 Years Later", "narrative": "A decade passes. How did your choices shape the world?\\n\\n" + "**Your story is complete.**", "location": "The Future", "mood": "dramatic",
                 "choices": [
                     {"label": "Reflect on your journey", "emoji": "📖", "hint": "The end", "result": "You lived. You chose. History remembers.", "flag": "ending_complete", "major": True}
                 ]}
            ],
            
            # 15 RANDOM ENCOUNTERS!
            "random_encounters": [
                {"id": "patrol", "title": "Enemy Patrol", "type": "Combat", "narrative": "You patrol the perimeter and encounter 3 enemy scouts!",
                 "challenge": {"stat": "str", "dc": 13, "success": "You defeat them silently.", "failure": "They escape and alert the enemy!",
"success_consequences": {"xp_gain": 75}, "failure_consequences": {"reputation": {"Army": -10}}}},
                {"id": "wounded", "title": "Wounded Soldier", "type": "Moral Choice", "narrative": "A dying enemy soldier begs for water.",
                 "challenge": {"stat": "cha", "dc": 11, "success": "You help him. He thanks you and dies peacefully.", "failure": "He curses you with his last breath.",
                 "success_consequences": {"reputation": {"Honor": 15}}, "failure_consequences": {"hp_change": -5}}},
                {"id": "disease", "title": "Camp Disease", "type": "Survival", "narrative": "Dysentery spreads through camp. Dozens sick.",
                 "challenge": {"stat": "wis", "dc": 14, "success": "You quarantine effectively. Contained!", "failure": "It spreads. Your squad falls ill.",
                 "success_consequences": {"xp_gain": 50}, "failure_consequences": {"hp_change": -15}}},
                {"id": "deserters", "title": "Deserters", "type": "Moral Choice", "narrative": "You catch 2 soldiers deserting. They beg for mercy.",
                 "challenge": {"stat": "cha", "dc": 12, "success": "You let them go quietly.", "failure": "You report them. They're hanged.",
                 "success_consequences": {"reputation": {"Honor": 20}}, "failure_consequences": {"reputation": {"Army": 15}}}},
                {"id": "treasure", "title": "Battlefield Loot", "type": "Discovery", "narrative": "You find a dead officer with a bag of gold and a magic sword.",
                 "challenge": {"stat": "int", "dc": 10, "success": "You take it!", "failure": "Trap! It explodes!",
                 "success_consequences": {"gold_change": 300, "item": "⚔️ Magic Blade"}, "failure_consequences": {"hp_change": -20}}},
                {"id": "spy", "title": "The Spy", "type": "Investigation", "narrative": "You suspect someone in camp is an enemy spy.",
                 "challenge": {"stat": "wis", "dc": 15, "success": "You catch them! Intel gained!", "failure": "The spy escapes.",
                 "success_consequences": {"xp_gain": 100, "reputation": {"Command": 20}}, "failure_consequences": {}}},
                {"id": "duel", "title": "Honor Duel", "type": "Combat", "narrative": "A rival soldier challenges you to a duel for glory.",
                 "challenge": {"stat": "dex", "dc": 14, "success": "You win! Reputation soars!", "failure": "You lose but survive. Embarrassed.",
                 "success_consequences": {"xp_gain": 150, "reputation": {"Soldiers": 25}}, "failure_consequences": {"hp_change": -10}}},
                {"id": "siege", "title": "Siege Engine", "type": "Tactics", "narrative": "Enemy builds a catapult. Must destroy it!",
                 "challenge": {"stat": "int", "dc": 13, "success": "Night raid. Catapult destroyed!", "failure": "It fires on your camp!",
                 "success_consequences": {"xp_gain": 125}, "failure_consequences": {"hp_change": -25}}},
                {"id": "morale", "title": "Morale Crisis", "type": "Leadership", "narrative": "Soldiers are demoralized. Someone must inspire them.",
                 "challenge": {"stat": "cha", "dc": 14, "success": "Your speech rallies them! Morale restored!", "failure": "They remain broken.",
                 "success_consequences": {"reputation": {"Soldiers": 30}}, "failure_consequences": {}}},
                {"id": "ambush_camp", "title": "Camp Ambush", "type": "Combat", "narrative": "Enemy raids your camp at night!",
                 "challenge": {"stat": "dex", "dc": 15, "success": "You repel them!", "failure": "Supplies stolen!",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {"gold_change": -100}}},
                {"id": "prisoner_escape", "title": "Prison Break", "type": "Crisis", "narrative": "Enemy prisoners attempt escape!",
                 "challenge": {"stat": "str", "dc": 12, "success": "Recaptured!", "failure": "They flee!",
                 "success_consequences": {}, "failure_consequences": {"reputation": {"Army": -15}}}},
                {"id": "messenger", "title": "Urgent Message", "type": "Decision", "narrative": "A messenger brings orders to attack NOW or wait for reinforcements.",
                 "challenge": {"stat": "wis", "dc": 13, "success": "You make the right call!", "failure": "Bad timing...",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {}}},
                {"id": "traitor", "title": "The Traitor", "type": "Investigation", "narrative": "One of YOUR squad might be a traitor...",
                 "challenge": {"stat": "int", "dc": 16, "success": "You find them before they strike!", "failure": "They sabotage you!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"hp_change": -30}}},
                {"id": "weather", "title": "The Storm", "type": "Survival", "narrative": "Massive storm. Tents flood. Hypothermia risk.",
                 "challenge": {"stat": "wis", "dc": 11, "success": "You prepare well!", "failure": "You get frostbite.",
                 "success_consequences": {}, "failure_consequences": {"hp_change": -15}}},
                {"id": "champion", "title": "Enemy Champion", "type": "Combat", "narrative": "Enemy champion challenges your army's best fighter...",
                 "challenge": {"stat": "str", "dc": 17, "success": "YOU step up and WIN! LEGEND!", "failure": "You fall. Barely survive.",
                 "success_consequences": {"xp_gain": 300, "reputation": {"Army": 50}}, "failure_consequences": {"hp_change": -40}}}
            ],
            
            # 12 SIDE QUESTS!
            "side_quests": [
                {"id": "blacksmith", "title": "The Blacksmith's Favor", "narrative": "Camp blacksmith needs rare ore. Offers to forge you custom armor.",
                 "rewards_hint": "🛡️ Epic Armor", "challenge": {"stat": "str", "dc": 12, "success": "You retrieve the ore! Custom armor forged!", "failure": "Ore location too dangerous.",
                 "success_consequences": {"item": "🛡️ Custom Plate Armor", "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "love_letter", "title": "The Love Letter", "narrative": "Soldier asks you to deliver letter to his love in enemy camp.",
                  "rewards_hint": "💰 Gold + Honor", "challenge": {"stat": "dex", "dc": 14, "success": "Delivered! She responds!", "failure": "Caught! Interrogated!",
                 "success_consequences": {"gold_change": 150, "reputation": {"Honor": 20}}, "failure_consequences": {"hp_change": -20}}},
                {"id": "chess_master", "title": "The Chess Master", "narrative": "General challenges you to chess. Win and earn his respect.",
                 "rewards_hint": "⭐ Command Respect", "challenge": {"stat": "int", "dc": 15, "success": "Checkmate! He's impressed!", "failure": "You lose. He's disappointed.",
                 "success_consequences": {"reputation": {"Command": 40}, "xp_gain": 75}, "failure_consequences": {}}},
                {"id": "haunted", "title": "The Haunted Battlefield", "narrative": "Ghosts of fallen soldiers haunt old battlefield. Lay them to rest.",
                 "rewards_hint": "✨ Magic Blessing", "challenge": {"stat": "wis", "dc": 16, "success": "Spirits rest. They bless you!", "failure": "They curse you!",
                 "success_consequences": {"hp_change": 30, "xp_gain": 150}, "failure_consequences": {"hp_change": -25}}},
                {"id": "mutiny", "title": "Stop the Mutiny", "narrative": "Soldiers plan to kill incompetent officer. Stop it or join?",
                 "rewards_hint": "⚖️ Leadership Test", "challenge": {"stat": "cha", "dc": 15, "success": "You mediate. Crisis averted!", "failure": "Mutiny happens!",
                 "success_consequences": {"reputation": {"Command": 35, "Soldiers": 35}}, "failure_consequences": {"reputation": {"Army": -30}}}},
                {"id": "map", "title": "The Secret Map", "narrative": "You find a map to enemy's supply depot. Raid it?",
                 "rewards_hint": "💰💰💰 Massive Loot", "challenge": {"stat": "dex", "dc": 15, "success": "JACKPOT! Supplies stolen!", "failure": "Trap! Ambushed!",
                 "success_consequences": {"gold_change": 500, "xp_gain": 200}, "failure_consequences": {"hp_change": -35}}},
                {"id": "healer", "title": "The Wounded Healer", "narrative": "Field medic is critically injured. Save them or let nature take course?",
                 "rewards_hint": "🩹 Medical Training", "challenge": {"stat": "wis", "dc": 13, "success": "Saved! They teach you healing!", "failure": "They die...",
                 "success_consequences": {"xp_gain": 100, "item": "📚 Medical Manual"}, "failure_consequences": {"reputation": {"Soldiers": -10}}}},
                {"id": "beast", "title": "The War Beast", "narrative": "Enemy's war elephant rampages. Kill it or tame it?",
                 "rewards_hint": "🐘 Epic Mount?!", "challenge": {"stat": "cha" if char_class == "ranger" else "str", "dc": 17, "success": "TAMED! You ride an ELEPHANT!", "failure": "Barely escape alive!",
                 "success_consequences": {"companion": "🐘 War Elephant", "xp_gain": 300}, "failure_consequences": {"hp_change": -30}}},
                {"id": "prophecy", "title": "The Oracle's Prophecy", "narrative": "Mysterious oracle offers to reveal your fate. Listen?",
                 "rewards_hint": "🔮 Future Knowledge", "challenge": {"stat": "int", "dc": 14, "success": "You understand the cryptic vision!", "failure": "Confusing. No help.",
                 "success_consequences": {"xp_gain": 150, "flag": "prophecy_heard"}, "failure_consequences": {}}},
                {"id": "banner", "title": "Capture Enemy Banner", "narrative": "Enemy's war banner is their pride. Steal it for massive morale boost!",
                 "rewards_hint": "⭐⭐ Glory!", "challenge": {"stat": "dex", "dc": 16, "success": "YOU STEAL IT! Army cheers!", "failure": "Caught! Beaten badly.",
                 "success_consequences": {"reputation": {"Army": 60}, "xp_gain": 250}, "failure_consequences": {"hp_change": -40}}},
                {"id": "poison", "title": "Poison the Wells", "narrative": "Rogue suggests poisoning enemy's water. Effective but dishonorable.",
                 "rewards_hint": "⚖️ Moral Choice", "challenge": {"stat": "int", "dc": 12, "success": "Done. Enemy weakened. Your soul tarnished.", "failure": "Can't do it.",
                 "success_consequences": {"reputation": {"Army": 40, "Honor": -50}, "xp_gain": 100}, "failure_consequences": {"reputation": {"Honor": 25}}}},
                {"id": "dragon", "title": "The Dragon's Lair", "narrative": "Rumors say a dragon sleeps nearby. Attack it for glory?",
                 "rewards_hint": "🐉 EPIC LOOT", "challenge": {"stat": "str", "dc": 19, "success": "YOU. SLAY. A. DRAGON!!!", "failure": "Nearly die. Flee in terror.",
                 "success_consequences": {"xp_gain": 500, "gold_change": 1000, "item": "🐉 Dragon Scale Armor"}, "failure_consequences": {"hp_change": -50}}}
            ],
            
            "endings": {
                "ending_lord": {"requires": {"ending_lord": True}, "narrative": "⚔️ **THE LORD OF WAR**\\n\\nYou rose through blood to nobility. History calls you hero. Only you know the truth.\\n\\n**Final Stats:** Level " + str(10) + " | Scenes: Variable | Reputation: Mixed"},
                "ending_just": {"requires": {"ending_just": True}, "narrative": "⚖️ **THE HONORABLE**\\n\\nYou rejected blood money. Walked away. Soldiers whisper your name in awe."},
                "ending_regicide": {"requires": {"ending_regicide": True}, "narrative": "⚔️ **KINGSLAYER**\\n\\nYou killed both tyrants. Died. Sparked revolution. Immortal legend."},
                "ending_martyr": {"requires": {"ending_martyr": True}, "narrative": "⚖️ **THE MARTYR**\\n\\nExecuted for honor. Your death inspired rebellion. Kingdoms fell."},
                "ending_exile": {"requires": {"ending_exile": True}, "narrative": "🏃 **THE EXILE**\\n\\nEscaped. Hunted. Legend. Free."},
                "ending_turncloak": {"requires": {"turncloak": True}, "narrative": "💙 **TURNCLOAK HERO**\\n\\nYou saved the betrayed. Forever hunted by Red. Forever honored by Blue."},
                "ending_peace": {"requires": {"ending_peace": True}, "narrative": "🏡 **THE COWARD WHO LIVED**\\n\\nNo glory. Just life. Family. Peace. You won."},
                "ending_atone": {"requires": {"ending_atone": True}, "narrative": "⚔️ **THE REDEEMED**\\n\\nYou faced your cowardice. Died with honor."},
                "default": "War ended. You died on the Crimson Fields with 40,000 others. Unmarked grave. Forgotten name."
            }
        }
    
    def _gen_mystery_detective(self, char_class: str = None) -> dict:
        """Investigation campaign - INT focused - 10 scenes with branching"""
        return {
            "name": "Murder at Ravencrest Manor",
            "type": "Detective Mystery",
            "scenes": [
                # SCENE 0 - Setup
                {"title": "The Invitation", "narrative": "A black envelope arrives. No return address.\\n\\n*'Come to Ravencrest Manor. Solve the murder. Win 10,000 gold.'*\\n\\nYou recognize the seal: Lord Mortimer Ravencrest, the wealthiest man in the kingdom.\\n\\nBut Mortimer has been **dead** for 5 years.", "location": "Your Study", "mood": "mysterious",
                 "choices": [
                     {"label": "Accept - investigate", "emoji": "🔍", "hint": "You're a detective", "result": "You pack your tools. A mystery awaits.", "consequences": {"xp_gain": 25}, "next_scene": 1},
                     {"label": "Research Ravencrest first", "emoji": "📚", "hint": "Prepare", "result": "Files reveal: Mortimer died mysteriously. Family fortune vanished.", "consequences": {"item": "📋 Case Files"}, "flag": "researched", "next_scene": 1},
                     {"label": "Bring backup", "emoji": "🤝", "hint": "Safety in numbers", "result": "You hire Watson, a local constable.", "consequences": {"companion": "Constable Watson"}, "flag": "brought_watson", "next_scene": 1}
                 ]},
                # SCENE 1 - Arrival
                {"title": "Ravencrest Manor", "narrative": "The manor looms. Gothic. Decaying. **Five other detectives** arrived before you.\\n\\n**The victim:** Lady Helena Ravencrest, found poisoned this morning.\\n**The suspects:** Her five guests, all with motive.\\n**Your task:** Find the killer before they strike again.", "location": "Manor Entrance", "npc": "Butler Graves (Suspicious)", "mood": "dark",
                 "choices": [
                     {"label": "Examine the body", "emoji": "💀", "hint": "Evidence", "result": "Poison: Nightshade. Time of death: 3 AM. No struggle.", "consequences": {"xp_gain": 30}, "flag": "examined_body", "next_scene": 2},
                     {"label": "Interview suspects first", "emoji": "👥", "hint": "Gather alibis", "result": "Everyone has alibis. Everyone lies.", "consequences": {"reputation": {"Suspects": -10}}, "next_scene": 3},
                     {"label": "Search the manor", "emoji": "🔦", "hint": "Find clues", "result": "You find a hidden passage...", "consequences": {"item": "🗝️ Hidden Key"}, "flag": "found_passage", "next_scene": 4}
                 ]},
                # SCENE 2 - Body Examination Path
                {"title": "The Forensics", "narrative": "You examine the body closely. Nightshade poison. But wait...\\n\\nThere's a **puncture mark**. She was also INJECTED with something.\\n\\nTwo methods? Two killers?", "location": "Crime Scene", "mood": "tense",
                 "choices": [
                     {"label": "Test the injection site", "emoji": "🧪", "hint": "Lab work", "result": "Contains sedative. She was unconscious when poisoned.", "consequences": {"xp_gain": 75}, "flag": "found_sedative", "next_scene": 5},
                     {"label": "Check under fingernails", "emoji": "💅", "hint": "She fought back?", "result": "Skin tissue! She scratched someone!", "consequences": {"xp_gain": 100}, "flag": "found_skin", "next_scene": 5}
                 ]},
                # SCENE 3 - Interview Path
                {"title": "The Suspects", "narrative": "You interview all five:\\n\\n**1. Butler Graves** - Loyal 30 years\\n**2. Lady Seraphine** - Niece, bankrupt\\n**3. Dr. Mortis** - Family physician\\n**4. Count Vex** - Helena's ex-lover\\n**5. Madame Noir** - Fortune teller\\n\\nWho's lying?", "location": "Drawing Room", "mood": "tense",
                 "choices": [
                     {"label": "Focus on Seraphine", "emoji": "💍", "hint": "Money motive", "result": "She needs inheritance. Desperately.", "flag": "suspect_seraphine", "next_scene": 5},
                     {"label": "Focus on Count Vex", "emoji": "💔", "hint": "Crime of passion", "result": "Helena rejected him. Rage motive.", "flag": "suspect_vex", "next_scene": 5},
                     {"label": "Focus on Dr. Mortis", "emoji": "💊", "hint": "Had access to poison", "result": "His medical bag contains nightshade!", "flag": "suspect_doctor", "next_scene": 6}
                 ]},
                # SCENE 4 - Hidden Passage Path
                {"title": "The Secret Passage", "narrative": "Behind the bookshelf. Stone stairs descending into darkness.\\n\\nYou find: Old laboratory. Alchemical equipment. Poison recipes.\\n\\n**Lord Mortimer was making poisons before he died.**", "location": "Underground Lab", "mood": "dark",
                 "choices": [
                     {"label": "Search for more clues", "emoji": "🔍", "hint": "Thorough", "result": "You find Mortimer's journal. Family secrets exposed.", "consequences": {"item": "📕 Mortimer's Journal", "xp_gain": 150}, "flag": "found_journal", "next_scene": 5},
                     {"label": "Test the equipment", "emoji": "🧪", "hint": "Science", "result": "Recent use! Someone's been down here!", "consequences": {"xp_gain": 100}, "flag": "lab_used_recently", "next_scene": 5}
                 ]},
                # SCENE 5 - Convergence Point
                {"title": "The First Revelation", "narrative": "Pieces come together. Helena discovered something about her father's death.\\n\\nMortimer didn't die naturally. He was MURDERED 5 years ago.\\n\\nHelena knew who did it. And they silenced her.", "location": "Helena's Study", "mood": "mysterious",
                 "challenge": {"type": "Investigation", "stat": "int", "dc": 14, "description": "Connect the dots", "success": "You see it! Both murders are connected!", "failure": "Too many variables. Need more evidence.", "success_consequences": {"xp_gain": 100, "flag": "connected_murders", "next_scene": 6}, "failure_consequences": {"next_scene": 7}}},
                # SCENE 6 - Second Murder
                {"title": "The Second Victim", "narrative": "Midnight. A scream.\\n\\n**Dr. Mortis is dead.** Throat slit.\\n\\nHe was about to tell you something. Now he can't.\\n\\nThe killer is getting desperate.", "location": "East Wing", "mood": "horror",
                 "choices": [
                     {"label": "Examine the new crime scene", "emoji": "🔦", "hint": "Find clues", "result": "Muddy footprints. Size matches... Butler Graves!", "consequences": {"xp_gain": 100}, "flag": "graves_prints", "next_scene": 8},
                     {"label": "Set a trap immediately", "emoji": "🪤", "hint": "Catch them now", "result": "You stage fake evidence pointing at yourself as bait...", "consequences": {"xp_gain": 150}, "flag": "trap_set", "next_scene": 8},
                     {"label": "Gather everyone for safety", "emoji": "🛡️", "hint": "No more deaths", "result": "Everyone in the ballroom. Locked in together.", "consequences": {"reputation": {"Detectives": 20}}, "next_scene": 8}
                 ]},
                # SCENE 7 - Alternate Path (if failed deduction)
                {"title": "Another Detective Dies", "narrative": "You were too slow. Another detective found the truth.\\n\\nNow they're dead. Poisoned like Helena.\\n\\nYou MUST solve this before you're next.", "location": "Library", "mood": "desperate",
                 "challenge": {"type": "Survival", "stat": "wis", "dc": 15, "description": "Avoid becoming the next victim", "success": "You spot the killer approaching! Turn the tables!", "failure": "Drugged! You wake hours later, barely alive.", "success_consequences": {"xp_gain": 200, "next_scene": 8}, "failure_consequences": {"hp_change": -30, "next_scene": 8}}},
                # SCENE 8 - The Hidden Room
                {"title": "The Secret Chamber", "narrative": "The hidden key unlocks Mortimer's final secret.\\n\\n**His REAL will:** Everything goes to... a SECRET CHILD.\\n\\nHelena discovered this. Threatened to expose them.\\n\\nThe killer is the secret heir eliminating competition!", "location": "Secret Chamber", "mood": "dramatic",
                 "challenge": {"type": "Deduction", "stat": "int", "dc": 16, "description": "Identify the heir", "success": "You KNOW who it is! The clues all point to ONE person!", "failure": "Three suspects fit. You must guess...", "success_consequences": {"flag": "solved", "xp_gain": 200, "next_scene": 9}, "failure_consequences": {"next_scene": 9}}},
                # SCENE 9 - The Confrontation
                {"title": "The Accusation", "narrative": "You gather everyone in the ballroom. Detective work complete.\\n\\n**Time to reveal the killer.**\\n\\nGet it wrong... and you'll be their next victim.", "location": "Ballroom", "mood": "dramatic",
                 "choices": [
                     {"label": "Accuse Butler Graves", "emoji": "🎩", "hint": "Mortimer's secret son", "result": "He confesses! Was Mortimer's bastard son! Killed for inheritance!", "flag": "ending_butler", "major": True},
                     {"label": "Accuse Lady Seraphine", "emoji": "💍", "hint": "Not actually the niece", "result": "She draws a blade! Impostor who replaced real Seraphine years ago!", "flag": "ending_seraphine", "major": True},
                     {"label": "Accuse Madame Noir", "emoji": "🔮", "hint": "The fortune teller", "result": "She laughs. 'I foresaw you'd figure it out.' Secret daughter!", "flag": "ending_noir", "major": True}
                 ]}
            ],
            
            # 12 RANDOM ENCOUNTERS - Mystery/Investigation themed!
            "random_encounters": [
                {"id": "red_herring", "title": "False Lead", "type": "Investigation", "narrative": "You find 'evidence' but it's planted!",
                 "challenge": {"stat": "int", "dc": 14, "success": "You recognize it's fake!", "failure": "Wasted time on wrong lead!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {}}},
                {"id": "witness", "title": "Nervous Witness", "type": "Social", "narrative": "Servant saw something. Won't talk easily.",
                 "challenge": {"stat": "cha", "dc": 13, "success": "They confess! 'I saw the killer!'", "failure": "They flee. Lost info.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "poison_test", "title": "Test the Poison", "type": "Investigation", "narrative": "Lab analysis reveals poison source.",
                 "challenge": {"stat": "int", "dc": 15, "success": "Rare toxin! Only 2 suspects had access!", "failure": "Inconclusive.",
                 "success_consequences": {"xp_gain": 125}, "failure_consequences": {}}},
                {"id": "alibi_break", "title": "Break an Alibi", "type": "Social", "narrative": "One suspect's alibi doesn't match timeline.",
                 "challenge": {"stat": "cha", "dc": 14, "success": "They crack! Admit they lied!", "failure": "They stay silent.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "attack", "title": "Killer Attacks YOU!", "type": "Combat", "narrative": "Someone tries to eliminate you!",
                 "challenge": {"stat": "dex", "dc": 16, "success": "You fight them off!", "failure": "Wounded! Barely escape!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"hp_change": -25}}},
                {"id": "diary", "title": "Secret Diary Found", "type": "Discovery", "narrative": "Hidden diary reveals affairs and debts.",
                 "challenge": {"stat": "int", "dc": 12, "success": "Motive discovered!", "failure": "Can't read handwriting.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "fingerprints", "title": "Fingerprint Analysis", "type": "Investigation", "narrative": "Mysterious prints on murder weapon.",
                 "challenge": {"stat": "int", "dc": 15, "success": "Match found! Narrows suspects!", "failure": "Smudged. Useless.",
                 "success_consequences": {"xp_gain": 125}, "failure_consequences": {}}},
                {"id": "bribe", "title": "Bribe Attempt", "type": "Moral Choice", "narrative": "Suspect offers 500 gold to 'forget' evidence.",
                 "challenge": {"stat": "wis", "dc": 13, "success": "You refuse! Justice > gold!", "failure": "Tempted...",
                 "success_consequences": {"reputation": {"Justice": 30}}, "failure_consequences": {"gold_change": 500, "reputation": {"Justice": -50}}}},
                {"id": "letter", "title": "Blackmail Letter", "type": "Discovery", "narrative": "Victim was blackmailing someone!",
                 "challenge": {"stat": "int", "dc": 14, "success": "Target identified! New suspect!", "failure": "Letter coded.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "chase", "title": "Suspect Flees", "type": "Combat", "narrative": "One suspect runs! Chase through manor!",
                 "challenge": {"stat": "dex", "dc": 15, "success": "CAUGHT! Why run if innocent?", "failure": "They escape!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {}}},
                {"id": "seance", "title": "The Séance", "type": "Mystery", "narrative": "Medium offers to contact victim's ghost.",
                 "challenge": {"stat": "wis", "dc": 16, "success": "Real! Ghost names killer!", "failure": "Fraud. Waste of time.",
                 "success_consequences": {"xp_gain": 200}, "failure_consequences": {}}},
                {"id": "evidence_stolen", "title": "Evidence Stolen!", "type": "Crisis", "narrative": "Your key evidence vanishes!",
                 "challenge": {"stat": "int", "dc": 17, "success": "You find backup evidence!", "failure": "Case weakened!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {}}}
            ],
            
            # 10 SIDE QUESTS - Detective missions!
            "side_quests": [
                {"id": "sketch_artist", "title": "Draw the Suspect", "narrative": "Witness describes someone. Sketch them?",
                 "rewards_hint": "🎨 Visual ID", "challenge": {"stat": "int", "dc": 12, "success": "Perfect sketch! Matches killer!", "failure": "Bad drawing.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "interview_all", "title": "Interview Everyone", "narrative": "Systematically question all 20 servants.",
                 "rewards_hint": "📝 Complete Profiles", "challenge": {"stat": "cha", "dc": 14, "success": "One servant saw killer!", "failure": "They close ranks.",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {}}},
                {"id": "autopsy", "title": "Full Autopsy", "narrative": "Doctor offers detailed post-mortem analysis.",
                 "rewards_hint": "🩺 Medical Evidence", "challenge": {"stat": "int", "dc": 15, "success": "Time of death confirms alibi gaps!", "failure": "Inconclusive.",
                 "success_consequences": {"xp_gain": 175}, "failure_consequences": {}}},
                {"id": "search_rooms", "title": "Search All Bedrooms", "narrative": "Secretly search every suspect's room.",
                 "rewards_hint": "🔍 Hidden Secrets", "challenge": {"stat": "dex", "dc": 16, "success": "You find murder weapon hidden!", "failure": "Caught! Accused of tampering!",
                 "success_consequences": {"xp_gain": 200}, "failure_consequences": {"reputation": {"Suspects": -30}}}},
                {"id": "reconstruct", "title": "Recreate the Crime", "narrative": "Re-enact murder to test theories.",
                 "rewards_hint": "🎭 Timeline Clarity", "challenge": {"stat": "int", "dc": 14, "success": "One suspect's story IMPOSSIBLE!", "failure": "Too many variables.",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {}}},
                {"id": "handwriting", "title": "Handwriting Analysis", "narrative": "Compare all suspects' handwriting to threatening notes.",
                 "rewards_hint": "✍️ Forensics", "challenge": {"stat": "int", "dc": 15, "success": "MATCH! One suspect wrote threats!", "failure": "All similar.",
                 "success_consequences": {"xp_gain": 175}, "failure_consequences": {}}},
                {"id": "motive_map", "title": "Map All Motives", "narrative": "Chart relationships, debts, affairs.",
                 "rewards_hint": "🗺️ Connection Web", "challenge": {"stat": "int", "dc": 16, "success": "Pattern emerges! Clear motive!", "failure": "Too complex.",
                 "success_consequences": {"xp_gain": 200}, "failure_consequences": {}}},
                {"id": "trap_killer", "title": "Set Elaborate Trap", "narrative": "Stage fake clue to lure killer into revealing themselves.",
                 "rewards_hint": "🪤 Confession", "challenge": {"stat": "cha", "dc": 17, "success": "They take bait! Caught red-handed!", "failure": "They see through it.",
                 "success_consequences": {"xp_gain": 250}, "failure_consequences": {}}},
                {"id": "financial", "title": "Follow the Money", "narrative": "Audit all suspects' finances.",
                 "rewards_hint": "💰 Motive", "challenge": {"stat": "int", "dc": 15, "success": "One is bankrupt! Needed inheritance!", "failure": "Records destroyed.",
                 "success_consequences": {"xp_gain": 175}, "failure_consequences": {}}},
                {"id": "protect_witness", "title": "Protect Key Witness", "narrative": "Witness in danger! Killer might strike!",
                 "rewards_hint": "🛡️ Testimony", "challenge": {"stat": "dex", "dc": 16, "success": "Witness survives! Testifies!", "failure": "Witness killed!",
                 "success_consequences": {"xp_gain": 200}, "failure_consequences": {}}}
            ],
            
            "endings": {
                "ending_butler": {"requires": {"ending_butler": True}, "narrative": "🎩 **CASE CLOSED**\\n\\nButler Graves arrested. You claim 10,000 gold. Justice served."},
                "ending_niece": {"requires": {"ending_niece": True}, "narrative": "💍 **MASTERMIND EXPOSED**\\n\\nSeraphine tried to kill you too. You stopped her. Hero detective."},
                "ending_amnesia": {"requires": {"ending_amnesia": True}, "narrative": "🔪 **THE AMNESIAC KILLER**\\n\\nYou solved your own crime. Now you confess. Tragic. Brilliant."},
                "default": "You failed. The real killer escapes. Another detective solves it. You're forgotten."
            }
        }
    
    def _gen_wilderness_survival(self, char_class: str = None) -> dict:
        """Survival campaign - WIS focused - 10 scenes with branching"""
        return {
            "name": "Alone in the Frostpeak Wilds",
            "type": "Survival Horror",
            "scenes": [
                # SCENE 0 - Crash
                {"title": "The Crash", "narrative": "Your airship falls from the sky. Storm. Lightning. **Crash.**\\n\\nYou wake in snow. Alone. Your crew: dead or scattered.\\n\\nTemperature: -20°C. Night approaches. You have: a knife, flint, wet clothes.", "location": "Crash Site", "mood": "dark",
                 "choices": [
                     {"label": "Build fire immediately", "emoji": "🔥", "hint": "Warmth = life", "result": "Fire saves you from hypothermia.", "consequences": {"hp_change": 10}, "next_scene": 1},
                     {"label": "Search wreckage for supplies", "emoji": "📦", "hint": "Gear first", "result": "You find: rope, tinderbox, dried meat.", "consequences": {"item": "🎒 Survival Kit"}, "flag": "found_supplies", "next_scene": 1},
                     {"label": "Track any survivors", "emoji": "👣", "hint": "Find your crew", "result": "You find tracks... but also something ELSE.", "flag": "predator_aware", "next_scene": 2}
                 ]},
                # SCENE 1 - First Night
                {"title": "The First Night", "narrative": "Darkness. Cold. Wolves howl in the distance.\\n\\nYou have fire, but for how long?\\n\\nMust decide: stay at crash site or move to better shelter?", "location": "Makeshift Camp", "mood": "tense",
                 "choices": [
                     {"label": "Stay at crash site", "emoji": "⛺", "hint": "Wait for rescue", "result": "Familiar ground. But exposed.", "next_scene": 3},
                     {"label": "Move to forest shelter", "emoji": "🌲", "hint": "Better protection", "result": "You find natural cave. Warmer. Safer.", "consequences": {"hp_change": 15}, "flag": "cave_shelter", "next_scene": 3},
                     {"label": "Climb high ground for visibility", "emoji": "⛰️", "hint": "Signal fire location", "result": "Rocky outcrop. See for miles. Wind cuts deep.", "consequences": {"hp_change": -10}, "flag": "high_ground", "next_scene": 3}
                 ]},
                # SCENE 2 - Tracking Path
                {"title": "The Survivor", "narrative": "You follow the tracks and find: **Engineer Maya**, badly injured.\\n\\nBroken leg. Frostbite. Dying.\\n\\nShe has medical supplies. But she's dead weight.", "location": "Frozen Ravine", "npc": "Maya (Injured)", "mood": "dark",
                 "choices": [
                     {"label": "Carry her with you", "emoji": "🤝", "hint": "Save her life", "result": "Slower travel. But you're not alone.", "consequences": {"companion": "💊 Engineer Maya"}, "flag": "saved_maya", "major": True, "next_scene": 3},
                     {"label": "Take supplies, leave her", "emoji": "💊", "hint": "Harsh survival", "result": "She begs. You take her gear. Walk away.", "consequences": {"item": "🩹 Medical Kit", "hp_change": 20}, "flag": "left_maya", "next_scene": 3},
                     {"label": "Mercy kill", "emoji": "💀", "hint": "End her suffering", "result": "Quick. Painless. Haunting.", "consequences": {"xp_gain": 50}, "flag": "mercy_kill", "next_scene": 3}
                 ]},
                # SCENE 3 - The Hunt
                {"title": "Day 3 - The Hunt", "narrative": "Food runs out. You must hunt or starve.\\n\\nTracks lead to: deer, rabbit, or... something bigger.", "location": "Frozen Forest", "mood": "tense",
                 "choices": [
                     {"label": "Hunt the deer", "emoji": "🦌", "hint": "Big risk, big reward", "result": "You track for hours. One shot. Success!", "consequences": {"item": "🥩 Deer Meat (5 days)", "xp_gain": 75}, "next_scene": 4},
                     {"label": "Trap rabbits (safe)", "emoji": "🐰", "hint": "Reliable", "result": "Snares work. Small meals, but steady.", "consequences": {"item": "🥕 Rabbit (2 days)"}, "next_scene": 4},
                     {"label": "Follow the LARGE tracks", "emoji": "🐻", "hint": "Dangerous game", "result": "You find a cave. Growling inside. Bear? Or worse?", "flag": "found_cave", "next_scene": 5}
                 ]},
                # SCENE 4 - Weather Crisis
                {"title": "The Blizzard", "narrative": "Day 5. Storm hits. HARD.\\n\\nVisibility: zero. Wind: deadly. Temperature: -40°C.\\n\\nThis storm will kill you if you don't act smart.", "location": "Open Tundra", "mood": "chaotic",
                 "challenge": {"type": "Survival", "stat": "wis", "dc": 15, "description": "Survive the blizzard", "success": "You dig a snow shelter. Insulated. Survives the night.", "failure": "Hypothermia sets in. Losing consciousness...", "success_consequences": {"xp_gain": 150, "next_scene": 6}, "failure_consequences": {"hp_change": -35, "next_scene": 7}}},
                # SCENE 5 - Beast Path
                {"title": "The Ice Drake", "narrative": "It's NOT a bear.\\n\\n**Ice Drake.** Apex predator. 6 meters long. Frozen breath weapon.\\n\\nIt sees you. Hungry.", "location": "Drake's Lair", "mood": "horror",
                 "choices": [
                     {"label": "FIGHT IT!", "emoji": "⚔️", "hint": "Insane courage", "result": "Epic battle. You WIN! Drake meat for MONTHS!", "consequences": {"hp_change": -40, "xp_gain": 400, "item": "🐉 Drake Scales"}, "flag": "drake_slayer", "major": True, "next_scene": 6},
                     {"label": "Steal from its hoard and flee", "emoji": "💎", "hint": "Greed + risk", "result": "You grab treasure. It ROARS. You RUN!", "consequences": {"gold_change": 500, "hp_change": -20}, "flag": "drake_thief", "next_scene": 6},
                     {"label": "Back away slowly", "emoji": "🚶", "hint": "Smart survival", "result": "It lets you go. This time.", "consequences": {"xp_gain": 100}, "next_scene": 6}
                 ]},
                # SCENE 6 - Discovery
                {"title": "The Abandoned Outpost", "narrative": "Day 10. You find it: **Old military outpost.** Abandoned 20 years ago.\\n\\nSupplies. Shelter. Radio?\\n\\nBut something feels... wrong.", "location": "Outpost Frost-7", "mood": "mysterious",
                 "choices": [
                     {"label": "Search for working radio", "emoji": "📻", "hint": "Call for rescue", "result": "Radio WORKS! But batteries dying. One transmission!", "flag": "found_radio", "next_scene": 8},
                     {"label": "Fortify and survive here", "emoji": "🏰", "hint": "Make this home", "result": "Plenty of supplies. Could last months.", "flag": "fortified", "next_scene": 8},
                     {"label": "Investigate WHY it's abandoned", "emoji": "🔍", "hint": "Something's off", "result": "You find logs. They evacuated because... oh no.", "flag": "learned_truth", "next_scene": 7}
                 ]},
                # SCENE 7 - Dark Path
                {"title": "The Infection", "narrative": "The logs reveal: **Frostmind Parasite.**\\n\\nSpread through water. Drives hosts mad. Violent. Cannibalistic.\\n\\nThe outpost crew... they're still here. TRANSFORMED.", "location": "Outpost Lower Level", "mood": "horror",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 17, "description": "Fight the infected", "success": "You kill them all. Burn the bodies. Sterilize the area.", "failure": "Bitten! Infected! Must find cure FAST!", "success_consequences": {"xp_gain": 300, "next_scene": 8}, "failure_consequences": {"hp_change": -45, "flag": "infected", "next_scene": 8}}},
                # SCENE 8 - Convergence/Final Choice
                {"title": "Day 14 - The Signal", "narrative": "You spot smoke on the horizon: **Rescue team!**\\n\\nBut if you're infected... you'll spread the parasite.\\n\\nIf you fortified outpost... do you even WANT to leave?", "location": "Signal Hill", "mood": "dramatic",
                 "choices": [
                     {"label": "Signal for rescue", "emoji": "🔥", "hint": "Go home", "result": "Helicopter arrives. You're saved! Going home!", "flag": "ending_rescued", "major": True, "next_scene": 9},
                     {"label": "Stay in the wilderness", "emoji": "🏔️", "hint": "This IS home now", "result": "You wave them off. Survival IS your life now.", "flag": "ending_wild", "major": True, "next_scene": 9},
                     {"label": "If infected: Walk into the cold to die", "emoji": "❄️", "hint": "Sacrifice", "result": "You walk into blizzard. Save humanity. Die a hero.", "condition": {"infected": True}, "flag": "ending_sacrifice", "major": True}
                 ]},
                # SCENE 9 - Epilogue
                {"title": "Epilogue", "narrative": "Your journey ends. But the story continues...", "location": "Aftermath", "mood": "reflective",
                 "choices": [
                     {"label": "Reflect on survival", "emoji": "📖", "hint": "The end", "result": "You survived. Changed. Stronger. Or broken.", "flag": "ending_complete"}
                 ]}
            ],
            
            # 15 RANDOM ENCOUNTERS - Survival horror themed!
            "random_encounters": [
                {"id": "blizzard", "title": "Sudden Blizzard", "type": "Survival", "narrative": "Whiteout! Can't see 2 meters!",
                 "challenge": {"stat": "wis", "dc": 14, "success": "You find shelter!", "failure": "Lost for hours. Hypothermia!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {"hp_change": -20}}},
                {"id": "wolves", "title": "Wolf Pack", "type": "Combat", "narrative": "5 hungry wolves surround you!",
                 "challenge": {"stat": "str", "dc": 15, "success": "You fight them off!", "failure": "Mauled badly!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"hp_change": -30}}},
                {"id": "frostbite", "title": "Frostbite Risk", "type": "Survival", "narrative": "Fingers going numb. Losing feeling.",
                 "challenge": {"stat": "wis", "dc": 12, "success": "You warm up in time!", "failure": "Lose 2 fingers. -HP permanently!",
                 "success_consequences": {}, "failure_consequences": {"hp_change": -15}}},
                {"id": "food_poisoning", "title": "Tainted Meat", "type": "Survival", "narrative": "That meat you ate... was it fresh?",
                 "challenge": {"stat": "wis", "dc": 13, "success": "Your iron stomach handles it!", "failure": "Violently ill!",
                 "success_consequences": {}, "failure_consequences": {"hp_change": -25}}},
                {"id": "avalanche", "title": "Avalanche!", "type": "Crisis", "narrative": "RUMBLE. Snow cascades!",
                 "challenge": {"stat": "dex", "dc": 16, "success": "You dodge! Close call!", "failure": "Buried! Dig out!",
                 "success_consequences": {"xp_gain": 125}, "failure_consequences": {"hp_change": -30}}},
                {"id": "bear", "title": "Cave Bear", "type": "Combat", "narrative": "You stumble into bear's den!",
                 "challenge": {"stat": "str", "dc": 17, "success": "You KILL IT! Bear meat + fur!", "failure": "Retreat! Wounded!",
                 "success_consequences": {"xp_gain": 200, "item": "🐻 Bear Pelt"}, "failure_consequences": {"hp_change": -35}}},
                {"id": "ice_break", "title": "Ice Breaks", "type": "Crisis", "narrative": "Crossing frozen lake. ICE CRACKS!",
                 "challenge": {"stat": "dex", "dc": 14, "success": "You leap to safety!", "failure": "FALL IN! Freezing water!",
                 "success_consequences": {}, "failure_consequences": {"hp_change": -40}}},
                {"id": "survivor", "title": "Another Survivor", "type": "Social", "narrative": "Someone else from the crash! Injured.",
                 "challenge": {"stat": "wis", "dc": 12, "success": "You save them! Ally gained!", "failure": "Too late. They die.",
                 "success_consequences": {"companion": "⛑️ Survivor", "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "shelter_collapse", "title": "Shelter Collapses", "type": "Crisis", "narrative": "Your makeshift shelter FAILS!",
                 "challenge": {"stat": "wis", "dc": 13, "success": "You rebuild quickly!", "failure": "Exposed to elements all night!",
                 "success_consequences": {"xp_gain": 50}, "failure_consequences": {"hp_change": -20}}},
                {"id": "cliff", "title": "Cliff Edge", "type": "Crisis", "narrative": "Path ends at sheer drop!",
                 "challenge": {"stat": "dex", "dc": 15, "success": "You find way down!", "failure": "Must backtrack. Lost time.",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {}}},
                {"id": "herbs", "title": "Medicinal Herbs", "type": "Discovery", "narrative": "Rare healing plants!",
                 "challenge": {"stat": "wis", "dc": 14, "success": "You brew medicine! +HP!", "failure": "Picked wrong ones. Useless.",
                 "success_consequences": {"hp_change": 30, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "predator_tracks", "title": "Massive Tracks", "type": "Mystery", "narrative": "Footprints bigger than your head...",
                 "challenge": {"stat": "wis", "dc": 15, "success": "You avoid the area!", "failure": "You walk right into its territory!",
                 "success_consequences": {"xp_gain": 75}, "failure_consequences": {"hp_change": -15}}},
                {"id": "cabin", "title": "Abandoned Cabin", "type": "Discovery", "narrative": "Old trapper's cabin! Supplies?",
                 "challenge": {"stat": "int", "dc": 12, "success": "Tools, food, warmth!", "failure": "Empty. Disappointment.",
                 "success_consequences": {"item": "🏠 Cabin Supplies", "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "lightning", "title": "Lightning Strike", "type": "Crisis", "narrative": "Storm! Lightning everywhere!",
                 "challenge": {"stat": "wis", "dc": 14, "success": "You find safe spot!", "failure": "STRUCK! Burned!",
                 "success_consequences": {}, "failure_consequences": {"hp_change": -30}}},
                {"id": "yeti", "title": "The Yeti", "type": "Combat", "narrative": "LEGEND. Abominable Snowman. IT'S REAL.",
                 "challenge": {"stat": "str", "dc": 19, "success": "YOU KILL A YETI! LEGEND!", "failure": "Run or die!",
                 "success_consequences": {"xp_gain": 500, "item": "❄️ Yeti Fur"}, "failure_consequences": {"hp_change": -45}}}
            ],
            
            # 12 SIDE QUESTS - Survival missions!
            "side_quests": [
                {"id": "signal_fire", "title": "Build Signal Fire", "narrative": "Massive fire might attract rescuers.",
                 "rewards_hint": "🔥 Rescue Chance", "challenge": {"stat": "wis", "dc": 13, "success": "Smoke visible for miles!", "failure": "Fire too small.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "trap_line", "title": "Set Trap Line", "narrative": "20 traps for continuous food supply.",
                 "rewards_hint": "🪤 Food Security", "challenge": {"stat": "wis", "dc": 14, "success": "Daily food guaranteed!", "failure": "Traps fail.",
                 "success_consequences": {"item": "🥩 Trap Meat", "xp_gain": 125}, "failure_consequences": {}}},
                {"id": "snowshoes", "title": "Craft Snowshoes", "narrative": "Branches + rope = mobility!",
                 "rewards_hint": "👞 Movement", "challenge": {"stat": "int", "dc": 12, "success": "Travel speed doubles!", "failure": "Poorly made. Break.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "map", "title": "Map the Territory", "narrative": "Chart landmarks for navigation.",
                 "rewards_hint": "🗺️ Knowledge", "challenge": {"stat": "int", "dc": 14, "success": "Complete map! Know the area!", "failure": "Get lost.",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"hp_change": -10}}},
                {"id": "cache", "title": "Build Supply Cache", "narrative": "Hide emergency supplies in multiple locations.",
                 "rewards_hint": "📦 Safety Net", "challenge": {"stat": "wis", "dc": 13, "success": "Backup supplies secured!", "failure": "Animals find and destroy it.",
                 "success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "shelter_upgrade", "title": "Build Proper Shelter", "narrative": "Replace makeshift camp with LOG CABIN.",
                 "rewards_hint": "🏠 Comfort", "challenge": {"stat": "str", "dc": 16, "success": "Built! Warm, safe, permanent!", "failure": "Collapse during construction!",
                 "success_consequences": {"hp_change": 40, "xp_gain": 200}, "failure_consequences": {"hp_change": -20}}},
                {"id": "smoke_meat", "title": "Smoke Meat Preservation", "narrative": "Preserve food for long-term survival.",
                 "rewards_hint": "🥓 Food Storage", "challenge": {"stat": "wis", "dc": 13, "success": "Meat lasts weeks!", "failure": "Spoils immediately.",
                 "success_consequences": {"item": "🥩 Smoked Meat", "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "water_source", "title": "Find Clean Water", "narrative": "Locate reliable, unfrozen stream.",
                 "rewards_hint": "💧 Hydration", "challenge": {"stat": "wis", "dc": 14, "success": "Fresh water found!", "failure": "Still melting snow.",
                 "success_consequences": {"hp_change": 20, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "climb_peak", "title": "Climb Highest Peak", "narrative": "See rescue routes from summit.",
                 "rewards_hint": "🏔️ Vantage", "challenge": {"stat": "str", "dc": 17, "success": "You spot village! Route mapped!", "failure": "Fall! Injured!",
                 "success_consequences": {"xp_gain": 250}, "failure_consequences": {"hp_change": -35}}},
                {"id": "tame_animal", "title": "Tame Wolf Pup", "narrative": "Orphaned wolf pup. Tame companion?",
                 "rewards_hint": "🐺 Ally", "challenge": {"stat": "cha", "dc": 15, "success": "Wolf companion! Loyal friend!", "failure": "It runs away.",
                 "success_consequences": {"companion": "🐺 Wolf", "xp_gain": 150}, "failure_consequences": {}}},
                {"id": "weapon_upgrade", "title": "Craft Better Weapons", "narrative": "Spear, bow, arrows from forest materials.",
                 "rewards_hint": "⚔️ Combat Bonus", "challenge": {"stat": "int", "dc": 14, "success": "Weapons crafted! Hunting easier!", "failure": "Break during crafting.",
                 "success_consequences": {"item": "🏹 Hunting Bow", "xp_gain": 125}, "failure_consequences": {}}},
                {"id": "cave_explore", "title": "Explore Deep Cave", "narrative": "Unknown cave. Could have supplies... or danger.",
                 "rewards_hint": "💎 Discovery", "challenge": {"stat": "wis", "dc": 16, "success": "Ancient supplies! Gear upgrade!", "failure": "Cave-in! Trapped!",
                 "success_consequences": {"gold_change": 500, "xp_gain": 200}, "failure_consequences": {"hp_change": -30}}}
            ],
            
            "endings": {
                "ending_survivor": {"requires": {"ending_survivor": True}, "narrative": "🏔️ **THE SURVIVOR**\\n\\nYou conquered Frostpeak. Alone. Legendary."},
                "ending_hero": {"requires": {"ending_hero": True}, "narrative": "👥 **THE RESCUER**\\n\\nYou came back. Saved lives. True hero."},
                "default": "The wilds claimed you. Another frozen corpse in the snow."
            }
        }
    
    def _gen_character_drama(self, char_class: str = None) -> dict:
        """Emotional drama campaign - CHA focused - 22 SCENES + 15 ENCOUNTERS + 12 QUESTS = 49 TOTAL!"""
        intro = "You return home after 10 years abroad. Everything changed.\n\n"
        if char_class == 'bard':
            intro += "**As a bard**, you left to chase fame. You found it. But at what cost?"
        elif char_class == 'cleric':
            intro += "**As a cleric**, you left to serve the gods. Your family never understood."
        elif char_class == 'paladin':
            intro += "**As a paladin**, duty called. You answered. They never forgave you."
        
        return {
            "name": "The Prodigal's Return",
            "type": "Character Drama",
            "scenes": [
                # ACT 1: HOMECOMING (Scenes 1-6)
                {"title": "The Road Home", "narrative": intro + "Your village appears on the horizon. Memories flood back.\n\n**What haunts you most?**", "location": "Forest Road", "mood": "reflective",
                 "choices": [
                     {"label": "The love you abandoned", "emoji": "💔", "hint": "Romance path", "result": "Her face. Her tears. 'Don't go.' You went anyway.", "flag": "romance_path", "major": True},
                     {"label": "The father you disappointed", "emoji": "👨", "hint": "Family path", "result": "His last words: 'You're dead to me.' Was he right?", "flag": "family_path", "major": True},
                     {"label": "The friend you betrayed", "emoji": "🤝", "hint": "Friendship path", "result": "You took credit for his work. He knows. Everyone knows.", "flag": "betrayal_path", "major": True}
                 ]},
                {"title": "The Village Gate", "narrative": "Familiar faces. Some smile. Some turn away.\n\nYour brother **Elias** stands at the gate. Ten years older. His eyes... cold.", "location": "Village Entrance", "npc": "Elias (Brother)", "mood": "tense",
                 "choices": [
                     {"label": "Embrace him", "emoji": "🤗", "hint": "Reconciliation", "result": "He stiffens. 'You LEFT us.' Not forgiveness. Not yet.", "consequences": {"reputation": {"Family": 5}}},
                     {"label": "Apologize immediately", "emoji": "🙏", "hint": "Humble", "result": "'Sorry doesn't bring back the dead, does it?' What dead?!", "consequences": {"xp_gain": 25}, "flag": "mystery_revealed"},
                     {"label": "Act like nothing's wrong", "emoji": "😊", "hint": "Denial", "result": "He laughs bitterly. 'Still the same. Still running.'", "consequences": {"reputation": {"Family": -10}}}
                 ]},
                {"title": "Mother's Grave", "narrative": "Elias leads you to the cemetery.\n\n**Your mother died 5 years ago.**\n\nYou didn't come to the funeral. You were 'too busy.'\n\nHer tombstone: *'She waited for you until her last breath.'*", "location": "Cemetery", "mood": "dark",
                 "challenge": {"type": "Emotional", "stat": "cha", "dc": 14, "description": "Process the grief", "success": "You weep. Finally. The guilt flows out.", "failure": "Numb. Empty. Nothing left inside.", "success_consequences": {"xp_gain": 100}, "failure_consequences": {"hp_change": -10}}},
                {"title": "The Tavern - Faces from the Past", "narrative": "You need a drink. The village tavern. Same as ever.\n\n**Three figures:**\n- **Sera** (your ex-lover, now married)\n- **Marcus** (the friend you betrayed, now village blacksmith)\n- **Old Thomas** (your father's best friend)\n\nWho do you approach first?", "location": "The Broken Arrow Tavern", "mood": "tense",
                 "choices": [
                     {"label": "Talk to Sera", "emoji": "💔", "hint": "Face the past", "result": "She sees you. Freezes. Her husband notices. Tension.", "flag": "sera_contact", "major": True},
                     {"label": "Talk to Marcus", "emoji": "⚒️", "hint": "Apologize", "result": "'Ten years. NOW you show up?' He's FURIOUS.", "flag": "marcus_contact", "major": True},
                     {"label": "Talk to Old Thomas", "emoji": "👴", "hint": "Learn", "result": "'Your father... he never stopped hoping you'd return. Never.'", "flag": "thomas_contact"}
                 ]},
                {"title": "Sera's Confession", "narrative": "Late night. Sera finds you alone.\n\n**Sera:** 'I married Gareth because I thought you were DEAD. Then... letters stopped coming. I moved on.'\n\nShe pauses. 'But I never stopped...'\n\n**Choose carefully.**", "location": "Moonlit Bridge", "npc": "Sera", "mood": "dramatic",
                 "choices": [
                     {"label": "Tell her you still love her", "emoji": "❤️", "hint": "Romance", "result": "She kisses you. Forbidden. Wrong. Perfect.", "flag": "affair_begins", "major": True},
                     {"label": "Respect her marriage", "emoji": "💍", "hint": "Honor", "result": "'You're a better person now.' She walks away. Forever.", "consequences": {"reputation": {"Honor": 50}}, "flag": "sera_closure"},
                     {"label": "Tell her you've moved on", "emoji": "👋", "hint": "Lie", "result": "Relief in her eyes. Then sadness. She knows you're lying.", "flag": "sera_rejected"}
                 ]},
                {"title": "Father's Letter", "narrative": "Elias gives you an envelope. Unopened. From Father.\n\nWritten one week before he died.\n\n**'My child,\n\nI was wrong. I said terrible things. Forgive me. Come home.\n\nYour loving father'**\n\nYou never got this letter.", "location": "Father's Study", "mood": "dark",
                 "challenge": {"type": "Will", "stat": "wis", "dc": 15, "description": "Don't break down", "success": "You hold it together. Barely.", "failure": "You SHATTER. Cry for hours.", "success_consequences": {"xp_gain": 75}, "failure_consequences": {"hp_change": -15, "flag": "broken"}}},
                
                # ACT 2: REDEMPTION (Scenes 7-15)
                {"title": "Marcus Confrontation", "narrative": "Marcus corners you. Drunk. ANGRY.\n\n**Marcus:** 'You stole my invention. Got rich off MY work. While I rotted here!'\n\nHe's right. You did.", "location": "Tavern Alley", "mood": "chaotic",
                 "choices": [
                     {"label": "Give him half your fortune", "emoji": "💰", "hint": "Make amends", "result": "'...You mean it?' His anger cracks. Maybe forgiveness?", "consequences": {"gold_change": -1500, "reputation": {"Marcus": 100}}, "flag": "marcus_redeemed", "major": True},
                     {"label": "Fight him", "emoji": "👊", "hint": "Violence", "result": "Brawl! You WIN but lose respect.", "consequences": {"hp_change": -20, "reputation": {"Village": -30}}},
                     {"label": "Deny everything", "emoji": "🤥", "hint": "Lie", "result": "He spits. 'You're STILL a coward.' He's right.", "consequences": {"reputation": {"Marcus": -100}}, "flag": "marcus_enemy"}
                 ]},
                {"title": "The Village Crisis", "narrative": "Disaster: bandits threaten the village. Demand tribute or burn it.\n\nYou could LEAVE again. Or STAY and fight.\n\n**This is your moment.**", "location": "Village Square", "mood": "chaotic",
                 "choices": [
                     {"label": "Lead the defense", "emoji": "⚔️", "hint": "Heroism", "result": "'He's BACK!' They follow you. You FIGHT!", "consequences": {"xp_gain": 200, "reputation": {"Village": 50}}, "flag": "hero_moment", "major": True},
                     {"label": "Flee (again)", "emoji": "🏃", "hint": "Coward", "result": "You run. AGAIN. History repeats.", "flag": "fled_again", "flag_value": True, "next_scene": 20, "major": True}
                 ]},
                {"title": "The Battle", "narrative": "You fight beside Elias, Marcus, villagers.\n\nBlood. Steel. Screaming.\n\n**This time, you DON'T run.**", "location": "Village Walls", "mood": "chaotic",
                 "challenge": {"type": "Combat", "stat": "str", "dc": 16, "description": "Protect your home", "success": "Victory! Bandits FLEE! You're a HERO!", "failure": "Wounded but alive. Village saved.", "success_consequences": {"xp_gain": 300, "reputation": {"Village": 100}}, "failure_consequences": {"hp_change": -40, "reputation": {"Village": 50}}}},
                {"title": "After the Battle - Recognition", "narrative": "Village celebrates. They chant YOUR name.\n\nElias approaches. Bloody. Tired. He SMILES.\n\n**Elias:** 'Welcome home, brother.'", "location": "Village Square", "npc": "Elias", "mood": "hopeful",
                 "choices": [
                     {"label": "I'm staying", "emoji": "🏠", "hint": "Commitment", "result": "Cheers! You're HOME. Finally.", "flag": "staying", "major": True},
                     {"label": "I have to go back", "emoji": "🚶", "hint": "Duty calls", "result": "Silence. Disappointment. But understanding.", "flag": "leaving_again"}
                 ]},
                {"title": "Sera's Choice", "narrative": "If you began the affair, her husband **Gareth** discovers it.\n\nConfrontation. Rage. Pain.", "location": "Sera's House", "npc": "Gareth (Husband)", "mood": "dark",
                 "condition": {"affair_begins": True},
                 "choices": [
                     {"label": "Fight for her", "emoji": "⚔️", "hint": "Love", "result": "Duel! You WIN. She chooses YOU. Scandal!", "consequences": {"reputation": {"Village": -50}}, "flag": "sera_together", "major": True},
                     {"label": "Step away", "emoji": "💔", "hint": "Sacrifice", "result": "You leave. She stays with Gareth. Noble. Heartbreaking.", "consequences": {"reputation": {"Honor": 80}}, "flag": "sera_sacrifice", "major": True}
                 ]},
                {"title": "Marcus's Workshop", "narrative": "If you made amends, Marcus shows you his NEW invention.\n\n**A mechanical wing.** Flight itself.\n\n'Partner with me. THIS time... as equals.'", "location": "Blacksmith", "npc": "Marcus", "mood": "hopeful",
                 "condition": {"marcus_redeemed": True},
                 "choices": [
                     {"label": "Yes - partners!", "emoji": "🤝", "hint": "Redemption complete", "result": "You shake hands. TRUE partnership. REAL friendship.", "consequences": {"companion": "🔧 Partner Marcus", "xp_gain": 200}},
                     {"label": "Decline - solo", "emoji": "🚫", "hint": "Independence", "result": "His face falls. Trust broken again.", "consequences": {"reputation": {"Marcus": -50}}}
                 ]},
                {"title": "The Village Elder's Request", "narrative": "Elder: 'Stay. Be our leader. We NEED you.'\n\nYour childhood dream. Offered. Now.", "location": "Elder's House", "npc": "Village Elder", "mood": "hopeful",
                 "choices": [
                     {"label": "Accept leadership", "emoji": "👑", "hint": "Stay forever", "result": "You're HOME. Forever. Peace.", "flag": "ending_leader", "major": True},
                     {"label": "Decline - wanderer", "emoji": "🌍", "hint": "Free spirit", "result": "You're not meant to be caged. Even by love.", "flag": "ending_wanderer", "major": True}
                 ]},
                {"title": "Your Brother's Secret", "narrative": "Elias confesses: He was JEALOUS of you.\n\n'You got to leave. Chase dreams. I was stuck here, watching Father die ALONE.'\n\nPain. Guilt. Understanding.", "location": "Cemetery Night", "npc": "Elias", "mood": "dark",
                 "choices": [
                     {"label": "I'm sorry", "emoji": "🙏", "hint": "Humility", "result": "He cries. You cry. Brothers again.", "consequences": {"reputation": {"Family": 100}}},
                     {"label": "You could have left too", "emoji": "🤷", "hint": "Harsh truth", "result": "'Maybe. But I STAYED. That's the difference.'", "consequences": {"reputation": {"Family": -20}}}
                 ]},
                {"title": "The Wedding", "narrative": "If you fought for Sera, you MARRY her.\n\nVillage divided. Some celebrate. Some condemn.\n\nLove won. But at what cost?", "location": "Village Chapel", "mood": "bittersweet",
                 "condition": {"sera_together": True},
                 "choices": [
                     {"label": "Embrace the scandal", "emoji": "💍", "hint": "Love > everything", "result": "Married! Happy! Controversial! Who cares?", "flag": "ending_controversial_love", "major": True}
                 ]},
                
                # ACT 3: RESOLUTION (Scenes 16-22)
                {"title": "One Year Later", "narrative": "Time passed. Wounds healed. Some.\n\nWhat became of you?", "location": "Village - One Year", "mood": "reflective",
                 "choices": [
                     {"label": "Reflect on changes", "emoji": "💭", "hint": "Growth", "result": "You're not who you were. Better? Different? Both.", "consequences": {"xp_gain": 100}}
                 ]},
                {"title": "Legacy - Father's Grave", "narrative": "You visit Father's grave regularly now.\n\n'I came back, Dad. Late. But I came back.'", "location": "Cemetery", "mood": "peaceful",
                 "choices": [
                     {"label": "Leave flowers", "emoji": "🌹", "hint": "Respect", "result": "Wind rustles. Peace.", "consequences": {"xp_gain": 50}},
                     {"label": "Tell him everything", "emoji": "💬", "hint": "Closure", "result": "You speak for hours. Tears. Laughter. Forgiveness.", "consequences": {"xp_gain": 150}, "flag": "closure_found"}
                 ]},
                {"title": "Marcus's Success", "narrative": "Marcus's flying machine WORKS! First flight!\n\nIf you're partners, you SOAR together.", "location": "Testing Field", "mood": "triumphant",
                 "condition": {"marcus_redeemed": True},
                 "choices": [
                     {"label": "Fly with him!", "emoji": "🕊️", "hint": "Partnership", "result": "FLIGHT! Together! Dreams realized!", "consequences": {"xp_gain": 300}}
                 ]},
                {"title": "Sera's Pregnancy", "narrative": "If married to Sera: she's pregnant.\n\nNew life. New beginning.", "location": "Your Home", "npc": "Sera", "mood": "joyful",
                 "condition": {"sera_together": True},
                 "choices": [
                     {"label": "Joy and terror", "emoji": "👶", "hint": "Fatherhood", "result": "You're going to be a FATHER. Everything changes.", "flag": "ending_family_man", "major": True}
                 ]},
                {"title": "The Wanderer's Goodbye", "narrative": "If you chose to leave: you say goodbye.\n\nAgain.\n\nBut this time... they understand.", "location": "Village Gate", "mood": "bittersweet",
                 "condition": {"ending_wanderer": True},
                 "choices": [
                     {"label": "Promise to return", "emoji": "🤝", "hint": "Hope", "result": "'We'll be here.' They will. You know they will.", "consequences": {"xp_gain": 200}}
                 ]},
                {"title": "Coward's Path - Empty Road", "narrative": "You fled again. AGAIN.\n\nAlone. Rich. Empty.", "location": "The Road - Nowhere", "mood": "dark",
                 "condition": {"fled_again": True},
                 "choices": [
                     {"label": "Regret everything", "emoji": "💔", "hint": "Despair", "result": "You ruined everything. Again. Forever.", "flag": "ending_eternal_coward", "major": True}
                 ]},
                {"title": "Epilogue - 10 Years Forward", "narrative": "Another decade passes.\n\nHow did your story end?", "location": "The Future", "mood": "reflective",
                 "choices": [
                     {"label": "Remember", "emoji": "📖", "hint": "Closure", "result": "You chose. You lived. You loved. Enough.", "flag": "ending_complete"}
                 ]}
            ],
            
            # 15 RANDOM ENCOUNTERS - Emotional/social drama!
            "random_encounters": [
                {"id": "gossip", "title": "Village Gossip", "type": "Social", "narrative": "People whisper when you pass.",
                 "challenge": {"stat": "cha", "dc": 12, "success": "You win them over gradually!", "failure": "Rumors spread!",
"success_consequences": {"reputation": {"Village": 10}}, "failure_consequences": {"reputation": {"Village": -10}}}},
                {"id": "child", "title": "Child's Question", "type": "Moral", "narrative": "Small child: 'Why did you leave Mommy Sera?'",
                 "challenge": {"stat": "cha", "dc": 14, "success": "Honest, kind answer.", "failure": "You hurt the child.",
"success_consequences": {"xp_gain": 50}, "failure_consequences": {"reputation": {"Village": -15}}}},
                {"id": "nightmare", "title": "Nightmare - Mother", "type": "Emotional", "narrative": "You dream of Mother's funeral YOU missed.",
                 "challenge": {"stat": "wis", "dc": 15, "success": "You wake crying but healing.", "failure": "Trauma deepens.",
"success_consequences": {"xp_gain": 75}, "failure_consequences": {"hp_change": -10}}},
                {"id": "drunk_elias", "title": "Drunk Brother", "type": "Family", "narrative": "Elias drinks too much. Confesses pain.",
                 "challenge": {"stat": "cha", "dc": 13, "success": "You comfort him. Bond strengthens.", "failure": "Fight breaks out.",
"success_consequences": {"reputation": {"Family": 20}}, "failure_consequences": {"hp_change": -10}}},
                {"id": "sera_tears", "title": "Sera Cries Alone", "type": "Romance", "narrative": "You find Sera weeping in garden.",
                 "challenge": {"stat": "cha", "dc": 14, "success": "You comfort her.", "failure": "She pushes you away.",
"success_consequences": {"reputation": {"Sera": 20}}, "failure_consequences": {}}},
                {"id": "marcus_drinking", "title": "Marcus at Bar", "type": "Friend", "narrative": "Marcus drinks alone. Bitter.",
                 "challenge": {"stat": "cha", "dc": 15, "success": "You TALK. Really talk.", "failure": "He leaves angry.",
"success_consequences": {"reputation": {"Marcus": 15}, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "gareth_threat", "title": "Husband's Threat", "type": "Conflict", "narrative": "Gareth warns: 'Stay away from my wife.'",
                 "challenge": {"stat": "cha", "dc": 16, "success": "Diplomatic resolution.", "failure": "Violence threatened.",
"success_consequences": {}, "failure_consequences": {"reputation": {"Village": -20}}}},
                {"id": "festival", "title": "Harvest Festival", "type": "Social", "narrative": "Village celebrates. Will you join ?",
                 "challenge": {"stat": "cha", "dc": 11, "success": "You dance! You BELONG!", "failure": "You watch from afar.",
"success_consequences": {"reputation": {"Village": 25}, "xp_gain": 50}, "failure_consequences": {}}},
                {"id": "memory", "title": "Childhood Memory", "type": "Nostalgia", "narrative": "You pass the tree where you carved initials.",
                 "challenge": {"stat": "wis", "dc": 12, "success": "Sweet nostalgia.", "failure": "Painful regret.",
"success_consequences": {"xp_gain": 50}, "failure_consequences": {"hp_change": -5}}},
                {"id": "letter_old", "title": "Old Letters Found", "type": "Discovery", "narrative": "You find letters you NEVER sent home.",
                 "challenge": {"stat": "int", "dc": 13, "success": "Understanding your past.", "failure": "Just more guilt.",
"success_consequences": {"xp_gain": 100}, "failure_consequences": {}}},
                {"id": "sermon", "title": "Church Sermon", "type": "Moral", "narrative": "Priest: 'Prodigal son returns.' About YOU.",
                 "challenge": {"stat": "wis", "dc": 14, "success": "You accept the parallel.", "failure": "Resentful.",
"success_consequences": {"xp_gain": 75}, "failure_consequences": {}}},
                {"id": "children", "title": "Village Children", "type": "Social", "narrative": "Kids ask about your adventures!",
                 "challenge": {"stat": "cha", "dc": 11, "success": "You inspire them!", "failure": "They're disappointed.",
"success_consequences": {"reputation": {"Village": 15}}, "failure_consequences": {}}},
                {"id": "storm", "title": "Emotional Storm", "type": "Crisis", "narrative": "Everything hits at once. Breakdown imminent.",
                 "challenge": {"stat": "wis", "dc": 17, "success": "You SURVIVE the pain.", "failure": "Emotional collapse.",
"success_consequences": {"xp_gain": 150}, "failure_consequences": {"hp_change": -20}}},
                {"id": "forgiveness", "title": "Unexpected Forgiveness", "type": "Healing", "narrative": "Someone you hurt forgives you.",
                 "challenge": {"stat": "cha", "dc": 12, "success": "You accept grace.", "failure": "Can't accept it.",
"success_consequences": {"reputation": {"Village": 30}, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "proposal", "title": "Remarriage Proposal", "type": "Romance", "narrative": "If divorced Sera, she asks you back.",
                 "challenge": {"stat": "cha", "dc": 16, "success": "Complicated reunion.", "failure": "Too broken.",
"success_consequences": {"companion": "💕 Sera"}, "failure_consequences": {}}}
            ],
            
            # 12 SIDE QUESTS - Personal growth missions!
            "side_quests": [
                {"id": "garden_restore", "title": "Restore Mother's Garden", "narrative": "Her garden is overgrown. Bring it back to life.",
                 "rewards_hint": "🌸 Peace", "challenge": {"stat": "wis", "dc": 12, "success": "Beautiful again! Memorial.", "failure": "Too painful to complete.",
"success_consequences": {"reputation": {"Family": 30}, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "debt_pay", "title": "Pay Father's Debts", "narrative": "Father owed money. Pay it off.",
                 "rewards_hint": "💰 Honor", "challenge": {"stat": "int", "dc": 11, "success": "Debts cleared! Family honored!", "failure": "Can't afford it.",
"success_consequences": {"gold_change": -500, "reputation": {"Family": 40}}, "failure_consequences": {}}},
                {"id": "elias_business", "title": "Help Brother's Business", "narrative": "Elias struggles financially. Help him.",
                 "rewards_hint": "🤝 Brotherhood", "challenge": {"stat": "int", "dc": 14, "success": "Business THRIVES! He's grateful!", "failure": "Makes it worse.",
"success_consequences": {"reputation": {"Family": 50}, "xp_gain": 150}, "failure_consequences": {"reputation": {"Family": -20}}}},
                {"id": "sera_gift", "title": "Perfect Gift for Sera", "narrative": "Find something that says 'I'm sorry.'",
                 "rewards_hint": "💝 Romance", "challenge": {"stat": "cha", "dc": 15, "success": "She softens. Maybe...", "failure": "Wrong gift. Awkward.",
"success_consequences": {"reputation": {"Sera": 40}, "xp_gain": 100}, "failure_consequences": {}}},
                {"id": "marcus_materials", "title": "Get Rare Materials", "narrative": "Marcus needs rare metal for invention.",
                 "rewards_hint": "⚒️ Partnership", "challenge": {"stat": "int", "dc": 14, "success": "Materials secured! Progress!", "failure": "Can't find them.",
"success_consequences": {"reputation": {"Marcus": 30}, "xp_gain": 125}, "failure_consequences": {}}},
                {"id": "festival_organize", "title": "Organize Festival", "narrative": "Prove you CARE about village. Organize event.",
                 "rewards_hint": "🎉 Community", "challenge": {"stat": "cha", "dc": 16, "success": "BEST FESTIVAL EVER!", "failure": "Disaster. Embarrassing.",
"success_consequences": {"reputation": {"Village": 60}, "xp_gain": 200}, "failure_consequences": {"reputation": {"Village": -30}}}},
                {"id": "therapy_elias", "title": "Talk Through Pain with Elias", "narrative": "Deep conversation. Heal old wounds.",
                 "rewards_hint": "❤️‍🩹 Healing", "challenge": {"stat": "cha", "dc": 15, "success": "Catharsis! True healing!", "failure": "Too painful. Aborted.",
"success_consequences": {"reputation": {"Family": 70}, "xp_gain": 175}, "failure_consequences": {}}},
                {"id": "shrine_rebuild", "title": "Rebuild Family Shrine", "narrative": "Old shrine to ancestors. Rebuild it.",
                 "rewards_hint": "⛩️ Legacy", "challenge": {"stat": "wis", "dc": 14, "success": "Shrine restored! Ancestors honored!", "failure": "Half-finished.",
"success_consequences": {"reputation": {"Family": 40}, "xp_gain": 150}, "failure_consequences": {}}},
                {"id": "teach_children", "title": "Teach Village Children", "narrative": "Share your knowledge with next generation.",
                 "rewards_hint": "📚 Legacy", "challenge": {"stat": "int", "dc": 13, "success": "They're inspired! Future secured!", "failure": "Boring lessons.",
"success_consequences": {"reputation": {"Village": 50}, "xp_gain": 125}, "failure_consequences": {}}},
                {"id": "duel_honor", "title": "Honor Duel with Gareth", "narrative": "Settle Sera situation honorably.",
                 "rewards_hint": "⚔️ Resolution", "challenge": {"stat": "str", "dc": 16, "success": "Victory! He respects you now!", "failure": "Defeat. Humiliation.",
"success_consequences": {"xp_gain": 200}, "failure_consequences": {"hp_change": -30}}},
                {"id": "memoir", "title": "Write Your Memoir", "narrative": "Document your journey. Share lessons.",
                 "rewards_hint": "📖 Wisdom", "challenge": {"stat": "int", "dc": 15, "success": "Published! Village treasure!", "failure": "Too painful to finish.",
"success_consequences": {"xp_gain": 250, "reputation": {"Village": 40}}, "failure_consequences": {}}},
                {"id": "reconcile_all", "title": "Ultimate Reconciliation", "narrative": "Gather EVERYONE. Apologize publicly.",
                 "rewards_hint": "🙏 Complete Redemption", "challenge": {"stat": "cha", "dc": 18, "success": "FORGIVEN! All relationships healed!", "failure": "Some never forgive.",
"success_consequences": {"reputation": {"Village": 100, "Family": 100, "Marcus": 100}, "xp_gain": 500}, "failure_consequences": {}}}
            ],
            
            "endings": {
                "ending_leader": {"requires": {"ending_leader": True}, "narrative": "🏠 **THE VILLAGE LEADER**\n\nYou stayed. Led. Prospered. Home forever."},
                "ending_wanderer": {"requires": {"ending_wanderer": True}, "narrative": "🌍 **THE ETERNAL WANDERER**\n\nYou left again. But this time, with love behind you."},
                "ending_controversial_love": {"requires": {"ending_controversial_love": True}, "narrative": "💕 **LOVE ABOVE ALL**\n\nScandal. Judgment. But LOVE. Worth it."},
                "ending_family_man": {"requires": {"ending_family_man": True}, "narrative": "👶 **THE FATHER**\n\nNew life. New beginning. Cycle of love continues."},
                "ending_eternal_coward": {"requires": {"ending_eternal_coward": True}, "narrative": "💔 **THE COWARD**\n\nYou ran. Again. Forever running. Empty. Alone."},
                "default": "You returned. Made amends. Not perfect. But enough."
            }
        }
    
    def _gen_trade_empire(self, char_class: str = None) -> dict:
        """Trade/business empire campaign - INT focused - 24 SCENES + 15 ENCOUNTERS + 12 QUESTS = 51 TOTAL!"""
        intro = "You have 100 gold, a cart, and a dream.\n\n**Build an empire.**\n\n"
        if char_class == 'rogue':
            intro += "**As a rogue**, you know the BLACK market. Profitable. Dangerous."
        elif char_class == 'wizard':
            intro += "**As a wizard**, you'll sell ENCHANTED goods. Magic = money."
        elif char_class == 'cleric':
            intro += "**As a cleric**, you'll build an ETHICAL empire. Can it work?"
        
        return {
            "name": "Rise of the Trade Baron",
            "type": "Trade Empire",
            "scenes": [
                # ACT 1: HUMBLE BEGINNINGS (Scenes 1-6)
                {"title": "The First Day", "narrative": intro + "Market square. Hundreds of merchants.\n\n**What will you sell?**", "location": "City Market", "mood": "hopeful",
                 "choices": [
                     {"label": "Common goods (safe)", "emoji": "🍞", "hint": "Slow growth", "result": "Bread, cloth, basics. Reliable. Boring.", "flag": "safe_merchant"},
                     {"label": "Luxury goods (risky)", "emoji": "💎", "hint": "High risk/reward", "result": "Jewels, silk, perfumes. Expensive. Profitable!", "flag": "luxury_merchant", "major": True},
                     {"label": "Illegal goods (dangerous)", "emoji": "🗡️", "hint": "Criminal", "result": "Weapons, poisons, contraband. Dangerous. VERY profitable.", "flag": "black_market", "major": True}
                 ]},
                {"title": "First Customer", "narrative": "A wealthy noble approaches.\n\n**Noble:** 'I'll pay triple... if you deliver by tonight. Impossible deadline.'", "location": "Your Stall", "npc": "Lord Varen", "mood": "tense",
                 "challenge": {"type": "Business", "stat": "int", "dc": 13, "description": "Can you deliver?", "success": "You DELIVER! Triple profit! Reputation!", "failure": "You fail. Reputation damaged.", "success_consequences": {"gold_change": 150, "reputation": {"Nobles": 20}}, "failure_consequences": {"reputation": {"Nobles": -15}}}},
                {"title": "Competition Appears", "narrative": "**Kassandra the Ruthless** - veteran merchant. Controls half the market.\n\nShe NOTICES you. Not good.\n\n**Kassandra:** 'New blood. Cute. You'll fail within a month.'", "location": "Market Square", "npc": "Kassandra", "mood": "competitive",
                 "choices": [
                     {"label": "Challenge her", "emoji": "💪", "hint": "Confident", "result": "She LAUGHS. 'I like you. See you at bankruptcy court.'", "flag": "kassandra_rival", "major": True},
                     {"label": "Propose alliance", "emoji": "🤝", "hint": "Diplomatic", "result": "'Alliance? With YOU? ...Maybe. Prove yourself first.'", "flag": "kassandra_neutral"},
                     {"label": "Undercut her prices", "emoji": "💰", "hint": "Aggressive", "result": "Price war BEGINS! Dangerous game!", "consequences": {"gold_change": -50}, "flag": "price_war", "major": True}
                 ]},
                {"title": "The Merchant's Guild", "narrative": "Guild invitation arrives.\n\nJoin = protection, connections, RULES.\n\nRefuse = freedom, enemies, struggle.\n\n**What do you choose?**", "location": "Guild Hall", "mood": "official",
                 "choices": [
                     {"label": "Join the Guild", "emoji": "🏛️", "hint": "Play by rules", "result": "Member! Fees: 50 gold/month. Protection: priceless.", "consequences": {"companion": "⚖️ Guild Member"}, "flag": "guild_member", "major": True},
                     {"label": "Refuse - stay independent", "emoji": "🚫", "hint": "Lone wolf", "result": "Freedom! But Guild won't help you. Ever.", "flag": "independent", "major": True}
                 ]},
                {"title": "Employee Crisis", "narrative": "You hired 3 workers. One is STEALING from you.\n\nWho?", "location": "Warehouse", "mood": "suspicious",
                 "challenge": {"type": "Investigation", "stat": "int", "dc": 14, "description": "Catch the thief", "success": "You identify the thief! Fire them!", "failure": "Wrong person accused. Morale plummets.", "success_consequences": {"gold_change": 75}, "failure_consequences": {"reputation": {"Workers": -30}}}},
                {"title": "First Big Contract", "narrative": "City guard needs supplies. 1000 gold contract!\n\nBut... delivery in 3 days. Impossible?\n\n**Risk it?**", "location": "Guard Captain's Office", "npc": "Captain Thane", "mood": "opportunity",
                 "choices": [
                     {"label": "Accept (work day/night)", "emoji": "💼", "hint": "Ambition", "result": "You WORK NONSTOP. Make it! Contract secured!", "consequences": {"gold_change": 1000, "xp_gain": 200}, "flag": "guard_contract"},
                     {"label": "Decline (too risky)", "emoji": "👎", "hint": "Caution", "result": "Captain disappointed. Contract goes to Kassandra.", "consequences": {"reputation": {"Guard": -20}}}
                 ]},
                
                # ACT 2: EXPANSION (Scenes 7-15)
                {"title": "Expansion Opportunity", "narrative": "You can buy a second location!\n\n- **Port District** (trade routes, expensive)\n- **Slums** (cheap, dangerous)\n- **Noble Quarter** (prestige, restrictive)", "location": "Real Estate Office", "mood": "strategic",
                 "choices": [
                     {"label": "Port District", "emoji": "⚓", "hint": "Trade focus", "result": "SHIPPING ROUTES! International trade!", "consequences": {"gold_change": -800}, "flag": "port_location", "major": True},
                     {"label": "Slums", "emoji": "🏚️", "hint": "Low cost", "result": "Cheap rent. Sketchy customers. Crime issues.", "consequences": {"gold_change": -200}, "flag": "slum_location"},
                     {"label": "Noble Quarter", "emoji": "👑", "hint": "Prestige", "result": "LUXURY clientele! High costs, high rewards!", "consequences": {"gold_change": -1200}, "flag": "noble_location", "major": True}
                 ]},
                {"title": "Kassandra's Sabotage", "narrative": "Your warehouse BURNS. Arson.\n\nKassandra's men seen nearby.\n\n**She denies involvement.** Do you believe her?", "location": "Burned Warehouse", "mood": "chaotic",
                 "choices": [
                     {"label": "Retaliate - burn HER warehouse", "emoji": "🔥", "hint": "Revenge", "result": "WAR. Guild intervenes. Both fined.", "consequences": {"gold_change": -500, "reputation": {"Guild": -50}}, "flag": "merchant_war"},
                     {"label": "Sue her in Guild Court", "emoji": "⚖️", "hint": "Legal", "result": "Trial! You NEED proof!", "flag": "lawsuit_kassandra"},
                     {"label": "Absorb the loss", "emoji": "💔", "hint": "Move on", "result": "Costs you 800 gold. But no more drama.", "consequences": {"gold_change": -800}}
                 ]},
                {"title": "The Lawsuit", "narrative": "If you sued Kassandra, court convenes.\n\nEvidence? Witnesses? PROOF?", "location": "Guild Court", "npc": "Judge Morick", "mood": "tense",
                 "condition": {"lawsuit_kassandra": True},
                 "challenge": {"type": "Legal", "stat": "int", "dc": 16, "description": "Win the case", "success": "GUILTY! She pays 2000 gold damages!", "failure": "Insufficient evidence. Case dismissed. She SMIRKS.", "success_consequences": {"gold_change": 2000, "reputation": {"Guild": 30}}, "failure_consequences": {"reputation": {"Guild": -20}, "reputation": {"Kassandra": -50}}}},
                {"title": "Partnership Offer", "narrative": "Mysterious investor: **Corvax**.\n\n'I'll invest 5000 gold. You give me 40% ownership.'\n\nDeal?", "location": "Tavern Meeting", "npc": "Corvax", "mood": "suspicious",
                 "choices": [
                     {"label": "Accept partnership", "emoji": "🤝", "hint": "Fast growth", "result": "5000 GOLD! Expansion! ...But he controls 40%.", "consequences": {"gold_change": 5000}, "flag": "corvax_partner", "major": True},
                     {"label": "Reject - stay solo", "emoji": "🚫", "hint": "Control", "result": "'Your loss.' He leaves. Independent forever.", "flag": "solo_empire"}
                 ]},
                {"title": "Employee Unionization", "narrative": "Your 20 workers demand RIGHTS.\n\n- Better pay\n- Safer conditions\n- Shorter hours\n\n**Do you negotiate?**", "location": "Warehouse", "mood": "tense",
                 "choices": [
                     {"label": "Grant demands (expensive)", "emoji": "✊", "hint": "Ethical", "result": "They're LOYAL now! Productivity UP!", "consequences": {"gold_change": -300}, "flag": "ethical_employer", "reputation": {"Workers": 100}},
                     {"label": "Fire all, hire new", "emoji": "❌", "hint": "Ruthless", "result": "Replaced! Cheap labor! ...Strikes incoming?", "consequences": {"reputation": {"Workers": -100}}, "flag": "ruthless_employer"},
                     {"label": "Compromise", "emoji": "⚖️", "hint": "Balanced", "result": "Middle ground. Acceptable.", "consequences": {"gold_change": -150}, "reputation": {"Workers": 30}}
                 ]},
                {"title": "Illegal Opportunity", "narrative": "Black market contact: 'Smuggle this. 10,000 gold profit. No questions.'\n\n**It's clearly drugs.**", "location": "Dark Alley", "npc": "Shadows", "mood": "dark",
                 "choices": [
                     {"label": "Accept (crime)", "emoji": "💀", "hint": "Profit > morals", "result": "PROFIT! But you're a criminal now.", "consequences": {"gold_change": 10000}, "flag": "criminal_empire", "major": True},
                     {"label": "Refuse", "emoji": "🛡️", "hint": "Ethics", "result": "Clean conscience. Poor wallet.", "consequences": {"reputation": {"Honor": 50}}},
                     {"label": "Report to authorities", "emoji": "🚨", "hint": "Hero", "result": "Smugglers arrested! Guard rewards you!", "consequences": {"gold_change": 500, "reputation": {"Guard": 50}}}
                 ]},
                {"title": "Corvax's True Nature", "narrative": "If partnered with Corvax: you discover he's using YOUR business to launder money.\n\nCRIMINAL.", "location": "Secret Meeting Overhead", "npc": "Corvax", "mood": "dark",
                 "condition": {"corvax_partner": True},
                 "choices": [
                     {"label": "Confront him", "emoji": "⚔️", "hint": "Risky", "result": "He KILLS you... or buys you OUT. (He buys you out)", "consequences": {"gold_change": 15000}, "flag": "corvax_buyout"},
                     {"label": "Join his schemes", "emoji": "💰", "hint": "Crime", "result": "RICH. Corrupt. Powerful. Criminal.", "consequences": {"gold_change": 25000}, "flag": "crime_lord", "major": True},
                     {"label": "Report to authorities", "emoji": "🚨", "hint": "Justice", "result": "He's arrested! You lose 40% but gain INTEGRITY.", "consequences": {"reputation": {"Honor": 100}, "gold_change": -2000}}
                 ]},
                {"title": "The Monopoly", "narrative": "You control 60% of the market.\n\nGuild accuses you of MONOPOLY. Illegal.\n\n**Trial incoming.**", "location": "Guild Hall", "mood": "tense",
                 "choices": [
                     {"label": "Bribe the judges", "emoji": "💰", "hint": "Corruption", "result": "Case dismissed! Cost: 5000 gold.", "consequences": {"gold_change": -5000}, "flag": "corrupt_victory"},
                     {"label": "Fight legally", "emoji": "⚖️", "hint": "Honor", "result": "LEGAL battle! Need evidence of fair practices!", "flag": "monopoly_trial"}
                 ]},
                {"title": "The Monopoly Trial", "narrative": "Prove your empire is FAIR.", "location": "Guild Court", "npc": "Three Judges", "mood": "dramatic",
                 "condition": {"monopoly_trial": True},
                 "challenge": {"type": "Legal Defense", "stat": "int", "dc": 17, "description": "Defend your practices", "success": "ACQUITTED! Fair competition proven!", "failure": "GUILTY. Empire split. Assets seized.", "success_consequences": {"xp_gain": 500}, "failure_consequences": {"gold_change": -10000}, "flag": "monopoly_broken"}},
                {"title": "Hostile Takeover", "narrative": "Kassandra is BANKRUPT. You can buy her out.\n\nEnd the rivalry. Permanently.", "location": "Guild Auction", "npc": "Kassandra", "mood": "dramatic",
                 "choices": [
                     {"label": "Buy her business", "emoji": "💰", "hint": "Domination", "result": "Her empire is YOURS! She's destroyed!", "consequences": {"gold_change": -8000}, "flag": "kassandra_conquered", "major": True},
                     {"label": "Offer partnership", "emoji": "🤝", "hint": "Mercy", "result": "She's SHOCKED. 'You... saved me?' Allies now!", "consequences": {"gold_change": -4000, "companion": "🤝 Ally Kassandra"}, "flag": "kassandra_ally", "major": True},
                     {"label": "Let her fall", "emoji": "👎", "hint": "Indifference", "result": "Someone else buys her. Rival remains.", "consequences": {}}
                 ]},
                
                # ACT 3: EMPIRE SUMMIT (Scenes 16-24)
                {"title": "The Trade Summit", "narrative": "International Trade Summit. 50 nations.\n\nYou're INVITED as a major merchant.\n\n**Negotiate deals.**", "location": "Royal Palace", "mood": "prestigious",
                 "challenge": {"type": "Diplomacy", "stat": "cha", "dc": 15, "description": "Impress world leaders", "success": "Trade routes with 10 kingdoms! EMPIRE EXPANDS!", "failure": "Deals fall through. Opportunity lost.", "success_consequences": {"gold_change": 20000, "xp_gain": 500}, "failure_consequences": {}}},
                {"title": "The Inheritance", "narrative": "A distant relative dies. Leaves you...\n\n**50,000 GOLD.**\n\nNo strings attached. Windfall.", "location": "Lawyer's Office", "mood": "fortunate",
                 "choices": [
                     {"label": "Invest in empire", "emoji": "📈", "hint": "Growth", "result": "MASSIVE expansion! Branches in 5 cities!", "consequences": {"xp_gain": 300}},
                     {"label": "Donate to charity", "emoji": "❤️", "hint": "Ethical", "result": "Reputation SOARS! Beloved!", "consequences": {"gold_change": 50000, "reputation": {"Common Folk": 200}}},
                     {"label": "Retire early", "emoji": "🏖️", "hint": "Peace", "result": "You're DONE. Rich. Retired. Happy.", "flag": "ending_retired", "major": True}
                 ]},
                {"title": "Worker Strike", "narrative": "If ruthless employer: city-wide STRIKE. No one works.\n\nYour empire HALTS.", "location": "Empty Warehouses", "mood": "chaotic",
                 "condition": {"ruthless_employer": True},
                 "choices": [
                     {"label": "Cave to demands", "emoji": "✊", "hint": "Surrender", "result": "Workers WIN. You lose control.", "consequences": {"gold_change": -5000}},
                     {"label": "Hire mercenaries", "emoji": "⚔️", "hint": "Violence", "result": "BLOODSHED. Strike broken. Reputation destroyed.", "consequences": {"reputation": {"City": -200}}, "flag": "blood_baron"}
                 ]},
                {"title": "The Rival Consortium", "narrative": "Five merchants unite AGAINST you.\n\n**They control 40% of market. War.**", "location": "Market District", "mood": "war",
                 "choices": [
                     {"label": "Price war (lose money short-term)", "emoji": "💰", "hint": "Attrition", "result": "You OUTLAST them! They break!", "consequences": {"gold_change": -10000, "xp_gain": 400}, "flag": "consortium_defeated"},
                     {"label": "Sabotage their supplies", "emoji": "🔥", "hint": "Dirty", "result": "Their warehouses burn. Victory. Dishonor.", "consequences": {"reputation": {"Guild": -100}}, "flag": "saboteur"},
                     {"label": "Negotiate merger", "emoji": "🤝", "hint": "Diplomatic", "result": "MERGER! You control 80% market!", "consequences": {"companion": "🏢 Consortium"}, "flag": "mega_corporation"}
                 ]},
                {"title": "Government Regulation", "narrative": "King declares: 'No one merchant shall control >50% market.'\n\n**You violate this. Penalty: EXILE.**", "location": "Royal Decree", "mood": "crisis",
                 "choices": [
                     {"label": "Divest (obey law)", "emoji": "⚖️", "hint": "Legal", "result": "You split empire. Legal. Still rich.", "consequences": {"gold_change": -15000}},
                     {"label": "Bribe the King", "emoji": "👑", "hint": "Corruption", "result": "He ACCEPTS. Law ignored. Cost: 30k.", "consequences": {"gold_change": -30000}, "flag": "corrupt_empire"},
                     {"label": "Flee to another kingdom", "emoji": "🏃", "hint": "Exile", "result": "You LEAVE. Start over elsewhere.", "flag": "ending_exiled", "major": True}
                 ]},
                {"title": "The Charity Hospital", "narrative": "If ethical: workers beg you to fund free hospital.\n\nCost: 20,000 gold. Profit: 0.", "location": "Workers' Petition", "mood": "moral",
                 "condition": {"ethical_employer": True},
                 "choices": [
                     {"label": "Fund the hospital", "emoji": "🏥", "hint": "Altruism", "result": "BELOVED! You're a HERO!", "consequences": {"gold_change": -20000, "reputation": {"City": 300}, "xp_gain": 500}, "flag": "philanthropist"},
                     {"label": "Decline", "emoji": "💰", "hint": "Business", "result": "They understand. Business is business.", "consequences": {}}
                 ]},
                {"title": "Kassandra's Proposal", "narrative": "If allied with Kassandra: she proposes MARRIAGE.\n\n'Business AND pleasure. We'd be unstoppable.'", "location": "Private Dinner", "npc": "Kassandra", "mood": "romantic",
                 "condition": {"kassandra_ally": True},
                 "choices": [
                     {"label": "Accept marriage", "emoji": "💍", "hint": "Power couple", "result": "MARRIED! Combined empire! True partnership!", "consequences": {"companion": "💕 Wife Kassandra"}, "flag": "ending_dynasty", "major": True},
                     {"label": "Keep it professional", "emoji": "💼", "hint": "Business only", "result": "She respects that. Partners forever.", "consequences": {}}
                 ]},
                {"title": "The Final Deal", "narrative": "Emperor himself offers: Buy your ENTIRE empire.\n\n**Price: 500,000 gold.**\n\nYou'd be richest person alive. But... no empire.", "location": "Imperial Palace", "npc": "Emperor Anton", "mood": "monumental",
                 "choices": [
                     {"label": "SELL - retire as baron", "emoji": "💎", "hint": "Ultimate wealth", "result": "500k GOLD! Retired! Legendary!", "flag": "ending_sold", "major": True},
                     {"label": "REFUSE - keep empire", "emoji": "🏰", "hint": "Legacy", "result": "Empire is YOURS forever! Legacy!", "flag": "ending_empire_keeper", "major": True}
                 ]},
                {"title": "Epilogue - The Trade Baron", "narrative": "10 years later.\n\nWhat became of your empire?", "location": "The Future", "mood": "reflective",
                 "choices": [
                     {"label": "Look back on legacy", "emoji": "📜", "hint": "Reflection", "result": "You built something. Good or evil. But YOURS.", "flag": "ending_complete"}
                 ]}
            ],
            
            # 15 RANDOM ENCOUNTERS - Business chaos!
            "random_encounters": [
                {"id": "competitor_sabotage", "title": "Competitor Sabotage", "type": "Business", "narrative": "Rival burns your shipment!",
                 "challenge": {"stat": "int", "dc": 14, "success": "You trace it back! Retaliate!", "failure": "500 gold lost.",
                 "success_consequences": {"reputation": {"Rivals": -20}}, "failure_consequences": {"gold_change": -500}}},
                {"id": "tax_audit", "title": "Tax Audit", "type": "Legal", "narrative": "Government audits your books!",
                 "challenge": {"stat": "int", "dc": 15, "success": "Books clean! No issues!", "failure": "Fined 1000 gold!",
                 "success_consequences": {}, "failure_consequences": {"gold_change": -1000}}},
                {"id": "trade_deal", "title": "Spontaneous Deal", "type": "Opportunity", "narrative": "Merchant offers rare goods!",
                 "challenge": {"stat": "int", "dc": 13, "success": "Good deal! Profit 800!", "failure": "Overpaid!",
                 "success_consequences": {"gold_change": 800}, "failure_consequences": {"gold_change": -200}}},
                {"id": "employee_theft", "title": "Employee Caught Stealing", "type": "Crisis", "narrative": "Worker stealing! Fire or forgive?",
                 "challenge": {"stat": "int", "dc": 14, "success": "Resolved fairly!", "failure": "Morale drops!",
                 "success_consequences": {"xp_gain": 50}, "failure_consequences": {"reputation": {"Workers": -20}}}},
                {"id": "market_crash", "title": "Market Crash", "type": "Disaster", "narrative": "Prices PLUMMET! Panic!",
                 "challenge": {"stat": "int", "dc": 16, "success": "You predicted it! Hedged bets!", "failure": "Lose 2000 gold!",
                 "success_consequences": {"xp_gain": 200}, "failure_consequences": {"gold_change": -2000}}},
                {"id": "innovation", "title": "New Invention", "type": "Opportunity", "narrative": "Inventor offers new tech!",
                 "challenge": {"stat": "int", "dc": 14, "success": "Invest! Major advantage!", "failure": "Scam! Lost money!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"gold_change": -500}}},
                {"id": "guild_politics", "title": "Guild Election", "type": "Politics", "narrative": "Guild votes! Support who?",
                 "challenge": {"stat": "cha", "dc": 13, "success": "Your candidate WINS!", "failure": "Enemy elected!",
                 "success_consequences": {"reputation": {"Guild": 30}}, "failure_consequences": {"reputation": {"Guild": -20}}}},
                {"id": "shipwreck", "title": "Shipwreck Recovery", "type": "Salvage", "narrative": "Your ship sinks! Insurance?",
                 "challenge": {"stat": "int", "dc": 15, "success": "Insured! No loss!", "failure": "3000 gold GONE!",
                 "success_consequences": {}, "failure_consequences": {"gold_change": -3000}}},
                {"id": "bribe_offer", "title": "Bribe Offer", "type": "Corruption", "narrative": "Official wants bribe. Pay?",
                 "challenge": {"stat": "cha", "dc": 14, "success": "Negotiate lower bribe!", "failure": "Overpay or refused!",
                 "success_consequences": {"gold_change": -200}, "failure_consequences": {"gold_change": -800}}},
                {"id": "warehouse_fire", "title": "Warehouse Fire", "type": "Disaster", "narrative": "FIRE! Save what you can!",
                 "challenge": {"stat": "str", "dc": 14, "success": "Saved 80% inventory!", "failure": "Total loss!",
                 "success_consequences": {"gold_change": -400}, "failure_consequences": {"gold_change": -2000}}},
                {"id": "noble_patron", "title": "Noble Patronage", "type": "Opportunity", "narrative": "Duke offers exclusive contract!",
                 "challenge": {"stat": "cha", "dc": 15, "success": "Contract secured! Prestige!", "failure": "Insulted him!",
                 "success_consequences": {"gold_change": 1500, "reputation": {"Nobles": 40}}, "failure_consequences": {}}},
                {"id": "strike_threat", "title": "Strike Threatened", "type": "Labor", "narrative": "Workers unhappy! Negotiate!",
                 "challenge": {"stat": "cha", "dc": 14, "success": "Avoided strike!", "failure": "Production halts!",
                 "success_consequences": {}, "failure_consequences": {"gold_change": -1000}}},
                {"id": "espionage", "title": "Corporate Espionage", "type": "Intrigue", "narrative": "Spy selling competitor secrets!",
                 "challenge": {"stat": "int", "dc": 15, "success": "Intel gained! Advantage!", "failure": "Double agent! Betrayed!",
                 "success_consequences": {"xp_gain": 150}, "failure_consequences": {"gold_change": -800}}},
                {"id": "lottery_win", "title": "Lucky Windfall", "type": "Luck", "narrative": "Investment pays off HUGE!",
                 "challenge": {"stat": "int", "dc": 12, "success": "5000 gold profit!", "failure": "Modest 500 gain.",
                 "success_consequences": {"gold_change": 5000}, "failure_consequences": {"gold_change": 500}}},
                {"id": "scandal", "title": "Public Scandal", "type": "Crisis", "narrative": "Rumor spreads! Damage control!",
                 "challenge": {"stat": "cha", "dc": 16, "success": "Quashed! Reputation saved!", "failure": "Reputation destroyed!",
                 "success_consequences": {}, "failure_consequences": {"reputation": {"City": -80}}}}
            ],
            
            # 12 SIDE QUESTS - Business missions!
            "side_quests": [
                {"id": "rare_spice", "title": "Acquire Rare Spice", "narrative": "Find legendary spice. Priceless!",
                 "rewards_hint": "🌶️ 3000 gold", "challenge": {"stat": "int", "dc": 15, "success": "Spice secured! Sell for 3000!", "failure": "Fake spice. Scammed.",
                 "success_consequences": {"gold_change": 3000}, "failure_consequences": {"gold_change": -500}}},
                {"id": "trade_route", "title": "Establish Trade Route", "narrative": "Open new route. Risky but profitable!",
                 "rewards_hint": "🗺️ +1000 gold/season", "challenge": {"stat": "int", "dc": 14, "success": "Route OPEN! Passive income!", "failure": "Bandits control it.",
                 "success_consequences": {"companion": "📍 Trade Route"}, "failure_consequences": {}}},
                {"id": "hire_genius", "title": "Hire Business Genius", "narrative": "Recruit legendary manager!",
                 "rewards_hint": "🎓 +20% profits", "challenge": {"stat": "cha", "dc": 16, "success": "Hired! Empire optimized!", "failure": "They reject you.",
                 "success_consequences": {"companion": "🧠 Genius Manager", "xp_gain": 200}, "failure_consequences": {}}},
                {"id": "patent", "title": "Patent New Invention", "narrative": "Inventor needs funding. Partner?",
                 "rewards_hint": "💡 Monopoly item", "challenge": {"stat": "int", "dc": 15, "success": "Patented! Exclusive sales!", "failure": "Competitor patents it!",
                 "success_consequences": {"xp_gain": 250}, "failure_consequences": {}}},
                {"id": "hostile_takeover", "title": "Hostile Takeover", "narrative": "Buy out rival forcefully!",
                 "rewards_hint": "💼 Eliminate competition", "challenge": {"stat": "int", "dc": 17, "success": "Acquired! Monopoly grows!", "failure": "They resist! War begins!",
                 "success_consequences": {"gold_change": -5000, "xp_gain": 300}, "failure_consequences": {}}},
                {"id": "guild_leadership", "title": "Run for Guild Master", "narrative": "Campaign for Guild leadership!",
                 "rewards_hint": "👑 Control Guild", "challenge": {"stat": "cha", "dc": 17, "success": "ELECTED! You RUN the Guild!", "failure": "Defeated. Humiliation.",
                 "success_consequences": {"companion": "⚖️ Guild Master", "xp_gain": 400}, "failure_consequences": {}}},
                {"id": "bank_start", "title": "Start a Bank", "narrative": "Loans, interest, investment!",
                 "rewards_hint": "🏦 Financial empire", "challenge": {"stat": "int", "dc": 16, "success": "Bank OPENS! Profit machine!", "failure": "Bank run! Bankruptcy!",
                 "success_consequences": {"companion": "🏦 Bank", "xp_gain": 350}, "failure_consequences": {"gold_change": -10000}}},
                {"id": "insurance", "title": "Start Insurance Company", "narrative": "Insure merchants. Profit from fear!",
                 "rewards_hint": "🛡️ Steady income", "challenge": {"stat": "int", "dc": 15, "success": "Insurance empire! Safe profits!", "failure": "Claims bankrupt you!",
                 "success_consequences": {"companion": "🛡️ Insurance Co"}, "failure_consequences": {"gold_change": -5000}}},
                {"id": "charity", "title": "Found Charity", "narrative": "Give back. Build reputation!",
                 "rewards_hint": "❤️ Massive reputation", "challenge": {"stat": "cha", "dc": 14, "success": "BELOVED! Hero status!", "failure": "Seen as publicity stunt.",
                 "success_consequences": {"reputation": {"City": 150}, "xp_gain": 200}, "failure_consequences": {}}},
                {"id": "apprentice", "title": "Train an Heir", "narrative": "Teach someone your ways!",
                 "rewards_hint": "👨‍🎓 Legacy secured", "challenge": {"stat": "cha", "dc": 15, "success": "Heir trained! Legacy continues!", "failure": "They betray you!",
                 "success_consequences": {"companion": "👨‍🎓 Heir", "xp_gain": 250}, "failure_consequences": {}}},
                {"id": "mansion", "title": "Buy Merchant's Mansion", "narrative": "Ultimate status symbol!",
                 "rewards_hint": "🏰 Prestige +200", "challenge": {"stat": "int", "dc": 13, "success": "MANSION bought! Legendary!", "failure": "Overpaid massively.",
                 "success_consequences": {"gold_change": -20000, "reputation": {"Nobles": 100}}, "failure_consequences": {"gold_change": -30000}}},
                {"id": "dynasty", "title": "Establish Dynasty", "narrative": "Marry, have kids, build EMPIRE FAMILY!",
                 "rewards_hint": "👨‍👩‍👧‍👦 Eternal legacy", "challenge": {"stat": "cha", "dc": 16, "success": "Dynasty founded! Empire eternal!", "failure": "No heirs. Empire dies with you.",
                 "success_consequences": {"companion": "👨‍👩‍👧‍👦 Dynasty", "xp_gain": 500}, "failure_consequences": {}}}
            ],
            
            "endings": {
                "ending_retired": {"requires": {"ending_retired": True}, "narrative": "🏖️ **THE EARLY RETIREMENT**\n\nYou made it. Rich. Done. Beach forever."},
                "ending_exiled": {"requires": {"ending_exiled": True}, "narrative": "🏃 **THE EXILED BARON**\n\nFled kingdom. Started over. Built empire again."},
                "ending_dynasty": {"requires": {"ending_dynasty": True}, "narrative": "💍 **THE POWER DYNASTY**\n\nMarried Kassandra. Combined empire. Legendary."},
                "ending_sold": {"requires": {"ending_sold": True}, "narrative": "💎 **THE RICHEST PERSON ALIVE**\n\n500,000 gold. Retired. Immortalized."},
                "ending_empire_keeper": {"requires": {"ending_empire_keeper": True}, "narrative": "🏰 **THE ETERNAL EMPIRE**\n\nYou kept it. Grew it. Passed it down."},
                "crime_lord": {"requires": {"crime_lord": True}, "narrative": "💀 **THE CRIME LORD**\n\nRich through blood. Feared. Powerful. Evil."},
                "philanthropist": {"requires": {"philanthropist": True}, "narrative": "❤️ **THE PHILANTHROPIST**\n\nRich. Generous. Beloved. Saint of merchants."},
                "blood_baron": {"requires": {"blood_baron": True}, "narrative": "⚔️ **THE BLOOD BARON**\n\nBroken strikes with violence. Hated. Rich."},
                "default": "You built an empire. Success or failure? You decide."
            }
        }
    
    @app_commands.command(name="dnd", description="🎭 Enter the narrative. Every choice matters.")
    @app_commands.describe(campaign="Choose your epic")
    @app_commands.choices(campaign=[
        app_commands.Choice(name="👑 Court Intrigue - Politics, Lies, Power", value="Court Intrigue"),
        app_commands.Choice(name="🌊 World Explorer - Uncharted Waters", value="World Explorer"),
        app_commands.Choice(name="⚔️ War Campaign - Strategy & Blood", value="War Campaign"),
        app_commands.Choice(name="🔍 Mystery Detective - Uncover Truth", value="Mystery Detective"),
        app_commands.Choice(name="🌲 Wilderness Survival - Nature's Wrath", value="Wilderness Survival"),
        app_commands.Choice(name="🎭 Character Drama - Emotions & Betrayal", value="Character Drama"),
        app_commands.Choice(name="💰 Trade Empire - Build Your Fortune", value="Trade Empire"),
        app_commands.Choice(name="🌌 Infinity Adventure - Infinite Realities", value="Chaotic Mayhem")
    ])
    async def dnd_command(self, interaction: discord.Interaction, campaign: str):
        """Begin your story - choose Solo or Party mode"""
        await interaction.response.defer()
        
        user_id = interaction.user.id
        
        # Check existing session
        if user_id in self.active_sessions:
            await interaction.followup.send("❌ You're already in a campaign! Finish or quit first.")
            return
        
        # Show game mode selection: Solo, Create Party, Join Party
        # Show mode selection: Solo, Create Party, Join Party
        view = GameModeSelectView(self, user_id, interaction.user.display_name, campaign, interaction.channel)
        await interaction.followup.send(view=view)


async def setup(bot):
    await bot.add_cog(DND(bot))

